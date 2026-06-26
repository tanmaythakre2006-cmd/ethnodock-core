import re
import asyncio
import logging
import random
from typing import List, Dict, Any
from urllib.parse import urlparse, urlunparse

from ddgs import DDGS

logger = logging.getLogger(__name__)

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

def synthesize_tier1_queries(herb_name: str) -> List[str]:
    return [
        f"{herb_name} clinical trials site:ncbi.nlm.nih.gov",
        f"{herb_name} pharmacology site:pubmed.ncbi.nlm.nih.gov",
        f"{herb_name} site:wikipedia.org",
        f"{herb_name} uses side effects site:.edu",
        f"{herb_name} dietary supplement site:.gov"
    ]

def synthesize_tier2_queries(herb_name: str) -> List[str]:
    return [
        f"{herb_name} pharmacological properties medical uses",
        f"{herb_name} traditional medicine history ethnobotany",
        f"{herb_name} active compounds phytochemicals",
        f"{herb_name} traditional uses ethnomedicine"
    ]

def synthesize_tier3_queries(herb_name: str) -> List[str]:
    return [
        f"{herb_name} botanical taxonomy filetype:pdf",
        f"{herb_name} chemical constituents filetype:pdf",
        f"{herb_name} mechanism of action filetype:pdf"
    ]

def normalize_url(url: str) -> str:
    try:
        parsed = urlparse(url)
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, '', '', ''))
    except Exception:
        return url

def determine_trust(url: str) -> bool:
    try:
        parsed_url = urlparse(url)
        netloc = parsed_url.netloc.lower()
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

# Since DuckDuckGo rate-limits aggressively and AsyncDDGS is removed in v6+,
# we run the synchronous DDGS client in a background thread to maintain an async facade,
# while using a lock to serialize requests and add organic jitter.

async def search_with_resilience(query: str, max_results: int, lock: asyncio.Lock) -> List[Dict[str, str]]:
    results = []
    max_retries = 3

    async def _do_search():
        with DDGS() as ddgs:
            return ddgs.text(query, max_results=max_results)

    async with lock:
        for attempt in range(max_retries):
            try:
                # Run the blocking call in a thread pool so we don't freeze the async event loop
                raw_results = await asyncio.to_thread(lambda: list(DDGS().text(query, max_results=max_results)))
                for r in raw_results:
                    if 'href' in r:
                        results.append({"url": r['href'], "title": r.get('title', '')})
                break
            except Exception as e:
                logger.warning(f"Search attempt {attempt + 1} failed for query '{query}': {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(random.uniform(2.1, 4.7) * (attempt + 1))

        # Jitter after a successful query (or failed) before releasing lock
        await asyncio.sleep(random.uniform(1.5, 3.5))

    return results

async def execute_radar(herb_name: str, max_results: int = 10) -> List[Dict[str, Any]]:
    all_results = []
    seen_urls = set()
    search_lock = asyncio.Lock()

    tier1_queries = synthesize_tier1_queries(herb_name)
    tier2_queries = synthesize_tier2_queries(herb_name)
    tier3_queries = synthesize_tier3_queries(herb_name)

    async def run_tier(queries):
        tasks = [search_with_resilience(query, max_results=3, lock=search_lock) for query in queries]
        gathered = await asyncio.gather(*tasks)

        tier_results = []
        for i, query_results in enumerate(gathered):
            for r in query_results:
                norm_url = normalize_url(r["url"])
                if norm_url not in seen_urls:
                    seen_urls.add(norm_url)
                    tier_results.append({
                        "url": norm_url,
                        "is_trusted": determine_trust(norm_url),
                        "query_used": queries[i]
                    })
        return tier_results

    logger.info("Running Tier 1 Scraper (Institutional)...")
    tier1_results = await run_tier(tier1_queries)
    all_results.extend(tier1_results)

    if len(all_results) >= max_results:
        logger.info("Tier 1 yielded sufficient results.")
        return sorted(all_results, key=lambda x: (not x["is_trusted"], len(x["url"])))[:max_results]

    logger.info(f"Tier 1 yielded only {len(all_results)} urls. Cascading to Tier 2 (General Web)...")
    tier2_results = await run_tier(tier2_queries)
    all_results.extend(tier2_results)

    if len(all_results) >= max_results:
        logger.info("Tier 2 yielded sufficient results.")
        return sorted(all_results, key=lambda x: (not x["is_trusted"], len(x["url"])))[:max_results]

    logger.info(f"Tier 2 yielded only {len(all_results)} urls. Cascading to Tier 3 (Scientific PDFs)...")
    tier3_results = await run_tier(tier3_queries)
    all_results.extend(tier3_results)

    sorted_results = sorted(all_results, key=lambda x: (not x["is_trusted"], len(x["url"])))
    return sorted_results[:max_results]
