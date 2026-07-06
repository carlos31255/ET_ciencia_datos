import joblib
import pandas as pd
import os

def probar_prediccion():
    directorio_actual = os.path.dirname(os.path.abspath(__file__))
    ruta_modelo = os.path.join(directorio_actual, "modelo.pkl")
    
    print(f"Cargando modelo desde: {ruta_modelo}")
    modelo = joblib.load(ruta_modelo)
    
    datos_mock = {
        "mes": 3,
        "diasemana": 5,
        "hora_aprox": 22,
        "es_fin_de_semana": 0,
        "franja_horaria": "Noche",
        "region_dpa": "13",
        "comuna_dpa": "13101",
        "distancia_hospital_km": 4.2,
        "siniestros_por_region": 1823,
        "dist_media_region_km": 8.5,
        "pct_fatal_region": 4.8
    }

    df_entrada = pd.DataFrame([datos_mock])
    
    clase = modelo.predict(df_entrada)[0]
    probabilidades = dict(zip(modelo.classes_, modelo.predict_proba(df_entrada)[0]))
    
    print(f"Gravedad Predicha: {clase}")
    print("Probabilidades por clase:")
    for c, p in probabilidades.items():
        print(f"  - {c}: {p:.4f}")

if __name__ == "__main__":
    probar_prediccion()