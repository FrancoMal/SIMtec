# Tablas de verificacion del EDA 05 (script `scripts/eda/05_calidad_cobertura_leakage_verificacion.py`)

sales 59,384 | agenda filas 631,623 | turnos 492,442 | turnos con vehiculo 489,545 | vehiculos con id 111,752 | mant. concluidos 222,889

## V1. KM es snapshot; VehicleCurrentKM es lectura del turno


### V1.1 KM vs VehicleCurrentKM del ultimo turno, tres definiciones

| definicion                                                  |   vehiculos |   con KM y VCK no nulos |   % KM == VCK (sobre vehiculos) |   % KM == VCK (sobre ambos no nulos) |   % KM > VCK |   % KM < VCK |
|:------------------------------------------------------------|------------:|------------------------:|--------------------------------:|-------------------------------------:|-------------:|-------------:|
| ultimo turno (60) Concluido (fila real)                     |      104349 |                  100236 |                            91.7 |                                 95.5 |          2.3 |          2.2 |
| ultimo (60) Concluido con VCK no nulo (= .last() de pandas) |      104349 |                  100236 |                            91.7 |                                 95.5 |          2.3 |          2.2 |
| ultimo turno de cualquier status con VCK no nulo            |      106370 |                  101763 |                            91.7 |                                 95.9 |          0.5 |          3.6 |

_KM constante por vehiculo: 82,340 de 82,347 con >=2 lecturas (100.0%); VCK varia en 73,813 de 75,688 (97.5%)._

### V1.2 Relacion KM vs VCK del ultimo concluido, por ConnectedStatusARG (hipotesis: KM viene de telemetria en conectados)

| ConnectedStatusARG              |   KM < VCK |   KM > VCK |   igual |   vehiculos |
|:--------------------------------|-----------:|-----------:|--------:|------------:|
| Conectado                       |        0.7 |        3.5 |    95.8 |       36301 |
| No Conectado                    |        3.2 |        1.7 |    95.1 |       45384 |
| No tiene Conectividad           |        4.2 |        1.4 |    94.5 |       10269 |
| Sin Información de Conectividad |        1.5 |        0.7 |    97.8 |        8282 |

### V1.2b Cuando KM > VCK del ultimo concluido: exceso mediano y antiguedad del ultimo turno

| ConnectedStatusARG              |   vehiculos |   mediana KM - VCK |   mediana dias CUTOFF - ultimo turno |
|:--------------------------------|------------:|-------------------:|-------------------------------------:|
| Conectado                       |        1285 |               7210 |                                  230 |
| No Conectado                    |         794 |               8018 |                                  417 |
| No tiene Conectividad           |         142 |              10896 |                                  315 |
| Sin Información de Conectividad |          60 |              10992 |                                  298 |

### V1.3 Turnos concluidos: KM == VCK segun sea o no el ultimo concluido del vehiculo

| es_ultimo   |   turnos concluidos |   % KM == VCK |
|:------------|--------------------:|--------------:|
| False       |              234384 |           2.5 |
| True        |              100236 |          95.5 |

### V1.4 Turnos concluidos por anio: % KM == VCK y % que son el ultimo del vehiculo (confusion)

|   ScheduleDate |   % KM == VCK |   % es ultimo |
|---------------:|--------------:|--------------:|
|           2024 |          13   |          12.3 |
|           2025 |          20.9 |          20.7 |
|           2026 |          66.1 |          65.8 |

### V1.5 Nulos de VehicleCurrentKM por StatusARG

| StatusARG             |   % VCK nulo |   turnos |
|:----------------------|-------------:|---------:|
| (30) Agendado         |         76.5 |     3953 |
| (40) En progreso      |         60.4 |     1832 |
| (60) Concluido        |          0   |   342691 |
| (70) Cancelado        |        100   |   101222 |
| (80) No asistio       |         71.9 |    27237 |
| (90) Concluido sin OS |          2.8 |    15507 |
KM >= max(VCK) (crudo): 92.9%; KM >= max(VCK) con VCK limpio (100..1M): 92.9%.

## V2. ConnectedStatusARG es snapshot y esta confundido con la generacion

Vehiculos con >=2 turnos: 85,143; con >1 valor de ConnectedStatusARG: 74 (0.1%).

'Conectado' con WSD < 2023-07-01: 0.6% (n=54,691); WSD >= 2023-07-01: 66.4% (n=55,804).


### V2.1 ConnectedStatusARG por trimestre de WSD (trimestres citados)

| WSD    |   Conectado |   No Conectado |   No tiene Conectividad |   Sin Información de Conectividad |   vehiculos |
|:-------|------------:|---------------:|------------------------:|----------------------------------:|------------:|
| 2023Q2 |         0.6 |           81.8 |                     8.3 |                               9.3 |        3990 |
| 2023Q3 |        62.9 |           21.5 |                    10.8 |                               4.8 |        6354 |
| 2024Q2 |        82.5 |            1.6 |                    13   |                               2.9 |        4900 |
| 2025Q1 |        66.6 |            1   |                    16.2 |                              16.2 |        6042 |
| 2025Q4 |        49.8 |            1.1 |                    14   |                              35.1 |        2984 |
| 2026Q2 |        34.3 |            0.4 |                     5.9 |                              59.4 |         899 |
| 2026Q3 |         4.2 |            0   |                     3.2 |                              92.6 |         310 |

### V2.2 Resultado del turno por ConnectedStatusARG, sin control (reproduce B2b)

| ConnectedStatusARG              |   % concluido |   % mant. concluido |   turnos |
|:--------------------------------|--------------:|--------------------:|---------:|
| Conectado                       |          68.2 |                41.8 |   189186 |
| No Conectado                    |          70.8 |                47.1 |   235596 |
| No tiene Conectividad           |          69.3 |                47.9 |    44388 |
| Sin Información de Conectividad |          68.7 |                49.6 |    23272 |

### V2.3 Mismo control por generacion/edad: vehiculos con WSD 2023-07..2024-12, turnos 2025-01..CUTOFF

| ConnectedStatusARG              |   % concluido |   % mant. concluido |   % no asistio |   % cancelado |   turnos |
|:--------------------------------|--------------:|--------------------:|---------------:|--------------:|---------:|
| Conectado                       |          69.1 |                44.3 |            4.9 |          22   |   107772 |
| No Conectado                    |          69.4 |                52.1 |            5.4 |          22   |     9279 |
| No tiene Conectividad           |          70.1 |                47.6 |            5.8 |          20.7 |    19383 |
| Sin Información de Conectividad |          72.5 |                63.6 |            2.7 |          22.4 |     1827 |

_Controlando la generacion, la brecha Conectado vs No tiene Conectividad en mantenimiento concluido se reduce a pocos puntos._
## V3. SurveyResponseDate es anterior al turno

Turnos con survey: 36,920 de 492,442 (7.5%). Por status: (60) Concluido: 26,072, (70) Cancelado: 8,363, (80) No asistio: 1,341, (90) Concluido sin OS: 682, (30) Agendado: 396, (40) En progreso: 66


### V3.1 Lags survey vs fechas del turno

| lag                   |     n |   min |   p5 |   mediana |   p95 |   max |   % < 0 |   % = 0 |   % > 0 |   n > 0 |
|:----------------------|------:|------:|-----:|----------:|------:|------:|--------:|--------:|--------:|--------:|
| survey - checkout     | 26724 |  -350 |  -30 |        -9 |    -2 |     0 |  100    |    0    |    0    |       0 |
| survey - checkin      | 24839 |  -349 |  -24 |        -8 |    -2 |   314 |   99.94 |    0.01 |    0.04 |      11 |
| survey - ScheduleDate | 36920 |  -365 |  -26 |        -8 |    -2 |     0 |   99.99 |    0.01 |    0    |       0 |

### V3.2 % de turnos con survey por ScheduleSource

| ScheduleSource   |   % con survey |   turnos |
|:-----------------|---------------:|---------:|
| CAF              |            0   |     1202 |
| Dealer           |            0   |   357401 |
| FordPass         |           29.1 |   103964 |
| Mobile           |           30.9 |    10092 |
| WEB              |           18   |    19783 |

### V3.3 Rating medio por StatusARG

| StatusARG             |   size |   mean |
|:----------------------|-------:|-------:|
| (30) Agendado         |    396 |   4.75 |
| (40) En progreso      |     66 |   4.76 |
| (60) Concluido        |  26072 |   4.75 |
| (70) Cancelado        |   8363 |   4.73 |
| (80) No asistio       |   1341 |   4.66 |
| (90) Concluido sin OS |    682 |   4.7  |
Turnos con survey cuyo (vehicle_id, SurveyResponseDate) se repite en otro turno: 752 de 36,920 (2.0%); por (customer_id, SurveyResponseDate): 1,517 (4.1%).


### V3.4 Combinaciones de status cuando la misma survey aparece en >1 turno del vehiculo

| StatusARG                              |   grupos |
|:---------------------------------------|---------:|
| (60) Concluido | (70) Cancelado        |      237 |
| (70) Cancelado | (70) Cancelado        |       89 |
| (70) Cancelado | (80) No asistio       |       13 |
| (60) Concluido | (80) No asistio       |        9 |
| (70) Cancelado | (90) Concluido sin OS |        9 |
| (60) Concluido | (60) Concluido        |        4 |
Lag survey - ultimo checkout concluido previo del mismo vehiculo (estricto <): n con previo 24,823 (67.2%); mediana 140 d; <=14 d: 3.3% de los que tienen previo, 2.2% del total.

Anticipacion (ScheduleDate - survey): mediana 8, p75 14, p90 21, <=30 d: 97.3%.

Surveys con fecha > CUTOFF: 9; minima: 2023-10-13.


### V3.5 Reservas futuras conocidas en t gracias a la survey (unico proxy de fecha de reserva)

| t          |   turnos con ScheduleDate >= t y survey < t |   vehiculos |   concluidos luego |   mant. concluidos luego |
|:-----------|--------------------------------------------:|------------:|-------------------:|-------------------------:|
| 2025-07-01 |                                         436 |         426 |                315 |                      291 |
| 2026-01-01 |                                         482 |         477 |                352 |                      331 |
| 2026-06-01 |                                         449 |         443 |                315 |                      290 |
## V4. Left-censoring

Vehiculos con id: 111,752; con WSD: 110,495; WSD < 2024-01-01: 66,795 = 59.8% de todos, 60.5% de los que tienen WSD.


### V4.1 Reproduccion de A1 con codigo propio

| t          |   activos |   % sin mant. |   mediana dsl |   p90 dsl |   techo |   % gap > 0 |   mediana gap |
|:-----------|----------:|--------------:|--------------:|----------:|--------:|------------:|--------------:|
| 2024-07-01 |     41478 |          33.4 |            80 |       158 |     182 |        77.7 |             3 |
| 2025-01-01 |     62975 |          28   |           111 |       292 |     366 |        67.6 |             2 |
| 2026-01-01 |     94657 |          23.8 |           163 |       525 |     731 |        53.9 |             1 |
| 2026-08-25 |    111184 |          21.3 |           202 |       705 |     967 |        48.5 |             0 |
A3 reproducida (share de la distribucion de dsl al CUTOFF que supera cada ventana): 182 d: 53.5%, 366 d: 28.6%, 547 d: 17.5%, 731 d: 8.9%


### V4.2 Misma poblacion (vehiculos con >=1 turno en los 182 d previos al CUTOFF, n=54667): % sin mantenimiento observado segun profundidad de historia, total y por edad

|   historia (dias) |   % sin mant. observado |   <1 |   1-2 |   2-3 |   3-5 |   5-8 |   8+ |
|------------------:|------------------------:|-----:|------:|------:|------:|------:|-----:|
|               182 |                    25.6 | 31.9 |  15.6 |  20.8 |  21.1 |  39   | 62.6 |
|               366 |                    16.1 | 31   |   5.7 |   8.3 |  10.9 |  27   | 53.9 |
|               547 |                    13.2 | 31   |   4.7 |   4.2 |   7   |  21.2 | 48.5 |
|               731 |                    12   | 31   |   4.6 |   2.8 |   5.2 |  17.6 | 45.7 |
|               967 |                    11.2 | 31   |   4.6 |   2.5 |   3.9 |  14.5 | 43.1 |

_Aisla el efecto de la profundidad de historia del efecto calendario/poblacion que mezcla A2._
## V5. maint_number del ultimo service como proxy de historia invisible

Primer mantenimiento concluido observado (fila real, maint_number no nulo): 87,531 vehiculos; con WSD 87,069. Correlacion Pearson(maint_number, edad) = 0.761; Spearman = 0.801. Edad > 2 anios: 26,518; de ellos con 1° service: 554 (2.1%).

Mantenimientos concluidos con maint_number nulo (has_maint por regex sin ServiceMaintenance): 0.


### V5.1 gap = maint_number del ultimo service - n mantenimientos observados, por visibilidad de la historia (tasa de falsos positivos del proxy)

|                                                                   |   vehiculos |   % gap > 0 |   % gap >= 2 |   % gap < 0 |   mediana gap |
|:------------------------------------------------------------------|------------:|------------:|-------------:|------------:|--------------:|
| ('2025-01-01', 'WSD < 2024-01-01 (historia invisible posible)')   |       40484 |        74.8 |         63   |         1   |             3 |
| ('2025-01-01', 'WSD >= 2024-01-01 (toda la historia es visible)') |        4627 |         4.9 |          1.6 |         2.9 |             0 |
| ('2026-08-25', 'WSD < 2024-01-01 (historia invisible posible)')   |       48821 |        77.9 |         65.1 |         2.5 |             3 |
| ('2026-08-25', 'WSD >= 2024-01-01 (toda la historia es visible)') |       38196 |        10.7 |          2.5 |         3.7 |             0 |
Incremento entre mantenimientos consecutivos (n=134,172): +1 77.5%, +2 7.4%, >=3 5.2%, 0 5.3%, <0 4.7%.

Edad mediana al service por maint_number: 1°: 0.73, 2°: 1.28, 3°: 1.65, 4°: 1.97, 8°: 3.20, 10°: 3.72, 12°: 4.04, 13°: 4.08, 19°: 5.69, 20°: 6.77


### V5.2 ServiceName por ServiceMaintenance (codigos 1-3, 11-13, 19-20)

| ServiceName             |   1.0 |   2.0 |   3.0 |   11.0 |   12.0 |   13.0 |   19.0 |   20.0 |
|:------------------------|------:|------:|------:|-------:|-------:|-------:|-------:|-------:|
| 13° Maintenance service |     0 |     0 |     0 |      0 |      0 |   3539 |      0 |      0 |
| 1ª Maintenance review   | 15235 |     0 |     0 |   1273 |      0 |      0 |      0 |      0 |
| 1° Maintenance service  | 48553 |     0 |     0 |   5128 |      0 |      0 |      0 |      0 |
| 20ª Maintenance review  |     0 |     0 |     0 |      0 |      0 |      0 |      0 |    807 |
| 20° Maintenance service |     0 |     0 |     0 |      0 |      0 |      0 |      0 |   3354 |
| 2ª Maintenance review   |     0 | 13897 |     0 |      0 |   1174 |      0 |      0 |      0 |
| 2° Maintenance service  |     0 | 31975 |     0 |      0 |   4453 |      0 |      0 |      0 |
| 3ª Maintenance review   |     0 |     0 | 10175 |      0 |      0 |    975 |      0 |      0 |
| 3° Maintenance service  |     0 |     0 | 22248 |      0 |      0 |      0 |      0 |      0 |
| 9ª Maintenance review   |     0 |     0 |     0 |      0 |      0 |      0 |    321 |      0 |
| 9° Maintenance service  |     0 |     0 |     0 |      0 |      0 |      0 |    962 |      0 |
## V6. Turnos futuros / pendientes


### V6.1 Reproduccion de D1

|                                                          |   valor |
|:---------------------------------------------------------|--------:|
| ScheduleDate > CUTOFF                                    |    3826 |
| (30)                                                     |    3321 |
| (70)                                                     |     498 |
| (40)                                                     |       7 |
| otros                                                    |       0 |
| con item mant.                                           |    2460 |
| vehiculos (30)                                           |    3263 |
| pendientes total                                         |    5785 |
| pendientes <= CUTOFF                                     |    2457 |
| stale (<= CUTOFF-30)                                     |     962 |
| (40) stale                                               |     687 |
| (30) stale                                               |     275 |
| pendientes <= CUTOFF-180                                 |     377 |
| filas-item (30) con ScheduleDate > CUTOFF (agenda cruda) |    4185 |
| (60) con ScheduleDate > CUTOFF                           |       0 |
(40) En progreso: check-in no nulo 100.0%, checkout nulo 99.9%; ultimo checkout 2026-08-25; ultimo check-in 2026-08-27. Reservas futuras por mes: 2026-08: 2,259, 2026-09: 1,534, 2026-10: 23, 2026-11: 9, 2026-12: 1

Columnas que podrian ser fecha de creacion: ['ShortVehicleModelGroupTreated'] (ninguna).

## V7. IsReschedule y ScheduleReturn


### V7.1 IsReschedule x StatusARG (turnos)

| IsReschedule   |   (30) Agendado |   (40) En progreso |   (60) Concluido |   (70) Cancelado |   (80) No asistio |   (90) Concluido sin OS |
|:---------------|----------------:|-------------------:|-----------------:|-----------------:|------------------:|------------------------:|
| N              |               0 |                  0 |                0 |            32439 |                 1 |                       0 |
| NaN            |            3475 |               1554 |           297026 |                0 |             23607 |                   13595 |
| Y              |             478 |                278 |            45665 |            68783 |              3629 |                    1912 |

### V7.2 En filas canceladas: IsReschedule x ScheduleStatus (agenda cruda)

| IsReschedule   |   (70) Cancelado |   NaN |
|:---------------|-----------------:|------:|
| N              |            36424 |     0 |
| Y              |                0 | 77013 |

### V7.3 Cancelados segun IsReschedule: que hay antes y despues (mismo vehiculo)

| IsReschedule   |   turnos |   % turno posterior <=7d |   % <=30d |   % algun turno posterior |   % siguiente es concluido (<=30d) |   % siguiente tiene IsReschedule=Y |   % siguiente el MISMO dia |   % turno anterior <=30d |   % anterior cancelado <=30d |
|:---------------|---------:|-------------------------:|----------:|--------------------------:|-----------------------------------:|-----------------------------------:|---------------------------:|-------------------------:|-----------------------------:|
| N              |    32439 |                     27.7 |      44.5 |                      79.4 |                               26.7 |                               15.7 |                       11   |                     43.2 |                         16.7 |
| Y              |    68782 |                     53.2 |      71.9 |                      90.8 |                               45.9 |                               65.3 |                       14.4 |                     54.5 |                         17.2 |

### V7.4 Concluidos segun IsReschedule y ScheduleReturn

| grupo                 |   turnos |   % turno anterior <=30d |   % anterior cancelado <=30d |   % anterior concluido <=30d |   % con mant. |   % con reparacion |   % con diagnostico |
|:----------------------|---------:|-------------------------:|-----------------------------:|-----------------------------:|--------------:|-------------------:|--------------------:|
| (60) IsReschedule=Y   |    45460 |                     67.1 |                         62.5 |                          3.5 |          68.6 |                8.5 |                18.7 |
| (60) IsReschedule=NaN |   295165 |                     16.6 |                          4   |                          9.8 |          64.5 |                9.4 |                20   |
| (60) ScheduleReturn=Y |    29247 |                     97.2 |                         15.3 |                         75   |          15   |               31   |                35.6 |
| (60) ScheduleReturn=N |   301959 |                     16.2 |                         11.4 |                          2.7 |          69.3 |                7.5 |                18.5 |
Inverso: entre concluidos con un turno previo a <=30 d (79,355), ScheduleReturn=Y en 35.8%; con previo concluido a <=30 d (30,584): 71.7%.

## V8. Cancelaciones y no-show


### V8.1 Reproduccion de G2 (join completo, sin merge_asof)

|                                |    valor |
|:-------------------------------|---------:|
| (70) con vehicle_id            | 101221   |
| % con (60) el mismo dia        |     16.9 |
| % con (60) a <=7 d             |     54.1 |
| % seguido de (60) en 30 d      |     56.8 |
| (70) con item de mantenimiento |  25796   |
| % con (60) con mant. a <=7 d   |     46.5 |
| (80) con vehicle_id            |  26727   |
| % seguido de (60) en 30 d      |     28.5 |
Mantenimientos concluidos a <=7 d de otro del mismo vehiculo: 988 (mismo maint_number 673); a <=30 d: 2,201; mismo dia: 335.

Pares (vehiculo, ScheduleDate) con >1 schedule_id: 24,952; turnos 52,339.

## V9. Cobertura sales vs agenda

Vehiculos en ambas tablas: 42,211.

Con WSD en ambas: 42,150; iguales 41,745 (99.0%); distintas 405; |dif| > 30 d: 25; mediana |dif| entre distintas: 8. Con WSD en agenda pero nula en sales: 56. WSD agenda == DeliveryDate sales: 98.8%.

Vehiculos de la agenda con WSD >= 2024-01-01: 43,700; en sales 42,205 (96.6%).

MY >= 2024 y no en sales: 11,712; con WSD en 2023: 10,189.


### V9.1 Presencia en agenda de los vendidos, tres definiciones

| ventas   |     n |   % >=1 turno |   % >=1 (60) |   % >=1 mant. concluido |
|:---------|------:|--------------:|-------------:|------------------------:|
| todas    | 59384 |          71.1 |         68.1 |                    62.2 |
| > 365 d  | 39928 |          88.5 |         86.3 |                    82.2 |
| > 730 d  | 14712 |          91.4 |         90.2 |                    86.6 |

### V9.2 Ventas > 365 d por segmento

|              |   % en agenda |
|:-------------|--------------:|
| Ford Blue    |          91.4 |
| Ford Pro     |          82   |
| CONSORTIUM   |          88.8 |
| DIRECT SALES |          80.7 |
| HR           |          67.5 |
| ROR          |          90.5 |

### V9.3 % de vendidos con >=1 turno dentro de los 365 d de la venta, por trimestre de venta (exposicion completa)

| SalesDate   |   ventas |   pct_turno_365d |
|:------------|---------:|-----------------:|
| 2024Q1      |     4890 |             68.2 |
| 2024Q2      |     5521 |             73   |
| 2024Q3      |     6767 |             72.8 |
| 2024Q4      |     5867 |             71.3 |
| 2025Q1      |     6691 |             70.8 |
| 2025Q2      |     6483 |             71.8 |
| 2025Q3      |     3709 |             69.8 |

_Si es estable, la caida de cobertura en cohortes recientes es solo falta de tiempo._
Primer turno antes de DeliveryDate: 1,798 (4.3%); > 30 d antes: 227.

Comprador aparece en algun turno: 29,576 de 42,211 (70.1%).

## V10. Inconsistencias puntuales

Check-in < 2024-01-01: 4 turnos; fechas ['2001-10-12', '2023-12-28', '2023-12-28', '2023-12-29']; DaysInDealer [8461.0, 342.0, nan, nan].

Turnos con check-in: 313,224; mismo dia 91.7%; |gap| > 30: 564; |gap| > 45 (eventos.py usa ScheduleDate): 328; event_date != check-in entre turnos con check-in: 328.

(60) sin check-in: 45,433 de 342,691 (13.3%); en 2024: 22.9%; 2025: 8.8%; 2026: 7.6%.

VCK < 100 en concluidos: 10,076 (2.9%); top valores: {1.0: 6049, 10.0: 839, 3.0: 357, 12.0: 234, 30.0: 226}; VCK > 1e6: 162; > 5e5: 617.


### V10.1 Retrocesos de odometro y ritmo implausible, crudo vs. con placeholders excluidos

| filtro                                             |   pares |   retrocede > 1.000 km |   % pares |   vehiculos con retroceso |   retrocede > 10.000 |   > 300 km/dia (excl. mismo dia) |   % > 300 km/dia |   km/dia mediana |   km/dia p99 |
|:---------------------------------------------------|--------:|-----------------------:|----------:|--------------------------:|---------------------:|---------------------------------:|-----------------:|-----------------:|-------------:|
| VCK > 0 (script original)                          |  236276 |                   6948 |       2.9 |                      6347 |                 5481 |                             8104 |              3.4 |             69.3 |       1230.7 |
| VCK en [100, 1.000.000] (placeholders y >1M fuera) |  227977 |                   5058 |       2.2 |                      4684 |                 3717 |                             6485 |              2.8 |             69.9 |        881.5 |
Vehiculos con ModelYear 0/<2005: 29; sin WSD: 28.

sales: DeliveryDate < 2020: 3 ([2013, 2015, 2015]); Status != ACCEPTED: 107, sin DeliveryDate: 77; GLOBAL RANGER: 1; PersonType: {'F': 34900, 'J': 23631, '25': 656, '29': 153, nan: 35, '30': 9}; PersonType 25 canal HR: 80.3%.

ServicePriceDiscount: no nulo 220,118 (34.8%); == 0: 72,589; mediana 29,829,050.


### V10.2 ServicePriceDiscount en items de mantenimiento por trimestre (refuta 'informado desde 2025')

| ScheduleDate   |   items |   pct_no_nulo |       mediana |   mediana 1° service |
|:---------------|--------:|--------------:|--------------:|---------------------:|
| 2024Q1         |   21188 |            46 |   2.17017e+07 |           0          |
| 2024Q2         |   20029 |            52 |   2.57688e+07 |           0          |
| 2024Q3         |   23886 |            44 |   2.88482e+07 |           0          |
| 2024Q4         |   24928 |            49 |   3.07037e+07 |           0          |
| 2025Q1         |   26325 |            29 |   3.17756e+07 |           2.7266e+07 |
| 2025Q2         |   26316 |            58 |   3.2323e+07  |           2.8019e+07 |
| 2025Q3         |   28218 |            57 |   3.61826e+07 |           3.221e+07  |
| 2025Q4         |   28434 |            56 |   3.95284e+07 |           3.4244e+07 |
| 2026Q1         |   30747 |            62 |   4.33644e+07 |           3.6715e+07 |
| 2026Q2         |   28771 |            66 |   4.94139e+07 |           4.3731e+07 |
| 2026Q3         |   19592 |            67 |   5.47561e+07 |           4.8445e+07 |
| 2026Q4         |      27 |             0 | nan           |         nan          |
ServiceLaborCost no nulo: 4,703 (0.7%); anios: {2026: 4703}; ServiceType: {'Mantenimiento': 4703}; mediana 576,380.

ServiceFordFixedPrice valores: {0.0: 96364, 131000.0: 12846, 170500.0: 157} (misma escala que ServiceLaborCost, no que ServicePriceDiscount).

Vehiculos con >1 customer_id: 23,245 = 20.8% de 111,752 vehiculos; 27.3% de los 85,143 con >=2 turnos; 27.6% de los con >=2 customer_id no nulos.

