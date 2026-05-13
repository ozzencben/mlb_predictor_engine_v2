import json
import os
from app.services.mlb_unified_engine import MLBUnifiedEngine
from app.services.odds_provider import OddsProvider
from app.services.data_collector import DataCollector
from app.services.matchup_scraper import MatchupScraper
from app.services.pitcher_scraper import PitcherScraper
from app.services.weather_scraper import WeatherScraper

class PredictionRunner:
    """
    Sistemin ana şalteri.
    Tüm scraper'ları sırayla çalıştırır, ardından MLBUnifiedEngine ile tahminleri üretir.
    """
    def __init__(self):
        self.data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data'))
        os.makedirs(self.data_dir, exist_ok=True)
        self.odds_provider = OddsProvider()

    def _load_json(self, filename: str):
        filepath = os.path.join(self.data_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"⚠️ Uyarı: {filename} bulunamadı!")
            return [] if filename == 'live_odds.json' else {}

    def _run_scrapers(self):
        """Tüm veri toplama adımlarını sırayla çalıştırır."""
        print("📡 [1/5] Takım istatistikleri çekiliyor (TeamRankings)...")
        try:
            DataCollector().collect_all_stats()
        except Exception as e:
            print(f"⚠️ DataCollector hatası: {e}")

        print("⚾ [2/5] Günün maçları ve form durumları çekiliyor (MLB API)...")
        try:
            MatchupScraper().fetch_todays_matchups()
        except Exception as e:
            print(f"⚠️ MatchupScraper hatası: {e}")

        print("🎯 [3/5] Gelişmiş Atıcı istatistikleri çekiliyor (MLB API - Statcast)...")
        try:
            PitcherScraper().build_pitcher_library()
        except Exception as e:
            print(f"⚠️ PitcherScraper hatası: {e}")

        print("💰 [4/5] Canlı bahis oranları çekiliyor (The Odds API)...")
        try:
            self.odds_provider.fetch_live_odds()
        except Exception as e:
            print(f"⚠️ OddsProvider hatası: {e}")
            
        print("☁️ [5/5] Stadyum Hava Durumları çekiliyor (Open-Meteo)...")
        try:
            matchups_data = self._load_json('daily_matchups.json')
            WeatherScraper().fetch_todays_weather(matchups_data)
        except Exception as e:
            print(f"⚠️ WeatherScraper hatası: {e}")

    def run_daily_predictions(self):
        print("\n🚀 V8 Tahmin Motoru Başlatılıyor...")

        # 1. Her zaman taze veri topla
        self._run_scrapers()

        # 2. Scraper çıktılarını oku
        team_db = self._load_json('live_stats.json')
        pitcher_db = self._load_json('pitcher_stats.json')
        matchups_data = self._load_json('daily_matchups.json')
        ballpark_db = self._load_json('ballpark_stats.json')
        live_odds_data = self._load_json('live_odds.json')
        weather_db = self._load_json('live_weather.json')

        if not team_db or not pitcher_db or not matchups_data:
            print("❌ Kritik veri dosyaları hâlâ eksik, scraper'lar başarısız olmuş olabilir.")
            return []

        # 3. Orkestra Şefini Uyandır
        engine = MLBUnifiedEngine(team_db=team_db, pitcher_db=pitcher_db, ballpark_db=ballpark_db)

        # 4. Maçları Sırayla İşle
        all_predictions = []
        games = matchups_data.get('games', [])
        
        print(f"\n⚾ Bugünün {len(games)} maçı için EDGE (Avantaj) analizleri yapılıyor...\n")
        print("=" * 75)
        
        for game in games:
            away_team = game['away_team']
            home_team = game['home_team']
            away_pitcher = game['away_pitcher']
            home_pitcher = game['home_pitcher']

            try:
                # Motoru çalıştır (Artık tüm 'game' sözlüğünü içeri atıyoruz)
                prediction = engine.predict_matchup(game)
                
                # Oranları ve Edge'i Hesapla
                best_odds = self.odds_provider.get_best_odds_for_game(away_team, home_team, live_odds_data)
                
                # Olasılıkları Çek
                away_prob = prediction['Full_Game']['full_away_win_prob']
                home_prob = prediction['Full_Game']['full_home_win_prob']
                
                away_edge = self.odds_provider.calculate_edge(away_prob, best_odds['away_odds'])
                home_edge = self.odds_provider.calculate_edge(home_prob, best_odds['home_odds'])
                
                # Frontend için Oranları JSON'a ekle
                prediction['Odds'] = {
                    'best_away_odds': best_odds['away_odds'],
                    'best_home_odds': best_odds['home_odds'],
                    'over_under': best_odds['over_under'],
                    'away_edge_pct': round(away_edge * 100, 1),
                    'home_edge_pct': round(home_edge * 100, 1)
                }
                
                # YENİ: Frontend için Hava Durumunu JSON'a ekle
                weather_info = weather_db.get(home_team, {})
                prediction['Weather'] = weather_info
                
                all_predictions.append(prediction)
                
                # Ekrana VIP Bahisçi Özeti Bas
                f5_data = prediction['F5']
                full_data = prediction['Full_Game']
                nrfi_data = prediction['NRFI']

                print(f"🔹 {away_team} ({away_pitcher}) @ {home_team} ({home_pitcher})")
                print(f"   ➤ F5 (İlk 5): Skor: {f5_data['f5_away_score']} - {f5_data['f5_home_score']}")
                print(f"   ➤ Tam Maç : Skor: {full_data['full_away_score']} - {full_data['full_home_score']} (Total: {full_data['full_total']})")
                
                away_win_pct = int(away_prob * 100)
                home_win_pct = int(home_prob * 100)
                
                # Edge Görselleştirmesi
                away_val_str = f" 🔥 VALUE (+%{round(away_edge*100, 1)})" if away_edge >= 0.05 else ""
                home_val_str = f" 🔥 VALUE (+%{round(home_edge*100, 1)})" if home_edge >= 0.05 else ""
                
                print(f"   ➤ PİYASA  : {away_team} Oran: {best_odds['away_odds']}  |  {home_team} Oran: {best_odds['home_odds']} | O/U: {best_odds['over_under']}")
                print(f"   ➤ MODEL   : {away_team} %{away_win_pct}{away_val_str}  |  %{home_win_pct} {home_team}{home_val_str}")
                print(f"   ➤ NRFI/YRFI: Sistem: [{nrfi_data['pick']}] (Güven: {nrfi_data['confidence']})")
                
                # YENİ: Hava Durumu Çıktısı
                weather_str = f"{weather_info.get('temp_f', 'N/A')}°F, Rüzgar: {weather_info.get('wind_mph', 'N/A')}mph ({weather_info.get('wind_direction', 'N/A')}) - {weather_info.get('condition', 'N/A')}"
                print(f"   ➤ HAVA    : {weather_str}")
                
                # Eğer "Details" içinden value alert geldiyse ekrana bas
                for alert in prediction.get('Details', {}).get('value_alerts', []):
                    print(f"   {alert}")

                print("-" * 75)
                
            except Exception as e:
                import traceback
                print(f"❌ Hata ({away_team} vs {home_team}): {e}")
                traceback.print_exc()

        # 5. Çıktıları API ve Frontend İçin Kaydet
        output_path = os.path.join(self.data_dir, 'todays_predictions.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({
                "date": matchups_data.get('date'), 
                "total_games": len(all_predictions),
                "predictions": all_predictions
            }, f, indent=4, ensure_ascii=False)

        print(f"\n✅ EDGE Analizleri tamamlandı! Tüm veriler 'todays_predictions.json' dosyasına kaydedildi.")
        return all_predictions

if __name__ == "__main__":
    runner = PredictionRunner()
    runner.run_daily_predictions()