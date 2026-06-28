import streamlit as st
import asyncio

from core.pipeline import run_autonomous_extraction
from database.supabase_client import save_master_matrix, save_experimental_matrix

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

st.title("EthnoDock Hybrid Sovereign Engine")

api_key = st.text_input("Gemini API Key (For Stream B Sandbox)", type="password")
herb_name = st.text_input("Target Herb", placeholder="e.g., Turmeric")
max_urls = st.slider("Max URLs", min_value=1, max_value=15, value=5)

def render_matrix(matrix, is_experimental=False):
    mythologies = matrix.get("mythologies", {})
    if not mythologies:
        st.warning("No data found.")
        return

    tabs = st.tabs(list(mythologies.keys()))
    for idx, (myth_name, texts) in enumerate(mythologies.items()):
        with tabs[idx]:
            for text_name, text_data in texts.items():
                props = text_data.get("properties", [])
                prop_list = "".join([f"<li>{p}</li>" for p in props])

                card_class = "node-card node-card-experimental" if is_experimental else "node-card"
                header_class = "node-header node-header-experimental" if is_experimental else "node-header"

                html = f"""
                <div class="{card_class}">
                    <div class="{header_class}">{text_name}</div>
                    <div><span class="node-label">Nomenclature:</span> <span class="node-value">{', '.join(text_data.get('nomenclature', [])) or 'Unknown'}</span></div>
                    <div><span class="node-label">Species:</span> <span class="node-value">{', '.join(text_data.get('species', [])) or 'Unknown'}</span></div>
                    <div style="margin-top: 10px;"><span class="node-label">Properties:</span></div>
                    <ul class="node-value" style="margin-top: 5px;">{prop_list}</ul>
                </div>
                """
                st.markdown(html, unsafe_allow_html=True)

if st.button("Commence Neural Extraction"):
    if not herb_name:
        st.error("SYSTEM FAILURE: Target Herb is required.")
    else:
        async def execute():
            with st.status("Hybrid Pipeline Active... Searching...") as status:
                progress = st.progress(25)

                master_matrix, experimental_matrix = await run_autonomous_extraction(herb_name, api_key, max_urls)

                status.update(label="Saving to Sovereign Datastores...")
                progress.progress(80)

                if master_matrix:
                    try: save_master_matrix(herb_name, master_matrix, ["Hybrid_Run"])
                    except: pass
                if experimental_matrix:
                    try: save_experimental_matrix(herb_name, experimental_matrix, ["Hybrid_Run"])
                    except: pass

                progress.progress(100)
                status.update(label="Extraction Complete.", state="complete")
            return master_matrix, experimental_matrix

        m_matrix, e_matrix = asyncio.run(execute())

        # Render outside the status block so they aren't hidden
        st.subheader("Stream A: Verified Scientific Data (Core Matrix)")
        render_matrix(m_matrix, is_experimental=False)

        st.subheader("Stream B: Conventional Insights (Sandbox Findings)")
        if api_key:
            render_matrix(e_matrix, is_experimental=True)
        else:
            st.info("API Key required for Stream B (Cognitive Sandbox).")
