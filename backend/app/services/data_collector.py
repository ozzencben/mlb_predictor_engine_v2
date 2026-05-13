import requests
from bs4 import BeautifulSoup
import json
import os
from datetime import datetime

class DataCollector:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
        }
        # Klasör yolları
        self.base_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
        self.history_dir = os.path.join(self.base_dir, 'history')
        
        # Klasörleri oluştur
        for path in [self.base_dir, self.history_dir]:
            if not os.path.exists(path):
                os.makedirs(path)

        self.league_avg_ops = 0.730
        self.avg_pa_per_game = 38.0 

    def _safe_float(self, val):
        if isinstance(val, str):
            val = val.strip().replace('%', '')
        return float(val) if val and val != '--' else 0.0

    def _scrape_teamrankings_table(self, url):
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('table', {'class': 'datatable'})
            rows = table.find('tbody').find_all('tr')
            
            data = {}
            for row in rows:
                cols = row.find_all('td')
                team_name = cols[1].text.strip()
                data[team_name] = {
                    "current": self._safe_float(cols[2].text),
                    "last_3": self._safe_float(cols[3].text),
                    "home": self._safe_float(cols[5].text),
                    "away": self._safe_float(cols[6].text)
                }
            return data
        except Exception as e:
            print(f"❌ Hata (URL: {url}): {e}")
            return {}

    def collect_all_stats(self):
        print(f"🚀 VERİ TOPLAMA BAŞLADI: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        # 1. Ham Verileri Çek
        rpg_off = self._scrape_teamrankings_table("https://www.teamrankings.com/mlb/stat/runs-per-game")
        rpg_def = self._scrape_teamrankings_table("https://www.teamrankings.com/mlb/stat/opponent-runs-per-game")
        ba_data = self._scrape_teamrankings_table("https://www.teamrankings.com/mlb/stat/batting-average")
        ops_data = self._scrape_teamrankings_table("https://www.teamrankings.com/mlb/stat/on-base-plus-slugging-pct")
        so_data = self._scrape_teamrankings_table("https://www.teamrankings.com/mlb/stat/strikeouts-per-game")
        
        if not rpg_off:
            print("❌ Kritik veriler çekilemedi.")
            return

        # 2. Verileri Birleştir
        unified_stats = {}
        for team in rpg_off.keys():
            team_ops = ops_data.get(team, {}).get("current", self.league_avg_ops)
            wrc_proxy = round((team_ops / self.league_avg_ops) * 100, 1)
            
            team_so = so_data.get(team, {}).get("current", 8.5)
            k_pct_proxy = round((team_so / self.avg_pa_per_game) * 100, 1)

            unified_stats[team] = {
                "rpg_offense": rpg_off.get(team, {}),
                "rpg_defense": rpg_def.get(team, {}),
                "batting_avg": ba_data.get(team, {}),
                "advanced_metrics": {
                    "wrc_plus": wrc_proxy,
                    "k_pct": k_pct_proxy
                }
            }

        # 3. KAYIT İŞLEMİ (HİBRİT)
        # A. Canlı Kullanım İçin (Update Always)
        live_path = os.path.join(self.base_dir, 'live_stats.json')
        with open(live_path, 'w', encoding='utf-8') as f:
            json.dump(unified_stats, f, indent=4, ensure_ascii=False)
        
        # B. Tarihsel Arşiv İçin (Archive)
        today_str = datetime.now().strftime('%Y-%m-%d')
        history_path = os.path.join(self.history_dir, f'{today_str}_stats.json')
        with open(history_path, 'w', encoding='utf-8') as f:
            json.dump(unified_stats, f, indent=4, ensure_ascii=False)
        
        print(f"✅ Canlı veri güncellendi: {live_path}")
        print(f"📂 Geçmişe kaydedildi: {history_path}")
        return unified_stats

if __name__ == "__main__":
    collector = DataCollector()
    collector.collect_all_stats()