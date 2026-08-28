# Desafío 2 — Data-Driven Powertrain Intelligence

> Predecir eventos de degradación de la eficiencia de combustión causados por el uso del cliente, a partir de telemetría de vehículos conectados, para habilitar mantenimiento predictivo/preventivo. En la reunión mencionaron específicamente **pérdida de eficiencia en la ingesta de oxígeno del motor**.

---

## 1. Cómo leemos el problema

Es un problema de **mantenimiento predictivo sobre series temporales de telemetría**: detectar (y anticipar) cuándo un motor se está saliendo de su comportamiento eficiente, y conectarlo con *patrones de uso del conductor*. Tiene dos sub-preguntas que conviene explicitar:

1. **Detección/predicción**: ¿este vehículo va a tener (o está teniendo) un evento de degradación?
2. **Atribución**: ¿qué comportamiento del cliente lo causa? (trayectos cortos en frío, régimen de RPM, combustible, falta de service…)

La atribución es lo que lo hace valioso para Ford: no solo avisar "llevalo al taller" sino "este patrón de uso degrada el motor" → feedback al cliente y a ingeniería.

**Posicionamiento**: es el desafío más técnico/ingenieril de los tres. Si el equipo tiene alguien con base de mecánica/electrónica automotriz, acá se luce. Probablemente menos demandado que Repurchase → más chances de selección.

## 2. Contexto de dominio (estudiar antes del kick-off)

Conceptos que casi seguro aparecen en los datos y conviene manejar:

- **Sensor de O2 (lambda)**: mide oxígeno en el escape; la ECU lo usa para ajustar la mezcla aire/combustible. Su degradación (o la del sistema de admisión) se refleja en los *fuel trims*.
- **STFT / LTFT (short/long term fuel trim)**: correcciones que hace la ECU sobre la mezcla. LTFT alto sostenido = la ECU está compensando algo → proxy clásico de degradación de eficiencia.
- **MAF/MAP**: sensores de flujo/presión de aire de admisión.
- **Ciclos de manejo**: ciudad vs. ruta, trayectos cortos con motor frío (no llega a temperatura → más desgaste y consumo), régimen de RPM, agresividad de aceleración.
- **OBD-II / PIDs**: formato típico de telemetría vehicular (velocidad, RPM, temperatura de refrigerante, carga de motor, consumo instantáneo…).

No hace falta ser expertos: con estos 5 conceptos podemos hablar el idioma de los mentores (Nico y Cami) y hacer preguntas inteligentes.

## 3. Datos esperados (hipótesis hasta que los manden)

Probable: series temporales por vehículo (señales de motor muestreadas por viaje o por ventana de tiempo) + algún label o proxy de evento de degradación. Dataset curado y reducido según la reunión.

**Preguntas para los mentores en el kick-off:**
1. ¿Cómo está definido el "evento de degradación"? ¿Es un label explícito, un umbral sobre alguna señal, o lo tenemos que construir nosotros?
2. ¿Granularidad: muestras por segundo, por viaje, por día? ¿Cuántos vehículos y cuánto tiempo de historia?
3. ¿Horizonte de predicción deseado: detectar el evento cuando ocurre, o anticiparlo N días/km antes?
4. ¿Qué señales de "uso del cliente" vienen (estilo de manejo, tipo de trayecto) vs. señales de estado del motor?
5. ¿Qué acción dispararía la predicción? (notificación en la app, aviso al concesionario, recall preventivo) → define costo de falso positivo.

## 4. Enfoque técnico (pipeline)

```
EDA por vehículo → construcción/validación del label → features por ventana → baseline umbral → clasificador GBM → (opcional) anomaly detection → explicabilidad → demo "salud del motor"
```

1. **EDA orientado a series**: plotear señales clave de vehículos "sanos" vs. "degradados" a lo largo del tiempo. Buscar la firma visual del evento — si la encontramos, la mitad del pitch es ese gráfico.
2. **Definición del label** (crítico): si el label no viene dado, proponer uno defendible (ej.: deriva sostenida de LTFT por encima de umbral, caída de km/l normalizada por tipo de uso). Validarlo con los mentores ANTES de modelar.
3. **Feature engineering por ventanas** (ej. rolling de N viajes/días):
   - *Estado del motor*: media/tendencia/varianza de fuel trims, temperatura, consumo normalizado.
   - *Uso del cliente*: % de trayectos cortos, % tiempo en frío, distribución de RPM, agresividad (derivada de aceleración), km entre services.
   - *Tendencias*: pendiente de regresión de la señal de eficiencia en la ventana (la deriva importa más que el nivel).
4. **Baseline**: umbral simple sobre la mejor señal individual (ej.: "LTFT medio de la última semana > X"). Barato y nos da piso; el modelo tiene que ganarle a esto para justificarse.
5. **Modelo principal**: LightGBM sobre features de ventana → "probabilidad de evento en los próximos N días". Formulación clasificación con horizonte; simple, robusta y explicable.
6. **Complementos si el tiempo alcanza** (no antes de tener lo básico):
   - Isolation Forest / autoencoder como detector de anomalías no supervisado (útil si hay pocos eventos etiquetados).
   - Análisis de supervivencia (tiempo hasta el evento) como propuesta conceptual en el PDF.
7. **Validación**: split **por vehículo** (vehículos de test nunca vistos en train) y/o temporal. Nunca mezclar ventanas del mismo vehículo entre train y test — leakage garantizado.
8. **Explicabilidad**: SHAP para separar contribución de *uso del cliente* vs. *estado del motor* → directamente responde la consigna ("degradación debido al uso indebido del cliente").

## 5. Métricas

1. **Detección anticipada**: % de eventos detectados con al menos N días/km de anticipación (la métrica que importa para mantenimiento preventivo).
2. **Precision/recall del evento** con análisis de costo: falso positivo = visita al taller innecesaria (molesta al cliente); falso negativo = cliente percibe pérdida de eficiencia (daña la marca).
3. **Lead time promedio** de la alerta.
4. Comparación contra el baseline de umbral (justifica el ML).

## 6. Herramientas a preparar ANTES de recibir los datos

| Herramienta | Qué preparamos | Estado |
|---|---|---|
| Repo template | Igual estructura que los otros desafíos | ⬜ |
| Entorno | pandas, scikit-learn, lightgbm, shap, matplotlib, scipy; opcional: tsfresh (features automáticas de series), statsmodels | ⬜ |
| Notebook EDA series | Template para plotear N señales × M vehículos, resampleo, rolling stats, comparación sano vs. degradado | ⬜ |
| Librería de features de ventana | Funciones propias: rolling mean/std/slope, conteos por condición (ej. % tiempo bajo temperatura X) — reutilizables sea cual sea el dataset | ⬜ |
| Pipeline baseline | Umbral univariado + LightGBM con split por vehículo, métricas de anticipación | ⬜ |
| Demo Streamlit | "Ficha de salud del motor": seleccionás un vehículo → señales en el tiempo + score de riesgo + qué factores de uso contribuyen. Con datos sintéticos mientras tanto | ⬜ |
| Estudio de dominio | Doc de 2 páginas con los conceptos de §2 (lo armamos nosotros, sirve para el video y el kick-off) | ⬜ |

## 7. Estrategia y diferenciación

- **El gráfico ganador**: una línea de tiempo de un vehículo real del dataset donde se ve la señal degradándose, el punto donde nuestro modelo alerta, y el punto donde el evento ocurre. "Avisamos 3 semanas antes." Eso vale más que cualquier tabla de métricas.
- **Separar uso vs. desgaste**: mostrar con SHAP qué comportamientos del cliente anticipan la degradación → entregable doble: alerta predictiva + insight para diseño/comunicación al cliente ("tus trayectos cortos en frío están afectando el consumo").
- **Historia de experiencia de cliente**: la consigna insiste en CX. Cerrar el pitch con el flujo completo: telemetría → modelo → notificación en la app de Ford → turno de service preventivo → cliente nunca percibe la falla.
- **Honestidad técnica**: dejar claro el manejo de leakage (split por vehículo) y la diferencia entre detectar y anticipar. Los mentores son ingenieros de este dominio: la rigurosidad acá pesa más que en los otros desafíos.
- **Riesgo a evitar**: perderse en el procesamiento de señales y llegar al Trials Day sin modelo. Por eso: baseline de umbral en semana 1 sí o sí.

## 8. Estructura del PDF final

1. Resumen ejecutivo.
2. Entendimiento del problema (con el vocabulario de dominio correcto).
3. Datos y EDA: la "firma" del evento de degradación.
4. Definición del label y justificación.
5. Features: estado del motor + uso del cliente.
6. Modelo, validación (split por vehículo) y comparación contra baseline.
7. Resultados: anticipación, precision/recall, caso ilustrativo (el gráfico ganador).
8. Atribución: qué usos degradan (SHAP) → recomendaciones.
9. Flujo propuesto de producto (app / concesionario) + roadmap.

## 9. Si elegimos este desafío: ángulo del video de inscripción

- Mostrar que ya conocemos el dominio: nombrar fuel trims / sensor lambda / trayectos en frío como hipótesis de señales.
- Plantear el enfoque en dos niveles: anticipar el evento + explicar qué uso lo causa.
- Si alguno del equipo tiene perfil de ingeniería/mecánica, que eso se note.

## 10. Reparto de roles sugerido

- **Rol A (señales/datos)**: EDA de series, construcción del label, features de ventana.
- **Rol B (modelado)**: baseline, LightGBM, validación por vehículo, SHAP.
- **Rol C (dominio/comunicación)**: investigación powertrain, relación con mentores, demo, PDF y presentación.
