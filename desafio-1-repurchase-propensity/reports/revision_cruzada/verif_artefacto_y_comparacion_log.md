# Verificación bloque 'artefacto_y_comparacion' (docs/04 §2.2 y §4)

## A. Artefacto de calendario en el test de astra (`test_predicciones.parquet`)

Filas: 23,740; meses: ['2026-04', '2026-05', '2026-06', '2026-07']; target nulo: 0; duplicados (vehicle_id, scoring_date): 0
Vencimientos con hora no-medianoche: 74.6%. Rango de días al vencimiento (truncado): 0..30; |dias − dias_al_vencimiento de astra| máx = 1.000 (la columna de astra es float; truncar no cambia el orden entre días distintos)

Churn por posición del vencimiento en el mes (días desde el 1°; '0' = vence el 1°):

| bucket   |   ventanas |   churn |   score_medio |
|:---------|-----------:|--------:|--------------:|
| 0-5      |       4102 |  0.7557 |        0.779  |
| 6-10     |       3818 |  0.7559 |        0.7803 |
| 11-15    |       3828 |  0.7803 |        0.783  |
| 16-20    |       3711 |  0.7747 |        0.7816 |
| 21-25    |       4228 |  0.8065 |        0.807  |
| 26-31    |       4053 |  0.8167 |        0.811  |

Misma tabla por DÍA DEL MES del vencimiento (1 = primer día):

| dom   |   size |   mean |
|:------|-------:|-------:|
| 1-5   |   3446 | 0.7528 |
| 6-10  |   3685 | 0.7593 |
| 11-15 |   3806 | 0.7717 |
| 16-20 |   3712 | 0.7761 |
| 21-25 |   4188 | 0.7997 |
| 26-31 |   4903 | 0.8177 |

Churn por bucket y mes de scoring:

| scoring_date   |   0-5 |   6-10 |   11-15 |   16-20 |   21-25 |   26-31 |
|:---------------|------:|-------:|--------:|--------:|--------:|--------:|
| 2026-04        | 0.747 |  0.741 |   0.779 |   0.762 |   0.804 |   0.824 |
| 2026-05        | 0.786 |  0.773 |   0.786 |   0.791 |   0.814 |   0.818 |
| 2026-06        | 0.732 |  0.76  |   0.788 |   0.769 |   0.807 |   0.836 |
| 2026-07        | 0.76  |  0.752 |   0.767 |   0.776 |   0.801 |   0.797 |

ROC-AUC modelo astra: 0.6733 (astra reporta 0,6733). ROC-AUC 'días al vencimiento' (entero): 0.5383; con la columna float de astra: 0.5385.
Spearman(score, días entero): 0.0936; Spearman(score, días float de astra): 0.0917.
ROC-AUC de la regla de calendario por mes: {'2026-04': 0.543, '2026-05': 0.527, '2026-06': 0.554, '2026-07': 0.529}

Lift@10 % regla de calendario: global/arbitrario (script 01) 1.0534; por mes/arbitrario 1.0526; por mes/valor esperado 1.0522; por mes con la columna float de astra (sin empates) 1.0580.
Lift@10 % modelo astra: por mes 1.2016 (astra reporta 1,2016); global 1.2005.
  2026-04: k=575, umbral=27 días, estrictamente arriba 522, empatados 221
  2026-05: k=600, umbral=28 días, estrictamente arriba 461, empatados 237
  2026-06: k=572, umbral=26 días, estrictamente arriba 564, empatados 242
  2026-07: k=630, umbral=28 días, estrictamente arriba 527, empatados 234

ROC-AUC del modelo de astra DENTRO de cada bucket de calendario (si fuera calendario puro, caería a 0,5): {'0-5': 0.69, '6-10': 0.68, '11-15': 0.686, '16-20': 0.66, '21-25': 0.657, '26-31': 0.642}

## B. Comparación con la misma etiqueta mensual

Particiones de astra (src/modeling.py::split_name aplicado a su ventanas.parquet):

| split       |     n | desde               | hasta               |   con_label |
|:------------|------:|:--------------------|:--------------------|------------:|
| calibration | 11874 | 2026-01-01 00:00:00 | 2026-02-01 00:00:00 |       11848 |
| demo        |  6285 | 2026-08-01 00:00:00 | 2026-08-01 00:00:00 |           0 |
| embargo     | 17589 | 2025-09-01 00:00:00 | 2026-03-01 00:00:00 |       17562 |
| test        | 23763 | 2026-04-01 00:00:00 | 2026-07-01 00:00:00 |       23740 |
| train       | 61885 | 2024-07-01 00:00:00 | 2025-08-01 00:00:00 |       61846 |
| valid       | 11473 | 2025-10-01 00:00:00 | 2025-11-01 00:00:00 |       11459 |

Astra: LightGBM_31 (300 árboles fijos) ajustado en train jul-24..ago-25; selección por AP en oct-nov 25; calibración sigmoide en ene-feb 26; sep-25, dic-25 y mar-26 en embargo; test abr-jul 26 con capacidad 10 % por mes (ceil).

Informe 02 (artefactos guardados): split {'train_end': '2025-11-30', 'valid_end': '2026-03-31'}, n_train 100,296 (churn 0.788), n_valid 24,783, n_test 25,612, best_iteration 209, features 86, test ['2026-04-01', '2026-07-01']
Test guardado: n=25,612, churn 0.7964, ROC-AUC (cal) 0.7295, ROC-AUC (raw) 0.7306, AP (cal) 0.9072
Valores distintos de p_lgbm_cal (isotónica): 95 de 25,612; de p_lgbm_raw: 24,388
  2026-04: n=6259, k=626, umbral p_cal=0.9181, estrictamente arriba 624, empatados en el umbral 484
  2026-05: n=6339, k=634, umbral p_cal=0.9536, estrictamente arriba 518, empatados en el umbral 138
  2026-06: n=6357, k=636, umbral p_cal=0.9625, estrictamente arriba 572, empatados en el umbral 129
  2026-07: n=6657, k=666, umbral p_cal=1.0000, estrictamente arriba 0, empatados en el umbral 722
Lift@10 % por mes de fable (informe 02 = 1,240): desempate arbitrario 1.2399; desempate por score crudo 1.2404; valor esperado 1.2403; ordenando por score crudo 1.2404. Lift@20 %: arbitrario 1.2002, esperado 1.2002.

Ventanas evaluables reconstruidas: 150,691; churn 0.7893 (informe 02: 150.691 / 0,789)
Ventanas donde el vehículo volvió justo el 1° del mes: fable las excluye como 'preempted' (826); astra las contaría como retorno. Diferencia de población menor.
Split de fable: train 2024-01-01..2025-11-01 (n=100,296, horizonte máx 2025-11-30); valid 2025-12-01..2026-03-01 (n=24,783, horizonte máx 2026-03-31); test 2026-04-01..2026-07-01 (n=25,612)
Sin solapamiento de horizontes entre train/valid/test (el horizonte mensual cierra antes del siguiente scoring). Asimetría: fable entrena con scoring ene-24..nov-25 (incluye 2024-H1 y sep-nov 25) y usa dic-25..mar-26 para early stopping + isotónica; astra entrena sólo jul-24..ago-25. Fable usa 3 meses más recientes de entrenamiento y 6 más antiguos.
Features: 104 columnas; todas las 'days_since_*' son > 0 (as-of estricto). Test n=25,612

Re-entrenando (1) split del informe 02 ...
Re-entrenando (2) período de astra: train jul-24..ago-25; valid = oct-nov 25 + ene-feb 26 (early stopping + isotónica); sin 2024-H1 ni meses de embargo ...
Re-entrenando (3) período de astra y sin features que astra eligió no usar (dealer, TMA, encuestas, zona) ...

Resultados en el test abr-jul 2026 (población mensual de fable, capacidad 10 % por mes):

| corrida                                            |   n_train |   best_iter |   n_test |   roc_auc |     ap |   lift10_arb |   lift10_esp |   lift10_raw |   lift20_esp |
|:---------------------------------------------------|----------:|------------:|---------:|----------:|-------:|-------------:|-------------:|-------------:|-------------:|
| (1) fable, split del informe 02 (train ≤ nov-25)   |    100296 |         209 |    25612 |    0.7295 | 0.9072 |       1.2399 |       1.2403 |       1.2404 |       1.2002 |
| (2) fable, período de astra (train jul-24..ago-25) |     69727 |         204 |    25612 |    0.7216 | 0.9049 |       1.2355 |       1.2353 |       1.2355 |       1.1931 |
| (3) = (2) sin dealer/TMA/zona/región/encuestas     |     69727 |         199 |    25612 |    0.7046 | 0.8889 |       1.1816 |       1.1812 |       1.1836 |       1.165  |

Reproducibilidad del informe 02 (0,730 / 1,240): corrida (1) da ROC-AUC 0.7295 y lift arbitrario 1.2399. Correlación de Spearman entre el score guardado del informe 02 y el re-entrenado: 1.0000

Top-12 features por ganancia (corrida 1): maint_per_year_observed (20.8%), last_maint_dealer (9.7%), days_since_last_survey (7.9%), last_maint_km_vs_plan (6.2%), last_interval_days (4.4%), vehicle_age_days (3.9%), km_rate_per_day (2.8%), last_maint_km (2.6%), km_expected_at_scoring (2.6%), days_since_last_km (2.4%), mean_interval_days (2.2%), days_anchor_to_due (2.1%)
Peso de 'days_to_due_at_scoring' (= el artefacto de calendario, que astra también tiene como dias_al_vencimiento): 1.6% de la ganancia.

### B.5 Vehículos-mes comunes (merge 1:1 por vehicle_id + scoring_date): 9,322 (informe 02: 9.322)
Cobertura: 39.3% del test de astra (23,740) y 36.4% del test mensual de fable (25,612). Vehículos del test de astra que fable scorea en abr-jul pero en OTRO mes: 6,501. Formato de id: astra strip() + string; fable string sin strip: longitud única [16] vs [16].
Etiquetas coinciden: 96.59% (informe 02: 96,6 %). Con la etiqueta por VIN de astra (target_vin): 99.31%. Churn en comunes: fable 0.727, astra 0.761.
Tipo de ancla en el test de fable, comunes vs no comunes:
| comun   |   maintenance |   warranty |
|:--------|--------------:|-----------:|
| False   |         0.709 |      0.291 |
| True    |         0.996 |      0.004 |

Cara a cara en los comunes, score del informe 02:

|                             |   roc_auc |   lift10_arb |   lift10_esp |   lift10_raw |
|:----------------------------|----------:|-------------:|-------------:|-------------:|
| ('fable', 'etiqueta fable') |    0.6893 |       1.2695 |       1.2704 |       1.271  |
| ('fable', 'etiqueta astra') |    0.6839 |       1.2421 |       1.2428 |       1.2421 |
| ('astra', 'etiqueta fable') |    0.6461 |       1.2504 |       1.2504 |       1.2504 |
| ('astra', 'etiqueta astra') |    0.6587 |       1.2365 |       1.2365 |       1.2365 |
Spearman entre scores (fable crudo vs astra): 0.6844 (informe 02: 0,684 con el score isotónico).
ROC-AUC de fable (informe 02) en comunes 0.6893 vs en NO comunes 0.7323 (n=16,290, churn 0.836); churn de astra en sus NO comunes: 0.796. El 0,730 global y el 0,673 de astra están medidos sobre poblaciones distintas; la comparación limpia es la de los comunes.

Cara a cara en los comunes (n=9,322), fable re-entrenado (2) período de astra:

|                             |   roc_auc |   lift10_arb |   lift10_esp |   lift10_raw |
|:----------------------------|----------:|-------------:|-------------:|-------------:|
| ('fable', 'etiqueta fable') |    0.6783 |       1.2769 |       1.2751 |       1.2828 |
| ('fable', 'etiqueta astra') |    0.6753 |       1.2506 |       1.2483 |       1.252  |
| ('astra', 'etiqueta fable') |    0.6461 |       1.2504 |       1.2504 |       1.2504 |
| ('astra', 'etiqueta astra') |    0.6587 |       1.2365 |       1.2365 |       1.2365 |

Cara a cara en los comunes (n=9,322), fable re-entrenado (3) período de astra sin dealer/TMA/encuestas:

|                             |   roc_auc |   lift10_arb |   lift10_esp |   lift10_raw |
|:----------------------------|----------:|-------------:|-------------:|-------------:|
| ('fable', 'etiqueta fable') |    0.6653 |       1.2577 |       1.2611 |       1.2607 |
| ('fable', 'etiqueta astra') |    0.6616 |       1.2323 |       1.2341 |       1.2379 |
| ('astra', 'etiqueta fable') |    0.6461 |       1.2504 |       1.2504 |       1.2504 |
| ('astra', 'etiqueta astra') |    0.6587 |       1.2365 |       1.2365 |       1.2365 |

Bootstrap por cliente (300 réplicas, 8,640 clientes) de la diferencia fable − astra en los comunes (IC 95 %): ΔAUC etiqueta fable [+0.033, +0.054]; ΔAUC etiqueta astra [+0.015, +0.037]; Δlift@10 % etiqueta fable [-0.007, +0.050]; Δlift@10 % etiqueta astra [-0.013, +0.025].