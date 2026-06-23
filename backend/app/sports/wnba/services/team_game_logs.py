"""
Ham box score JSON'larından normalize takım-maç log üretir.

Her maç → 2 satır (home perspektifi + away perspektifi).
Her satırda: temel box score + advanced metrikler + hedef (target) değerler.
Çıktı: processed/team_game_logs.json
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.sports.wnba.services.config import (
    DATA_DIR,
    RAW_BOX_SCORES_DIR,
    RAW_GAMES_DIR,
)
from app.sports.wnba.services.metrics import compute_all

PROCESSED_DIR = DATA_DIR / "processed"
LOGS_FILE = PROCESSED_DIR / "team_game_logs.json"

# Box score'u olmayan ya da skor tutarsızlığı olan maçlar
SKIP_GAME_IDS = {"401018942"}  # 2018 iptal maç, 0-0


def _load_box(game_id: str) -> dict[str, Any] | None:
    p = RAW_BOX_SCORES_DIR / f"{game_id}.json"
    if not p.exists():
        return None
    data = json.loads(p.read_text(encoding="utf-8"))
    if not data.get("home_box") or not data.get("away_box"):
        return None
    if not data["home_box"] or not data["away_box"]:
        return None
    return data


def _game_entry(
    game: dict[str, Any],
    box: dict[str, Any],
    side: str,
) -> dict[str, Any]:
    """home veya away perspektifinden tek satır oluştur."""
    is_home = side == "home"
    opp_side = "away" if is_home else "home"

    team_id = game[f"{side}_team_id"]
    opp_id = game[f"{opp_side}_team_id"]
    team_abbr = game.get(f"{side}_team_abbr", "")
    opp_abbr = game.get(f"{opp_side}_team_abbr", "")

    my_box = box[f"{side}_box"]
    opp_box = box[f"{opp_side}_box"]

    my_score = game.get(f"{side}_score") or box.get(f"{side}_score")
    opp_score = game.get(f"{opp_side}_score") or box.get(f"{opp_side}_score")

    if my_score is None or opp_score is None:
        return {}

    my_score = int(my_score)
    opp_score = int(opp_score)
    won = 1 if my_score > opp_score else 0
    margin = my_score - opp_score

    period = box.get("period", 4)
    adv = compute_all(my_box, opp_box, period=period)

    return {
        "game_id": game["game_id"],
        "date": game.get("date"),
        "season": game.get("season"),
        "season_type": game.get("season_type", "unknown"),
        "team_id": team_id,
        "team_abbr": team_abbr,
        "opp_id": opp_id,
        "opp_abbr": opp_abbr,
        "is_home": int(is_home),
        # Skorlar
        "pts": my_score,
        "opp_pts": opp_score,
        "margin": margin,
        "won": won,
        # Temel box score
        "fgm": my_box.get("FGM"),
        "fga": my_box.get("FGA"),
        "fg_pct": my_box.get("FG_PCT"),
        "tpm": my_box.get("3PM"),
        "tpa": my_box.get("3PA"),
        "tp_pct": my_box.get("3P_PCT"),
        "ftm": my_box.get("FTM"),
        "fta": my_box.get("FTA"),
        "ft_pct": my_box.get("FT_PCT"),
        "oreb": my_box.get("OREB"),
        "drb": my_box.get("DRB"),
        "reb": my_box.get("REB"),
        "ast": my_box.get("AST"),
        "stl": my_box.get("STL"),
        "blk": my_box.get("BLK"),
        "tov": my_box.get("TOV"),
        "pf": my_box.get("PF"),
        # Advanced metrikler
        "poss": adv["poss"],
        "efg_pct": adv["efg_pct"],
        "ts_pct": adv["ts_pct"],
        "tov_pct": adv["tov_pct"],
        "orb_pct": adv["orb_pct"],
        "drb_pct": adv["drb_pct"],
        "off_rtg": adv["off_rtg"],
        "def_rtg": adv["def_rtg"],
        "net_rtg": adv["net_rtg"],
        "pace": adv["pace"],
        "ft_rate": adv["ft_rate"],
        "ast_tov": adv["ast_tov"],
        # Rakip advanced
        "opp_efg_pct": compute_all(opp_box, my_box, period=period)["efg_pct"],
        "opp_ts_pct": compute_all(opp_box, my_box, period=period)["ts_pct"],
        "opp_tov_pct": compute_all(opp_box, my_box, period=period)["tov_pct"],
        "opp_off_rtg": compute_all(opp_box, my_box, period=period)["off_rtg"],
    }


def build_team_game_logs(
    start_season: int = 2016,
    end_season: int = 2026,
    save: bool = True,
) -> list[dict[str, Any]]:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    logs: list[dict[str, Any]] = []
    skipped = 0

    for year in range(start_season, end_season + 1):
        games_path = RAW_GAMES_DIR / f"{year}.json"
        if not games_path.exists():
            continue
        games = json.loads(games_path.read_text(encoding="utf-8"))["games"]

        for game in games:
            gid = game["game_id"]
            if gid in SKIP_GAME_IDS:
                skipped += 1
                continue

            box = _load_box(gid)
            if box is None:
                skipped += 1
                continue

            for side in ("home", "away"):
                entry = _game_entry(game, box, side)
                if entry:
                    logs.append(entry)

    # Tarihe göre sırala
    logs.sort(key=lambda r: (r.get("date") or "", r.get("game_id", "")))

    output = {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "total_rows": len(logs),
        "skipped_games": skipped,
        "logs": logs,
    }

    if save:
        with open(LOGS_FILE, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"[OK] {len(logs)} satır -> {LOGS_FILE}")

    return logs


def load_team_game_logs() -> list[dict[str, Any]]:
    if not LOGS_FILE.exists():
        return build_team_game_logs(save=True)
    return json.loads(LOGS_FILE.read_text(encoding="utf-8"))["logs"]
