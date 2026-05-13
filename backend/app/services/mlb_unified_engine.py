from app.models.f5_model import F5Model
from app.models.mlb_model import MLBModel
from app.models.nrfi_model import NRFIModel

class MLBUnifiedEngine:
    """
    The Orchestrator. 
    Routes live data to specific models (NRFI, F5, MLB), applies safety logic, 
    and returns a unified dictionary ready for the frontend.
    """
    
    def __init__(self, team_db: dict, pitcher_db: dict, ballpark_db: dict = None, standings_db: dict = None):
        if ballpark_db is None:
            ballpark_db = {}
        if standings_db is None:
             standings_db = {}
             
        self.team_db = team_db
        self.pitcher_db = pitcher_db
        self.ballpark_db = ballpark_db
        self.standings_db = standings_db

        # Initialize Models with the new advanced data sources
        self.nrfi_model = NRFIModel(pitcher_db, team_db, ballpark_db)
        self.f5_model = F5Model(team_db, pitcher_db)
        self.mlb_model = MLBModel(team_db, pitcher_db, ballpark_db)

    def _recalculate_probabilities(self, away_score: float, home_score: float, exponent: float = 1.83):
        """Recalculates win probabilities if safety checks alter the scores."""
        if away_score == 0 and home_score == 0:
            return 0.500, 0.500
        
        a_pow = away_score ** exponent
        h_pow = home_score ** exponent
        total_pow = a_pow + h_pow
        
        return a_pow / total_pow, h_pow / total_pow

    def predict_matchup(self, game_data: dict) -> dict:
        """
        Executes all models, ensures safety, and builds the rich JSON payload.
        Now takes a full game dictionary from the matchup_scraper.
        """
        
        away_team = game_data['away_team']
        home_team = game_data['home_team']
        away_pitcher = game_data['away_pitcher']
        home_pitcher = game_data['home_pitcher']

        # 1. Execute Models
        nrfi_result = self.nrfi_model.calculate(away_team, home_team, away_pitcher, home_pitcher)
        f5_result = self.f5_model.calculate(away_team, home_team, away_pitcher, home_pitcher)
        full_result, raw_pitcher_data = self.mlb_model.calculate(away_team, home_team, away_pitcher, home_pitcher)

        # 2. Extract Variables
        f5_away = f5_result["f5_away_score"]
        f5_home = f5_result["f5_home_score"]
        
        full_away = full_result["full_away_score"]
        full_home = full_result["full_home_score"]

        # 3. SAFETY CHECK
        # Full game score must be at least 0.5 higher than the F5 score.
        adjusted = False
        if full_away < f5_away + 0.5:
            full_away = f5_away + 0.5
            adjusted = True
            
        if full_home < f5_home + 0.5:
            full_home = f5_home + 0.5
            adjusted = True

        # If scores were adjusted, recalculate totals and probabilities
        if adjusted:
            full_away = round(full_away, 1)
            full_home = round(full_home, 1)
            away_prob, home_prob = self._recalculate_probabilities(full_away, full_home)
            
            full_result["full_away_score"] = full_away
            full_result["full_home_score"] = full_home
            full_result["full_total"] = round(full_away + full_home, 2)
            full_result["full_away_win_prob"] = round(away_prob, 3)
            full_result["full_home_win_prob"] = round(home_prob, 3)
            full_result["full_spread_adv"] = round(abs(full_home - full_away) - 1.5, 2)

        # 4. Value Check Logic (Basic comparison to live odds if available)
        value_alerts = []
        book_total = game_data.get('odds', {}).get('over_under', 0)
        if book_total > 0:
            diff = abs(full_result['full_total'] - book_total)
            if diff > 0.7:
                 value_alerts.append("🔥 SIGNIFICANT TOTAL EDGE")

        # 5. Build the Final Output Format (API Payload)
        return {
            "matchup": {
                "away_team": away_team,
                "home_team": home_team,
                "away_pitcher": away_pitcher,
                "home_pitcher": home_pitcher,
                "game_time": game_data.get('game_time', 'TBD'),
                "away_stats": game_data.get('away_team_stats', {}), 
                "home_stats": game_data.get('home_team_stats', {}),
                "status": game_data.get('status', 'TBD')
            },
            "NRFI": nrfi_result,
            "F5": f5_result,
            "Full_Game": full_result,
            "Details": {
                 "pitcher_analysis": raw_pitcher_data,
                 "value_alerts": value_alerts
            }
        }