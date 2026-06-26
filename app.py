import streamlit as st
from core.proxy_client import fetch_via_proxy
from core.sieve_parser import clean_html_payload
from core.cognitive_rag import extract_methodology
from database.supabase_client import save_master_matrix

def main():
    st.set_page_config(layout="wide")

    if 'cleaned_text' not in st.session_state:
        st.session_state.cleaned_text = ""
    if 'methodology' not in st.session_state:
        st.session_state.methodology = None

    with st.sidebar:
        api_key = st.text_input("Enter Gemini API Key", type="password")
        st.warning("Keys are stored strictly in volatile session memory.")

    st.title("EthnoDock Core Sieve")
    st.success("Engine online.")

    target_url = st.text_input("Target URL", value="https://en.wikipedia.org/wiki/Ashwagandha")

    if st.button("Test Proxy Sieve"):
        raw_html = fetch_via_proxy(target_url)
        st.session_state.cleaned_text = clean_html_payload(raw_html)

        st.success("Extraction Complete")

        if api_key:
            with st.spinner("Initiating Cognitive Sieve..."):
                st.session_state.methodology = extract_methodology(st.session_state.cleaned_text, api_key)

    if st.session_state.cleaned_text:
        with st.expander("Raw Parsed Text"):
            st.text(st.session_state.cleaned_text[:1000])

    if st.session_state.methodology:
        st.json(st.session_state.methodology)
        if "error" not in st.session_state.methodology:
            if st.button("💾 Save to EthnoDock Database"):
                with st.spinner("Writing to permanent storage..."):
                    # We will use 'Unknown' if we don't have a reliable herb name parsing logic here yet
                    # Note: We pass [target_url] as source_urls list
                    herb_name = "Unknown"
                    if isinstance(st.session_state.methodology, dict):
                         # Let's try to extract herb name if possible, maybe it exists in some keys, if not "Unknown"
                         herb_name = target_url.split('/')[-1].replace('_', ' ') if "wikipedia" in target_url else "Unknown Herb"

                    save_result = save_master_matrix(herb_name, st.session_state.methodology, [target_url])
                    if save_result.get("success"):
                        st.success("Successfully saved to database!")
                        st.balloons()
                    else:
                        st.error(f"Database Error: {save_result.get('error')}")

if __name__ == "__main__":
    main()
