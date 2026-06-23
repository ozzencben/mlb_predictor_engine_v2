import re
from typing import Any


def _parse_made_attempted(value: str) -> tuple[int | None, int | None]:
    if not value or "-" not in value:
        return None, None
    parts = value.split("-", 1)
    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        return None, None


def _to_float(value: str | int | float | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value: str | int | float | None) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def parse_team_statistics(statistics: list[dict[str, Any]]) -> dict[str, Any]:
    """ESPN summary boxscore statistics listesini normalize eder."""
    stats: dict[str, Any] = {}
    for item in statistics:
        name = item.get("name", "")
        display = item.get("displayValue", "")

        if name == "fieldGoalsMade-fieldGoalsAttempted":
            fgm, fga = _parse_made_attempted(display)
            stats["FGM"], stats["FGA"] = fgm, fga
        elif name == "fieldGoalPct":
            stats["FG_PCT"] = _to_float(display)
        elif name == "threePointFieldGoalsMade-threePointFieldGoalsAttempted":
            pm, pa = _parse_made_attempted(display)
            stats["3PM"], stats["3PA"] = pm, pa
        elif name == "threePointFieldGoalPct":
            stats["3P_PCT"] = _to_float(display)
        elif name == "freeThrowsMade-freeThrowsAttempted":
            ftm, fta = _parse_made_attempted(display)
            stats["FTM"], stats["FTA"] = ftm, fta
        elif name == "freeThrowPct":
            stats["FT_PCT"] = _to_float(display)
        elif name == "totalRebounds":
            stats["REB"] = _to_int(display)
        elif name == "offensiveRebounds":
            stats["OREB"] = _to_int(display)
        elif name == "defensiveRebounds":
            stats["DRB"] = _to_int(display)
        elif name == "assists":
            stats["AST"] = _to_int(display)
        elif name == "steals":
            stats["STL"] = _to_int(display)
        elif name == "blocks":
            stats["BLK"] = _to_int(display)
        elif name == "turnovers":
            stats["TOV"] = _to_int(display)
        elif name == "fouls":
            stats["PF"] = _to_int(display)
        elif name in ("points", "totalPoints"):
            stats["PTS"] = _to_int(display)

    if stats.get("PTS") is None and all(k in stats for k in ("FGM", "3PM", "FTM")):
        stats["PTS"] = stats["FGM"] * 2 + stats["3PM"] + stats["FTM"]

    return stats


def validate_box_score(box: dict[str, Any], required: tuple[str, ...]) -> list[str]:
    missing = [field for field in required if box.get(field) is None]
    return missing
