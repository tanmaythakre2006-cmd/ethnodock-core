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

async def process_url(client: httpx.AsyncClient, url_info: Dict[str, Any]) -> Dict[str, Any]:
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

    evaluated_chunks = evaluate_chunks(chunks)

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

async def orchestrate_council(url_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Orchestrates the entire council process for a list of URLs asynchronously using httpx and asyncio.
    """
    results = []

    # We use a semaphore to avoid overloading the CORS proxy
    sem = asyncio.Semaphore(5)

    async def bound_process_url(client, url_info):
        async with sem:
            try:
                return await process_url(client, url_info)
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
