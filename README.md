# Panel de Riesgo y Eficiencia Energetica Regional

Este proyecto consiste en un pipeline de datos (ETL), modelamiento (Machine Learning) y visualizacion para analizar e identificar el **"estres energetico"** de las distintas regiones de Chile.

## Idea de Negocio

El objetivo principal es construir un dashboard analitico que cruza los costos marginales de la red electrica nacional (en tiempo real o historico) con datos macroeconomicos regionales.

Esto permite identificar que regiones de Chile enfrentan mayor **"estres energetico"** (combinacion de alto costo marginal frente al tamano de su economia local), y agrupar o clasificar geograficamente las subestaciones/barras segun su perfil de riesgo.

## Arquitectura de Datos (Fuentes ETL)

El pipeline ETL integra tres fuentes de datos de distinta naturaleza:

| Fuente | Tipo | Aporte al Proyecto |
| :--- | :--- | :--- |
| **Coordinador Electrico Nacional (SIP)** | `API REST` | Costo marginal por barra electrica, obtenido mediante peticiones paginadas a la API oficial. 16,704 registros horarios extraidos. |
| **Banco Central de Chile** | `CSV / Excel` | PIB de las 16 regiones para dar contexto socioeconomico. |
| **Base de Datos Relacional** | `SQLite / SQL` | Almacenamiento historico y normalizado. Permite joins complejos para cruzar la geografia con los costos electricos. |

## Estructura del Proyecto

- `/etl/`: Scripts (`extract.py`, `transform.py`, `load.py`, `pipeline.py`) y notebook `01_etl_experimentacion.ipynb` para la ingesta y procesamiento de datos.
- `/models/`: Notebooks de Machine Learning en orden de ejecucion:
  - `02_modelo_riesgo.ipynb`: K-Means (clustering de nodos) + Random Forest Classifier. Genera `kmeans_model.pkl`, `scaler.pkl` y `modelo_rf.pkl`.
  - `03_modelo_regresion.ipynb`: XGBoost Regressor optimizado con Optuna (15 trials, objetivo: minimizar RMSE). R2=0.88, RMSE=8.52 USD/MWh. Genera `modelo_regresor.pkl`.
- `/api/`: Microservicio FastAPI (`main.py`) que carga los modelos `.pkl` y expone el endpoint `/predict` en el puerto 8000.
- `/dashboards/`: Aplicacion Streamlit (`app.py`) con el simulador interactivo y el analisis historico por nodo.
- `/docker/`: Dockerfiles individuales para la API y el Dashboard.
- `/docs/`: Documentacion tecnica y reporte del proyecto.
- `/tests/`: Pruebas unitarias con pytest.
- `/data/`: Datos divididos en `raw/` (originales) y `processed/` (base de datos `energia.db`).
- `iniciar.bat` / `finalizar.bat`: Scripts de Windows para levantar y detener Docker con un doble clic.
- `docker-compose.yml`: Orquestacion de los contenedores API + Dashboard.

## Ramas de Git

El proyecto usa el siguiente flujo de trabajo por ramas:

| Rama | Proposito |
| :--- | :--- |
| `main` | Version estable y lista para presentacion |
| `dev` | Integracion de features antes de subir a main |
| `feature/etl` | Desarrollo del pipeline ETL |
| `feature/modelo` | Desarrollo de los modelos de ML |
| `feature/api` | Desarrollo del microservicio FastAPI |
| `feature/dashboard` | Desarrollo del dashboard Streamlit |

## Configuracion y Ejecucion

Sigue estos pasos **en orden**. Si saltas alguno, el siguiente fallara.

---

### Opcion Rapida: Docker (Recomendada)

Si tienes Docker instalado, puedes levantar todo el sistema (API + Dashboard) con un doble clic:

1. Ejecuta `iniciar.bat` para construir e iniciar los contenedores.
2. Accede al Dashboard en `http://localhost:8501` y a la API en `http://localhost:8000`.
3. Ejecuta `finalizar.bat` para detener y limpiar los contenedores.

O desde terminal:
```bash
docker-compose up --build
```

---

### Opcion Manual (Sin Docker)

#### Paso 1: Crear el entorno virtual

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

#### Paso 2: Crear el archivo `.env` con el token

La base de datos y el token **nunca se suben a Git** (estan en `.gitignore`).
Crea manualmente el archivo `.env` en la raiz del proyecto:

```
COORDINADOR_API_TOKEN=
```

---

#### Paso 3: Ejecutar el Pipeline ETL

Descarga los datos reales del Coordinador Electrico y genera `energia.db`. Tarda ~20 minutos por dia de datos.

```bash
.\.venv\Scripts\python.exe etl/pipeline.py --api-fecha-inicio "2026-04-01" --api-fecha-fin "2026-04-01" --api-max-paginas 9999
```

Cuando termine veras: `Pipeline ETL completado exitosamente.`

---

#### Paso 4: Entrenar los Modelos de Machine Learning

Abre Jupyter y ejecuta los notebooks **en este orden exacto** (Kernel > Restart and Run All en cada uno):

1. `etl/01_etl_experimentacion.ipynb` — EDA y validacion del ETL
2. `models/02_modelo_riesgo.ipynb` — K-Means + Random Forest Classifier -> genera `kmeans_model.pkl`, `scaler.pkl`, `modelo_rf.pkl`
3. `models/03_modelo_regresion.ipynb` — XGBoost + Optuna -> genera `modelo_regresor.pkl`

Los archivos `.pkl` quedan en `models/saved_models/`.

---

#### Paso 5: Levantar el Microservicio (API)

Con los `.pkl` generados, enciende el servidor FastAPI:

```bash
.\.venv\Scripts\python.exe -m uvicorn api.main:app --reload
```

Interfaz interactiva Swagger UI disponible en: `http://127.0.0.1:8000/docs`

---

#### Paso 6: Dashboard

Abre una segunda terminal y ejecuta:

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

El panel interactivo se abrira en `http://localhost:8501`.
