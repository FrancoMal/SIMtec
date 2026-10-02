# Resumen de la corrida del modelo

- Corrida: 2026-10-01 17:02  |  cutoff de datos: 2026-08-25
- Parámetros de ventana: `{"cycle_days": 365, "km_interval": 16000, "km_by_generation": {"RANGER (P703)": 16000, "RANGER RAPTOR (P703)": 16000, "RANGER (P375)": 10000, "RANGER RAPTOR": 10000, "RANGER": 10000}, "lead_days": 30, "horizon_days": 90, "min_gap_days": 90, "first_due_days": 300, "anchor": "last_maintenance", "km_source": "current", "min_history_days": 0, "split_visit_days": 30, "label_margin_days": 30, "label_mode": "ventana"}`
- Split temporal: train ≤ 2025-09-30 (n=102,040, churn 41.4%); valid ≤ 2025-12-31 (n=20,888, churn 41.6%); test 2026-01-01 → 2026-03-28 (n=19,709, churn 42.6%)
- Features: 86  |  iteraciones LightGBM: 271  |  snapshot excluido: True

## Métricas en test (fuera de tiempo)

| modelo                                      |     n |   base_rate |   roc_auc |   pr_auc |    brier |   log_loss |      ece |
|:--------------------------------------------|------:|------------:|----------:|---------:|---------:|-----------:|---------:|
| azar (prioridad uniforme, situación actual) | 19709 |      0.4262 |    0.4969 |   0.4224 |   0.3347 |     1.0049 |   0.2553 |
| heurística de reglas                        | 19709 |      0.4262 |    0.6093 |   0.518  | nan      |   nan      | nan      |
| regresión logística (calibrada)             | 19709 |      0.4262 |    0.6744 |   0.5961 |   0.2222 |     0.6505 |   0.0179 |
| LightGBM sin calibrar                       | 19709 |      0.4262 |    0.7407 |   0.7124 |   0.1985 |     0.5766 |   0.0129 |
| LightGBM calibrado (isotónica)              | 19709 |      0.4262 |    0.7403 |   0.7042 |   0.1985 |     0.5781 |   0.0098 |

## Recall a capacidad (LightGBM calibrado)

|   capacidad_pct |   contactados |   churners_capturados |   recall |   precision |   lift |   umbral_score |
|----------------:|--------------:|----------------------:|---------:|------------:|-------:|---------------:|
|            0.05 |           985 |                   969 |    0.115 |       0.984 |  2.308 |          0.88  |
|            0.1  |          1971 |                  1742 |    0.207 |       0.884 |  2.074 |          0.747 |
|            0.2  |          3942 |                  3055 |    0.364 |       0.775 |  1.818 |          0.616 |
|            0.3  |          5913 |                  4121 |    0.491 |       0.697 |  1.635 |          0.511 |
|            0.4  |          7884 |                  5038 |    0.6   |       0.639 |  1.499 |          0.441 |
|            0.5  |          9854 |                  5826 |    0.694 |       0.591 |  1.387 |          0.365 |

## Capacidad mensual absoluta: 3,000 contactos/mes → recall 65.2%, precisión 60.9% (3 meses de test)

## Lift por decil (LightGBM calibrado)

|   decil |    n |   churners |   p_medio |   tasa |   lift |   cum_churners |   cum_recall |   cum_n |   cum_precision |   cum_lift |
|--------:|-----:|-----------:|----------:|-------:|-------:|---------------:|-------------:|--------:|----------------:|-----------:|
|       1 | 1971 |       1742 |     0.888 |  0.884 |  2.074 |           1742 |        0.207 |    1971 |           0.884 |      2.074 |
|       2 | 1971 |       1313 |     0.685 |  0.666 |  1.563 |           3055 |        0.364 |    3942 |           0.775 |      1.818 |
|       3 | 1971 |       1066 |     0.543 |  0.541 |  1.269 |           4121 |        0.491 |    5913 |           0.697 |      1.635 |
|       4 | 1971 |        917 |     0.469 |  0.465 |  1.092 |           5038 |        0.6   |    7884 |           0.639 |      1.499 |
|       5 | 1971 |        788 |     0.402 |  0.4   |  0.938 |           5826 |        0.694 |    9855 |           0.591 |      1.387 |
|       6 | 1971 |        703 |     0.341 |  0.357 |  0.837 |           6529 |        0.777 |   11826 |           0.552 |      1.295 |
|       7 | 1971 |        585 |     0.292 |  0.297 |  0.696 |           7114 |        0.847 |   13797 |           0.516 |      1.21  |
|       8 | 1971 |        553 |     0.262 |  0.281 |  0.658 |           7667 |        0.913 |   15768 |           0.486 |      1.141 |
|       9 | 1971 |        459 |     0.213 |  0.233 |  0.546 |           8126 |        0.967 |   17739 |           0.458 |      1.075 |
|      10 | 1970 |        274 |     0.133 |  0.139 |  0.326 |           8400 |        1     |   19709 |           0.426 |      1     |

## Calibración (LightGBM calibrado)

|   bin |    n |   score_medio |   tasa_observada |   gap |
|------:|-----:|--------------:|-----------------:|------:|
|     0 | 1971 |         0.133 |            0.136 | 0.003 |
|     1 | 1971 |         0.213 |            0.236 | 0.024 |
|     2 | 1971 |         0.262 |            0.277 | 0.015 |
|     3 | 1971 |         0.292 |            0.306 | 0.015 |
|     4 | 1971 |         0.341 |            0.351 | 0.01  |
|     5 | 1970 |         0.402 |            0.401 | 0.001 |
|     6 | 1971 |         0.469 |            0.468 | 0.001 |
|     7 | 1971 |         0.543 |            0.542 | 0.001 |
|     8 | 1971 |         0.685 |            0.661 | 0.024 |
|     9 | 1971 |         0.888 |            0.883 | 0.005 |

## Segmentos en test

| segmento   |    n |   p_media |   tasa_churn |   churners |   share_churners |   share | accion                                                                                                                             |
|:-----------|-----:|----------:|-------------:|-----------:|-----------------:|--------:|:-----------------------------------------------------------------------------------------------------------------------------------|
| Alto       | 3941 |     0.787 |        0.775 |       3053 |            0.363 |     0.2 | Llamado del concesionario (asesor de service) dentro de las 48 h + oferta concreta (precio fijo / turno con retiro y entrega).     |
| Medio      | 5913 |     0.472 |        0.469 |       2772 |            0.33  |     0.3 | Recordatorio personalizado por FordPass/WhatsApp con turno sugerido y beneficio liviano; segundo toque a los 10 días si no agenda. |
| Bajo       | 9855 |     0.248 |        0.261 |       2575 |            0.307 |     0.5 | Recordatorio estándar automático (Service Reminder). No gastar capacidad de contacto humano.                                       |

## ROI por capacidad (supuestos: uplift 15%, valor USD 250, costo contacto USD 3.0; umbral rentable p ≥ 0.08)

|   capacidad_pct |   contactos |   churners_alcanzados_modelo |   churners_alcanzados_azar |   recall_modelo |   recall_azar |   services_recuperados_modelo |   services_recuperados_azar |   valor_modelo_usd |   valor_azar_usd |   costo_contacto_usd |   beneficio_neto_modelo_usd |   beneficio_neto_azar_usd |   ganancia_incremental_usd |   roi_modelo |
|----------------:|------------:|-----------------------------:|---------------------------:|----------------:|--------------:|------------------------------:|----------------------------:|-------------------:|-----------------:|---------------------:|----------------------------:|--------------------------:|---------------------------:|-------------:|
|             0.1 |        1971 |                         1742 |                        840 |            0.21 |           0.1 |                        261.3  |                      126.01 |              65325 |          31501.6 |                 5913 |                       59412 |                   25588.6 |                    33823.4 |        10.05 |
|             0.2 |        3942 |                         3055 |                       1680 |            0.36 |           0.2 |                        458.25 |                      252.01 |             114562 |          63003.2 |                11826 |                      102736 |                   51177.2 |                    51559.3 |         8.69 |
|             0.3 |        5913 |                         4121 |                       2520 |            0.49 |           0.3 |                        618.15 |                      378.02 |             154538 |          94504.8 |                17739 |                      136798 |                   76765.8 |                    60032.7 |         7.71 |
|             0.5 |        9854 |                         5826 |                       4200 |            0.69 |           0.5 |                        873.9  |                      629.97 |             218475 |         157492   |                29562 |                      188913 |                  127930   |                    60983   |         6.39 |

## Sensibilidad del ROI (capacidad = segmento Alto)

|   uplift |   valor_retencion_usd |   ganancia_incremental_usd |   beneficio_neto_modelo_usd |   roi_modelo |
|---------:|----------------------:|---------------------------:|----------------------------:|-------------:|
|     0.05 |                   100 |                       6875 |                        3449 |          0.3 |
|     0.05 |                   200 |                      13749 |                       18724 |          1.6 |
|     0.05 |                   300 |                      20624 |                       33999 |          2.9 |
|     0.05 |                   500 |                      34373 |                       64549 |          5.5 |
|     0.1  |                   100 |                      13749 |                       18724 |          1.6 |
|     0.1  |                   200 |                      27498 |                       49274 |          4.2 |
|     0.1  |                   300 |                      41247 |                       79824 |          6.7 |
|     0.1  |                   500 |                      68746 |                      140924 |         11.9 |
|     0.15 |                   100 |                      20624 |                       33999 |          2.9 |
|     0.15 |                   200 |                      41247 |                       79824 |          6.7 |
|     0.15 |                   300 |                      61871 |                      125649 |         10.6 |
|     0.15 |                   500 |                     103119 |                      217299 |         18.4 |
|     0.25 |                   100 |                      34373 |                       64549 |          5.5 |
|     0.25 |                   200 |                      68746 |                      140924 |         11.9 |
|     0.25 |                   300 |                     103119 |                      217299 |         18.4 |
|     0.25 |                   500 |                     171864 |                      370049 |         31.3 |

## Top 20 features (SHAP global)

| nombre                                           |   mean_abs_shap |
|:-------------------------------------------------|----------------:|
| versión (TMA)                                    |            7    |
| mantenimientos por año observados                |            4.72 |
| concesionario del último mantenimiento           |            4.59 |
| antigüedad del vehículo (días)                   |            4.26 |
| tamaño de flota (compras 2024-26)                |            3.29 |
| uso (km/día)                                     |            3.05 |
| meses de historia observable                     |            2.76 |
| km de atraso del último service vs. plan nominal |            2.69 |
| días entre los dos últimos mantenimientos        |            2.31 |
| visitas concluidas (cualquier tipo)              |            1.34 |
| provincia de venta                               |            1.19 |
| último intervalo en km relativo al plan          |            1.16 |
| generación (P375 / P703)                         |            1.03 |
| días desde la última encuesta                    |            0.91 |
| último km registrado                             |            0.85 |
| intervalo del plan (km) según generación         |            0.84 |
| región                                           |            0.84 |
| vehículos del cliente vistos en agenda           |            0.81 |
| intervalo medio entre mantenimientos             |            0.8  |
| días desde la última lectura de km               |            0.66 |

## Población actual scoreada: 30,504 vehículos (22,255 en ventana hoy, 8,249 entran en 30 días); 1,791 ya tienen turno agendado.

| segmento   |     n |
|:-----------|------:|
| Bajo       | 15252 |
| Medio      |  9152 |
| Alto       |  6100 |
