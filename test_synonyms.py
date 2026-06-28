import asyncio
from core.synonym_engine import get_synonyms

async def main():
    mulethi = await get_synonyms("Mulethi")
    print("Mulethi:", mulethi)

    watermelon = await get_synonyms("Water melon ")
    print("Water melon :", watermelon)

if __name__ == "__main__":
    asyncio.run(main())
