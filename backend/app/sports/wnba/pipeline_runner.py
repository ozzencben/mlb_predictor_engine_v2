"""
WNBA günlük pipeline orchestrator.

Çalıştırma:
  cd backend
  uv run python -m app.sports.wnba.pipeline_runner

Sıra:
  1. ESPN'den bugünkü fikstür → today_matches.json
  2. The Odds API'den oranlar → today_odds.json
  3. Dünün biten maçlarını raw/games ve box_scores'a ekle (incremental)
  4. Faz 2 feature'larını artımlı güncelle (team_game_logs, ELO)
  5. Bugünkü maçlar için canlı feature hesapla → today_predictions_raw.json
"""
from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone

from app.sports.wnba.services.config import DATA_DIR

logger = logging.getLogger("wnba.pipeline")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def _update_yesterday_games() -> int:
    """Dünün biten maçlarını box score havuzuna ekle (incremental)."""
    from datetime import timedelta
    from zoneinfo import ZoneInfo
    from app.sports.wnba.services.fetch_schedule import _fetch_scoreboard
    from app.sports.wnba.services.fetch_games import _parse_game_event
    from app.sports.wnba.services.config import RAW_GAMES_DIR
    from app.sports.wnba.services.fetch_box_scores import fetch_box_score, box_score_exists
    from app.sports.wnba.services.espn_client import EspnClient

    ET = ZoneInfo("America/New_York")
    yesterday = (datetime.now(ET) - timedelta(days=1)).strftime("%Y%m%d")
    year = yesterday[:4]

    client = EspnClient(delay=0.25)
    raw = _fetch_scoreboard(yesterday)
    events = raw.get("events", [])

    added = 0
    for event in events:
        parsed = _parse_game_event(event)
        if not parsed or not parsed.get("game_id"):
            continue
        gid = parsed["game_id"]
        if not parsed.get("season"):
            parsed["season"] = int(year)

        # Box score indir (atla)
        if not box_score_exists(gid):
            try:
                fetch_box_score(gid, client=client, game_meta=parsed, save=True, skip_existing=True)
                added += 1
            except Exception as e:
                logger.warning(f"Box score indirilemedi {gid}: {e}")

        # Games dosyasına ekle
        games_path = RAW_GAMES_DIR / f"{year}.json"
        if games_path.exists():
            data = json.loads(games_path.read_text(encoding="utf-8"))
            existing_ids = {g["game_id"] for g in data["games"]}
            if gid not in existing_ids:
                data["games"].append(parsed)
                data["game_count"] = len(data["games"])
                games_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    return added


def _compute_today_live_features() -> list[dict]:
    """
    Bugünün her maçı için mevcut team_game_logs + ELO üzerinden canlı feature hesapla.
    Faz 4 predict.py hazır olana kadar raw feature dict olarak döner.
    """
    from app.sports.wnba.services.fetch_schedule import load_today_matches
    from app.sports.wnba.services.team_game_logs import load_team_game_logs
    from app.sports.wnba.services.elo import load_elo_history, get_pre_game_elo, DEFAULT_ELO
    from app.sports.wnba.services.feature_builder import (
        _rolling_stats, _rest_days, _b2b, _h2h_edge, _hca_weight, _diff,
        _mean, MIN_GAMES_REQUIRED
    )
    from app.sports.wnba.services.wnba_odds import load_today_odds, match_odds_to_game

    matches = load_today_matches()
    if not matches:
        logger.info("Bugün maç yok veya today_matches.json boş.")
        return []

    logs = load_team_game_logs()
    elo_data = load_elo_history()
    odds_list = load_today_odds()

    results = []
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    for match in matches:
        if match.get("completed"):
            continue

        home_id = match["home_team_id"]
        away_id = match["away_team_id"]
        home_abbr = match["home_team_abbr"]
        away_abbr = match["away_team_abbr"]

        home_l5 = _rolling_stats(logs, home_id, today, 5)
        away_l5 = _rolling_stats(logs, away_id, today, 5)

        if not home_l5 or not away_l5:
            logger.warning(f"Yetersiz geçmiş: {home_abbr} vs {away_abbr}")
            continue
        if home_l5["n"] < MIN_GAMES_REQUIRED or away_l5["n"] < MIN_GAMES_REQUIRED:
            logger.warning(f"Min {MIN_GAMES_REQUIRED} maç geçmiş yok: {home_abbr} vs {away_abbr}")
            continue

        home_l10 = _rolling_stats(logs, home_id, today, 10)
        away_l10 = _rolling_stats(logs, away_id, today, 10)
        home_l5_home = _rolling_stats(logs, home_id, today, 5, home_only=True)
        away_l5_away = _rolling_stats(logs, away_id, today, 5, away_only=True)

        elo_home = elo_data["current"].get(home_id, DEFAULT_ELO)
        elo_away = elo_data["current"].get(away_id, DEFAULT_ELO)
        rest_home = _rest_days(logs, home_id, today)
        rest_away = _rest_days(logs, away_id, today)
        h2h_rate, h2h_games = _h2h_edge(logs, home_id, away_id, today, window=10)
        hca = _hca_weight(logs, home_id, today)

        from app.sports.wnba.services.feature_builder import (
            _opp_quality_index, _form_streak
        )
        home_opp_q = _opp_quality_index(logs, home_id, today, window=5)
        away_opp_q = _opp_quality_index(logs, away_id, today, window=5)
        home_streak = _form_streak(logs, home_id, today)
        away_streak = _form_streak(logs, away_id, today)

        home_ppg_abs = home_l5.get("ppg")
        away_ppg_abs = away_l5.get("ppg")
        home_def_abs = home_l5.get("oppg")
        away_def_abs = away_l5.get("oppg")
        pace_abs_val = _mean([home_l5.get("pace"), away_l5.get("pace")])

        features = {
            # Orijinal 12
            "feature_net_rating_diff": _diff(home_l5.get("net_rtg"), away_l5.get("net_rtg")),
            "feature_elo_diff": round(elo_home - elo_away, 2),
            "feature_ppg_diff": _diff(home_l5.get("ppg"), away_l5.get("ppg")),
            "feature_efg_diff": _diff(home_l5.get("efg_pct"), away_l5.get("efg_pct")),
            "feature_tov_diff": _diff(home_l5.get("tov_pct"), away_l5.get("tov_pct")),
            "feature_pace_diff": _diff(home_l5.get("pace"), away_l5.get("pace")),
            "feature_ts_diff": _diff(home_l5.get("ts_pct"), away_l5.get("ts_pct")),
            "feature_reb_diff": _diff(home_l5.get("reb"), away_l5.get("reb")),
            "feature_rest_diff": _diff(rest_home, rest_away),
            "feature_b2b_fatigue": _b2b(logs, away_id, today) - _b2b(logs, home_id, today),
            "feature_h2h_edge": h2h_rate if h2h_rate is not None else 0.5,
            "feature_hca_weight": hca if hca is not None else 0.0,
            # Yeni 7
            "feature_home_off_abs": home_ppg_abs if home_ppg_abs is not None else 0.0,
            "feature_away_off_abs": away_ppg_abs if away_ppg_abs is not None else 0.0,
            "feature_home_def_abs": home_def_abs if home_def_abs is not None else 0.0,
            "feature_away_def_abs": away_def_abs if away_def_abs is not None else 0.0,
            "feature_pace_abs": pace_abs_val if pace_abs_val is not None else 0.0,
            "feature_opp_quality_diff": _diff(home_opp_q, away_opp_q) if (home_opp_q and away_opp_q) else 0.0,
            "feature_form_streak_diff": float(home_streak - away_streak),
        }

        odds = match_odds_to_game(odds_list, home_abbr, away_abbr)

        results.append({
            "game_id": match["game_id"],
            "date": match["date"],
            "name": match["name"],
            "home_team_id": home_id,
            "away_team_id": away_id,
            "home_team_abbr": home_abbr,
            "away_team_abbr": away_abbr,
            "home_team_name": match["home_team_name"],
            "away_team_name": match["away_team_name"],
            "home_logo": match.get("home_logo"),
            "away_logo": match.get("away_logo"),
            "venue": match.get("venue"),
            "features": features,
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
            "odds": odds,
        })

    return results


def run_pipeline(skip_yesterday: bool = False) -> dict:
    logger.info("=" * 50)
    logger.info("WNBA Günlük Pipeline Başlıyor")
    logger.info("=" * 50)

    from app.sports.wnba.services.fetch_schedule import fetch_today_matches
    from app.sports.wnba.services.wnba_odds import fetch_wnba_odds
    from app.sports.wnba.services.team_game_logs import build_team_game_logs
    from app.sports.wnba.services.elo import build_elo_history

    # 1. Bugünkü fikstür
    logger.info("[1/5] ESPN fikstür çekiliyor...")
    matches = fetch_today_matches(save=True)
    logger.info(f"  -> {len(matches)} maç")

    # 2. Odds
    logger.info("[2/5] The Odds API WNBA oranları çekiliyor...")
    odds = fetch_wnba_odds(save=True)
    logger.info(f"  -> {len(odds)} maç oranı")

    # 3. Dünün maçlarını ekle
    added = 0
    if not skip_yesterday:
        logger.info("[3/5] Dünün biten maçları güncelleniyor...")
        try:
            added = _update_yesterday_games()
            logger.info(f"  -> {added} yeni box score eklendi")
        except Exception as e:
            logger.error(f"  Dün güncelleme hatası: {e}")

    # 4. Faz 2 feature'larını artımlı yenile
    logger.info("[4/5] Feature log ve ELO güncelleniyor...")
    try:
        logs = build_team_game_logs(save=True)
        elo_data = build_elo_history(logs, save=True)
        logger.info(f"  -> {len(logs)//2} maç logu, {elo_data['total_games']} ELO güncellendi")
    except Exception as e:
        logger.error(f"  Feature güncelleme hatası: {e}")

    # 5. Bugünkü canlı feature'lar
    logger.info("[5/6] Bugunku maclar icin feature hesaplaniyor...")
    live_features = _compute_today_live_features()
    logger.info(f"  -> {len(live_features)} mac feature hazir")

    # Kaydet
    raw_predictions_file = DATA_DIR / "today_predictions_raw.json"
    output = {
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "match_count": len(live_features),
        "matches": live_features,
    }
    with open(raw_predictions_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # 6. Model tahminleri (Faz 4)
    logger.info("[6/6] Model tahminleri uretiliyor...")
    predictions = []
    try:
        from app.sports.wnba.models.predict import generate_predictions, reset_model_cache
        reset_model_cache()
        predictions = generate_predictions(save=True)
        logger.info(f"  -> {len(predictions)} tahmin kaydedildi")
    except FileNotFoundError:
        logger.warning("  Model bulunamadi. 'train_model.py' calistirilmali.")
    except Exception as e:
        logger.error(f"  Tahmin hatasi: {e}")

    logger.info("Pipeline tamamlandi.")
    return {
        "date": output["date"],
        "matches": len(matches),
        "odds": len(odds),
        "new_box_scores": added,
        "features_computed": len(live_features),
        "predictions": len(predictions),
    }


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="WNBA günlük pipeline")
    parser.add_argument("--skip-yesterday", action="store_true")
    args = parser.parse_args(argv)
    run_pipeline(skip_yesterday=args.skip_yesterday)
    return 0


if __name__ == "__main__":
    sys.exit(main())
