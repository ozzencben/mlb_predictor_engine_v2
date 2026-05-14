from pydantic import BaseModel, Field

from app.models.nrfi_model import NRFIModel
from app.models.f5_model import F5Model
from app.models.mlb_model import MLBModel

# --- Pydantic Schema --- (FastAPI Endpoint'i için gerekli yapı)
class GameInputData(BaseModel):
    away_team: str
    home_team: str
    away_pitcher: str
    home_pitcher: str
    game_time: str = "TBD"
    status: str = "TBD"
    odds: dict = Field(default_factory=dict)
    away_team_stats: dict = Field(default_factory=dict)
    home_team_stats: dict = Field(default_factory=dict)

# Artık bu sınıfları doğrudan import ediyoruz. (Önceki adımlarda yazdığımız sınıflar)
# from core.models.nrfi import NRFIModel
# from core.models.f5 import F5Model
# from core.models.mlb import MLBModel

class MLBUnifiedEngine:
    """
    The Orchestrator. 
    Routes live data to specific models (NRFI, F5, MLB), applies safety logic, 
    and returns a unified dictionary ready for the frontend.
    """
    
    def __init__(self, team_db: dict, pitcher_db: dict, ballpark_db: dict = None, standings_db: dict = None):
        self.team_db = team_db
        self.pitcher_db = pitcher_db
        self.ballpark_db = ballpark_db or {}
        self.standings_db = standings_db or {}

        # Modellerin başlatılması
        self.nrfi_model = NRFIModel(pitcher_db, team_db, ballpark_db)
        self.f5_model = F5Model(team_db, pitcher_db)
        self.mlb_model = MLBModel(team_db, pitcher_db, ballpark_db)

    def _recalculate_probabilities(self, away_score: float, home_score: float, exponent: float = 1.83) -> tuple[float, float]:
        """Skorlar güvenlik sınırına takılırsa kazanma ihtimallerini yeniden hesaplar."""
        if away_score == 0 and home_score == 0:
            return 0.500, 0.500
        
        a_pow = away_score ** exponent
        h_pow = home_score ** exponent
        total_pow = a_pow + h_pow
        
        return a_pow / total_pow, h_pow / total_pow

    def predict_matchup(self, game: GameInputData) -> dict:
        """
        Bütün tahmin motorlarını çalıştırır, mantık hatalarını düzeltir (Safety Check)
        ve FastAPI için uygun JSON payload'unu oluşturur.
        """
        
        # 1. Modellerin Çalıştırılması
        nrfi_result = self.nrfi_model.calculate(game.away_team, game.home_team, game.away_pitcher, game.home_pitcher)
        f5_result = self.f5_model.calculate(game.away_team, game.home_team, game.away_pitcher, game.home_pitcher)
        full_result, raw_pitcher_data = self.mlb_model.calculate(game.away_team, game.home_team, game.away_pitcher, game.home_pitcher)

        # 2. Değişkenlerin Çıkartılması
        f5_away = f5_result["f5_away_score"]
        f5_home = f5_result["f5_home_score"]
        full_away = full_result["full_away_score"]
        full_home = full_result["full_home_score"]

        # 3. MANTIKSAL GÜVENLİK KONTROLÜ (SAFETY CHECK)
        # Mantık: Bir takım maçın tamamında, ilk 5 inning'de attığı sayıdan daha az sayı atmış olamaz.
        adjusted = False
        if full_away < f5_away + 0.5:
            full_away = f5_away + 0.5
            adjusted = True
            
        if full_home < f5_home + 0.5:
            full_home = f5_home + 0.5
            adjusted = True

        # Skorlar düzeltildiyse diğer metrikleri güncelle
        if adjusted:
            full_away = round(full_away, 1)
            full_home = round(full_home, 1)
            away_prob, home_prob = self._recalculate_probabilities(full_away, full_home)
            
            full_result.update({
                "full_away_score": full_away,
                "full_home_score": full_home,
                "full_total": round(full_away + full_home, 2),
                "full_away_win_prob": round(away_prob, 3),
                "full_home_win_prob": round(home_prob, 3),
                "full_spread_adv": round(abs(full_home - full_away) - 1.5, 2)
            })

        # 4. Value Bet Yakalayıcı (Market Oranlarına Karşı)
        value_alerts = []
        book_total = game.odds.get('over_under', 0)
        if book_total > 0:
            diff = abs(full_result['full_total'] - book_total)
            if diff > 0.7:
                value_alerts.append("🔥 SIGNIFICANT TOTAL EDGE")

        # 5. Frontend İçin Nihai JSON Payload
        return {
            "matchup": {
                "away_team": game.away_team,
                "home_team": game.home_team,
                "away_pitcher": game.away_pitcher,
                "home_pitcher": game.home_pitcher,
                "game_time": game.game_time,
                "away_stats": game.away_team_stats, 
                "home_stats": game.home_team_stats,
                "status": game.status
            },
            "NRFI": nrfi_result,
            "F5": f5_result,
            "Full_Game": full_result,
            "Details": {
                 "pitcher_analysis": raw_pitcher_data,
                 "value_alerts": value_alerts
            }
        }