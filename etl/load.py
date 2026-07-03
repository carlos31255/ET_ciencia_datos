# -*- coding: utf-8 -*-
"""
etl/load.py
───────────
Módulo de carga (L del ETL).
Responsabilidades:
  1. Guardar el dataset procesado como CSV en data/processed/.
  2. Guardar el DataFrame de hospitales como CSV en data/processed/ (caché).
  3. Opcionalmente, cargar los datos a una base de datos SQL.
"""

import logging
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)

# ── Rutas de salida ──────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = ROOT / "data" / "processed"


def _asegurar_directorio(path: Path) -> None:
    """Crea el directorio si no existe."""
    path.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# 1. Guardar dataset procesado
# ─────────────────────────────────────────────────────────────────────────────

def guardar_dataset_procesado(
    df: pd.DataFrame,
    nombre: str = "datos_limpios.csv"
) -> Path:
    """
    Guarda el dataset transformado en data/processed/.

    Este archivo es la entrada para la etapa de modelado (models/).
    Tu compañero puede consumirlo directamente sin re-ejecutar el ETL.

    Parameters
    ----------
    df : pd.DataFrame
        Dataset procesado (salida de transform.transformar()).
    nombre : str
        Nombre del archivo CSV de salida.

    Returns
    -------
    Path
        Ruta absoluta del archivo guardado.
    """
    _asegurar_directorio(PROCESSED_DIR)
    ruta = PROCESSED_DIR / nombre
    df.to_csv(ruta, index=False, encoding="utf-8-sig")
    log.info(f"Dataset procesado guardado en: {ruta}  ({len(df):,} filas, {df.shape[1]} columnas)")
    return ruta


# ─────────────────────────────────────────────────────────────────────────────
# 2. Guardar hospitales (caché)
# ─────────────────────────────────────────────────────────────────────────────

def guardar_hospitales(
    df_hospitales: pd.DataFrame,
    nombre: str = "hospitales_chile.csv"
) -> Path:
    """
    Guarda el DataFrame de hospitales como caché en data/processed/.

    Al tener este archivo en disco, el ETL puede omitir la llamada a la API
    Overpass en ejecuciones futuras, lo que reduce el tiempo de ~50s a <1s.

    Parameters
    ----------
    df_hospitales : pd.DataFrame
        DataFrame de hospitales (salida de extract.obtener_hospitales()).
    nombre : str
        Nombre del archivo CSV de salida.

    Returns
    -------
    Path
        Ruta absoluta del archivo guardado.
    """
    _asegurar_directorio(PROCESSED_DIR)
    ruta = PROCESSED_DIR / nombre
    df_hospitales.to_csv(ruta, index=False, encoding="utf-8-sig")
    log.info(f"Caché de hospitales guardada: {ruta}  ({len(df_hospitales):,} registros)")
    return ruta


def cargar_hospitales_cache(
    nombre: str = "hospitales_chile.csv"
) -> pd.DataFrame | None:
    """
    Intenta cargar el caché de hospitales desde disco.

    Returns
    -------
    pd.DataFrame | None
        DataFrame de hospitales si existe el caché, None si no existe.
    """
    ruta = PROCESSED_DIR / nombre
    if ruta.exists():
        df = pd.read_csv(ruta)
        log.info(f"Hospitales cargados desde caché: {ruta}  ({len(df):,} registros)")
        return df
    log.info("No se encontró caché de hospitales — se consultará la API.")
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Ejecución directa: pipeline E → T → L completo
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(ROOT))

    from etl.extract import cargar_siniestros, obtener_hospitales
    from etl.transform import transformar

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    log.info("╔══ INICIO PIPELINE ETL COMPLETO ══╗")

    # Extract
    df_siniestros = cargar_siniestros()

    # Intentar cargar hospitales desde caché (evita llamar la API si ya existe)
    df_hospitales = cargar_hospitales_cache()
    if df_hospitales is None:
        df_hospitales = obtener_hospitales()
        guardar_hospitales(df_hospitales)

    # Transform
    df_procesado = transformar(df_siniestros, df_hospitales)

    # Load
    ruta_salida = guardar_dataset_procesado(df_procesado)

    log.info("╚══ PIPELINE ETL COMPLETO ══╝")
    log.info(f"Archivo listo para modelado: {ruta_salida}")
    print(f"\n[OK] ETL completado. Dataset guardado en:\n   {ruta_salida}")
    print(f"   Shape: {df_procesado.shape}")
    print(f"\nColumnas disponibles para el modelo:\n   {list(df_procesado.columns)}")
