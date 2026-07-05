from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)

payload_valido = {
    "mes": 3,
    "diasemana": 5,
    "hora_aprox": 22,
    "es_fin_de_semana": 0,
    "region_dpa": "13",
    "comuna_dpa": "13101",
    "lat": -33.45,
    "lon": -70.67,
    "distancia_hospital_km": 4.2,
    "siniestros_por_region": 1823,
    "dist_media_region_km": 8.5,
    "pct_fatal_region": 4.8
}

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "modelo_cargado" in data

def test_predict_valido():
    response = client.post("/predict", json=payload_valido)
    
    # Si el modelo no está creado aún, esperamos un 503. Si está, un 200.
    if response.status_code == 200:
        data = response.json()
        assert "gravedad" in data
        assert "probabilidades" in data
    else:
        assert response.status_code == 503

def test_predict_invalido_fuera_de_chile():
    payload_invalido = payload_valido.copy()
    payload_invalido["lat"] = 0.0 # Falla validación: no está en Chile
    
    response = client.post("/predict", json=payload_invalido)
    # FastAPI devuelve 422 Unprocessable Entity cuando falla Pydantic
    assert response.status_code == 422 
    
    errores = response.json()["detail"]
    assert errores[0]["loc"] == ["body", "lat"]
    # python -m pytest tests/