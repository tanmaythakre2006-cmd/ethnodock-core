import sqlite3
import pandas as pd
import streamlit as st
from pathlib import Path

# Set up page configurations
st.set_page_config(
    page_title="TCM Data Extraction Pipeline",
    page_icon="🌿",
    layout="wide"
)

# -------------------------------------------------------------------------
# CONSTANTS & CONFIGURATION
# -------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "step_1_db.sqlite"

GENERIC_PLANTS = [
    "Ginseng", "Licorice", "Ginger", "Cinnamon", "Peony",
    "Angelica", "Mugwort", "Lotus", "Jujube (Chinese date)", "Ephedra"
]

# -------------------------------------------------------------------------
# DATA LOADING
# -------------------------------------------------------------------------

@st.cache_data(ttl=60)  # Caches the dataframe to prevent constant disk I/O, refreshed every 60s
def load_step_1_data() -> pd.DataFrame:
    """
    Loads the Step 1 synonym extraction data from SQLite into memory.
    If the database or table does not exist, returns an empty DataFrame.
    """
    if not DB_PATH.exists():
        return pd.DataFrame()

    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("SELECT plant_name, book_name, synonym FROM synonyms", conn)
        conn.close()
        return df
    except sqlite3.Error as e:
        # Fails gracefully if the DB exists but the 'synonyms' table does not
        return pd.DataFrame()

# -------------------------------------------------------------------------
# UI COMPONENTS
# -------------------------------------------------------------------------

def main():
    st.title("🌿 TCM Data Extraction Pipeline")
    st.markdown("---")

    # Check if the extraction engine has been run
    df_synonyms = load_step_1_data()
    is_step_1_complete = not df_synonyms.empty

    # ------------------
    # Step 1 Section
    # ------------------
    st.header("Step 1: Synonym Extraction")

    if not is_step_1_complete:
        st.warning("⚠️ Step 1 Database is empty. Please run the Extraction Engine (engine_step_1.py).")
    else:
        st.success("✅ Step 1 Database successfully loaded.")

        # User selects one of the 10 plants
        selected_plant = st.selectbox(
            "Select a TCM Plant to view extracted synonyms:",
            options=GENERIC_PLANTS
        )

        # Filter the DataFrame based on user selection
        filtered_df = df_synonyms[df_synonyms["plant_name"] == selected_plant]

        # Display the data in a clean Streamlit dataframe UI
        st.dataframe(
            filtered_df,
            hide_index=True,
            use_container_width=True,
            column_config={
                "plant_name": "Plant Name",
                "book_name": "Source Book",
                "synonym": "Extracted Synonym"
            }
        )

    st.markdown("---")

    # ------------------
    # Step 2 Section
    # ------------------
    st.header("Step 2: Sub-species Extraction")
    st.write("This step requires Step 1 to be fully populated.")

    # The Step 2 button is conditionally locked based on Step 1 completion status
    st.button(
        "Extract Sub-species",
        disabled=not is_step_1_complete,
        help="Run Step 1 Extraction Engine first to unlock this feature." if not is_step_1_complete else "Initialize Step 2."
    )


if __name__ == "__main__":
    main()
