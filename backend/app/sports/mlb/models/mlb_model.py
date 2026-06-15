import os
import json
import math
from dataclasses import dataclass
from app.sports.mlb.models.schemas import BallparkStatsSchema, PitcherStatsSchema, TeamStatsSchema


@dataclass
class TeamMLBStats:
    wrc_plus: float
    off_current: float
    off_last3: float
    def_current: float  # RPG defense proxy
    siera: float = 3.90  # Bullpen SIERA

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
        """SIERA üzerinden Bullpen kalitesi (0.8 - 1.2 arası)"""
        rating = 3.90 / max(0.1, self.siera)
        return max(0.8, min(1.2, rating))


@dataclass
class PitcherStats:
    era: float
    fip: float
    k_bb_pct: float
    xera: float = 4.20
    xfip: float = 4.20
    throws: str = "R"

    @property
    def sp_rating(self) -> float:
        """Blended SP rating incorporating actual stats (60%) and expected stats (40%) (0.6 - 1.4 arası)"""
        # Actual stats strength (FIP & K-BB%)
        actual_rating = (4.20 / max(0.1, self.fip)) * (1.0 + (self.k_bb_pct - 0.14))
        
        # Expected stats strength (xERA & xFIP)
        expected_rating = (4.20 / max(0.1, self.xfip)) * (4.20 / max(0.1, self.xera))
        expected_rating = math.sqrt(max(0.01, expected_rating))
        
        rating = (actual_rating * 0.60) + (expected_rating * 0.40)
        return max(0.6, min(1.4, rating))


class MLBModel:
    """
    Calculates the "Full Game" projected scores and probabilities.
    Integrates Tyler's 40(SP)/30(Off)/20(BP)/10(Park) philosophy using Sabermetrics.
    Upgraded with Bullpen SIERA, Blended Pitcher Expected Stats, Dynamic HFA, and Sonny Moore PR.
    Supports Lineup wRC+/wOBA blending and vs LHP/RHP team hitting splits.
    """

    def __init__(self, team_db: dict, pitcher_db: dict, ballpark_db: dict = None):
        self.team_db = team_db
        self.pitcher_db = pitcher_db
        self.ballpark_db = ballpark_db or {}

        self.lgERA = 4.20
        self.hfa = 1.03
        self.offExp = 1.83

        # Load Bullpen SIERA and Sonny Moore PR
        data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
        try:
            with open(os.path.join(data_dir, "bullpen_siera.json"), "r", encoding="utf-8") as f:
                self.bullpen_siera = json.load(f)
        except Exception:
            self.bullpen_siera = {}

        try:
            with open(os.path.join(data_dir, "sonny_moore.json"), "r", encoding="utf-8") as f:
                self.sonny_moore = json.load(f)
        except Exception:
            self.sonny_moore = {}

        if self.sonny_moore:
            self.sonny_moore_avg = sum(self.sonny_moore.values()) / len(self.sonny_moore)
        else:
            self.sonny_moore_avg = 100.0

    def _get_pitcher_data(self, pitcher_name: str) -> tuple[PitcherStats, dict]:
        p = self.pitcher_db.get(
            pitcher_name, {"era": 4.2, "fip": 4.2, "k_bb_pct": 0.14, "xera": 4.20, "xfip": 4.20, "throws": "R"}
        )
        validated = PitcherStatsSchema.model_validate(p)
        throws = p.get("throws", "R")
        return PitcherStats(
            era=validated.era,
            fip=validated.fip,
            k_bb_pct=validated.k_bb_pct,
            xera=validated.xera,
            xfip=validated.xfip,
            throws=throws
        ), validated.model_dump()

    def _get_team_data(self, team_name: str) -> TeamMLBStats:
        t = self.team_db.get(team_name, {})
        validated = TeamStatsSchema.model_validate(
            {
                "wrc_plus": t.get("advanced_metrics", {}).get("wrc_plus", 100.0),
                "off_current": t.get("rpg_offense", {}).get("current", 4.5),
                "off_last3": t.get("rpg_offense", {}).get("last_3", 4.5),
                "def_current": t.get("rpg_defense", {}).get("current", 4.5),
            }
        )
        siera = self.bullpen_siera.get(team_name, 3.90)
        return TeamMLBStats(
            wrc_plus=validated.wrc_plus,
            off_current=validated.off_current,
            off_last3=validated.off_last3,
            def_current=validated.def_current,
            siera=siera
        )

    def _get_park_factor(self, home_team: str) -> float:
        raw_ballpark = self.ballpark_db.get(home_team, {})
        validated = BallparkStatsSchema.model_validate(raw_ballpark)
        return validated.park_factor

    def calculate_score(
        self, offense_team: str, pitching_team: str, pitcher: str, is_home: bool,
        lineup_avg: dict = None, splits: dict = None
    ) -> tuple[float, dict]:
        pitcher_data, p_raw = self._get_pitcher_data(pitcher)
        off_stats = self._get_team_data(offense_team)
        def_stats = self._get_team_data(pitching_team)
        park_f = self._get_park_factor(offense_team if is_home else pitching_team)

        # Apply Base Weights: 66% SP and 34% BP
        pitching_defense_strength = (pitcher_data.sp_rating * 0.66) + (
            def_stats.bullpen_rating * 0.34
        )

        offense_rating = off_stats.offense_rating

        # 1. Starting Lineup wRC+/wOBA Blending
        if lineup_avg:
            lineup_wrc = lineup_avg.get("wrc_plus", 100.0)
            lineup_woba = lineup_avg.get("woba", 0.315)
            
            team_wrc = off_stats.wrc_plus
            team_woba = 0.250 + (off_stats.off_current * 0.015)
            
            wrc_ratio = lineup_wrc / team_wrc if team_wrc > 0 else 1.0
            woba_ratio = lineup_woba / team_woba if team_woba > 0 else 1.0
            
            lineup_mult = (wrc_ratio * 0.5 + woba_ratio * 0.5) * 0.7 + 0.3
            offense_rating *= lineup_mult

        # 2. Team splits vs starting pitcher's throwing arm (throws)
        if splits and pitcher_data:
            hand = pitcher_data.throws
            split_key = "vs_LHP" if hand == "L" else "vs_RHP"
            split_ops = splits.get(split_key, {}).get("ops", 0.720)
            
            overall_ops = 0.550 + (off_stats.off_current * 0.04)
            split_mult = split_ops / overall_ops if overall_ops > 0 else 1.0
            # Smooth splits weight to prevent massive variations
            split_mult = split_mult * 0.8 + 0.2
            offense_rating *= split_mult

        score = (
            4.5 * offense_rating * (1.0 / pitching_defense_strength) * park_f
        )
        
        # Dynamic stadyum HFA
        hfa_modifier = self.hfa
        home_team_name = offense_team if is_home else pitching_team
        home_stats = self.team_db.get(home_team_name, {})

        if is_home:
            # Home team scoring (offense_team is home_team_name)
            home_off_rpg = home_stats.get("rpg_offense", {}).get("home", 4.5)
            away_off_rpg = home_stats.get("rpg_offense", {}).get("away", 4.5)
            if away_off_rpg > 0:
                ratio = home_off_rpg / away_off_rpg
                hfa_modifier = 1.01 + (ratio - 1.0) * 0.10
                hfa_modifier = max(1.01, min(1.08, hfa_modifier))
            score *= hfa_modifier
        else:
            # Away team scoring (pitching_team is home_team_name)
            home_def_rpg = home_stats.get("rpg_defense", {}).get("home", 4.5)
            away_def_rpg = home_stats.get("rpg_defense", {}).get("away", 4.5)
            if away_def_rpg > 0:
                ratio = home_def_rpg / away_def_rpg
                hfa_modifier = 0.99 - (1.0 - ratio) * 0.10
                hfa_modifier = max(0.92, min(0.99, hfa_modifier))
            score *= hfa_modifier

        # Sonny Moore Power Rankings Differential Bump
        sm_off = self.sonny_moore.get(offense_team, self.sonny_moore_avg)
        sm_def = self.sonny_moore.get(pitching_team, self.sonny_moore_avg)
        sm_diff = sm_off - sm_def
        sm_bump = 1.0 + (sm_diff * 0.003)
        score *= sm_bump

        return round(max(0.5, min(15.0, score)), 1), p_raw

    def calculate(
        self, away_team: str, home_team: str, away_pitcher: str, home_pitcher: str,
        away_lineup_avg: dict = None, home_lineup_avg: dict = None,
        away_splits: dict = None, home_splits: dict = None
    ) -> tuple[dict, dict]:
        away_score, p_home_raw = self.calculate_score(
            away_team, home_team, home_pitcher, is_home=False,
            lineup_avg=away_lineup_avg, splits=away_splits
        )
        home_score, p_away_raw = self.calculate_score(
            home_team, away_team, away_pitcher, is_home=True,
            lineup_avg=home_lineup_avg, splits=home_splits
        )

        # Pythagorean Win Probabilities
        if away_score == 0 and home_score == 0:
            away_prob, home_prob = 0.5, 0.5
        else:
            away_pow = away_score**self.offExp
            home_pow = home_score**self.offExp
            total_pow = away_pow + home_pow
            away_prob = away_pow / total_pow
            home_prob = home_pow / total_pow

        result_dict = {
            "full_away_score": away_score,
            "full_home_score": home_score,
            "full_total": round(away_score + home_score, 2),
            "full_away_win_prob": round(away_prob, 3),
            "full_home_win_prob": round(home_prob, 3),
            "full_spread_adv": round(abs(home_score - away_score) - 1.5, 2),
        }

        return result_dict, {"away": p_away_raw, "home": p_home_raw}
