import logging
from typing import Dict, List, Any
from core.proxy_client import fetch_via_proxy
from core.sieve_parser import clean_html_payload
from core.critic import chunk_text_sliding_window, evaluate_chunks

logger = logging.getLogger(__name__)

# Thresholds for the Orchestrator's autonomous decision logic
THRESHOLD_A = 3.0  # High confidence, keep chunk
THRESHOLD_B = 0.5  # Junk/Noise, assassinate chunk

def process_url(url_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Processes a single URL through the entire local reasoning pipeline.
    Expects input like: {"url": str, "is_trusted": bool, ...}
    Returns structured output containing mathematically validated chunks.
    """
    url = url_info.get("url", "")
    is_trusted = url_info.get("is_trusted", False)

    if not url:
        return {"url": url, "is_trusted": is_trusted, "validated_chunks": [], "error": "Empty URL"}

    # Step 1: Resilient Data Acquisition
    # Our fetching via proxy handles catching basic requests errors but let's wrap
    # the entire processing logic for the orchestrator loop gracefully.
    try:
        raw_html = fetch_via_proxy(url)
    except Exception as e:
        logger.error(f"Failed to fetch {url}: {e}")
        return {"url": url, "is_trusted": is_trusted, "validated_chunks": [], "error": f"Fetch failed: {str(e)}"}

    if not raw_html:
        return {"url": url, "is_trusted": is_trusted, "validated_chunks": [], "error": "Empty DOM or fetch failed"}

    # Step 2: Clean Payload
    try:
        cleaned_text = clean_html_payload(raw_html)
    except Exception as e:
        logger.error(f"Failed to clean payload for {url}: {e}")
        return {"url": url, "is_trusted": is_trusted, "validated_chunks": [], "error": f"Parse failed: {str(e)}"}

    if not cleaned_text:
         return {"url": url, "is_trusted": is_trusted, "validated_chunks": [], "error": "Parsed text empty"}

    # Step 3: Algorithmic Chunking
    chunks = chunk_text_sliding_window(cleaned_text, window_size=150, overlap=50)

    if not chunks:
        return {"url": url, "is_trusted": is_trusted, "validated_chunks": [], "error": "No chunks generated"}

    # Step 4: Multi-Criteria Reasoning Engine (The Critic)
    evaluated_chunks = evaluate_chunks(chunks)

    validated_chunks = []

    # Step 5: Agentic Optimization (The Decision Logic)
    for evaluation in evaluated_chunks:
        score = evaluation["score"]

        # If score is below Threshold B, it's noise/junk. Assassinate immediately.
        if score < THRESHOLD_B:
            continue

        # If score is above Threshold A, it's high confidence. Keep it.
        # Alternatively, if it's in between, we might keep it but maybe it's less prioritized.
        # We'll just keep everything above THRESHOLD_B since we already assassinate below it.
        # But we could further rank or tag them based on THRESHOLD_A.
        # For now we'll just keep anything that isn't junk, but flag it if it's high confidence.

        # Adjust trust dynamically: If the site is already "trusted" mathematically,
        # we can afford a lower threshold or give a trust boost. Let's keep it pure
        # for now, the scores speak for themselves.

        validated_chunks.append({
            "text": evaluation["text"],
            "score": score,
            "is_high_confidence": score >= THRESHOLD_A
        })

    # Optional: Sort chunks by score descending
    validated_chunks.sort(key=lambda x: x["score"], reverse=True)

    return {
        "url": url,
        "is_trusted": is_trusted,
        "validated_chunks": validated_chunks
    }

def orchestrate_council(url_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Orchestrates the entire council process for a list of URLs.
    Handles exceptions at the individual URL level to prevent total crashes.
    """
    results = []
    for url_info in url_list:
        try:
            result = process_url(url_info)
            results.append(result)
        except Exception as e:
            logger.error(f"Council crash on {url_info.get('url')}: {e}")
            results.append({
                "url": url_info.get("url"),
                "is_trusted": url_info.get("is_trusted"),
                "validated_chunks": [],
                "error": f"Orchestrator crash: {str(e)}"
            })

    return results
