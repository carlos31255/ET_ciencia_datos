"""
Tests unitarios para etl/pipeline.py

Ejecutar desde la raíz del proyecto con:
    pytest tests/test_pipeline.py -v
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "etl"))
from transform import (
    limpiar_nombre_region,
    normalizar_texto,
    MAPA_REGIONES,
)
from extract import generar_mock_costos_marginales
from load import cargar_a_sql
from sqlalchemy import create_engine, text  # noqa: E402


def test_normalizar_texto_quita_tildes():
    assert normalizar_texto("Región de Ñuble") == "region de nuble"


def test_normalizar_texto_espacios_extra():
    assert normalizar_texto("  Los   Ríos  ") == "los rios"


def test_limpiar_nombre_region_quita_prefijo_numerico():
    entrada = "8. Región del Libertador General Bernardo OHiggins"
    assert limpiar_nombre_region(entrada) == "region del libertador general bernardo ohiggins"


def test_todas_las_claves_del_mapa_estan_normalizadas():
    """Cada clave del diccionario MAPA_REGIONES debe ser el resultado exacto
    de normalizar_texto (sin tildes, minúsculas, sin espacios extra)."""
    for clave in MAPA_REGIONES:
        assert clave == normalizar_texto(clave)


def test_mapa_regiones_tiene_16_entradas():
    assert len(MAPA_REGIONES) == 16


def test_mock_costos_marginales_estructura():
    df = generar_mock_costos_marginales(n_horas=10, seed=1)
    assert set(df.columns) == {
        "fecha", "barra_codigo", "barra_nombre", "costo_marginal_usd_mwh", "version"
    }
    assert (df["costo_marginal_usd_mwh"] >= 0).all()


def test_mock_costos_marginales_reproducible():
    """Misma semilla debe generar exactamente los mismos datos (reproducibilidad)."""
    df1 = generar_mock_costos_marginales(n_horas=20, seed=7)
    df2 = generar_mock_costos_marginales(n_horas=20, seed=7)
    pd.testing.assert_frame_equal(df1, df2)


def test_cargar_a_sql_inserta_filas_correctamente(tmp_path):
    db_path = tmp_path / "test.db"
    engine = create_engine(f"sqlite:///{db_path}")
    df = pd.DataFrame({"a": [1, 2, 3], "b": ["x", "y", "z"]})

    cargar_a_sql(df, "tabla_prueba", engine)

    with engine.connect() as conn:
        n_filas = conn.execute(text("SELECT COUNT(*) FROM tabla_prueba")).scalar()
    assert n_filas == 3


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
