import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

def get_supabase_client() -> Client:
    """
    Initializes and returns the Supabase database client.

    Returns:
        The Supabase client instance, or None if credentials are missing.
    """
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        return None
    return create_client(url, key)

def save_extraction(extracted_data: dict, source_url: str) -> dict:
    """
    Saves the extracted data to the Supabase database.

    Args:
        extracted_data (dict): The extracted methodology data.
        source_url (str): The URL the data was extracted from.
    """
    client = get_supabase_client()
    if client is None:
        return {"error": "Database credentials missing"}

    payload = {
        "plant_name": extracted_data.get("plant_name"),
        "scientific_name": extracted_data.get("scientific_name"),
        "traditional_uses": extracted_data.get("traditional_uses"),
        "modern_applications": extracted_data.get("modern_applications"),
        "active_compounds": extracted_data.get("active_compounds"),
        "source_url": source_url
    }

    try:
        response = client.table('botanical_data').insert(payload).execute()
        return {"success": True, "data": response.data}
    except Exception as e:
        return {"error": str(e)}
