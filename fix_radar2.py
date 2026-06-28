with open("core/council_orchestrator.py", "r") as f:
    code = f.read()

# Let's ensure the fallback chunk is ALWAYS injected in the pipeline if we don't have enough!
# Actually, the user doesn't care if we inject a Wikipedia fallback URL, as long as it's not a fake hardcoded URL. I ALREADY removed the fake text in `council_orchestrator.py`.
# Wait, why are so many herbs failing? Because PubMed rate limit!
# "Failed to fetch https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=Bibhatsu[Title/Abstract]&retmode=json&retmax=15: HTTP 429"
# PubMed 429 blocks EVERYTHING.

# And Wikipedia? Wikipedia API also rate-limits!
# So ALL direct API hits are failing due to 429 in tests.

# Let's add a robust fallback for 429 in `direct_ingestion.py` that just returns a valid chunk for testing purposes?
# No, "do NOT implement 'guessed' or hardcoded fallback URLs. That is a brittle band-aid, not an architectural solution."
# The user wants "ensure the test suite passes on the entire list of herbs without using hardcoded URL shortcuts."
# To fix 429s, we should just use `asyncio.sleep` to respect rate limits, but the test needs to finish. Let's add exponential backoff in the proxy client or `fetch_direct_data`.
