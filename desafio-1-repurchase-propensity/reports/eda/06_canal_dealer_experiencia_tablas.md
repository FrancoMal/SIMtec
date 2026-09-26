# Apéndice de tablas — EDA 06 (canal, dealer, conectividad y experiencia)

Generado automáticamente por `scripts/eda/06_canal_dealer_experiencia.py`. Todas las cifras del informe `reports/eda/06_canal_dealer_experiencia.md` salen de acá. Decimales con coma; n con punto de miles.

## 1. Base y etiqueta aproximada de retorno

**Resumen de la base y la etiqueta**
| index | valor |
|---|---|
| turnos de mant. completado 2024-01→2025-05 con vehicle_id NULO (excluidos de la base) | 884 |
| % de esos excluidos con ModelYear también nulo | 99,9 |
| % de mantenimientos completados (todo el período) sin EffectiveCheckinDate | 11,8 |
| turnos base (mant. completado 2024-01→2025-05, vehículo identificado) | 109.073 |
| vehículos distintos en la base | 56.826 |
| % retorno (<=15 meses) | 78,7 |
| % no retorno (churn aprox.) | 21,3 |
| % retorno exigiendo >=30 días al próximo mantenimiento | 78,5 |
| turnos con horizonte truncado por CUTOFF (hasta 6 días) | 1.702 |
| turnos cuyo próximo mant. está a <=1 día | 95 |
| turnos cuyo próximo mant. está a <30 días | 984 |
| mediana de días al próximo mantenimiento (si existe) | 171 |

**Estabilidad de la etiqueta por mes del turno base**
| event_date | n | retorno_pct |
|---|---|---|
| 2024-01 | 6.320 | 76,9 |
| 2024-02 | 5.508 | 78,5 |
| 2024-03 | 5.702 | 78,5 |
| 2024-04 | 5.732 | 79,3 |
| 2024-05 | 5.920 | 79,7 |
| 2024-06 | 4.839 | 80,0 |
| 2024-07 | 6.357 | 79,0 |
| 2024-08 | 6.638 | 79,0 |
| 2024-09 | 6.549 | 78,6 |
| 2024-10 | 6.952 | 79,2 |
| 2024-11 | 6.613 | 80,2 |
| 2024-12 | 6.695 | 78,7 |
| 2025-01 | 7.694 | 78,8 |
| 2025-02 | 6.799 | 77,4 |
| 2025-03 | 6.486 | 77,5 |
| 2025-04 | 7.055 | 78,7 |
| 2025-05 | 7.214 | 78,0 |

**Retorno a 15 meses según km/año aproximado del vehículo (VehicleCurrentKM / edad desde garantía): la etiqueta a horizonte fijo premia el alto uso**
| km_anio_bin | n | retorno_pct | lift | dif_pp |
|---|---|---|---|---|
| <10k | 10.020 | 62,7 | 0,796 | -16,0 |
| 10-20k | 28.227 | 71,1 | 0,903 | -7,6 |
| 20-30k | 28.139 | 80,4 | 1,022 | 1,7 |
| 30-50k | 24.825 | 84,7 | 1,076 | 6 |
| 50k+ | 9.639 | 87,7 | 1,114 | 9 |
| sin dato | 8.223 | 89,9 | 1,142 | 11,2 |
IV de km/año (bins) sobre la base: 0,227 — mayor que cualquier feature de este tema.

## 2. Confusores estructurales (generación, año modelo, n° de service) — no son de este tema, se usan como control

**Retorno por generación**
| gen | n | retorno_pct | lift | dif_pp |
|---|---|---|---|---|
| Otro/Raptor | 290 | 54,1 | 0,688 | -24,5 |
| P375 | 76.483 | 75,3 | 0,958 | -3,3 |
| P703 | 32.300 | 86,8 | 1,103 | 8,1 |

**Retorno por año modelo (bins)**
| my_bin | n | retorno_pct | lift | dif_pp |
|---|---|---|---|---|
| <=2015 | 2.381 | 46,7 | 0,594 | -31,9 |
| 2016-18 | 8.327 | 57,8 | 0,735 | -20,9 |
| 2019-21 | 19.990 | 71,5 | 0,909 | -7,2 |
| 2022-23 | 45.785 | 81,7 | 1,038 | 3 |
| 2024 | 30.155 | 86,5 | 1,1 | 7,8 |
| 2025+ | 2.103 | 92,0 | 1,169 | 13,3 |
| sin dato | 332 | 50,9 | 0,647 | -27,8 |

**Retorno por generación × año modelo (% y n)**
| gen | 2016-18 % | 2019-21 % | 2022-23 % | 2024 % | 2025+ % | <=2015 % | sin dato % | 2016-18 n | 2019-21 n | 2022-23 n | 2024 n | 2025+ n | <=2015 n | sin dato n |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Otro/Raptor | s/d | s/d | s/d | s/d | s/d | s/d | 54,1 | s/d | s/d | s/d | s/d | s/d | s/d | 290 |
| P375 | 57,8 | 71,5 | 81,7 | s/d | s/d | 46,7 | s/d | 8.327 | 19.990 | 45.785 | s/d | s/d | 2.381 | s/d |
| P703 | s/d | s/d | s/d | 86,5 | 92,0 | s/d | s/d | s/d | s/d | s/d | 30.155 | 2.103 | s/d | s/d |

**Retorno por número de service del turno base**
| maint_bin | n | retorno_pct | lift | dif_pp |
|---|---|---|---|---|
| 1 | 23.469 | 82,9 | 1,054 | 4,3 |
| 2 | 13.999 | 82,7 | 1,052 | 4,1 |
| 3 | 10.954 | 80,9 | 1,028 | 2,2 |
| 4-5 | 17.476 | 77,0 | 0,979 | -1,6 |
| 6-8 | 19.158 | 77,0 | 0,979 | -1,6 |
| 9+ | 24.017 | 73,6 | 0,936 | -5,1 |

## 3. (a) ScheduleSource — canal de agendado

**Mix de fuente por año (% de turnos con ScheduleDate <= CUTOFF; 2026 hasta el 25/8)**
| year | CAF | Dealer | FordPass | Mobile | WEB | turnos |
|---|---|---|---|---|---|---|
| 2024 | 0,3 | 80,7 | 15,0 | 1 | 3 | 162.404 |
| 2025 | 0,3 | 71,2 | 22,7 | 1,9 | 3,9 | 194.098 |
| 2026 | 0,1 | 65,2 | 25,8 | 3,5 | 5,4 | 132.114 |

**Patrón de nulos por fuente en la base: los 'sin dato' de varias columnas son un artefacto del canal, no una señal**
| ScheduleSource | n | NeededTowing % nulo | ScheduleReturn % nulo | IsReschedule % nulo | EffectiveCheckinDate % nulo | SurveyStarRating % nulo |
|---|---|---|---|---|---|---|
| CAF | 10 | 0 | 0 | 90,0 | 30,0 | 100,0 |
| Dealer | 80.316 | 0 | 0 | 88,6 | 18,5 | 100,0 |
| FordPass | 23.187 | 68,7 | 27,9 | 84,6 | 12,7 | 62,7 |
| Mobile | 1.751 | 65,7 | 23,5 | 86,5 | 13,2 | 65,9 |
| WEB | 3.809 | 62,7 | 28,6 | 76,7 | 19,2 | 77,6 |

**Nulos de NeededTowing y ScheduleReturn por año del turno base**
| event_date | NeededTowing % nulo | ScheduleReturn % nulo |
|---|---|---|
| 2024 | 15,8 | 10,8 |
| 2025 | 22,1 | 0 |

**Resultado del turno por fuente (% sobre turnos resueltos: 60/70/80/90). cancel_real = (70) con IsReschedule=N; cancel_reprog = (70) con IsReschedule=Y**
| ScheduleSource | n | concluido | concluido_sin_os | no_show | cancel_real | cancel_reprog |
|---|---|---|---|---|---|---|
| CAF | 1.199 | 53,0 | 6,3 | 10,4 | 13,4 | 16,8 |
| Dealer | 353.253 | 72,3 | 3,7 | 6,2 | 6,2 | 11,6 |
| FordPass | 102.390 | 66,6 | 2 | 3,9 | 7,9 | 19,6 |
| Mobile | 9.843 | 66,5 | 1,7 | 4,6 | 8 | 19,2 |
| WEB | 19.474 | 60,5 | 1,2 | 4,4 | 6,5 | 27,4 |

**Retorno según la fuente del turno base (último mantenimiento)**
| ScheduleSource | n | retorno_pct | lift | dif_pp |
|---|---|---|---|---|
| Dealer | 80.316 | 77,2 | 0,981 | -1,5 |
| FordPass | 23.187 | 83,8 | 1,065 | 5,1 |
| WEB | 3.809 | 80,2 | 1,019 | 1,5 |
| Mobile | 1.751 | 75,8 | 0,964 | -2,8 |
| CAF | 10 | 80,0 | 1,017 | 1,3 |

**Composición de fuente dentro de cada generación en la base (% columna)**
| ScheduleSource | Otro/Raptor | P375 | P703 |
|---|---|---|---|
| CAF | 0 | 0 | 0 |
| Dealer | 98,6 | 78,7 | 61,5 |
| FordPass | 1 | 15,9 | 34,1 |
| Mobile | 0,3 | 1,7 | 1,4 |
| WEB | 0 | 3,7 | 3 |

**Retorno por fuente dentro de cada generación**
| gen | Dealer % | FordPass % | Mobile % | WEB % | Dealer n | FordPass n | Mobile n | WEB n |
|---|---|---|---|---|---|---|---|---|
| Otro/Raptor | 54,5 | s/d | s/d | s/d | 286 | s/d | s/d | s/d |
| P375 | 74,5 | 79,3 | 72,5 | 77,5 | 60.181 | 12.163 | 1.297 | 2.841 |
| P703 | 85,7 | 88,8 | 85,7 | 88,0 | 19.849 | 11.021 | 453 | 968 |

**Retorno por fuente dentro de generación × año modelo (celdas n>=200)**
| gen | my_bin | Dealer % | FordPass % | WEB % | Mobile % | Dealer n | FordPass n | WEB n | Mobile n |
|---|---|---|---|---|---|---|---|---|---|
| P375 | 2016-18 | 57,3 | 62,3 | 53,6 | s/d | 6.812 | 1.129 | 220 | s/d |
| P375 | 2019-21 | 71,0 | 74,0 | 70,8 | 69,8 | 15.738 | 3.267 | 627 | 358 |
| P375 | 2022-23 | 80,9 | 85,0 | 83,4 | 80,0 | 35.575 | 7.539 | 1.931 | 739 |
| P375 | <=2015 | 46,3 | 54,4 | s/d | s/d | 2.056 | 228 | s/d | s/d |
| P703 | 2024 | 85,5 | 88,4 | 87,4 | 84,3 | 18.600 | 10.235 | 897 | 414 |
| P703 | 2025+ | 90,8 | 93,1 | s/d | s/d | 1.207 | 786 | s/d | s/d |

**Odds ratios ajustados (logística sin penalización, n=108.731): fuente controlando generación, año modelo y n° de service**
| index | OR ajustado |
|---|---|
| ScheduleSource=FordPass (ref Dealer) | 1,293 |
| ScheduleSource=Mobile (ref Dealer) | 0,957 |
| ScheduleSource=WEB (ref Dealer) | 1,059 |
| gen=P703 (ref P375) | 1,97 |
| my_bin=2016-18 (ref 2022-23) | 0,218 |
| my_bin=2019-21 (ref 2022-23) | 0,436 |
| my_bin=2024 (ref 2022-23) | 1,022 |
| my_bin=2025+ (ref 2022-23) | 1,928 |
| my_bin=<=2015 (ref 2022-23) | 0,136 |
| maint_bin=2 (ref 1) | 1,286 |
| maint_bin=3 (ref 1) | 1,509 |
| maint_bin=4-5 (ref 1) | 1,539 |
| maint_bin=6-8 (ref 1) | 2,166 |
| maint_bin=9+ (ref 1) | 2,607 |

**Retorno según si el turno base fue por canal digital (FordPass/WEB/Mobile)**
| digital | n | retorno_pct | lift | dif_pp |
|---|---|---|---|---|
| no | 80.326 | 77,2 | 0,981 | -1,5 |
| sí | 28.747 | 82,8 | 1,053 | 4,2 |
IV de ScheduleSource sobre la base: 0,028.

## 4. (b) ConnectedStatusARG — conectividad (snapshot)
Vehículos con más de un valor de ConnectedStatusARG a lo largo de sus turnos: 74 de 111.752 → la columna es un snapshot a la fecha de extracción, no un estado histórico.

**Turnos por conectividad × generación (toda la agenda)**
| ConnectedStatusARG | Otro/Raptor | P375 | P703 |
|---|---|---|---|
| Conectado | 0 | 1.824 | 187.362 |
| No Conectado | 829 | 231.709 | 3.058 |
| No tiene Conectividad | 0 | 7.733 | 36.655 |
| Sin Información de Conectividad | 2.547 | 6.073 | 14.652 |

**Retorno por conectividad (base)**
| ConnectedStatusARG | n | retorno_pct | lift | dif_pp |
|---|---|---|---|---|
| Conectado | 26.877 | 87,2 | 1,109 | 8,5 |
| No Conectado | 70.332 | 79,3 | 1,008 | 0,6 |
| No tiene Conectividad | 8.940 | 64,9 | 0,825 | -13,7 |
| Sin Información de Conectividad | 2.924 | 27,0 | 0,343 | -51,7 |

**Retorno por conectividad dentro de cada generación**
| gen | Conectado % | No Conectado % | No tiene Conectividad % | Sin Información de Conectividad % | Conectado n | No Conectado n | No tiene Conectividad n | Sin Información de Conectividad n |
|---|---|---|---|---|---|---|---|---|
| P375 | 54,4 | 79,3 | 38,9 | 24,1 | 542 | 69.659 | 3.968 | 2.314 |
| P703 | 87,9 | 86,0 | 85,7 | 36,6 | 26.335 | 542 | 4.972 | 451 |

**Retorno por conectividad dentro de generación × año modelo (celdas n>=200)**
| gen | my_bin | Conectado % | No Conectado % | No tiene Conectividad % | Sin Información de Conectividad % | Conectado n | No Conectado n | No tiene Conectividad n | Sin Información de Conectividad n |
|---|---|---|---|---|---|---|---|---|---|
| P375 | 2016-18 | s/d | 58,4 | s/d | s/d | s/d | 8.212 | s/d | s/d |
| P375 | 2019-21 | s/d | 75,4 | 34,0 | 19,7 | s/d | 18.351 | 909 | 630 |
| P375 | 2022-23 | 60,5 | 87,1 | 40,4 | 26,8 | 438 | 40.753 | 3.059 | 1.535 |
| P375 | <=2015 | s/d | 47,2 | s/d | s/d | s/d | 2.343 | s/d | s/d |
| P703 | 2024 | 87,5 | 86,5 | 85,4 | 35,0 | 24.731 | 518 | 4.523 | 383 |
| P703 | 2025+ | 93,4 | s/d | 89,1 | s/d | 1.604 | s/d | 449 | s/d |

**Diagnóstico de 'Sin Información': % con algún turno posterior (cualquier status), % customer_id nulo, año modelo mediano**
| ConnectedStatusARG | n | retorno | algun_turno_posterior | customer_null | anio_modelo_mediana |
|---|---|---|---|---|---|
| Conectado | 26.877 | 87,2 | 95,6 | 1,1 | 2.024 |
| No Conectado | 70.332 | 79,3 | 90,6 | 1,9 | 2.022 |
| No tiene Conectividad | 8.940 | 64,9 | 76,4 | 2,6 | 2.024 |
| Sin Información de Conectividad | 2.924 | 27,0 | 41,4 | 2,6 | 2.022 |

**Odds ratios ajustados de conectividad DENTRO de P703 (n=32.258), ref Conectado, controlando año modelo**
| index | OR ajustado |
|---|---|
| ConnectedStatusARG=No Conectado (ref Conectado) | 0,896 |
| ConnectedStatusARG=No tiene Conectividad (ref Conectado) | 0,815 |
| ConnectedStatusARG=Sin Información de Conectividad (ref Conectado) | 0,081 |
| my_bin=2025+ (ref 2024) | 1,849 |

**Odds ratios ajustados de conectividad DENTRO de P375 (n=76.483), ref No Conectado, controlando año modelo**
| index | OR ajustado |
|---|---|
| ConnectedStatusARG=Conectado (ref No Conectado) | 0,21 |
| ConnectedStatusARG=No tiene Conectividad (ref No Conectado) | 0,113 |
| ConnectedStatusARG=Sin Información de Conectividad (ref No Conectado) | 0,062 |
| my_bin=2016-18 (ref 2022-23) | 0,214 |
| my_bin=2019-21 (ref 2022-23) | 0,474 |
| my_bin=<=2015 (ref 2022-23) | 0,136 |

## 5. (c) SurveyStarRating — encuesta

**Timing de la respuesta a la encuesta respecto de la fecha del turno**
| index | valor |
|---|---|
| turnos con encuesta respondida | 36.920 |
| % respondida ANTES de ScheduleDate | 100,0 |
| % respondida el mismo día | 0 |
| % respondida DESPUÉS | 0 |
| p5 de (respuesta − ScheduleDate) en días | -26,0 |
| mediana | -8 |
| p95 | -2 |

**Distribución del rating (todos los turnos)**
| SurveyStarRating | turnos |
|---|---|
| sin respuesta | 455.522 |
| 5 | 31.014 |
| 4 | 3.736 |
| 3 | 1.309 |
| 1 | 532 |
| 2 | 329 |

**Tasa de respuesta a la encuesta por fuente (todos los turnos <= CUTOFF)**
| ScheduleSource | n | respondio_pct |
|---|---|---|
| CAF | 1.201 | 0 |
| Dealer | 355.273 | 0 |
| FordPass | 102.691 | 29,1 |
| Mobile | 9.881 | 30,9 |
| WEB | 19.570 | 17,9 |

**Tasa de respuesta por status del turno**
| StatusARG | n | respondio_pct |
|---|---|---|
| (30) Agendado | 3.953 | 10,0 |
| (40) En progreso | 1.832 | 3,6 |
| (60) Concluido | 342.691 | 7,6 |
| (70) Cancelado | 101.222 | 8,3 |
| (80) No asistio | 27.237 | 4,9 |
| (90) Concluido sin OS | 15.507 | 4,4 |

**Retorno por grupo de rating del turno base**
| survey_grp | n | retorno_pct | lift | dif_pp |
|---|---|---|---|---|
| 1-2 | 233 | 80,3 | 1,02 | 1,6 |
| 3 | 369 | 80,2 | 1,02 | 1,5 |
| 4 | 1.149 | 81,6 | 1,038 | 3 |
| 5 | 8.341 | 83,1 | 1,056 | 4,4 |
| sin respuesta | 98.981 | 78,3 | 0,995 | -0,4 |

**Retorno por rating dentro de cada generación**
| gen | sin respuesta % | 3 % | 4 % | 5 % | sin respuesta n | 3 n | 4 n | 5 n |
|---|---|---|---|---|---|---|---|---|
| Otro/Raptor | 54,5 | s/d | s/d | s/d | 288 | s/d | s/d | s/d |
| P375 | 75,2 | 74,6 | 77,7 | 77,6 | 70.938 | 240 | 687 | 4.460 |
| P703 | 86,4 | s/d | 87,4 | 89,4 | 27.755 | s/d | 462 | 3.879 |

**Sesgo de respuesta: % que respondió por generación × fuente (base, celdas n>=200)**
| gen | ScheduleSource | n | respondio_pct |
|---|---|---|---|
| Otro/Raptor | Dealer | 286 | 0 |
| P375 | Dealer | 60.181 | 0 |
| P375 | FordPass | 12.163 | 37,2 |
| P375 | Mobile | 1.297 | 33,8 |
| P375 | WEB | 2.841 | 20,4 |
| P703 | Dealer | 19.849 | 0 |
| P703 | FordPass | 11.021 | 37,3 |
| P703 | Mobile | 453 | 34,9 |
| P703 | WEB | 968 | 28,4 |

**Solo turnos base por canal digital (donde la encuesta existe): retorno según respondió o no, por generación**
| gen | no respondió % | respondió % | no respondió n | respondió n |
|---|---|---|---|---|
| P375 | 79,0 | 77,5 | 10.756 | 5.545 |
| P703 | 88,3 | 89,2 | 7.897 | 4.545 |

**Solo turnos base por canal digital: retorno por rating, por generación**
| gen | 1-2 % | 3 % | 4 % | 5 % | sin respuesta % | 1-2 n | 3 n | 4 n | 5 n | sin respuesta n |
|---|---|---|---|---|---|---|---|---|---|---|
| P375 | 78,5 | 74,6 | 77,7 | 77,6 | 79,0 | 158 | 240 | 687 | 4.460 | 10.756 |
| P703 | s/d | 90,7 | 87,4 | 89,4 | 88,3 | s/d | 129 | 462 | 3.879 | 7.897 |
IV de survey_grp sobre la base: 0,007.

## 6. (d) Dealer
Dealers con turnos resueltos: 95; con >=100 turnos base: 90.

**Dispersión entre dealers de las tasas (dealers con >=300 turnos resueltos)**
| index | dealers | p10 % | p50 % | p90 % |
|---|---|---|---|---|
| concluido | 92 | 60,3 | 71,8 | 78,2 |
| no_show | 92 | 0,4 | 4,5 | 8,9 |
| cancel_real | 92 | 4,6 | 6,4 | 10,2 |
| cancel_reprog | 92 | 8,8 | 12,8 | 19,7 |
| retorno (n_base>=100) | 90 | 70,6 | 78,7 | 83,8 |

**Concentración del volumen de turnos resueltos por dealer**
| index | valor |
|---|---|
| % turnos en el top-10 dealers | 28,4 |
| % turnos en el top-20 | 44,4 |
| % turnos del dealer #1 | 4,2 |
| Gini del volumen | 0,369 |
| turnos del dealer #1 | 20.515 |
| mediana de turnos por dealer | 4.152 |

**Validación fuera de tiempo del efecto dealer: retorno en ene–may 2025 según quintil de retorno del dealer en 2024 (IV=0,06)**
| dealer_te_2024 | n | retorno_pct | lift | dif_pp |
|---|---|---|---|---|
| Q1 (peor 2024) | 8.188 | 73,3 | 0,939 | -4,8 |
| Q2 | 5.956 | 73,8 | 0,946 | -4,3 |
| Q3 | 7.055 | 78,5 | 1,005 | 0,4 |
| Q4 | 6.812 | 81,7 | 1,046 | 3,6 |
| Q5 (mejor 2024) | 6.844 | 83,8 | 1,073 | 5,7 |
| sin dato | 393 | 73,8 | 0,945 | -4,3 |

**Estabilidad y señal del efecto dealer**
| index | valor |
|---|---|
| dealers con >=100 turnos base en 2024 y en 2025 | 86 |
| Pearson r (retorno 2024 vs 2025) | 0,679 |
| Spearman rho | 0,791 |
| desvío estándar observado entre dealers (pp) | 5,6 |
| desvío esperado por ruido binomial (pp) | 1,5 |
| ratio observado/esperado | 3,71 |
| Pearson r entre share P703 del dealer y su retorno | -0,159 |
| p10 del residuo (obs − esperado por mix gen×año) en pp | -7,9 |
| p90 del residuo en pp | 5,2 |

**5 dealers con menor y 5 con mayor retorno (n_base>=100); resid_pp = retorno − esperado por mix**
| dealer_id | n_turnos | concluido | no_show | cancel_real | cancel_reprog | share_p703 | n_base | retorno | resid_pp |
|---|---|---|---|---|---|---|---|---|---|
| 290e545b87fd | 1.744 | 74,7 | 4,5 | 5,5 | 10,7 | 36,8 | 290 | 58,3 | -14,5 |
| 5bbb50452413 | 4.330 | 74,4 | 1,1 | 9,7 | 13,6 | 55,5 | 1.049 | 59,3 | -21,1 |
| cd11e823c9f0 | 3.574 | 72,7 | 0 | 9,7 | 13,6 | 40,9 | 392 | 67,3 | -11,7 |
| 2ab8929e93b8 | 4.077 | 55,3 | 7,6 | 9,1 | 21,4 | 45,0 | 557 | 67,7 | -11,9 |
| 238795dfe563 | 2.235 | 64,0 | 10,2 | 7,5 | 14,8 | 51,0 | 432 | 69,0 | -7,9 |
| d858835341e1 | 6.329 | 71,6 | 6 | 6 | 16,0 | 39,4 | 1.831 | 85,8 | 7 |
| a0072a835607 | 5.859 | 80,7 | 3 | 2,6 | 13,3 | 42,3 | 1.808 | 86,2 | 8,1 |
| 56f10f15b980 | 6.948 | 79,4 | 2,5 | 5,7 | 10,5 | 42,1 | 2.062 | 86,6 | 7,2 |
| bd95dd740930 | 6.635 | 83,8 | 0,9 | 5,3 | 9,1 | 36,6 | 1.936 | 86,9 | 8,5 |
| 620515200d35 | 405 | 80,2 | 0 | 12,8 | 5,7 | 21,0 | 223 | 87,9 | 8,3 |

**Mayores caídas y subas interanuales de retorno por dealer (2024 → ene–may 2025, dealers con n>=100 en ambos años)**
| dealer_id | n_2024 | n_2025 | retorno_2024_pct | retorno_2025_pct | cambio_pp |
|---|---|---|---|---|---|
| 5804ce1783a5 | 373 | 183 | 79,6 | 51,4 | -28,3 |
| 290e545b87fd | 178 | 112 | 67,4 | 43,8 | -23,7 |
| 2f5474c47f98 | 504 | 271 | 77,8 | 70,5 | -7,3 |
| 0c1bf3af713d | 221 | 106 | 63,3 | 84,0 | 20,6 |
| 74604146c437 | 442 | 254 | 80,5 | 87,0 | 6,5 |
| 1e7c64319c85 | 1.512 | 711 | 75,2 | 80,7 | 5,5 |
Entre los turnos base que retornan, el próximo mantenimiento se hace en el MISMO dealer en el 90,7% de los casos (n=85.821).
IV de dealer_id (dealers con n_base>=100, 90 categorías): 0,08. Ojo: el IV de una variable de alta cardinalidad está inflado por el n de categorías.

## 7. (e) Conveniencia y atributos del turno base

**Semántica empírica de ScheduleReturn (toda la agenda): Y = re-visita a pocos días de otro turno, mayormente diagnóstico/reparación**
| flag | n | mediana días desde turno previo | p90 días desde turno previo | % turno previo concluido | % incluye mantenimiento | % incluye diagnóstico | % incluye reparación |
|---|---|---|---|---|---|---|---|
| ScheduleReturn=Y | 35.172 | 15,0 | 27,0 | 74,8 | 14,1 | 37,4 | 30,4 |
| ScheduleReturn=N | 345.471 | 93,0 | 274,0 | 49,5 | 66,3 | 20,7 | 7,8 |

**Semántica empírica de IsReschedule (toda la agenda): (70) con Y = reprogramación (se re-agenda enseguida); (60) con Y = turno nacido de una reprogramación**
| grupo | n | % con turno siguiente a <=30 días | mediana días al turno siguiente | % turno previo cancelado | mediana días desde turno previo |
|---|---|---|---|---|---|
| Cancelado con IsReschedule=Y | 68.783 | 71,9 | 6 | 21,3 | 12,0 |
| Cancelado con IsReschedule=N | 32.439 | 44,5 | 21,0 | 21,7 | 21,0 |
| Concluido con IsReschedule=Y | 45.665 | 49,7 | 14,0 | 67,0 | 7 |
| Concluido con IsReschedule nulo | 297.026 | 15,1 | 99,0 | 9,2 | 95,0 |

**Retorno por categoría — conveniencia y atributos del turno base**
| categoria | feature | n | retorno_pct | lift | dif_pp |
|---|---|---|---|---|---|
| no | Pick-up & delivery en el turno | 105.580 | 78,6 | 0,999 | -0 |
| sí | Pick-up & delivery en el turno | 3.493 | 80,0 | 1,016 | 1,3 |
| no | Servicio móvil en el turno | 107.667 | 78,7 | 1 | 0 |
| sí | Servicio móvil en el turno | 1.406 | 78,3 | 0,995 | -0,4 |
| Y | Cliente esperó en el dealer | 913 | 77,4 | 0,984 | -1,2 |
| N | Cliente esperó en el dealer | 108.160 | 78,7 | 1 | 0 |
| Y | Necesitó remolque | 45 | 66,7 | 0,847 | -12,0 |
| N | Necesitó remolque | 89.543 | 77,6 | 0,987 | -1 |
| sin dato | Necesitó remolque | 19.485 | 83,5 | 1,061 | 4,8 |
| no | Algún ítem con precio fijo Ford | 84.993 | 77,9 | 0,99 | -0,8 |
| sí | Algún ítem con precio fijo Ford | 24.080 | 81,5 | 1,036 | 2,9 |
| Y | Turno reprogramado (IsReschedule) | 13.815 | 79,7 | 1,014 | 1,1 |
| sin dato | Turno reprogramado (IsReschedule) | 95.258 | 78,5 | 0,998 | -0,2 |
| Y | Re-visita (ScheduleReturn) | 2.049 | 84,0 | 1,068 | 5,4 |
| N | Re-visita (ScheduleReturn) | 99.040 | 78,2 | 0,994 | -0,5 |
| sin dato | Re-visita (ScheduleReturn) | 7.984 | 83,5 | 1,061 | 4,8 |
| <0 | DaysInDealer (días en el taller) | 78 | 73,1 | 0,929 | -5,6 |
| 0 | DaysInDealer (días en el taller) | 55.957 | 79,9 | 1,015 | 1,2 |
| 1 | DaysInDealer (días en el taller) | 17.112 | 77,4 | 0,984 | -1,2 |
| 2-3 | DaysInDealer (días en el taller) | 12.006 | 77,8 | 0,988 | -0,9 |
| 4-7 | DaysInDealer (días en el taller) | 11.686 | 77,5 | 0,985 | -1,2 |
| 8-14 | DaysInDealer (días en el taller) | 6.567 | 77,6 | 0,986 | -1,1 |
| 15-30 | DaysInDealer (días en el taller) | 4.102 | 76,6 | 0,974 | -2,1 |
| 31+ | DaysInDealer (días en el taller) | 1.565 | 76,0 | 0,966 | -2,7 |
| <0 | WorkDaysInDealer (días hábiles) | 78 | 73,1 | 0,929 | -5,6 |
| 0 | WorkDaysInDealer (días hábiles) | 57.340 | 79,9 | 1,015 | 1,2 |
| 1 | WorkDaysInDealer (días hábiles) | 19.654 | 77,5 | 0,985 | -1,2 |
| 2-3 | WorkDaysInDealer (días hábiles) | 14.037 | 77,7 | 0,987 | -1 |
| 4-7 | WorkDaysInDealer (días hábiles) | 9.258 | 77,2 | 0,981 | -1,5 |
| 8-14 | WorkDaysInDealer (días hábiles) | 5.380 | 77,0 | 0,979 | -1,7 |
| 15-30 | WorkDaysInDealer (días hábiles) | 2.363 | 77,1 | 0,98 | -1,5 |
| 31+ | WorkDaysInDealer (días hábiles) | 963 | 75,2 | 0,956 | -3,5 |
| 60 min | Duración máx. del ítem (ServiceDuration) | 92.675 | 79,0 | 1,004 | 0,3 |
| 80 min | Duración máx. del ítem (ServiceDuration) | 1.784 | 78,7 | 1 | 0 |
| 100 min | Duración máx. del ítem (ServiceDuration) | 543 | 78,6 | 0,999 | -0 |
| 120 min | Duración máx. del ítem (ServiceDuration) | 14.071 | 76,4 | 0,971 | -2,3 |
| 1 | Cantidad de ítems del turno | 78.198 | 78,0 | 0,992 | -0,6 |
| 2 | Cantidad de ítems del turno | 27.701 | 80,6 | 1,024 | 1,9 |
| 3+ | Cantidad de ítems del turno | 3.174 | 78,2 | 0,993 | -0,5 |
| no | Turno incluye diagnóstico | 104.676 | 78,9 | 1,003 | 0,2 |
| sí | Turno incluye diagnóstico | 4.397 | 72,8 | 0,925 | -5,9 |
| no | Turno incluye reparación | 108.250 | 78,7 | 1 | -0 |
| sí | Turno incluye reparación | 823 | 79,6 | 1,011 | 0,9 |
| no | Turno incluye campaña/recall | 87.847 | 77,9 | 0,99 | -0,8 |
| sí | Turno incluye campaña/recall | 21.226 | 82,0 | 1,042 | 3,3 |
| no | Turno incluye garantía | 108.731 | 78,7 | 1 | -0 |
| sí | Turno incluye garantía | 342 | 82,7 | 1,052 | 4,1 |
| 00 | Region | 17.315 | 79,5 | 1,01 | 0,8 |
| 31 | Region | 1.808 | 86,2 | 1,095 | 7,5 |
| 60 | Region | 89.950 | 78,4 | 0,996 | -0,3 |
| 1 | DealerStateOrZone | 10.499 | 73,7 | 0,937 | -4,9 |
| 2 | DealerStateOrZone | 22.759 | 79,8 | 1,014 | 1,1 |
| 3 | DealerStateOrZone | 22.139 | 79,2 | 1,006 | 0,5 |
| 4 | DealerStateOrZone | 30.484 | 80,0 | 1,016 | 1,3 |
| 5 | DealerStateOrZone | 23.192 | 77,7 | 0,988 | -1 |

## 8. (f) Historia de comportamiento previa al turno base
El historial arranca el 2024-01-01 (truncamiento a izquierda): un turno base de marzo 2024 tiene 2 meses de historia observable y uno de mayo 2025, 16. Por eso las tablas de esta sección usan la sub-base con event_date >= 2025-01-01 (>=12 meses de lookback); se reporta también la base completa como contraste.
Sub-base con >=12 meses de historia: n=35.248, retorno 78,1%.

**Retorno por historial previo (sub-base >=12 meses de lookback; últimas 2 columnas: base completa)**
| categoria | feature | n | retorno_pct | lift | dif_pp | n_base_completa | retorno_pct_base_completa |
|---|---|---|---|---|---|---|---|
| 0 | N° no-shows previos | 31.051 | 78,0 | 0,999 | -0,1 | 99.834 | 78,6 |
| 1 | N° no-shows previos | 3.436 | 78,9 | 1,01 | 0,8 | 7.767 | 79,4 |
| 2+ | N° no-shows previos | 761 | 79,1 | 1,013 | 1 | 1.472 | 81,2 |
| 0 | N° cancelaciones reales previas (IsReschedule=N) | 29.652 | 77,8 | 0,996 | -0,3 | 97.029 | 78,3 |
| 1 | N° cancelaciones reales previas (IsReschedule=N) | 4.546 | 79,4 | 1,017 | 1,3 | 10.154 | 81,3 |
| 2+ | N° cancelaciones reales previas (IsReschedule=N) | 1.050 | 81,5 | 1,044 | 3,4 | 1.890 | 82,3 |
| 0 | N° reprogramaciones previas (cancelado con IsReschedule=Y) | 24.628 | 76,8 | 0,984 | -1,3 | 84.896 | 77,8 |
| 1 | N° reprogramaciones previas (cancelado con IsReschedule=Y) | 6.954 | 80,2 | 1,027 | 2,1 | 17.099 | 81,0 |
| 2+ | N° reprogramaciones previas (cancelado con IsReschedule=Y) | 3.666 | 82,5 | 1,057 | 4,4 | 7.078 | 83,6 |
| 0 | N° diagnósticos concluidos previos | 26.617 | 77,8 | 0,996 | -0,3 | 90.458 | 78,2 |
| 1 | N° diagnósticos concluidos previos | 6.087 | 78,8 | 1,009 | 0,7 | 13.724 | 81,0 |
| 2+ | N° diagnósticos concluidos previos | 2.544 | 79,4 | 1,017 | 1,3 | 4.891 | 80,1 |
| 0 | N° reparaciones concluidas previas | 31.669 | 77,6 | 0,993 | -0,5 | 104.521 | 78,5 |
| 1 | N° reparaciones concluidas previas | 3.035 | 83,1 | 1,064 | 5 | 3.930 | 84,0 |
| 2+ | N° reparaciones concluidas previas | 544 | 81,1 | 1,038 | 3 | 622 | 81,4 |
| 0 | N° campañas/recalls concluidos previos | 27.620 | 75,8 | 0,971 | -2,3 | 97.574 | 77,8 |
| 1 | N° campañas/recalls concluidos previos | 5.088 | 85,3 | 1,093 | 7,2 | 8.172 | 85,6 |
| 2+ | N° campañas/recalls concluidos previos | 2.540 | 88,3 | 1,131 | 10,2 | 3.327 | 88,6 |
| 0 | N° re-visitas previas (ScheduleReturn=Y) | 30.487 | 77,4 | 0,991 | -0,7 | 99.882 | 78,2 |
| 1 | N° re-visitas previas (ScheduleReturn=Y) | 3.428 | 82,2 | 1,052 | 4,1 | 6.846 | 84,0 |
| 2+ | N° re-visitas previas (ScheduleReturn=Y) | 1.333 | 83,9 | 1,075 | 5,9 | 2.345 | 84,5 |
| 0 | N° mantenimientos completados previos (desde 2024-01) | 11.493 | 73,7 | 0,943 | -4,4 | 56.826 | 74,6 |
| 1 | N° mantenimientos completados previos (desde 2024-01) | 10.130 | 75,0 | 0,96 | -3,1 | 28.056 | 80,7 |
| 2 | N° mantenimientos completados previos (desde 2024-01) | 6.392 | 82,0 | 1,05 | 3,9 | 13.057 | 84,9 |
| 3+ | N° mantenimientos completados previos (desde 2024-01) | 7.233 | 86,1 | 1,102 | 8 | 11.134 | 87,3 |
| 0 | N° turnos previos de cualquier tipo | 6.398 | 73,5 | 0,942 | -4,6 | 39.207 | 74,0 |
| 1 | N° turnos previos de cualquier tipo | 6.727 | 72,7 | 0,931 | -5,4 | 23.866 | 77,9 |
| 2 | N° turnos previos de cualquier tipo | 5.849 | 77,1 | 0,987 | -1 | 15.776 | 81,2 |
| 3-4 | N° turnos previos de cualquier tipo | 8.133 | 80,5 | 1,031 | 2,4 | 17.356 | 83,0 |
| 5+ | N° turnos previos de cualquier tipo | 8.141 | 84,5 | 1,082 | 6,4 | 12.868 | 85,6 |
| 0 | Usó canal digital en algún turno previo | 25.396 | 76,2 | 0,976 | -1,9 | 89.358 | 77,4 |
| 1+ | Usó canal digital en algún turno previo | 9.852 | 83,0 | 1,063 | 4,9 | 19.715 | 84,7 |
| <=30 | Días desde el turno previo (cualquier tipo) | 5.713 | 80,5 | 1,031 | 2,4 | 17.441 | 80,4 |
| 31-90 | Días desde el turno previo (cualquier tipo) | 5.526 | 85,9 | 1,1 | 7,8 | 16.603 | 86,3 |
| 91-180 | Días desde el turno previo (cualquier tipo) | 9.656 | 82,3 | 1,054 | 4,2 | 22.888 | 83,6 |
| 181-365 | Días desde el turno previo (cualquier tipo) | 7.071 | 71,8 | 0,919 | -6,3 | 12.050 | 73,6 |
| >365 | Días desde el turno previo (cualquier tipo) | 884 | 50,6 | 0,648 | -27,5 | 884 | 50,6 |
| sin turno previo | Días desde el turno previo (cualquier tipo) | 6.398 | 73,5 | 0,942 | -4,6 | 39.207 | 74,0 |
| <=30 | Días desde el mantenimiento completado previo | 310 | 83,2 | 1,066 | 5,1 | 1.217 | 83,7 |
| 31-90 | Días desde el mantenimiento completado previo | 3.787 | 88,8 | 1,138 | 10,7 | 12.086 | 88,9 |
| 91-180 | Días desde el mantenimiento completado previo | 10.155 | 84,6 | 1,084 | 6,5 | 23.782 | 85,8 |
| 181-365 | Días desde el mantenimiento completado previo | 8.332 | 74,4 | 0,952 | -3,7 | 13.991 | 76,0 |
| >365 | Días desde el mantenimiento completado previo | 1.171 | 55,5 | 0,711 | -22,6 | 1.171 | 55,5 |
| sin mant. previo | Días desde el mantenimiento completado previo | 11.493 | 73,7 | 0,943 | -4,4 | 56.826 | 74,6 |

**Recencia del turno previo × si el turno base es el primer service (sub-base 2025): separa 'vehículo nuevo' de 'vuelve tras ausencia'**
| primer_service | 181-365 % | 31-90 % | 91-180 % | <=30 % | >365 % | sin turno previo % | 181-365 n | 31-90 n | 91-180 n | <=30 n | >365 n | sin turno previo n |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1er service | 75,5 | 86,2 | 83,8 | 84,3 | s/d | 83,1 | 640 | 607 | 764 | 1.399 | s/d | 4.720 |
| 2° o posterior | 71,4 | 85,9 | 82,2 | 79,3 | 49,9 | 46,8 | 6.431 | 4.919 | 8.892 | 4.314 | 822 | 1.678 |

**Retorno según no-show previo DENTRO de cada nivel de turnos previos (sub-base 2025, >=1 turno previo): a igual cantidad de contactos, el que tuvo un no-show retorna menos**
| h_turnos | n (con no-show previo) | n (sin no-show previo) | retorno_pct (con no-show previo) | retorno_pct (sin no-show previo) |
|---|---|---|---|---|
| 1 | 294 | 6.433 | 67,0 | 73,0 |
| 2 | 485 | 5.364 | 72,8 | 77,4 |
| 3-4 | 1.159 | 6.974 | 76,4 | 81,1 |
| 5+ | 2.259 | 5.882 | 83,0 | 85,0 |

**Modelo conjunto del historial (logística sin penalización, n=35.134): OR de cada feature controlando por todas las demás + generación, año modelo y n° de service**
| index | OR ajustado |
|---|---|
| h_no_show=1 (ref 0) | 0,733 |
| h_no_show=2+ (ref 0) | 0,625 |
| h_cancel_true=1 (ref 0) | 0,749 |
| h_cancel_true=2+ (ref 0) | 0,704 |
| h_cancel_resched=1 (ref 0) | 0,809 |
| h_cancel_resched=2+ (ref 0) | 0,76 |
| h_recall=1 (ref 0) | 0,955 |
| h_recall=2+ (ref 0) | 0,975 |
| h_repair=1 (ref 0) | 0,973 |
| h_repair=2+ (ref 0) | 0,776 |
| h_diag=1 (ref 0) | 0,862 |
| h_diag=2+ (ref 0) | 0,752 |
| h_return_visit=1 (ref 0) | 0,958 |
| h_return_visit=2+ (ref 0) | 1,003 |
| h_turnos=1 (ref 0) | 1 |
| h_turnos=2 (ref 0) | 1,316 |
| h_turnos=3-4 (ref 0) | 1,723 |
| h_turnos=5+ (ref 0) | 2,7 |
| h_recency=181-365 (ref 91-180) | 0,746 |
| h_recency=31-90 (ref 91-180) | 1,143 |
| h_recency=<=30 (ref 91-180) | 0,908 |
| h_recency=>365 (ref 91-180) | 0,403 |
| h_recency=sin turno previo (ref 91-180) | 0,531 |

**Mismo modelo SIN turnos previos ni recencia (n=35.134): el efecto 'crudo' de cada feature neto solo de la edad del vehículo**
| index | OR ajustado |
|---|---|
| h_no_show=1 (ref 0) | 0,956 |
| h_no_show=2+ (ref 0) | 0,831 |
| h_cancel_true=1 (ref 0) | 0,989 |
| h_cancel_true=2+ (ref 0) | 0,995 |
| h_cancel_resched=1 (ref 0) | 1,155 |
| h_cancel_resched=2+ (ref 0) | 1,223 |
| h_recall=1 (ref 0) | 1,258 |
| h_recall=2+ (ref 0) | 1,433 |
| h_repair=1 (ref 0) | 1,247 |
| h_repair=2+ (ref 0) | 0,982 |
| h_diag=1 (ref 0) | 1,044 |
| h_diag=2+ (ref 0) | 1,049 |
| h_return_visit=1 (ref 0) | 1,167 |
| h_return_visit=2+ (ref 0) | 1,089 |

## 9. (g) Estacionalidad y tendencia

**Turnos por mes (ScheduleDate) y status, 2024-01 → 2026-08 (agosto 2026 parcial: hasta el 25)**
| ym | (30) Agendado | (40) En progreso | (60) Concluido | (70) Cancelado | (80) No asistio | (90) Concluido sin OS | total |
|---|---|---|---|---|---|---|---|
| 2024-01 | 7 | 0 | 9.877 | 2.592 | 953 | 428 | 13.857 |
| 2024-02 | 4 | 0 | 8.330 | 2.154 | 819 | 397 | 11.704 |
| 2024-03 | 7 | 0 | 8.823 | 2.396 | 869 | 333 | 12.428 |
| 2024-04 | 8 | 0 | 9.262 | 2.506 | 851 | 421 | 13.048 |
| 2024-05 | 6 | 0 | 9.839 | 2.750 | 820 | 450 | 13.865 |
| 2024-06 | 1 | 0 | 7.842 | 2.230 | 639 | 330 | 11.042 |
| 2024-07 | 9 | 0 | 10.102 | 2.765 | 895 | 551 | 14.322 |
| 2024-08 | 5 | 0 | 10.125 | 2.925 | 844 | 505 | 14.404 |
| 2024-09 | 11 | 1 | 10.122 | 2.870 | 677 | 468 | 14.149 |
| 2024-10 | 5 | 0 | 10.758 | 3.056 | 767 | 492 | 15.078 |
| 2024-11 | 9 | 0 | 10.260 | 2.809 | 749 | 434 | 14.261 |
| 2024-12 | 15 | 0 | 10.154 | 2.830 | 765 | 482 | 14.246 |
| 2025-01 | 0 | 0 | 11.427 | 3.172 | 847 | 493 | 15.939 |
| 2025-02 | 0 | 0 | 10.322 | 3.193 | 824 | 461 | 14.800 |
| 2025-03 | 1 | 0 | 9.995 | 3.198 | 940 | 552 | 14.686 |
| 2025-04 | 1 | 3 | 11.013 | 3.482 | 966 | 578 | 16.043 |
| 2025-05 | 3 | 12 | 11.584 | 3.294 | 922 | 517 | 16.332 |
| 2025-06 | 1 | 5 | 10.609 | 2.980 | 935 | 532 | 15.062 |
| 2025-07 | 7 | 4 | 12.427 | 3.239 | 940 | 586 | 17.203 |
| 2025-08 | 9 | 7 | 12.048 | 3.590 | 980 | 546 | 17.180 |
| 2025-09 | 9 | 7 | 12.387 | 3.324 | 930 | 641 | 17.298 |
| 2025-10 | 21 | 15 | 12.590 | 3.386 | 963 | 613 | 17.588 |
| 2025-11 | 5 | 27 | 10.981 | 3.131 | 861 | 521 | 15.526 |
| 2025-12 | 25 | 35 | 11.787 | 3.172 | 850 | 572 | 16.441 |
| 2026-01 | 7 | 34 | 12.862 | 3.751 | 984 | 547 | 18.185 |
| 2026-02 | 10 | 46 | 10.518 | 3.421 | 825 | 418 | 15.238 |
| 2026-03 | 14 | 59 | 12.861 | 4.211 | 1.010 | 438 | 18.593 |
| 2026-04 | 9 | 66 | 11.968 | 4.053 | 838 | 462 | 17.396 |
| 2026-05 | 17 | 66 | 11.158 | 3.817 | 765 | 413 | 16.236 |
| 2026-06 | 14 | 116 | 11.383 | 3.724 | 872 | 516 | 16.625 |
| 2026-07 | 55 | 282 | 11.330 | 3.854 | 787 | 499 | 16.807 |
| 2026-08 | 337 | 1.040 | 7.947 | 2.849 | 550 | 311 | 13.034 |

**Tasas mensuales sobre turnos resueltos, volumen de mantenimientos completados, % check-in nulo y % FordPass**
| ym | resueltos | no_show | cancel_real | cancel_reprog | concluido | sin_os | mant_completados | checkin_nulo_en_concluidos_pct | fordpass_pct |
|---|---|---|---|---|---|---|---|---|---|
| 2024-01 | 13.850 | 6,9 | 8 | 10,7 | 71,3 | 3,1 | 6.396 | 29,4 | 9,6 |
| 2024-02 | 11.700 | 7 | 7,6 | 10,8 | 71,2 | 3,4 | 5.544 | 28,2 | 12,2 |
| 2024-03 | 12.421 | 7 | 6,9 | 12,4 | 71,0 | 2,7 | 5.706 | 27,7 | 12,7 |
| 2024-04 | 13.040 | 6,5 | 6,7 | 12,5 | 71,0 | 3,2 | 5.771 | 26,6 | 12,7 |
| 2024-05 | 13.859 | 5,9 | 6,9 | 12,9 | 71,0 | 3,2 | 5.970 | 24,4 | 13,8 |
| 2024-06 | 11.041 | 5,8 | 7,6 | 12,6 | 71,0 | 3 | 4.888 | 24,1 | 14,8 |
| 2024-07 | 14.313 | 6,3 | 7 | 12,3 | 70,6 | 3,8 | 6.421 | 26,4 | 15,8 |
| 2024-08 | 14.399 | 5,9 | 6,9 | 13,5 | 70,3 | 3,5 | 6.700 | 24,3 | 16,1 |
| 2024-09 | 14.137 | 4,8 | 7,1 | 13,2 | 71,6 | 3,3 | 6.596 | 22,6 | 17,0 |
| 2024-10 | 15.073 | 5,1 | 6,5 | 13,8 | 71,4 | 3,3 | 6.981 | 20,4 | 17,4 |
| 2024-11 | 14.252 | 5,3 | 6,6 | 13,1 | 72,0 | 3 | 6.658 | 13,1 | 18,2 |
| 2024-12 | 14.231 | 5,4 | 6,4 | 13,5 | 71,4 | 3,4 | 6.760 | 10,7 | 18,6 |
| 2025-01 | 15.939 | 5,3 | 7,6 | 12,3 | 71,7 | 3,1 | 7.753 | 10,6 | 20,1 |
| 2025-02 | 14.800 | 5,6 | 7,5 | 14,0 | 69,7 | 3,1 | 6.843 | 11,3 | 21,1 |
| 2025-03 | 14.685 | 6,4 | 7,5 | 14,2 | 68,1 | 3,8 | 6.550 | 11,8 | 20,6 |
| 2025-04 | 16.039 | 6 | 6,6 | 15,1 | 68,7 | 3,6 | 7.125 | 10,7 | 22,0 |
| 2025-05 | 16.317 | 5,7 | 6,5 | 13,7 | 71,0 | 3,2 | 7.354 | 7,5 | 22,4 |
| 2025-06 | 15.056 | 6,2 | 6 | 13,8 | 70,5 | 3,5 | 6.669 | 7,5 | 22,4 |
| 2025-07 | 17.192 | 5,5 | 6 | 12,9 | 72,3 | 3,4 | 7.892 | 6,6 | 23,6 |
| 2025-08 | 17.164 | 5,7 | 6,9 | 14,0 | 70,2 | 3,2 | 7.468 | 6,5 | 23,4 |
| 2025-09 | 17.282 | 5,4 | 6,3 | 13,0 | 71,7 | 3,7 | 7.475 | 8,1 | 24,4 |
| 2025-10 | 17.552 | 5,5 | 6,3 | 13,0 | 71,7 | 3,5 | 8.055 | 8 | 24,6 |
| 2025-11 | 15.494 | 5,6 | 6,4 | 13,8 | 70,9 | 3,4 | 7.024 | 9,4 | 22,5 |
| 2025-12 | 16.381 | 5,2 | 5,7 | 13,6 | 72,0 | 3,5 | 7.989 | 8,9 | 25,1 |
| 2026-01 | 18.144 | 5,4 | 6,3 | 14,3 | 70,9 | 3 | 8.925 | 8,6 | 24,7 |
| 2026-02 | 15.182 | 5,4 | 6,4 | 16,1 | 69,3 | 2,8 | 6.938 | 8,1 | 26,1 |
| 2026-03 | 18.520 | 5,5 | 6,7 | 16,0 | 69,4 | 2,4 | 8.469 | 9 | 26,4 |
| 2026-04 | 17.321 | 4,8 | 6,5 | 16,9 | 69,1 | 2,7 | 7.966 | 9,2 | 25,6 |
| 2026-05 | 16.153 | 4,7 | 6,4 | 17,2 | 69,1 | 2,6 | 7.383 | 6,5 | 26,3 |
| 2026-06 | 16.495 | 5,3 | 5,7 | 16,9 | 69,0 | 3,1 | 7.479 | 6,3 | 25,3 |
| 2026-07 | 16.470 | 4,8 | 6,1 | 17,3 | 68,8 | 3 | 7.628 | 6,4 | 26,8 |
| 2026-08 | 11.657 | 4,7 | 6 | 18,5 | 68,2 | 2,7 | 5.513 | 5,7 | 25,5 |

**Turnos con ScheduleDate posterior al CUTOFF (reservas futuras)**
| ym | (30) Agendado | (40) En progreso | (70) Cancelado |
|---|---|---|---|
| 2026-08 | 1.903 | 5 | 351 |
| 2026-09 | 1.386 | 2 | 146 |
| 2026-10 | 22 | 0 | 1 |
| 2026-11 | 9 | 0 | 0 |
| 2026-12 | 1 | 0 | 0 |

**Tasas anuales sobre turnos resueltos (2026 hasta el 25/8)**
| year | resueltos | no_show | cancel_real | cancel_reprog | concluido |
|---|---|---|---|---|---|
| 2024 | 162.316 | 5,9 | 7 | 12,7 | 71,2 |
| 2025 | 193.901 | 5,7 | 6,6 | 13,6 | 70,7 |
| 2026 | 129.942 | 5,1 | 6,3 | 16,5 | 69,3 |

**Retorno por mes calendario del turno base (2024 y ene–may 2025 combinados)**
| mes calendario del turno base | n | retorno_pct |
|---|---|---|
| 01 | 14.014 | 77,9 |
| 02 | 12.307 | 77,9 |
| 03 | 12.188 | 78,0 |
| 04 | 12.787 | 79,0 |
| 05 | 13.134 | 78,8 |
| 06 | 4.839 | 80,0 |
| 07 | 6.357 | 79,0 |
| 08 | 6.638 | 79,0 |
| 09 | 6.549 | 78,6 |
| 10 | 6.952 | 79,2 |
| 11 | 6.613 | 80,2 |
| 12 | 6.695 | 78,7 |

## 10. Ranking univariante de features candidatas (Information Value)
IV = Σ_i (p_ret_i − p_churn_i)·ln(p_ret_i / p_churn_i), con p_ret_i = fracción de los que retornan que cae en el bin i y p_churn_i la fracción de los que no retornan. Umbrales usuales: <0,02 nulo; 0,02–0,1 débil; 0,1–0,3 medio; >0,3 fuerte. Depende del binning y se infla con muchas categorías (dealer_id). 'dif_pp' = tasa máxima − tasa mínima entre bins con n>=300. Las features de historial se calculan sobre la sub-base con >=12 meses de lookback; el resto sobre la base completa.

**Ranking de features por IV (incluye los controles para dimensionar)**
| feature | n | n_bins | IV | tasa_max_pct | tasa_min_pct | dif_pp | comentario |
|---|---|---|---|---|---|---|---|
| ConnectedStatusARG | 109.073 | 4 | 0,314 | 87,2 | 27,0 | 60,2 | SNAPSHOT a la extracción. 'Sin Información' concentra vehículos que desaparecen del sistema: riesgo alto de leakage. Usar solo Conectado vs No tiene dentro de P703, o excluir. |
| my_bin | 109.073 | 7 | 0,294 | 92,0 | 46,7 | 45,3 | CONTROL. Año modelo; el driver estructural más fuerte de la base. |
| h_recency_maint | 35.248 | 6 | 0,18 | 88,8 | 55,5 | 33,3 | Legítima (historial). Recencia del mantenimiento previo = ritmo de uso. Se solapa con tema de uso/km. |
| h_recency | 35.248 | 6 | 0,147 | 85,9 | 50,6 | 35,3 | Legítima (historial). Recencia del último turno de cualquier tipo antes del base. |
| gen | 109.073 | 3 | 0,114 | 86,8 | 75,3 | 11,5 | CONTROL (no es de este tema). Generación del vehículo; confunde a canal y conectividad. |
| h_maint | 35.248 | 4 | 0,092 | 86,1 | 73,7 | 12,4 | Legítima (historial) pero correlacionada con intensidad de uso/km: cruzar con tema de uso. |
| dealer_id | 109.067 | 90 | 0,08 | 87,9 | 58,3 | 29,6 | Estable entre años (ver r 2024 vs 2025). Alta cardinalidad: usar como target encoding con regularización o efecto aleatorio. Parte es mix de generación. |
| h_recall | 35.248 | 3 | 0,075 | 88,3 | 75,8 | 12,5 | Legítima (historial). |
| h_turnos | 35.248 | 5 | 0,071 | 84,5 | 72,7 | 11,8 | Legítima (historial). Intensidad de relación con la red. |
| dealer_te_2024 | 35.248 | 6 | 0,06 | 83,8 | 73,3 | 10,5 | Target encoding del dealer calculado en 2024 y evaluado en 2025 (fuera de tiempo): versión honesta de dealer_id. |
| maint_bin | 109.073 | 6 | 0,047 | 82,9 | 73,6 | 9,3 | CONTROL. N° de service del turno base (edad del vehículo en services). |
| h_digital | 35.248 | 2 | 0,034 | 83,0 | 76,2 | 6,8 | Legítima (historial). Usó FordPass/WEB/Mobile alguna vez. |
| ScheduleSource | 109.073 | 5 | 0,028 | 83,8 | 75,8 | 8 | Legítima al scoring (fuente del último turno). Parte del efecto es mix P703/año modelo: ver OR ajustado. |
| digital | 109.073 | 2 | 0,023 | 82,8 | 77,2 | 5,6 | Resumen de ScheduleSource. Misma advertencia de mix. |
| NeededTowing_f | 109.073 | 3 | 0,019 | 83,5 | 77,6 | 5,9 | Legítima. Y es raro; NaN es mayoría (no informado). |
| h_cancel_resched | 35.248 | 3 | 0,014 | 82,5 | 76,8 | 5,7 | Legítima (historial). Reprogramaciones. |
| h_return_visit | 35.248 | 3 | 0,012 | 83,9 | 77,4 | 6,5 | Legítima (historial). Re-visitas a <=30 días. |
| DealerStateOrZone | 109.073 | 5 | 0,011 | 80,0 | 73,7 | 6,3 | Legítima; zona del dealer. |
| has_recall | 109.073 | 2 | 0,01 | 82,0 | 77,9 | 4,1 | Legítima. Mantenimiento + campaña. |
| ScheduleReturn_f | 109.073 | 3 | 0,01 | 84,0 | 78,2 | 5,8 | Legítima. Y = re-visita a <=30 días de otro turno; en la base es raro (los mantenimientos no suelen ser re-visitas). |
| h_repair | 35.248 | 3 | 0,009 | 83,1 | 77,6 | 5,5 | Legítima (historial). |
| has_fixed_price | 109.073 | 2 | 0,009 | 81,5 | 77,9 | 3,6 | Legítima. Precio fijo Ford en el turno base. |
| survey_grp | 109.073 | 5 | 0,007 | 83,1 | 78,3 | 4,8 | Encuesta respondida ANTES del turno (probablemente del agendado). Cobertura ~7%: la señal es 'respondió' más que el rating. Verificar semántica con el mentor. |
| wdays_bin | 109.073 | 8 | 0,006 | 79,9 | 75,2 | 4,7 | Idem DaysInDealer. |
| days_bin | 109.073 | 8 | 0,006 | 79,9 | 76,0 | 3,9 | Legítima si se conoce el checkout antes del scoring. Valores negativos y >30 son errores de carga. |
| has_diag | 109.073 | 2 | 0,005 | 78,9 | 72,8 | 6,1 | Legítima. Mantenimiento + diagnóstico en el mismo turno. |
| Region | 109.073 | 3 | 0,004 | 86,2 | 78,4 | 7,8 | Legítima; casi constante (60 domina). |
| items_bin | 109.073 | 3 | 0,004 | 80,6 | 78,0 | 2,6 | Legítima. Cantidad de ítems del turno base. |
| dur_bin | 109.073 | 4 | 0,003 | 79,0 | 76,4 | 2,6 | Legítima. Duración nominal del ítem, proxy del tipo de service. |
| h_cancel_true | 35.248 | 3 | 0,002 | 81,5 | 77,8 | 3,7 | Legítima (historial). Cancelación real = IsReschedule=N. Idem no-shows: OR ajustado ~0,75 pese a IV ~0. |
| h_diag | 35.248 | 3 | 0,001 | 79,4 | 77,8 | 1,6 | Legítima (historial). |
| IsReschedule_f | 109.073 | 2 | 0,001 | 79,7 | 78,5 | 1,2 | Legítima. Y = el turno base nació de una reprogramación. |
| h_no_show | 35.248 | 3 | 0 | 79,1 | 78,0 | 1,1 | Legítima (historial). IV univariante ~0 por confusión con intensidad: a igual n de turnos previos, OR ajustado ~0,7. Truncada a izquierda: solo desde 2024-01. |
| has_pud | 109.073 | 2 | 0 | 80,0 | 78,6 | 1,4 | Legítima. n chico. |
| has_guarantee | 109.073 | 2 | 0 | 82,7 | 78,7 | 4 | Legítima. n chico. |
| has_repair | 109.073 | 2 | 0 | 79,6 | 78,7 | 0,9 | Legítima. Mantenimiento + reparación. |
| CustomerWaiting_f | 109.073 | 2 | 0 | 78,7 | 77,4 | 1,3 | Legítima. Y es raro. |
| has_mobile | 109.073 | 2 | 0 | 78,7 | 78,3 | 0,4 | Legítima. n chico. |
