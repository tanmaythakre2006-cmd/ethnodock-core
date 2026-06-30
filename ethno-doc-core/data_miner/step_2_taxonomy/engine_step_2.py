"""
Extraction Engine Step 2: Taxonomy Deep-Dive & Paragraph Extraction
Reads from step_1_db.sqlite, generates mock taxonomy data, validates via Pydantic,
streams to an airlock JSONL file, and finally commits to step_2_db.sqlite.
"""

import json
import os
import sqlite3
import sys
from pathlib import Path
from pydantic import BaseModel

# -------------------------------------------------------------------------
# PATH CONFIGURATION
# -------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent.parent
STEP_1_DB_PATH = BASE_DIR / "step_1_db.sqlite"
STEP_2_DB_PATH = BASE_DIR / "step_2_db.sqlite"
AIRLOCK_PATH = BASE_DIR / "temp_step_2_airlock.jsonl"


# -------------------------------------------------------------------------
# PYDANTIC SCHEMA
# -------------------------------------------------------------------------

class TaxonomyData(BaseModel):
    """
    Pydantic schema to validate extracted taxonomy data.
    """
    parent_synonym_id: int
    plant_name: str
    book_name: str
    sub_species_discovered: str
    scientific_name: str
    context_paragraph: str


# -------------------------------------------------------------------------
# EXTRACTION LOGIC
# -------------------------------------------------------------------------

def generate_mock_taxonomy(row_id: int, plant_name: str, book_name: str, synonym: str) -> dict:
    """
    Generates mock taxonomy data based on a row from Step 1.
    """
    return {
        "parent_synonym_id": row_id,
        "plant_name": plant_name,
        "book_name": book_name,
        "sub_species_discovered": f"{plant_name} Common Variant",
        "scientific_name": f"Mockgenus {plant_name.lower()}ensis",
        "context_paragraph": f"A lengthy text from {book_name} discussing the use of {synonym} (a variant of {plant_name}). It mentions various properties and preparations."
    }

def run_step_2():
    """
    Executes the Step 2 data extraction using the Airlock flow pattern.
    Validates data, writes to JSONL, and commits to SQLite upon completion.
    """
    print("Initiating Extraction Engine Step 2 (Taxonomy)...")

    # 1. Connect to Step 1 DB
    if not STEP_1_DB_PATH.exists():
        print(f"Error: Step 1 database not found at {STEP_1_DB_PATH}. Please run Step 1 first.", file=sys.stderr)
        sys.exit(1)

    try:
        conn_1 = sqlite3.connect(STEP_1_DB_PATH)
        cursor_1 = conn_1.cursor()
        cursor_1.execute("SELECT id, plant_name, book_name, synonym FROM synonyms")
        rows = cursor_1.fetchall()
        conn_1.close()
    except sqlite3.Error as e:
        print(f"Error reading from Step 1 database: {e}", file=sys.stderr)
        sys.exit(1)

    if not rows:
        print("Error: Step 1 database is empty. Please run Step 1 first.", file=sys.stderr)
        sys.exit(1)

    print(f"Successfully read {len(rows)} rows from Step 1 database.")

    # 2. Clean previous run state
    if AIRLOCK_PATH.exists():
        os.remove(AIRLOCK_PATH)

    # 3. Extract and stream to Airlock JSONL
    print(f"Streaming validated data to Airlock: {AIRLOCK_PATH}")
    with open(AIRLOCK_PATH, "a", encoding="utf-8") as airlock_file:
        for row in rows:
            row_id, plant_name, book_name, synonym = row

            # Generate mock taxonomy data
            mock_data = generate_mock_taxonomy(row_id, plant_name, book_name, synonym)

            # Validate mock data via Pydantic model
            validated_data = TaxonomyData(**mock_data)

            # Write safely to JSONL airlock
            airlock_file.write(validated_data.model_dump_json() + "\n")

    print("Step 2 Extraction 100% complete. Airlock populated.")

    # 4. Commit Airlock to SQLite
    print(f"Committing data to Step 2 SQLite Database at: {STEP_2_DB_PATH}")
    conn_2 = sqlite3.connect(STEP_2_DB_PATH)
    cursor_2 = conn_2.cursor()

    cursor_2.execute("""
        CREATE TABLE IF NOT EXISTS taxonomy (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            parent_synonym_id INTEGER NOT NULL,
            plant_name TEXT NOT NULL,
            book_name TEXT NOT NULL,
            sub_species_discovered TEXT NOT NULL,
            scientific_name TEXT NOT NULL,
            context_paragraph TEXT NOT NULL
        )
    """)

    # For idempotency, clear out old data on full commit
    cursor_2.execute("DELETE FROM taxonomy")

    with open(AIRLOCK_PATH, "r", encoding="utf-8") as airlock_file:
        for line in airlock_file:
            row_data = json.loads(line.strip())
            cursor_2.execute(
                """
                INSERT INTO taxonomy
                (parent_synonym_id, plant_name, book_name, sub_species_discovered, scientific_name, context_paragraph)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    row_data["parent_synonym_id"],
                    row_data["plant_name"],
                    row_data["book_name"],
                    row_data["sub_species_discovered"],
                    row_data["scientific_name"],
                    row_data["context_paragraph"]
                )
            )

    conn_2.commit()
    conn_2.close()

    # 5. Clean up Airlock
    os.remove(AIRLOCK_PATH)
    print("Airlock successfully flushed. Step 2 Database fully populated.")


if __name__ == "__main__":
    run_step_2()
