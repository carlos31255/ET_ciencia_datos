import joblib
import pandas as pd
import os

USAR_MOCK = False
MODEL_PATH = "models/saved_models/modelo.pkl"
modelo = None

def cargar_modelo():
    global modelo
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
                "Fatal": 0.03,
                "Grave": 0.12,
                "Leve": 0.71,
                "Sin lesionados": 0.14
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
    clase_ganadora = modelo.predict(df)[0]

    return {
        "gravedad": str(clase_ganadora),
        "probabilidades": probs_dict
    }