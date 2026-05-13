import math

class F5Model:
    """
    Calculates the "First 5 Innings" (F5) projected scores using Live Data.
    Location: app/models/f5_model_module.py
    """

    def __init__(self, team_db: dict, pitcher_db: dict):
        # Sadece güncel live_stats ve pitcher_stats JSON'larını alıyoruz. 
        # Karmaşık mapping ve ayrı db'lere gerek kalmadı.
        self.team_db = team_db
        self.pitcher_db = pitcher_db
        
        # Global Parameters
        self.lgERA = 4.20
        self.hfa = 1.03
        self.offExp = 1.83
        self.pMin = 0.60
        self.pMax = 1.40
        self.vMin = 0.95
        self.vMax = 1.10

    def _fetch_offense_stats(self, team_name: str):
        """live_stats.json yapısından takımın hücum değerlerini çeker."""
        data = self.team_db.get(team_name, {})
        
        # Momentum Ağırlıklı RPG (%30 Sezon, %70 Son 3 Maç)
        off_current = data.get('rpg_offense', {}).get('current', 4.5)
        off_last3 = data.get('rpg_offense', {}).get('last_3', 4.5)
        rpg0 = (0.3 * off_current) + (0.7 * off_last3)
        
        # Advanced Metrics
        wrc = data.get('advanced_metrics', {}).get('wrc_plus', 100.0)
        ba = data.get('batting_avg', {}).get('current', 0.245)
            
        return rpg0, wrc, ba

    def _fetch_pitching_stats(self, pitcher_name: str, team_name: str):
        """Atıcıların xERA değerlerini ve rakip takımın yediği sayı (bullpen proxy) ortalamasını çeker."""
        # Starting Pitcher xERA
        p_data = self.pitcher_db.get(pitcher_name, {})
        sp_xera = float(p_data.get('xera', p_data.get('era', 4.20)))
        
        # Bullpen Proxy (Takımın RPG Defense verisi bullpen kalitesini yansıtır)
        t_data = self.team_db.get(team_name, {})
        bp_proxy = float(t_data.get('rpg_defense', {}).get('current', 4.39))
            
        return sp_xera, bp_proxy

    def calculate_score(self, offense_team: str, pitching_team: str, pitcher: str, is_home: bool) -> float:
        rpg0, wrc, ba = self._fetch_offense_stats(offense_team)
        sp0, bp0 = self._fetch_pitching_stats(pitcher, pitching_team)
        
        # 1. Base Variables
        rpg = max(3.0, min(6.0, float(rpg0))) if rpg0 > 0 else 4.5
        sp = max(2.0, min(8.0, float(sp0)))
        bp = max(2.0, min(8.0, float(bp0)))
        
        base_score = 0.6 * rpg + 0.4 * self.lgERA
        
        # 2. Offense
        ba_term = 1.0 if ba <= 0 else (ba / 0.245) ** 0.5
        ba_term_capped = max(0.95, min(1.05, ba_term))
        off = ((wrc / 100.0) ** self.offExp) * ba_term_capped
        
        # 3. Pitching (F5 ÖZEL: %95 SP ağırlığı, %5 BP ağırlığı)
        exponent = ((0.95 * sp + 0.05 * bp) - self.lgERA) / self.lgERA
        pitchRaw = math.exp(exponent)
        pitch = max(self.pMin, min(self.pMax, pitchRaw))
        
        # 4. Volatility (Skor değişkenliği)
        volRaw = 0.5 * (abs(wrc - 100.0) / 50.0 + abs(sp - self.lgERA) / 2.0)
        vol = max(self.vMin, min(self.vMax, volRaw))
        
        # 5. Raw Score Calculation (9-Inning projection)
        raw_score = base_score * off * pitch * vol
        if is_home:
            raw_score *= self.hfa
            
        # 6. CRITICAL FIX: Scale down to First 5 Innings (5/9 multiplier)
        f5_score = raw_score * (5.0 / 9.0)
            
        return round(max(0.0, min(15.0, f5_score)), 1)

    def calculate(self, away_team: str, home_team: str, away_pitcher: str, home_pitcher: str) -> dict:
        away_score = self.calculate_score(away_team, home_team, home_pitcher, is_home=False)
        home_score = self.calculate_score(home_team, away_team, away_pitcher, is_home=True)
        
        # Pythagorean Win Probabilities specifically for F5
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