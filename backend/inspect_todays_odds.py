import json
import os

def main():
    data_dir = os.path.join("app", "sports", "mlb", "data")
    file_path = os.path.join(data_dir, "todays_predictions.json")
    
    if not os.path.exists(file_path):
        print("todays_predictions.json not found!")
        return
        
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    print(f"Date: {data.get('date')}")
    print(f"Last Updated: {data.get('last_updated', 'None')}")
    
    predictions = data.get("predictions", [])
    print(f"Total predictions: {len(predictions)}")
    
    for i, p in enumerate(predictions):
        matchup = p.get("matchup", {})
        away = matchup.get("away_team")
        home = matchup.get("home_team")
        odds = p.get("Odds", {})
        
        # Check if this match has weird odds
        print(f"\n{i+1}: {away} at {home}")
        print(f"  Game Time: {matchup.get('game_time')}")
        print(f"  Status: {matchup.get('status')}")
        print(f"  Odds block:")
        print(f"    best_away_odds: {odds.get('best_away_odds')}")
        print(f"    best_home_odds: {odds.get('best_home_odds')}")
        print(f"    over_under: {odds.get('over_under')}")
        print(f"    away_book: {odds.get('away_book')}")
        print(f"    home_book: {odds.get('home_book')}")
        
if __name__ == "__main__":
    main()
