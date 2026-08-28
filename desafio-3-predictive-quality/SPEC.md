# Desafío 3 — Data-Driven Predictive Quality

> Con el historial de línea de producción de Planta Pacheco (tiempos de ciclo, parámetros de ajuste, interacciones — todos **dentro de especificación**), predecir qué unidades se beneficiarían de una revisión preventiva de precisión antes del Gate Release. Pasar de calidad reactiva a predictiva.

---

## 1. Cómo leemos el problema

Es **clasificación/ranking sobre datos de manufactura con clases muy desbalanceadas**, con una sutileza que es el corazón del desafío: **todas las unidades están dentro de tolerancia**. No buscamos defectos evidentes — buscamos *combinaciones* de micro-variaciones individualmente normales que, juntas, correlacionan con riesgo. Esto define todo:

- Los features individuales van a parecer inútiles en un EDA univariado. El valor está en las **interacciones** → argumento perfecto para ML (un umbral por variable, que es lo que hace el control clásico, no puede capturar esto).
- El output no es "esta unidad está fallada" sino "**estas N unidades por turno son las que más conviene revisar**" → es un problema de **priorización de inspección bajo capacidad limitada**.

**Posicionamiento**: el desafío más "de planta" — el jurado de este desafío vive este problema todos los días. Pablo y Martina (mentores) son de calidad. Si contamos bien la historia de la inspección enfocada, es muy ganable. Ideal si hay un perfil industrial en el equipo.

## 2. Contexto de dominio (estudiar antes del kick-off)

- **SPC (Statistical Process Control)**: cartas de control, Cp/Cpk (capacidad de proceso), límites de especificación vs. límites de control. Es el lenguaje de calidad en manufactura — usarlo bien genera confianza inmediata.
- **Gate Release**: punto de liberación de la unidad al final de línea; nuestro modelo actúa justo antes.
- **Calidad reactiva vs. predictiva**: hoy → controles estándar iguales para todas las unidades; propuesta → intensidad de control proporcional al riesgo predicho.
- **Trazabilidad de unidad**: cada unidad acumula registros de cada estación (torque de apriete, tiempos de ciclo, temperaturas, mediciones dimensionales…).
- **Costo asimétrico**: un escape de defecto (falso negativo) cuesta órdenes de magnitud más que una inspección extra (falso positivo) — garantía, retrabajo, imagen de marca.

## 3. Datos esperados (hipótesis hasta que los manden)

Probable: una fila por unidad (o unidad × estación) con parámetros de proceso, y un label de "unidad que requirió corrección / tuvo hallazgo en revisión". Label probablemente MUY minoritario (¿1-5%?). Dataset curado y chico según la reunión.

**Preguntas para los mentores en el kick-off:**
1. ¿Qué es exactamente el label positivo? ¿Hallazgo en inspección, retrabajo, reclamo posterior de garantía?
2. ¿Qué % de unidades son positivas? (define toda la estrategia de métricas)
3. ¿Cuántas unidades por turno/día puede absorber la revisión preventiva? → nuestro **presupuesto de inspección** (el modelo se optimiza para ese k).
4. ¿Los datos son por unidad agregada o por estación/proceso? ¿Hay orden temporal (deriva de herramientas, cambios de turno)?
5. ¿Hay variables de contexto: turno, línea, modelo de vehículo, proveedor de componente, mantenimiento reciente de la estación?

## 4. Enfoque técnico (pipeline)

```
EDA + SPC → baseline (reglas/LogReg) → LightGBM con manejo de desbalance → threshold por capacidad de inspección → SHAP → simulación de impacto → demo "cola de inspección"
```

1. **EDA con mirada SPC**: distribución de cada parámetro respecto de sus tolerancias, deriva temporal (¿los positivos se agrupan por turno/día/herramienta?), correlaciones entre estaciones. Buscar el hallazgo visual: "los hallazgos se concentran cuando el parámetro A está en el cuarto superior de la tolerancia Y el B en el inferior".
2. **Features**:
   - Posición normalizada dentro de la tolerancia: `(valor − centro_especificación) / ancho_tolerancia` por parámetro → comparable entre estaciones y habla el idioma de calidad.
   - Interacciones y agregados: cantidad de parámetros en el tercio extremo de su tolerancia, distancia de Mahalanobis al "centro" multivariado del proceso.
   - Contexto: turno, secuencia (¿primeras unidades después de un cambio?), tiempos de ciclo anómalos (ciclo muy corto = ¿paso apurado?).
3. **Baseline**: regla tipo "unidades con ≥k parámetros cerca del límite" + regresión logística. Representa "lo que haría un ingeniero de calidad sin ML" — nuestro modelo debe ganarle.
4. **Modelo principal**: LightGBM con `class_weight` / `scale_pos_weight`. Evitar SMOTE como primera opción (con datos industriales suele inventar ruido); preferir pesos + threshold tuning. Probar también Isolation Forest como feature adicional de "rareza multivariada".
5. **Decisión de threshold orientada a capacidad**: no optimizar F1 abstracto. Optimizar **recall@k**, con k = unidades/turno que la planta puede revisar. "Con capacidad de revisar el 5%, capturamos el X% de los hallazgos."
6. **Validación temporal**: entrenar en semanas pasadas, testear en semanas siguientes (los procesos derivan; validación aleatoria mentiría). Nunca CV aleatorio si hay estructura temporal.
7. **Explicabilidad**: SHAP global (qué combinaciones de parámetros generan riesgo → insight de proceso para ingeniería) + local (por qué se flaguea ESTA unidad → el inspector sabe qué mirar).
8. **Simulación de impacto**: comparar tres políticas sobre el test set: (a) inspección aleatoria del 5%, (b) regla del ingeniero, (c) nuestro modelo. Tabla de hallazgos capturados por cada una → ESE es el resultado central del PDF.

## 5. Métricas

1. **Recall@k / captura con presupuesto de inspección** (la métrica del negocio): "revisando el 5% priorizado por el modelo se captura el X% de los hallazgos vs. Y% revisando al azar" → lift.
2. **PR-AUC** (con desbalance fuerte, ROC-AUC engaña — mencionarlo explícitamente suma rigurosidad).
3. **Curva de captura vs. % inspeccionado**: le permite al jurado elegir su punto de operación — convierte el modelo en una herramienta de decisión gerencial.
4. Estimación de costo evitado (supuestos declarados: costo de escape vs. costo de inspección).

## 6. Herramientas a preparar ANTES de recibir los datos

| Herramienta | Qué preparamos | Estado |
|---|---|---|
| Repo template | Igual estructura que los otros desafíos | ⬜ |
| Entorno | pandas, scikit-learn, lightgbm, shap, matplotlib, imbalanced-learn (por si acaso), scipy | ⬜ |
| Notebook EDA industrial | Template: distribución vs. tolerancias, cartas de control simples, deriva temporal, análisis del desbalance | ⬜ |
| Utilidades SPC | Funciones: normalización por tolerancia, Cp/Cpk, distancia de Mahalanobis, conteo de parámetros en zona extrema | ⬜ |
| Pipeline baseline | Regla simple + LogReg + LightGBM con pesos, validación temporal, recall@k parametrizable | ⬜ |
| Simulador de políticas | Script que compara aleatoria vs. regla vs. modelo sobre un test set → tabla y gráfico listos | ⬜ |
| Demo Streamlit | "Cola de inspección del turno": lista de unidades priorizadas con score + top-3 razones (SHAP) por unidad. Con datos sintéticos mientras tanto | ⬜ |
| Estudio de dominio | Doc de 2 páginas de SPC/Cpk/calidad predictiva para hablar el idioma de Pablo y Martina | ⬜ |

## 7. Estrategia y diferenciación

- **La historia**: "hoy la inspección extra es uniforme o aleatoria; nosotros le decimos a la planta exactamente dónde mirar". El deliverable mental para el jurado es la **cola de inspección priorizada del turno**, no el modelo.
- **El argumento conceptual que nos diferencia**: los controles univariados (un límite por parámetro) no pueden ver combinaciones; el ML sí. Ilustrarlo con un gráfico 2D de dos parámetros donde los hallazgos viven en una esquina que ningún límite individual captura. Es LA diapositiva del pitch.
- **Hablar en SPC**: usar Cp/Cpk, "dentro de especificación", "deriva de proceso" correctamente. Con un jurado de manufactura, el idioma genera credibilidad instantánea.
- **Resultado como decisión, no como score**: la curva captura-vs-capacidad le da al gerente una perilla ("si me das 3% de capacidad capturo X, con 8% capturo Y"). Eso es pensar como ellos.
- **Honestidad técnica**: validación temporal, PR-AUC en vez de ROC, y advertencia sobre el reentrenamiento (los procesos cambian → monitoreo de drift en el roadmap).
- **Riesgo a evitar**: (a) que el EDA univariado "no muestre nada" y nos desmoralice — es esperable por diseño del problema, el valor está en lo multivariado; (b) reportar accuracy (con 97% de negativos, accuracy 97% = modelo inútil).

## 8. Estructura del PDF final

1. Resumen ejecutivo: de calidad reactiva a predictiva, con el número de captura@k.
2. Entendimiento del problema y del proceso productivo.
3. Datos y EDA: la evidencia de patrones multivariados.
4. Features (normalización por tolerancia) y metodología.
5. Manejo del desbalance y validación temporal.
6. Resultados: curva captura vs. capacidad + simulación de las 3 políticas.
7. Qué combinaciones de parámetros generan riesgo (SHAP) → insight para ingeniería de proceso.
8. Demo: cola de inspección priorizada.
9. Costo evitado estimado + roadmap (integración con sistemas de planta, monitoreo de drift, reentrenamiento).

## 9. Si elegimos este desafío: ángulo del video de inscripción

- Mostrar que entendimos la sutileza: "todas las unidades están dentro de norma; el riesgo está en las combinaciones" — casi ningún equipo lo va a formular así.
- Plantear el output como priorización con capacidad limitada de inspección.
- Si hay un perfil de ingeniería industrial en el equipo, destacarlo: este desafío es su cancha.

## 10. Reparto de roles sugerido

- **Rol A (proceso/datos)**: EDA con mirada SPC, features de tolerancia, análisis de deriva.
- **Rol B (modelado)**: desbalance, LightGBM, validación temporal, recall@k, SHAP.
- **Rol C (negocio/comunicación)**: simulación de políticas, costo evitado, demo, PDF y presentación.
