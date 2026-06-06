from curl_cffi import requests
from datetime import datetime, timedelta

def test_h2h():
    today = datetime.now()
    yesterday = today - timedelta(days=1)
    # 2025 and 2026 seasons
    start_date = "2025-03-20"
    end_date = yesterday.strftime("%Y-%m-%d")
    
    # DET is 116, CLE is 114
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&startDate={start_date}&endDate={end_date}&teamId=114&opponentId=116&hydrate=linescore"
    r = requests.get(url, timeout=10, impersonate="chrome110")
    print("H2H query status:", r.status_code)
    if r.status_code == 200:
        data = r.json()
        games = []
        for date_node in data.get("dates", []):
            for g in date_node.get("games", []):
                if g['status']['statusCode'] == 'F':
                    games.append(g)
        print(f"Found {len(games)} completed H2H games between Cleveland and Detroit since 2025.")
        if games:
            print("Sample H2H games:")
            for g in games[:3]:
                print(f"  Date: {g['gameDate']} | Away: {g['teams']['away']['team']['name']} ({g['teams']['away'].get('score')}) vs Home: {g['teams']['home']['team']['name']} ({g['teams']['home'].get('score')})")

if __name__ == "__main__":
    test_h2h()
