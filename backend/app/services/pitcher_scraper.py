import requests
import json
import os
from datetime import datetime

class PitcherScraper:
    def __init__(self):
        self.data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
        # Geçerli sezon yılı
        self.current_year = datetime.now().year
        # FIP sabiti (Genelde MLB'de 3.10 ile 3.20 arasıdır, 3.15 alıyoruz)
        self.fip_constant = 3.15 

    def _get_pitcher_id(self, pitcher_name):
        """MLB API'sinde atıcının ismini aratıp resmi ID'sini bulur."""
        url = f"https://statsapi.mlb.com/api/v1/people/search?names={pitcher_name}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            if data.get('people'):
                return data['people'][0]['id']
            return None
        except:
            return None

    def _get_pitcher_stats(self, person_id):
        """Atıcının bu sezonki ham istatistiklerini çeker."""
        url = f"https://statsapi.mlb.com/api/v1/people/{person_id}?hydrate=stats(group=[pitching],type=[season],season={self.current_year})"
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            
            # İstatistik bloğunu güvenli bir şekilde bul
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
        print("🚀 Atıcı Kütüphanesi (Pitcher Library) oluşturuluyor...")
        
        # 1. Bugünün maçlarını oku (Kimin atacağını bulmak için)
        matchups_file = os.path.join(self.data_dir, 'daily_matchups.json')
        try:
            with open(matchups_file, 'r', encoding='utf-8') as f:
                matchups_data = json.load(f)
        except FileNotFoundError:
            print("❌ daily_matchups.json bulunamadı! Önce matchup_scraper.py çalıştırılmalı.")
            return

        # 2. Listedeki benzersiz atıcıları topla
        pitcher_names = set()
        for game in matchups_data.get('games', []):
            if game['away_pitcher'] != 'TBD': pitcher_names.add(game['away_pitcher'])
            if game['home_pitcher'] != 'TBD': pitcher_names.add(game['home_pitcher'])

        print(f"🔍 Toplam {len(pitcher_names)} adet başlangıç atıcısı (SP) analiz edilecek.")

        pitcher_library = {}

        # 3. Her atıcı için istatistikleri çek ve FIP (xERA) hesapla
        for name in pitcher_names:
            print(f"⚾ Çekiliyor: {name}...", end=" ")
            
            p_id = self._get_pitcher_id(name)
            if not p_id:
                print("❌ ID Bulunamadı.")
                continue
                
            stats = self._get_pitcher_stats(p_id)
            if not stats:
                print("⚠️ Bu sezon verisi yok (Çaylak veya Sakatlıktan dönmüş).")
                # Verisi olmayanlar için lig ortalaması yedek veriler ata
                pitcher_library[name] = {"era": 4.20, "xera": 4.20, "strikeouts": 0, "innings_pitched": 0.0}
                continue

            # Ham verileri al
            era = float(stats.get('era', 4.20))
            ip = float(stats.get('inningsPitched', 0.1))
            hr = int(stats.get('homeRuns', 0))
            bb = int(stats.get('baseOnBalls', 0))
            k = int(stats.get('strikeOuts', 0))

            # FIP (xERA Proxy) Hesaplama
            if ip > 0:
                fip = ((13 * hr) + (3 * bb) - (2 * k)) / ip + self.fip_constant
                fip = round(max(0.0, fip), 2) # Negatif olmasını engelle
            else:
                fip = era

            pitcher_library[name] = {
                "era": era,
                "xera": fip, # FIP'i xERA olarak kullanıyoruz
                "strikeouts": k,
                "walks": bb,
                "innings_pitched": ip,
                "k_per_9": round((k * 9) / ip, 1) if ip > 0 else 0.0
            }
            print(f"✅ Başarılı (ERA: {era} | xERA: {fip})")

        # ... (Önceki kodlar aynı) ...

        # 4. JSON Olarak Kaydet (HİBRİT DEPOLAMA)
        
        # A. Canlı Sistem İçin (Her gün üzerine yazar)
        output_path = os.path.join(self.data_dir, 'pitcher_stats.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(pitcher_library, f, indent=4, ensure_ascii=False)
            
        # B. Tarihsel Arşiv İçin (pitchers_history klasörüne günün tarihiyle kaydeder)
        history_dir = os.path.join(self.data_dir, 'history')
        if not os.path.exists(history_dir):
            os.makedirs(history_dir)
            
        today_str = datetime.now().strftime('%Y-%m-%d')
        history_path = os.path.join(history_dir, f'{today_str}_pitchers.json')
        with open(history_path, 'w', encoding='utf-8') as f:
            json.dump(pitcher_library, f, indent=4, ensure_ascii=False)
            
        print(f"\n🎉 MUHTEŞEM! {len(pitcher_library)} atıcının verileri hem canlıya hem de arşive ({today_str}_pitchers.json) kaydedildi.")

if __name__ == "__main__":
    scraper = PitcherScraper()
    scraper.build_pitcher_library()