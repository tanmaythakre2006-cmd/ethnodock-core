import logging
import asyncio
import httpx
from typing import Dict, List, Any
from core.proxy_client import fetch_via_proxy
from core.sieve_parser import clean_html_payload
from core.critic import chunk_text_sliding_window, evaluate_chunks

logger = logging.getLogger(__name__)

THRESHOLD_A = 3.0  # High confidence, keep chunk
THRESHOLD_B = 0.5  # Junk/Noise, assassinate chunk

from core.critic import PHARMA_TERMS, HISTORY_TERMS
import re

async def process_url(client: httpx.AsyncClient, url_info: Dict[str, Any], herb_name: str = "") -> Dict[str, Any]:
    """
    Processes a single URL asynchronously through the entire local reasoning pipeline.
    """
    url = url_info.get("url", "")
    is_trusted = url_info.get("is_trusted", False)

    if not url:
        return {"url": url, "is_trusted": is_trusted, "validated_chunks": [], "error": "Empty URL"}

    try:
        raw_html = await fetch_via_proxy(client, url)
    except Exception as e:
        logger.error(f"Failed to fetch {url}: {e}")
        return {"url": url, "is_trusted": is_trusted, "validated_chunks": [], "error": f"Fetch failed: {str(e)}"}

    if not raw_html:
        return {"url": url, "is_trusted": is_trusted, "validated_chunks": [], "error": "Empty DOM or fetch failed"}

    try:
        cleaned_text = clean_html_payload(raw_html)
    except Exception as e:
        logger.error(f"Failed to clean payload for {url}: {e}")
        return {"url": url, "is_trusted": is_trusted, "validated_chunks": [], "error": f"Parse failed: {str(e)}"}

    if not cleaned_text:
         return {"url": url, "is_trusted": is_trusted, "validated_chunks": [], "error": "Parsed text empty"}

    chunks = chunk_text_sliding_window(cleaned_text, window_size=150, overlap=50)

    if not chunks:
        return {"url": url, "is_trusted": is_trusted, "validated_chunks": [], "error": "No chunks generated"}

    # Multi-pass data isolation loop
    isolated_chunks = []
    for chunk in chunks:
        chunk_lower = chunk.lower()

        # Pass 1: Context (is the target mentioned?)
        pass_1_cleared = herb_name.lower() in chunk_lower if herb_name else True

        if pass_1_cleared:
            # Pass 2: Phytochemistry (bioactive compounds, alkaloids, etc)
            pass_2_cleared = any(re.search(rf'\b{re.escape(term)}\b', chunk_lower) for term in PHARMA_TERMS)

            # Pass 3: Ethnomedicine & History
            pass_3_cleared = any(re.search(rf'\b{re.escape(term)}\b', chunk_lower) for term in HISTORY_TERMS)

            if pass_2_cleared or pass_3_cleared:
                isolated_chunks.append(chunk)

    if not isolated_chunks:
        isolated_chunks = chunks

    evaluated_chunks = evaluate_chunks(isolated_chunks, herb_name)

    validated_chunks = []

    for evaluation in evaluated_chunks:
        score = evaluation["score"]
        if score < THRESHOLD_B:
            continue

        validated_chunks.append({
            "text": evaluation["text"],
            "score": score,
            "is_high_confidence": score >= THRESHOLD_A
        })

    validated_chunks.sort(key=lambda x: x["score"], reverse=True)

    return {
        "url": url,
        "is_trusted": is_trusted,
        "validated_chunks": validated_chunks
    }

async def orchestrate_council(url_list: List[Dict[str, Any]], herb_name: str = "") -> List[Dict[str, Any]]:
    """
    Orchestrates the entire council process for a list of URLs asynchronously using httpx and asyncio.
    """
    results = []

    # We use a semaphore to avoid overloading the CORS proxy
    sem = asyncio.Semaphore(5)

    async def bound_process_url(client, url_info):
        async with sem:
            try:
                return await process_url(client, url_info, herb_name)
            except Exception as e:
                logger.error(f"Council crash on {url_info.get('url')}: {e}")
                return {
                    "url": url_info.get("url"),
                    "is_trusted": url_info.get("is_trusted"),
                    "validated_chunks": [],
                    "error": f"Orchestrator crash: {str(e)}"
                }

    async with httpx.AsyncClient(http2=True) as client:
        tasks = [bound_process_url(client, url_info) for url_info in url_list]
        results = await asyncio.gather(*tasks)

    return list(results)
