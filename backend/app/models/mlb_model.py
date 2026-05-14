from dataclasses import dataclass

@dataclass
class TeamMLBStats:
    wrc_plus: float
    off_current: float
    off_last3: float
    def_current: float # Bullpen proxy
    
    @property
    def rpg_momentum(self) -> float:
        """Hücum ivmesi (Son 3 maça %70 ağırlık)"""
        return (0.3 * self.off_current) + (0.7 * self.off_last3)

    @property
    def offense_rating(self) -> float:
        """wRC+ ve RPG üzerinden standardize edilmiş hücum skoru (0.7 - 1.3 arası)"""
        rating = (self.wrc_plus / 100.0) * (self.rpg_momentum / 4.5)
        return max(0.7, min(1.3, rating))
        
    @property
    def bullpen_rating(self) -> float:
        """Lig ortalama ERA'sı üzerinden Bullpen kalitesi (0.8 - 1.2 arası)"""
        rating = 4.20 / max(0.1, self.def_current) # ZeroDivision koruması
        return max(0.8, min(1.2, rating))

@dataclass
class PitcherStats:
    era: float
    fip: float
    k_bb_pct: float
    
    @property
    def sp_rating(self) -> float:
        """FIP ve K-BB% tabanlı Starting Pitcher Kalitesi (0.6 - 1.4 arası)"""
        rating = (4.20 / max(0.1, self.fip)) * (1 + (self.k_bb_pct - 0.14))
        return max(0.6, min(1.4, rating))


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

    def _get_pitcher_data(self, pitcher_name: str) -> tuple[PitcherStats, dict]:
        p = self.pitcher_db.get(pitcher_name, {"era": 4.2, "fip": 4.2, "k_bb_pct": 0.14})
        return PitcherStats(
            era=float(p.get('era', 4.2)),
            fip=float(p.get('fip', 4.2)),
            k_bb_pct=float(p.get('k_bb_pct', 0.14))
        ), p

    def _get_team_data(self, team_name: str) -> TeamMLBStats:
        t = self.team_db.get(team_name, {})
        return TeamMLBStats(
            wrc_plus=float(t.get('advanced_metrics', {}).get('wrc_plus', 100.0)),
            off_current=float(t.get('rpg_offense', {}).get('current', 4.5)),
            off_last3=float(t.get('rpg_offense', {}).get('last_3', 4.5)),
            def_current=float(t.get('rpg_defense', {}).get('current', 4.5))
        )

    def _get_park_factor(self, home_team: str) -> float:
        factor = float(self.ballpark_db.get(home_team, {}).get('park_factor', 1.0))
        return factor / 100.0 if factor > 10 else factor

    def calculate_score(self, offense_team: str, pitching_team: str, pitcher: str, is_home: bool) -> tuple[float, dict]:
        pitcher_data, p_raw = self._get_pitcher_data(pitcher)
        off_stats = self._get_team_data(offense_team)
        def_stats = self._get_team_data(pitching_team)
        park_f = self._get_park_factor(pitching_team if is_home else offense_team)

        # Apply Weights: 66% SP and 34% BP
        pitching_defense_strength = (pitcher_data.sp_rating * 0.66) + (def_stats.bullpen_rating * 0.34)
        
        score = 4.5 * off_stats.offense_rating * (1.0 / pitching_defense_strength) * park_f
        if is_home: 
            score *= self.hfa

        return round(max(0.5, min(15.0, score)), 1), p_raw

    def calculate(self, away_team: str, home_team: str, away_pitcher: str, home_pitcher: str) -> tuple[dict, dict]:
        away_score, p_home_raw = self.calculate_score(away_team, home_team, home_pitcher, is_home=False)
        home_score, p_away_raw = self.calculate_score(home_team, away_team, away_pitcher, is_home=True)
        
        # Pythagorean Win Probabilities
        if away_score == 0 and home_score == 0:
             away_prob, home_prob = 0.5, 0.5
        else:
            away_pow = away_score ** self.offExp
            home_pow = home_score ** self.offExp
            total_pow = away_pow + home_pow
            away_prob = away_pow / total_pow
            home_prob = home_pow / total_pow
        
        result_dict = {
            "full_away_score": away_score,
            "full_home_score": home_score,
            "full_total": round(away_score + home_score, 2),
            "full_away_win_prob": round(away_prob, 3),
            "full_home_win_prob": round(home_prob, 3),
            "full_spread_adv": round(abs(home_score - away_score) - 1.5, 2)
        }
        
        return result_dict, {"away": p_away_raw, "home": p_home_raw}