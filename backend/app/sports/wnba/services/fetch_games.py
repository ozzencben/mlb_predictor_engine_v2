import json
from datetime import datetime, timezone
from typing import Any

from app.sports.wnba.services.config import CORE_TEAM_IDS, RAW_GAMES_DIR
from app.sports.wnba.services.espn_client import EspnClient


def _parse_score(score_obj: Any) -> int | None:
    if score_obj is None:
        return None
    if isinstance(score_obj, dict):
        return int(float(score_obj.get("value", score_obj.get("displayValue", 0))))
    try:
        return int(float(score_obj))
    except (TypeError, ValueError):
        return None


def _season_type(competition: dict[str, Any], event: dict[str, Any] | None = None) -> str:
    season = competition.get("season") or (event or {}).get("season") or {}
    if isinstance(season, dict):
        season_type = season.get("type", {})
        if isinstance(season_type, dict):
            abbrev = (season_type.get("abbreviation") or season_type.get("name") or "unknown").lower()
        else:
            abbrev = str(season_type).lower()
    else:
        abbrev = "regular"  # default to regular if it is an int/string
    if abbrev in {"reg", "regular", "regular season"}:
        return "regular"
    if abbrev in {"post", "playoffs", "postseason"}:
        return "playoff"
    if "pre" in abbrev:
        return "preseason"
    if "cc" in abbrev or "commissioner" in abbrev:
        return "commissioners_cup"
    return abbrev


def _parse_game_event(event: dict[str, Any]) -> dict[str, Any] | None:
    competition = (event.get("competitions") or [{}])[0]
    status = competition.get("status", {}).get("type", {})
    if not status.get("completed"):
        return None

    competitors = competition.get("competitors", [])
    if len(competitors) != 2:
        return None

    home = away = None
    for comp in competitors:
        side = comp.get("homeAway")
        team = comp.get("team", {})
        record = {
            "team_id": str(team.get("id", "")),
            "team_abbr": team.get("abbreviation", ""),
            "team_name": team.get("displayName", ""),
            "score": _parse_score(comp.get("score")),
        }
        if side == "home":
            home = record
        elif side == "away":
            away = record

    if not home or not away:
        return None

    date_str = event.get("date", "")
    game_date = date_str[:10] if date_str else None
    
    season_val = competition.get("season") or event.get("season") or {}
    if isinstance(season_val, dict):
        season_year = season_val.get("year")
    else:
        season_year = season_val

    return {
        "game_id": str(event.get("id", "")),
        "date": game_date,
        "season": season_year,
        "season_type": _season_type(competition, event),
        "name": event.get("name", ""),
        "home_team_id": home["team_id"],
        "away_team_id": away["team_id"],
        "home_team_abbr": home["team_abbr"],
        "away_team_abbr": away["team_abbr"],
        "home_team_name": home["team_name"],
        "away_team_name": away["team_name"],
        "home_score": home["score"],
        "away_score": away["score"],
    }



def team_ids_for_season(season: int, teams: list[dict[str, Any]] | None = None) -> list[str]:
    if season <= 2024:
        return list(CORE_TEAM_IDS.keys())
    if teams is None:
        from app.sports.wnba.services.fetch_teams import load_teams

        teams = load_teams()
    return [t["id"] for t in teams]


def fetch_season_games(
    season: int,
    client: EspnClient | None = None,
    teams: list[dict[str, Any]] | None = None,
    save: bool = True,
) -> list[dict[str, Any]]:
    client = client or EspnClient()
    RAW_GAMES_DIR.mkdir(parents=True, exist_ok=True)

    team_ids = team_ids_for_season(season, teams)
    games_by_id: dict[str, dict[str, Any]] = {}

    for team_id in team_ids:
        payload = client.get_team_schedule(team_id, season)
        for event in payload.get("events", []):
            parsed = _parse_game_event(event)
            if parsed and parsed["game_id"]:
                if not parsed.get("season"):
                    parsed["season"] = season
                games_by_id[parsed["game_id"]] = parsed

    games = sorted(games_by_id.values(), key=lambda g: (g.get("date") or "", g["game_id"]))

    output = {
        "season": season,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "team_ids_scanned": team_ids,
        "game_count": len(games),
        "games": games,
    }

    if save:
        out_path = RAW_GAMES_DIR / f"{season}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

    return games


def load_season_games(season: int) -> list[dict[str, Any]]:
    path = RAW_GAMES_DIR / f"{season}.json"
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("games", [])


def load_all_games(start_season: int, end_season: int) -> list[dict[str, Any]]:
    all_games: dict[str, dict[str, Any]] = {}
    for season in range(start_season, end_season + 1):
        for game in load_season_games(season):
            all_games[game["game_id"]] = game
    return sorted(all_games.values(), key=lambda g: (g.get("date") or "", g["game_id"]))
