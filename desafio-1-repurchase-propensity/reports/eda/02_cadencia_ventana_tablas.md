# Tablas generadas por `scripts/eda/02_cadencia_ventana.py`

Generado automáticamente. CUTOFF = 2026-08-25. No editar a mano: el informe `02_cadencia_ventana.md` cita estos números.

### c1. Nulos de KM, VehicleCurrentKM y check-in por estado del turno (todos los turnos)

| StatusARG | turnos | KM_nulo_pct | VehicleCurrentKM_nulo_pct | Checkin_nulo_pct |
|---|---|---|---|---|
| (30) Agendado | 3.953 | 14,9 | 76,5 | 99,8 |
| (40) En progreso | 1.832 | 12,3 | 60,4 | 0,0 |
| (60) Concluido | 342.691 | 2,4 | 0,0 | 13,3 |
| (70) Cancelado | 101.222 | 4,1 | 100,0 | 100,0 |
| (80) No asistio | 27.237 | 12,3 | 71,9 | 94,3 |
| (90) Concluido sin OS | 15.507 | 2,8 | 2,8 | 18,9 |

### c2. KM es un atributo del vehículo (snapshot), VehicleCurrentKM es el odómetro del evento

| métrica | valor |
|---|---|
| vehículos en agenda | 111.752 |
| vehículos con KM constante (<=1 valor distinto) | 111.745 |
| % vehículos con KM constante | 99,99 |
| vehículos con >1 valor de KM | 7 |
| vehículos con >=2 turnos | 85.143 |
| vehículos con >=2 turnos y >1 valor de VehicleCurrentKM | 73.813 |
| vehículos con alguna lectura VehicleCurrentKM | 106.370 |
| % KM == VehicleCurrentKM de la última visita con lectura | 91,7 |
| % KM >= VehicleCurrentKM de la última visita con lectura | 92,2 |
| % KM == max(VehicleCurrentKM) del vehículo | 84,4 |

Lectura: `KM` no varía entre turnos del mismo vehículo y coincide con el `VehicleCurrentKM` de la última visita con lectura. Es el 'último km conocido' a la fecha de extracción, NO el km del turno.

### c3. Valores anómalos de km en mantenimientos completados

| métrica | valor |
|---|---|
| mantenimientos completados | 222.889 |
| VehicleCurrentKM nulo | 0 |
| VehicleCurrentKM < 100 (inválido) | 3.728 |
| VehicleCurrentKM == 1 | 2.582 |
| VehicleCurrentKM > 500.000 | 321 |
| VehicleCurrentKM > 1.000.000 (inválido) | 66 |
| KM (snapshot) nulo | 4.526 |
| KM == 0 | 4 |
| KM > 500.000 | 378 |
| event_date < 2024-01-01 (check-in anómalo) | 0 |
| event_date > CUTOFF | 0 |

### m0. Base M: mantenimientos completados usados en este EDA

| métrica | valor |
|---|---|
| turnos en agenda (schedule_id) | 492.442 |
| mantenimientos completados (is_completed_maintenance) | 222.889 |
|   con event_date fuera de [2024-01-01, CUTOFF] | 0 |
|   filas colapsadas por repetirse vehículo + event_date | 1.033 |
| eventos en M | 221.856 |
| vehículos en M | 87.531 |
|   de los cuales en sales | 36.950 |
| eventos con km_evento válido (100 <= VehicleCurrentKM <= 1.000.000) | 218.149 |
| eventos con WSD (agenda o sales) | 220.517 |

### c5. WarrantyStartDate: consistencia dentro de la agenda y contra sales (vehículos con mantenimiento completado)

| métrica | valor |
|---|---|
| vehículos con mantenimiento completado | 87.531 |
|   con WarrantyStartDate nulo en todos sus turnos | 464 |
|   con >1 WarrantyStartDate distinto en agenda | 0 |
| vehículos también en sales (con WSD en ambas) | 36.897 |
| % WSD agenda == WSD sales | 99,0 |
| % |WSD agenda − WSD sales| > 30 días | 0,06 |
| eventos de M con edad negativa (event_date < WSD) | 82 |
| eventos de M con WSD nulo | 1.339 |

### c4. Consistencia del odómetro entre mantenimientos consecutivos del mismo vehículo

| métrica | valor |
|---|---|
| pares consecutivos (mismo vehículo) | 133.837 |
| pares con km_evento en ambos | 130.382 |
| d_km < 0 (odómetro decrece) | 2.393 |
| % d_km < 0 | 1,8 |
| d_km == 0 (mismo km repetido) | 3.895 |
| % d_km == 0 | 3,0 |
| d_dias < 30 | 1.789 |
| % d_dias < 30 | 1,3 |
| d_dias < 30 y d_km <= 0 (misma visita partida) | 738 |
| d_km > 100.000 en un intervalo | 503 |

### d1. Cobertura de los dos métodos de tasa de uso

| métrica | valor |
|---|---|
| vehículos con tasa A (km_evento / años desde WSD, edad >= 3 meses) | 86.022 |
|   de los cuales fuera de [2.000, 150.000] km/año | 290 |
| vehículos con tasa B (pendiente 1ª→última visita, >= 90 días, km creciente) | 52.838 |

### d2. Distribución de la tasa de uso (km/año) por método

| index | n | p5 | p10 | p25 | p50 | p75 | p90 | p95 | media |
|---|---|---|---|---|---|---|---|---|---|
| A: km acumulado / edad | 85.495 | 7.590 | 9.924 | 14.616 | 21.514 | 31.307 | 43.765 | 52.732 | 24.746 |
| B: pendiente entre visitas | 52.548 | 8.591 | 11.218 | 16.681 | 24.689 | 35.827 | 49.337 | 59.016 | 28.149 |

### d3. Concordancia entre métodos de tasa de uso

| métrica | valor |
|---|---|
| vehículos con ambos métodos | 52.368 |
| correlación de Spearman A vs B | 0,895 |
| mediana de B/A | 1,001 |
| p25 de B/A | 0,913 |
| p75 de B/A | 1,119 |
| % con |B/A − 1| <= 0,25 | 78,5 |
| mediana |B − A| (km/año) | 2.330 |

### d4. Tasa de uso (método A, km/año) por generación y, para vehículos en sales, por BusinessUnit y PersonType

| index | n | p5 | p10 | p25 | p50 | p75 | p90 | p95 | media |
|---|---|---|---|---|---|---|---|---|---|
| gen Otro | 9 | 16.486 | 18.844 | 20.388 | 24.106 | 28.152 | 39.222 | 40.570 | 26.113 |
| gen P375 | 38.952 | 6.880 | 9.004 | 13.076 | 19.069 | 27.549 | 38.300 | 46.668 | 21.913 |
| gen P703 | 46.534 | 8.446 | 11.033 | 16.337 | 23.790 | 34.339 | 47.312 | 56.566 | 27.118 |
| BU Ford Blue | 25.826 | 8.457 | 11.024 | 16.221 | 23.390 | 33.214 | 45.064 | 53.886 | 26.385 |
| BU Ford Pro | 10.367 | 9.610 | 12.624 | 18.862 | 28.312 | 41.269 | 55.461 | 64.444 | 31.709 |
| PersonType F | 21.041 | 8.046 | 10.553 | 15.579 | 22.455 | 31.922 | 43.798 | 52.946 | 25.452 |
| PersonType J | 14.851 | 10.149 | 13.275 | 19.498 | 28.406 | 40.390 | 53.806 | 62.854 | 31.576 |
| PersonType otro/s.d. | 301 | 7.419 | 9.424 | 13.061 | 16.915 | 22.228 | 30.495 | 36.127 | 18.874 |

### a1. Días entre mantenimientos completados consecutivos (vehículos con >= 2)

| index | n | p5 | p10 | p25 | p50 | p75 | p90 | p95 | media |
|---|---|---|---|---|---|---|---|---|---|
| global | 133.837 | 56 | 72 | 106 | 161 | 245 | 352 | 393 | 188 |
| gen Otro | 200 | 51 | 62 | 86 | 126 | 202 | 335 | 403 | 161 |
| gen P375 | 77.106 | 54 | 69 | 100 | 153 | 234 | 350 | 405 | 183 |
| gen P703 | 56.531 | 61 | 80 | 117 | 174 | 258 | 355 | 382 | 196 |
| MY 2016-2019 | 10.621 | 77 | 98 | 139 | 203 | 304 | 407 | 489 | 234 |
| MY 2020-2022 | 37.036 | 57 | 71 | 102 | 151 | 226 | 337 | 395 | 180 |
| MY 2023 | 27.927 | 48 | 60 | 87 | 134 | 210 | 319 | 375 | 164 |
| MY 2024 | 41.892 | 67 | 87 | 126 | 189 | 282 | 364 | 397 | 211 |
| MY 2025-2026 | 14.627 | 48 | 66 | 98 | 140 | 196 | 254 | 293 | 151 |
| MY <=2015 | 1.522 | 59 | 89 | 141 | 223 | 338 | 438 | 510 | 247 |
| uso alto (>27.347) | 70.509 | 48 | 61 | 85 | 120 | 166 | 218 | 262 | 134 |
| uso bajo (<16.875) | 22.052 | 117 | 157 | 224 | 316 | 375 | 441 | 509 | 309 |
| uso medio | 40.038 | 90 | 112 | 149 | 203 | 271 | 343 | 385 | 218 |
| BU Ford Blue | 23.463 | 71 | 90 | 125 | 176 | 251 | 347 | 370 | 195 |
| BU Ford Pro | 12.571 | 42 | 59 | 89 | 130 | 193 | 273 | 334 | 150 |
| PersonType F | 17.288 | 74 | 93 | 128 | 183 | 260 | 353 | 374 | 201 |
| PersonType J | 18.564 | 47 | 64 | 96 | 140 | 203 | 285 | 346 | 158 |
| PersonType otro/s.d. | 182 | 90 | 112 | 162 | 220 | 314 | 364 | 394 | 237 |

Base: 133.837 pares consecutivos de 55.776 vehículos. Los grupos BU/PersonType usan solo vehículos presentes en sales (ventas 2024-2026, casi todos P703).

### a2. Km entre mantenimientos completados consecutivos (pares con odómetro válido y creciente)

| index | n | p5 | p10 | p25 | p50 | p75 | p90 | p95 | media |
|---|---|---|---|---|---|---|---|---|---|
| global | 124.094 | 7.490 | 8.783 | 10.099 | 13.141 | 16.839 | 20.547 | 28.893 | 15.486 |
| gen Otro | 179 | 8.162 | 8.902 | 10.094 | 12.831 | 18.120 | 28.337 | 37.125 | 19.366 |
| gen P375 | 70.898 | 7.143 | 8.333 | 9.561 | 10.563 | 12.917 | 20.242 | 27.788 | 13.961 |
| gen P703 | 53.017 | 8.682 | 11.522 | 14.679 | 16.201 | 17.998 | 20.846 | 30.131 | 17.512 |
| MY 2016-2019 | 9.685 | 6.632 | 8.166 | 9.609 | 10.840 | 14.155 | 21.551 | 30.168 | 14.931 |
| MY 2020-2022 | 34.096 | 7.231 | 8.357 | 9.555 | 10.544 | 12.760 | 20.248 | 28.307 | 13.872 |
| MY 2023 | 25.740 | 7.251 | 8.391 | 9.557 | 10.503 | 12.617 | 19.764 | 25.175 | 13.555 |
| MY 2024 | 39.123 | 8.663 | 11.356 | 14.581 | 16.216 | 18.158 | 21.484 | 31.448 | 17.684 |
| MY 2025-2026 | 13.883 | 8.740 | 12.112 | 14.930 | 16.166 | 17.632 | 19.867 | 22.338 | 17.029 |
| MY <=2015 | 1.377 | 5.210 | 7.544 | 9.542 | 11.040 | 14.719 | 22.314 | 32.509 | 16.942 |
| uso alto (>27.347) | 65.853 | 8.162 | 9.206 | 10.631 | 15.076 | 17.636 | 21.818 | 31.850 | 16.705 |
| uso bajo (<16.875) | 20.108 | 5.091 | 6.994 | 9.243 | 10.498 | 13.292 | 17.422 | 20.481 | 12.070 |
| uso medio | 37.344 | 7.931 | 8.926 | 10.001 | 12.152 | 16.408 | 19.909 | 25.557 | 14.581 |
| BU Ford Blue | 22.279 | 9.688 | 12.518 | 14.957 | 16.231 | 17.808 | 20.138 | 24.962 | 17.371 |
| BU Ford Pro | 11.768 | 7.270 | 10.340 | 14.292 | 16.058 | 17.817 | 20.608 | 27.445 | 17.085 |
| PersonType F | 16.474 | 9.451 | 12.235 | 14.882 | 16.181 | 17.678 | 19.901 | 23.408 | 17.265 |
| PersonType J | 17.399 | 8.187 | 11.288 | 14.632 | 16.166 | 17.964 | 20.726 | 28.653 | 17.285 |
| PersonType otro/s.d. | 174 | 9.038 | 11.759 | 14.848 | 15.992 | 17.424 | 19.990 | 23.689 | 16.660 |

Base: 124.094 pares (se excluyen 9.743 pares con km nulo, repetido o decreciente).

### a3. Cantidad de mantenimientos completados por vehículo en el extracto

| mantenimientos completados 2024-01→2026-08 | vehículos | % |
|---|---|---|
| 1 | 31.755 | 36,3 |
| 2 | 23.254 | 26,6 |
| 3 | 13.672 | 15,6 |
| 4 | 7.864 | 9,0 |
| 5 | 4.515 | 5,2 |
| 6 | 2.702 | 3,1 |
| 7 | 1.541 | 1,8 |
| 8 | 892 | 1,0 |
| 9 | 551 | 0,6 |
| 10 | 324 | 0,4 |
| 11 | 196 | 0,2 |
| 12 | 104 | 0,1 |

### a4. Días entre mantenimientos: pares ingenuos (a1) vs anclas con 18 meses de seguimiento garantizado (corrige la censura)

| grupo | pares ingenuos | mediana ingenua (d) | % > 365 d ingenuo | anclas con 18 m de seguimiento | % retorna en 18 m | mediana entre retornos en 18 m (d) | % > 365 d entre retornos en 18 m | mediana incondicional (sin retorno = censurado) |
|---|---|---|---|---|---|---|---|---|
| global | 133.837 | 161 | 7,9 | 86.894 | 80,5 | 165 | 9,5 | 202 |
| gen P703 | 56.531 | 174 | 7,4 | 21.993 | 89,3 | 195 | 11,5 | 213 |
| gen P375 | 77.106 | 153 | 8,2 | 64.491 | 77,8 | 154 | 8,7 | 196 |
| uso alto (>27.347) | 70.509 | 120 | 1,5 | 38.484 | 87,6 | 113 | 2,0 | 125 |
| uso bajo (<16.875) | 22.052 | 316 | 30,1 | 19.728 | 68,0 | 321 | 31,5 | 374 |
| uso medio | 40.038 | 203 | 6,8 | 26.993 | 81,8 | 197 | 7,4 | 223 |

La tabla a1 sólo ve intervalos que ya cerraron antes del CUTOFF (sesgo hacia intervalos cortos). Con seguimiento garantizado la mediana entre retornos sube poco, pero el 19 % que no vuelve en 18 meses no aparece en a1. 'Mediana incondicional' trata el no-retorno como un intervalo mayor a 548 d.

### b0. Distribución del número de service en los mantenimientos completados (base M)

| index | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| eventos | 48.927 | 35.919 | 25.412 | 18.779 | 15.318 | 14.264 | 10.326 | 9.108 | 8.259 | 6.954 | 5.321 | 4.676 | 3.785 | 3.059 | 2.470 | 1.956 | 1.467 | 1.294 | 1.068 | 3.494 |

El salto de 19 a 20 sugiere que 20 funciona como tope ('20 o más').

### b1. Km al evento y edad del vehículo por número de service (ServiceMaintenance) y generación

| gen | n° service | eventos | km p25 | km mediana | km p75 | km/n mediana | edad meses p25 | edad meses mediana | edad meses p75 | meses/n mediana |
|---|---|---|---|---|---|---|---|---|---|---|
| P375 | 1 | 4.440 | 9.863 | 11.250 | 16.910 | 11.250 | 9,4 | 12,2 | 19,0 | 12,2 |
| P375 | 2 | 7.680 | 19.522 | 20.602 | 23.697 | 10.301 | 13,2 | 18,9 | 24,6 | 9,4 |
| P375 | 3 | 10.453 | 29.593 | 30.656 | 33.636 | 10.219 | 16,9 | 24,3 | 33,9 | 8,1 |
| P375 | 4 | 10.859 | 39.760 | 40.735 | 43.155 | 10.184 | 19,9 | 28,1 | 38,4 | 7,0 |
| P375 | 5 | 11.209 | 49.860 | 50.913 | 53.340 | 10.183 | 22,9 | 31,5 | 42,8 | 6,3 |
| P375 | 6 | 11.964 | 59.996 | 61.300 | 65.902 | 10.217 | 26,8 | 36,5 | 51,9 | 6,1 |
| P375 | 7 | 9.183 | 70.024 | 71.100 | 73.588 | 10.157 | 28,3 | 38,0 | 51,2 | 5,4 |
| P375 | 8 | 8.326 | 80.022 | 81.149 | 83.678 | 10.144 | 30,1 | 40,3 | 54,9 | 5,0 |
| P375 | 9 | 7.904 | 89.981 | 91.237 | 94.144 | 10.137 | 31,6 | 42,2 | 57,9 | 4,7 |
| P375 | 10 | 6.764 | 100.000 | 101.309 | 104.658 | 10.131 | 33,8 | 45,3 | 63,1 | 4,5 |
| P375 | 11 | 5.222 | 110.115 | 111.510 | 115.000 | 10.137 | 35,2 | 47,0 | 66,2 | 4,3 |
| P375 | 12 | 4.586 | 120.004 | 121.500 | 124.902 | 10.125 | 36,4 | 49,1 | 69,7 | 4,1 |
| P703 | 1 | 44.143 | 14.676 | 16.040 | 16.939 | 16.040 | 5,7 | 8,4 | 11,6 | 8,4 |
| P703 | 2 | 28.140 | 30.144 | 32.158 | 33.543 | 16.079 | 10,3 | 14,5 | 20,2 | 7,3 |
| P703 | 3 | 14.895 | 46.481 | 48.451 | 50.260 | 16.150 | 12,9 | 17,7 | 23,3 | 5,9 |
| P703 | 4 | 7.881 | 62.485 | 64.693 | 67.269 | 16.173 | 15,0 | 19,8 | 25,0 | 4,9 |
| P703 | 5 | 4.075 | 78.089 | 80.746 | 83.783 | 16.149 | 16,7 | 21,4 | 26,5 | 4,3 |
| P703 | 6 | 2.257 | 92.011 | 96.527 | 100.022 | 16.088 | 17,6 | 22,5 | 27,1 | 3,7 |
| P703 | 7 | 1.121 | 107.096 | 112.868 | 116.708 | 16.124 | 19,7 | 23,9 | 28,7 | 3,4 |
| P703 | 8 | 763 | 84.824 | 126.570 | 131.017 | 15.821 | 19,7 | 24,0 | 28,6 | 3,0 |
| P703 | 9 | 336 | 112.385 | 143.646 | 147.967 | 15.961 | 21,3 | 25,5 | 29,5 | 2,8 |
| P703 | 10 | 169 | 105.490 | 152.895 | 162.464 | 15.290 | 20,5 | 25,0 | 29,1 | 2,5 |
| P703 | 11 | 93 | 110.845 | 126.283 | 177.138 | 11.480 | 20,3 | 24,5 | 30,1 | 2,2 |
| P703 | 12 | 79 | 76.050 | 127.835 | 192.066 | 10.653 | 15,2 | 24,6 | 28,6 | 2,1 |

`km/n` = km al evento dividido el número de service: si el plan fuera cada K km, converge a K. `meses/n` converge a 12 sólo si la regla de tiempo fuera la que manda. OJO: para P703 la edad está truncada por construcción (el p1 de WSD es 2023-07-26, ningún P703 supera ~37 meses), así que a n alto sólo llegan los de uso extremo (n = 10: tasa mediana 66.170 km/año); `meses/n` para n >= 5 en P703 no es evidencia de nada. La evidencia limpia contra 12·n es n = 1 (8,4 meses) y Δdías n→n+1 (b2).

### b2. Incremento de km y de días entre services con numeración consecutiva (n → n+1)

| index | n | p5 | p10 | p25 | p50 | p75 | p90 | p95 | media |
|---|---|---|---|---|---|---|---|---|---|
| P375 Δkm (n→n+1) | 51.593 | 7.247 | 8.301 | 9.460 | 10.330 | 11.724 | 15.401 | 20.266 | 12.530 |
| P375 Δdías (n→n+1) | 51.593 | 57 | 71 | 101 | 151 | 225 | 332 | 382 | 177 |
| P703 Δkm (n→n+1) | 46.043 | 9.409 | 11.922 | 14.726 | 16.138 | 17.639 | 19.743 | 21.641 | 16.840 |
| P703 Δdías (n→n+1) | 46.043 | 70 | 87 | 121 | 177 | 258 | 352 | 375 | 197 |

Base: 97.636 pares con numeración consecutiva (78.7% de los pares con km válido).

### b3. Km al 1° service en la flota nueva (ModelYear >= 2024, n=42.987)

| km al 1° service (MY >= 2024) | % de 1° services |
|---|---|
| (0.0, 5000.0] | 2,1 |
| (5000.0, 8000.0] | 2,8 |
| (8000.0, 10000.0] | 3,6 |
| (10000.0, 12000.0] | 5,6 |
| (12000.0, 15000.0] | 13,8 |
| (15000.0, 18000.0] | 59,0 |
| (18000.0, 20000.0] | 7,8 |
| (20000.0, 30000.0] | 3,2 |
| (30000.0, inf] | 2,2 |

### b4. Salto de numeración entre mantenimientos consecutivos observados (distribución completa)

| maint_number − maint_number previo | pares | % |
|---|---|---|
| -3 | 680 | 0,5 |
| -2 | 982 | 0,7 |
| -1 | 1.712 | 1,3 |
| 0 | 6.836 | 5,1 |
| 1 | 103.982 | 77,7 |
| 2 | 9.877 | 7,4 |
| 3 | 2.650 | 2,0 |
| 4 | 1.296 | 1,0 |
| 5 | 720 | 0,5 |
| < -3 | 2.841 | 2,1 |
| > 5 | 2.261 | 1,7 |
| negativo (total) | 6.215 | 4,6 |
| >= +2 (total) | 16.804 | 12,6 |

Un salto de +2 o más PUEDE significar que el service intermedio no está en el extracto (hecho fuera de la red, antes de 2024-01 o no registrado); 0 o negativo indica numeración inconsistente. Ver b5: sólo la mitad de los saltos +2 tiene un Δkm compatible con un intervalo doble.

### b5. Δkm según el salto de numeración, y 'intervalo doble' medido por km (Δkm >= 1,5·K_gen)

| gen | salto | pares | Δkm p25 | Δkm mediana | Δkm p75 | Δkm mediana / K | Δdías mediana | % Δkm en [1,5K, 2,5K] | % Δkm >= 1,5K (doble por km) | % salto >= +2 | % doble por km entre salto +1 | % doble por km entre salto >= +2 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P703 | 0 | 1.892 | 7.630 | 14.352 | 16.916 | 0,96 | 127 | 4,8 |  |  |  |  |
| P703 | 1 | 46.043 | 14.726 | 16.138 | 17.639 | 1,08 | 177 | 3,3 |  |  |  |  |
| P703 | 2 | 2.875 | 16.799 | 24.808 | 32.550 | 1,65 | 211 | 46,1 |  |  |  |  |
| P703 | 3 | 563 | 15.987 | 20.797 | 44.305 | 1,39 | 186 | 13,7 |  |  |  |  |
| P703 | 4 | 299 | 15.047 | 17.206 | 26.606 | 1,15 | 137 | 9,0 |  |  |  |  |
| P703 | todos | 53.017 |  | 16.201 |  | 1,08 | 175 |  | 7,9 | 7,6 | 4,2 | 49,4 |
| P375 | 0 | 3.759 | 9.199 | 10.596 | 13.335 | 1,06 | 123 | 13,3 |  |  |  |  |
| P375 | 1 | 51.593 | 9.460 | 10.330 | 11.724 | 1,03 | 151 | 7,7 |  |  |  |  |
| P375 | 2 | 6.267 | 11.182 | 16.227 | 20.339 | 1,62 | 193 | 46,4 |  |  |  |  |
| P375 | 3 | 1.853 | 10.847 | 19.284 | 28.694 | 1,93 | 215 | 24,1 |  |  |  |  |
| P375 | 4 | 885 | 10.420 | 16.109 | 32.944 | 1,61 | 202 | 17,2 |  |  |  |  |
| P375 | todos | 70.898 |  | 10.563 |  | 1,06 | 154 |  | 18,5 | 16,0 | 10,7 | 51,3 |

Si el salto +2 fuera siempre un service hecho afuera, Δkm mediana / K sería ≈ 2; es ≈ 1,6 y sólo ~46 % cae en [1,5K, 2,5K]: la mitad de los saltos es ruido de numeración. Medido por km, el intervalo doble es el 7,9 % de los pares P703 y el 18,5 % de P375.

### e1. Cohorte WarrantyStartDate 2024 (n=21.290 vehículos en sales): % que completó el 1° mantenimiento en la red dentro de h meses

| horizonte (meses) | vehículos con seguimiento >= h | % con 1° mantenimiento dentro de h |
|---|---|---|
| 6 | 21.290 | 20,5 |
| 9 | 21.290 | 41,9 |
| 12 | 21.290 | 64,5 |
| 15 | 21.290 | 77,1 |
| 18 | 21.290 | 80,9 |

18.317 de 21.290 (86.0%) tienen al menos un mantenimiento completado hasta el CUTOFF; seguimiento mínimo de la cohorte: 19.8 meses. El 1° evento observado está numerado como 1° service en el 88.5% de los casos con evento (9.0% como 2°, 2.5% como 3° o más); 7 vehículos tienen el 1° mantenimiento antes del WarrantyStartDate.

### e2. Misma cohorte: del 1° al 2° mantenimiento completado

| horizonte (meses) | vehículos con seguimiento >= h desde el 1° | % con 2° mantenimiento dentro de h |
|---|---|---|
| 6 | 17.390 | 26,3 |
| 9 | 16.277 | 50,1 |
| 12 | 14.085 | 75,4 |
| 15 | 10.560 | 87,5 |
| 18 | 6.364 | 91,5 |

SESGO DE SELECCIÓN: sólo tienen h meses de seguimiento tras el 1° los que hicieron el 1° temprano. El subconjunto con >= 18 m tiene t1 mediana 5.8 meses vs 9.2 en todos los que hicieron el 1°; ver e4. La comparación limpia WSD→1° vs 1°→2° es a 12 meses (mismo horizonte, denominador casi completo).

### e4. Cohorte 2024: retorno al 2° mantenimiento (12 m) según cuánto tardó el 1°

| meses WSD → 1° (bucket) | n (seguimiento >= 12 m tras el 1°) | % con 2° dentro de 12 m | % que además tiene seguimiento >= 18 m |
|---|---|---|---|
| <= 4 | 1.547 | 91,5 | 86,9 |
| 4-6 | 2.820 | 90,3 | 70,7 |
| 6-8 | 3.078 | 82,5 | 49,3 |
| 8-10 | 2.473 | 75,8 | 34,3 |
| 10-12 | 2.562 | 58,1 | 20,7 |
| 12-15 | 1.425 | 46,8 | 8,8 |
| > 15 | 176 | 49,4 | 0,0 |

El retraso del 1° service predice fuerte el retorno al 2° (91 % si el 1° fue a <= 4 meses, 47 % si fue a 12-15). Es una feature ('retraso del service anterior'), y explica por qué el 91,5 % a 18 m de e2 está inflado.

### e3. Cohorte 2024: percentiles del tiempo (meses) WSD→1° y 1°→2°, y km al 1° service

| index | n | p5 | p10 | p25 | p50 | p75 | p90 | p95 | media |
|---|---|---|---|---|---|---|---|---|---|
| meses WSD → 1° | 18.310 | 3,4 | 4,2 | 6,1 | 9,2 | 12,0 | 15,2 | 18,8 | 9,6 |
| meses 1° → 2° (seguimiento >= 18 m) | 5.864 | 2,4 | 3,0 | 4,2 | 6,1 | 8,9 | 11,8 | 13,1 | 6,8 |
| km al 1° mantenimiento | 18.208 | 8.050,4 | 10.652,8 | 14.853,8 | 16.172,0 | 17.607,2 | 30.438,9 | 33.566,5 | 18.275,9 |

### f1. Retraso real (días) del siguiente mantenimiento respecto del due_date, por regla (ventanas ancladas en mantenimientos completados con 18 meses de seguimiento, n=86.484; retornos dentro de 18 m)

| regla | ventanas | % retorna en 18 m | % ventanas donde manda el tope de 365 d | due mediana (días desde ancla) | p5 | p10 | p25 | p50 | p75 | p90 | p95 | % retornos antes de due-30 | % retornos antes de due-60 | % retornos antes de due-90 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sólo tiempo (365 d) | 86.484 | 80,8 | 100,0 | 365 | -309 | -294 | -259 | -200 | -107 | -1 | 41 | 85,9 | 82,3 | 78,0 |
| K = 10.000 | 86.484 | 80,8 | 7,1 | 149 | -114 | -71 | -20 | 20 | 78 | 155 | 211 | 20,3 | 12,0 | 7,3 |
| K = 15.000 | 86.484 | 80,8 | 18,9 | 223 | -193 | -152 | -87 | -33 | 20 | 89 | 144 | 51,6 | 36,0 | 24,1 |
| K por generación (15k P703 / 10k P375) | 86.484 | 80,8 | 8,8 | 165 | -132 | -85 | -28 | 7 | 54 | 129 | 187 | 24,3 | 14,5 | 9,3 |
| K por generación, tasa reciente | 86.484 | 80,8 | 8,9 | 162 | -130 | -80 | -24 | 10 | 57 | 132 | 189 | 22,4 | 13,5 | 8,7 |

due_date = ancla + min(365 d, K / tasa_i × 365,25); tasa_i = km al evento / edad del vehículo en el ancla (sin información posterior al ancla); fallback a la mediana de la generación en el 4.1% de las ventanas. La variante 'tasa reciente' usa la pendiente del último intervalo (disponible en el 37.4% de las ventanas; si no, la acumulada). Retraso negativo = volvió antes del due.

### f2. Sensibilidad al horizonte H: % de retornos capturados y prevalencia de churn resultante, por regla

| regla | horizonte H (días tras due) | % retornos (18 m) capturados hasta due+H | % churn incondicional (no volvió hasta due+H) | % churn entre ventanas abiertas en due-30 | ventanas abiertas |
|---|---|---|---|---|---|
| sólo tiempo (365 d) | 0 | 90,5 | 26,9 | 87,7 | 26.524 |
| sólo tiempo (365 d) | 30 | 94,2 | 23,9 | 78,0 | 26.524 |
| sólo tiempo (365 d) | 60 | 96,2 | 22,3 | 72,7 | 26.524 |
| sólo tiempo (365 d) | 90 | 97,6 | 21,2 | 69,2 | 26.524 |
| sólo tiempo (365 d) | 120 | 98,6 | 20,4 | 66,4 | 26.524 |
| sólo tiempo (365 d) | 150 | 99,4 | 19,8 | 64,5 | 26.524 |
| sólo tiempo (365 d) | 180 | 99,9 | 19,3 | 62,9 | 26.524 |
| K = 10.000 | 0 | 37,3 | 69,9 | 83,6 | 72.297 |
| K = 10.000 | 30 | 55,8 | 55,0 | 65,8 | 72.297 |
| K = 10.000 | 60 | 69,0 | 44,3 | 53,0 | 72.297 |
| K = 10.000 | 90 | 78,4 | 36,7 | 43,9 | 72.297 |
| K = 10.000 | 120 | 84,8 | 31,5 | 37,7 | 72.297 |
| K = 10.000 | 150 | 89,4 | 27,8 | 33,2 | 72.297 |
| K = 10.000 | 180 | 92,6 | 25,2 | 30,1 | 72.297 |
| K = 15.000 | 0 | 66,7 | 46,1 | 79,1 | 50.470 |
| K = 15.000 | 30 | 78,3 | 36,8 | 63,0 | 50.470 |
| K = 15.000 | 60 | 85,7 | 30,8 | 52,8 | 50.470 |
| K = 15.000 | 90 | 90,2 | 27,2 | 46,6 | 50.470 |
| K = 15.000 | 120 | 93,3 | 24,7 | 42,3 | 50.470 |
| K = 15.000 | 150 | 95,4 | 23,0 | 39,4 | 50.470 |
| K = 15.000 | 180 | 96,9 | 21,7 | 37,2 | 50.470 |
| K por generación (15k P703 / 10k P375) | 0 | 44,4 | 64,2 | 79,8 | 69.548 |
| K por generación (15k P703 / 10k P375) | 30 | 65,1 | 47,4 | 59,0 | 69.548 |
| K por generación (15k P703 / 10k P375) | 60 | 77,1 | 37,7 | 46,9 | 69.548 |
| K por generación (15k P703 / 10k P375) | 90 | 84,3 | 31,9 | 39,7 | 69.548 |
| K por generación (15k P703 / 10k P375) | 120 | 88,9 | 28,2 | 35,1 | 69.548 |
| K por generación (15k P703 / 10k P375) | 150 | 92,2 | 25,6 | 31,8 | 69.548 |
| K por generación (15k P703 / 10k P375) | 180 | 94,5 | 23,7 | 29,5 | 69.548 |
| K por generación, tasa reciente | 0 | 41,6 | 66,4 | 81,1 | 70.831 |
| K por generación, tasa reciente | 30 | 63,1 | 49,0 | 59,9 | 70.831 |
| K por generación, tasa reciente | 60 | 75,8 | 38,8 | 47,3 | 70.831 |
| K por generación, tasa reciente | 90 | 83,6 | 32,5 | 39,7 | 70.831 |
| K por generación, tasa reciente | 120 | 88,5 | 28,5 | 34,8 | 70.831 |
| K por generación, tasa reciente | 150 | 91,9 | 25,8 | 31,5 | 70.831 |
| K por generación, tasa reciente | 180 | 94,4 | 23,8 | 29,0 | 70.831 |

### f3. Regla 'K por generación': retraso y sensibilidad por generación

| gen | ventanas | % retorna en 18 m | % manda tope 365 d | due mediana (días) | p5 | p10 | p25 | p50 | p75 | p90 | p95 | % capturado H=60 | % churn abiertas H=60 | % capturado H=90 | % churn abiertas H=90 | % capturado H=120 | % churn abiertas H=120 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P375 | 64.491 | 77,8 | 8,0 | 158 | -128 | -83 | -30 | 5 | 51 | 129 | 188 | 77,6 | 49,1 | 84,5 | 42,4 | 89,0 | 38,2 |
| P703 | 21.993 | 89,3 | 11,3 | 187 | -138 | -90 | -25 | 13 | 58 | 129 | 185 | 75,8 | 40,5 | 83,7 | 31,6 | 88,9 | 25,9 |

### f4a. Tasa de uso mediana (km/año) por segmento BusinessUnit × PersonType usada para el arranque en frío

| BusinessUnit | PersonType | km/año |
|---|---|---|
| Ford Blue | F | 22.330 |
| Ford Blue | J | 26.103 |
| Ford Blue | otro/s.d. | 16.851 |
| Ford Pro | F | 23.103 |
| Ford Pro | J | 32.347 |
| Ford Pro | otro/s.d. | 20.200 |

### f4. Primer service (arranque en frío): cohorte ventas 2024 anclada en WarrantyStartDate

| regla (1° service, ancla WSD) | due (días desde WSD, mediana) | ventanas | % retorna en 18 m | p5 | p10 | p25 | p50 | p75 | p90 | p95 | % capturado H=60 | % churn abiertas H=60 | % capturado H=90 | % churn abiertas H=90 | % capturado H=120 | % churn abiertas H=120 | % capturado H=180 | % churn abiertas H=180 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| sólo tiempo (365 d) | 365 | 21.283 | 80,9 | -264 | -239 | -183 | -99 | -8 | 37 | 87 | 92,7 | 53,8 | 95,2 | 49,4 | 97,0 | 46,4 | 99,9 | 41,3 |
| K = 15.000 con tasa poblacional P703 | 230 | 21.283 | 80,9 | -129 | -104 | -48 | 36 | 127 | 172 | 222 | 55,8 | 73,0 | 62,9 | 65,3 | 71,8 | 55,8 | 91,0 | 35,1 |
| K = 10.000 con tasa poblacional P703 | 154 | 21.283 | 80,9 | -53 | -28 | 28 | 112 | 203 | 248 | 298 | 34,8 | 77,8 | 43,3 | 70,3 | 51,7 | 62,9 | 66,0 | 50,5 |
| K = 15.000 con tasa por segmento BU × PersonType | 237 | 21.283 | 80,9 | -121 | -94 | -39 | 45 | 123 | 185 | 236 | 54,2 | 72,3 | 62,1 | 64,2 | 74,1 | 51,6 | 89,2 | 35,8 |

Sin km previo no hay tasa individual: el due se calcula con la tasa mediana poblacional de P703 o, en la última fila, con la mediana del segmento BusinessUnit × PersonType del vehículo (tabla f4a).

### f5. Regla 'K por generación': retraso por tercil de tasa de uso

| tercil de uso | ventanas | % retorna en 18 m | p5 | p10 | p25 | p50 | p75 | p90 | p95 |
|---|---|---|---|---|---|---|---|---|---|
| alto (>27.347) | 38.475 | 87,6 | -111 | -63 | -22 | 5 | 38 | 96 | 155 |
| bajo (<16.875) | 19.727 | 68,0 | -167 | -118 | -43 | 10 | 76 | 153 | 198 |
| medio | 26.987 | 81,8 | -133 | -89 | -36 | 12 | 69 | 151 | 209 |

### f6. Grilla apertura × horizonte: cobertura de retornos y prevalencia de churn entre ventanas abiertas

| regla | apertura (días vs due) | horizonte H | largo ventana (días) | % ventanas abiertas | % retornos (18 m) dentro de [apertura, due+H] | % retornos antes de la apertura | % churn entre abiertas (no vuelve hasta due+H) |
|---|---|---|---|---|---|---|---|
| K por generación (15k P703 / 10k P375) | -90 | 60 | 150 | 92,5 | 67,8 | 9,3 | 40,8 |
| K por generación (15k P703 / 10k P375) | -90 | 90 | 180 | 92,5 | 75,0 | 9,3 | 34,5 |
| K por generación (15k P703 / 10k P375) | -90 | 120 | 210 | 92,5 | 79,7 | 9,3 | 30,5 |
| K por generación (15k P703 / 10k P375) | -60 | 60 | 120 | 88,3 | 62,6 | 14,5 | 42,7 |
| K por generación (15k P703 / 10k P375) | -60 | 90 | 150 | 88,3 | 69,8 | 14,5 | 36,2 |
| K por generación (15k P703 / 10k P375) | -60 | 120 | 180 | 88,3 | 74,4 | 14,5 | 31,9 |
| K por generación (15k P703 / 10k P375) | -30 | 60 | 90 | 80,4 | 52,9 | 24,3 | 46,9 |
| K por generación (15k P703 / 10k P375) | -30 | 90 | 120 | 80,4 | 60,0 | 24,3 | 39,7 |
| K por generación (15k P703 / 10k P375) | -30 | 120 | 150 | 80,4 | 64,7 | 24,3 | 35,1 |
| K por generación (15k P703 / 10k P375) | 0 | 60 | 60 | 64,3 | 32,9 | 44,2 | 58,7 |
| K por generación (15k P703 / 10k P375) | 0 | 90 | 90 | 64,3 | 40,1 | 44,2 | 49,7 |
| K por generación (15k P703 / 10k P375) | 0 | 120 | 120 | 64,3 | 44,7 | 44,2 | 43,9 |
| K por generación, tasa reciente | -90 | 60 | 150 | 93,0 | 67,1 | 8,7 | 41,7 |
| K por generación, tasa reciente | -90 | 90 | 180 | 93,0 | 74,9 | 8,7 | 35,0 |
| K por generación, tasa reciente | -90 | 120 | 210 | 93,0 | 79,8 | 8,7 | 30,7 |
| K por generación, tasa reciente | -60 | 60 | 120 | 89,1 | 62,4 | 13,5 | 43,5 |
| K por generación, tasa reciente | -60 | 90 | 150 | 89,1 | 70,1 | 13,5 | 36,5 |
| K por generación, tasa reciente | -60 | 120 | 180 | 89,1 | 75,1 | 13,5 | 32,0 |
| K por generación, tasa reciente | -30 | 60 | 90 | 81,9 | 53,4 | 22,4 | 47,3 |
| K por generación, tasa reciente | -30 | 90 | 120 | 81,9 | 61,2 | 22,4 | 39,7 |
| K por generación, tasa reciente | -30 | 120 | 150 | 81,9 | 66,1 | 22,4 | 34,8 |
| K por generación, tasa reciente | 0 | 60 | 60 | 66,5 | 34,4 | 41,5 | 58,3 |
| K por generación, tasa reciente | 0 | 90 | 90 | 66,5 | 42,1 | 41,5 | 48,9 |
| K por generación, tasa reciente | 0 | 120 | 120 | 66,5 | 47,1 | 41,5 | 42,9 |

Una ventana está 'abierta' si el vehículo no volvió antes de la apertura (o no volvió nunca en 18 m). 'Churn entre abiertas' es la prevalencia del target que vería el modelo al abrir la ventana.

### f7. Tasa reciente vs acumulada comparadas sólo en las ventanas donde la reciente existe (comparación no diluida)

| tasa | ventanas (sólo con tasa reciente) | p10 | p50 | p90 | mediana |retraso| (d) | % |retraso| <= 30 d | % |retraso| <= 60 d | % ventanas abiertas en due-30 | % retornos antes de due-30 | % capturado hasta due+90 | % churn abiertas H=90 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| acumulada (km al ancla / edad) | 32.323 | -55 | 6 | 107 | 30 | 49,5 | 72,2 | 83,6 | 19,2 | 87,5 | 30,0 |
| reciente (pendiente del último intervalo) | 32.323 | -43 | 13 | 117 | 31 | 49,1 | 71,5 | 87,6 | 14,5 | 85,8 | 30,4 |

Este subconjunto (vehículos con >= 2 visitas con km) está sesgado hacia los de más uso; por eso el retraso es más angosto que en f1. La conclusión es la misma: la tasa reciente no centra ni angosta mejor que la acumulada.

### f8. Prevalencia de churn entre abiertas (apertura due-30, H=90) reponderada a la mezcla de generaciones de 2026

| métrica | valor |
|---|---|
| % P703 entre las ventanas evaluadas (anclas 2024-01→2025-02) | 25,4 |
| % P703 entre los mantenimientos de 2026-01→08 | 69,6 |
| prevalencia observada (mezcla de las ventanas evaluadas) | 39,7 |
| prevalencia P703 | 31,6 |
| prevalencia P375 | 42,4 |
| prevalencia reponderada a la mezcla de 2026 | 34,8 |

### g1. Volumen mensual de mantenimientos completados (2024-01 → 2026-08; agosto 2026 hasta el 25)

| mes | mantenimientos | P703 | P375 | dias_habiles | por_dia_habil |
|---|---|---|---|---|---|
| 2024-01 | 6.331 | 437 | 5.856 | 23 | 275,3 |
| 2024-02 | 5.522 | 528 | 4.958 | 21 | 263,0 |
| 2024-03 | 5.693 | 728 | 4.935 | 21 | 271,1 |
| 2024-04 | 5.744 | 854 | 4.860 | 22 | 261,1 |
| 2024-05 | 5.932 | 1.043 | 4.854 | 23 | 257,9 |
| 2024-06 | 4.845 | 1.043 | 3.775 | 20 | 242,2 |
| 2024-07 | 6.368 | 1.468 | 4.869 | 23 | 276,9 |
| 2024-08 | 6.648 | 1.806 | 4.811 | 22 | 302,2 |
| 2024-09 | 6.562 | 2.091 | 4.449 | 21 | 312,5 |
| 2024-10 | 6.953 | 2.271 | 4.662 | 23 | 302,3 |
| 2024-11 | 6.620 | 2.219 | 4.374 | 21 | 315,2 |
| 2024-12 | 6.697 | 2.437 | 4.234 | 22 | 304,4 |
| 2025-01 | 7.705 | 2.948 | 4.717 | 23 | 335,0 |
| 2025-02 | 6.805 | 2.778 | 4.006 | 20 | 340,2 |
| 2025-03 | 6.495 | 2.864 | 3.595 | 21 | 309,3 |
| 2025-04 | 7.060 | 3.285 | 3.746 | 22 | 320,9 |
| 2025-05 | 7.225 | 3.489 | 3.701 | 22 | 328,4 |
| 2025-06 | 6.707 | 3.442 | 3.230 | 21 | 319,4 |
| 2025-07 | 7.806 | 4.145 | 3.633 | 23 | 339,4 |
| 2025-08 | 7.429 | 4.162 | 3.251 | 21 | 353,8 |
| 2025-09 | 7.475 | 4.249 | 3.211 | 22 | 339,8 |
| 2025-10 | 8.034 | 4.755 | 3.267 | 23 | 349,3 |
| 2025-11 | 7.012 | 4.260 | 2.738 | 20 | 350,6 |
| 2025-12 | 7.937 | 5.007 | 2.918 | 23 | 345,1 |
| 2026-01 | 8.936 | 5.728 | 3.183 | 22 | 406,2 |
| 2026-02 | 6.936 | 4.536 | 2.386 | 20 | 346,8 |
| 2026-03 | 8.453 | 5.787 | 2.649 | 22 | 384,2 |
| 2026-04 | 7.939 | 5.562 | 2.367 | 22 | 360,9 |
| 2026-05 | 7.393 | 5.218 | 2.165 | 21 | 352,0 |
| 2026-06 | 7.438 | 5.346 | 2.072 | 22 | 338,1 |
| 2026-07 | 7.647 | 5.625 | 2.009 | 23 | 332,5 |
| 2026-08 | 5.509 | 4.123 | 1.372 | 17 | 324,1 |

### g2. Índice estacional por mes del año: crudo (2024 y 2025) y con la tendencia removida (2024-01→2026-07)

| mes del año | 2024 | 2025 | índice 2024 (media=100) | índice 2025 (media=100) | índice medio | índice medio por día hábil | índice sin tendencia (regresión, por día hábil, 2024-01→2026-07) | residuo % 2024 | residuo % 2025 | residuo % 2026 |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 6.331 | 7.705 | 102,8 | 105,4 | 104,1 | 98,7 | 108,8 | -4,5 | 0,1 | 4,4 |
| 2 | 5.522 | 6.805 | 89,6 | 93,1 | 91,4 | 97,3 | 100,9 | -2,8 | 8,0 | -5,1 |
| 3 | 5.693 | 6.495 | 92,4 | 88,9 | 90,7 | 94,1 | 100,9 | -1,0 | -2,8 | 3,9 |
| 4 | 5.744 | 7.060 | 93,3 | 96,6 | 94,9 | 94,1 | 97,5 | -2,7 | 3,0 | -0,3 |
| 5 | 5.932 | 7.225 | 96,3 | 98,9 | 97,6 | 94,6 | 95,9 | -3,4 | 5,7 | -2,3 |
| 6 | 4.845 | 6.707 | 78,7 | 91,8 | 85,2 | 90,5 | 90,6 | -5,3 | 7,3 | -2,0 |
| 7 | 6.368 | 7.806 | 103,4 | 106,8 | 105,1 | 99,6 | 95,0 | 2,1 | 7,5 | -9,6 |
| 8 | 6.648 | 7.429 | 107,9 | 101,7 | 104,8 | 106,2 | 105,0 | -0,4 | 0,4 |  |
| 9 | 6.562 | 7.475 | 106,5 | 102,3 | 104,4 | 106,0 | 103,3 | 3,3 | -3,3 |  |
| 10 | 6.953 | 8.034 | 112,9 | 109,9 | 111,4 | 105,6 | 101,7 | 0,3 | -0,3 |  |
| 11 | 6.620 | 7.012 | 107,5 | 96,0 | 101,7 | 108,1 | 102,8 | 2,2 | -2,2 |  |
| 12 | 6.697 | 7.937 | 108,7 | 108,6 | 108,7 | 105,3 | 99,0 | 1,2 | -1,2 |  |

Tendencia estimada: 1.26 % mensual por día hábil (≈ 16 % anual). El índice crudo mezcla tendencia y estacionalidad; el de regresión es el que hay que leer. Los residuos por año dicen si el efecto de un mes es sistemático (mismo signo todos los años) o de un solo año.

### r1. Resumen de parámetros empíricos

| métrica | valor |
|---|---|
| K P703 (km entre services, mediana Δkm n→n+1) | 16.138 |
| K P375 (km entre services, mediana Δkm n→n+1) | 10.330 |
| días entre services mediana P703 | 174 |
| días entre services mediana P375 | 153 |
| % pares con > 365 días entre services (ingenuo, censurado) | 7,9 |
| % > 365 días entre retornos en 18 m (anclas con seguimiento garantizado) | 9,5 |
| % anclas sin retorno en 18 m | 19,5 |
| mediana días entre services, incondicional (anclas con seguimiento) | 202 |
| tasa de uso mediana (km/año, método A) | 21.514 |
| tasa de uso mediana P703 | 23.790 |
| tasa de uso mediana P375 | 19.069 |
| regla K por generación: retraso p10 (días) | -85 |
| regla K por generación: retraso p50 (días) | 7 |
| regla K por generación: retraso p90 (días) | 129 |
| regla sólo tiempo: retraso p50 (días) | -200 |
