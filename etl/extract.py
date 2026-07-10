import logging
import time
import numpy as np
import pandas as pd
import requests
from pathlib import Path
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger("etl_energia")

API_BASE_URL = "https://sipub.api.coordinador.cl"
ENDPOINT_COSTO_MARGINAL = "/costo-marginal-real/v4/findByDate"


def crear_sesion_http(reintentos: int = 3, backoff: float = 1.5) -> requests.Session:
    sesion = requests.Session()
    estrategia = Retry(
        total=reintentos,
        backoff_factor=backoff,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adaptador = HTTPAdapter(max_retries=estrategia)
    sesion.mount("https://", adaptador)
    return sesion


def leer_excel_pib_crudo(ruta_excel: Path, header_row: int = 2) -> pd.DataFrame:
    """Extrae la pestaña 'Cuadro' del Excel del BCentral sin hacer transformaciones."""
    if not ruta_excel.exists():
        raise FileNotFoundError(f"No se encontró el archivo Excel: {ruta_excel}")
    return pd.read_excel(ruta_excel, sheet_name="Cuadro", header=header_row)


def _limpiar_pagina_costos_marginales(registros):
    df = pd.DataFrame(registros)
    if df.empty:
        return df
    df["barra_info"] = df["barra_info"].replace("nan", np.nan)
    df["fecha_hora"] = pd.to_datetime(df["fecha_hora"], errors="coerce")
    columnas = ["fecha_hora", "barra_transf", "barra_info", "cmg_usd_mwh_", "version"]
    return df[columnas].rename(columns={
        "fecha_hora": "fecha",
        "barra_transf": "barra_codigo",
        "barra_info": "barra_nombre",
        "cmg_usd_mwh_": "costo_marginal_usd_mwh",
    })


def extraer_costos_marginales_raw(fecha_inicio: str, fecha_fin: str, token: str, limit: int = 1000,
                                   max_paginas: int | None = None, pausa: float = 0.2) -> pd.DataFrame:
    """Extrae los costos paginando desde la API. Retorna el df concatenado con posibles duplicados."""
    sesion = crear_sesion_http()
    paginas_df = []
    pagina = 0

    while True:
        params = {
            "startDate": fecha_inicio,
            "endDate": fecha_fin,
            "page": pagina,
            "limit": limit,
            "user_key": token,
        }
        try:
            resp = sesion.get(f"{API_BASE_URL}{ENDPOINT_COSTO_MARGINAL}", params=params, timeout=30)
            resp.raise_for_status()
        except requests.exceptions.RequestException as e:
            logger.error(f"Fallo al consultar la API del Coordinador en página {pagina}: {e}")
            raise

        payload = resp.json()
        registros = payload.get("data", [])
        if not registros:
            break

        paginas_df.append(_limpiar_pagina_costos_marginales(registros))

        total_paginas = payload.get("totalPages", 1)
        pagina += 1
        
        # Log para mostrar el progreso en vivo
        if pagina % 5 == 0 or pagina == total_paginas:
            logger.info(f"Descargando página {pagina} de {total_paginas}...")
            
        if pagina >= total_paginas or (max_paginas is not None and pagina >= max_paginas):
            break
        time.sleep(pausa)

    if not paginas_df:
        return pd.DataFrame(columns=["fecha", "barra_codigo", "barra_nombre", "costo_marginal_usd_mwh", "version"])

    df_final = pd.concat(paginas_df, ignore_index=True)
    logger.info(f"Extraídas {len(df_final)} filas raw ({pagina} páginas) desde la API.")
    return df_final


def generar_mock_costos_marginales(n_horas: int = 500, seed: int = 42) -> pd.DataFrame:
    """Mock para desarrollo sin API token."""
    rng = np.random.default_rng(seed)
    barras = [
        ("CRUCERO_______220", "S/E Crucero 220kV"),
        ("CHARRUA_______220", "S/E Charrúa 220kV"),
        ("A.JAHUEL______220", "S/E Alto Jahuel 220kV"),
        ("CARDONES______220", "S/E Cardones 220kV"),
        ("ANCOA_________220", "S/E Ancoa 220kV"),
    ]
    fechas = pd.date_range("2026-01-01", periods=n_horas, freq="h")
    base_por_barra = {b[0]: v for b, v in zip(barras, [45, 60, 55, 40, 58])}

    filas = []
    for fecha in fechas:
        for barra_codigo, barra_nombre in barras:
            ruido = rng.normal(0, 8)
            filas.append({
                "fecha": fecha,
                "barra_codigo": barra_codigo,
                "barra_nombre": barra_nombre,
                "costo_marginal_usd_mwh": max(round(base_por_barra[barra_codigo] + ruido, 2), 0),
                "version": "MOCK",
            })
    return pd.DataFrame(filas)
