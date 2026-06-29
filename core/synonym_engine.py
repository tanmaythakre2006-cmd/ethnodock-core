import httpx
import logging
import json
import re

logger = logging.getLogger(__name__)

def _is_valid_synonym(synonym: str) -> bool:
    if not synonym:
        return False

    synonym = synonym.strip().title()

    if re.search(r'\d', synonym):
        return False

    if '×' in synonym or re.search(r'\b[xX]\b', synonym):
        return False

    synonym_lower = synonym.lower()

    banned_words = [
        'powder', 'rice', 'extract', 'juice', 'pill', 'capsule', 'drink', 'recipe',
        'plant', 'common', 'medicinal', 'brand', 'product', 'fruit', 'leaf', 'root',
        'seed', 'oil', 'tea', 'supplement', 'chikara', 'green', 'red',
        'peel', 'rind', 'core', 'bark', 'chai', 'latte', 'company', 'corp', 'inc', 'incorporated',
        'emperor', 'great', 'maurya', 'dream', 'band', 'music', 'film', 'movie', 'song',
        'wood', 'stem', 'mangal', 'branch', 'flower', 'petal'
    ]

    banned_chars = ['皮', '子', '仁', '根', '叶', '壳', '霜', '果', '肉', '核', '枝', '茎', '粉', '膏', '汁', '提取物', '花', '木']

    # Devanagari blocklist
    banned_devanagari = ['बीज', 'छिलका', 'जड़', 'फूल', 'छाल']

    for word in banned_words:
        if re.search(rf'\b{re.escape(word)}\b', synonym_lower):
            return False

    for char in banned_chars:
        if char in synonym_lower:
            return False

    for word in banned_devanagari:
        if word in synonym_lower:
            return False

    return True


import os
import httpx

async def refine_with_ai(synonyms: list[str]) -> list[str]:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return synonyms

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"

    prompt = (
        "You are a botanical semantic filter. You are given a raw list of plant synonyms. "
        "Deduplicate the list at a high linguistic level, map obscure regional dialects to language families "
        "and scrub complex semantic noise that rigid regex missed (like completely unrelated brands, figures, or products). "
        "Return ONLY a raw JSON array of strings. No markdown formatting, no explanation."
        f"\n\nInput: {json.dumps(synonyms)}"
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.0}
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                text = text.replace("```json", "").replace("```", "").strip()
                refined = json.loads(text)
                if isinstance(refined, list):
                    return refined
    except Exception as e:
        logger.error(f"Gemini API failure in synonym refinement: {e}")

    return synonyms


async def get_synonyms(herb_name: str) -> list[str]:
    """
    Finds global, cultural, and linguistic synonyms for a generalized herb name using Wikidata.
    This ensures we pull structured taxonomic and alias data rather than lazy redirects.
    """
    synonyms = [herb_name.strip().title()]

    import urllib.parse
    encoded_herb = urllib.parse.quote(herb_name)

    try:
        from core.proxy_client import fetch_via_proxy
        async with httpx.AsyncClient(http2=True, timeout=10.0, follow_redirects=True) as client:
            # 1. Option A: Wikidata Search
            search_url = f"https://www.wikidata.org/w/api.php?action=wbsearchentities&search={encoded_herb}&language=en&format=json"
            resp_html = await fetch_via_proxy(client, search_url)

            entity_id = None
            resolved_title = None

            if resp_html:
                try:
                    data = json.loads(resp_html)
                    for item in data.get("search", []):
                        q_id = item["id"]
                        # Check P31 (instance of)
                        ent_url = f"https://www.wikidata.org/w/api.php?action=wbgetentities&ids={q_id}&languages=en&props=claims&format=json"
                        ent_resp = await fetch_via_proxy(client, ent_url)
                        if ent_resp:
                            try:
                                ent_data = json.loads(ent_resp)
                                claims = ent_data.get("entities", {}).get(q_id, {}).get("claims", {})
                                p31s = []
                                if "P31" in claims:
                                    for c in claims["P31"]:
                                        val = c.get("mainsnak", {}).get("datavalue", {}).get("value", {}).get("id")
                                        if val: p31s.append(val)

                                # Strict Ontological Filtering:
                                # Accept instances of Taxon (Q16521), Plant (Q756), or Food (Q28128).
                                # HARD REJECTION for Human (Q5), Musical Group (Q215380), Business/Enterprise (Q4830453), or Media/Film (e.g., Q11424, Q83900).
                                hard_rejections = {"Q5", "Q215380", "Q4830453", "Q11424", "Q83900", "Q2431196"}
                                accepted_classes = {"Q16521", "Q756", "Q28128"}

                                if any(p in hard_rejections for p in p31s):
                                    continue

                                if not any(p in accepted_classes for p in p31s):
                                    continue

                                entity_id = q_id
                                resolved_title = item.get("label")
                                break
                            except json.JSONDecodeError:
                                pass
                except json.JSONDecodeError as e:
                    logger.debug(f"JSON decode failed for Wikidata search: {e}")

            # 2. Option B: Wikipedia Search Fallback
            if not entity_id:
                wiki_search_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={encoded_herb}&utf8=&format=json"
                wiki_resp_html = await fetch_via_proxy(client, wiki_search_url)
                if wiki_resp_html:
                    try:
                        wiki_data = json.loads(wiki_resp_html)
                        for search_item in wiki_data.get("query", {}).get("search", []):
                            top_title = search_item["title"]
                            resolved_title = top_title

                            # Get Wikidata ID for this Wikipedia title
                            ent_url = f"https://www.wikidata.org/w/api.php?action=wbgetentities&sites=enwiki&titles={urllib.parse.quote(top_title)}&languages=en&props=claims&format=json"
                            ent_html = await fetch_via_proxy(client, ent_url)
                            if ent_html:
                                ent_d = json.loads(ent_html)
                                entities = ent_d.get("entities", {})
                                keys = list(entities.keys())
                                if keys and keys[0] != "-1":
                                    cand_q_id = keys[0]
                                    claims = entities.get(cand_q_id, {}).get("claims", {})
                                    p31s = []
                                    if "P31" in claims:
                                        for c in claims["P31"]:
                                            val = c.get("mainsnak", {}).get("datavalue", {}).get("value", {}).get("id")
                                            if val: p31s.append(val)

                                    hard_rejections = {"Q5", "Q215380", "Q4830453", "Q11424", "Q83900", "Q2431196"}
                                    accepted_classes = {"Q16521", "Q756", "Q28128"}

                                    if any(p in hard_rejections for p in p31s):
                                        continue
                                    if not any(p in accepted_classes for p in p31s):
                                        continue

                                    entity_id = cand_q_id
                                    break
                    except json.JSONDecodeError as e:
                        logger.debug(f"JSON decode failed for Wikipedia search fallback: {e}")

            en_wiki_title = None
            if not entity_id:
                # Still no entity found, just return original input
                # Limit return array logic is removed later, but we need to do it correctly
                pass
            else:
                if resolved_title:
                    synonyms.append(resolved_title.strip().title())

                # Fetch entity claims
                entity_url = f"https://www.wikidata.org/w/api.php?action=wbgetentities&ids={entity_id}&languages=en&format=json"
                ent_resp_html = await fetch_via_proxy(client, entity_url)

                if ent_resp_html:
                    try:
                        ent_data = json.loads(ent_resp_html)
                        entity = ent_data.get("entities", {}).get(entity_id, {})
                    except json.JSONDecodeError as e:
                        logger.debug(f"JSON decode failed for Wikidata getentities: {e}")
                        entity = {}
                else:
                    entity = {}

                claims = entity.get("claims", {})

                # 1. Aliases
                aliases = entity.get("aliases", {}).get("en", [])
                for a in aliases:
                    val = a.get("value")
                    if val and len(val.split()) <= 4:
                        synonyms.append(val)

                # 2. P225 (Taxon Name)
                if "P225" in claims:
                    for c in claims["P225"]:
                        val = c.get("mainsnak", {}).get("datavalue", {}).get("value")
                        if val and len(val.split()) <= 4:
                            synonyms.append(val)

                # 3. P1843 (Taxon Common Name)
                if "P1843" in claims:
                    for c in claims["P1843"]:
                        val = c.get("mainsnak", {}).get("datavalue", {}).get("value", {}).get("text")
                        if val and len(val.split()) <= 4:
                            synonyms.append(val)

                # 4. Wikipedia Interlanguage Links
                en_wiki_title = entity.get("sitelinks", {}).get("enwiki", {}).get("title")

            try:
                # Use Wikidata's entity to get the English Wikipedia title if available
                wiki_title = en_wiki_title if en_wiki_title else herb_name

                wiki_url = f"https://en.wikipedia.org/w/api.php?action=query&titles={wiki_title}&prop=langlinks&redirects=1&lllimit=500&format=json"
                wiki_resp_html = await fetch_via_proxy(client, wiki_url)

                if wiki_resp_html:
                    wiki_data = json.loads(wiki_resp_html)
                    pages = wiki_data.get("query", {}).get("pages", {})
                    for page_id, page_info in pages.items():
                        langlinks = page_info.get("langlinks", [])
                        for langlink in langlinks:
                            lang = langlink.get("lang")
                            # We want hi, sa, zh
                            if lang in ["hi", "sa", "zh"]:
                                val = langlink.get("*")
                                if val:
                                    synonyms.append(val)
            except Exception as e:
                logger.warning(f"Wikipedia langlinks extraction failed for {herb_name}: {e}")

    except Exception as e:
        logger.warning(f"Synonym extraction failed for {herb_name}: {e}")

    # Deduplicate and filter
    filtered_synonyms = []
    seen = set()
    for s in synonyms:
        if not s:
            continue
        # Clean FIRST before validation and deduplication
        s_cleaned = s.strip().title()
        if _is_valid_synonym(s_cleaned):
            s_lower = s_cleaned.lower()
            if s_lower not in seen:
                filtered_synonyms.append(s_cleaned)
                seen.add(s_lower)

    refined = await refine_with_ai(list(filtered_synonyms))
    return refined
