@echo off
echo ===================================================
echo Iniciando Sistema Electrico Nacional (API + Dashboard)
echo ===================================================
echo.
echo Levantando contenedores Docker en segundo plano...
docker-compose up --build -d
echo.
echo ===================================================
echo [OK] Servicios iniciados exitosamente.
echo.
echo - API (Swagger UI): http://localhost:8000/docs
echo - Dashboard (App) : http://localhost:8501
echo ===================================================
echo.
pause
