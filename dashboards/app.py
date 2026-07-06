import streamlit as st
import requests
import pandas as pd

# Configuracion de la pagina
st.set_page_config(
    page_title="Prediccion de Siniestros Viales",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Constantes
API_URL = "http://127.0.0.1:8000/predict"

# Diccionarios de mapeo para mejorar la UI
DICCIONARIO_REGIONES = {
    "Metropolitana": "13",
    "Valparaiso": "05",
    "Biobio": "08",
    "Araucania": "09",
    "Maule": "07",
    "Coquimbo": "04",
    "O'Higgins": "06",
    "Los Lagos": "10",
    "Antofagasta": "02",
    "Los Rios": "14",
    "Tarapaca": "01",
    "Arica y Parinacota": "15",
    "Atacama": "03",
    "Nuble": "16",
    "Aysen": "11",
    "Magallanes": "12"
}

# Interfaz Principal
st.title("🚦 Predictor de Gravedad en Siniestros Viales")
st.markdown("""
Esta herramienta permite predecir la gravedad esperada de un accidente de transito en zonas rurales de Chile,
utilizando un modelo de Random Forest entrenado con datos de CONASET y distancias a centros de salud (OSM).
""")

# Barra lateral para Inputs
st.sidebar.header("📝 Datos del Siniestro")

mes = st.sidebar.slider("Mes", 1, 12, 6)
diasemana = st.sidebar.slider("Dia de la semana (1=Lunes, 7=Domingo)", 1, 7, 3)
hora_aprox = st.sidebar.slider("Hora (0-23)", 0, 23, 14)
es_fin_de_semana = 1 if diasemana >= 6 else 0

st.sidebar.subheader("📍 Ubicacion")
region_nombre = st.sidebar.selectbox("Region", list(DICCIONARIO_REGIONES.keys()))
region_dpa = DICCIONARIO_REGIONES[region_nombre]
comuna_dpa = st.sidebar.text_input("Codigo Comuna (DPA)", "13101")

lat = st.sidebar.number_input("Latitud", min_value=-56.0, max_value=-17.0, value=-33.45)
lon = st.sidebar.number_input("Longitud", min_value=-76.0, max_value=-66.0, value=-70.67)

st.sidebar.subheader("🏥 Infraestructura y Estadisticas")
distancia_hospital_km = st.sidebar.number_input("Distancia al hospital (km)", min_value=0.1, max_value=200.0, value=5.0, step=0.5)

# Valores por defecto para metricas regionales (en un sistema real se consultarian a la DB)
st.sidebar.markdown("*Estadisticas Regionales (Valores Historicos)*")
siniestros_por_region = st.sidebar.number_input("Total Siniestros (Historico)", min_value=0, value=1500)
dist_media_region_km = st.sidebar.number_input("Dist. Media Hospital Region", min_value=0.0, value=10.0)
pct_fatal_region = st.sidebar.number_input("% Fatalidad Region", min_value=0.0, max_value=100.0, value=4.5)

# Boton de prediccion
if st.sidebar.button("Predecir Gravedad 🚀", use_container_width=True):
    # Preparar el payload
    payload = {
        "mes": mes,
        "diasemana": diasemana,
        "hora_aprox": hora_aprox,
        "es_fin_de_semana": es_fin_de_semana,
        "region_dpa": region_dpa,
        "comuna_dpa": str(comuna_dpa),
        "lat": lat,
        "lon": lon,
        "distancia_hospital_km": distancia_hospital_km,
        "siniestros_por_region": siniestros_por_region,
        "dist_media_region_km": dist_media_region_km,
        "pct_fatal_region": pct_fatal_region
    }

    with st.spinner("Consultando modelo de Machine Learning..."):
        try:
            # Llamar a la API
            response = requests.post(API_URL, json=payload)
            
            if response.status_code == 200:
                data = response.json()
                gravedad = data["gravedad"]
                probs = data["probabilidades"]
                
                # Definir color segun gravedad
                color_map = {
                    "Fatal": "red",
                    "Grave": "orange",
                    "Leve": "blue",
                    "Sin lesionados": "green"
                }
                color = color_map.get(gravedad, "gray")
                
                # Mostrar resultado principal
                st.markdown("---")
                st.subheader("Resultado de la Prediccion")
                st.markdown(f"### Nivel de Gravedad Esperado: :{color}[**{gravedad.upper()}**]")
                
                # Mostrar probabilidades en un grafico
                st.markdown("#### Probabilidades por Clase")
                
                # Convertir a DataFrame para chart nativo de Streamlit
                df_probs = pd.DataFrame(
                    list(probs.items()),
                    columns=["Clase", "Probabilidad"]
                )
                df_probs["Probabilidad (%)"] = df_probs["Probabilidad"] * 100
                
                # Ordenar
                df_probs = df_probs.sort_values(by="Probabilidad (%)", ascending=False)
                
                # Mostrar bar chart
                st.bar_chart(df_probs.set_index("Clase")["Probabilidad (%)"])
                
                # Info adicional
                with st.expander("Ver JSON de la API"):
                    st.json(data)
                    
            elif response.status_code == 503:
                st.error("❌ El servicio de prediccion no esta disponible. El modelo no esta cargado.")
            else:
                st.error(f"❌ Error en la API: {response.text}")
                
        except requests.exceptions.ConnectionError:
            st.error("❌ No se pudo conectar con la API. Verifica que uvicorn este corriendo en el puerto 8000.")
