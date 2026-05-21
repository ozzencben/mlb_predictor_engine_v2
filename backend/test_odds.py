import httpx
import asyncio
from app.core.config import settings

async def main():
    api_key = "0d0dc3ee89d686ebd81213ac126c9af6"
    url = "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds"
    params = {
        "apiKey": api_key,
        "regions": "us",
        "markets": "h2h,spreads,totals",
        "bookmakers": "fanduel,draftkings,caesars,betmgm,fanatics,pointsbetus",
        "oddsFormat": "decimal",
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params, timeout=10.0)
        print("Status Code:", response.status_code)
        if response.status_code == 200:
            data = response.json()
            print("Successfully fetched odds for", len(data), "games.")
            if data:
                print("First game sample keys:", data[0].keys())
                bookies = data[0].get("bookmakers", [])
                if bookies:
                    print("Sample bookmaker markets for", bookies[0]["title"], ":")
                    for m in bookies[0]["markets"]:
                        print("  Market:", m["key"])
                        print("    Outcomes sample:", m["outcomes"][:2])
        else:
            print("Error response:", response.text)

if __name__ == "__main__":
    asyncio.run(main())
