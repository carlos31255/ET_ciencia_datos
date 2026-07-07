import os
import json
import optuna
import pandas as pd
import sys
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.ensemble import RandomForestClassifier
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline

# Asegurar importación de transformers locales
directorio_actual = os.path.dirname(os.path.abspath(__file__)) 
directorio_raiz = os.path.dirname(directorio_actual) 
sys.path.insert(0, directorio_raiz)
from models.transformers import RegionStatsEncoder

SEED = 42

def load_data():
    ruta_datos = os.path.join(directorio_raiz, "data", "processed", "datos_limpios.csv")
    df = pd.read_csv(ruta_datos, encoding='utf-8-sig')
    X = df.drop(columns=["IdAccident", "gravedad"])
    y = df["gravedad"]
    return X, y

def build_pipeline(params):
    cat_cols = ["franja_horaria", "REGION_DPA", "COMUNA_DPA"]
    num_cols = ["Mes", "Diasemana", "Hora_aprox", "es_fin_de_semana",
                "distancia_hospital_km", "siniestros_por_region",
                "dist_media_region_km", "pct_severo_region"]

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), num_cols),
            ("cat", OneHotEncoder(handle_unknown="ignore"), cat_cols)
        ]
    )

    pipeline = Pipeline(steps=[
        ("region_stats", RegionStatsEncoder(region_col="REGION_DPA")),
        ("preprocessor", preprocessor),
        ("classifier", RandomForestClassifier(
            class_weight="balanced", 
            random_state=SEED,
            n_jobs=-1,
            **params
        ))
    ])
    return pipeline

def objective(trial):
    X, y = load_data()
    
    # Espacio de búsqueda de hiperparámetros
    params = {
        'n_estimators': trial.suggest_int('n_estimators', 50, 200),
        'max_depth': trial.suggest_int('max_depth', 5, 25),
        'min_samples_split': trial.suggest_int('min_samples_split', 2, 20),
        'min_samples_leaf': trial.suggest_int('min_samples_leaf', 1, 50)
    }
    
    pipeline = build_pipeline(params)
    cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=SEED)
    
    # Evaluamos con macro F1 porque hay desbalance (Severo vs Leve)
    scores = cross_val_score(pipeline, X, y, cv=cv, scoring='f1_macro', n_jobs=-1)
    return scores.mean()

if __name__ == "__main__":
    print("Iniciando búsqueda de hiperparámetros con Optuna...")
    # Maximizar F1-Macro
    study = optuna.create_study(direction="maximize")
    # Limitar a 15 trials para que no tarde demasiado durante el desarrollo
    study.optimize(objective, n_trials=15)
    
    print("\nOptimización finalizada.")
    print(f"Mejor trial (F1-Macro: {study.best_value:.4f})")
    print("Mejores hiperparámetros:", study.best_params)
    
    # Guardar los mejores parámetros en un JSON
    ruta_json = os.path.join(directorio_actual, "best_params.json")
    with open(ruta_json, "w", encoding="utf-8") as f:
        json.dump(study.best_params, f, indent=4)
        
    print(f"Hiperparámetros guardados exitosamente en: {ruta_json}")
