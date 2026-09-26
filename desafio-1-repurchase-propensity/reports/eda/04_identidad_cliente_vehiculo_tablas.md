# Tablas generadas por scripts/eda/04_identidad_cliente_vehiculo.py

CUTOFF = 2026-08-25; proxy retorno_15m = otro mantenimiento completado en 456 días; flota = >= 3 vehículos por customer_id.

### 0.1 Cobertura de identificadores en turnos

|                             |   turnos |
|:----------------------------|---------:|
| total                       |   492442 |
| sin vehicle_id              |     2897 |
| sin customer_id             |     9398 |
| con ambos (base de trabajo) |   480565 |

### 0.2 ¿KM y VehicleCurrentKM varían entre turnos del mismo vehículo? (vehículos con >=2 valores no nulos)

|                  |   vehículos evaluados | % con un único valor (constante)   |
|:-----------------|----------------------:|:-----------------------------------|
| KM               |                 82347 | 100.0%                             |
| VehicleCurrentKM |                 75688 | 2.5%                               |

_Si KM es constante por vehículo, es un snapshot al momento de la extracción (último odómetro conocido) y NO puede usarse como feature as-of._

### 0.3 ¿KM coincide con VehicleCurrentKM del último turno con odómetro? (vehículos con KM y >=1 VehicleCurrentKM)

|                                                                          |   vehículos | pct    |
|:-------------------------------------------------------------------------|------------:|:-------|
| vehículos con KM y VehicleCurrentKM                                      |      101768 | 100.0% |
| KM == VehicleCurrentKM del ÚLTIMO turno                                  |       97549 | 95.9%  |
| KM == máximo VehicleCurrentKM                                            |       94358 | 92.7%  |
| KM == VehicleCurrentKM del PRIMER turno (solo vehículos con >=2 valores) |        2965 | 4.0%   |

### a.1 Vehículos por cantidad de customer_id distintos en la agenda

|   customer_id |   vehículos | pct   |
|--------------:|------------:|:------|
|             1 |       87306 | 79.0% |
|             2 |       19624 | 17.8% |
|             3 |        3083 | 2.8%  |
|             4 |         440 | 0.4%  |
|             5 |          85 | 0.1%  |
|             6 |           8 | 0.0%  |
|             7 |           4 | 0.0%  |
|             8 |           1 | 0.0%  |

### a.2 Patrón temporal de los vehículos multi-cliente

| patron                         |   vehículos | pct_multi   |
|:-------------------------------|------------:|:------------|
| secuencial (cambio permanente) |       17792 | 76.5%       |
| alternancia (uso compartido)   |        5224 | 22.5%       |
| ambiguo (cambio el mismo día)  |         229 | 1.0%        |

_23,245 vehículos con >1 customer_id; 35,836 cambios de cliente entre turnos consecutivos._

### a.3 Patrón temporal por cantidad de clientes

|   n_cust |   alternancia (uso compartido) |   ambiguo (cambio el mismo día) |   secuencial (cambio permanente) |
|---------:|-------------------------------:|--------------------------------:|---------------------------------:|
|        2 |                           3763 |                             162 |                            15699 |
|        3 |                           1147 |                              61 |                             1875 |
|        4 |                            247 |                               6 |                              187 |
|        5 |                             67 |                               0 |                               31 |

### a.4 Qué acompaña a un cambio de customer_id (pares de turnos consecutivos, vehículos multi-cliente)

|                                      | en cambio de cliente   | en turnos consecutivos sin cambio   |
|:-------------------------------------|:-----------------------|:------------------------------------|
| cambia ScheduleSource                | 52.8%                  | 15.7%                               |
| cambia dealer_id                     | 21.8%                  | 7.4%                                |
| cruce Dealer<->FordPass              | 34.1%                  | 11.4%                               |
| cliente nuevo tiene >=3 vehículos    | 30.2%                  | 26.4%                               |
| cliente anterior tiene >=3 vehículos | 37.8%                  | 26.4%                               |

_n cambios = 35,836; n pares sin cambio = 100,962_

### a.5 Canal del turno anterior vs canal del turno donde cambia el cliente

| prev_src   |   CAF |   Dealer |   FordPass |   Mobile |   WEB |   All |
|:-----------|------:|---------:|-----------:|---------:|------:|------:|
| CAF        |     4 |       31 |         46 |        1 |     4 |    86 |
| Dealer     |    24 |    15004 |       8734 |     1448 |  2713 | 27923 |
| FordPass   |     4 |     3472 |       1355 |      129 |   226 |  5186 |
| Mobile     |     0 |      295 |         86 |       48 |    30 |   459 |
| WEB        |     2 |     1463 |        189 |       35 |   493 |  2182 |
| All        |    34 |    20265 |      10410 |     1661 |  3466 | 35836 |

### a.6 Multi-cliente según mezcla de canales del vehículo (vehículos con >=2 turnos)

|                               |   vehículos | % con >1 customer_id   |
|:------------------------------|------------:|:-----------------------|
| mezcla FordPass y no-FordPass |       28041 | 42.3%                  |
| un solo tipo de canal         |       56101 | 20.3%                  |

### a.6b % multi-cliente según mezcla de canal, estratificado por n° de turnos del vehículo

| n_turnos   | % multi | mezcla FP y no-FP   | % multi | un solo tipo de canal   |   n mezcla FP y no-FP |   n un solo tipo de canal |
|:-----------|:------------------------------|:----------------------------------|----------------------:|--------------------------:|
| 2          | 28.8%                         | 9.3%                              |                  2537 |                     16362 |
| 3          | 33.6%                         | 16.2%                             |                  3673 |                     10978 |
| 4-5        | 38.7%                         | 22.1%                             |                  7087 |                     13169 |
| 6-8        | 44.4%                         | 28.8%                             |                  7584 |                      9082 |
| 9+         | 53.0%                         | 39.0%                             |                  7160 |                      6510 |

_La brecha se reduce de 22 pp (sin estratificar) a 14-19 pp dentro de cada franja de turnos, pero no desaparece._

### a.7 Transferencias probables por nivel de confianza (acumulativo) y por año del cambio

|                                                                  |   transferencias |   vehículos |   2024 |   2025 |   2026 (hasta 25/8) |   gap mediano (días) |   edad mediana (años) |
|:-----------------------------------------------------------------|-----------------:|------------:|-------:|-------:|--------------------:|---------------------:|----------------------:|
| (i) solo secuencial                                              |            20137 |       17792 |   3845 |   8939 |                7353 |                  168 |                  2.05 |
| (ii) sin cruce Dealer<->FordPass                                 |            12991 |       11611 |   2623 |   5527 |                4841 |                  168 |                  2.34 |
| (iii) estricta: sin cruce de canal y ambos clientes <3 vehículos |             7417 |        6940 |   1372 |   3325 |                2720 |                  189 |                  2.55 |

_Año = fecha del primer turno del cliente nuevo. 2024 subestima (no se ven turnos previos a 2024-01) y 2026 es parcial._

### a.8 Edad del vehículo (años desde WarrantyStartDate) al momento de la transferencia (nivel iii)

| edad_veh_anios   |   transferencias | pct   |
|:-----------------|-----------------:|:------|
| <1               |              804 | 10.9% |
| 1-2              |             1958 | 26.5% |
| 2-3              |             1541 | 20.8% |
| 3-4              |              817 | 11.0% |
| 4-5              |              704 | 9.5%  |
| 5-7              |              692 | 9.4%  |
| 7-10             |              656 | 8.9%  |
| 10+              |              226 | 3.1%  |

_n = 7,417; sin WarrantyStartDate: 19_

### a.9 Tasa anual aproximada de transferencia (2025, nivel iii)

|                                   | valor   |
|:----------------------------------|:--------|
| transferencias 2025               | 3325    |
| vehículos con algún turno en 2025 | 73701   |
| tasa                              | 4.5%    |

### a.8b Tasa de transferencia 2025 por edad del vehículo (transferencias / vehículos activos en 2025 en esa franja de edad)

|      |   transferencias 2025 (iii) | % de las transferencias (iii)   |   vehículos activos 2025 | % del parque activo   | tasa (iii) por vehículo-año   | tasa (iii) sobre activos con >=2 turnos   | tasa (i) sobre activos con >=2 turnos   |
|:-----|----------------------------:|:--------------------------------|-------------------------:|:----------------------|:------------------------------|:------------------------------------------|:----------------------------------------|
| <1   |                         313 | 9.4%                            |                    20567 | 28.1%                 | 1.5%                          | 1.7%                                      | 9.0%                                    |
| 1-2  |                         920 | 27.7%                           |                    18508 | 25.3%                 | 5.0%                          | 5.1%                                      | 15.2%                                   |
| 2-3  |                         596 | 18.0%                           |                     9262 | 12.7%                 | 6.4%                          | 6.7%                                      | 18.2%                                   |
| 3-4  |                         389 | 11.7%                           |                     5892 | 8.1%                  | 6.6%                          | 7.0%                                      | 15.6%                                   |
| 4-5  |                         357 | 10.8%                           |                     4917 | 6.7%                  | 7.3%                          | 7.8%                                      | 14.9%                                   |
| 5-7  |                         322 | 9.7%                            |                     4841 | 6.6%                  | 6.7%                          | 7.7%                                      | 14.8%                                   |
| 7-10 |                         319 | 9.6%                            |                     6326 | 8.7%                  | 5.0%                          | 6.5%                                      | 11.5%                                   |
| 10+  |                         101 | 3.0%                            |                     2776 | 3.8%                  | 3.6%                          | 6.1%                                      | 10.0%                                   |

_Edad del parque medida al 2025-07-01. La tasa por vehículo-año es una meseta entre los años 1 y 7: la concentración de a.8 en 1-4 años refleja que el parque observado es joven, no una mayor propensión a transferirse a los 2-3 años._

### a.12 Vehículos VENDIDOS 2024-26, secuenciales con 2 clientes: posición del comprador en la secuencia

| caso                                                        |   vehículos | pct   |
|:------------------------------------------------------------|------------:|:------|
| comprador primero, otro después (transferencia o artefacto) |        3207 | 57.5% |
| comprador no aparece                                        |        1263 | 22.6% |
| otro primero, comprador después (artefacto seguro)          |        1112 | 19.9% |

### a.12b Los 'artefactos seguros': canal del cambio y momento del primer turno del id 'otro' respecto de DeliveryDate

|                                                        |   vehículos | pct    |
|:-------------------------------------------------------|------------:|:-------|
| artefactos seguros                                     |        1112 | 100.0% |
| el cambio es cruce Dealer<->FordPass                   |         350 | 31.5%  |
| el cambio es Dealer -> Dealer                          |         633 | 56.9%  |
| 1er turno del 'otro' ANTES de la entrega (pre-entrega) |         310 | 27.9%  |
| 0-30 días después de la entrega                        |         139 | 12.5%  |
| > 180 días después de la entrega                       |         344 | 30.9%  |
| 1er turno del 'otro' incluye ítem de mantenimiento     |         459 | 41.3%  |

_Solo un tercio de los artefactos seguros es un cruce Dealer<->FordPass: el filtro de canal del nivel (ii) no limpia los artefactos Dealer->Dealer (mismo dueño con dos ids cargados por el dealer, o comprador-empresa y chofer)._

### a.10.1 Ejemplo de cambio permanente (transferencia probable) — vehículo b9f0…41

|    | event_date   | customer_id   | dealer_id   | ScheduleSource   | StatusARG      |   maint_number |     KM |
|---:|:-------------|:--------------|:------------|:-----------------|:---------------|---------------:|-------:|
|  0 | 2024-03-20   | affd…7d       | bd95…30     | Dealer           | (60) Concluido |            nan | 374920 |
|  1 | 2024-07-11   | fe61…93       | bd95…30     | Dealer           | (60) Concluido |            nan | 374920 |
|  2 | 2024-10-24   | fe61…93       | bd95…30     | Dealer           | (60) Concluido |            nan | 374920 |
|  3 | 2024-12-30   | fe61…93       | bd95…30     | Dealer           | (60) Concluido |             20 | 374920 |
|  4 | 2025-04-02   | fe61…93       | bd95…30     | Dealer           | (60) Concluido |             20 | 374920 |
|  5 | 2025-07-15   | fe61…93       | bd95…30     | Dealer           | (60) Concluido |             20 | 374920 |
|  6 | 2025-09-18   | fe61…93       | bd95…30     | Dealer           | (60) Concluido |            nan | 374920 |
|  7 | 2025-11-19   | fe61…93       | bd95…30     | Dealer           | (60) Concluido |             20 | 374920 |
|  8 | 2026-04-21   | fe61…93       | bd95…30     | Dealer           | (60) Concluido |            nan | 374920 |
|  9 | 2026-06-18   | fe61…93       | bd95…30     | Dealer           | (60) Concluido |            nan | 374920 |

### a.10.2 Ejemplo de cambio permanente (transferencia probable) — vehículo f0c8…9e

|    | event_date   | customer_id   | dealer_id   | ScheduleSource   | StatusARG      |   maint_number |    KM |
|---:|:-------------|:--------------|:------------|:-----------------|:---------------|---------------:|------:|
|  0 | 2024-04-12   | ca99…7b       | 3262…c4     | FordPass         | (60) Concluido |            nan | 31628 |
|  1 | 2024-12-30   | d70b…31       | 3262…c4     | WEB              | (60) Concluido |              1 | 31628 |

### a.11.1 Ejemplo de alternancia (uso compartido / flota / chofer) — vehículo 81a8…91

|    | event_date   | customer_id   | dealer_id   | ScheduleSource   | StatusARG      |   maint_number |     KM |
|---:|:-------------|:--------------|:------------|:-----------------|:---------------|---------------:|-------:|
|  0 | 2024-07-05   | ea83…ed       | 2243…64     | Dealer           | (60) Concluido |             10 | 132643 |
|  1 | 2025-01-02   | ea83…ed       | 2243…64     | Dealer           | (60) Concluido |             11 | 132643 |
|  2 | 2025-01-16   | ea83…ed       | 2243…64     | Dealer           | (60) Concluido |            nan | 132643 |
|  3 | 2025-04-03   | 1f52…f5       | 2243…64     | WEB              | (60) Concluido |             12 | 132643 |
|  4 | 2025-05-13   | ea83…ed       | 2243…64     | Dealer           | (60) Concluido |            nan | 132643 |
|  5 | 2025-09-12   | 1f52…f5       | 2243…64     | Mobile           | (60) Concluido |             13 | 132643 |
|  6 | 2025-11-10   | 1f52…f5       | 2243…64     | Dealer           | (60) Concluido |            nan | 132643 |

### a.11.2 Ejemplo de alternancia (uso compartido / flota / chofer) — vehículo f005…db

|    | event_date   | customer_id   | dealer_id   | ScheduleSource   | StatusARG             |   maint_number |    KM |
|---:|:-------------|:--------------|:------------|:-----------------|:----------------------|---------------:|------:|
|  0 | 2024-10-02   | cc21…e7       | 80f9…65     | Dealer           | (90) Concluido sin OS |            nan | 46874 |
|  1 | 2025-01-21   | 15c0…39       | 80f9…65     | FordPass         | (60) Concluido        |              1 | 46874 |
|  2 | 2025-03-26   | cc21…e7       | 80f9…65     | Dealer           | (60) Concluido        |            nan | 46874 |
|  3 | 2025-03-26   | cc21…e7       | 80f9…65     | Dealer           | (70) Cancelado        |            nan | 46874 |
|  4 | 2025-07-24   | 15c0…39       | 80f9…65     | FordPass         | (60) Concluido        |              2 | 46874 |
|  5 | 2026-03-25   | 15c0…39       | 80f9…65     | FordPass         | (70) Cancelado        |              6 | 46874 |
|  6 | 2026-03-25   | 15c0…39       | 80f9…65     | FordPass         | (60) Concluido        |              3 | 46874 |

### b.1 Vehículos vendidos con turnos: ¿el comprador aparece en la agenda de ese vehículo?

|                                                                                    |   vehículos | pct    |
|:-----------------------------------------------------------------------------------|------------:|:-------|
| vendidos y con turnos (customer_id no nulo)                                        |       41906 | 100.0% |
| comprador aparece en la agenda del vehículo                                        |       29576 | 70.6%  |
| comprador es el PRIMER cliente de la agenda                                        |       27695 | 66.1%  |
| comprador es el ÚLTIMO cliente (vigente al CUTOFF)                                 |       25008 | 59.7%  |
| comprador NO aparece en este vehículo pero sí en otros (sobre los que no aparecen) |        4225 | 34.3%  |

### b.2 Comprador en agenda según PersonType del comprador

| PersonType   |     n | % comprador en agenda   |
|:-------------|------:|:------------------------|
| 25           |   348 | 4.3%                    |
| 29           |    23 | 73.9%                   |
| F            | 24796 | 82.2%                   |
| J            | 16721 | 54.8%                   |

### b.3 Comprador en agenda según BusinessUnit

| BusinessUnit   |     n | % comprador en agenda   |
|:---------------|------:|:------------------------|
| Ford Blue      | 29865 | 71.5%                   |
| Ford Pro       | 12041 | 68.3%                   |

### b.4 Comprador en agenda según SalesChannel

| SalesChannel   |     n | % comprador en agenda   |
|:---------------|------:|:------------------------|
| CONSORTIUM     |  5013 | 78.2%                   |
| DIRECT SALES   |  5607 | 55.7%                   |
| HR             |   439 | 3.0%                    |
| ROR            | 30847 | 73.0%                   |

### b.5 PersonType x BusinessUnit (vehículos vendidos con turnos): % comprador en agenda

| PersonType   | Ford Blue   | Ford Pro   |
|:-------------|:------------|:-----------|
| 25           | 2.3%        | 21.6%      |
| 29           | 75.0%       | 66.7%      |
| F            | 82.1%       | 82.8%      |
| J            | 52.6%       | 57.9%      |

### b.6 Cuando el comprador NO aparece: ¿el cliente vigente del vehículo es una flota (>=3 vehículos en agenda)?

| k                    |     n | % cliente vigente es flota   |
|:---------------------|------:|:-----------------------------|
| comprador aparece    | 29576 | 13.8%                        |
| comprador no aparece | 12330 | 18.3%                        |

### b.7 Concentración de compradores en canal HR y PersonType 25

|                   |   ventas |   compradores distintos |   ventas del comprador más frecuente | mismo id top en ambos   |
|:------------------|---------:|------------------------:|-------------------------------------:|:------------------------|
| SalesChannel = HR |     1060 |                     292 |                                  752 | True                    |
| PersonType = 25   |      656 |                     219 |                                  387 | True                    |

### c.1 Distribución de vehículos por customer_id (tamaño de flota) en sales y en agenda

| vehicle_id   |   clientes en sales |   vehículos en sales |   clientes en agenda |   vehículos en agenda |
|:-------------|--------------------:|---------------------:|---------------------:|----------------------:|
| 1            |               42425 |                42425 |                92035 |                 92035 |
| 2            |                2349 |                 4698 |                 9306 |                 18612 |
| 3-9          |                1011 |                 4108 |                 2808 |                 11305 |
| 10-49        |                 141 |                 2638 |                  313 |                  5837 |
| 50+          |                  33 |                 5515 |                   62 |                 10283 |
| total        |               45959 |                59384 |               104524 |                138072 |

_Flota = customer_id con >=3 vehículos. En sales: 1,185 clientes flota con 12,261 vehículos (20.6% de las ventas). En agenda: 3,183 clientes flota con 27,425 vehículos-cliente._

### c.2 Los 8 customer_id con más vehículos en la agenda

| customer_id   |   vehículos |   dealers distintos | % turnos canal Dealer   | % turnos concluidos   | es comprador en sales   |   vehículos comprados en sales |
|:--------------|------------:|--------------------:|:------------------------|:----------------------|:------------------------|-------------------------------:|
| c681…28       |         849 |                  40 | 100.0%                  | 70.1%                 | True                    |                            339 |
| 9c91…72       |         829 |                  53 | 99.6%                   | 69.2%                 | False                   |                              0 |
| a86b…17       |         583 |                  48 | 97.9%                   | 64.9%                 | False                   |                              0 |
| 2fc0…83       |         531 |                  21 | 100.0%                  | 67.1%                 | True                    |                             87 |
| eb16…1a       |         526 |                  31 | 99.8%                   | 77.3%                 | False                   |                              0 |
| 754a…40       |         417 |                  56 | 99.9%                   | 73.6%                 | True                    |                            327 |
| 1e7e…2f       |         359 |                   2 | 100.0%                  | 57.9%                 | True                    |                              8 |
| 331c…fe       |         335 |                  53 | 99.1%                   | 68.8%                 | True                    |                              8 |

### c.3 Ventas: tamaño de flota del comprador x BusinessUnit

| flota_cat   |   Ford Blue |   Ford Pro |   UNKNOWN |   All |
|:------------|------------:|-----------:|----------:|------:|
| 1           |       32975 |       9449 |         1 | 42425 |
| 2           |        3366 |       1332 |         0 |  4698 |
| 3-9         |        1739 |       2369 |         0 |  4108 |
| 10-49       |         554 |       2084 |         0 |  2638 |
| 50+         |        1808 |       3707 |         0 |  5515 |
| All         |       40442 |      18941 |         1 | 59384 |

### c.4 Ventas: % Ford Pro según tamaño de flota, y % de cada BusinessUnit que es flota (>=3)

| flota_cat   | Ford Blue   | Ford Pro   | UNKNOWN   |
|:------------|:------------|:-----------|:----------|
| 1           | 77.7%       | 22.3%      | 0.0%      |
| 2           | 71.6%       | 28.4%      | 0.0%      |
| 3-9         | 42.3%       | 57.7%      | 0.0%      |
| 10-49       | 21.0%       | 79.0%      | 0.0%      |
| 50+         | 32.8%       | 67.2%      | 0.0%      |

_Ford Pro entre compradores de 1 vehículo: 22.3%; Ford Pro que son flota (>=3): 43.1%; Ford Blue que son flota: 10.1%_

### c.5 Ventas: tamaño de flota x PersonType

| flota_cat   |   25 |   29 |   30 |     F |     J |   All |
|:------------|-----:|-----:|-----:|------:|------:|------:|
| 1           |  169 |  149 |    9 | 32390 |  9676 | 42393 |
| 2           |   22 |    2 |    0 |  2005 |  2667 |  4696 |
| 3-9         |   34 |    2 |    0 |   458 |  3613 |  4107 |
| 10-49       |   16 |    0 |    0 |    47 |  2575 |  2638 |
| 50+         |  415 |    0 |    0 |     0 |  5100 |  5515 |
| All         |  656 |  153 |    9 | 34900 | 23631 | 59349 |

### c.6 % de vehículos con >=1 mantenimiento programado completado en cada año de vida (años enteramente observados), por grupo

|   anio_vida | % 2 vehículos   | % flota (>=3)   | % particular (1)   |   n 2 vehículos |   n flota (>=3) |   n particular (1) |
|------------:|:----------------|:----------------|:-------------------|----------------:|----------------:|-------------------:|
|           1 | 74.3%           | 73.0%           | 71.6%              |            4932 |            5231 |              25123 |
|           2 | 78.1%           | 68.9%           | 79.2%              |            3764 |            5938 |              23462 |
|           3 | 63.8%           | 55.5%           | 70.5%              |            2206 |            4878 |              12647 |
|           4 | 56.2%           | 51.7%           | 62.8%              |            1768 |            2523 |               9289 |
|           5 | 44.9%           | 47.6%           | 55.5%              |            1553 |            1505 |               7713 |
|           6 | 32.8%           | 26.6%           | 40.0%              |             957 |             830 |               5436 |
|           7 | 30.2%           | 23.5%           | 34.9%              |             705 |             818 |               5452 |
|           8 | 25.1%           | 20.4%           | 30.7%              |             717 |             682 |               6081 |

_Población: vehículos con al menos un turno en 2024-2026 (sesgo de supervivencia: no incluye vehículos que dejaron de venir antes de 2024). Año de vida k = [WSD + (k-1) años, WSD + k años)._

### c.6b Años de vida 1 y 2 desde SALES (incluye vendidos que nunca tuvieron turno; flota = sales ∪ agenda)

|   anio_vida | % 2 vehículos   | % flota (>=3)   | % particular (1)   |   n 2 vehículos |   n flota (>=3) |   n particular (1) |
|------------:|:----------------|:----------------|:-------------------|----------------:|----------------:|-------------------:|
|           1 | 69.9%           | 59.1%           | 64.8%              |            5317 |            9380 |              23728 |
|           2 | 77.5%           | 66.4%           | 73.5%              |            1870 |            3004 |               8366 |

_Comparar con c.6: al incluir a los que nunca vinieron, la flota ya está 5-6 pp por debajo del particular en el año 1 (c.6 la mostraba igual o arriba)._

### c.7 Turnos hasta el CUTOFF por grupo de flota del cliente: estado y canal

| grupo_flota    |   turnos | no_show   | cancelado   | concluido   | con_mantenimiento   | FordPass   | Dealer   | reprogramado   |
|:---------------|---------:|:----------|:------------|:------------|:--------------------|:-----------|:---------|:---------------|
| 2 vehículos    |    64783 | 5.0%      | 20.6%       | 70.8%       | 55.0%               | 24.4%      | 70.7%    | 24.2%          |
| flota (>=3)    |    92318 | 5.8%      | 20.9%       | 70.5%       | 57.5%               | 7.4%       | 82.9%    | 25.8%          |
| particular (1) |   319780 | 5.5%      | 20.6%       | 70.0%       | 53.5%               | 24.9%      | 69.9%    | 24.3%          |

### d.1 Overlap de dealer_id entre sales y agenda

|                                     | valor   |
|:------------------------------------|:--------|
| dealers en sales                    | 107     |
| dealers en agenda                   | 95      |
| ids en ambas                        | 61      |
| solo sales                          | 46      |
| solo agenda                         | 34      |
| % ventas cuyo dealer está en agenda | 76.1%   |
| % turnos cuyo dealer está en sales  | 75.7%   |

### d.2 ¿La ausencia del dealer vendedor en la agenda explica que el vehículo no aparezca? (% vehículos vendidos con algún turno)

| dealer_en_agenda   |     n | % vehículos con turnos   |
|:-------------------|------:|:-------------------------|
| False              | 14169 | 71.9%                    |
| True               | 45215 | 70.8%                    |

### d.3 Concentración del dealer del primer turno según el dealer vendedor esté o no en la agenda (mediana del share del dealer más frecuente, %)

| dealer en agenda   |   dealers |   share_top_mediana |
|:-------------------|----------:|--------------------:|
| False              |        41 |               59    |
| True               |        58 |               57.65 |

_Si un dealer vendedor ausente de la agenda concentra sus vehículos en un único dealer de agenda, probablemente sea el mismo dealer con otro código._

### d.4 Los 10 dealers vendedores ausentes de la agenda con más ventas

| dealer_id    |   vehículos | top dealer agenda = mismo id   | share del dealer agenda más frecuente   | dealer en agenda   |
|:-------------|------------:|:-------------------------------|:----------------------------------------|:-------------------|
| 85cc31b84261 |        1910 | 0.0%                           | 67.1%                                   | False              |
| 4cc4b715e345 |        1844 | 0.0%                           | 60.8%                                   | False              |
| d8c874bd7792 |        1763 | 0.0%                           | 59.7%                                   | False              |
| d67af46fa9e6 |         828 | 0.0%                           | 36.6%                                   | False              |
| 9a9814bc02ab |         675 | 0.0%                           | 17.0%                                   | False              |
| 1141a4ef5ea3 |         608 | 0.0%                           | 13.0%                                   | False              |
| d6a79a9dc5b0 |         510 | 0.0%                           | 41.8%                                   | False              |
| 98ac3977c8a5 |         478 | 0.0%                           | 40.4%                                   | False              |
| aa6414339ccd |         458 | 0.0%                           | 51.1%                                   | False              |
| f05cfd21bbf9 |         246 | 0.0%                           | 53.7%                                   | False              |

### d.4b Dealers vendedores ausentes: naturaleza de su destino principal

|                                                                  | valor   |
|:-----------------------------------------------------------------|:--------|
| dealers ausentes con ventas rastreables                          | 41      |
| ventas                                                           | 10042   |
| cuyo destino principal es un dealer SOLO-agenda (34)             | 13      |
| % de sus ventas                                                  | 65.0%   |
| destinos principales distintos                                   | 28      |
| destinos compartidos por >1 dealer ausente                       | 9       |
| con share del destino principal >= 50 %                          | 26      |
| dealers presentes cuyo destino principal es él mismo             | 86.2%   |
| dealers presentes con >= 50 % de sus primeros turnos en él mismo | 53.4%   |

_'Mismo dealer con otro código' es plausible solo para los ausentes que derivan a un dealer solo-agenda; los que derivan a un dealer que ya vende con su id son más bien puntos de venta / sucursales de otro taller._

### d.5 % de vehículos vendidos cuyo primer mantenimiento completado / primer turno ocurre en el dealer que los vendió

|                                                 |   vehículos | % 1er mantenimiento en dealer vendedor   | % 1er turno (cualquiera) en dealer vendedor   |
|:------------------------------------------------|------------:|:-----------------------------------------|:----------------------------------------------|
| todos los vendidos con mantenimiento completado |       36705 | 38.1%                                    | 39.1%                                         |
| solo si el dealer vendedor está en la agenda    |       28112 | 49.7%                                    | 51.1%                                         |

### d.6 % 1er mantenimiento en el dealer vendedor por BusinessUnit y PersonType (dealer vendedor en agenda)

|           |     n | % mismo dealer   |
|:----------|------:|:-----------------|
| Ford Blue | 20331 | 48.8%            |
| Ford Pro  |  7781 | 52.0%            |
| 25        |     2 | 0.0%             |
| 29        |     9 | 55.6%            |
| F         | 16919 | 50.8%            |
| J         | 11181 | 48.0%            |

### g.0 Proxy de retorno: eventos elegibles

|                                                       | valor      |
|:------------------------------------------------------|:-----------|
| mantenimientos completados con d <= CUTOFF - 456 días | 105782     |
| vehículos                                             | 55712      |
| primer evento                                         | 2024-01-02 |
| último evento                                         | 2025-05-26 |
| retorno_15m base                                      | 78.5%      |

### g.1 Retorno a 15 meses (proxy) por nivel de cada feature candidata

|                                                                          |   n eventos | retorno_15m   |   lift vs base |
|:-------------------------------------------------------------------------|------------:|:--------------|---------------:|
| ('es_comprador', 'comprador')                                            |        8875 | 88.2%         |          1.124 |
| ('es_comprador', 'otro')                                                 |        5885 | 89.1%         |          1.135 |
| ('es_comprador', 'sin venta')                                            |       91022 | 76.8%         |          0.979 |
| ('n_clientes_distintos_vehiculo (as-of)', '1')                           |       92577 | 77.9%         |          0.993 |
| ('n_clientes_distintos_vehiculo (as-of)', '2')                           |       11944 | 82.3%         |          1.049 |
| ('n_clientes_distintos_vehiculo (as-of)', '3+')                          |        1261 | 84.4%         |          1.075 |
| ('tamaño_flota_cliente (agenda, as-of)', '1')                            |       80212 | 77.5%         |          0.988 |
| ('tamaño_flota_cliente (agenda, as-of)', '10+')                          |        9621 | 80.1%         |          1.021 |
| ('tamaño_flota_cliente (agenda, as-of)', '2')                            |        8419 | 82.4%         |          1.05  |
| ('tamaño_flota_cliente (agenda, as-of)', '3-9')                          |        7530 | 82.3%         |          1.049 |
| ('tamaño_flota_comprador (sales)', '1')                                  |       10263 | 88.6%         |          1.129 |
| ('tamaño_flota_comprador (sales)', '10-49')                              |         549 | 86.0%         |          1.096 |
| ('tamaño_flota_comprador (sales)', '2')                                  |        1784 | 89.2%         |          1.136 |
| ('tamaño_flota_comprador (sales)', '3-9')                                |        1332 | 88.3%         |          1.125 |
| ('tamaño_flota_comprador (sales)', '50+')                                |         832 | 88.5%         |          1.127 |
| ('mismo_dealer_que_venta', 'no')                                         |        5596 | 89.3%         |          1.138 |
| ('mismo_dealer_que_venta', 'sin venta / dealer no en agenda')            |       94344 | 77.2%         |          0.984 |
| ('mismo_dealer_que_venta', 'sí')                                         |        5842 | 88.8%         |          1.132 |
| ('cambio_de_dealer (vs turno anterior)', 'no')                           |       61812 | 81.2%         |          1.035 |
| ('cambio_de_dealer (vs turno anterior)', 'primer turno')                 |       38607 | 73.8%         |          0.941 |
| ('cambio_de_dealer (vs turno anterior)', 'sí')                           |        5363 | 80.1%         |          1.02  |
| ('cambio_de_dealer (vs mantenimiento anterior)', 'no')                   |       46023 | 83.2%         |          1.061 |
| ('cambio_de_dealer (vs mantenimiento anterior)', 'primer mantenimiento') |       55712 | 74.4%         |          0.948 |
| ('cambio_de_dealer (vs mantenimiento anterior)', 'sí')                   |        4047 | 80.5%         |          1.026 |
| ('meses_desde_transferencia', '0-3')                                     |        7854 | 80.7%         |          1.028 |
| ('meses_desde_transferencia', '12+')                                     |         150 | 82.7%         |          1.053 |
| ('meses_desde_transferencia', '3-6')                                     |        1814 | 85.2%         |          1.086 |
| ('meses_desde_transferencia', '6-12')                                    |        1531 | 83.6%         |          1.065 |
| ('BusinessUnit (sales)', 'Ford Blue')                                    |       10108 | 89.8%         |          1.145 |
| ('BusinessUnit (sales)', 'Ford Pro')                                     |        4652 | 85.8%         |          1.094 |
| ('BusinessUnit (sales)', 'sin venta')                                    |       91022 | 76.8%         |          0.979 |
| ('PersonType (sales)', '25')                                             |          58 | 87.9%         |          1.121 |
| ('PersonType (sales)', '29')                                             |           1 | 100.0%        |          1.274 |
| ('PersonType (sales)', 'F')                                              |        7899 | 87.5%         |          1.114 |
| ('PersonType (sales)', 'J')                                              |        6798 | 89.8%         |          1.145 |
| ('PersonType (sales)', 'sin venta')                                      |       91026 | 76.8%         |          0.979 |
| ('n° de mantenimiento del evento', '1')                                  |       22800 | 82.8%         |          1.056 |
| ('n° de mantenimiento del evento', '2')                                  |       13524 | 82.5%         |          1.052 |
| ('n° de mantenimiento del evento', '3')                                  |       10624 | 80.7%         |          1.028 |
| ('n° de mantenimiento del evento', '4')                                  |        8924 | 78.9%         |          1.005 |
| ('n° de mantenimiento del evento', '5')                                  |        8076 | 74.5%         |          0.95  |
| ('n° de mantenimiento del evento', '6+')                                 |       41834 | 74.9%         |          0.954 |

_Base = 78.5% sobre 105,782 eventos. Lift = tasa del nivel / tasa base._

### g.2 Rango de retorno entre niveles (puntos porcentuales, niveles con n >= 500)

| feature                                      | min   | max   |   rango_pp |
|:---------------------------------------------|:------|:------|-----------:|
| PersonType (sales)                           | 76.8% | 89.8% |       13   |
| BusinessUnit (sales)                         | 76.8% | 89.8% |       13   |
| es_comprador                                 | 76.8% | 89.1% |       12.2 |
| mismo_dealer_que_venta                       | 77.2% | 89.3% |       12.1 |
| cambio_de_dealer (vs mantenimiento anterior) | 74.4% | 83.2% |        8.8 |
| n° de mantenimiento del evento               | 74.5% | 82.8% |        8.3 |
| cambio_de_dealer (vs turno anterior)         | 73.8% | 81.2% |        7.4 |
| n_clientes_distintos_vehiculo (as-of)        | 77.9% | 84.4% |        6.5 |
| tamaño_flota_cliente (agenda, as-of)         | 77.5% | 82.4% |        4.9 |
| meses_desde_transferencia                    | 80.7% | 85.2% |        4.6 |
| tamaño_flota_comprador (sales)               | 86.0% | 89.2% |        3.2 |

### g.3 Retorno por es_comprador x PersonType del comprador (solo vendidos)

| person_type   | % comprador   | % otro   |   n comprador |   n otro |
|:--------------|:--------------|:---------|--------------:|---------:|
| 25            | nan%          | 87.9%    |           nan |       58 |
| 29            | nan%          | 100.0%   |           nan |        1 |
| F             | 87.8%         | 86.5%    |          5911 |     1988 |
| J             | 89.1%         | 90.4%    |          2964 |     3834 |
| sin venta     | nan%          | 75.0%    |           nan |        4 |

### g.4 Retorno por es_comprador x BusinessUnit (solo vendidos)

| business_unit   | % comprador   | % otro   |   n comprador |   n otro |
|:----------------|:--------------|:---------|--------------:|---------:|
| Ford Blue       | 89.6%         | 90.2%    |          6105 |     4003 |
| Ford Pro        | 85.2%         | 86.7%    |          2770 |     1882 |

### g.5 Retorno por tamaño de flota (agenda as-of) x n° de mantenimiento

| n_maint_cat   | 1     | 10+   | 2     | 3-9   |
|:--------------|:------|:------|:------|:------|
| 1             | 82.8% | 80.5% | 85.1% | 81.9% |
| 2             | 81.8% | 85.0% | 85.2% | 85.0% |
| 3             | 79.8% | 85.0% | 82.7% | 82.0% |
| 4             | 77.4% | 81.1% | 84.7% | 84.7% |
| 5             | 75.7% | 57.4% | 84.7% | 82.5% |
| 6+            | 72.8% | 82.8% | 78.8% | 81.3% |

### g.6 Retorno según mismo dealer que venta x cambio de dealer vs mantenimiento anterior (solo vendidos con dealer en agenda)

| cambio_dealer_vs_maint_anterior   | % no   | % sí   |   n no |   n sí |
|:----------------------------------|:-------|:-------|-------:|-------:|
| no                                | 92.4%  | 92.4%  |   1280 |   1452 |
| primer mantenimiento              | 88.3%  | 87.7%  |   4078 |   4327 |
| sí                                | 90.8%  | 85.7%  |    238 |     63 |

### g.7 Sensibilidad: retorno a 12 meses por nivel (mismas features)

|                                                                          |   n eventos | retorno_12m   |   lift vs base |
|:-------------------------------------------------------------------------|------------:|:--------------|---------------:|
| ('es_comprador', 'comprador')                                            |        8875 | 81.2%         |          1.118 |
| ('es_comprador', 'otro')                                                 |        5885 | 83.1%         |          1.145 |
| ('es_comprador', 'sin venta')                                            |       91022 | 71.1%         |          0.979 |
| ('n_clientes_distintos_vehiculo (as-of)', '1')                           |       92577 | 71.7%         |          0.988 |
| ('n_clientes_distintos_vehiculo (as-of)', '2')                           |       11944 | 78.4%         |          1.08  |
| ('n_clientes_distintos_vehiculo (as-of)', '3+')                          |        1261 | 82.2%         |          1.132 |
| ('tamaño_flota_cliente (agenda, as-of)', '1')                            |       80212 | 70.7%         |          0.974 |
| ('tamaño_flota_cliente (agenda, as-of)', '10+')                          |        9621 | 77.7%         |          1.07  |
| ('tamaño_flota_cliente (agenda, as-of)', '2')                            |        8419 | 78.3%         |          1.079 |
| ('tamaño_flota_cliente (agenda, as-of)', '3-9')                          |        7530 | 79.5%         |          1.095 |
| ('tamaño_flota_comprador (sales)', '1')                                  |       10263 | 80.8%         |          1.113 |
| ('tamaño_flota_comprador (sales)', '10-49')                              |         549 | 83.8%         |          1.154 |
| ('tamaño_flota_comprador (sales)', '2')                                  |        1784 | 84.2%         |          1.161 |
| ('tamaño_flota_comprador (sales)', '3-9')                                |        1332 | 85.1%         |          1.173 |
| ('tamaño_flota_comprador (sales)', '50+')                                |         832 | 84.7%         |          1.167 |
| ('mismo_dealer_que_venta', 'no')                                         |        5596 | 82.5%         |          1.137 |
| ('mismo_dealer_que_venta', 'sin venta / dealer no en agenda')            |       94344 | 71.4%         |          0.984 |
| ('mismo_dealer_que_venta', 'sí')                                         |        5842 | 82.1%         |          1.131 |
| ('cambio_de_dealer (vs turno anterior)', 'no')                           |       61812 | 76.7%         |          1.057 |
| ('cambio_de_dealer (vs turno anterior)', 'primer turno')                 |       38607 | 65.6%         |          0.904 |
| ('cambio_de_dealer (vs turno anterior)', 'sí')                           |        5363 | 74.9%         |          1.032 |
| ('cambio_de_dealer (vs mantenimiento anterior)', 'no')                   |       46023 | 80.3%         |          1.106 |
| ('cambio_de_dealer (vs mantenimiento anterior)', 'primer mantenimiento') |       55712 | 65.9%         |          0.908 |
| ('cambio_de_dealer (vs mantenimiento anterior)', 'sí')                   |        4047 | 76.7%         |          1.057 |
| ('meses_desde_transferencia', '0-3')                                     |        7854 | 76.1%         |          1.048 |
| ('meses_desde_transferencia', '12+')                                     |         150 | 78.7%         |          1.084 |
| ('meses_desde_transferencia', '3-6')                                     |        1814 | 83.3%         |          1.147 |
| ('meses_desde_transferencia', '6-12')                                    |        1531 | 80.3%         |          1.107 |

_Base retorno_12m = 72.6%._

### g.8.0 Retorno a 15 m por edad del vehículo al evento (confundidor principal)

| edad_cat   |     n | tasa   |
|:-----------|------:|:-------|
| 2-4 años   | 29619 | 77.7%  |
| 4+ años    | 18040 | 58.9%  |
| <2 años    | 57678 | 85.2%  |

### g.8 Retorno a 15 m por nivel de cada feature, estratificado por edad del vehículo al evento

|                                                                          | % 2-4 años   | % 4+ años   | % <2 años   |   n 2-4 años |   n 4+ años |   n <2 años |
|:-------------------------------------------------------------------------|:-------------|:------------|:------------|-------------:|------------:|------------:|
| ('n_clientes_distintos_vehiculo (as-of)', '1')                           | 77.1%        | 58.2%       | 85.0%       |        25647 |       16413 |       50104 |
| ('n_clientes_distintos_vehiculo (as-of)', '2')                           | 81.1%        | 65.5%       | 86.6%       |         3542 |        1489 |        6882 |
| ('n_clientes_distintos_vehiculo (as-of)', '3+')                          | 86.0%        | 71.7%       | 85.8%       |          430 |         138 |         692 |
| ('tamaño_flota_cliente (agenda, as-of)', '1')                            | 76.6%        | 58.4%       | 85.3%       |        22530 |       15643 |       41724 |
| ('tamaño_flota_cliente (agenda, as-of)', '10+')                          | 80.7%        | 61.9%       | 82.2%       |         2939 |         721 |        5923 |
| ('tamaño_flota_cliente (agenda, as-of)', '2')                            | 80.3%        | 64.0%       | 87.0%       |         2104 |         942 |        5317 |
| ('tamaño_flota_cliente (agenda, as-of)', '3-9')                          | 82.2%        | 62.1%       | 85.8%       |         2046 |         734 |        4714 |
| ('cambio_de_dealer (vs mantenimiento anterior)', 'no')                   | 82.4%        | 70.3%       | 88.3%       |        16448 |        7353 |       22079 |
| ('cambio_de_dealer (vs mantenimiento anterior)', 'primer mantenimiento') | 71.1%        | 50.6%       | 83.1%       |        11846 |       10199 |       33384 |
| ('cambio_de_dealer (vs mantenimiento anterior)', 'sí')                   | 78.1%        | 62.7%       | 86.1%       |         1325 |         488 |        2215 |
| ('meses_desde_transferencia', '0-3')                                     | 79.3%        | 62.9%       | 85.2%       |         2196 |        1021 |        4619 |
| ('meses_desde_transferencia', '12+')                                     | 79.0%        | 61.5%       | 95.2%       |           62 |          26 |          62 |
| ('meses_desde_transferencia', '3-6')                                     | 85.7%        | 73.0%       | 87.9%       |          558 |         222 |        1026 |
| ('meses_desde_transferencia', '6-12')                                    | 83.3%        | 72.0%       | 87.0%       |          581 |         200 |         749 |
| ('es_comprador', 'comprador')                                            |              |             | 88.2%       |            0 |           0 |        8875 |
| ('es_comprador', 'otro')                                                 |              |             | 89.1%       |            0 |           0 |        5883 |
| ('es_comprador', 'sin venta')                                            | 77.7%        | 58.9%       | 84.0%       |        29619 |       18040 |       42920 |
| ('mismo_dealer_que_venta', 'no')                                         |              |             | 89.3%       |            0 |           0 |        5594 |
| ('mismo_dealer_que_venta', 'sin venta / dealer no en agenda')            | 77.7%        | 58.9%       | 84.2%       |        29619 |       18040 |       46242 |
| ('mismo_dealer_que_venta', 'sí')                                         |              |             | 88.8%       |            0 |           0 |        5842 |

_Comparar niveles dentro de cada columna (misma franja de edad). Los niveles 'sin venta' concentran vehículos viejos._

### e.1 Clientes con varios vehículos (actividad 2025-01-01 → CUTOFF)

|                                                                | valor   |
|:---------------------------------------------------------------|:--------|
| customer_id con algún turno 2025-26                            | 86580   |
| de los cuales con >=2 vehículos (cualquier turno)              | 7882    |
| vehículos-cliente en esos clientes                             | 30220   |
| % de los pares vehículo-cliente activos                        | 27.7%   |
| clientes VIGENTES (último turno) con vehículos activos 2025-26 | 78331   |
| de los cuales con >=2 vehículos vigentes                       | 5415    |
| vehículos en esos clientes                                     | 19909   |
| % de los vehículos activos                                     | 21.4%   |

### e.2 Distribución de vehículos activos 2025-26 por cliente vigente

|       |   clientes |   vehículos |
|:------|-----------:|------------:|
| 1     |      72916 |       72916 |
| 2     |       4030 |        8060 |
| 3-9   |       1194 |        4924 |
| 10-49 |        162 |        3086 |
| 50+   |         29 |        3839 |

### e.3 Clientes con >=2 vehículos que entran en ventana (mantenimiento completado + 12 meses) el mismo mes

|                                                                                  | valor   |
|:---------------------------------------------------------------------------------|:--------|
| ventanas (mantenimiento completado + 12 m), todas                                | 216655  |
| vehículos                                                                        | 86753   |
| clientes con >=2 vehículos en ventana el mismo mes (alguna vez)                  | 2253    |
| pares (cliente, mes) con >=2 vehículos                                           | 7068    |
| vehículos-ventana involucrados                                                   | 29301   |
| % de todas las ventanas                                                          | 13.5%   |
| ventanas en 2025-09 → 2026-08                                                    | 82140   |
| clientes con >=2 vehículos el mismo mes en ese período                           | 1193    |
| vehículos-ventana involucrados                                                   | 10795   |
| % de las ventanas del período                                                    | 13.1%   |
| [método original] ventanas 2025-09 → 2026-08 usando solo el ÚLTIMO mantenimiento | 17449   |
| [método original]   vehículos de clientes con >=2 el mismo mes                   | 1262    |
| [método original]   % coincidencia                                               | 7.2%    |

_El método original (solo último mantenimiento) daba 195 clientes / 1.262 vehículos / 7,2 %: subestimaba la población de ventanas ~5 veces._

### e.4 Distribución de vehículos por (cliente, mes de ventana) cuando hay >=2

|   n_veh |   pares cliente-mes |
|--------:|--------------------:|
|       2 |                4332 |
|       3 |                1022 |
|       4 |                 499 |
|       5 |                 275 |
|       6 |                 178 |
|       7 |                 122 |
|       8 |                 118 |
|       9 |                  59 |
|      10 |                 463 |

### e.5 Vehículos que entran en ventana por mes (2025-09 → 2026-12)

|         |   vehículos en ventana |   de clientes con >=2 el mismo mes |   [método original] solo último mantenimiento |
|:--------|-----------------------:|-----------------------------------:|----------------------------------------------:|
| 2025-09 |                   6373 |                                901 |                                          1134 |
| 2025-10 |                   6749 |                                959 |                                          1191 |
| 2025-11 |                   6468 |                                865 |                                          1143 |
| 2025-12 |                   6549 |                                899 |                                          1240 |
| 2026-01 |                   7538 |                                894 |                                          1474 |
| 2026-02 |                   6631 |                                794 |                                          1373 |
| 2026-03 |                   6342 |                                866 |                                          1338 |
| 2026-04 |                   6912 |                                905 |                                          1433 |
| 2026-05 |                   7071 |                                905 |                                          1567 |
| 2026-06 |                   6589 |                                908 |                                          1461 |
| 2026-07 |                   7648 |                                984 |                                          2021 |
| 2026-08 |                   7270 |                                915 |                                          2074 |
| 2026-09 |                   7331 |                               1049 |                                          2635 |
| 2026-10 |                   7851 |                               1072 |                                          3017 |
| 2026-11 |                   6820 |                                883 |                                          2940 |
| 2026-12 |                   7749 |                                971 |                                          3797 |

_Los meses > 2026-08 son ventanas ya definidas (mantenimientos de 2025-09 → 2026-08) cuyo retorno todavía no se puede observar: se listan como proyección de carga._

### f.1 Meses desde WarrantyStartDate al CUTOFF: vehículos vendidos sin ningún turno vs con turnos

| meses_desde_wsd   |   nunca en agenda |   con turnos | % nunca en agenda (fila)   |
|:------------------|------------------:|-------------:|:---------------------------|
| 0-3               |              4648 |          541 | 89.6%                      |
| 3-6               |              3321 |         1168 | 74.0%                      |
| 6-9               |              2696 |         2082 | 56.4%                      |
| 9-12              |              2180 |         4134 | 34.5%                      |
| 12-15             |              1042 |         5500 | 15.9%                      |
| 15-18             |               826 |         5390 | 13.3%                      |
| 18-24             |              1241 |        11186 | 10.0%                      |
| 24-36             |              1094 |        12148 | 8.3%                       |
| 36+               |                 5 |            2 | 71.4%                      |

_Sin turno: 17,173 vehículos (13,448 compradores); sin WarrantyStartDate: 120._

### f.2 Resumen de los vendidos sin turno

|                                                                          | valor   |
|:-------------------------------------------------------------------------|:--------|
| vehículos vendidos sin turno                                             | 17173   |
| % con < 12 meses desde WSD (todavía no les tocaba)                       | 74.8%   |
| con >= 12 meses (ventana vencida)                                        | 4208    |
| con >= 15 meses (ventana + tolerancia vencida = 'elegible y nunca vino') | 3166    |
| % con >= 15 meses                                                        | 18.4%   |
| % que representan sobre TODOS los vendidos con >= 15 meses               | 9.9%    |
| mediana de meses desde WSD                                               | 6.6     |

### f.3 Entre vendidos con >= 15 meses: % que nunca tuvo un turno, por segmento

|              |     n | % nunca vino   |
|:-------------|------:|:---------------|
| 25           |   451 | 30.4%          |
| 29           |     6 | 33.3%          |
| F            | 18331 | 8.8%           |
| J            | 13096 | 10.7%          |
| Ford Blue    | 22119 | 7.3%           |
| Ford Pro     |  9773 | 15.9%          |
| CONSORTIUM   |  3988 | 9.5%           |
| DIRECT SALES |  4319 | 17.0%          |
| HR           |   542 | 31.7%          |
| ROR          | 23043 | 8.2%           |
| 1            | 22689 | 7.9%           |
| 2            |  2701 | 8.1%           |
| 3-9          |  2278 | 13.3%          |
| 10-49        |  1435 | 20.8%          |
| 50+          |  2789 | 20.3%          |
| False        |  7707 | 10.4%          |
| True         | 24185 | 9.8%           |

### f.4 Vendidos con >= 15 meses: % con 1er mantenimiento programado completado dentro de los 15 meses desde WSD

|           |     n | % 1er service en 15 m   |
|:----------|------:|:------------------------|
| Ford Blue | 22119 | 80.2%                   |
| Ford Pro  |  9773 | 70.4%                   |
| 25        |   451 | 27.9%                   |
| 29        |     6 | 66.7%                   |
| F         | 18331 | 79.2%                   |
| J         | 13096 | 76.0%                   |
| 1         | 22689 | 80.4%                   |
| 2         |  2701 | 79.1%                   |
| 3-9       |  2278 | 73.2%                   |
| 10-49     |  1435 | 61.9%                   |
| 50+       |  2789 | 60.0%                   |

_Total: 77.2% sobre 31,892 vehículos._
