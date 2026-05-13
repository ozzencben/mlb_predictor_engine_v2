from app.models.f5_model import F5Model
from app.models.mlb_model import MLBModel
from app.models.nrfi_model import NRFIModel

class MLBUnifiedEngine:
    """
    The Orchestrator. 
    Routes live data to specific models (NRFI, F5, MLB), applies safety logic, 
    and returns a unified dictionary ready for the frontend.
    """
    
    def __init__(self, team_db: dict, pitcher_db: dict, ballpark_db: dict = None):
        if ballpark_db is None:
            ballpark_db = {}
            
        # 1. Modelleri Başlat (Instantiation)
        # Bütün o karmaşık veritabanları çöpe gitti. 
        # Modellerimiz artık sadece 2 taze JSON verisiyle (Team ve Pitcher) çalışıyor.
        self.nrfi_model = NRFIModel(pitcher_db, team_db, ballpark_db)
        self.f5_model = F5Model(team_db, pitcher_db)
        self.mlb_model = MLBModel(team_db, pitcher_db)

    def _recalculate_probabilities(self, away_score: float, home_score: float, exponent: float = 1.83):
        """Eğer Emniyet Kemeri skorları değiştirirse, olasılıkları yeniden hesaplar."""
        if away_score == 0 and home_score == 0:
            return 0.500, 0.500
        
        a_pow = away_score ** exponent
        h_pow = home_score ** exponent
        total_pow = a_pow + h_pow
        
        return a_pow / total_pow, h_pow / total_pow

    def predict_matchup(self, away_team: str, home_team: str, away_pitcher: str, home_pitcher: str) -> dict:
        """
        Gerekli tüm modelleri çalıştırır, güvenliği sağlar ve JSON çıktısını hazırlar.
        """
        
        # 1. Modelleri Çalıştır (Delegation)
        nrfi_result = self.nrfi_model.calculate(away_team, home_team, away_pitcher, home_pitcher)
        f5_result = self.f5_model.calculate(away_team, home_team, away_pitcher, home_pitcher)
        full_result = self.mlb_model.calculate(away_team, home_team, away_pitcher, home_pitcher)

        # 2. Değişkenleri Çıkar
        f5_away = f5_result["f5_away_score"]
        f5_home = f5_result["f5_home_score"]
        
        full_away = full_result["full_away_score"]
        full_home = full_result["full_home_score"]

        # 3. EMNİYET KEMERİ (Safety Check)
        # Tam maç skoru, F5 skorundan en az 0.5 yüksek olmak zorundadır.
        adjusted = False
        if full_away < f5_away + 0.5:
            full_away = f5_away + 0.5
            adjusted = True
            
        if full_home < f5_home + 0.5:
            full_home = f5_home + 0.5
            adjusted = True

        # Eğer skorlar güvenliğe takılıp yükseltildiyse, kazanma oranlarını ve totali güncelle
        if adjusted:
            full_away = round(full_away, 1)
            full_home = round(full_home, 1)
            away_prob, home_prob = self._recalculate_probabilities(full_away, full_home)
            
            # Güncellenmiş değerleri geri yaz
            full_result["full_away_score"] = full_away
            full_result["full_home_score"] = full_home
            full_result["full_total"] = round(full_away + full_home, 2)
            full_result["full_away_win_prob"] = round(away_prob, 3)
            full_result["full_home_win_prob"] = round(home_prob, 3)
            full_result["full_spread_adv"] = round(abs(full_home - full_away) - 1.5, 2)

        # 4. Final Çıktısı (API'nin Okuyacağı Format)
        return {
            "matchup": {
                "away_team": away_team,
                "home_team": home_team,
                "away_pitcher": away_pitcher,
                "home_pitcher": home_pitcher
            },
            "NRFI": nrfi_result,
            "F5": f5_result,
            "Full_Game": full_result
        }