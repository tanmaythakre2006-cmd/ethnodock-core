import requests
import logging

PROXY_URL = "https://cors-proxy-worker.ethnodock-engine.workers.dev"

def fetch_via_proxy(target_url: str) -> str:
    """
    Fetches the content of a target URL via the proxy worker.

    Args:
        target_url (str): The URL to fetch.

    Returns:
        str: The fetched content.
    """
    try:
        response = requests.get(PROXY_URL, params={"url": target_url})
        if response.status_code == 200:
            return response.text
        else:
            logging.error(f"Failed to fetch {target_url}: HTTP {response.status_code}")
            return ""
    except Exception as e:
        logging.error(f"Exception fetching {target_url}: {e}")
        return ""
