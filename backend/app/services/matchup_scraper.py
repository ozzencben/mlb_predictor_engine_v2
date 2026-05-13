import requests
import json
import os
from datetime import datetime

class MatchupScraper:
    def __init__(self):
        self.data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

        # Takım isimlerini eşleştirmek için haritalama (Eski koddan miras)
        mapping_file = os.path.join(self.data_dir, 'team_mappings.json')
        try:
            with open(mapping_file, 'r', encoding='utf-8') as f:
                mappings = json.load(f)
                self.mlb_to_tr_map = mappings.get("mlb_to_tr", {})
        except FileNotFoundError:
            print("⚠️ Uyarı: team_mappings.json bulunamadı. Ham MLB isimleri kullanılacak.")
            self.mlb_to_tr_map = {}

    def _fetch_standings(self):
        """MLB Puan Durumunu çeker ve takımların Ev/Deplasman/Son 10 maç formunu çıkarır."""
        print("📊 Takım Formları ve Lig Kayıtları Çekiliyor...")
        # 103 = American League, 104 = National League
        url = "https://statsapi.mlb.com/api/v1/standings?leagueId=103,104"
        
        team_records = {}
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            for record in data.get('records', []):
                for team in record.get('teamRecords', []):
                    team_id = team['team']['id']
                    
                    # Genel Kayıt
                    wins = team.get('wins', 0)
                    losses = team.get('losses', 0)
                    
                    # Detaylı Kayıtlar (Ev, Deplasman, Son 10)
                    home_rec = "0-0"
                    away_rec = "0-0"
                    l10_rec = "0-0"
                    
                    for split in team.get('records', {}).get('splitRecords', []):
                        if split['type'] == 'home':
                            home_rec = f"{split['wins']}-{split['losses']}"
                        elif split['type'] == 'away':
                            away_rec = f"{split['wins']}-{split['losses']}"
                        elif split['type'] == 'lastTen':
                            l10_rec = f"{split['wins']}-{split['losses']}"
                            
                    team_records[team_id] = {
                        "record": f"{wins}-{losses}",
                        "home_record": home_rec,
                        "away_record": away_rec,
                        "l10": l10_rec
                    }
            return team_records
        except Exception as e:
            print(f"❌ Puan Durumu Çekme Hatası: {e}")
            return {}

    def fetch_todays_matchups(self):
        today_str = datetime.now().strftime('%Y-%m-%d')
        print(f"🌐 {today_str} tarihi için MLB Maçları Çekiliyor...")

        # 1. Önce puan durumunu al (Takım formları)
        standings = self._fetch_standings()

        # 2. Bugünün maç programını al
        url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today_str}&hydrate=probablePitcher"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            matchups = []
            
            if not data.get('dates'):
                print("ℹ️ Bugün için planlanmış MLB maçı bulunamadı.")
                return matchups

            games = data['dates'][0].get('games', [])
            
            for game in games:
                if game['status']['statusCode'] in ['P', 'S', 'I', 'F', 'O']: 
                    
                    away_node = game['teams']['away']
                    home_node = game['teams']['home']
                    
                    away_team_full = away_node['team']['name']
                    home_team_full = home_node['team']['name']
                    
                    away_id = away_node['team']['id']
                    home_id = home_node['team']['id']
                    
                    away_team = self.mlb_to_tr_map.get(away_team_full, away_team_full)
                    home_team = self.mlb_to_tr_map.get(home_team_full, home_team_full)
                    
                    away_pitcher = away_node.get('probablePitcher', {}).get('fullName', 'TBD')
                    home_pitcher = home_node.get('probablePitcher', {}).get('fullName', 'TBD')
                    
                    # Puan durumu verilerini (varsa) eşleştir, yoksa boş değer ata
                    away_stats = standings.get(away_id, {"record": "0-0", "home_record": "0-0", "away_record": "0-0", "l10": "0-0"})
                    home_stats = standings.get(home_id, {"record": "0-0", "home_record": "0-0", "away_record": "0-0", "l10": "0-0"})
                    
                    matchups.append({
                        "game_id": game['gamePk'],
                        "away_team": away_team,
                        "home_team": home_team,
                        "away_pitcher": away_pitcher,
                        "home_pitcher": home_pitcher,
                        "status": game['status']['detailedState'],
                        # TYLER'IN İSTEDİĞİ YENİ VERİLER BURADA!
                        "away_team_stats": away_stats,
                        "home_team_stats": home_stats
                    })

            output_path = os.path.join(self.data_dir, 'daily_matchups.json')
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump({"date": today_str, "games": matchups}, f, indent=4, ensure_ascii=False)
            
            print(f"✅ Başarılı! {len(matchups)} maç ve detaylı takım formları arşivlendi.")
            return matchups

        except Exception as e:
            print(f"❌ MLB Maçları Çekilirken Hata: {e}")
            return []

if __name__ == "__main__":
    scraper = MatchupScraper()
    todays_games = scraper.fetch_todays_matchups()