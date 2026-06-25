import json
import time
import requests
import logging

logger = logging.getLogger(__name__)

def extract_methodology(text_chunk: str, api_key: str, herb_name: str, is_trusted: bool) -> dict:
    """
    Extracts methodology information from a text chunk using Gemini BYOK.
    Enforces a strict Deep Matrix JSON schema for structured parsing.

    Args:
        text_chunk (str): The mathematically validated text block to extract from.
        api_key (str): The API key for Gemini.
        herb_name (str): The specific target herb name to search for.
        is_trusted (bool): Whether the source URL originated from a mathematically trusted domain.

    Returns:
        dict: The extracted methodology data matching the Deep Matrix Schema.
    """
    if not text_chunk or not api_key:
        return {"error": "Missing text or API key"}

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}

    sandbox_directive = ""
    if not is_trusted:
        sandbox_directive = (
            "WARNING: This text is sourced from an unverified domain. Act as a skeptical botanist. "
            "You must cross-reference claims in this text against standard botanical science. "
            "Discard any properties that are biologically impossible or highly speculative before adding them to the JSON.\n\n"
        )

    prompt = (
        f"Read the following text and extract data about '{herb_name}' into the exact JSON structure provided below. "
        "Output ONLY raw JSON. Do not include markdown formatting like ```json or ```.\n\n"
        f"{sandbox_directive}"
        "JSON structure: {\n"
        "  \"plant_term\": \"The user's query\",\n"
        "  \"mythologies\": {\n"
        "    \"Mythology/System Name (e.g., Ayurveda, Traditional Chinese Medicine)\": {\n"
        "      \"Text Name (e.g., Atharva Veda)\": {\n"
        "        \"original_nomenclature\": \"The ancient word used in the text\",\n"
        "        \"resolved_species\": \"The exact scientific species mapped by the AI\",\n"
        "        \"properties\": [\n"
        "          {\"claim\": \"Historical use\", \"mechanism\": \"Biological action if mentioned\"}\n"
        "        ]\n"
        "      }\n"
        "    }\n"
        "  }\n"
        "}\n\n"
        f"Text: {text_chunk}"
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json"
        }
    }

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)

            if response.status_code != 200:
                logger.warning(f"API Error {response.status_code}: {response.text}")
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return {"error": f"API Error {response.status_code}: {response.text}"}

            data = response.json()

            try:
                raw_text = data['candidates'][0]['content']['parts'][0]['text']
            except KeyError:
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return {"error": "API returned unexpected structure", "raw_output": str(data)}

            text = raw_text.strip()

            # Clean up markdown formatting if the model still returns it
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

            try:
                return json.loads(text)
            except json.JSONDecodeError:
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                return {"error": "LLM failed to output valid JSON", "raw_output": text}

        except Exception as e:
            logger.warning(f"API Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                return {} # Empty dictionary on complete failure

    return {}
