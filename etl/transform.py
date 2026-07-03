# -*- coding: utf-8 -*-
"""
etl/transform.py
────────────────
Módulo de transformación (T del ETL).
Aplica las decisiones de diseño documentadas en el EDA:
  1. Limpieza y validación de datos crudos del CSV.
  2. Construcción de la variable objetivo: 'gravedad'.
  3. Ingeniería de features: features temporales derivadas.
  4. Cálculo de 'distancia_hospital_mas_cercano' cruzando CSV con API Overpass.
  5. Descarte de columnas con data leakage o redundantes.
  6. Devuelve un DataFrame listo para la etapa de carga (load.py).
"""

import logging
import numpy as np
import pandas as pd
from math import radians, sin, cos, sqrt, atan2

log = logging.getLogger(__name__)

# ── Columnas a descartar (justificación en EDA sección 8) ────────────────────
COLUMNAS_DESCARTAR = [
    "X", "Y",               # Redundantes con Lat/Lon
    "FID",                  # Identificador interno del CSV
    "Zona",                 # Varianza cero: 100% RURAL
    "Región", "Ciudad",     # Redundantes con versión DPA
    "Tipo__CONA",           # Data leakage: concurrente con la gravedad
    "Causa__CON",           # Data leakage: determinación posterior al siniestro
    "Fallecidos", "Graves",
    "Menos_Grav", "Leves",
    "Lesionados",           # Columnas fuente de la variable objetivo
    "Hora",                 # Reemplazada por Hora_aprox (numérica)
    "Fecha",                # Descompuesta en Mes, Diasemana, Año
]

# ── Columnas de coordenadas requeridas ───────────────────────────────────────
COLS_COORDENADAS = ["Lat", "Lon"]


# ─────────────────────────────────────────────────────────────────────────────
# 1. Limpieza básica
# ─────────────────────────────────────────────────────────────────────────────

def limpiar_siniestros(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica limpieza básica al DataFrame crudo de siniestros.

    - Elimina filas duplicadas.
    - Elimina filas con coordenadas inválidas (fuera del territorio de Chile).
    - Normaliza texto en columnas categóricas clave.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame crudo devuelto por extract.cargar_siniestros().

    Returns
    -------
    pd.DataFrame
        DataFrame limpio.
    """
    n_inicial = len(df)
    log.info(f"Iniciando limpieza — {n_inicial:,} registros.")

    # Duplicados
    df = df.drop_duplicates()
    log.info(f"Duplicados eliminados: {n_inicial - len(df)}")

    # Coordenadas fuera del rango geográfico de Chile
    mask_validas = (
        df["Lat"].between(-56.0, -17.0) &
        df["Lon"].between(-76.0, -66.0)
    )
    n_invalidas = (~mask_validas).sum()
    if n_invalidas > 0:
        log.warning(f"Registros con coordenadas fuera de Chile: {n_invalidas} — se eliminan.")
    df = df[mask_validas].reset_index(drop=True)

    # Normalizar texto en columnas categóricas
    cols_texto = ["Tipo__CONA", "Causa__CON", "Zona", "REGION_DPA", "COMUNA_DPA"]
    for col in cols_texto:
        if col in df.columns:
            df[col] = df[col].str.strip().str.upper()

    log.info(f"Limpieza completa — {len(df):,} registros válidos.")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# 2. Variable objetivo: gravedad
# ─────────────────────────────────────────────────────────────────────────────

def construir_variable_objetivo(df: pd.DataFrame) -> pd.DataFrame:
    """
    Crea la columna 'gravedad' a partir de las columnas de víctimas.

    Jerarquía de clasificación:
        Fatal          → si Fallecidos > 0
        Grave          → si Graves > 0 (y sin fallecidos)
        Leve           → si Menos_Grav > 0 o Leves > 0
        Sin lesionados → resto

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame con columnas Fallecidos, Graves, Menos_Grav, Leves.

    Returns
    -------
    pd.DataFrame
        DataFrame con columna 'gravedad' añadida.
    """
    def _clasificar(row):
        if row["Fallecidos"] > 0:
            return "Fatal"
        elif row["Graves"] > 0:
            return "Grave"
        elif row["Menos_Grav"] > 0 or row["Leves"] > 0:
            return "Leve"
        return "Sin lesionados"

    df["gravedad"] = df.apply(_clasificar, axis=1)
    dist = df["gravedad"].value_counts()
    log.info(f"Variable objetivo construida:\n{dist.to_string()}")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# 3. Ingeniería de features temporales
# ─────────────────────────────────────────────────────────────────────────────

def agregar_features_temporales(df: pd.DataFrame) -> pd.DataFrame:
    """
    Crea features derivadas de las variables temporales existentes.

    Nuevas columnas:
        es_fin_de_semana : int  (1 si Diasemana en {6,7}, 0 si no)
        franja_horaria   : str  (Madrugada / Mañana / Tarde / Noche)

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame con columnas Diasemana y Hora_aprox.

    Returns
    -------
    pd.DataFrame
        DataFrame con las dos nuevas columnas.
    """
    df["es_fin_de_semana"] = df["Diasemana"].isin([6, 7]).astype(int)

    def _franja(h):
        if 0 <= h < 6:   return "Madrugada"
        elif 6 <= h < 12: return "Mañana"
        elif 12 <= h < 18: return "Tarde"
        return "Noche"

    df["franja_horaria"] = df["Hora_aprox"].apply(_franja)
    log.info("Features temporales añadidas: es_fin_de_semana, franja_horaria.")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# 4. Distancia al hospital más cercano (Haversine)
# ─────────────────────────────────────────────────────────────────────────────

def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calcula la distancia en kilómetros entre dos coordenadas geográficas
    usando la fórmula de Haversine.
    """
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


def calcular_distancia_hospital(
    df_siniestros: pd.DataFrame,
    df_hospitales: pd.DataFrame
) -> pd.DataFrame:
    """
    Para cada siniestro, calcula la distancia en km al hospital más cercano.

    Estrategia: vectorización con numpy broadcasting para evitar bucles Python.
    Complejidad: O(n_siniestros × n_hospitales) — viable para ~15k × ~1.2k.

    Parameters
    ----------
    df_siniestros : pd.DataFrame
        DataFrame de siniestros con columnas Lat y Lon.
    df_hospitales : pd.DataFrame
        DataFrame de hospitales con columnas lat y lon.

    Returns
    -------
    pd.DataFrame
        df_siniestros con la columna 'distancia_hospital_km' añadida.
    """
    log.info(
        f"Calculando distancia a hospital más cercano "
        f"({len(df_siniestros):,} siniestros × {len(df_hospitales):,} hospitales)..."
    )

    # Arrays de hospitales
    lat_h = np.radians(df_hospitales["lat"].values)
    lon_h = np.radians(df_hospitales["lon"].values)

    distancias_min = []
    R = 6371.0

    for _, row in df_siniestros.iterrows():
        lat_s = np.radians(row["Lat"])
        lon_s = np.radians(row["Lon"])

        dlat = lat_h - lat_s
        dlon = lon_h - lon_s
        a = np.sin(dlat / 2)**2 + np.cos(lat_s) * np.cos(lat_h) * np.sin(dlon / 2)**2
        dist = R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
        distancias_min.append(dist.min())

    df_siniestros = df_siniestros.copy()
    df_siniestros["distancia_hospital_km"] = np.round(distancias_min, 3)
    log.info(
        f"Distancias calculadas. "
        f"Min: {df_siniestros['distancia_hospital_km'].min():.2f} km | "
        f"Max: {df_siniestros['distancia_hospital_km'].max():.2f} km | "
        f"Media: {df_siniestros['distancia_hospital_km'].mean():.2f} km"
    )
    return df_siniestros


# ─────────────────────────────────────────────────────────────────────────────
# 5. Descarte de columnas
# ─────────────────────────────────────────────────────────────────────────────

def descartar_columnas(df: pd.DataFrame) -> pd.DataFrame:
    """
    Elimina columnas con data leakage, redundantes o sin valor predictivo,
    según las decisiones documentadas en el EDA (sección 8).

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame con todas las columnas.

    Returns
    -------
    pd.DataFrame
        DataFrame solo con las columnas necesarias para el modelo.
    """
    cols_a_eliminar = [c for c in COLUMNAS_DESCARTAR if c in df.columns]
    df = df.drop(columns=cols_a_eliminar)
    log.info(
        f"Columnas eliminadas ({len(cols_a_eliminar)}): {cols_a_eliminar}\n"
        f"Columnas restantes ({len(df.columns)}): {list(df.columns)}"
    )
    return df


# ─────────────────────────────────────────────────────────────────────────────
# Función principal: pipeline de transformación completo
# ─────────────────────────────────────────────────────────────────────────────

def transformar(
    df_siniestros: pd.DataFrame,
    df_hospitales: pd.DataFrame
) -> pd.DataFrame:
    """
    Pipeline completo de transformación.

    Aplica en orden:
        1. limpiar_siniestros()
        2. construir_variable_objetivo()
        3. agregar_features_temporales()
        4. calcular_distancia_hospital()
        5. descartar_columnas()

    Parameters
    ----------
    df_siniestros : pd.DataFrame
        DataFrame crudo de siniestros (salida de extract.cargar_siniestros()).
    df_hospitales : pd.DataFrame
        DataFrame de hospitales (salida de extract.obtener_hospitales()).

    Returns
    -------
    pd.DataFrame
        Dataset procesado y listo para cargar en load.py.
    """
    log.info("=== INICIO PIPELINE DE TRANSFORMACIÓN ===")

    df = limpiar_siniestros(df_siniestros)
    df = construir_variable_objetivo(df)
    df = agregar_features_temporales(df)
    df = calcular_distancia_hospital(df, df_hospitales)
    df = descartar_columnas(df)

    log.info(f"=== TRANSFORMACIÓN COMPLETA — Shape final: {df.shape} ===")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# Ejecución directa (modo prueba rápida)
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent))
    from etl.extract import cargar_siniestros, obtener_hospitales

    df_s = cargar_siniestros()
    df_h = obtener_hospitales()
    df_final = transformar(df_s, df_h)

    print("\n--- Dataset transformado (primeras filas) ---")
    print(df_final.head(3))
    print(f"\nShape final: {df_final.shape}")
    print(f"\nColumnas: {list(df_final.columns)}")
    print(f"\nDistribución de gravedad:\n{df_final['gravedad'].value_counts()}")
