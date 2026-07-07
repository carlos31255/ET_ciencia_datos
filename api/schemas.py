from pydantic import BaseModel, Field
from typing import Dict

class SiniestroInput(BaseModel):
    mes: int = Field(..., ge=1, le=12, description="Mes del año (1-12)")
    diasemana: int = Field(..., ge=1, le=7, description="Día de la semana (1-7)")
    hora_aprox: int = Field(..., ge=0, le=23, description="Hora del siniestro (0-23)")
    es_fin_de_semana: int = Field(..., ge=0, le=1, description="0 (No) o 1 (Sí)")
    region_dpa: str
    comuna_dpa: str
    lat: float = Field(..., ge=-56.0, le=-17.0, description="Latitud (Chile)")
    lon: float = Field(..., ge=-76.0, le=-66.0, description="Longitud (Chile)")
    distancia_hospital_km: float = Field(..., gt=0, description="Distancia al hospital en km (>0)")
    siniestros_por_region: int
    dist_media_region_km: float
    pct_severo_region: float

class SiniestroOutput(BaseModel):
    gravedad: str
    probabilidades: Dict[str, float]