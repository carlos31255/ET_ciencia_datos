# Dashboard de Energía (Frontend)

Construir la interfaz visual interactiva para el usuario final utilizando **Streamlit**.

## ¿Qué tienes disponible?

### 1. Base de Datos Local (`energia.db`)
En la carpeta `data/processed/energia.db` tienes la base de datos SQLite poblada con cientos de miles de registros reales (Costos marginales, Barras y PIB regional).
Puedes conectarte a ella directamente con `sqlite3` o `pandas` para armar gráficos históricos:
```python
import sqlite3
import pandas as pd

conn = sqlite3.connect('../data/processed/energia.db')
df = pd.read_sql("SELECT * FROM costos_marginales LIMIT 100", conn)
```

### 2. API Predictiva (FastAPI)
En la carpeta `api/` está el microservicio con los modelos K-Means y XGBoost cargados.
Para que tu dashboard consuma predicciones en tiempo real, primero levanta la API en una terminal separada:
```bash
uvicorn api.main:app --reload
```
Luego, desde tu código de Streamlit, haz peticiones POST a la API usando la librería `requests`:
```python
import requests

url = "http://127.0.0.1:8000/predict"
payload = {
    "costo_promedio": 58.5,
    "costo_maximo": 145.2,
    "pib_millones_clp": 19663.6,
    "hora_del_dia": 14,
    "dia_semana": 2,
    "pct_renovable": 85.0
}
respuesta = requests.post(url, json=payload)
prediccion = respuesta.json()
print("Cluster asignado:", prediccion["cluster_arquetipo"])
print("Costo predicho USD:", prediccion["costo_marginal_predicho_usd"])
```

## Próximos Pasos para ti:
1. Crea tu archivo `dashboards/app.py`.
2. Importa `streamlit` y `plotly`.
3. Arma un par de gráficos que muestren el costo histórico (leyendo de `energia.db`).
4. Haz un formulario en la barra lateral (`st.sidebar`) donde el usuario meta los 6 datos requeridos, envíalos a la API, y muestra la predicción en pantalla gigante.
5. Revisa cualquier tipo de error que pueda aparecer, y si la base de datos tiene persistencia en caso de que la api no funcione.
