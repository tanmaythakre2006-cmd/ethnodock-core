"""
Extraction Engine Step 1: Synonym Extraction
Populates the Step 1 Dictionary by extracting generic TCM plant synonyms.
Implements an 'Airlock' data flow, writing validated data temporarily to a JSONL file
and ONLY committing to the SQLite database upon 100% completion.
"""

import json
import os
import sqlite3
from pathlib import Path
from pydantic import BaseModel

# -------------------------------------------------------------------------
# CONSTANTS
# -------------------------------------------------------------------------

GENERIC_PLANTS = [
    "Ginseng", "Licorice", "Ginger", "Cinnamon", "Peony",
    "Angelica", "Mugwort", "Lotus", "Jujube (Chinese date)", "Ephedra"
]

TCM_BOOKS = [
    "Huangdi Neijing", "Shennong Bencao Jing", "Shanghan Lun",
    "Jingui Yaolue", "Bencao Gangmu", "Zhenjiu Jiayi Jing",
    "Xinxiu Bencao", "Bencao Tujing", "Nan Jing", "Wenbing Tiaobian"
]

# Database and Airlock locations
# Placing them at the root of the ethno-doc-core repository.
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DB_PATH = BASE_DIR / "step_1_db.sqlite"
AIRLOCK_PATH = BASE_DIR / "temp_step_1_airlock.jsonl"


# -------------------------------------------------------------------------
# PYDANTIC MODELS
# -------------------------------------------------------------------------

class SynonymData(BaseModel):
    """
    Pydantic schema to validate extracted synonym data.
    """
    plant_name: str
    book_name: str
    synonym: str


# -------------------------------------------------------------------------
# EXTRACTION LOGIC
# -------------------------------------------------------------------------

def extract_mock_synonyms(plant: str, book: str) -> str:
    """
    Generates a mock generic synonym for a given plant and book.
    (API calls will be implemented here in the future).
    """
    return f"{plant} alias found in {book}"


def run_extraction():
    """
    Executes the Step 1 data extraction using the Airlock flow pattern.
    Validates data, writes to JSONL, and commits to SQLite upon completion.
    """
    # 1. Clean previous run state
    if AIRLOCK_PATH.exists():
        os.remove(AIRLOCK_PATH)

    print("Initiating Extraction Engine Step 1...")

    # 2. Extract and stream to Airlock JSONL
    with open(AIRLOCK_PATH, "a", encoding="utf-8") as airlock_file:
        for plant in GENERIC_PLANTS:
            for book in TCM_BOOKS:
                # Generate mock extraction data
                mock_synonym = extract_mock_synonyms(plant, book)

                # Validate mock data via Pydantic model
                validated_data = SynonymData(
                    plant_name=plant,
                    book_name=book,
                    synonym=mock_synonym
                )

                # Write safely to JSONL airlock
                airlock_file.write(validated_data.model_dump_json() + "\n")

    print(f"Extraction 100% complete. Validated data written to Airlock: {AIRLOCK_PATH}")

    # 3. Commit Airlock to SQLite
    print(f"Committing data to SQLite Database at: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS synonyms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plant_name TEXT NOT NULL,
            book_name TEXT NOT NULL,
            synonym TEXT NOT NULL
        )
    """)

    # For idempotency, clear out old data on full commit
    cursor.execute("DELETE FROM synonyms")

    with open(AIRLOCK_PATH, "r", encoding="utf-8") as airlock_file:
        for line in airlock_file:
            row_data = json.loads(line.strip())
            cursor.execute(
                "INSERT INTO synonyms (plant_name, book_name, synonym) VALUES (?, ?, ?)",
                (row_data["plant_name"], row_data["book_name"], row_data["synonym"])
            )

    conn.commit()
    conn.close()

    # 4. Clean up Airlock
    os.remove(AIRLOCK_PATH)
    print("Airlock successfully flushed. Database fully populated.")


if __name__ == "__main__":
    run_extraction()
