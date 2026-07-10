# Panel de Riesgo y Eficiencia Energética Regional

Este proyecto consiste en un pipeline de datos (ETL), modelamiento (Machine Learning) y visualización para analizar e identificar el **"estrés energético"** de las distintas regiones de Chile.

## 💡 Idea de Negocio
El objetivo principal es construir un dashboard analítico que cruza los costos marginales de la red eléctrica nacional (en tiempo real o histórico) con datos macroeconómicos regionales. 

Esto nos permite identificar qué regiones de Chile enfrentan mayor **"estrés energético"** (entendido como la combinación de un alto costo marginal de la electricidad frente al tamaño de su economía local), y agrupar o clasificar geográficamente las subestaciones/barras según su perfil de riesgo.

## 🗄️ Arquitectura de Datos (Fuentes ETL)

El pipeline de extracción, transformación y carga (ETL) integra **tres fuentes de datos de distinta naturaleza**, cumpliendo con altos estándares de ingeniería de datos:

| Fuente | Tipo | Aporte al Proyecto |
| :--- | :--- | :--- |
| **Coordinador Eléctrico Nacional (SIP)** | `API REST` | Costo marginal por barra eléctrica, obtenido mediante peticiones paginadas a la API oficial. |
| **Banco Central de Chile** | `CSV / Excel` | Producto Interno Bruto (PIB). Se extraen dos archivos: uno con el PIB de las 16 regiones para dar contexto socioeconómico, y otro con 3 series macro (Subtotal regionalizado, Extrarregional y PIB Nacional) para validación de integridad. |
| **Base de Datos Relacional** | `SQLite / SQL` | Almacenamiento histórico y normalizado (tablas de costos, regiones, y dimensión de barras). Permite la ejecución de *joins* complejos para cruzar la geografía con los costos eléctricos. |

## ⚙️ Estructura del Proyecto

El proyecto está diseñado bajo una arquitectura modular y escalable, cumpliendo con los estándares requeridos:

- `/etl/`: Scripts (`extract.py`, `transform.py`, `load.py`, `pipeline.py`) y notebooks Jupyter (`01_etl_experimentacion.ipynb`) para la ingesta y procesamiento de datos.
- `/models/`: Scripts y notebooks para el entrenamiento, evaluación y serialización del modelo de Machine Learning (K-Means).
- `/api/`: Código fuente del **Microservicio Interno** (ej. FastAPI). Este servidor carga el modelo entrenado y expone un endpoint REST (ej. por el puerto 8000 mediante Port Forward) para que el dashboard consulte las predicciones, manteniendo una arquitectura desacoplada.
- `/dashboards/`: Aplicación interactiva (ej. Streamlit o Dash) para la visualización del Panel de Riesgo Energético.
- `/docker/`: Archivos y configuraciones (`Dockerfile`, `docker-compose.yml`) para la contenerización del proyecto.
- `/docs/`: Documentación técnica, manuales y contexto del negocio.
- `/tests/`: Pruebas unitarias (`pytest`) para asegurar la calidad del código.
- `/data/`: Almacenamiento local dividido en `raw/` (datos originales) y `processed/` (datos limpios y base de datos SQL).
- `README.md`, archivos de configuración (ej. `.env`, `.gitignore`) y scripts de automatización en la raíz del proyecto.

## Configuracion y Ejecucion

Sigue estos pasos **en orden**. Si saltas alguno, el siguiente fallara.

---

### Paso 1: Clonar el repositorio y crear el entorno virtual

**En Windows:**
```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

**En Mac/Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

### Paso 2: Crear el archivo `.env` con el token

La base de datos y el token **nunca se suben a Git** (estan en `.gitignore`).
Cada integrante debe crear manualmente el archivo `.env` en la raiz del proyecto con este contenido:

```
COORDINADOR_API_TOKEN=aqui_va_el_token_que_te_pase_el_lider_del_equipo
```

Sin el token, el pipeline usara datos mock que no son compatibles con los notebooks de ML.

---

### Paso 3: Ejecutar el Pipeline ETL

Descarga los datos reales del Coordinador Electrico y genera `energia.db`. Tarda ~20 minutos para 1 dia de datos.

```bash
.\.venv\Scripts\python.exe etl/pipeline.py --api-fecha-inicio "2026-04-01" --api-fecha-fin "2026-04-01" --api-max-paginas 9999
```

Cuando termine veras: `Pipeline ETL completado exitosamente.`

---

### Paso 4: Entrenar los Modelos de Machine Learning

Abre Jupyter y ejecuta los notebooks **en este orden exacto** (Kernel > Restart and Run All en cada uno):

1. `etl/01_etl_experimentacion.ipynb` — EDA y validacion del ETL
2. `models/02_modelo_riesgo.ipynb` — K-Means + Clasificador → genera `modelo_rf.pkl` y `scaler.pkl`
3. `models/03_modelo_regresion.ipynb` — XGBoost + Optuna → genera `modelo_regresor.pkl`

Los tres archivos `.pkl` quedan en `models/saved_models/`.

---

### Paso 5: Levantar el Microservicio (API)

Con los `.pkl` generados, enciende el servidor FastAPI:

```bash
.\.venv\Scripts\python.exe -m uvicorn api.main:app --reload
```

Interfaz de prueba disponible en: `http://127.0.0.1:8000/docs`

---

### Paso 6: Dashboard

Para visualizar el panel de Streamlit (el simulador y los historicos), debes abrir **una segunda terminal**, activar el entorno y ejecutar la app:

**En Windows:**
```bash
.\.venv\Scripts\activate
python -m streamlit run dashboards/app.py
```

**En Mac/Linux:**
```bash
source .venv/bin/activate
python3 -m streamlit run dashboards/app.py
```

El panel interactivo se abrira automaticamente en tu navegador en `http://localhost:8501`.
