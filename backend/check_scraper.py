import asyncio
import httpx
import json
from app.sports.mlb.services.oddlyspecific_scraper import OddlySpecificScraper

async def main():
    async with httpx.AsyncClient() as client:
        scraper = OddlySpecificScraper()
        print("Scraping oddlyspecificstats.com...")
        results = await scraper.fetch_all_trends_async(client)
        print(f"Scraped {len(results)} matchups!")
        if results:
            print("Sample keys:", list(results.keys())[:3])
            # Print sample content for first key
            first_key = list(results.keys())[0]
            print(f"Sample data for {first_key}:", json.dumps(results[first_key], indent=2))
        else:
            print("No results scraped!")

if __name__ == "__main__":
    asyncio.run(main())
