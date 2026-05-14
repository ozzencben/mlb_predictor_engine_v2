import json
import os
import tempfile
import traceback
from app.services.mlb_unified_engine import MLBUnifiedEngine, GameInputData # Pydantic importu eklendi
from app.services.odds_provider import OddsProvider
from app.services.data_collector import DataCollector
from app.services.matchup_scraper import MatchupScraper
from app.services.pitcher_scraper import PitcherScraper
from app.services.weather_scraper import WeatherScraper
from pydantic import ValidationError # Hata ayıklama için

class PredictionRunner:
    """
    Sistemin ana şalteri.
    Tüm scraper'ları sırayla çalıştırır, ardından MLBUnifiedEngine ile tahminleri üretir.
    """
    def __init__(self):
        self.data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))
        os.makedirs(self.data_dir, exist_ok=True)
        self.odds_provider = OddsProvider()

    def _atomic_save(self, filepath: str, data: dict):
        """Nihai çıktının bozulmasını önleyen atomik yazma işlemi."""
        dir_name = os.path.dirname(filepath)
        fd, temp_path = tempfile.mkstemp(dir=dir_name, suffix='.json')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            os.replace(temp_path, filepath)
        except Exception as e:
            os.remove(temp_path)
            raise e

    def _load_json(self, filename: str):
        filepath = os.path.join(self.data_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"⚠️ Uyarı: {filename} bulunamadı!")
            return [] if filename == 'live_odds.json' else {}

    def _run_scrapers(self) -> bool:
        """
        Tüm veri toplama adımlarını sırayla çalıştırır.
        Kritik bir adımda hata olursa (örn: Maç listesi çekilemezse) False döner ve süreci iptal eder (Fast Fail).
        """
        print("📡 [1/5] Takım istatistikleri çekiliyor (TeamRankings)...")
        try:
            DataCollector().collect_all_stats()
        except Exception as e:
            print(f"❌ Kritik Hata: DataCollector başarısız oldu. ({e})")
            return False

        print("⚾ [2/5] Günün maçları ve form durumları çekiliyor (MLB API)...")
        try:
            matchups = MatchupScraper().fetch_todays_matchups()
            if not matchups:
                print("ℹ️ Çekilecek maç bulunamadı veya API hatası. İşlem durduruluyor.")
                return False
        except Exception as e:
            print(f"❌ Kritik Hata: MatchupScraper başarısız oldu. ({e})")
            return False

        print("🎯 [3/5] Gelişmiş Atıcı istatistikleri çekiliyor (MLB API - Statcast)...")
        try:
            PitcherScraper().build_pitcher_library()
        except Exception as e:
            print(f"⚠️ Uyarı: PitcherScraper hatası. Lig ortalamaları kullanılacak. ({e})")

        print("💰 [4/5] Canlı bahis oranları çekiliyor (The Odds API)...")
        try:
            self.odds_provider.fetch_live_odds()
        except Exception as e:
            print(f"⚠️ Uyarı: OddsProvider hatası. Oran karşılaştırması atlanacak. ({e})")

        print("☁️ [5/5] Stadyum Hava Durumları çekiliyor (Open-Meteo)...")
        try:
            matchups_data = self._load_json('daily_matchups.json')
            WeatherScraper().fetch_todays_weather(matchups_data)
        except Exception as e:
            print(f"⚠️ Uyarı: WeatherScraper hatası. Standart hava atandı. ({e})")
            
        return True

    def run_daily_predictions(self):
        print("\n🚀 V8 Tahmin Motoru Başlatılıyor...")

        # 1. Scraper'ları çalıştır ve Fast Fail kontrolü yap
        if not self._run_scrapers():
            print("🛑 Zincirleme hata tespit edildi. Tahmin motoru durduruldu.")
            return []

        # 2. Scraper çıktılarını oku
        team_db = self._load_json('live_stats.json')
        pitcher_db = self._load_json('pitcher_stats.json')
        matchups_data = self._load_json('daily_matchups.json')
        ballpark_db = self._load_json('ballpark_stats.json')
        live_odds_data = self._load_json('live_odds.json')
        weather_db = self._load_json('live_weather.json')

        # İkinci bir güvenlik duvarı
        if not team_db or not matchups_data:
            print("❌ Kritik veri dosyaları okunamadı.")
            return []

        # 3. Orkestra Şefini Uyandır
        engine = MLBUnifiedEngine(team_db=team_db, pitcher_db=pitcher_db, ballpark_db=ballpark_db)

        # 4. Maçları Sırayla İşle
        all_predictions = []
        games = matchups_data.get('games', [])
        
        print(f"\n⚾ Bugünün {len(games)} maçı için EDGE (Avantaj) analizleri yapılıyor...\n")
        print("=" * 75)
        
        for game_dict in games:
            try:
                # KRİTİK DÜZELTME: Sözlüğü Pydantic nesnesine dönüştür
                try:
                    game_input = GameInputData(**game_dict)
                except ValidationError as ve:
                    print(f"❌ Veri Formatı Hatası ({game_dict.get('away_team')} vs {game_dict.get('home_team')}): {ve}")
                    continue # Bozuk veri varsa bu maçı atla

                # Pydantic objesini motora gönder
                prediction = engine.predict_matchup(game_input)
                
                away_team = game_input.away_team
                home_team = game_input.home_team
                
                # Oranları ve Edge'i Hesapla
                best_odds = self.odds_provider.get_best_odds_for_game(away_team, home_team, live_odds_data)
                
                away_prob = prediction['Full_Game']['full_away_win_prob']
                home_prob = prediction['Full_Game']['full_home_win_prob']
                
                away_edge = self.odds_provider.calculate_edge(away_prob, best_odds['away_odds'])
                home_edge = self.odds_provider.calculate_edge(home_prob, best_odds['home_odds'])
                
                # Çıktıya metrikleri ekle
                prediction['Odds'] = {
                    'best_away_odds': best_odds['away_odds'],
                    'best_home_odds': best_odds['home_odds'],
                    'over_under': best_odds['over_under'],
                    'away_edge_pct': round(away_edge * 100, 1),
                    'home_edge_pct': round(home_edge * 100, 1)
                }
                
                weather_info = weather_db.get(home_team, {})
                prediction['Weather'] = weather_info
                
                all_predictions.append(prediction)
                
            except Exception as e:
                print(f"❌ Hesaplama Hatası: {e}")
                traceback.print_exc()

        # 5. Çıktıları Atomik Olarak Kaydet
        output_path = os.path.join(self.data_dir, 'todays_predictions.json')
        payload = {
            "date": matchups_data.get('date'), 
            "total_games": len(all_predictions),
            "predictions": all_predictions
        }
        
        # Atomik metodu çağır
        self._atomic_save(output_path, payload)

        print(f"\n✅ EDGE Analizleri tamamlandı! {len(all_predictions)} maç verisi kaydedildi.")
        return all_predictions