# Reporte Técnico: Análisis y Predicción de Costos Marginales del Sistema Eléctrico Nacional

## 1. Contexto y Problema de Negocio
El mercado eléctrico chileno es altamente complejo y presenta una gran volatilidad en sus precios (costos marginales). Estos costos varían drásticamente dependiendo de la zona geográfica, la infraestructura de transmisión, la hora del día y la capacidad económica (PIB) de la región donde se ubican los nodos (barras) de conexión.

El objetivo de este proyecto es construir un sistema de Machine Learning end-to-end que permita a las empresas del sector energía clasificar estratégicamente los nodos del país y predecir el costo horario de la energía, facilitando la toma de decisiones sobre dónde instalar nuevas plantas o cuándo consumir energía.

### 1.1. Estándar de Divisa: ¿Por qué USD y no CLP?
En este proyecto, notarás que el **Costo Marginal de la energía** se mide en **Dólares por Megavatio-hora (USD/MWh)**, mientras que el PIB regional se mantiene en Pesos Chilenos (CLP). Esta discrepancia es intencional y refleja la realidad del mercado:
- **Dolarización de Insumos:** Gran parte de la energía en Chile se genera con combustibles importados (GNL, carbón, diésel) que se transan internacionalmente en dólares.
- **Riesgo Cambiario y Financiamiento:** Los grandes proyectos de generación (solares, eólicos) se financian mediante deuda internacional. Para que estos proyectos sean viables y no quiebren ante la volatilidad del tipo de cambio, el mercado mayorista eléctrico opera oficialmente en dólares.

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

*Nota Académica sobre Fuga de Datos (Data Leakage):* 
Inicialmente, una variable simulada de % renovable dominaba el modelo (78% de importancia) por una fuga de datos, ya que era una función directa de la hora. Al identificar y retirar esa variable, el modelo redistribuyó su aprendizaje hacia las variables temporales genuinas — hora del día (82%) y día de la semana (17%) — confirmando que el costo marginal en Chile está fuertemente determinado por el ciclo diario de generación solar, consistente con la matriz energética nacional.

El análisis actual de importancia de variables revela el siguiente relato técnico:
1. **Hora del Día:** Es la variable temporal más crítica ya que captura a la perfección la "Curva de Pato" (Duck Curve) del sistema chileno. Al mediodía, el costo marginal tiende a desplomarse debido a la inyección masiva y a costo cero de las plantas solares, mientras que en la madrugada (sin sol), el precio se eleva al requerir generación térmica (carbón/GNL).
2. **Día de la Semana:** Modula el patrón base, capturando el "efecto fin de semana" donde la disminución del consumo industrial reduce los costos estructurales del sistema.
3. **Cluster Arquetipo:** Ajusta la línea base del precio al contextualizar geográficamente la subestación (Ej. zonas industriales en el norte minero vs. zonas residenciales).

## 4. Conclusión
El cruce de datos económicos (PIB) con datos técnicos del Coordinador Eléctrico, procesados a través de algoritmos de Machine Learning (K-Means + XGBoost), demuestra ser una herramienta predictiva robusta. La transición desde el análisis macro (clustering) hasta la predicción micro (regresión horaria) cumple con los estándares más altos para la toma de decisiones en el sector energético.
