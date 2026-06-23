"""WNBA beta operasyonlari — arsiv, dogruluk takibi, meta."""
from __future__ import annotations

import json
import logging
import os
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from app.sports.wnba.services.config import DATA_DIR, RAW_BOX_SCORES_DIR

logger = logging.getLogger(__name__)

ET = ZoneInfo("America/New_York")
ARCHIVE_DIR = DATA_DIR / "archive"
PREDICTIONS_FILE = DATA_DIR / "today_predictions.json"
RESULTS_FILE = DATA_DIR / "today_accuracy_results.json"
METRICS_FILE = DATA_DIR / "models" / "metrics.json"

BETA_VERSION = "1.0.0-beta"


def _today_et() -> str:
    return datetime.now(ET).strftime("%Y-%m-%d")


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("JSON okunamadi %s: %s", path, e)
        return None


def _file_date(path: Path) -> str | None:
    data = _load_json(path)
    if data and data.get("date"):
        return str(data["date"])
    if path.exists():
        mtime = os.path.getmtime(path)
        return datetime.fromtimestamp(mtime, tz=ET).strftime("%Y-%m-%d")
    return None


def _load_actual_results(game_ids: list[str]) -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    for gid in game_ids:
        path = RAW_BOX_SCORES_DIR / f"{gid}.json"
        if not path.exists():
            continue
        try:
            box = json.loads(path.read_text(encoding="utf-8"))
            hs = int(float(box.get("home_score") or 0))
            aw = int(float(box.get("away_score") or 0))
            if hs == 0 and aw == 0:
                continue
            results[gid] = {
                "home_score": hs,
                "away_score": aw,
                "home_win": 1 if hs > aw else 0,
                "margin": hs - aw,
                "total": hs + aw,
            }
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
    return results


def _evaluate_predictions_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    preds = payload.get("predictions") or []
    if not preds:
        return None

    game_ids = [p["game_id"] for p in preds if p.get("game_id")]
    actuals = _load_actual_results(game_ids)
    if not actuals:
        return None

    evaluated: list[dict[str, Any]] = []
    ml_correct = ml_total = 0
    spread_correct = spread_total = 0
    total_correct = total_total = 0

    for pred in preds:
        gid = pred.get("game_id")
        if not gid or gid not in actuals:
            continue

        act = actuals[gid]
        pred_home_win = float(pred.get("home_win_prob", 0.5)) >= 0.5
        actual_home_win = bool(act["home_win"])
        ml_ok = pred_home_win == actual_home_win
        ml_total += 1
        if ml_ok:
            ml_correct += 1

        odds = pred.get("odds") or {}
        spread_line = odds.get("spread_home")
        if spread_line is not None:
            try:
                line = float(spread_line)
                home_covered = act["margin"] > line
                model_home_cover = float(pred.get("predicted_spread", 0)) > line
                spread_ok = home_covered == model_home_cover
                spread_total += 1
                if spread_ok:
                    spread_correct += 1
            except (TypeError, ValueError):
                pass

        total_line = odds.get("total_over")
        if total_line is not None:
            try:
                line = float(total_line)
                went_over = act["total"] > line
                model_over = float(pred.get("predicted_total", 0)) > line
                total_ok = went_over == model_over
                total_total += 1
                if total_ok:
                    total_correct += 1
            except (TypeError, ValueError):
                pass

        evaluated.append({
            "game_id": gid,
            "name": pred.get("name"),
            "home_team_abbr": pred.get("home_team_abbr"),
            "away_team_abbr": pred.get("away_team_abbr"),
            "predicted_winner_abbr": pred.get("predicted_winner_abbr"),
            "actual_score": f"{act['away_score']}-{act['home_score']}",
            "ml_correct": ml_ok,
            "home_win_prob": pred.get("home_win_prob"),
            "predicted_spread": pred.get("predicted_spread"),
            "predicted_total": pred.get("predicted_total"),
        })

    if not evaluated:
        return None

    return {
        "date": payload.get("date"),
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "games_evaluated": len(evaluated),
        "ml_accuracy": round(ml_correct / ml_total, 4) if ml_total else None,
        "ml_correct": ml_correct,
        "ml_total": ml_total,
        "spread_accuracy": round(spread_correct / spread_total, 4) if spread_total else None,
        "spread_correct": spread_correct,
        "spread_total": spread_total,
        "total_accuracy": round(total_correct / total_total, 4) if total_total else None,
        "total_correct": total_correct,
        "total_total": total_total,
        "results": evaluated,
    }


def evaluate_today_accuracy(save: bool = True) -> dict[str, Any] | None:
    """Tamamlanan maclar icin kayitli tahminleri gercek sonuclarla karsilastir."""
    payload = _load_json(PREDICTIONS_FILE)
    if not payload:
        yesterday = (datetime.now(ET) - timedelta(days=1)).strftime("%Y-%m-%d")
        archive_path = ARCHIVE_DIR / f"predictions_{yesterday}.json"
        payload = _load_json(archive_path)

    if not payload:
        logger.info("Degerlendirilecek tahmin dosyasi yok.")
        return None

    report = _evaluate_predictions_payload(payload)
    if not report:
        logger.info("Tamamlanmis mac + tahmin eslesmesi bulunamadi.")
        return None

    if save:
        RESULTS_FILE.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(
            "WNBA accuracy: ML %s/%s (%.1f%%)",
            report["ml_correct"],
            report["ml_total"],
            (report["ml_accuracy"] or 0) * 100,
        )
    return report


def archive_past_data() -> None:
    """Eski gun tahmin/sonuc dosyalarini archive/ altina tasir."""
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    today_str = _today_et()

    for src, prefix in (
        (PREDICTIONS_FILE, "predictions"),
        (RESULTS_FILE, "results"),
    ):
        if not src.exists():
            continue
        try:
            data = _load_json(src)
            file_date = (data or {}).get("date") or _file_date(src)
            if not file_date or file_date >= today_str:
                continue

            if prefix == "predictions" and data:
                evaluate_report = _evaluate_predictions_payload(data)
                if evaluate_report:
                    results_path = ARCHIVE_DIR / f"results_{file_date}.json"
                    if not results_path.exists():
                        results_path.write_text(
                            json.dumps(evaluate_report, ensure_ascii=False, indent=2),
                            encoding="utf-8",
                        )

            archive_path = ARCHIVE_DIR / f"{prefix}_{file_date}.json"
            if not archive_path.exists():
                shutil.copy2(src, archive_path)
                logger.info("WNBA arsiv: %s -> %s", src.name, archive_path.name)
        except Exception as e:
            logger.error("Arsiv hatasi (%s): %s", src.name, e)


def load_model_meta() -> dict[str, Any]:
    metrics = _load_json(METRICS_FILE) or {}
    win = metrics.get("win") or {}
    return {
        "beta_version": BETA_VERSION,
        "model_trained_at": metrics.get("trained_at"),
        "win_accuracy": win.get("accuracy"),
        "win_feature_count": win.get("feature_count"),
        "spread_mae": (metrics.get("spread") or {}).get("mae"),
        "total_mae": (metrics.get("total") or {}).get("mae"),
    }
