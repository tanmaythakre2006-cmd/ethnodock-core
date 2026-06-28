import httpx
import logging
import json
import re

logger = logging.getLogger(__name__)

async def get_synonyms(herb_name: str) -> list[str]:
    """
    Finds global, cultural, and linguistic synonyms for a generalized herb name using Wikipedia.
    """
    synonyms = [herb_name]
    url = f"https://en.wikipedia.org/w/api.php?action=query&prop=redirects&titles={herb_name}&format=json"

    try:
        from core.proxy_client import fetch_via_proxy
        async with httpx.AsyncClient(http2=True, timeout=10.0, follow_redirects=True) as client:
            # 1. Fetch redirects (e.g. alternate names)
            resp_html = await fetch_via_proxy(client, url)
            if resp_html:
                try:
                    data = json.loads(resp_html)
                    pages = data.get("query", {}).get("pages", {})
                    for page_id, page_info in pages.items():
                        redirects = page_info.get("redirects", [])
                        for rd in redirects:
                            title = rd.get("title")
                            if title and title.lower() not in [s.lower() for s in synonyms] and len(title.split()) <= 3:
                                synonyms.append(title)
                except Exception as e:
                    logger.debug(f"JSON decode failed for Wikipedia redirects: {e}")

            # 2. Try to extract bolded alternative names from the summary extract
            extract_url = f"https://en.wikipedia.org/w/api.php?action=query&prop=extracts&exintro=true&titles={herb_name}&format=json"
            extract_html = await fetch_via_proxy(client, extract_url)
            if extract_html:
                try:
                    extract_data = json.loads(extract_html)
                    ext_pages = extract_data.get("query", {}).get("pages", {})
                    for page_id, page_info in ext_pages.items():
                        extract = page_info.get("extract", "")
                        bolds = re.findall(r'<b>(.*?)</b>', extract)
                        for b in bolds:
                            clean_b = re.sub(r'<[^>]+>', '', b).strip()
                            if clean_b and clean_b.lower() not in [s.lower() for s in synonyms] and len(clean_b.split()) <= 4:
                                synonyms.append(clean_b)
                except Exception as e:
                    logger.debug(f"JSON decode failed for Wikipedia extract: {e}")

    except Exception as e:
        logger.warning(f"Synonym extraction failed for {herb_name}: {e}")

    return list(set(synonyms))[:8] # Cap at 8 synonyms to avoid explosion
