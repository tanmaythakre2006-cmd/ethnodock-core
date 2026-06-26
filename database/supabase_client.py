from core.pruner import merge_matrices, prune_empty_nodes
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


def save_master_matrix(herb_name: str, new_matrix: dict, new_urls: list) -> dict:
    """
    Saves or updates the master matrix data in the Supabase database.

    Args:
        herb_name (str): The name of the herb.
        new_matrix (dict): The extracted master matrix methodology data.
        new_urls (list): A list of URLs the data was extracted from.
    """
    if not new_matrix:
        return {"error": "Cannot save an empty matrix."}

    client = get_supabase_client()
    if client is None:
        return {"error": "Database credentials missing"}

    try:
        normalized_herb_name = herb_name.strip().lower()

        # Query if the herb already exists
        existing_response = client.table('botanical_data').select("*").eq('herb_name', normalized_herb_name).execute()
        existing_data = existing_response.data

        if not existing_data:
            # Insert logic
            payload = {
                "herb_name": normalized_herb_name,
                "master_matrix": new_matrix,
                "source_urls": new_urls
            }
            response = client.table('botanical_data').insert(payload).execute()
            return {"success": True, "action": "inserted", "data": response.data}
        else:
            # Update logic
            row = existing_data[0]
            row_id = row['id']
            existing_matrix = row.get('master_matrix', {})
            existing_urls = row.get('source_urls', [])

            # Combine and deduplicate URLs
            combined_urls = list(set(existing_urls + new_urls))

            # Merge matrices and prune
            merged_matrix = merge_matrices([existing_matrix, new_matrix])
            final_matrix = prune_empty_nodes(merged_matrix)

            payload = {
                "master_matrix": final_matrix,
                "source_urls": combined_urls
            }

            response = client.table('botanical_data').update(payload).eq('id', row_id).execute()
            return {"success": True, "action": "updated", "data": response.data}

    except Exception as e:
        return {"error": str(e)}
