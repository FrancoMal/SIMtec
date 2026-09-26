# Verificación independiente del EDA 02 — Cadencia de mantenimiento y parámetros empíricos de la ventana

Rol: verificador escéptico. Objetivo: intentar refutar las afirmaciones clave de `reports/eda/02_cadencia_ventana.md`
recalculándolas con código propio (`scripts/eda/02_cadencia_ventana_verificacion.py`, tablas V0-V10 en
`reports/eda/02_cadencia_ventana_verificacion_tablas.md`, figura `reports/figures/eda/02_cadencia_ventana_verif_estacionalidad_detrended.png`).
Cuando encontré un error o una salvedad importante, corregí directamente el script y el informe originales (sección 3).

Método: reconstruí desde cero la base M (mantenimientos completados, una fila por vehículo-día), los pares consecutivos, las
ventanas con 18 meses de seguimiento, la cohorte 2024 y el índice estacional, buscando los errores típicos: joins que duplican,
ítem vs turno, censura por la derecha, selección por seguimiento, comparaciones diluidas, índices contaminados por tendencia,
denominadores equivocados, promedios dominados por outliers.

## 1. Sanidad de la base

| chequeo | resultado |
|---|---|
| `vehicle_id` único en sales (los joins de M con sales no duplican) | 59.384 filas = 59.384 vehículos: OK (V0) |
| `schedule_id` único en appointments | 492.442 = 492.442: OK |
| Base M reconstruida | 222.889 completados → 221.856 eventos (1.033 vehículo-día repetidos), 87.531 vehículos, 218.149 con km válido: idéntico a m0 |
| Todos los números citados en el informe existen en las tablas del script | Sí, con una excepción: el "76,1 %" de etiqueta 1° service (ver afirmación 6) estaba calculado con el denominador equivocado |

## 2. Veredictos por afirmación

| # | afirmación | veredicto | número original | número recalculado | nota |
|---|---|---|---|---|---|
| 1 | Regla por km y por generación: P703 15.000, P375 10.000; 12·n meses no describe los datos | **confirmada** (con salvedad) | km/n 16.040-16.173 (P703) / 10.125-10.330 (P375); Δkm n→n+1 16.138 / 10.330; 59,0 % de 1° services MY≥2024 en (15k, 18k]; "10° service a 25,0 meses = 2,5 meses/service" | Idénticos: km/n 16.040-16.173 y 10.125-10.330; Δkm 16.138 (p25-p75 14.726-17.639) / 10.330 (9.460-11.724); 59,0 % (V1a-V1c) | La salvedad: la "edad al 10° service = 25 meses" para P703 es un artefacto de truncamiento, no una cadencia. El p1 de WSD de P703 es 2023-07-26, ningún P703 supera ~37 meses al CUTOFF, y los 169 vehículos con n = 10 tienen tasa mediana 66.170 km/año. La evidencia limpia contra 12·n es el 1° service a 8,4 meses (26 % pasados los 11,5) y Δdías n→n+1 = 177 (P703) / 151 (P375). Corregido en el informe. |
| 2 | El tope anual casi no opera: mediana 161 d, 7,9 % de intervalos > 365 d, tope manda en 8,8 % | **ajustada** | mediana 161 (P703 174, P375 153); 7,9 % > 365 d; tope 8,8 % (P703 11,3 %); terciles 120 / 316 | Los pares "ingenuos" están censurados por la derecha (un par solo existe si el siguiente service ya ocurrió). Con 18 m de seguimiento garantizado (86.484 anclas): mediana entre retornos 165 d (P703 195, P375 154), 9,5 % de los retornos > 365 d (10,5 % con 24 m), 19,2 % sin retorno en 18 m, mediana incondicional 202 d (V2a, V2b, V10a). Tope 8,8 % confirmado. Terciles con seguimiento: 113 / 197 / 321 d (retornos), 125 / 223 / 374 incondicional; en uso bajo el 31,5 % de los retornos supera 365 d | La conclusión ("manda el km") se sostiene, pero 161 d y 7,9 % subestiman los intervalos largos, que son justamente el target. Agregada tabla a4 al script y párrafo en el informe. El "pico secundario en 365 d" existe pero está en 350-370 d (P703: 2.329 pares en 355-375 vs 1.704 en 335-355 y 1.109 en 375-395). |
| 3 | `KM` es snapshot por vehículo; el km del evento es `VehicleCurrentKM`; usar `KM` a nivel evento es leakage | **confirmada** | 99,99 % constante; = última lectura 91,7 %; = máximo 84,4 %; VCK 0 % nulo en (60), 100 % en (70), 71,9 % en (80) | Idénticos, también a nivel ítem en la agenda cruda (111.745 / 111.752). Detalle de los 8.819 vehículos (8,3 %) donde `KM` ≠ última lectura: 4.607 `KM` nulo, 475 última lectura inválida, 520 `KM` > última (dato más nuevo), 3.692 `KM` < última; 94,4 % de los vehículos tiene `KM` igual a alguna de sus lecturas (V3a, V3b) | Agregado el desglose al informe. Hallazgo colateral: el EDA 03 calcula "km/año implícito" como `KM` (snapshot) / edad al evento y obtiene 34.080 km/año; es un odómetro futuro sobre una edad pasada y está inflado (21.514 con `VehicleCurrentKM`; 16.596 con `KM` / edad al CUTOFF, subestimado por snapshots viejos). Señalado en el informe 02, sección 1; no toqué el 03. |
| 4 | La tasa individual se estima bien con una visita; la tasa reciente no agrega precisión | **confirmada** (evidencia reemplazada) | A: 86.022 veh., mediana 21.514 (p25 14.616, p75 31.307); B: 52.838; Spearman 0,895; B/A 1,001; 78,5 % ±25 %; reciente −80/+10/+132 vs −85/+7/+129; disponible 37,4 %; Ford Pro 28.312 vs Blue 23.390; J 28.406 vs F 22.455 | A/B, Spearman, B/A, 78,5 % y segmentos: idénticos (V4a, V4b). La comparación de f1 estaba **diluida** (la reciente cae a la acumulada en el 62,6 % de las ventanas). Sin diluir, en las 32.323 ventanas con tasa reciente: mediana de \|retraso\| 30 (acumulada) vs 31 (reciente); 49,5 % vs 49,1 % dentro de ±30 d; p10/p50/p90 −55/+6/+107 vs −43/+13/+117; el promedio de ambas 28 d y 51,8 % (V4c, f7) | La conclusión se sostiene con la comparación correcta; la original no podía haber detectado una mejora aunque existiera. Agregada tabla f7 al script; texto del informe reemplazado. |
| 5 | Ventana due = ancla + min(365, K_gen/tasa×365,25), apertura −30, horizonte +90; churn entre abiertas 39,7 % (P703 31,6, P375 42,4) | **confirmada** (con salvedad de mezcla) | 86.484 ventanas; 80,8 % vuelve; retraso −85/−28/+7/+54/+129; 80,4 % abiertas; 24,3 % antes; 84,3 % capturado (+90), 88,9 (+120), 77,1 (+60); churn 39,7 / 35,1 / 46,9; 31,9 = 19,2 + 12,7 | Todos idénticos al decimal (V5a, V5b). Sensibilidad: excluir "retornos" a < 30 d del ancla (846, 1,0 %) → 39,8 %. Por año del ancla: P375 41,9 % (2024) / 46,3 % (2025, solo ene-feb), P703 31,3 / 32,6 (V5c, V5d) | La salvedad: las ventanas evaluadas son 74,6 % P375 (anclas 2024-01→2025-02) y la población de 2026 es 69,6 % P703; reponderando por generación la prevalencia esperada hoy es 34,8 %, no 39,7 % (V10b, f8). Agregado al script y al informe. |
| 6 | El mayor riesgo de churn está en la primera ventana; no se puede individualizar sin km previo | **ajustada** | 64,5 % en 12 m, 80,9 % en 18, 86,0 % al cutoff; mediana 9,2 m y 16.172 km; 1°→2° 75,4 % (12 m) y 91,5 % (18 m); "19 % no vuelve vs 8,5 % del 1° al 2°"; etiqueta 1° en 76,1 %; arranque en frío −104/+36/+172 | Cohorte y arranque en frío: idénticos (V6a, V10c). **Dos problemas.** (a) El 91,5 % a 18 m está sesgado por selección: solo tienen 18 m de seguimiento los que hicieron el 1° temprano (t1 mediana 5,8 m vs 9,2), y el retorno al 2° en 12 m va de 91,5 % (1° a ≤ 4 m) a 46,8 % (1° a 12-15 m) (V6b). La comparación limpia es a 12 m: 35,5 % sin 1° vs 24,6 % sin 2°. (b) El "76,1 %" de primeros eventos etiquetados 1° usa como denominador toda la cohorte (incluidos los 2.973 sin evento); sobre los 18.317 con evento es 88,5 % (9,0 % como 2°, 2,5 % como 3° o más) (V10e) | La afirmación principal se sostiene (la primera ventana es la de mayor churn), pero con la magnitud correcta. Además surge una feature fuerte: el retraso del service anterior. Corregidos script (denominador; tablas e2 nota, e4) e informe (secciones 5, 8, 10). |
| 7 | El intervalo en km no depende del segmento, el de días sí | **confirmada** | km: Blue 16.231 vs Pro 16.058; F 16.181 vs J 16.166. Días: Blue 176 vs Pro 130; F 183 vs J 140 | Controlando generación (solo P703) y numeración consecutiva: Δkm Blue 16.198 vs Pro 16.045; F 16.149 vs J 16.139. Δdías Blue 177 vs Pro 134; F 183 vs J 144 (V7) | Sin cambios. Los intervalos en días siguen censurados (afirmación 2), pero la comparación entre segmentos no cambia de signo. |
| 8 | Estacionalidad moderada: junio bajo, octubre alto, enero sin caída | **refutada en parte / ajustada** | crudo: junio 85,2 (90,5 por día hábil), octubre 111,4, enero 104,1 (98,7 por día hábil) | El índice "media anual = 100" está contaminado por una tendencia de +1,26 % mensual por día hábil (≈ 16 % anual): infla jul-dic y deprime ene-jun. Regresión log(n / día hábil) = tendencia + mes (2024-01→2026-07): junio 90,6 (bajo los tres años: 86 / 97 / 89 vs tendencia), **enero 108,8 (el mes más alto, alto los tres años: 104 / 109 / 114)**, octubre 101,7, julio 95,0, diciembre 99,0. Ratio a media móvil 2×12: enero 113,2, junio 91,9, octubre 105,6 (V8a, V8b) | Junio bajo: confirmado. Octubre alto: refutado (era tendencia). Enero: no es "sin caída", es el pico del año. Magnitud moderada (91-109): confirmada. La composición del parque (P375 5.856 → 2.009, P703 437 → 5.625) pesa más: confirmada. Agregada la fila "sin tendencia" a g2, la figura y el texto del informe. |
| 9 | ~10 % de intervalos son "dobles" (service intermedio fuera de la red); numeración ruidosa | **ajustada** | +1 77,7 %, +2 7,4 %, +3 2,0 %, +4 1,0 %, +5 0,5 %, 0 5,1 %, negativo 2,5 %; 20 concentra 3.494 vs 1.068 en 19; ServiceName dice "1°" con ServiceMaintenance 11 | Distribución completa: negativo 4,6 % (el original solo sumaba −1..−3; hay 2,1 % por debajo de −3), ≥ +2 12,6 % (1,7 % por encima de +5) (V9a). **El salto +2 es un intervalo doble solo la mitad de las veces:** Δkm mediana 1,65·K (P703) / 1,62·K (P375), 46 % en [1,5K, 2,5K] (V9b). Medido por km (Δkm ≥ 1,5·K): 7,9 % de los pares P703 y 18,5 % de P375; el 4,2 % / 10,7 % de los pares con salto +1 también son dobles por km (V10d). ServiceName: 100 % mal en 11, 12, 14, 16-19; 20-22 % mal en 13 y 15 (V9c). Tope 20: 3.494 vs 1.068, km mediano 222.285 vs 192.067 (V9d) | El "~10 %" es correcto como orden de magnitud por km (7,9 % P703 / 18,5 % P375), pero atribuirlo al salto de numeración es incorrecto: la mitad de los saltos es ruido y una parte de los dobles reales tiene salto +1. La feature útil es Δkm ≥ 1,5·K, no el salto. Agregada tabla b5, corregidos b4, informe (secciones 2, 3, 8, 9, 10). |

## 3. Correcciones aplicadas

Script `scripts/eda/02_cadencia_ventana.py` (sigue corriendo de punta a punta, ~28 s; regenera tablas y figuras):

1. **e1 (nota):** el "% del 1° evento numerado como 1° service" se calculaba sobre toda la cohorte (`(coh.first_n == 1).mean()`,
   con los sin evento contando como no); ahora sobre los que tienen evento (88,5 %), con el desglose 2° (9,0 %) / ≥ 3° (2,5 %).
2. **a4 (nueva):** días entre mantenimientos con 18 meses de seguimiento garantizado (corrige la censura de a1): % que retorna,
   mediana entre retornos, % > 365 d, mediana incondicional; global, por generación y por tercil de uso.
3. **b1 (nota):** advertencia de truncamiento de `meses/n` para P703 (edad máxima ~37 meses; n = 10 → 66.170 km/año).
4. **b4:** distribución completa del salto (filas "< −3", "> 5", "negativo (total)", "≥ +2 (total)"). **b5 (nueva):** Δkm por
   salto y "intervalo doble por km" (Δkm ≥ 1,5·K_gen).
5. **e2 (nota) y e4 (nueva):** sesgo de selección en 1° → 2°; retorno al 2° (12 m) según cuánto tardó el 1°.
6. **f7 (nueva):** tasa reciente vs acumulada comparadas solo en las ventanas donde la reciente existe (no diluida).
7. **f8 (nueva):** prevalencia de churn entre abiertas reponderada a la mezcla P703/P375 de 2026.
8. **g2:** columna "índice sin tendencia" (regresión log(n / día hábil) = tendencia lineal + efecto mes, 31 meses completos) y
   residuos por año; la figura `estacionalidad` muestra las tres versiones del índice.
9. **r1:** agrega el % > 365 d con seguimiento garantizado, el % sin retorno en 18 m y la mediana incondicional.
10. Corrección técnica: la columna auxiliar de tercil en M se llama `tercil_uso_veh` para no chocar con el join de f5.

Informe `reports/eda/02_cadencia_ventana.md`:

- Encabezado: referencia a esta verificación.
- Resumen ejecutivo 1, 2, 5, 6, 7 y 8 reescritos con los números corregidos (truncamiento, censura, selección, tasa reciente
  no diluida, prevalencia reponderada, estacionalidad sin tendencia).
- Sección 1: desglose de los vehículos donde `KM` ≠ última lectura; nota de coherencia sobre el 34.080 km/año del EDA 03.
- Sección 2: bullet de censura (tabla a4); bullet de intervalos dobles reescrito con b5.
- Sección 3: bullet "12·n meses" reescrito; nota de `maint_number` con la distribución completa del salto y el detalle del bug
  de `ServiceName` (11, 12, 14, 16-19 al 100 %; 13 y 15 al 20-22 %).
- Sección 5: 76,1 % → 88,5 %; párrafo de sesgo de selección; lectura con la comparación a 12 meses.
- Sección 6: nota de dilución en f1; prevalencia reponderada (f8) y sensibilidad a retornos < 30 d; fila "tasa de uso" y fila
  "tope" de la tabla 6.4 con los números correctos.
- Sección 7: tabla g2 con la fila "sin tendencia" y bullets reescritos (junio bajo, enero alto, octubre no se distingue).
- Sección 8: features `intervalo_doble_km` y `retraso_dias_anterior`; ítems 5 y 6 corregidos.
- Sección 9: ítems 6 y 7 con las magnitudes correctas. Sección 10: preguntas 6 y 7 corregidas.

## 4. Lo que NO cambié y por qué

- La definición de `is_completed_maintenance`, `event_date` y CUTOFF (tema de eventos): las usé tal cual y reproducen todo.
- La regla recomendada (K por generación, tasa acumulada, apertura −30, horizonte +90): los números que la sostienen
  reproducen al decimal y las sensibilidades que agregué (retornos < 30 d, año del ancla, subconjunto con tasa reciente) no la
  mueven. Sí conviene presentar la prevalencia por generación y reponderada (34,8 %), no el 39,7 % a secas.
- El EDA 03 (34.080 km/año con `KM` snapshot / edad al evento): lo señalo como inconsistencia entre informes, no es mi tema.

## 5. Preguntas abiertas que dejó la verificación

1. El 3,5 % de vehículos con `KM` snapshot menor que su última lectura de `VehicleCurrentKM`: ¿otra fuente (garantía,
   telemetría) o error de carga? Refuerza la pregunta 5 al mentor.
2. Enero es el mes de mayor volumen (108,8 sin tendencia; 8.936 mantenimientos en 2026-01, máximo de la serie). ¿Campaña
   de verano / pre-vacaciones? Cambia la lectura de "no hay efecto vacaciones".
3. El 4,6 % de saltos negativos de numeración y el 50 % de saltos +2 sin Δkm compatible sugieren carga manual del número de
   service por el dealer. ¿Es así? Define si `ServiceMaintenance` sirve como feature o solo como aproximación.
