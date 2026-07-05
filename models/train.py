import os
import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline

# Definir rutas absolutas usando os
directorio_actual = os.path.dirname(os.path.abspath(__file__)) 
directorio_raiz = os.path.dirname(directorio_actual) 
ruta_datos = os.path.join(directorio_raiz, "data", "processed", "datos_limpios.csv")

# Cargar datos
print(f"Cargando datos desde: {ruta_datos}")
df = pd.read_csv(ruta_datos)

df.columns = df.columns.str.lower()

# Separar variables independientes (X) y objetivo (y)
X = df.drop(columns=["gravedad"])
y = df["gravedad"]

cat_cols = ["franja_horaria", "region_dpa", "comuna_dpa"]
num_cols = ["mes", "diasemana", "hora_aprox", "es_fin_de_semana",
            "distancia_hospital_km", "siniestros_por_region",
            "dist_media_region_km", "pct_fatal_region"]

# Crear el preprocesador
preprocessor = ColumnTransformer(
    transformers=[
        ("num", StandardScaler(), num_cols),
        ("cat", OneHotEncoder(handle_unknown="ignore"), cat_cols)
    ]
)

# Crear el Pipeline
pipeline = Pipeline(steps=[
    ("preprocessor", preprocessor),
    # Random Forest maneja bien múltiples clases. class_weight="balanced" es obligatorio por el desbalance.
    ("classifier", RandomForestClassifier(class_weight="balanced", random_state=42))
])

# Dividir datos (Estratificando 'y' para mantener la proporción de la clase Fatal)
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# Entrenar el modelo
print("Entrenando el modelo...")
pipeline.fit(X_train, y_train)

# Exportar modelo y datos de prueba a la carpeta models/
print("Exportando archivos...")

ruta_modelo = os.path.join(directorio_actual, "modelo.pkl")
ruta_x = os.path.join(directorio_actual, "X_test.csv")
ruta_y = os.path.join(directorio_actual, "y_test.csv")

joblib.dump(pipeline, ruta_modelo)
X_test.to_csv(ruta_x, index=False)
y_test.to_csv(ruta_y, index=False)

print(f"¡Éxito! Archivos guardados correctamente en: {directorio_actual}")