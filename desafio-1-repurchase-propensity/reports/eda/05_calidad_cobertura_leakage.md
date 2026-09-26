# EDA 05 — Calidad de datos, cobertura temporal y riesgos de leakage

**Desafío:** Repurchase Propensity (churn de mantenimiento programado, Ranger Argentina).
**Datos:** `data/interim/sales.parquet` (59.384 ventas) y `data/interim/agenda.parquet` (631.623 filas-ítem → 492.442 turnos vía `repurchase.eventos.appointments()`), CUTOFF = 2026-08-25.
**Reproducibilidad:** todo número citado acá sale de `scripts/eda/05_calidad_cobertura_leakage.py`, que escribe las tablas completas en `reports/eda/05_calidad_cobertura_leakage_salida.md` y las figuras en `reports/figures/eda/05_calidad_cobertura_leakage_*.png`. Las letras entre paréntesis (A1, B3, …) referencian las tablas de ese archivo de salida.
**Verificación:** las afirmaciones clave fueron recalculadas de forma independiente en `scripts/eda/05_calidad_cobertura_leakage_verificacion.py`; los veredictos y las correcciones aplicadas están en `reports/eda/05_calidad_cobertura_leakage_verificacion.md`.

---

## Resumen ejecutivo

1. **`KM` es un atributo del vehículo a la fecha de extracción (su última lectura conocida), no la lectura del turno.** Es constante dentro del vehículo en el 100 % de los vehículos con ≥2 lecturas (7 de 82.347 varían) y coincide con `VehicleCurrentKM` del *último* turno concluido en el 95,5 % de los vehículos con ambos valores (91,7 % si el denominador incluye a los que tienen `KM` nulo; B3). Usarlo como feature en backtest es leakage directo (revela cuánto se usó el vehículo *después* de la fecha de scoring). La lectura por visita es `VehicleCurrentKM`, que varía en el 97,5 % de los vehículos y sólo existe cuando el auto entró al taller.
2. **`ConnectedStatusARG` también es una foto**: constante en el 99,9 % de los vehículos, y la categoría "Sin Información de Conectividad" crece con la fecha de entrega (2,9 % en 2024Q2 → 92,6 % en 2026Q3, B2). No sirve para backtest; como mucho, feature estática con advertencia en el scoring actual.
3. **`SurveyResponseDate` es siempre anterior al turno** (mediana 8 días antes de `ScheduleDate`, nunca después del checkout; C1) y aparece en turnos cancelados y no asistidos. No califica el servicio recibido: es una calificación al momento de reservar por canal digital (FordPass 29,1 %, Mobile 30,9 %, WEB 18,0 %; Dealer 0 %). Es temporalmente segura si `SurveyResponseDate < t`, pero su semántica es otra, y de paso es el único proxy de *fecha de reserva* que existe (7,5 % de los turnos).
4. **Left-censoring fuerte:** el 59,8 % de los vehículos de la agenda (60,5 % de los que tienen `WarrantyStartDate`) fue entregado antes de 2024-01-01 (historia previa invisible). A 6 meses de historia (t = 2024-07-01) el 33,4 % de los vehículos activos no tiene ningún mantenimiento observado y "días desde el último mantenimiento" no puede superar 182 (A1). Sobre una misma población (activos en los 182 días previos al CUTOFF), 6 meses de historia etiquetan "sin mantenimiento" al 25,6 % contra 11,2 % con 32 meses: **+14,4 puntos de truncamiento puro; con 12 meses quedan +4,9 pp, con 18 meses +2,0 pp, con 24 meses +0,8 pp** (A5). `maint_number` del último service recupera buena parte de esa historia (correlación 0,76 con la edad; falsos positivos 5–11 %; A4, A4b).
5. **"Tener turno agendado" no es reconstruible hacia atrás:** no hay fecha de creación del turno. Las 3.826 reservas con `ScheduleDate > CUTOFF` (3.321 (30) Agendado) sólo existen para el scoring actual (D1). En backtest, cualquier turno con `ScheduleDate ≥ t` debe quedar fuera de las features.
6. **`IsReschedule` en turnos cancelados codifica el re-agendamiento, una acción cuya fecha no está en los datos:** con Y, el 71,9 % tiene otro turno dentro de 30 días (53,2 % dentro de 7) contra 44,5 % / 27,7 % con N, y en el 65,3 % el turno siguiente también lleva Y (D2). En filas canceladas el flag es colineal con `ScheduleStatus` (Y ⇔ nulo, N ⇔ "(70) Cancelado"). Como el re-agendamiento suele hacerse *antes* de la fecha original del turno, el flag no es necesariamente posterior a t, pero puede revelar una reserva creada después de t; por eso se lo trata de forma conservadora.
7. **Más de la mitad de las cancelaciones son re-agendamientos (del dealer o del cliente)**, no abandono: el 54,1 % tiene un turno concluido del mismo vehículo a ≤7 días, el 16,9 % el mismo día (G2). Una feature "n cancelaciones" sin esta limpieza mide otra cosa.
8. Inconsistencias puntuales acotadas (E1): 4 check-in con fecha imposible (ya neutralizados por la regla ±45 días de `eventos.py`), 10.076 lecturas `VehicleCurrentKM < 100` (placeholders), 5.058 pares de visitas con odómetro que retrocede >1.000 km una vez excluidos los placeholders (6.948 sin excluirlos), 3 ventas con `DeliveryDate` de 2013/2015, 107 ventas con `Status ≠ ACCEPTED`, 1 "GLOBAL RANGER". `ServicePriceDiscount` no es un descuento (mediana 29,8 M, crece trimestre a trimestre como la inflación; los ceros son ítems de precio fijo Ford / campañas; E5) y `ServiceLaborCost` está vacío al 99,3 %.

---

## A. Left-censoring: la agenda arranca el 2024-01-01 pero el parque no

### Hallazgo 1 — Seis de cada diez vehículos tienen historia invisible

De los 111.752 vehículos con id en la agenda, 110.495 tienen `WarrantyStartDate`; **66.795 fueron entregados antes del 2024-01-01 (59,8 % de todos los vehículos con id; 60,5 % de los que tienen WSD)** y 46.629 (41,7 % de todos) antes del 2023-01-01. Para todos ellos, cualquier conteo de "mantenimientos previos" empieza en cero por construcción del extracto, no porque el cliente no haya ido.

### Hallazgo 2 — Cómo cambia lo observable según la fecha de scoring (A1)

| | 2024-07-01 | 2025-01-01 | 2025-07-01 | 2026-01-01 | 2026-08-25 |
|:--|--:|--:|--:|--:|--:|
| meses observables | 6,0 | 12,0 | 18,0 | 24,0 | 31,8 |
| vehículos activos (≥1 turno < t) | 41.478 | 62.975 | 79.120 | 94.657 | 111.184 |
| % sin mantenimiento observado | 33,4 | 28,0 | 25,6 | 23,8 | 21,3 |
| % con 1 mantenimiento | 53,7 | 43,5 | 36,7 | 32,3 | 28,5 |
| % con ≥2 mantenimientos | 12,9 | 28,5 | 37,7 | 43,9 | 50,1 |
| mediana días desde último mant. | 80 | 111 | 141 | 163 | 202 |
| p90 días desde último mant. | 158 | 292 | 403 | 525 | 705 |
| máximo observable (días) | 182 | 366 | 547 | 731 | 967 |
| % con maint_number > n observados | 77,7 | 67,6 | 59,6 | 53,9 | 48,5 |
| mediana de services invisibles (gap) | 3 | 2 | 1 | 1 | 0 |

Lectura: en 2024-07 la mediana de "días desde el último mantenimiento" es 80 y el p90 es 158 **porque el techo es 182**, no porque los clientes vuelvan cada 80 días. Ojo con la interpretación: para los vehículos que sí tienen un mantenimiento observado, la recencia es exacta (el último service dentro de la ventana es el último service a secas); el truncamiento vive íntegramente en el grupo "sin mantenimiento observado", que mezcla vehículos nuevos (todavía no les tocó) con vehículos cuyo último service quedó antes del extracto. Ver `05_calidad_cobertura_leakage_censura_izquierda.png` (panel derecho: las curvas acumuladas terminan en 1 exactamente en el techo de cada ventana).

La tabla A3 (53,5 % / 28,6 % / 17,5 % / 8,9 % de la distribución de recencia al CUTOFF supera 182 / 366 / 547 / 731 días) describe el corte transversal al CUTOFF entre vehículos con ≥1 mantenimiento en 32 meses, que incluye a los que no visitan la red hace más de seis meses; **no** es la fracción de vehículos activos en t con recencia truncada. La medida limpia, con la misma población y variando sólo la profundidad de historia, es A5:

| historia observable | % sin mant. observado | <1 año | 1-2 | 2-3 | 3-5 | 5-8 | 8+ |
|:--|--:|--:|--:|--:|--:|--:|--:|
| 6 meses (182 d) | 25,6 | 31,9 | 15,6 | 20,8 | 21,1 | 39,0 | 62,6 |
| 12 meses (366 d) | 16,1 | 31,0 | 5,7 | 8,3 | 10,9 | 27,0 | 53,9 |
| 18 meses (547 d) | 13,2 | 31,0 | 4,7 | 4,2 | 7,0 | 21,2 | 48,5 |
| 24 meses (731 d) | 12,0 | 31,0 | 4,6 | 2,8 | 5,2 | 17,6 | 45,7 |
| 32 meses (967 d) | 11,2 | 31,0 | 4,6 | 2,5 | 3,9 | 14,5 | 43,1 |

Población: los 54.667 vehículos con ≥1 turno en los 182 días previos al CUTOFF; edad medida al CUTOFF. La diferencia entre la primera fila y la última (**+14,4 pp con 6 meses, +4,9 pp con 12, +2,0 pp con 18, +0,8 pp con 24**) es la fracción de vehículos que un backtest etiqueta "sin mantenimiento" sólo por truncamiento. En los <1 año no cambia nada (31 %: todavía no les tocó, es real); en los de 5-8 años pasa de 39,0 % a 14,5 %.

### Hallazgo 3 — El sesgo no es uniforme: pega en los vehículos viejos, que son justo el segmento que más importa (A2)

% de vehículos activos sin mantenimiento observado, por edad en t:

| edad en t (años) | 2024-07-01 | 2025-01-01 | 2025-07-01 | 2026-01-01 | 2026-08-25 |
|:--|--:|--:|--:|--:|--:|
| <1 | 43,5 | 45,6 | 37,7 | 36,7 | 34,9 |
| 1-2 | 16,6 | 12,2 | 10,1 | 8,5 | 7,3 |
| 2-3 | 18,5 | 12,0 | 9,6 | 7,1 | 5,5 |
| 3-5 | 25,8 | 17,4 | 14,6 | 12,6 | 9,6 |
| 5-8 | 50,2 | 42,8 | 39,0 | 32,9 | 25,7 |
| 8+ | 72,0 | 66,3 | 64,2 | 63,3 | 61,0 |

Los <1 año no tienen historia porque todavía no les tocó el primer service (eso es real). Los 5-8 y 8+ años sí la tienen, pero está fuera del extracto: a 6 meses el 50,2 % de los 5-8 años "no tiene mantenimientos", y con 32 meses baja a 25,7 %. Salvedad: las columnas de A2 comparan poblaciones y momentos distintos (los activos en cada t); la comparación a población fija de A5 da 39,0 % → 14,5 % para 5-8 años y 62,6 % → 43,1 % para 8+, misma dirección y magnitud parecida. Un modelo entrenado con scoring temprano aprendería "auto viejo = sin historia = churn", que es en parte artefacto.

### Hallazgo 4 — `maint_number` del último service recupera la historia invisible (A4)

- Correlación entre el `maint_number` del primer service observado y la edad del vehículo: **0,761**. Sólo 553 de 26.518 vehículos con más de 2 años (2,1 %) tienen como primer service observado el 1°.
- Edad mediana al service según `maint_number`: 1°: 0,73 años, 2°: 1,28, 3°: 1,65, 4°: 1,97, 5°: 2,32, 6°: 2,77, 8°: 3,20, 10°: 3,72, 20°: 6,77. Es decir, la red numera ~2 services por año en los primeros años (no 1 por año como la regla "15.000 km o 1 año" sugeriría). Esto es tema del EDA de ventana; acá se señala como pregunta.
- Entre mantenimientos consecutivos observados, `maint_number` sube +1 en el 77,5 %, +2 en 7,4 % y baja o repite en 9,9 % (ruido de carga). Ver `05_calidad_cobertura_leakage_historia_invisible.png`.
- **Tasa de falsos positivos del proxy (A4b):** el "gap" (`maint_number` del último service − mantenimientos observados) es > 0 en el 74,8 % de los vehículos entregados antes de 2024 (mediana 3) pero también en el **4,9 %** de los entregados desde 2024, cuya historia completa está en el extracto (a t = 2025-01-01; 10,7 % al CUTOFF, casi todo gap = 1). En esos vehículos un gap > 0 no es historia invisible: es un salto de numeración o un service hecho fuera de la red / del extracto (señal propia de churn parcial). El proxy discrimina bien, pero conviene usarlo como `historia_invisible = max(gap, 0)` sólo para WSD < 2024 y como `services_fuera_de_red` para el resto.
- **Etiquetas truncadas:** `ServiceName` pierde el primer dígito para `ServiceMaintenance` 11, 12 y 19 ("1°", "2°", "9° Maintenance service") y en parte para 13 ("3ª Maintenance review"). El código numérico es el consistente con la edad (11°: 3,87 años; 12°: 4,04; 19°: 5,69), así que `maint_number` debe salir de `ServiceMaintenance`, nunca del nombre. El salto de edad entre 19° (5,69) y 20° (6,77), con 20 más frecuente que 14-19, sugiere que 20 agrupa "20 o más" (pregunta al mentor).

### Mitigaciones recomendadas (en orden de preferencia)

1. **Restringir el backtest a fechas de scoring ≥ 2025-01-01** (12 meses de historia mínima). Con 12 meses el truncamiento puro etiqueta "sin mantenimiento" a un 4,9 % adicional de los activos (contra 14,4 % con 6 meses; A5) y el 72,0 % de los vehículos activos ya tiene ≥1 mantenimiento observado (A1). Con t ≥ 2025-07-01 (18 meses, +2,0 pp) quedan todavía 79.120 vehículos activos.
2. **Features explícitas de censura**: `meses_observables = (t − 2024-01-01)`, `edad_vehiculo_en_t` (por WSD) y `max_maint_number_hasta_t`; e `historia_invisible = max_maint_number − n_mant_observados` (mediana 2 en 2025-01). El modelo puede así separar "sin historia porque es nuevo" de "sin historia porque el extracto no la trae".
3. **Recencia con censura explícita**: `dias_desde_ultimo_mant` con techo = ventana observable + flag `sin_mant_observado`; nunca imputar con un número grande arbitrario.
4. **Exigir mínimo de historia sólo si el negocio lo acepta**: excluir vehículos con `first_ev` a menos de N meses de t sesga hacia clientes fieles; preferible el punto 2.

---

## B. Columnas snapshot (foto) vs. evento

### Hallazgo 5 — Qué varía dentro de un vehículo (B1, sólo vehículos con ≥2 turnos: 85.143)

| columna | vehículos con >1 valor distinto | % (sobre ≥2 valores no nulos) | interpretación |
|:--|--:|--:|:--|
| ConnectedStatusARG | 74 | 0,1 | **snapshot** |
| KM | 7 | 0,0 | **snapshot** |
| VehicleCurrentKM | 73.813 | 97,5 | evento (lectura del turno) |
| WarrantyStartDate | 1 | 0,0 | atributo fijo |
| ModelYear | 0 | 0,0 | atributo fijo |
| TMA | 0 | 0,0 | atributo fijo |
| ShortVehicleModelGroupTreated | 90 | 0,1 | atributo fijo |
| Region | 5.093 | 6,0 | atributo del dealer del turno |
| DealerStateOrZone | 7.903 | 9,3 | atributo del dealer del turno |
| dealer_id | 18.552 | 21,8 | evento |
| customer_id | 23.245 | 27,6 | evento (cambio de titular / registro) |

Region y DealerStateOrZone son atributos del dealer (0 de 95 dealers tiene más de una Region o Zona); varían dentro del vehículo sólo cuando cambia de concesionario, así que son seguros como "atributos del último turno < t".

### Hallazgo 6 — `KM` es el odómetro a la extracción (B3, figura `km_snapshot`)

| métrica | valor |
|:--|--:|
| vehículos con ≥2 lecturas no nulas de KM cuyo KM es constante | 100,0 % |
| vehículos con ≥2 lecturas de VehicleCurrentKM que varían | 97,5 % |
| vehículos cuyo KM == VehicleCurrentKM del **último** turno concluido (sobre vehículos con ≥1 concluido con lectura) | 91,7 % |
| ídem, sobre vehículos con KM y VehicleCurrentKM no nulos | 95,5 % |
| vehículos cuyo KM ≥ max(VehicleCurrentKM) (ambos no nulos) | 92,9 % |
| turnos concluidos: KM == VehicleCurrentKM cuando el turno es el último del vehículo | 95,5 % |
| turnos concluidos: KM == VehicleCurrentKM cuando NO es el último | 2,5 % |
| turnos concluidos de 2024 con KM == VehicleCurrentKM | 13,0 % |
| turnos concluidos de 2026 con KM == VehicleCurrentKM | 66,1 % |

Las dos últimas filas son el mismo efecto visto por año: en 2024 el 12,3 % de los turnos concluidos es el último del vehículo y en 2026 el 65,8 %. Cuando `KM` difiere de la última lectura (4,5 % de los vehículos) lo hace en ambas direcciones (2,3 % arriba, 2,2 % abajo) y no se concentra en los vehículos "Conectado" (3,5 % arriba vs 1,7 % en "No Conectado"): no hay evidencia de que `KM` venga de telemetría; es la última lectura conocida del vehículo en la base, actualizada en la última visita. Para el backtest da lo mismo: es información posterior a t.

Consecuencia: el tutor dijo que "fecha del último service y kilometraje" son las variables clave. **El kilometraje que se puede usar en backtest es `VehicleCurrentKM` de turnos anteriores a t** (con `running max` por vehículo para absorber retrocesos, ver E4). `VehicleCurrentKM` es nulo en el 100 % de los cancelados, 71,9 % de los no-show y 76,5 % de los agendados, y 0,0 % de los concluidos: sólo existe si el auto entró.

### Hallazgo 7 — `ConnectedStatusARG` es una foto y además está confundido con la generación (B2, figura `conectividad_snapshot`)

- "Conectado" entre vehículos entregados antes de 2023-07-01: **0,6 %**; entregados después: 66,4 % (la P703 trae módem; la P375 no).
- "Sin Información de Conectividad" por trimestre de entrega: 2024Q2 2,9 %, 2025Q1 16,2 %, 2025Q4 35,1 %, 2026Q2 59,4 %, 2026Q3 92,6 %. Los vehículos recientes todavía no se activaron *a la fecha de extracción*; en un backtest con t = 2025-01 el valor que veríamos para un vehículo entregado en 2024Q4 sería el de 2026-08, no el de 2025-01.
- Sin controlar por edad, la diferencia de resultado es chica y va al revés de lo intuitivo: mantenimiento concluido en 41,8 % de los turnos "Conectado" vs 47,1 % "No Conectado" (B2b), porque "Conectado" ≈ vehículo nuevo con turnos de campaña/diagnóstico.

Recomendación: **no usar en backtest**. Si se quiere una señal de conectividad, derivar `generacion_conectada = (TMA ∈ {6DC,7DC,8DC,TA1})` que es determinística y estable. En el scoring actual puede mostrarse como atributo descriptivo, no como driver.

---

## C. Survey: qué es realmente `SurveyResponseDate`

### Hallazgo 8 — La encuesta se responde antes del turno, no después del service (C1, figura `survey_lag`)

Turnos con survey: 36.920 (7,5 %), de los cuales 26.072 concluidos, **8.363 cancelados, 1.341 no asistidos**, 682 concluidos sin OS, 396 agendados y 66 en progreso.

| lag en días (sólo turnos con ambas fechas) | n | p5 | p25 | mediana | p75 | p95 | máx | % < 0 | % > 0 |
|:--|--:|--:|--:|--:|--:|--:|--:|--:|--:|
| survey − checkout | 26.724 | −30 | −16 | −9 | −6 | −2 | 0 | 100,0 | 0,0 |
| survey − check-in | 24.839 | −24 | −13 | −8 | −5 | −2 | 314 | 99,9 | 0,04 (11 turnos) |
| survey − ScheduleDate | 36.920 | −26 | −14 | −8 | −4 | −2 | 0 | 100,0 | 0,0 |

- Sólo aparece en reservas por canal digital: FordPass 29,1 %, Mobile 30,9 %, WEB 18,0 %; Dealer y CAF 0 %.
- En 752 turnos (2,0 %) la misma `SurveyResponseDate` aparece en otro turno del mismo vehículo, en su mayoría pares que incluyen un cancelado (237 grupos cancelado + concluido, 89 cancelado + cancelado): la survey está atada a la sesión de reserva, no al turno.
- El rating medio es 4,75 en agendados, 4,75 en concluidos, 4,73 en cancelados y 4,66 en no asistidos: no distingue resultado porque se responde antes de que ocurra.
- No es la encuesta de la visita anterior: el lag contra el último checkout concluido previo del mismo vehículo tiene mediana 139 días y sólo el 2,9 % cae a ≤14 días.
- Hay 9 surveys con fecha posterior al CUTOFF y la mínima es 2023-10-13.

Regla: **usar sólo surveys con `SurveyResponseDate < t`** (regla que pedía el enunciado; se cumple automáticamente si se filtran turnos con `ScheduleDate < t`, porque la survey siempre es anterior a la fecha del turno). Interpretación para el jurado (hipótesis a confirmar con el mentor, consistente con todos los datos): "calificación de la experiencia de reserva en la app", no "satisfacción con el service". Uso adicional: `ScheduleDate − SurveyResponseDate` es un proxy de anticipación de la reserva (mediana 8 días, p90 21, 97,3 % ≤ 30 días), útil para dimensionar el horizonte de un mes: quien va a ir el mes que viene, en general todavía no reservó. Salvedad: un turno con `ScheduleDate ≥ t` y `SurveyResponseDate < t` es una reserva futura *conocida* en t (información legítima), pero son pocos y sólo de canal digital: 436 turnos / 426 vehículos a t = 2025-07-01 y 482 / 477 a t = 2026-01-01 (C). No justifica relajar la regla "nada con `ScheduleDate ≥ t`".

---

## D. Turnos futuros, pendientes y flags que miran hacia adelante

### Hallazgo 9 — "Tiene turno agendado" sólo existe para el scoring actual (D1, figura `turnos_pendientes`)

| | turnos | vehículos |
|:--|--:|--:|
| ScheduleDate > CUTOFF (reservas futuras) | 3.826 | 3.454 |
| de las cuales (30) Agendado | 3.321 | 3.263 |
| de las cuales (70) Cancelado | 498 | |
| de las cuales (40) En progreso | 7 | |
| con ítem de mantenimiento | 2.460 | 2.346 |
| pendientes ((30)+(40)) en total | 5.785 | 5.567 |
| pendientes con ScheduleDate ≤ CUTOFF (atrasados) | 2.457 | 2.349 |
| pendientes con ScheduleDate ≤ CUTOFF − 30 d (stale) | 962 | |
| (40) En progreso stale | 687 | |
| (30) Agendado stale | 275 | |
| pendientes con ScheduleDate ≤ CUTOFF − 180 d | 377 | |

Nota: los "4.185 turnos (30) Agendado futuros" del diccionario son filas-ítem; a nivel turno son 3.321. Las reservas futuras se concentran en 2026-08 (2.259) y 2026-09 (1.534); sólo 33 caen de octubre en adelante.

Implicancia: no hay `CreatedDate`, así que para una fecha t histórica no se puede saber si el cliente ya tenía turno. Cualquier feature del tipo "tiene reserva futura" o "días hasta el próximo turno" en backtest sería leakage (el turno se creó, con alta probabilidad, después de t; la mediana de anticipación estimada por survey es 8 días). Tratamiento propuesto:

- **Backtest:** features sólo con turnos `ScheduleDate < t` (y `event_date < t`). Nada con `ScheduleDate ≥ t`, ni siquiera cancelados.
- **Scoring actual:** regla operativa post-modelo: si el vehículo tiene un (30) Agendado con `ScheduleDate > hoy`, se lo saca de la lista de contacto (o se lo marca "ya reservó"), sin que el modelo lo use como feature. Son 3.263 vehículos hoy.
- **Pendientes stale:** los (40) En progreso tienen check-in en el 100 % y no tienen checkout en el 99,9 %: son órdenes abiertas a la extracción; las de más de 30 días (687) nunca se cerraron. Para el target, ni (30) ni (40) cuentan como mantenimiento concluido; para las features, un (40) con `event_date < t` cuenta como "ingresó al taller".

### Hallazgo 10 — `IsReschedule` en cancelados describe lo que pasó después (D2)

| grupo | turnos | % turno posterior ≤7 d | % turno posterior ≤30 d | % concluido ≤30 d después | % turno anterior ≤30 d | % anterior cancelado ≤30 d |
|:--|--:|--:|--:|--:|--:|--:|
| (70) Cancelado, IsReschedule = N | 32.439 | 27,7 | 44,5 | 26,7 | 43,2 | 16,7 |
| (70) Cancelado, IsReschedule = Y | 68.782 | 53,2 | 71,9 | 45,9 | 54,5 | 17,2 |
| (60) Concluido, IsReschedule = Y | 45.460 | 36,4 | 49,9 | 5,6 | 67,1 | 62,5 |
| (60) Concluido, IsReschedule = NaN | 295.165 | 5,3 | 15,2 | 9,5 | 16,6 | 4,0 |
| (60) Concluido, ScheduleReturn = Y | 29.247 | 10,0 | 25,7 | 14,2 | 97,2 | 15,3 |
| (60) Concluido, ScheduleReturn = N | 301.959 | 9,2 | 19,1 | 8,5 | 16,2 | 11,4 |

- En un cancelado, `IsReschedule = Y` casi duplica la probabilidad de tener un turno posterior a ≤7 días (53,2 % vs 27,7 %), el 90,8 % tiene algún turno posterior (79,4 % con N) y en el 65,3 % el turno siguiente también lleva `IsReschedule = Y` (15,7 % con N): el flag marca el par cancelado / re-agendado. En las filas canceladas es además colineal con `ScheduleStatus` (Y ⇔ `ScheduleStatus` nulo, 77.013 filas; N ⇔ "(70) Cancelado", 36.424): son dos vías de cancelación del sistema de origen, y `ScheduleStatus` nulo en un cancelado lleva la misma información.
- Sobre el riesgo temporal: la fecha de la acción de re-agendar no está en los datos. Lo habitual es re-agendar *antes* de la fecha original, con lo cual el flag ya existía en t para cualquier cancelado con `ScheduleDate < t`; pero no se puede descartar la cancelación tardía (el dealer que limpia un no-show y recarga), y el turno nuevo puede tener `ScheduleDate ≥ t`. El flag puede, entonces, revelar una reserva creada después de t. Regla conservadora: ignorar `IsReschedule` de cancelaciones ocurridas en los 30 días previos a t (o usar sólo la versión "este turno concluido es un re-agendamiento", que mira al pasado: 67,1 % tiene un turno previo a ≤30 días, 62,5 % cancelado).
- `ScheduleReturn = Y` es una **visita de retorno**: 97,2 % tiene un turno previo a ≤30 días (75,0 % un turno *concluido* a ≤30 días), y su composición es 15,0 % mantenimiento / 31,0 % reparación / 35,6 % diagnóstico, contra 69,3 % / 7,5 % / 18,5 % en N. En sentido inverso, de los concluidos con un concluido previo a ≤30 días el 71,7 % lleva Y. Mira al pasado, así que es seguro como feature; pero para el target conviene no contar un retorno como "mantenimiento programado" (pregunta abierta).

---

## E. Inconsistencias puntuales: tabla de problemas (E1)

| tabla | problema | magnitud | decisión |
|:--|:--|:--|:--|
| agenda | ModelYear = 0 o < 2005 | 43 turnos / 29 vehículos (28 sin WSD) | flag; excluir los 28 sin WSD |
| agenda | ModelYear nulo | 4.431 turnos / 821 vehículos con id (2.896 turnos sin vehicle_id) | imputar edad por WSD; si no, flag |
| agenda | WSD.year − ModelYear fuera de [−1, +1] | 940 turnos (0,2 %) | flag; la edad se calcula por WSD |
| agenda | EffectiveCheckinDate < 2024-01-01 | 4 turnos (uno en 2001 con DaysInDealer 8.461; tres del 28-29/12/2023) | ya corregido: `eventos.py` usa el check-in sólo si \|check-in − ScheduleDate\| ≤ 45 d |
| agenda | \|check-in − ScheduleDate\| > 30 días | 564 turnos (> 10 d: 2.406; > 45 d: 328) | dejar; para los 328 con \|gap\| > 45 d event_date ya cae a ScheduleDate |
| agenda | (60) Concluido sin check-in | 45.433 turnos (13,3 % de los concluidos; 22,9 % en 2024) | dejar: event_date cae a ScheduleDate, que coincide con el check-in el 91,7 % de las veces (E3) |
| agenda | checkout < check-in | 130 turnos | flag |
| agenda | (80) No asistió con check-in | 1.556 turnos (5,7 % de los no-show) | prevalece StatusARG; flag |
| agenda | KM (snapshot) = 0 / > 500.000 / > 1.000.000 en concluidos | 7 / 673 / 123 turnos | irrelevante: KM no se usa (B3) |
| agenda | VehicleCurrentKM < 100 en concluidos | 10.076 turnos (2,9 %); valores típicos 1, 10, 3, 12, 30 | corregir a nulo (placeholder) |
| agenda | VehicleCurrentKM > 500.000 / > 1.000.000 | 617 / 162 turnos | > 1 M a nulo; 500k–1M flag |
| agenda | VehicleCurrentKM retrocede > 1.000 km entre visitas concluidas consecutivas | 6.948 pares (2,9 %) en 6.347 de 72.940 vehículos con VCK > 0; **excluyendo placeholders (<100) y >1 M: 5.058 pares (2,2 %) en 4.684 vehículos** (E4b) | primero anular placeholders, después running max por vehículo + flag |
| agenda | > 300 km/día entre visitas (excluye mismo día) | 8.104 pares (3,4 %); mediana 69 km/día, p95 250, p99 1.231; **sin placeholders: 6.485 pares (2,8 %), p99 881** (E4b) | flag; recortar km/día a p99 después de anular placeholders |
| agenda | ServicePriceDiscount no es un descuento | no nulo en 34,8 % de los ítems; = 0 en 72.589 (62.727 campañas, 5.880 PUD; el 100 % de los ítems con ServiceFordFixedPriceFlag = Y y precio no nulo vale 0); mediana 29,8 M; informado en 44-52 % de los ítems de mantenimiento desde 2024Q1, pero para el 1° service recién desde 2025Q1 (2024: ≤53 valores por trimestre, todos 0); mediana del 1° service 27,3 M (2025Q1) → 36,7 M (2026Q1) → 48,4 M (2026Q3) | sólo flag "precio informado"; 0 = precio fijo Ford / gratuito, no "sin dato"; preguntar unidad |
| agenda | ServiceLaborCost | 4.703 ítems (0,7 %), todos Mantenimiento 2026; mediana 576.380, misma escala que ServiceFordFixedPrice (131.000 / 170.500) | excluir columna |
| sales/agenda | WSD distinto entre sales y agenda | 406 de 42.150 vehículos con WSD en ambas (1,0 %); \|dif\| > 30 d: 25; > 365 d: 2; mediana 8 d; otros 56 tienen WSD nula en sales | usar WSD de sales; la WSD de agenda = DeliveryDate de sales en 98,8 % |
| agenda | WSD posterior al primer turno concluido | 1.505 vehículos; > 30 d: 198; > 365 d: 3 | edad negativa se recorta a 0 (PDI/entrega) |
| sales | DeliveryDate 2013/2015 y SalesDate > DeliveryDate | 3 filas (las mismas) | excluir |
| sales | SalesDate > RegistrationDate | 9.806 filas (16,5 %) | no se usa; preguntar semántica |
| sales | WSD < DeliveryDate | 1.425 filas | inicio de vida útil = min(WSD, DeliveryDate) |
| sales | PersonType 25 / 29 / 30 / nulo | 656 / 153 / 9 / 35 (el 25 es 80 % canal HR) | categoría "otro" con flag |
| sales | Status 1 / 2 / 3 | 107 filas; 77 sin DeliveryDate; presencia en agenda 57,9 % vs 71,1 % | excluir hasta que tengan DeliveryDate |
| sales | GLOBAL RANGER - FSAO | 1 fila (MY 2013, canal UNKNOWN, sin ModelCode ni WSD) | excluir |
| sales | dealer_id / WSD / DeliveryDate nulos | 139 / 180 / 90 filas | dejar; WSD nulo ← DeliveryDate |

Detalles que valen una línea:

- **Check-in vs ScheduleDate (E3, figura `checkin_y_odometro`):** 313.224 turnos con check-in; mismo día 91,7 %; ±1 día 95,8 %; check-in anterior al turno 0,6 %. La definición `event_date = check-in si existe, si no ScheduleDate` es razonable. Check-in no nulo por status: (60) 86,7 %, (90) 81,1 %, (40) 100 %, (80) 5,7 %, (70) 0 %.
- **Coherencia WSD vs ModelYear (E2):** −1 en 125.472 turnos, 0 en 325.009, +1 en 35.483; fuera de eso 940. ModelYear es año-modelo, no año de entrega: la edad hay que calcularla con WSD.
- **ServicePriceDiscount (E5):** la mediana por trimestre en ítems de mantenimiento va de 21,7 M (2024Q1) a 54,8 M (2026Q3), monótona: parece un precio de lista en centavos o ×100 (la mediana del 1° service en 2026Q1 es 36.715.000, es decir $367.150, verosímil; `ServiceLaborCost` y `ServiceFordFixedPrice` están en la escala ×1). Está informado en entre 29 % (2025Q1) y 67 % (2026Q3) de los ítems de mantenimiento según el trimestre, ya desde 2024Q1 (46 %); el 1° service en particular sólo desde 2025Q1. Los ceros (0-2 % de los precios no nulos de mantenimiento) son ítems de precio fijo Ford o gratuitos (campañas, PUD), no falta de dato. No es un dato del cliente y no aporta a churn más allá de un flag.
- **(90) Concluido sin OS:** tiene check-in en el 81,1 % y `VehicleCurrentKM` en el 97,2 %. El auto entró pero no se abrió orden. No es tema de este EDA, pero afecta el target: hoy queda fuera del "mantenimiento concluido".

---

## F. Turnos sin vehicle_id o sin customer_id (F1)

| | sin vehicle_id | sin customer_id |
|:--|--:|--:|
| turnos | 2.897 | 9.398 |
| % de turnos | 0,6 | 1,9 |
| (60) Concluido | 2.066 | 6.294 |
| mantenimientos concluidos | 1.186 | 3.948 |
| sin el otro id tampoco | 418 | 418 |
| % ModelYear nulo | 100,0 | 5,7 |
| % WarrantyStartDate nulo | 100,0 | 6,4 |
| % KM nulo | 99,2 | 7,5 |
| origen Dealer | 2.896 | 7.141 |

- **Sin vehicle_id (2.897):** no tienen ModelYear, WSD ni KM: son turnos cargados por el dealer sin identificar el vehículo. No se pueden asignar a ninguna unidad usuario-vehículo → **excluir** (se pierden 1.186 mantenimientos concluidos, 0,5 % del total).
- **Sin customer_id pero con vehicle_id (8.980):** el evento es real para el vehículo (3.948 mantenimientos concluidos). **Mantener** en la historia del vehículo; 2.961 vehículos tienen algún turno sin cliente y 1.760 de ellos tienen otro turno con cliente, así que se puede imputar el customer_id del vehículo (último conocido antes de t).

---

## G. Duplicados lógicos

### Hallazgo 11 — Filas idénticas y turnos multi-fila

- 19.554 filas idénticas (3,1 %) en 11.575 schedule_id, 19.492 de ellas en turnos concluidos. `appointments()` ya las elimina.
- A nivel `schedule_id`, las columnas de nivel turno son consistentes: sólo 4 schedule_id tienen más de un StatusARG, y 0 tienen más de una ScheduleDate, check-in, KM, vehicle_id, customer_id o dealer_id.

### Hallazgo 12 — Mismo vehículo, misma fecha, distinto schedule_id (G1, figura `duplicados_cancelaciones`)

24.952 pares (vehículo, ScheduleDate) con más de un turno, 52.339 turnos, 19.594 vehículos:

| combinación de StatusARG | pares | % |
|:--|--:|--:|
| (60) Concluido \| (70) Cancelado | 14.572 | 58,4 |
| (60) Concluido \| (60) Concluido | 2.988 | 12,0 |
| (70) Cancelado \| (70) Cancelado | 2.630 | 10,5 |
| (70) Cancelado \| (80) No asistió | 1.134 | 4,5 |
| (60) Concluido \| (70) Cancelado \| (70) Cancelado | 1.097 | 4,4 |
| (70) Cancelado \| (90) Concluido sin OS | 557 | 2,2 |
| (60) Concluido \| (80) No asistió | 424 | 1,7 |

- Mantenimientos concluidos duplicados: 332 pares (vehículo, event_date) con más de un mantenimiento concluido el mismo día (667 turnos); 988 mantenimientos a ≤7 días de otro del mismo vehículo (673 con el mismo `maint_number`); 2.201 a ≤30 días (1.087 mismo `maint_number`). Recomendación: **colapsar mantenimientos concluidos del mismo vehículo a ≤7 días en un solo evento**; para el target, el que cuenta es el primero.

### Hallazgo 13 — Más de la mitad de las cancelaciones son re-agendamientos, no abandono (G2)

| | turnos | % |
|:--|--:|--:|
| (70) Cancelado con vehicle_id | 101.221 | 100,0 |
| con un (60) Concluido del mismo vehículo el mismo día | 17.144 | 16,9 |
| con un (60) Concluido a ≤7 días (antes o después) | 54.752 | 54,1 |
| seguido de un (60) Concluido dentro de 30 días | 57.529 | 56,8 |
| (80) No asistió con vehicle_id | 26.727 | 100,0 |
| seguido de un (60) Concluido dentro de 30 días | 7.624 | 28,5 |

El patrón dominante (un cancelado + un concluido el mismo día, 14.572 pares) es compatible con el dealer que cancela y vuelve a cargar el turno; el resto de los "≤7 días" incluye también al cliente que re-agenda por su cuenta. Los datos no distinguen quién canceló, sólo que no fue abandono. De los 25.796 cancelados con ítem de mantenimiento, el 46,5 % tiene un mantenimiento *concluido* del mismo vehículo a ±7 días. Una feature "cantidad de cancelaciones" cruda mezcla abandono con re-agendamiento; propuesta: `cancelaciones_netas` = cancelados sin un concluido del mismo vehículo a ±7 días, y `no_show_netos` análogo (los no-show sí parecen abandono: sólo el 28,5 % se concreta en 30 días).

---

## H. Cobertura sales vs agenda

### Hallazgo 14 — Los vendidos aparecen en la agenda cuando tuvieron tiempo (H1, figura `cobertura`)

| ventas | n | % con ≥1 turno en agenda | % con ≥1 mantenimiento concluido |
|:--|--:|--:|--:|
| todas | 59.384 | 71,1 | 62,2 |
| > 180 días antes del CUTOFF | 50.773 | 80,4 | 72,2 |
| > 365 días | 39.928 | 88,5 | 82,2 |
| > 548 días | 27.197 | 90,4 | 85,1 |
| > 730 días | 14.712 | 91,4 | 86,6 |

Entre ventas con más de 365 días, la presencia en agenda es 91,4 % Ford Blue vs 82,0 % Ford Pro; 90,5 % ROR, 88,8 % CONSORTIUM, 80,7 % DIRECT SALES y **67,5 % HR**; PersonType F 89,6 %, J 87,6 %, "25" 69,2 % (H1b). "≥1 turno" incluye cancelados y no-show; con la vara que importa para el target (≥1 mantenimiento concluido) la presencia baja unos 5-6 puntos. Que la caída en cohortes recientes sea falta de tiempo y no un cambio de comportamiento se verifica a exposición fija (H1c): el % de vendidos con ≥1 turno dentro de los 365 días de la venta es 68,2 % (2024Q1), 73,0 %, 72,8 %, 71,3 %, 70,8 %, 71,8 % y 69,8 % (2025Q3), estable. Los 17.173 vehículos "sólo sales" son mayormente ventas recientes: el 8,6 % restante entre ventas de más de dos años es el "churn total" (nunca pisaron la red) y es población legítima del problema, no un defecto de cobertura.

### Hallazgo 15 — WSD es coherente y sales cubre casi todo lo entregado desde 2024 (H2)

- Para los 42.150 vehículos en ambas tablas con WSD en las dos, la WSD coincide en 41.744 (99,0 %); las 406 diferencias tienen mediana 8 días y sólo 25 superan 30 días (otros 56 vehículos tienen WSD nula en sales). La WSD de la agenda es igual a `DeliveryDate` de sales en el 98,8 %: **WSD = fecha de entrega**.
- Vehículos de la agenda con WSD ≥ 2024-01-01: 43.700; **42.205 (96,6 %) están en sales**; 1.495 (3,4 %) no (562 7DC, 456 8DC, 374 6DC, 62 TA1; 1.203 con WSD 2024, 214 de 2025, 78 de 2026). Son ventas fuera del extracto (otra unidad de negocio o carga tardía); para ellos hay que usar la WSD y el ModelYear de la agenda como si fuera la venta.
- De los 11.712 vehículos con ModelYear ≥ 2024 que no están en sales, 10.189 tienen WSD en 2023: ModelYear 2024 entregado en 2023, antes del extracto; coherente.
- 1.798 vehículos (4,3 % de los 42.211 en ambas tablas) tienen su primer turno antes de `DeliveryDate`, sólo 227 más de 30 días antes: PDI o carga previa a la entrega. La mediana entre entrega y primer turno es 6,1 meses (p90 12,3).
- Sólo en el 70,1 % de los vehículos en ambas tablas (29.576 de 42.211) el customer_id del comprador aparece en algún turno. El 29,9 % restante pasa por el taller siempre con otro customer_id: es relevante para el requisito "identificar si el que va al service es el que compró" (tema de otro EDA; acá se deja como pregunta).

---

## I. Síntesis

### I1. Columnas con riesgo de leakage y regla de uso

| columna | por qué | regla de uso |
|:--|:--|:--|
| `KM` | última lectura conocida del vehículo a la extracción (constante por vehículo; = lectura del último turno concluido en 95,5 %) | **No usar.** Odómetro = `VehicleCurrentKM` de turnos con `event_date < t`, placeholders a nulo, running max por vehículo. |
| `ConnectedStatusARG` | foto a la extracción; confundida con generación | **No usar en backtest.** Alternativa: `generacion_conectada` por TMA. Descriptivo en scoring actual, con advertencia. |
| `IsReschedule` en (70) | Y = par cancelado / re-agendado; la fecha de la acción no está en los datos y el turno nuevo puede ser ≥ t | Ignorar en cancelaciones de los 30 días previos a t; o usar sólo la versión en (60) ("es re-agendamiento", mira al pasado). Mismo tratamiento para `ScheduleStatus` nulo en cancelados (colineal). |
| `ScheduleReturn` | visita de retorno (mira al pasado) | Usable si `event_date < t`; no contar retornos como mantenimiento programado en el target (a confirmar). |
| `SurveyResponseDate` / `SurveyStarRating` | se responde antes del turno; sólo canales digitales | Usable si `SurveyResponseDate < t`; semántica = calificación de la reserva. Proxy de fecha de reserva. |
| turnos con `ScheduleDate ≥ t` (cualquier status) | sin fecha de creación | Fuera de las features en backtest. "Ya tiene turno" = regla operativa post-modelo en el scoring actual. |
| (30)/(40) con `ScheduleDate < t` | estado abierto a la extracción | No cuentan como mantenimiento concluido; (40) con check-in < t cuenta como ingreso. Stale (>30 d) con flag. |
| `EffectiveCheckoutDate`, `DaysInDealer`, `WorkDaysInDealer`, `EffectiveTerm` | resultado de la visita | Sólo de turnos con `EffectiveCheckoutDate < t`. |
| `customer_id` (agenda) | cambia en 20,8 % de los vehículos (27,6 % de los que tienen ≥2 turnos con cliente) | Usar el del último turno < t; nunca "alguna vez cambió". |
| `WarrantyStartDate`, `ModelYear`, `TMA`, `ShortVehicleModelGroupTreated` | fijos | Libres (edad, generación). |
| `Region`, `DealerStateOrZone`, `dealer_id` | del dealer del turno | Como atributos del último turno < t. |
| `ServicePriceDiscount` | precio ×100, informado en ~50 % de los ítems de mantenimiento desde 2024Q1 (1° service desde 2025Q1); 0 = precio fijo / campaña | Flag "precio informado"; confirmar unidad. |
| `ServiceLaborCost` | 0,7 % no nulo | Excluir. |
| `maint_number` | +1 entre services en 77,5 %; gap > 0 en 4,9-10,7 % de vehículos con historia completa visible | Máximo observado hasta t como proxy de historia (`historia_invisible` sólo si WSD < 2024). Tomarlo de `ServiceMaintenance`, no del nombre. |

### I2. Exclusiones y correcciones, con conteos

| tabla | exclusión / corrección | afectados | tratamiento |
|:--|:--|:--|:--|
| agenda | filas idénticas | 19.554 filas-ítem | excluir (ya lo hace `appointments()`) |
| agenda | turnos sin vehicle_id | 2.897 turnos (1.186 mant. concluidos) | excluir |
| agenda | turnos sin customer_id con vehicle_id | 8.980 turnos | mantener; imputar cliente del vehículo (1.760 vehículos) |
| agenda | ModelYear 0/<2005 sin WSD | 28 vehículos | excluir |
| agenda | sin WSD ni ModelYear | 772 vehículos (1.257 sin WSD) | flag edad desconocida; imputar por TMA si se retienen |
| agenda | check-in con \|check-in − ScheduleDate\| > 45 d (incluye los 4 anteriores a 2024) | 328 turnos | event_date = ScheduleDate (ya lo hace `eventos.py`) |
| agenda | VehicleCurrentKM < 100 o > 1.000.000 (concluidos) | 10.238 turnos | a nulo |
| agenda | pendientes stale ((30)/(40) ≤ CUTOFF − 30 d) | 962 turnos | no concluidos, con flag |
| agenda | mantenimientos concluidos a ≤7 días de otro del mismo vehículo | 988 turnos | colapsar (queda el primero) |
| agenda | turnos con ScheduleDate > CUTOFF | 3.826 turnos | fuera del backtest; regla operativa en scoring actual |
| sales | GLOBAL RANGER / DeliveryDate < 2020 / Status ≠ ACCEPTED | 110 filas | excluir de la población de vendidos |

---

## Implicancias para target, ventana y features

**Target.** (a) Sólo (60) Concluido con ítem de mantenimiento cuenta; (30)/(40) atrasados no cuentan, y los stale se marcan. (b) Colapsar mantenimientos del mismo vehículo a ≤7 días (988 turnos) para no contar dos veces. (c) Decidir con el mentor si un (60) con `ScheduleReturn = Y` (15 % con ítem de mantenimiento) y un (90) Concluido sin OS cuentan como "mantenimiento programado completado". (d) El horizonte de resultado debe cerrar antes del CUTOFF menos un margen: hay 1 check-in el 2026-08-27 y 9 surveys posteriores al CUTOFF, pero ningún checkout ni (60) con ScheduleDate > CUTOFF; el margen razonable son 30 días por las órdenes abiertas.

**Ventana / fechas de scoring.** Backtest con t ≥ 2025-01-01 (12 meses de historia observable) como mínimo: el truncamiento puro pasa de +14,4 pp (6 meses) a +4,9 pp (12 meses) de vehículos etiquetados "sin mantenimiento" (A5); t ≥ 2025-07-01 lo deja en +2,0 pp. Incluir `meses_observables`, `edad_en_t` e `historia_invisible` como features para que el modelo no atribuya a churn lo que es censura. Para vehículos entregados antes de 2024, la "ventana de mantenimiento" no puede anclarse en el último service observado sin flag: en 2025-01 el 74,8 % de ellos tiene services anteriores al extracto (A4b).

**Features.** Odómetro por `VehicleCurrentKM` (running max, placeholders a nulo, km/día recortado a p99); nunca `KM`. Nada de `ConnectedStatusARG` en backtest. `cancelaciones_netas` y `no_show_netos` (sin re-agendamientos a ±7 días). `IsReschedule` sólo en su versión "este turno concluido fue re-agendado". Survey sólo con fecha < t y con la semántica correcta. Todo lo demás (edad, generación, dealer, zona, maint_number, recencia con techo) es seguro si se filtra por `event_date < t` y `EffectiveCheckoutDate < t`.

---

## Preguntas para el mentor

1. **`KM` vs `VehicleCurrentKM`:** ¿confirma que `KM` es el odómetro vigente del vehículo en la base a la fecha de extracción (y `VehicleCurrentKM` la lectura cargada en el turno)? ¿En producción el scoring tendría acceso al odómetro "actual" (telemetría para conectados)? Si sí, se puede usar en el scoring actual aunque no en backtest.
2. **`ConnectedStatusARG`:** ¿es el estado a la fecha de extracción? ¿Existe historial de activación (fecha en que pasó a Conectado)? Sin eso, no entra al modelo.
3. **`SurveyResponseDate` / `SurveyStarRating`:** ¿qué encuesta es? Los datos indican que se responde entre 2 y 26 días *antes* del turno y sólo en reservas por FordPass/Mobile/WEB. ¿Es la calificación de la experiencia de reserva en la app?
4. **Fecha de creación del turno:** ¿`SCHEDULES_AGENDA.SCHEDULES_SERVICES_MOD` en BigQuery tiene `CreatedDate` o equivalente? Con ese campo, "tiene turno agendado a la fecha t" pasa a ser una feature válida en backtest y el proxy por survey deja de hacer falta.
5. **`IsReschedule` y `ScheduleReturn`:** ¿en qué momento se setean? En los cancelados `IsReschedule = Y` coincide exactamente con `ScheduleStatus` nulo (77.013 filas) y `N` con "(70) Cancelado" (36.424): ¿son dos vías distintas de cancelación (re-agendamiento vs. cancelación explícita)? ¿La cancelación puede registrarse después de la fecha del turno? ¿`ScheduleReturn = Y` es "retorno por reclamo/re-trabajo"? ¿Un retorno con ítem de mantenimiento cuenta como mantenimiento programado?
6. **`ServicePriceDiscount`:** ¿qué es exactamente (precio de lista, precio con descuento, unidad en centavos)? Los valores (mediana 29,8 M, monótonos en el tiempo) no son un descuento.
7. **(40) En progreso stale:** 687 órdenes con más de 30 días abiertas (algunas de 2024). ¿Son órdenes que nunca se cerraron en el sistema? ¿Se pueden considerar concluidas si tienen `VehicleCurrentKM`?
8. **(90) Concluido sin OS:** el auto entró (81 % con check-in) pero no hubo orden. ¿Cuenta como visita a la red? ¿Puede ser un mantenimiento cobrado fuera del sistema?
9. **Vehículos entregados desde 2024 que no están en sales (1.495, 3,4 %):** ¿son ventas de otra unidad de negocio o carga posterior? ¿Corresponde tratarlos como población o excluirlos?
10. **Numeración de services:** la edad mediana al 2° service es 1,28 años y al 4° es 1,97: parece un ciclo de ~6 meses/7.500 km más que "15.000 km o 1 año". ¿La regla de la ventana es por modelo/año? (Afecta la definición de ventana, no este EDA.) Además: `ServiceName` dice "1°/2°/9° Maintenance service" para `ServiceMaintenance` 11/12/19 (¿truncamiento de la etiqueta?), y el código 20 es más frecuente que 14-19 con un salto de edad (5,69 → 6,77 años): ¿20 significa "20 o más"? ¿Un gap en la numeración en vehículos 0 km (4,9-10,7 %) indica un service hecho fuera de la red?
11. **`RegistrationDate`:** 9.806 ventas tienen `SalesDate > RegistrationDate`. ¿Qué representa esa fecha?
12. **Titularidad:** en el 29,9 % de los vehículos en ambas tablas el comprador nunca aparece como customer_id de un turno. ¿El customer_id de la agenda es el titular o quien reservó (chofer, empresa, taller)?
