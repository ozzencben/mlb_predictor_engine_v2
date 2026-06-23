"""
WNBA Model Egitimi — Faz 4

3 model:
  model_win    : XGBClassifier  — ev sahibi kazanır mı? (1/0)
  model_spread : XGBRegressor   — ev sahibi puan farkı (home - away)
  model_total  : XGBRegressor   — toplam puan (home + away)

Yontem:
  - TimeSeriesSplit (zaman sirali CV — veri sizdirmaz)
  - Optuna hiperparametre arama (sample-weight'li CV)
  - Platt Scaling — train holdout uzerinde (test sizintisi yok)
  - Win modeli icin ayri 14-feature seti

Calistirma:
  cd backend
  uv run python -m app.sports.wnba.models.train_model
  uv run python -m app.sports.wnba.models.train_model --win-only --trials 80
  uv run python -m app.sports.wnba.models.train_model --quick
"""
from __future__ import annotations

import json
import sys
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import numpy as np
import optuna
import xgboost as xgb
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, brier_score_loss, log_loss,
    mean_absolute_error, mean_squared_error,
)
from sklearn.model_selection import TimeSeriesSplit

from app.sports.wnba.models.model_features import REGRESS_FEATURE_COLS, WIN_FEATURE_COLS

optuna.logging.set_verbosity(optuna.logging.WARNING)

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
FEATURES_FILE = DATA_DIR / "processed" / "game_features.json"
MODELS_DIR = DATA_DIR / "models"

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

N_SPLITS = 5
DEFAULT_TRIALS = 60
CALIBRATION_HOLDOUT_RATIO = 0.15


def load_dataset(
    feature_cols: list[str],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """game_features.json'dan feature matrisi, hedefler, agirliklar ve sezonlar."""
    if not FEATURES_FILE.exists():
        raise FileNotFoundError(
            f"game_features.json bulunamadi: {FEATURES_FILE}\n"
            "Once 'build_features.py' calistirilmali."
        )

    raw = json.loads(FEATURES_FILE.read_text(encoding="utf-8"))
    games: list[dict[str, Any]] = raw.get("games", [])
    if not games:
        raise ValueError("game_features.json bos!")

    games.sort(key=lambda g: (g.get("date") or "", g.get("game_id", "")))

    rows_X: list[list[float]] = []
    y_win: list[int] = []
    y_spread: list[float] = []
    y_total: list[float] = []
    weights: list[float] = []
    seasons: list[int] = []
    skipped = 0

    for g in games:
        feats = g.get("features", {})
        row: list[float] = []
        ok = True
        for col in feature_cols:
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
        season_int = int(season) if season else 0
        w = SEASON_WEIGHTS.get(season_int, DEFAULT_WEIGHT) if season else DEFAULT_WEIGHT

        rows_X.append(row)
        y_win.append(int(tw))
        y_spread.append(float(ts))
        y_total.append(float(tt))
        weights.append(w)
        seasons.append(season_int)

    print(f"[INFO] Veri: {len(rows_X)} gecerli oyun, {skipped} atlandi")

    return (
        np.array(rows_X, dtype=np.float32),
        np.array(y_win),
        np.array(y_spread, dtype=np.float32),
        np.array(y_total, dtype=np.float32),
        np.array(weights, dtype=np.float32),
        np.array(seasons),
    )


def _xgb_base_space(trial: optuna.Trial) -> dict[str, Any]:
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


def _weighted_cv_accuracy(
    params: dict[str, Any],
    X: np.ndarray,
    y: np.ndarray,
    weights: np.ndarray,
    tscv: TimeSeriesSplit,
) -> float:
    scores: list[float] = []
    for train_idx, val_idx in tscv.split(X):
        model = xgb.XGBClassifier(**params)
        model.fit(X[train_idx], y[train_idx], sample_weight=weights[train_idx])
        scores.append(float(accuracy_score(y[val_idx], model.predict(X[val_idx]))))
    return float(np.mean(scores))


def _weighted_cv_neg_mae(
    params: dict[str, Any],
    X: np.ndarray,
    y: np.ndarray,
    weights: np.ndarray,
    tscv: TimeSeriesSplit,
) -> float:
    scores: list[float] = []
    for train_idx, val_idx in tscv.split(X):
        model = xgb.XGBRegressor(**params)
        model.fit(X[train_idx], y[train_idx], sample_weight=weights[train_idx])
        mae = mean_absolute_error(y[val_idx], model.predict(X[val_idx]))
        scores.append(-mae)
    return float(np.mean(scores))


def objective_win(
    trial: optuna.Trial,
    X: np.ndarray,
    y: np.ndarray,
    weights: np.ndarray,
    tscv: TimeSeriesSplit,
) -> float:
    params = _xgb_base_space(trial)
    params["eval_metric"] = "logloss"
    return _weighted_cv_accuracy(params, X, y, weights, tscv)


def objective_regressor(
    trial: optuna.Trial,
    X: np.ndarray,
    y: np.ndarray,
    weights: np.ndarray,
    tscv: TimeSeriesSplit,
) -> float:
    params = _xgb_base_space(trial)
    params["eval_metric"] = "rmse"
    return _weighted_cv_neg_mae(params, X, y, weights, tscv)


def _train_with_optuna(
    X_tr: np.ndarray,
    y_tr: np.ndarray,
    weights_tr: np.ndarray,
    tscv: TimeSeriesSplit,
    mode: str,
    n_trials: int,
    label: str,
) -> tuple[Any, dict[str, Any]]:
    print(f"\n[{label}] Optuna arama basliyor ({n_trials} deneme, weighted CV)...")

    study = optuna.create_study(
        direction="maximize",
        sampler=optuna.samplers.TPESampler(seed=42),
    )

    if mode == "classify":
        obj: Callable[[optuna.Trial], float] = (
            lambda t: objective_win(t, X_tr, y_tr, weights_tr, tscv)
        )
    else:
        obj = lambda t: objective_regressor(t, X_tr, y_tr, weights_tr, tscv)

    study.optimize(obj, n_trials=n_trials, show_progress_bar=False)
    best_params = study.best_params
    print(f"  -> En iyi CV skoru: {study.best_value:.4f}")
    print(f"  -> Parametreler: {best_params}")

    best_params["random_state"] = 42
    best_params["n_jobs"] = -1

    if mode == "classify":
        best_params["eval_metric"] = "logloss"
        model: Any = xgb.XGBClassifier(**best_params)
    else:
        best_params["eval_metric"] = "rmse"
        model = xgb.XGBRegressor(**best_params)

    model.fit(X_tr, y_tr, sample_weight=weights_tr)
    return model, best_params


def _season_accuracy_breakdown(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    seasons: np.ndarray,
) -> dict[str, dict[str, float | int]]:
    breakdown: dict[str, dict[str, float | int]] = {}
    for season in sorted(set(seasons.tolist())):
        if season <= 0:
            continue
        mask = seasons == season
        if mask.sum() == 0:
            continue
        yt, yp = y_true[mask], y_pred[mask]
        baseline = max(float(np.mean(yt)), 1 - float(np.mean(yt)))
        breakdown[str(season)] = {
            "n": int(mask.sum()),
            "accuracy": round(float(accuracy_score(yt, yp)), 4),
            "baseline_accuracy": round(baseline, 4),
        }
    return breakdown


def _platt_calibrate(raw_probs: np.ndarray, coef: float, intercept: float) -> np.ndarray:
    logit = coef * raw_probs + intercept
    return 1.0 / (1.0 + np.exp(-logit))


def _fit_platt_on_holdout(
    model: xgb.XGBClassifier,
    X_tr: np.ndarray,
    y_tr: np.ndarray,
    w_tr: np.ndarray,
) -> dict[str, float]:
    """Train son %15 uzerinde Platt — test setine dokunulmaz."""
    holdout = max(50, int(len(X_tr) * CALIBRATION_HOLDOUT_RATIO))
    fit_end = len(X_tr) - holdout
    if fit_end < 100:
        fit_end = int(len(X_tr) * 0.85)

    cal_model = xgb.XGBClassifier(**model.get_params())
    cal_model.fit(X_tr[:fit_end], y_tr[:fit_end], sample_weight=w_tr[:fit_end])
    raw_cal = cal_model.predict_proba(X_tr[fit_end:])[:, 1]

    lr_cal = LogisticRegression(C=1.0, max_iter=500)
    lr_cal.fit(raw_cal.reshape(-1, 1), y_tr[fit_end:])
    return {
        "method": "platt",
        "coef": float(lr_cal.coef_[0][0]),
        "intercept": float(lr_cal.intercept_[0]),
        "holdout_samples": len(y_tr) - fit_end,
    }


def _train_win_model(
    X_tr: np.ndarray,
    X_te: np.ndarray,
    yw_tr: np.ndarray,
    yw_te: np.ndarray,
    w_tr: np.ndarray,
    seasons_te: np.ndarray,
    tscv: TimeSeriesSplit,
    n_trials: int,
    feature_cols: list[str],
) -> dict[str, Any]:
    print("\n" + "=" * 40)
    print(f"WIN MODEL (XGBClassifier — {len(feature_cols)} feature)")
    print("=" * 40)

    win_model, win_params = _train_with_optuna(
        X_tr, yw_tr, w_tr, tscv, "classify", n_trials, "WIN",
    )

    y_pred_win = win_model.predict(X_te)
    y_prob_win_raw = win_model.predict_proba(X_te)[:, 1]
    acc = accuracy_score(yw_te, y_pred_win)
    brier = brier_score_loss(yw_te, y_prob_win_raw)
    ll = log_loss(yw_te, y_prob_win_raw)
    baseline_acc = max(float(np.mean(yw_te)), 1 - float(np.mean(yw_te)))

    print(f"\n  WIN Model Test Metrikleri:")
    print(f"    Accuracy  : {acc:.4f}  (Baseline: {baseline_acc:.4f})")
    print(f"    Brier     : {brier:.4f}")
    print(f"    Log-Loss  : {ll:.4f}")

    season_breakdown = _season_accuracy_breakdown(yw_te, y_pred_win, seasons_te)
    if season_breakdown:
        print("\n  Sezon bazli test accuracy:")
        for season, stats in season_breakdown.items():
            print(
                f"    {season}: n={stats['n']} "
                f"acc={stats['accuracy']:.1%} baseline={stats['baseline_accuracy']:.1%}"
            )

    print("\n  Platt Scaling (train holdout)...")
    calib_data = _fit_platt_on_holdout(win_model, X_tr, yw_tr, w_tr)
    calib_path = MODELS_DIR / "model_win_calibration.json"
    calib_path.write_text(json.dumps(calib_data, indent=2), encoding="utf-8")
    print(
        f"  -> Kalibrasyon: coef={calib_data['coef']:.4f}, "
        f"intercept={calib_data['intercept']:.4f} "
        f"(n={calib_data['holdout_samples']})"
    )

    cal_probs = _platt_calibrate(y_prob_win_raw, calib_data["coef"], calib_data["intercept"])
    brier_cal = brier_score_loss(yw_te, cal_probs)
    print(f"  -> Test Brier (kalibre): {brier_cal:.4f}")

    win_metrics: dict[str, Any] = {
        "accuracy": round(acc, 4),
        "baseline_accuracy": round(baseline_acc, 4),
        "brier_score": round(brier, 4),
        "log_loss": round(ll, 4),
        "brier_score_calibrated": round(brier_cal, 4),
        "best_params": win_params,
        "features": feature_cols,
        "feature_count": len(feature_cols),
        "season_breakdown": season_breakdown,
        "feature_importance": dict(
            sorted(
                dict(zip(feature_cols, win_model.feature_importances_.tolist())).items(),
                key=lambda x: -x[1],
            )
        ),
    }

    win_path = MODELS_DIR / "model_win.json"
    win_model.save_model(str(win_path))
    print(f"  -> Model kaydedildi: {win_path}")
    return win_metrics


def train(n_trials: int = DEFAULT_TRIALS, win_only: bool = False) -> dict[str, Any]:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("WNBA Model Egitimi Basliyor" + (" [WIN ONLY]" if win_only else ""))
    print("=" * 60)

    # Win ve regressor icin ayri feature matrisleri
    X_win, y_win, y_spread, y_total, weights, seasons = load_dataset(WIN_FEATURE_COLS)
    X_reg, _, _, _, _, _ = load_dataset(REGRESS_FEATURE_COLS)

    n = len(X_win)
    split_idx = int(n * 0.80)

    Xw_tr, Xw_te = X_win[:split_idx], X_win[split_idx:]
    Xr_tr, Xr_te = X_reg[:split_idx], X_reg[split_idx:]
    yw_tr, yw_te = y_win[:split_idx], y_win[split_idx:]
    ys_tr, ys_te = y_spread[:split_idx], y_spread[split_idx:]
    yt_tr, yt_te = y_total[:split_idx], y_total[split_idx:]
    w_tr = weights[:split_idx]
    seasons_te = seasons[split_idx:]

    print(f"[INFO] Toplam ornek: {n}")
    print(f"[INFO] Win features: {len(WIN_FEATURE_COLS)} | Regress features: {len(REGRESS_FEATURE_COLS)}")
    print(f"[INFO] Train: {split_idx} | Test: {n - split_idx}")
    print(f"[INFO] Ortalama sample weight (train): {w_tr.mean():.2f}")

    tscv = TimeSeriesSplit(n_splits=N_SPLITS)

    metrics: dict[str, Any] = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "n_train": split_idx,
        "n_test": n - split_idx,
        "n_trials": n_trials,
        "win_only_run": win_only,
    }

    metrics["win"] = _train_win_model(
        Xw_tr, Xw_te, yw_tr, yw_te, w_tr, seasons_te, tscv, n_trials, WIN_FEATURE_COLS,
    )

    if win_only:
        # Mevcut spread/total metriklerini koru
        metrics_path = MODELS_DIR / "metrics.json"
        if metrics_path.exists():
            prev = json.loads(metrics_path.read_text(encoding="utf-8"))
            metrics["spread"] = prev.get("spread", {})
            metrics["total"] = prev.get("total", {})
        metrics["regress_features"] = REGRESS_FEATURE_COLS
        metrics_path.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\n[OK] Metrikler kaydedildi: {metrics_path}")
        print("\n" + "=" * 60)
        print("WIN EGITIM OZETI")
        print("=" * 60)
        print(f"  Win Accuracy : {metrics['win']['accuracy']:.1%} (Baseline: {metrics['win']['baseline_accuracy']:.1%})")
        print(f"  Win Brier Cal: {metrics['win']['brier_score_calibrated']:.4f}")
        print("=" * 60)
        return metrics

    # SPREAD
    print("\n" + "=" * 40)
    print("SPREAD MODEL (XGBRegressor)")
    print("=" * 40)
    spread_model, spread_params = _train_with_optuna(
        Xr_tr, ys_tr, w_tr, tscv, "regress", n_trials, "SPREAD",
    )
    y_pred_spread = spread_model.predict(Xr_te)
    mae_spread = mean_absolute_error(ys_te, y_pred_spread)
    rmse_spread = float(np.sqrt(mean_squared_error(ys_te, y_pred_spread)))
    baseline_mae_spread = mean_absolute_error(ys_te, np.full_like(ys_te, np.mean(ys_tr)))
    print(f"\n  SPREAD: MAE={mae_spread:.2f} (Baseline: {baseline_mae_spread:.2f}) RMSE={rmse_spread:.2f}")

    metrics["spread"] = {
        "mae": round(mae_spread, 3),
        "rmse": round(rmse_spread, 3),
        "baseline_mae": round(baseline_mae_spread, 3),
        "best_params": spread_params,
        "features": REGRESS_FEATURE_COLS,
        "feature_importance": dict(
            sorted(
                dict(zip(REGRESS_FEATURE_COLS, spread_model.feature_importances_.tolist())).items(),
                key=lambda x: -x[1],
            )
        ),
    }
    spread_model.save_model(str(MODELS_DIR / "model_spread.json"))

    # TOTAL
    print("\n" + "=" * 40)
    print("TOTAL MODEL (XGBRegressor)")
    print("=" * 40)
    total_model, total_params = _train_with_optuna(
        Xr_tr, yt_tr, w_tr, tscv, "regress", n_trials, "TOTAL",
    )
    y_pred_total = total_model.predict(Xr_te)
    mae_total = mean_absolute_error(yt_te, y_pred_total)
    rmse_total = float(np.sqrt(mean_squared_error(yt_te, y_pred_total)))
    baseline_mae_total = mean_absolute_error(yt_te, np.full_like(yt_te, np.mean(yt_tr)))
    print(f"\n  TOTAL: MAE={mae_total:.2f} (Baseline: {baseline_mae_total:.2f}) RMSE={rmse_total:.2f}")

    metrics["total"] = {
        "mae": round(mae_total, 3),
        "rmse": round(rmse_total, 3),
        "baseline_mae": round(baseline_mae_total, 3),
        "best_params": total_params,
        "features": REGRESS_FEATURE_COLS,
        "feature_importance": dict(
            sorted(
                dict(zip(REGRESS_FEATURE_COLS, total_model.feature_importances_.tolist())).items(),
                key=lambda x: -x[1],
            )
        ),
    }
    total_model.save_model(str(MODELS_DIR / "model_total.json"))

    metrics["regress_features"] = REGRESS_FEATURE_COLS
    metrics_path = MODELS_DIR / "metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n[OK] Metrikler kaydedildi: {metrics_path}")

    print("\n" + "=" * 60)
    print("EGITIM OZETI")
    print("=" * 60)
    print(f"  Win  Accuracy : {metrics['win']['accuracy']:.1%} (Baseline: {metrics['win']['baseline_accuracy']:.1%})")
    print(f"  Win  Brier Cal: {metrics['win']['brier_score_calibrated']:.4f}")
    print(f"  Spread MAE    : {metrics['spread']['mae']:.2f} puan")
    print(f"  Total  MAE    : {metrics['total']['mae']:.2f} puan")
    print("=" * 60)
    return metrics


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="WNBA Model Egitimi")
    parser.add_argument("--trials", type=int, default=DEFAULT_TRIALS, help="Optuna deneme sayisi")
    parser.add_argument("--quick", action="store_true", help="Hizli test (5 deneme)")
    parser.add_argument("--win-only", action="store_true", help="Sadece Win modelini egit")
    args = parser.parse_args(argv)

    n_trials = 5 if args.quick else args.trials
    train(n_trials=n_trials, win_only=args.win_only)
    return 0


if __name__ == "__main__":
    sys.exit(main())
