import logging
from typing import Dict, List, Any

logger = logging.getLogger(__name__)

def merge_matrices(matrix_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Takes an array of Deep Matrix JSONs and merges them into a single, unified JSON dictionary.
    Schema: mythologies -> mythology_name -> text_name -> nomenclature, species, properties.

    Args:
        matrix_list (List[Dict[str, Any]]): A list of dictionary objects representing the extracted data matrices.

    Returns:
        Dict[str, Any]: A single merged dictionary where conflicting nodes have their arrays appended to avoid data loss.
    """
    master_matrix: Dict[str, Any] = {"mythologies": {}}

    if not matrix_list:
        return master_matrix

    for matrix in matrix_list:
        if not isinstance(matrix, dict):
            logger.warning("Encountered non-dictionary matrix item. Skipping.")
            continue

        mythologies = matrix.get("mythologies", {})
        if not isinstance(mythologies, dict):
            logger.warning(f"Expected 'mythologies' to be a dict, got {type(mythologies)}. Skipping.")
            continue

        for myth_name, texts in mythologies.items():
            if not isinstance(texts, dict):
                logger.warning(f"Expected texts for mythology '{myth_name}' to be a dict, got {type(texts)}. Skipping.")
                continue

            if myth_name not in master_matrix["mythologies"]:
                master_matrix["mythologies"][myth_name] = {}

            for text_name, text_data in texts.items():
                if not isinstance(text_data, dict):
                    logger.warning(f"Expected data for text '{text_name}' to be a dict, got {type(text_data)}. Skipping.")
                    continue

                if text_name not in master_matrix["mythologies"][myth_name]:
                    master_matrix["mythologies"][myth_name][text_name] = {
                        "nomenclature": [],
                        "species": [],
                        "properties": []
                    }

                master_text = master_matrix["mythologies"][myth_name][text_name]

                # Helper function to append strings or extend lists
                def _append_or_extend(target_list: List[str], source_data: Any) -> None:
                    if isinstance(source_data, list):
                        target_list.extend([str(item) for item in source_data if item])
                    elif source_data:
                        target_list.append(str(source_data))

                _append_or_extend(master_text["nomenclature"], text_data.get("nomenclature"))
                _append_or_extend(master_text["species"], text_data.get("species"))
                _append_or_extend(master_text["properties"], text_data.get("properties"))

    return master_matrix

def prune_empty_nodes(master_matrix: Dict[str, Any]) -> Dict[str, Any]:
    """
    Crawls the merged dictionary and recursively deletes empty structural nodes.
    - If a Text object has an empty "properties" array, delete the Text entirely.
    - If a Mythology object has no Texts inside it after pruning, delete the Mythology entirely.
    - If the entire dictionary is empty after pruning, return exactly {}.

    Args:
        master_matrix (Dict[str, Any]): The merged master matrix to be pruned.

    Returns:
        Dict[str, Any]: A pristine dictionary with no empty sub-nodes. Returns {} if empty.
    """
    if not isinstance(master_matrix, dict) or "mythologies" not in master_matrix:
        logger.warning("Invalid master_matrix format provided to pruner.")
        return {}

    mythologies = master_matrix["mythologies"]
    if not isinstance(mythologies, dict):
        return {}

    # Cast to list to avoid RuntimeError: dictionary changed size during iteration
    myth_keys = list(mythologies.keys())

    for myth_name in myth_keys:
        texts = mythologies[myth_name]

        if not isinstance(texts, dict):
            logger.warning(f"Found invalid texts structure for {myth_name}. Pruning.")
            del mythologies[myth_name]
            continue

        text_keys = list(texts.keys())

        for text_name in text_keys:
            text_data = texts[text_name]

            if not isinstance(text_data, dict):
                logger.warning(f"Found invalid text_data for {text_name}. Pruning.")
                del texts[text_name]
                continue

            properties = text_data.get("properties", [])
            # Zero Clutter Rule: if properties is empty or not a list, prune the text
            if not properties or (isinstance(properties, list) and len(properties) == 0):
                logger.debug(f"Pruning text node '{text_name}' due to empty properties.")
                del texts[text_name]

        # If the mythology now has no texts left, prune the mythology
        if not texts:
            logger.debug(f"Pruning mythology node '{myth_name}' due to empty texts.")
            del mythologies[myth_name]

    # If the master matrix contains no mythologies, return an explicit {}
    if not mythologies:
        logger.info("Pruning resulted in an empty matrix.")
        return {}

    return master_matrix
