import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.sports.wnba.services.config import RAW_BOX_SCORES_DIR, REQUIRED_BOX_FIELDS
from app.sports.wnba.services.espn_client import EspnClient
from app.sports.wnba.services.stat_parser import parse_team_statistics, validate_box_score


def _box_score_path(game_id: str) -> Path:
    return RAW_BOX_SCORES_DIR / f"{game_id}.json"


def box_score_exists(game_id: str) -> bool:
    return _box_score_path(game_id).exists()


def parse_summary_box_score(summary: dict[str, Any], game_meta: dict[str, Any] | None = None) -> dict[str, Any]:
    boxscore = summary.get("boxscore", {})
    teams = boxscore.get("teams", [])
    if len(teams) != 2:
        raise ValueError("Box score iki takım içermiyor")

    parsed_teams: dict[str, dict[str, Any]] = {}
    for team_entry in teams:
        team = team_entry.get("team", {})
        team_id = str(team.get("id", ""))
        stats = parse_team_statistics(team_entry.get("statistics", []))
        parsed_teams[team_id] = {
            "team_id": team_id,
            "abbreviation": team.get("abbreviation", ""),
            "display_name": team.get("displayName", ""),
            "box": stats,
        }

    home_id = away_id = None
    home_score = away_score = None

    header = summary.get("header", {})
    competitions = header.get("competitions") or summary.get("boxscore", {}).get("teams")
    if header.get("competitions"):
        comp = header["competitions"][0]
        for comp_team in comp.get("competitors", []):
            tid = str(comp_team.get("team", {}).get("id", ""))
            score_val = comp_team.get("score")
            if isinstance(score_val, dict):
                score = int(float(score_val.get("value", 0)))
            else:
                score = int(float(score_val or 0))
            if comp_team.get("homeAway") == "home":
                home_id, home_score = tid, score
            elif comp_team.get("homeAway") == "away":
                away_id, away_score = tid, score

    if game_meta:
        home_id = home_id or game_meta.get("home_team_id")
        away_id = away_id or game_meta.get("away_team_id")
        home_score = home_score if home_score is not None else game_meta.get("home_score")
        away_score = away_score if away_score is not None else game_meta.get("away_score")

    if not home_id or not away_id or home_id not in parsed_teams or away_id not in parsed_teams:
        ids = list(parsed_teams.keys())
        if len(ids) == 2:
            home_id, away_id = ids[0], ids[1]

    result = {
        "game_id": str(summary.get("header", {}).get("id") or game_meta.get("game_id") if game_meta else ""),
        "date": game_meta.get("date") if game_meta else None,
        "season": game_meta.get("season") if game_meta else None,
        "season_type": game_meta.get("season_type") if game_meta else None,
        "name": game_meta.get("name") if game_meta else summary.get("header", {}).get("competitions", [{}])[0].get("description"),
        "home_team_id": home_id,
        "away_team_id": away_id,
        "home_team_abbr": parsed_teams.get(home_id, {}).get("abbreviation") if home_id else None,
        "away_team_abbr": parsed_teams.get(away_id, {}).get("abbreviation") if away_id else None,
        "home_score": home_score,
        "away_score": away_score,
        "period": summary.get("header", {}).get("competitions", [{}])[0].get("status", {}).get("period", 4),
        "home_box": parsed_teams.get(home_id, {}).get("box", {}) if home_id else {},
        "away_box": parsed_teams.get(away_id, {}).get("box", {}) if away_id else {},
        "fetched_at": datetime.now(timezone.utc).isoformat(),
    }

    if not result["game_id"] and game_meta:
        result["game_id"] = game_meta["game_id"]

    return result


def fetch_box_score(
    game_id: str,
    client: EspnClient | None = None,
    game_meta: dict[str, Any] | None = None,
    save: bool = True,
    skip_existing: bool = True,
) -> dict[str, Any] | None:
    if skip_existing and box_score_exists(game_id):
        with open(_box_score_path(game_id), "r", encoding="utf-8") as f:
            return json.load(f)

    client = client or EspnClient()
    RAW_BOX_SCORES_DIR.mkdir(parents=True, exist_ok=True)

    summary = client.get_game_summary(game_id)
    parsed = parse_summary_box_score(summary, game_meta)

    home_missing = validate_box_score(parsed["home_box"], REQUIRED_BOX_FIELDS)
    away_missing = validate_box_score(parsed["away_box"], REQUIRED_BOX_FIELDS)
    if home_missing or away_missing:
        parsed["validation_warnings"] = {
            "home_missing": home_missing,
            "away_missing": away_missing,
        }

    if save:
        with open(_box_score_path(game_id), "w", encoding="utf-8") as f:
            json.dump(parsed, f, ensure_ascii=False, indent=2)

    return parsed
