import asyncio
import json
import os
import tempfile
import unicodedata
from datetime import datetime, timezone
import httpx
from app.core.config import settings

class TennisOddsProvider:
    """
    The Odds API'den ATP ve WTA canlı oranlarını çeker, oyuncuları fuzzy match ile eşleştirir
    ve model tahminleriyle birleştirerek Edge / Kelly Criterion staking hesaplaması yapar.
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.ODDS_API_KEY
        self.data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
        os.makedirs(self.data_dir, exist_ok=True)

        if not self.api_key:
            print("❌ [TennisOddsProvider] HATA: ODDS_API_KEY bulunamadı! Lütfen .env dosyasını kontrol edin.")

    def _normalize_string(self, text: str) -> str:
        """Karakterleri normalize eder, Türkçe/yabancı aksanları temizler, küçük harfe çevirir."""
        if not text:
            return ""
        # Remove accents
        text_nkfd = unicodedata.normalize('NFKD', text)
        text_ascii = text_nkfd.encode('ASCII', 'ignore').decode('utf-8')
        # Clean special chars, keep only letters and spaces
        cleaned = "".join(c for c in text_ascii if c.isalnum() or c.isspace())
        return cleaned.lower().strip()

    def is_name_match(self, api_name: str, flash_name: str) -> bool:
        """
        API ismi (örn: 'Petra Marcinko', 'Novak Djokovic') ile 
        Flashscore ismini (örn: 'Marcinko P.', 'Djokovic N.') karşılaştırır.
        """
        api_norm = self._normalize_string(api_name)
        flash_norm = self._normalize_string(flash_name)

        if not api_norm or not flash_norm:
            return False

        # Flashscore formatı genelde "soyadı ön_isim_baş_harfi" (örn: "marcinko p")
        flash_tokens = flash_norm.split()
        if not flash_tokens:
            return False

        # Son token baş harf mi kontrolü (örn: "p", "j", "n")
        # Genelde 1 veya 2 harfli olur
        has_initial = False
        initial = ""
        surname_tokens = flash_tokens
        
        if len(flash_tokens) > 1 and len(flash_tokens[-1]) <= 2:
            has_initial = True
            initial = flash_tokens[-1]
            surname_tokens = flash_tokens[:-1]

        flash_surname = " ".join(surname_tokens)
        api_tokens = api_norm.split()
        if not api_tokens:
            return False

        # API formatı genelde "Ön_isim Soyad" veya "Ön_isim İkinci_ön_isim Soyad"
        # API isminde, Flashscore soyadının geçip geçmediğini kontrol et
        # Ayrıca API ilk isminin baş harfinin Flashscore initial ile uyumunu kontrol et
        surname_match = False
        if flash_surname in api_norm:
            surname_match = True
        else:
            # Token bazlı kontrol (soyadının kelimeleri API isminde var mı)
            surname_match = all(st in api_tokens for st in surname_tokens)

        if not surname_match:
            return False

        # Eğer Flashscore'da baş harf varsa, API ilk isminin (api_tokens[0]) baş harfiyle eşleşmeli
        if has_initial:
            api_first_name = api_tokens[0]
            if not api_first_name.startswith(initial[0]):
                return False

        return True

    def _atomic_save(self, filepath: str, data: list):
        """Dosya kilitleme ve bozulmaları önleyen atomik yazma işlemi."""
        dir_name = os.path.dirname(filepath)
        fd, temp_path = tempfile.mkstemp(dir=dir_name, suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            os.replace(temp_path, filepath)
        except Exception as e:
            os.remove(temp_path)
            raise e

    async def fetch_live_tennis_odds_async(self, client: httpx.AsyncClient) -> list:
        """The Odds API'den ATP ve WTA maçlarının oranlarını dinamik olarak çeker, birleştirir ve kaydeder."""
        if not self.api_key:
            return []

        print("💰 [TennisOddsProvider] Aktif tenis turnuva anahtarları sorgulanıyor...")
        
        # 1. Aktif sporları çek
        sports_url = "https://api.the-odds-api.com/v4/sports"
        sport_keys = []
        try:
            resp = await client.get(sports_url, params={"apiKey": self.api_key}, timeout=10.0)
            if resp.status_code == 200:
                sports = resp.json()
                sport_keys = [
                    s["key"] for s in sports 
                    if s.get("active") and (s["key"].startswith("tennis_atp") or s["key"].startswith("tennis_wta"))
                ]
                print(f"🎾 [TennisOddsProvider] Aktif tenis spor anahtarları bulundu: {sport_keys}")
            else:
                print(f"⚠️ [TennisOddsProvider] Spor listesi alınamadı: {resp.status_code}")
                return []
        except Exception as e:
            print(f"❌ [TennisOddsProvider] Spor listesi çekilirken hata: {e}")
            return []

        if not sport_keys:
            print("ℹ️ [TennisOddsProvider] Şu an aktif tenis turnuvası bulunamadı.")
            return []

        regions = "us,eu"
        markets = "h2h"
        bookmakers = "fanduel,draftkings,caesars,betmgm,betrivers,bovada,pinnacle"

        params = {
            "apiKey": self.api_key,
            "regions": regions,
            "markets": markets,
            "bookmakers": bookmakers,
            "oddsFormat": "decimal",
        }

        # 2. Aktif turnuvaların oranlarını asenkron ve paralel olarak çek
        tasks = []
        for key in sport_keys:
            url = f"https://api.the-odds-api.com/v4/sports/{key}/odds"
            tasks.append(client.get(url, params=params, timeout=12.0))

        combined_odds = []
        try:
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            for key, resp in zip(sport_keys, responses):
                if isinstance(resp, Exception):
                    print(f"❌ [TennisOddsProvider] {key} oranı çekilirken hata oluştu: {resp}")
                elif resp.status_code == 200:
                    data = resp.json()
                    combined_odds.extend(data)
                    print(f"🎾 [TennisOddsProvider] {key} turnuvasından {len(data)} maçın oranı çekildi.")
                else:
                    print(f"⚠️ [TennisOddsProvider] {key} API Hatası: {resp.status_code}")
        except Exception as e:
            print(f"❌ [TennisOddsProvider] İstekler paralel yürütülürken hata: {e}")

        # Atomik olarak diske kaydet
        if combined_odds:
            output_path = os.path.join(self.data_dir, "live_odds_tennis.json")
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._atomic_save, output_path, combined_odds)
            print(f"✅ [TennisOddsProvider] Toplam {len(combined_odds)} tenis maçının güncel oranları kaydedildi.")
            
        return combined_odds

    def match_odds_for_game(self, p1_name: str, p2_name: str, match_timestamp: int, tennis_odds: list) -> dict:
        """
        Gelen tenis oranları listesinde, Flashscore oyuncuları ve zamanına göre eşleşme arar.
        Zaman penceresi toleransı: +/- 6 saattir (21600 saniye).
        """
        if not tennis_odds:
            return None

        for game in tennis_odds:
            # Commence time'ı parse et (örn: "2026-06-15T10:00:00Z")
            commence_str = game.get("commence_time")
            if not commence_str:
                continue
            
            try:
                # Standard ISO format parsing
                cleaned_str = commence_str.replace("Z", "").split(".")[0]
                dt = datetime.strptime(cleaned_str, "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
                commence_ts = int(dt.timestamp())
            except Exception:
                continue

            # 1. Zaman penceresi kontrolü (+/- 6 saat)
            if abs(match_timestamp - commence_ts) > 6 * 3600:
                continue

            api_home = game.get("home_team", "")
            api_away = game.get("away_team", "")

            # 2. İsim eşleşmesi kontrolü (Normal ve Swapped oyuncu sıralaması için)
            matched = False
            swapped = False

            if self.is_name_match(api_home, p1_name) and self.is_name_match(api_away, p2_name):
                matched = True
            elif self.is_name_match(api_home, p2_name) and self.is_name_match(api_away, p1_name):
                matched = True
                swapped = True

            if matched:
                # Piyasada (bookmaker'lar arasında) sunulan en yüksek oranları bul
                best_home_odds = 0.0
                best_away_odds = 0.0

                for bookie in game.get("bookmakers", []):
                    for market in bookie.get("markets", []):
                        if market.get("key") == "h2h":
                            for outcome in market.get("outcomes", []):
                                price = float(outcome.get("price", 0.0))
                                name = outcome.get("name", "")
                                if name == api_home:
                                    if price > best_home_odds:
                                        best_home_odds = price
                                elif name == api_away:
                                    if price > best_away_odds:
                                        best_away_odds = price

                # Oranlar sıfırdan büyükse
                if best_home_odds > 0.0 and best_away_odds > 0.0:
                    if swapped:
                        return {
                            "p1_odds": best_away_odds,
                            "p2_odds": best_home_odds
                        }
                    else:
                        return {
                            "p1_odds": best_home_odds,
                            "p2_odds": best_away_odds
                        }

        return None
