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


# 1b. Carga de barras reales (para el selector de la demo)
@st.cache_data
def load_barras_disponibles():
    """Trae las barras reales con sus estadísticas (costo promedio/máximo, PIB
    de la región), para que el usuario elija una barra concreta en vez de
    tener que inventar valores numéricos a mano -- más natural para la demo
    y evita combinaciones de costo/PIB que no existen en la realidad.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        query = """
        SELECT
            b.barra_nombre,
            b.region,
            AVG(c.costo_marginal_usd_mwh) as costo_promedio,
            MAX(c.costo_marginal_usd_mwh) as costo_maximo,
            AVG(p.pib_millones_clp) as pib_millones_clp
        FROM costos_marginales c
        JOIN dim_barras b ON c.barra_codigo = b.barra_codigo
        LEFT JOIN pib_regional p ON b.region = p.region
        WHERE b.barra_nombre IS NOT NULL
        GROUP BY b.barra_nombre, b.region
        HAVING pib_millones_clp IS NOT NULL
        ORDER BY b.region, b.barra_nombre
        """
        df = pd.read_sql(query, conn)
        conn.close()
        return df
    except Exception as e:
        st.sidebar.warning(f"No se pudieron cargar barras reales ({e}); se usará entrada manual.")
        return pd.DataFrame()


df_barras = load_barras_disponibles()

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
    # Solo se ofrecen los días presentes en los datos de entrenamiento
    # (2026-04-01 a 2026-04-04 = Miércoles a Sábado). Ofrecer días fuera de
    # ese rango sería extrapolación pura -- XGBoost, al ser un modelo de
    # árboles, no interpola/extrapola de forma confiable fuera del rango
    # de valores que vio en el entrenamiento.
    DIAS_DISPONIBLES = {
        2: "Miércoles",
        3: "Jueves",
        4: "Viernes",
        5: "Sábado",
    }
    dia = st.selectbox(
        "Día de la Semana",
        options=list(DIAS_DISPONIBLES.keys()),
        format_func=lambda x: DIAS_DISPONIBLES[x],
        index=0,
    )
    st.caption("⚠️ Solo se ofrecen los días presentes en los datos de entrenamiento (4 días: mié-sáb).")
    
    st.markdown("**Barra / Nodo**")
    if not df_barras.empty:
        opciones_barra = df_barras["barra_nombre"] + " — " + df_barras["region"]
        idx_seleccionado = st.selectbox(
            "Selecciona una barra real",
            options=range(len(df_barras)),
            format_func=lambda i: opciones_barra.iloc[i],
        )
        fila = df_barras.iloc[idx_seleccionado]
        costo_prom = float(fila["costo_promedio"])
        costo_max = float(fila["costo_maximo"])
        pib = float(fila["pib_millones_clp"])

        # Se muestran como referencia (no editables) para transparencia:
        # el usuario ve exactamente qué valores reales está usando el modelo.
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Costo Prom.", f"${costo_prom:.1f}")
        col_b.metric("Costo Máx.", f"${costo_max:.1f}")
        col_c.metric("PIB Región", f"{pib:,.0f}")
    else:
        # Fallback si no se pudo conectar a la BD: entrada manual como antes
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