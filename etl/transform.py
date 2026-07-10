import re
import unicodedata
import logging
import pandas as pd

logger = logging.getLogger("etl_energia")

MAPA_REGIONES = {
    "region de arica y parinacota": "Arica y Parinacota",
    "region de tarapaca": "Tarapacá",
    "region de antofagasta": "Antofagasta",
    "region de atacama": "Atacama",
    "region de coquimbo": "Coquimbo",
    "region de valparaiso": "Valparaíso",
    "region metropolitana de santiago": "Metropolitana",
    "region del libertador general bernardo ohiggins": "O'Higgins",
    "region del maule": "Maule",
    "region de nuble": "Ñuble",
    "region del biobio": "Biobío",
    "region de la araucania": "La Araucanía",
    "region de los rios": "Los Ríos",
    "region de los lagos": "Los Lagos",
    "region de aysen del general carlos ibanez del campo": "Aysén",
    "region de magallanes y de la antartica chilena": "Magallanes",
}

REGIONES_CHILE = 16


def normalizar_texto(texto: str) -> str:
    texto = texto.strip()
    texto = "".join(
        c for c in unicodedata.normalize("NFD", texto)
        if unicodedata.category(c) != "Mn"
    )
    texto = texto.lower()
    texto = re.sub(r"\s+", " ", texto)
    return texto


def limpiar_nombre_region(nombre_columna: str) -> str:
    sin_numero = re.sub(r"^\d+\.\s*", "", nombre_columna)
    return normalizar_texto(sin_numero)


def mapear_region_barra(codigo: str, nombre: str) -> str:
    texto = f"{str(codigo)} {str(nombre)}".upper()
    if "ARICA" in texto or "PARINACOTA" in texto or "CHAPIQUINA" in texto: return "Arica y Parinacota"
    elif "IQUIQUE" in texto or "TARAPACA" in texto or "POZO ALMONTE" in texto: return "Tarapacá"
    elif "ANTOFAGASTA" in texto or "CALAMA" in texto or "MEJILLONES" in texto or "CRUCERO" in texto or "TOCOPILLA" in texto: return "Antofagasta"
    elif "COPIAPO" in texto or "VALLENAR" in texto or "ATACAMA" in texto or "CARDONES" in texto: return "Atacama"
    elif "LA SERENA" in texto or "COQUIMBO" in texto or "OVALLE" in texto or "ILLAPEL" in texto or "PAN DE AZUCAR" in texto: return "Coquimbo"
    elif "VALPARAISO" in texto or "VINA" in texto or "QUILLOTA" in texto or "LOS ANDES" in texto or "SAN ANTONIO" in texto: return "Valparaíso"
    elif "SANTIAGO" in texto or "MAIPO" in texto or "CERRO NAVIA" in texto or "ALTO JAHUEL" in texto or "POLPAICO" in texto: return "Metropolitana"
    elif "RANCAGUA" in texto or "SAN FERNANDO" in texto or "RAPEL" in texto or "O'HIGGINS" in texto or "OHIGGINS" in texto: return "O'Higgins"
    elif "TALCA" in texto or "CURICO" in texto or "LINARES" in texto or "MAULE" in texto or "COLBUN" in texto: return "Maule"
    elif "CHILLAN" in texto or "NUBLE" in texto or "ÑUBLE" in texto: return "Ñuble"
    elif "CONCEPCION" in texto or "LOS ANGELES" in texto or "BIOBIO" in texto or "CHARRUA" in texto or "CHIGUAYANTE" in texto or "RALCO" in texto: return "Biobío"
    elif "TEMUCO" in texto or "ARAUCANIA" in texto or "VILLARRICA" in texto or "ANGOL" in texto: return "La Araucanía"
    elif "VALDIVIA" in texto or "LOS RIOS" in texto or "PANGUIPULLI" in texto or "CHUMPULLO" in texto: return "Los Ríos"
    elif "PUERTO MONTT" in texto or "OSORNO" in texto or "CASTRO" in texto or "LOS LAGOS" in texto or "CHILOE" in texto: return "Los Lagos"
    elif "COYHAIQUE" in texto or "AYSEN" in texto or "PUERTO AYSEN" in texto: return "Aysén"
    elif "PUNTA ARENAS" in texto or "MAGALLANES" in texto or "NATALES" in texto: return "Magallanes"
    return "Desconocida"


def transformar_pib_regional(df_wide: pd.DataFrame) -> pd.DataFrame:
    region_cols = [c for c in df_wide.columns if c != "Periodo"]

    if len(region_cols) < REGIONES_CHILE:
        logger.warning(
            f"Se esperaban {REGIONES_CHILE} regiones y se encontraron {len(region_cols)}."
        )

    df_long = df_wide.melt(
        id_vars="Periodo", value_vars=region_cols,
        var_name="region_original", value_name="pib_millones_clp",
    )
    df_long["region_clave"] = df_long["region_original"].apply(limpiar_nombre_region)
    df_long["region"] = df_long["region_clave"].map(MAPA_REGIONES)

    no_mapeadas = df_long[df_long["region"].isna()]["region_clave"].unique()
    assert len(no_mapeadas) == 0, f"Quedaron claves de región sin mapear: {no_mapeadas}"

    df_long["Periodo"] = pd.to_datetime(df_long["Periodo"], errors="coerce")
    df_long["anio"] = df_long["Periodo"].dt.year
    df_long["trimestre"] = df_long["Periodo"].dt.quarter

    df_final = df_long[["Periodo", "anio", "trimestre", "region", "pib_millones_clp"]].sort_values(
        ["region", "Periodo"]
    ).reset_index(drop=True)

    logger.info(f"PIB regional transformado: {len(df_final)} filas, {df_final['region'].nunique()} regiones.")
    return df_final


def transformar_pib_totales_control(df: pd.DataFrame) -> pd.DataFrame:
    df["Periodo"] = pd.to_datetime(df["Periodo"])
    df = df.rename(columns={
        "17. Subtotal regionalizado": "subtotal_regionalizado",
        "18. Extrarregional": "extrarregional",
        "19. Producto Interno Bruto": "pib_nacional",
    })
    columnas_esperadas = ["subtotal_regionalizado", "extrarregional", "pib_nacional"]
    faltantes = [c for c in columnas_esperadas if c not in df.columns]
    if faltantes:
        logger.warning(f"Columnas no encontradas en archivo de totales: {faltantes}")
    return df[["Periodo", *columnas_esperadas]]


def validar_integridad_regional(
    df_pib_long: pd.DataFrame,
    df_totales: pd.DataFrame | None,
    tolerancia_pct: float = 1.0,
) -> None:
    if df_totales is None:
        return

    suma_regiones = df_pib_long.groupby("Periodo")["pib_millones_clp"].sum()
    control = df_totales.set_index("Periodo")["subtotal_regionalizado"]

    comparacion = pd.DataFrame({
        "suma_16_regiones": suma_regiones,
        "subtotal_oficial_bcentral": control,
    }).dropna()
    comparacion["diferencia_pct"] = (
        (comparacion["suma_16_regiones"] - comparacion["subtotal_oficial_bcentral"])
        / comparacion["subtotal_oficial_bcentral"] * 100
    )

    desajustes = comparacion[comparacion["diferencia_pct"].abs() > tolerancia_pct]
    if len(desajustes) > 0:
        logger.warning(f"{len(desajustes)} períodos con diferencia > {tolerancia_pct}% vs. subtotal oficial")
    else:
        logger.info("Validación de integridad OK: la suma regional cuadra con el subtotal oficial.")


def limpiar_duplicados_costos(df_costos_raw: pd.DataFrame) -> pd.DataFrame:
    if df_costos_raw.empty:
        return df_costos_raw
    df_limpio = df_costos_raw.groupby(
        ["fecha", "barra_codigo", "barra_nombre", "version"], 
        dropna=False
    )["costo_marginal_usd_mwh"].mean().reset_index()
    logger.info(f"Costos marginales limpios: {len(df_limpio)} filas tras agrupar duplicados sub-horarios.")
    return df_limpio


def generar_dimension_barras(df_costos: pd.DataFrame) -> pd.DataFrame:
    logger.info("Generando tabla dimensional de barras y su mapeo regional...")
    df_barras = df_costos[["barra_codigo", "barra_nombre"]].drop_duplicates(subset=["barra_codigo"]).copy()
    df_barras["region"] = df_barras.apply(
        lambda row: mapear_region_barra(row["barra_codigo"], row["barra_nombre"]), axis=1
    )
    return df_barras
