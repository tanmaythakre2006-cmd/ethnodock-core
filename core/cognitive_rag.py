import json
import requests

def extract_methodology(text_chunk: str, api_key: str) -> dict:
    """
    Extracts methodology information from a text chunk using Gemini BYOK.

    Args:
        text_chunk (str): The text to extract from.
        api_key (str): The API key for Gemini.

    Returns:
        dict: The extracted methodology data.
    """
    if not text_chunk or not api_key:
        return {"error": "Missing text or API key"}

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
        headers = {'Content-Type': 'application/json'}

        prompt = (
            "Read the following text and extract data into the exact JSON structure provided below. "
            "Output ONLY raw JSON. Do not include markdown formatting like ```json or ```. "
            "JSON structure: {\"plant_name\": \"\", \"scientific_name\": \"\", \"traditional_uses\": [], \"modern_applications\": [], \"active_compounds\": []}\n\n"
            f"Text: {text_chunk}"
        )

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json"
            }
        }

        response = requests.post(url, headers=headers, json=payload)

        if response.status_code != 200:
            return {"error": f"API Error {response.status_code}: {response.text}"}

        data = response.json()

        try:
            raw_text = data['candidates'][0]['content']['parts'][0]['text']
        except KeyError:
            return {"error": "API returned unexpected structure", "raw_output": str(data)}

        text = raw_text.strip()

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
            return {"error": "LLM failed to output valid JSON", "raw_output": text}
    except Exception as e:
        return {"error": str(e)}
