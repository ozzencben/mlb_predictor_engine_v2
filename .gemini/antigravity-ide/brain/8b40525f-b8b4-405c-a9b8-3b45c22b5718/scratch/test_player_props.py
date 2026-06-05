import requests

def test_bulk_props():
    api_key = "0d0dc3ee89d686ebd81213ac126c9af6"
    url = f"https://api.the-odds-api.com/v4/sports/baseball_mlb/odds?apiKey={api_key}&regions=us&markets=pitcher_strikeouts,pitcher_outs&oddsFormat=decimal"
    resp = requests.get(url)
    print("Status code:", resp.status_code)
    
    if resp.status_code == 200:
        data = resp.json()
        print(f"Bulk data returned: {len(data)} events.")
        if data:
            sample = data[0]
            print("\nSample Event:", sample.get("home_team"), "@", sample.get("away_team"))
            print("Bookmakers count:", len(sample.get("bookmakers", [])))
            for b in sample.get("bookmakers", [])[:2]:
                print(f"Bookmaker: {b['key']}")
                for m in b.get("markets", []):
                    print(f"  Market: {m['key']}")
                    print(f"  Outcomes count: {len(m['outcomes'])}")
    else:
        print("Raw Response:", resp.text)

if __name__ == "__main__":
    test_bulk_props()
