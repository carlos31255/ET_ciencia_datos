"""
Análisis de umbral óptimo mediante la curva Precision-Recall.
Guarda el umbral en models/best_threshold.json para uso en producción.
"""
import os
import sys
import json
import joblib
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.metrics import (
    precision_recall_curve, f1_score, classification_report, roc_auc_score
)

# ── Rutas ────────────────────────────────────────────────────────────────────
directorio_actual = os.path.dirname(os.path.abspath(__file__))
directorio_raiz = os.path.dirname(directorio_actual)
sys.path.insert(0, directorio_raiz)
from models.transformers import RegionStatsEncoder  # noqa: necesario para joblib

ruta_modelo  = os.path.join(directorio_actual, "saved_models", "modelo.pkl")
ruta_X       = os.path.join(directorio_actual, "X_test.csv")
ruta_y       = os.path.join(directorio_actual, "y_test.csv")
ruta_thresh  = os.path.join(directorio_actual, "best_threshold.json")
ruta_figura  = os.path.join(directorio_actual, "precision_recall_curve.png")

# ── Cargar modelo y datos de prueba ───────────────────────────────────────────
print("Cargando modelo y datos de prueba...")
modelo  = joblib.load(ruta_modelo)
X_test  = pd.read_csv(ruta_X, encoding="utf-8-sig")
y_test  = pd.read_csv(ruta_y, encoding="utf-8-sig").squeeze()

# ── Probabilidades para la clase "Severo" ─────────────────────────────────────
clases           = modelo.classes_.tolist()
idx_severo       = clases.index("Severo")
y_prob_severo    = modelo.predict_proba(X_test)[:, idx_severo]

# ── Curva Precision-Recall ────────────────────────────────────────────────────
precisions, recalls, thresholds = precision_recall_curve(
    y_test, y_prob_severo, pos_label="Severo"
)

# F1 en cada umbral (thresholds tiene un elemento menos que prec/rec)
f1_scores = (2 * precisions[:-1] * recalls[:-1]) / (
    precisions[:-1] + recalls[:-1] + 1e-8
)
idx_best  = np.argmax(f1_scores)
umbral_optimo = float(thresholds[idx_best])

print(f"\n--- Umbral por defecto (0.50) ---")
y_pred_default = (y_prob_severo >= 0.50).astype(int)
y_pred_default_labels = np.where(y_pred_default, "Severo", "Leve")
print(classification_report(y_test, y_pred_default_labels))

print(f"--- Umbral óptimo ({umbral_optimo:.4f}) ---")
y_pred_optimo = (y_prob_severo >= umbral_optimo).astype(int)
y_pred_optimo_labels = np.where(y_pred_optimo, "Severo", "Leve")
print(classification_report(y_test, y_pred_optimo_labels))

# ── Gráfica ───────────────────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(9, 6))
ax.plot(recalls, precisions, color="#4A90D9", lw=2, label="Precision-Recall curve")
ax.axvline(recalls[idx_best], color="#E8534A", linestyle="--", lw=1.5,
           label=f"Umbral óptimo = {umbral_optimo:.3f}\n"
                 f"Precision={precisions[idx_best]:.2f} | Recall={recalls[idx_best]:.2f}")
ax.axvline(recalls[(np.abs(thresholds - 0.50)).argmin()], color="#888",
           linestyle=":", lw=1.5, label="Umbral por defecto (0.50)")

ax.set_xlabel("Recall (Severo)", fontsize=12)
ax.set_ylabel("Precision (Severo)", fontsize=12)
ax.set_title("Curva Precision-Recall — Clase 'Severo'", fontsize=14, fontweight="bold")
ax.legend(fontsize=10)
ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(ruta_figura, dpi=150)
print(f"\nGráfica guardada en: {ruta_figura}")

# ── Guardar umbral ────────────────────────────────────────────────────────────
with open(ruta_thresh, "w", encoding="utf-8") as f:
    json.dump({"umbral_severo": umbral_optimo}, f, indent=4)
print(f"Umbral óptimo ({umbral_optimo:.4f}) guardado en: {ruta_thresh}")
