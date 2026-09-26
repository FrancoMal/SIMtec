# Tablas de verificación del EDA 04 (scripts/eda/04_identidad_cliente_vehiculo_verificacion.py)

### V1.1 Vehículos por n° de customer_id distintos (recalculado)

|                 |   vehículos | pct    |
|:----------------|------------:|:-------|
| con customer_id |      110551 | 100.0% |
| >1 cliente      |       23245 | 21.0%  |
| 2 clientes      |       19624 | 17.8%  |
| 3 clientes      |        3083 | 2.8%   |

### V1.2 Patrón temporal recalculado (todos los turnos, como el original)

| patron      |   vehículos | pct   |
|:------------|------------:|:------|
| secuencial  |       17792 | 76.5% |
| alternancia |        5224 | 22.5% |
| ambiguo     |         229 | 1.0%  |

### V1.3 Patrón temporal usando SOLO turnos concluidos ((60) y (90))

| patron      |   vehículos | pct   |
|:------------|------------:|:------|
| secuencial  |       16786 | 82.0% |
| alternancia |        3621 | 17.7% |
| ambiguo     |          55 | 0.3%  |

_20,462 vehículos multi-cliente entre concluidos (vs 23,245 con todos los estados)._

### V1.4 Secuenciales: turnos del cliente nuevo (último)

|                                                             |   vehículos | pct    |
|:------------------------------------------------------------|------------:|:-------|
| secuenciales                                                |       17792 | 100.0% |
| cliente nuevo con 1 solo turno                              |        6462 | 36.3%  |
| cliente nuevo sin ningún turno (60) Concluido               |        1542 | 8.7%   |
| cliente nuevo sin mantenimiento completado                  |        3845 | 21.6%  |
| cliente(s) anterior(es) sin ningún (60) Concluido           |        1417 | 8.0%   |
| ambos lados con >=1 (60) Concluido                          |       14995 | 84.3%  |
| último turno del cliente nuevo es reserva futura (> CUTOFF) |         738 | 4.1%   |

_'Cambio permanente' solo es verificable cuando ambos clientes tienen turnos efectivamente concluidos._

### V2.1 Cambio de canal en pares consecutivos: switch vs no-switch, y baseline en vehículos de un solo cliente

|                                      |   n pares | cambia ScheduleSource   | cruce Dealer<->FordPass   |
|:-------------------------------------|----------:|:------------------------|:--------------------------|
| cambio de cliente                    |     35836 | 52.8%                   | 34.1%                     |
| sin cambio (vehículos multi-cliente) |    100962 | 15.7%                   | 11.4%                     |
| sin cambio (vehículos de 1 cliente)  |    233216 | 16.8%                   | 12.5%                     |

### V2.2 % de vehículos multi-cliente según mezcla de canal, ESTRATIFICADO por n° de turnos

| n_turnos_cat   | % multi | un solo tipo de canal   | % multi | mezcla FP y no-FP   |   n un solo tipo |   n mezcla |
|:---------------|:----------------------------------|:------------------------------|-----------------:|-----------:|
| 2              | 9.3%                              | 28.8%                         |            16362 |       2537 |
| 3              | 16.2%                             | 33.6%                         |            10978 |       3673 |
| 4-5            | 22.1%                             | 38.7%                         |            13169 |       7087 |
| 6-8            | 28.8%                             | 44.4%                         |             9082 |       7584 |
| 9+             | 39.0%                             | 53.0%                         |             6510 |       7160 |

_Sin estratificar: mezcla 42.3% vs un solo tipo 20.3%._

### V2.3 Secuenciales de 2 clientes en vehículos VENDIDOS 2024-26: ¿dónde está el comprador?

| caso                                                        |   vehículos | pct   |
|:------------------------------------------------------------|------------:|:------|
| comprador primero, otro después (transferencia o artefacto) |        3207 | 57.5% |
| comprador no aparece                                        |        1263 | 22.6% |
| OTRO primero, comprador DESPUÉS (artefacto seguro)          |        1112 | 19.9% |

_Un vehículo vendido 0 km en 2024-26 no puede tener un dueño real anterior al comprador: si el comprador aparece segundo, el primer id es un artefacto._

### V2.4 Canal (anterior -> nuevo) en los cambios 'artefacto seguro' (otro -> comprador)

| prev_src   |   Dealer |   FordPass |   Mobile |   WEB |   All |
|:-----------|---------:|-----------:|---------:|------:|------:|
| Dealer     |      633 |        157 |       24 |    12 |   826 |
| FordPass   |      193 |         20 |        3 |     1 |   217 |
| Mobile     |       10 |          0 |        1 |     1 |    12 |
| WEB        |       53 |          4 |        0 |     0 |    57 |
| All        |      889 |        181 |       28 |    14 |  1112 |

### V2.5 En los 'artefacto seguro': ¿cuándo ocurre el primer turno del id 'otro' respecto de la entrega?

|                                               |   vehículos | pct    |
|:----------------------------------------------|------------:|:-------|
| artefactos seguros                            |        1112 | 100.0% |
| 1er turno ANTES de DeliveryDate (pre-entrega) |         310 | 27.9%  |
| 0-30 días después de la entrega               |         139 | 12.5%  |
| > 30 días después                             |         663 | 59.6%  |
| > 180 días después                            |         344 | 30.9%  |
| 1er turno incluye ítem de mantenimiento       |         459 | 41.3%  |
| 1er turno (60) Concluido                      |         824 | 74.1%  |

_Si el 'otro' id usa el vehículo meses después de la entrega y hace mantenimientos, es un usuario real (chofer/familiar) con id distinto al comprador, no un turno de pre-entrega._

### V3.1 Transferencias 2025 por nivel (recalculado) y tasa sobre vehículos con turno en 2025

|       |   cambios totales |   2025 | tasa 2025   |   edad mediana |
|:------|------------------:|-------:|:------------|---------------:|
| (i)   |             20137 |   8939 | 12.1%       |           2.05 |
| (ii)  |             12991 |   5527 | 7.5%        |           2.34 |
| (iii) |              7417 |   3325 | 4.5%        |           2.55 |

_vehículos con turno en 2025: 73,701 (== 73,701 con event_date <= CUTOFF)_

### V3.2 Tasa 2025 con denominador 'vehículos con turno en 2025 y >=2 turnos en total'

|                | valor   |
|:---------------|:--------|
| vehículos      | 66482   |
| tasa nivel iii | 5.0%    |
| tasa nivel i   | 13.4%   |

### V3.3 Transferencias 2025 (nivel iii) por edad del vehículo vs composición del parque activo: hazard por edad

|      |   transferencias 2025 (iii) | % de las transferencias   |   vehículos activos 2025 | % del parque activo   | tasa por vehículo-año   |
|:-----|----------------------------:|:--------------------------|-------------------------:|:----------------------|:------------------------|
| <1   |                         313 | 9.4%                      |                    20567 | 28.1%                 | 1.5%                    |
| 1-2  |                         920 | 27.7%                     |                    18508 | 25.3%                 | 5.0%                    |
| 2-3  |                         596 | 18.0%                     |                     9262 | 12.7%                 | 6.4%                    |
| 3-4  |                         389 | 11.7%                     |                     5892 | 8.1%                  | 6.6%                    |
| 4-5  |                         357 | 10.8%                     |                     4917 | 6.7%                  | 7.3%                    |
| 5-7  |                         322 | 9.7%                      |                     4841 | 6.6%                  | 6.7%                    |
| 7-10 |                         319 | 9.6%                      |                     6326 | 8.7%                  | 5.0%                    |
| 10+  |                         101 | 3.0%                      |                     2776 | 3.8%                  | 3.6%                    |

_Si la tasa por vehículo-año es plana o creciente, 'ocurren temprano' refleja que el parque observado es joven, no una propensión mayor a transferirse a los 2-3 años._

### V3.4 Hazard por edad, nivel (i) y (iii), con denominador 'activos 2025 con >=2 turnos'

|      |   activos 2025 (>=2 turnos) | tasa nivel i   | tasa nivel iii   |
|:-----|----------------------------:|:---------------|:-----------------|
| <1   |                       18482 | 9.0%           | 1.7%             |
| 1-2  |                       17889 | 15.2%          | 5.1%             |
| 2-3  |                        8940 | 18.2%          | 6.7%             |
| 3-4  |                        5589 | 15.6%          | 7.0%             |
| 4-5  |                        4556 | 14.9%          | 7.8%             |
| 5-7  |                        4183 | 14.8%          | 7.7%             |
| 7-10 |                        4888 | 11.5%          | 6.5%             |
| 10+  |                        1645 | 10.0%          | 6.1%             |

### V4.1 Comprador en la agenda de su vehículo (recalculado)

|                                                                       |   vehículos | pct    |
|:----------------------------------------------------------------------|------------:|:-------|
| vendidos con turnos (customer_id no nulo)                             |       41906 | 100.0% |
| comprador aparece                                                     |       29576 | 70.6%  |
| comprador es primero                                                  |       27695 | 66.1%  |
| comprador es último (<= CUTOFF)                                       |       25008 | 59.7%  |
| vehículos cuyo único turno es reserva futura (> CUTOFF): último = NaN |         371 | 0.9%   |
| comprador es último, excluyendo los sin historia <= CUTOFF            |       25008 | 60.2%  |

### V4.2 % comprador en agenda por PersonType y canal (recalculado)

|              |     n | tasa   |
|:-------------|------:|:-------|
| 25           |   348 | 4.3%   |
| 29           |    23 | 73.9%  |
| F            | 24796 | 82.2%  |
| J            | 16721 | 54.8%  |
| CONSORTIUM   |  5013 | 78.2%  |
| DIRECT SALES |  5607 | 55.7%  |
| HR           |   439 | 3.0%   |
| ROR          | 30847 | 73.0%  |
| Ford Blue    | 29865 | 71.5%  |
| Ford Pro     | 12041 | 68.3%  |

### V4.3 HR / PersonType 25: concentración (recalculado)

|               |   ventas |   top id ventas | mismo id   |
|:--------------|---------:|----------------:|:-----------|
| HR            |     1060 |             752 | True       |
| PersonType 25 |      656 |             387 | True       |

### V5.1 Base del proxy (recalculado)

|             | valor   |
|:------------|:--------|
| eventos     | 105782  |
| vehículos   | 55712   |
| retorno_15m | 78.5%   |

### V5.2 retorno_15m por es_comprador (recalculado), total y por PersonType / BusinessUnit

|                            |     n | tasa   |
|:---------------------------|------:|:-------|
| comprador                  |  8875 | 88.2%  |
| otro                       |  5885 | 89.1%  |
| sin venta                  | 91022 | 76.8%  |
| ('25', 'otro')             |    58 | 87.9%  |
| ('29', 'otro')             |     1 | 100.0% |
| ('F', 'comprador')         |  5911 | 87.8%  |
| ('F', 'otro')              |  1988 | 86.5%  |
| ('J', 'comprador')         |  2964 | 89.1%  |
| ('J', 'otro')              |  3834 | 90.4%  |
| ('Ford Blue', 'comprador') |  6105 | 89.6%  |
| ('Ford Blue', 'otro')      |  4003 | 90.2%  |
| ('Ford Pro', 'comprador')  |  2770 | 85.2%  |
| ('Ford Pro', 'otro')       |  1882 | 86.7%  |

### V5.3 Gap al siguiente mantenimiento completado entre los eventos con retorno=1 (calidad del proxy)

|                 |   eventos | % de los eventos   |
|:----------------|----------:|:-------------------|
| retorno_15m = 1 |     83008 | 78.5%              |
| gap <= 7 días   |       510 | 0.5%               |
| gap <= 30 días  |      1164 | 1.1%               |
| gap <= 90 días  |     14223 | 13.4%              |

_Un 'retorno' a <= 30 días no es el próximo mantenimiento programado; infla el proxy (afecta a todos los temas, no solo a este)._

### V5.4 retorno_15m 'limpio' (siguiente mantenimiento a > 30 días) por es_comprador

|                    |     n | tasa   |
|:-------------------|------:|:-------|
| comprador          |  8875 | 88.1%  |
| otro               |  5885 | 88.9%  |
| sin venta          | 91022 | 76.6%  |
| ('25', 'otro')     |    58 | 87.9%  |
| ('29', 'otro')     |     1 | 100.0% |
| ('F', 'comprador') |  5911 | 87.7%  |
| ('F', 'otro')      |  1988 | 86.3%  |
| ('J', 'comprador') |  2964 | 88.9%  |
| ('J', 'otro')      |  3834 | 90.3%  |

_Base limpia = 78.3%._

### V5.5 retorno_15m por mismo_dealer_que_venta (recalculado)

| mismo_dealer   |     n | retorno_15m   | retorno_15m limpio   |
|:---------------|------:|:--------------|:---------------------|
| n/a            | 94344 | 77.2%         | 77.0%                |
| no             |  5596 | 89.3%         | 89.1%                |
| sí             |  5842 | 88.8%         | 88.7%                |

### V5.6 1er mantenimiento completado en el dealer vendedor (recalculado)

|                           |   vehículos | % mismo dealer   |
|:--------------------------|------------:|:-----------------|
| todos                     |       36705 | 38.1%            |
| dealer vendedor en agenda |       28112 | 49.7%            |

### V6.1 Ventas por tamaño de flota del comprador: sales solo vs combinado (sales ∪ agenda)

| tam_sales   |     1 |    2 |   3-9 |   10-49 |   50+ |   All |
|:------------|------:|-----:|------:|--------:|------:|------:|
| 1           | 36752 | 4917 |   740 |      12 |     4 | 42425 |
| 2           |     0 | 3246 |  1426 |      24 |     2 |  4698 |
| 3-9         |     0 |    0 |  3366 |     717 |    25 |  4108 |
| 10-49       |     0 |    0 |     0 |    2116 |   522 |  2638 |
| 50+         |     0 |    0 |     0 |       0 |  5515 |  5515 |
| All         | 36752 | 8163 |  5532 |    2869 |  6068 | 59384 |

_Flota (>=3) por sales: 20.6% de las ventas; por combinado: 24.4%. Compradores '1 vehículo' en sales que tienen >=3 en la agenda: 564 ventas._

### V6.2 % Ford Pro por tamaño de flota (sales) y % de cada BU que es flota (recalculado)

|       | Ford Blue   | Ford Pro   | UNKNOWN   | comb: Ford Blue   | comb: Ford Pro   | comb: UNKNOWN   |
|:------|:------------|:-----------|:----------|:------------------|:-----------------|:----------------|
| 1     | 77.7%       | 22.3%      | 0.0%      | 77.1%             | 22.9%            | 0.0%            |
| 2     | 71.6%       | 28.4%      | 0.0%      | 79.2%             | 20.8%            | 0.0%            |
| 3-9   | 42.3%       | 57.7%      | 0.0%      | 55.2%             | 44.8%            | 0.0%            |
| 10-49 | 21.0%       | 79.0%      | 0.0%      | 23.0%             | 77.0%            | 0.0%            |
| 50+   | 32.8%       | 67.2%      | 0.0%      | 32.0%             | 68.0%            | 0.0%            |

_Ford Pro con flota>=3 (sales): 43.1%; (comb): 46.5%. Ford Blue flota (sales): 10.1%; (comb): 14.0%. J con 1 vehículo (sales): 9,676 (40.9%); (comb): 8,259 (34.9%)._

### V7.1 Vendidos con >=15 meses: 1er mantenimiento completado en 15 m por tamaño de flota (sales y combinado) y BU

|            |     n | tasa   |
|:-----------|------:|:-------|
| 1          | 22689 | 80.4%  |
| 2          |  2701 | 79.1%  |
| 3-9        |  2278 | 73.2%  |
| 10-49      |  1435 | 61.9%  |
| 50+        |  2789 | 60.0%  |
| comb 1     | 19729 | 79.5%  |
| comb 2     |  4434 | 82.4%  |
| comb 3-9   |  3068 | 77.6%  |
| comb 10-49 |  1576 | 63.3%  |
| comb 50+   |  3085 | 61.3%  |
| Ford Blue  | 22119 | 80.2%  |
| Ford Pro   |  9773 | 70.4%  |

_Total 77.2% sobre 31,892. Con 'cualquier turno concluido en 15 m': 82.6%._

### V7.2 % con mantenimiento completado por año de vida (recalculado)

|   k | dos   | flota   | particular   |   n dos |   n flota |   n particular |
|----:|:------|:--------|:-------------|--------:|----------:|---------------:|
|   1 | 74.3% | 73.0%   | 71.6%        |    4932 |      5231 |          25123 |
|   2 | 78.1% | 68.9%   | 79.2%        |    3764 |      5938 |          23462 |
|   3 | 63.8% | 55.5%   | 70.5%        |    2206 |      4878 |          12647 |
|   4 | 56.2% | 51.7%   | 62.8%        |    1768 |      2523 |           9289 |
|   5 | 44.9% | 47.6%   | 55.5%        |    1553 |      1505 |           7713 |
|   6 | 32.8% | 26.6%   | 40.0%        |     957 |       830 |           5436 |
|   7 | 30.2% | 23.5%   | 34.9%        |     705 |       818 |           5452 |
|   8 | 25.1% | 20.4%   | 30.7%        |     717 |       682 |           6081 |

### V7.3 Años 1 y 2 desde SALES (incluye vendidos que nunca tuvieron turno; grupo = flota combinada)

|   k | dos   | flota   | particular   |   n dos |   n flota |   n particular |
|----:|:------|:--------|:-------------|--------:|----------:|---------------:|
|   1 | 69.9% | 59.1%   | 64.8%        |    5317 |      9380 |          23728 |
|   2 | 77.5% | 66.4%   | 73.5%        |    1870 |      3004 |           8366 |

_Compara con V7.2: la población 'con al menos un turno' infla el año 1-2, sobre todo en flotas._

### V7.4 retorno_15m por tamaño de flota [as-of (como el original)] x edad del vehículo

| tam_asof   | <2    | 2-4   | 4+    |   n <2 |   n 2-4 |   n 4+ |
|:-----------|:------|:------|:------|-------:|--------:|-------:|
| 1          | 85.3% | 76.6% | 58.4% |  41724 |   22530 |  15643 |
| 2          | 87.0% | 80.3% | 64.0% |   5317 |    2104 |    942 |
| 3-9        | 85.8% | 82.2% | 62.1% |   4714 |    2046 |    734 |
| 10+        | 82.2% | 80.7% | 61.9% |   5923 |    2939 |    721 |

### V7.4 retorno_15m por tamaño de flota [período completo] x edad del vehículo

| tam_full   | <2    | 2-4   | 4+    |   n <2 |   n 2-4 |   n 4+ |
|:-----------|:------|:------|:------|-------:|--------:|-------:|
| 1          | 85.5% | 76.8% | 59.1% |  35270 |   18417 |  13491 |
| 2          | 85.6% | 76.2% | 56.3% |   8263 |    4626 |   2470 |
| 3-9        | 85.9% | 81.5% | 62.5% |   6528 |    3045 |   1117 |
| 10+        | 82.7% | 80.7% | 60.0% |   7617 |    3531 |    962 |

### V7.5 Cruce: tamaño de flota as-of vs período completo en los eventos del proxy (cuántos 'flota' quedan como '1' por truncamiento)

| tam_asof   |     1 |     2 |   3-9 |   10+ |    All |
|:-----------|------:|------:|------:|------:|-------:|
| 1          | 67436 | 10253 |  2325 |   198 |  80212 |
| 2          |     0 |  5193 |  3006 |   220 |   8419 |
| 3-9        |     0 |     0 |  5405 |  2125 |   7530 |
| 10+        |     0 |     0 |     0 |  9621 |   9621 |
| All        | 67436 | 15446 | 10736 | 12164 | 105782 |

### V7.6 Turnos por grupo: no-show, cancelado, FordPass (recalculado)

| grupo_t    |   turnos | no_show   | cancelado   | fordpass   |
|:-----------|---------:|:----------|:------------|:-----------|
| dos        |    64783 | 5.0%      | 20.6%       | 24.4%      |
| flota      |    92318 | 5.8%      | 20.9%       | 7.4%       |
| particular |   319780 | 5.5%      | 20.6%       | 24.9%      |

### V8.1 Overlap de dealer_id (recalculado)

|                                      | valor   |
|:-------------------------------------|:--------|
| sales                                | 107     |
| agenda                               | 95      |
| ambas                                | 61      |
| solo sales                           | 46      |
| solo agenda                          | 34      |
| % ventas con dealer en agenda        | 76.1%   |
| % turnos (base) con dealer en sales  | 75.7%   |
| % turnos (todos) con dealer en sales | 75.7%   |

### V8.2 Concentración del dealer del 1er turno por dealer vendedor: ausentes vs presentes

| en_agenda   |   dealers |   ventas |   share_top_mediana |   share_top_p25 |   share_top_p75 |   top_es_mismo_id |   top_es_dealer_solo_agenda |
|:------------|----------:|---------:|--------------------:|----------------:|----------------:|------------------:|----------------------------:|
| False       |        41 |    10042 |            0.589744 |        0.365942 |        1        |          0        |                   0.317073  |
| True        |        58 |    31766 |            0.576351 |        0.430272 |        0.760227 |          0.862069 |                   0.0517241 |

### V8.3 Dealers vendedores ausentes: ¿su destino principal es un dealer que existe solo en la agenda (34) o uno compartido (61)?

|                                         | valor   |
|:----------------------------------------|:--------|
| dealers ausentes                        | 41      |
| ventas                                  | 10042   |
| top = dealer solo-agenda (dealers)      | 13      |
| top = dealer solo-agenda (% ventas)     | 65.0%   |
| destinos top distintos                  | 28      |
| dealers ausentes con share_top >= 50%   | 26      |
| ventas de ausentes con share_top >= 50% | 64.8%   |

### V8.4 Los 10 ausentes con más ventas: destino principal y si ese destino es solo-agenda

| dealer_id    |    n | top          | share_top   | share_2do   | top_es_solo_agenda   |
|:-------------|-----:|:-------------|:------------|:------------|:---------------------|
| 85cc31b84261 | 1910 | 7fc11e64ab78 | 67.1%       | 23.1%       | False                |
| 4cc4b715e345 | 1844 | 59eb40e9e7ea | 60.8%       | 16.0%       | True                 |
| d8c874bd7792 | 1763 | 5457d57b0bc8 | 59.7%       | 5.8%        | True                 |
| d67af46fa9e6 |  828 | aa82211a7fb2 | 36.6%       | 17.0%       | True                 |
| 9a9814bc02ab |  675 | 80f9367d7065 | 17.0%       | 12.7%       | False                |
| 1141a4ef5ea3 |  608 | e22568834b3a | 13.0%       | 11.8%       | True                 |
| d6a79a9dc5b0 |  510 | 3bfa5c5bfffe | 41.8%       | 35.9%       | True                 |
| 98ac3977c8a5 |  478 | 50396739e186 | 40.4%       | 3.1%        | True                 |
| aa6414339ccd |  458 | 5bbb50452413 | 51.1%       | 8.5%        | False                |
| f05cfd21bbf9 |  246 | 850728b9f99f | 53.7%       | 6.1%        | True                 |

### V8.5 Destinos principales compartidos por más de un dealer ausente

| top          |   n_ausentes |   ventas |
|:-------------|-------------:|---------:|
| c08468899650 |            4 |       49 |
| c7e2569ff6a8 |            3 |      255 |
| cd11e823c9f0 |            3 |       25 |
| 0a655cfb90e8 |            2 |       19 |
| 5d476b0fbac9 |            2 |       44 |
| ec449b176cbf |            2 |       19 |
| 7fc11e64ab78 |            2 |     1916 |
| c0e0a93812ef |            2 |      141 |
| 5bbb50452413 |            2 |      463 |

### V9.1 Clientes vigentes con vehículos activos 2025-26 (recalculado)

|                     | valor   |
|:--------------------|:--------|
| clientes vigentes   | 78331   |
| con >=2 vehículos   | 5415    |
| % clientes          | 6.9%    |
| vehículos en ellos  | 19909   |
| % vehículos activos | 21.4%   |

### V9.2 Vehículos que entran en ventana 2025-09 → 2026-08 y coincidencia por cliente: método original vs corregido

|                                  | original (solo último mantenimiento)   | corregido (todos los mantenimientos, cliente del turno)   | corregido (todos, cliente vigente)   |
|:---------------------------------|:---------------------------------------|:----------------------------------------------------------|:-------------------------------------|
| vehículos-ventana en el período  | 17449                                  | 82140                                                     | 82140                                |
| de clientes con >=2 el mismo mes | 1262                                   | 10795                                                     | 9281                                 |
| % coincidencia                   | 7.2%                                   | 13.1%                                                     | 11.3%                                |
| clientes con >=2 el mismo mes    | 195                                    | 1193                                                      | 1002                                 |

_El método original toma el ÚLTIMO mantenimiento al CUTOFF: un vehículo que volvió corre su ventana al futuro y desaparece del período. Subestima las ventanas de los meses más viejos y sesga la población hacia los que NO volvieron._

### V9.3 Vehículos que entran en ventana por mes: original vs corregido

| mes     |   original |   corregido |
|:--------|-----------:|------------:|
| 2025-09 |       1134 |        6373 |
| 2025-10 |       1191 |        6749 |
| 2025-11 |       1143 |        6468 |
| 2025-12 |       1240 |        6549 |
| 2026-01 |       1474 |        7538 |
| 2026-02 |       1373 |        6631 |
| 2026-03 |       1338 |        6342 |
| 2026-04 |       1433 |        6912 |
| 2026-05 |       1567 |        7071 |
| 2026-06 |       1461 |        6589 |
| 2026-07 |       2021 |        7648 |
| 2026-08 |       2074 |        7270 |

### V10.1 Vendidos sin ningún turno (recalculado)

|                                                | valor   |
|:-----------------------------------------------|:--------|
| sin turno                                      | 17173   |
| % <12 meses (sobre 17.173, NaN cuenta como no) | 74.8%   |
| % <12 meses (sobre los con WSD)                | 75.3%   |
| >=12 meses                                     | 4208    |
| >=15 meses                                     | 3166    |
| vendidos con >=15 meses                        | 31892   |
| % nunca / vendidos >=15 m                      | 9.9%    |
| mediana meses                                  | 6.6     |

### V10.2 Vendidos con >=15 meses: tres definiciones de 'nunca vino'

|                                                              |   vehículos | pct    |
|:-------------------------------------------------------------|------------:|:-------|
| vendidos >=15 m                                              |       31892 | 100.0% |
| sin NINGÚN turno (ni cancelado)                              |        3166 | 9.9%   |
| sin ningún turno concluido (60/90)                           |        3735 | 11.7%  |
| sin ningún mantenimiento completado                          |        5070 | 15.9%  |
| en la agenda pero solo con cancelados / no-show / pendientes |         569 | 1.8%   |

_'Elegible y nunca vino' depende de la definición: 9,9 % (sin ningún turno), 11,7 % (sin turno concluido), 15,9 % (sin mantenimiento completado nunca); y 22,8 % si se exige el 1er mantenimiento DENTRO de los 15 meses (complemento del 77,2 % de f.4)._

### V10.3 Vendidos >=15 m: % sin ningún turno por segmento (recalculado)

|              |     n | t     |
|:-------------|------:|:------|
| Ford Blue    | 22119 | 7.3%  |
| Ford Pro     |  9773 | 15.9% |
| CONSORTIUM   |  3988 | 9.5%  |
| DIRECT SALES |  4319 | 17.0% |
| HR           |   542 | 31.7% |
| ROR          | 23043 | 8.2%  |
| 1            | 22689 | 7.9%  |
| 2            |  2701 | 8.1%  |
| 3-9          |  2278 | 13.3% |
| 10-49        |  1435 | 20.8% |
| 50+          |  2789 | 20.3% |

### V11.1 KM / VehicleCurrentKM constantes por vehículo (nivel turno, recalculado)

|                  |   vehículos con >=2 valores | % constante   |
|:-----------------|----------------------------:|:--------------|
| KM               |                       82347 | 99.99%        |
| VehicleCurrentKM |                       75688 | 2.48%         |

### V11.2 KM constante por vehículo a nivel FILA (agenda cruda)

|                                | valor   |
|:-------------------------------|:--------|
| vehículos con >=2 filas con KM | 88143   |
| % con un único KM              | 99.99%  |

### V11.3 ¿KM coincide con VehicleCurrentKM del último turno / con el máximo? (vehículos con KM y >=1 VCK)

|                            |   vehículos | pct    |
|:---------------------------|------------:|:-------|
| vehículos                  |      101768 | 100.0% |
| KM == VCK del último turno |       97549 | 95.9%  |
| KM == max(VCK)             |       94358 | 92.7%  |
| KM >= max(VCK)             |       94548 | 92.9%  |
| KM < max(VCK)              |        7220 | 7.1%   |

_La afirmación 'KM coincide con VehicleCurrentKM en el último turno' NO está en el script original (tabla 0.2 solo mide constancia)._

### V11.4 Vehículos con >=2 VCK: KM == último VCK vs KM == primer VCK

|                                                              | valor   |
|:-------------------------------------------------------------|:--------|
| vehículos                                                    | 74508   |
| KM == último VCK                                             | 95.6%   |
| KM == primer VCK                                             | 4.0%    |
| KM > último VCK (odómetro posterior al último turno con VCK) | 0.5%    |
