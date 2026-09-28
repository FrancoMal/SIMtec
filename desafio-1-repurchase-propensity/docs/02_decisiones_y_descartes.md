# 02 — Decisiones tomadas y caminos descartados (con evidencia)

> Cada decisión lista **qué se decidió, por qué, con qué número, y qué alternativa se descartó y por qué**. Es el
> material para la defensa ante el jurado: "¿por qué esto y no aquello?". Las cifras salen de
> `reports/eda/*.md` (verificadas por un segundo analista), `reports/modelo/resumen.md`,
> `reports/modelo/sensibilidad_ventana.csv` y `reports/modelo/ablaciones.md`. Corte de datos: 2026-08-25.

## 1. Qué problema se resuelve (y cuál no)

| Decisión | Por qué | Descartado |
|---|---|---|
| **Modelar churn de service**: probabilidad de que un usuario–vehículo que entra en ventana de mantenimiento NO complete el próximo mantenimiento programado en la red oficial dentro del horizonte. | Es la definición literal de la ficha técnica oficial de Ford (11/9/2026) y lo que evalúan sus 9 criterios. La recompra es el *porqué* (service → satisfacción → lealtad → recompra), no lo observable. | **Modelar recompra directamente**: no hay label de recompra en el dataset (sales tiene una fila por vehículo vendido 2024-26; sólo 3.534 clientes compran >1 vehículo y son mayormente flotas). Habría sido inventar un target. |
| **Unidad usuario–vehículo–ventana**, scoring al abrir la ventana, con vista consolidada por usuario. | Lo pide la ficha. El riesgo es del vehículo (su plan de km); la acción es sobre el usuario. | Unidad "cliente" a secas: pierde el riesgo por VIN y el 21 % de los vehículos tiene más de un `customer_id`, en buena parte por artefactos de identidad entre canales (EDA 04). |

## 2. Evento objetivo: qué cuenta como "mantenimiento programado completado"

| Decisión | Evidencia (EDA 01) | Descartado |
|---|---|---|
| Turno `(60) Concluido` con ≥1 ítem con `ServiceMaintenance` no nulo. 220.522 eventos en 87.531 vehículos. | `ServiceMaintenance` es 100 % consistente con el nombre del ítem y con `ServiceType = Mantenimiento`. | Contar `(90) Concluido sin OS` como retorno: el auto entró (check-out 96 %) pero sólo 26 % traía mantenimiento y 49 % era diagnóstico. Se usa como **visita** (feature), no como target (+1,8 % de eventos si se incluyera). |
| Excluir garantía, campañas/recalls, cambio de aceite suelto, inspecciones. | Son visitas, no el plan de mantenimiento; incluir campañas sumaría 31.707 turnos que no son "retorno al plan". | Incluir recalls como retorno: inflaría la retención con visitas que Ford provoca (campañas), no que el cliente elige. |
| Colapsar turnos del mismo vehículo el mismo día y, a ≤30 días, los que repiten el **mismo número de service** (el mismo service cargado dos veces: Δkm mediana 0). | 335 duplicados por vehículo-día + 846 con mismo número a ≤30 días (EDA 01 §12, verificado). Los pares cercanos con número distinto son visitas reales de flotas de alto uso y se conservan. | Dejar duplicados: crea "retornos" falsos a 5 días. Colapsar cualquier par a <30 días (regla inicial): borraba visitas reales. |

## 3. Ventana, vencimiento y horizonte (los parámetros que más discutió el equipo)

Regla implementada (`src/repurchase/ventanas.py`, `config/params.json`):

```
ancla        = último mantenimiento completado (o inicio de garantía para el primer service)
tasa_uso     = km al ancla / edad del vehículo al ancla          (fallback: mediana de la generación, 4 % de casos)
vencimiento  = ancla + min(365 días, K_gen / tasa_uso)          K = 16.000 km (P703) / 10.000 km (P375), plan oficial Ford
primer service: vencimiento = inicio de garantía + 300 días     (sin km previo no hay tasa individual)
apertura y scoring = vencimiento − 30 días ; horizonte = vencimiento + 90 días
churn = 1 si no hay mantenimiento completado entre la apertura y el cierre del horizonte
```

| Decisión | Por qué (número) | Descartado y por qué |
|---|---|---|
| **K por generación (16k P703 / 10k P375)** | Son los intervalos oficiales del plan Ford Argentina (ford.com.ar: "revisión de 16.000 km ó 12 meses" para la Ranger nueva; manual de garantía Ranger T6 2016: "10.000 km ó 1 año"), y los datos los reproducen: km al n-ésimo service 16.0-16.2k × n en P703 y 10.1-10.3k × n en P375; Δkm mediano 16.138 / 10.330 (EDA 02). Corrección de esta vuelta: el EDA había leído 16.1k como "15.000 + atraso"; la revisión cruzada (docs/04) lo corrigió al nominal de 16.000. | **"1 año" (regla de tiempo)**: ubica el vencimiento 200 días *después* de la mediana de retorno; el 86 % de los clientes ya volvió antes de que la ventana abra. En el harness: 66.589 ventanas, 58 % churn, sólo 18 % de los retornos caen dentro de la ventana (`sensibilidad_ventana.csv`, fila 25). **K = 15.000 para todo el parque**: corre el vencimiento 33 días tarde en P375 (28 % de retornos antes de abrir). **K = 10.000 para todos**: adelanta 20 días en P703. |
| **Tope anual de 365 días** | Manda sólo en el 4,6 % de las ventanas; sin tope, los de bajo uso (p10 = 9.900 km/año) esperarían 1,5 años. | Tope de 270 días: adelanta el vencimiento de quienes sí vuelven al año. |
| **Tasa de uso acumulada (km/edad)** | Disponible en el 96 % de las anclas; concuerda con la pendiente entre visitas (Spearman 0,895). | Tasa "reciente" (último intervalo): no mejora (p50 +10 vs +7 días) y existe sólo en 37 % de las ventanas. |
| **Apertura a −30 días** | 80 % de las ventanas abiertas; alineado con el "próximo mes" del tutor y con el lead time típico de un Service Reminder. | **−60 días**: abre el 88 % de las ventanas y captura más retornos (64 % vs 53 % en el harness) pero la ventana pasa a 150 días y se aleja del corto plazo; queda como alternativa si el negocio contacta con más anticipación (fila 5 del harness: 169.327 ventanas, 37 % churn). |
| **Horizonte +90 días** | Captura el 84 % de los retornos de quienes vuelven en 18 meses (EDA 02, tabla f2); prevalencia de churn 39,7 % entre ventanas abiertas; el resultado se conoce a tiempo de actuar. | **+60**: etiqueta como churn a muchos "tardíos" (77 % capturado, 47 % churn). **+180**: captura 94 % pero el resultado llega 7 meses después del ancla, tarde para medir campañas. |
| **Primer service: vencimiento a 300 días del inicio de garantía** | Mediana real 9,2 meses; 64,5 % lo hace en 12 meses. Sin km previo ninguna regla centra (p10-p90 de ~280 días). | 365 días: abre tarde (el 62 % ya vino). K/tasa poblacional: peor dispersión. **Mejor solución pendiente**: km de telemetría de vehículos conectados (pregunta al mentor). |
| **Ancla = último mantenimiento** | Reproduce cómo "le toca" al cliente según su uso. | **Aniversarios del plan** (12·n meses desde garantía): 76 % de churn y 17 % de captura (fila 34): el plan no es anual. |

| **Margen de 30 días antes del corte para etiquetar** | Agosto 2026 tiene 1.040 turnos "en progreso" y 337 agendados vencidos: un mantenimiento en curso en la última semana se vería como churn. Ventanas cuyo horizonte cierra después del 26/07/2026 quedan censuradas (síntesis EDA, riesgo "censura a la derecha"). | Sin margen: 27.327 ventanas de test y ROC-AUC 0,736; con margen: 20.191 y 0,736 (ambas con K = 15.000); con margen y K = 16.000 oficial (y 10.000 para las Ranger anteriores a la T6): 19.709 y 0,740. No cambia el resultado, pero evita etiquetas falsas en el borde. |

Efecto de la definición: 142.637 ventanas evaluables (2024-2026), churn 41,6 % (P703 ≈ 32 %, P375 ≈ 42 %, primer service ≈ 47 %); 35.190 ventanas censuradas al cutoff (población a scorear hoy) y 19 % de anclas "preempted" (el cliente volvió antes de abrir la ventana: no necesita contacto). La revisión cruzada con la otra solución (docs/04) confirmó que la población y el evento coinciden entre ambos trabajos y que la única diferencia material es el horizonte.

## 4. Leakage: lo que se encontró y cómo se resolvió

| Hallazgo | Evidencia | Decisión |
|---|---|---|
| **`KM` es una foto por vehículo, no el km del turno.** | Constante en el 99,99 % de los vehículos, igual al último `VehicleCurrentKM` en 92-97 % (EDA 01, 02, 04, 05 lo detectaron por separado). | Nunca se usa. El km del evento es `VehicleCurrentKM` limpio (100 ≤ km ≤ 1.000.000, monotónico dentro del vehículo). **Ablación**: con `KM` el ROC-AUC fuera de tiempo sube de 0,740 a 0,813 y la calibración se rompe (ECE 0,056): era un resultado inflado. |
| **`ConnectedStatusARG` es un snapshot** | No varía en el tiempo (74 de 111.752 vehículos con más de un valor); "Sin información de conectividad" retorna 27 % y marca vehículos que *salieron* del sistema (se sabe después). | Excluido del modelo. **Ablación**: incluirlo *empeora* el test fuera de tiempo (0,730 vs 0,740) y la calibración (ECE 0,029): un leakage que no generaliza. |
| **Turnos futuros agendados** | No hay fecha de creación del turno: "tiene turno" no es reconstruible al scoring histórico. | No es feature. Se usa como **regla operativa** post-modelo en el scoring actual: 1.791 vehículos con turno agendado se marcan y se sacan de la lista de contacto. |
| **Encuestas** | `SurveyResponseDate` es *anterior* al turno (mediana 8 días): es una encuesta del agendado, no del service; sin señal (EDA 06). | Se usan sólo respuestas anteriores al scoring; su peso es marginal; ablación "sin encuestas" en `ablaciones.md`. |
| **Historia previa invisible (censura a la izquierda)** | La agenda arranca en 2024-01; el 60 % de los vehículos tiene garantía anterior. Al scorear en 2025-01, el 28 % de los vehículos activos no tiene ningún mantenimiento observado y el 68 % tiene services invisibles (EDA 05). | Features `months_observable` (el modelo sabe cuánta historia ve), `last_maint_number` y edad del vehículo como proxies de la historia invisible; split temporal que evalúa en 2026 (≥24 meses de historia). La síntesis del EDA recomienda entrenar sólo con scoring ≥ 2025-01; la ablación "exige ≥ 6 meses de historia observable" da el mismo resultado (ROC-AUC 0,738 vs 0,740), así que se conservan todas las ventanas y se documenta. Los 17.973 vehículos con garantía anterior a 2024 y sin ningún mantenimiento en 2024-2026 no tienen ancla observable: quedan fuera del backtest como "población invisible" (son clientes ya perdidos, no ventanas). |
| **Features "as-of"** | Toda feature se calcula con `merge_asof` estricto (evento < fecha de scoring). | Chequeo automático en el notebook 02: ninguna recencia ≤ 0. |

**Exclusiones de población** (EDA 05): 2.897 turnos sin `vehicle_id`; 110 ventas inválidas (107 con `Status ≠ ACCEPTED`, 3 con entrega 2013/2015, 1 "GLOBAL RANGER"); vehículos con `ModelYear` inválido y sin garantía. El canal HR y los `PersonType` 25/29/30 (un único comprador con 752 ventas, retención 18-19 % en el primer año) se conservan y se marcan por `sales_channel` / `person_type`: si el mentor confirma que son cuentas institucionales, se sacan de la población de contacto.

## 5. Features: qué entra, qué no, y por qué

**Entran** (84 columnas, `src/repurchase/features.py`): recencia (días desde el último mantenimiento / turno / visita), frecuencia e intensidad (mantenimientos por año observado, visitas, diagnósticos, reparaciones, recalls), patrón de uso (km/año, km al ancla, atraso en km respecto del plan, services salteados), ciclo de vida (antigüedad, n° de service del plan, generación, año modelo, versión), canal (último canal, proporción FordPass), dealer (concesionario y zona del último mantenimiento, cambios de dealer), relación (tamaño de flota, vehículos del cliente, es comprador, cambios de cliente), venta (unidad de negocio, tipo de persona, canal, provincia), geometría de la ventana (qué regla vence primero, días al vencimiento), mes del scoring.

**Qué pesa** (SHAP, test): versión/generación y antigüedad del vehículo, intensidad de mantenimiento observada, concesionario del último service, tamaño de flota, uso (km/día), atraso del último service respecto del plan, meses de historia observable.

**Lo que engaña en crudo y el jurado va a preguntar** (EDA 06 y su verificación): los no-shows previos no separan en univariante (78,0 / 78,9 / 79,1 % de retorno con 0 / 1 / 2+) por una **paradoja de Simpson**: tener un no-show implica haber tenido turnos, y los turnos previos son el predictor más fuerte del bloque. Controlando por turnos previos, el no-show baja el retorno (67 vs 73 % con 1 turno; 73 vs 77 % con 2) y en un modelo conjunto tiene OR 0,73 / 0,63; las cancelaciones duras OR 0,75 / 0,70. Por eso el modelo lleva `n_noshow`, `n_hard_cancel` **y** `n_appts` juntos. Las reprogramaciones se re-agendan en 72 % de los casos a mediana 6 días. Un vehículo "con problemas" (reparaciones, recalls) vuelve más **porque tuvo más contactos**, no por el problema (OR ajustado ≈ 1). La encuesta no aporta (es previa al turno). Sí discriminan: recencia (turno previo hace >365 días: 51 % vs 86 % si fue hace 31-90), FordPass (OR 1,29 ajustado por generación, dealer e intensidad), el dealer (estable entre años incluso con vehículos disjuntos: Spearman 0,68; 73 % vs 84 % entre peor y mejor quintil) y un diagnóstico en el turno (OR 0,82).

**Pendiente de agregar** (verificación EDA 02): contar "intervalos dobles" por km (Δkm ≥ 1,5·K) en vez de por salto de numeración, porque la mitad de los saltos de numeración es ruido; hoy `last_interval_km_vs_k` cubre sólo el último intervalo.

**Descartado**: `ServiceMonth` (= 12·n nominal, no observado), `ServiceName` para el número de service (bug de catálogo 11→"1°"), `LoanerVehicle`, `Quicklane`, `CancellationReason`, `ScheduleModalityCode`, `SalesType` (100 % nulos o constantes), `ServiceLaborCost` (0,7 % no nulo), `ServicePriceDiscount` (valores no interpretables).

## 6. Modelo, validación y métricas

| Decisión | Por qué | Descartado |
|---|---|---|
| **LightGBM** (gradient boosting) con categóricas nativas, early stopping. | Datos tabulares con nulos estructurales (sin km, sin historia) y ~150k filas: es el estado del arte práctico; entrena en 15 s, se re-entrena cada mes. | Deep learning: sin ventaja en tabular chico y más difícil de explicar. Regresión logística sola: ROC-AUC 0,67 vs 0,74 (queda como baseline interpretable). |
| **Split temporal** por fecha de scoring: train ≤ sep-2025, calibración oct-dic 2025, test ene-abr 2026. | Es lo que pide la ficha (criterio 2) y lo que va a pasar en producción: se entrena con el pasado y se scorea el futuro. El mix P375/P703 cambia mes a mes (EDA 02), así que una validación cruzada aleatoria mentiría. | CV aleatoria estratificada: mezcla ventanas del mismo vehículo en train y test y no captura el drift de composición. |
| **Calibración isotónica** ajustada en el período de validación, nunca en test. | La ficha pide probabilidades reales (criterio 4); la lista de contacto usa la probabilidad para calcular valor esperado. ECE final 0,010. | Sin calibrar: LightGBM ya sale bien calibrado acá (ECE 0,011), la isotónica es un seguro barato; Platt: menos flexible. |
| **Métricas en este orden: recall a capacidad de contacto → lift por decil → PR-AUC → ROC-AUC → calibración.** | La decisión es "a quién llamo con N llamados por mes": recall a capacidad es la métrica del negocio. Contactando al 20 % de mayor score se captura el 36 % de los churners (1,8× el azar); decil 1 tiene 88 % de churn (2,1×). | Accuracy: con 43 % de churn, un modelo "todos vuelven" tiene 57 % de accuracy y cero valor. |
| **Baselines de comparación**: azar (= prioridad uniforme actual), heurística de reglas (antigüedad + no-shows), regresión logística. | La ficha pide mostrar el impacto vs la priorización actual. | — |
| **Segmentos por capacidad (Alto 20 % / Medio 30 % / Bajo 50 %)** en lugar de umbrales fijos de probabilidad. | La capacidad de contacto es finita y conocida; los umbrales de probabilidad resultantes se reportan (p ≥ 0,62 Alto, ≥ 0,37 Medio en test). Umbral de rentabilidad p ≥ 0,08 con los supuestos declarados: casi todos "valen" un recordatorio digital, sólo los de arriba un llamado. | Tres clusters no supervisados: no se atan a una acción ni a una capacidad. |

## 7. Supuestos de negocio (declarados, editables en `config/negocio.json`)

- **Uplift del contacto**: 15 % de los churners contactados se recuperan (campañas de retención de service en la industria: 10-25 %). Se mide con un A/B por decil.
- **Valor de un service retenido**: USD 250 (margen del mantenimiento + valor futuro atribuible: siguientes services, repuestos fuera de garantía, lealtad). Conservador.
- **Costo de un contacto humano**: USD 3; un recordatorio digital cuesta centavos.
- **Capacidad**: 3.000 contactos humanos por mes en toda la red (≈ 32 por concesionario).
- Con eso: contactar al 20 % de mayor score de un mes de test recupera ~1,7× más services que contactar al azar la misma cantidad; el modelo es rentable con uplift ≥ 5 % y valor ≥ USD 100 (`reports/modelo/roi_sensibilidad.csv`).

## 8. Lo que no se pudo resolver con estos datos (y cómo se resolvería)

1. **Primer service**: sin km previo la ventana es imprecisa (±140 días). Con la telemetría de vehículos conectados (km real) se convierte en una ventana exacta. Es donde más churn hay (19 % de los compradores 2024 no volvió en 18 meses).
2. **Identidad del cliente**: el `customer_id` cambia con el canal de reserva (Dealer vs FordPass) en el 53 % de los "cambios de cliente". Unificar identidades en origen mejoraría la vista por usuario.
3. **Turnos futuros**: guardar la fecha de creación del turno permitiría usar "ya agendó" como feature y medir el efecto del recordatorio.
4. **Historia previa a 2024**: con el histórico completo de la agenda desaparece la censura a la izquierda.
5. **Servicios fuera de la red**: el 9,4 % de los pares de services salta un número del plan (se hizo afuera). Hoy es una feature indirecta; con datos de repuestos/garantía sería directa.
