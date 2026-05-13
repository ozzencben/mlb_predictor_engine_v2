class F5Model:
    """
    Calculates the "First 5 Innings" (F5) projected scores.
    Relies almost entirely on the Starting Pitcher's Sabermetrics.
    """

    def __init__(self, team_db: dict, pitcher_db: dict):
        self.team_db = team_db
        self.pitcher_db = pitcher_db
        self.lgERA = 4.20
        self.hfa = 1.03
        self.offExp = 1.83

    def _get_pitcher_rating(self, pitcher_name: str):
        """Uses FIP and K-BB% for SP rating."""
        p = self.pitcher_db.get(pitcher_name, {"era": 4.2, "fip": 4.2, "k_bb_pct": 0.14})
        fip = p.get('fip', 4.2)
        k_bb = p.get('k_bb_pct', 0.14)
        rating = (self.lgERA / fip) * (1 + (k_bb - 0.14))
        return max(0.6, min(1.4, rating))

    def _get_offense_rating(self, team_name: str):
        t = self.team_db.get(team_name, {})
        wrc = t.get('advanced_metrics', {}).get('wrc_plus', 100.0)
        off_current = t.get('rpg_offense', {}).get('current', 4.5)
        off_last3 = t.get('rpg_offense', {}).get('last_3', 4.5)
        rpg = (0.3 * off_current) + (0.7 * off_last3)
        
        rating = (wrc / 100.0) * (rpg / 4.5)
        return max(0.7, min(1.3, rating))

    def calculate_score(self, offense_team: str, pitching_team: str, pitcher: str, is_home: bool) -> float:
        sp_rating = self._get_pitcher_rating(pitcher)
        off_rating = self._get_offense_rating(offense_team)
        
        # F5 Defense is 95% SP.
        pitching_defense_strength = sp_rating * 0.95 + 0.05
        
        raw_score = 4.5 * off_rating * (1 / pitching_defense_strength)
        if is_home: raw_score *= self.hfa
            
        # Scale to 5 innings
        f5_score = raw_score * (5.0 / 9.0)
            
        return round(max(0.0, min(10.0, f5_score)), 1)

    def calculate(self, away_team: str, home_team: str, away_pitcher: str, home_pitcher: str) -> dict:
        away_score = self.calculate_score(away_team, home_team, home_pitcher, is_home=False)
        home_score = self.calculate_score(home_team, away_team, away_pitcher, is_home=True)
        
        if away_score == 0 and home_score == 0:
            away_prob, home_prob = 0.5, 0.5
        else:
            away_pow = away_score ** self.offExp
            home_pow = home_score ** self.offExp
            away_prob = away_pow / (away_pow + home_pow)
            home_prob = home_pow / (away_pow + home_pow)
            
        return {
            "f5_away_score": away_score,
            "f5_home_score": home_score,
            "f5_total": round(away_score + home_score, 2),
            "f5_away_win_prob": round(away_prob, 3),
            "f5_home_win_prob": round(home_prob, 3),
            "f5_spread_adv": round(abs(home_score - away_score) - 1.5, 2)
        }