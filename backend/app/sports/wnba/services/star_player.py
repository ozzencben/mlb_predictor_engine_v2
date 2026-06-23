"""ESPN WNBA injury feed + yildiz oyuncu yokluk feature'lari."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.sports.wnba.services.config import DATA_DIR
from app.sports.wnba.services.espn_client import EspnClient

INJURIES_FILE = DATA_DIR / "today_injuries.json"

TOP_STAR_COUNT = 3
STAR_ROLLING_WINDOW = 10
STAR_MIN_GAMES = 5
STAR_MINUTES_OUT_THRESHOLD = 0.0
STAR_MINUTES_LIMITED_THRESHOLD = 20.0
INJURY_OUT_STATUSES = frozenset({"out", "doubtful"})


def fetch_wnba_injuries(save: bool = True, client: EspnClient | None = None) -> dict[str, Any]:
    client = client or EspnClient()
    raw = client.get_injuries()
    by_team: dict[str, list[dict[str, Any]]] = {}

    for team_block in raw.get("injuries", []):
        team_id = str(team_block.get("id", ""))
        if not team_id:
            continue
        entries: list[dict[str, Any]] = []
        for inj in team_block.get("injuries", []):
            athlete = inj.get("athlete", {})
            aid = athlete.get("id")
            if not aid:
                continue
            entries.append({
                "athlete_id": str(aid),
                "name": athlete.get("displayName") or athlete.get("shortName", ""),
                "status": (inj.get("status") or "").strip(),
                "date": inj.get("date"),
                "short_comment": inj.get("shortComment"),
            })
        by_team[team_id] = entries

    payload = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "team_count": len(by_team),
        "by_team": by_team,
    }

    if save:
        INJURIES_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[OK] {len(by_team)} takim injury kaydi -> {INJURIES_FILE}")

    return payload


def load_injuries() -> dict[str, list[dict[str, Any]]]:
    if not INJURIES_FILE.exists():
        return {}
    return json.loads(INJURIES_FILE.read_text(encoding="utf-8")).get("by_team", {})


def _team_player_logs(
    player_logs: list[dict[str, Any]],
    team_id: str,
    before_date: str,
) -> list[dict[str, Any]]:
    return sorted(
        [
            r for r in player_logs
            if r["team_id"] == team_id and (r.get("date") or "") < before_date
        ],
        key=lambda r: (r.get("date") or "", r["game_id"]),
    )


def _identify_top_stars(
    team_logs: list[dict[str, Any]],
    before_date: str,
) -> list[dict[str, Any]]:
    """Son STAR_ROLLING_WINDOW mac icinde en yuksek PPG'li TOP_STAR_COUNT oyuncu."""
    recent_game_ids: list[str] = []
    seen: set[str] = set()
    for row in reversed(team_logs):
        gid = row["game_id"]
        if gid not in seen:
            seen.add(gid)
            recent_game_ids.append(gid)
        if len(recent_game_ids) >= STAR_ROLLING_WINDOW:
            break
    if not recent_game_ids:
        return []

    recent_set = set(recent_game_ids)
    by_athlete: dict[str, dict[str, Any]] = {}

    for row in team_logs:
        if row["game_id"] not in recent_set:
            continue
        aid = row["athlete_id"]
        bucket = by_athlete.setdefault(aid, {
            "athlete_id": aid,
            "name": row.get("name", ""),
            "points": [],
            "minutes": [],
        })
        bucket["points"].append(row["points"])
        bucket["minutes"].append(row["minutes"])

    ranked: list[dict[str, Any]] = []
    for aid, data in by_athlete.items():
        games_played = len(data["points"])
        if games_played < STAR_MIN_GAMES:
            continue
        avg_pts = sum(data["points"]) / games_played
        avg_min = sum(data["minutes"]) / games_played
        ranked.append({
            "athlete_id": aid,
            "name": data["name"],
            "avg_ppg": round(avg_pts, 2),
            "avg_min": round(avg_min, 2),
            "games": games_played,
        })

    ranked.sort(key=lambda x: (-x["avg_ppg"], -x["avg_min"]))
    return ranked[:TOP_STAR_COUNT]


def _last_team_game_players(
    team_logs: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    if not team_logs:
        return {}
    last_gid = team_logs[-1]["game_id"]
    return {
        r["athlete_id"]: r
        for r in team_logs
        if r["game_id"] == last_gid
    }


def _injured_athlete_ids(
    injuries_by_team: dict[str, list[dict[str, Any]]],
    team_id: str,
) -> set[str]:
    ids: set[str] = set()
    for inj in injuries_by_team.get(team_id, []):
        status = (inj.get("status") or "").lower()
        if status in INJURY_OUT_STATUSES:
            ids.add(inj["athlete_id"])
    return ids


def compute_star_absence(
    player_logs: list[dict[str, Any]],
    team_id: str,
    before_date: str,
    injuries_by_team: dict[str, list[dict[str, Any]]] | None = None,
) -> dict[str, float | int]:
    """
  Pre-game yildiz yokluk sinyali (veri sizintisi yok).
  - Son macta oynamayan top-3 scorer -> out
  - Canli injury feed varsa Out/Doubtful yildizlar da out sayilir
    """
    team_logs = _team_player_logs(player_logs, team_id, before_date)
    stars = _identify_top_stars(team_logs, before_date)
    if not stars:
        return {"out_count": 0, "impact_ppg": 0.0, "minutes_avail_pct": 1.0}

    last_players = _last_team_game_players(team_logs)
    injured_ids = _injured_athlete_ids(injuries_by_team or {}, team_id)

    out_count = 0
    impact_ppg = 0.0
    minutes_sum = 0.0

    for star in stars:
        aid = star["athlete_id"]
        last_row = last_players.get(aid)
        last_min = last_row["minutes"] if last_row else 0.0

        is_out = False
        if last_row is None or last_min <= STAR_MINUTES_OUT_THRESHOLD:
            is_out = True
        elif aid in injured_ids:
            is_out = True

        if is_out:
            out_count += 1
            impact_ppg += star["avg_ppg"]
            minutes_sum += 0.0
        elif last_min < STAR_MINUTES_LIMITED_THRESHOLD:
            # Sinirli dakika — kismi etki
            impact_ppg += star["avg_ppg"] * 0.5
            minutes_sum += last_min
        else:
            minutes_sum += last_min

    max_minutes = 40.0 * len(stars)
    minutes_avail_pct = round(minutes_sum / max_minutes, 4) if max_minutes else 1.0

    return {
        "out_count": out_count,
        "impact_ppg": round(impact_ppg, 2),
        "minutes_avail_pct": minutes_avail_pct,
    }


def compute_star_feature_diffs(
    player_logs: list[dict[str, Any]],
    home_id: str,
    away_id: str,
    before_date: str,
    injuries_by_team: dict[str, list[dict[str, Any]]] | None = None,
) -> dict[str, float]:
    home = compute_star_absence(player_logs, home_id, before_date, injuries_by_team)
    away = compute_star_absence(player_logs, away_id, before_date, injuries_by_team)

    return {
        "feature_star_out_impact_diff": round(home["impact_ppg"] - away["impact_ppg"], 4),
        "feature_star_out_count_diff": float(home["out_count"] - away["out_count"]),
        "feature_star_minutes_avail_diff": round(
            home["minutes_avail_pct"] - away["minutes_avail_pct"], 4
        ),
    }
