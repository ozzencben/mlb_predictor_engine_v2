import requests
import json
import os
from datetime import datetime

class PitcherScraper:
    def __init__(self):
        self.data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
        self.current_year = datetime.now().year
        # MLB'de FIP sabiti genelde 3.10 - 3.20 arasıdır.
        self.fip_constant = 3.15 
        
        # Çaylaklar için varsayılan değerleri güncelledik (W-L eklendi)
        self.league_averages = {
            "era": 4.20,
            "fip": 4.20,
            "k_bb_pct": 0.14, # %14
            "innings_pitched": 0.0,
            "wins": 0,
            "losses": 0,
            "record": "0-0"
        }

    def _get_pitcher_id(self, pitcher_name):
        """MLB API'de atıcıyı isminden arar ve resmi ID'sini bulur."""
        url = f"https://statsapi.mlb.com/api/v1/people/search?names={pitcher_name}"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            if data.get('people'):
                return data['people'][0]['id']
            return None
        except:
            return None

    def _get_advanced_stats(self, person_id):
        """Atıcının saf yetenek metriklerini hesaplamak için ham MLB verilerini çeker."""
        url = f"https://statsapi.mlb.com/api/v1/people/{person_id}?hydrate=stats(group=[pitching],type=[season],season={self.current_year})"
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            people = data.get('people', [])
            if not people: return None
            
            stats_list = people[0].get('stats', [])
            if not stats_list: return None
            
            splits = stats_list[0].get('splits', [])
            if not splits: return None
            
            return splits[0].get('stat', {})
        except:
            return None

    def build_pitcher_library(self):
        print("🚀 Kırılmaz MLB Statcast Kütüphanesi Oluşturuluyor (W-L Kayıtları ile)...")
        
        matchups_file = os.path.join(self.data_dir, 'daily_matchups.json')
        try:
            with open(matchups_file, 'r', encoding='utf-8') as f:
                matchups_data = json.load(f)
        except FileNotFoundError:
            print("❌ daily_matchups.json bulunamadı!")
            return

        pitcher_names = set()
        for game in matchups_data.get('games', []):
            if game['away_pitcher'] != 'TBD': pitcher_names.add(game['away_pitcher'])
            if game['home_pitcher'] != 'TBD': pitcher_names.add(game['home_pitcher'])

        print(f"🔍 Toplam {len(pitcher_names)} adet başlangıç atıcısı (SP) aranıyor...")

        pitcher_library = {}

        for name in pitcher_names:
            print(f"⚾ Çekiliyor: {name}...", end=" ")
            
            p_id = self._get_pitcher_id(name)
            if not p_id:
                print("⚠️ ID Bulunamadı. Çaylak/Farklı İsim.")
                pitcher_library[name] = self.league_averages.copy()
                continue
                
            stats = self._get_advanced_stats(p_id)
            if not stats:
                print("⚠️ Bu sezon verisi yok. Lig ortalaması atandı.")
                pitcher_library[name] = self.league_averages.copy()
                continue

            # Temel veriler
            era = float(stats.get('era', 4.20))
            ip = float(stats.get('inningsPitched', 0.1))
            hr = int(stats.get('homeRuns', 0))
            bb = int(stats.get('baseOnBalls', 0))
            k = int(stats.get('strikeOuts', 0))
            bf = int(stats.get('battersFaced', 1))
            
            # YENİ EKLENENLER: Galibiyet ve Mağlubiyet
            wins = int(stats.get('wins', 0))
            losses = int(stats.get('losses', 0))

            # 1. Gerçek K-BB% Hesaplama
            if bf > 0:
                k_pct = k / bf
                bb_pct = bb / bf
                k_bb_pct = round(k_pct - bb_pct, 3)
            else:
                k_bb_pct = 0.0

            # 2. FIP Hesaplama
            if ip > 0:
                fip = ((13 * hr) + (3 * bb) - (2 * k)) / ip + self.fip_constant
                fip = round(max(0.0, fip), 2)
            else:
                fip = era

            pitcher_library[name] = {
                "era": era,
                "fip": fip, 
                "k_bb_pct": k_bb_pct,
                "innings_pitched": ip,
                "wins": wins,
                "losses": losses,
                "record": f"{wins}-{losses}" # Frontend için hazır string (Örn: "5-2")
            }
            print(f"✅ Başarılı (W-L: {wins}-{losses} | FIP: {fip})")

        output_path = os.path.join(self.data_dir, 'pitcher_stats.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(pitcher_library, f, indent=4, ensure_ascii=False)
            
        history_dir = os.path.join(self.data_dir, 'history')
        if not os.path.exists(history_dir):
            os.makedirs(history_dir)
            
        today_str = datetime.now().strftime('%Y-%m-%d')
        history_path = os.path.join(history_dir, f'{today_str}_pitchers.json')
        with open(history_path, 'w', encoding='utf-8') as f:
            json.dump(pitcher_library, f, indent=4, ensure_ascii=False)
            
        print(f"\n🎉 GÖREV TAMAM! {len(pitcher_library)} atıcının İleri Seviye İstatistikleri ve W-L kayıtları çekildi.")

if __name__ == "__main__":
    scraper = PitcherScraper()
    scraper.build_pitcher_library()