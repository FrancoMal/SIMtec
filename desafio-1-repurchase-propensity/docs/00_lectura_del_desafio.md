# 00 — Lectura del desafío: qué pide Ford, cómo se evalúa y qué hay que entregar

> Fuentes leídas completas el 2026-09-15: `Reglamento FIC 3_v3.pdf`, `Resumen Desafios FIC_3 - AI Edition.pdf`,
> `SPEC.md`, `ENTREGABLES.md`, `notas-tutor-2026-09-11.md`, `Status.md`, `ESTRUCTURA.md` y la
> **ficha técnica oficial del desafío** (`Ficha_Técnica_FIC3_Data_Strategy_2026_08.docx`, en la carpeta
> compartida de datos, fechada 11/9/2026, mentor y SPOC: Facundo Bertolosso; referente de Data Science:
> L. Rosa). Este documento consolida todo eso en un solo lugar y marca dónde la ficha corrige al SPEC.

## 1. La ficha técnica redefine el desafío (esto es lo más importante)

El resumen público de desafíos habla de "Repurchase Propensity": *identificar a quienes están a punto de
elegir, una vez más, un Ford*. La ficha técnica que vino con el dataset lo aterriza en algo mucho más
concreto y distinto:

> **Título oficial:** "Data-Driven Repurchase based on Service Retention: Predicción de retorno a la red
> oficial en ventana de servicio". Área: Customer Experience & Data Strategy — Posventa / Retención de
> Servicio.

| Punto | Lo que dice la ficha técnica (fuente de verdad) |
|---|---|
| **Problema** | Anticipar cuáles usuarios cuyos vehículos entran en la **ventana de mantenimiento** tienen mayor probabilidad de **no volver a la red oficial** (churn de service). Hoy la priorización es uniforme por reglas de tiempo/km/vencimiento; el churn se reconoce tarde. |
| **Target** | `churn = 1` si **no se observa un mantenimiento programado completado en la red oficial** dentro del horizonte posterior al scoring; `churn = 0` si se observa. Se excluyen como retorno los eventos que no son mantenimiento programado. Ventanas con horizonte no terminado = **casos censurados** (no se usan como churn confirmado). |
| **Unidad** | **usuario – vehículo (VIN) – ventana**. Si un usuario tiene varios VIN, vista consolidada sin perder el riesgo por vehículo. |
| **Momento de scoring** | Apertura de la ventana (opcionalmente actualizaciones durante la ventana). Ninguna variable posterior a la fecha de scoring puede ser feature. |
| **Output mínimo** | `customer_id`, `vehicle_id`, fecha de scoring, probabilidad 0-1, segmento de riesgo, principales drivers. Explicable, reproducible y utilizable antes del cierre de la ventana. |
| **Población** | Usuarios con ≥1 Ranger dentro de una ventana de mantenimiento en Argentina. Datos: ventas y turnos de Agenda Ford 2024-2026. |
| **Features sugeridas** | Recencia y frecuencia de servicios/turnos, cancelaciones, no-show, kilometraje, antigüedad, garantía, canal de agenda, tipo de servicio, historial de relación, señales conectadas. |
| **Validación** | Temporal (train/valid/test separados por fecha, simulando uso real). |
| **Criterios de evaluación (9)** | (1) formulación de población, ventana y target; (2) ausencia de leakage y calidad de la validación temporal; (3) poder predictivo: ROC-AUC y **especialmente PR-AUC**, recall/precision sobre churn, **lift por deciles** y **recall dentro de una capacidad de contacto definida**; (4) **calibración**; (5) explicabilidad de drivers; (6) accionabilidad e integración al proceso; (7) viabilidad técnica y reproducibilidad; (8) carácter innovador; (9) claridad del power pitch. |
| **Entregables mínimos** | Dataset analítico documentado; definición reproducible del target; pipeline de features; modelo entrenado; evaluación temporal; explicación global e individual; ranking priorizado; propuesta de activación; power pitch con beneficios, riesgos y próximos pasos. |
| **Canales de consumo** | Service Leads, Service Reminder, Vehicle Tweet, Customer Tweet. |
| **Impacto esperado** | Retención (anticipar pérdidas antes de que se vean en *VIN Share*), eficiencia (priorizar capacidad finita de contacto), conversión (más turnos y mantenimientos), CLTV, gestión (medir por decil de riesgo, acción, dealer y período). |
| **Pendiente de Ford** | "Las reglas exactas de ventana y horizonte deberán validarse por modelo/año antes del entrenamiento final" y "Reglas de ventana de servicio y diccionario definitivo: a validar con los referentes de negocio". **No vinieron con el paquete.** Las definimos nosotros, empíricamente, y las dejamos parametrizadas. |

### Contradicciones / correcciones respecto del SPEC y de las notas del tutor

1. **El target NO es "recompra de un vehículo"**. El SPEC lo planteaba como propensity de recompra a 6-24
   meses con "reframing" sugerido por el tutor. La ficha lo cierra: el target es **no completar el próximo
   mantenimiento programado en la red oficial dentro del horizonte**. La recompra es el *porqué* del negocio
   (service → satisfacción → lealtad → recompra), no lo que se modela. En el dataset no hay ninguna variable
   de recompra: sales tiene una fila por vehículo vendido 2024-2026 y no hay forma de saber si un cliente
   "recompró" salvo que aparezca dos veces como comprador (3.534 clientes con >1 vehículo, mayormente flotas).
   Camino descartado: modelar recompra directamente. Motivo: no hay label, y no es lo que pide la ficha.
2. **Horizonte "el próximo mes"** (tutor) vs "horizonte definido por negocio" (ficha, sin número). Se fija
   empíricamente a partir de la distribución real de retornos (ver `01_hallazgos_eda.md`) y queda como
   parámetro. Lo que sí se respeta del tutor: **scoring de corto plazo y frecuencia mensual de re-scoring**.
3. **"3 tipos de cliente"** (tutor): la ficha pide "segmento de riesgo". Se implementan tres niveles de
   riesgo accionables (alto / medio / bajo) atados a la acción y a la capacidad de contacto.
4. **Regla "15.000 km o 1 año"** (tutor): la ficha la deja "a validar por modelo/año". El plan de
   mantenimiento en la agenda está indexado por mes (`ServiceMonth = 12 × n`). Se valida empíricamente con
   los intervalos reales entre services (tema 02 del EDA) antes de fijar K km y el ciclo en días.
5. **Datos "chicos, pocas variables"** (SPEC §2): falso. Son 631.623 filas de agenda (49 columnas útiles) y
   59.384 ventas. Y son **transaccionales**, no una foto por cliente: el dataset analítico hay que construirlo.
6. **"Clics/navegación web"** (SPEC §2): no hay. Lo más parecido es `ScheduleSource` (FordPass / WEB / Dealer).
7. **Evaluación por backtesting con lift** (tutor): coincide con la ficha (validación temporal, lift por
   deciles, recall a capacidad de contacto). Es el diseño de evaluación que se implementa.

## 2. Reglamento: lo formal

- Entregable único: **un PDF con la explicación detallada de la idea** (§5.1.1), por mail a
  `umonten1@ford.com` y `avedia@ford.com` **antes del 25/09/2026 23:59** (§5.2).
- Jurado por desafío: directores, gerentes y supervisores de Ford (§5.3). Un 1º y un 2º premio por desafío.
- Criterio del reglamento (§8.1): originalidad, creatividad y uso de las herramientas enseñadas. Se suma a
  los 9 criterios técnicos de la ficha.
- Trials Day 02/10/2026 en Pacheco (presentación de avances); Awards semana del 05/10.
- Cesión total de derechos a Ford (§5.6); el equipo declara originalidad. Los datos no pueden replicarse ni
  difundirse fuera del entorno autorizado (ficha, "Seguridad y privacidad") → **los CSV y cualquier derivado
  con IDs quedan fuera de git** (`.gitignore` ya cubre `data/`, `*.csv`, `*.parquet`).

## 3. Qué significa esto para el trabajo

El "producto" que se defiende ante el jurado es:

1. **Una definición defendible y reproducible de población–ventana–target** (criterio 1), construida y
   validada con los datos, con los supuestos explícitos y parametrizados.
2. **Un modelo calibrado y explicable** (criterios 3-5) evaluado **fuera de tiempo** (criterio 2), comparado
   contra la priorización actual (uniforme / por reglas) para mostrar el lift incremental.
3. **Un ranking priorizado accionable** (criterio 6): a quién contactar primero, por qué canal, con qué
   mensaje, dentro de una capacidad de contacto dada, y cómo medir el impacto (A/B por decil).
4. **Impacto en plata y en operación**: valor de un mantenimiento retenido vs costo de contacto, costo de
   equivocarse en cada dirección, dimensionamiento mensual de la población en ventana.
5. **Pitch claro** (criterio 9) + PDF + dashboard + notebook (entregables del tutor).

Lo que queda abierto con el mentor está listado y priorizado al final de `01_hallazgos_eda.md`.
