import json
import os
from app.services.mlb_unified_engine import MLBUnifiedEngine
from app.services.odds_provider import OddsProvider # YENİ: Oran Sağlayıcımızı import ettik

class PredictionRunner:
    """
    Sistemin ana şalteri.
    Verileri okur, MLBUnifiedEngine'i başlatır, oranları karşılaştırır ve tahminleri üretir.
    """
    def __init__(self):
        self.data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
        self.odds_provider = OddsProvider() # YENİ: Oran motorunu başlattık

    def _load_json(self, filename: str):
        filepath = os.path.join(self.data_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"⚠️ Uyarı: {filename} bulunamadı! (Boş veri ile devam ediliyor)")
            return [] if filename == 'live_odds.json' else {}

    def run_daily_predictions(self):
        print("🚀 Tahmin Motoru Başlatılıyor (Yakıt ve Oranlar Pompalanıyor)...")

        # 1. JSON Verilerini Oku
        team_db = self._load_json('live_stats.json')
        pitcher_db = self._load_json('pitcher_stats.json')
        matchups_data = self._load_json('daily_matchups.json')
        ballpark_db = self._load_json('ballpark_stats.json')
        live_odds_data = self._load_json('live_odds.json') # YENİ: Oranları oku

        if not team_db or not pitcher_db or not matchups_data:
            print("❌ Kritik veri dosyaları eksik! Önce scraper'ları çalıştırın.")
            return []

        # 2. Orkestra Şefini Uyandır
        engine = MLBUnifiedEngine(team_db=team_db, pitcher_db=pitcher_db, ballpark_db=ballpark_db)

        # 3. Maçları Sırayla İşle
        all_predictions = []
        games = matchups_data.get('games', [])
        
        print(f"⚾ Bugünün {len(games)} maçı için EDGE (Avantaj) analizleri yapılıyor...\n")
        print("=" * 75)
        
        for game in games:
            away_team = game['away_team']
            home_team = game['home_team']
            away_pitcher = game['away_pitcher']
            home_pitcher = game['home_pitcher']

            try:
                # Motoru çalıştır (Skorlar ve Olasılıklar)
                prediction = engine.predict_matchup(away_team, home_team, away_pitcher, home_pitcher)
                
                # YENİ: Oranları ve Edge'i Hesapla
                best_odds = self.odds_provider.get_best_odds_for_game(away_team, home_team, live_odds_data)
                
                away_prob = prediction['Full_Game']['full_away_win_prob']
                home_prob = prediction['Full_Game']['full_home_win_prob']
                
                away_edge = self.odds_provider.calculate_edge(away_prob, best_odds['away_odds'])
                home_edge = self.odds_provider.calculate_edge(home_prob, best_odds['home_odds'])
                
                # Frontend için oranları JSON'a ekle
                prediction['Odds'] = {
                    'best_away_odds': best_odds['away_odds'],
                    'best_home_odds': best_odds['home_odds'],
                    'away_edge_pct': round(away_edge * 100, 1),
                    'home_edge_pct': round(home_edge * 100, 1)
                }
                
                all_predictions.append(prediction)
                
                # YENİ: Ekrana VIP Bahisçi Özeti (Edge Dahil) Bas
                print(f"🔹 {away_team} ({away_pitcher}) @ {home_team} ({home_pitcher})")
                print(f"   ➤ F5 (İlk 5): Skor: {prediction['F5']['f5_away_score']} - {prediction['F5']['f5_home_score']}")
                print(f"   ➤ Tam Maç : Skor: {prediction['Full_Game']['full_away_score']} - {prediction['Full_Game']['full_home_score']} (Total: {prediction['Full_Game']['full_total']})")
                
                away_win_pct = int(away_prob * 100)
                home_win_pct = int(home_prob * 100)
                
                # Edge Görselleştirmesi
                away_val_str = f" 🔥 VALUE (+%{round(away_edge*100, 1)})" if away_edge >= 0.05 else ""
                home_val_str = f" 🔥 VALUE (+%{round(home_edge*100, 1)})" if home_edge >= 0.05 else ""
                
                print(f"   ➤ PİYASA  : {away_team} Oran: {best_odds['away_odds']}  |  {home_team} Oran: {best_odds['home_odds']}")
                print(f"   ➤ MODEL   : {away_team} %{away_win_pct}{away_val_str}  |  %{home_win_pct} {home_team}{home_val_str}")
                print(f"   ➤ NRFI/YRFI: Sistem: [{prediction['NRFI']['pick']}] (Güven: {prediction['NRFI']['confidence']})")
                print("-" * 75)
                
            except Exception as e:
                print(f"❌ Hata ({away_team} vs {home_team}): {e}")

        # 4. Çıktıları API ve Frontend İçin Kaydet
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