# Desafío 1 — Data-Driven Repurchase Propensity

> Predecir qué clientes están próximos a recomprar un Ford, usando su historial (cambios de auto, servicios, interacciones web, etc.), para habilitar marketing y descuentos personalizados.

---

## 1. Cómo leemos el problema

Es un problema clásico de **propensity scoring / churn invertido**: en vez de predecir quién se va, predecimos quién está listo para volver a comprar. Es el desafío más "estándar" de data science de los tres — eso significa:

- **Ventaja**: hay metodología probada, es difícil trabarse técnicamente.
- **Riesgo**: todos los equipos van a hacer más o menos lo mismo (un gradient boosting sobre datos tabulares). **La diferenciación va a estar en el framing de negocio y la comunicación, no en el modelo.**

El output que le sirve a Ford no es "el modelo predice bien": es **una lista priorizada de clientes con score de propensión + las señales que lo explican + qué acción tomar con cada segmento**.

## 2. Datos esperados (hipótesis hasta que los manden)

Según la reunión: cada cuánto cambia el auto, historial de servicios, clics/navegación en la web, y "un montón de otros datos". Dataset curado, chico, pocas variables.

Estructura probable: una fila por cliente con features agregadas + label (recompró / no recompró en ventana X), o tabla transaccional que habrá que agregar nosotros.

> **Actualización (reunión con el tutor, 11/9)** — ver detalle completo en
> [`notas-tutor-2026-09-11.md`](./notas-tutor-2026-09-11.md). Resumen de lo que ya quedó definido:
> - Todos los datos vienen **enmascarados** (anonimizados).
> - Variables clave confirmadas: **fecha del último service** y **kilometraje** (con eso se infiere
>   el patrón de uso y cuándo le toca el próximo service). Hay un campo tipo **`schedule_id`** que
>   identifica el service agendado, y el dataset detalla **varios motivos de entrada al service**.
> - Ciclo de service típico: **cada 15.000 km o 1 año** (lo que ocurra primero).
> - Caso especial a contemplar: **transferencia de titularidad** — si el dueño original transfiere
>   el auto y el nuevo dueño acepta compartir sus datos, vuelve a entrar como cliente activo.
> - Hay que poder distinguir si el cliente que va al service es el mismo que compró el auto.

**Preguntas para los mentores en el kick-off (lo que todavía falta cerrar):**
1. ¿Cómo está definido el target exactamente? ¿Recompra en qué ventana de tiempo (6/12/24 meses)? — *ver también el reframing de target en §3.1, sugerido por el tutor.*
2. ¿El dataset es una foto (snapshot) o tiene dimensión temporal? ¿Hay riesgo de leakage (features calculadas después del evento)?
3. ¿Qué acción tomaría Ford con el score? (campaña de mail, descuento, llamado del concesionario) → define la métrica: no es lo mismo optimizar para top-1000 clientes que para todo el universo.
4. ¿Qué tasa base de recompra hay? (para calibrar expectativas de lift)
5. ¿Hay datos de campañas pasadas? (habilitaría hablar de uplift modeling, aunque sea como propuesta futura)
6. ¿Cuáles son exactamente los 3 tipos/segmentos de cliente que el tutor tiene en mente? (mencionados en la reunión pero sin definir criterio exacto todavía).

## 3. Enfoque técnico (pipeline)

### 3.1 Reframing del target (según el tutor)

El tutor marcó que lo que más le importa no es directamente "¿el cliente va a recomprar?", sino
un proxy más accionable y de corto plazo: **la probabilidad de que el cliente NO vaya al service
cuando le corresponde**, prediciendo a horizonte de **el próximo mes**. La lógica causal que
plantea es:

```
patrón de uso (km + fecha último service) → ventana esperada de próximo service
→ si el cliente NO va en esa ventana (ni antes ni después) → pierde satisfacción
→ se aleja de la marca → no recompra
```

Esto sugiere que el target real a modelar podría ser binario por cliente-mes: *"¿va a faltar a su
service programado del próximo mes?"*, y no solo un score de recompra a 6-24 meses. Ambos enfoques
no son excluyentes — el segundo (no-asistencia a service) puede ser un modelo intermedio que
alimenta al de propensión de recompra, o directamente el approach principal si el mentor lo
confirma en el kick-off. **Confirmar cuál de los dos targets quiere Ford como entregable
principal.**

```
EDA → features RFM → baseline (LogReg) → LightGBM/XGBoost → calibración → explicabilidad (SHAP) → segmentación accionable → demo
```

1. **EDA**: distribución del target, missing values, correlaciones, análisis por cohortes (antigüedad del cliente, modelo de auto, canal).
2. **Feature engineering — marco RFM adaptado a automotriz**:
   - *Recency*: tiempo desde última compra, último servicio, última visita web.
   - *Frequency*: cantidad de servicios en N años, regularidad del mantenimiento, visitas web/mes.
   - *Monetary/valor*: gama del vehículo actual, gasto en servicios.
   - *Ciclo de vida*: edad del vehículo actual vs. ciclo típico de recambio del segmento (probablemente LA feature más predictiva: un cliente con un auto de 4-5 años está "en ventana").
   - *Patrón de service* (confirmado por el tutor como variable clave): a partir de **fecha del último service + kilometraje**, calcular cuándo le corresponde el próximo service (ciclo típico: cada 15.000 km o 1 año, lo que ocurra primero) y si el cliente lo cumplió a tiempo, tarde, o directamente faltó.
   - *Engagement digital*: clics en configurador/página de modelos = señal de intención fuerte.
3. **Baseline primero**: regresión logística con 5-10 features. Nos da piso de métrica y features interpretables desde el día 2.
4. **Modelo principal**: LightGBM (maneja missing, categóricas, rápido de iterar). No perder tiempo con deep learning: con datos tabulares chicos, gradient boosting gana.
5. **Validación**: split temporal si hay fechas (entrenar en pasado, validar en futuro); si no, CV estratificado. Vigilar leakage obsesivamente — es el error clásico de este tipo de desafío. El tutor confirmó que la evaluación del proyecto se hace por **backtesting**: se mide el lift del modelo contra lo que efectivamente pasó, así que este split temporal no es opcional — es el método de evaluación esperado.
6. **Calibración** (Platt/isotonic): si vamos a decir "probabilidad de recompra 72%", que sea una probabilidad real. Detalle que casi ningún equipo hace y queda muy profesional.
7. **Explicabilidad**: SHAP global (qué señales importan) + SHAP local (por qué ESTE cliente tiene score alto) → esto alimenta la historia de negocio.
8. **Segmentación accionable**: cortar el score en 3-4 segmentos con acción sugerida:
   - Score alto + auto viejo → contacto comercial directo.
   - Score alto + engagement web reciente → retargeting con el modelo que estuvo mirando.
   - Score medio → nurturing por mail.
   - Score bajo → no gastar presupuesto.

## 4. Métricas (en este orden de importancia para el pitch)

1. **Lift / captura por decil**: "contactando al 10% top de clientes, capturás el X% de las recompras" → gráfico de ganancia acumulada. ESTE es el gráfico que el jurado tiene que recordar.
2. **PR-AUC / precision@k**: k = tamaño realista de una campaña.
3. ROC-AUC como métrica general de referencia.
4. **Traducción a plata** (aunque sea con supuestos): margen promedio por venta × recompras capturadas − costo de campaña = ROI estimado. Declarar los supuestos explícitamente.

## 5. Herramientas a preparar ANTES de recibir los datos

| Herramienta | Qué preparamos | Estado |
|---|---|---|
| Repo template | Estructura `data/ notebooks/ src/ reports/`, `requirements.txt`, `.gitignore` | ⬜ |
| Entorno | Python 3.11+, pandas, scikit-learn, lightgbm, xgboost, shap, matplotlib/seaborn, jupyter | ⬜ |
| Notebook EDA genérico | Perfilado automático: tipos, nulos, distribuciones, target rate, correlaciones (ydata-profiling o propio) | ⬜ |
| Pipeline baseline | Script `train.py` parametrizable: carga CSV → preprocesa → LogReg + LightGBM → métricas + curvas → listo para enchufar el dataset el día 1 | ⬜ |
| Notebook SHAP | Template de summary plot + dependence plots + waterfall de casos individuales | ⬜ |
| Demo Streamlit | App esqueleto: subís score de clientes → tabla priorizada + filtros por segmento + ficha de cliente con explicación. Con datos fake mientras tanto | ⬜ |
| Template del PDF final | Estructura del entregable (ver §7) armada de antemano | ⬜ |

## 6. Estrategia y diferenciación

- **Contar la historia desde marketing, no desde ML**: "hoy Ford le habla igual a todos; con esto le habla primero a los que están por decidir". El jurado (directores/gerentes) compra eso.
- **Demo interactiva**: la app de Streamlit con la "bandeja de clientes priorizados" convierte un notebook en un producto. Bajo costo, alto impacto.
- **Calibración + honestidad**: mostrar qué NO puede hacer el modelo (clientes nuevos sin historial = cold start) y cómo se mitigaría.
- **Propuesta de siguiente paso**: A/B test de campaña sobre el top-decil vs. control, y a futuro uplift modeling (targetear a los *persuadibles*, no a los que compraban igual). Mencionar uplift muestra sofisticación aunque no lo implementemos.
- **Riesgo a evitar**: quedarnos en "AUC 0.85". Sin traducción a acción comercial, este desafío se vuelve indistinguible del de cualquier otro equipo.

## 7. Estructura del PDF final

1. Resumen ejecutivo (media página, sin jerga).
2. Entendimiento del problema y del negocio.
3. Datos y EDA (hallazgos, no inventario).
4. Metodología (features, modelo, validación anti-leakage).
5. Resultados: curva de lift + captura por decil + métricas.
6. Qué señales predicen la recompra (SHAP) — insights de negocio.
7. Segmentos accionables + demo.
8. ROI estimado con supuestos.
9. Limitaciones y roadmap a producción.

## 8. Si elegimos este desafío: ángulo del video de inscripción

- Enfatizar que entendemos que el fin es **acción comercial personalizada**, no un modelo.
- Mencionar el marco RFM + ciclo de recambio del vehículo como hipótesis inicial (muestra que ya pensamos el dominio).
- Metodología: baseline rápido → iterar con mentores → entregar segmentos accionables con demo.

## 9. Reparto de roles sugerido

- **Rol A (datos)**: EDA, limpieza, features RFM.
- **Rol B (modelado)**: baseline, LightGBM, validación, calibración, SHAP.
- **Rol C (negocio/comunicación)**: segmentos, ROI, demo Streamlit, PDF y presentación.
- Los tres revisan todo; rotar en las reuniones de sync.
