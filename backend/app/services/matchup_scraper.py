import requests
import json
import os
import tempfile # Atomik yazma için eklendi
from datetime import datetime
import pytz 

class MatchupScraper:
    def __init__(self):
        self.data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
        os.makedirs(self.data_dir, exist_ok=True)

        mapping_file = os.path.join(self.data_dir, 'team_mappings.json')
        try:
            with open(mapping_file, 'r', encoding='utf-8') as f:
                mappings = json.load(f)
                self.mlb_to_tr_map = mappings.get("mlb_to_tr", {})
        except FileNotFoundError:
            print("⚠️ Uyarı: team_mappings.json bulunamadı. Ham MLB isimleri kullanılacak.")
            self.mlb_to_tr_map = {}

    def _atomic_save(self, filepath: str, data: dict):
        """Dosyanın bozulmasını önleyen atomik yazma işlemi."""
        dir_name = os.path.dirname(filepath)
        fd, temp_path = tempfile.mkstemp(dir=dir_name, suffix='.json')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            os.replace(temp_path, filepath)
        except Exception as e:
            os.remove(temp_path)
            raise e

    def _fetch_standings(self):
        """MLB Puan Durumunu çeker."""
        print("📊 Takım Formları ve Lig Kayıtları Çekiliyor...")
        url = "https://statsapi.mlb.com/api/v1/standings?leagueId=103,104"
        team_records = {}
        try:
            # timeout eklendi, ağ sorunlarında sonsuza kadar beklemez
            response = requests.get(url, timeout=10) 
            response.raise_for_status()
            data = response.json()
            
            for record in data.get('records', []):
                for team in record.get('teamRecords', []):
                    team_id = team['team']['id']
                    wins = team.get('wins', 0)
                    losses = team.get('losses', 0)
                    
                    home_rec, away_rec, l10_rec = "0-0", "0-0", "0-0"
                    
                    for split in team.get('records', {}).get('splitRecords', []):
                        rec_str = f"{split.get('wins', 0)}-{split.get('losses', 0)}"
                        if split['type'] == 'home':
                            home_rec = rec_str
                        elif split['type'] == 'away':
                            away_rec = rec_str
                        elif split['type'] == 'lastTen':
                            l10_rec = rec_str
                            
                    team_records[team_id] = {
                        "record": f"{wins}-{losses}",
                        "home_record": home_rec,
                        "away_record": away_rec,
                        "l10": l10_rec
                    }
            return team_records
        except Exception as e:
            print(f"❌ Puan Durumu Çekme Hatası: {e}")
            return {} # Standings olmadan da program devam etmeli

    def fetch_todays_matchups(self):
        tz_et = pytz.timezone('US/Eastern')
        now_et = datetime.now(tz_et)
        today_str = now_et.strftime('%Y-%m-%d')
        
        print(f"🌐 [Timezone: ET] {today_str} tarihi için MLB Maçları Çekiliyor...")

        standings = self._fetch_standings()
        url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={today_str}&hydrate=probablePitcher"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            matchups = []
            if not data.get('dates'):
                print("ℹ️ Bugün için planlanmış MLB maçı bulunamadı.")
                # GÜVENLİK: Boş liste döndürmek yerine durumu bildirip çıkıyoruz. 
                # Mevcut JSON dosyasına dokunmuyoruz ki dünkü veriler ekranda kalsın.
                return []

            games = data['dates'][0].get('games', [])
            
            for game in games:
                if game['status']['statusCode'] in ['P', 'S', 'I', 'F', 'O']: 
                    away_node = game['teams']['away']
                    home_node = game['teams']['home']
                    
                    away_team_full = away_node['team']['name']
                    home_team_full = home_node['team']['name']
                    
                    away_team = self.mlb_to_tr_map.get(away_team_full, away_team_full)
                    home_team = self.mlb_to_tr_map.get(home_team_full, home_team_full)
                    
                    away_pitcher = away_node.get('probablePitcher', {}).get('fullName', 'TBD')
                    home_pitcher = home_node.get('probablePitcher', {}).get('fullName', 'TBD')
                    
                    raw_date = game.get('gameDate')
                    game_time = "TBD"
                    if raw_date:
                        try:
                            utc_dt = pytz.utc.localize(datetime.strptime(raw_date, '%Y-%m-%dT%H:%M:%SZ'))
                            et_dt = utc_dt.astimezone(tz_et)
                            game_time = et_dt.strftime('%I:%M %p ET').lstrip('0')
                        except Exception:
                            game_time = raw_date 
                    
                    away_stats = standings.get(away_node['team']['id'], {"record": "0-0", "home_record": "0-0", "away_record": "0-0", "l10": "0-0"})
                    home_stats = standings.get(home_node['team']['id'], {"record": "0-0", "home_record": "0-0", "away_record": "0-0", "l10": "0-0"})
                    
                    matchups.append({
                        "game_id": game['gamePk'],
                        "away_team": away_team,
                        "home_team": home_team,
                        "away_pitcher": away_pitcher,
                        "home_pitcher": home_pitcher,
                        "game_time": game_time,
                        "status": game['status']['detailedState'],
                        "away_team_stats": away_stats,
                        "home_team_stats": home_stats
                    })

            # Eğer API yanıt döndüyse ama maç yoksa (örn: All-Star arası), eski veriyi ezmemek için kontrol
            if not matchups:
                return []

            last_updated_str = now_et.strftime('%B %d, %I:%M %p ET')
            output_path = os.path.join(self.data_dir, 'daily_matchups.json')
            
            # GÜVENLİK: Atomik yazma işlemi
            self._atomic_save(output_path, {"date": today_str, "games": matchups, "last_updated": last_updated_str})
            
            print(f"✅ Başarılı! {len(matchups)} maç arşivlendi.")
            return matchups

        except Exception as e:
            # GÜVENLİK: API çökerse dünkü/mevcut JSON dosyasını ezme. Sadece hata dön.
            print(f"❌ MLB Maçları Çekilirken Hata: {e}. Mevcut veri korundu.")
            return []