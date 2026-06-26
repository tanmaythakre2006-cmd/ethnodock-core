import httpx
import logging

logger = logging.getLogger(__name__)

PROXY_URL = "https://cors-proxy-worker.ethnodock-engine.workers.dev"

async def fetch_via_proxy(client: httpx.AsyncClient, target_url: str) -> str:
    """
    Fetches the content of a target URL via the proxy worker asynchronously.
    """
    try:
        response = await client.get(PROXY_URL, params={"url": target_url}, timeout=15.0)
        if response.status_code == 200:
            return response.text
        else:
            logger.error(f"Failed to fetch {target_url}: HTTP {response.status_code}")
            return ""
    except Exception as e:
        logger.error(f"Exception fetching {target_url}: {e}")
        return ""
