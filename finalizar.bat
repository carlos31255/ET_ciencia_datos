@echo off
echo ===================================================
echo Apagando Sistema Electrico Nacional...
echo ===================================================
echo.
docker-compose down
echo.
echo ===================================================
echo [OK] Contenedores detenidos y red eliminada.
echo ===================================================
echo.
pause
