"""
Extraction Engine Step 2: Taxonomy Deep-Dive & Paragraph Extraction
Generates mock taxonomy data based on synonyms extracted in Step 1.
Implements an 'Airlock' data flow, writing validated data temporarily to a JSONL file
and ONLY committing to the SQLite database upon 100% completion.
"""

import json
import os
import sqlite3
import sys
from pathlib import Path
from pydantic import BaseModel

# -------------------------------------------------------------------------
# CONSTANTS & PATH CONFIGURATION
# -------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent.parent
STEP_1_DB_PATH = BASE_DIR / "step_1_db.sqlite"
STEP_2_DB_PATH = BASE_DIR / "step_2_db.sqlite"
AIRLOCK_PATH = BASE_DIR / "temp_step_2_airlock.jsonl"


# -------------------------------------------------------------------------
# PYDANTIC MODELS
# -------------------------------------------------------------------------

class TaxonomyData(BaseModel):
    """
    Pydantic schema to validate extracted taxonomy data for Step 2.
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

def run_extraction():
    """
    Executes the Step 2 data extraction using the Airlock flow pattern.
    Reads from Step 1 DB, validates data, writes to JSONL, and commits to SQLite upon completion.
    """
    print("Initiating Extraction Engine Step 2...")

    # 1. Connect to Step 1 Database
    if not STEP_1_DB_PATH.exists():
        print(f"Error: Step 1 database not found at {STEP_1_DB_PATH}")
        sys.exit(1)

    print(f"Reading from Step 1 Database at: {STEP_1_DB_PATH}")
    conn_step_1 = sqlite3.connect(STEP_1_DB_PATH)
    cursor_step_1 = conn_step_1.cursor()

    try:
        cursor_step_1.execute("SELECT id, plant_name, book_name FROM synonyms")
        rows = cursor_step_1.fetchall()
    except sqlite3.Error as e:
        print(f"Error querying Step 1 database: {e}")
        conn_step_1.close()
        sys.exit(1)

    conn_step_1.close()

    if not rows:
        print("Error: Step 1 database is empty.")
        sys.exit(1)

    # 2. Clean previous run state
    if AIRLOCK_PATH.exists():
        os.remove(AIRLOCK_PATH)

    # 3. Process and stream to Airlock JSONL
    print(f"Processing {len(rows)} records and streaming to Airlock: {AIRLOCK_PATH}")
    with open(AIRLOCK_PATH, "a", encoding="utf-8") as airlock_file:
        for row in rows:
            parent_id, plant, book = row

            # Generate mock data
            mock_sub_species = "Common Variant"
            mock_scientific = f"{plant.split()[0]} species"
            mock_context = f"This is a mock context paragraph extracted from {book} describing the medicinal properties of {plant}."

            # Validate mock data via Pydantic model
            validated_data = TaxonomyData(
                parent_synonym_id=parent_id,
                plant_name=plant,
                book_name=book,
                sub_species_discovered=mock_sub_species,
                scientific_name=mock_scientific,
                context_paragraph=mock_context
            )

            # Write safely to JSONL airlock
            airlock_file.write(validated_data.model_dump_json() + "\n")

    print("Extraction 100% complete. All data validated and written to Airlock.")

    # 4. Commit Airlock to SQLite
    print(f"Committing data to Step 2 SQLite Database at: {STEP_2_DB_PATH}")
    conn_step_2 = sqlite3.connect(STEP_2_DB_PATH)
    cursor_step_2 = conn_step_2.cursor()

    cursor_step_2.execute("""
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
    cursor_step_2.execute("DELETE FROM taxonomy")

    print("Flushing Airlock to database...")
    with open(AIRLOCK_PATH, "r", encoding="utf-8") as airlock_file:
        for line in airlock_file:
            row_data = json.loads(line.strip())
            cursor_step_2.execute(
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

    conn_step_2.commit()
    conn_step_2.close()

    # 5. Clean up Airlock
    os.remove(AIRLOCK_PATH)
    print("Airlock successfully flushed. Step 2 Database fully populated.")


if __name__ == "__main__":
    run_extraction()
