from app.models.mlb_model import PitcherStats, TeamMLBStats

class F5Model:
    """
    Calculates the "First 5 Innings" (F5) projected scores.
    Relies heavily on the Starting Pitcher's Sabermetrics (95% weight).
    """

    def __init__(self, team_db: dict, pitcher_db: dict):
        self.team_db = team_db
        self.pitcher_db = pitcher_db
        self.lgERA = 4.20
        self.hfa = 1.03
        self.offExp = 1.83

    # KOD TEKRARI ÖNLENDİ: Doğrudan Dataclass'ları döndüren metodlar
    def _get_pitcher_data(self, pitcher_name: str) -> PitcherStats:
        p = self.pitcher_db.get(pitcher_name, {})
        return PitcherStats(
            era=float(p.get('era', 4.2)),
            fip=float(p.get('fip', 4.2)),
            k_bb_pct=float(p.get('k_bb_pct', 0.14))
        )

    def _get_team_data(self, team_name: str) -> TeamMLBStats:
        t = self.team_db.get(team_name, {})
        return TeamMLBStats(
            wrc_plus=float(t.get('advanced_metrics', {}).get('wrc_plus', 100.0)),
            off_current=float(t.get('rpg_offense', {}).get('current', 4.5)),
            off_last3=float(t.get('rpg_offense', {}).get('last_3', 4.5)),
            def_current=4.5 # F5'te BP kullanılmadığı için proxy
        )

    def calculate_score(self, offense_team: str, pitcher: str, is_home: bool) -> float:
        pitcher_data = self._get_pitcher_data(pitcher)
        off_stats = self._get_team_data(offense_team)
        
        # F5 Defense is 95% SP. Base 0.05 ekleyerek ZeroDivision ve ufak sapmaları koruyoruz.
        pitching_defense_strength = (pitcher_data.sp_rating * 0.95) + 0.05
        
        raw_score = 4.5 * off_stats.offense_rating * (1.0 / pitching_defense_strength)
        
        if is_home: 
            raw_score *= self.hfa
            
        # Scale to 5 innings
        f5_score = raw_score * (5.0 / 9.0)
            
        return round(max(0.0, min(10.0, f5_score)), 1)

    def calculate(self, away_team: str, home_team: str, away_pitcher: str, home_pitcher: str) -> dict:
        # GEREKSİZ PARAMETRE KALDIRILDI: pitching_team F5'te kullanılmadığı için metoddan çıkartıldı.
        away_score = self.calculate_score(away_team, home_pitcher, is_home=False)
        home_score = self.calculate_score(home_team, away_pitcher, is_home=True)
        
        # Pythagorean Optimizasyonu (total_pow ile CPU kazancı)
        if away_score == 0 and home_score == 0:
            away_prob, home_prob = 0.5, 0.5
        else:
            away_pow = away_score ** self.offExp
            home_pow = home_score ** self.offExp
            total_pow = away_pow + home_pow
            away_prob = away_pow / total_pow
            home_prob = home_pow / total_pow
            
        return {
            "f5_away_score": away_score,
            "f5_home_score": home_score,
            "f5_total": round(away_score + home_score, 2),
            "f5_away_win_prob": round(away_prob, 3),
            "f5_home_win_prob": round(home_prob, 3),
            "f5_spread_adv": round(abs(home_score - away_score) - 1.5, 2)
        }