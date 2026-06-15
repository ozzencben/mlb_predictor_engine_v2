import math

from app.sports.mlb.models.pitcher_k_model import (
    PitcherKModel,
    PitcherStats,
    LineupAvg,
)


class PitcherPropsEngine:
    """
    ML regression-based calculation engine for Pitcher Player Props (Strikeouts and Total Outs).

    K projection is delegated to PitcherKModel (de-constructed from K Model.ods).
    Total Outs projection continues to use the xFIP/wRC+ regression approach.

    Public interface is unchanged: project_pitcher_props() returns the same dict shape
    that prediction_runner.py already consumes.
    """

    def __init__(self, ballpark_db: dict = None):
        self.ballpark_db = ballpark_db or {}

    def project_pitcher_props(
        self,
        pitcher_stats: dict,
        lineup_avg_stats: dict,
        weather: dict,
        ballpark_name: str,
        is_home: bool = False,
    ) -> dict:
        # ------------------------------------------------------------------
        # PART 1: Strikeout Projection via PitcherKModel
        # ------------------------------------------------------------------
        #
        # Build PitcherStats from the hydrated pitcher_stats dict
        # (produced by prediction_runner.calculate_pitcher_metrics).
        #
        # Key stat availability:
        #   - k_pct        → from statsapi season stats
        #   - csw_pct      → derived in calculate_pitcher_metrics (0.55*k_pct+15)
        #   - swstr_pct    → derived in calculate_pitcher_metrics (0.45*k_pct+2)
        #   - avg_ip / avg_bf → derived in calculate_pitcher_metrics
        #   - throws       → from pitcher_stats.json / statsapi
        #
        # Note: k_pct_home and k_pct_away are not yet split per game from the
        # statsapi season stats endpoint; we therefore use the overall k_pct as
        # a safe proxy for both splits.  When granular home/away splits become
        # available they can be wired in here directly.

        raw_k_pct = pitcher_stats.get("k_pct", 22.0)

        pitcher_schema = PitcherStats(
            throws=pitcher_stats.get("throws", "R"),
            k_pct_home=raw_k_pct,
            k_pct_away=raw_k_pct,
            csw_pct=pitcher_stats.get("csw_pct", 28.2),
            swstr_pct=pitcher_stats.get("swstr_pct", 10.4),
            avg_ip=pitcher_stats.get("avg_ip", 5.2),
            avg_bf=pitcher_stats.get("avg_bf", 22.5),
        )

        # Build LineupAvg from the hydrated lineup averages dict.
        # lineup_avg_stats contains an overall k_pct but not hand-split k_pcts.
        # We compute split proxies using the team_splits data when available via
        # the keys "k_pct_vs_rhp" / "k_pct_vs_lhp" (added below as opt-in).
        lineup_k_pct = (lineup_avg_stats or {}).get("k_pct", 22.0)
        lineup_k_rhp = (lineup_avg_stats or {}).get("k_pct_vs_rhp", lineup_k_pct)
        lineup_k_lhp = (lineup_avg_stats or {}).get("k_pct_vs_lhp", lineup_k_pct)
        lineup_k_home = (lineup_avg_stats or {}).get("k_pct_home", lineup_k_pct)
        lineup_k_away = (lineup_avg_stats or {}).get("k_pct_away", lineup_k_pct)

        lineup_schema = LineupAvg(
            k_pct_rhp=lineup_k_rhp,
            k_pct_lhp=lineup_k_lhp,
            k_pct_home=lineup_k_home,
            k_pct_away=lineup_k_away,
        )

        # Determine home/away context for the pitcher.
        # The pitcher is always the one for their own team.
        # We don't have a direct "is_home" flag here, so we default to False
        # (away) as a safe neutral; the K% difference is minor when home/away
        # splits are the same proxy value derived from overall k_pct.

        k_result = PitcherKModel.calculate_projection(pitcher_schema, lineup_schema, is_home)
        proj_k = k_result.projected_k

        # Weather temperature adjustment (kept from original engine for stability)
        temp = float((weather or {}).get("temp_f", 72.0))
        if temp < 50.0:
            proj_k *= 0.90
        elif temp > 85.0:
            proj_k *= 1.05

        proj_k = max(1.5, min(12.0, round(proj_k, 2)))

        # ------------------------------------------------------------------
        # PART 2: Total Outs Projection (unchanged xFIP/wRC+ regression)
        # ------------------------------------------------------------------
        p_avg_ip = pitcher_stats.get("avg_ip", 5.2)
        l_wrc = (lineup_avg_stats or {}).get("wrc_plus", 100.0)

        base_outs = p_avg_ip * 3.0

        p_xfip = pitcher_stats.get("xfip", 4.20)
        outs_matchup_factor = (4.20 / max(0.1, p_xfip)) * (100.0 / max(1.0, l_wrc))
        outs_matchup_factor = math.sqrt(max(0.5, outs_matchup_factor))

        proj_outs = base_outs * (0.7 + 0.3 * outs_matchup_factor)

        wind_mph = float((weather or {}).get("wind_mph", 0.0))
        is_dome = (weather or {}).get("is_dome", False)
        if wind_mph > 8.0 and not is_dome:
            proj_outs *= 0.95

        proj_outs = max(9.0, min(24.0, round(proj_outs, 2)))

        return {
            "projected_k": proj_k,
            "projected_outs": proj_outs,
        }
