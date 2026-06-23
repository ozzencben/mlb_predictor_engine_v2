"""Takim logo URL cozumleme — ESPN API degisikliklerine dayanikli."""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from app.sports.wnba.services.config import TEAMS_FILE

# ESPN CDN: kucuk harf kisaltma (GS -> gs, CON -> conn degil con)
_ABBR_CDN_OVERRIDES: dict[str, str] = {
    "CON": "con",
    "CONN": "con",
    "GS": "gs",
    "LV": "lv",
    "LA": "la",
    "NY": "ny",
    "PHX": "phx",
    "WSH": "wsh",
    "MIN": "min",
    "SEA": "sea",
    "ATL": "atl",
    "CHI": "chi",
    "DAL": "dal",
    "IND": "ind",
    "POR": "por",
    "TOR": "tor",
}


def _cdn_logo(abbr: str) -> str | None:
    if not abbr:
        return None
    slug = _ABBR_CDN_OVERRIDES.get(abbr.upper(), abbr.lower())
    return f"https://a.espncdn.com/i/teamlogos/wnba/500/{slug}.png"


@lru_cache(maxsize=1)
def _logo_by_id() -> dict[str, str]:
    if not TEAMS_FILE.exists():
        return {}
    data = json.loads(TEAMS_FILE.read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    for team in data.get("teams", []):
        tid = str(team.get("id", ""))
        logo = team.get("logo_url")
        if tid and logo:
            out[tid] = logo
    return out


def extract_team_logo(team: dict[str, Any], team_id: str = "", team_abbr: str = "") -> str | None:
    """
    ESPN takim objesinden logo URL cikarir.
    Oncelik: team.logo (yeni API) -> logos[] -> teams.json -> CDN fallback.
    """
    direct = team.get("logo")
    if isinstance(direct, str) and direct.startswith("http"):
        return direct

    for entry in team.get("logos", []):
        rel = entry.get("rel") or []
        if "default" in rel or rel == ["full", "default"]:
            href = entry.get("href")
            if href:
                return href

    logos = team.get("logos") or []
    if logos and logos[0].get("href"):
        return logos[0]["href"]

    tid = team_id or str(team.get("id", ""))
    abbr = team_abbr or team.get("abbreviation", "")
    cached = _logo_by_id().get(tid)
    if cached:
        return cached

    return _cdn_logo(abbr)
