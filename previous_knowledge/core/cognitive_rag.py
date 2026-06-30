import json
import logging
import asyncio
import httpx
from typing import Dict, Any

logger = logging.getLogger(__name__)

class SandboxValidator:
    """
    Validates unverified/conventional sources (Stream B) against the master matrix.
    Uses LLM (Gemini) to evaluate consistency, coherence, and attribution.
    """
    def __init__(self, api_key: str, master_matrix: Dict[str, Any]):
        self.api_key = api_key
        self.master_matrix = master_matrix
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"

    async def validate_and_extract(self, text_chunk: str, herb_name: str) -> Dict[str, Any]:
        if not self.api_key:
            return {"error": "Missing API Key"}

        prompt = (
            f"You are the SandboxValidator for a botanical database.\n"
            f"Target Herb: {herb_name}\n\n"
            f"Here is the verified Master Matrix for this herb. This is established truth:\n"
            f"{json.dumps(self.master_matrix)}\n\n"
            f"Here is an unverified claim from a conventional/experimental source:\n"
            f"{text_chunk}\n\n"
            f"Evaluate this claim based on:\n"
            f"1. Consistency: Does it contradict the Master Matrix? (If it directly opposes verified facts, it fails).\n"
            f"2. Coherence: Is the claim internally logical?\n"
            f"3. Attribution: Does it cite mechanisms or sources?\n\n"
            f"If the claim passes validation, return a JSON object with the exact 'Deep Matrix' schema representing the new experimental insights, labeled under a mythology of 'Experimental/Conventional'. "
            f"The JSON schema must be exactly: {{\"mythologies\": {{\"Experimental/Conventional\": {{\"<source_name>\": {{\"nomenclature\": [], \"species\": [], \"properties\": []}}}}}}}}\n"
            f"If the claim fails validation, return: {{\"error\": \"Failed validation\"}}\n"
            f"Output ONLY raw JSON. No markdown."
        )

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json"
            }
        }

        headers = {'Content-Type': 'application/json'}

        max_retries = 3
        async with httpx.AsyncClient() as client:
            for attempt in range(max_retries):
                try:
                    response = await client.post(self.url, headers=headers, json=payload, timeout=30.0)
                    if response.status_code != 200:
                        logger.warning(f"Gemini API returned {response.status_code} on attempt {attempt+1}")
                        await asyncio.sleep(2 ** attempt)
                        continue

                    data = response.json()
                    raw_text = data['candidates'][0]['content']['parts'][0]['text'].strip()

                    if raw_text.startswith("```json"): raw_text = raw_text[7:]
                    if raw_text.startswith("```"): raw_text = raw_text[3:]
                    if raw_text.endswith("```"): raw_text = raw_text[:-3]

                    try:
                        parsed = json.loads(raw_text.strip())
                        return parsed
                    except json.JSONDecodeError as e:
                        return {"error": "LLM failed to output valid JSON", "raw_output": raw_text}

                except Exception as e:
                    logger.warning(f"Error during validation: {e}")
                    await asyncio.sleep(2 ** attempt)

        return {"error": "LLM extraction failed after retries."}
