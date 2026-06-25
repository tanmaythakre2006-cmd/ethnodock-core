import streamlit as st
from core.proxy_client import fetch_via_proxy
from core.sieve_parser import clean_html_payload

def main():
    st.set_page_config(layout="wide")
    st.title("EthnoDock Core Sieve")
    st.success("Engine online.")

    target_url = st.text_input("Target URL", value="https://en.wikipedia.org/wiki/Ashwagandha")

    if st.button("Test Proxy Sieve"):
        raw_html = fetch_via_proxy(target_url)
        cleaned_text = clean_html_payload(raw_html)

        st.success("Extraction Complete")

        with st.expander("Raw Parsed Text"):
            st.text(cleaned_text[:1000])

if __name__ == "__main__":
    main()
