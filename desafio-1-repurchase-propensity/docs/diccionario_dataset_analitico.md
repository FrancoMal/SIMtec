# Diccionario del dataset analítico

Generado por `scripts/diccionario_dataset.py` a partir de `data/processed/dataset_analitico.parquet` (salida de `scripts/run_pipeline.py`).

## Qué es

- **Unidad de observación**: una fila por vehículo × ventana de mantenimiento. La ventana se abre 30 días antes del vencimiento estimado y el horizonte cierra 90 días después. El cliente vigente es un atributo de la fila.
- **Filas**: 142.637 ventanas, 80.276 vehículos. Evaluables (con etiqueta): 142.637; churn = 41,6 %.
- **Columnas**: 105 (87 columnas de features, de las que el modelo usa 86: `connected_status` se excluye por ser una foto; + 18 identificadores, geometría y etiquetas).
- **Regla de oro**: toda feature se calcula sólo con turnos de fecha anterior a `scoring_date` y encuestas respondidas antes (uniones as-of estrictas, `src/repurchase/features.py`). Nunca se usan `KM` ni `ConnectedStatusARG` de la agenda (son fotos a la fecha de extracción) ni turnos futuros.
- **Parámetros de la ventana** (`config/params.json`): {"cycle_days": 365, "km_interval": 16000, "km_by_generation": {"RANGER (P703)": 16000, "RANGER RAPTOR (P703)": 16000, "RANGER (P375)": 10000, "RANGER RAPTOR": 10000, "RANGER": 10000}, "lead_days": 30, "horizon_days": 90, "min_gap_days": 90, "first_due_days": 300, "anchor": "last_maintenance", "km_source": "current", "min_history_days": 0, "split_visit_days": 30, "label_margin_days": 30, "label_mode": "ventana"}.
- **Split temporal** (`config/params.json` → `split`): entrenamiento con ventanas abiertas hasta el 30/09/2025, calibración oct-dic 2025, test ene-mar 2026 (horizonte cerrado 30 días antes del corte 25/08/2026).
- **Cómo se construye**: `src/repurchase/eventos.py` (agenda → turnos, evento `mant_completado`), `ventanas.py` (anclas, vencimiento, apertura, horizonte, etiqueta y censura), `features.py` (features as-of). Reproducible con `scripts/run_pipeline.py`.

## Identificadores, geometría de la ventana y etiquetas

| Columna | Tipo | Rol | Descripción | % nulos |
|---|---|---|---|---:|
| `window_id` | categórica | identificador | id único de la ventana (vehículo + número de ventana) | 0,0 % |
| `vehicle_id` | categórica | identificador | id seudonimizado del vehículo (VIN hasheado) | 0,0 % |
| `scoring_date` | fecha | geometría | fecha de scoring = apertura de la ventana (vencimiento − 30 días); ninguna feature usa datos posteriores | 0,0 % |
| `anchor_date` | fecha | geometría | fecha del ancla: último mantenimiento programado completado o inicio de garantía (primer service) | 0,0 % |
| `due_date` | fecha | geometría | vencimiento estimado = ancla + min(365 días, K_gen / tasa de uso); primer service: garantía + 300 días | 0,0 % |
| `due_time` | fecha | geometría | vencimiento que daría sólo la regla de tiempo (ancla + 365 días) | 0,0 % |
| `due_km` | fecha | geometría | vencimiento que daría sólo la regla de kilómetros (ancla + K_gen / tasa de uso) | 22,3 % |
| `history_days` | entera | geometría | días de historia observable del vehículo en la agenda antes del scoring | 0,0 % |
| `customer_id` | categórica | identificador | cliente vigente del vehículo al momento del scoring (último turno anterior); nulo si no hay | 6,9 % |
| `last_dealer_id` | categórica | identificador | concesionario del último turno anterior al scoring | 17,2 % |
| `warranty_start` | fecha | identificador | inicio de garantía (fecha de entrega); fallback DeliveryDate de ventas | 0,4 % |
| `sales_customer_id` | categórica | identificador | comprador según la base de ventas (nulo si el vehículo no se vendió en 2024-26) | 69,7 % |
| `sales_dealer_id` | categórica | identificador | concesionario de la venta | 69,8 % |
| `SalesDate` | fecha | identificador | fecha de venta | 69,7 % |
| `label_churn` | numérica | etiqueta | TARGET: 1 si no hubo mantenimiento programado completado entre la apertura y el cierre del horizonte (vencimiento + 90 días); 0 si lo hubo | 0,0 % |
| `label_no_visit` | numérica | etiqueta | etiqueta secundaria: 1 si no hubo ninguna visita concluida a la red en el horizonte | 0,0 % |
| `status` | categórica | etiqueta | estado de la ventana: evaluable (etiquetada), censurada (horizonte abierto al corte), preempted, fuera_de_rango, futura | 0,0 % |
| `window_n` | entera | identificador | número de orden de la ventana dentro del vehículo | 0,0 % |

## Features (todas calculadas con información anterior a `scoring_date`)

### Recencia

| Columna | Tipo | Significado | % nulos | Nota |
|---|---|---|---:|---|
| `days_since_last_appt` | numérica | días desde el último turno (cualquier tipo) | 16,1 % |  |
| `days_since_last_maint` | numérica | días desde el último mantenimiento | 22,3 % |  |
| `days_since_last_noshow` | numérica | días desde el último no-show | 88,9 % | nulo = sin registro en la red antes del scoring |
| `days_since_last_cancel` | numérica | días desde la última cancelación | 66,4 % | nulo = sin registro en la red antes del scoring |
| `days_since_last_visit` | numérica | días desde la última visita concluida | 17,5 % |  |
| `days_since_last_km` | numérica | días desde la última lectura de km | 18,6 % |  |
| `days_since_last_survey` | numérica | días desde la última encuesta | 84,7 % | nulo = sin registro en la red antes del scoring |

### Frecuencia e intensidad

| Columna | Tipo | Significado | % nulos | Nota |
|---|---|---|---:|---|
| `n_maint` | entera | mantenimientos completados (historia observable) | 0,0 % |  |
| `n_completed` | entera | visitas concluidas (cualquier tipo) | 0,0 % |  |
| `n_no_os` | entera | turnos concluidos sin orden de servicio | 0,0 % |  |
| `n_noshow` | entera | no-shows previos | 0,0 % |  |
| `n_cancel` | entera | cancelaciones previas | 0,0 % |  |
| `n_appts` | entera | turnos previos (todos) | 0,0 % |  |
| `n_recall` | entera | recalls / campañas atendidas | 0,0 % |  |
| `n_diag` | entera | diagnósticos previos | 0,0 % |  |
| `n_repair` | entera | reparaciones previas | 0,0 % |  |
| `n_guarantee` | entera | servicios en garantía previos | 0,0 % |  |
| `n_fordpass` | entera | turnos por FordPass | 0,0 % |  |
| `n_web_or_app` | entera | turnos por canales digitales | 0,0 % |  |
| `n_pud` | entera | servicios con retiro y entrega | 0,0 % |  |
| `n_mobile` | entera | servicios móviles | 0,0 % |  |
| `n_fixed_price` | entera | servicios a precio fijo Ford | 0,0 % |  |
| `n_reschedule` | entera | reprogramaciones | 0,0 % |  |
| `n_hard_cancel` | entera | cancelaciones duras (sin reprogramar) | 0,0 % |  |
| `n_return_visits` | entera | visitas de retorno por el mismo problema | 0,0 % |  |
| `n_towing` | entera | remolques | 0,0 % |  |
| `n_customer_changes` | entera | cambios de cliente del vehículo | 0,0 % |  |
| `n_dealer_changes` | entera | cambios de concesionario | 0,0 % |  |
| `n_numbering_jumps` | entera | services salteados (hechos fuera de la red) | 0,0 % |  |
| `n_intervals_known` | entera | intervalos conocidos | 0,0 % |  |
| `n_surveys` | entera | encuestas respondidas | 0,0 % |  |
| `n_vehicles_customer_agenda` | entera | vehículos del cliente vistos en agenda | 0,0 % |  |
| `noshow_rate` | numérica | tasa de no-show | 16,1 % |  |
| `cancel_rate` | numérica | tasa de cancelación | 16,1 % |  |
| `fordpass_share` | numérica | proporción de turnos por FordPass | 16,1 % |  |
| `maint_per_year_observed` | numérica | mantenimientos por año observados | 0,0 % |  |

### Último turno / último mantenimiento

| Columna | Tipo | Significado | % nulos | Nota |
|---|---|---|---:|---|
| `last_status` | categórica | estado del último turno | 16,1 % | categórica nativa en LightGBM |
| `last_source` | categórica | canal del último turno | 16,1 % | categórica nativa en LightGBM |
| `last_dealer_zone` | categórica | zona del último concesionario | 16,1 % | categórica nativa en LightGBM |
| `last_days_in_dealer` | numérica | días en taller (último turno) | 26,8 % |  |
| `last_maint_km` | numérica | km en el último mantenimiento | 24,6 % |  |
| `last_maint_number` | numérica | n° del último service del plan | 22,3 % |  |
| `last_maint_source` | categórica | canal del último mantenimiento | 22,3 % | categórica nativa en LightGBM |
| `last_maint_dealer` | categórica | concesionario del último mantenimiento | 22,3 % | categórica nativa en LightGBM |
| `last_maint_days_in_dealer` | numérica | días en taller (último mantenimiento) | 22,3 % |  |
| `last_maint_fixed_price` | numérica | último mantenimiento a precio fijo | 22,3 % |  |
| `last_maint_pud` | numérica | último mantenimiento con retiro y entrega | 22,3 % |  |
| `last_maint_customer_waiting` | numérica | cliente esperó en el concesionario | 22,3 % |  |
| `last_interval_days` | numérica | días entre los dos últimos mantenimientos | 57,6 % | nulo = sin registro en la red antes del scoring |
| `last_interval_km` | numérica | km entre los dos últimos mantenimientos | 61,0 % | nulo = sin registro en la red antes del scoring |
| `last_rating` | numérica | última calificación (1-5) | 84,7 % | nulo = sin registro en la red antes del scoring |
| `last_maint_late_days` | numérica | atraso del último intervalo vs. 12 meses | 57,6 % | nulo = sin registro en la red antes del scoring |
| `last_maint_km_vs_plan` | numérica | km de atraso del último service vs. plan nominal | 24,6 % |  |
| `last_interval_km_vs_k` | numérica | último intervalo en km relativo al plan | 61,0 % | nulo = sin registro en la red antes del scoring |

### Intervalos entre mantenimientos

| Columna | Tipo | Significado | % nulos | Nota |
|---|---|---|---:|---|
| `mean_interval_days` | numérica | intervalo medio entre mantenimientos | 57,6 % | nulo = sin registro en la red antes del scoring |
| `std_interval_days` | numérica | regularidad (desvío del intervalo) | 76,3 % | nulo = sin registro en la red antes del scoring |

### Encuestas

| Columna | Tipo | Significado | % nulos | Nota |
|---|---|---|---:|---|
| `min_rating` | numérica | peor calificación en encuestas | 84,7 % | nulo = sin registro en la red antes del scoring |
| `mean_rating` | numérica | calificación media | 84,7 % | nulo = sin registro en la red antes del scoring |

### Uso y kilometraje

| Columna | Tipo | Significado | % nulos | Nota |
|---|---|---|---:|---|
| `anchor_km` | numérica | km al inicio de la ventana | 2,1 % |  |
| `km_rate_per_day` | numérica | uso (km/día) | 22,3 % |  |
| `last_km` | numérica | último km registrado | 18,6 % |  |
| `km_per_year` | numérica | uso (km/año) | 22,3 % |  |
| `km_expected_at_scoring` | numérica | km estimados al scoring | 24,4 % |  |

### Ciclo de vida

| Columna | Tipo | Significado | % nulos | Nota |
|---|---|---|---:|---|
| `k_gen` | numérica | intervalo del plan (km) según generación | 0,0 % |  |
| `generation` | categórica | generación (P375 / P703) | 0,0 % | categórica nativa en LightGBM |
| `model_year` | numérica | año modelo | 0,3 % |  |
| `tma` | categórica | versión (TMA) | 2,6 % | categórica nativa en LightGBM |
| `vehicle_age_days` | numérica | antigüedad del vehículo (días) | 0,4 % |  |
| `vehicle_age_years` | numérica | antigüedad del vehículo (años) | 0,4 % |  |
| `months_observable` | numérica | meses de historia observable | 0,0 % |  |
| `is_first_service` | entera | es el primer service del vehículo | 0,0 % |  |

### Venta y cliente

| Columna | Tipo | Significado | % nulos | Nota |
|---|---|---|---:|---|
| `connected_status` | categórica | estado de conectividad | 2,5 % | EXCLUIDA del modelo (exclude_snapshot): es una foto a la fecha de extracción; queda en el dataset sólo para la ablación |
| `region` | categórica | región | 2,5 % | categórica nativa en LightGBM |
| `in_sales` | entera | vendido 2024-2026 (en base de ventas) | 0,0 % |  |
| `person_type` | categórica | tipo de persona (F/J) | 69,7 % | categórica nativa en LightGBM; nulo = sin registro en la red antes del scoring |
| `business_unit` | categórica | unidad de negocio (Blue/Pro) | 69,7 % | categórica nativa en LightGBM; nulo = sin registro en la red antes del scoring |
| `sales_channel` | categórica | canal de venta | 69,7 % | categórica nativa en LightGBM; nulo = sin registro en la red antes del scoring |
| `sales_state` | categórica | provincia de venta | 69,7 % | categórica nativa en LightGBM; nulo = sin registro en la red antes del scoring |
| `is_buyer` | entera | el cliente actual es el comprador | 0,0 % |  |
| `same_dealer_as_sale` | entera | mismo concesionario que la venta | 0,0 % |  |
| `fleet_size_sales` | entera | tamaño de flota (compras 2024-26) | 0,0 % |  |

### Geometría de la ventana

| Columna | Tipo | Significado | % nulos | Nota |
|---|---|---|---:|---|
| `rate_source` | categórica | origen de la tasa de uso (individual / generación) | 0,0 % | categórica nativa en LightGBM |
| `binding_rule` | categórica | qué regla vence primero (km/tiempo) | 0,0 % | categórica nativa en LightGBM |
| `anchor_type` | categórica | tipo de ancla (1er service / siguiente) | 0,0 % | categórica nativa en LightGBM |
| `days_anchor_to_due` | entera | días del último service al vencimiento | 0,0 % |  |
| `days_to_due_at_scoring` | entera | días hasta el vencimiento al scoring | 0,0 % |  |
| `scoring_month` | entera | mes del scoring | 0,0 % |  |

## Ranking priorizado (`data/processed/scores_actuales.csv`)

Una fila por vehículo en ventana o que entra en los próximos 30 días al corte. Incluye el output mínimo de la ficha (ids, fecha de scoring, probabilidad, segmento, drivers) más las columnas de contexto que muestra el dashboard. `scores_actuales_por_usuario.parquet` es la vista consolidada por cliente (sus vehículos en ventana y el peor score).

| Columna | Descripción |
|---|---|
| `window_id` | id de la ventana |
| `vehicle_id` | id seudonimizado del vehículo |
| `customer_id` | id seudonimizado del cliente vigente |
| `fecha_apertura_ventana` | apertura de la ventana (vencimiento − 30 días) |
| `vencimiento_estimado` | vencimiento estimado del service |
| `cierre_horizonte` | fin del horizonte (vencimiento + 90 días) |
| `poblacion_actual` | en_ventana (ya abierta) o abre_en_30_dias |
| `anchor_type` | tipo de ancla (1er service / siguiente) |
| `binding_rule` | qué regla vence primero (km/tiempo) |
| `vehicle_age_years` | antigüedad del vehículo (años) |
| `km_per_year` | uso (km/año) |
| `last_km` | último km registrado |
| `days_since_last_maint` | días desde el último mantenimiento |
| `n_maint` | mantenimientos completados (historia observable) |
| `n_noshow` | no-shows previos |
| `n_cancel` | cancelaciones previas |
| `last_source` | canal del último turno |
| `last_maint_dealer` | concesionario del último mantenimiento |
| `last_dealer_zone` | zona del último concesionario |
| `generation` | generación (P375 / P703) |
| `model_year` | año modelo |
| `business_unit` | unidad de negocio (Blue/Pro) |
| `person_type` | tipo de persona (F/J) |
| `is_buyer` | el cliente actual es el comprador |
| `fleet_size_sales` | tamaño de flota (compras 2024-26) |
| `n_vehicles_customer_agenda` | vehículos del cliente vistos en agenda |
| `last_rating` | última calificación (1-5) |
| `fecha_scoring` | fecha en que se calculó el score (corte de datos) |
| `dias_restantes_horizonte` | días que quedan hasta el cierre del horizonte |
| `dias_en_ventana` | días transcurridos desde la apertura |
| `prob_churn` | probabilidad calibrada (0-1) de no completar el mantenimiento en el horizonte |
| `segmento` | Alto / Medio / Bajo según score y capacidad de contacto (20 % / 30 % / 50 %) |
| `tiene_turno_agendado` | ya tiene un turno futuro en la agenda (regla operativa: sale de la lista de contacto) |
| `fecha_turno_agendado` | fecha de ese turno |
| `driver_1` | principal driver en lenguaje llano, con dirección (↑/↓ riesgo) |
| `driver_2` | segundo driver |
| `driver_3` | tercer driver |
| `driver_1_feature` | nombre técnico de la feature del driver 1 |
| `driver_2_feature` | nombre técnico de la feature del 2 |
| `driver_3_feature` | nombre técnico de la feature del 3 |
| `driver_1_shap` | contribución SHAP del driver 1 (log-odds) |
| `driver_2_shap` | contribución SHAP del 2 (log-odds) |
| `driver_3_shap` | contribución SHAP del 3 (log-odds) |
| `prioridad` | ranking (1 = contactar primero): segmento, luego probabilidad |
