import asyncio
import logging
from core.pipeline import run_autonomous_extraction

logging.basicConfig(level=logging.INFO)

FAMOUS_PLANTS = [
    "Ashwagandha", "Papaya", "Turmeric", "Neem", "Holy Basil",
    "Ginger", "Garlic", "Aloe Vera", "Echinacea", "Ginkgo Biloba",
    "Ginseng", "Lavender", "Chamomile", "Peppermint", "Rosemary",
    "Thyme", "Sage", "Oregano", "Cinnamon", "Cardamom"
]

async def test_cascade():
    success_count = 0
    failure_count = 0

    for plant in FAMOUS_PLANTS:
        print(f"\\n--- Testing {plant} ---")
        master_matrix, experimental_matrix = await run_autonomous_extraction(plant, max_urls=3)

        # We only care about stream A success (Master Matrix), as requested, no API call
        if not master_matrix:
            print(f"FAILED: Empty result for {plant}")
            failure_count += 1
        else:
            print(f"SUCCESS: Extracted data for {plant}")
            print(f"Data: {master_matrix}")
            success_count += 1

    print(f"\\n--- Test Results ---")
    print(f"Total Successes: {success_count}/{len(FAMOUS_PLANTS)}")
    print(f"Total Failures: {failure_count}/{len(FAMOUS_PLANTS)}")

    assert failure_count == 0, f"Cascade test failed. {failure_count} plants returned empty results."
    print("ALL TESTS PASSED.")

if __name__ == "__main__":
    asyncio.run(test_cascade())
