"""
WNBA oyuncu mac loglari — box score summary'den uretilir.

Cache: data/raw/player_box/{game_id}.json
Cikti: data/processed/player_game_logs.json
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.sports.wnba.services.config import DATA_DIR, RAW_GAMES_DIR, RAW_PLAYER_BOX_DIR
from app.sports.wnba.services.espn_client import EspnClient
from app.sports.wnba.services.fetch_games import load_all_games
from app.sports.wnba.services.player_stats import parse_players_from_summary

PROCESSED_DIR = DATA_DIR / "processed"
PLAYER_LOGS_FILE = PROCESSED_DIR / "player_game_logs.json"


def _player_box_path(game_id: str) -> Path:
    return RAW_PLAYER_BOX_DIR / f"{game_id}.json"


def fetch_and_cache_player_box(
    game_id: str,
    game_meta: dict[str, Any],
    client: EspnClient | None = None,
    skip_existing: bool = True,
) -> dict[str, Any] | None:
    path = _player_box_path(game_id)
    if skip_existing and path.exists():
        return json.loads(path.read_text(encoding="utf-8"))

    client = client or EspnClient()
    RAW_PLAYER_BOX_DIR.mkdir(parents=True, exist_ok=True)

    try:
        summary = client.get_game_summary(game_id)
    except Exception:
        return None

    players_by_team = parse_players_from_summary(summary)
    if not players_by_team:
        return None

    payload = {
        "game_id": game_id,
        "date": game_meta.get("date"),
        "season": game_meta.get("season"),
        "home_team_id": str(game_meta.get("home_team_id", "")),
        "away_team_id": str(game_meta.get("away_team_id", "")),
        "players_by_team": players_by_team,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def _expand_player_rows(box: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    gid = box["game_id"]
    gdate = box.get("date") or ""
    season = box.get("season")
    home_id = str(box.get("home_team_id", ""))
    away_id = str(box.get("away_team_id", ""))

    for team_id, players in (box.get("players_by_team") or {}).items():
        team_id = str(team_id)
        opp_id = away_id if team_id == home_id else home_id
        is_home = 1 if team_id == home_id else 0
        for p in players:
            rows.append({
                "game_id": gid,
                "date": gdate,
                "season": season,
                "team_id": team_id,
                "opp_id": opp_id,
                "is_home": is_home,
                "athlete_id": p["athlete_id"],
                "name": p.get("name", ""),
                "minutes": float(p.get("minutes", 0)),
                "points": int(p.get("points", 0)),
            })
    return rows


def build_player_game_logs(
    start_season: int = 2016,
    end_season: int = 2026,
    fetch_missing: bool = True,
    save: bool = True,
    client: EspnClient | None = None,
) -> list[dict[str, Any]]:
    games = load_all_games(start_season, end_season)
    games.sort(key=lambda g: (g.get("date") or "", g.get("game_id", "")))

    client = client if fetch_missing else None
    all_rows: list[dict[str, Any]] = []
    fetched = 0
    cached = 0
    skipped = 0

    for game in games:
        gid = game.get("game_id")
        if not gid:
            skipped += 1
            continue

        path = _player_box_path(gid)
        if path.exists():
            box = json.loads(path.read_text(encoding="utf-8"))
            cached += 1
        elif fetch_missing and client:
            box = fetch_and_cache_player_box(gid, game, client=client)
            if box:
                fetched += 1
            else:
                skipped += 1
                continue
        else:
            skipped += 1
            continue

        all_rows.extend(_expand_player_rows(box))

    if save:
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        output = {
            "built_at": datetime.now(timezone.utc).isoformat(),
            "total_rows": len(all_rows),
            "games_cached": cached + fetched,
            "games_fetched": fetched,
            "games_skipped": skipped,
            "logs": all_rows,
        }
        PLAYER_LOGS_FILE.write_text(json.dumps(output, ensure_ascii=False), encoding="utf-8")
        print(f"[OK] {len(all_rows)} oyuncu-mac satiri -> {PLAYER_LOGS_FILE}")
        print(f"     (cache: {cached}, yeni fetch: {fetched}, atlandi: {skipped})")

    return all_rows


def load_player_game_logs() -> list[dict[str, Any]]:
    if not PLAYER_LOGS_FILE.exists():
        return []
    return json.loads(PLAYER_LOGS_FILE.read_text(encoding="utf-8")).get("logs", [])
