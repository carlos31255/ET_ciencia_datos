import joblib
import pandas as pd
import os

import json

USAR_MOCK = False
MODEL_PATH = "models/saved_models/modelo.pkl"
THRESH_PATH = "models/best_threshold.json"
modelo = None
umbral_optimo = 0.5

def cargar_modelo():
    global modelo, umbral_optimo
    # Cargar umbral si existe
    if os.path.exists(THRESH_PATH):
        try:
            with open(THRESH_PATH, "r", encoding="utf-8") as f:
                umbral_optimo = json.load(f).get("umbral_severo", 0.5)
        except Exception as e:
            print(f"Error cargando umbral: {e}")
            
    if os.path.exists(MODEL_PATH):
        try:
            modelo = joblib.load(MODEL_PATH)
            return True
        except Exception as e:
            print(f"Error cargando el modelo: {e}")
            return False
    return False

# Intentar cargar al levantar la app
cargar_modelo()

def hacer_prediccion(datos: dict) -> dict:
    if not USAR_MOCK and modelo is None:
        raise ValueError("Modelo no cargado")

    if USAR_MOCK:
        return {
            "gravedad": "Leve",
            "probabilidades": {
                "Severo": 0.15,
                "Leve": 0.85
            }
        }

    hora = datos.get("hora_aprox", 0)
    if 0 <= hora <= 5:
        datos["franja_horaria"] = "Madrugada"
    elif 6 <= hora <= 11:
        datos["franja_horaria"] = "Mañana"
    elif 12 <= hora <= 17:
        datos["franja_horaria"] = "Tarde"
    else:
        datos["franja_horaria"] = "Noche"

    df = pd.DataFrame([datos])
    
    # Predecir
    probabilidades = modelo.predict_proba(df)[0]
    clases = modelo.classes_

    probs_dict = {str(clase): round(float(prob), 4) for clase, prob in zip(clases, probabilidades)}
    
    # Aplicar el umbral óptimo para decidir si es Severo
    prob_severo = probs_dict.get("Severo", 0.0)
    clase_ganadora = "Severo" if prob_severo >= umbral_optimo else "Leve"

    return {
        "gravedad": clase_ganadora,
        "probabilidades": probs_dict
    }