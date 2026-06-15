import math
from typing import Optional
from pydantic import BaseModel, Field, field_validator


# --- CONSTANTS ---
# League average constants (historically loaded from database, here defined as class-level fallbacks)
DEFAULT_LEAGUE_CSW = 0.282      # 28.2%
DEFAULT_LEAGUE_SWSTR = 0.10396  # 10.396%

# Default stats for rookie/fallback pitchers to prevent errors
DEFAULT_PITCHER_K = 22.0
DEFAULT_PITCHER_CSW = 28.2
DEFAULT_PITCHER_SWSTR = 10.4
DEFAULT_PITCHER_IP = 5.2
DEFAULT_PITCHER_BF = 22.5


class PitcherStats(BaseModel):
    pitcher_id: Optional[int] = Field(None, description="StatsAPI Pitcher ID")
    throws: str = Field("R", description="Pitcher throwing hand ('L' or 'R')")
    k_pct_home: Optional[float] = Field(default=DEFAULT_PITCHER_K, description="Strikeout % at Home (0-100 scale)")
    k_pct_away: Optional[float] = Field(default=DEFAULT_PITCHER_K, description="Strikeout % Away (0-100 scale)")
    csw_pct: Optional[float] = Field(default=DEFAULT_PITCHER_CSW, description="Called+Swinging Strike % (0-100 scale)")
    swstr_pct: Optional[float] = Field(default=DEFAULT_PITCHER_SWSTR, description="Swinging Strike % (0-100 scale)")
    avg_ip: Optional[float] = Field(default=DEFAULT_PITCHER_IP, description="Average Innings Pitched per game (Baseball notation, e.g. 5.2)")
    avg_bf: Optional[float] = Field(default=DEFAULT_PITCHER_BF, description="Average Batters Faced per game")

    @field_validator("throws")
    @classmethod
    def validate_throws(cls, v: str) -> str:
        v_upper = v.strip().upper()
        if v_upper not in ("L", "R"):
            return "R"  # Fallback to Right-handed
        return v_upper

    @field_validator("k_pct_home", "k_pct_away", "csw_pct", "swstr_pct")
    @classmethod
    def validate_pct(cls, v: Optional[float]) -> float:
        # Protect against None or negative values
        if v is None or v < 0:
            return 22.0
        # If the input was mistakenly provided as 0-1 scale (e.g. 0.22 instead of 22.0)
        if 0.0 < v <= 1.0:
            return v * 100.0
        return v

    @field_validator("avg_ip", "avg_bf")
    @classmethod
    def validate_volume(cls, v: Optional[float], info) -> float:
        if v is None or v <= 0:
            return DEFAULT_PITCHER_IP if info.field_name == "avg_ip" else DEFAULT_PITCHER_BF
        return v


class LineupAvg(BaseModel):
    k_pct_rhp: Optional[float] = Field(default=22.0, description="Opposing lineup K% vs Right-Handed Pitchers (0-100 scale)")
    k_pct_lhp: Optional[float] = Field(default=22.0, description="Opposing lineup K% vs Left-Handed Pitchers (0-100 scale)")
    k_pct_home: Optional[float] = Field(default=22.0, description="Opposing lineup K% at Home (0-100 scale)")
    k_pct_away: Optional[float] = Field(default=22.0, description="Opposing lineup K% Away (0-100 scale)")

    @field_validator("k_pct_rhp", "k_pct_lhp", "k_pct_home", "k_pct_away")
    @classmethod
    def validate_pct(cls, v: Optional[float]) -> float:
        if v is None or v < 0:
            return 22.0
        if 0.0 < v <= 1.0:
            return v * 100.0
        return v


class ProjectionResult(BaseModel):
    projected_k: float = Field(..., description="Projected Strikeouts count for the game")
    k_final_pct: float = Field(..., description="Adjusted Final Strikeout Percentage (0-100 scale)")
    expected_bf: float = Field(..., description="Expected Batters Faced volume")
    projected_outs: float = Field(..., description="Projected Total Outs (1 Inn = 3 Outs)")


class PitcherKModel:
    """
    Pitcher Strikeout Prediction Model.
    De-constructed and fixed from K Model.ods.
    Contains the mathematical logic for Expected K%, CSW/SwStr adjustments,
    and volume calculations.
    """

    @staticmethod
    def baseball_ip_to_math_ip(ip: float) -> float:
        """
        Converts baseball notation innings pitched (e.g. 5.2) to actual mathematical innings (5.6667).
        Handles fractional parts correctly (0.1 -> 1 out = 0.333 innings, 0.2 -> 2 outs = 0.667 innings).
        """
        full_innings = int(ip)
        outs_part = round((ip - full_innings) * 10)
        # If it's already mathematically formatted (fractional part is greater or equal to 3)
        if outs_part >= 3:
            return ip
        return full_innings + (outs_part / 3.0)

    @classmethod
    def calculate_projection(
        cls,
        pitcher: PitcherStats,
        lineup: LineupAvg,
        is_home: bool,
        league_csw: float = DEFAULT_LEAGUE_CSW,
        league_swstr: float = DEFAULT_LEAGUE_SWSTR
    ) -> ProjectionResult:
        # 1. Scale percentages to 0-1 for standard mathematical formulas
        p_k_home = pitcher.k_pct_home / 100.0
        p_k_away = pitcher.k_pct_away / 100.0
        p_csw = pitcher.csw_pct / 100.0
        p_swstr = pitcher.swstr_pct / 100.0

        l_k_rhp = lineup.k_pct_rhp / 100.0
        l_k_lhp = lineup.k_pct_lhp / 100.0
        l_k_home = lineup.k_pct_home / 100.0
        l_k_away = lineup.k_pct_away / 100.0

        # 2. Compute Expected K% (K% exp) matching home/away locations
        if is_home:
            # Pitcher is home, opponent lineup is away (l_k_away used)
            opp_hand_k = l_k_rhp if pitcher.throws == "R" else l_k_lhp
            opp_adjusted_k = (opp_hand_k * 0.55) + (l_k_away * 0.35)
            k_exp = (p_k_home * 0.65) + (opp_adjusted_k * 0.45)
        else:
            # Pitcher is away, opponent lineup is home (l_k_home used)
            opp_hand_k = l_k_rhp if pitcher.throws == "R" else l_k_lhp
            opp_adjusted_k = (opp_hand_k * 0.55) + (l_k_home * 0.35)
            k_exp = (p_k_away * 0.65) + (opp_adjusted_k * 0.45)

        # 3. Calculate CSW and SwStr adjustments vs League Averages (both scales are 0-1)
        csw_adj = p_csw - league_csw
        swstr_adj = p_swstr - league_swstr

        # 4. Final K% (Bounded between 5% and 50% for safety)
        k_final = k_exp + (csw_adj * 0.35) + (swstr_adj * 0.35)
        k_final = max(0.05, min(0.50, k_final))

        # 5. Volume calculations (fixing the squaring bug from ODS file)
        math_ip = cls.baseball_ip_to_math_ip(pitcher.avg_ip)
        # Protect against zero division
        safe_ip = max(0.1, math_ip)
        bf_per_inn = pitcher.avg_bf / safe_ip

        # Expected volume of batters faced
        expected_bf = math_ip * bf_per_inn

        # 6. Calculate projections
        projected_k = expected_bf * k_final
        projected_outs = math_ip * 3.0

        return ProjectionResult(
            projected_k=round(projected_k, 2),
            k_final_pct=round(k_final * 100, 1),
            expected_bf=round(expected_bf, 2),
            projected_outs=round(projected_outs, 1)
        )
