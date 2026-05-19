import re
import json
import httpx

class OddlySpecificScraper:
    def __init__(self):
        self.url = "https://www.oddlyspecificstats.com/"
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

    async def fetch_all_trends_async(self, client: httpx.AsyncClient) -> dict:
        trends_master_db = {}
        try:
            response = await client.get(self.url, headers=self.headers, follow_redirects=True, timeout=15.0)
            response.raise_for_status()

            clean_html = response.text.replace('\\"', '"')
            match = re.search(r'"initialMatchups":(\[.*?\]),"initialThresholds"', clean_html)

            if not match:
                return trends_master_db

            data = json.loads(match.group(1))

            def safe_float(val, default=50.0):
                try: return float(val) if val is not None else default
                except (ValueError, TypeError): return default

            def safe_int(val, default=0):
                try: return int(val) if val is not None else default
                except (ValueError, TypeError): return default

            for game in data:
                t_away = (game.get('away', {}).get('teamName', '') or '').strip()
                t_home = (game.get('home', {}).get('teamName', '') or '').strip()
                
                if not t_away or not t_home:
                    continue
                
                match_key = f"{t_away}-{t_home}".lower()

                # Kod Tekrarını Önlemek (DRY) İçin Dictionary Mapping
                pitchers = {
                    "away_pitcher": game.get('away', {}).get('pitcher', {}), 
                    "home_pitcher": game.get('home', {}).get('pitcher', {})
                }

                trends_master_db[match_key] = {"is_scraper_fallback": False}

                for side, pitcher_data in pitchers.items():
                    stats = pitcher_data.get('stats') or {}
                    
                    s_starts = safe_int(stats.get('seasonStarts'))
                    s_pct = safe_float(stats.get('seasonNrfiPct'))
                    
                    l_starts = safe_int(stats.get('locationStarts'))
                    l_pct = safe_float(stats.get('locationNrfiPct'))
                    
                    l10_starts = safe_int(stats.get('last10Starts'))
                    l10_pct = safe_float(stats.get('last10NrfiPct'))

                    streak_raw = stats.get('streak') or {}
                    streak_count = safe_int(streak_raw.get('count'))
                    streak_type = streak_raw.get('type', '')

                    streak_score = streak_count if streak_type == 'nrfi' else -streak_count

                    trends_master_db[match_key][side] = {
                        "season_record": self._calculate_record(s_starts, s_pct),
                        "season_nrfi_pct": s_pct,
                        "location_record": self._calculate_record(l_starts, l_pct),
                        "location_nrfi_pct": l_pct,
                        "last10_record": self._calculate_record(l10_starts, l10_pct),
                        "last10_nrfi_pct": l10_pct,
                        "streak_score": streak_score,
                        "streak_emoji": self._get_streak_emoji(streak_type, streak_count)
                    }

            return trends_master_db
        except Exception as e:
            print(f"❌ [OddlySpecificStats] Scraper hatası: {e}")
            return trends_master_db