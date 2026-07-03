# ET_ciencia_datos
Proyecto de Ciencia de Datos.

## Configuración del Entorno Virtual

Para aislar las dependencias del proyecto, utilizamos un entorno virtual (`venv`). Sigue estos pasos para activarlo e instalar las dependencias necesarias:

### En Windows (PowerShell/CMD):
```bash
# 1. Crear el entorno virtual (solo la primera vez)
python -m venv venv

# 2. Activar el entorno
.\venv\Scripts\activate

# 3. Instalar las dependencias
pip install -r requirements.txt
```

### En macOS / Linux:
```bash
# 1. Crear el entorno virtual (solo la primera vez)
python3 -m venv venv

# 2. Activar el entorno
source venv/bin/activate

# 3. Instalar las dependencias
pip install -r requirements.txt
```

Una vez activo, tu consola debería mostrar `(venv)` al inicio de la línea.
