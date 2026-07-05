import pandas as pd
import joblib
from sklearn.metrics import classification_report, f1_score, roc_auc_score

# 1. Cargar el modelo y los datos de prueba
modelo = joblib.load("modelo.pkl")
X_test = pd.read_csv("X_test.csv")
y_test = pd.read_csv("y_test.csv").squeeze()

# 2. Generar predicciones y probabilidades
y_pred = modelo.predict(X_test)
y_pred_proba = modelo.predict_proba(X_test)

# 3. Calcular métricas obligatorias
f1_mac = f1_score(y_test, y_pred, average="macro")
auc_roc = roc_auc_score(y_test, y_pred_proba, multi_class="ovr")

# 4. Mostrar resultados
print("="*40)
print(" RESULTADOS DE EVALUACIÓN")
print("="*40)
print(f"F1-Macro:       {f1_mac:.4f}")
print(f"AUC-ROC (OvR):  {auc_roc:.4f}")
print("-" * 40)
print("Reporte de Clasificación Detallado:")
print(classification_report(y_test, y_pred))