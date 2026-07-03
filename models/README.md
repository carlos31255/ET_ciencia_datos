# Módulo de Modelado — `models/`

Esta carpeta es la siguiente etapa del pipeline, después del ETL.

---

## Punto de partida

El ETL ya dejó el dataset listo en:

```
data/processed/datos_limpios.csv   (15.838 filas, 20 columnas)
```

No necesitas correr nada del ETL. Carga directamente ese archivo:

```python
import pandas as pd

df = pd.read_csv("../data/processed/datos_limpios.csv")
```

---

## Variable objetivo

La columna que debes predecir es **`gravedad`**, con 4 clases:

| Clase | Descripción |
|---|---|
| `Fatal` | Al menos un fallecido |
| `Grave` | Al menos un herido grave |
| `Leve` | Solo heridos leves o menos graves |
| `Sin lesionados` | Sin víctimas |

---

## Features disponibles para el modelo

| Feature | Tipo | Descripción |
|---|---|---|
| `Mes` | Numérica | Mes del año (1–12) |
| `Diasemana` | Numérica | Día de la semana (1–7) |
| `Hora_aprox` | Numérica | Hora del día (0–23) |
| `es_fin_de_semana` | Binaria | 1 = sábado o domingo |
| `franja_horaria` | Categórica | Madrugada / Mañana / Tarde / Noche |
| `REGION_DPA` | Categórica | Código de región oficial |
| `COMUNA_DPA` | Categórica | Código de comuna oficial |
| `distancia_hospital_km` | Numérica | Km al hospital más cercano (Haversine) |
| `siniestros_por_region` | Numérica | Volumen histórico de siniestros en esa región |
| `dist_media_region_km` | Numérica | Distancia media al hospital en la región |
| `pct_fatal_region` | Numérica | % de siniestros fatales históricos en la región |

---

## Advertencia: desbalance de clases

Las clases no están balanceadas:

- Sin lesionados: 43.9%
- Leve: 39.2%
- Grave: 12.3%
- **Fatal: 4.6%** ← clase minoritaria crítica

**Obligatorio usar:**
- `class_weight='balanced'` en todos los modelos sklearn
- Métricas: **F1-macro** y **AUC-ROC multiclase (OvR)** — no usar accuracy sola
- Opcional: SMOTE con `imbalanced-learn` si se necesita oversampling

---

## Estructura sugerida

```
models/
  train.py        ← Pipeline de entrenamiento (sklearn)
  evaluate.py     ← Métricas y comparación de modelos
  predict.py      ← Función de predicción para la API
  modelo.pkl      ← Modelo entrenado exportado (ignorado por git si es pesado)
```

---

## Rama de trabajo

Trabaja en la rama `feature/modelo` y haz merge a `dev` cuando esté listo.

```bash
git checkout dev
git checkout -b feature/modelo
```
