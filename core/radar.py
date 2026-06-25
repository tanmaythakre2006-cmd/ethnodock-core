import re
import time
import logging
from typing import List, Dict, Any
from urllib.parse import urlparse
try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        DDGS = None

logger = logging.getLogger(__name__)

# List of trusted domains and suffixes for the trust router
TRUSTED_DOMAINS = [
    ".edu",
    ".gov",
    "ncbi.nlm.nih.gov",
    "pubmed.ncbi.nlm.nih.gov",
    "wikipedia.org",
    "who.int",
    "nature.com",
    "sciencemag.org",
    "cell.com",
    "thelancet.com",
    "bmj.com",
    "jamanetwork.com",
]

def synthesize_queries(herb_name: str) -> List[str]:
    """
    Synthesize distinct search vectors based on the generic herb name.
    Now utilizes multiple "radars" by appending targeted site filters to maximize trusted data extraction.
    """
    base_queries = [
        f"{herb_name} pharmacological properties medical uses",
        f"{herb_name} traditional medicine history ethnobotany",
        f"{herb_name} clinical trials efficacy safety",
        f"{herb_name} active compounds phytochemicals",
        f"{herb_name} mythological historical sources"
    ]

    targeted_queries = []

    # 1. The General Web Radar
    for q in base_queries[:2]:
        targeted_queries.append(q)

    # 2. The Science/Medical Radar
    targeted_queries.append(f"{herb_name} clinical trials site:ncbi.nlm.nih.gov")
    targeted_queries.append(f"{herb_name} pharmacology site:pubmed.ncbi.nlm.nih.gov")

    # 3. The Encyclopedia Radar
    targeted_queries.append(f"{herb_name} site:wikipedia.org")

    # 4. Institutional Radars
    targeted_queries.append(f"{herb_name} uses side effects site:.edu")
    targeted_queries.append(f"{herb_name} dietary supplement site:.gov")

    return targeted_queries

def determine_trust(url: str) -> bool:
    """
    Evaluate URL trust based on authoritative domains.
    Returns True if the URL is from a highly authoritative scientific/institutional domain.
    """
    try:
        parsed_url = urlparse(url)
        netloc = parsed_url.netloc.lower()

        # Check against trusted domains/suffixes
        for trusted in TRUSTED_DOMAINS:
            if trusted.startswith("."):
                if netloc.endswith(trusted):
                    return True
            else:
                if netloc == trusted or netloc.endswith("." + trusted):
                    return True
        return False
    except Exception:
        return False

def search_with_resilience(query: str, max_results: int) -> List[Dict[str, str]]:
    """
    Execute DuckDuckGo search with robust anti-blocking resilience.
    Uses intelligent backoff on failures.
    """
    if DDGS is None:
        logger.error("duckduckgo-search is not installed.")
        return []

    results = []
    max_retries = 3
    base_sleep = 2

    for attempt in range(max_retries):
        try:
            # We use a short timeout/backoff for resilience
            ddgs = DDGS()
            raw_results = ddgs.text(query, max_results=max_results)
            # DDGS might return a generator or list
            for r in raw_results:
                if 'href' in r:
                    results.append({"url": r['href'], "title": r.get('title', '')})
            break # Success, exit retry loop
        except Exception as e:
            logger.warning(f"Search attempt {attempt + 1} failed for query '{query}': {e}")
            if attempt < max_retries - 1:
                sleep_time = base_sleep * (2 ** attempt) # Exponential backoff
                time.sleep(sleep_time)
            else:
                logger.error(f"Search failed permanently for query '{query}'")

    return results

def execute_radar(herb_name: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Primary function for the Autonomous Radar & Trust Router.
    Output signature strictly returns: [{"url": str, "is_trusted": bool, "query_used": str}]
    """
    queries = synthesize_queries(herb_name)
    all_results = []
    seen_urls = set()

    # Calculate results per query to approximate max_results, ensuring we get at least some from each radar
    results_per_query = max(3, max_results // len(queries))

    for query in queries:
        query_results = search_with_resilience(query, max_results=results_per_query)

        # Avoid rapid consecutive requests which can trigger rate limiting
        time.sleep(2)

        for r in query_results:
            url = r["url"]
            if url not in seen_urls:
                seen_urls.add(url)
                is_trusted = determine_trust(url)
                all_results.append({
                    "url": url,
                    "is_trusted": is_trusted,
                    "query_used": query
                })

    # Sort results: trusted first, to ensure high quality data is prioritized
    # Then by URL length just for a consistent secondary sort
    sorted_results = sorted(all_results, key=lambda x: (not x["is_trusted"], len(x["url"])))

    return sorted_results[:max_results]
