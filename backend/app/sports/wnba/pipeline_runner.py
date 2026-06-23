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
import os
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.sports.wnba.services.config import DATA_DIR, DEFAULT_PIPELINE_LOOKBACK_DAYS

logger = logging.getLogger("wnba.pipeline")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

ET = ZoneInfo("America/New_York")


def _today_et() -> str:
    return datetime.now(ET).strftime("%Y-%m-%d")


def _sync_recent_games(lookback_days: int = DEFAULT_PIPELINE_LOOKBACK_DAYS) -> int:
    """
    Son N gundeki biten maclari raw/games ve box_scores'a ekle.
    PC kapandiginda veya pipeline atlandiginda olusan bosluklari kapatir.
    """
    from datetime import timedelta
    from zoneinfo import ZoneInfo
    from app.sports.wnba.services.fetch_schedule import _fetch_scoreboard
    from app.sports.wnba.services.fetch_games import _parse_game_event
    from app.sports.wnba.services.config import RAW_GAMES_DIR
    from app.sports.wnba.services.fetch_box_scores import fetch_box_score, box_score_exists
    from app.sports.wnba.services.espn_client import EspnClient

    ET = ZoneInfo("America/New_York")
    client = EspnClient(delay=0.25)
    now = datetime.now(ET)
    added = 0

    for delta in range(1, lookback_days + 1):
        day = (now - timedelta(days=delta)).strftime("%Y%m%d")
        year = day[:4]
        try:
            raw = _fetch_scoreboard(day, client=client)
        except Exception as e:
            logger.warning(f"Scoreboard alinamadi {day}: {e}")
            continue

        for event in raw.get("events", []):
            parsed = _parse_game_event(event)
            if not parsed or not parsed.get("game_id"):
                continue
            gid = parsed["game_id"]
            if not parsed.get("season"):
                parsed["season"] = int(year)

            if not box_score_exists(gid):
                try:
                    fetch_box_score(gid, client=client, game_meta=parsed, save=True, skip_existing=True)
                    added += 1
                except Exception as e:
                    logger.warning(f"Box score indirilemedi {gid}: {e}")

            games_path = RAW_GAMES_DIR / f"{year}.json"
            if games_path.exists():
                data = json.loads(games_path.read_text(encoding="utf-8"))
                existing_ids = {g["game_id"] for g in data["games"]}
                if gid not in existing_ids:
                    data["games"].append(parsed)
                    data["game_count"] = len(data["games"])
                    games_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    return added


def _update_yesterday_games() -> int:
    """Geriye uyumluluk: son 1 gun."""
    return _sync_recent_games(lookback_days=1)


def _compute_today_live_features() -> list[dict]:
    """
    Bugünün her maçı için mevcut team_game_logs + ELO üzerinden canlı feature hesapla.
    Faz 4 predict.py hazır olana kadar raw feature dict olarak döner.
    """
    from app.sports.wnba.services.fetch_schedule import load_today_matches
    from app.sports.wnba.services.team_game_logs import load_team_game_logs
    from app.sports.wnba.services.elo import load_elo_history, DEFAULT_ELO
    from app.sports.wnba.services.feature_builder import compute_match_features
    from app.sports.wnba.services.player_game_logs import load_player_game_logs
    from app.sports.wnba.services.star_player import load_injuries
    from app.sports.wnba.services.wnba_odds import load_today_odds, match_odds_to_game

    matches = load_today_matches()
    if not matches:
        logger.info("Bugün maç yok veya today_matches.json boş.")
        return []

    logs = load_team_game_logs()
    elo_data = load_elo_history()
    odds_list = load_today_odds()
    player_logs = load_player_game_logs()
    injuries_by_team = load_injuries()

    results = []
    today = _today_et()

    for match in matches:
        if match.get("completed"):
            continue

        home_id = match["home_team_id"]
        away_id = match["away_team_id"]
        home_abbr = match["home_team_abbr"]
        away_abbr = match["away_team_abbr"]

        elo_home = elo_data["current"].get(home_id, DEFAULT_ELO)
        elo_away = elo_data["current"].get(away_id, DEFAULT_ELO)

        features, ctx = compute_match_features(
            logs, home_id, away_id, today, elo_home, elo_away,
            player_logs=player_logs,
            injuries_by_team=injuries_by_team,
        )
        if features is None:
            logger.warning(f"Yetersiz geçmiş: {home_abbr} vs {away_abbr}")
            continue

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
            **ctx,
            "odds": odds,
        })

    return results


def run_pipeline(skip_yesterday: bool = False, lookback_days: int = DEFAULT_PIPELINE_LOOKBACK_DAYS) -> dict:
    from app.sports.wnba.services.beta_ops import archive_past_data, evaluate_today_accuracy

    logger.info("=" * 50)
    logger.info("WNBA Günlük Pipeline Başlıyor")
    logger.info("=" * 50)

    logger.info("[0/7] Eski tahminler arsivleniyor...")
    archive_past_data()

    from app.sports.wnba.services.fetch_schedule import fetch_today_matches
    from app.sports.wnba.services.wnba_odds import fetch_wnba_odds
    from app.sports.wnba.services.team_game_logs import build_team_game_logs
    from app.sports.wnba.services.elo import build_elo_history
    from app.sports.wnba.services.feature_builder import build_game_features

    # 1. Bugünkü fikstür
    logger.info("[1/7] ESPN fikstür çekiliyor...")
    matches = fetch_today_matches(save=True)
    logger.info(f"  -> {len(matches)} maç")

    # 2. Odds
    logger.info("[2/7] The Odds API WNBA oranlari cekiliyor...")
    odds = fetch_wnba_odds(save=True)
    logger.info(f"  -> {len(odds)} mac orani")

    # 2b. ESPN injury feed
    logger.info("[2b/7] ESPN injury feed cekiliyor...")
    try:
        from app.sports.wnba.services.star_player import fetch_wnba_injuries
        inj = fetch_wnba_injuries(save=True)
        logger.info(f"  -> {inj.get('team_count', 0)} takim injury")
    except Exception as e:
        logger.warning(f"  Injury feed hatasi: {e}")

    # 3. Son N gundeki eksik maclari tamamla
    added = 0
    if not skip_yesterday:
        logger.info(f"[3/7] Son {lookback_days} gunun maclari senkronize ediliyor...")
        try:
            added = _sync_recent_games(lookback_days=lookback_days)
            logger.info(f"  -> {added} yeni box score eklendi")
        except Exception as e:
            logger.error(f"  Mac senkronizasyon hatasi: {e}")

    # 4. Faz 2 feature'larini artimli yenile
    logger.info("[4/7] Feature log, ELO, player logs ve game_features guncelleniyor...")
    try:
        logs = build_team_game_logs(save=True)
        elo_data = build_elo_history(logs, save=True)
        from app.sports.wnba.services.player_game_logs import build_player_game_logs
        build_player_game_logs(fetch_missing=True, save=True)
        features = build_game_features(logs, elo_data, save=True)
        logger.info(
            f"  -> {len(logs)//2} mac logu, {elo_data['total_games']} ELO, "
            f"{len(features)} game_features guncellendi"
        )
    except Exception as e:
        logger.error(f"  Feature guncelleme hatasi: {e}")

    # 5. Bugünkü canlı feature'lar
    logger.info("[5/7] Bugunku maclar icin feature hesaplaniyor...")
    live_features = _compute_today_live_features()
    logger.info(f"  -> {len(live_features)} mac feature hazir")

    # Kaydet
    raw_predictions_file = DATA_DIR / "today_predictions_raw.json"
    output = {
        "date": _today_et(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "match_count": len(live_features),
        "matches": live_features,
    }
    with open(raw_predictions_file, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    # 6. Model tahminleri (Faz 4)
    logger.info("[6/7] Model tahminleri uretiliyor...")
    predictions = []
    try:
        from app.sports.wnba.models.predict import generate_predictions, reset_model_cache
        reset_model_cache()
        skip_ai = os.getenv("WNBA_SKIP_AI", "").lower() in ("1", "true", "yes")
        predictions = generate_predictions(save=True, skip_ai=skip_ai)
        logger.info(f"  -> {len(predictions)} tahmin kaydedildi")
    except FileNotFoundError:
        logger.warning("  Model bulunamadi. 'train_model.py' calistirilmali.")
    except Exception as e:
        logger.error(f"  Tahmin hatasi: {e}")

    logger.info("[7/7] Tamamlanan maclar degerlendiriliyor...")
    try:
        evaluate_today_accuracy(save=True)
    except Exception as e:
        logger.warning(f"  Accuracy degerlendirme hatasi: {e}")

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
    parser.add_argument(
        "--lookback-days",
        type=int,
        default=DEFAULT_PIPELINE_LOOKBACK_DAYS,
        help=f"Kac gun geriye eksik mac aransin (varsayilan: {DEFAULT_PIPELINE_LOOKBACK_DAYS})",
    )
    args = parser.parse_args(argv)
    run_pipeline(skip_yesterday=args.skip_yesterday, lookback_days=args.lookback_days)
    return 0


if __name__ == "__main__":
    sys.exit(main())
