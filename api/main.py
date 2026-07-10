from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import joblib
import pandas as pd
import numpy as np
import os

# Inicializar la app FastAPI
app = FastAPI(
    title="API de Predicción de Energía Eléctrica (CEN)",
    description="Microservicio que integra modelos de Machine Learning (K-Means + XGBoost) para predecir costos marginales horarios.",
    version="1.0.0"
)

# Variables globales para los modelos
kmeans_model = None
scaler = None
xgboost_regressor = None

# Rutas absolutas a los modelos (asumiendo que la API se corre desde la raíz del proyecto)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__line__ if '__file__' not in globals() else __file__)))
MODELS_DIR = os.path.join(BASE_DIR, 'models', 'saved_models')

@app.on_event("startup")
def load_models():
    """Carga los modelos en memoria al iniciar el servidor."""
    global kmeans_model, scaler, xgboost_regressor
    try:
        kmeans_model = joblib.load(os.path.join(MODELS_DIR, 'kmeans_model.pkl'))
        scaler = joblib.load(os.path.join(MODELS_DIR, 'scaler.pkl'))
        xgboost_regressor = joblib.load(os.path.join(MODELS_DIR, 'modelo_regresor.pkl'))
        print("[OK] Modelos cargados exitosamente en la API.")
    except Exception as e:
        print(f"[ERROR] Error al cargar los modelos. Verifica la ruta: {e}")

# Esquema de datos de entrada (Pydantic)
class EnergyPredictionRequest(BaseModel):
    costo_promedio: float = Field(..., description="Costo histórico promedio de la barra (USD/MWh)")
    costo_maximo: float = Field(..., description="Costo histórico máximo de la barra (USD/MWh)")
    pib_millones_clp: float = Field(..., description="PIB de la región donde está la barra")
    hora_del_dia: int = Field(..., ge=0, le=23, description="Hora a predecir (0-23)")
    dia_semana: int = Field(..., ge=0, le=6, description="Día de la semana (0=Lunes, 6=Domingo)")

class EnergyPredictionResponse(BaseModel):
    cluster_arquetipo: int
    costo_marginal_predicho_usd: float

@app.get("/")
def home():
    return {"mensaje": "Bienvenido a la API Predictiva de Energía Eléctrica. Ve a /docs para probarla."}

@app.post("/predict", response_model=EnergyPredictionResponse)
def predict_energy_cost(data: EnergyPredictionRequest):
    """
    Endpoint principal de inferencia.
    Paso 1: Predice el clúster con K-Means (No Supervisado)
    Paso 2: Usa el clúster y variables temporales para predecir el costo con XGBoost (Supervisado)
    """
    if kmeans_model is None or xgboost_regressor is None:
        raise HTTPException(status_code=500, detail="Los modelos no están cargados.")

    # 1. Feature Engineering para K-Means
    # El escalador espera un DataFrame con los mismos nombres de columnas que en el entrenamiento
    x_cluster_raw = pd.DataFrame([{
        'costo_promedio': data.costo_promedio,
        'costo_maximo': data.costo_maximo,
        'pib_millones_clp': data.pib_millones_clp
    }])
    
    try:
        x_cluster_scaled = scaler.transform(x_cluster_raw)
        cluster_pred = kmeans_model.predict(x_cluster_scaled)[0]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error en K-Means: {str(e)}")

    # 2. Feature Engineering para XGBoost
    # XGBoost espera: ['hora_del_dia', 'dia_semana', 'cluster_arquetipo']
    # NOTA: 'pct_renovable' fue retirada del modelo. Se había implementado como
    # una variable SIMULADA en función de 'hora_del_dia' (ver notebook 03), lo que
    # introducía fuga de datos (proxy leakage): el modelo terminaba aprendiendo
    # el patrón horario a través de esta variable falsa en vez de usar
    # 'hora_del_dia' directamente, distorsionando la interpretación del feature
    # importance. Se intentó reemplazarla por el dato real de generación ERNC
    # vía el endpoint /generacion-real/v3/findByDate del SIP, pero el servicio
    # devolvió consistentemente error 502 (InternalServerErrorException) — ver
    # docs/reporte_tecnico.md, sección de limitaciones conocidas.
    x_reg_raw = pd.DataFrame([{
        'hora_del_dia': data.hora_del_dia,
        'dia_semana': data.dia_semana,
        'cluster_arquetipo': cluster_pred
    }])
    
    try:
        # Predecir con el modelo supervisado
        costo_pred = xgboost_regressor.predict(x_reg_raw)[0]
        # Nos aseguramos de que no de negativo por error estadístico
        costo_pred = max(0.0, float(costo_pred)) 
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error en XGBoost: {str(e)}")

    return EnergyPredictionResponse(
        cluster_arquetipo=int(cluster_pred),
        costo_marginal_predicho_usd=round(costo_pred, 2)
    )
