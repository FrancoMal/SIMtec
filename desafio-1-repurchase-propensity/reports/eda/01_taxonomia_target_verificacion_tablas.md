# Apéndice generado: verificación del EDA 01 (taxonomía de eventos y target)

Generado por `scripts/eda/01_taxonomia_target_verificacion.py` sobre `data/interim/agenda.parquet` (612069 ítems tras eliminar duplicados exactos) y `sales.parquet`. CUTOFF = 2026-08-25.

### V0.1 Nombres de servicio que contienen 'maint' (cualquier mayúscula) y su número

|                               |   ítems |
|:------------------------------|--------:|
| ('Maintenance review', True)  |   67326 |
| ('Maintenance service', True) |  201364 |

Si hubiera ítems 'Maintenance ...' sin ServiceMaintenance, aparecerían con False.

### V0.2 Consistencia ServiceMaintenance

|                                             | n                                              |
|:--------------------------------------------|:-----------------------------------------------|
| ítems con ServiceMaintenance no nulo        | 268690                                         |
| ... con ServiceType != Mantenimiento        | 0                                              |
| ítems con 'maint' en el nombre y sin número | 0                                              |
| ítems ServiceType=Mantenimiento sin número  | 5515                                           |
| ... nombres                                 | {'Guarantee': 5467, 'Contactless service': 48} |

### V0.3 Turnos con más de un ítem de mantenimiento

|                                  | valor                                       |
|:---------------------------------|:--------------------------------------------|
| turnos con ítem de mantenimiento | 268592                                      |
| con >= 2 ítems de mantenimiento  | 97                                          |
| con números distintos            | 91                                          |
| distribución max−min (top 5)     | {1.0: 45, 2.0: 14, 3.0: 12, 5.0: 5, 4.0: 5} |

maint_number = min por turno; con 97 turnos afectados es irrelevante.

### V0.4 Colapso propio vs appointments(): coincidencia de flags

|                                     |   valor |
|:------------------------------------|--------:|
| turnos (propio)                     |  492442 |
| turnos appointments()               |  492442 |
| StatusARG distinto                  |       0 |
| turnos con StatusARG mixto en ítems |       4 |
| has_maint distinto                  |       0 |
| event_date distinto                 |       0 |
| maint_number distinto               |       0 |

### V1.1 Recuento independiente de la regla final

|                                                            |   turnos |   vehículos |
|:-----------------------------------------------------------|---------:|------------:|
| (60) & número, contado desde ítems (schedule_id distintos) |   222889 |       87531 |
| candidatos (60) & has_maint (colapso propio)               |   222889 |       87531 |
| − sin vehicle_id                                           |     1186 |           0 |
| − ScheduleDate > CUTOFF (con vehicle_id)                   |        0 |           0 |
| − segundo evento mismo vehículo-día                        |      335 |         330 |
| − mismo número a <= 30 d (iterativo, sin cadena)           |      836 |         800 |
| (variante shift del script original)                       |      846 |         800 |
| evento objetivo final                                      |   220532 |       87531 |

Informe: 222.889 / 87.531; −1.186; −335; −846; 220.522.

### V1.2 Evento objetivo por año de event_date

|   event_date |   eventos |
|-------------:|----------:|
|         2024 |     73367 |
|         2025 |     87155 |
|         2026 |     60010 |

Informe: 73.361 / 87.153 / 60.008.

### V1.3 Sensibilidad de la deduplicación

|                                                        |   valor |
|:-------------------------------------------------------|--------:|
| diferencia entre variante shift (original) e iterativa |      10 |
| descartados por número sin EffectiveCheckinDate        |     231 |

### V1.4 (60)+mant sin vehicle_id: ¿tienen customer_id y ese cliente tiene un único vehículo en la agenda?

|                                              |   valor |
|:---------------------------------------------|--------:|
| (60)+mant sin vehicle_id                     |    1186 |
| con customer_id                              |    1001 |
| cliente con exactamente 1 vehículo en agenda |     258 |
| cliente con >= 2 vehículos                   |     354 |
| cliente sin ningún vehículo conocido         |     389 |

Tema del EDA de linkage; se deja como dato para decidir si vale la pena recuperarlos.

### V2.1 Perfil por estado (recalculado)

| StatusARG             |   turnos |   checkin |   checkout |   vck |   dias_med |   has_maint |   has_diag |   has_repair |
|:----------------------|---------:|----------:|-----------:|------:|-----------:|------------:|-----------:|-------------:|
| (60) Concluido        |   342691 |      86.7 |      100   | 100   |          1 |        65   |       19.8 |          9.3 |
| (90) Concluido sin OS |    15507 |      81.1 |       96.4 |  97.2 |          4 |        26.2 |       48.8 |         14.9 |
| (80) No asistio       |    27237 |       5.7 |        0.1 |  28.1 |          0 |        46.9 |       32.9 |         10.6 |
| (70) Cancelado        |   101222 |       0   |        0   |   0   |        nan |        25.5 |       10.3 |          4.6 |

Informe (90): check-in 81,1 / check-out 96,4 / VCK 97,2 / mediana 4 días / mant 26,2 / diag 48,8.

### V2.2 (90): % 'solo diagnóstico' (recalculado por ServiceType)

|                    | valor   |
|:-------------------|:--------|
| turnos (90)        | 15507   |
| % solo Diagnóstico | 37.6%   |

Informe: 37,6 %.

### V2.3 (90) con vehicle_id: cercanía a un (60)

|                         | valor   |
|:------------------------|:--------|
| (90) con vehículo       | 15247   |
| % con (60) en ±30 d     | 31.7%   |
| (90) con ítem mant      | 3977    |
| con (60)+mant en (0,30] | 206     |
| con (60)+mant en [0,30] | 270     |
| con (60)+mant en (0,90] | 542     |

Informe: 15.247 / 31,7 % / 3.977 / 206 / – / 542.

### V2.4 TEST: número de service del SIGUIENTE (60)+mant del vehículo respecto del (90)+mant

|                         |   turnos (90)+mant |    % |   mediana días al siguiente |   mediana Δ km al siguiente |
|:------------------------|-------------------:|-----:|----------------------------:|----------------------------:|
| sin (60)+mant posterior |               1640 | 41.2 |                         nan |                       nan   |
| n+1                     |               1325 | 33.3 |                         178 |                     15671   |
| mismo número (n)        |                519 | 13.1 |                          88 |                      8472.5 |
| n+2 o más               |                371 |  9.3 |                         220 |                     20640   |
| número menor            |                122 |  3.1 |                         157 |                     10037.5 |

Si el service se hubiera hecho en el (90), el siguiente debería traer n+1; si no se hizo, el mismo n.

### V2.5 Ídem, solo (90)+mant con al menos 365 días de seguimiento

|                         |   turnos (90)+mant (>= 1 año de seguimiento) |    % |
|:------------------------|---------------------------------------------:|-----:|
| n+1                     |                                         1090 | 43.4 |
| sin (60)+mant posterior |                                          603 | 24   |
| mismo número (n)        |                                          386 | 15.4 |
| n+2 o más               |                                          323 | 12.9 |
| número menor            |                                          107 |  4.3 |

### V2.6 Número del (60)+mant ANTERIOR respecto del (90)+mant

|                                        |   turnos (90)+mant |
|:---------------------------------------|-------------------:|
| sin (60)+mant anterior                 |               1843 |
| n−1 (el (90) es el siguiente del plan) |               1477 |
| salto > 1                              |                341 |
| mismo número                           |                188 |
| número mayor                           |                128 |

### V2.7 Retención a 365 días: (60)+mant vs (90)+mant vs (90) sin mant (eventos con >= 1 año de seguimiento)

|                                         | (60)+mant   | (90)+mant   | (90) sin mant   |
|:----------------------------------------|:------------|:------------|:----------------|
| eventos                                 | 129539      | 2509        | 6695            |
| % con (60)+mant del vehículo en (0,365] | 72.5%       | 67.2%       | 62.9%           |
| % con (60)+mant en (0,180]              | 42.4%       | 38.9%       | 39.4%           |

Si el (90)+mant fuera un service hecho sin OS, su retención posterior debería parecerse a la de un (60)+mant.

### V2.8 Δn del SIGUIENTE (60)+mant: tasa base tras un (60)+mant vs tras un (90)+mant (solo con siguiente observado)

|           | tras (60)+mant   | tras (90)+mant   |
|:----------|:-----------------|:-----------------|
| pares     | 134172           | 2337             |
| n+1       | 77.5%            | 56.7%            |
| mismo n   | 5.3%             | 22.2%            |
| n+2 o más | 12.5%            | 15.9%            |
| menor     | 4.7%             | 5.2%             |

'mismo n' = el vehículo vuelve por el mismo hito: evidencia de que ese service no se había hecho.

### V3.1 Escenarios de target (recalculados)

|                     |   turnos |   vehículos |   Δ turnos vs A |
|:--------------------|---------:|------------:|----------------:|
| A (60)&mant         |   222889 |       87531 |               0 |
| B A+aceite          |   224016 |       87821 |            1127 |
| C B+garantía        |   227805 |       88156 |            4916 |
| D C+campañas/recall |   254596 |       93434 |           31707 |
| E A+(90) con mant   |   226947 |       88157 |            4058 |

Informe: 222.889 / 224.016 / 227.805 / 254.596 / 226.947.

### V3.2 Guarantee por año de ScheduleDate

|   ScheduleDate |   ítems |
|---------------:|--------:|
|           2024 |    5467 |

### V3.3 'Service campaign' vs 'Recall' por mes (2025-10 en adelante)

| ScheduleDate   |   Recall |   Service campaign |
|:---------------|---------:|-------------------:|
| 2025-10        |        0 |               2864 |
| 2025-11        |        0 |               2309 |
| 2025-12        |        0 |               2019 |
| 2026-01        |      488 |               1613 |
| 2026-02        |     2013 |                115 |
| 2026-03        |     2785 |                  7 |
| 2026-04        |     2149 |                  2 |
| 2026-05        |     1778 |                  0 |
| 2026-06        |     1715 |                  0 |
| 2026-07        |     1594 |                  0 |
| 2026-08        |     1544 |                  0 |
| 2026-09        |      156 |                  0 |
| 2026-10        |        1 |                  0 |
| 2026-11        |        4 |                  0 |

Transición limpia enero-febrero 2026, igual que 'service' -> 'review'.

### V3.4 Campañas/Recall: precio fijo y flag

| ServiceName      |   ('N', 0.0) |   ('Y', 0.0) |
|:-----------------|-------------:|-------------:|
| Recall           |        14227 |            0 |
| Service campaign |            0 |        68316 |

Ambos nombres tienen ServiceFordFixedPrice = 0 (gratuito); 'Recall' lleva flag N, no Y.

### V3.5 Campañas/Recall y Oil&filter: edad y km (ítems, todos los estados)

|                                     | Campañas/Recall   | Oil and filter change   |
|:------------------------------------|:------------------|:------------------------|
| ítems                               | 82543             | 2601                    |
| mediana edad (meses)                | 13.6              | 32.8                    |
| mediana VehicleCurrentKM (no nulos) | 24174.0           | 65496.0                 |
| % VehicleCurrentKM no nulo          | 86.2%             | 80.5%                   |

Informe: campañas 13,6 meses / 24.174 km; aceite 32,8 meses / 65.496 km.

### V3.6 (60) 'solo Oil and filter change' (+PUD/móvil): ¿reemplaza un service del plan?

|                                                                      | valor                                                                                                                                                                                                     |
|:---------------------------------------------------------------------|:----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| turnos (60) solo aceite                                              | 820                                                                                                                                                                                                       |
| vehículos                                                            | 748                                                                                                                                                                                                       |
| P703                                                                 | 328                                                                                                                                                                                                       |
| P375                                                                 | 490                                                                                                                                                                                                       |
| VehicleCurrentKM p25/p50/p75                                         | [41254.0, 89005.0, 170690.0]                                                                                                                                                                              |
| % con (60)+mant ANTERIOR del vehículo                                | 74.6%                                                                                                                                                                                                     |
| mediana días desde el (60)+mant anterior                             | 210.0                                                                                                                                                                                                     |
| mediana Δ km desde el (60)+mant anterior                             | 14153.5                                                                                                                                                                                                   |
| número del (60)+mant anterior (top 6)                                | {1.0: 79, 2.0: 70, 3.0: 58, 4.0: 34, 5.0: 28, 6.0: 33}                                                                                                                                                    |
| % con (60)+mant POSTERIOR                                            | 6.1%                                                                                                                                                                                                      |
| mediana días al (60)+mant posterior                                  | 95.0                                                                                                                                                                                                      |
| % con anterior y posterior: Δn = +1 (el aceite no cuenta en el plan) | 1.1%                                                                                                                                                                                                      |
| % con anterior y posterior: Δn >= 2 (el aceite 'ocupó' un hito)      | 2.3%                                                                                                                                                                                                      |
| % con km a ±15 % de un múltiplo del hito (15k P703 / 10k P375)       | 36.2%                                                                                                                                                                                                     |
| ... P703                                                             | 32.9%                                                                                                                                                                                                     |
| ... P375                                                             | 38.4%                                                                                                                                                                                                     |
| ModelYear                                                            | {2008.0: 1, 2011.0: 2, 2012.0: 5, 2013.0: 6, 2014.0: 18, 2015.0: 19, 2016.0: 41, 2017.0: 37, 2018.0: 43, 2019.0: 49, 2020.0: 25, 2021.0: 73, 2022.0: 89, 2023.0: 82, 2024.0: 142, 2025.0: 179, 2026.0: 7} |

Si el cambio de aceite sustituyera un service del plan, esperaríamos km cerca de un múltiplo del hito y Δn >= 2 entre el service anterior y el posterior.

### V3.7 'Solo aceite': Δ km y días desde el (60)+mant anterior, por generación

|                                | P703    | P375    |
|:-------------------------------|:--------|:--------|
| turnos con (60)+mant anterior  | 215     | 396     |
| mediana Δ km                   | 14793.0 | 12751.5 |
| p25 Δ km                       | 9206.0  | 9650.0  |
| p75 Δ km                       | 19712.0 | 23870.0 |
| mediana días desde el anterior | 159.0   | 240.0   |
| % con anterior a <= 400 días   | 57.3%   | 60.8%   |

Comparar con el intervalo entre services consecutivos Δn=+1: P703 ~16.000 km, P375 ~10.200 km (V6.2).

### V4.1 km al ingreso y edad por número de service, turnos (60), por generación (recalculado)

|   n |   P703 ítems |   P703 mediana km |   P703 p25 km |   P703 p75 km |   P703 mediana edad |   P375 ítems |   P375 mediana km |   P375 mediana edad |
|----:|-------------:|------------------:|--------------:|--------------:|--------------------:|-------------:|------------------:|--------------------:|
|   1 |        44325 |           16008   |       14447   |       16908   |                 8.4 |         4445 |           11060   |                12.2 |
|   2 |        28230 |           32130.5 |       29953   |       33509.8 |                14.5 |         7690 |           20547.5 |                18.9 |
|   3 |        14926 |           48416   |       46279.2 |       50218   |                17.7 |        10467 |           30614   |                24.3 |
|   4 |         7905 |           64650   |       62281   |       67227   |                19.8 |        10872 |           40695.5 |                28.1 |
|   5 |         4100 |           80710.5 |       77672.2 |       83685   |                21.4 |        11225 |           50870   |                31.5 |
|   6 |         2265 |           96481   |       91542   |       99931   |                22.4 |        11974 |           61242   |                36.5 |
|   7 |         1126 |          112827   |      106822   |      116687   |                23.9 |         9192 |           71063   |                38   |
|   8 |          766 |          126269   |       83900.5 |      130932   |                24   |         8342 |           81110   |                40.3 |
|   9 |          336 |          143440   |      110018   |      147907   |                25.5 |         7921 |           91185   |                42.2 |
|  10 |          171 |          152229   |      105304   |      162359   |                25   |         6774 |          101265   |                45.3 |
|  11 |           98 |          125086   |      110490   |      177028   |                24.5 |         5227 |          111483   |                47   |
|  12 |           81 |          127695   |       64806   |      191153   |                24.6 |         4591 |          121482   |                49.1 |
|  13 |           54 |          125426   |       32590.5 |      187878   |                18.3 |         3735 |          131392   |                49.5 |
|  14 |           53 |           47238   |       22166   |      144479   |                14.4 |         3007 |          141523   |                51.5 |
|  15 |           33 |           32992   |       16262   |      142829   |                11.5 |         2432 |          151208   |                53.8 |
|  16 |           34 |           17050   |       16000   |       40164   |                 9.1 |         1915 |          161508   |                59.4 |
|  17 |           30 |           18150.5 |       13150.5 |       33809.8 |                11.7 |         1441 |          171523   |                60.5 |
|  18 |           10 |           18552   |       16554.2 |       40176   |                 8.3 |         1284 |          181712   |                64.9 |
|  19 |            5 |           17303   |       13621   |       49500   |                10   |         1062 |          191998   |                68.3 |
|  20 |           73 |            2628   |        2142   |        4680   |                 2.4 |         3416 |          221749   |                82.6 |

Informe P703: 16.008 / 32.130 / 48.416 / 64.650; P375: 11.060 / 20.548 / 30.614 / 40.696; n=20 P375 221.749.

### V4.2 % de ítems dentro de ±20 % de n × hito

|                               | valor   |
|:------------------------------|:--------|
| P703 ±20 % de n×15.000        | 75.4%   |
| P703 ±20 % de n×10.000        | 8.1%    |
| P703 mediana km/n             | 16073   |
| P375 ±20 % de n×10.000        | 78.5%   |
| P375 ±20 % de n×15.000        | 7.9%    |
| P375 mediana km/n             | 10161   |
| P703 n<=10: ±20 % de n×15.000 | 75.7%   |
| P375 n<=10: ±20 % de n×10.000 | 77.0%   |

Informe: 75,4 % / 8,1 % / 16.073; 78,5 % / 7,9 % / 10.161.

### V4.3 edad − ServiceMonth

|                                                 | valor   |
|:------------------------------------------------|:--------|
| mediana (meses)                                 | -17.5   |
| % con |edad − ServiceMonth| <= 6                | 24.2%   |
| % ítems sin WarrantyStartDate (cuentan como no) | 0.9%    |

Informe: −17,5 / 24,2 %.

### V4.4 P703, 1° service (60): edad por cohorte trimestral de WarrantyStartDate (la mediana global 8,4 mezcla cohortes censuradas)

| cohorte   |   items |   mediana_edad |   p75_edad |   p90_edad |   mediana_km |   seguimiento_min_meses |
|:----------|--------:|---------------:|-----------:|-----------:|-------------:|------------------------:|
| 2023Q3    |    3759 |           10.4 |       12.4 |       15.2 |      15822   |                    34.8 |
| 2023Q4    |    4468 |            9.6 |       12.1 |       14.6 |      15904   |                    31.8 |
| 2024Q1    |    3303 |            9.4 |       12   |       14.4 |      15947   |                    28.8 |
| 2024Q2    |    4013 |            8.9 |       11.7 |       13.4 |      15987   |                    25.9 |
| 2024Q3    |    5600 |            8.5 |       11.7 |       13   |      16002.5 |                    22.8 |
| 2024Q4    |    4512 |            8.3 |       11.6 |       13.2 |      16029.5 |                    19.8 |
| 2025Q1    |    5466 |            9.2 |       11.8 |       13   |      15962.5 |                    16.8 |
| 2025Q2    |    5099 |            8.5 |       11.5 |       12.5 |      16025   |                    13.8 |
| 2025Q3    |    4445 |            7.5 |       10.1 |       11.8 |      16137   |                    10.8 |
| 2025Q4    |    2174 |            6.1 |        7.7 |        8.9 |      16296.5 |                     7.8 |
| 2026Q1    |     987 |            4.7 |        5.7 |        6.4 |      16289   |                     4.8 |
| 2026Q2    |     197 |            3   |        3.6 |        4.1 |      16325   |                     1.8 |
| 2026Q3    |       9 |            0.7 |        1   |        1.3 |      15710   |                     0   |

Las cohortes de 2023 tienen censura por la izquierda (la agenda empieza en 2024-01: sus 1° service tempranos no se ven); las de 2025-2026 por la derecha (todavía no llegaron al 1° service los que tardan más).

### V4.5 P703, 1° service: cohorte WarrantyStart 2024-01..06 (>= 26 meses de seguimiento) vs todas

|                                        | todas las cohortes   | cohorte 2024-H1   | cohorte 2024-H1, edad <= 24 m   |
|:---------------------------------------|:---------------------|:------------------|:--------------------------------|
| ítems n=1                              | 44325                | 7316              | 7248                            |
| mediana edad (meses)                   | 8.4                  | 9.1               | 9.1                             |
| p75                                    | 11.6                 | 11.9              | 11.9                            |
| p90                                    | 13.0                 | 13.8              | 13.5                            |
| % con 1° service antes de los 12 meses | 80.5%                | 77.6%             | 78.4%                           |

### V5.1 ¿El número del nombre coincide con ServiceMaintenance? por n y familia

|   n |   ('review', False) |   ('review', True) |   ('service', False) |   ('service', True) |
|----:|--------------------:|-------------------:|---------------------:|--------------------:|
|   9 |                   0 |               1807 |                    0 |                7931 |
|  10 |                   0 |               1521 |                    0 |                6693 |
|  11 |                1229 |                  0 |                 5027 |                   0 |
|  12 |                1123 |                  0 |                 4371 |                   0 |
|  13 |                 939 |                  0 |                    0 |                3467 |
|  14 |                 748 |                  0 |                 2849 |                   0 |
|  15 |                 586 |                  0 |                    0 |                2303 |
|  16 |                 486 |                  0 |                 1816 |                   0 |
|  17 |                 375 |                  0 |                 1334 |                   0 |
|  18 |                 356 |                  0 |                 1143 |                   0 |
|  19 |                 316 |                  0 |                  938 |                   0 |
|  20 |                   0 |                786 |                    0 |                3321 |

### V5.2 review vs service por mes (dic-2025 a mar-2026)

| ScheduleDate   |   review |   service |
|:---------------|---------:|----------:|
| 2025-12        |        1 |      9472 |
| 2026-01        |     2477 |      8390 |
| 2026-02        |     7951 |       536 |
| 2026-03        |    10209 |        21 |

Primer 'review': 2025-12-30. Informe: ene 2.477/8.390; feb 7.951/536; mar 10.209/21.

### V5.3 % review por dealer desde 2026-02

|                    |   valor |
|:-------------------|--------:|
| dealers            |    94   |
| mínimo % review    |    92.4 |
| dealers con < 99 % |    21   |

Informe: 94 / 92,4 % / 21.

### V5.4 % ítems con n >= 11 por generación

| ShortVehicleModelGroupTreated   |   % n>=11 |
|:--------------------------------|----------:|
| RANGER                          |       6.5 |
| RANGER (P375)                   |      22.9 |
| RANGER (P703)                   |       1.3 |
| RANGER RAPTOR                   |       0   |
| RANGER RAPTOR (P703)            |       1.9 |

Informe: P375 22,9 %; P703 1,3 %.

### V5.5 ModelYear 2012: % n >= 11

|         | valor   |
|:--------|:--------|
| ítems   | 408     |
| % n>=11 | 58.3%   |

Informe: 58 %.

### V6.1 Δn entre (60)+mant consecutivos (antes y después de la deduplicación)

|                          | antes de dedup   | después de dedup   |
|:-------------------------|:-----------------|:-------------------|
| pares                    | 134172           | 133001             |
| Δn = +1                  | 77.5%            | 78.2%              |
| Δn = 0                   | 5.3%             | 4.5%               |
| Δn < 0                   | 4.7%             | 4.7%               |
| Δn > 1                   | 12.5%            | 12.6%              |
| vehículos con >= 2       | 55815            | 55647              |
| secuencia no decreciente | 90.7%            | –                  |
| estrictamente creciente  | 82.2%            | –                  |
| mediana días             | 161.0            | 162.0              |
| mediana Δ km (Δn=+1)     | 12434.0          | –                  |

Informe: 134.172; 77,5 / 5,3 / 4,7 / 12,5 %; 55.815; 90,7 / 82,2 %; 161 d; 12.434 km.

### V6.2 Δ km entre services consecutivos con Δn = +1, por generación

| ShortVehicleModelGroupTreated   |   size |   median |   p25 |   p75 |
|:--------------------------------|-------:|---------:|------:|------:|
| RANGER                          |    104 |    11293 |  9648 | 16692 |
| RANGER (P375)                   |  55521 |    10234 |  9213 | 11631 |
| RANGER (P703)                   |  48368 |    16093 | 14502 | 17668 |
| RANGER RAPTOR (P703)            |      6 |    16028 | 15588 | 17519 |

El 12.434 pooled mezcla 15.000 (P703) y 10.000 (P375).

### V6.3 Pares con el MISMO número: gap en días y Δ km

| bucket   |   size |   median |   % |Δkm| <= 500 |
|:---------|-------:|---------:|-----------------:|
| 0-3 d    |    476 |      0   |             0.8  |
| 4-30 d   |    611 |      0   |             0.47 |
| 31-90 d  |   1782 |   9999   |             0.09 |
| 91-180 d |   2307 |  11155   |             0.06 |
| > 180 d  |   1902 |  12356.5 |             0.05 |

Los pares con mismo número a > 30 días quedan como dos eventos en la regla final.

### V6.4 Vehículos de SALES: número del primer (60)+mant observado

|           | valor   |
|:----------|:--------|
| vehículos | 36950   |
| % n = 1   | 92.0%   |
| n = 1     | 33979   |

Informe: 36.950 / 92,0 % / 33.979.

### V7.1 IsReschedule x StatusARG

| IsReschedule   |   (30) Agendado |   (40) En progreso |   (60) Concluido |   (70) Cancelado |   (80) No asistio |   (90) Concluido sin OS |
|:---------------|----------------:|-------------------:|-----------------:|-----------------:|------------------:|------------------------:|
| (nulo)         |            3475 |               1554 |           297026 |                0 |             23607 |                   13595 |
| N              |               0 |                  0 |                0 |            32439 |                 1 |                       0 |
| Y              |             478 |                278 |            45665 |            68783 |              3629 |                    1912 |

### V7.2 Cancelados: ScheduleStatus crudo x IsReschedule

| row_0                            |     N |     Y |
|:---------------------------------|------:|------:|
| (70) Cancelado                   | 32439 |     0 |
| (nulo)                           |     0 | 68782 |
| status.agendamento.naoCompareceu |     0 |     1 |

### V7.3 (60): ¿hay algún (70) del mismo vehículo en [-14, 0] días de ScheduleDate?

|                        | valor   |
|:-----------------------|:--------|
| (60) IsReschedule=Y    | 45460   |
| % con (70) en [-14,0]  | 69.7%   |
| (60) IsReschedule nulo | 295165  |
| % con (70) en [-14,0]  | 4.0%    |

Informe (solo el turno inmediato anterior): 57,7 % vs 3,0 %.

### V7.4 ScheduleReturn = Y (recalculado)

|                                      | valor   |
|:-------------------------------------|:--------|
| turnos Y                             | 35172   |
| con vehículo                         | 35171   |
| % con algún turno previo en [-30,-1] | 97.9%   |
| % con (60) previo en [-30,-1]        | 88.4%   |
| % has_maint                          | 14.1%   |
| % has_diag                           | 37.4%   |
| % has_repair                         | 30.4%   |
| % fuente Dealer                      | 90.6%   |
| (60)+mant con ScheduleReturn=Y       | 4380    |

Informe: 35.172; 98,0 %; 74,2 %; 14,1 / 37,4 / 30,4 %; 90,6 %; 4.380. (El 98,0 % del informe usa <= 30 incluyendo el mismo día.)

### V8.1 Seguimiento (ScheduleDate <= CUTOFF−90): % con un (60) del mismo vehículo en la ventana

| caso                       |   turnos | [0,30]   | [0,60]   | [0,90]   | [-30,-1]   | [-30,90]   |
|:---------------------------|---------:|:---------|:---------|:---------|:-----------|:-----------|
| (70) -> algún (60)         |    89858 | 57.5%    | 64.2%    | 69.1%    | 26.9%      | 83.6%      |
| (70) Y -> algún (60)       |    60286 | 66.9%    | 72.5%    | 76.6%    | 29.6%      | 92.2%      |
| (70) N -> algún (60)       |    29572 | 38.3%    | 47.2%    | 53.6%    | 21.4%      | 66.0%      |
| (70) con mant -> (60)+mant |    22620 | 39.1%    | 43.9%    | 49.7%    | 28.4%      | 73.0%      |
| (80) -> algún (60)         |    24460 | 28.6%    | 39.7%    | 47.8%    | 17.0%      | 57.5%      |
| (80) con mant -> (60)+mant |    11397 | 34.8%    | 44.3%    | 50.3%    | 9.2%       | 57.6%      |
| (60) -> otro (60)          |   308816 | 10.1%    | 19.5%    | 29.5%    | –          | –          |

Informe [0,30/60/90]: (70) 57,5/64,2/69,1; Y 66,9/72,5/76,6; N 38,3/47,2/53,6; (70)mant 39,1/43,9/49,7; (80) 28,6/39,7/47,8; (80)mant 34,8/44,3/50,3; base 10,1/19,5/29,5.

### V8.2 (70) IsReschedule=Y: ¿el turno reprogramado cayó ANTES de la fecha cancelada?

|                                       | valor   |
|:--------------------------------------|:--------|
| (70) Y con seguimiento                | 60286   |
| % con (60) IsReschedule=Y en [-30,-1] | 22.3%   |
| % con (60) IsReschedule=Y en [0,90]   | 62.4%   |
| % con (60) IsReschedule=Y en [-30,90] | 81.2%   |
| % con algún (60) en [-30,90]          | 92.2%   |

La 'cancelación efectiva' del informe (23,4 % para Y) ignora las reprogramaciones a una fecha anterior.

### V8.3 Cancelaciones sin ningún ítem tipado

|                                        |   valor |
|:---------------------------------------|--------:|
| (70)                                   |  101222 |
| (70) con un único ítem sin ServiceType |   58110 |

Informe: 58.113 de 101.222.

### V9.1 KM y VehicleCurrentKM por vehículo (nulos tratados explícitamente)

|                                                  | valor   |
|:-------------------------------------------------|:--------|
| vehículos con >= 2 turnos                        | 85143   |
| ... con KM nulo en todos                         | 2785    |
| ... con KM en >= 2 turnos                        | 82347   |
| % de esos con un único valor de KM               | 100.0%  |
| ... con VehicleCurrentKM en >= 2 turnos          | 75688   |
| % de esos con un único valor de VehicleCurrentKM | 2.5%    |

Informe: 100 % / 13,3 % (el 13,3 % incluía vehículos con VehicleCurrentKM en un solo turno o en ninguno).

### V9.2 KM vs VehicleCurrentKM

|                                           | valor   |
|:------------------------------------------|:--------|
| vehículos con KM y algún VehicleCurrentKM | 101768  |
| % |KM − último VCK no nulo| <= 1.000      | 96.4%   |
| % KM >= último VCK − 1.000                | 96.8%   |
| % |KM − primer VCK no nulo| <= 1.000      | 30.4%   |
| % KM > primer VCK + 1.000                 | 66.6%   |

Informe (último turno con ambos): 96,5 %; primer turno: 30,1 % / 67,0 %.

### V9.3 P703 1° service: KM vs VehicleCurrentKM (cuantiles)

|                  |   0.25 |   0.5 |   0.75 |
|:-----------------|-------:|------:|-------:|
| KM               |  16337 | 31498 |  48700 |
| VehicleCurrentKM |  14446 | 16008 |  16908 |

Informe: VCK 14.446 / 16.008 / 16.908; KM mediana 31.498, p75 48.700.

### V9.4 % VehicleCurrentKM no nulo por estado

| StatusARG             |     % |
|:----------------------|------:|
| (30) Agendado         |  23.5 |
| (40) En progreso      |  39.6 |
| (60) Concluido        | 100   |
| (70) Cancelado        |   0   |
| (80) No asistio       |  28.1 |
| (90) Concluido sin OS |  97.2 |

### V10.1 Constancia por dealer (filas ítem)

|                           |   valor |
|:--------------------------|--------:|
| dealers                   |      95 |
| con > 1 Region            |       0 |
| con > 1 DealerStateOrZone |       0 |

### V10.2 Region

| Region   |   dealers |   turnos |   % turnos |
|:---------|----------:|---------:|-----------:|
| 00       |        11 |    77931 |      15.83 |
| 31       |         1 |     5910 |       1.2  |
| 60       |        80 |   408470 |      82.95 |
| A        |         3 |      131 |       0.03 |

Informe: 60 → 80 dealers / 82,95 %; 00 → 11 / 15,83 %; 31 → 1; A → 3 (131 turnos).

### V10.3 Dealers por DealerStateOrZone

| zona   |   dealers |
|:-------|----------:|
| (nulo) |         2 |
| 1      |        15 |
| 2      |        17 |
| 3      |        18 |
| 4      |        23 |
| 5      |        20 |

Informe: 15/17/18/23/20.

### V10.4 Dealers Region 00: provincia principal en SALES

| prov         |   dealers |
|:-------------|----------:|
| BUENOS AIRES |         3 |
| (sin ventas) |         2 |
| MISIONES     |         2 |
| ENTRE RIOS   |         1 |
| CORDOBA      |         1 |
| SANTA FE     |         1 |
| SANTA CRUZ   |         1 |

### V10.5 Zona 1: provincias (dealers con ventas)

| prov            |   dealers |
|:----------------|----------:|
| (sin ventas)    |        10 |
| BUENOS AIRES    |         3 |
| CAPITAL FEDERAL |         2 |

### V10.6 dealer_id SALES vs AGENDA

|          |   valor |
|:---------|--------:|
| SALES    |     107 |
| AGENDA   |      95 |
| en común |      61 |

### V10.7 Region x ScheduleSource (% por fila)

| Region   |   CAF |   Dealer |   FordPass |   Mobile |   WEB |
|:---------|------:|---------:|-----------:|---------:|------:|
| 00       |   0.3 |     72.7 |       22.7 |      1.5 |   2.8 |
| 31       |   0.1 |     49.2 |       45.8 |      2   |   2.8 |
| 60       |   0.2 |     72.9 |       20.5 |      2.2 |   4.3 |
| A        |   0   |     66.4 |       29   |      2.3 |   2.3 |
