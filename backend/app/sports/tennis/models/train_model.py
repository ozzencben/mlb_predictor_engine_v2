import json
import optuna
from pathlib import Path
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score
import xgboost as xgb

base_dir = Path(__file__).parent.parent
dataset_dir = base_dir / "data" / "dataset.json"

# --- 1. OPTUNA DENEME FONKSİYONU (Zeki Arama Motoru) ---
def objective(trial, X_train, y_train):
    """Optuna'nın binlerce kombinasyonu deneyeceği alan"""
    param = {
        # Denenecek parametre sınırlarını belirliyoruz
        "n_estimators": trial.suggest_int("n_estimators", 100, 500, step=50),
        "max_depth": trial.suggest_int("max_depth", 3, 6),
        "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.2, log=True),
        # Overfitting'i önleyen ekstra parametreler
        "subsample": trial.suggest_float("subsample", 0.6, 1.0),
        "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
        "eval_metric": "logloss",
        "random_state": 42
    }

    model = xgb.XGBClassifier(**param)

    # Modeli 5 farklı parçaya bölerek (5-Fold CV) test et ki şansa başarı elde etmesin
    score = cross_val_score(model, X_train, y_train, cv=5, scoring="accuracy", n_jobs=-1)
    return score.mean() # 5 sınavın ortalamasını Optuna'ya geri yolla

# --- 2. ANA EĞİTİM FONKSİYONU ---
def train_test_model():
    if not dataset_dir.exists():
        print("Hata: dataset.json dosyası bulunamadı. Önce dataset_generator.py çalıştırılmalı.")
        return
    
    with open(dataset_dir, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    X = []
    y = []

    for row in dataset:
        features = [
            row["feature_surface_rate"],
            row["feature_momentum_diff"],
            row["feature_ground_diff"],
            row["feature_fatigue"],
            row["feature_rank_diff"],
            row["feature_dominance_diff"],
            row["feature_h2h_score"],
            row["feature_game_dominance_diff"],
            row["feature_rest_days_diff"],
            row["feature_surface_elo_diff"],
        ]
        X.append(features)
        y.append(row["target_winner"])

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    print(f"=== OPTUNA: HİPERPARAMETRE AVI BAŞLIYOR ===")
    print(f"Eğitim Havuzu: {len(X_train)} maç | Sınav Havuzu: {len(X_test)} maç\n")
    
    # Optuna'ya "başarıyı en üst düzeye çıkar (maximize)" diyoruz
    study = optuna.create_study(direction="maximize")
    # n_trials=30 demek, Optuna'nın 30 farklı kombinasyon deneyeceği anlamına gelir. 
    study.optimize(lambda trial: objective(trial, X_train, y_train), n_trials=30) 

    print("\n--- OPTUNA ARAMASI BİTTİ ---")
    print(f"En İyi Çapraz Doğrulama (CV) Başarısı: %{study.best_value * 100:.2f}")
    print("Bulunan En Kusursuz Parametreler:", study.best_params)

    # --- 3. FİNAL MODELİNİ EN İYİ PARAMETRELERLE EĞİTME ---
    print("\n=== FİNAL MODELİ EĞİTİLİYOR ===")
    best_params = study.best_params
    best_params["eval_metric"] = "logloss"
    best_params["random_state"] = 42

    final_model = xgb.XGBClassifier(**best_params)
    final_model.fit(X_train, y_train)

    y_pred = final_model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    
    print("--- Gerçek Sınav Sonucu ---")
    print(f"Tahmin Motorunun Final Başarı Yüzdesi (Accuracy): %{accuracy * 100:.2f}")

    model_output_dir = base_dir / "data" / "tennis_brain.json"
    final_model.save_model(str(model_output_dir))
    print(f"-> Başarı: Optimize edilmiş model beyni '{model_output_dir.name}' adıyla diske mühürlendi!")

    return final_model

if __name__ == "__main__":
    train_test_model()