import math

class NRFIModel:
    """
    Applies Tyler's Logic natively to the new Live Data Pipeline.
    Uses Poisson Distribution to predict NRFI/YRFI probabilities dynamically.
    Location: app/models/nrfi_model.py
    """

    def __init__(self, pitcher_db: dict, team_db: dict, ballpark_db: dict):
        # Artık rpg_db ve team_mapping'e gerek yok. Her şey pitcher_db ve team_db içinde standart!
        self.pitcher_db = pitcher_db
        self.team_db = team_db
        self.ballpark_db = ballpark_db

        self.fallback_park_n = 0.50
        self.fallback_park_y = 0.50

    @staticmethod
    def clamp_norm(val, base, divisor) -> float:
        """Return max(0, min(1, (val - base) / divisor))."""
        try:
            return max(0.0, min(1.0, (float(val) - base) / divisor))
        except (ValueError, TypeError):
            return 0.5

    def _calculate_poisson_nrfi(self, runs_per_9_innings: float) -> float:
        """
        MÜHENDİSLİK GÜNCELLEMESİ:
        Bir takımın veya atıcının 9 inninglik verisini 1 inning'e böler.
        Poisson Dağılımı ile 0 sayı olma (NRFI) ihtimalini hesaplar.
        """
        runs_per_1_inning = runs_per_9_innings / 9.0
        # P(X=0) = e^(-lambda)
        return math.exp(-runs_per_1_inning)

    def _get_pitcher_stats(self, pitcher_name: str):
        # Yeni pitcher_stats.json yapısından verileri çeker
        data = self.pitcher_db.get(pitcher_name, {})
        
        # xERA'yı kullan, yoksa ERA'yı, o da yoksa lig ortalaması 4.20'yi al
        xera = data.get('xera', data.get('era', 4.20))
        
        # Poisson ile Atıcının NRFI ve YRFI Gücünü hesapla
        p_nrfi = self._calculate_poisson_nrfi(xera)
        
        return p_nrfi, float(xera)

    def _get_team_stats(self, team_name: str):
        # Yeni live_stats.json yapısından verileri çeker
        data = self.team_db.get(team_name, {})
        
        # Hücum (Offense) ve Savunma (Defense) RPG değerleri
        off_current = data.get('rpg_offense', {}).get('current', 4.5)
        off_last3 = data.get('rpg_offense', {}).get('last_3', 4.5)
        
        def_current = data.get('rpg_defense', {}).get('current', 4.5)
        def_last3 = data.get('rpg_defense', {}).get('last_3', 4.5)
        
        # Advanced Metrics
        ba = data.get('batting_avg', {}).get('current', 0.245)
        wrc = data.get('advanced_metrics', {}).get('wrc_plus', 100.0)

        # Takımın NRFI Gücü (Ne kadar az sayı atarsa NRFI o kadar yüksek olur)
        t_nrfi = self._calculate_poisson_nrfi(off_current)
        t_yrfi = 1.0 - t_nrfi # YRFI tam tersidir

        return t_nrfi, t_yrfi, def_current, ba, wrc, off_current, off_last3, def_current, def_last3

    def _get_ballpark_stats(self, home_team: str):
        # Şimdilik statik tutuyoruz, ileride burayı da kazıyabiliriz
        park_data = self.ballpark_db.get(home_team, {})
        park_n = park_data.get('nrfi_pct', self.fallback_park_n)
        park_y = park_data.get('yrfi_pct', self.fallback_park_y)
        
        if park_n > 1: park_n /= 100.0
        if park_y > 1: park_y /= 100.0
            
        return park_n, park_y

    def calculate(self, away_team: str, home_team: str, away_pitcher: str, home_pitcher: str) -> dict:
        """
        Executes Tyler's logic using the fresh live data pipeline.
        """
        # İsim eşleştirmelerine (Mapping) artık gerek yok, her şey saf ve temiz!
        pNRFIa, eraA = self._get_pitcher_stats(away_pitcher)
        pNRFIh, eraH = self._get_pitcher_stats(home_pitcher)

        tNRFIa, tYRFIa, raA, baA, wrcA, away_rpg_cur, away_rpg_l3, away_orpg_cur, away_orpg_l3 = self._get_team_stats(away_team)
        tNRFIh, tYRFIh, raH, baH, wrcH, home_rpg_cur, home_rpg_l3, home_orpg_cur, home_orpg_l3 = self._get_team_stats(home_team)

        parkN, parkY = self._get_ballpark_stats(home_team)

        # Weighted RPG & Normalize (Momentum Hesaplaması: %30 Sezon, %70 Son 3 Maç)
        rpgA_n = min(1.0, (0.3 * away_rpg_cur + 0.7 * away_rpg_l3) / 10.0) 
        rpgH_n = min(1.0, (0.3 * home_rpg_cur + 0.7 * home_rpg_l3) / 10.0)
        orpgVsA_n = min(1.0, (0.3 * home_orpg_cur + 0.7 * home_orpg_l3) / 10.0)
        orpgVsH_n = min(1.0, (0.3 * away_orpg_cur + 0.7 * away_orpg_l3) / 10.0)

        # Thresholds (Bağlar)
        baThrA = self.clamp_norm(baA, 0.25, 0.08)
        baThrH = self.clamp_norm(baH, 0.25, 0.08)
        wrcThrA = self.clamp_norm(wrcA, 100, 50)
        wrcThrH = self.clamp_norm(wrcH, 100, 50)
        eraThrA = self.clamp_norm(eraA, 0, 6)
        eraThrH = self.clamp_norm(eraH, 0, 6)

        # Excel Logic: NRFI Score (Tyler's Formula)
        nrfi_score = (
            0.25 * pNRFIa + 0.25 * pNRFIh + 0.05 * tNRFIa + 0.05 * tNRFIh + 0.15 * parkN +
            0.03 * (1.0 - baThrA) + 0.03 * (1.0 - baThrH) + 0.03 * (1.0 - wrcThrA) +
            0.03 * (1.0 - wrcThrH) + 0.065 * (1.0 - eraThrA) + 0.065 * (1.0 - eraThrH)
        )

        # Excel Logic: YRFI Score (Tyler's Formula)
        era_comp = (min(1.0, eraA / 6.0) + min(1.0, eraH / 6.0)) / 2.0
        yrfi_score = (
            0.20 * ((tYRFIa + tYRFIh) / 2.0) + 0.15 * ((raA + raH) / 10.0) +
            0.25 * ((rpgA_n + rpgH_n) / 2.0) + 0.20 * ((orpgVsA_n + orpgVsH_n) / 2.0) +
            0.10 * parkY + 0.10 * era_comp
        )

        return {
            "nrfi_score": round(nrfi_score, 4),
            "yrfi_score": round(yrfi_score, 4),
            "confidence": round(max(nrfi_score, yrfi_score), 4),
            "pick": "NRFI" if nrfi_score >= yrfi_score else "YRFI"
        }