"""
WNBA Takım ELO sistemi.

- Başlangıç ELO: 1500
- K faktörü: 20
- Margin of Victory multiplier: log(|margin| + 1) * 0.8  (NBA research)
- Sezon başında önceki ELO'nun %75'i + 1500'ün %25'i (regresyon)
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.sports.wnba.services.config import (
    CORE_TEAM_IDS,
    DATA_DIR,
    EXPANSION_TEAM_IDS,
    HISTORICAL_TEAM_NAMES,
)

PROCESSED_DIR = DATA_DIR / "processed"
ELO_HISTORY_FILE = PROCESSED_DIR / "team_elo_history.json"

DEFAULT_ELO = 1500.0
K = 20.0
SEASON_REGRESSION = 0.75  # yeni sezonda önceki ELO'nun tutulma oranı


def _team_label(team_id: str) -> str:
    if team_id in CORE_TEAM_IDS:
        return CORE_TEAM_IDS[team_id]
    if team_id in EXPANSION_TEAM_IDS:
        return EXPANSION_TEAM_IDS[team_id]
    if team_id in HISTORICAL_TEAM_NAMES:
        return HISTORICAL_TEAM_NAMES[team_id]
    return f"ID:{team_id}"


def _expected(elo_a: float, elo_b: float) -> float:
    return 1.0 / (1.0 + 10.0 ** ((elo_b - elo_a) / 400.0))


def _mov_multiplier(margin: int) -> float:
    """Margin of Victory çarpanı — büyük farkları öldürür."""
    import math
    return math.log(abs(margin) + 1) * 0.8


def build_elo_history(
    logs: list[dict[str, Any]],
    save: bool = True,
) -> dict[str, Any]:
    """
    Takım-maç log'undan kronolojik ELO geçmişi üret.
    Her maç girişine pre-game ELO eklenir (data leakage yok).

    Returns:
        {
          "by_game":  {game_id: {team_id: elo_before_game}},
          "current":  {team_id: current_elo},
          "history":  [{date, team_id, elo_before, elo_after, ...}]
        }
    """
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    current_elo: dict[str, float] = {}
    current_season: int | None = None

    by_game: dict[str, dict[str, float]] = {}
    history: list[dict[str, Any]] = []

    seen_games: set[str] = set()

    # Logs zaten tarihe göre sıralı (team_game_logs.py sıralar)
    # Ama her maçta 2 satır var (home + away) — tek işle
    game_map: dict[str, tuple[dict, dict]] = {}

    for log in logs:
        gid = log["game_id"]
        if gid not in game_map:
            game_map[gid] = [log]
        else:
            game_map[gid].append(log)

    # Tarihe göre benzersiz maç listesi
    unique_games: list[tuple[str, str, dict, dict]] = []
    added: set[str] = set()
    for log in logs:
        gid = log["game_id"]
        if gid in added:
            continue
        pair = game_map.get(gid, [])
        if len(pair) != 2:
            continue
        home_log = next((p for p in pair if p["is_home"] == 1), None)
        away_log = next((p for p in pair if p["is_home"] == 0), None)
        if not home_log or not away_log:
            continue
        unique_games.append((gid, log["date"] or "", home_log, away_log))
        added.add(gid)

    for gid, date_str, home_log, away_log in unique_games:
        season = home_log.get("season")
        home_id = home_log["team_id"]
        away_id = away_log["team_id"]

        # Sezon değişiminde ELO regresyonu
        if season and season != current_season:
            current_season = season
            for tid in list(current_elo.keys()):
                current_elo[tid] = SEASON_REGRESSION * current_elo[tid] + (1 - SEASON_REGRESSION) * DEFAULT_ELO

        elo_home = current_elo.get(home_id, DEFAULT_ELO)
        elo_away = current_elo.get(away_id, DEFAULT_ELO)

        # Maç öncesi ELO kaydet
        if gid not in by_game:
            by_game[gid] = {}
        by_game[gid][home_id] = round(elo_home, 2)
        by_game[gid][away_id] = round(elo_away, 2)

        # Sonuç
        margin = home_log["margin"]
        home_won = home_log["won"]

        exp_home = _expected(elo_home, elo_away)
        actual_home = float(home_won)
        mov = _mov_multiplier(margin) if home_won else _mov_multiplier(-margin)
        k_adj = K * mov

        delta_home = k_adj * (actual_home - exp_home)
        new_elo_home = elo_home + delta_home
        new_elo_away = elo_away - delta_home

        current_elo[home_id] = new_elo_home
        current_elo[away_id] = new_elo_away

        history.append({
            "game_id": gid,
            "date": date_str,
            "season": season,
            "home_id": home_id,
            "away_id": away_id,
            "elo_home_before": round(elo_home, 2),
            "elo_away_before": round(elo_away, 2),
            "elo_home_after": round(new_elo_home, 2),
            "elo_away_after": round(new_elo_away, 2),
            "home_margin": margin,
            "home_won": home_won,
        })

    result = {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "total_games": len(unique_games),
        "current": {k: round(v, 2) for k, v in sorted(current_elo.items())},
        "by_game": by_game,
        "history": history,
    }

    if save:
        with open(ELO_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f"[OK] ELO geçmişi -> {ELO_HISTORY_FILE}")
        print("  Mevcut ELO sıralaması:")
        for tid, elo in sorted(current_elo.items(), key=lambda x: -x[1]):
            print(f"    {_team_label(tid)} ({tid}): {elo:.1f}")

    return result


def load_elo_history() -> dict[str, Any]:
    if not ELO_HISTORY_FILE.exists():
        raise FileNotFoundError("ELO geçmişi bulunamadı. Önce build_features çalıştırın.")
    return json.loads(ELO_HISTORY_FILE.read_text(encoding="utf-8"))


def get_pre_game_elo(elo_data: dict[str, Any], game_id: str, team_id: str) -> float:
    return elo_data["by_game"].get(game_id, {}).get(team_id, DEFAULT_ELO)
