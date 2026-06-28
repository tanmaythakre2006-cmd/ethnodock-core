import asyncio
from core.synonym_engine import get_synonyms

async def main():
    res = await get_synonyms("Ashoka")
    print("Ashoka:", res)
    res = await get_synonyms("Mulethi")
    print("Mulethi:", res)

if __name__ == "__main__":
    asyncio.run(main())
