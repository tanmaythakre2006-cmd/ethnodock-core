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
    synonym = synonym.strip()
    if not synonym:
        return False

    synonym_lower = synonym.lower()

    # DROP any string containing numbers
    if re.search(r'\d', synonym):
        return False

    # DROP any string containing all-caps alphanumeric codes/words that look like codes
    # Check if string has any uppercase word with numbers (already caught by \d)
    # Check if entirely uppercase and looks like a code (e.g. CAPA)
    # Just checking for all uppercase words without spaces might be too aggressive for acronyms,
    # but the \d check handles "CAPA23". Let's also block words that are pure caps and > 3 letters
    # unless it's a known valid acronym (but herbs rarely are).
    # We will just rely on \d for codes and specific banned words.

    # Banned words
    banned_words = [
        'powder', 'rice', 'extract', 'juice', 'pill', 'capsule', 'drink', 'recipe',
        'plant', 'common', 'medicinal', 'brand', 'product', 'fruit', 'leaf', 'root',
        'seed', 'oil', 'tea', 'supplement', 'chikara'
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

    except Exception as e:
        logger.warning(f"Synonym extraction failed for {herb_name}: {e}")

    # Deduplicate and filter
    filtered_synonyms = []
    seen = set()
    for s in synonyms:
        s_lower = s.lower()
        if s_lower not in seen and _is_valid_synonym(s):
            filtered_synonyms.append(s)
            seen.add(s_lower)

    return filtered_synonyms[:8] # Cap at 8 synonyms to avoid explosion
