# EDA 02 — Cadencia de mantenimiento (tiempo y km) y parámetros empíricos de la ventana

Script: `scripts/eda/02_cadencia_ventana.py` (corre de punta a punta en ~30 s sobre los parquet de `data/interim`).
Todas las tablas citadas están, con su numeración (c1, a1, f6, ...), en `reports/eda/02_cadencia_ventana_tablas.md`,
generado por el script. Figuras en `reports/figures/eda/02_cadencia_ventana_*.png`. CUTOFF = 2026-08-25.

Este informe fue verificado de forma independiente (`reports/eda/02_cadencia_ventana_verificacion.md`, script
`scripts/eda/02_cadencia_ventana_verificacion.py`). Las correcciones aplicadas a raíz de esa verificación están listadas ahí;
las más importantes: la censura de los intervalos (tabla a4), el índice estacional sin tendencia (g2), el sesgo de selección en
1° → 2° (e4), la comparación no diluida de la tasa reciente (f7) y la etiqueta del 1° service en la cohorte 2024 (88,5 %, no 76,1 %).

Evento objetivo: `is_completed_maintenance` tal como lo define `src/repurchase/eventos.py` (turno `(60) Concluido`
con al menos un ítem de mantenimiento programado). No se redefine acá; los problemas detectados se listan en la sección 9.

---

## Resumen ejecutivo

1. **La regla real de mantenimiento es por kilómetros, no por tiempo, y difiere por generación: P703 cada 15.000 km,
   P375 cada 10.000 km.** El km al evento dividido el número de service converge a 16.040-16.173 km (P703, n = 1..7) y a
   10.125-10.330 km (P375, n = 2..12); el incremento de km entre services consecutivos tiene mediana 16.138 km (P703) y
   10.330 km (P375). La edad al n-ésimo service NO es 12·n meses: el 1° service de P703 ocurre a 8,4 meses de mediana (no a
   12) y entre services consecutivos pasan 177 días de mediana (P703) / 151 (P375), no 365. Las edades a n ≥ 5 en P703 no
   sirven como evidencia: ningún P703 tiene más de ~37 meses, así que a n = 10 solo llegan vehículos de 66.000 km/año y el
   "2,5 meses por service" es selección, no cadencia (tablas b1, b2; figuras `box_km_por_service`, `box_edad_por_service`).
2. **El tope anual casi no opera.** Mediana de 161 días entre mantenimientos consecutivos observados (P703 174, P375 153); solo
   el 7,9 % de los pares supera 365 días. Esos números están censurados (un par solo existe si el siguiente service ya ocurrió):
   con 18 meses de seguimiento garantizado la mediana entre retornos es 165 días, el 9,5 % de los retornos tarda más de 365
   días y el 19,2 % de las anclas no vuelve en 18 meses (mediana incondicional 202 días; tabla a4). Con la regla recomendada el
   tope de 365 días manda en el 8,8 % de las ventanas (P703 11,3 %).
3. **`KM` no es el km del turno: es un snapshot por vehículo.** Es constante en el 99,99 % de los vehículos y coincide con el
   `VehicleCurrentKM` de la última visita en el 91,7 %. Usarlo como feature a nivel evento es leakage. El km del evento es
   `VehicleCurrentKM` (0 % nulo en Concluido, 100 % nulo en Cancelado) (tablas c1, c2).
4. **Tasa de uso mediana 21.514 km/año** (p25 14.616, p75 31.307); Ford Pro 28.312 vs Ford Blue 23.390; jurídicas 28.406 vs
   físicas 22.455. El método "km acumulado / edad" y el de "pendiente entre visitas" concuerdan (Spearman 0,895, mediana del
   cociente 1,001) (tablas d2-d4).
5. **Cohorte de ventas con garantía iniciada en 2024 (21.290 vehículos): 64,5 % hizo el 1° service en la red dentro de los 12
   meses, 80,9 % dentro de 18, 86,0 % hasta el cutoff.** Mediana 9,2 meses y 16.172 km al 1° service. Del 1° al 2°: 75,4 % en
   12 meses (14.085 vehículos con seguimiento); el 91,5 % a 18 meses está inflado por selección (solo tienen 18 meses de
   seguimiento tras el 1° los que lo hicieron temprano, y esos vuelven más: tabla e4). El retraso del 1° service predice el
   retorno al 2°: 91 % vuelve en 12 meses si el 1° fue a ≤ 4 meses, 47 % si fue a 12-15 (tablas e1-e4; figura `cohorte2024_curvas`).
6. **Ventana recomendada:** `due = ancla + min(365 d, K_gen / tasa_uso × 365,25)` con K_gen = 15.000 (P703) / 10.000 (P375)
   y tasa_uso = km al ancla / edad del vehículo al ancla; **apertura en due − 30 d, horizonte due + 90 d**. Con eso el
   retraso real tiene mediana +7 d (p10 −85, p90 +129); el 84,3 % de los que vuelven en 18 meses lo hace antes de due + 90;
   el 80,4 % de las ventanas está abierta a due − 30 y la prevalencia de churn en esas ventanas es 39,7 % (P703 31,6 %,
   P375 42,4 %; 34,8 % reponderando a la mezcla de generaciones de 2026, tabla f8) (tablas f1-f3, f6, f8; figura
   `ventana_retraso_sensibilidad`).
7. **Descartadas:** la regla "solo tiempo (365 d)" ubica el due 200 días DESPUÉS de la mediana de retorno y deja el 85,9 % de
   los retornos antes de due − 30 (la ventana se abriría con el cliente ya atendido). K = 15.000 para todo el parque corre el
   due 33 días tarde en P375; K = 10.000 para todo el parque lo adelanta 20 días en P703. La tasa "reciente" (pendiente del
   último intervalo) no mejora a la acumulada: comparadas sin diluir en las 32.323 ventanas donde la reciente existe, la mediana
   de |retraso| es 31 vs 30 días y el 49,1 % vs 49,5 % cae dentro de ±30 días (tabla f7); además solo existe en el 37,4 % de las
   ventanas.
8. **Estacionalidad moderada, y hay que leerla sin la tendencia:** el volumen por día hábil crece 1,3 % mensual (≈ 16 % anual),
   así que un índice "media anual = 100" infla el segundo semestre. Con la tendencia removida (regresión con efecto mes, por
   día hábil, 2024-01→2026-07): junio es el mes bajo (90,6, y por debajo de la tendencia los tres años), enero el alto (108,8,
   por encima de la tendencia los tres años: no hay caída por vacaciones, hay un pico); octubre (101,7), julio (95,0) y diciembre
   (99,0) no se distinguen; el "octubre alto" del índice crudo (111,4) era tendencia. Mucho más fuerte que la estacionalidad es
   el cambio de composición del parque: los mantenimientos P375 caen de 5.856 (2024-01) a 2.009 (2026-07) mientras P703 sube
   de 437 a 5.625 (tablas g1, g2; figura `estacionalidad`).

---

## 0. Base de trabajo

Tabla m0. De 492.442 turnos, 222.889 son mantenimientos completados. Se descartan 0 por fecha fuera de rango y se colapsan
1.033 filas que repiten vehículo + `event_date` (misma visita partida en varios `schedule_id`). Queda la base **M: 221.856
eventos de 87.531 vehículos**, 36.950 de ellos también en sales. `km_evento` = `VehicleCurrentKM` si está entre 100 y
1.000.000 (válido en 218.149 eventos); `WSD` = `WarrantyStartDate` de agenda con fallback a sales (disponible en 220.517).
Generación: `ShortVehicleModelGroupTreated` mapeado a P703 / P375 / Otro.

---

## 1. Qué es `KM` y qué es `VehicleCurrentKM` (punto c)

**Tabla c1 — nulos por estado del turno (todos los turnos):**

| StatusARG | turnos | KM nulo % | VehicleCurrentKM nulo % | check-in nulo % |
|---|---|---|---|---|
| (60) Concluido | 342.691 | 2,4 | 0,0 | 13,3 |
| (90) Concluido sin OS | 15.507 | 2,8 | 2,8 | 18,9 |
| (80) No asistio | 27.237 | 12,3 | 71,9 | 94,3 |
| (70) Cancelado | 101.222 | 4,1 | 100,0 | 100,0 |
| (30) Agendado | 3.953 | 14,9 | 76,5 | 99,8 |

**Tabla c2 — `KM` es un atributo del vehículo:** de 111.752 vehículos, 111.745 (99,99 %) tienen un único valor de `KM` en
todos sus turnos (incluidos los cancelados); solo 7 tienen más de uno. En cambio, de 85.143 vehículos con ≥ 2 turnos, 73.813
tienen más de un valor de `VehicleCurrentKM`. `KM` coincide con el `VehicleCurrentKM` de la última visita con lectura en el
91,7 % de los vehículos y con el máximo de `VehicleCurrentKM` en el 84,4 %. Figura `km_vs_vehiclecurrentkm` (panel derecho):
la diferencia `KM − VehicleCurrentKM_última` es 0 en ~10⁵ vehículos; el resto es una cola de diferencias pequeñas y raras. De los
8.819 vehículos (8,3 %) donde no coinciden: 4.607 tienen `KM` nulo, 475 una última lectura inválida (< 100 o > 10⁶), 520 tienen
`KM` mayor que la última lectura (dato más nuevo que la agenda) y 3.692 `KM` menor (otra fuente o error de carga); el 94,4 % de los
vehículos tiene un `KM` igual a alguna de sus lecturas de `VehicleCurrentKM`.

**Lectura.** `KM` = último km conocido del vehículo a la fecha de extracción (probablemente el que muestra la ficha del
vehículo en el sistema del dealer). Se lo copia en cada turno, incluidos los cancelados y los futuros. **No es el km al
agendar ni al check-in**; a nivel evento contiene información posterior al evento (leakage). El km del evento es
`VehicleCurrentKM`, que se carga cuando el vehículo efectivamente entra (0 % nulo en Concluido, 100 % en Cancelado).

**Coherencia con otros temas.** Dividir `KM` (snapshot) por la edad del vehículo *al evento* infla la tasa de uso, porque mezcla
un odómetro futuro con una edad pasada: da una mediana de 34.080 km/año (así está calculada en el EDA 03, tabla
`B_km_anio_y_gap`), contra 21.514 km/año con `VehicleCurrentKM` al último mantenimiento (sección 4). La cifra de 34.080 no
debería citarse como tasa de uso del parque; y `KM` / edad al CUTOFF tampoco sirve (mediana 16.596: subestima porque el snapshot
queda viejo en los vehículos que dejaron de venir).

**Tablas c3, c4 — anomalías del odómetro en mantenimientos completados:** 3.728 lecturas < 100 km (1,7 %; 2.582 valen
exactamente 1: un placeholder), 321 > 500.000 y 66 > 1.000.000. Entre pares consecutivos del mismo vehículo (133.837 pares,
130.382 con km en ambos): el odómetro decrece en 2.393 (1,8 %) y se repite exacto en 3.895 (3,0 %); 1.789 pares (1,3 %) están a
menos de 30 días y 738 de ellos con km igual o menor (misma visita partida en dos turnos); 503 pares saltan más de 100.000 km.

**Propuesta de "km en el evento" robusto** (`km_evento`, implementada en el script):
1. `VehicleCurrentKM` si 100 ≤ valor ≤ 1.000.000; si no, nulo.
2. Dentro de cada vehículo, tratar como nulo un valor menor que el de la visita anterior (1,8 %) y colapsar visitas a < 30 días
   con km ≤ anterior (reprogramaciones/OS partidas) en un solo evento.
3. Imputar los nulos por interpolación lineal en el tiempo con la tasa de uso del vehículo (sección 4), y para el último km
   conocido usar la última lectura válida (no `KM`, aunque en la práctica coinciden en el 91,7 %).
4. `KM` puede usarse solo como atributo del vehículo **a la fecha de extracción**, nunca como feature de un evento pasado.

---

## 2. Cadencia: días y km entre mantenimientos consecutivos (punto a)

Base: 133.837 pares consecutivos de 55.776 vehículos con ≥ 2 mantenimientos completados en el extracto (tabla a3: el
36,3 % de los 87.531 vehículos tiene un solo mantenimiento en 32 meses, 26,6 % dos, 15,6 % tres).

**Tabla a1 — días entre mantenimientos consecutivos:**

| grupo | n | p5 | p10 | p25 | p50 | p75 | p90 | p95 | media |
|---|---|---|---|---|---|---|---|---|---|
| global | 133.837 | 56 | 72 | 106 | 161 | 245 | 352 | 393 | 188 |
| P703 | 56.531 | 61 | 80 | 117 | 174 | 258 | 355 | 382 | 196 |
| P375 | 77.106 | 54 | 69 | 100 | 153 | 234 | 350 | 405 | 183 |
| uso bajo (< 16.875 km/año) | 22.052 | 117 | 157 | 224 | 316 | 375 | 441 | 509 | 309 |
| uso medio | 40.038 | 90 | 112 | 149 | 203 | 271 | 343 | 385 | 218 |
| uso alto (> 27.347 km/año) | 70.509 | 48 | 61 | 85 | 120 | 166 | 218 | 262 | 134 |
| Ford Blue (sales) | 23.463 | 71 | 90 | 125 | 176 | 251 | 347 | 370 | 195 |
| Ford Pro (sales) | 12.571 | 42 | 59 | 89 | 130 | 193 | 273 | 334 | 150 |
| PersonType F (sales) | 17.288 | 74 | 93 | 128 | 183 | 260 | 353 | 374 | 201 |
| PersonType J (sales) | 18.564 | 47 | 64 | 96 | 140 | 203 | 285 | 346 | 158 |

**Tabla a2 — km entre mantenimientos consecutivos (124.094 pares con odómetro válido y creciente):**

| grupo | n | p5 | p10 | p25 | p50 | p75 | p90 | p95 | media |
|---|---|---|---|---|---|---|---|---|---|
| global | 124.094 | 7.490 | 8.783 | 10.099 | 13.141 | 16.839 | 20.547 | 28.893 | 15.486 |
| P703 | 53.017 | 8.682 | 11.522 | 14.679 | 16.201 | 17.998 | 20.846 | 30.131 | 17.512 |
| P375 | 70.898 | 7.143 | 8.333 | 9.561 | 10.563 | 12.917 | 20.242 | 27.788 | 13.961 |
| uso bajo | 20.108 | 5.091 | 6.994 | 9.243 | 10.498 | 13.292 | 17.422 | 20.481 | 12.070 |
| uso alto | 65.853 | 8.162 | 9.206 | 10.631 | 15.076 | 17.636 | 21.818 | 31.850 | 16.705 |
| Ford Blue / Ford Pro (sales) | 22.279 / 11.768 | | | 14.957 / 14.292 | 16.231 / 16.058 | 17.808 / 17.817 | | | |
| PersonType F / J (sales) | 16.474 / 17.399 | | | 14.882 / 14.632 | 16.181 / 16.166 | 17.678 / 17.964 | | | |

Lecturas:
- La distribución de **km** es bimodal por generación (figura `hist_intervalos`, derecha): un pico angosto en ~10.300 (P375) y
  otro en ~16.200 (P703). El intervalo en km **no depende del segmento** (Ford Blue 16.231 vs Ford Pro 16.058; F 16.181 vs J
  16.166): es el plan de mantenimiento. El intervalo en **días** sí depende del uso: mediana 120 días en el tercil alto vs 316 en
  el bajo; Ford Pro 130 vs Ford Blue 176; jurídicas 140 vs físicas 183. Es decir, el tiempo entre services es km / tasa de uso.
- La cola derecha en km (p90 20.547, p95 28.893) son "intervalos dobles": el service intermedio no está en el extracto (hecho
  fuera de la red, antes de 2024-01 o no registrado). Medidos por km (Δkm ≥ 1,5·K_gen) son el 7,9 % de los pares P703 y el
  18,5 % de P375 (tabla b5). La numeración solo los detecta a medias: el salto +2 tiene Δkm mediana 1,65·K (P703) / 1,62·K
  (P375) y solo el 46 % cae en [1,5K, 2,5K]; la otra mitad de los saltos +2 es ruido de numeración. Y entre los pares con salto +1
  hay un 4,2 % (P703) / 10,7 % (P375) de intervalos dobles por km.
- Hay un pico secundario en 365 días para P703 (figura `hist_intervalos`, izquierda): una minoría de bajo uso sigue la regla
  anual "al día".
- Sesgo de truncamiento: los grupos jóvenes (MY 2025-2026: mediana 140 días) solo pueden mostrar intervalos cortos porque su
  seguimiento es corto; no leer esa fila como "los nuevos vuelven más rápido".
- **Censura por la derecha (tabla a4):** un par solo entra en a1 si el siguiente mantenimiento ya ocurrió antes del CUTOFF, así
  que los intervalos largos están subrepresentados. Sobre anclas con 18 meses de seguimiento garantizado (86.484 de P703/P375):
  80,8 % vuelve en 18 meses; entre los que vuelven la mediana es 165 días (P703 195, P375 154) y el 9,5 % tarda más de 365 días
  (P703 11,5 %, P375 8,7 %); la mediana incondicional (no-retorno tratado como > 548 días) es 202 días. En el tercil de uso bajo
  el 31,5 % de los retornos tarda más de 365 días y el 32 % no vuelve en 18 meses. Para el modelo esto es lo que importa: los
  "tardíos" y los que no vuelven son el target, y a1 no los ve.

---

## 3. ¿10.000 o 15.000 km? ¿12·n meses? (punto b)

**Tabla b1 (extracto) — km al evento y edad por número de service:**

| gen | n° service | eventos | km mediana | km/n mediana | edad meses mediana | meses/n |
|---|---|---|---|---|---|---|
| P703 | 1 | 44.143 | 16.040 | 16.040 | 8,4 | 8,4 |
| P703 | 2 | 28.140 | 32.158 | 16.079 | 14,5 | 7,3 |
| P703 | 3 | 14.895 | 48.451 | 16.150 | 17,7 | 5,9 |
| P703 | 5 | 4.075 | 80.746 | 16.149 | 21,4 | 4,3 |
| P703 | 7 | 1.121 | 112.868 | 16.124 | 23,9 | 3,4 |
| P703 | 10 | 169 | 152.895 | 15.290 | 25,0 | 2,5 |
| P375 | 1 | 4.440 | 11.250 | 11.250 | 12,2 | 12,2 |
| P375 | 2 | 7.680 | 20.602 | 10.301 | 18,9 | 9,4 |
| P375 | 5 | 11.209 | 50.913 | 10.183 | 31,5 | 6,3 |
| P375 | 8 | 8.326 | 81.149 | 10.144 | 40,3 | 5,0 |
| P375 | 10 | 6.764 | 101.309 | 10.131 | 45,3 | 4,5 |
| P375 | 12 | 4.586 | 121.500 | 10.125 | 49,1 | 4,1 |

**Tabla b2 — incremento entre services con numeración consecutiva (97.636 pares, 78,7 % de los pares con km válido):**

| | n | p10 | p25 | p50 | p75 | p90 |
|---|---|---|---|---|---|---|
| P703 Δkm | 46.043 | 11.922 | 14.726 | **16.138** | 17.639 | 19.743 |
| P703 Δdías | 46.043 | 87 | 121 | **177** | 258 | 352 |
| P375 Δkm | 51.593 | 8.301 | 9.460 | **10.330** | 11.724 | 15.401 |
| P375 Δdías | 51.593 | 71 | 101 | **151** | 225 | 332 |

**Tabla b3 — km al 1° service en la flota nueva (MY ≥ 2024, 42.987 eventos):** 59,0 % entre 15.000 y 18.000 km; 13,8 % entre
12.000 y 15.000; 7,8 % entre 18.000 y 20.000; 8,5 % a ≤ 10.000; 5,4 % a más de 20.000.

**Conclusión (figuras `box_km_por_service`, `box_edad_por_service`):**
- **P703: plan de 15.000 km.** Los clientes llegan sistemáticamente ~1.000 km después del nominal (mediana 16.040 en el 1°, Δkm
  16.138 entre consecutivos; p25-p75 14.726-17.639). El boxplot de km sigue la recta 15.000·n con precisión hasta n = 7; a partir
  de n = 8 (< 800 eventos, vehículos de lanzamiento con uso extremo) se ensancha.
- **P375: plan de 10.000 km.** km/n = 10.125-10.330 para n = 2..12, Δkm mediana 10.330; el 1° service (11.250) tiene más
  dispersión porque solo se observan los P375 vendidos en 2023-2024.
- **La regla de tiempo (12·n meses) no describe los datos.** El 1° service de P703 ocurre a 8,4 meses de mediana (p75 11,6: el
  26 % lo hace pasados los 11,5 meses, cerca del año, por tiempo) y entre services consecutivos pasan 177 días (P703) / 151
  (P375), no 365 (tabla b2). Ojo con leer `meses/n` a n alto como evidencia: para P703 la edad está truncada por construcción
  (el p1 de WSD es 2023-07-26, ningún P703 supera ~37 meses), así que a n = 10 solo llegan los de uso extremo (tasa mediana
  66.170 km/año) y el "2,5 meses por service" es un artefacto de selección, no una cadencia. Para P375 (edad hasta 20 años)
  meses/n baja de 12,2 (n = 1) a 4,1 (n = 12) con el mismo sesgo, más suave.
- **Regla real: "cada K_gen km o 1 año, lo que ocurra primero", con K_gen = 15.000 (P703) / 10.000 (P375), y en la práctica
  manda el km.** La ficha del tutor ("15.000 km o 1 año") es correcta para la generación nueva, que es la que está en sales.
- Nota sobre `maint_number`: `ServiceMaintenance` es coherente con el km (P375 n = 11 → 111.510 km, n = 12 → 121.500) aunque el
  `ServiceName` de esos ítems diga "1°"/"2°" (el bug del nombre afecta al 100 % de los ítems con `ServiceMaintenance` 11, 12,
  14, 16, 17, 18 y 19 —nombre "1°", "2°", "4°", "6°"..."9°"— y al 20-22 % de los de 13 y 15). El valor 20 concentra 3.494 eventos
  contra 1.068 en 19 (tabla b0) y su km mediano en P375 es 222.285 vs 192.067 en n = 19: funciona como tope "20 o más".
  Distribución completa del salto de numeración (tabla b4): +1 en 77,7 %, ≥ +2 en 12,6 % (7,4 % +2, 2,0 % +3, 1,0 % +4, 0,5 % +5,
  1,7 % más de +5), 0 en 5,1 %, negativo en 4,6 % (2,1 % por debajo de −3).

---

## 4. Tasa de uso (km/año) por vehículo (punto d)

Método A: `km_evento / años desde WSD` en el último mantenimiento completado del vehículo (edad ≥ 3 meses): 86.022 vehículos,
290 fuera del rango plausible [2.000, 150.000] km/año. Método B: pendiente entre la primera y la última visita con km válido
(≥ 90 días, km creciente): 52.838 vehículos.

**Tabla d2 — distribución (km/año):**

| método | n | p5 | p10 | p25 | p50 | p75 | p90 | p95 | media |
|---|---|---|---|---|---|---|---|---|---|
| A: km acumulado / edad | 85.495 | 7.590 | 9.924 | 14.616 | 21.514 | 31.307 | 43.765 | 52.732 | 24.746 |
| B: pendiente entre visitas | 52.548 | 8.591 | 11.218 | 16.681 | 24.689 | 35.827 | 49.337 | 59.016 | 28.149 |

**Tabla d3 — concordancia** (52.368 vehículos con ambos): Spearman 0,895; mediana de B/A 1,001 (p25 0,913, p75 1,119); 78,5 % de
los vehículos con |B/A − 1| ≤ 0,25; mediana |B − A| 2.330 km/año. B es algo mayor en promedio porque solo existe para vehículos
con ≥ 2 visitas (sesgo hacia los de más uso), no porque midan distinto (figura `tasa_uso`, derecha: la nube está sobre la
diagonal).

**Tabla d4 — por segmento (método A):** P703 23.790 vs P375 19.069; Ford Pro 28.312 vs Ford Blue 23.390; jurídicas 28.406 vs
físicas 22.455 (p75: 40.390 vs 31.922). Terciles de uso (cortes 16.875 y 27.347 km/año) usados en las secciones 2 y 6.

**Implicancia:** con K_gen = 15.000 y una mediana de 23.790 km/año, al P703 típico "le toca" cada 230 días; a un Ford Pro
jurídico (32.347 km/año, tabla f4a) cada 169 días; al p10 (11.033 km/año) lo alcanza antes el año. La tasa individual es
estimable con una sola visita (método A) y la reciente no agrega precisión (sección 6), así que la feature `tasa_uso` puede
calcularse para todo vehículo con al menos un km válido y WSD.

---

## 5. Cohorte de ventas 2024 (punto e)

Cohorte: 21.290 vehículos de sales con `WarrantyStartDate` en 2024 (seguimiento mínimo 19,8 meses, así que hasta 18 meses no
hay censura). Figura `cohorte2024_curvas`.

**Tabla e1 — WSD → 1° mantenimiento completado en la red:**

| horizonte | 6 m | 9 m | 12 m | 15 m | 18 m | hasta el cutoff |
|---|---|---|---|---|---|---|
| % que lo completó | 20,5 | 41,9 | 64,5 | 77,1 | 80,9 | 86,0 |

Mediana 9,2 meses (p25 6,1, p75 12,0, p90 15,2); km al 1° mantenimiento mediana 16.172 (p25 14.854, p75 17.607) (tabla e3). El
1° evento observado está numerado como "1° service" en el 88,5 % de los 18.317 casos con evento (9,0 % como 2°, 2,5 % como 3° o
más); 7 vehículos tienen el evento antes del WSD.

**Tabla e2 — 1° → 2° mantenimiento** (denominador: vehículos con seguimiento ≥ h desde el 1°):

| horizonte | 6 m | 9 m | 12 m | 15 m | 18 m |
|---|---|---|---|---|---|
| n con seguimiento | 17.390 | 16.277 | 14.085 | 10.560 | 6.364 |
| % que lo completó | 26,3 | 50,1 | 75,4 | 87,5 | 91,5 |

Mediana 1° → 2° 6,1 meses (p25 4,2, p75 8,9, p90 11,8), calculada sobre los 5.864 con 18 meses de seguimiento tras el 1°.

**Sesgo de selección en e2 (tabla e4):** solo tienen h meses de seguimiento tras el 1° los que hicieron el 1° temprano (el
subconjunto con ≥ 18 m tiene t1 mediana 5,8 meses vs 9,2 en el total), y esos vuelven más. El retorno al 2° dentro de 12 meses
va de 91,5 % (1° a ≤ 4 meses) a 46,8 % (1° a 12-15 meses). Por eso el 91,5 % a 18 meses no es comparable con el 80,9 % de
WSD → 1°; la comparación limpia es a 12 meses: 35,5 % sin 1° service vs 24,6 % sin 2° (denominador 14.085, casi completo).

**Lectura:** el 1° service tarda más (9,2 meses) que los siguientes (6,1) aunque el intervalo en km sea el mismo; hipótesis a
verificar: el vehículo nuevo acumula km más despacio al principio, o el WSD antecede a la entrega efectiva. Un 19 % de los
compradores 2024 no volvió a la red en 18 meses y a 12 meses falta el 35,5 % (vs 24,6 % del 1° al 2°): **el mayor riesgo de
churn está en la primera ventana**, que además es la única sin km previo para individualizar el due (sección 6.3). Y el retraso
con que se hizo el service anterior es una feature fuerte para las ventanas siguientes (tabla e4).

---

## 6. Propuesta empírica de ventana (punto f)

### 6.1 Definición evaluada

Para cada mantenimiento completado (ancla) con 18 meses de seguimiento antes del CUTOFF (anclas hasta fines de febrero de
2025; 86.484 ventanas P703/P375; el 80,8 % vuelve a hacer un mantenimiento en 18 meses):

`due_date = ancla + min(365 d, K / tasa_i × 365,25)`, con `tasa_i = km_evento / edad del vehículo en el ancla` (solo información
disponible al ancla; fallback a la mediana de la generación en el 4,1 % de las ventanas). Retraso = fecha del siguiente
mantenimiento − due. Se prueban K = 10.000, K = 15.000, K por generación (15k P703 / 10k P375), solo tiempo (365 d) y la variante
con tasa "reciente" (pendiente del último intervalo, disponible en el 37,4 % de las ventanas).

**Tabla f1 — retraso real (días) entre quienes vuelven en 18 meses:**

| regla | % manda tope 365 | due mediana | p5 | p10 | p25 | p50 | p75 | p90 | p95 | % retornos antes de due−30 / −60 / −90 |
|---|---|---|---|---|---|---|---|---|---|---|
| solo tiempo (365 d) | 100,0 | 365 | −309 | −294 | −259 | −200 | −107 | −1 | 41 | 85,9 / 82,3 / 78,0 |
| K = 10.000 | 7,1 | 149 | −114 | −71 | −20 | 20 | 78 | 155 | 211 | 20,3 / 12,0 / 7,3 |
| K = 15.000 | 18,9 | 223 | −193 | −152 | −87 | −33 | 20 | 89 | 144 | 51,6 / 36,0 / 24,1 |
| **K por generación** | 8,8 | 165 | −132 | −85 | −28 | **7** | 54 | 129 | 187 | 24,3 / 14,5 / 9,3 |
| K por generación, tasa reciente | 8,9 | 162 | −130 | −80 | −24 | 10 | 57 | 132 | 189 | 22,4 / 13,5 / 8,7 |

Figura `ventana_retraso_sensibilidad` (izquierda): la ECDF de "K por generación" cruza el 50 % en +7 días; la de "solo tiempo"
está corrida 200 días a la izquierda. La fila "tasa reciente" de f1 está diluida: en el 62,6 % de las ventanas no hay intervalo
previo con km y la regla cae a la acumulada; la comparación no diluida (solo ventanas con tasa reciente) está en la tabla f7,
sección 6.4, y da la misma conclusión.

**Tabla f3 — regla K por generación, por generación:** P375 (64.491 ventanas, 77,8 % vuelve en 18 m): due mediana 158 d, retraso
p50 +5, p90 +129; P703 (21.993 ventanas, 89,3 % vuelve): due mediana 187 d, tope anual en 11,3 %, retraso p50 +13, p90 +129.
**Tabla f5 — por tercil de uso:** p50 +5 / +12 / +10 (alto / medio / bajo); p90 +96 / +151 / +153; % que vuelve en 18 m 87,6 /
81,8 / 68,0. La regla centra bien en los tres terciles; la dispersión (y el churn) crecen a menor uso.

### 6.2 Apertura y horizonte: sensibilidad

**Tabla f2 (regla K por generación, apertura due − 30):**

| H (días tras due) | 0 | 30 | 60 | 90 | 120 | 150 | 180 |
|---|---|---|---|---|---|---|---|
| % de retornos (18 m) capturados hasta due + H | 44,4 | 65,1 | 77,1 | 84,3 | 88,9 | 92,2 | 94,5 |
| % churn incondicional (no volvió hasta due + H) | 64,2 | 47,4 | 37,7 | 31,9 | 28,2 | 25,6 | 23,7 |
| % churn entre ventanas abiertas en due − 30 (69.548 = 80,4 %) | 79,8 | 59,0 | 46,9 | 39,7 | 35,1 | 31,8 | 29,5 |

**Tabla f6 — grilla apertura × horizonte (regla K por generación):**

| apertura | H | largo (d) | % ventanas abiertas | % retornos dentro de [apertura, due+H] | % retornos antes de la apertura | % churn entre abiertas |
|---|---|---|---|---|---|---|
| −90 | 90 | 180 | 92,5 | 75,0 | 9,3 | 34,5 |
| −90 | 120 | 210 | 92,5 | 79,7 | 9,3 | 30,5 |
| −60 | 90 | 150 | 88,3 | 69,8 | 14,5 | 36,2 |
| −60 | 120 | 180 | 88,3 | 74,4 | 14,5 | 31,9 |
| **−30** | **90** | **120** | **80,4** | **60,0** | **24,3** | **39,7** |
| −30 | 120 | 150 | 80,4 | 64,7 | 24,3 | 35,1 |
| 0 | 90 | 90 | 64,3 | 40,1 | 44,2 | 49,7 |

Una ventana está "abierta" si el vehículo no volvió antes de la apertura; "churn entre abiertas" es la prevalencia del target
que ve el modelo al abrir. Descomposición a H = 90: 31,9 % de churn incondicional = 19,2 % que no vuelve en 18 meses + 12,7 % que
vuelve entre due + 90 y 18 meses ("tardíos").

La prevalencia de 39,7 % corresponde a la mezcla de las ventanas evaluadas (anclas 2024-01→2025-02: solo 25,4 % P703). En 2026
el 69,6 % de los mantenimientos son P703; reponderando por generación (31,6 % / 42,4 %) la prevalencia esperada en la población
actual es 34,8 % (tabla f8). Excluir los "retornos" a menos de 30 días del ancla (846 ventanas, 1,0 %; visitas partidas o
re-trabajos) no cambia nada: 39,8 %.

### 6.3 Primer service (arranque en frío)

Sin km previo no hay tasa individual. Tabla f4 (cohorte 2024, ancla WSD, 21.283 ventanas):

| regla | due (d, mediana) | p10 | p50 | p90 | % capturado H = 120 | % churn abiertas H = 120 |
|---|---|---|---|---|---|---|
| solo tiempo (365 d) | 365 | −239 | −99 | 37 | 97,0 | 46,4 |
| K = 15.000, tasa poblacional P703 | 230 | −104 | 36 | 172 | 71,8 | 55,8 |
| K = 15.000, tasa por segmento BU × PersonType | 237 | −94 | 45 | 185 | 74,1 | 51,6 |
| K = 10.000, tasa poblacional P703 | 154 | −28 | 112 | 248 | 51,7 | 62,9 |

Ninguna regla centra bien sin km (p10-p90 de ~280 días). La tasa por segmento (Ford Pro J 32.347 vs Ford Blue F 22.330 km/año,
tabla f4a) mejora poco. Para la primera ventana conviene anclar en tiempo (due = WSD + 270-300 d, entre la mediana de 9,2 meses
y el año nominal) o, mejor, usar km de telemetría para los vehículos `Conectado` (pregunta 4 al mentor).

### 6.4 Parámetros recomendados y alternativas descartadas

| parámetro | recomendación | justificación numérica | alternativa descartada y por qué |
|---|---|---|---|
| K (km del ciclo) | **15.000 P703 / 10.000 P375** (nominal por generación) | Δkm mediana 16.138 / 10.330; km/n = 16.0-16.2k / 10.1-10.3k; retraso mediano +7 d | K = 15.000 para todos: retraso mediano −33 d y 51,6 % de retornos antes de due − 30 (P375 ya atendido al abrir). K = 10.000 para todos: el due de los P703 cae a 2/3 del ciclo real (retraso mediano global +20 d, p90 +155 d, 92,6 % capturado recién a due + 180). Usar el Δkm empírico (16.138) en vez del nominal: corre el due 1.138 km, unos 17 días a la tasa mediana P703 de 23.790 km/año; no cambia la conclusión. |
| ciclo en días (tope) | **365** | manda solo en 8,8 % de ventanas (11,3 % P703); 9,5 % de los retornos en 18 m tarda > 365 d (7,9 % en los pares ingenuos, censurados); pico secundario en 365 d | sin tope: deja sin due a los de bajo uso (p10 de tasa 9.924 km/año → 15.000 km tarda 1,5 años). Un tope menor (p. ej. 270 d) no se evaluó; el pico en 365 d de la figura `hist_intervalos` indica que hay clientes que siguen la regla anual exacta y un tope menor los marcaría como tardíos. |
| tasa de uso | **acumulada: km al ancla / edad al ancla** | disponible en 95,9 % de ventanas; concordancia con pendiente entre visitas Spearman 0,895 | tasa reciente: comparada sin diluir en las 32.323 ventanas donde existe (tabla f7): mediana de \|retraso\| 31 vs 30 d, 49,1 % vs 49,5 % dentro de ±30 d, p10/p50/p90 −43/+13/+117 vs −55/+6/+107; no mejora, y solo existe en el 37,4 % de las ventanas. (En f1, sobre todas las ventanas con fallback, −80/+10/+132 vs −85/+7/+129.) Tasa poblacional: solo como fallback (4,1 %) y para el 1° service. |
| apertura | **due − 30 d** | 80,4 % de ventanas abiertas; 24,3 % de retornos ocurren antes (clientes que no necesitan contacto) | due − 60: 88,3 % abiertas, 14,5 % antes, churn 36,2 % (H = 90); mejora la cobertura a costa de una ventana de 150 d, más lejos del "próximo mes" del tutor. Elegir según el lead time de contacto del dealer (pregunta 2). due: 44,2 % ya vino, prevalencia 49,7 %: abre tarde. |
| horizonte de resultado | **due + 90 d** (sensibilidad: + 120) | captura 84,3 % de los retornos en 18 m (88,9 % con 120); prevalencia de churn entre abiertas 39,7 % (35,1 % con 120); P703 31,6 % / P375 42,4 % | due + 60: 77,1 % capturado, 46,9 % churn (muchos "tardíos" etiquetados churn). due + 180: 94,5 % capturado pero ventana de 210 d y prevalencia 29,5 %: el resultado se conoce demasiado tarde para actuar. |
| regla solo tiempo (365 d) | **descartada** | retraso mediano −200 d; 85,9 % de retornos antes de due − 30; solo 30,7 % de ventanas abiertas y 87,7 % de churn entre ellas a H = 0 | es la regla que se lee en la ficha ("1 año") pero no describe a un parque que hace 21.514 km/año de mediana. |

Con estos parámetros la **unidad usuario-vehículo-ventana** queda: ancla = último mantenimiento completado (o WSD para la
primera), `due` según la fila 1-3, scoring en `due − 30`, target = 1 si no hay mantenimiento completado en la red entre la
apertura y `due + 90`. La ventana total dura 120 días, compatible con la lectura "¿va a faltar al service que le toca en los
próximos meses?" del tutor. Si el negocio necesita estrictamente "el próximo mes", la alternativa es scoring mensual sobre las
ventanas abiertas con target "no vuelve en los próximos 30 días", que es un re-corte del mismo dato, no otra definición.

---

## 7. Estacionalidad (punto g)

**Tabla g2 — índice por mes del año (media = 100):**

| mes | ene | feb | mar | abr | may | jun | jul | ago | sep | oct | nov | dic |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| crudo (2024 y 2025, media anual = 100) | 104,1 | 91,4 | 90,7 | 94,9 | 97,6 | 85,2 | 105,1 | 104,8 | 104,4 | 111,4 | 101,7 | 108,7 |
| crudo por día hábil | 98,7 | 97,3 | 94,1 | 94,1 | 94,6 | 90,5 | 99,6 | 106,2 | 106,0 | 105,6 | 108,1 | 105,3 |
| **sin tendencia** (regresión log(n / día hábil) = tendencia + mes, 2024-01→2026-07) | **108,8** | 100,9 | 100,9 | 97,5 | 95,9 | **90,6** | 95,0 | 105,0 | 103,3 | 101,7 | 102,8 | 99,0 |

- **El índice crudo está contaminado por la tendencia:** el volumen por día hábil crece 1,26 % mensual (≈ 16 % anual), así que
  "media anual = 100" infla julio-diciembre y deprime enero-junio. El patrón "segundo semestre alto" de las dos primeras filas es
  sobre todo tendencia, no estacionalidad. Hay que leer la tercera fila.
- **Junio es el mes bajo (90,6)** y lo es todos los años (86 / 97 / 89 respecto de la tendencia en 2024 / 2025 / 2026). **Enero es
  el mes alto (108,8)**, también todos los años (104 / 109 / 114): no hay caída por vacaciones, hay un pico (en 2026-01 se hizo el
  máximo de la serie, 8.936). Octubre (101,7), julio (95,0) y diciembre (99,0) no se distinguen una vez removida la tendencia: el
  "octubre alto" del índice crudo era tendencia. El rango total (91-109) es moderado.
- Tabla g1 y figura `estacionalidad`: el volumen mensual total sube de 6.331 (2024-01) a 7.647 (2026-07) con máximo 8.936
  (2026-01). Por generación, P375 baja de 5.856 a 2.009 mensuales (−66 %) y P703 sube de 437 a 5.625: el parque que va a la red
  se está renovando y **la composición de la población de ventanas cambia mes a mes**. Esto pesa más que la estacionalidad para la
  validación temporal.

---

## 8. Implicancias para target, ventana y features

1. **Target/ventana:** definir el due con K por generación y tasa individual; abrir en due − 30 y cerrar en due + 90. Reportar la
   prevalencia por generación (31,6 % vs 42,4 %) y por tercil de uso (el churn a 18 m va de 12,4 % en uso alto a 32,0 % en bajo).
2. **Población:** las ventanas se anclan solo en mantenimientos completados en la red; los vehículos con un único service en el
   extracto (36,3 %) generan una sola ventana. Con 86.484 ventanas totalmente observadas (anclas hasta 2025-02) hay masa
   suficiente para backtesting temporal, pero la mezcla P375/P703 se invierte a lo largo del período: estratificar o reportar
   por generación.
3. **Features de cadencia (todas calculables al ancla, sin leakage):** `km_evento` (con la limpieza de la sección 1),
   `tasa_uso` acumulada, `K_gen`, `dias_hasta_due`, `n_service` (`ServiceMaintenance`, no `ServiceName`), `salto_numeracion`
   (≥ +2 en el 12,6 % de los pares, pero solo la mitad es un service hecho afuera; mejor `intervalo_doble_km` = Δkm anterior ≥
   1,5·K_gen: 7,9 % P703 / 18,5 % P375), `retraso_km_anterior` (km del ancla − K·n: cuánto tarde llegó la última vez; mediana
   +1.000 km en P703), `retraso_dias_anterior` (cuánto tardó el service anterior respecto de su due: en la cohorte 2024 el retorno
   al 2° en 12 m va de 91 % si el 1° fue a ≤ 4 meses a 47 % si fue a 12-15, tabla e4), `intervalo_anterior_dias`, `edad_meses`,
   `es_primer_service`.
4. **Nunca usar `KM`** (snapshot) ni `VehicleCurrentKM` de eventos posteriores al ancla. Tampoco `ServiceMonth` (= 12·n, es
   nominal, no observado).
5. **Primer service:** ventana aparte con due por tiempo (WSD + 270-300 d) o con km de telemetría; es donde está el mayor
   churn (a 12 meses falta el 35,5 % vs 24,6 % del 1° al 2°; el 8,5 % a 18 meses del 1° al 2° está sesgado por selección, tabla e4).
6. **Estacionalidad:** incluir mes del año como feature de bajo peso (con la tendencia removida: junio −9 %, enero +9 %; octubre
   no se distingue); no justifica ajustar el horizonte. Para la validación temporal, la tendencia (+16 % anual por día hábil) y el
   recambio P375 → P703 pesan más que el mes.

---

## 9. Problemas de calidad de datos detectados

| # | problema | magnitud | tratamiento propuesto |
|---|---|---|---|
| 1 | `KM` es un snapshot por vehículo, no el km del turno | constante en 99,99 % de vehículos; = última lectura en 91,7 % | no usar como feature de evento; documentar en el diccionario |
| 2 | `VehicleCurrentKM` inválido | 3.728 lecturas < 100 (2.582 = 1), 66 > 1.000.000, 321 > 500.000 | nulo + imputación por tasa de uso |
| 3 | Odómetro no monotónico entre visitas | 1,8 % decrece, 3,0 % repetido, 503 saltos > 100.000 km | nulo el valor inconsistente; colapsar visitas partidas |
| 4 | Misma visita en varios `schedule_id` | 1.033 filas colapsadas por vehículo + fecha; 738 pares a < 30 d con km ≤ anterior | dedupe por vehículo-día (hecho) y por < 30 d con km ≤ anterior (a decidir en el tema de eventos) |
| 5 | Check-in nulo en turnos concluidos | 13,3 % de (60) Concluido | `event_date` cae a `ScheduleDate` (la diferencia check-in − turno es 0 en la gran mayoría) |
| 6 | Numeración de service inconsistente | 5,1 % repite el número, 4,6 % retrocede (2,1 % más de 3), 12,6 % salta ≥ +2 (7,4 % +2, 2,0 % +3, 1,0 % +4, 0,5 % +5, 1,7 % más de +5); solo ~la mitad de los saltos +2 tiene Δkm de intervalo doble (b5); el valor 20 es tope | usar `ServiceMaintenance` como está; medir el intervalo doble por km (Δkm ≥ 1,5·K) y no solo por salto; no reconstruir |
| 7 | `ServiceName` con bug de etiqueta (11 → "1°", 12 → "2°", 14 → "4°", 16-19 → "6°"-"9°") | 100 % de los ítems con `ServiceMaintenance` 11, 12, 14, 16-19; 20-22 % de los de 13 y 15 | ignorar `ServiceName` para el número de service |
| 8 | Edad negativa (evento antes del WSD) | 82 eventos en M; 7 en la cohorte 2024 | excluir de tasas y ventanas |
| 9 | WSD nulo | 464 vehículos con mantenimiento; 1.339 eventos en M | fallback a sales (hecho); sin WSD no hay tasa acumulada → fallback poblacional |
| 10 | Intervalos truncados en cohortes jóvenes | MY 2025-2026 mediana 140 d vs 189 d en MY 2024 | no comparar intervalos entre cohortes sin controlar seguimiento |

Coherencias verificadas: `WarrantyStartDate` es único por vehículo en agenda (0 vehículos con más de un valor) y coincide con
sales en el 99,0 % (0,06 % difiere en más de 30 días) (tabla c5).

---

## 10. Preguntas para el mentor

1. **Plan oficial por generación:** ¿confirma que el plan es 15.000 km / 1 año para Ranger P703 y 10.000 km / 1 año para P375?
   Los datos lo muestran con claridad, pero conviene tenerlo por escrito para la presentación (y saber si Raptor difiere).
2. **Lead time de contacto:** ¿cuántos días antes del due necesita el concesionario/marketing para que el contacto sirva? Eso
   decide entre apertura en due − 30 (80 % de ventanas abiertas, ventana de 120 d) y due − 60 (88 %, 150 d).
3. **Horizonte "próximo mes":** ¿el negocio quiere un score por ventana (target a due + 90) o un score mensual sobre ventanas
   abiertas ("no vuelve en 30 días")? Ambos salen del mismo dato; cambia la prevalencia y la métrica.
4. **Km de telemetría:** para los vehículos `ConnectedStatusARG = Conectado`, ¿existe el odómetro actual fuera de la agenda? Sería
   la única forma de individualizar el due de la primera ventana (hoy p10-p90 del retraso ≈ 280 días) y de detectar ventanas
   abiertas sin depender de la última visita.
5. **Semántica de `KM`:** ¿es el último km registrado en la ficha del vehículo a la fecha de extracción? ¿Se alimenta también de
   fuentes distintas de la agenda (garantía, telemetría)? Eso explicaría el 8,3 % de vehículos donde no coincide con la última
   visita.
6. **Services fuera de la red:** el 12,6 % de los pares consecutivos salta ≥ 2 números de service, pero solo la mitad de esos
   saltos tiene un Δkm compatible con un service intermedio; medido por km hay intervalos dobles en el 7,9 % de los pares P703 y
   el 18,5 % de P375 (tabla b5). ¿Ford considera "churn" un service hecho en un taller independiente que luego vuelve, o solo la
   ausencia de retorno? ¿La numeración la carga el dealer a mano (explicaría el 4,6 % de saltos negativos)?
7. **Primer service en la cohorte 2024:** el 11,5 % de los primeros eventos observados no están numerados como 1° (9,0 % figuran
   como 2°, 2,5 % como 3° o más). ¿Puede ser que el 1° service se registre con otro estado (por ejemplo `(90) Concluido sin OS`,
   sin cargo) y quede fuera de `is_completed_maintenance`, o que el dealer numere mal? Impacta en el target de la primera ventana.
8. **Tope 20 en `ServiceMaintenance`:** ¿es "20 o más" o hay un plan que termina ahí?

---

## Anexo — figuras generadas

| archivo | contenido |
|---|---|
| `02_cadencia_ventana_km_vs_vehiclecurrentkm.png` | nulos por estado; distribución de KM − VehicleCurrentKM de la última visita |
| `02_cadencia_ventana_tasa_uso.png` | histograma de la tasa de uso por método y terciles; dispersión A vs B |
| `02_cadencia_ventana_hist_intervalos.png` | histogramas de días y km entre mantenimientos consecutivos, por generación |
| `02_cadencia_ventana_box_km_por_service.png` | boxplots de km al evento por n° de service (1..10), P703 y P375, con rectas 10.000·n y 15.000·n |
| `02_cadencia_ventana_box_edad_por_service.png` | boxplots de edad (meses) por n° de service, con la recta 12·n |
| `02_cadencia_ventana_cohorte2024_curvas.png` | curvas acumuladas WSD → 1° y 1° → 2° mantenimiento |
| `02_cadencia_ventana_ventana_retraso_sensibilidad.png` | ECDF del retraso por regla; % capturado y % churn vs horizonte |
| `02_cadencia_ventana_estacionalidad.png` | volumen mensual por generación; índice estacional crudo, por día hábil y sin tendencia (regresión) |
