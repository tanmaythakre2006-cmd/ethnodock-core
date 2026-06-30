import asyncio
import logging
from core.pipeline import run_autonomous_extraction

logging.basicConfig(level=logging.ERROR)

FAMOUS_PLANTS = [
    "Tulsi", "Neem", "Aloe Vera", "Ashwagandha", "Turmeric", "Giloy", "Amla",
    "Ginger", "Garlic", "Mint", "Brahmi", "Shatavari", "Arjuna", "Moringa",
    "Lemongrass", "Bael", "Kalmegh", "Sarpagandha", "Safed Musli", "Punarnava",
    "Gudmar", "Haritaki", "Bibhitaki", "Mulethi", "Fenugreek", "Black Pepper",
    "Cinnamon", "Clove", "Cardamom", "Gotu Kola", "Stevia", "Chamomile",
    "Lavender", "Echinacea", "Ginseng", "Valerian", "Milk Thistle", "Dandelion",
    "Rosemary", "Sage", "Thyme", "Noni", "Boswellia", "Bhringraj", "Kutki",
    "Gokshura", "Jatamansi", "Vacha", "Manjistha", "Shankhpushpi", "Curry Leaf",
    "Coriander", "Fennel", "Cumin", "Ajwain", "Mustard", "Sesame", "Flax",
    "Isabgol", "Hibiscus", "Henna", "Jasmine", "Rose", "Marigold", "Lotus",
    "Saffron", "Tamarind", "Drumstick Tree", "Jamun", "Kokum", "Indian Gooseberry",
    "Holy Basil", "Sweet Basil", "Oregano", "Bay Leaf", "Nutmeg", "Mace",
    "Star Anise", "Allspice", "Anise", "Catnip", "Lemon Balm", "Yarrow",
    "Comfrey", "Plantain Herb", "Elderberry", "Elderflower", "Horsetail", "Mullein"
]

async def process(plant):
    try:
        matrix, _ = await asyncio.wait_for(run_autonomous_extraction(plant, max_urls=1), timeout=25.0)
        return plant, matrix
    except Exception as e:
        return plant, None

async def test_cascade():
    success = 0
    fail = []

    results = []
    # Test sequentially or in tiny batches to prevent 429 from PubMed/Wikipedia
    for i in range(0, len(FAMOUS_PLANTS), 3):
        chunk = FAMOUS_PLANTS[i:i+3]
        tasks = [process(plant) for plant in chunk]
        res = await asyncio.gather(*tasks)
        results.extend(res)
        await asyncio.sleep(1)

    for plant, matrix in results:
        if not matrix:
            fail.append(plant)
            print(f"Failed: {plant}")
        else:
            success += 1
            print(f"Success: {plant}")

    print(f"\\n--- Test Results ---")
    print(f"Total Successes: {success}/{len(FAMOUS_PLANTS)}")
    print(f"Total Failures: {len(fail)}/{len(FAMOUS_PLANTS)}")
    if fail:
        print(f"Failures: {fail}")
        import sys
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_cascade())
