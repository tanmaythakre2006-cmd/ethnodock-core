import httpx
import logging
import json
import xml.etree.ElementTree as ET
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

async def fetch_direct_data(synonyms: List[str], herb_name: str) -> List[Dict[str, Any]]:
    results = []

    # --- Wikipedia Direct ---
    async def fetch_wiki(synonym):
        clean_syn = synonym.replace(" ", "_")
        url = f"https://en.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext=true&titles={clean_syn}&format=json"
        try:
            from core.proxy_client import fetch_via_proxy
            async with httpx.AsyncClient(http2=True, timeout=15.0, follow_redirects=True) as client:
                try:
                    resp = await client.get(url)
                    html = resp.text
                except:
                    html = await fetch_via_proxy(client, url)
                if not html: return None
                data = json.loads(html)
                pages = data.get("query", {}).get("pages", {})
                for page_id, page_info in pages.items():
                    extract = page_info.get("extract", "")
                    if extract:
                        import re
                        clean_text = re.sub(r'<[^>]+>', '', extract)
                        from core.critic import chunk_text_sliding_window, evaluate_chunks
                        chunks = chunk_text_sliding_window(clean_text, window_size=150, overlap=50)
                        if not chunks: continue
                        evaluated = evaluate_chunks(chunks, herb_name)
                        validated = [
                            {"text": ev["text"], "score": ev["score"], "is_high_confidence": ev["score"] >= 3.0}
                            for ev in evaluated if ev["score"] >= 0.5
                        ]
                        validated.sort(key=lambda x: x["score"], reverse=True)
                        if validated:
                            return {
                                "url": f"https://en.wikipedia.org/wiki/{clean_syn}",
                                "is_trusted": True,
                                "validated_chunks": validated
                            }
        except Exception:
            pass
        return {"url": f"https://en.wikipedia.org/wiki/{clean_syn}", "is_trusted": True, "validated_chunks": []}

    # --- PubMed Direct ---
    async def fetch_pubmed(synonym):
        clean_syn = synonym.replace(" ", "+")
        search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={clean_syn}[Title/Abstract]&retmode=json&retmax=15"
        try:
            from core.proxy_client import fetch_via_proxy
            async with httpx.AsyncClient(http2=True, timeout=15.0, follow_redirects=True) as client:
                try:
                    resp = await client.get(search_url)
                    search_html = resp.text
                except:
                    search_html = await fetch_via_proxy(client, search_url)
                if not search_html: return None
                data = json.loads(search_html)
                ids = data.get("esearchresult", {}).get("idlist", [])
                if not ids: return None

                fetch_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id={','.join(ids)}&retmode=xml"
                try:
                    resp2 = await client.get(fetch_url)
                    xml_text = resp2.text
                except:
                    xml_text = await fetch_via_proxy(client, fetch_url)
                if not xml_text: return None

                root = ET.fromstring(xml_text)
                abstracts = []
                for abstract_node in root.findall(".//AbstractText"):
                    if abstract_node.text:
                        abstracts.append(abstract_node.text)

                if abstracts:
                    full_text = " ".join(abstracts)
                    from core.critic import chunk_text_sliding_window, evaluate_chunks
                    chunks = chunk_text_sliding_window(full_text, window_size=150, overlap=50)
                    evaluated = evaluate_chunks(chunks, herb_name)
                    validated = [
                        {"text": ev["text"], "score": ev["score"], "is_high_confidence": ev["score"] >= 3.0}
                        for ev in evaluated if ev["score"] >= 0.5
                    ]
                    validated.sort(key=lambda x: x["score"], reverse=True)
                    if validated:
                        return {
                            "url": f"https://pubmed.ncbi.nlm.nih.gov/{ids[0]}/",
                            "is_trusted": True,
                            "validated_chunks": validated
                        }
        except Exception:
            pass
        return {"url": f"https://pubmed.ncbi.nlm.nih.gov/?term={clean_syn}", "is_trusted": True, "validated_chunks": []}

    import asyncio
    wiki_tasks = [fetch_wiki(syn) for syn in synonyms]
    pubmed_tasks = [fetch_pubmed(syn) for syn in synonyms]

    all_res = await asyncio.gather(*(wiki_tasks + pubmed_tasks), return_exceptions=True)
    for res in all_res:
        if res and not isinstance(res, Exception):
            results.append(res)

    return results
