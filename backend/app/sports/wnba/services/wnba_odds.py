"""
WNBA odds çekici — The Odds API, sport key: basketball_wnba
MLB OddsProvider'ın WNBA adaptörü.
"""
from __future__ import annotations

import json
import os
import tempfile
from typing import Any

import requests

from app.core.config import settings
from app.sports.wnba.services.config import DATA_DIR
from app.sports.wnba.services.http import make_requests_session

ODDS_FILE = DATA_DIR / "today_odds.json"
SPORT_KEY = "basketball_wnba"
BOOKMAKERS = "fanduel,draftkings,caesars,betmgm,fanatics,pointsbetus"
BASE_URL = f"https://api.the-odds-api.com/v4/sports/{SPORT_KEY}/odds"

# ESPN abbreviation → The Odds API tam isim eşlemesi
TEAM_NAME_MAP: dict[str, list[str]] = {
    "ATL": ["Atlanta Dream"],
    "CHI": ["Chicago Sky"],
    "CON": ["Connecticut Sun"],
    "DAL": ["Dallas Wings"],
    "IND": ["Indiana Fever"],
    "LV": ["Las Vegas Aces"],
    "LA": ["Los Angeles Sparks"],
    "MIN": ["Minnesota Lynx"],
    "NY": ["New York Liberty"],
    "PHX": ["Phoenix Mercury"],
    "SEA": ["Seattle Storm"],
    "WSH": ["Washington Mystics"],
    "GS": ["Golden State Valkyries"],
    "POR": ["Portland Fire"],
    "TOR": ["Toronto Tempo"],
}

# Ters eşleme: "Las Vegas Aces" → "LV"
_REVERSE_MAP: dict[str, str] = {}
for abbr, names in TEAM_NAME_MAP.items():
    for name in names:
        _REVERSE_MAP[name.lower()] = abbr


def _abbr_from_name(name: str) -> str | None:
    return _REVERSE_MAP.get(name.strip().lower())


def _atomic_save(path: str, data: Any) -> None:
    dir_name = os.path.dirname(path)
    fd, tmp_path = tempfile.mkstemp(dir=dir_name, suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, path)
    except Exception:
        os.remove(tmp_path)
        raise


def fetch_wnba_odds(save: bool = True) -> list[dict[str, Any]]:
    """
    The Odds API'den WNBA h2h, spreads, totals oranlarını çeker.
    Returns: Normalize odds listesi.
    """
    api_key = settings.ODDS_API_KEY
    if not api_key:
        print("[WARN] [WNBAOdds] ODDS_API_KEY tanimli degil, odds atlaniyor.")
        return []

    params = {
        "apiKey": api_key,
        "regions": "us",
        "markets": "h2h,spreads,totals",
        "bookmakers": BOOKMAKERS,
        "oddsFormat": "american",
    }

    try:
        resp = make_requests_session().get(BASE_URL, params=params, timeout=15)
        if resp.status_code == 422:
            print("[WARN] [WNBAOdds] 422 - Plan bu marketleri desteklemiyor.")
            return []
        if resp.status_code == 401:
            print("[WARN] [WNBAOdds] 401 - API key gecersiz.")
            return []
        if resp.status_code == 429:
            print("[WARN] [WNBAOdds] 429 - Kota doldu.")
            return []
        resp.raise_for_status()
        raw_games = resp.json()
    except requests.RequestException as e:
        print(f"[ERR] [WNBAOdds] Istek hatasi: {e}")
        return []

    if not raw_games:
        print("[INFO] [WNBAOdds] Su an aktif WNBA maci/orani yok.")
        return []

    normalized = [_normalize_game(g) for g in raw_games]
    normalized = [g for g in normalized if g]

    if save:
        _atomic_save(str(ODDS_FILE), normalized)
        print(f"[OK] [WNBAOdds] {len(normalized)} mac orani kaydedildi.")

    return normalized


def _normalize_game(game: dict[str, Any]) -> dict[str, Any] | None:
    """Ham Odds API maçını ESPN-uyumlu normalize formata çevirir."""
    home_name = game.get("home_team", "")
    away_name = game.get("away_team", "")

    home_abbr = _abbr_from_name(home_name)
    away_abbr = _abbr_from_name(away_name)

    result: dict[str, Any] = {
        "game_id_odds": game.get("id", ""),
        "commence_time": game.get("commence_time", ""),
        "home_team": home_name,
        "away_team": away_name,
        "home_abbr": home_abbr,
        "away_abbr": away_abbr,
        "moneyline_home": None,
        "moneyline_away": None,
        "spread_home": None,
        "spread_away": None,
        "spread_line": None,
        "total_line": None,
        "total_over": None,
        "total_under": None,
    }

    bookmakers = game.get("bookmakers", [])
    if not bookmakers:
        return result

    # FanDuel > DraftKings > ilk bookmaker
    priority = ["fanduel", "draftkings", "caesars", "betmgm"]
    bk = None
    for pkey in priority:
        bk = next((b for b in bookmakers if b.get("key") == pkey), None)
        if bk:
            break
    if not bk:
        bk = bookmakers[0]

    for market in bk.get("markets", []):
        key = market.get("key")
        outcomes = market.get("outcomes", [])

        if key == "h2h":
            for o in outcomes:
                if o.get("name", "").lower() == home_name.lower():
                    result["moneyline_home"] = o.get("price")
                elif o.get("name", "").lower() == away_name.lower():
                    result["moneyline_away"] = o.get("price")

        elif key == "spreads":
            for o in outcomes:
                if o.get("name", "").lower() == home_name.lower():
                    result["spread_home"] = o.get("price")
                    result["spread_line"] = o.get("point")
                elif o.get("name", "").lower() == away_name.lower():
                    result["spread_away"] = o.get("price")

        elif key == "totals":
            for o in outcomes:
                if o.get("name", "").lower() == "over":
                    result["total_over"] = o.get("price")
                    result["total_line"] = o.get("point")
                elif o.get("name", "").lower() == "under":
                    result["total_under"] = o.get("price")

    return result


def load_today_odds() -> list[dict[str, Any]]:
    if not ODDS_FILE.exists():
        return []
    return json.loads(ODDS_FILE.read_text(encoding="utf-8"))


def match_odds_to_game(
    odds_list: list[dict[str, Any]],
    home_abbr: str,
    away_abbr: str,
) -> dict[str, Any] | None:
    """ESPN abbreviation üzerinden odds kaydını bul."""
    for o in odds_list:
        if (o.get("home_abbr") == home_abbr and o.get("away_abbr") == away_abbr):
            return o
        if (o.get("home_abbr") == away_abbr and o.get("away_abbr") == home_abbr):
            # Flip
            return {
                **o,
                "home_abbr": away_abbr,
                "away_abbr": home_abbr,
                "moneyline_home": o.get("moneyline_away"),
                "moneyline_away": o.get("moneyline_home"),
                "spread_line": -o["spread_line"] if o.get("spread_line") is not None else None,
                "spread_home": o.get("spread_away"),
                "spread_away": o.get("spread_home"),
            }
    return None
