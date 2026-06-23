import json
from datetime import datetime, timezone
from typing import Any

from app.sports.wnba.services.config import TEAMS_FILE, DATA_DIR, CORE_TEAM_IDS, EXPANSION_TEAM_IDS
from app.sports.wnba.services.espn_client import EspnClient
from app.sports.wnba.services.team_branding import extract_team_logo


def _extract_teams(payload: dict[str, Any]) -> list[dict[str, Any]]:
    teams = []
    active_ids = set(CORE_TEAM_IDS) | set(EXPANSION_TEAM_IDS)
    for sport in payload.get("sports", []):
        for league in sport.get("leagues", []):
            for entry in league.get("teams", []):
                team = entry.get("team", {})
                if not team.get("id"):
                    continue
                tid = str(team["id"])
                abbr = team.get("abbreviation", "")
                logo = extract_team_logo(team, team_id=tid, team_abbr=abbr)

                teams.append(
                    {
                        "id": tid,
                        "abbreviation": abbr,
                        "display_name": team.get("displayName", ""),
                        "short_name": team.get("shortDisplayName", ""),
                        "location": team.get("location", ""),
                        "slug": team.get("slug", ""),
                        "uid": team.get("uid", ""),
                        "logo_url": logo,
                        "is_core": tid in CORE_TEAM_IDS,
                    }
                )
    return teams


def fetch_teams(client: EspnClient | None = None, save: bool = True) -> list[dict[str, Any]]:
    client = client or EspnClient()
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    payload = client.get_teams()
    teams = _extract_teams(payload)
    teams.sort(key=lambda t: t["abbreviation"])

    output = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "team_count": len(teams),
        "teams": teams,
    }

    if save:
        with open(TEAMS_FILE, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

    return teams


def load_teams() -> list[dict[str, Any]]:
    if not TEAMS_FILE.exists():
        return fetch_teams(save=True)
    with open(TEAMS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("teams", [])
