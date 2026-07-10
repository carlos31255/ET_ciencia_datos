
import streamlit as st
import pandas as pd
import sqlite3
import requests
import plotly.express as px
import os

# Para ejecutar
# streamlit run C:\Users\noram\Downloads\ET_ciencia_datos-feature-dashboard\dashboards\app.py

# Configuración inicial de la página
st.set_page_config(
    page_title="Dashboard SEN | Predicción de Costos",
    page_icon="⚡",
    layout="wide"
)

st.title("⚡ Sistema Eléctrico Nacional: Análisis y Predicción")
st.markdown("---")

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.abspath(os.path.join(CURRENT_DIR, "..", "data", "processed", "energia.db"))

# 1. Conexión a Base de Datos Local y Carga de Datos (Históricos)
@st.cache_data
def load_historical_data():
    try:
        conn = sqlite3.connect(DB_PATH)
        
        query = """
        SELECT 
            fecha, 
            AVG(costo_marginal_usd_mwh) as costo_marginal_usd_mwh 
        FROM costos_marginales 
        GROUP BY fecha
        ORDER BY fecha
        """
        df = pd.read_sql(query, conn)
        conn.close()
        
        # Convertir a datetime
        if 'fecha' in df.columns:
            df['fecha'] = pd.to_datetime(df['fecha'])
            
        return df
    except sqlite3.OperationalError as e:
        st.error(f" **Error de conexión a BD:** {e}")
        return pd.DataFrame()

df_historico = load_historical_data()

# Visualización de Datos Históricos (Panel Principal)
st.subheader("📊 Histórico de Costos Marginales")

# Contenedor vacío que podemos actualizar después
grafico_placeholder = st.empty() 

if not df_historico.empty:
    fig = px.line(
        df_historico, 
        x='fecha', 
        y='costo_marginal_usd_mwh', 
        title="Fluctuación de Costos",
        labels={'fecha': 'Fecha y Hora', 'costo_marginal_usd_mwh': 'Costo (USD/MWh)'},
        color_discrete_sequence=['#1f77b4']
    )
    grafico_placeholder.plotly_chart(fig, width="stretch")
else:
    st.warning("No hay datos históricos disponibles para mostrar.")

#  Simulador Predictivo (Barra Lateral con conexión a FastAPI)
st.sidebar.header(" Simulador XGBoost")
st.sidebar.markdown("Modifica los parámetros para predecir el costo marginal.")

# Controles de formulario
with st.sidebar.form("form_prediccion"):
    hora = st.slider("Hora del Día", min_value=0, max_value=23, value=14)
    dia = st.selectbox("Día de la Semana (0=Lunes, 6=Domingo)", options=[0, 1, 2, 3, 4, 5, 6], index=2)
    
    st.markdown("**Variables de Entorno (Nodo)**")
    costo_prom = st.number_input("Costo Promedio (USD)", value=58.5)
    costo_max = st.number_input("Costo Máximo (USD)", value=145.2)
    pib = st.number_input("PIB Regional (MM CLP)", value=19663.6)
    
    submit_button = st.form_submit_button("Generar Predicción")

# Lógica de Petición a la API y Manejo de Errores
if submit_button:
    payload = {
        "costo_promedio": costo_prom,
        "costo_maximo": costo_max,
        "pib_millones_clp": pib,
        "hora_del_dia": hora,
        "dia_semana": dia
    }
        
    API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/predict")
    
    try:
        # Un timeout corto (ej. 3 segundos) evita que la app se quede congelada si la API está caída
        with st.spinner('Consultando modelo...'):
            respuesta = requests.post(API_URL, json=payload, timeout=3)
            respuesta.raise_for_status() # Lanza un error si el código HTTP no es 200
            
            prediccion = respuesta.json()
            cluster = prediccion.get("cluster_arquetipo", "Desconocido")
            costo = prediccion.get("costo_marginal_predicho_usd", 0.0)
            
            # Mostrar resultados en grande
            st.markdown("---")
            st.subheader("Resultados de la Predicción")
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric(label="Arquetipo Asignado (K-Means)", value=f"Cluster {cluster}")
            with col2:
                # Destacando el KPI principal
                st.metric(label="Costo Predicho (XGBoost)", value=f"${costo:.2f} USD")

            if not df_historico.empty:
                ultima_fecha = df_historico['fecha'].max()
                fecha_simulada = ultima_fecha + pd.Timedelta(days=1)
                fecha_simulada = fecha_simulada.replace(hour=hora)

                ultimo_costo = df_historico.loc[df_historico['fecha'] == ultima_fecha, 'costo_marginal_usd_mwh'].values[0]

                # Dibujamos la línea de progresión punteada
                fig.add_scatter(
                    x=[ultima_fecha, fecha_simulada],
                    y=[ultimo_costo, costo],
                    mode='lines',
                    line=dict(dash='dash', color='gray', width=2),
                    name='Tendencia Esperada'
                )

                # 4. Agregamos la estrella roja de la predicción encima
                fig.add_scatter(
                    x=[fecha_simulada],
                    y=[costo],
                    mode='markers+text',
                    marker=dict(color='red', size=16, symbol='star'),
                    name='Predicción',
                    text=[f'${costo:.2f}'],
                    textposition='top center'
                )

                # 5. Sobrescribimos el gráfico en el contenedor vacío
                grafico_placeholder.plotly_chart(fig, width="stretch")

                

    except requests.exceptions.ConnectionError:
        st.error(" **Error de Conexión:** No se pudo contactar a la API Predictiva. Asegúrate de que el servidor FastAPI esté corriendo (`uvicorn api.main:app --reload`). El dashboard histórico sigue funcional.")
    except requests.exceptions.Timeout:
        st.error(" **Tiempo de espera agotado:** La API tardó demasiado en responder.")
    except Exception as e:
        st.error(f" **Error inesperado:** {e}")