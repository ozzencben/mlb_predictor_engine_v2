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
        odds_data = []
        if self.api_key:
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
                if odds_data:
                    output_path = os.path.join(self.data_dir, "live_odds.json")
                    loop = asyncio.get_running_loop()
                    await loop.run_in_executor(None, self._atomic_save, output_path, odds_data)
            except httpx.HTTPStatusError as e:
                self._log_api_error(e.response.status_code, e.response.text)
            except httpx.RequestError as e:
                req_url = e.request.url if hasattr(e, "request") else "URL Yok"
                print(f"❌ [OddsProvider] Ağ Hatası: {req_url} -> Detay: {str(e)}")
            except Exception as e:
                print(f"❌ [OddsProvider] Beklenmeyen Hata: {e}")

        # 2. HİBRİT ÇİFT-API PARÇASI: Tyler'ın yeni odds-api.io keyi varsa F5 verilerini de çek
        await self.fetch_live_odds_io_async(client, odds_data)

        return odds_data

    async def fetch_live_odds_io_async(self, client: httpx.AsyncClient, main_odds_data: list = None) -> list:
        """
        Tyler'ın odds-api.io API key'ini kullanarak F5 ML ve F5 Totals oranlarını çeker.
        DraftKings ve FanDuel sitelerinden gelen verileri okur ve atomik kaydeder.
        """
        api_key_io = getattr(settings, "ODDS_API_IO_KEY", "")
        if not api_key_io:
            print("ℹ️ [OddsProvider] odds-api.io API key (ODDS_API_IO_KEY) tanımlı değil, F5 oranları atlanıyor.")
            return []

        print("💰 odds-api.io'dan F5 oranları çekiliyor... (DraftKings & FanDuel - Async)")
        base_url_io = "https://api.odds-api.io/v3"
        
        # 1. Fetch upcoming MLB events
        events_url = f"{base_url_io}/events"
        events_params = {
            "apiKey": api_key_io,
            "sport": "baseball",
            "league": "usa-mlb"
        }
        
        try:
            r = await client.get(events_url, params=events_params, timeout=15.0)
            if r.status_code != 200:
                print(f"❌ [OddsProvider] odds-api.io events fetch failed ({r.status_code}): {r.text}")
                return []
            events = r.json()
            if not events:
                return []
                
            pending_events = [e for e in events if e.get("status") == "pending"]
            if not pending_events:
                print("ℹ️ [OddsProvider] odds-api.io'da aktif 'pending' maç bulunamadı.")
                return []

            # 2. Bugünün/yarının maçlarını filtreleyerek kota tüketimini azaltalım
            matching_teams = set()
            if main_odds_data:
                for game in main_odds_data:
                    home = game.get("home_team")
                    away = game.get("away_team")
                    if home:
                        matching_teams.add(home.lower())
                        mapped_home = self.mlb_to_tr_map.get(home, home)
                        matching_teams.add(mapped_home.lower())
                    if away:
                        matching_teams.add(away.lower())
                        mapped_away = self.mlb_to_tr_map.get(away, away)
                        matching_teams.add(mapped_away.lower())

            filtered_events = []
            for event in pending_events:
                home = event.get("home", "")
                away = event.get("away", "")
                
                if matching_teams:
                    if home.lower() not in matching_teams and away.lower() not in matching_teams:
                        continue
                else:
                    # Fallback (Ana API anahtarı boşsa veya hata verdiyse): Tarihe göre filtrele (Gelecek 36 saat ve geçmiş 6 saat arası)
                    from datetime import datetime, timedelta, timezone
                    event_date_str = event.get("date")
                    if event_date_str:
                        try:
                            event_date = datetime.strptime(event_date_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                            now_utc = datetime.now(timezone.utc)
                            if event_date > now_utc + timedelta(hours=36) or event_date < now_utc - timedelta(hours=6):
                                continue
                        except Exception:
                            pass
                filtered_events.append(event)

            print(f"ℹ️ [OddsProvider] Toplam pending maç: {len(pending_events)}, Filtrelenmiş (Bugün/Yarın): {len(filtered_events)}")
            if not filtered_events:
                return []

            consolidated_odds = []
            multi_success = True

            # 3. /odds/multi kullanarak 10'arlı gruplar halinde çekelim (Kota tasarrufu!)
            chunk_size = 10
            event_chunks = [filtered_events[i:i + chunk_size] for i in range(0, len(filtered_events), chunk_size)]
            
            for chunk in event_chunks:
                event_ids = ",".join([e["id"] for e in chunk])
                odds_url = f"{base_url_io}/odds/multi"
                odds_params = {
                    "apiKey": api_key_io,
                    "eventIds": event_ids,
                    "bookmakers": "DraftKings,FanDuel"
                }
                
                try:
                    await asyncio.sleep(0.3)  # short sleep to respect rate limit
                    odds_r = await client.get(odds_url, params=odds_params, timeout=15.0)
                    if odds_r.status_code == 200:
                        odds_data = odds_r.json()
                        if isinstance(odds_data, list):
                            consolidated_odds.extend(odds_data)
                        elif isinstance(odds_data, dict):
                            consolidated_odds.append(odds_data)
                    elif odds_r.status_code == 429:
                        print("⚠️ [OddsProvider] odds-api.io /odds/multi rate limit (429) hit, falling back to individual calls.")
                        multi_success = False
                        break
                    else:
                        print(f"⚠️ [OddsProvider] odds-api.io /odds/multi failed ({odds_r.status_code}): {odds_r.text}")
                        multi_success = False
                except Exception as ex:
                    print(f"⚠️ [OddsProvider] Exception fetching multi odds: {ex}")
                    multi_success = False

            # 4. Fallback: Eğer /odds/multi başarısız olursa veya desteklenmezse bireysel sorgular atalım (max 15 maç)
            if not multi_success and not consolidated_odds:
                print("⚠️ [OddsProvider] Bireysel oran sorgularına geri dönülüyor (maksimum 15 maç)...")
                for event in filtered_events[:15]:
                    event_id = event.get("id")
                    if not event_id:
                        continue
                        
                    odds_url = f"{base_url_io}/odds"
                    odds_params = {
                        "apiKey": api_key_io,
                        "eventId": event_id,
                        "bookmakers": "DraftKings,FanDuel"
                    }
                    
                    try:
                        await asyncio.sleep(0.3)
                        odds_r = await client.get(odds_url, params=odds_params, timeout=10.0)
                        if odds_r.status_code == 200:
                            odds_data = odds_r.json()
                            consolidated_odds.append(odds_data)
                        elif odds_r.status_code == 429:
                            print("⚠️ [OddsProvider] odds-api.io rate limit (429) hit, skipping remaining events.")
                            break
                        else:
                            print(f"⚠️ [OddsProvider] Failed to fetch odds for event {event_id}: {odds_r.text}")
                    except Exception as ex:
                        print(f"⚠️ [OddsProvider] Exception fetching odds for event {event_id}: {ex}")
                        
            if consolidated_odds:
                output_path = os.path.join(self.data_dir, "live_odds_io.json")
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(None, self._atomic_save, output_path, consolidated_odds)
                print(f"✅ [OddsProvider] Başarılı! {len(consolidated_odds)} maçın F5/DraftKings/FanDuel oranları kaydedildi.")
                return consolidated_odds
                
        except Exception as e:
            print(f"❌ [OddsProvider] odds-api.io unexpected error: {e}")
            
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

        # 1. ORİJİNAL KISIM: the-odds-api.com verilerini işle (Eğer varsa)
        if odds_data:
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

        # 2. HİBRİT ÇİFT-API BİRLEŞTİRİCİSİ: odds-api.io verilerini işle (F5 ML, Totals ve Alternatif Oranlar)
        io_path = os.path.join(self.data_dir, "live_odds_io.json")
        if os.path.exists(io_path):
            try:
                with open(io_path, "r", encoding="utf-8") as f:
                    io_odds_data = json.load(f)
                
                for io_game in io_odds_data:
                    io_away = io_game.get("away", "")
                    io_home = io_game.get("home", "")
                    
                    api_away_tr = self.mlb_to_tr_map.get(io_away, io_away)
                    api_home_tr = self.mlb_to_tr_map.get(io_home, io_home)
                    
                    if api_away_tr == away_team_tr and api_home_tr == home_team_tr:
                        io_bookmakers = io_game.get("bookmakers", {})
                        for bookie_name, markets in io_bookmakers.items():
                            
                            # Eşleşen bir bookmaker satırı bul veya oluştur
                            bookie_line = next((b for b in result["bookmakers"] if b["bookmaker"].lower() == bookie_name.lower()), None)
                            if not bookie_line:
                                bookie_line = {
                                    "bookmaker": bookie_name,
                                    "away_ml": None, "home_ml": None,
                                    "away_spread": None, "away_spread_price": None,
                                    "home_spread": None, "home_spread_price": None,
                                    "total_line": None, "over_price": None, "under_price": None
                                }
                                result["bookmakers"].append(bookie_line)

                            for market in markets:
                                m_name = market.get("name", "")
                                odds_list = market.get("odds", [])
                                if not odds_list:
                                    continue
                                
                                # --- F5 Moneyline ---
                                if m_name in ["First 5 Innings ML", "First 5 Innings Moneyline", "ML HT", "1st Half Moneyline"]:
                                    outcome = odds_list[0]
                                    home_price = float(outcome.get("home", 0))
                                    away_price = float(outcome.get("away", 0))
                                    if away_price > result["f5_away_odds"]:
                                        result["f5_away_odds"] = away_price
                                        result["f5_away_book"] = bookie_name
                                    if home_price > result["f5_home_odds"]:
                                        result["f5_home_odds"] = home_price
                                        result["f5_home_book"] = bookie_name

                                # --- Fallback Full Game Moneyline (Eğer the-odds-api key boş/hatalıysa) ---
                                elif m_name in ["ML", "Moneyline", "Head to Head"] and (result["away_odds"] == 0.0 or result["home_odds"] == 0.0):
                                    outcome = odds_list[0]
                                    home_price = float(outcome.get("home", 0))
                                    away_price = float(outcome.get("away", 0))
                                    bookie_line["away_ml"] = away_price
                                    bookie_line["home_ml"] = home_price
                                    if away_price > result["away_odds"]:
                                        result["away_odds"] = away_price
                                        result["away_book"] = bookie_name
                                    if home_price > result["home_odds"]:
                                        result["home_odds"] = home_price
                                        result["home_book"] = bookie_name

                                # --- Fallback Totals (Eğer the-odds-api key boş/hatalıysa) ---
                                elif m_name in ["Totals", "Total Runs", "Over/Under"] and result["over_under"] == 0.0:
                                    outcome = odds_list[0]
                                    point = float(outcome.get("hdp", 0))
                                    over_p = float(outcome.get("over", 0))
                                    under_p = float(outcome.get("under", 0))
                                    bookie_line["total_line"] = point
                                    bookie_line["over_price"] = over_p
                                    bookie_line["under_price"] = under_p
                                    result["over_under"] = point

                                # --- Fallback Spreads (Eğer the-odds-api key boş/hatalıysa) ---
                                elif m_name in ["Spread", "Run Line", "Handicap"] and bookie_line["away_spread"] is None:
                                    outcome = odds_list[0]
                                    hdp = float(outcome.get("hdp", 0))
                                    home_p = float(outcome.get("home", 0))
                                    away_p = float(outcome.get("away", 0))
                                    bookie_line["away_spread"] = hdp
                                    bookie_line["away_spread_price"] = away_p
                                    bookie_line["home_spread"] = -hdp
                                    bookie_line["home_spread_price"] = home_p
            except Exception as e:
                print(f"⚠️ [OddsProvider] Error merging F5 odds from live_odds_io.json: {e}")

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