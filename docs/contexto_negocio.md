# Contexto de Negocio y Arquitectura

## Objetivo del proyecto

Construir una solución de ciencia de datos end-to-end que **prediga la gravedad de un siniestro de tránsito en rutas de Chile** a partir de variables contextuales (temporales y geográficas), integrando múltiples fuentes de datos y sirviendo el modelo a través de un microservicio API consultado por un dashboard interactivo.

**Pregunta de negocio:** dado un contexto (fecha, hora, comuna/región, cercanía a un hospital), ¿qué tan grave podría ser un siniestro de tránsito en ruta? Esto permite priorizar recursos de fiscalización, señalización o respuesta de emergencia en zonas/horarios de mayor riesgo.

## Fuentes de datos (arquitectura del proyecto)

| Fuente | Tipo | Contenido | Rol en el proyecto |
|---|---|---|---|
| **Siniestros en Ruta Chile 2024** (CONASET) | CSV | 15.839 registros individuales de siniestros en rutas rurales/interurbanas, con fecha, ubicación, tipo, causa y resultado en personas | Fuente principal — variable objetivo y features de contexto |
| **Hospitales cercanos** (OpenStreetMap Overpass API) | API REST (consumida) | Ubicación de hospitales/clínicas por zona geográfica | Enriquecimiento — distancia al hospital más cercano por siniestro |
| **Datos enriquecidos** | SQL (SQLite/PostgreSQL) | Resultado del cruce CSV + API, limpio y listo para modelar | Almacenamiento intermedio del pipeline ETL |

## Flujo general del sistema

```
CSV (CONASET) ──┐
                 ├──► ETL (extract-transform-load) ──► SQL ──► Entrenamiento modelo ML
API Overpass ────┘                                                    │
                                                                       ▼
                                                        Modelo entrenado (.pkl/.joblib)
                                                                       │
                                                                       ▼
                                              API REST propia (microservicio) — /predict
                                                                       │
                                                                       ▼
                                              Dashboard interactivo (consume la API)
```

- **Docker**: contenedores separados para API, dashboard y base de datos, orquestados con `docker-compose`.
- **CI/CD**: automatización básica de pruebas/build.
- **Testing**: pruebas unitarias sobre funciones clave del ETL (ej. clasificación de gravedad, manejo de errores de la API).

---

## Usuarios potenciales del sistema

### 1. CONASET / Ministerio de Transportes *(política pública)*
Priorizar dónde invertir en señalización, radares, iluminación o mejoras de infraestructura vial. Si un tramo de ruta muestra alta probabilidad de siniestros graves en ciertos horarios/meses, eso justifica intervención concreta (ej. reductores de velocidad, fiscalización nocturna).

### 2. Carabineros / Fiscalización de Tránsito
Asignar patrullajes y controles de alcoholemia donde el modelo indica mayor riesgo de gravedad — no solo dónde hay más siniestros, sino **dónde son más graves cuando ocurren** (son cosas distintas: una comuna puede tener pocos siniestros pero muy letales).

### 3. SAMU / Servicios de Emergencia y Salud Pública
Aquí es donde la variable `distancia_hospital_km` cobra sentido real de negocio: si el modelo identifica zonas rurales con alto riesgo de siniestros fatales y lejos de un hospital, eso es información directa para decidir **dónde ubicar ambulancias o postas de urgencia**, o priorizar tiempos de respuesta.

### 4. Aseguradoras
Ajustar pólizas o primas de seguro automotriz según perfil de riesgo geográfico/temporal de una ruta — uso comercial real y bastante común en la industria.

### 5. Empresas de Transporte y Logística
Planificar rutas de camiones o buses evitando tramos/horarios de mayor riesgo de siniestros graves (turnos nocturnos, ciertos meses).

---

## Limitación honesta del modelo *(anticipar preguntas en la presentación)*

> [!IMPORTANT]
> El modelo predice gravedad usando variables de contexto siempre disponibles (hora, comuna, mes), pero **no** usa velocidad del vehículo, estado del conductor ni condiciones del momento exacto del siniestro — porque eso es data leakage o simplemente no está en el dataset.

Esto significa que en la práctica el modelo responde a una pregunta más acotada:

> *"Dado el patrón histórico de esta zona y horario, ¿qué tan graves tienden a ser los siniestros ahí?"*

Es decir, es un **modelo de riesgo estructural del lugar/momento**, no un sistema de predicción en tiempo real de un accidente específico. Esta distinción es clave para la defensa técnica del proyecto (IEP 2.1.3 — justificar la selección del modelo según la naturaleza del problema).

**El caso de uso más honesto y defendible:**
SAMU, Carabineros y CONASET usando el modelo como **herramienta de priorización de recursos por zona-horario**, no como un sistema que "prediga si alguien va a tener un accidente grave hoy".
