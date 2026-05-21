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
    Tyler'ın güvendiği belirli bahis sitelerini filtreler.
    """

    def __init__(self, api_key: str = None):
        self.api_key = api_key or settings.ODDS_API_KEY

        if not self.api_key:
            print("❌ [OddsProvider] HATA: ODDS_API_KEY bulunamadı! Lütfen .env dosyasını kontrol edin.")

        self.base_url = "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds"
        self.data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        os.makedirs(self.data_dir, exist_ok=True)

        mapping_file = os.path.join(self.data_dir, "team_mappings.json")
        try:
            with open(mapping_file, "r", encoding="utf-8") as f:
                mappings = json.load(f)
                self.mlb_to_tr_map = mappings.get("mlb_to_tr", {})
        except FileNotFoundError:
            print("⚠️ [OddsProvider] Uyarı: team_mappings.json bulunamadı.")
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

    def _log_api_error(self, status_code: int, response_text: str):
        """HTTP durum kodlarına göre detaylı ve anlaşılır hata logları basar."""
        print(f"\n❌ [The Odds API] API Hatası Reddedildi! (Durum Kodu: {status_code})")
        if status_code == 422:
            print("⚠️ SEBEP (422): API abonelik planınız bu marketleri desteklemiyor.")
            print("💡 ÇÖZÜM: 'h2h_h1' (F5) veya 'totals_1st_1_innings' (NRFI) marketlerini çekmek için The Odds API planınızı yükseltmeniz gerekmektedir.")
        elif status_code == 429:
            print("⚠️ SEBEP (429): API İstek Limitiniz (Kota) Doldu!")
            print("💡 ÇÖZÜM: Ücretsiz deneme limitini aştınız. Geliştirme aşamasındaki yoğun testler sebebiyle kota doldu, yarın sıfırlanacaktır.")
        elif status_code == 401:
            print("⚠️ SEBEP (401): API Anahtarı (Key) Geçersiz veya Süresi Dolmuş.")
            print("💡 ÇÖZÜM: Lütfen The Odds API panelinden yeni bir anahtar alıp .env dosyanızı güncelleyin.")
        else:
            print(f"⚠️ DETAY: {response_text}")
        print("-" * 60 + "\n")

    # DİKKAT: 422 Hatasını önlemek için markets="h2h,spreads,totals" olarak güncellendi.
    def fetch_live_odds(self, regions="us", markets="h2h,spreads,totals", bookmakers="fanduel,draftkings,caesars,betmgm,fanatics,pointsbetus") -> list:
        """API'den Tyler'ın Bookie filtreleriyle birlikte taze oranları çeker."""
        if not self.api_key:
            return []

        print("💰 The Odds API'den filtrelenmiş oranlar (ML, Spreads ve Totals) çekiliyor...")

        params = {
            "apiKey": self.api_key,
            "regions": regions,
            "markets": markets,
            "bookmakers": bookmakers,
            "oddsFormat": "decimal",
        }

        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            odds_data = response.json()

            if not odds_data:
                print("ℹ️ [OddsProvider] Şu an için The Odds API'den veri dönmedi (Maç yok veya Piyasalar kapalı).")
                return []

            output_path = os.path.join(self.data_dir, "live_odds.json")
            self._atomic_save(output_path, odds_data)

            print(f"✅ [OddsProvider] Başarılı! {len(odds_data)} maçın güncel/filtrelenmiş oranları kaydedildi.")
            return odds_data

        except requests.exceptions.HTTPError as e:
            self._log_api_error(e.response.status_code, e.response.text)
            return []
        except requests.RequestException as e:
            print(f"❌ [OddsProvider] Ağ Hatası: İnternet bağlantınızı kontrol edin. Detay: {str(e)}")
            return []
        except Exception as e:
            print(f"❌ [OddsProvider] Beklenmeyen Hata: {e}")
            return []

    # DİKKAT: 422 Hatasını önlemek için markets="h2h,spreads,totals" olarak güncellendi.
    async def fetch_live_odds_async(self, client: httpx.AsyncClient, regions="us", markets="h2h,spreads,totals", bookmakers="fanduel,draftkings,caesars,betmgm,fanatics,pointsbetus") -> list:
        """API'den taze oranları asenkron olarak çeker, atomik kaydeder."""
        if not self.api_key:
            return []

        print("💰 The Odds API'den filtrelenmiş oranlar (ML, Spreads ve Totals) çekiliyor... (Async)")

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
                print("ℹ️ [OddsProvider] Şu an için The Odds API'den veri dönmedi.")
                return []

            output_path = os.path.join(self.data_dir, "live_odds.json")
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._atomic_save, output_path, odds_data)

            return odds_data

        except httpx.HTTPStatusError as e:
            self._log_api_error(e.response.status_code, e.response.text)
            return []
        except httpx.RequestError as e:
            req_url = e.request.url if hasattr(e, "request") else "URL Yok"
            print(f"❌ [OddsProvider] Ağ Hatası: {req_url} -> Detay: {str(e)}")
            return []
        except Exception as e:
            print(f"❌ [OddsProvider] Beklenmeyen Hata: {e}")
            return []

    def get_best_odds_for_game(self, away_team_tr: str, home_team_tr: str, odds_data: list) -> dict:
        """
        Piyasadaki (Filtrelenmiş Bookieler arasından) en yüksek oranları bulur.
        Dönen Veri: Match ML, F5 ML, NRFI/YRFI, Book O/U, Spread bilgisi ve detaylı 3-column bahis tablosu verisi.
        """
        result = {
            "away_odds": 0.0, "home_odds": 0.0, "over_under": 0.0,
            "f5_away_odds": 0.0, "f5_home_odds": 0.0,
            "nrfi_odds": 0.0, "yrfi_odds": 0.0,
            "away_book": "", "home_book": "",
            "f5_away_book": "", "f5_home_book": "",
            "nrfi_book": "", "yrfi_book": "",
            "bookmakers": []
        }

        if not odds_data:
            return result

        for game in odds_data:
            api_away_tr = self.mlb_to_tr_map.get(game["away_team"], game["away_team"])
            api_home_tr = self.mlb_to_tr_map.get(game["home_team"], game["home_team"])

            if api_away_tr == away_team_tr and api_home_tr == home_team_tr:
                bookmakers = game.get("bookmakers", [])
                bookmaker_lines = []

                for bookie in bookmakers:
                    bookie_title = bookie.get("title", bookie.get("key", ""))
                    
                    away_ml = None
                    home_ml = None
                    away_spread = None
                    away_spread_price = None
                    home_spread = None
                    home_spread_price = None
                    total_line = None
                    over_price = None
                    under_price = None

                    for market in bookie.get("markets", []):
                        market_key = market["key"]

                        if market_key == "h2h":
                            for outcome in market["outcomes"]:
                                outcome_name_tr = self.mlb_to_tr_map.get(outcome["name"], outcome["name"])
                                price = float(outcome.get("price", 0))

                                if outcome_name_tr == away_team_tr:
                                    away_ml = price
                                    if price > result["away_odds"]:
                                        result["away_odds"] = price
                                        result["away_book"] = bookie_title
                                elif outcome_name_tr == home_team_tr:
                                    home_ml = price
                                    if price > result["home_odds"]:
                                        result["home_odds"] = price
                                        result["home_book"] = bookie_title

                        elif market_key == "totals":
                            for outcome in market["outcomes"]:
                                price = float(outcome.get("price", 0))
                                point = float(outcome.get("point", 0))
                                total_line = point
                                if result["over_under"] == 0.0:
                                    result["over_under"] = point
                                
                                if outcome["name"] == "Over":
                                    over_price = price
                                elif outcome["name"] == "Under":
                                    under_price = price

                        elif market_key == "spreads":
                            for outcome in market["outcomes"]:
                                outcome_name_tr = self.mlb_to_tr_map.get(outcome["name"], outcome["name"])
                                price = float(outcome.get("price", 0))
                                point = float(outcome.get("point", 0))
                                
                                if outcome_name_tr == away_team_tr:
                                    away_spread = point
                                    away_spread_price = price
                                elif outcome_name_tr == home_team_tr:
                                    home_spread = point
                                    home_spread_price = price

                        elif market_key == "h2h_h1":
                            for outcome in market["outcomes"]:
                                outcome_name_tr = self.mlb_to_tr_map.get(outcome["name"], outcome["name"])
                                price = float(outcome.get("price", 0))

                                if outcome_name_tr == away_team_tr and price > result["f5_away_odds"]:
                                    result["f5_away_odds"] = price
                                    result["f5_away_book"] = bookie_title
                                elif outcome_name_tr == home_team_tr and price > result["f5_home_odds"]:
                                    result["f5_home_odds"] = price
                                    result["f5_home_book"] = bookie_title

                        elif market_key == "totals_1st_1_innings":
                            for outcome in market["outcomes"]:
                                if outcome.get("point") == 0.5:
                                    price = float(outcome.get("price", 0))
                                    if outcome["name"] == "Over" and price > result["yrfi_odds"]:
                                        result["yrfi_odds"] = price
                                        result["yrfi_book"] = bookie_title
                                    elif outcome["name"] == "Under" and price > result["nrfi_odds"]:
                                        result["nrfi_odds"] = price
                                        result["nrfi_book"] = bookie_title

                    bookmaker_lines.append({
                        "bookmaker": bookie_title,
                        "away_ml": away_ml,
                        "home_ml": home_ml,
                        "away_spread": away_spread,
                        "away_spread_price": away_spread_price,
                        "home_spread": home_spread,
                        "home_spread_price": home_spread_price,
                        "total_line": total_line,
                        "over_price": over_price,
                        "under_price": under_price
                    })

                result["bookmakers"] = bookmaker_lines
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