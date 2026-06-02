import json
import os

def main():
    data_dir = os.path.join("app", "data")
    file_path = os.path.join(data_dir, "todays_predictions.json")
    
    if not os.path.exists(file_path):
        print("todays_predictions.json not found!")
        return
        
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    print(f"Loaded todays_predictions.json. Keys: {list(data.keys())}")
    
    # Let's inspect 'predictions' key if it exists, or just print keys and a sample
    for key, value in data.items():
        print(f"Key: {key}, Type: {type(value)}")
        if isinstance(value, list) and len(value) > 0:
            print("  List length:", len(value))
            print("  First item details:")
            item = value[0]
            print("    Matchup:", item.get("matchup", {}).get("away_team"), "at", item.get("matchup", {}).get("home_team"))
            print("    Odds keys:", item.get("Odds", {}).keys())
            print("    nrfi_odds:", item.get("Odds", {}).get("nrfi_odds"))
            print("    yrfi_odds:", item.get("Odds", {}).get("yrfi_odds"))
        elif isinstance(value, dict):
            print("  Dict keys:", list(value.keys())[:5])

if __name__ == "__main__":
    main()
