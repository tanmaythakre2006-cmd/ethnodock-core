import logging
import asyncio
import httpx
import hashlib
from typing import Dict, List, Any
from core.proxy_client import fetch_via_proxy
from core.sieve_parser import clean_html_payload
from core.critic import chunk_text_sliding_window, evaluate_chunks

logger = logging.getLogger(__name__)

THRESHOLD_A = 3.0  # High confidence, keep chunk
THRESHOLD_B = 0.5  # Junk/Noise, assassinate chunk

from core.critic import PHARMA_TERMS, HISTORY_TERMS
import re

# DOM-hash deduplicator state
processed_dom_hashes = set()

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
        # Deep-Document & Archival Ghost (The Deep Web)
        if not raw_html or "403 Forbidden" in raw_html or "Captcha" in raw_html:
            cdx_url = f"http://web.archive.org/cdx/search/cdx?url={url}&output=json&limit=1"
            cdx_resp = await client.get(cdx_url, timeout=5.0)
            if cdx_resp.status_code == 200:
                try:
                    import json
                    data = json.loads(cdx_resp.text)
                    if len(data) > 1:
                        timestamp = data[1][1]
                        archive_url = f"http://web.archive.org/web/{timestamp}id_/{url}"
                        raw_html = await fetch_via_proxy(client, archive_url)
                except Exception:
                    pass
    except Exception as e:
        logger.error(f"Failed to fetch {url}: {e}")
        return {"url": url, "is_trusted": is_trusted, "validated_chunks": [], "error": f"Fetch failed: {str(e)}"}

    if url.endswith(".pdf"):
        # PDF Parsing with PyMuPDF
        import fitz
        import tempfile
        import os
        try:
            pdf_resp = await client.get(url, timeout=10.0, follow_redirects=True)
            if pdf_resp.status_code == 200:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(pdf_resp.content)
                    tmp_name = tmp.name
                doc = fitz.open(tmp_name)
                text = ""
                for page in doc:
                    text += page.get_text()
                doc.close()
                os.unlink(tmp_name)
                raw_html = text
        except Exception as e:
            logger.debug(f"PDF Parse failed: {e}")

    if not raw_html:
        return {"url": url, "is_trusted": is_trusted, "validated_chunks": [], "error": "Empty DOM or fetch failed"}

    # DOM-hash deduplicator logic
    dom_hash = hashlib.md5(raw_html.encode('utf-8')).hexdigest()
    if dom_hash in processed_dom_hashes:
        logger.info(f"Duplicate DOM hash skipped for URL: {url}")
        return {"url": url, "is_trusted": is_trusted, "validated_chunks": [], "error": "Duplicate DOM hash skipped"}
    processed_dom_hashes.add(dom_hash)

    try:
        cleaned_text = clean_html_payload(raw_html)

        # Detect and translate Hindi back to English
        if cleaned_text and any('ऀ' <= char <= 'ॿ' for char in cleaned_text[:1000]):
            try:
                from deep_translator import GoogleTranslator
                translator = GoogleTranslator(source='hi', target='en')
                # Translate in chunks to avoid limits
                translated_parts = []
                for i in range(0, len(cleaned_text), 4000):
                    translated_parts.append(translator.translate(cleaned_text[i:i+4000]))
                cleaned_text = " ".join(translated_parts)
            except Exception as e:
                logger.debug(f"Translation failed for {url}: {e}")
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

    # Raised semaphore to 50 for the massive wave of URLs per instruction
    sem = asyncio.Semaphore(50)

    async def bound_process_url(client, url_info):
        async with sem:
            try:
                # Add a timeout specifically for this url processing so it doesn't freeze the gathering entirely
                return await asyncio.wait_for(process_url(client, url_info, herb_name), timeout=25.0)
            except asyncio.TimeoutError:
                return {"url": url_info.get("url"), "is_trusted": url_info.get("is_trusted"), "validated_chunks": [], "error": "Timeout"}
            except Exception as e:
                logger.error(f"Council crash on {url_info.get('url')}: {e}")
                return {
                    "url": url_info.get("url"),
                    "is_trusted": url_info.get("is_trusted"),
                    "validated_chunks": [],
                    "error": f"Orchestrator crash: {str(e)}"
                }

    async with httpx.AsyncClient(http2=True, timeout=15.0, follow_redirects=True) as client:
        tasks = [bound_process_url(client, url_info) for url_info in url_list]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    final_results = [r for r in results if not isinstance(r, Exception)]

    return final_results
