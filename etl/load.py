import logging
import pandas as pd
from sqlalchemy import text

logger = logging.getLogger("etl_energia")

DDL_REGIONES = """
CREATE TABLE IF NOT EXISTS pib_regional (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    periodo DATE NOT NULL,
    anio INTEGER NOT NULL,
    trimestre INTEGER NOT NULL,
    region TEXT NOT NULL,
    pib_millones_clp REAL NOT NULL
);
"""

DDL_COSTOS = """
CREATE TABLE IF NOT EXISTS costos_marginales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha DATETIME NOT NULL,
    barra_codigo TEXT NOT NULL,
    barra_nombre TEXT,
    costo_marginal_usd_mwh REAL NOT NULL,
    version TEXT
);
"""

DDL_DIM_BARRAS = """
CREATE TABLE IF NOT EXISTS dim_barras (
    barra_codigo TEXT PRIMARY KEY,
    barra_nombre TEXT,
    region TEXT
);
"""


def crear_esquema(engine) -> None:
    """Crea (si no existen) las tablas del esquema relacional."""
    with engine.begin() as conn:
        conn.execute(text(DDL_REGIONES))
        conn.execute(text(DDL_COSTOS))
        conn.execute(text(DDL_DIM_BARRAS))
    logger.info("Esquema creado/verificado en la base de datos.")


def cargar_a_sql(df: pd.DataFrame, tabla: str, engine, si_existe: str = "replace") -> None:
    """Carga un dataframe a SQL con manejo de errores."""
    try:
        df.to_sql(tabla, con=engine, if_exists=si_existe, index=False)
        logger.info(f"Cargadas {len(df)} filas en tabla '{tabla}'.")
    except Exception as e:
        logger.error(f"Error al cargar tabla '{tabla}': {e}")
        raise
