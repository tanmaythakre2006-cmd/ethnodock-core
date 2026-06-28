import httpx
import logging
import json
import re

logger = logging.getLogger(__name__)

def _is_valid_synonym(synonym: str) -> bool:
    """
    Implements a strict exclusion filter to drop nonsense, commercial products,
    recipes, physical states, and codes.
    """
    if not synonym:
        return False

    synonym = synonym.strip().title()

    # DROP any string containing numbers
    if re.search(r'\d', synonym):
        return False

    synonym_lower = synonym.lower()

    # Banned words
    banned_words = [
        'powder', 'rice', 'extract', 'juice', 'pill', 'capsule', 'drink', 'recipe',
        'plant', 'common', 'medicinal', 'brand', 'product', 'fruit', 'leaf', 'root',
        'seed', 'oil', 'tea', 'supplement', 'chikara', 'green', 'red'
    ]

    for word in banned_words:
        if re.search(rf'\b{word}\b', synonym_lower):
            return False

    return True

async def get_synonyms(herb_name: str) -> list[str]:
    """
    Finds global, cultural, and linguistic synonyms for a generalized herb name using Wikidata.
    This ensures we pull structured taxonomic and alias data rather than lazy redirects.
    """
    synonyms = [herb_name]

    # Use Wikidata wbsearchentities
    search_url = f"https://www.wikidata.org/w/api.php?action=wbsearchentities&search={herb_name}&language=en&format=json"

    try:
        from core.proxy_client import fetch_via_proxy
        async with httpx.AsyncClient(http2=True, timeout=10.0, follow_redirects=True) as client:
            resp_html = await fetch_via_proxy(client, search_url)
            if not resp_html:
                return list(set([s for s in synonyms if _is_valid_synonym(s)]))[:8]

            try:
                data = json.loads(resp_html)
            except json.JSONDecodeError as e:
                logger.debug(f"JSON decode failed for Wikidata search: {e}")
                return list(set([s for s in synonyms if _is_valid_synonym(s)]))[:8]

            if not data.get("search"):
                return list(set([s for s in synonyms if _is_valid_synonym(s)]))[:8]

            entity_id = data["search"][0]["id"]

            # Fetch entity claims
            entity_url = f"https://www.wikidata.org/w/api.php?action=wbgetentities&ids={entity_id}&languages=en&format=json"
            ent_resp_html = await fetch_via_proxy(client, entity_url)
            if not ent_resp_html:
                return list(set([s for s in synonyms if _is_valid_synonym(s)]))[:8]

            try:
                ent_data = json.loads(ent_resp_html)
            except json.JSONDecodeError as e:
                logger.debug(f"JSON decode failed for Wikidata getentities: {e}")
                return list(set([s for s in synonyms if _is_valid_synonym(s)]))[:8]

            entity = ent_data.get("entities", {}).get(entity_id, {})
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
            try:
                # Use Wikidata's entity to get the English Wikipedia title
                en_wiki_title = entity.get("sitelinks", {}).get("enwiki", {}).get("title")

                # If no enwiki sitelink, fallback to searching the herb_name directly
                wiki_title = en_wiki_title if en_wiki_title else herb_name

                wiki_url = f"https://en.wikipedia.org/w/api.php?action=query&titles={wiki_title}&prop=langlinks&lllimit=500&format=json"
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
        if _is_valid_synonym(s):
            s_cleaned = s.strip().title()
            s_lower = s_cleaned.lower()
            if s_lower not in seen:
                filtered_synonyms.append(s_cleaned)
                seen.add(s_lower)

    return list(filtered_synonyms)[:8] # Cap at 8 synonyms to avoid explosion
