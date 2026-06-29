import asyncio
import os
import json
from core.synonym_engine import get_synonyms, refine_with_ai

TEST_CASES = ["Apple", "Mulethi", "Ashoka", "Watermelon", "Mentha × piperita"]

async def main():
    # Hack to test Before and After within the same run.
    # We will temporarily clear the API key to simulate "Before", then set it for "After".

    # Store original API key
    api_key = os.environ.get("GEMINI_API_KEY", "")

    print("## Synonym Refinement Evaluation")
    print("| Plant/Query | Programmatic Extraction (Before AI) | AI Semantic Filter (After AI) |")
    print("|---|---|---|")

    for word in TEST_CASES:
        # Before AI
        os.environ["GEMINI_API_KEY"] = ""
        before_syns = await get_synonyms(word)

        # After AI
        # (Since get_synonyms is cached or depends on external, we just directly run refine_with_ai on the before result)
        os.environ["GEMINI_API_KEY"] = api_key
        if api_key:
            after_syns = await refine_with_ai(before_syns)
        else:
            # If we don't actually have a key during this test, just simulate it or say unavailable
            after_syns = ["API Key Missing"]

        b_str = ", ".join(before_syns)
        a_str = ", ".join(after_syns)
        print(f"| {word} | {b_str} | {a_str} |")

if __name__ == "__main__":
    asyncio.run(main())
