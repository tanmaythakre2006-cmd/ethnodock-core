import logging
from typing import Dict, Any, List, Tuple

from core.radar import execute_radar
from core.council_orchestrator import orchestrate_council
from core.triangulator import LogicTriangulator
from core.cognitive_rag import SandboxValidator
from core.pruner import merge_matrices, prune_empty_nodes
from database.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

async def run_autonomous_extraction(herb_name: str, api_key: str = "", max_urls: int = 5) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Hybrid Sovereign Pipeline (Dual-Stream).
    Returns (master_matrix, experimental_matrix)
    """
    if not herb_name:
        logger.error("Missing herb_name.")
        return {}, {}

    logger.info(f"Initiating Hybrid Pipeline for: '{herb_name}'")

    master_matrix = {}

    # --- Pre-Flight Check ---
    client = get_supabase_client()
    if client:
        try:
            normalized_herb = herb_name.strip().lower()
            existing_response = client.table('botanical_data').select("*").eq('herb_name', normalized_herb).execute()
            if existing_response.data:
                logger.info("Found existing Master Matrix.")
                master_matrix = existing_response.data[0].get('master_matrix', {})
            if master_matrix:
                return master_matrix, {}
        except Exception as e:
            logger.warning(f"Supabase pre-flight failed: {e}")

    # --- Step 1: Radar ---
    urls = await execute_radar(herb_name, max_results=max_urls)
    if not urls:
        return master_matrix, {}

    # --- Step 2: Orchestrate Council ---
    council_results = await orchestrate_council(urls)

    # --- Step 3: Data Router ---
    stream_a_matrices = []
    stream_b_chunks = []

    triangulator = LogicTriangulator(herb_name)

    for result in council_results:
        url = result.get("url", "Unknown")
        is_trusted = result.get("is_trusted", False)
        chunks = result.get("validated_chunks", [])

        for chunk_data in chunks:
            if is_trusted:
                # Stream A: Sovereign Logic (API-Free)
                matrix = triangulator.verify_and_build(chunk_data, is_trusted)
                if matrix:
                    stream_a_matrices.append(matrix)
            else:
                # Stream B: The Cognitive Sandbox
                stream_b_chunks.append(chunk_data.get("text", ""))

    # Merge Stream A
    if stream_a_matrices:
        new_master = merge_matrices(stream_a_matrices)
        master_matrix = merge_matrices([master_matrix, new_master]) if master_matrix else new_master
        master_matrix = prune_empty_nodes(master_matrix)

    experimental_matrix = {}

    # Process Stream B if API key is provided
    if api_key and stream_b_chunks:
        logger.info(f"Processing {len(stream_b_chunks)} chunks in Stream B Cognitive Sandbox.")
        sandbox = SandboxValidator(api_key, master_matrix)
        experimental_matrices = []

        for chunk_text in stream_b_chunks:
            if not chunk_text: continue
            result = await sandbox.validate_and_extract(chunk_text, herb_name)
            if result and "error" not in result:
                experimental_matrices.append(result)

        if experimental_matrices:
            merged_exp = merge_matrices(experimental_matrices)
            experimental_matrix = prune_empty_nodes(merged_exp)

    return master_matrix, experimental_matrix
