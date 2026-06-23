"""ESPN game summary'den oyuncu istatistiklerini parse eder."""
from __future__ import annotations

from typing import Any


def _parse_minutes(raw: str | None) -> float:
    if not raw or raw in ("--", "DNP", "NA"):
        return 0.0
    if ":" in raw:
        parts = raw.split(":")
        try:
            return float(parts[0]) + float(parts[1]) / 60.0
        except (ValueError, IndexError):
            return 0.0
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 0.0


def _parse_int(raw: str | None) -> int:
    if not raw or raw in ("--", "DNP", "NA"):
        return 0
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        return 0


def parse_players_from_summary(summary: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """
    ESPN summary -> {team_id: [player dict]}.
    Her oyuncu: athlete_id, name, minutes, points.
    """
    result: dict[str, list[dict[str, Any]]] = {}
    players_block = summary.get("boxscore", {}).get("players", [])

    for team_entry in players_block:
        team = team_entry.get("team", {})
        team_id = str(team.get("id", ""))
        if not team_id:
            continue

        roster: list[dict[str, Any]] = []
        for stat_group in team_entry.get("statistics", []):
            labels = stat_group.get("labels") or stat_group.get("names") or []
            label_idx = {lbl.upper(): i for i, lbl in enumerate(labels)}

            min_i = label_idx.get("MIN", 0)
            pts_i = label_idx.get("PTS", 1)

            for ath in stat_group.get("athletes", []):
                athlete = ath.get("athlete", {})
                stats = ath.get("stats") or []
                if not athlete.get("id"):
                    continue
                minutes = _parse_minutes(stats[min_i] if min_i < len(stats) else None)
                points = _parse_int(stats[pts_i] if pts_i < len(stats) else None)
                roster.append({
                    "athlete_id": str(athlete["id"]),
                    "name": athlete.get("displayName") or athlete.get("shortName", ""),
                    "minutes": round(minutes, 2),
                    "points": points,
                })

        result[team_id] = roster

    return result
