# Tablas de la verificación independiente del EDA 02

Generado por `scripts/eda/02_cadencia_ventana_verificacion.py`. CUTOFF = 2026-08-25.

### V0. Sanidad: unicidad de claves usadas en joins

| métrica | valor |
|---|---|
| sales: filas | 59.384 |
| sales: vehicle_id únicos | 59.384 |
| appointments: filas | 492.442 |
| appointments: schedule_id únicos | 492.442 |

### V0b. Base M reconstruida

| métrica | valor |
|---|---|
| mantenimientos completados en rango | 222.889 |
| eventos M (dedupe vehículo-día) | 221.856 |
| vehículos | 87.531 |
| eventos con km válido | 218.149 |

### V1a. km/n y meses/n por generación y n° de service (recalculado)

| gen | n | eventos | km mediana | km/n | edad meses mediana | meses/n |
|---|---|---|---|---|---|---|
| P375 | 1 | 4.440 | 11.250 | 11.250 | 12,2 | 12,2 |
| P375 | 2 | 7.680 | 20.602 | 10.301 | 18,9 | 9,4 |
| P375 | 3 | 10.453 | 30.656 | 10.219 | 24,3 | 8,1 |
| P375 | 4 | 10.859 | 40.735 | 10.184 | 28,1 | 7,0 |
| P375 | 5 | 11.209 | 50.913 | 10.183 | 31,5 | 6,3 |
| P375 | 6 | 11.964 | 61.300 | 10.217 | 36,5 | 6,1 |
| P375 | 7 | 9.183 | 71.100 | 10.157 | 38,0 | 5,4 |
| P375 | 8 | 8.326 | 81.149 | 10.144 | 40,3 | 5,0 |
| P375 | 9 | 7.904 | 91.237 | 10.137 | 42,2 | 4,7 |
| P375 | 10 | 6.764 | 101.309 | 10.131 | 45,3 | 4,5 |
| P375 | 11 | 5.222 | 111.510 | 10.137 | 47,0 | 4,3 |
| P375 | 12 | 4.586 | 121.500 | 10.125 | 49,1 | 4,1 |
| P703 | 1 | 44.143 | 16.040 | 16.040 | 8,4 | 8,4 |
| P703 | 2 | 28.140 | 32.158 | 16.079 | 14,5 | 7,3 |
| P703 | 3 | 14.895 | 48.451 | 16.150 | 17,7 | 5,9 |
| P703 | 4 | 7.881 | 64.693 | 16.173 | 19,8 | 4,9 |
| P703 | 5 | 4.075 | 80.746 | 16.149 | 21,4 | 4,3 |
| P703 | 6 | 2.257 | 96.527 | 16.088 | 22,5 | 3,7 |
| P703 | 7 | 1.121 | 112.868 | 16.124 | 23,9 | 3,4 |
| P703 | 8 | 763 | 126.570 | 15.821 | 24,0 | 3,0 |
| P703 | 9 | 336 | 143.646 | 15.961 | 25,5 | 2,8 |
| P703 | 10 | 169 | 152.895 | 15.290 | 25,0 | 2,5 |
| P703 | 11 | 93 | 126.283 | 11.480 | 24,5 | 2,2 |
| P703 | 12 | 79 | 127.835 | 10.653 | 24,6 | 2,1 |

### V1b. Δkm y Δdías entre services con numeración consecutiva (recalculado)

| index | n | p5 | p10 | p25 | p50 | p75 | p90 | p95 | media |
|---|---|---|---|---|---|---|---|---|---|
| P375 Δkm | 51.593 | 7.247 | 8.301 | 9.460 | 10.330 | 11.724 | 15.401 | 20.266 | 12.530 |
| P703 Δkm | 46.043 | 9.409 | 11.922 | 14.726 | 16.138 | 17.639 | 19.743 | 21.641 | 16.840 |
| P375 Δdías | 51.593 | 57 | 71 | 101 | 151 | 225 | 332 | 382 | 177 |
| P703 Δdías | 46.043 | 70 | 87 | 121 | 177 | 258 | 352 | 375 | 197 |

### V1c. Sesgo de truncamiento en 'edad al n-ésimo service' y km al 1° service (MY>=2024)

| métrica | valor |
|---|---|
| P703: edad máxima posible al CUTOFF (meses, p1 de WSD) | 37,0 |
| P703: eventos con n=10 | 169 |
| P703 n=10: tasa de uso mediana (km/año) de esos vehículos | 66.170 |
| P703 n=1: edad mediana (meses) | 8,4 |
| P703 n=1: % con edad > 11,5 meses | 26,0 |
| 1° service MY>=2024: n | 42.987 |
| 1° service MY>=2024: % en (15.000, 18.000] | 59,0 |
| 1° service MY>=2024: % en (12.000, 15.000] | 13,8 |
| 1° service MY>=2024: % <= 10.000 | 8,5 |

P703 WSD p1 = 2023-07-26. Ningún P703 puede tener más de ~37 meses: el 'meses/n' para n alto está truncado por construcción (solo llegan a n=10 los de uso extremo).

### V2a. Intervalos > 365 días: ingenuo (todos los pares) vs con 18 m de seguimiento garantizado

| métrica | valor |
|---|---|
| pares ingenuos (todos) | 133.837 |
|   mediana días | 161 |
|   % > 365 d | 7,9 |
| anclas con seguimiento >= 548 d (P703/P375) | 86.484 |
|   % que retorna en 18 m | 80,8 |
|   mediana días al siguiente, entre retornos en 18 m | 165 |
|   % > 365 d entre retornos en 18 m | 9,5 |
|   % > 365 d o sin retorno en 18 m (sobre todas las anclas) | 26,9 |
|   mediana incondicional (no-retorno = censurado > 548 d) | 202 |
|   p75 incondicional | 382 |
| anclas con seguimiento >= 730 d: % > 365 d entre retornos en 24 m | 10,5 |

### V2b. Lo mismo por generación

| gen | anclas | % retorna 18 m | mediana días (retornos) | p90 días (retornos) | % > 365 d (retornos) | mediana incondicional |
|---|---|---|---|---|---|---|
| P375 | 64.491 | 77,8 | 154 | 357 | 8,7 | 196 |
| P703 | 21.993 | 89,3 | 195 | 372 | 11,5 | 213 |

### V3a. KM es constante por vehículo (nivel ítem, agenda cruda) y coincide con el último VehicleCurrentKM

| métrica | valor |
|---|---|
| vehículos (agenda cruda) | 111.752 |
|   con KM constante (nunique <= 1) | 111.745 |
|   % constante | 99,99 |
| vehículos con alguna lectura VCK | 106.370 |
|   % KM == VCK última visita (cualquier estado) | 91,7 |
|   % KM == VCK última visita (60) Concluido | 91,7 |
|   % KM == VCK de alguna visita del vehículo | 94,4 |
| vehículos KM != VCK última | 8.819 |
|   de ellos KM nulo | 4.607 |
|   de ellos VCK última inválida (<100 o >1e6) | 475 |
|   de ellos KM > VCK última (dato más nuevo que la agenda) | 520 |
|   de ellos KM < VCK última | 3.692 |

### V3b. Nulos de VehicleCurrentKM y KM por StatusARG (recalculado)

| StatusARG | turnos | vck_nulo_pct | km_nulo_pct |
|---|---|---|---|
| (30) Agendado | 3.953,0 | 76,5 | 14,9 |
| (40) En progreso | 1.832,0 | 60,4 | 12,3 |
| (60) Concluido | 342.691,0 | 0,0 | 2,4 |
| (70) Cancelado | 101.222,0 | 100,0 | 4,1 |
| (80) No asistio | 27.237,0 | 71,9 | 12,3 |
| (90) Concluido sin OS | 15.507,0 | 2,8 | 2,8 |

### V4a. Tasa de uso: métodos A y B recalculados; y la variante 'KM snapshot / edad al CUTOFF'

| métrica | valor |
|---|---|
| A: vehículos | 85.495 |
| A: mediana km/año | 21.514 |
| A: p25 | 14.616 |
| A: p75 | 31.307 |
| B: vehículos | 52.548 |
| B: mediana km/año | 24.689 |
| ambos: n | 52.368 |
| Spearman A-B | 0,895 |
| mediana B/A | 1,001 |
| % |B/A-1| <= 0,25 | 78,5 |
| KM snapshot / edad al CUTOFF: vehículos | 82.755 |
|   mediana km/año | 16.596 |
|   Spearman vs A (vehículos con ambos) | 0,870 |

### V4b. Tasa A por segmento (recalculado)

| index | n | p5 | p10 | p25 | p50 | p75 | p90 | p95 | media |
|---|---|---|---|---|---|---|---|---|---|
| P703 | 46.534 | 8.446 | 11.033 | 16.337 | 23.790 | 34.339 | 47.312 | 56.566 | 27.118 |
| P375 | 38.952 | 6.880 | 9.004 | 13.076 | 19.069 | 27.549 | 38.300 | 46.668 | 21.913 |
| Ford Blue | 25.826 | 8.457 | 11.024 | 16.221 | 23.390 | 33.214 | 45.064 | 53.886 | 26.385 |
| Ford Pro | 10.367 | 9.610 | 12.624 | 18.862 | 28.312 | 41.269 | 55.461 | 64.444 | 31.709 |
| PersonType F | 21.041 | 8.046 | 10.553 | 15.579 | 22.455 | 31.922 | 43.798 | 52.946 | 25.452 |
| PersonType J | 14.851 | 10.149 | 13.275 | 19.498 | 28.406 | 40.390 | 53.806 | 62.854 | 31.576 |

### V4c. Tasa reciente vs acumulada, comparadas SOLO en las ventanas donde la reciente existe (comparación no diluida)

| tasa | ventanas (subconjunto con tasa reciente) | p10 | p50 | p90 | mediana |retraso| | % |retraso| <= 30 d | % |retraso| <= 60 d | % abiertas a due-30 | % retornos antes de due-30 | % capturado hasta due+90 | % churn abiertas H=90 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| acumulada (km/edad) | 31.790 | -55 | 6 | 107 | 30 | 49,5 | 72,2 | 83,6 | 19,2 | 87,5 | 30,0 |
| reciente (pendiente último intervalo) | 31.790 | -43 | 13 | 117 | 31 | 49,1 | 71,5 | 87,6 | 14,5 | 85,8 | 30,4 |
| promedio de ambas | 31.790 | -40 | 10 | 113 | 28 | 51,8 | 74,0 | 88,2 | 13,8 | 86,6 | 29,4 |

La tabla f1 del informe original compara 'acumulada' contra 'reciente con fallback a acumulada' sobre TODAS las ventanas; como la reciente existe solo en el 36.8% de ellas, la diferencia queda diluida. Acá se compara sobre ese subconjunto.

### V5a. Regla K por generación, apertura due-30, horizonte due+90 (recalculado)

| métrica | valor |
|---|---|
| ventanas | 86.484 |
| % retorna en 18 m | 80,8 |
| % fallback a tasa poblacional | 4,1 |
| % manda el tope 365 d | 8,8 |
| due mediana (d) | 165 |
| retraso p10 | -85 |
| retraso p25 | -28 |
| retraso p50 | 7 |
| retraso p75 | 54 |
| retraso p90 | 129 |
| % ventanas abiertas a due-30 | 80,4 |
| % retornos antes de due-30 | 24,3 |
| % retornos capturados hasta due+90 | 84,3 |
|   hasta due+60 | 77,1 |
|   hasta due+120 | 88,9 |
| % churn incondicional H=90 | 31,9 |
| % churn entre abiertas H=90 | 39,7 |
|   H=60 | 46,9 |
|   H=120 | 35,1 |
| descomposición: % no vuelve en 18 m | 19,2 |
| descomposición: % tardíos (vuelve entre due+90 y 18 m) | 12,7 |

### V5b. Por generación (recalculado)

| gen | ventanas | % retorna 18 m | % tope 365 | due mediana | retraso p50 | retraso p90 | % abiertas | % churn abiertas H=90 |
|---|---|---|---|---|---|---|---|---|
| P375 | 64.491 | 77,8 | 8,0 | 158 | 5 | 129 | 80,6 | 42,4 |
| P703 | 21.993 | 89,3 | 11,3 | 187 | 13 | 129 | 79,7 | 31,6 |

### V5c. Sensibilidad: excluir 'retornos' a menos de 30 días del ancla

| métrica | valor |
|---|---|
| ventanas con siguiente mantenimiento a < 30 d | 846 |
|   % del total | 1,0 |
|   de ellas con km <= km del ancla (visita partida) | 356 |
| sin ellas: % churn entre abiertas H=90 | 39,8 |
| sin ellas: % retornos antes de due-30 | 23,4 |
| sin ellas: retraso p50 | 8 |

### V5d. Prevalencia por año del ancla y generación (¿drift?)

| año ancla | gen | ventanas | % retorna 18 m | % churn abiertas H=90 |
|---|---|---|---|---|
| 2.024 | P375 | 56.637 | 78,3 | 41,9 |
| 2.024 | P703 | 16.925 | 89,6 | 31,3 |
| 2.025 | P375 | 7.854 | 74,7 | 46,3 |
| 2.025 | P703 | 5.068 | 88,4 | 32,6 |

### V6a. Cohorte WSD 2024 (recalculado)

| métrica | valor |
|---|---|
| vehículos | 21.290 |
| seguimiento mínimo (meses) | 19,8 |
| % 1° mant. <= 12 m | 64,5 |
| % <= 18 m | 80,9 |
| % hasta CUTOFF | 86,0 |
| mediana meses WSD->1° | 9,2 |
| mediana km al 1° | 16.172 |
| % 1° evento con maint_number == 1 | 88,5 |
| 1°->2°: n con seguimiento >= 12 m | 14.085 |
|   % 2° <= 12 m | 75,4 |
| 1°->2°: n con seguimiento >= 18 m | 6.364 |
|   % 2° <= 18 m | 91,5 |
|   t1 mediana (meses) de ese subconjunto | 5,8 |
|   t1 mediana de todos los que hicieron el 1° | 9,2 |

### V6b. Retorno al 2° service (12 m) según cuánto tardó el 1°: selección del subconjunto con 18 m de seguimiento

| meses WSD->1° (bucket) | n (seg. >= 12 m tras el 1°) | % 2° <= 12 m | % con seg. >= 18 m |
|---|---|---|---|
| <=4 | 1.547 | 91,5 | 86,9 |
| 4-6 | 2.820 | 90,3 | 70,7 |
| 6-8 | 3.078 | 82,5 | 49,3 |
| 8-10 | 2.473 | 75,8 | 34,3 |
| 10-12 | 2.562 | 58,1 | 20,7 |
| 12-15 | 1.425 | 46,8 | 8,8 |
| >15 | 176 | 49,4 | 0,0 |

Los vehículos con 18 m de seguimiento tras el 1° son los que hicieron el 1° temprano (t1 chico), que retornan más: el 91,5 % 'del 1° al 2° en 18 m' está sesgado hacia arriba. La comparación limpia es a 12 m: 64,5 % (WSD→1°) vs 75,4 % (1°→2°).

### V7. Δkm y Δdías por segmento, solo P703 con numeración consecutiva (control de generación e intervalos dobles)

| segmento (P703, n→n+1, en sales) | pares | Δkm p25 | Δkm mediana | Δkm p75 | Δdías p25 | Δdías mediana | Δdías p75 |
|---|---|---|---|---|---|---|---|
| Ford Blue | 19.773 | 14.999 | 16.198 | 17.582 | 127 | 177 | 250 |
| Ford Pro | 9.814 | 14.541 | 16.045 | 17.516 | 94 | 134 | 196 |
| PersonType F | 14.937 | 14.917 | 16.149 | 17.482 | 131 | 183 | 260 |
| PersonType J | 14.488 | 14.787 | 16.139 | 17.647 | 101 | 144 | 204 |

### V8a. Índice estacional: crudo vs con la tendencia removida

| mes | índice crudo (orig., 2024-25) | índice regresión: tendencia lineal + mes, por día hábil (2024-01→2026-07) | índice ratio a media móvil 2×12 (crudo) |
|---|---|---|---|
| ene | 104,1 | 108,8 | 113,2 |
| feb | 91,4 | 100,9 | 97,1 |
| mar | 90,7 | 100,9 | 91,7 |
| abr | 94,9 | 97,5 | 98,5 |
| may | 97,6 | 95,9 | 100,0 |
| jun | 85,2 | 90,6 | 91,9 |
| jul | 105,1 | 95,0 | 103,7 |
| ago | 104,8 | 105,0 | 102,1 |
| sep | 104,4 | 103,3 | 100,4 |
| oct | 111,4 | 101,7 | 105,6 |
| nov | 101,7 | 102,8 | 95,3 |
| dic | 108,7 | 99,0 | 100,6 |

Tendencia estimada: 1.26 % mensual por día hábil (≈ 16 % anual). El índice crudo del informe original no remueve la tendencia, por lo que infla jul-dic y deprime ene-jun.

### V8b. Residuo (%) por año y mes tras quitar tendencia y estacionalidad: ¿junio/enero son sistemáticos?

| index | 2024 | 2025 | 2026 |
|---|---|---|---|
| ene | -4,5 | 0,1 | 4,4 |
| feb | -2,8 | 8,0 | -5,1 |
| mar | -1,0 | -2,8 | 3,9 |
| abr | -2,7 | 3,0 | -0,3 |
| may | -3,4 | 5,7 | -2,3 |
| jun | -5,3 | 7,3 | -2,0 |
| jul | 2,1 | 7,5 | -9,6 |
| ago | -0,4 | 0,4 |  |
| sep | 3,3 | -3,3 |  |
| oct | 0,3 | -0,3 |  |
| nov | 2,2 | -2,2 |  |
| dic | 1,2 | -1,2 |  |

### V9a. Distribución completa del salto de maint_number (recalculado)

| index | pares | % |
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
| nulo | 0 | 0,0 |

### V9b. ¿El salto +2 es un 'intervalo doble'? Δkm por salto de numeración y generación

| gen | salto | pares | Δkm p25 | Δkm mediana | Δkm p75 | Δkm mediana / K | Δdías mediana | % Δkm en [1,5K, 2,5K] |
|---|---|---|---|---|---|---|---|---|
| P703 | -1 | 438 | 12.391 | 15.762 | 18.798 | 1,05 | 126 | 9,1 |
| P703 | 0 | 1.892 | 7.630 | 14.352 | 16.916 | 0,96 | 127 | 4,8 |
| P703 | 1 | 46.043 | 14.726 | 16.138 | 17.639 | 1,08 | 177 | 3,3 |
| P703 | 2 | 2.875 | 16.799 | 24.808 | 32.550 | 1,65 | 211 | 46,1 |
| P703 | 3 | 563 | 15.987 | 20.797 | 44.305 | 1,39 | 186 | 13,7 |
| P703 | 4 | 299 | 15.047 | 17.206 | 26.606 | 1,15 | 137 | 9,0 |
| P375 | -1 | 984 | 9.531 | 10.786 | 14.002 | 1,08 | 147 | 14,1 |
| P375 | 0 | 3.759 | 9.199 | 10.596 | 13.335 | 1,06 | 123 | 13,3 |
| P375 | 1 | 51.593 | 9.460 | 10.330 | 11.724 | 1,03 | 151 | 7,7 |
| P375 | 2 | 6.267 | 11.182 | 16.227 | 20.339 | 1,62 | 193 | 46,4 |
| P375 | 3 | 1.853 | 10.847 | 19.284 | 28.694 | 1,93 | 215 | 24,1 |
| P375 | 4 | 885 | 10.420 | 16.109 | 32.944 | 1,61 | 202 | 17,2 |

### V9c. ServiceMaintenance vs número que dice ServiceName (nivel ítem, agenda cruda)

| ServiceMaintenance | nombre != n | nombre == n | % nombre != n | nombre más frecuente |
|---|---|---|---|---|
| 1 | 0 | 63.788 | 0,0 | 1° Maintenance service |
| 2 | 0 | 45.872 | 0,0 | 2° Maintenance service |
| 3 | 0 | 32.423 | 0,0 | 3° Maintenance service |
| 4 | 0 | 23.418 | 0,0 | 4° Maintenance service |
| 5 | 0 | 18.934 | 0,0 | 5° Maintenance service |
| 6 | 0 | 17.766 | 0,0 | 6° Maintenance service |
| 7 | 0 | 12.623 | 0,0 | 7° Maintenance service |
| 8 | 0 | 11.080 | 0,0 | 8° Maintenance service |
| 9 | 0 | 9.913 | 0,0 | 9° Maintenance service |
| 10 | 0 | 8.390 | 0,0 | 10° Maintenance service |
| 11 | 6.401 | 0 | 100,0 | 1° Maintenance service |
| 12 | 5.627 | 0 | 100,0 | 2° Maintenance service |
| 13 | 975 | 3.539 | 21,6 | 13° Maintenance service |
| 14 | 3.679 | 0 | 100,0 | 4° Maintenance service |
| 15 | 604 | 2.352 | 20,4 | 15° Maintenance service |
| 16 | 2.359 | 0 | 100,0 | 6° Maintenance service |
| 17 | 1.745 | 0 | 100,0 | 7° Maintenance service |
| 18 | 1.529 | 0 | 100,0 | 8° Maintenance service |
| 19 | 1.283 | 0 | 100,0 | 9° Maintenance service |
| 20 | 0 | 4.161 | 0,0 | 20° Maintenance service |

### V9d. Tope 20

| métrica | valor |
|---|---|
| eventos M con maint_number 19 | 1.068 |
| eventos M con maint_number 20 | 3.494 |
| km mediana en n=20 (P375) | 222.285 |
| km mediana en n=19 (P375) | 192.067 |

### V10a. Días entre mantenimientos por tercil de uso: pares ingenuos vs anclas con 18 m de seguimiento

| tercil de uso | anclas (18 m seg.) | % retorna 18 m | mediana días (retornos) | mediana incondicional | % > 365 d (retornos) | pares ingenuos: mediana días |
|---|---|---|---|---|---|---|
| alto | 38.475 | 87,6 | 113 | 125 | 2,0 | 120 |
| bajo | 19.727 | 68,0 | 321 | 375 | 31,5 | 316 |
| medio | 26.987 | 81,8 | 197 | 223 | 7,4 | 203 |

### V10b. Prevalencia de churn entre abiertas (H=90) reponderada a la mezcla P703/P375 de 2026

| métrica | valor |
|---|---|
| mezcla ventanas evaluadas: % P703 | 25,4 |
| mezcla mantenimientos 2026-01→08: % P703 | 69,6 |
| prevalencia observada (mezcla 2024-25) | 39,7 |
| prevalencia reponderada a mezcla 2026 | 34,8 |

### V10c. Primer service, ancla WSD, K=15.000 con tasa poblacional P703 (recalculado)

| métrica | valor |
|---|---|
| ventanas | 21.283 |
| due (d) | 230 |
| retraso p10 | -104 |
| retraso p50 | 36 |
| retraso p90 | 172 |
| sólo tiempo (365 d): retraso p10 | -239 |
|   p50 | -99 |
|   p90 | 37 |

### V10d. 'Intervalos dobles' por km (Δkm >= 1,5·K) vs por salto de numeración

| gen | pares km válido | % Δkm >= 1,5K (intervalo doble por km) | % salto >= +2 | % ambos | % Δkm >= 1,5K entre salto +1 | % Δkm >= 1,5K entre salto >= +2 | % salto >= +2 entre Δkm >= 1,5K |
|---|---|---|---|---|---|---|---|
| P703 | 53.017,0 | 7,9 | 7,6 | 3,8 | 4,2 | 49,4 | 47,9 |
| P375 | 70.898,0 | 18,5 | 16,0 | 8,2 | 10,7 | 51,3 | 44,4 |

### V10e. Cohorte 2024: '% del 1° evento etiquetado como 1° service' según denominador

| métrica | valor |
|---|---|
| sobre toda la cohorte (21.290, sin evento cuenta como no) | 76,1 |
| sobre los que tienen evento (18.317) | 88,5 |
| 1° evento con n1 == 2 | 9,0 |
| 1° evento con n1 >= 3 | 2,5 |
| 1° evento con n1 nulo | 0,0 |
