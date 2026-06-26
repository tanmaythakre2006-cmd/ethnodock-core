import logging
from typing import Dict, Any, List

from core.radar import execute_radar
from core.council_orchestrator import orchestrate_council
from core.cognitive_rag import extract_methodology
from core.pruner import merge_matrices, prune_empty_nodes

logger = logging.getLogger(__name__)

def run_autonomous_extraction(herb_name: str, api_key: str, max_urls: int = 5) -> Dict[str, Any]:
    """
    Orchestrates the entire extraction pipeline:
    Radar -> Council Orchestrator (Critic) -> LLM Extraction -> Pruner.

    Args:
        herb_name (str): The name of the botanical subject to investigate.
        api_key (str): The API key for the LLM extraction model (Gemini).
        max_urls (int): The maximum number of URLs to scrape and analyze. Defaults to 5.

    Returns:
        Dict[str, Any]: The pristine, unified Master Matrix containing all extracted data.
    """
    if not herb_name or not api_key:
        logger.error("Missing herb_name or api_key. Aborting extraction.")
        return {}

    logger.info(f"Initiating autonomous extraction for herb: '{herb_name}' (max_urls: {max_urls})")

    # --- Step 1: Execute Radar ---
    logger.info("Executing Radar to locate source materials...")
    try:
        urls = execute_radar(herb_name, max_results=max_urls)
        logger.info(f"Radar successfully found {len(urls)} URLs.")
    except Exception as e:
        logger.error(f"Radar phase failed critically: {e}")
        return {}

    if not urls:
        logger.warning("Radar found no valid URLs. Pipeline terminating early.")
        return {}

    # --- Step 2: Orchestrate Council (Critic Validation) ---
    logger.info("Orchestrating Council to validate text chunks...")
    try:
        council_results = orchestrate_council(urls)
    except Exception as e:
        logger.error(f"Council orchestration failed critically: {e}")
        return {}

    total_validated_chunks = sum(len(result.get("validated_chunks", [])) for result in council_results)
    logger.info(f"Critic validated {total_validated_chunks} chunks across {len(council_results)} URLs.")

    if total_validated_chunks == 0:
        logger.warning("Critic found no mathematically valid chunks. Pipeline terminating early.")
        return {}

    # --- Step 3: LLM Extraction ---
    logger.info("Initiating LLM Extraction on validated chunks...")
    matrices: List[Dict[str, Any]] = []
    extraction_failures = 0

    for result in council_results:
        url = result.get("url", "Unknown URL")
        is_trusted = result.get("is_trusted", False)
        chunks = result.get("validated_chunks", [])

        for chunk_data in chunks:
            chunk_text = chunk_data.get("text")
            if not chunk_text:
                continue

            logger.debug(f"Extracting methodology for chunk from source: {url}")
            try:
                matrix = extract_methodology(chunk_text, api_key, herb_name, is_trusted)

                if matrix and isinstance(matrix, dict) and "error" not in matrix:
                    matrices.append(matrix)
                else:
                    error_msg = matrix.get('error', 'Unknown Error') if isinstance(matrix, dict) else 'Invalid JSON format'
                    logger.warning(f"LLM extraction failure for chunk: {error_msg}")
                    extraction_failures += 1
            except Exception as e:
                logger.error(f"Unhandled exception during LLM extraction: {e}")
                extraction_failures += 1

    logger.info(f"LLM completed extraction. Successes: {len(matrices)}, Failures: {extraction_failures}")

    if not matrices:
        logger.warning("LLM extraction produced no valid matrices. Pipeline terminating early.")
        return {}

    # --- Step 4: Matrix Consolidation and Pruning ---
    logger.info("Initiating Matrix Merger...")
    try:
        master_matrix = merge_matrices(matrices)
        logger.info(f"Successfully merged {len(matrices)} matrices into unified Master Matrix.")
    except Exception as e:
        logger.error(f"Matrix merging failed: {e}")
        return {}

    logger.info("Initiating ruthless Pruner to eliminate empty structural nodes...")
    try:
        pruned_matrix = prune_empty_nodes(master_matrix)
        logger.info("Pruning complete. Returning final Master Matrix.")
    except Exception as e:
        logger.error(f"Matrix pruning failed: {e}")
        return {}

    return pruned_matrix
