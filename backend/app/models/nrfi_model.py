import math

class NRFIModel:
    """
    Applies Tyler's Logic natively.
    Uses Poisson Distribution to predict NRFI/YRFI probabilities dynamically.
    Now utilizes FIP for improved accuracy.
    """

    def __init__(self, pitcher_db: dict, team_db: dict, ballpark_db: dict):
        self.pitcher_db = pitcher_db
        self.team_db = team_db
        self.ballpark_db = ballpark_db

        self.fallback_park_n = 0.50
        self.fallback_park_y = 0.50

    @staticmethod
    def clamp_norm(val, base, divisor) -> float:
        try:
            return max(0.0, min(1.0, (float(val) - base) / divisor))
        except (ValueError, TypeError):
            return 0.5

    def _calculate_poisson_nrfi(self, runs_per_9_innings: float) -> float:
        runs_per_1_inning = runs_per_9_innings / 9.0
        return math.exp(-runs_per_1_inning)

    def _get_pitcher_stats(self, pitcher_name: str):
        data = self.pitcher_db.get(pitcher_name, {})
        # Use FIP instead of ERA for better predictive value
        fip = data.get('fip', data.get('era', 4.20))
        p_nrfi = self._calculate_poisson_nrfi(fip)
        return p_nrfi, float(fip)

    def _get_team_stats(self, team_name: str):
        data = self.team_db.get(team_name, {})
        
        off_current = data.get('rpg_offense', {}).get('current', 4.5)
        off_last3 = data.get('rpg_offense', {}).get('last_3', 4.5)
        
        def_current = data.get('rpg_defense', {}).get('current', 4.5)
        def_last3 = data.get('rpg_defense', {}).get('last_3', 4.5)
        
        ba = data.get('batting_avg', {}).get('current', 0.245)
        wrc = data.get('advanced_metrics', {}).get('wrc_plus', 100.0)

        t_nrfi = self._calculate_poisson_nrfi(off_current)
        t_yrfi = 1.0 - t_nrfi

        return t_nrfi, t_yrfi, def_current, ba, wrc, off_current, off_last3, def_current, def_last3

    def _get_ballpark_stats(self, home_team: str):
        park_data = self.ballpark_db.get(home_team, {})
        park_n = park_data.get('nrfi_pct', self.fallback_park_n)
        park_y = park_data.get('yrfi_pct', self.fallback_park_y)
        
        if park_n > 1: park_n /= 100.0
        if park_y > 1: park_y /= 100.0
            
        return park_n, park_y

    def calculate(self, away_team: str, home_team: str, away_pitcher: str, home_pitcher: str) -> dict:
        pNRFIa, fipA = self._get_pitcher_stats(away_pitcher)
        pNRFIh, fipH = self._get_pitcher_stats(home_pitcher)

        tNRFIa, tYRFIa, raA, baA, wrcA, away_rpg_cur, away_rpg_l3, away_orpg_cur, away_orpg_l3 = self._get_team_stats(away_team)
        tNRFIh, tYRFIh, raH, baH, wrcH, home_rpg_cur, home_rpg_l3, home_orpg_cur, home_orpg_l3 = self._get_team_stats(home_team)

        parkN, parkY = self._get_ballpark_stats(home_team)

        rpgA_n = min(1.0, (0.3 * away_rpg_cur + 0.7 * away_rpg_l3) / 10.0) 
        rpgH_n = min(1.0, (0.3 * home_rpg_cur + 0.7 * home_rpg_l3) / 10.0)
        orpgVsA_n = min(1.0, (0.3 * home_orpg_cur + 0.7 * home_orpg_l3) / 10.0)
        orpgVsH_n = min(1.0, (0.3 * away_orpg_cur + 0.7 * away_orpg_l3) / 10.0)

        baThrA = self.clamp_norm(baA, 0.25, 0.08)
        baThrH = self.clamp_norm(baH, 0.25, 0.08)
        wrcThrA = self.clamp_norm(wrcA, 100, 50)
        wrcThrH = self.clamp_norm(wrcH, 100, 50)
        fipThrA = self.clamp_norm(fipA, 0, 6)
        fipThrH = self.clamp_norm(fipH, 0, 6)

        nrfi_score = (
            0.25 * pNRFIa + 0.25 * pNRFIh + 0.05 * tNRFIa + 0.05 * tNRFIh + 0.15 * parkN +
            0.03 * (1.0 - baThrA) + 0.03 * (1.0 - baThrH) + 0.03 * (1.0 - wrcThrA) +
            0.03 * (1.0 - wrcThrH) + 0.065 * (1.0 - fipThrA) + 0.065 * (1.0 - fipThrH)
        )

        fip_comp = (min(1.0, fipA / 6.0) + min(1.0, fipH / 6.0)) / 2.0
        yrfi_score = (
            0.20 * ((tYRFIa + tYRFIh) / 2.0) + 0.15 * ((raA + raH) / 10.0) +
            0.25 * ((rpgA_n + rpgH_n) / 2.0) + 0.20 * ((orpgVsA_n + orpgVsH_n) / 2.0) +
            0.10 * parkY + 0.10 * fip_comp
        )

        return {
            "nrfi_score": round(nrfi_score, 4),
            "yrfi_score": round(yrfi_score, 4),
            "confidence": round(max(nrfi_score, yrfi_score), 4),
            "pick": "NRFI" if nrfi_score >= yrfi_score else "YRFI"
        }