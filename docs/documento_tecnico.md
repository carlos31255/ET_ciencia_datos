# Documento Técnico: Pipeline y Pruebas de API

## 1. Contexto de las Pruebas
Durante la fase inicial de desarrollo, se realizaron pruebas en el script `tests/test_api.py` para extraer datos de hospitales e infraestructura de salud en Santiago utilizando la **API de Overpass (OpenStreetMap)**. 

El objetivo de estas pruebas fue validar la disponibilidad, los tiempos de respuesta y la exactitud de los resultados retornados por la API antes de integrarlos formalmente en el pipeline de ETL.

---

## 2. Problemas Encontrados y Soluciones Aplicadas

A lo largo de las pruebas de extracción de datos espaciales, se identificaron varios desafíos técnicos que fueron resueltos para estabilizar las consultas. A continuación, el resumen de los hallazgos:

### 2.1. Error 406 (Not Acceptable)
- **Problema:** La solicitud inicial a la API devolvía un código de estado `406`.
- **Causa:** El servidor de Overpass rechaza las peticiones de clientes que no cuentan con un `User-Agent` identificable (comportamiento por defecto de la librería `requests` de Python).
- **Solución:** Se agregó un header explícito en la petición con el nombre del proyecto y un correo de contacto:
  ```python
  headers = {"User-Agent": "EFT-SCY1101-ProyectoUniversitario/1.0 (contacto: tu_correo@duoc.cl)"}
  ```

### 2.2. Falta de Resultados (Solo 1 resultado retornado)
- **Problema:** Al consultar por infraestructura de salud en Santiago, la API devolvía un único registro.
- **Causa:** El uso del polígono administrativo de "Santiago" estaba mal delimitado en OSM para los fines del proyecto. Además, el uso exclusivo de la etiqueta `amenity=hospital` era muy restrictivo y dejaba fuera centros de salud relevantes.
- **Solución:** 
  1. Se reemplazó la búsqueda por polígono por una búsqueda radial (`around:radio,lat,lon`) usando como centro aproximado la Plaza de Armas de Santiago y un radio de 15 km.
  2. Se combinaron múltiples etiquetas (`amenity=hospital`, `healthcare=hospital`) incluyendo nodos y vías, logrando subir la tasa de captura significativamente (ej. 64 elementos).

### 2.3. Tiempos de Respuesta Elevados
- **Problema:** El tiempo de respuesta de las consultas variaba entre 3 y 9 segundos por ejecución.
- **Conclusión y Solución (Mejora Continua):** Aunque este tiempo de respuesta es aceptable para un proceso ETL en lote, **no es viable para consultas en tiempo real**. La estrategia a seguir será **cachear o persistir** estos resultados (por ejemplo, en un archivo `.csv` o base de datos local) durante el pipeline ETL, asegurando que el dashboard final consuma los datos pre-procesados en lugar de consultar la API en vivo por cada interacción.

---

## 3. Estado Actual de `test_api.py`

Las modificaciones anteriores dieron como resultado una consulta funcional que sirve de base para el proceso de extracción final. Actualmente, la prueba ejecuta correctamente con un código 200 y es capaz de parsear los elementos en formato JSON.

*(Nota: Hasta este punto se ha documentado la prueba de concepto para la API. Este documento se irá ampliando a medida que se integren los modelos y los procesos finales).*
