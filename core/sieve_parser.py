from bs4 import BeautifulSoup

def clean_html_payload(raw_html: str) -> str:
    """
    Cleans raw HTML payload, stripping out unnecessary tags and content.

    Args:
        raw_html (str): The raw HTML content.

    Returns:
        str: The cleaned HTML content.
    """
    if not raw_html:
        return ""

    soup = BeautifulSoup(raw_html, "html.parser")
    for tag in soup(["script", "style", "nav"]):
        tag.decompose()

    return soup.get_text(separator="\n", strip=True)
