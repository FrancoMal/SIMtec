# Salida del script `scripts/eda/05_calidad_cobertura_leakage.py`

CUTOFF = 2026-08-25 ; inicio de la agenda = 2024-01-01

sales: 59,384 filas / 59,384 vehiculos. agenda: 631,623 filas-item / 492,442 turnos / 111,752 vehiculos con id. Mantenimientos concluidos (is_completed_maintenance): 222,889.

## A. Left-censoring: historia previa invisible

Vehiculos en agenda con id: 111,752; con WarrantyStartDate: 110,495 (nulo: 1,257). Con WSD anterior al inicio de la agenda (historia previa invisible): 66,795 (59.8% de todos los vehiculos con id; 60.5% de los que tienen WSD); con WSD anterior a 2023-01-01: 46,629 (41.7% de todos).

### A1. Historia observable por fecha de scoring

`% sin mant. observado` = vehiculos activos sin ningun mantenimiento concluido antes de t. `gap` = maint_number del ultimo service observado menos cantidad de mantenimientos observados (services que ocurrieron antes de 2024 y no vemos).

|                                           | 2024-07-01   | 2025-01-01   | 2025-07-01   | 2026-01-01   | 2026-08-25   |
|:------------------------------------------|:-------------|:-------------|:-------------|:-------------|:-------------|
| meses observables                         | 6.0          | 12.0         | 18.0         | 24.0         | 31.8         |
| vehiculos activos (>=1 turno < t)         | 41,478       | 62,975       | 79,120       | 94,657       | 111,184      |
| % sin mant. observado                     | 33.4         | 28.0         | 25.6         | 23.8         | 21.3         |
| % con 1 mant.                             | 53.7         | 43.5         | 36.7         | 32.3         | 28.5         |
| % con >=2 mant.                           | 12.9         | 28.5         | 37.7         | 43.9         | 50.1         |
| mediana dias desde ult. mant.             | 80           | 111          | 141          | 163          | 202          |
| p90 dias desde ult. mant.                 | 158          | 292          | 403          | 525          | 705          |
| max observable (dias)                     | 182          | 366          | 547          | 731          | 967          |
| % maint_number > n obs. (hist. invisible) | 77.7         | 67.6         | 59.6         | 53.9         | 48.5         |
| mediana services invisibles (gap)         | 3            | 2            | 1            | 1            | 0            |

### A2. % de vehiculos activos sin mantenimiento observado, por edad y fecha de scoring

| edad del vehiculo en t (anios)   |   2024-07-01 |   2025-01-01 |   2025-07-01 |   2026-01-01 |   2026-08-25 |
|:---------------------------------|-------------:|-------------:|-------------:|-------------:|-------------:|
| <1                               |         43.5 |         45.6 |         37.7 |         36.7 |         34.9 |
| 1-2                              |         16.6 |         12.2 |         10.1 |          8.5 |          7.3 |
| 2-3                              |         18.5 |         12.0 |          9.6 |          7.1 |          5.5 |
| 3-5                              |         25.8 |         17.4 |         14.6 |         12.6 |          9.6 |
| 5-8                              |         50.2 |         42.8 |         39.0 |         32.9 |         25.7 |
| 8+                               |         72.0 |         66.3 |         64.2 |         63.3 |         61.0 |

### A3. Cota aproximada del truncamiento de 'dias desde el ultimo mantenimiento'

Referencia: distribucion observada al CUTOFF (ventana de 967 dias), que a su vez sigue truncada por arriba; el numero es una cota inferior de la fraccion de vehiculos cuyo verdadero 'dias desde el ultimo mantenimiento' no cabe en la ventana.

| fecha scoring t   | ventana observable (dias)   | % de la distribucion de referencia (CUTOFF) que supera la ventana   |
|:------------------|:----------------------------|:--------------------------------------------------------------------|
| 2024-07-01        | 182                         | 53.5                                                                |
| 2025-01-01        | 366                         | 28.6                                                                |
| 2025-07-01        | 547                         | 17.5                                                                |
| 2026-01-01        | 731                         | 8.9                                                                 |

Lectura: A3 describe el corte transversal al CUTOFF entre vehiculos con >=1 mantenimiento en 32 meses (incluye a los que no visitan la red hace mas de 6 meses); NO es la fraccion de vehiculos activos en t con recencia truncada. Esa fraccion se mide en A5 con la misma poblacion y distinta profundidad de historia.

### A5. Misma poblacion (vehiculos con >=1 turno en los 182 dias previos al CUTOFF, n=54,667): % sin mantenimiento observado segun la profundidad de historia, total y por edad en el CUTOFF

Aisla el efecto de la profundidad de historia (lo que cambia con la fecha de scoring) del efecto calendario/poblacion que mezclan A1 y A2. La diferencia entre la fila 182 y la fila 967 es la fraccion de vehiculos que un backtest con 6 meses de historia etiqueta 'sin mantenimiento' por truncamiento.

|   historia observable (dias) |   % sin mant. observado |   <1 |   1-2 |   2-3 |   3-5 |   5-8 |   8+ |
|-----------------------------:|------------------------:|-----:|------:|------:|------:|------:|-----:|
|                          182 |                    25.6 | 31.9 |  15.6 |  20.8 |  21.1 |  39.0 | 62.6 |
|                          366 |                    16.1 | 31.0 |   5.7 |   8.3 |  10.9 |  27.0 | 53.9 |
|                          547 |                    13.2 | 31.0 |   4.7 |   4.2 |   7.0 |  21.2 | 48.5 |
|                          731 |                    12.0 | 31.0 |   4.6 |   2.8 |   5.2 |  17.6 | 45.7 |
|                          967 |                    11.2 | 31.0 |   4.6 |   2.5 |   3.9 |  14.5 | 43.1 |

### A4. maint_number del primer service observado vs. edad del vehiculo (proxy de historia invisible)

Correlacion (maint_number del primer service observado, edad en anios) = 0.761. Vehiculos con edad > 2 anios cuyo primer service observado es el 1°: 553 de 26,518 (2.1%).

| edad al primer service observado   |     1 |    2 |    3 |    4 |    5 |    6 |   7 |   8+ |
|:-----------------------------------|------:|-----:|-----:|-----:|-----:|-----:|----:|-----:|
| <1                                 | 36882 | 2683 |  841 |  370 |  173 |   86 |  32 |  242 |
| 1-2                                |  8948 | 4319 | 2187 | 1357 |  897 |  578 | 312 |  642 |
| 2-3                                |   305 | 1201 | 1447 | 1177 | 1118 |  921 | 554 | 1658 |
| 3-5                                |   117 |  204 |  768 | 1178 | 1184 | 1174 | 869 | 3406 |
| 5-8                                |    69 |   59 |  122 |  203 |  418 |  899 | 573 | 4038 |
| 8+                                 |    62 |   28 |   37 |   35 |   47 |  304 |  94 | 2249 |

Incremento de maint_number entre mantenimientos consecutivos del mismo vehiculo (n=134,172): +1 en 77.5%, +2 en 7.4%, <=0 en 9.9%.

### A4b. gap = maint_number del ultimo service - mantenimientos observados, segun si la historia previa puede ser invisible (tasa de falsos positivos del proxy)

En vehiculos entregados desde 2024 no hay historia invisible: un gap > 0 ahi es salto de numeracion o un service hecho fuera de la red / del extracto.

|                                                                   | vehiculos   | % gap > 0   | % gap >= 2   | % gap < 0   | mediana gap   |
|:------------------------------------------------------------------|:------------|:------------|:-------------|:------------|:--------------|
| ('2025-01-01', 'WSD < 2024-01-01 (historia invisible posible)')   | 40,484      | 74.8        | 63.0         | 1.1         | 3             |
| ('2025-01-01', 'WSD >= 2024-01-01 (toda la historia es visible)') | 4,627       | 4.9         | 1.6          | 2.9         | 0             |
| ('2026-08-25', 'WSD < 2024-01-01 (historia invisible posible)')   | 48,821      | 77.9        | 65.1         | 2.5         | 3             |
| ('2026-08-25', 'WSD >= 2024-01-01 (toda la historia es visible)') | 38,196      | 10.7        | 2.5          | 3.7         | 0             |

ServiceName segun ServiceMaintenance (el nombre pierde el primer digito en 11, 12, 19 y en parte de 13; el codigo numerico es el coherente con la edad del vehiculo): 11 -> 1° Maintenance service (5,128), 1ª Maintenance review (1,273); 12 -> 2° Maintenance service (4,453), 2ª Maintenance review (1,174); 13 -> 13° Maintenance service (3,539), 3ª Maintenance review (975); 19 -> 9° Maintenance service (962), 9ª Maintenance review (321).

Edad mediana (anios) al service segun maint_number: 1°: 0.73, 2°: 1.28, 3°: 1.65, 4°: 1.97, 5°: 2.32, 6°: 2.77, 7°: 2.97, 8°: 3.20, 9°: 3.43, 10°: 3.72, 11°: 3.87, 12°: 4.04, 13°: 4.08, 14°: 4.25, 15°: 4.45, 16°: 4.88, 17°: 4.94, 18°: 5.39, 19°: 5.69, 20°: 6.77

Figura: `reports/figures/eda/05_calidad_cobertura_leakage_censura_izquierda.png`

Figura: `reports/figures/eda/05_calidad_cobertura_leakage_historia_invisible.png`

## B. Columnas snapshot (foto a la extraccion) vs. evento

### B1. Variacion dentro de un mismo vehicle_id (solo vehiculos con >=2 turnos)

| columna                       | vehiculos con >=2 turnos   | vehiculos con >=2 valores no nulos   | vehiculos con >1 valor distinto   | % con >1 valor (sobre >=2 no nulos)   |
|:------------------------------|:---------------------------|:-------------------------------------|:----------------------------------|:--------------------------------------|
| ConnectedStatusARG            | 85,143                     | 85,143                               | 74                                | 0.1                                   |
| KM                            | 85,143                     | 82,347                               | 7                                 | 0.0                                   |
| VehicleCurrentKM              | 85,143                     | 75,688                               | 73,813                            | 97.5                                  |
| WarrantyStartDate             | 85,143                     | 84,608                               | 1                                 | 0.0                                   |
| ModelYear                     | 85,143                     | 84,823                               | 0                                 | 0.0                                   |
| TMA                           | 85,143                     | 84,937                               | 0                                 | 0.0                                   |
| ShortVehicleModelGroupTreated | 85,143                     | 85,143                               | 90                                | 0.1                                   |
| Region                        | 85,143                     | 85,143                               | 5,093                             | 6.0                                   |
| DealerStateOrZone             | 85,143                     | 85,132                               | 7,903                             | 9.3                                   |
| dealer_id                     | 85,143                     | 85,143                               | 18,552                            | 21.8                                  |
| customer_id                   | 85,143                     | 84,142                               | 23,245                            | 27.6                                  |

Region y DealerStateOrZone son atributos del dealer: dealers con >1 Region = 0, con >1 DealerStateOrZone = 0 (de 95). Varian dentro de un vehiculo solo cuando cambia de dealer.

### B2. ConnectedStatusARG (% de vehiculos) por trimestre de WarrantyStartDate

'Conectado' entre vehiculos con WSD < 2023-07-01: 0.6%; con WSD >= 2023-07-01: 66.4%. 'Sin Informacion de Conectividad' para ModelYear 2026: 59.0%.

| trimestre de WarrantyStartDate   | Conectado   | No Conectado   | No tiene Conectividad   | Sin Información de Conectividad   | n vehiculos   |
|:---------------------------------|:------------|:---------------|:------------------------|:----------------------------------|:--------------|
| 2023Q1                           | 0.7         | 78.8           | 12.8                    | 7.7                               | 4,072         |
| 2023Q2                           | 0.6         | 81.8           | 8.3                     | 9.3                               | 3,990         |
| 2023Q3                           | 62.9        | 21.5           | 10.8                    | 4.8                               | 6,354         |
| 2023Q4                           | 74.2        | 6.8            | 14.8                    | 4.3                               | 5,750         |
| 2024Q1                           | 77.9        | 5.4            | 13.4                    | 3.2                               | 4,142         |
| 2024Q2                           | 82.5        | 1.6            | 13.0                    | 2.9                               | 4,900         |
| 2024Q3                           | 79.7        | 1.3            | 15.1                    | 3.9                               | 6,489         |
| 2024Q4                           | 70.2        | 1.1            | 18.9                    | 9.8                               | 5,104         |
| 2025Q1                           | 66.6        | 1.0            | 16.2                    | 16.2                              | 6,042         |
| 2025Q2                           | 59.9        | 0.7            | 15.4                    | 24.1                              | 5,608         |
| 2025Q3                           | 51.3        | 0.4            | 15.1                    | 33.2                              | 5,335         |
| 2025Q4                           | 49.8        | 1.1            | 14.0                    | 35.1                              | 2,984         |
| 2026Q1                           | 46.1        | 0.3            | 9.8                     | 43.9                              | 1,887         |
| 2026Q2                           | 34.3        | 0.4            | 5.9                     | 59.4                              | 899           |
| 2026Q3                           | 4.2         | 0.0            | 3.2                     | 92.6                              | 310           |

### B2b. Resultado del turno segun ConnectedStatusARG (sin controlar por edad; solo para mostrar que no es una senal fuerte)

| ConnectedStatusARG              |   % concluido |   % mant. concluido |   % no asistio |   % cancelado |
|:--------------------------------|--------------:|--------------------:|---------------:|--------------:|
| Conectado                       |          68.2 |                41.8 |            5.0 |          21.7 |
| No Conectado                    |          70.8 |                47.1 |            5.8 |          19.8 |
| No tiene Conectividad           |          69.3 |                47.9 |            6.0 |          20.5 |
| Sin Información de Conectividad |          68.7 |                49.6 |            6.5 |          18.6 |

Figura: `reports/figures/eda/05_calidad_cobertura_leakage_conectividad_snapshot.png`

### B3. KM es una foto del odometro a la extraccion; VehicleCurrentKM es la lectura del turno

| metrica                                                                                                      | valor   |
|:-------------------------------------------------------------------------------------------------------------|:--------|
| vehiculos con >=2 valores no nulos de KM cuyo KM es constante                                                | 100.0%  |
| vehiculos con >=2 valores no nulos de VehicleCurrentKM que varian                                            | 97.5%   |
| vehiculos cuyo KM == VehicleCurrentKM del ULTIMO turno concluido (sobre vehiculos con >=1 concluido con VCK) | 91.7%   |
| vehiculos cuyo KM == VehicleCurrentKM del ULTIMO turno concluido (sobre vehiculos con KM y VCK no nulos)     | 95.5%   |
| vehiculos cuyo KM >= max(VehicleCurrentKM) (KM y VCK no nulos)                                               | 92.9%   |
| turnos concluidos: KM == VehicleCurrentKM cuando el turno ES el ultimo concluido del vehiculo                | 95.5%   |
| turnos concluidos: KM == VehicleCurrentKM cuando NO es el ultimo                                             | 2.5%    |
| turnos concluidos 2024 con KM == VehicleCurrentKM                                                            | 13.0%   |
| turnos concluidos 2026 con KM == VehicleCurrentKM                                                            | 66.1%   |

Nulos de VehicleCurrentKM por StatusARG: (30) Agendado: 76.5%, (40) En progreso: 60.4%, (60) Concluido: 0.0%, (70) Cancelado: 100.0%, (80) No asistio: 71.9%, (90) Concluido sin OS: 2.8%

Turnos concluidos fuera del rango [-5.000, 120.000] de KM - VehicleCurrentKM (no graficados): 11,698 de 334,636.

Figura: `reports/figures/eda/05_calidad_cobertura_leakage_km_snapshot.png`

## C. Survey: SurveyResponseDate es ANTERIOR al turno

Turnos con survey: 36,920 de 492,442 (7.5%). Por StatusARG: (60) Concluido: 26,072, (70) Cancelado: 8,363, (80) No asistio: 1,341, (90) Concluido sin OS: 682, (30) Agendado: 396, (40) En progreso: 66.

### C1. Lag (dias) entre SurveyResponseDate y las fechas del mismo turno (solo turnos con ambas fechas)

|                       | n      | min   | p5   | p25   | mediana   | p75   | p95   | max   | % <0   | % >0   |
|:----------------------|:-------|:------|:-----|:------|:----------|:------|:------|:------|:-------|:-------|
| survey - checkout     | 26,724 | -350  | -30  | -16   | -9        | -6    | -2    | 0     | 100.0  | 0.0    |
| survey - checkin      | 24,839 | -349  | -24  | -13   | -8        | -5    | -2    | 314   | 99.9   | 0.0    |
| survey - ScheduleDate | 36,920 | -365  | -26  | -14   | -8        | -4    | -2    | 0     | 100.0  | 0.0    |

% de turnos con survey por ScheduleSource: CAF: 0.0%, Dealer: 0.0%, FordPass: 29.1%, Mobile: 30.9%, WEB: 18.0%.

Rating medio por StatusARG del turno: (30) Agendado: 4.75, (40) En progreso: 4.76, (60) Concluido: 4.75, (70) Cancelado: 4.73, (80) No asistio: 4.66, (90) Concluido sin OS: 4.70.

Hipotesis 'survey de la visita anterior' descartada: lag entre la survey y el ultimo checkout concluido previo del mismo vehiculo: mediana 139 dias, solo 2.9% a <=14 dias, 32.6% sin visita previa.

Surveys con fecha posterior al CUTOFF: 9; minima fecha de survey: 2023-10-13.

Turnos con survey cuyo (vehicle_id, SurveyResponseDate) se repite en otro turno del mismo vehiculo: 752 (2.0%), en su mayoria pares que incluyen un cancelado (re-agendamiento): la survey esta atada a la sesion de reserva, no al turno.

Reservas futuras conocidas en t via survey (unico caso en que un turno con ScheduleDate >= t es informacion legitima en t; solo canales digitales): t=2025-07-01: 436 turnos / 426 vehiculos (315 luego concluidos); t=2026-01-01: 482 turnos / 477 vehiculos (352 luego concluidos).

Como proxy de anticipacion de la reserva (ScheduleDate - SurveyResponseDate): mediana 8 dias, p75 14, p90 21; 78.1% a <=14 dias y 97.3% a <=30 dias.

Fuera de rango en la figura: survey - ScheduleDate < -40 d: 358; survey - checkout < -60 d: 215.

Figura: `reports/figures/eda/05_calidad_cobertura_leakage_survey_lag.png`

## D. Turnos futuros, pendientes y flags que incorporan informacion posterior

### D1. Reservas futuras y turnos pendientes

Filas-item (30) Agendado con ScheduleDate > CUTOFF en la agenda cruda: 4,185 (el conteo de 4.185 del diccionario es a nivel item; a nivel turno son 3,321). Reservas futuras por mes: 2026-08: 2,259, 2026-09: 1,534, 2026-10: 23, 2026-11: 9, 2026-12: 1.

|                                                   | turnos   | vehiculos   |
|:--------------------------------------------------|:---------|:------------|
| ScheduleDate > CUTOFF (reservas futuras)          | 3,826    | 3,454       |
| de las cuales (30) Agendado                       | 3,321    | 3,263       |
| de las cuales (70) Cancelado                      | 498      |             |
| de las cuales (40) En progreso                    | 7        |             |
| con item de mantenimiento                         | 2,460    | 2,346       |
| pendientes ((30)+(40)) en total                   | 5,785    | 5,567       |
| pendientes con ScheduleDate <= CUTOFF (atrasados) | 2,457    | 2,349       |
| pendientes con ScheduleDate <= CUTOFF-30d (stale) | 962      |             |
| (40) En progreso stale                            | 687      |             |
| (30) Agendado stale                               | 275      |             |
| pendientes con ScheduleDate <= CUTOFF-180d        | 377      |             |

(40) En progreso: 100.0% tiene check-in y 99.9% no tiene checkout: son ordenes abiertas a la fecha de extraccion; las de mas de 30 dias nunca se cerraron en el sistema.

Ultimo check-in: 2026-08-27; ultimo checkout: 2026-08-25; turnos (60) Concluido con ScheduleDate > CUTOFF: 0.

### D2. IsReschedule y ScheduleReturn: que informacion codifican (misma unidad vehiculo, turnos ordenados por event_date)

| grupo                            | turnos   | % con turno posterior <=7d   | % con turno posterior <=30d   | % con turno concluido <=30d despues   | % con turno anterior <=30d   | % con turno anterior cancelado <=30d   |
|:---------------------------------|:---------|:-----------------------------|:------------------------------|:--------------------------------------|:-----------------------------|:---------------------------------------|
| (70) Cancelado, IsReschedule=N   | 32,439   | 27.7                         | 44.5                          | 26.7                                  | 43.2                         | 16.7                                   |
| (70) Cancelado, IsReschedule=Y   | 68,782   | 53.2                         | 71.9                          | 45.9                                  | 54.5                         | 17.2                                   |
| (60) Concluido, IsReschedule=Y   | 45,460   | 36.4                         | 49.9                          | 5.6                                   | 67.1                         | 62.5                                   |
| (60) Concluido, IsReschedule=NaN | 295,165  | 5.3                          | 15.2                          | 9.5                                   | 16.6                         | 4.0                                    |
| (60) Concluido, ScheduleReturn=Y | 29,247   | 10.0                         | 25.7                          | 14.2                                  | 97.2                         | 15.3                                   |
| (60) Concluido, ScheduleReturn=N | 301,959  | 9.2                          | 19.1                          | 8.5                                   | 16.2                         | 11.4                                   |

Cancelados con IsReschedule=Y: 90.8% tiene algun turno posterior (N: 79.4%) y en 65.3% el turno siguiente tambien tiene IsReschedule=Y (N: 15.7%): el flag marca el par cancelado / re-agendado.

En filas canceladas IsReschedule es colineal con ScheduleStatus (dos vias de cancelacion del sistema de origen): IsReschedule=N & ScheduleStatus=(70) Cancelado: 36,424; IsReschedule=Y & ScheduleStatus=NaN: 77,013.

Composicion del turno concluido segun ScheduleReturn:

| ScheduleReturn   |   % con mantenimiento |   % con reparacion |   % con diagnostico |   % con campania/recall |
|:-----------------|----------------------:|-------------------:|--------------------:|------------------------:|
| N                |                  69.3 |                7.5 |                18.5 |                    20.0 |
| Y                |                  15.0 |               31.0 |                35.6 |                    12.4 |

Figura: `reports/figures/eda/05_calidad_cobertura_leakage_turnos_pendientes.png`

## E. Inconsistencias puntuales

### E1. Tabla de problemas

| tabla        | problema                                                                    | magnitud                                                                                                                                                                                                                        | decision recomendada                                                                                                                                                                                                                                       |
|:-------------|:----------------------------------------------------------------------------|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| agenda       | ModelYear = 0 o < 2005                                                      | 43 turnos / 29 vehiculos                                                                                                                                                                                                        | flag: edad no confiable (usar WSD si existe); excluir vehiculos si tampoco hay WSD                                                                                                                                                                         |
| agenda       | ModelYear nulo                                                              | 4,431 turnos / 821 vehiculos con id (2,896 sin vehicle_id)                                                                                                                                                                      | imputar edad por WSD; si no, flag                                                                                                                                                                                                                          |
| agenda       | WarrantyStartDate.year - ModelYear fuera de [-1, +1]                        | 940 turnos (0.2%)                                                                                                                                                                                                               | dejar con flag; la edad se calcula por WSD                                                                                                                                                                                                                 |
| agenda       | EffectiveCheckinDate < 2024-01-01                                           | 4 turnos (1 en 2001 con DaysInDealer 8.461)                                                                                                                                                                                     | ya corregido en eventos.py: event_date usa el check-in solo si |check-in - ScheduleDate| <= 45 d                                                                                                                                                           |
| agenda       | |EffectiveCheckinDate - ScheduleDate| > 30 dias                             | 564 turnos (> 10 d: 2,406; > 45 d: 328)                                                                                                                                                                                         | dejar; eventos.py usa el check-in solo si |gap| <= 45 d (328 turnos caen a ScheduleDate)                                                                                                                                                                   |
| agenda       | (60) Concluido sin EffectiveCheckinDate                                     | 45,433 turnos (13.3% de los concluidos; 2024: 22.9%)                                                                                                                                                                            | dejar: event_date cae a ScheduleDate (coincide con el check-in el 91,7% de las veces)                                                                                                                                                                      |
| agenda       | EffectiveCheckoutDate < EffectiveCheckinDate                                | 130 turnos                                                                                                                                                                                                                      | dejar con flag (no afecta target)                                                                                                                                                                                                                          |
| agenda       | (80) No asistio con EffectiveCheckinDate                                    | 1,556 turnos (5.7% de los no-show)                                                                                                                                                                                              | dejar: prevalece StatusARG; flag                                                                                                                                                                                                                           |
| agenda       | KM (snapshot) = 0 en turnos concluidos                                      | 7 turnos                                                                                                                                                                                                                        | no usar KM como feature (ver B3)                                                                                                                                                                                                                           |
| agenda       | KM (snapshot) > 500.000 / > 1.000.000                                       | 673 / 123 turnos concluidos                                                                                                                                                                                                     | no usar KM como feature (ver B3)                                                                                                                                                                                                                           |
| agenda       | VehicleCurrentKM < 100 en turnos concluidos                                 | 10,076 turnos (2.9%); valores tipicos 1, 10, 3, 12, 30                                                                                                                                                                          | corregir: tratar como nulo (placeholder)                                                                                                                                                                                                                   |
| agenda       | VehicleCurrentKM > 500.000 / > 1.000.000 en concluidos                      | 617 / 162 turnos                                                                                                                                                                                                                | corregir: > 1.000.000 a nulo; 500k-1M flag                                                                                                                                                                                                                 |
| agenda       | VehicleCurrentKM decrece entre visitas concluidas consecutivas (> 1.000 km) | 6,948 pares (2.9%) en 6,347 vehiculos de 72,940                                                                                                                                                                                 | corregir: km acumulado por vehiculo = maximo acumulado (running max) de lecturas validas; flag por vehiculo                                                                                                                                                |
| agenda       | Ritmo implausible > 300 km/dia entre visitas (excluye mismo dia)            | 8,104 pares (3.4%)                                                                                                                                                                                                              | flag; recortar km/dia a p99 al construir features de uso                                                                                                                                                                                                   |
| agenda       | ServicePriceDiscount: no es un descuento                                    | no nulo en 220,118 items (34.8%); = 0 en 72,589 (62,727 campanias; el 100% de los items con ServiceFordFixedPriceFlag=Y y precio no nulo vale 0); mediana 29,829,050; mediana 1° service 2025Q1 27,266,000 -> 2026Q3 48,445,000 | dejar solo como flag 'precio informado'; preguntar al mentor (parece precio de lista x100; informado en 44-52% de los items de mantenimiento desde 2024Q1, para el 1° service recien desde 2025Q1; 0 = item de precio fijo Ford / campania, no 'sin dato') |
| agenda       | ServiceLaborCost casi vacio                                                 | 4,703 items (0.7%), todos Mantenimiento y anio 2026                                                                                                                                                                             | excluir columna                                                                                                                                                                                                                                            |
| sales/agenda | WarrantyStartDate distinto entre sales y agenda (mismo vehiculo)            | 406 de 42,150 vehiculos con WSD en ambas (1.0%); |dif| > 30 d: 25; > 365 d: 2; mediana de las diferencias 8 d; ademas 56 con WSD nula en sales                                                                                  | dejar: usar WSD de sales cuando existe (la WSD de la agenda = DeliveryDate de sales en 98.8% de los casos)                                                                                                                                                 |
| agenda       | WarrantyStartDate posterior al primer turno concluido                       | 1,505 vehiculos; > 30 d: 198; > 365 d: 3                                                                                                                                                                                        | dejar: edad negativa en el primer turno se recorta a 0 (PDI / entrega)                                                                                                                                                                                     |
| sales        | DeliveryDate < 2020 (2013, 2015)                                            | 3 filas                                                                                                                                                                                                                         | excluir de la poblacion 'vendidos 2024-2026' (reventa/usado)                                                                                                                                                                                               |
| sales        | SalesDate > DeliveryDate                                                    | 3 filas (las mismas 3)                                                                                                                                                                                                          | excluir                                                                                                                                                                                                                                                    |
| sales        | SalesDate > RegistrationDate                                                | 9,806 filas (16.5%)                                                                                                                                                                                                             | dejar: RegistrationDate no se usa; preguntar semantica                                                                                                                                                                                                     |
| sales        | WarrantyStartDate < DeliveryDate                                            | 1,425 filas                                                                                                                                                                                                                     | dejar: usar min(WSD, DeliveryDate) como inicio de vida util                                                                                                                                                                                                |
| sales        | PersonType raro (25 / 29 / 30) o nulo                                       | 25: 656, 29: 153, 30: 9, nulo: 35 (25 es 80% canal HR)                                                                                                                                                                          | dejar: categoria 'otro' con flag                                                                                                                                                                                                                           |
| sales        | Status 1 / 2 / 3 (no ACCEPTED)                                              | 107 filas; 77 sin DeliveryDate; presencia en agenda 57.9% vs 71.1%                                                                                                                                                              | excluir de la poblacion hasta que tengan DeliveryDate (venta no concretada)                                                                                                                                                                                |
| sales        | ModelShortName GLOBAL RANGER - FSAO                                         | 1 fila (ModelYear 2013, canal UNKNOWN, sin ModelCode ni WSD)                                                                                                                                                                    | excluir                                                                                                                                                                                                                                                    |
| sales        | dealer_id nulo / WarrantyStartDate nulo / DeliveryDate nulo                 | 139 / 180 / 90 filas                                                                                                                                                                                                            | dejar; WSD nulo se imputa con DeliveryDate                                                                                                                                                                                                                 |

### E2. Coherencia WarrantyStartDate vs ModelYear (turnos)

|   WarrantyStartDate.year - ModelYear |   turnos |
|-------------------------------------:|---------:|
|                                  -11 |        1 |
|                                   -1 |   125472 |
|                                    0 |   325009 |
|                                    1 |    35483 |
|                                    2 |      755 |
|                                    3 |       94 |
|                                    4 |       39 |
|                                    5 |       28 |
|                                    6 |        6 |
|                                    7 |        9 |
|                                    9 |        3 |
|                                   16 |        4 |
|                                2,024 |        1 |

### E3. Gap check-in vs fecha del turno

Turnos con check-in: 313,224. Mismo dia: 91.7%; |gap| <= 1 dia: 95.8%; gap < 0: 0.6%; gap > 10 d: 1,917; gap < -10 d: 489.

Check-in no nulo por StatusARG: (30) Agendado: 0.2%, (40) En progreso: 100.0%, (60) Concluido: 86.7%, (70) Cancelado: 0.0%, (80) No asistio: 5.7%, (90) Concluido sin OS: 81.1%.

|   EffectiveCheckinDate - ScheduleDate (dias) |   turnos |
|---------------------------------------------:|---------:|
|                                           -7 |       40 |
|                                           -6 |       47 |
|                                           -5 |       34 |
|                                           -4 |       79 |
|                                           -3 |      112 |
|                                           -2 |       92 |
|                                           -1 |      961 |
|                                            0 |   287128 |
|                                            1 |    12019 |
|                                            2 |     3253 |
|                                            3 |     3143 |
|                                            4 |      985 |
|                                            5 |      661 |
|                                            6 |      697 |
|                                            7 |      553 |
|                                            8 |      415 |
|                                            9 |      266 |
|                                           10 |      251 |
|                                           11 |      186 |
|                                           12 |      182 |
|                                           13 |      168 |
|                                           14 |      180 |

### E4. Odometro (VehicleCurrentKM) entre visitas concluidas consecutivas

|                                                                 | valor   |
|:----------------------------------------------------------------|:--------|
| pares de visitas concluidas consecutivas (VehicleCurrentKM > 0) | 236,276 |
| km decrece                                                      | 7,973   |
| km decrece > 1.000                                              | 6,948   |
| km decrece > 10.000                                             | 5,481   |
| km igual                                                        | 19,231  |
| km/dia mediana                                                  | 69.3    |
| km/dia p95                                                      | 250.2   |
| km/dia p99                                                      | 1,230.7 |
| pares > 300 km/dia (excl. mismo dia)                            | 8,104   |

E4b. Lo mismo excluyendo placeholders (VehicleCurrentKM en [100, 1.000.000]): 227,977 pares; retrocede > 1.000 km en 5,058 (2.2%) de 4,684 vehiculos; > 300 km/dia (excl. mismo dia): 6,485 (2.8%); km/dia mediana 69.9, p99 881.

### E5. ServicePriceDiscount en items de mantenimiento, por trimestre

| trimestre   |   items de mantenimiento |   items con precio no nulo |   % no nulo |   % igual a 0 (sobre no nulos) |    mediana |   1° service: no nulos |   1° service: mediana |
|:------------|-------------------------:|---------------------------:|------------:|-------------------------------:|-----------:|-----------------------:|----------------------:|
| 2024Q1      |                   21,188 |                      9,791 |          46 |                              0 | 21,701,700 |                      7 |                     0 |
| 2024Q2      |                   20,029 |                     10,403 |          52 |                              0 | 25,768,750 |                      5 |                     0 |
| 2024Q3      |                   23,886 |                     10,410 |          44 |                              1 | 28,848,150 |                     34 |                     0 |
| 2024Q4      |                   24,928 |                     12,132 |          49 |                              1 | 30,703,700 |                     53 |                     0 |
| 2025Q1      |                   26,325 |                      7,644 |          29 |                              1 | 31,775,600 |                    448 |            27,266,000 |
| 2025Q2      |                   26,316 |                     15,224 |          58 |                              1 | 32,322,950 |                  2,570 |            28,019,000 |
| 2025Q3      |                   28,218 |                     16,053 |          57 |                              1 | 36,182,650 |                  2,625 |            32,210,000 |
| 2025Q4      |                   28,434 |                     15,830 |          56 |                              1 | 39,528,400 |                  3,155 |            34,244,000 |
| 2026Q1      |                   30,747 |                     19,099 |          62 |                              1 | 43,364,450 |                  3,480 |            36,715,000 |
| 2026Q2      |                   28,771 |                     19,056 |          66 |                              2 | 49,413,900 |                  2,884 |            43,731,000 |
| 2026Q3      |                   19,592 |                     13,219 |          67 |                              1 | 54,756,100 |                  1,909 |            48,445,000 |

Fuera de rango en la figura (excluye mismo dia): km/dia < -50: 6,075; km/dia > 400: 5,551; pares del mismo dia (no graficados): 4,176. Gap check-in fuera de [-10, 30]: 853.

Figura: `reports/figures/eda/05_calidad_cobertura_leakage_checkin_y_odometro.png`

## F. Turnos sin vehicle_id o sin customer_id

### F1. Magnitud y perfil

|                           | sin vehicle_id   | sin customer_id   |
|:--------------------------|:-----------------|:------------------|
| turnos                    | 2,897            | 9,398             |
| % de turnos               | 0.6              | 1.9               |
| (60) Concluido            | 2,066            | 6,294             |
| mantenimientos concluidos | 1,186            | 3,948             |
| sin el otro id tampoco    | 418              | 418               |
| % ModelYear nulo          | 100.0            | 5.7               |
| % WarrantyStartDate nulo  | 100.0            | 6.4               |
| % KM nulo                 | 99.2             | 7.5               |
| origen Dealer             | 2,896            | 7,141             |

Vehiculos con algun turno sin customer_id: 2,961; de ellos 1,760 tienen otro turno con customer_id (se puede imputar el cliente del vehiculo).

StatusARG de los turnos sin vehicle_id: (60) Concluido: 2,066, (80) No asistio: 510, (90) Concluido sin OS: 260, (30) Agendado: 40, (40) En progreso: 20, (70) Cancelado: 1.

## G. Duplicados logicos

Filas identicas en la agenda cruda: 19,554 (3.1%), en 11,575 schedule_id; por StatusARG: (60) Concluido: 19,492, (40) En progreso: 32, (90) Concluido sin OS: 20, (80) No asistio: 5, (30) Agendado: 3, (70) Cancelado: 2. Se eliminan en `appointments()`.

schedule_id con >1 valor de: StatusARG: 4, ScheduleDate: 0, EffectiveCheckinDate: 0, KM: 0, vehicle_id: 0, customer_id: 0, dealer_id: 0 (las columnas de nivel turno son consistentes).

### G1. Mismo vehiculo, misma ScheduleDate, distinto schedule_id: 24,952 pares (vehiculo, fecha), 52,339 turnos, 19,594 vehiculos

| combinacion de StatusARG                         | pares (vehiculo, fecha)   | % de los pares   |
|:-------------------------------------------------|:--------------------------|:-----------------|
| (60) Concluido | (70) Cancelado                  | 14,572                    | 58.4             |
| (60) Concluido | (60) Concluido                  | 2,988                     | 12.0             |
| (70) Cancelado | (70) Cancelado                  | 2,630                     | 10.5             |
| (70) Cancelado | (80) No asistio                 | 1,134                     | 4.5              |
| (60) Concluido | (70) Cancelado | (70) Cancelado | 1,097                     | 4.4              |
| (70) Cancelado | (90) Concluido sin OS           | 557                       | 2.2              |
| (60) Concluido | (80) No asistio                 | 424                       | 1.7              |
| (60) Concluido | (60) Concluido | (70) Cancelado | 252                       | 1.0              |
| (70) Cancelado | (70) Cancelado | (70) Cancelado | 227                       | 0.9              |
| (60) Concluido | (90) Concluido sin OS           | 170                       | 0.7              |

(vehiculo, event_date) con >1 turno (60) Concluido: 2,239 (4,603 turnos); con >1 mantenimiento concluido el mismo dia: 332 (667 turnos).

Mantenimientos concluidos a <= 7 dias de otro mantenimiento concluido del mismo vehiculo: 988 (mismo maint_number: 673); a <= 30 dias: 2,201 (mismo maint_number: 1,087); sobre 134,172 pares consecutivos.

### G2. Cancelaciones y no-show 'administrativos' (re-agendamiento) vs. abandono

|                                                       | turnos   | %                  |
|:------------------------------------------------------|:---------|:-------------------|
| (70) Cancelado con vehicle_id                         | 101,221  | 100.0              |
| con un (60) Concluido del mismo vehiculo el MISMO dia | 17,144   | 16.9               |
| con un (60) Concluido a <= 7 dias (antes o despues)   | 54,752   | 54.1               |
| seguido de un (60) Concluido dentro de 30 dias        | 57529    | 56.83504411139981  |
| (80) No asistio con vehicle_id                        | 26,727   | 100.0              |
| seguido de un (60) Concluido dentro de 30 dias        | 7624     | 28.525461144161333 |

Cancelaciones fuera del rango [-45, 45] o sin turno concluido del vehiculo (no graficadas): 19,691 de 101,221.

Figura: `reports/figures/eda/05_calidad_cobertura_leakage_duplicados_cancelaciones.png`

## H. Cobertura sales vs agenda

### H1. Vehiculos vendidos (sales) que aparecen en la agenda

|                             | ventas   | % con >=1 turno en agenda   | % con >=1 mantenimiento concluido   |
|:----------------------------|:---------|:----------------------------|:------------------------------------|
| todas                       | 59,384   | 71.1                        | 62.2                                |
| > 180 dias antes del CUTOFF | 50,773   | 80.4                        | 72.2                                |
| > 365 dias                  | 39,928   | 88.5                        | 82.2                                |
| > 548 dias                  | 27,197   | 90.4                        | 85.1                                |
| > 730 dias                  | 14,712   | 91.4                        | 86.6                                |

### H1c. Cobertura a exposicion fija (365 dias desde la venta) por cohorte de venta: si es estable, la caida en cohortes recientes es solo falta de tiempo

| trimestre de venta   | ventas (con >=365 d de exposicion)   | % con >=1 turno dentro de los 365 d de la venta   |
|:---------------------|:-------------------------------------|:--------------------------------------------------|
| 2024Q1               | 4,890                                | 68.2                                              |
| 2024Q2               | 5,521                                | 73.0                                              |
| 2024Q3               | 6,767                                | 72.8                                              |
| 2024Q4               | 5,867                                | 71.3                                              |
| 2025Q1               | 6,691                                | 70.8                                              |
| 2025Q2               | 6,483                                | 71.8                                              |
| 2025Q3               | 3,709                                | 69.8                                              |

### H1b. Presencia en agenda de ventas con mas de 365 dias, por segmento

| segmento     |   % en agenda (ventas > 365 d) |
|:-------------|-------------------------------:|
| Ford Blue    |                           91.4 |
| Ford Pro     |                           82.0 |
| CONSORTIUM   |                           88.8 |
| DIRECT SALES |                           80.7 |
| HR           |                           67.5 |
| ROR          |                           90.5 |
| 25           |                           69.2 |
| 29           |                           83.3 |
| F            |                           89.6 |
| J            |                           87.6 |

### H2. Vehiculos de la agenda por ModelYear y presencia en sales

| ModelYear (agenda)   |   NO en sales |   en sales |
|:---------------------|--------------:|-----------:|
| <2022                |         35718 |          2 |
| 2022                 |         10568 |          4 |
| 2023                 |         11543 |        412 |
| 2024                 |         11322 |      14772 |
| 2025                 |           302 |      25627 |
| 2026                 |            88 |       1394 |

ModelYear >= 2024 y NO en sales: 11,712; de ellos con WSD en 2023: 10,189 (vendidos antes del extracto), con WSD >= 2024-01-01: 1,427.

Vehiculos de la agenda con WSD >= 2024-01-01: 43,700; en sales 42,205 (96.6%); NO en sales 1,495 (3.4%), TMA: 7DC: 562, 8DC: 456, 6DC: 374, TA1: 62, 7BC: 20; WSD por anio: 2024: 1203, 2025: 214, 2026: 78.

Vehiculos en ambas tablas: 42,211. Primer turno anterior a DeliveryDate: 1,798 (4.3%); mas de 30 dias antes: 227. Meses entre DeliveryDate y primer turno: mediana 6.1, p90 12.3.

Vehiculos en ambas tablas cuyo customer_id de sales aparece en al menos un turno: 70.1% (29,576 de 42,211).

Figura: `reports/figures/eda/05_calidad_cobertura_leakage_cobertura.png`

## I. Sintesis: columnas con riesgo de leakage y exclusiones

### I1. Columnas con riesgo de leakage y regla de uso

| columna                                                              | por que hay riesgo                                                                                                                                                           | regla de uso                                                                                                                                                        |
|:---------------------------------------------------------------------|:-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------|:--------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| KM                                                                   | snapshot del odometro a la extraccion (constante por vehiculo; = lectura del ultimo turno concluido en el 91,7%)                                                             | NO usar como feature. Usar VehicleCurrentKM de turnos con event_date < t (running max).                                                                             |
| ConnectedStatusARG                                                   | snapshot a la extraccion (constante en 99,9% de los vehiculos; 'Sin informacion' crece con la fecha de entrega)                                                              | NO usar en backtest. En scoring actual, solo con advertencia. Alternativa segura: 'generacion con conectividad' derivada de TMA/WSD.                                |
| IsReschedule (en turnos (70) Cancelado)                              | Y indica que el turno fue re-agendado: describe un evento POSTERIOR a la cancelacion                                                                                         | Usar solo para cancelaciones cuyo re-agendamiento tambien es anterior a t; regla simple: ignorar el flag de cancelaciones ocurridas en los 30 dias previos a t.     |
| IsReschedule (en turnos (60) Concluido)                              | Y indica que este turno es re-agendamiento de uno anterior (pasado)                                                                                                          | Usable si event_date < t.                                                                                                                                           |
| ScheduleReturn                                                       | Y = visita de retorno a <= 30 dias de otra visita (97% tiene turno previo a <= 30 d); 85% sin item de mantenimiento                                                          | Usable como feature si event_date < t. Para el target: no contar un retorno como 'mantenimiento programado' (pregunta al mentor).                                   |
| SurveyResponseDate / SurveyStarRating                                | se responde ANTES del turno (mediana 8 dias antes de ScheduleDate; nunca despues del checkout); solo canales digitales; rating ~4,75 en todos los status                     | Usable solo si SurveyResponseDate < t. Semantica: calificacion de la reserva en la app, no del servicio. Sirve como proxy de fecha de reserva (7,5% de los turnos). |
| Turnos con ScheduleDate >= t (cualquier status)                      | no hay fecha de creacion: no se sabe si el turno existia en t                                                                                                                | Excluir por completo de las features en backtest. 'Tiene turno agendado' solo en el scoring actual, como regla operativa post-modelo.                               |
| StatusARG (30)/(40) de turnos con ScheduleDate < t                   | estado abierto a la extraccion; stale si ScheduleDate <= CUTOFF-30 d                                                                                                         | En backtest con t <= CUTOFF-30 d tratar (30)/(40) atrasados como 'no concluido' con flag; en el target, no cuentan como mantenimiento concluido.                    |
| EffectiveCheckoutDate, DaysInDealer, WorkDaysInDealer, EffectiveTerm | resultado de la visita (posterior al check-in)                                                                                                                               | Usables solo de turnos con EffectiveCheckoutDate < t.                                                                                                               |
| customer_id de la agenda                                             | cambia en el 20,8% de los vehiculos (27,6% de los que tienen >=2 turnos con cliente)                                                                                         | Usar el customer_id del ultimo turno con event_date < t; no usar 'alguna vez tuvo otro cliente'.                                                                    |
| WarrantyStartDate, ModelYear, TMA, ShortVehicleModelGroupTreated     | atributos fijos del vehiculo (0-1 vehiculos con variacion)                                                                                                                   | Usables sin restriccion (edad, generacion).                                                                                                                         |
| Region, DealerStateOrZone, dealer_id                                 | atributos del dealer del turno; varian solo si el vehiculo cambia de dealer                                                                                                  | Usables como atributos del ultimo turno < t.                                                                                                                        |
| ServicePriceDiscount                                                 | precio (no descuento) en escala x100; informado en ~50% de los items de mantenimiento desde 2024Q1 (1° service recien desde 2025Q1); 0 = item de precio fijo Ford / campania | Solo como flag 'precio informado' o precio deflactado; confirmar unidad con el mentor.                                                                              |
| ServiceLaborCost                                                     | 0,7% no nulo, solo 2026                                                                                                                                                      | Excluir.                                                                                                                                                            |
| maint_number (ServiceMaintenance)                                    | numero de service declarado; +1 entre services consecutivos en 77,5%                                                                                                         | Usable como proxy de historia previa (correlacion 0,76 con la edad); tomar el maximo observado hasta t.                                                             |

### I2. Exclusiones y correcciones recomendadas, con conteos

| tabla   | exclusion / correccion                                           | filas o vehiculos afectados                    | tratamiento                                                              |
|:--------|:-----------------------------------------------------------------|:-----------------------------------------------|:-------------------------------------------------------------------------|
| agenda  | filas identicas                                                  | 19,554 filas-item                              | excluir (ya lo hace appointments())                                      |
| agenda  | turnos sin vehicle_id                                            | 2,897 turnos (1,186 mantenimientos concluidos) | excluir: no se pueden asignar a una unidad usuario-vehiculo              |
| agenda  | turnos sin customer_id pero con vehicle_id                       | 8,980 turnos                                   | dejar: imputar customer_id del vehiculo (posible en 1,760 vehiculos)     |
| agenda  | vehiculos con ModelYear 0/<2005 y sin WSD                        | 29 vehiculos (28 sin WSD)                      | excluir los sin WSD; el resto usa edad por WSD                           |
| agenda  | vehiculos sin WSD ni ModelYear (edad desconocida)                | 772 vehiculos (1,257 sin WSD)                  | flag edad desconocida; imputar por TMA si se quiere retener              |
| agenda  | check-in con fecha imposible (< 2024-01-01)                      | 4 turnos                                       | corregir event_date = ScheduleDate                                       |
| agenda  | VehicleCurrentKM < 100 o > 1.000.000 (concluidos)                | 10,238 turnos                                  | corregir a nulo                                                          |
| agenda  | pendientes stale ((30)/(40) con ScheduleDate <= CUTOFF-30 d)     | 962 turnos                                     | tratar como no concluidos, con flag                                      |
| agenda  | mantenimientos concluidos a <= 7 dias de otro del mismo vehiculo | 988 turnos                                     | colapsar en un solo evento (queda el primero)                            |
| agenda  | turnos con ScheduleDate > CUTOFF                                 | 3,826 turnos                                   | excluir del backtest; usar solo en la regla operativa del scoring actual |
| sales   | GLOBAL RANGER / DeliveryDate < 2020 / Status != ACCEPTED         | 110 filas                                      | excluir de la poblacion de vendidos                                      |
