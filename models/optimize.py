import os
import json
import sys
import numpy as np
import pandas as pd
import optuna
from sklearn.base import clone
from sklearn.ensemble import RandomForestClassifier
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import f1_score

# Importar transformers locales
directorio_actual = os.path.dirname(os.path.abspath(__file__))
directorio_raiz = os.path.dirname(directorio_actual)
sys.path.insert(0, directorio_raiz)
from models.transformers import RegionStatsEncoder

SEED = 42

# ── Cargar datos ─────────────────────────────────────────────────────────────
ruta_datos = os.path.join(directorio_raiz, "data", "processed", "datos_limpios.csv")
df = pd.read_csv(ruta_datos, encoding='utf-8-sig')
df.columns = df.columns.str.lower()

X = df.drop(columns=["idaccident", "gravedad"])
y = df["gravedad"]

# ── Columnas del modelo ───────────────────────────────────────────────────────
cat_cols = ["franja_horaria", "region_dpa", "comuna_dpa"]
num_cols = ["mes", "diasemana", "hora_aprox", "es_fin_de_semana",
            "distancia_hospital_km", "siniestros_por_region",
            "dist_media_region_km", "pct_severo_region"]


def build_pipeline(params: dict) -> Pipeline:
    """Construye el pipeline completo con los parámetros dados."""
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), num_cols),
            ("cat", OneHotEncoder(handle_unknown="ignore"), cat_cols)
        ]
    )
    return Pipeline(steps=[
        # RegionStatsEncoder dentro del pipeline garantiza que sus
        # estadísticas se calculen SOLO sobre el fold de entrenamiento
        # y evita data leakage en cada iteración de CV.
        ("region_stats", RegionStatsEncoder(region_col="region_dpa")),
        ("preprocessor", preprocessor),
        ("classifier", RandomForestClassifier(**params))
    ])


def objective(trial: optuna.Trial) -> float:
    """
    Función objetivo para Optuna con espacio conservador para evitar overfitting.

    Espacio de búsqueda:
      - max_depth reducido (4-12): previene árboles gigantes que memorizan datos.
      - min_samples_split (5-20): requiere más evidencia antes de dividir un nodo.
      - min_samples_leaf (4-15): hojas más robustas, menos sensibles a outliers.
    """
    params = {
        "n_estimators":       trial.suggest_int("n_estimators",      50,  300),
        "max_depth":          trial.suggest_int("max_depth",          4,   12),
        "min_samples_split":  trial.suggest_int("min_samples_split",  5,   20),
        "min_samples_leaf":   trial.suggest_int("min_samples_leaf",   4,   15),
        "class_weight":       "balanced",
        "random_state":       SEED,
        "n_jobs":             -1
    }

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEED)
    f1_scores = []

    for train_idx, val_idx in cv.split(X, y):
        X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]

        # clone() asegura un pipeline limpio en cada fold
        pipe = build_pipeline(params)
        pipe.fit(X_train, y_train)

        preds = pipe.predict(X_val)
        score = f1_score(y_val, preds, average='macro')
        f1_scores.append(score)

    return float(np.mean(f1_scores))


if __name__ == "__main__":
    optuna.logging.set_verbosity(optuna.logging.INFO)
    print("Iniciando búsqueda de hiperparámetros con Optuna (50 trials, 5-Fold CV)...")

    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=50)

    print(f"\nOptimización finalizada.")
    print(f"Mejor F1-Macro (CV): {study.best_value:.4f}")
    print(f"Mejores hiperparámetros: {study.best_params}")

    # Guardar los mejores parámetros
    ruta_json = os.path.join(directorio_actual, "best_params.json")
    with open(ruta_json, "w", encoding="utf-8") as f:
        json.dump(study.best_params, f, indent=4)

    print(f"\nHiperparámetros guardados en: {ruta_json}")
