import re
with open("core/council_orchestrator.py", "r") as f:
    code = f.read()

# Remove fake data injection
code = re.sub(
r'''    # GUARANTEED MASTER MATRIX.*?return final_results''',
'''    return final_results''', code, flags=re.DOTALL)

# Add PDF parsing via PyMuPDF (fitz) and CDX fallback for 403s
code = code.replace(
'''    try:
        raw_html = await fetch_via_proxy(client, url)
    except Exception as e:
        logger.error(f"Failed to fetch {url}: {e}")
        return {"url": url, "is_trusted": is_trusted, "validated_chunks": [], "error": f"Fetch failed: {str(e)}"}''',
'''    try:
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
            logger.debug(f"PDF Parse failed: {e}")''')

with open("core/council_orchestrator.py", "w") as f:
    f.write(code)
