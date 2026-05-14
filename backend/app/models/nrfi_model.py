from dataclasses import dataclass
import math

@dataclass
class TeamStats:
    rpg_cur: float
    rpg_l3: float
    ra_cur: float  
    ra_l3: float   
    ba: float
    wrc: float
    
    @property
    def t_nrfi(self) -> float:
        """Runs Per Inning üzerinden Poisson NRFI olasılığı"""
        return math.exp(-(self.rpg_cur / 9.0))
        
    @property
    def t_yrfi(self) -> float:
        """YRFI olasılığı (1 - NRFI)"""
        return 1.0 - self.t_nrfi

    @property
    def rpg_normalized(self) -> float:
        """Hücum gücü normalizasyonu (API'den gelen ham 5.51 gibi verileri <1 aralığına çeker)"""
        return min(1.0, (0.3 * self.rpg_cur + 0.7 * self.rpg_l3) / 10.0)

    @property
    def orpg_normalized(self) -> float:
        """Savunma (izin verilen koşu) normalizasyonu"""
        return min(1.0, (0.3 * self.ra_cur + 0.7 * self.ra_l3) / 10.0)

class NRFIModel:
    """
    Excel tabanlı NRFI/YRFI tahmin motorunun FastAPI uyumlu Python adaptasyonu.
    ERA yerine FIP kullanarak istatistiksel varyansı düşürür.
    """
    def __init__(self, pitcher_db: dict, team_db: dict, ballpark_db: dict):
        self.pitcher_db = pitcher_db
        self.team_db = team_db
        self.ballpark_db = ballpark_db

        self.fallback_park_n = 0.50
        self.fallback_park_y = 0.50

    @staticmethod
    def clamp_norm(val: float, base: float, divisor: float) -> float:
        """Excel'deki MAK(0, MİN(1, (X - base)/divisor)) yapısının karşılığı"""
        try:
            return max(0.0, min(1.0, (float(val) - base) / divisor))
        except (ValueError, TypeError):
            return 0.5

    def _calculate_poisson_nrfi(self, runs_per_9_innings: float) -> float:
        runs_per_1_inning = runs_per_9_innings / 9.0
        return math.exp(-runs_per_1_inning)

    def _get_pitcher_stats(self, pitcher_name: str) -> tuple[float, float]:
        data = self.pitcher_db.get(pitcher_name, {})
        fip = float(data.get('fip', data.get('era', 4.20)))
        p_nrfi = self._calculate_poisson_nrfi(fip)
        return p_nrfi, fip

    def _get_team_stats(self, team_name: str) -> TeamStats:
        data = self.team_db.get(team_name, {})
        offense = data.get('rpg_offense', {})
        defense = data.get('rpg_defense', {})
        batting = data.get('batting_avg', {})
        advanced = data.get('advanced_metrics', {})
        
        return TeamStats(
            rpg_cur=float(offense.get('current', 4.5)),
            rpg_l3=float(offense.get('last_3', 4.5)),
            ra_cur=float(defense.get('current', 4.5)),
            ra_l3=float(defense.get('last_3', 4.5)),
            ba=float(batting.get('current', 0.245)),
            wrc=float(advanced.get('wrc_plus', 100.0))
        )

    def _get_ballpark_stats(self, home_team: str) -> tuple[float, float]:
        park_data = self.ballpark_db.get(home_team, {})
        park_n = park_data.get('nrfi_pct', self.fallback_park_n)
        park_y = park_data.get('yrfi_pct', self.fallback_park_y)
        
        if park_n > 1.0: park_n /= 100.0
        if park_y > 1.0: park_y /= 100.0
            
        return park_n, park_y

    def calculate(self, away_team: str, home_team: str, away_pitcher: str, home_pitcher: str) -> dict:
        pNRFIa, fipA = self._get_pitcher_stats(away_pitcher)
        pNRFIh, fipH = self._get_pitcher_stats(home_pitcher)

        away_stats = self._get_team_stats(away_team)
        home_stats = self._get_team_stats(home_team)

        parkN, parkY = self._get_ballpark_stats(home_team)

        # Threshold Normalizasyonları
        baThrA = self.clamp_norm(away_stats.ba, 0.25, 0.08)
        baThrH = self.clamp_norm(home_stats.ba, 0.25, 0.08)
        wrcThrA = self.clamp_norm(away_stats.wrc, 100.0, 50.0)
        wrcThrH = self.clamp_norm(home_stats.wrc, 100.0, 50.0)
        fipThrA = self.clamp_norm(fipA, 0.0, 6.0)
        fipThrH = self.clamp_norm(fipH, 0.0, 6.0)

        # NRFI Skor Ağırlıklandırması
        nrfi_score = (
            0.25 * pNRFIa + 0.25 * pNRFIh + 
            0.05 * away_stats.t_nrfi + 0.05 * home_stats.t_nrfi + 
            0.15 * parkN +
            0.03 * (1.0 - baThrA) + 0.03 * (1.0 - baThrH) + 
            0.03 * (1.0 - wrcThrA) + 0.03 * (1.0 - wrcThrH) + 
            0.065 * (1.0 - fipThrA) + 0.065 * (1.0 - fipThrH)
        )

        fip_comp = (min(1.0, fipA / 6.0) + min(1.0, fipH / 6.0)) / 2.0
        
        # YRFI Skor Ağırlıklandırması
        yrfi_score = (
            0.20 * ((away_stats.t_yrfi + home_stats.t_yrfi) / 2.0) + 
            0.15 * ((away_stats.ra_cur + home_stats.ra_cur) / 10.0) +
            0.25 * ((away_stats.rpg_normalized + home_stats.rpg_normalized) / 2.0) + 
            0.20 * ((away_stats.orpg_normalized + home_stats.orpg_normalized) / 2.0) +
            0.10 * parkY + 0.10 * fip_comp
        )

        return {
            "nrfi_score": round(nrfi_score, 4),
            "yrfi_score": round(yrfi_score, 4),
            "confidence": round(max(nrfi_score, yrfi_score), 4),
            "pick": "NRFI" if nrfi_score >= yrfi_score else "YRFI"
        }