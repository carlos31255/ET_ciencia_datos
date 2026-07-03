# Módulo API — `api/`

Microservicio REST que expone el modelo entrenado para que el dashboard lo consuma.

> **Prerequisito:** el modelo ya debe estar entrenado y exportado como `models/modelo.pkl`
> antes de reemplazar el mock por la predicción real.

---

## Qué construir aquí

### Archivos a crear

```
api/
  main.py       ← App FastAPI con los endpoints
  schemas.py    ← Definición de inputs/outputs con Pydantic
  predictor.py  ← Carga el modelo .pkl y hace la predicción
  README.md     ← Este archivo
```

---

## Endpoints requeridos

### `GET /health`
Verifica que la API está corriendo.

```json
// Respuesta esperada
{ "status": "ok", "modelo_cargado": true }
```

---

### `POST /predict`
Recibe los datos de un siniestro y devuelve la gravedad predicha.

**Input esperado:**
```json
{
  "mes": 3,
  "diasemana": 5,
  "hora_aprox": 22,
  "es_fin_de_semana": 0,
  "region_dpa": "13",
  "comuna_dpa": "13101",
  "lat": -33.45,
  "lon": -70.67,
  "distancia_hospital_km": 4.2,
  "siniestros_por_region": 1823,
  "dist_media_region_km": 8.5,
  "pct_fatal_region": 4.8
}
```

**Output esperado:**
```json
{
  "gravedad": "Leve",
  "probabilidades": {
    "Fatal": 0.03,
    "Grave": 0.12,
    "Leve": 0.71,
    "Sin lesionados": 0.14
  }
}
```

---

## Pasos de implementación (en orden)

- [ ] **1.** Instalar FastAPI y uvicorn
  ```bash
  pip install fastapi uvicorn
  ```

- [ ] **2.** Crear `schemas.py` con los modelos Pydantic de entrada y salida (validar rangos: mes 1–12, hora 0–23, lat en Chile, etc.)

- [ ] **3.** Crear `predictor.py` — cargar `models/modelo.pkl` con `joblib.load()`

- [ ] **4.** Crear `main.py` con los dos endpoints (`/health` y `/predict`)

- [ ] **5.** Probar localmente:
  ```bash
  uvicorn api.main:app --reload --port 8000
  ```
  Abrir `http://localhost:8000/docs` — FastAPI genera Swagger automáticamente.

- [ ] **6.** Agregar manejo de errores: si el modelo no está cargado, devolver `503 Service Unavailable`

- [ ] **7.** Agregar test en `tests/test_api_predict.py` que llame al endpoint con datos válidos e inválidos

---

## Validaciones obligatorias en `schemas.py`

| Campo | Tipo | Rango válido |
|---|---|---|
| `mes` | int | 1 – 12 |
| `diasemana` | int | 1 – 7 |
| `hora_aprox` | int | 0 – 23 |
| `es_fin_de_semana` | int | 0 o 1 |
| `lat` | float | -56.0 a -17.0 (Chile) |
| `lon` | float | -76.0 a -66.0 (Chile) |
| `distancia_hospital_km` | float | > 0 |

---

## Notas para la defensa

- La API devuelve **probabilidades por clase**, no solo la clase ganadora — esto permite al dashboard mostrar niveles de confianza.
- El endpoint `/health` es la prueba de que el sistema está desplegado y funcionando (criterio IEP 3.1.1 — demo en vivo).
- FastAPI genera documentación Swagger automática en `/docs` — muéstrala en la presentación.

---

## Rama de trabajo

```bash
git checkout dev
git checkout -b feature/api
```

Hacer merge a `dev` cuando esté listo y probado.
