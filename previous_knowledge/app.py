import streamlit as st
import asyncio

from core.synonym_engine import get_synonyms

st.markdown("""
    <style>
    :root {
        --bg-color: #0d0d0d;
        --panel-bg: #1a1a1a;
        --text-color: #e0e0e0;
        --neon-green: #00ff41;
        --neon-cyan: #00e5ff;
        --neon-purple: #b026ff;
        --neon-orange: #ff9900;
        --border-color: #333;
    }
    body, .stApp { background-color: var(--bg-color) !important; color: var(--text-color) !important; font-family: 'Courier New', monospace; }
    h1, h2, h3 { color: var(--neon-cyan) !important; text-transform: uppercase; letter-spacing: 2px; text-shadow: 0 0 10px rgba(0, 229, 255, 0.5); }
    .stButton>button { background-color: transparent; color: var(--neon-green); border: 1px solid var(--neon-green); text-transform: uppercase; transition: all 0.3s ease; width: 100%; margin-top: 10px; }
    .stButton>button:hover { background-color: rgba(0, 255, 65, 0.1); box-shadow: 0 0 15px var(--neon-green); }

    .node-card { background-color: var(--panel-bg); border: 1px solid var(--neon-purple); border-radius: 4px; padding: 15px; margin-bottom: 15px; box-shadow: 0 0 10px rgba(176, 38, 255, 0.1); }
    .node-card-experimental { border-color: var(--neon-orange); box-shadow: 0 0 10px rgba(255, 153, 0, 0.1); }

    .node-header { color: var(--neon-purple); font-size: 1.1rem; margin-bottom: 8px; border-bottom: 1px solid rgba(176, 38, 255, 0.3); padding-bottom: 5px; text-transform: uppercase; }
    .node-header-experimental { color: var(--neon-orange); border-bottom-color: rgba(255, 153, 0, 0.3); }

    .node-label { color: var(--neon-cyan); font-weight: bold; }
    .node-value { color: var(--neon-green); }
    </style>
""", unsafe_allow_html=True)

st.title("Synonym Engine Unit Test")

herb_name = st.text_input("Enter Herb Name to Test Synonym Resolution", placeholder="e.g., Turmeric")

if st.button("Test Synonym Resolver") or herb_name:
    if not herb_name:
        st.error("SYSTEM FAILURE: Target Herb is required.")
    else:
        with st.spinner(f"Resolving synonyms for '{herb_name}'..."):
            synonyms = asyncio.run(get_synonyms(herb_name))

            st.subheader("Resolution Results")
            st.write(f"**Target:** {herb_name}")
            st.json({"synonyms": synonyms})
