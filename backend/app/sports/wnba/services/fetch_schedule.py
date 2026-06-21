"""
Günlük WNBA fikstürü ESPN'den çeker ve today_matches.json olarak kaydeder.
Her maça günlük pipeline'da canlı feature hesabı için gerekli context ekler.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo

import requests

from app.sports.wnba.services.config import DATA_DIR, ESPN_BASE

TODAY_MATCHES_FILE = DATA_DIR / "today_matches.json"
ET = ZoneInfo("America/New_York")

_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (compatible; WNBAScheduleFetcher/1.0)",
}


def _fetch_scoreboard(date_str: str | None = None) -> dict[str, Any]:
    """ESPN WNBA scoreboard. date_str = 'YYYYMMDD', None = bugün."""
    params = {}
    if date_str:
        params["dates"] = date_str
    resp = requests.get(f"{ESPN_BASE}/scoreboard", headers=_HEADERS, params=params, timeout=20)
    resp.raise_for_status()
    return resp.json()


def _parse_game(event: dict[str, Any]) -> dict[str, Any] | None:
    comp = (event.get("competitions") or [{}])[0]
    competitors = comp.get("competitors", [])
    if len(competitors) != 2:
        return None

    home = away = None
    for c in competitors:
        team = c.get("team", {})
        rec = {
            "team_id": str(team.get("id", "")),
            "team_abbr": team.get("abbreviation", ""),
            "team_name": team.get("displayName", ""),
            "logo": next(
                (l.get("href") for l in team.get("logos", []) if "default" in l.get("rel", [])),
                None,
            ),
            "score": c.get("score"),
        }
        if c.get("homeAway") == "home":
            home = rec
        else:
            away = rec

    if not home or not away:
        return None

    status = comp.get("status", {})
    status_type = status.get("type", {})
    state = status_type.get("name", "unknown")      # "STATUS_SCHEDULED" / "STATUS_IN_PROGRESS" / "STATUS_FINAL"
    completed = status_type.get("completed", False)
    display_clock = status.get("displayClock", "")
    period = status.get("period", 0)

    date_str = event.get("date", "")
    game_date = date_str[:10] if date_str else None

    venue = comp.get("venue", {})

    return {
        "game_id": str(event.get("id", "")),
        "name": event.get("name", ""),
        "date": game_date,
        "date_iso": date_str,
        "state": state,
        "completed": completed,
        "period": period,
        "clock": display_clock,
        "home_team_id": home["team_id"],
        "away_team_id": away["team_id"],
        "home_team_abbr": home["team_abbr"],
        "away_team_abbr": away["team_abbr"],
        "home_team_name": home["team_name"],
        "away_team_name": away["team_name"],
        "home_logo": home["logo"],
        "away_logo": away["logo"],
        "home_score": home["score"],
        "away_score": away["score"],
        "venue": venue.get("fullName", ""),
        "city": venue.get("address", {}).get("city", ""),
    }


def fetch_today_matches(
    date_str: str | None = None,
    save: bool = True,
) -> list[dict[str, Any]]:
    """
    Bugünün (veya verilen tarihin) WNBA maçlarını ESPN'den çeker.

    date_str: 'YYYYMMDD' formatında tarih (None = bugün ET)
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if date_str is None:
        now_et = datetime.now(ET)
        date_str = now_et.strftime("%Y%m%d")
        today_iso = now_et.strftime("%Y-%m-%d")
    else:
        today_iso = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"

    raw = _fetch_scoreboard(date_str)
    events = raw.get("events", [])

    matches = []
    for event in events:
        parsed = _parse_game(event)
        if parsed:
            matches.append(parsed)

    output = {
        "date": today_iso,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "game_count": len(matches),
        "matches": matches,
    }

    if save:
        with open(TODAY_MATCHES_FILE, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

    return matches


def load_today_matches() -> list[dict[str, Any]]:
    if not TODAY_MATCHES_FILE.exists():
        return []
    return json.loads(TODAY_MATCHES_FILE.read_text(encoding="utf-8")).get("matches", [])
