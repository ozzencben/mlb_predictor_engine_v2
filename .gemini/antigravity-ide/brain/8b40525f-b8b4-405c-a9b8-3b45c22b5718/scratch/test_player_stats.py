import requests

def test_player(player_id, group="hitting"):
    url = f"https://statsapi.mlb.com/api/v1/people/{player_id}/stats?stats=season&group={group}&season=2026"
    res = requests.get(url).json()
    
    stats_list = res.get("stats", [])
    if not stats_list:
        print("No stats found.")
        return
        
    splits = stats_list[0].get("splits", [])
    if not splits:
        print("No splits found.")
        return
        
    stat = splits[0].get("stat", {})
    print(f"Stats keys for player {player_id} ({group}):")
    print(sorted(list(stat.keys())))
    print("\nSample values:")
    for k in ["avg", "obp", "slg", "ops", "homeRuns", "baseOnBalls", "strikeOuts", "plateAppearances", "hits", "doubles", "triples", "atBats", "hitByPitch", "sacFlies"]:
        if k in stat:
            print(f" - {k}: {stat[k]}")

if __name__ == "__main__":
    print("Judge (Hitter):")
    test_player(592450, "hitting")
    print("\nSasaki (Pitcher):")
    test_player(673540, "pitching") # Roki Sasaki ID is 673540 or similar, let's see
