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
