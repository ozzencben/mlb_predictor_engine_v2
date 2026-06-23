"""
WNBA box score'dan advanced metrik hesaplama.
WNBA maçları 40 dakika (4 x 10 dk) oynanır — Pace normalize 40 dk üzerinden.
"""
from __future__ import annotations

from typing import Any


def _safe(v: Any, default: float = 0.0) -> float:
    if v is None:
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def possessions(box: dict[str, Any]) -> float:
    """Oliver formülü: FGA - OREB + TOV + 0.44 * FTA"""
    fga = _safe(box.get("FGA"))
    oreb = _safe(box.get("OREB"))
    tov = _safe(box.get("TOV"))
    fta = _safe(box.get("FTA"))
    poss = fga - oreb + tov + 0.44 * fta
    return max(poss, 1.0)


def efg_pct(box: dict[str, Any]) -> float | None:
    """Effective Field Goal %: (FGM + 0.5 * 3PM) / FGA"""
    fgm = _safe(box.get("FGM"))
    tpm = _safe(box.get("3PM"))
    fga = _safe(box.get("FGA"))
    if fga == 0:
        return None
    return round((fgm + 0.5 * tpm) / fga, 4)


def ts_pct(box: dict[str, Any]) -> float | None:
    """True Shooting %: PTS / (2 * (FGA + 0.44 * FTA))"""
    pts = _safe(box.get("PTS"))
    fga = _safe(box.get("FGA"))
    fta = _safe(box.get("FTA"))
    denom = 2.0 * (fga + 0.44 * fta)
    if denom == 0:
        return None
    return round(pts / denom, 4)


def tov_pct(box: dict[str, Any]) -> float | None:
    """Turnover %: TOV / possessions"""
    tov = _safe(box.get("TOV"))
    poss = possessions(box)
    return round(tov / poss, 4)


def orb_pct(box: dict[str, Any], opp_box: dict[str, Any]) -> float | None:
    """Offensive Rebound %: OREB / (OREB + opp_DRB)"""
    oreb = _safe(box.get("OREB"))
    opp_drb = _safe(opp_box.get("DRB"))
    denom = oreb + opp_drb
    if denom == 0:
        return None
    return round(oreb / denom, 4)


def drb_pct(box: dict[str, Any], opp_box: dict[str, Any]) -> float | None:
    """Defensive Rebound %: DRB / (DRB + opp_OREB)"""
    drb = _safe(box.get("DRB"))
    opp_oreb = _safe(opp_box.get("OREB"))
    denom = drb + opp_oreb
    if denom == 0:
        return None
    return round(drb / denom, 4)


def off_rating(box: dict[str, Any]) -> float | None:
    """Offensive Rating: 100 * PTS / possessions"""
    pts = _safe(box.get("PTS"))
    poss = possessions(box)
    return round(100.0 * pts / poss, 2)


def def_rating(opp_box: dict[str, Any]) -> float | None:
    """Defensive Rating = rakip takımın Offensive Rating'i"""
    return off_rating(opp_box)


def net_rating(box: dict[str, Any], opp_box: dict[str, Any]) -> float | None:
    """Net Rating: OffRtg - DefRtg"""
    off = off_rating(box)
    def_ = def_rating(opp_box)
    if off is None or def_ is None:
        return None
    return round(off - def_, 2)


def pace(box: dict[str, Any], opp_box: dict[str, Any], minutes: float = 40.0) -> float | None:
    """
    Pace (40 dk normalize): possessions * (40 / minutes)
    WNBA = 40 dk, NBA = 48 dk
    """
    poss_team = possessions(box)
    poss_opp = possessions(opp_box)
    avg_poss = (poss_team + poss_opp) / 2.0
    return round(avg_poss * (40.0 / minutes), 2)


def ft_rate(box: dict[str, Any]) -> float | None:
    """FT Rate: FTA / FGA"""
    fta = _safe(box.get("FTA"))
    fga = _safe(box.get("FGA"))
    if fga == 0:
        return None
    return round(fta / fga, 4)


def ast_tov_ratio(box: dict[str, Any]) -> float | None:
    """AST/TOV ratio"""
    ast = _safe(box.get("AST"))
    tov = _safe(box.get("TOV"))
    if tov == 0:
        return None
    return round(ast / tov, 3)


def compute_all(box: dict[str, Any], opp_box: dict[str, Any], period: int = 4) -> dict[str, Any]:
    """Bir takımın tüm advanced metriklerini dict olarak hesapla."""
    minutes = 40.0
    if period > 4:
        minutes = 40.0 + (period - 4) * 5.0
    return {
        "poss": round(possessions(box), 2),
        "efg_pct": efg_pct(box),
        "ts_pct": ts_pct(box),
        "tov_pct": tov_pct(box),
        "orb_pct": orb_pct(box, opp_box),
        "drb_pct": drb_pct(box, opp_box),
        "off_rtg": off_rating(box),
        "def_rtg": def_rating(opp_box),
        "net_rtg": net_rating(box, opp_box),
        "pace": pace(box, opp_box, minutes=minutes),
        "ft_rate": ft_rate(box),
        "ast_tov": ast_tov_ratio(box),
    }
