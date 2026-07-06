from fastapi import FastAPI, HTTPException, status
from api.schemas import SiniestroInput, SiniestroOutput
import api.predictor as predictor
from fastapi.responses import RedirectResponse


# Para ejecutarlo:
# uvicorn api.main:app --reload --port 8000
# http://127.0.0.1:8000/docs

app = FastAPI(
    title="API Predictor de Gravedad de Siniestros",
    description="API REST para predecir la gravedad de siniestros viales.",
    version="1.0.0"
)


@app.get("/", include_in_schema=False)
def read_root():
    return RedirectResponse(url="/docs")

@app.get("/health", summary="Verifica el estado de la API")
def health_check():
    cargado = predictor.modelo is not None
    if not cargado:
        # Reintentar cargar por si el modelo se añadió después de iniciar
        cargado = predictor.cargar_modelo()
        
    return {
        "status": "ok",
        "modelo_cargado": cargado
    }

@app.post("/predict", response_model=SiniestroOutput, summary="Predice la gravedad del siniestro")
def predict(siniestro: SiniestroInput):
    # Validar si el modelo está disponible
    if predictor.modelo is None and not predictor.cargar_modelo():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service Unavailable: El modelo de predicción no está cargado."
        )

    try:
        # Pydantic v2 usa model_dump() en lugar de dict()
        datos = siniestro.model_dump()
        resultado = predictor.hacer_prediccion(datos)
        return resultado
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno al realizar la predicción: {str(e)}"
        )