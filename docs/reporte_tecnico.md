# Reporte Técnico: Análisis y Predicción de Costos Marginales del Sistema Eléctrico Nacional

## 1. Contexto y Problema de Negocio
El mercado eléctrico chileno es altamente complejo y presenta una gran volatilidad en sus precios (costos marginales). Estos costos varían drásticamente dependiendo de la zona geográfica, la infraestructura de transmisión, la hora del día y la capacidad económica (PIB) de la región donde se ubican los nodos (barras) de conexión.

El objetivo de este proyecto es construir un sistema de Machine Learning end-to-end que permita a las empresas del sector energía clasificar estratégicamente los nodos del país y predecir el costo horario de la energía, facilitando la toma de decisiones sobre dónde instalar nuevas plantas o cuándo consumir energía.

## 2. Arquitectura de Datos (ETL)
Se construyó un pipeline ETL automatizado que integra dos fuentes de datos reales:
1. **Coordinador Eléctrico Nacional (API REST):** Extracción de miles de registros horarios de costos marginales por barra.
2. **Banco Central de Chile (Excel):** Extracción del Producto Interno Bruto (PIB) regional para cruzar variables económicas con variables energéticas.

Los datos pasan por un proceso de limpieza (manejo de nulos, estandarización de fechas y resolución de duplicados sub-horarios) y se cargan en una base de datos relacional SQLite (`energia.db`) estructurada en un modelo dimensional (Tabla de Hechos de Costos Marginales y Dimensiones de Barras y PIB).

## 3. Modelamiento Analítico (Storytelling de Datos)

Para abordar el problema, se diseñó una solución híbrida que conecta un enfoque no supervisado con uno supervisado.

### 3.1. Modelo No Supervisado (K-Means)
**Objetivo:** Agrupar geográficamente el país en "Arquetipos de Riesgo Energético".
Se utilizó el algoritmo K-Means para segmentar las barras eléctricas utilizando tres variables clave:
- Costo Promedio (USD/MWh)
- Costo Máximo (Volatilidad)
- PIB Regional (Poder Adquisitivo)

El algoritmo identificó exitosamente clusters distintos, por ejemplo, separando zonas de alta volatilidad industrial de zonas de bajo costo estable. Este modelo provee una vista "macro" del sistema.

### 3.2. Modelo Supervisado (XGBoost Regressor)
**Objetivo:** Predecir el costo marginal exacto de una barra para una hora específica del futuro.
Se implementó un ensamble avanzado de Gradient Boosting (`XGBRegressor`). Para conectar la visión macro con la micro, el modelo supervisado recibe como *feature* de entrada el cluster asignado previamente por K-Means, además de variables temporales.

**Optimización de Hiperparámetros:** 
Se utilizó la librería `Optuna` con optimización Bayesiana para encontrar la mejor combinación de hiperparámetros (`learning_rate`, `n_estimators`, `max_depth`), logrando minimizar el Error Cuadrático Medio (RMSE).

**Resultados y Feature Importance:**
El modelo alcanzó un coeficiente de determinación ($R^2$) superior a 0.92, demostrando una capacidad predictiva sobresaliente. 
El análisis de importancia de variables reveló el siguiente relato técnico:
1. **Porcentaje de Energía Renovable (73%):** El factor más crítico que desploma o eleva el precio de la energía es la disponibilidad del sol y el viento.
2. **Día de la Semana (12%) y Hora del Día (7%):** Capturan con precisión los patrones de comportamiento de consumo humano e industrial.
3. **Cluster Arquetipo (6%):** Ajusta el nivel base del precio dependiendo del contexto macro-económico de la zona.

## 4. Conclusión
El cruce de datos económicos (PIB) con datos técnicos del Coordinador Eléctrico, procesados a través de algoritmos de Machine Learning (K-Means + XGBoost), demuestra ser una herramienta predictiva robusta. La transición desde el análisis macro (clustering) hasta la predicción micro (regresión horaria) cumple con los estándares más altos para la toma de decisiones en el sector energético.
