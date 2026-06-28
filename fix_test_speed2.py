with open("run_all.py", "r") as f:
    code = f.read()

# We test it concurrently in small batches to finish quicker, but maybe batches are causing the 429!
code = code.replace(
'''    tasks = [process(plant) for plant in FAMOUS_PLANTS]
    results = await asyncio.gather(*tasks)''',
'''    results = []
    # Test sequentially or in tiny batches to prevent 429 from PubMed/Wikipedia
    for i in range(0, len(FAMOUS_PLANTS), 3):
        chunk = FAMOUS_PLANTS[i:i+3]
        tasks = [process(plant) for plant in chunk]
        res = await asyncio.gather(*tasks)
        results.extend(res)
        await asyncio.sleep(1)''')
with open("run_all.py", "w") as f:
    f.write(code)
