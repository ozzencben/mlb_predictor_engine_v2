import asyncio
import json
import os
import tempfile
import requests

import httpx
from app.core.config import settings


class OddsProvider:
    """
    The Odds API'den canlı oranları çeker, takımları eşleştirir ve
    modelimiz için "The Edge" (Değer/Avantaj) hesaplaması yapar.
    Tyler'ın güvendiği belirli bahis sitelerini filtreler, F5 ve NRFI marketlerini çeker.
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.ODDS_API_KEY

        if not self.api_key:
            print("❌ HATA: ODDS_API_KEY bulunamadı! Lütfen .env dosyasını kontrol edin.")

        self.base_url = "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds"
        self.data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        os.makedirs(self.data_dir, exist_ok=True)

        mapping_file = os.path.join(self.data_dir, "team_mappings.json")
        try:
            with open(mapping_file, "r", encoding="utf-8") as f:
                mappings = json.load(f)
                self.mlb_to_tr_map = mappings.get("mlb_to_tr", {})
        except FileNotFoundError:
            print("⚠️ Uyarı: team_mappings.json bulunamadı.")
            self.mlb_to_tr_map = {}

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

    def fetch_live_odds(self, regions="us", markets="h2h,totals,h2h_h1,totals_1st_inning", bookmakers="fanduel,draftkings,caesars,betmgm,fanatics,pointsbetus") -> list:
        """API'den Tyler'ın Bookie filtreleriyle birlikte taze oranları çeker."""
        if not self.api_key:
            return []

        print("💰 The Odds API'den filtrelenmiş oranlar (ML, F5, NRFI/YRFI) çekiliyor...")

        params = {
            "apiKey": self.api_key,
            "regions": regions,
            "markets": markets,
            "bookmakers": bookmakers, # Sadece seçili Bookieler (Bandwidth Optimizasyonu)
            "oddsFormat": "decimal",
        }

        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            odds_data = response.json()

            if not odds_data:
                print("ℹ️ Şu an için The Odds API'den veri dönmedi (Maç yok veya Piyasalar kapalı).")
                return []

            output_path = os.path.join(self.data_dir, "live_odds.json")
            self._atomic_save(output_path, odds_data)

            print(f"✅ Başarılı! {len(odds_data)} maçın güncel/filtrelenmiş oranları live_odds.json dosyasına yazıldı.")
            return odds_data

        except httpx.HTTPStatusError as e:
            print(f"❌ Oranlar HTTP Hatası ({e.response.status_code}): {e.response.text}")
            return []
        except requests.RequestException as e:
            error_type = type(e).__name__
            print(f"❌ Oranlar Ağ Hatası [{error_type}]: Detay: {str(e)}")
            return []
        except Exception as e:
            error_type = type(e).__name__
            print(f"❌ Oranlar Beklenmeyen Hata [{error_type}]: {e}")
            return []

    async def fetch_live_odds_async(self, client: httpx.AsyncClient, regions="us", markets="h2h,totals,h2h_h1,totals_1st_inning", bookmakers="fanduel,draftkings,caesars,betmgm,fanatics,pointsbetus") -> list:
        """API'den taze oranları asenkron olarak çeker, atomik kaydeder."""
        if not self.api_key:
            return []

        print("💰 The Odds API'den filtrelenmiş oranlar (ML, F5, NRFI) çekiliyor... (Async)")

        params = {
            "apiKey": self.api_key,
            "regions": regions,
            "markets": markets,
            "bookmakers": bookmakers,
            "oddsFormat": "decimal",
        }

        try:
            response = await client.get(self.base_url, params=params, timeout=10.0)
            response.raise_for_status()
            odds_data = response.json()

            if not odds_data:
                print("ℹ️ Şu an için The Odds API'den veri dönmedi (Maç yok veya Piyasalar kapalı).")
                return []

            output_path = os.path.join(self.data_dir, "live_odds.json")
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._atomic_save, output_path, odds_data)

            return odds_data

        except httpx.HTTPStatusError as e:
            print(f"❌ Oranlar HTTP Hatası ({e.response.status_code}): {e.response.text}")
            return []
        except httpx.RequestError as e:
            error_type = type(e).__name__
            req_url = e.request.url if hasattr(e, "request") else "URL Yok"
            print(f"❌ Oranlar Ağ Hatası [{error_type}]: {req_url} -> Detay: {str(e)}")
            return []
        except Exception as e:
            error_type = type(e).__name__
            print(f"❌ Oranlar Beklenmeyen Hata [{error_type}]: {e}")
            return []

    def get_best_odds_for_game(self, away_team_tr: str, home_team_tr: str, odds_data: list) -> dict:
        """
        Piyasadaki (Filtrelenmiş Bookieler arasından) en yüksek oranları bulur.
        Dönen Veri: Match ML, F5 ML, NRFI/YRFI ve Book O/U.
        """
        result = {
            "away_odds": 0.0, "home_odds": 0.0, "over_under": 0.0,
            "f5_away_odds": 0.0, "f5_home_odds": 0.0,
            "nrfi_odds": 0.0, "yrfi_odds": 0.0
        }

        if not odds_data:
            return result

        for game in odds_data:
            api_away_tr = self.mlb_to_tr_map.get(game["away_team"], game["away_team"])
            api_home_tr = self.mlb_to_tr_map.get(game["home_team"], game["home_team"])

            if api_away_tr == away_team_tr and api_home_tr == home_team_tr:
                bookmakers = game.get("bookmakers", [])

                for bookie in bookmakers:
                    for market in bookie.get("markets", []):
                        market_key = market["key"]

                        # 1. Full Game ML (Maç Sonu Taraf)
                        if market_key == "h2h":
                            for outcome in market["outcomes"]:
                                outcome_name_tr = self.mlb_to_tr_map.get(outcome["name"], outcome["name"])
                                price = float(outcome.get("price", 0))

                                if outcome_name_tr == away_team_tr and price > result["away_odds"]:
                                    result["away_odds"] = price
                                elif outcome_name_tr == home_team_tr and price > result["home_odds"]:
                                    result["home_odds"] = price

                        # 2. Full Game Alt/Üst (Sadece ana baremi alır)
                        elif market_key == "totals" and result["over_under"] == 0.0:
                            for outcome in market["outcomes"]:
                                if "point" in outcome:
                                    result["over_under"] = float(outcome["point"])
                                    break 

                        # 3. F5 ML (İlk Yarı Taraf)
                        elif market_key == "h2h_h1":
                            for outcome in market["outcomes"]:
                                outcome_name_tr = self.mlb_to_tr_map.get(outcome["name"], outcome["name"])
                                price = float(outcome.get("price", 0))

                                if outcome_name_tr == away_team_tr and price > result["f5_away_odds"]:
                                    result["f5_away_odds"] = price
                                elif outcome_name_tr == home_team_tr and price > result["f5_home_odds"]:
                                    result["f5_home_odds"] = price

                        # 4. NRFI / YRFI (İlk İning 0.5 Alt/Üst)
                        elif market_key == "totals_1st_inning":
                            for outcome in market["outcomes"]:
                                # Sadece 0.5 baremini yakalıyoruz (İlk ining sayısı)
                                if outcome.get("point") == 0.5:
                                    price = float(outcome.get("price", 0))
                                    if outcome["name"] == "Over" and price > result["yrfi_odds"]:
                                        result["yrfi_odds"] = price
                                    elif outcome["name"] == "Under" and price > result["nrfi_odds"]:
                                        result["nrfi_odds"] = price

                # Hedef maçı bulduğumuz için diğer maçlara bakmaya gerek yok
                break

        return result

    def convert_decimal_to_prob(self, decimal_odds: float) -> float:
        if decimal_odds <= 1.0:
            return 0.0
        return round(1.0 / decimal_odds, 3)

    def calculate_edge(self, model_prob: float, market_odds: float) -> float:
        market_prob = self.convert_decimal_to_prob(market_odds)
        if market_prob == 0.0:
            return 0.0
        return round(model_prob - market_prob, 3)