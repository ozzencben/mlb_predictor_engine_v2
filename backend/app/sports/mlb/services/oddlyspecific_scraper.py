import re
import json
import httpx
import asyncio

class OddlySpecificScraper:
    def __init__(self):
        self.base_url = "https://www.oddlyspecificstats.com"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        }

    @staticmethod
    def _calculate_record(starts: int, pct: float) -> str:
        """Yüzde ve toplam maç sayısından W-L (Galibiyet-Mağlubiyet) stringi üretir."""
        if not starts or pct is None:
            return "0-0"
        nrfi_wins = round((pct / 100.0) * starts)
        yrfi_losses = starts - nrfi_wins
        return f"{nrfi_wins}-{yrfi_losses}"

    @staticmethod
    def _get_streak_emoji(streak_type: str, count: int) -> str:
        """UI için serinin durumuna göre dinamik emoji döndürür."""
        if count <= 0:
            return ""
        if streak_type == "nrfi":
            if count >= 10: return "👑" # Elite NRFI Streak
            if count >= 5: return "🔥"  # Hot NRFI Streak
            return "✅"
        if streak_type == "yrfi":
            if count >= 5: return "🚨"  # Bad YRFI Streak
            return "⚠️"
        return ""

    @staticmethod
    def _calc_team_stats(logs: list, location_context: str) -> dict:
        """Ham maç loglarından takımın istatistiklerini hesaplar."""
        if not logs:
            return {}

        # 1. Season (Tüm Maçlar)
        season_starts = len(logs)
        season_nrfi = sum(1 for row in logs if row.get("gameNrfi") == 1)
        season_pct = (season_nrfi / season_starts * 100.0) if season_starts else 0.0

        # 2. Location (Sadece Ev veya Sadece Deplasman Maçları)
        loc_logs = [row for row in logs if row.get("location") == location_context]
        loc_starts = len(loc_logs)
        loc_nrfi = sum(1 for row in loc_logs if row.get("gameNrfi") == 1)
        loc_pct = (loc_nrfi / loc_starts * 100.0) if loc_starts else 0.0

        # 3. Last 10 (Son 10 Maç)
        l10_logs = logs[:10]
        l10_starts = len(l10_logs)
        l10_nrfi = sum(1 for row in l10_logs if row.get("gameNrfi") == 1)
        l10_pct = (l10_nrfi / l10_starts * 100.0) if l10_starts else 0.0

        # 4. Streak Hesaplama (Art arda NRFI veya YRFI)
        streak_count = 0
        streak_type = None
        if logs:
            first_game_is_nrfi = logs[0].get("gameNrfi") == 1
            streak_type = "nrfi" if first_game_is_nrfi else "yrfi"
            for row in logs:
                is_nrfi = row.get("gameNrfi") == 1
                if (is_nrfi and streak_type == "nrfi") or (not is_nrfi and streak_type == "yrfi"):
                    streak_count += 1
                else:
                    break

        return {
            "seasonStarts": season_starts,
            "seasonNrfiPct": season_pct,
            "locationStarts": loc_starts,
            "locationNrfiPct": loc_pct,
            "last10Starts": l10_starts,
            "last10NrfiPct": l10_pct,
            "streak": {"type": streak_type, "count": streak_count}
        }

    async def fetch_all_trends_async(self, client: httpx.AsyncClient) -> dict:
        trends_master_db = {}
        try:
            # 1. Asenkron Paralel İstek (Performans kaybını önler)
            matchups_task = client.get(f"{self.base_url}/", headers=self.headers, follow_redirects=True, timeout=15.0)
            teams_task = client.get(f"{self.base_url}/teams", headers=self.headers, follow_redirects=True, timeout=15.0)
            
            matchups_response, teams_response = await asyncio.gather(matchups_task, teams_task)
            
            matchups_response.raise_for_status()
            teams_response.raise_for_status()

            def safe_float(val, default=50.0):
                try: return float(val) if val is not None else default
                except (ValueError, TypeError): return default

            def safe_int(val, default=0):
                try: return int(val) if val is not None else default
                except (ValueError, TypeError): return default

            # --- 2. Takım Verilerini Parse Etme ve Gruplama (Teams Page) ---
            team_logs_db = {}
            clean_teams_html = teams_response.text.replace('\\"', '"')
            
            # gameRows array'ini yakalıyoruz
            game_rows_match = re.search(r'"gameRows":(\[.*?\]),"splitBuckets"', clean_teams_html) 
            
            if game_rows_match:
                game_rows = json.loads(game_rows_match.group(1))
                # Her takımın maçlarını listesinde grupluyoruz
                for row in game_rows:
                    t_name = row.get("team", "").strip().lower()
                    if t_name not in team_logs_db:
                        team_logs_db[t_name] = []
                    team_logs_db[t_name].append(row)
                
                # Her takımın maçlarını tarihe göre yeniden eskiye (descending) sıralıyoruz
                for t_name in team_logs_db:
                    team_logs_db[t_name].sort(key=lambda x: x.get("officialDate", ""), reverse=True)

            # --- 3. Matchup Verilerini Parse Etme (Main Page) ---
            clean_matchups_html = matchups_response.text.replace('\\"', '"')
            match = re.search(r'"initialMatchups":(\[.*?\]),"initialThresholds"', clean_matchups_html)

            if not match:
                return trends_master_db

            data = json.loads(match.group(1))

            for game in data:
                away_data = game.get('away') or {}
                home_data = game.get('home') or {}
                
                t_away = (away_data.get('teamName', '') or '').strip()
                t_home = (home_data.get('teamName', '') or '').strip()
                
                if not t_away or not t_home:
                    continue
                
                match_key = f"{t_away}-{t_home}".lower()

                pitchers = {
                    "away_pitcher": away_data.get('pitcher') or {}, 
                    "home_pitcher": home_data.get('pitcher') or {}
                }
                
                # Takım verilerini ham loglardan dinamik olarak hesaplıyoruz
                teams_raw = {
                    "away_team_nrfi": self._calc_team_stats(team_logs_db.get(t_away.lower(), []), "away"),
                    "home_team_nrfi": self._calc_team_stats(team_logs_db.get(t_home.lower(), []), "home")
                }

                trends_master_db[match_key] = {"is_scraper_fallback": False}

                # Helper fonksiyonu: Hem pitcher hem de takım verilerini aynı formata sokar
                def process_stats(stats_dict):
                    stats_dict = stats_dict or {}
                    s_starts = safe_int(stats_dict.get('seasonStarts'))
                    s_pct = safe_float(stats_dict.get('seasonNrfiPct'))
                    l_starts = safe_int(stats_dict.get('locationStarts'))
                    l_pct = safe_float(stats_dict.get('locationNrfiPct'))
                    l10_starts = safe_int(stats_dict.get('last10Starts'))
                    l10_pct = safe_float(stats_dict.get('last10NrfiPct'))
                    
                    streak_raw = stats_dict.get('streak') or {}
                    streak_count = safe_int(streak_raw.get('count'))
                    streak_type = streak_raw.get('type', '')
                    streak_score = streak_count if streak_type == 'nrfi' else -streak_count

                    return {
                        "season_record": self._calculate_record(s_starts, s_pct),
                        "season_nrfi_pct": round(s_pct, 1),
                        "location_record": self._calculate_record(l_starts, l_pct),
                        "location_nrfi_pct": round(l_pct, 1),
                        "last10_record": self._calculate_record(l10_starts, l10_pct),
                        "last10_nrfi_pct": round(l10_pct, 1),
                        "streak_score": streak_score,
                        "streak_emoji": self._get_streak_emoji(streak_type, streak_count)
                    }

                # Pitcher verilerini kaydet
                for side, pitcher_data in pitchers.items():
                    pitcher_dict = pitcher_data or {}
                    trends_master_db[match_key][side] = process_stats(pitcher_dict.get('stats'))

                # Takım verilerini kaydet (Yeni Eklenti)
                for side, t_stats in teams_raw.items():
                    trends_master_db[match_key][side] = process_stats(t_stats)

            return trends_master_db
        except Exception as e:
            print(f"❌ [OddlySpecificStats] Scraper hatası: {e}")
            return trends_master_db