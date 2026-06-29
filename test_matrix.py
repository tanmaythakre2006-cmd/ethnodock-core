import asyncio
from core.synonym_engine import get_synonyms
import re

TEST_CASES = [
    "Apple", "Ashoka", "Mulethi", "Watermelon", "Lemon",
    "Amazon", "Lotus", "BlackBerry", "Lincoln", "Washington",
    "Mentha × piperita", "Aloe vera", "Garlic", "Ginger",
    "Turmeric", "Neem", "Tulsi", "Ginseng", "Chamomile", "Lavender",
    "Company", "Corp", "Inc"
]

async def run_tests():
    all_passed = True
    for word in TEST_CASES:
        syns = await get_synonyms(word)
        print(f"\n--- Testing: {word} ---")
        print(f"Synonyms: {syns}")

        for syn in syns:
            # General rule: No trailing spaces or numbers
            if syn != syn.strip():
                print(f"FAIL: Trailing space in '{syn}' for '{word}'")
                all_passed = False
            if re.search(r'\d', syn):
                print(f"FAIL: Number in '{syn}' for '{word}'")
                all_passed = False

            # Word-specific rules
            if word == "Ashoka":
                if any(x in syn for x in ["Emperor", "Great", "Maurya"]):
                    print(f"FAIL: Invalid historical reference in '{syn}' for Ashoka")
                    all_passed = False
            if word == "Mulethi":
                if any(x in syn for x in ["Chai", "Latte"]):
                    print(f"FAIL: Invalid recipe reference in '{syn}' for Mulethi")
                    all_passed = False
            if word == "Apple":
                if any(x in syn for x in ["Inc", "Company", "Corp"]):
                    print(f"FAIL: Invalid corporate reference in '{syn}' for Apple")
                    all_passed = False
            if word == "Watermelon":
                if any(x in syn for x in ["西瓜皮", "西瓜子"]):
                    print(f"FAIL: Invalid sub-product in '{syn}' for Watermelon")
                    all_passed = False

    if all_passed:
        print("\nSUCCESS: All tests passed!")
    else:
        print("\nFAILURE: Some tests failed.")
        import sys
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(run_tests())
