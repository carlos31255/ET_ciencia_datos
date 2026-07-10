"""
pipeline.py — Orquestador ETL: PIB Regional + Costos Marginales -> SQL

Este script ejecuta el flujo completo llamando a los módulos:
- extract.py: Descarga y lectura de datos crudos
- transform.py: Limpieza, validación y cruces
- load.py: Carga a la base de datos SQL
"""

from __future__ import annotations
import argparse
import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine

# Importamos nuestros nuevos módulos
from extract import (
    leer_excel_pib_crudo,
    extraer_costos_marginales_raw,
    generar_mock_costos_marginales
)
from transform import (
    transformar_pib_regional,
    transformar_pib_totales_control,
    validar_integridad_regional,
    limpiar_duplicados_costos,
    generar_dimension_barras
)
from load import (
    crear_esquema,
    cargar_a_sql
)

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("etl_energia")


def ejecutar_pipeline(
    raw_dir: Path,
    out_dir: Path,
    db_url: str | None = None,
    api_token: str | None = None,
    api_fecha_inicio: str = "2026-04-01",
    api_fecha_fin: str = "2026-04-01",
    api_max_paginas: int | None = 3,
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Extract
    logger.info("--- Iniciando Extracción ---")
    df_pib_raw = leer_excel_pib_crudo(raw_dir / "CCNN2018_PIB_REGIONAL_T.xlsx")
    df_totales_raw = leer_excel_pib_crudo(raw_dir / "CCNN2018_PIB_REGIONAL_T_3Series.xlsx")
    
    token = api_token or os.getenv("COORDINADOR_API_TOKEN")
    if token:
        logger.info(f"Consultando API real del Coordinador ({api_fecha_inicio} a {api_fecha_fin})...")
        df_costos_raw = extraer_costos_marginales_raw(
            fecha_inicio=api_fecha_inicio,
            fecha_fin=api_fecha_fin,
            token=token,
            max_paginas=api_max_paginas,
        )
        if df_costos_raw.empty:
            logger.warning("La API no devolvió datos; se usa el mock como respaldo.")
            df_costos_raw = generar_mock_costos_marginales()
    else:
        logger.warning("No se encontró token; usando mock.")
        df_costos_raw = generar_mock_costos_marginales()

    # 2. Transform
    logger.info("--- Iniciando Transformación ---")
    df_pib = transformar_pib_regional(df_pib_raw)
    df_pib.to_csv(out_dir / "pib_regional_long.csv", index=False)

    df_totales = transformar_pib_totales_control(df_totales_raw)
    validar_integridad_regional(df_pib, df_totales)
    df_totales.to_csv(out_dir / "pib_totales_control.csv", index=False)

    df_costos = limpiar_duplicados_costos(df_costos_raw)
    nombre_salida_costos = "costos_marginales_real.csv" if token and not df_costos.empty else "costos_marginales_mock.csv"
    df_costos.to_csv(out_dir / nombre_salida_costos, index=False)

    df_barras = generar_dimension_barras(df_costos)
    df_barras.to_csv(out_dir / "dim_barras.csv", index=False)

    # 3. Load
    logger.info("--- Iniciando Carga a SQL ---")
    db_url = db_url or os.getenv("DATABASE_URL", f"sqlite:///{out_dir / 'energia.db'}")
    engine = create_engine(db_url)
    crear_esquema(engine)
    
    cargar_a_sql(df_pib, "pib_regional", engine)
    cargar_a_sql(df_costos, "costos_marginales", engine)
    cargar_a_sql(df_barras, "dim_barras", engine)

    logger.info("Pipeline ETL completado exitosamente.")


def main() -> None:
    parser = argparse.ArgumentParser(description="ETL: PIB Regional + Costos Marginales -> SQL")
    base_dir = Path(__file__).resolve().parent.parent
    parser.add_argument("--raw-dir", type=Path, default=base_dir / "data" / "raw")
    parser.add_argument("--out-dir", type=Path, default=base_dir / "data" / "processed")
    parser.add_argument("--db-url", type=str, default=None)
    parser.add_argument("--api-token", type=str, default=None)
    parser.add_argument("--api-fecha-inicio", type=str, default="2026-04-01")
    parser.add_argument("--api-fecha-fin", type=str, default="2026-04-01")
    parser.add_argument("--api-max-paginas", type=int, default=3)
    args = parser.parse_args()

    ejecutar_pipeline(
        args.raw_dir, args.out_dir, args.db_url,
        api_token=args.api_token,
        api_fecha_inicio=args.api_fecha_inicio,
        api_fecha_fin=args.api_fecha_fin,
        api_max_paginas=args.api_max_paginas,
    )

if __name__ == "__main__":
    main()
