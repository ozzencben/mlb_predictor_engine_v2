import asyncio
import json
import os
import tempfile
import traceback

import httpx
from pydantic import ValidationError

from app.models.schemas import NRFITrendSchema
from app.services.data_collector import DataCollector
from app.services.matchup_scraper import MatchupScraper
from app.services.mlb_unified_engine import GameInputData, MLBUnifiedEngine
from app.services.oddlyspecific_scraper import OddlySpecificScraper
from app.services.odds_provider import OddsProvider
from app.services.pitcher_scraper import PitcherScraper
from app.services.weather_scraper import WeatherScraper
from app.services.ai.factory import get_ai_predictor


class PredictionRunner:
    """
    Sistemin ana şalteri.
    Tüm scraper'ları sırayla çalıştırır, ardından MLBUnifiedEngine ile tahminleri üretir.
    """

    def __init__(self):
        self.data_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "data")
        )
        os.makedirs(self.data_dir, exist_ok=True)
        self.odds_provider = OddsProvider()
        
        mapping_file = os.path.join(self.data_dir, "team_mappings.json")
        try:
            with open(mapping_file, "r", encoding="utf-8") as f:
                mappings = json.load(f)
                mlb_to_tr = mappings.get("mlb_to_tr", {})
                self.tr_to_mlb_map = {v: k for k, v in mlb_to_tr.items()}
        except FileNotFoundError:
            self.tr_to_mlb_map = {}

    def _atomic_save(self, filepath: str, data: dict):
        """Nihai çıktının bozulmasını önleyen atomik yazma işlemi."""
        dir_name = os.path.dirname(filepath)
        fd, temp_path = tempfile.mkstemp(dir=dir_name, suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            os.replace(temp_path, filepath)
        except Exception as e:
            os.remove(temp_path)
            raise e

    def _load_json(self, filename: str):
        filepath = os.path.join(self.data_dir, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"⚠️ Uyarı: {filename} bulunamadı!")
            return [] if filename == "live_odds.json" else {}

    def _find_trend_data(self, away_team: str, home_team: str, trends_db: dict) -> dict:
        """
        ESPN (Örn: 'Cleveland') ile OddlySpecificStats (Örn: 'Cleveland Guardians') 
        takım isimleri arasındaki uyumsuzluğu çözen akıllı eşleştirici.
        """
        a_team = away_team.lower()
        h_team = home_team.lower()
        full_away = self.tr_to_mlb_map.get(away_team, away_team).lower()
        full_home = self.tr_to_mlb_map.get(home_team, home_team).lower()
        
        # Tam eşleşme kontrolü
        direct_key = f"{full_away}-{full_home}"
        if direct_key in trends_db:
            return trends_db[direct_key]
            
        # Parçalı (Fuzzy) eşleşme kontrolü
        def is_match(short_name, full_name, db_side):
            if short_name in db_side or full_name in db_side:
                return True
            # Oakland -> "athletics" vs "oakland athletics"
            last_word = full_name.split()[-1]
            if last_word in db_side:
                return True
            return False

        for db_key, data in trends_db.items():
            parts = db_key.split('-')
            if len(parts) == 2:
                db_a, db_h = parts
                if is_match(a_team, full_away, db_a) and is_match(h_team, full_home, db_h):
                    return data
                
        return None

    async def _run_scrapers_async(self, client: httpx.AsyncClient) -> bool:
        """
        Tüm veri toplama adımlarını asenkron pipeline içinde çalıştırır.
        Kritik bir adımda hata olursa False döner ve süreci iptal eder.
        """
        loop = asyncio.get_running_loop()

        print("📡 [1/5] Takım istatistikleri çekiliyor (TeamRankings)...")
        try:
            await loop.run_in_executor(None, DataCollector().collect_all_stats)
        except Exception as e:
            print(f"❌ Kritik Hata: DataCollector başarısız oldu. ({e})")
            return False

        print("⚾ [2/5] Günün maçları ve form durumları çekiliyor (MLB API)...")
        try:
            matchups = await loop.run_in_executor(
                None, MatchupScraper().fetch_todays_matchups
            )
            if not matchups:
                print("ℹ️ Çekilecek maç bulunamadı veya API hatası. İşlem durduruluyor.")
                return False
        except Exception as e:
            print(f"❌ Kritik Hata: MatchupScraper başarısız oldu. ({e})")
            return False

        print("🎯 [3/5] Gelişmiş Atıcı istatistikleri çekiliyor (MLB API - Statcast)...")
        pitcher_task = asyncio.create_task(
            PitcherScraper().build_pitcher_library_async(client)
        )

        print("💰 [4/5] Canlı bahis oranları çekiliyor (The Odds API)...")
        odds_task = asyncio.create_task(
            self.odds_provider.fetch_live_odds_async(client)
        )

        print("☁️ [5/5] Stadyum Hava Durumları çekiliyor (Open-Meteo)...")
        weather_task = asyncio.create_task(
            WeatherScraper().fetch_todays_weather_async(client, matchups)
        )

        print("📈 [6/6] NRFI Trendleri çekiliyor (OddlySpecificStats)...")
        trends_task = asyncio.create_task(
            OddlySpecificScraper().fetch_all_trends_async(client)
        )

        results = await asyncio.gather(
            pitcher_task, odds_task, weather_task, trends_task, return_exceptions=True
        )

        if isinstance(results[0], Exception):
            print(f"⚠️ Uyarı: PitcherScraper hatası. Lig ortalamaları kullanılacak. ({results[0]})")
            
        if isinstance(results[1], Exception):
            print(f"⚠️ Uyarı: OddsProvider hatası. Oran karşılaştırması atlanacak. ({results[1]})")
            
        if isinstance(results[2], Exception):
            print(f"⚠️ Uyarı: WeatherScraper hatası. Standart hava atandı. ({results[2]})")
            
        if not isinstance(results[3], Exception):
            self._atomic_save(os.path.join(self.data_dir, "nrfi_trends.json"), results[3])
        else:
            print(f"⚠️ Uyarı: OddlySpecificScraper hatası. ({results[3]})")
            self._atomic_save(os.path.join(self.data_dir, "nrfi_trends.json"), {})

        return True

    async def run_daily_predictions_async(self):
        print("\n🚀 V8 Tahmin Motoru Başlatılıyor...")
        
        # 1. AI Servisini başlat
        ai_service = get_ai_predictor()

        async with httpx.AsyncClient() as client:
            if not await self._run_scrapers_async(client):
                print("🛑 Zincirleme hata tespit edildi. Tahmin motoru durduruldu.")
                return []

        team_db = self._load_json("live_stats.json")
        pitcher_db = self._load_json("pitcher_stats.json")
        matchups_data = self._load_json("daily_matchups.json")
        ballpark_db = self._load_json("ballpark_stats.json")
        live_odds_data = self._load_json("live_odds.json")
        weather_db = self._load_json("live_weather.json")
        trends_db = self._load_json("nrfi_trends.json")

        if not team_db or not matchups_data:
            print("❌ Kritik veri dosyaları okunamadı.")
            return []

        engine = MLBUnifiedEngine(
            team_db=team_db, pitcher_db=pitcher_db, ballpark_db=ballpark_db
        )

        all_predictions = []
        games = matchups_data.get("games", [])

        print(f"\n⚾ Bugünün {len(games)} maçı için EDGE (Avantaj) analizleri yapılıyor...\n")
        print("=" * 75)

        for game_dict in games:
            try:
                try:
                    game_input = GameInputData(**game_dict)
                except ValidationError as ve:
                    print(f"❌ Veri Formatı Hatası ({game_dict.get('away_team')} vs {game_dict.get('home_team')}): {ve}")
                    continue

                # TAKIM İSMİ UYUMSUZLUĞU (FUZZY MATCH) ÇÖZÜMÜ
                trend_data = self._find_trend_data(game_input.away_team, game_input.home_team, trends_db)
                
                if trend_data:
                    trends_schema = NRFITrendSchema(**trend_data)
                else:
                    trends_schema = NRFITrendSchema(is_scraper_fallback=True)

                prediction = engine.predict_matchup(game_input, trends=trends_schema)

                away_team = game_input.away_team
                home_team = game_input.home_team

                best_odds = self.odds_provider.get_best_odds_for_game(
                    away_team, home_team, live_odds_data
                )

                away_prob = prediction["Full_Game"]["full_away_win_prob"]
                home_prob = prediction["Full_Game"]["full_home_win_prob"]

                f5_away_prob = prediction["F5"]["f5_away_win_prob"]
                f5_home_prob = prediction["F5"]["f5_home_win_prob"]

                nrfi_prob = prediction["NRFI"]["nrfi_score"]
                yrfi_prob = prediction["NRFI"]["yrfi_score"]

                away_edge = self.odds_provider.calculate_edge(away_prob, best_odds["away_odds"])
                home_edge = self.odds_provider.calculate_edge(home_prob, best_odds["home_odds"])

                f5_away_edge = self.odds_provider.calculate_edge(f5_away_prob, best_odds["f5_away_odds"])
                f5_home_edge = self.odds_provider.calculate_edge(f5_home_prob, best_odds["f5_home_odds"])

                nrfi_edge = self.odds_provider.calculate_edge(nrfi_prob, best_odds["nrfi_odds"])
                yrfi_edge = self.odds_provider.calculate_edge(yrfi_prob, best_odds["yrfi_odds"])

                prediction["Odds"] = {
                    "best_away_odds": best_odds["away_odds"],
                    "best_home_odds": best_odds["home_odds"],
                    "over_under": best_odds["over_under"],
                    "away_edge_pct": round(away_edge * 100, 1),
                    "home_edge_pct": round(home_edge * 100, 1),
                    
                    "f5_away_odds": best_odds["f5_away_odds"],
                    "f5_home_odds": best_odds["f5_home_odds"],
                    "f5_away_edge_pct": round(f5_away_edge * 100, 1),
                    "f5_home_edge_pct": round(f5_home_edge * 100, 1),
                    
                    "nrfi_odds": best_odds["nrfi_odds"],
                    "yrfi_odds": best_odds["yrfi_odds"],
                    "nrfi_edge_pct": round(nrfi_edge * 100, 1),
                    "yrfi_edge_pct": round(yrfi_edge * 100, 1),
                }

                weather_info = weather_db.get(home_team, {})
                prediction["Weather"] = weather_info
                
                # 2. AI asenkron döngüsünden önce None ataması yap
                if "Details" not in prediction:
                    prediction["Details"] = {}
                prediction["Details"]["ai_insight"] = None

                all_predictions.append(prediction)

            except Exception as e:
                print(f"❌ Hesaplama Hatası: {e}")
                traceback.print_exc()

        # 3 & 4. AI verilerini SIRALI (Sequential) çekme - Free Tier Koruması
        print("\n🤖 Maçlar için AI analizleri üretiliyor (Rate Limit Korumalı)...")
        
        for pred in all_predictions:
            away = pred['matchup']['away_team']
            home = pred['matchup']['home_team']
            print(f"   ➤ Processing AI for: {away} vs {home}")
            try:
                insight = await ai_service.generate_insight_async(pred)
                pred["Details"]["ai_insight"] = insight
            except Exception as e:
                print(f"❌ AI Insight Hatası ({away} @ {home}): {e}")
                pred["Details"]["ai_insight"] = "AI analysis is temporarily unavailable."
            finally:
                # Gemini Free Tier (15 RPM) limiti için her maç arası kesin olarak 4.5 saniye bekle
                # Bu sayede 1 dakika içinde atılan istek sayısı 13-14 civarında kalır, 429 yemez.
                await asyncio.sleep(4.5)

        print("✅ Tüm AI analizleri tamamlandı.")

        output_path = os.path.join(self.data_dir, "todays_predictions.json")
        payload = {
            "date": matchups_data.get("date"),
            "total_games": len(all_predictions),
            "predictions": all_predictions,
        }

        self._atomic_save(output_path, payload)

        print(f"\n✅ EDGE Analizleri tamamlandı! {len(all_predictions)} maç verisi kaydedildi.")
        return all_predictions

    def run_daily_predictions(self):
        """Senkron tetikleyiciler için asenkron metodun sarmalayıcısı."""
        return asyncio.run(self.run_daily_predictions_async())