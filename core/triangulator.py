from core.critic import PHARMA_TERMS, HISTORY_TERMS
import re
import logging
from typing import Dict, Any, List
from database.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

class LogicTriangulator:
    """
    Local Logic-Based Triangulator to extract and structure data without AI dependencies.
    """

    def __init__(self, herb_name: str, trusted_only: bool = False):
        self.herb_name = herb_name
        self.trusted_only = trusted_only
        self.db_client = get_supabase_client()
        self.existing_claims = self._fetch_existing_claims()

    def _fetch_existing_claims(self) -> set:
        """
        Fetches existing properties/claims from Supabase to cross-reference new data.
        """
        claims = set()
        if not self.db_client:
            return claims

        try:
            normalized_herb_name = self.herb_name.strip().lower()
            response = self.db_client.table('botanical_data').select("master_matrix").eq('herb_name', normalized_herb_name).execute()
            if response.data and isinstance(response.data, list) and len(response.data) > 0:
                matrix = response.data[0].get('master_matrix', {})
                mythologies = matrix.get('mythologies', {})
                for myth, texts in mythologies.items():
                    for text_name, data in texts.items():
                        props = data.get('properties', [])
                        for prop in props:
                            claims.add(prop.lower())
        except Exception as e:
            logger.warning(f"Triangulator failed to fetch existing claims for cross-referencing: {e}")

        return claims

    def extract_claims(self, text_chunk: str) -> Dict[str, Any]:
        """
        Uses heuristics and regex to extract botanical and pharmacological claims.
        """
        properties_found = set()

        text_lower = text_chunk.lower()

        for term in PHARMA_TERMS:
            if re.search(rf'\b{re.escape(term)}\b', text_lower):
                properties_found.add(term.capitalize())

        # Cross-reference: If we found claims, we can verify them against DB,
        # but also if the text contains a claim already in the DB, we definitely keep it.
        for existing_claim in self.existing_claims:
            if re.search(rf'\b{re.escape(existing_claim)}\b', text_lower):
                properties_found.add(existing_claim.capitalize() + " (Verified by DB)")

        mythology = "Unknown_Mythology"
        text_name = "Extracted_Source"

        from core.critic import BOOK_MYTHOLOGY_MAP
        found_book = False
        for book_name, mapped_mythology in BOOK_MYTHOLOGY_MAP.items():
            if book_name.lower() in text_lower:
                text_name = book_name
                mythology = mapped_mythology
                found_book = True
                break # We found a specific text match, use it.

        if not found_book:
            for term in HISTORY_TERMS:
                if term in text_lower:
                    if term in ["ayurveda", "ayurvedic"]:
                        mythology = "Ayurveda"
                    elif term in ["tcm", "chinese medicine"]:
                        mythology = "TCM"
                    elif term in ["egyptian medicine"]:
                        mythology = "Ancient Egyptian medicine"
                    elif term in ["greek medicine"]:
                        mythology = "Ancient Greek medicine"
                    elif term in ["mesopotamian medicine"]:
                        mythology = "Mesopotamian medicine"
                    elif term in ["persian medicine"]:
                        mythology = "Persian medicine"
                    elif term in ["mesoamerican medicine"]:
                        mythology = "Mesoamerican medicine"
                    elif term in ["arabic medicine", "islamic medicine"]:
                        mythology = "Arabic and Islamic medicine"
                    elif term in ["yoruba traditional medicine", "yoruba medicine"]:
                        mythology = "Yoruba traditional medicine"
                    elif term in ["norse healing"]:
                        mythology = "Norse healing traditions"
                    elif term in ["folk", "traditional"]:
                        mythology = "Traditional/Folk"

        return {
            "mythology": mythology,
            "text_name": text_name,
            "nomenclature": [self.herb_name.title()],
            "species": [],
            "properties": list(properties_found)
        }

    def verify_and_build(self, chunk_data: Dict[str, Any], is_trusted: bool) -> Dict[str, Any]:
        """
        Verifies extracted claims and builds the Deep Matrix schema.
        """
        text = chunk_data.get("text", "")
        if not text:
            return {}

        if self.trusted_only and not is_trusted:
            return {}

        extracted = self.extract_claims(text)

        if not extracted.get("properties") and extracted.get("mythology") == "Unknown_Mythology":
            return {}

        matrix = {
            "mythologies": {
                extracted["mythology"]: {
                    extracted["text_name"]: {
                        "nomenclature": extracted["nomenclature"],
                        "species": extracted["species"],
                        "properties": extracted["properties"]
                    }
                }
            }
        }

        return matrix
