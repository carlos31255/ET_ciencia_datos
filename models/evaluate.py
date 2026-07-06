import os
import pandas as pd
import joblib
from sklearn.metrics import classification_report, f1_score, roc_auc_score

directorio_actual = os.path.dirname(os.path.abspath(__file__))

ruta_modelo = os.path.join(directorio_actual, "modelo.pkl")
ruta_X = os.path.join(directorio_actual, "X_test.csv")
ruta_y = os.path.join(directorio_actual, "y_test.csv")

print("Cargando modelo y datos de prueba...")
modelo = joblib.load(ruta_modelo)
X_test = pd.read_csv(ruta_X)
y_test = pd.read_csv(ruta_y).squeeze()

print("Generando predicciones...")
y_pred = modelo.predict(X_test)
y_pred_proba = modelo.predict_proba(X_test)

f1_mac = f1_score(y_test, y_pred, average="macro")
auc_roc = roc_auc_score(y_test, y_pred_proba, multi_class="ovr")

# Mostrar resultados
print("\n" + "="*40)
print(" RESULTADOS DE EVALUACIÓN")
print("="*40)
print(f"F1-Macro:       {f1_mac:.4f}")
print(f"AUC-ROC (OvR):  {auc_roc:.4f}")
print("-" * 40)
print("Reporte de Clasificación Detallado:")
print(classification_report(y_test, y_pred))