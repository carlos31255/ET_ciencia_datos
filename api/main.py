from fastapi import FastAPI

app = FastAPI(
    title="API Riesgo Energético Regional",
    description="Microservicio interno para predecir el estrés energético por región",
    version="1.0.0"
)

@app.get("/")
def read_root():
    return {"message": "API de Riesgo Energético conectada. El modelo K-Means se cargará aquí próximamente."}
