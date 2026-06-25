import streamlit as st
from core.proxy_client import fetch_via_proxy
from core.sieve_parser import clean_html_payload
from core.cognitive_rag import extract_methodology

def main():
    st.set_page_config(layout="wide")

    with st.sidebar:
        api_key = st.text_input("Enter Gemini API Key", type="password")
        st.warning("Keys are stored strictly in volatile session memory.")

    st.title("EthnoDock Core Sieve")
    st.success("Engine online.")

    target_url = st.text_input("Target URL", value="https://en.wikipedia.org/wiki/Ashwagandha")

    if st.button("Test Proxy Sieve"):
        raw_html = fetch_via_proxy(target_url)
        cleaned_text = clean_html_payload(raw_html)

        st.success("Extraction Complete")

        with st.expander("Raw Parsed Text"):
            st.text(cleaned_text[:1000])

        if api_key:
            with st.spinner("Initiating Cognitive Sieve..."):
                methodology = extract_methodology(cleaned_text, api_key)
                st.json(methodology)

if __name__ == "__main__":
    main()
