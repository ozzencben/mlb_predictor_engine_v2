import math

class MLBModel:
    """
    Calculates the "Full Game" projected scores and probabilities.
    Integrates Tyler's 40(SP)/30(Off)/20(BP)/10(Park) philosophy using Sabermetrics.
    """

    def __init__(self, team_db: dict, pitcher_db: dict, ballpark_db: dict = None):
        self.team_db = team_db
        self.pitcher_db = pitcher_db
        self.ballpark_db = ballpark_db or {}
        
        self.lgERA = 4.20
        self.hfa = 1.03
        self.offExp = 1.83

    def _get_pitcher_rating(self, pitcher_name: str):
        """Calculates SP strength using FIP and K-BB%."""
        p = self.pitcher_db.get(pitcher_name, {"era": 4.2, "fip": 4.2, "k_bb_pct": 0.14})
        
        fip = p.get('fip', 4.2)
        k_bb = p.get('k_bb_pct', 0.14)
        
        # Lower FIP is better. Higher K-BB% is better.
        # Rating > 1 implies better than average.
        rating = (self.lgERA / fip) * (1 + (k_bb - 0.14)) # Adjust based on league avg K-BB% (approx 14%)
        return max(0.6, min(1.4, rating)), p

    def _get_offense_rating(self, team_name: str):
        """Calculates Offense strength using wRC+ and RPG."""
        t = self.team_db.get(team_name, {})
        wrc = t.get('advanced_metrics', {}).get('wrc_plus', 100.0)
        
        off_current = t.get('rpg_offense', {}).get('current', 4.5)
        off_last3 = t.get('rpg_offense', {}).get('last_3', 4.5)
        rpg = (0.3 * off_current) + (0.7 * off_last3) # Momentum weight
        
        rating = (wrc / 100.0) * (rpg / 4.5)
        return max(0.7, min(1.3, rating))

    def _get_bullpen_rating(self, team_name: str):
        """Calculates Bullpen strength (using defense RPG proxy for now)."""
        t = self.team_db.get(team_name, {})
        def_rpg = t.get('rpg_defense', {}).get('current', 4.5)
        
        rating = self.lgERA / def_rpg
        return max(0.8, min(1.2, rating))

    def _get_park_factor(self, home_team: str):
        p = self.ballpark_db.get(home_team, {"park_factor": 1.0})
        factor = p.get('park_factor', 1.0)
        if factor > 10: factor /= 100.0 
        return factor

    def calculate_score(self, offense_team: str, pitching_team: str, pitcher: str, is_home: bool):
        sp_rating, p_raw = self._get_pitcher_rating(pitcher)
        off_rating = self._get_offense_rating(offense_team)
        bp_rating = self._get_bullpen_rating(pitching_team)
        park_f = self._get_park_factor(pitching_team if is_home else offense_team)

        # Apply Weights: The defense score is 66% SP and 33% BP to maintain the 40:20 ratio from Tyler's list.
        pitching_defense_strength = (sp_rating * 0.66) + (bp_rating * 0.34)
        
        # Base runs (4.5) * Offense Multiplier * (1 / Defense Multiplier) * Park Multiplier
        score = 4.5 * off_rating * (1 / pitching_defense_strength) * park_f
        
        if is_home: score *= self.hfa

        return round(max(0.5, min(15.0, score)), 1), p_raw

    def calculate(self, away_team: str, home_team: str, away_pitcher: str, home_pitcher: str) -> tuple:
        away_score, p_away_raw = self.calculate_score(away_team, home_team, home_pitcher, is_home=False)
        home_score, p_home_raw = self.calculate_score(home_team, away_team, away_pitcher, is_home=True)
        
        # Pythagorean Win Probabilities
        if away_score == 0 and home_score == 0:
             away_prob, home_prob = 0.5, 0.5
        else:
            away_pow = away_score ** self.offExp
            home_pow = home_score ** self.offExp
            away_prob = away_pow / (away_pow + home_pow)
            home_prob = home_pow / (away_pow + home_pow)
        
        result_dict = {
            "full_away_score": away_score,
            "full_home_score": home_score,
            "full_total": round(away_score + home_score, 2),
            "full_away_win_prob": round(away_prob, 3),
            "full_home_win_prob": round(home_prob, 3),
            "full_spread_adv": round(abs(home_score - away_score) - 1.5, 2)
        }
        
        raw_pitcher_data = {"away": p_away_raw, "home": p_home_raw}
        
        return result_dict, raw_pitcher_data