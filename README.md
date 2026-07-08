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

## 🚀 Configuración y Ejecución

### 1. Entorno Virtual
Para ejecutar este proyecto, es estrictamente necesario crear un entorno virtual para aislar las dependencias:

**En Windows (VS Code):**
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

### 2. Ejecución del Pipeline (ETL)
Asegúrate de configurar tu archivo `.env` con el token de la API del Coordinador (`COORDINADOR_API_TOKEN`). Luego, para extraer datos reales y poblar tu base de datos SQLite, ejecuta:

```bash
python etl/pipeline.py --api-fecha-inicio "2026-04-01" --api-fecha-fin "2026-04-04" --api-max-paginas 50
```

### 3. Levantar la API (Microservicio)
Para encender el servidor de Machine Learning (FastAPI) y que quede escuchando peticiones:
```bash
uvicorn api.main:app --reload
```
Una vez corriendo, puedes acceder a la interfaz de prueba en `http://127.0.0.1:8000/docs`.
