# -*- coding: utf-8 -*-
"""
etl/extract.py
──────────────
Módulo de extracción (E del ETL).
Responsabilidades:
  1. Cargar el dataset de siniestros desde el CSV local.
  2. Consultar la API Overpass (OpenStreetMap) para obtener
     la ubicación de hospitales y centros de salud en Chile.
  3. Devolver ambos como DataFrames limpios para la etapa de transformación.
"""

import logging
import time
from pathlib import Path

import pandas as pd
import requests

# ── Configuración de logging ─────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Rutas ────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent   # raíz del proyecto
CSV_PATH = ROOT / "data" / "Rural_2024.csv"

# ── Configuración de la API Overpass ─────────────────────────────────────────
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
HEADERS = {
    "User-Agent": "EFT-SCY1101-ProyectoUniversitario/1.0 (contacto: tu_correo@duoc.cl)"
}

# Bounding box de Chile continental (sur a norte, oeste a este)
# Formato Overpass: [south, west, north, east]
CHILE_BBOX = (-56.0, -76.0, -17.0, -66.0)

# Tiempo máximo de espera para la API (segundos)
API_TIMEOUT = 60
# Reintentos en caso de fallo temporal
MAX_RETRIES = 3
RETRY_DELAY = 5   # segundos entre reintentos


# ─────────────────────────────────────────────────────────────────────────────
# 1. Extracción del CSV
# ─────────────────────────────────────────────────────────────────────────────

def cargar_siniestros(csv_path: Path = CSV_PATH) -> pd.DataFrame:
    """
    Carga el dataset de siniestros en rutas desde el CSV de CONASET.

    Parameters
    ----------
    csv_path : Path
        Ruta al archivo CSV (por defecto apunta a data/Rural_2024.csv).

    Returns
    -------
    pd.DataFrame
        DataFrame con todos los registros del CSV sin modificaciones.

    Raises
    ------
    FileNotFoundError
        Si el archivo CSV no se encuentra en la ruta especificada.
    """
    if not csv_path.exists():
        raise FileNotFoundError(
            f"CSV no encontrado: {csv_path}\n"
            "Asegúrate de que el archivo esté en la carpeta data/."
        )

    log.info(f"Cargando CSV desde: {csv_path}")
    df = pd.read_csv(csv_path)
    log.info(f"CSV cargado: {len(df):,} filas x {df.shape[1]} columnas")
    return df


# ─────────────────────────────────────────────────────────────────────────────
# 2. Extracción de hospitales vía API Overpass
# ─────────────────────────────────────────────────────────────────────────────

def _construir_query_hospitales(bbox: tuple) -> str:
    """
    Construye la query Overpass QL para obtener hospitales en el bbox dado.

    Parameters
    ----------
    bbox : tuple
        Tupla (south, west, north, east) con las coordenadas del bounding box.

    Returns
    -------
    str
        Query Overpass QL lista para enviar.
    """
    s, w, n, e = bbox
    return f"""
[out:json][timeout:{API_TIMEOUT}];
(
  node["amenity"="hospital"]({s},{w},{n},{e});
  node["healthcare"="hospital"]({s},{w},{n},{e});
  way["amenity"="hospital"]({s},{w},{n},{e});
  way["healthcare"="hospital"]({s},{w},{n},{e});
);
out center;
"""


def _parsear_elementos(elementos: list) -> pd.DataFrame:
    """
    Convierte la lista de elementos Overpass a un DataFrame estructurado.

    Parameters
    ----------
    elementos : list
        Lista de dicts devuelta por la API Overpass.

    Returns
    -------
    pd.DataFrame
        DataFrame con columnas: osm_id, tipo, nombre, lat, lon.
    """
    registros = []
    for elem in elementos:
        tags = elem.get("tags", {})
        # Para 'way', las coords vienen en 'center'
        if elem["type"] == "way":
            centro = elem.get("center", {})
            lat = centro.get("lat")
            lon = centro.get("lon")
        else:
            lat = elem.get("lat")
            lon = elem.get("lon")

        registros.append({
            "osm_id": elem.get("id"),
            "osm_type": elem.get("type"),
            "nombre": tags.get("name", "Sin nombre"),
            "amenity": tags.get("amenity", ""),
            "healthcare": tags.get("healthcare", ""),
            "lat": lat,
            "lon": lon,
        })

    return pd.DataFrame(registros)


def obtener_hospitales(bbox: tuple = CHILE_BBOX) -> pd.DataFrame:
    """
    Consulta la API Overpass para obtener hospitales y centros de salud en Chile.

    Implementa reintentos automáticos con espera entre intentos para
    manejar fallos temporales de la API.

    Parameters
    ----------
    bbox : tuple
        Bounding box (south, west, north, east). Por defecto: Chile continental.

    Returns
    -------
    pd.DataFrame
        DataFrame con columnas: osm_id, osm_type, nombre, amenity, healthcare, lat, lon.

    Raises
    ------
    RuntimeError
        Si la API falla tras todos los reintentos configurados.
    """
    query = _construir_query_hospitales(bbox)
    log.info("Consultando API Overpass para hospitales en Chile...")

    for intento in range(1, MAX_RETRIES + 1):
        try:
            inicio = time.time()
            resp = requests.get(
                OVERPASS_URL,
                params={"data": query},
                headers=HEADERS,
                timeout=API_TIMEOUT,
            )
            elapsed = round(time.time() - inicio, 2)

            if resp.status_code == 200:
                elementos = resp.json().get("elements", [])
                log.info(
                    f"API respondió en {elapsed}s — "
                    f"{len(elementos)} hospitales/centros encontrados."
                )
                df = _parsear_elementos(elementos)
                # Eliminar registros sin coordenadas
                df = df.dropna(subset=["lat", "lon"]).reset_index(drop=True)
                log.info(f"Hospitales con coordenadas válidas: {len(df)}")
                return df

            elif resp.status_code == 429:
                log.warning(f"Rate limit (429). Esperando {RETRY_DELAY}s antes de reintentar...")
                time.sleep(RETRY_DELAY)

            else:
                log.warning(
                    f"Intento {intento}/{MAX_RETRIES} — "
                    f"Status {resp.status_code}. Reintentando en {RETRY_DELAY}s..."
                )
                time.sleep(RETRY_DELAY)

        except requests.exceptions.Timeout:
            log.warning(f"Intento {intento}/{MAX_RETRIES} — Timeout. Reintentando...")
            time.sleep(RETRY_DELAY)

        except requests.exceptions.ConnectionError as e:
            log.error(f"Error de conexión: {e}")
            time.sleep(RETRY_DELAY)

    raise RuntimeError(
        f"API Overpass no respondió tras {MAX_RETRIES} intentos. "
        "Verifica tu conexión o intenta más tarde."
    )


# ─────────────────────────────────────────────────────────────────────────────
# Ejecución directa (modo prueba rápida)
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Prueba 1: Cargar CSV
    df_siniestros = cargar_siniestros()
    print("\n--- Siniestros (primeras filas) ---")
    print(df_siniestros.head(3))

    # Prueba 2: Obtener hospitales
    df_hospitales = obtener_hospitales()
    print("\n--- Hospitales extraídos (primeros 5) ---")
    print(df_hospitales.head())
    print(f"\nTotal hospitales: {len(df_hospitales)}")
