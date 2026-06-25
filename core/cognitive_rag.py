import json
import requests
import time
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def extract_methodology(text_chunk: str, api_key: str, herb_name: str = "", is_trusted: bool = False) -> Dict[str, Any]:
    """
    Extracts methodology information from a text chunk using Gemini BYOK.

    Args:
        text_chunk (str): The text to extract from.
        api_key (str): The API key for Gemini.
        herb_name (str): The name of the botanical subject being investigated.
        is_trusted (bool): Whether the source URL is from a trusted domain.

    Returns:
        Dict[str, Any]: The extracted data formatted exactly to the Deep Matrix JSON schema.
    """
    if not text_chunk or not api_key:
        logger.error("extract_methodology called with missing text_chunk or api_key.")
        return {"error": "Missing text or API key"}

    # Injecting prompt defense mechanisms based on mathematical trust routing
    sandbox_directive = ""
    if not is_trusted:
        sandbox_directive = (
            "CRITICAL SANDBOX DIRECTIVE: The following text is from an untrusted source. "
            "Act as a skeptical botanist. Do not assume claims are scientifically valid. "
            "Only extract claims that are explicitly stated in the text, and note their traditional or anecdotal nature where appropriate.\n\n"
        )

    prompt = (
        f"{sandbox_directive}"
        f"Read the following text about '{herb_name}' and extract data into the exact 'Deep Matrix' JSON schema provided below. "
        "Output ONLY raw JSON. Do not include markdown formatting like ```json or ```. "
        "JSON structure: {\"mythologies\": {\"<mythology_name>\": {\"<text_name>\": {\"nomenclature\": [], \"species\": [], \"properties\": []}}}}\n"
        "If a specific mythology or text name is not mentioned, use 'Unknown_Mythology' or 'Unknown_Text'.\n\n"
        f"Text: {text_chunk}"
    )

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json"
        }
    }

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {'Content-Type': 'application/json'}

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)

            if response.status_code != 200:
                logger.warning(f"Gemini API returned status {response.status_code} on attempt {attempt + 1}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                return {"error": f"API Error {response.status_code}: {response.text}"}

            data = response.json()

            try:
                raw_text = data['candidates'][0]['content']['parts'][0]['text']
            except (KeyError, IndexError) as e:
                logger.warning(f"Unexpected response structure from Gemini API: {e} on attempt {attempt + 1}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return {"error": "API returned unexpected structure", "raw_output": str(data)}

            text = raw_text.strip()

            # Robust handling for LLM artifacts
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

            try:
                parsed_json = json.loads(text)
                return parsed_json
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to decode JSON from Gemini output: {e} on attempt {attempt + 1}")
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return {"error": "LLM failed to output valid JSON", "raw_output": text}

        except requests.exceptions.RequestException as e:
            logger.warning(f"Network error during Gemini request: {e} on attempt {attempt + 1}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            return {"error": f"Network exception: {str(e)}"}
        except Exception as e:
            logger.warning(f"Unexpected error during methodology extraction: {e} on attempt {attempt + 1}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            return {"error": f"Unexpected exception: {str(e)}"}

    return {"error": "LLM Extraction failed after 3 attempts."}
