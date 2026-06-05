import requests

def test_splits(team_id):
    url = f"https://statsapi.mlb.com/api/v1/teams/{team_id}/stats?stats=statSplits&group=hitting&sitCodes=vl,vr&season=2026"
    res = requests.get(url).json()
    splits = res.get("stats", [{}])[0].get("splits", [])
    for i, s in enumerate(splits):
        print(f"\n--- Split {i} ---")
        print(s.get("split", {}))
        print("stat keys:", s.get("stat", {}).keys())
        print("OPS:", s.get("stat", {}).get("ops"))
        print("full split node (excluding stat):", {k: v for k, v in s.items() if k != "stat"})

if __name__ == "__main__":
    test_splits(147)
