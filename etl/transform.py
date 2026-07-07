# -*- coding: utf-8 -*-
"""
etl/transform.py
────────────────
Módulo de transformación (T del ETL).
Aplica las decisiones de diseño documentadas en el EDA:
  1. Validación de esquema y tipos de datos.
  2. Limpieza con múltiples técnicas de imputación y validación.
  3. Construcción de la variable objetivo: 'gravedad'.
  4. Ingeniería de features temporales derivadas.
  5. Cálculo de 'distancia_hospital_mas_cercano' (Haversine vectorizado).
  6. Enriquecimiento con agregados por región (groupby + merge/join).
  7. Optimización de tipos de datos (dtype) para reducir memoria.
  8. Descarte de columnas con data leakage o redundantes.
  9. Devuelve un DataFrame listo para la etapa de carga (load.py).
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
        if row["Fallecidos"] > 0 or row["Graves"] > 0:
            return "Severo"
        return "Leve"

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
# 6. Validación de esquema
# ─────────────────────────────────────────────────────────────────────────────

# Esquema esperado: columna -> (tipo_pandas, rango_válido o None)
ESQUEMA_SINIESTROS = {
    "IdAccident": ("int",   None),
    "Mes":        ("int",   (1, 12)),
    "Diasemana":  ("int",   (1, 7)),
    "Hora_aprox": ("int",   (0, 23)),
    "Lat":        ("float", (-56.0, -17.0)),
    "Lon":        ("float", (-76.0, -66.0)),
    "Fallecidos": ("int",   (0, None)),
    "Graves":     ("int",   (0, None)),
    "Leves":      ("int",   (0, None)),
}

def validar_esquema(df: pd.DataFrame) -> pd.DataFrame:
    """
    Valida el esquema del DataFrame: tipos de datos y rangos esperados.

    Emite warnings para columnas con tipos incorrectos o valores fuera de rango,
    e intenta coerción de tipo automática cuando es seguro hacerlo.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame crudo de siniestros.

    Returns
    -------
    pd.DataFrame
        DataFrame con tipos corregidos donde fue posible.
    """
    log.info("Validando esquema de datos...")
    errores = []

    for col, (tipo_esp, rango) in ESQUEMA_SINIESTROS.items():
        if col not in df.columns:
            errores.append(f"Columna faltante: '{col}'")
            continue

        # Verificar y coercionar tipo
        if tipo_esp == "int" and not pd.api.types.is_integer_dtype(df[col]):
            try:
                df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
                log.warning(f"'{col}' coercionado a entero.")
            except Exception:
                errores.append(f"'{col}' no pudo convertirse a entero.")

        elif tipo_esp == "float" and not pd.api.types.is_float_dtype(df[col]):
            try:
                df[col] = pd.to_numeric(df[col], errors="coerce")
                log.warning(f"'{col}' coercionado a float.")
            except Exception:
                errores.append(f"'{col}' no pudo convertirse a float.")

        # Verificar rango
        if rango and col in df.columns:
            lo, hi = rango
            fuera = 0
            if lo is not None:
                fuera += (df[col] < lo).sum()
            if hi is not None:
                fuera += (df[col] > hi).sum()
            if fuera > 0:
                log.warning(f"'{col}': {fuera} valores fuera del rango esperado {rango}.")

    if errores:
        log.error(f"Errores de esquema encontrados: {errores}")
        raise ValueError(f"Esquema inválido: {errores}")

    log.info("Esquema validado correctamente.")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# 7. Imputación de valores (múltiples técnicas documentadas)
# ─────────────────────────────────────────────────────────────────────────────

def imputar_valores(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica múltiples estrategias de imputación según el tipo y rol de cada columna.

    Estrategias aplicadas:
        - Columnas numéricas de conteo (víctimas): imputar con 0 (ausencia = sin víctimas).
        - Columnas temporales (Mes, Hora_aprox): imputar con mediana (robusta a outliers).
        - Columnas categóricas (REGION_DPA, COMUNA_DPA): imputar con moda.
        - Coordenadas (Lat, Lon): eliminar fila — no se puede imputar geolocalización.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame post-limpieza básica.

    Returns
    -------
    pd.DataFrame
        DataFrame sin valores nulos relevantes.
    """
    n_nulos_inicial = df.isnull().sum().sum()
    if n_nulos_inicial == 0:
        log.info("No se encontraron valores nulos — imputación no necesaria.")
        return df

    log.info(f"Iniciando imputación — {n_nulos_inicial} valores nulos encontrados.")

    # Columnas de conteo: imputar con 0
    cols_conteo = ["Fallecidos", "Graves", "Menos_Grav", "Leves", "Lesionados"]
    for col in cols_conteo:
        if col in df.columns and df[col].isnull().any():
            n = df[col].isnull().sum()
            df[col] = df[col].fillna(0)
            log.info(f"'{col}': {n} nulos imputados con 0 (técnica: zero-fill para conteos).")

    # Columnas temporales: imputar con mediana
    cols_temporales = ["Mes", "Hora_aprox", "Diasemana", "Diames"]
    for col in cols_temporales:
        if col in df.columns and df[col].isnull().any():
            n = df[col].isnull().sum()
            mediana = df[col].median()
            df[col] = df[col].fillna(mediana)
            log.info(f"'{col}': {n} nulos imputados con mediana={mediana} (técnica: mediana, robusta a outliers).")

    # Columnas categóricas: imputar con moda
    cols_categoricas = ["REGION_DPA", "COMUNA_DPA", "Tipo__CONA", "Causa__CON"]
    for col in cols_categoricas:
        if col in df.columns and df[col].isnull().any():
            n = df[col].isnull().sum()
            moda = df[col].mode()[0]
            df[col] = df[col].fillna(moda)
            log.info(f"'{col}': {n} nulos imputados con moda='{moda}' (técnica: moda para categóricas).")

    # Coordenadas: eliminar (no imputables)
    mask_coord_nulas = df["Lat"].isnull() | df["Lon"].isnull()
    if mask_coord_nulas.any():
        n = mask_coord_nulas.sum()
        df = df[~mask_coord_nulas].reset_index(drop=True)
        log.warning(f"{n} filas eliminadas por coordenadas nulas (no imputables).")

    log.info(f"Imputacion completa — nulos restantes: {df.isnull().sum().sum()}")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# 8. Enriquecimiento: agregados por región (groupby + merge/join)
# ─────────────────────────────────────────────────────────────────────────────

def enriquecer_con_agregados_region(df: pd.DataFrame) -> pd.DataFrame:
    """
    Enriquece el dataset con features agregadas por región (groupby + merge).

    Features añadidas:
        - siniestros_por_region:    N° total de siniestros en esa región.
        - dist_media_region_km:     Distancia media al hospital en esa región.
        - pct_fatal_region:         % de siniestros fatales en esa región (riesgo histórico).

    Estas features aportan contexto geográfico agregado que el modelo puede usar
    para aprender patrones regionales sin exponerse a data leakage.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame tras calcular distancia al hospital.

    Returns
    -------
    pd.DataFrame
        DataFrame con 3 columnas nuevas de contexto regional.
    """
    log.info("Enriqueciendo dataset con agregados por región (groupby + merge)...")

    # Groupby: conteo de siniestros por región
    agg_region = (
        df.groupby("REGION_DPA", observed=True)
        .agg(
            siniestros_por_region=("IdAccident", "count"),
            dist_media_region_km=("distancia_hospital_km", "mean"),
        )
        .round({"dist_media_region_km": 3})
        .reset_index()
    )

    # % de siniestros fatales por región
    if "gravedad" in df.columns:
        fatales_region = (
            df[df["gravedad"] == "Fatal"]
            .groupby("REGION_DPA", observed=True)
            .size()
            .reset_index(name="n_fatales")
        )
        agg_region = agg_region.merge(fatales_region, on="REGION_DPA", how="left")
        agg_region["n_fatales"] = agg_region["n_fatales"].fillna(0)
        agg_region["pct_fatal_region"] = (
            agg_region["n_fatales"] / agg_region["siniestros_por_region"] * 100
        ).round(2)
        agg_region = agg_region.drop(columns=["n_fatales"])

    # Join (merge left) de vuelta al dataset principal
    df = df.merge(agg_region, on="REGION_DPA", how="left")

    log.info(
        f"Agregados regionales añadidos: siniestros_por_region, "
        f"dist_media_region_km, pct_fatal_region."
    )
    return df


# ─────────────────────────────────────────────────────────────────────────────
# 9. Optimización de tipos de datos (memoria)
# ─────────────────────────────────────────────────────────────────────────────

def optimizar_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    """
    Reduce el uso de memoria optimizando los tipos de datos del DataFrame.

    Estrategias:
        - int64  → int32  para columnas enteras sin valores extremos.
        - float64 → float32 para columnas float de baja precisión requerida.
        - object  → category para columnas categóricas de baja cardinalidad.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame procesado.

    Returns
    -------
    pd.DataFrame
        DataFrame con tipos optimizados y menor huella de memoria.
    """
    mem_antes = df.memory_usage(deep=True).sum() / 1024**2

    # int64 -> int32
    cols_int = df.select_dtypes(include=["int64"]).columns
    for col in cols_int:
        if df[col].min() >= np.iinfo(np.int32).min and df[col].max() <= np.iinfo(np.int32).max:
            df[col] = df[col].astype(np.int32)

    # float64 -> float32
    cols_float = df.select_dtypes(include=["float64"]).columns
    for col in cols_float:
        df[col] = df[col].astype(np.float32)

    # object -> category (cardinalidad baja: < 50 valores únicos)
    cols_obj = df.select_dtypes(include=["object"]).columns
    for col in cols_obj:
        if df[col].nunique() < 50:
            df[col] = df[col].astype("category")

    mem_despues = df.memory_usage(deep=True).sum() / 1024**2
    ahorro = ((mem_antes - mem_despues) / mem_antes * 100)
    log.info(
        f"Optimizacion de dtypes: {mem_antes:.2f} MB -> {mem_despues:.2f} MB "
        f"(ahorro: {ahorro:.1f}%)"
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
        1. validar_esquema()
        2. limpiar_siniestros()
        3. imputar_valores()
        4. construir_variable_objetivo()
        5. agregar_features_temporales()
        6. calcular_distancia_hospital()
        7. enriquecer_con_agregados_region()
        8. optimizar_dtypes()
        9. descartar_columnas()

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
    log.info("=== INICIO PIPELINE DE TRANSFORMACION ===")

    df = validar_esquema(df_siniestros.copy())
    df = limpiar_siniestros(df)
    df = imputar_valores(df)
    df = construir_variable_objetivo(df)
    df = agregar_features_temporales(df)
    df = calcular_distancia_hospital(df, df_hospitales)

    df = descartar_columnas(df)
    df = optimizar_dtypes(df)

    log.info(f"=== TRANSFORMACION COMPLETA - Shape final: {df.shape} ===")
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
