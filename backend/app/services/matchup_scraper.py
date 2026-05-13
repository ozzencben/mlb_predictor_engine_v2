import requests
import json
import os
from datetime import datetime

class MatchupScraper:
    def __init__(self):
        self.data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

        # 1. Load Mappings from external config file
        mapping_file = os.path.join(self.data_dir, 'team_mappings.json')
        try:
            with open(mapping_file, 'r', encoding='utf-8') as f:
                mappings = json.load(f)
                self.mlb_to_tr_map = mappings.get("mlb_to_tr", {})
        except FileNotFoundError:
            print("⚠️ Warning: team_mappings.json not found. Using raw MLB names.")
            self.mlb_to_tr_map = {}

    def fetch_todays_matchups(self):
        today_str = datetime.now().strftime('%Y-%m-%d')
        print(f"🌐 Fetching daily matchups from MLB API for {today_str}...")

        url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today_str}&hydrate=probablePitcher"
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            
            matchups = []
            
            if not data.get('dates'):
                print("ℹ️ No scheduled MLB games found for today.")
                return matchups

            games = data['dates'][0].get('games', [])
            
            for game in games:
                if game['status']['statusCode'] in ['P', 'S', 'I', 'F', 'O']: 
                    
                    away_team_full = game['teams']['away']['team']['name']
                    home_team_full = game['teams']['home']['team']['name']
                    
                    away_team = self.mlb_to_tr_map.get(away_team_full, away_team_full)
                    home_team = self.mlb_to_tr_map.get(home_team_full, home_team_full)
                    
                    away_pitcher = game['teams']['away'].get('probablePitcher', {}).get('fullName', 'TBD')
                    home_pitcher = game['teams']['home'].get('probablePitcher', {}).get('fullName', 'TBD')
                    
                    matchups.append({
                        "game_id": game['gamePk'],
                        "away_team": away_team,
                        "home_team": home_team,
                        "away_pitcher": away_pitcher,
                        "home_pitcher": home_pitcher,
                        "status": game['status']['detailedState']
                    })

            output_path = os.path.join(self.data_dir, 'daily_matchups.json')
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump({"date": today_str, "games": matchups}, f, indent=4, ensure_ascii=False)
            
            print(f"✅ Success! {len(matchups)} games and probable pitchers have been archived.")
            return matchups

        except Exception as e:
            print(f"❌ Error fetching data from MLB API: {e}")
            return []

if __name__ == "__main__":
    scraper = MatchupScraper()
    todays_games = scraper.fetch_todays_matchups()