from curl_cffi import requests
from bs4 import BeautifulSoup
import json
import os
import tempfile
from datetime import datetime

from app.core.config import settings


class DataCollector:
    def __init__(self):
        self.headers = {"User-Agent": settings.SCRAPER_USER_AGENT}
        self.base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
        self.history_dir = os.path.join(self.base_dir, "history")

        for path in [self.base_dir, self.history_dir]:
            os.makedirs(
                path, exist_ok=True
            )  # exist_ok=True ile try-catch'e gerek kalmaz

        self.league_avg_ops = 0.730
        self.avg_pa_per_game = 38.0

    def _safe_float(self, val: str) -> float:
        if isinstance(val, str):
            val = val.strip().replace("%", "")
        return float(val) if val and val != "--" else 0.0

    def _scrape_teamrankings_table(self, url: str) -> dict:
        try:
            response = requests.get(
                url, headers=self.headers, timeout=10, impersonate="chrome110"
            )
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            table = soup.find("table", {"class": "datatable"})
            rows = table.find("tbody").find_all("tr")

            data = {}
            for row in rows:
                cols = row.find_all("td")
                team_name = cols[1].text.strip()
                data[team_name] = {
                    "current": self._safe_float(cols[2].text),
                    "last_3": self._safe_float(cols[3].text),
                    "home": self._safe_float(cols[5].text),
                    "away": self._safe_float(cols[6].text),
                }
            return data
        except Exception as e:
            print(f"Error (URL: {url}): {e}")
            return {}

    def _atomic_save(self, filepath: str, data: dict):
        """JSON dosyasını bozulma riski olmadan işletim sistemi seviyesinde güvenle kaydeder."""
        dir_name = os.path.dirname(filepath)
        # Geçici dosya oluştur
        fd, temp_path = tempfile.mkstemp(dir=dir_name, suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            # Atomik yer değiştirme (eski dosyayı güvenle ezer)
            os.replace(temp_path, filepath)
        except Exception as e:
            os.remove(temp_path)  # Hata olursa temp dosyasını temizle
            raise e

    def collect_all_stats(self) -> dict:
        print(f"DATA COLLECTION STARTED: {datetime.now().strftime('%Y-%m-%d %H:%M')}")

        # 1. Ham Verileri Çek
        rpg_off = self._scrape_teamrankings_table(
            "https://www.teamrankings.com/mlb/stat/runs-per-game"
        )
        rpg_def = self._scrape_teamrankings_table(
            "https://www.teamrankings.com/mlb/stat/opponent-runs-per-game"
        )
        ba_data = self._scrape_teamrankings_table(
            "https://www.teamrankings.com/mlb/stat/batting-average"
        )
        ops_data = self._scrape_teamrankings_table(
            "https://www.teamrankings.com/mlb/stat/on-base-plus-slugging-pct"
        )
        so_data = self._scrape_teamrankings_table(
            "https://www.teamrankings.com/mlb/stat/strikeouts-per-game"
        )

        # Check that all stats were fetched successfully before saving
        if not all([rpg_off, rpg_def, ba_data, ops_data, so_data]):
            print(
                "Warning: Missing data. Existing JSON will not be overwritten."
            )
            return {}

        # 2. Verileri Birleştir
        unified_stats = {}
        for team in rpg_off.keys():
            team_ops = ops_data.get(team, {}).get("current", self.league_avg_ops)
            wrc_proxy = round((team_ops / self.league_avg_ops) * 100.0, 1)

            team_so = so_data.get(team, {}).get("current", 8.5)
            k_pct_proxy = round((team_so / self.avg_pa_per_game) * 100.0, 1)

            unified_stats[team] = {
                "rpg_offense": rpg_off.get(team, {}),
                "rpg_defense": rpg_def.get(team, {}),
                "batting_avg": ba_data.get(team, {}),
                "advanced_metrics": {"wrc_plus": wrc_proxy, "k_pct": k_pct_proxy},
            }

        # 3. KAYIT İŞLEMİ (ATOMİK)
        live_path = os.path.join(self.base_dir, "live_stats.json")
        history_path = os.path.join(
            self.history_dir, f"{datetime.now().strftime('%Y-%m-%d')}_stats.json"
        )

        self._atomic_save(live_path, unified_stats)
        self._atomic_save(history_path, unified_stats)

        # Scrape and update bullpen SIERA
        try:
            self._scrape_covers_bullpen_siera()
        except Exception as e:
            print(f"Bullpen SIERA update failed: {e}")

        # Scrape and update Sonny Moore PR
        try:
            self._scrape_sonny_moore_pr()
        except Exception as e:
            print(f"Sonny Moore PR update failed: {e}")

        print(f"Live stats updated: {live_path}")
        return unified_stats

    def _scrape_covers_bullpen_siera(self) -> dict:
        current_year = datetime.now().year
        url = f"https://www.covers.com/sport/baseball/mlb/statistics/team-bullpenERA/{current_year}"
        
        COVERS_TO_TR = {
            "LAA": "LA Angels",
            "HOU": "Houston",
            "OAK": "Oakland",
            "ATH": "Oakland",
            "TOR": "Toronto",
            "ATL": "Atlanta",
            "MIL": "Milwaukee",
            "STL": "St Louis",
            "CHC": "Chi Cubs",
            "AZ": "Arizona",
            "LAD": "LA Dodgers",
            "SF": "SF Giants",
            "CLE": "Cleveland",
            "SEA": "Seattle",
            "MIA": "Miami",
            "NYM": "NY Mets",
            "WAS": "Washington",
            "BAL": "Baltimore",
            "SD": "San Diego",
            "PHI": "Philadelphia",
            "PIT": "Pittsburgh",
            "TEX": "Texas",
            "TB": "Tampa Bay",
            "BOS": "Boston",
            "CIN": "Cincinnati",
            "COL": "Colorado",
            "KC": "Kansas City",
            "DET": "Detroit",
            "MIN": "Minnesota",
            "CHW": "Chi White Sox",
            "NYY": "NY Yankees"
        }
        
        print(f"Fetching bullpen data from Covers.com: {url}")
        try:
            response = requests.get(url, headers=self.headers, timeout=10, impersonate="chrome110")
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            
            tables = soup.find_all("table")
            bullpen_siera = {}
            
            for table in tables:
                thead = table.find("thead")
                if thead and "Team" in thead.text:
                    tbody = table.find("tbody")
                    if tbody:
                        rows = tbody.find_all("tr")
                        for row in rows:
                            cols = [td.text.strip() for td in row.find_all("td")]
                            if len(cols) >= 9:
                                covers_team = cols[0]
                                tr_team = COVERS_TO_TR.get(covers_team, covers_team)
                                
                                era = float(cols[1])
                                er = int(cols[4])
                                h = int(cols[3])
                                bb = int(cols[7])
                                so = int(cols[8])
                                
                                # innings pitched calculation
                                if era > 0:
                                    ip = (er * 9) / era
                                else:
                                    ip = 50.0  # safe fallback
                                    
                                bf = (ip * 2.9) + h + bb
                                
                                k_pct = so / bf if bf > 0 else 0.20
                                bb_pct = bb / bf if bf > 0 else 0.08
                                
                                # standard SIERA-like formula
                                siera = (6.145 
                                         - 16.986 * k_pct 
                                         + 11.434 * bb_pct 
                                         - 1.858 * 0.10 
                                         + 7.653 * (k_pct ** 2) 
                                         + 10.130 * k_pct * 0.10 
                                         - 5.195 * bb_pct * 0.10)
                                
                                bullpen_siera[tr_team] = round(max(2.0, min(6.0, siera)), 2)
                        break
            
            if bullpen_siera and len(bullpen_siera) >= 28:
                siera_path = os.path.join(self.base_dir, "bullpen_siera.json")
                self._atomic_save(siera_path, bullpen_siera)
                print(f"Bullpen SIERA data updated: {siera_path} ({len(bullpen_siera)} teams)")
                return bullpen_siera
            else:
                print("Warning: Bullpen data missing or table not found. Update skipped.")
                return {}
        except Exception as e:
            print(f"Error: Covers.com bullpen SIERA retrieval error: {e}")
            return {}

    def _scrape_sonny_moore_pr(self) -> dict:
        url = "https://www.sonnymoorepowerratings.com/mlb.htm"
        MOORE_TO_TR = {
            "LOS ANGELES DODGERS": "LA Dodgers",
            "ATLANTA BRAVES": "Atlanta",
            "MILWAUKEE BREWERS": "Milwaukee",
            "NEW YORK YANKEES": "NY Yankees",
            "TAMPA BAY RAYS": "Tampa Bay",
            "TEXAS RANGERS": "Texas",
            "SEATTLE MARINERS": "Seattle",
            "ARIZONA DIAMONDBACKS": "Arizona",
            "PHILADELPHIA PHILLIES": "Philadelphia",
            "CLEVELAND GUARDIANS": "Cleveland",
            "SAN DIEGO PADRES": "San Diego",
            "ST. LOUIS CARDINALS": "St Louis",
            "PITTSBURGH PIRATES": "Pittsburgh",
            "WASHINGTON NATIONALS": "Washington",
            "CHICAGO WHITE SOX": "Chi White Sox",
            "BALTIMORE ORIOLES": "Baltimore",
            "CHICAGO CUBS": "Chi Cubs",
            "BOSTON RED SOX": "Boston",
            "TORONTO BLUE JAYS": "Toronto",
            "OAKLAND ATHLETICS": "Oakland",
            "DETROIT TIGERS": "Detroit",
            "NEW YORK METS": "NY Mets",
            "MINNESOTA TWINS": "Minnesota",
            "MIAMI MARLINS": "Miami",
            "CINCINNATI REDS": "Cincinnati",
            "SAN FRANCISCO GIANTS": "SF Giants",
            "HOUSTON ASTROS": "Houston",
            "KANSAS CITY ROYALS": "Kansas City",
            "LOS ANGELES ANGELS": "LA Angels",
            "COLORADO ROCKIES": "Colorado"
        }
        
        print(f"Fetching Sonny Moore Power Rankings from: {url}")
        try:
            response = requests.get(url, headers=self.headers, timeout=10, impersonate="chrome110")
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            pre = soup.find("pre")
            if not pre:
                print("Warning: No pre tag found in Sonny Moore page.")
                return {}
                
            lines = pre.text.split("\n")
            sonny_moore_pr = {}
            
            for line in lines:
                parts = line.strip().split()
                if not parts:
                    continue
                    
                if parts[0].isdigit():
                    if len(parts) >= 7:
                        pr_str = parts[-1]
                        team_raw = " ".join(parts[1:-5])
                        
                        try:
                            pr = float(pr_str)
                            tr_team = MOORE_TO_TR.get(team_raw.upper(), team_raw)
                            sonny_moore_pr[tr_team] = pr
                        except ValueError:
                            continue
                            
            if sonny_moore_pr and len(sonny_moore_pr) >= 28:
                moore_path = os.path.join(self.base_dir, "sonny_moore.json")
                self._atomic_save(moore_path, sonny_moore_pr)
                print(f"Sonny Moore PR data updated: {moore_path} ({len(sonny_moore_pr)} teams)")
                return sonny_moore_pr
            else:
                print("Warning: Sonny Moore parsed data missing or insufficient teams. Update skipped.")
                return {}
        except Exception as e:
            print(f"Error: Sonny Moore PR retrieval error: {e}")
            return {}
