"""
WNBA Gunluk Tahmin Motoru — Faz 4

1. today_predictions_raw.json'dan features yukle (pipeline_runner tarafindan uretilmis)
2. Win / Spread / Total modellerini calistir
3. Model-implied odds hesapla (American format)
4. Odds API satiri ile karsilastirip edge bul
5. Alternatif bet marketlerini confidence sirali uret
6. today_predictions.json kaydet

Calistirma:
  cd backend
  uv run python -m app.sports.wnba.models.predict
"""
from __future__ import annotations

import json
import math
import sys
import argparse
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import xgboost as xgb

from app.sports.wnba.models.model_features import SPREAD_TOTAL_FEATURE_COLS, WIN_FEATURE_COLS
from app.sports.wnba.services.beta_ops import BETA_VERSION, load_model_meta

# -----------------------------------------------------------------------
# Paths
# -----------------------------------------------------------------------
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = DATA_DIR / "models"

RAW_FILE = DATA_DIR / "today_predictions_raw.json"
OUTPUT_FILE = DATA_DIR / "today_predictions.json"

# Geriye uyumluluk
FEATURE_COLS = SPREAD_TOTAL_FEATURE_COLS

# -----------------------------------------------------------------------
# Model yukleme (tek seferlik, modül seviyesi önbellek)
# -----------------------------------------------------------------------
_win_model: xgb.XGBClassifier | None = None
_spread_model: xgb.XGBRegressor | None = None
_total_model: xgb.XGBRegressor | None = None
_calibration: dict[str, Any] | None = None


def _load_models() -> tuple[xgb.XGBClassifier, xgb.XGBRegressor, xgb.XGBRegressor, dict]:
    global _win_model, _spread_model, _total_model, _calibration

    if _win_model is None:
        win_path = MODELS_DIR / "model_win.json"
        if not win_path.exists():
            raise FileNotFoundError(
                f"Model bulunamadi: {win_path}\n"
                "Once 'train_model.py' calistirilmali."
            )
        _win_model = xgb.XGBClassifier()
        _win_model.load_model(str(win_path))

    if _spread_model is None:
        _spread_model = xgb.XGBRegressor()
        _spread_model.load_model(str(MODELS_DIR / "model_spread.json"))

    if _total_model is None:
        _total_model = xgb.XGBRegressor()
        _total_model.load_model(str(MODELS_DIR / "model_total.json"))

    if _calibration is None:
        calib_path = MODELS_DIR / "model_win_calibration.json"
        if calib_path.exists():
            _calibration = json.loads(calib_path.read_text(encoding="utf-8"))
        else:
            _calibration = {}

    return _win_model, _spread_model, _total_model, _calibration


def reset_model_cache() -> None:
    global _win_model, _spread_model, _total_model, _calibration
    _win_model = _spread_model = _total_model = _calibration = None


# -----------------------------------------------------------------------
# Olasilik Kalibrasyonu (Platt)
# -----------------------------------------------------------------------

def _platt_calibrate(raw_prob: float, coef: float, intercept: float) -> float:
    logit = coef * raw_prob + intercept
    calibrated = 1.0 / (1.0 + math.exp(-logit))
    # Overfitting / boundary guard: [0.04, 0.96]
    return max(0.04, min(0.96, calibrated))


# -----------------------------------------------------------------------
# Odds donusumleri
# -----------------------------------------------------------------------

def prob_to_american(prob: float) -> int:
    """Win olasiligi → American odds (yaklasik)."""
    prob = max(0.01, min(0.99, prob))
    if prob >= 0.50:
        odds = -(prob / (1 - prob)) * 100
    else:
        odds = ((1 - prob) / prob) * 100
    return int(round(odds))


def american_to_prob(american: int) -> float:
    """American odds → implied win olasiligi."""
    if american > 0:
        return 100.0 / (american + 100.0)
    else:
        return abs(american) / (abs(american) + 100.0)


def prob_to_decimal(prob: float) -> float:
    """Win olasiligi → decimal odds."""
    prob = max(0.01, min(0.99, prob))
    return round(1.0 / prob, 3)


# -----------------------------------------------------------------------
# Edge ve Confidence hesabi
# -----------------------------------------------------------------------

def _edge_pct(model_prob: float, market_prob: float) -> float:
    """
    Edge (%) = model_prob - market_prob.
    Pozitif: modelin pazardan daha yuksek olasilik gordugu taraf.
    """
    return round((model_prob - market_prob) * 100, 2)


def _confidence(edge_abs: float) -> str:
    """
    Edge buyuklugune gore guven etiketi.
    Finansal bahis camiasinda +3% civarinda anlamli, +7% ise kuvvetli kabul edilir.
    """
    if edge_abs >= 8.0:
        return "High"
    elif edge_abs >= 4.0:
        return "Medium"
    else:
        return "Low"


# -----------------------------------------------------------------------
# Spread / Total bet uretimi
# -----------------------------------------------------------------------

def _spread_bets(
    pred_spread: float,
    odds: dict[str, Any] | None,
    home_name: str,
    away_name: str,
) -> list[dict[str, Any]]:
    """
    Model spread tahminini piyasa line'iyla karsilastirir.
    pred_spread: pozitif = home favori (home - away beklentisi)
    """
    bets = []
    if not odds or odds.get("spread_line") is None:
        return bets

    line: float = float(odds["spread_line"])
    # Piyasa home için: line (e.g. -3.5 = home 3.5 favori, +3.5 = home 3.5 underdog)
    market_home_spread = line

    # diff = model-predicted margin + market home spread line.
    # E.g. Model expects home to win by 10 (pred_spread = 10), line is home -4.5 (market_home_spread = -4.5).
    # expected_cover_margin = 10 + (-4.5) = +5.5. Since diff > 0, home team has edge of 5.5.
    # E.g. Model expects home to lose by 1.3 (pred_spread = -1.3), line is home +4.5 (market_home_spread = 4.5).
    # expected_cover_margin = -1.3 + 4.5 = +3.2. Since diff > 0, home team has edge of 3.2.
    diff = pred_spread + market_home_spread

    if abs(diff) < 2.0:
        return bets

    if diff > 0:
        # Model home'un daha iyi kapatacagini düsünüyor → home spread al
        side = home_name
        edge_val = diff
        market_ml = odds.get("spread_home")
        line_str = f"{'+' if market_home_spread > 0 else ''}{market_home_spread}"
    else:
        # Model away'in daha iyi kapatacagini düsünüyor → away spread al
        side = away_name
        edge_val = abs(diff)
        market_ml = odds.get("spread_away")
        market_away_spread = -market_home_spread
        line_str = f"{'+' if market_away_spread > 0 else ''}{market_away_spread}"

    conf = _confidence(edge_val)
    bets.append({
        "market": "Spread",
        "pick": f"{side} ({line_str})",
        "model_prediction": f"Predicted spread: {pred_spread:+.1f}",
        "edge": round(edge_val, 2),
        "confidence": conf,
        "odds": market_ml,
        "odds_format": "american",
    })
    return bets



TOTAL_MODEL_MAE = 14.5   # Egitimde olculen test MAE (puan)
TOTAL_MAX_RELIABLE = TOTAL_MODEL_MAE * 2  # Bu esigi asan edge = model sinir disi


def _total_bets(
    pred_total: float,
    odds: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Model total tahminini piyasa o/u line'iyla karsilastirir."""
    bets = []
    if not odds or odds.get("total_line") is None:
        return bets

    line: float = float(odds["total_line"])
    diff = pred_total - line

    if abs(diff) < 3.0:
        return bets

    if diff > 0:
        direction = "Over"
        edge_val = diff
        market_ml = odds.get("total_over")
    else:
        direction = "Under"
        edge_val = abs(diff)
        market_ml = odds.get("total_under")

    # Cok buyuk edge: modelin MAE'sinin 2 katini asiyorsa guvenilirlik duser.
    # Bu genellikle skor trendinin egitim verisinden farkli olduguna isarettir.
    if edge_val > TOTAL_MAX_RELIABLE:
        conf = "Low"
        note = f"Caution: edge ({edge_val:.1f} pts) exceeds model MAE x2 ({TOTAL_MAX_RELIABLE:.0f} pts)"
    else:
        conf = _confidence(edge_val)
        note = None

    bet: dict[str, Any] = {
        "market": "Total",
        "pick": f"{direction} {line}",
        "model_prediction": f"Predicted total: {pred_total:.1f}",
        "edge": round(edge_val, 2),
        "confidence": conf,
        "odds": market_ml,
        "odds_format": "american",
    }
    if note:
        bet["note"] = note
    bets.append(bet)
    return bets


def _moneyline_bet(
    home_win_prob: float,
    away_win_prob: float,
    odds: dict[str, Any] | None,
    home_name: str,
    away_name: str,
) -> list[dict[str, Any]]:
    """Model win olasiligi vs piyasa ML orani."""
    bets = []
    if not odds:
        return bets

    picks: list[tuple[str, float, float | None, float]] = []

    ml_home = odds.get("moneyline_home")
    ml_away = odds.get("moneyline_away")

    if ml_home is not None:
        market_prob_home = american_to_prob(int(ml_home))
        edge = _edge_pct(home_win_prob, market_prob_home)
        if abs(edge) >= 4.0:
            picks.append((home_name, edge, ml_home, home_win_prob))

    if ml_away is not None:
        market_prob_away = american_to_prob(int(ml_away))
        edge = _edge_pct(away_win_prob, market_prob_away)
        if abs(edge) >= 4.0:
            picks.append((away_name, edge, ml_away, away_win_prob))

    for item in picks:
        name, edge, ml, model_prob = item
        if edge > 0:
            bets.append({
                "market": "Moneyline",
                "pick": name,
                "model_win_prob": f"{model_prob:.1%}",
                "edge": round(edge, 2),
                "confidence": _confidence(abs(edge)),
                "odds": ml,
                "odds_format": "american",
            })

    return bets


# -----------------------------------------------------------------------
# AI insights
# -----------------------------------------------------------------------

async def generate_wnba_ai_insights_async(output: dict[str, Any]) -> None:
    from app.services.ai.factory import get_ai_predictor

    predictor = get_ai_predictor()
    if getattr(predictor, "quota_exhausted", False):
        for pred in output.get("predictions", []):
            pred.setdefault("ai_insight", "AI analysis is temporarily unavailable due to API limits.")
        return

    for pred in output.get("predictions", []):
        if pred.get("ai_insight") and "unavailable" not in str(pred["ai_insight"]).lower():
            continue
        name = pred.get("name", "?")
        print(f"  [AI] {name}...")
        try:
            pred["ai_insight"] = await predictor.generate_wnba_insight_async(pred)
        except Exception as e:
            pred["ai_insight"] = f"AI insight generation failed: {e}"


def _load_cached_ai_insights() -> dict[str, str]:
    if not OUTPUT_FILE.exists():
        return {}
    try:
        data = json.loads(OUTPUT_FILE.read_text(encoding="utf-8"))
        return {
            p["game_id"]: p["ai_insight"]
            for p in data.get("predictions", [])
            if p.get("game_id") and p.get("ai_insight")
        }
    except Exception:
        return {}


# -----------------------------------------------------------------------
# Ana tahmin fonksiyonu
# -----------------------------------------------------------------------

def generate_predictions(save: bool = True, skip_ai: bool = False) -> list[dict[str, Any]]:
    """
    today_predictions_raw.json'daki her mac icin:
      - Win olasiligi (kalibrasyon + Platt)
      - Spread tahmini
      - Total tahmini
      - Alternatif bet marketleri (confidence sirali)
    Sonuci today_predictions.json olarak kaydeder.
    """
    if not RAW_FILE.exists():
        print("[WARN] today_predictions_raw.json bulunamadi. Once pipeline_runner calistirin.")
        return []

    raw_data = json.loads(RAW_FILE.read_text(encoding="utf-8"))
    matches = raw_data.get("matches", [])

    if not matches:
        print("[INFO] Bugün oynanacak mac yok.")
        if save:
            _save_empty(raw_data.get("date", ""))
        return []

    win_model, spread_model, total_model, calib = _load_models()
    print(f"[INFO] {len(matches)} mac icin tahmin uretiliyor...")

    cached_ai = _load_cached_ai_insights()
    predictions: list[dict[str, Any]] = []

    for match in matches:
        feats = match.get("features", {})

        win_row = []
        reg_row = []
        ok = True
        for col in WIN_FEATURE_COLS:
            v = feats.get(col)
            if v is None:
                ok = False
                break
            win_row.append(float(v))
        for col in SPREAD_TOTAL_FEATURE_COLS:
            v = feats.get(col)
            if v is None:
                ok = False
                break
            reg_row.append(float(v))

        if not ok:
            print(f"  [SKIP] Eksik feature: {match.get('name', '?')}")
            continue

        X_win = np.array([win_row], dtype=np.float32)
        X_reg = np.array([reg_row], dtype=np.float32)

        # --- Model tahminleri ---
        raw_prob_home = float(win_model.predict_proba(X_win)[0][1])

        if calib.get("coef"):
            home_win_prob = _platt_calibrate(
                raw_prob_home, calib["coef"], calib["intercept"]
            )
        else:
            home_win_prob = max(0.04, min(0.96, raw_prob_home))

        away_win_prob = 1.0 - home_win_prob
        pred_spread = float(spread_model.predict(X_reg)[0])
        pred_total = float(total_model.predict(X_reg)[0])

        # --- Model-implied odds ---
        implied_home_ml = prob_to_american(home_win_prob)
        implied_away_ml = prob_to_american(away_win_prob)

        # --- Bet marketleri ---
        odds = match.get("odds")
        home_name = match["home_team_name"]
        away_name = match["away_team_name"]

        alt_bets: list[dict[str, Any]] = []
        alt_bets.extend(_moneyline_bet(home_win_prob, away_win_prob, odds, home_name, away_name))
        alt_bets.extend(_spread_bets(pred_spread, odds, home_name, away_name))
        alt_bets.extend(_total_bets(pred_total, odds))

        # Confidence sırası: High > Medium > Low, sonra edge büyüklüğü
        conf_order = {"High": 0, "Medium": 1, "Low": 2}
        alt_bets.sort(key=lambda b: (conf_order.get(b["confidence"], 3), -b.get("edge", 0)))

        proj_home = round((pred_total + pred_spread) / 2, 1)
        proj_away = round((pred_total - pred_spread) / 2, 1)

        predictions.append({
            "game_id": match["game_id"],
            "date": match["date"],
            "name": match["name"],
            "home_team_id": match["home_team_id"],
            "away_team_id": match["away_team_id"],
            "home_team_abbr": match["home_team_abbr"],
            "away_team_abbr": match["away_team_abbr"],
            "home_team_name": home_name,
            "away_team_name": away_name,
            "home_logo": match.get("home_logo"),
            "away_logo": match.get("away_logo"),
            "venue": match.get("venue"),
            # Tahminler
            "home_win_prob": round(home_win_prob, 4),
            "away_win_prob": round(away_win_prob, 4),
            "home_win_prob_pct": f"{home_win_prob:.1%}",
            "away_win_prob_pct": f"{away_win_prob:.1%}",
            "predicted_spread": round(pred_spread, 2),
            "predicted_total": round(pred_total, 1),
            "predicted_home_score": proj_home,
            "predicted_away_score": proj_away,
            "predicted_winner": home_name if home_win_prob >= 0.50 else away_name,
            "predicted_winner_abbr": match["home_team_abbr"] if home_win_prob >= 0.50 else match["away_team_abbr"],
            # Model-implied odds
            "implied_home_ml": implied_home_ml,
            "implied_away_ml": implied_away_ml,
            # Piyasa odds (referans)
            "odds": odds,
            # Alternatif bet marketleri
            "alt_bets": alt_bets,
            "bet_count": len(alt_bets),
            # UI detay verileri
            "home_l5": match.get("home_l5"),
            "away_l5": match.get("away_l5"),
            "home_l10": match.get("home_l10"),
            "away_l10": match.get("away_l10"),
            "home_l5_home": match.get("home_l5_home"),
            "away_l5_away": match.get("away_l5_away"),
            "h2h_last10": match.get("h2h_last10"),
            "home_recent_games": match.get("home_recent_games"),
            "away_recent_games": match.get("away_recent_games"),
            "elo_home": match.get("elo_home"),
            "elo_away": match.get("elo_away"),
            "rest_home": match.get("rest_home"),
            "rest_away": match.get("rest_away"),
            "features": feats,
            "ai_insight": cached_ai.get(match["game_id"]),
        })

        print(
            f"  [{match['away_team_abbr']:3s} @ {match['home_team_abbr']:3s}] "
            f"Home win: {home_win_prob:.1%} | "
            f"Spread: {pred_spread:+.1f} | "
            f"Total: {pred_total:.1f} | "
            f"Bets: {len(alt_bets)}"
        )

    if save:
        output = {
            "date": raw_data.get("date", ""),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "match_count": len(predictions),
            "beta_version": BETA_VERSION,
            "model_meta": load_model_meta(),
            "predictions": predictions,
        }
        if predictions and not skip_ai:
            asyncio.run(generate_wnba_ai_insights_async(output))

        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        archive_dir = DATA_DIR / "archive"
        archive_dir.mkdir(parents=True, exist_ok=True)
        archive_path = archive_dir / f"predictions_{output['date']}.json"
        with open(archive_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"[OK] {len(predictions)} tahmin kaydedildi -> {OUTPUT_FILE}")

    return predictions


def _save_empty(date_str: str) -> None:
    output = {
        "date": date_str or datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d"),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "match_count": 0,
        "beta_version": BETA_VERSION,
        "model_meta": load_model_meta(),
        "predictions": [],
    }
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)


# -----------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="WNBA gunluk tahmin")
    parser.add_argument("--no-save", action="store_true")
    parser.add_argument("--skip-ai", action="store_true")
    args = parser.parse_args(argv)
    generate_predictions(save=not args.no_save, skip_ai=args.skip_ai)
    return 0


if __name__ == "__main__":
    sys.exit(main())
