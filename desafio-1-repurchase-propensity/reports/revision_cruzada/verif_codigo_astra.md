# Verificación del bloque `codigo_astra` (docs/04 §1.1 y §2.2)

> Rol escéptico: recalculé cada afirmación con código propio sobre la agenda cruda (parquet tipado de fable), el `eventos.parquet` / `ventanas.parquet` / `test_predicciones.parquet` de astra y una re-ejecución mes a mes de su `snapshot()` (importado en solo lectura), que reproduce sus 132.869 ventanas y episodios exactamente.
>
> **Resultado**: 5 afirmaciones confirmadas (b, c, d, e, f) y 2 ajustadas (a, g). Ninguna refutada. Las salvedades que importan: (1) la brecha 225.479 vs 220.522 mezcla nivel turno con nivel vehículo-día; el efecto real de contar Guarantee es +3,776 turnos; (2) la fecha de evento de astra es el **checkout** (fable: check-in), lo que convierte en churn a 1,184 ventanas cuyo vehículo entró al taller dentro del mes, y en 'retorno' a 1,084 vehículos que ya estaban en el taller el día del scoring; (3) la preempción de astra corta el 1° del mes y no en vencimiento − 30: 12,596 episodios que fable etiquetaría como retorno no existen en astra; (4) 3,573 episodios nunca se scorean porque el vencimiento recalculado salta de 'futuro' a 'vencido' entre dos snapshots (hallazgo nuevo, no está en el doc). Los archivos: `scripts/revision_cruzada/verif_codigo_astra.py`, `reports/revision_cruzada/verif_codigo_astra_*.csv`. Nota de integridad: la primera corrida importó `src.features` y `src.modeling` de astra y Python regeneró tres `.pyc` en su `src/__pycache__/` (mismo código fuente, sin efecto); el script ahora fija `sys.dont_write_bytecode`. No se tocó ningún otro archivo de astra.

Corte de datos de fable: 2026-08-25. Agenda cruda sin duplicados exactos: 612,069 ítems, 492,442 turnos; turnos contradictorios (regla de astra): 4.

## (a) `maintenance` de astra = ServiceType == 'Mantenimiento' a nivel turno; incluye Guarantee

Flag `maintenance` de astra vs mi recálculo 'algún ítem con ServiceType=Mantenimiento': coinciden en 100.0000% de 489,541 turnos utilizables por astra.
Turnos (60) Concluido con algún ítem ServiceType=Mantenimiento: 226,697; de ellos SIN ningún ítem numerado (ServiceMaintenance nulo): **3,808**.
  Composición de esos 3,808: sólo Guarantee 3,788; sólo Contactless 19; ambos 1.
  De esos 3,808, los que astra efectivamente cuenta como mantenimiento estricto (maintenance & valid_complete en su eventos.parquet): **3,777**. Los demás caen por: sin vehicle_id 31; checkout inválido 0; contradictorios 0.
Mantenimientos estrictos de astra (turnos, maintenance & valid_complete): **225,479**.
Mantenimientos de fable: a nivel TURNO (is_completed_maintenance & vehicle_id) **221,703** (más 1,186 sin VIN que ninguno de los dos usa; el 01_reconciliacion los cuenta en su '222.889'); a nivel vehículo-día tras dedup y visitas partidas (`maintenance_events`) **220,522**.
Comparación turno a turno: sólo astra 3,777 (sin ítem numerado: 3,777; con ítem numerado: 0); sólo fable 1 (checkout inválido 1; contradictorios 0).
Diferencia neta a nivel turno: +3,776; la cifra del doc (225.479 vs 220.522 = +4,957) mezcla el nivel turno de astra con el nivel vehículo-día deduplicado de fable (1,181 turnos colapsados por fable como misma visita).

## (b) Retorno exige el mismo `customer_id`; retorno anónimo → NaN; agosto sin etiqueta

Recalculé `target` desde eventos.parquet con la regla '[scoring, fin) & mismo customer_id; anónimo sin retorno propio → NaN; fin > 1/8/2026 → NaN': coincide con el parquet en 100.0000% de 132,869 ventanas (0 discrepancias). `target_vin` (cualquier customer_id): coincide en 100.0000%.
Ventanas de agosto 2026: 6,285, con etiqueta: 0 (window_end = 1/9 > observed_until).
Ventanas con horizonte observado: 126,584; sin etiqueta por retorno anónimo: 129 (0.102%); de ellas 129 tienen efectivamente un retorno anónimo del VIN en el mes (verificado).
Churn por identidad (target=1 pero target_vin=0: el VIN volvió con otro customer_id): 3,936 = 3.11% de las ventanas etiquetadas = 4.00% de sus churn. Churn mismo usuario 0.779 vs mismo VIN 0.748.

## (c) Horizonte [scoring, 1° del mes siguiente); scoring = 1° del mes del vencimiento; mediana 14 d tras vencer

scoring_date == 1° del mes del vencimiento en 100.0000% de las ventanas; window_end == scoring + 1 mes en 100.0000%; scoring ≤ due < window_end en 100.0000%.
Casos borde: 590 ventanas cuyo único retorno propio cae exactamente el 1° del mes siguiente → etiqueta {1.0: 590} (churn: el fin es exclusivo). 575 ventanas con retorno exactamente el día del scoring → etiqueta {0.0: 575} (cuenta: inicio inclusivo).
Test astra (23,740 ventanas abr-jul 2026, target no nulo: 23,740): días de observación después del vencimiento: mediana **14** (días enteros) / 14.4 (fraccionarios); p25 6.9, p75 22.1; mínimo 0.00, máximo 31.00. Con menos de 5 días: 18.1 %; con menos de 1 día: 2.7 %.
Todas las ventanas etiquetables: mediana 14.2 d, máximo 31.0 d (el rango es 0-31, no 0-30: meses de 31 días con vencimiento el 1°: 2,073 ventanas).

## (d) Exigir checkout válido: cuántos mantenimientos concluidos se pierden

astra: (60) Concluido & ServiceType=Mantenimiento: 225,480 turnos con VIN; sin checkout **0**; checkout anterior al turno **1** (comparando fechas normalizadas como astra; sin normalizar: 1); contradictorios 0.
fable: (60) Concluido & ítem numerado: 221,703 turnos con VIN; sin checkout **0**; checkout anterior al turno **1** (comparando fechas normalizadas como astra; sin normalizar: 1); contradictorios 0.
Control contra la auditoría de astra ('cierres_anteriores_al_turno' = 13, todos los status): recalculado 13.
Fecha de evento: astra usa el checkout, fable el check-in (si está a ±45 d del turno) o la fecha del turno. En los 225,479 mantenimientos válidos de astra, checkout − fecha de turno: mediana 0 d, p90 7, > 0 en 47.2 %, ≥ 7 d en 10.5 %; checkout − check-in: > 0 en 36.6 %, ≥ 7 d en 7.4 % (check-in nulo: 11.9 %).
El checkout cae en un mes calendario distinto al de la fecha del turno en 13,792 mantenimientos (6.1 %).
Ventanas etiquetadas churn cuyo vehículo (mismo usuario) ENTRÓ al taller por un mantenimiento dentro del mes (fecha de turno o check-in en el mes) pero salió el mes siguiente: **1,184** (1.20% de los churn; 0.94% de las ventanas). Con la fecha de evento de fable serían retornos. El checkout cae a ≤ 3 días del fin de mes en 580 de ellas, a ≤ 7 días en 798 (mediana 4 d).
Ventanas etiquetadas retorno cuyo mantenimiento ya había empezado ANTES del scoring (turno/check-in < 1° ≤ checkout): **1,084** (3.87% de los retornos): el vehículo estaba en el taller al momento de scorear; fable las trataría como preempted.

## (e) Primer ciclo anclado en entrega + 1 año cuando no hay odómetro

Ventanas de primer ciclo (sin_mantenimiento_previo=1): 18,234 de 132,869 (13.7 %); anchor_id='entrega' en 100.00%; anchor_date == entrega (o garantía si no hay entrega) en 100.00%; anclada en entrega (venta conocida) 91.3 %, en garantía de agenda 8.7 %.
Sin odómetro (km_ultimo nulo): 12,933 (70.9 %); en ellas due_date == ancla + 1 año (DateOffset) en 100.00%.
Con odómetro de alguna visita cerrada previa (no mantenimiento): 5,301 (29.1 %); vencimiento a mediana 365 d del ancla; antes de los 365 d en 47.1 %.
Test: 3,562 ventanas de primer ciclo, churn 0.784; edad del vehículo al scoring (desde el ancla): mediana 349 d, p10 336, p90 362; con odómetro previo 20.8 %.
Vehículos entregados ene-2024/jun-2025 con mantenimiento observado después de la entrega: 29,097 de 34,534; primer service a 9.1 meses de mediana, antes de 9 meses 49.4 %, antes de 6 24.1 %. Lo hacen ANTES del 1° del mes de entrega+1 año (nunca tendrían ventana de primer ciclo en astra): 69.2 %.
De esos 34,534 vehículos entregados, con ventana de primer ciclo en astra: 14,566 (42.2 %).

## (f) `meses_observables`: constante por mes de scoring; fuera de rango en test

Valores distintos por scoring_date: máximo 1 (constante por mes: sí).
Rango por partición de astra:
| split       |   min |   max |
|:------------|------:|------:|
| calibration | 24.01 | 25.03 |
| demo        | 30.98 | 30.98 |
| embargo     | 20.01 | 25.95 |
| test        | 26.97 | 29.96 |
| train       |  5.98 | 18.99 |
| valid       | 20.99 | 22.01 |
Posición por |SHAP| medio en resultados.json: 5°.
Modelo de astra sobre su test: score idéntico si `meses_observables` se fija en el máximo de train (18.99): máx |Δ| = 0.00e+00 (los valores 27-30 caen en el último bin: el modelo los trata como agosto 2025). Fijándola en la mediana de train (13.96): máx |Δ| = 0.083, ROC-AUC 0.6733 → 0.6715, score medio 0.791 → 0.786.

## (g) Cada episodio (VIN:ancla) entra una sola vez; retorno antes del 1° → la ventana no existe

En ventanas.parquet: episodios duplicados 0; pares (vehicle_id, scoring_date) duplicados 0; vehículos con >1 ventana 31,426 (máximo 15 ventanas).
Ventanas con un mantenimiento (definición astra) entre el ancla y el scoring: 0 (si volvió antes del 1°, el ancla es la nueva).
Reproducción de build_windows con los snapshots re-ejecutados: ventanas 132,869 vs 132,869 en el parquet; meses con recuento idéntico: 26 de 26; episodios idénticos: True.
customer_id de la ventana coincide con el del snapshot re-ejecutado en 100.0000%.

Clasificación de todos los episodios (VIN:ancla) vistos en algún snapshot jul-2024/ago-2026:
| clase                         |   ancla_entrega |   ancla_mantenimiento |   total |
|:------------------------------|----------------:|----------------------:|--------:|
| censurado_futuro              |           14779 |                 43483 |   58262 |
| excluido_identidad_o_regla    |             343 |                  1720 |    2063 |
| preempted_ancla_reemplazada   |           24915 |                 43529 |   68444 |
| salteado_luego_volvio         |             894 |                  1320 |    2214 |
| salteado_sigue_vencido        |             516 |                   843 |    1359 |
| sin_fecha                     |             709 |                     0 |     709 |
| vencido_al_aparecer_posterior |           13672 |                   137 |   13809 |
| vencido_antes_de_jul2024      |            9380 |                  3286 |   12666 |
| ventana                       |           18234 |                114635 |  132869 |

Episodios 'preempted': 68,444; al mes siguiente el vehículo tiene otra ancla en 100.00% de los casos (sin fila siguiente: 0, son los que el vehículo deja de aparecer).
Retorno (ancla nueva) respecto del vencimiento estimado en el último snapshot (68,444 con fecha): mediana -88 d; retorno en [due−30, due) → fable lo etiquetaría retorno (0), astra no crea la ventana: 12,596 (18.4 %); retorno más de 30 d antes del vencimiento (preempted en ambos): 55,848. Sólo anclas de mantenimiento: 10,641 de 43,529 (24.4 %).
Episodios sin clase ('otro'): 0.
Episodios salteados por salto del vencimiento (estuvieron 'futura', pasaron a 'vencida' sin ningún mes 'en_mes', nunca scoreados): 3,573 (anclas de mantenimiento: 2,163); equivalen al 2.7% de las ventanas creadas. De ellos el vehículo volvió después (ancla nueva) en 2,214 y sigue vencido sin ventana al final de los datos en 1,359.
  Ejemplo (episodio 0034d0e385331e72:c742875bfcd9754b):
| scoring    | anchor_date   | due_date   |   km_ultimo | st      |
|:-----------|:--------------|:-----------|------------:|:--------|
| 2024-07-01 | 2024-04-06    | 2024-08-18 |       41148 | futura  |
| 2024-08-01 | 2024-04-06    | 2024-06-23 |       52681 | vencida |
| 2024-09-01 | 2024-04-06    | 2024-06-23 |       52681 | vencida |
| 2024-10-01 | 2024-04-06    | 2024-06-23 |       52681 | vencida |
  Ejemplo de churn por fecha de checkout: ventana row_id 132 (VIN 0a807af278bd0e42, scoring 2024-07-01, fin 2024-08-01): turno de mantenimiento el 2024-07-29, check-in 2024-07-29, checkout 2024-08-01 → astra: churn; fable (fecha = check-in): retorno.

## Tabla de veredictos

| Afirmación | Veredicto | Número original | Número recalculado | Nota |
|---|---|---|---|---|
| (a) `maintenance` = ServiceType=='Mantenimiento' a nivel turno e incluye Guarantee; 3.808 turnos concluidos sin ServiceMaintenance contados como mantenimiento; 225.479 vs 220.522 | **ajustada** | 3.808 / 225.479 vs 220.522 | 3,808 sin número, de los cuales astra cuenta 3,777 / 225,479 vs 221,703 (turno) o 220,522 (vehículo-día) | La regla y la inclusión de Guarantee son correctas (flag reproducido al 100 %). Pero 31 de los 3.808 no entran (sin VIN o checkout inválido) y 19 son 'Contactless service', no garantía. La comparación 225.479 vs 220.522 mezcla niveles: a nivel turno es 225,479 vs 221,703 (+3,776). |
| (b) Retorno exige el mismo customer_id; retorno anónimo → NaN; ventanas de agosto sin etiqueta | **confirmada** | — | target recalculado coincide 100.00%; 129 NaN por anonimato; agosto 6,285/6,285 sin etiqueta | Salvedad de magnitud: el 'churn por identidad' es 3.1% de las ventanas pero 4.0% de sus churn (el doc §0.7 dice '3,1 % de sus churn'). |
| (c) Horizonte [scoring, 1° del mes siguiente); scoring = 1° del mes del vencimiento; mediana 14 d de observación tras vencer en test | **confirmada** | 14 | 14 (enteros) / 14.4 (fraccionarios); rango 0.0-31.0 | Intervalo verificado con casos borde. Rango real 0-31 d (no 0-30). 18.1 % del test tiene < 5 d de observación. |
| (d) Exigir checkout válido no pierde eventos: 0 sin checkout, 1 con checkout anterior al turno | **confirmada** | 0 / 1 | 0 / 1 (ambas definiciones) | Cierto para el FILTRO. Lo que sí mueve etiquetas es usar el checkout como FECHA del evento: 1,184 churn de astra entraron al taller dentro del mes y salieron al siguiente (1.2% de sus churn), y 1,084 'retornos' ya estaban en el taller al scorear. |
| (e) Primer ciclo anclado en entrega + 1 año cuando no hay odómetro | **confirmada** | — | 100.0% de las ventanas sin odómetro vencen exactamente a ancla + 1 año; 70.9 % sin odómetro | Salvedad: el 29.1 % de las ventanas de primer ciclo sí tiene odómetro de otra visita y vence antes (mediana 365 d). Ancla = entrega si hay venta (91.3 %), si no garantía de agenda. Test: 3,562 ventanas, churn 0.784. |
| (f) meses_observables constante por mes de scoring; en test fuera del rango de entrenamiento (27-30 vs ≤ 20) | **confirmada** | 27-30 vs ≤ 20; 5° por SHAP | train 5.98-18.99, test 26.97-29.96; 5° por SHAP | Salvedad: el LightGBM no extrapola: los valores 27-30 caen en el último bin y el score es idéntico al de fijar la variable en su máximo de train (agosto 2025). No es fuga ni inestabilidad, es una constante que fija el nivel de la última época vista. |
| (g) Cada episodio entra una sola vez; un retorno antes del 1° hace que la ventana no exista (≈ preempted de fable) | **ajustada** | — | 0 episodios duplicados; 0 ventanas con retorno entre ancla y scoring; build_windows reproducido (132,869 = 132,869) | La equivalencia no es exacta: astra preempta hasta el 1° del mes del vencimiento, fable hasta due−30 (el corte de astra siempre es igual o posterior). De 68,444 episodios preemptados por astra, 12,596 (18.4 %) volvieron en [due−30, due): fable los contaría como retornos (label 0), astra los saca de la población. Además 3,573 episodios nunca se scorean porque el vencimiento recalculado salta de 'futuro' a 'vencido' entre dos snapshots (2.7% de las ventanas creadas). |