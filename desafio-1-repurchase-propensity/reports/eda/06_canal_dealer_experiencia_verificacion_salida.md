# Salida de la verificación del EDA 06

Script: `scripts/eda/06_canal_dealer_experiencia_verificacion.py`. CUTOFF = 2026-08-25.

## V1. Etiqueta aproximada y base

**Resumen de la base (recalculado con merge_asof)**

| index | valor |
|---|---|
| mant. completados en el período con vehicle_id nulo (excluidos) | 884 |
| % de esos sin ModelYear | 99.9 |
| turnos base | 109073 |
| vehículos distintos | 56826 |
| % retorno <=15 meses | 78.7 |
| % churn aprox. | 21.3 |
| % retorno exigiendo >=30 días | 78.5 |
| turnos con horizonte truncado por CUTOFF | 1702 |
| turnos con próximo mant. a <=1 día | 95 |
| mediana días al próximo mant. (si existe) | 171 |
Retorno por mes del turno base: mín 76.9 (2024-01), máx 80.2 (2024-11).

**Retorno a 15 meses según km/año aproximado (VehicleCurrentKM / edad desde garantía; edad >6 meses)**

| km_anio_bin | n | pct |
|---|---|---|
| <10k | 10020 | 62.7 |
| 10-20k | 28227 | 71.1 |
| 20-30k | 28139 | 80.4 |
| 30-50k | 24825 | 84.7 |
| 50k+ | 9639 | 87.7 |
| sin dato | 8223 | 89.9 |
IV de km_anio_bin sobre la base: 0.2273.

## V2. Verificación por fuerza bruta del historial (muestra aleatoria de 400 turnos base)
Discrepancias entre historial vectorizado y fuerza bruta (7 campos x 400 turnos): 0.

## V2b. Recencia e intensidad (sub-base ene–may 2025)
Sub-base: n=35248, retorno 78.1%.

**Días desde el turno previo (cualquier status)**

| rec | n | pct |
|---|---|---|
| <=30 | 5713 | 80.5 |
| 31-90 | 5526 | 85.9 |
| 91-180 | 9656 | 82.3 |
| 181-365 | 7071 | 71.8 |
| >365 | 884 | 50.6 |
| sin turno previo | 6398 | 73.5 |

**Días desde el mantenimiento completado previo**

| recm | n | pct |
|---|---|---|
| <=30 | 310 | 83.2 |
| 31-90 | 3787 | 88.8 |
| 91-180 | 10155 | 84.6 |
| 181-365 | 8332 | 74.4 |
| >365 | 1171 | 55.5 |
| sin mant. previo | 11493 | 73.7 |

**Mantenimientos previos**

| b_maint | n | pct |
|---|---|---|
| 0 | 11493 | 73.7 |
| 1 | 10130 | 75 |
| 2 | 6392 | 82 |
| 3+ | 7233 | 86.1 |

**Turnos previos**

| b_turnos | n | pct |
|---|---|---|
| 0 | 6398 | 73.5 |
| 1 | 6727 | 72.7 |
| 2 | 5849 | 77.1 |
| 3-4 | 8133 | 80.5 |
| 5+ | 8141 | 84.5 |
IV recencia (turno previo): 0.1471; IV recencia (mant. previo): 0.1797; IV mant. previos: 0.0922; IV turnos previos: 0.0711.

**Recencia × primer service (sub-base 2025)**

| primer | rec | n | pct |
|---|---|---|---|
| 1er service | 181-365 | 640 | 75.5 |
| 1er service | 31-90 | 607 | 86.2 |
| 1er service | 91-180 | 764 | 83.8 |
| 1er service | <=30 | 1399 | 84.3 |
| 1er service | >365 | 62 | 59.7 |
| 1er service | sin turno previo | 4720 | 83.1 |
| 2° o posterior | 181-365 | 6431 | 71.4 |
| 2° o posterior | 31-90 | 4919 | 85.9 |
| 2° o posterior | 91-180 | 8892 | 82.2 |
| 2° o posterior | <=30 | 4314 | 79.3 |
| 2° o posterior | >365 | 822 | 49.9 |
| 2° o posterior | sin turno previo | 1678 | 46.8 |
Turnos '>365' por mes del turno base: {'2025-01': 88, '2025-02': 148, '2025-03': 163, '2025-04': 233, '2025-05': 252}

**Días desde el último turno CONCLUIDO (sensibilidad: excluye cancelados/no-show)**

| recd | n | pct |
|---|---|---|
| <=30 | 1056 | 84.2 |
| 31-90 | 5494 | 87.5 |
| 91-180 | 11019 | 83.2 |
| 181-365 | 8409 | 72.6 |
| >365 | 1108 | 51.5 |
| sin turno previo | 8162 | 73.3 |
IV recencia (último concluido): 0.1909.

## V3. No-shows, cancelaciones y 'vehículo con problemas'
No-shows previos: 0: 78.0% (n 31051.0) / 1: 78.9% (n 3436.0) / 2+: 79.1% (n 761.0) — IV 0.0003
Cancelaciones reales previas: 0: 77.8% (n 29652.0) / 1: 79.4% (n 4546.0) / 2+: 81.5% (n 1050.0) — IV 0.0023
Reprogramaciones previas: 0: 76.8% (n 24628.0) / 1: 80.2% (n 6954.0) / 2+: 82.5% (n 3666.0) — IV 0.0144
Recalls previos: 0: 75.8% (n 27620.0) / 1: 85.3% (n 5088.0) / 2+: 88.3% (n 2540.0) — IV 0.0753
Reparaciones previas: 0: 77.6% (n 31669.0) / 1: 83.1% (n 3035.0) / 2+: 81.1% (n 544.0) — IV 0.0093
Diagnósticos previos: 0: 77.8% (n 26617.0) / 1: 78.8% (n 6087.0) / 2+: 79.4% (n 2544.0) — IV 0.001
Re-visitas previas: 0: 77.4% (n 30487.0) / 1: 82.2% (n 3428.0) / 2+: 83.9% (n 1333.0) — IV 0.0124

**Retorno según no-show previo DENTRO de cada nivel de turnos previos (sub-base 2025, >=1 turno previo)**

| b_turnos | ns_any | n | pct |
|---|---|---|---|
| 1 | con no-show previo | 294 | 67 |
| 1 | sin no-show previo | 6433 | 73 |
| 2 | con no-show previo | 485 | 72.8 |
| 2 | sin no-show previo | 5364 | 77.4 |
| 3-4 | con no-show previo | 1159 | 76.4 |
| 3-4 | sin no-show previo | 6974 | 81.1 |
| 5+ | con no-show previo | 2259 | 83 |
| 5+ | sin no-show previo | 5882 | 85 |

**Retorno según % de no-shows entre los turnos previos**

| ns_rate_bin | n | pct |
|---|---|---|
| 0% | 24653 | 79.1 |
| 1-20% | 1780 | 83.8 |
| 21-50% | 2034 | 76.6 |
| >50% | 383 | 68.1 |

**OR ajustados (n=35134): no-shows y cancelaciones reales previas controlando turnos previos, generación, año modelo y n° de service**

| index | OR |
|---|---|
| b_no_show_1 | 0.762 |
| b_no_show_2+ | 0.655 |
| b_cancel_true_1 | 0.764 |
| b_cancel_true_2+ | 0.72 |
| b_turnos_1 | 1.393 |
| b_turnos_2 | 1.948 |
| b_turnos_3-4 | 2.532 |
| b_turnos_5+ | 3.526 |
| gen_P703 | 2.371 |
| my_bin_2016-18 | 0.379 |
| my_bin_2019-21 | 0.535 |
| my_bin_2024 | 0.938 |
| my_bin_2025+ | 2.529 |
| my_bin_<=2015 | 0.243 |
| maint_bin_2 | 0.965 |
| maint_bin_3 | 0.953 |
| maint_bin_4-5 | 0.964 |
| maint_bin_6-8 | 1.218 |
| maint_bin_9+ | 1.279 |

**OR ajustados (n=35134): recalls y reparaciones previas controlando turnos previos, generación, año modelo y n° de service**

| index | OR |
|---|---|
| b_recall_1 | 1.05 |
| b_recall_2+ | 1.053 |
| b_repair_1 | 1.064 |
| b_repair_2+ | 0.816 |
| b_turnos_1 | 1.329 |
| b_turnos_2 | 1.785 |
| b_turnos_3-4 | 2.19 |
| b_turnos_5+ | 2.742 |
| gen_P703 | 2.325 |
| my_bin_2016-18 | 0.366 |
| my_bin_2019-21 | 0.527 |
| my_bin_2024 | 0.926 |
| my_bin_2025+ | 2.509 |
| my_bin_<=2015 | 0.234 |
| maint_bin_2 | 0.954 |
| maint_bin_3 | 0.953 |
| maint_bin_4-5 | 0.98 |
| maint_bin_6-8 | 1.259 |
| maint_bin_9+ | 1.336 |

**Modelo conjunto del historial (n=35134): OR de cada feature controlando por todas las demás + generación, año modelo y n° de service**

| index | OR |
|---|---|
| b_no_show_1 | 0.733 |
| b_no_show_2+ | 0.625 |
| b_cancel_true_1 | 0.749 |
| b_cancel_true_2+ | 0.704 |
| b_cancel_resched_1 | 0.809 |
| b_cancel_resched_2+ | 0.76 |
| b_recall_1 | 0.955 |
| b_recall_2+ | 0.975 |
| b_repair_1 | 0.973 |
| b_repair_2+ | 0.776 |
| b_diag_1 | 0.862 |
| b_diag_2+ | 0.752 |
| b_return_visit_1 | 0.958 |
| b_return_visit_2+ | 1.003 |
| b_turnos_1 | 1 |
| b_turnos_2 | 1.316 |
| b_turnos_3-4 | 1.723 |
| b_turnos_5+ | 2.7 |
| rec_181-365 | 0.746 |
| rec_31-90 | 1.143 |
| rec_<=30 | 0.908 |
| rec_>365 | 0.403 |
| rec_sin turno previo | 0.531 |

**Mismo modelo SIN turnos previos ni recencia (n=35134): muestra cuánto del efecto crudo es intensidad de contacto**

| index | OR |
|---|---|
| b_no_show_1 | 0.956 |
| b_no_show_2+ | 0.831 |
| b_cancel_true_1 | 0.989 |
| b_cancel_true_2+ | 0.995 |
| b_cancel_resched_1 | 1.155 |
| b_cancel_resched_2+ | 1.223 |
| b_recall_1 | 1.258 |
| b_recall_2+ | 1.433 |
| b_repair_1 | 1.247 |
| b_repair_2+ | 0.982 |
| b_diag_1 | 1.044 |
| b_diag_2+ | 1.049 |
| b_return_visit_1 | 1.167 |
| b_return_visit_2+ | 1.089 |
Entre los turnos base con no-show previo (n=4197), días desde el último no-show: mediana 169, p25 61, p75 293; % a <=30 días: 16.6.

## V4. Canal de agendado

**Retorno por fuente del turno base**

| ScheduleSource | n | pct |
|---|---|---|
| Dealer | 80316 | 77.2 |
| FordPass | 23187 | 83.8 |
| WEB | 3809 | 80.2 |
| Mobile | 1751 | 75.8 |
| CAF | 10 | 80 |

**FordPass − Dealer dentro de generación × año modelo (celdas n>=200)**

| gen | my_bin | Dealer | FordPass | dif_pp | n_FordPass |
|---|---|---|---|---|---|
| P375 | 2016-18 | 57.3 | 62.3 | 5 | 1129 |
| P375 | 2019-21 | 71 | 74 | 3 | 3267 |
| P375 | 2022-23 | 80.9 | 85 | 4.1 | 7539 |
| P375 | <=2015 | 46.3 | 54.4 | 8.1 | 228 |
| P703 | 2024 | 85.5 | 88.4 | 2.9 | 10235 |
| P703 | 2025+ | 90.8 | 93.1 | 2.3 | 786 |
Diferencia FordPass−Dealer ponderada por n FordPass del estrato: 3.4 pp (cruda: 6.6 pp).

**OR fuente (n=108731) controlando gen, año modelo, n° de service — réplica**

| index | OR |
|---|---|
| ScheduleSource_FordPass | 1.293 |
| ScheduleSource_Mobile | 0.957 |
| ScheduleSource_WEB | 1.059 |

**OR fuente (n=108731) agregando efecto fijo por DEALER**

| index | OR |
|---|---|
| ScheduleSource_FordPass | 1.346 |
| ScheduleSource_Mobile | 0.981 |
| ScheduleSource_WEB | 1.098 |

**OR fuente en la sub-base 2025 (n=35132) agregando turnos previos y recencia**

| index | OR |
|---|---|
| ScheduleSource_FordPass | 1.285 |
| ScheduleSource_Mobile | 0.987 |
| ScheduleSource_WEB | 1.139 |

**OR fuente en la sub-base 2025 (n=35132) con turnos previos, recencia y efecto fijo por dealer**

| index | OR |
|---|---|
| ScheduleSource_FordPass | 1.311 |
| ScheduleSource_Mobile | 1.053 |
| ScheduleSource_WEB | 1.169 |
IV ScheduleSource (base): 0.0284.
% FordPass ene-24: 9.6; ago-26: 25.5.
FordPass como % de turnos base: P703 34.1, P375 15.9.

**No-show / reprogramación / cancelación real por fuente (turnos resueltos)**

| ScheduleSource | n | no_show | reprog | cancel_real |
|---|---|---|---|---|
| CAF | 1199 | 10.4 | 16.8 | 13.4 |
| Dealer | 353253 | 6.2 | 11.6 | 6.2 |
| FordPass | 102390 | 3.9 | 19.6 | 7.9 |
| Mobile | 9843 | 4.6 | 19.2 | 8 |
| WEB | 19474 | 4.4 | 27.4 | 6.5 |

## V5. Dealer
Dealers con >=100 turnos base en 2024 y 2025: 86. Pearson 0.679, Spearman 0.791.
Vehículos de la base 2025 que también están en la base 2024: 65.6%.
Vehículos DISJUNTOS (2025 sin turno base en 2024): 79 dealers (n24>=100, n25>=50); Pearson 0.641, Spearman 0.683.
Split-half por vehículo dentro de 2024 (87 dealers con >=50 en cada mitad): Pearson 0.756.
Dealers n_base>=100: 90. SD observado 5.6 pp; SD binomial esperado 1.5 pp; ratio 3.71. p10/p50/p90 del retorno: 70.6/78.7/83.8.
Residuo obs − esperado por mix (gen × año modelo × n° service), dealers n>=100: p10 -6.2, p90 5.2, SD 5.0 pp (vs SD crudo 5.6 pp).
Pearson share P703 vs retorno (dealers n>=100): -0.047.
Residuos ajustados por mix, 2024 vs 2025 (86 dealers): Pearson 0.559, Spearman 0.713.

**TE 2024 → 2025, quintiles calculados sobre TURNOS de 2025 (réplica del original)**

| q_turno | n | pct |
|---|---|---|
| Q1 | 8188 | 73.3 |
| Q2 | 5956 | 73.8 |
| Q3 | 7055 | 78.5 |
| Q4 | 6812 | 81.7 |
| Q5 | 6844 | 83.8 |
| sin dato | 393 | 73.8 |

**TE 2024 → 2025, quintiles calculados sobre DEALERS (cada quintil = ~17 dealers)**

| q_dealer | n | pct |
|---|---|---|
| Q1 | 5296 | 71.4 |
| Q2 | 8469 | 74.8 |
| Q3 | 7949 | 78.4 |
| Q4 | 5427 | 81.5 |
| Q5 | 7714 | 83.8 |
| sin dato | 393 | 73.8 |
IV TE por turno: 0.0605; IV TE por dealer: 0.0637.

**Quintil TE 2024 (por turno) en 2025: observado vs esperado por mix del propio quintil**

| q_turno | n | obs | esp | resid_pp |
|---|---|---|---|---|
| Q1 | 8188 | 73.3 | 77.3 | -4 |
| Q2 | 5956 | 73.8 | 77.6 | -3.8 |
| Q3 | 7055 | 78.5 | 78.3 | 0.2 |
| Q4 | 6812 | 81.7 | 77.9 | 3.8 |
| Q5 | 6844 | 83.8 | 79.1 | 4.7 |

**OR del quintil TE 2024 en 2025 controlando gen, año modelo y n° de service (n=34742, ref Q3)**

| index | OR |
|---|---|
| q_turno_Q1 | 0.777 |
| q_turno_Q2 | 0.793 |
| q_turno_Q4 | 1.274 |
| q_turno_Q5 | 1.4 |
Retornos: 85821 (= suma de ret, sin duplicar por merge); próximo mantenimiento en el mismo dealer: 90.7%.
Dealers: 95; top-10 = 28.4%; top-20 = 44.4%; dealer #1 = 4.2% (20515); Gini (fórmula estándar) 0.369.

**Mayores caídas 2024→2025 (dealers n>=100 ambos años)**

| dealer_id | size_2024 | size_2025 | cambio_pp |
|---|---|---|---|
| 5804ce1783a5 | 373 | 183 | -28.3 |
| 290e545b87fd | 178 | 112 | -23.7 |
| 2f5474c47f98 | 504 | 271 | -7.3 |

## V6. ConnectedStatusARG
Vehículos con >1 valor: 74 de 111752.

**Retorno y % con algún turno posterior por conectividad**

| ConnectedStatusARG | n | retorno | turno_posterior | turno_posterior_sin_reservas_futuras |
|---|---|---|---|---|
| Conectado | 26877 | 87.2 | 95.6 | 95.6 |
| No Conectado | 70332 | 79.3 | 90.6 | 90.5 |
| No tiene Conectividad | 8940 | 64.9 | 76.4 | 76.3 |
| Sin Información de Conectividad | 2924 | 27 | 41.4 | 41.3 |

**% con algún turno posterior por conectividad × año del turno base**

| ConnectedStatusARG | 2024 % | 2025 % | 2024 n | 2025 n |
|---|---|---|---|---|
| Conectado | 96 | 95.2 | 14155 | 12722 |
| No Conectado | 93.1 | 84 | 50543 | 19789 |
| No tiene Conectividad | 70.4 | 92 | 6478 | 2462 |
| Sin Información de Conectividad | 40.4 | 50.9 | 2649 | 275 |

**P703 año modelo 2024: retorno por conectividad**

| ConnectedStatusARG | n | pct |
|---|---|---|
| Conectado | 24731 | 87.5 |
| No Conectado | 518 | 86.5 |
| No tiene Conectividad | 4523 | 85.4 |
| Sin Información de Conectividad | 383 | 35 |

**OR dentro de P703 (n=32258), ref Conectado, control año modelo**

| index | OR |
|---|---|
| ConnectedStatusARG_No Conectado | 0.896 |
| ConnectedStatusARG_No tiene Conectividad | 0.815 |
| ConnectedStatusARG_Sin Información de Conectividad | 0.081 |
'No tiene Conectividad' en P375: n=3968, retorno 38.9%.
IV ConnectedStatusARG: 0.3144; IV año modelo (my_bin): 0.2938; IV gen: 0.1137.

**Participación de 'Sin Información' por trimestre del turno base**

| event_date | % Sin Información |
|---|---|
| 2024Q1 | 5.1 |
| 2024Q2 | 4.3 |
| 2024Q3 | 3.7 |
| 2024Q4 | 1.7 |
| 2025Q1 | 0.9 |
| 2025Q2 | 0.6 |
- Conectado: distribución del ÚLTIMO evento del vehículo por trimestre: {'2024Q1': 0.3, '2024Q2': 0.5, '2024Q3': 1.1, '2024Q4': 1.6, '2025Q1': 2.4, '2025Q2': 3.4, '2025Q3': 4.9, '2025Q4': 9.6, '2026Q1': 17.4, '2026Q2': 29.9, '2026Q3': 29.0, '2026Q4': 0.0}
- No Conectado: distribución del ÚLTIMO evento del vehículo por trimestre: {'2024Q1': 1.2, '2024Q2': 1.3, '2024Q3': 1.9, '2024Q4': 4.6, '2025Q1': 8.4, '2025Q2': 8.7, '2025Q3': 8.1, '2025Q4': 10.2, '2026Q1': 14.9, '2026Q2': 21.3, '2026Q3': 19.3, '2026Q4': 0.0}
- No tiene Conectividad: distribución del ÚLTIMO evento del vehículo por trimestre: {'2024Q1': 8.0, '2024Q2': 10.5, '2024Q3': 15.5, '2024Q4': 8.3, '2025Q1': 2.7, '2025Q2': 2.8, '2025Q3': 3.6, '2025Q4': 6.3, '2026Q1': 9.4, '2026Q2': 15.5, '2026Q3': 17.6}
- Sin Información de Conectividad: distribución del ÚLTIMO evento del vehículo por trimestre: {'2024Q1': 16.8, '2024Q2': 19.3, '2024Q3': 26.5, '2024Q4': 14.6, '2025Q1': 7.1, '2025Q2': 2.2, '2025Q3': 2.1, '2025Q4': 2.6, '2026Q1': 3.2, '2026Q2': 3.0, '2026Q3': 2.7}

**Proxy de transferencia por conectividad**

| ConnectedStatusARG | % vehículos con >1 customer_id en la agenda |
|---|---|
| Conectado | 37.2 |
| No Conectado | 33.6 |
| No tiene Conectividad | 28.9 |
| Sin Información de Conectividad | 10.9 |

## V7. SurveyStarRating
Turnos con encuesta: 36920 (7.5% de 492442). % antes de ScheduleDate: 100.0; mismo día: 0.0; después: 0.0. p5/mediana/p95: -26/-8/-2.
Respecto del check-in (cuando existe, n=24839): % antes 99.9, % mismo día 0.0, % después 0.0.
5 estrellas: 84.0%.

**Tasa de respuesta por fuente**

| ScheduleSource | n | pct |
|---|---|---|
| CAF | 1201 | 0 |
| Dealer | 355273 | 0 |
| FordPass | 102691 | 29.1 |
| Mobile | 9881 | 30.9 |
| WEB | 19570 | 17.9 |

**Retorno por rating**

| sg | n | pct |
|---|---|---|
| 1-2 | 233 | 80.3 |
| 3 | 369 | 80.2 |
| 4 | 1149 | 81.6 |
| 5 | 8341 | 83.1 |
| sin respuesta | 98981 | 78.3 |

**Solo canales digitales: respondió vs no, por generación**

| gen | resp | n | pct |
|---|---|---|---|
| P375 | no respondió | 10756 | 79 |
| P375 | respondió | 5545 | 77.5 |
| P703 | no respondió | 7897 | 88.3 |
| P703 | respondió | 4545 | 89.2 |
IV survey_grp: 0.0066.

## V8. Semántica de IsReschedule y ScheduleReturn
Cancelados: 101222; con IsReschedule=Y: 68783 (68.0%).

**Cancelados según IsReschedule (vehículo identificado)**

| grupo | n | % turno siguiente <=30d | mediana días al siguiente | % turno (anterior o siguiente) a <=30d | % sin ningún otro turno | % turno siguiente concluido |
|---|---|---|---|---|---|---|
| Cancelado IsReschedule=Y | 68782 | 71.9 | 6 | 99 | 0 | 59.8 |
| Cancelado IsReschedule=N | 32439 | 44.5 | 21 | 69.7 | 5.8 | 51.7 |
Concluidos con IsReschedule=Y: 45665; % con turno previo cancelado: 67.0; mediana días desde previo: 7.

**ScheduleReturn (toda la agenda)**

| ScheduleReturn | n | mediana días desde previo | p90 | % previo concluido | % mant. | % diag | % repar. | % sin turno previo |
|---|---|---|---|---|---|---|---|---|
| Y | 35172 | 15 | 27 | 74.8 | 14.1 | 37.4 | 30.4 | 1.3 |
| N | 345471 | 93 | 274 | 49.5 | 66.3 | 20.7 | 7.8 | 26.7 |

## V9. Conveniencia y atributos del turno base
PUD: False: 78.6% (n 105580.0) / True: 80.0% (n 3493.0) — IV 0.0002
Móvil: False: 78.7% (n 107667.0) / True: 78.3% (n 1406.0) — IV 0.0
Esperó: N: 78.7% (n 108160.0) / Y: 77.4% (n 913.0) — IV 0.0
Remolque: N: 77.6% (n 89543.0) / Y: 66.7% (n 45.0) / sin dato: 83.5% (n 19485.0) — IV 0.0194
Precio fijo: False: 77.9% (n 84993.0) / True: 81.5% (n 24080.0) — IV 0.0086
Diagnóstico: False: 78.9% (n 104676.0) / True: 72.8% (n 4397.0) — IV 0.0048
Recall: False: 77.9% (n 87847.0) / True: 82.0% (n 21226.0) — IV 0.0097
Zona: 1: 73.7% (n 10499.0) / 2: 79.8% (n 22759.0) / 3: 79.2% (n 22139.0) / 4: 80.0% (n 30484.0) / 5: 77.7% (n 23192.0) — IV 0.0112
DaysInDealer: 0: 79.9% (n 55957.0) / 1: 77.4% (n 17112.0) / 15-30: 76.6% (n 4102.0) / 2-3: 77.8% (n 12006.0) / 31+: 76.0% (n 1565.0) / 4-7: 77.5% (n 11686.0) / 8-14: 77.6% (n 6567.0) / <0: 73.1% (n 78.0) — IV 0.0056

**Diagnóstico en el turno base, dentro de cada generación**

| gen | has_diag | n | pct |
|---|---|---|---|
| Otro | False | 279 | 54.5 |
| Otro | True | 11 | 45.5 |
| P375 | False | 73186 | 75.6 |
| P375 | True | 3297 | 69.2 |
| P703 | False | 31211 | 86.9 |
| P703 | True | 1089 | 83.9 |
OR has_diag ajustado por gen/año modelo/n° service: 0.818 (n=108741).

**OR DaysInDealer (ref 0 días) ajustado por gen/año modelo/n° service (n=108741)**

| index | OR |
|---|---|
| days_bin_1 | 0.862 |
| days_bin_15-30 | 0.81 |
| days_bin_2-3 | 0.869 |
| days_bin_31+ | 0.773 |
| days_bin_4-7 | 0.861 |
| days_bin_8-14 | 0.843 |
| days_bin_<0 | 0.94 |

**% nulo de NeededTowing y ScheduleReturn por fuente (base)**

| ScheduleSource | NeededTowing | ScheduleReturn |
|---|---|---|
| CAF | 0 | 0 |
| Dealer | 0 | 0 |
| FordPass | 68.7 | 27.9 |
| Mobile | 65.7 | 23.5 |
| WEB | 62.7 | 28.6 |

## V10. Estacionalidad y tendencia
Agosto 2026, ScheduleDate < 2026-09-01 (como el script original): turnos 15293; (30) Agendado 2240; (40) En progreso 1045; (70) Cancelado 3200; resueltos 12008; reprogramación 20.3%; cancel. real 6.4%; no-show 4.6%; concluido 66.2%.
Agosto 2026, ScheduleDate <= CUTOFF (25/8/2026): turnos 13034; (30) Agendado 337; (40) En progreso 1040; (70) Cancelado 2849; resueltos 11657; reprogramación 18.5%; cancel. real 6.0%; no-show 4.7%; concluido 68.2%.
Turnos totales ene-24: 13857; mar-26: 18593; jul-26: 16807.
Mant. completados ene-24: 6396; ene-26: 8925.
No-show: ene-24 6.9 → jul-26 4.8 → ago-26 4.7. Reprogramación: ene-24 10.7 → jul-26 17.3 → ago-26 18.5. Cancelación real: mín 5.7 (2025-12), máx 8.0 (2024-01).
Check-in nulo entre concluidos: ene-24 29.4, oct-24 20.4, nov-24 13.1, dic-24 10.7, 2025 rango 6.5–11.8, 2026 rango 5.7–9.2.
Concluido por año: {2024: 71.2, 2025: 70.7, 2026: 69.3}.

**Turnos con ScheduleDate > CUTOFF**

| ym | (30) Agendado | (40) En progreso | (70) Cancelado |
|---|---|---|---|
| 2026-08 | 1903 | 5 | 351 |
| 2026-09 | 1386 | 2 | 146 |
| 2026-10 | 22 | 0 | 1 |
| 2026-11 | 9 | 0 | 0 |
| 2026-12 | 1 | 0 | 0 |
Retorno por mes calendario: mín 77.9 máx 80.2.