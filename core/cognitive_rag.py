import json
import google.generativeai as genai

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
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')

        prompt = (
            "Read the following text and extract data into the exact JSON structure provided below. "
            "Output ONLY raw JSON. Do not include markdown formatting like ```json or ```. "
            "JSON structure: {\"plant_name\": \"\", \"scientific_name\": \"\", \"traditional_uses\": [], \"modern_applications\": [], \"active_compounds\": []}\n\n"
            f"Text: {text_chunk}"
        )

        response = model.generate_content(prompt)
        text = response.text.strip()

        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        return json.loads(text)
    except Exception as e:
        return {"error": str(e)}
