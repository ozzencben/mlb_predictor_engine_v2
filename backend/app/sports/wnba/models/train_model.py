"""
WNBA Model Egitimi — Faz 4

3 model:
  model_win    : XGBClassifier  — ev sahibi kazanır mı? (1/0)
  model_spread : XGBRegressor   — ev sahibi puan farkı (home - away)
  model_total  : XGBRegressor   — toplam puan (home + away)

Yontem:
  - TimeSeriesSplit (zaman sirali CV — veri sizdirmaz)
  - Optuna hiperparametre arama
  - Platt Scaling olasılik kalibrasyonu (win modeli)
  - Feature importance kaydedilir
  - Tam metrikler metrics.json'a yazılır

Calistirma:
  cd backend
  uv run python -m app.sports.wnba.models.train_model
  uv run python -m app.sports.wnba.models.train_model --trials 50
  uv run python -m app.sports.wnba.models.train_model --quick     (5 trial, test icin)
"""
from __future__ import annotations

import json
import sys
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import optuna
import xgboost as xgb
from sklearn.calibration import CalibratedClassifierCV
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, brier_score_loss, log_loss,
    mean_absolute_error, mean_squared_error
)
from sklearn.model_selection import TimeSeriesSplit, cross_val_score

# Suppress Optuna verbose logs
optuna.logging.set_verbosity(optuna.logging.WARNING)

# -----------------------------------------------------------------------
# Paths
# -----------------------------------------------------------------------
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
FEATURES_FILE = DATA_DIR / "processed" / "game_features.json"
MODELS_DIR = DATA_DIR / "models"

FEATURE_COLS = [
    # --- Orijinal 12 diferansiyel ---
    "feature_net_rating_diff",
    "feature_elo_diff",
    "feature_ppg_diff",
    "feature_efg_diff",
    "feature_tov_diff",
    "feature_pace_diff",
    "feature_ts_diff",
    "feature_reb_diff",
    "feature_rest_diff",
    "feature_b2b_fatigue",
    "feature_h2h_edge",
    "feature_hca_weight",
    # --- Yeni 7: mutlak skor + opp quality + form ---
    "feature_home_off_abs",
    "feature_away_off_abs",
    "feature_home_def_abs",
    "feature_away_def_abs",
    "feature_pace_abs",
    "feature_opp_quality_diff",
    "feature_form_streak_diff",
]

# Sezon agirlik haritasi: yakin sezonlara daha fazla agirlik ver.
# Eski veri hala kullanilir ama katkisi azaltilir.
SEASON_WEIGHTS: dict[int, float] = {
    2026: 3.0,
    2025: 2.5,
    2024: 2.0,
    2023: 1.5,
    2022: 1.2,
    2021: 1.0,
    2020: 0.9,
    2019: 0.8,
    2018: 0.8,
    2017: 0.7,
    2016: 0.7,
}
DEFAULT_WEIGHT = 1.0

N_SPLITS = 5        # TimeSeriesSplit katlama sayisi
DEFAULT_TRIALS = 60


# -----------------------------------------------------------------------
# Veri Yukleme
# -----------------------------------------------------------------------

def load_dataset() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    game_features.json'dan X, y_win, y_spread, y_total, sample_weights yukler.
    Kronolojik sirali; yakin sezonlara daha fazla agirlik verilir.
    """
    if not FEATURES_FILE.exists():
        raise FileNotFoundError(
            f"game_features.json bulunamadi: {FEATURES_FILE}\n"
            "Once 'build_features.py' calistirilmali."
        )

    raw = json.loads(FEATURES_FILE.read_text(encoding="utf-8"))
    games: list[dict[str, Any]] = raw.get("games", [])

    if not games:
        raise ValueError("game_features.json bos!")

    # Kronolojik siralama (data leakage onleme)
    games.sort(key=lambda g: (g.get("date") or "", g.get("game_id", "")))

    rows_X: list[list[float]] = []
    y_win: list[int] = []
    y_spread: list[float] = []
    y_total: list[float] = []
    weights: list[float] = []

    skipped = 0
    for g in games:
        feats = g.get("features", {})
        row = []
        ok = True
        for col in FEATURE_COLS:
            v = feats.get(col)
            if v is None:
                ok = False
                break
            row.append(float(v))
        if not ok:
            skipped += 1
            continue

        tw = g.get("target_home_win")
        ts = g.get("target_spread")
        tt = g.get("target_total")
        if tw is None or ts is None or tt is None:
            skipped += 1
            continue

        season = g.get("season")
        if season is None and g.get("date"):
            try:
                season = int(g["date"][:4])
            except (ValueError, TypeError):
                season = None
        w = SEASON_WEIGHTS.get(int(season), DEFAULT_WEIGHT) if season else DEFAULT_WEIGHT

        rows_X.append(row)
        y_win.append(int(tw))
        y_spread.append(float(ts))
        y_total.append(float(tt))
        weights.append(w)

    print(f"[INFO] Veri: {len(rows_X)} gecerli oyun, {skipped} atlandi")

    X = np.array(rows_X, dtype=np.float32)
    return (
        X,
        np.array(y_win),
        np.array(y_spread, dtype=np.float32),
        np.array(y_total, dtype=np.float32),
        np.array(weights, dtype=np.float32),
    )


# -----------------------------------------------------------------------
# Optuna Objective Fonksiyonlari
# -----------------------------------------------------------------------

def _xgb_base_space(trial: optuna.Trial) -> dict[str, Any]:
    """Hem classifier hem regressor icin ortak XGBoost arama uzayi."""
    return {
        "n_estimators": trial.suggest_int("n_estimators", 100, 600, step=50),
        "max_depth": trial.suggest_int("max_depth", 3, 7),
        "learning_rate": trial.suggest_float("learning_rate", 0.005, 0.2, log=True),
        "subsample": trial.suggest_float("subsample", 0.6, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.5, 1.0),
        "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
        "reg_alpha": trial.suggest_float("reg_alpha", 1e-4, 1.0, log=True),
        "reg_lambda": trial.suggest_float("reg_lambda", 0.5, 5.0),
        "random_state": 42,
        "n_jobs": -1,
    }


def objective_win(trial: optuna.Trial, X: np.ndarray, y: np.ndarray, tscv: TimeSeriesSplit) -> float:
    params = _xgb_base_space(trial)
    params["eval_metric"] = "logloss"
    model = xgb.XGBClassifier(**params)
    scores = cross_val_score(model, X, y, cv=tscv, scoring="accuracy", n_jobs=1)
    return float(scores.mean())


def objective_regressor(
    trial: optuna.Trial, X: np.ndarray, y: np.ndarray, tscv: TimeSeriesSplit
) -> float:
    params = _xgb_base_space(trial)
    params["eval_metric"] = "rmse"
    model = xgb.XGBRegressor(**params)
    scores = cross_val_score(model, X, y, cv=tscv, scoring="neg_mean_absolute_error", n_jobs=1)
    return float(scores.mean())  # negatif MAE — Optuna maximize eder


# -----------------------------------------------------------------------
# Model Egitim Yardimcisi
# -----------------------------------------------------------------------

def _train_with_optuna(
    X_tr: np.ndarray,
    y_tr: np.ndarray,
    X_te: np.ndarray,
    y_te: np.ndarray,
    tscv: TimeSeriesSplit,
    mode: str,
    n_trials: int,
    label: str,
    sample_weight: np.ndarray | None = None,
) -> tuple[Any, dict[str, Any]]:
    """
    mode: 'classify' veya 'regress'
    sample_weight: None ise uniform agirlik kullanilir.
    Returns: (fitted_model, best_params)
    """
    print(f"\n[{label}] Optuna arama basliyor ({n_trials} deneme)...")

    study = optuna.create_study(
        direction="maximize",
        sampler=optuna.samplers.TPESampler(seed=42),
    )

    # CV sirasinda sample_weight kullanamiyoruz (TimeSeriesSplit fold'larda index karisiyor)
    # Bu yuzden CV'de uniform, final fit'te agirlikli egitim yapiyoruz.
    if mode == "classify":
        obj = lambda t: objective_win(t, X_tr, y_tr, tscv)
    else:
        obj = lambda t: objective_regressor(t, X_tr, y_tr, tscv)

    study.optimize(obj, n_trials=n_trials, show_progress_bar=False)
    best_params = study.best_params
    print(f"  -> En iyi CV skoru: {study.best_value:.4f}")
    print(f"  -> Parametreler: {best_params}")

    best_params["random_state"] = 42
    best_params["n_jobs"] = -1

    if mode == "classify":
        best_params["eval_metric"] = "logloss"
        model = xgb.XGBClassifier(**best_params)
    else:
        best_params["eval_metric"] = "rmse"
        model = xgb.XGBRegressor(**best_params)

    # Final model: sample_weight ile agirlikli egitim
    if sample_weight is not None:
        model.fit(X_tr, y_tr, sample_weight=sample_weight)
    else:
        model.fit(X_tr, y_tr)
    return model, best_params


# -----------------------------------------------------------------------
# Ana Egitim Fonksiyonu
# -----------------------------------------------------------------------

def train(n_trials: int = DEFAULT_TRIALS) -> dict[str, Any]:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("WNBA Model Egitimi Basliyor")
    print("=" * 60)

    # 1. Veri yukle
    X, y_win, y_spread, y_total, weights = load_dataset()
    n = len(X)
    print(f"[INFO] Toplam ornek: {n} | Features: {len(FEATURE_COLS)}")

    # Zaman sirali train/test bolmesi (%80 / %20)
    split_idx = int(n * 0.80)
    X_tr, X_te = X[:split_idx], X[split_idx:]
    yw_tr, yw_te = y_win[:split_idx], y_win[split_idx:]
    ys_tr, ys_te = y_spread[:split_idx], y_spread[split_idx:]
    yt_tr, yt_te = y_total[:split_idx], y_total[split_idx:]
    w_tr = weights[:split_idx]

    print(f"[INFO] Train: {len(X_tr)} | Test: {len(X_te)}")
    print(f"[INFO] Ortalama sample weight (train): {w_tr.mean():.2f}")

    tscv = TimeSeriesSplit(n_splits=N_SPLITS)

    metrics: dict[str, Any] = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "n_train": len(X_tr),
        "n_test": len(X_te),
        "features": FEATURE_COLS,
        "n_trials": n_trials,
    }

    # ----------------------------------------------------------------
    # 2. WIN MODELİ
    # ----------------------------------------------------------------
    print("\n" + "=" * 40)
    print("1/3  WIN MODEL (XGBClassifier)")
    print("=" * 40)

    win_model, win_params = _train_with_optuna(
        X_tr, yw_tr, X_te, yw_te, tscv, "classify", n_trials, "WIN",
        sample_weight=w_tr,
    )

    # Test metrikleri
    y_pred_win = win_model.predict(X_te)
    y_prob_win_raw = win_model.predict_proba(X_te)[:, 1]
    acc = accuracy_score(yw_te, y_pred_win)
    brier = brier_score_loss(yw_te, y_prob_win_raw)
    ll = log_loss(yw_te, y_prob_win_raw)
    baseline_acc = max(np.mean(yw_te), 1 - np.mean(yw_te))

    print(f"\n  WIN Model Test Metrikleri:")
    print(f"    Accuracy  : {acc:.4f}  (Baseline: {baseline_acc:.4f})")
    print(f"    Brier     : {brier:.4f}")
    print(f"    Log-Loss  : {ll:.4f}")

    metrics["win"] = {
        "accuracy": round(acc, 4),
        "baseline_accuracy": round(baseline_acc, 4),
        "brier_score": round(brier, 4),
        "log_loss": round(ll, 4),
        "best_params": win_params,
    }

    # Platt Scaling kalibrasyonu
    print("\n  Platt Scaling kalibrasyonu yapiliyor...")
    lr_cal = LogisticRegression(C=1.0, max_iter=500)
    lr_cal.fit(y_prob_win_raw.reshape(-1, 1), yw_te)
    calib_data = {
        "method": "platt",
        "coef": float(lr_cal.coef_[0][0]),
        "intercept": float(lr_cal.intercept_[0]),
    }
    calib_path = MODELS_DIR / "model_win_calibration.json"
    calib_path.write_text(json.dumps(calib_data, indent=2), encoding="utf-8")
    print(f"  -> Kalibrasyon: coef={calib_data['coef']:.4f}, intercept={calib_data['intercept']:.4f}")

    # Kalibrasyon sonrasi Brier
    def platt_calibrate(raw_probs: np.ndarray, coef: float, intercept: float) -> np.ndarray:
        logit = coef * raw_probs + intercept
        return 1.0 / (1.0 + np.exp(-logit))

    cal_probs = platt_calibrate(y_prob_win_raw, calib_data["coef"], calib_data["intercept"])
    brier_cal = brier_score_loss(yw_te, cal_probs)
    print(f"  -> Kalibrasyon sonrasi Brier: {brier_cal:.4f}")
    metrics["win"]["brier_score_calibrated"] = round(brier_cal, 4)

    # Feature importance
    fi_win = dict(zip(FEATURE_COLS, win_model.feature_importances_.tolist()))
    metrics["win"]["feature_importance"] = dict(
        sorted(fi_win.items(), key=lambda x: -x[1])
    )

    # Modeli kaydet
    win_path = MODELS_DIR / "model_win.json"
    win_model.save_model(str(win_path))
    print(f"  -> Model kaydedildi: {win_path}")

    # ----------------------------------------------------------------
    # 3. SPREAD MODELİ
    # ----------------------------------------------------------------
    print("\n" + "=" * 40)
    print("2/3  SPREAD MODEL (XGBRegressor)")
    print("=" * 40)

    spread_model, spread_params = _train_with_optuna(
        X_tr, ys_tr, X_te, ys_te, tscv, "regress", n_trials, "SPREAD",
        sample_weight=w_tr,
    )

    y_pred_spread = spread_model.predict(X_te)
    mae_spread = mean_absolute_error(ys_te, y_pred_spread)
    rmse_spread = float(np.sqrt(mean_squared_error(ys_te, y_pred_spread)))
    baseline_mae_spread = mean_absolute_error(ys_te, np.full_like(ys_te, np.mean(ys_tr)))

    print(f"\n  SPREAD Model Test Metrikleri:")
    print(f"    MAE   : {mae_spread:.2f} puan  (Baseline: {baseline_mae_spread:.2f})")
    print(f"    RMSE  : {rmse_spread:.2f} puan")

    metrics["spread"] = {
        "mae": round(mae_spread, 3),
        "rmse": round(rmse_spread, 3),
        "baseline_mae": round(baseline_mae_spread, 3),
        "best_params": spread_params,
        "feature_importance": dict(
            sorted(
                dict(zip(FEATURE_COLS, spread_model.feature_importances_.tolist())).items(),
                key=lambda x: -x[1],
            )
        ),
    }

    spread_path = MODELS_DIR / "model_spread.json"
    spread_model.save_model(str(spread_path))
    print(f"  -> Model kaydedildi: {spread_path}")

    # ----------------------------------------------------------------
    # 4. TOTAL MODEL
    # ----------------------------------------------------------------
    print("\n" + "=" * 40)
    print("3/3  TOTAL MODEL (XGBRegressor)")
    print("=" * 40)

    total_model, total_params = _train_with_optuna(
        X_tr, yt_tr, X_te, yt_te, tscv, "regress", n_trials, "TOTAL",
        sample_weight=w_tr,
    )

    y_pred_total = total_model.predict(X_te)
    mae_total = mean_absolute_error(yt_te, y_pred_total)
    rmse_total = float(np.sqrt(mean_squared_error(yt_te, y_pred_total)))
    baseline_mae_total = mean_absolute_error(yt_te, np.full_like(yt_te, np.mean(yt_tr)))

    print(f"\n  TOTAL Model Test Metrikleri:")
    print(f"    MAE   : {mae_total:.2f} puan  (Baseline: {baseline_mae_total:.2f})")
    print(f"    RMSE  : {rmse_total:.2f} puan")

    metrics["total"] = {
        "mae": round(mae_total, 3),
        "rmse": round(rmse_total, 3),
        "baseline_mae": round(baseline_mae_total, 3),
        "best_params": total_params,
        "feature_importance": dict(
            sorted(
                dict(zip(FEATURE_COLS, total_model.feature_importances_.tolist())).items(),
                key=lambda x: -x[1],
            )
        ),
    }

    total_path = MODELS_DIR / "model_total.json"
    total_model.save_model(str(total_path))
    print(f"  -> Model kaydedildi: {total_path}")

    # ----------------------------------------------------------------
    # 5. Metrikleri kaydet
    # ----------------------------------------------------------------
    metrics_path = MODELS_DIR / "metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[OK] Metrikler kaydedildi: {metrics_path}")

    # Ozet
    print("\n" + "=" * 60)
    print("EGITIM OZETI")
    print("=" * 60)
    print(f"  Win  Accuracy : {metrics['win']['accuracy']:.1%} (Baseline: {metrics['win']['baseline_accuracy']:.1%})")
    print(f"  Win  Brier Cal: {metrics['win']['brier_score_calibrated']:.4f}")
    print(f"  Spread MAE    : {metrics['spread']['mae']:.2f} puan")
    print(f"  Total  MAE    : {metrics['total']['mae']:.2f} puan")
    print(f"  Modeller      : {MODELS_DIR}")
    print("=" * 60)

    return metrics


# -----------------------------------------------------------------------
# CLI
# -----------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="WNBA Model Egitimi")
    parser.add_argument("--trials", type=int, default=DEFAULT_TRIALS, help="Optuna deneme sayisi")
    parser.add_argument("--quick", action="store_true", help="Hizli test (5 deneme)")
    args = parser.parse_args(argv)

    n_trials = 5 if args.quick else args.trials
    train(n_trials=n_trials)
    return 0


if __name__ == "__main__":
    sys.exit(main())
