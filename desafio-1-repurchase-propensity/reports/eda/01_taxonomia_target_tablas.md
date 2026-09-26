# Apéndice generado: tablas del EDA 01 (taxonomía de eventos y target)

Generado por `scripts/eda/01_taxonomia_target.py` sobre `data/interim/agenda.parquet` (631623 filas, 19554 duplicadas eliminadas) y `sales.parquet`. CUTOFF = 2026-08-25.

### 0.1 Volumen

|                                        | valor      |
|:---------------------------------------|:-----------|
| filas agenda (ítems)                   | 631623     |
| filas totalmente duplicadas eliminadas | 19554      |
| filas ítem tras dedup                  | 612069     |
| turnos (schedule_id)                   | 492442     |
| filas tabla appointments()             | 492442     |
| vehículos con turno                    | 111752     |
| CUTOFF                                 | 2026-08-25 |

### 0.2 Turnos por StatusARG

| StatusARG             |   turnos |    % |
|:----------------------|---------:|-----:|
| (30) Agendado         |     3953 |  0.8 |
| (40) En progreso      |     1832 |  0.4 |
| (60) Concluido        |   342691 | 69.6 |
| (70) Cancelado        |   101222 | 20.6 |
| (80) No asistio       |    27237 |  5.5 |
| (90) Concluido sin OS |    15507 |  3.1 |

### 0.3 schedule_id con más de un valor en columnas de nivel turno

|                       |   schedule_ids con >1 valor |
|:----------------------|----------------------------:|
| vehicle_id            |                           0 |
| customer_id           |                           0 |
| dealer_id             |                           0 |
| StatusARG             |                           4 |
| ScheduleDate          |                           0 |
| ScheduleSource        |                           0 |
| IsReschedule          |                           5 |
| ScheduleReturn        |                           4 |
| KM                    |                           0 |
| VehicleCurrentKM      |                           0 |
| EffectiveCheckinDate  |                           0 |
| EffectiveCheckoutDate |                           0 |
| DaysInDealer          |                           0 |

StatusARG varía en 4 turnos (mezcla (70)/(80) en ítems sin tipo): irrelevante en volumen.

### 1.1 Clase de ítem asignada a cada ServiceType (filas ítem, tras dedup)

|    | item_class     | ServiceType                   |   ítems |
|---:|:---------------|:------------------------------|--------:|
|  0 | MANT           | Mantenimiento                 |  268690 |
|  1 | DIAG           | Diagnóstico                   |   99811 |
|  2 | CAMPANA_RECALL | Campañas de Servicio          |   68316 |
|  3 | SIN_ITEM       | (nulo)                        |   58275 |
|  4 | REPAR          | Reparación                    |   42792 |
|  5 | PUD            | Pick Up & Delivery            |   16707 |
|  6 | CAMPANA_RECALL | Campañas De Servicio          |   14227 |
|  7 | SERV_GRAL      | Servicios Generales           |   10256 |
|  8 | OTRO           | Accesorios                    |    6444 |
|  9 | GARANTIA       | Mantenimiento                 |    5467 |
| 10 | OTRO           | Alineación/Balanceo/Cubiertas |    5370 |
| 11 | MOVIL          | Mobile Service                |    5159 |
| 12 | OTRO           | Chapa y Pintura               |    4225 |
| 13 | ACEITE_FILTRO  | Servicios Generales           |    2601 |
| 14 | OTRO           | Lavado                        |    1532 |
| 15 | MOVIL          | Taller Móvil                  |    1368 |
| 16 | INSPECCION     | Servicios Generales           |     781 |
| 17 | CONTACTLESS    | Mantenimiento                 |      48 |

### 1.2 Consistencia ServiceMaintenance vs ServiceName/ServiceType

|                                                                    |      n |
|:-------------------------------------------------------------------|-------:|
| ítems con ServiceMaintenance no nulo                               | 268690 |
| ... de los cuales ServiceType != Mantenimiento                     |      0 |
| ítems 'Maintenance service/review' sin número                      |      0 |
| ítems ServiceType Mantenimiento sin número (Guarantee+Contactless) |   5515 |

### 1.3 Las 15 combinaciones de ítems más frecuentes por turno y su StatusARG

| combo                |   (30) Agendado |   (40) En progreso |   (60) Concluido |   (70) Cancelado |   (80) No asistio |   (90) Concluido sin OS |   total |   % turnos |
|:---------------------|----------------:|-------------------:|-----------------:|-----------------:|------------------:|------------------------:|--------:|-----------:|
| MANT                 |            1960 |                350 |           158565 |            18110 |              9564 |                    2470 |  191019 |       38.8 |
| DIAG                 |             544 |                573 |            47344 |             7602 |              6844 |                    5826 |   68733 |       14   |
| SIN_ITEM             |               2 |                  0 |              127 |            58113 |                21 |                       8 |   58271 |       11.8 |
| CAMPANA_RECALL+MANT  |             185 |                 45 |            32599 |             3771 |              1772 |                     662 |   39034 |        7.9 |
| REPAR                |             288 |                206 |            24586 |             3622 |              2278 |                    1762 |   32742 |        6.6 |
| CAMPANA_RECALL       |              59 |                 31 |            12980 |             1389 |              1294 |                     802 |   16555 |        3.4 |
| CAMPANA_RECALL+DIAG  |              81 |                 65 |             7462 |              996 |              1295 |                     938 |   10837 |        2.2 |
| MANT+PUD             |             113 |                 26 |             7428 |             1161 |               212 |                      97 |    9037 |        1.8 |
| OTRO                 |              41 |                 33 |             6916 |              665 |               824 |                     423 |    8902 |        1.8 |
| DIAG+MANT            |              73 |                 26 |             6750 |              848 |               382 |                     293 |    8372 |        1.7 |
| SERV_GRAL            |             169 |                201 |             4461 |              764 |               432 |                     323 |    6350 |        1.3 |
| CAMPANA_RECALL+REPAR |              30 |                 26 |             3659 |              442 |               400 |                     340 |    4897 |        1   |
| GARANTIA             |               1 |                  0 |             3204 |              321 |               404 |                     371 |    4301 |        0.9 |
| MANT+OTRO            |              20 |                 15 |             3263 |              341 |               199 |                     100 |    3938 |        0.8 |
| MANT+MOVIL           |              37 |                 12 |             3370 |              157 |               122 |                      58 |    3756 |        0.8 |

Combinaciones distintas: 262. Las 15 primeras cubren 94.8% de los turnos.

### 1.4 Definición preliminar is_completed_maintenance = (60) Concluido & algún ítem con ServiceMaintenance

|                                       |   turnos |   vehículos |
|:--------------------------------------|---------:|------------:|
| (60) & has_maint  [target preliminar] |   222889 |       87531 |
| (60) cualquier ítem                   |   342691 |      104349 |
| (60) sin ítem de mantenimiento        |   119802 |       59932 |

### 1.5 Composición del target preliminar por combinación de ítems (top 10)

| combo                    |   turnos |    % |
|:-------------------------|---------:|-----:|
| MANT                     |   158565 | 71.1 |
| CAMPANA_RECALL+MANT      |    32599 | 14.6 |
| MANT+PUD                 |     7428 |  3.3 |
| DIAG+MANT                |     6750 |  3   |
| MANT+MOVIL               |     3370 |  1.5 |
| MANT+OTRO                |     3263 |  1.5 |
| CAMPANA_RECALL+MANT+PUD  |     1770 |  0.8 |
| MANT+REPAR               |     1468 |  0.7 |
| CAMPANA_RECALL+DIAG+MANT |     1321 |  0.6 |
| MANT+SERV_GRAL           |      966 |  0.4 |

### 2.1 Perfil de cada StatusARG: presencia de fechas efectivas, km, días en taller y tipo de ítems

| StatusARG             |   % no nulo EffectiveCheckinDate |   % no nulo EffectiveCheckoutDate |   % no nulo KM |   % no nulo VehicleCurrentKM |   % no nulo DaysInDealer |   % no nulo SurveyStarRating |   mediana DaysInDealer |   % has_maint |   % has_recall |   % has_diag |   % ScheduleReturn=Y |
|:----------------------|---------------------------------:|----------------------------------:|---------------:|-----------------------------:|-------------------------:|-----------------------------:|-----------------------:|--------------:|---------------:|-------------:|---------------------:|
| (30) Agendado         |                              0.2 |                               0   |           85.1 |                         23.5 |                      0   |                         10   |                    nan |          64.4 |           11.2 |         20.2 |                  8.3 |
| (40) En progreso      |                            100   |                               0.1 |           87.7 |                         39.6 |                    100   |                          3.6 |                     16 |          29   |           12.2 |         39.5 |                 15.8 |
| (60) Concluido        |                             86.7 |                             100   |           97.6 |                        100   |                    100   |                          7.6 |                      1 |          65   |           19.1 |         19.8 |                  8.5 |
| (70) Cancelado        |                              0   |                               0   |           95.9 |                          0   |                      0   |                          8.3 |                    nan |          25.5 |            7.7 |         10.3 |                  0   |
| (80) No asistio       |                              5.7 |                               0.1 |           87.7 |                         28.1 |                      0.1 |                          4.9 |                      0 |          46.9 |           19.4 |         32.9 |                  9.8 |
| (90) Concluido sin OS |                             81.1 |                              96.4 |           97.2 |                         97.2 |                     96.4 |                          4.4 |                      4 |          26.2 |           20.5 |         48.8 |                 17   |

### 2.2 (90) Concluido sin OS: combinaciones de ítems (top 10)

| combo                |   turnos |    % |
|:---------------------|---------:|-----:|
| DIAG                 |     5826 | 37.6 |
| MANT                 |     2470 | 15.9 |
| REPAR                |     1762 | 11.4 |
| CAMPANA_RECALL+DIAG  |      938 |  6   |
| CAMPANA_RECALL       |      802 |  5.2 |
| CAMPANA_RECALL+MANT  |      662 |  4.3 |
| OTRO                 |      423 |  2.7 |
| GARANTIA             |      371 |  2.4 |
| CAMPANA_RECALL+REPAR |      340 |  2.2 |
| SERV_GRAL            |      323 |  2.1 |

### 2.3 (90) con vehicle_id (n=15247): ¿hay un turno concluido del mismo vehículo cerca?

| ventana (días)   |   turnos (90) con un (60) del mismo vehículo |   turnos (90) con un (60)+mantenimiento |   % (60) |   % (60)+mant |
|:-----------------|---------------------------------------------:|----------------------------------------:|---------:|--------------:|
| [-30, -1]        |                                         2542 |                                    1363 |     16.7 |           8.9 |
| [0, 0]           |                                          210 |                                     107 |      1.4 |           0.7 |
| [1, 30]          |                                         2646 |                                     593 |     17.4 |           3.9 |
| [-30, 30]        |                                         4830 |                                    2033 |     31.7 |          13.3 |
| [1, 90]          |                                         5770 |                                    2378 |     37.8 |          15.6 |

### 2.4 (90) que incluían un ítem de mantenimiento

|                            |   valor |
|:---------------------------|--------:|
| n                          |  3977   |
| vehículos                  |  3659   |
| con (60)+mant en (0,30]    |   206   |
| con (60)+mant en [-30,-1]  |   155   |
| con (60)+mant el mismo día |    65   |
| con (60)+mant en (0,90]    |   542   |
| % checkin no nulo          |    75   |
| % VehicleCurrentKM no nulo |    96.3 |
| mediana DaysInDealer       |     4   |

### 2.5 (90) como % de los turnos de cada dealer

|                                                    |   valor |
|:---------------------------------------------------|--------:|
| dealers                                            |    95   |
| mediana % (90) por dealer                          |     2.1 |
| máximo % (90) por dealer                           |    13.6 |
| dealers con >10% de (90)                           |     6   |
| dealers sin (90)                                   |     7   |
| % de los (90) que concentra el dealer con más (90) |    10.7 |

### 2.6 Datos de la figura status90_perfil (%)

|                       |   Check-in registrado |   Check-out registrado |   Km al ingreso (VehicleCurrentKM) |   Incluye ítem de mantenimiento |   Otro turno concluido en 30 días |
|:----------------------|----------------------:|-----------------------:|-----------------------------------:|--------------------------------:|----------------------------------:|
| (60) Concluido        |                  86.7 |                  100   |                              100   |                            65   |                              10.1 |
| (90) Concluido sin OS |                  81.1 |                   96.4 |                               97.2 |                            26.2 |                              19   |
| (80) No asistio       |                   5.7 |                    0.1 |                               28.1 |                            46.9 |                              28.6 |
| (70) Cancelado        |                   0   |                    0   |                                0   |                            25.5 |                              57.5 |

### 3.1 Turnos (60) Concluido que cambiarían de clase según se incluya cada familia en el target

| clase                               |   turnos (60) que la incluyen |   ... sin ítem de mantenimiento |   ... solo esa clase (+PUD/móvil) |   vehículos (solo esa clase) |   vehículos sin ningún (60)+mant |
|:------------------------------------|------------------------------:|--------------------------------:|----------------------------------:|-----------------------------:|---------------------------------:|
| Guarantee                           |                          4131 |                            3789 |                              3258 |                         2831 |                              305 |
| Service campaign / Recall           |                         65620 |                           27258 |                             13704 |                        11170 |                             2495 |
| Oil and filter change               |                          2021 |                            1127 |                               822 |                          748 |                              189 |
| Contactless service                 |                            39 |                              20 |                                11 |                           11 |                                2 |
| Inspección Ford / Revision de Viaje |                           486 |                             414 |                               302 |                          293 |                               94 |

### 3.2 Perfil de las familias candidatas (filas ítem)

|                                          | Guarantee    | Oil and filter change   | Campañas/Recall                         | Maintenance service/review               |
|:-----------------------------------------|:-------------|:------------------------|:----------------------------------------|:-----------------------------------------|
| ítems                                    | 5467         | 2601                    | 82543                                   | 268690                                   |
| ítems por año                            | {2024: 5467} | {2026: 2601}            | {2024: 25632, 2025: 40947, 2026: 15964} | {2024: 87649, 2025: 104724, 2026: 76317} |
| mediana edad (meses desde WarrantyStart) | 16.5         | 32.8                    | 13.6                                    | 22.1                                     |
| mediana VehicleCurrentKM                 | 30446.0      | 65496.0                 | 24174.0                                 | 45325.0                                  |
| ServiceDuration                          | {60.0: 5467} | {60.0: 2601}            | {60.0: 68316, 120.0: 14227}             | {60.0: 184803, 120.0: 83887}             |
| FordFixedPriceFlag                       | {'N': 5467}  | {'N': 2601}             | {'Y': 68316, 'N': 14227}                | {'N': 268690}                            |

### 3.3 'Service campaign' vs 'Recall' por año (mismo ServiceType, cambio de nombre en 2026)

| ServiceName      |   2024 |   2025 |   2026 |
|:-----------------|-------:|-------:|-------:|
| Recall           |      0 |      0 |  14227 |
| Service campaign |  25632 |  40947 |   1737 |

### 3.4 'Oil and filter change': % de turnos que además traen ítem de mantenimiento

|                                                          |   valor |
|:---------------------------------------------------------|--------:|
| % turnos con Oil&filter que también tienen mantenimiento |    41.8 |
| dealers que lo usan                                      |    87   |
| % del dealer que más lo usa                              |    19.8 |

### 3.5 Escenarios de definición del evento objetivo: turnos y vehículos que cumplen

|                                                        |   turnos |   vehículos |   Δ turnos vs A |   Δ vehículos vs A |
|:-------------------------------------------------------|---------:|------------:|----------------:|-------------------:|
| A. (60) & ítem Maintenance service/review [preliminar] |   222889 |       87531 |               0 |                  0 |
| B. A + Oil and filter change                           |   224016 |       87821 |            1127 |                290 |
| C. B + Guarantee                                       |   227805 |       88156 |            4916 |                625 |
| D. C + Campañas/Recall                                 |   254596 |       93434 |           31707 |               5903 |
| E. A + (90) con ítem mantenimiento                     |   226947 |       88157 |            4058 |                626 |
| F. Visita efectiva: (60) o (90), cualquier ítem        |   358198 |      105709 |          135309 |              18178 |

### 4.1 ServiceMaintenance (número) -> ServiceName observado

|   n | ServiceName (ítems)                                           |
|----:|:--------------------------------------------------------------|
|   1 | 1ª Maintenance review (14854), 1° Maintenance service (45466) |
|   2 | 2ª Maintenance review (13333), 2° Maintenance service (30342) |
|   3 | 3ª Maintenance review (9778), 3° Maintenance service (21490)  |
|   4 | 4ª Maintenance review (6327), 4° Maintenance service (16446)  |
|   5 | 5ª Maintenance review (4501), 5° Maintenance service (14012)  |
|   6 | 6ª Maintenance review (3545), 6° Maintenance service (13876)  |
|   7 | 7ª Maintenance review (2482), 7° Maintenance service (9909)   |
|   8 | 8ª Maintenance review (2234), 8° Maintenance service (8630)   |
|   9 | 9ª Maintenance review (1807), 9° Maintenance service (7931)   |
|  10 | 10ª Maintenance review (1521), 10° Maintenance service (6693) |
|  11 | 1ª Maintenance review (1229), 1° Maintenance service (5027)   |
|  12 | 2ª Maintenance review (1123), 2° Maintenance service (4371)   |
|  13 | 13° Maintenance service (3467), 3ª Maintenance review (939)   |
|  14 | 4ª Maintenance review (748), 4° Maintenance service (2849)    |
|  15 | 15° Maintenance service (2303), 5ª Maintenance review (586)   |
|  16 | 6ª Maintenance review (486), 6° Maintenance service (1816)    |
|  17 | 7ª Maintenance review (375), 7° Maintenance service (1334)    |
|  18 | 8ª Maintenance review (356), 8° Maintenance service (1143)    |
|  19 | 9ª Maintenance review (316), 9° Maintenance service (938)     |
|  20 | 20ª Maintenance review (786), 20° Maintenance service (3321)  |

### 4.2 Familia del catálogo por mes de turno (cambio de 'service' a 'review')

| ScheduleDate   |   Maintenance review |   Maintenance service |
|:---------------|---------------------:|----------------------:|
| 2025-10        |                    0 |                  9538 |
| 2025-11        |                    0 |                  8311 |
| 2025-12        |                    1 |                  9472 |
| 2026-01        |                 2477 |                  8390 |
| 2026-02        |                 7951 |                   536 |
| 2026-03        |                10209 |                    21 |
| 2026-04        |                 9712 |                    11 |
| 2026-05        |                 8946 |                    14 |
| 2026-06        |                 9083 |                     9 |
| 2026-07        |                 9278 |                     6 |
| 2026-08        |                 8703 |                     4 |
| 2026-09        |                  939 |                     1 |
| 2026-10        |                   19 |                     0 |
| 2026-11        |                    7 |                     0 |
| 2026-12        |                    1 |                     0 |

Primer ítem 'review': 2025-12-30; último ítem 'service': 2026-09-11.

### 4.3 ¿La familia depende del dealer, de la generación o de la fuente?

|                                               |   valor |
|:----------------------------------------------|--------:|
| mediana % review por dealer (todo el período) |   0.246 |
| p10 % review por dealer                       |   0.218 |
| p90 % review por dealer                       |   0.296 |
| mínimo % review por dealer desde 2026-02      |   0.924 |
| dealers con <99% review desde 2026-02         |  21     |
| dealers con ítems desde 2026-02               |  94     |

### 4.4 Familia x generación (ítems)

| familia             |   RANGER |   RANGER (P375) |   RANGER (P703) |   RANGER RAPTOR |   RANGER RAPTOR (P703) |
|:--------------------|---------:|----------------:|----------------:|----------------:|-----------------------:|
| Maintenance review  |      163 |           19652 |           47493 |               0 |                     18 |
| Maintenance service |     1458 |          119016 |           80799 |               2 |                     89 |

### 4.5 Familia x ScheduleSource (ítems)

| familia             |   CAF |   Dealer |   FordPass |   Mobile |   WEB |
|:--------------------|------:|---------:|-----------:|---------:|------:|
| Maintenance review  |     9 |    37461 |      22312 |     3133 |  4411 |
| Maintenance service |    68 |   137259 |      51089 |     4294 |  8654 |

### 4.6 Ítems con ServiceMaintenance >= 11 por generación

| ShortVehicleModelGroupTreated   |   False |   True |   % n>=11 |
|:--------------------------------|--------:|-------:|----------:|
| RANGER                          |    1516 |    105 |       6.5 |
| RANGER (P375)                   |  106896 |  31772 |      22.9 |
| RANGER (P703)                   |  126658 |   1634 |       1.3 |
| RANGER RAPTOR                   |       2 |      0 |       0   |
| RANGER RAPTOR (P703)            |     105 |      2 |       1.9 |

### 4.7 % de ítems con n >= 11 por ModelYear

|         |   2012.0 |   2013.0 |   2014.0 |   2015.0 |   2016.0 |   2017.0 |   2018.0 |   2019.0 |   2020.0 |   2021.0 |   2022.0 |   2023.0 |   2024.0 |   2025.0 |   2026.0 |
|:--------|---------:|---------:|---------:|---------:|---------:|---------:|---------:|---------:|---------:|---------:|---------:|---------:|---------:|---------:|---------:|
| ítems   |    408   |      462 |     1883 |   1928   |   3972   |   6140   |   5811   |   8687   |   6610   |  19739   |  37227   |  45689   |  81470   |    45728 |    603   |
| % n>=11 |     58.3 |       63 |       62 |     56.2 |     54.4 |     49.1 |     38.6 |     34.2 |     34.2 |     28.2 |     18.3 |      8.6 |      1.4 |        1 |      1.7 |

### 4.8 Número de service vs km real al ingreso y edad del vehículo, turnos (60)

|   n |   P703 ítems |   P703 mediana VehicleCurrentKM |   P703 mediana edad (meses) |   P375 ítems |   P375 mediana VehicleCurrentKM |   P375 mediana edad (meses) |   ServiceMonth (=12n) |
|----:|-------------:|--------------------------------:|----------------------------:|-------------:|--------------------------------:|----------------------------:|----------------------:|
|   1 |        44325 |                           16008 |                         8.4 |         4445 |                           11060 |                        12.2 |                    12 |
|   2 |        28230 |                           32130 |                        14.5 |         7690 |                           20548 |                        18.9 |                    24 |
|   3 |        14926 |                           48416 |                        17.7 |        10467 |                           30614 |                        24.3 |                    36 |
|   4 |         7905 |                           64650 |                        19.8 |        10872 |                           40696 |                        28.1 |                    48 |
|   5 |         4100 |                           80710 |                        21.4 |        11225 |                           50870 |                        31.5 |                    60 |
|   6 |         2265 |                           96481 |                        22.4 |        11974 |                           61242 |                        36.5 |                    72 |
|   7 |         1126 |                          112827 |                        23.9 |         9192 |                           71063 |                        38   |                    84 |
|   8 |          766 |                          126269 |                        24   |         8342 |                           81110 |                        40.3 |                    96 |
|   9 |          336 |                          143440 |                        25.5 |         7921 |                           91185 |                        42.2 |                   108 |
|  10 |          171 |                          152229 |                        25   |         6774 |                          101265 |                        45.3 |                   120 |
|  11 |           98 |                          125086 |                        24.5 |         5227 |                          111483 |                        47   |                   132 |
|  12 |           81 |                          127695 |                        24.6 |         4591 |                          121482 |                        49.1 |                   144 |
|  13 |           54 |                          125426 |                        18.3 |         3735 |                          131392 |                        49.5 |                   156 |
|  14 |           53 |                           47238 |                        14.4 |         3007 |                          141523 |                        51.5 |                   168 |
|  15 |           33 |                           32992 |                        11.5 |         2432 |                          151208 |                        53.8 |                   180 |
|  16 |           34 |                           17050 |                         9.1 |         1915 |                          161508 |                        59.4 |                   192 |
|  17 |           30 |                           18150 |                        11.7 |         1441 |                          171523 |                        60.5 |                   204 |
|  18 |           10 |                           18552 |                         8.3 |         1284 |                          181712 |                        64.9 |                   216 |
|  19 |            5 |                           17303 |                        10   |         1062 |                          191998 |                        68.3 |                   228 |
|  20 |           73 |                            2628 |                         2.4 |         3416 |                          221749 |                        82.6 |                   240 |

### 4.9 ¿n es un hito de km o de meses?

|                                                               | valor   |
|:--------------------------------------------------------------|:--------|
| P703: mediana VehicleCurrentKM / n                            | 16073.0 |
| P703: % ítems con VehicleCurrentKM dentro de ±20% de n×15.000 | 75.4%   |
| P703: % dentro de ±20% de n×10.000                            | 8.1%    |
| P375: mediana VehicleCurrentKM / n                            | 10161.0 |
| P375: % ítems dentro de ±20% de n×10.000                      | 78.5%   |
| P375: % dentro de ±20% de n×15.000                            | 7.9%    |
| mediana (edad en meses − ServiceMonth)                        | -17.5   |
| % ítems con |edad − ServiceMonth| <= 6 meses                  | 24.2%   |

### 4.10 ¿maint_number se comporta como 'n-ésimo service del vehículo'?

|                                                    | valor   |
|:---------------------------------------------------|:--------|
| pares consecutivos de (60)+mant del mismo vehículo | 134172  |
| % con Δn = +1                                      | 77.5%   |
| % con Δn = 0 (mismo número)                        | 5.3%    |
| % con Δn < 0                                       | 4.7%    |
| % con Δn > 1 (saltos)                              | 12.5%   |
| vehículos con >= 2 (60)+mant                       | 55815   |
| % de esos vehículos con secuencia no decreciente   | 90.7%   |
| % con secuencia estrictamente creciente            | 82.2%   |
| mediana días entre mantenimientos consecutivos     | 161     |
| mediana Δ VehicleCurrentKM cuando Δn = +1          | 12434   |

### 4.11 Primer mantenimiento observado en vehículos vendidos 2024-2026 (SALES, n=36950): número de service

|           |   1.0 |    2.0 |   3.0 |   4.0 |   5.0 |   6.0 |   7.0 |   8.0 |
|:----------|------:|-------:|------:|------:|------:|------:|------:|------:|
| vehículos | 33979 | 2284   | 347   | 117   |  33   |  44   |     8 |     9 |
| %         |    92 |    6.2 |   0.9 |   0.3 |   0.1 |   0.1 |     0 |     0 |

### 5.1 IsReschedule x StatusARG (turnos)

| IsReschedule   |   (30) Agendado |   (40) En progreso |   (60) Concluido |   (70) Cancelado |   (80) No asistio |   (90) Concluido sin OS |    All |
|:---------------|----------------:|-------------------:|-----------------:|-----------------:|------------------:|------------------------:|-------:|
| (nulo)         |            3475 |               1554 |           297026 |                0 |             23607 |                   13595 | 339257 |
| N              |               0 |                  0 |                0 |            32439 |                 1 |                       0 |  32440 |
| Y              |             478 |                278 |            45665 |            68783 |              3629 |                    1912 | 120745 |
| All            |            3953 |               1832 |           342691 |           101222 |             27237 |                   15507 | 492442 |

### 5.2 Cancelados: ScheduleStatus crudo x IsReschedule

| ScheduleStatus_raw               |     N |     Y |
|:---------------------------------|------:|------:|
| (70) Cancelado                   | 32439 |     0 |
| (nulo)                           |     0 | 68782 |
| status.agendamento.naoCompareceu |     0 |     1 |

### 5.3 ScheduleReturn x StatusARG (turnos)

| ScheduleReturn   |   (30) Agendado |   (40) En progreso |   (60) Concluido |   (70) Cancelado |   (80) No asistio |   (90) Concluido sin OS |    All |
|:-----------------|----------------:|-------------------:|-----------------:|-----------------:|------------------:|------------------------:|-------:|
| (nulo)           |               5 |                  0 |             9420 |           101219 |               838 |                     317 | 111799 |
| N                |            3618 |               1543 |           304023 |                3 |             23732 |                   12552 | 345471 |
| Y                |             330 |                289 |            29248 |                0 |              2667 |                    2638 |  35172 |
| All              |            3953 |               1832 |           342691 |           101222 |             27237 |                   15507 | 492442 |

### 5.4 ScheduleReturn x ScheduleSource

| ScheduleReturn   |   CAF |   Dealer |   FordPass |   Mobile |   WEB |
|:-----------------|------:|---------:|-----------:|---------:|------:|
| (nulo)           |   363 |    63084 |      36769 |     3251 |  8332 |
| N                |   799 |   262456 |      64599 |     6670 | 10947 |
| Y                |    40 |    31861 |       2596 |      171 |   504 |

### 5.5 ScheduleReturn: tipo de ítems (%)

| ScheduleReturn   |   has_maint |   has_diag |   has_repair |   has_recall |   has_guarantee |
|:-----------------|------------:|-----------:|-------------:|-------------:|----------------:|
| (nulo)           |        30.8 |       10.7 |          4.1 |          8.5 |             0.9 |
| N                |        66.3 |       20.7 |          7.8 |         19.9 |             0.9 |
| Y                |        14.1 |       37.4 |         30.4 |         12.3 |             3.5 |

### 5.6 Semántica empírica: distancia al turno anterior / posterior del mismo vehículo

| grupo                    |   turnos | % con turno previo <=14d   | % con turno previo <=30d   | % previo (60) <=30d   | % previo (70) <=14d   |   mediana d_prev | % con turno posterior <=14d   | % con turno posterior <=30d   |   mediana d_next |
|:-------------------------|---------:|:---------------------------|:---------------------------|:----------------------|:----------------------|-----------------:|:------------------------------|:------------------------------|-----------------:|
| ScheduleReturn = Y       |    35171 | 48.4%                      | 98.0%                      | 74.2%                 | 12.4%                 |               15 | 15.8%                         | 26.5%                         |               58 |
| ScheduleReturn = N       |   342577 | 13.9%                      | 16.9%                      | 3.1%                  | 10.1%                 |               93 | 13.8%                         | 20.8%                         |               86 |
| IsReschedule = Y & (60)  |    45460 | 60.3%                      | 66.3%                      | 3.6%                  | 57.7%                 |                7 | 43.9%                         | 50.7%                         |               13 |
| IsReschedule nulo & (60) |   295165 | 9.6%                       | 16.5%                      | 9.8%                  | 3.0%                  |               95 | 8.6%                          | 15.3%                         |               99 |
| IsReschedule = Y & (70)  |    68782 | 47.4%                      | 55.1%                      | 33.7%                 | 15.2%                 |               11 | 64.3%                         | 71.3%                         |                6 |
| IsReschedule = N & (70)  |    32439 | 35.9%                      | 43.7%                      | 23.7%                 | 14.6%                 |               21 | 34.9%                         | 44.1%                         |               21 |

### 6.1 Turnos con ScheduleDate <= CUTOFF-90d: % con un turno concluido del mismo vehículo dentro de N días (0..N)

| caso                                |   turnos | % con seguimiento <= 30 d   | % con seguimiento <= 60 d   | % con seguimiento <= 90 d   |
|:------------------------------------|---------:|:----------------------------|:----------------------------|:----------------------------|
| (70) Cancelado -> algún (60)        |    89858 | 57.5%                       | 64.2%                       | 69.1%                       |
| (70) Cancelado -> (60)+mant         |    89858 | 38.6%                       | 43.5%                       | 48.6%                       |
| (70) & IsReschedule=Y -> algún (60) |    60286 | 66.9%                       | 72.5%                       | 76.6%                       |
| (70) & IsReschedule=N -> algún (60) |    29572 | 38.3%                       | 47.2%                       | 53.6%                       |
| (70) con ítem mant -> (60)+mant     |    22620 | 39.1%                       | 43.9%                       | 49.7%                       |
| (80) No asistió -> algún (60)       |    24460 | 28.6%                       | 39.7%                       | 47.8%                       |
| (80) No asistió -> (60)+mant        |    24460 | 18.8%                       | 26.5%                       | 33.3%                       |
| (80) con ítem mant -> (60)+mant     |    11397 | 34.8%                       | 44.3%                       | 50.3%                       |
| (90) Concluido sin OS -> algún (60) |    13885 | 19.0%                       | 31.4%                       | 40.7%                       |
| (60) Concluido -> otro (60) [base]  |   308816 | 10.1%                       | 19.5%                       | 29.5%                       |

Para (60) se exige otro turno distinto con lag >= 1 día. 'Cancelación efectiva' = 100% menos el valor a 90 días.

### 6.2 Turnos sin ningún ítem tipado (ServiceType nulo) por StatusARG

| ítems del turno   |   (30) Agendado |   (40) En progreso |   (60) Concluido |   (70) Cancelado |   (80) No asistio |   (90) Concluido sin OS |    All |
|:------------------|----------------:|-------------------:|-----------------:|-----------------:|------------------:|------------------------:|-------:|
| con ítem          |            3951 |               1832 |           342564 |            43109 |             27216 |                   15499 | 434171 |
| sin ítem          |               2 |                  0 |              127 |            58113 |                21 |                       8 |  58271 |
| All               |            3953 |               1832 |           342691 |           101222 |             27237 |                   15507 | 492442 |

Casi todos los turnos sin ítem son cancelaciones: no se sabe qué servicio tenían reservado.

### 7.1 Turnos del mismo vehículo el MISMO día: estado del turno previo x estado del turno

| prev_status           |   (30) Agendado |   (40) En progreso |   (60) Concluido |   (70) Cancelado |   (80) No asistio |   (90) Concluido sin OS |
|:----------------------|----------------:|-------------------:|-----------------:|-----------------:|------------------:|------------------------:|
| (30) Agendado         |              12 |                  1 |               12 |               64 |                 1 |                       0 |
| (40) En progreso      |               0 |                  3 |               10 |               55 |                 0 |                       0 |
| (60) Concluido        |              10 |                 13 |             3443 |             8273 |               254 |                      85 |
| (70) Cancelado        |              56 |                 57 |             8389 |             4312 |               618 |                     310 |
| (80) No asistio       |               1 |                  2 |              219 |              663 |                84 |                       5 |
| (90) Concluido sin OS |               0 |                  0 |              105 |              311 |                 9 |                      10 |

Pares mismo día: 27387 (5.6% de los turnos con vehículo); mismo dealer en 95.6%.

### 7.2 Turnos del mismo vehículo a 1-3 días: estado previo x estado

| prev_status           |   (30) Agendado |   (40) En progreso |   (60) Concluido |   (70) Cancelado |   (80) No asistio |   (90) Concluido sin OS |
|:----------------------|----------------:|-------------------:|-----------------:|-----------------:|------------------:|------------------------:|
| (30) Agendado         |               7 |                  0 |                5 |               37 |                 1 |                       0 |
| (40) En progreso      |               7 |                  4 |                6 |               48 |                 2 |                       1 |
| (60) Concluido        |               7 |                 22 |             2217 |             7485 |               597 |                     156 |
| (70) Cancelado        |             128 |                 61 |            10517 |             4175 |               696 |                     492 |
| (80) No asistio       |               2 |                  3 |              761 |              371 |               132 |                      47 |
| (90) Concluido sin OS |               0 |                  0 |              127 |              307 |                27 |                      50 |

Pares a 1-3 días: 28498.

### 7.3 Mantenimientos completados consecutivos del mismo vehículo muy cercanos en el tiempo (de 134172 pares)

|             |   pares (60)+mant consecutivos | % mismo maint_number   | % Δn = +1   | % |Δ VehicleCurrentKM| <= 500   |   mediana Δ VehicleCurrentKM |
|:------------|-------------------------------:|:-----------------------|:------------|:--------------------------------|-----------------------------:|
| <= 3 días   |                            663 | 71.8%                  | 5.1%        | 74.4%                           |                          0   |
| 4 a 30 días |                           1538 | 39.7%                  | 32.3%       | 29.8%                           |                       1550.5 |
| <= 30 días  |                           2201 | 49.4%                  | 24.1%       | 43.3%                           |                          0   |

### 8.1 Turnos sin identificador por StatusARG

|                 |   (30) Agendado |   (40) En progreso |   (60) Concluido |   (70) Cancelado |   (80) No asistio |   (90) Concluido sin OS |   total |
|:----------------|----------------:|-------------------:|-----------------:|-----------------:|------------------:|------------------------:|--------:|
| sin vehicle_id  |              40 |                 20 |             2066 |                1 |               510 |                     260 |    2897 |
| sin customer_id |              96 |                 59 |             6294 |             2110 |               611 |                     228 |    9398 |
| sin ambos       |               2 |                  1 |              293 |                0 |                87 |                      35 |     418 |

### 8.2 Detalle de los faltantes

|                                                                  | valor                                                               |
|:-----------------------------------------------------------------|:--------------------------------------------------------------------|
| (60)+mant sin vehicle_id                                         | 1186                                                                |
| (60)+mant sin customer_id                                        | 3948                                                                |
| sin vehicle_id: ScheduleSource                                   | {'Dealer': 2896, 'CAF': 1}                                          |
| sin vehicle_id: generación                                       | {'RANGER': 1912, 'RANGER (P703)': 842, 'RANGER RAPTOR (P703)': 143} |
| sin vehicle_id: % con WarrantyStartDate                          | 0.0%                                                                |
| sin vehicle_id: % con ModelYear                                  | 0.0%                                                                |
| sin vehicle_id: dealers                                          | 77                                                                  |
| sin vehicle_id: % del dealer principal                           | 11.3%                                                               |
| sin customer_id pero el vehículo tiene customer_id en otro turno | 5117                                                                |
| sin customer_id: dealers                                         | 91                                                                  |
| sin customer_id: % del dealer principal                          | 19.0%                                                               |

### 9.1 Region: dealers y turnos

| Region   |   dealers |   turnos |   % turnos |   turnos 2024 |   turnos 2025 |   turnos 2026 |   % concluido (60) |
|:---------|----------:|---------:|-----------:|--------------:|--------------:|--------------:|-------------------:|
| 00       |        11 |    77931 |      15.83 |         26105 |         31003 |         20823 |               70.7 |
| 31       |         1 |     5910 |       1.2  |          2077 |          2291 |          1542 |               80.1 |
| 60       |        80 |   408470 |      82.95 |        134222 |        160804 |        113444 |               69.2 |
| A        |         3 |      131 |       0.03 |             0 |             0 |           131 |               39.7 |

Dealers con más de una Region: 0; con más de una DealerStateOrZone: 0 (de 95).

### 9.2 Region x DealerStateOrZone (turnos)

| Region   |   (nulo) |     1 |     2 |     3 |      4 |      5 |    All |
|:---------|---------:|------:|------:|------:|-------:|-------:|-------:|
| 00       |        0 |  8756 | 35745 |  2740 |  13946 |  16744 |  77931 |
| 31       |        0 |     0 |     0 |     0 |   5910 |      0 |   5910 |
| 60       |        0 | 40341 | 62592 | 92518 | 118002 |  95017 | 408470 |
| A        |       90 |     0 |     0 |     0 |     41 |      0 |    131 |
| All      |       90 | 49097 | 98337 | 95258 | 137899 | 111761 | 492442 |

### 9.3 DealerStateOrZone del dealer x provincia principal de sus ventas (SALES)

| provincia_sales              |   (nulo) |   1 |   2 |   3 |   4 |   5 |
|:-----------------------------|---------:|----:|----:|----:|----:|----:|
| (dealer sin ventas en SALES) |        2 |  10 |   5 |   4 |   7 |   6 |
| BUENOS AIRES                 |        0 |   3 |   1 |   4 |  10 |   5 |
| CAPITAL FEDERAL              |        0 |   2 |   2 |   2 |   0 |   3 |
| CATAMARCA                    |        0 |   0 |   0 |   2 |   0 |   0 |
| CHACO                        |        0 |   0 |   1 |   0 |   0 |   0 |
| CHUBUT                       |        0 |   0 |   0 |   0 |   0 |   2 |
| CORDOBA                      |        0 |   0 |   0 |   2 |   0 |   0 |
| CORRIENTES                   |        0 |   0 |   1 |   0 |   0 |   0 |
| ENTRE RIOS                   |        0 |   0 |   1 |   0 |   0 |   0 |
| JUJUY                        |        0 |   0 |   0 |   0 |   1 |   0 |
| LA PAMPA                     |        0 |   0 |   0 |   0 |   1 |   0 |
| MENDOZA                      |        0 |   0 |   0 |   0 |   2 |   0 |
| MISIONES                     |        0 |   0 |   3 |   0 |   0 |   0 |
| NEUQUEN                      |        0 |   0 |   0 |   0 |   0 |   1 |
| SALTA                        |        0 |   0 |   0 |   0 |   1 |   0 |
| SAN LUIS                     |        0 |   0 |   0 |   1 |   1 |   0 |
| SANTA CRUZ                   |        0 |   0 |   0 |   0 |   0 |   1 |
| SANTA FE                     |        0 |   0 |   3 |   1 |   0 |   0 |
| SANTIAGO DEL ESTERO          |        0 |   0 |   0 |   1 |   0 |   0 |
| TIERRA DEL FUEGO             |        0 |   0 |   0 |   0 |   0 |   2 |
| TUCUMAN                      |        0 |   0 |   0 |   1 |   0 |   0 |

### 9.4 Region del dealer x provincia principal de sus ventas (SALES)

| provincia_sales              |   00 |   31 |   60 |   A |
|:-----------------------------|-----:|-----:|-----:|----:|
| (dealer sin ventas en SALES) |    2 |    0 |   29 |   3 |
| BUENOS AIRES                 |    3 |    1 |   19 |   0 |
| CAPITAL FEDERAL              |    0 |    0 |    9 |   0 |
| CATAMARCA                    |    0 |    0 |    2 |   0 |
| CHACO                        |    0 |    0 |    1 |   0 |
| CHUBUT                       |    0 |    0 |    2 |   0 |
| CORDOBA                      |    1 |    0 |    1 |   0 |
| CORRIENTES                   |    0 |    0 |    1 |   0 |
| ENTRE RIOS                   |    1 |    0 |    0 |   0 |
| JUJUY                        |    0 |    0 |    1 |   0 |
| LA PAMPA                     |    0 |    0 |    1 |   0 |
| MENDOZA                      |    0 |    0 |    2 |   0 |
| MISIONES                     |    2 |    0 |    1 |   0 |
| NEUQUEN                      |    0 |    0 |    1 |   0 |
| SALTA                        |    0 |    0 |    1 |   0 |
| SAN LUIS                     |    0 |    0 |    2 |   0 |
| SANTA CRUZ                   |    1 |    0 |    0 |   0 |
| SANTA FE                     |    1 |    0 |    3 |   0 |
| SANTIAGO DEL ESTERO          |    0 |    0 |    1 |   0 |
| TIERRA DEL FUEGO             |    0 |    0 |    2 |   0 |
| TUCUMAN                      |    0 |    0 |    1 |   0 |

### 9.5 dealer_id: cruce SALES vs AGENDA

|                   |   valor |
|:------------------|--------:|
| dealers en SALES  |     107 |
| dealers en AGENDA |      95 |
| en ambas          |      61 |
| solo AGENDA       |      34 |
| solo SALES        |      46 |

### 10.1 KM es un atributo del vehículo (snapshot al último dato), VehicleCurrentKM es el odómetro al ingreso

|                                                          | valor   |
|:---------------------------------------------------------|:--------|
| vehículos con >= 2 turnos                                | 85143   |
| ... con KM no nulo en >= 2 turnos                        | 82347   |
| % de esos con un único valor de KM                       | 100.0%  |
| ... con VehicleCurrentKM no nulo en >= 2 turnos          | 75688   |
| % de esos con un único valor de VehicleCurrentKM         | 2.5%    |
| pares consecutivos (>30 d) con KM en ambos               | 228478  |
| % con KM idéntico                                        | 100.0%  |
| pares consecutivos (>30 d) con VehicleCurrentKM en ambos | 162920  |
| % VehicleCurrentKM creciente                             | 90.9%   |
| % igual                                                  | 6.0%    |
| % decreciente                                            | 3.2%    |
| último turno: % |KM − VehicleCurrentKM| <= 1.000         | 96.5%   |
| primer turno: % |KM − VehicleCurrentKM| <= 1.000         | 30.1%   |
| primer turno: % KM > VehicleCurrentKM + 1.000            | 67.0%   |

### 10.2 P703, 1° service completado: cuantiles de KM vs VehicleCurrentKM

|                  |   0.1 |   0.25 |   0.5 |   0.75 |   0.9 |
|:-----------------|------:|-------:|------:|-------:|------:|
| KM               | 13029 |  16337 | 31498 |  48700 | 71934 |
| VehicleCurrentKM |  9824 |  14446 | 16008 |  16908 | 18507 |

### 11.1 Regla final: conteo de turnos y vehículos

|                                                                     |   turnos |   vehículos |
|:--------------------------------------------------------------------|---------:|------------:|
| (2) visita_red: (60) o (90), con vehicle_id, ScheduleDate <= CUTOFF |   355872 |      105709 |
| candidatos a objetivo: (60) & has_maint (definición preliminar)     |   222889 |       87531 |
| − excluidos por no tener vehicle_id                                 |     1186 |           0 |
| − descartados: segundo (60)+mant del mismo vehículo el mismo día    |      335 |         330 |
| − descartados: mismo maint_number que el anterior a <= 30 días      |      846 |         800 |
| (1) mant_completado (evento objetivo)                               |   220522 |       87531 |

### 11.2 Eventos por año (event_date)

|   event_date |   visita_red |   mant_completado |
|-------------:|-------------:|------------------:|
|         2023 |            0 |                 0 |
|         2024 |       119536 |             73361 |
|         2025 |       142805 |             87153 |
|         2026 |        93531 |             60008 |

### 11.3 Casos borde y decisión

| caso borde                                                              |   turnos | decisión                                | motivo                                                                         |
|:------------------------------------------------------------------------|---------:|:----------------------------------------|:-------------------------------------------------------------------------------|
| (60) con ítem mantenimiento + otros ítems (recall, diagnóstico, PUD...) |    64371 | objetivo                                | el mantenimiento se hizo; los demás ítems son features                         |
| (60) solo campaña/recall                                                |    13704 | visita, no objetivo                     | gratuito, iniciado por Ford; no es mantenimiento programado                    |
| (60) solo Guarantee                                                     |     3258 | visita, no objetivo                     | reparación en garantía, sin número de service                                  |
| (60) solo Oil and filter change                                         |      822 | visita, no objetivo (consultar)         | cambio de aceite fuera del plan; aparece solo en 2026                          |
| (60) solo Contactless service                                           |       11 | visita, no objetivo                     | 48 ítems en 2024, sin número de service                                        |
| (60) solo Inspección Ford / Revisión de viaje                           |      302 | visita, no objetivo                     | inspección, no mantenimiento del plan                                          |
| (60) solo diagnóstico / reparación / otros                              |    87706 | visita, no objetivo                     | contacto con la red (feature de relación)                                      |
| (90) Concluido sin OS con ítem mantenimiento                            |     4058 | visita, no objetivo                     | sin orden de servicio: no hay evidencia de trabajo facturado                   |
| (90) Concluido sin OS sin ítem mantenimiento                            |    11449 | visita, no objetivo                     | el auto entró (check-out en 96%), pero no hubo OS                              |
| (40) En progreso con check-in y ScheduleDate <= CUTOFF                  |     1825 | censurado                               | abierto al corte; puede terminar en (60); no usar como negativo                |
| (30) Agendado                                                           |     3953 | nada (feature 'turno futuro')           | reserva pendiente; 3321 con fecha posterior al CUTOFF                          |
| (70) Cancelado                                                          |   101222 | nada como evento; feature               | IsReschedule=Y suele reprogramarse; =N es cancelación efectiva en 46.4% a 90 d |
| (80) No asistió                                                         |    27237 | nada como evento; feature               | 52.2% no vuelve en 90 días                                                     |
| Sin vehicle_id                                                          |     2897 | excluir de eventos                      | no se puede asignar a un usuario-vehículo-ventana                              |
| Con vehicle_id pero sin customer_id                                     |     8980 | evento del vehículo                     | el target es por vehículo; el customer se resuelve por linkage                 |
| Segundo (60)+mant del mismo vehículo el mismo día                       |      335 | un solo evento (se conserva el primero) | duplicado administrativo                                                       |
| (60)+mant con el mismo maint_number que el anterior a <= 30 días        |      846 | un solo evento (se conserva el primero) | mismo service registrado dos veces                                             |
| (60)+mant sin EffectiveCheckinDate                                      |    26213 | objetivo; event_date = ScheduleDate     | check-out siempre presente en (60)                                             |
| (60)+mant con ScheduleReturn = Y                                        |     4380 | objetivo                                | retorno que incluyó mantenimiento; dedup cubre repeticiones                    |
| (60)+mant con maint_number menor que el anterior del vehículo           |     6264 | objetivo                                | maint_number es ruidoso como contador; no invalida el evento                   |

### 11.4 Fecha del evento objetivo: check-in vs check-out vs ScheduleDate

|                                                           | valor      |
|:----------------------------------------------------------|:-----------|
| % con EffectiveCheckinDate                                | 88.4%      |
| % con EffectiveCheckoutDate                               | 100.0%     |
| % check-in el mismo día que ScheduleDate                  | 84.3%      |
| % |check-in − ScheduleDate| > 7 días                      | 0.5%       |
| check-in más de 30 días ANTES de ScheduleDate             | 49         |
| check-in más de 30 días DESPUÉS de ScheduleDate           | 55         |
| % check-out entre 0 y 3 días después de event_date        | 82.9%      |
| % check-out > 30 días después de event_date               | 1.0%       |
| eventos con event_date anterior a 2024-01-01              | 0          |
| mínimo EffectiveCheckinDate en la agenda (filas ítem)     | 2001-10-12 |
| filas ítem con EffectiveCheckinDate anterior a 2024-01-01 | 4          |
