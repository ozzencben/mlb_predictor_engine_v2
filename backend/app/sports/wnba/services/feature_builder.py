"""
WNBA Feature Builder — Faz 2 (Guclendirilmis v2 + Stage 2 L10/H-A)

12 orijinal diferansiyel + 7 v2 + 5 Stage 2 = 24 TOPLAM feature:

Diferansiyel (Home - Away, L5):
  1-12. feature_net_rating_diff ... feature_hca_weight

Mutlak (Total model icin kritik):
  13-17. feature_home_off_abs ... feature_pace_abs

Rakip kalitesi & Form:
  18-19. feature_opp_quality_diff, feature_form_streak_diff

Stage 2 — L10 diferansiyel:
  20-22. feature_net_rating_diff_l10, feature_ppg_diff_l10, feature_efg_diff_l10

Stage 2 — Home/Away court split (Tyler spec, L5):
  23-24. feature_home_court_off_diff, feature_home_court_def_diff

Stage 3 — Star player / injury proxy:
  25-27. feature_star_out_impact_diff, feature_star_out_count_diff, feature_star_minutes_avail_diff
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, date, timedelta, timezone
from pathlib import Path
from typing import Any

from app.sports.wnba.services.config import DATA_DIR
from app.sports.wnba.services.elo import DEFAULT_ELO, get_pre_game_elo
from app.sports.wnba.services.star_player import compute_star_feature_diffs

PROCESSED_DIR = DATA_DIR / "processed"
FEATURES_FILE = PROCESSED_DIR / "game_features.json"

MIN_GAMES_REQUIRED = 5


# ---------------------------------------------------------------------------
# Yardimci: Rolling pencere hesabi
# ---------------------------------------------------------------------------

def _mean(values: list[float | None]) -> float | None:
    clean = [v for v in values if v is not None]
    if not clean:
        return None
    return round(sum(clean) / len(clean), 4)


def _rolling_stats(
    logs: list[dict[str, Any]],
    team_id: str,
    before_date: str,
    window: int,
    home_only: bool = False,
    away_only: bool = False,
) -> dict[str, Any] | None:
    """
    team_id takiminin before_date'ten onceki son `window` macinin ortalamasidir.
    home_only/away_only ile ic/dis saha filtresi uygulanir.
    """
    team_logs = [
        l for l in logs
        if l["team_id"] == team_id
        and (l.get("date") or "") < before_date
        and (not home_only or l["is_home"] == 1)
        and (not away_only or l["is_home"] == 0)
    ]
    if len(team_logs) < 1:
        return None

    recent = team_logs[-window:]
    if len(recent) < 1:
        return None

    return {
        "n": len(recent),
        "ppg": _mean([r["pts"] for r in recent]),
        "oppg": _mean([r["opp_pts"] for r in recent]),
        "efg_pct": _mean([r["efg_pct"] for r in recent]),
        "oefg_pct": _mean([r["opp_efg_pct"] for r in recent]),
        "tov_pct": _mean([r["tov_pct"] for r in recent]),
        "ortg": _mean([r["off_rtg"] for r in recent]),
        "drtg": _mean([r["def_rtg"] for r in recent]),
        "net_rtg": _mean([r["net_rtg"] for r in recent]),
        "pace": _mean([r["pace"] for r in recent]),
        "ts_pct": _mean([r["ts_pct"] for r in recent]),
        "ft_rate": _mean([r["ft_rate"] for r in recent]),
        "reb": _mean([r["reb"] for r in recent]),
        "ast_tov": _mean([r["ast_tov"] for r in recent]),
        "win_rate": _mean([float(r["won"]) for r in recent]),
    }


def _rest_days(logs: list[dict[str, Any]], team_id: str, before_date: str) -> int | None:
    """Son mactan before_date'e kadar gecen gun sayisi."""
    team_logs = [
        l for l in logs
        if l["team_id"] == team_id and (l.get("date") or "") < before_date
    ]
    if not team_logs:
        return None
    last_date_str = team_logs[-1]["date"]
    if not last_date_str:
        return None
    try:
        d0 = date.fromisoformat(last_date_str)
        d1 = date.fromisoformat(before_date)
        return (d1 - d0).days
    except ValueError:
        return None


def _b2b(logs: list[dict[str, Any]], team_id: str, before_date: str) -> int:
    """1 = dun de mac vardi (B2B), 0 = yok."""
    rest = _rest_days(logs, team_id, before_date)
    return 1 if rest == 1 else 0


def _h2h_edge(
    logs: list[dict[str, Any]],
    home_id: str,
    away_id: str,
    before_date: str,
    window: int = 10,
) -> tuple[float | None, list[dict[str, Any]]]:
    """
    Iki takim arasindaki son `window` mactan home_id'nin kazanma orani.
    Hem home hem away perspektifindeki karsilasmalari dahil eder.
    """
    h2h_logs = [
        l for l in logs
        if l["team_id"] == home_id
        and l["opp_id"] == away_id
        and (l.get("date") or "") < before_date
    ]
    if not h2h_logs:
        return None, []

    recent = h2h_logs[-window:]
    win_rate = _mean([float(r["won"]) for r in recent])
    summary = [
        {
            "date": r["date"],
            "home_team": r["team_abbr"] if r["is_home"] else r["opp_abbr"],
            "away_team": r["opp_abbr"] if r["is_home"] else r["team_abbr"],
            "score": f"{r['pts']}-{r['opp_pts']}" if r["is_home"] else f"{r['opp_pts']}-{r['pts']}",
            "winner": r["team_abbr"] if r["won"] else r["opp_abbr"],
        }
        for r in recent
    ]
    return win_rate, summary


def _hca_weight(
    logs: list[dict[str, Any]], team_id: str, before_date: str, window: int = 20
) -> float | None:
    """
    Ev sahibi olmanin avantaji:
    ic saha win_rate - dis saha win_rate (son window mac)
    """
    home_stats = _rolling_stats(logs, team_id, before_date, window, home_only=True)
    away_stats = _rolling_stats(logs, team_id, before_date, window, away_only=True)
    if not home_stats or not away_stats:
        return None
    hw = home_stats.get("win_rate")
    aw = away_stats.get("win_rate")
    if hw is None or aw is None:
        return None
    return round(hw - aw, 4)


def _diff(a: float | None, b: float | None) -> float | None:
    if a is None or b is None:
        return None
    return round(a - b, 4)


# ---------------------------------------------------------------------------
# YENI: Rakip Kalite Indeksi
# ---------------------------------------------------------------------------

def _opp_quality_index(
    logs: list[dict[str, Any]],
    team_id: str,
    before_date: str,
    window: int = 5,
) -> float | None:
    """
    Son `window` maçta karşilaşilan rakiplerin L5 ortalamasindaki PPG'sini döndürür.
    Bu, takim istatistiklerinin kaliteli rakiplere karsi mi yoksa zayif rakiplere
    karsi mi elde edildigini olcmek icin kullanilir.
    
    Yüksek deger = bu takim güçlü rakiplerle oynayarak istatistik yapti (daha degerli).
    Düsük deger = zayif rakiplere karsi elde edilmis istatistikler.
    """
    team_logs = [
        l for l in logs
        if l["team_id"] == team_id
        and (l.get("date") or "") < before_date
    ]
    if not team_logs:
        return None

    recent = team_logs[-window:]
    opp_ppgs: list[float] = []

    for game in recent:
        opp_id = game["opp_id"]
        game_date = game.get("date") or ""
        # Rakibin o tarihe kadar olan ortalama PPG'si (kendi onceki 5 macindan)
        opp_recent = _rolling_stats(logs, opp_id, game_date, 5)
        if opp_recent and opp_recent.get("ppg") is not None:
            opp_ppgs.append(opp_recent["ppg"])

    return _mean(opp_ppgs)


# ---------------------------------------------------------------------------
# YENI: Imzali Form Serisi
# ---------------------------------------------------------------------------

def _form_streak(
    logs: list[dict[str, Any]],
    team_id: str,
    before_date: str,
) -> int:
    """
    Pozitif = son N galibiyetin sayisi, Negatif = son N yenilginin sayisi.
    Ornek: +3 = son 3 mac galibiyet serisi, -2 = 2 mac yenilgi serisi.
    Maksimum +/-7 ile sinirlandirilir.
    """
    team_logs = [
        l for l in logs
        if l["team_id"] == team_id
        and (l.get("date") or "") < before_date
    ]
    if not team_logs:
        return 0

    streak = 0
    last_result = None
    for log in reversed(team_logs[-7:]):
        result = bool(log["won"])
        if last_result is None:
            last_result = result
            streak = 1 if result else -1
        elif result == last_result:
            streak += 1 if result else -1
        else:
            break

    return max(-7, min(7, streak))


def _feature_or_zero(diff_val: float | None) -> float:
    return diff_val if diff_val is not None else 0.0


def compute_match_features(
    logs: list[dict[str, Any]],
    home_id: str,
    away_id: str,
    before_date: str,
    elo_home: float,
    elo_away: float,
    player_logs: list[dict[str, Any]] | None = None,
    injuries_by_team: dict[str, list[dict[str, Any]]] | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """
    Tek mac icin model feature dict + UI context (L5/L10/H-A rolling).
    Yetersiz L5 gecmisi varsa (None, {}) doner.
    """
    home_l5 = _rolling_stats(logs, home_id, before_date, 5)
    away_l5 = _rolling_stats(logs, away_id, before_date, 5)

    if not home_l5 or not away_l5:
        return None, {}
    if home_l5["n"] < MIN_GAMES_REQUIRED or away_l5["n"] < MIN_GAMES_REQUIRED:
        return None, {}

    home_l10 = _rolling_stats(logs, home_id, before_date, 10)
    away_l10 = _rolling_stats(logs, away_id, before_date, 10)
    home_l5_home = _rolling_stats(logs, home_id, before_date, 5, home_only=True)
    away_l5_away = _rolling_stats(logs, away_id, before_date, 5, away_only=True)

    rest_home = _rest_days(logs, home_id, before_date)
    rest_away = _rest_days(logs, away_id, before_date)
    h2h_rate, h2h_games = _h2h_edge(logs, home_id, away_id, before_date, window=10)
    hca_home = _hca_weight(logs, home_id, before_date)

    home_opp_quality = _opp_quality_index(logs, home_id, before_date, window=5)
    away_opp_quality = _opp_quality_index(logs, away_id, before_date, window=5)
    home_streak = _form_streak(logs, home_id, before_date)
    away_streak = _form_streak(logs, away_id, before_date)

    home_ppg_abs = home_l5.get("ppg")
    away_ppg_abs = away_l5.get("ppg")
    home_def_abs = home_l5.get("oppg")
    away_def_abs = away_l5.get("oppg")
    pace_abs = _mean([home_l5.get("pace"), away_l5.get("pace")])

    features: dict[str, Any] = {
        "feature_net_rating_diff": _diff(home_l5.get("net_rtg"), away_l5.get("net_rtg")),
        "feature_elo_diff": round(elo_home - elo_away, 2),
        "feature_ppg_diff": _diff(home_l5.get("ppg"), away_l5.get("ppg")),
        "feature_efg_diff": _diff(home_l5.get("efg_pct"), away_l5.get("efg_pct")),
        "feature_tov_diff": _diff(home_l5.get("tov_pct"), away_l5.get("tov_pct")),
        "feature_pace_diff": _diff(home_l5.get("pace"), away_l5.get("pace")),
        "feature_ts_diff": _diff(home_l5.get("ts_pct"), away_l5.get("ts_pct")),
        "feature_reb_diff": _diff(home_l5.get("reb"), away_l5.get("reb")),
        "feature_rest_diff": _diff(rest_home, rest_away),
        "feature_b2b_fatigue": _b2b(logs, away_id, before_date) - _b2b(logs, home_id, before_date),
        "feature_h2h_edge": h2h_rate if h2h_rate is not None else 0.5,
        "feature_hca_weight": hca_home if hca_home is not None else 0.0,
        "feature_home_off_abs": home_ppg_abs if home_ppg_abs is not None else 0.0,
        "feature_away_off_abs": away_ppg_abs if away_ppg_abs is not None else 0.0,
        "feature_home_def_abs": home_def_abs if home_def_abs is not None else 0.0,
        "feature_away_def_abs": away_def_abs if away_def_abs is not None else 0.0,
        "feature_pace_abs": pace_abs if pace_abs is not None else 0.0,
        "feature_opp_quality_diff": _feature_or_zero(_diff(home_opp_quality, away_opp_quality)),
        "feature_form_streak_diff": float(home_streak - away_streak),
        "feature_net_rating_diff_l10": _feature_or_zero(
            _diff(
                home_l10.get("net_rtg") if home_l10 else None,
                away_l10.get("net_rtg") if away_l10 else None,
            )
        ),
        "feature_ppg_diff_l10": _feature_or_zero(
            _diff(
                home_l10.get("ppg") if home_l10 else None,
                away_l10.get("ppg") if away_l10 else None,
            )
        ),
        "feature_efg_diff_l10": _feature_or_zero(
            _diff(
                home_l10.get("efg_pct") if home_l10 else None,
                away_l10.get("efg_pct") if away_l10 else None,
            )
        ),
        "feature_home_court_off_diff": _feature_or_zero(
            _diff(
                home_l5_home.get("ortg") if home_l5_home else None,
                away_l5_away.get("ortg") if away_l5_away else None,
            )
        ),
        "feature_home_court_def_diff": _feature_or_zero(
            _diff(
                home_l5_home.get("drtg") if home_l5_home else None,
                away_l5_away.get("drtg") if away_l5_away else None,
            )
        ),
    }

    if player_logs:
        features.update(
            compute_star_feature_diffs(
                player_logs, home_id, away_id, before_date, injuries_by_team,
            )
        )
    else:
        features.update({
            "feature_star_out_impact_diff": 0.0,
            "feature_star_out_count_diff": 0.0,
            "feature_star_minutes_avail_diff": 0.0,
        })

    context: dict[str, Any] = {
        "home_l5": home_l5,
        "away_l5": away_l5,
        "home_l10": home_l10,
        "away_l10": away_l10,
        "home_l5_home": home_l5_home,
        "away_l5_away": away_l5_away,
        "h2h_last10": h2h_games,
        "elo_home": round(elo_home, 1),
        "elo_away": round(elo_away, 1),
        "rest_home": rest_home,
        "rest_away": rest_away,
    }
    return features, context


# ---------------------------------------------------------------------------
# Ana feature olusturucu
# ---------------------------------------------------------------------------

def build_game_features(
    logs: list[dict[str, Any]],
    elo_data: dict[str, Any],
    save: bool = True,
    player_logs: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    if player_logs is None:
        from app.sports.wnba.services.player_game_logs import load_player_game_logs
        player_logs = load_player_game_logs()

    # Logs'dan benzersiz mac listesi cikar (home satiri = ana kayit)
    seen: set[str] = set()
    home_logs: list[dict[str, Any]] = []
    for log in logs:
        if log["game_id"] not in seen and log["is_home"] == 1:
            home_logs.append(log)
            seen.add(log["game_id"])

    # Tarihe gore sirala
    home_logs.sort(key=lambda r: (r.get("date") or "", r["game_id"]))

    features_list: list[dict[str, Any]] = []
    skipped = 0

    for game_log in home_logs:
        gid = game_log["game_id"]
        game_date = game_log.get("date") or ""
        home_id = game_log["team_id"]
        away_id = game_log["opp_id"]

        elo_home = get_pre_game_elo(elo_data, gid, home_id)
        elo_away = get_pre_game_elo(elo_data, gid, away_id)

        features, ctx = compute_match_features(
            logs, home_id, away_id, game_date, elo_home, elo_away,
            player_logs=player_logs,
        )
        if features is None:
            skipped += 1
            continue

        # Hedef degerler
        targets = {
            "target_home_win": game_log["won"],
            "target_spread": game_log["margin"],
            "target_total": game_log["pts"] + game_log["opp_pts"],
        }

        entry: dict[str, Any] = {
            "game_id": gid,
            "date": game_date,
            "season": game_log.get("season"),
            "season_type": game_log.get("season_type"),
            "home_team_id": home_id,
            "away_team_id": away_id,
            "home_team_abbr": game_log["team_abbr"],
            "away_team_abbr": game_log["opp_abbr"],
            **targets,
            "features": features,
            **ctx,
        }
        features_list.append(entry)

    output = {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "total_games": len(features_list),
        "skipped_insufficient_history": skipped,
        "feature_names": list(features_list[0]["features"].keys()) if features_list else [],
        "games": features_list,
    }

    if save:
        with open(FEATURES_FILE, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"[OK] {len(features_list)} mac feature'i -> {FEATURES_FILE}")
        print(f"     (atlandi: {skipped} - yetersiz gecmis)")

    return features_list


def load_game_features() -> list[dict[str, Any]]:
    if not FEATURES_FILE.exists():
        raise FileNotFoundError("game_features.json bulunamadi. Once build_features calistirin.")
    return json.loads(FEATURES_FILE.read_text(encoding="utf-8"))["games"]
