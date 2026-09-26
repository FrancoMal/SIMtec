# EDA 01 — Taxonomía de eventos de la Agenda y definición de "mantenimiento programado completado"

- Script reproducible: `scripts/eda/01_taxonomia_target.py` (corre de punta a punta con `PYTHONIOENCODING=utf8 PYTHONPATH=src .venv/Scripts/python.exe scripts/eda/01_taxonomia_target.py`).
- Apéndice con todas las tablas generadas (numeración `N.M` citada abajo): `reports/eda/01_taxonomia_target_tablas.md`.
- Figuras: `reports/figures/eda/01_taxonomia_target_*.png`.
- Datos: `data/interim/agenda.parquet` (631.623 filas ítem, 19.554 filas totalmente duplicadas eliminadas → 612.069 ítems, 492.442 turnos, 111.752 vehículos) y `sales.parquet`. CUTOFF = 2026-08-25.
- Todas las cifras de este informe salen del script; cuando una cifra viene de una tabla del apéndice se indica entre corchetes, p. ej. [T 2.1].
- Verificación independiente (recuento con código propio y tests adicionales): `reports/eda/01_taxonomia_target_verificacion.md`, script `scripts/eda/01_taxonomia_target_verificacion.py`, tablas `[V x.y]` en `reports/eda/01_taxonomia_target_verificacion_tablas.md`. Los párrafos marcados "(ajustado en verificación)" incorporan sus resultados.

## Resumen ejecutivo

1. **La definición preliminar del evento objetivo se sostiene**: `StatusARG == '(60) Concluido'` y al menos un ítem con `ServiceMaintenance` no nulo identifica 222.889 turnos en 87.531 vehículos. El campo `ServiceMaintenance` es consistente al 100 % con el nombre del ítem (`N° Maintenance service` / `Nª Maintenance review`) y con `ServiceType = Mantenimiento` [T 1.2]. Con dos ajustes (exigir `vehicle_id` y deduplicar), la regla final deja **220.522 eventos objetivo en 87.531 vehículos** [T 11.1].
2. **`(90) Concluido sin OS` es una visita real pero no un mantenimiento**: el auto entró (check-out registrado en 96,4 %, km al ingreso en 97,2 %, mediana 4 días en el taller), pero solo 26,2 % de esos turnos incluía un ítem de mantenimiento y 48,8 % era diagnóstico [T 2.1]. Se recomienda contarlo como *visita a la red* (feature) y no como retorno objetivo. Incluir los 4.058 turnos (90) con ítem de mantenimiento cambiaría el target en +1,8 %. (Ajustado en verificación: la evidencia de que en un (90)+mantenimiento el service *no* se hizo es que el siguiente (60)+mant del vehículo repite el mismo número en 22,2 % de los casos, contra 5,3 % tras un (60)+mant [V 2.8]; para el resto no se puede saber, porque el número es un hito de km y avanza igual se haya hecho o no el service anterior.)
3. **Garantía, campañas/recall e inspecciones no son mantenimiento programado**. Incluirlos moverían el target de 222.889 a 227.805 (+garantía) o 254.596 (+campañas, +31.707 turnos, +5.903 vehículos) [T 3.5]. **`Oil and filter change` es el caso discutible y hay que resolverlo con el mentor** (ajustado en verificación): son 822 turnos (60) solo con ese ítem (+1.127 si se cuenta cualquier (60) que lo incluya), aparece únicamente en 2026, y en 74,6 % de esos turnos el vehículo venía haciendo services del plan: el cambio de aceite cae a una mediana de 14.793 km del service anterior en P703 (el hito es 15.000) y 12.752 km en P375 [V 3.6, 3.7]. Es decir, se parece a un *sustituto barato del service del plan en el hito*, no a un servicio suelto de vehículos viejos. Con la regla actual esos vehículos quedan como churn en 2026.
4. **`ServiceMaintenance` (n) es un hito de kilometraje, no de tiempo**: en P703 la mediana de `VehicleCurrentKM` es 16.008 km en el 1°, 32.130 en el 2°, 48.416 en el 3° (75,4 % de los ítems dentro de ±20 % de n×15.000); en P375 es 11.060 / 20.548 / 30.614 (78,5 % dentro de ±20 % de n×10.000) [T 4.8, 4.9]. `ServiceMonth = 12n` no describe la edad del vehículo (solo 24,2 % de los ítems tiene |edad − ServiceMonth| ≤ 6 meses). Para P703 el 1° service ocurre a una mediana de 8,4 meses sobre todos los ítems; **9,1 meses (p75 11,9; 77,6 % antes de los 12 meses) en la cohorte con seguimiento completo** (garantía iniciada en 2024-H1), porque la cifra global mezcla cohortes de 2025-2026 todavía censuradas [V 4.4, 4.5] (ajustado en verificación).
5. **Los nombres "1° Maintenance service" con n = 11, "2°" con 12, etc. son un defecto del catálogo, no del número**: en P375 el 22,9 % de los ítems tiene n ≥ 11 (vehículos 2012-2018 con 110.000-220.000 km) y el km al ingreso sigue la recta n×10.000 sin quiebre [T 4.6, 4.8]. Usar el número, nunca el nombre. "Maintenance service" → "Maintenance review" es un renombre del catálogo en enero-febrero 2026 en todos los dealers (mínimo 92,4 % de "review" por dealer desde 2026-02), no dos catálogos [T 4.2, 4.3].
6. **`IsReschedule` solo se completa en cancelaciones y en los turnos que nacen de una reprogramación**; `IsReschedule = N` ⇔ `ScheduleStatus` crudo `(70) Cancelado` (cancelación "dura"), `IsReschedule = Y` ⇔ `ScheduleStatus` nulo (cancelación por reprogramación) [T 5.2]. **`ScheduleReturn = Y` es una visita de retorno**: 98,0 % tiene un turno previo del mismo vehículo a ≤ 30 días (74,2 % si se mira solo el turno inmediato anterior y es un (60); 88,4 % si se cuenta cualquier (60) del vehículo en los 30 días previos [V 7.4]), con 37,4 % diagnóstico y 30,4 % reparación [T 5.5, 5.6].
7. **Cancelar no es perder al cliente, no asistir sí lo es más**: a 90 días, 69,1 % de las cancelaciones y 47,8 % de los no-show tienen un turno concluido del mismo vehículo; mirando solo hacia adelante, la cancelación efectiva es 23,4 % con `IsReschedule = Y` y 46,4 % con `IsReschedule = N` [T 6.1]. (Ajustado en verificación: 22,3 % de las cancelaciones `Y` tienen un (60) con `IsReschedule = Y` en los 30 días *anteriores*, o sea que se reprogramaron a una fecha más temprana; contando la ventana [−30, +90] la cancelación efectiva `Y` baja a 7,8 % y la `N` a entre 34 % y 46 % [V 8.1, 8.2].)
8. **Hallazgo transversal y crítico para el modelado: `KM` es un snapshot del vehículo, no el km del turno.** Es idéntico en el 100 % de los turnos de un mismo vehículo (82.347 vehículos con `KM` no nulo en ≥ 2 turnos; otros 2.785 lo tienen nulo en todos) y coincide con `VehicleCurrentKM` del último turno en 96,5 % [T 10.1]; `VehicleCurrentKM`, en cambio, se repite en solo 2,5 % de los vehículos con ≥ 2 valores [V 9.1]. Usarlo como feature al momento del scoring es *leakage* del kilometraje futuro. El odómetro real de cada visita es `VehicleCurrentKM` (creciente en 90,9 % de los pares consecutivos; presente en 100 % de los (60), 0 % de los (70)).

---

## 1. Volumen y unidad de análisis

| StatusARG | turnos | % |
|---|---:|---:|
| (60) Concluido | 342.691 | 69,6 |
| (70) Cancelado | 101.222 | 20,6 |
| (80) No asistio | 27.237 | 5,5 |
| (90) Concluido sin OS | 15.507 | 3,1 |
| (30) Agendado | 3.953 | 0,8 |
| (40) En progreso | 1.832 | 0,4 |

[T 0.2]. Las columnas de nivel turno (vehículo, cliente, dealer, fechas, km, estado) no varían dentro de un `schedule_id` salvo en 4-5 turnos [T 0.3], así que colapsar la agenda a una fila por turno (función `appointments()` de `src/repurchase/eventos.py`) no pierde información.

## 2. Taxonomía de ítems y combinaciones por turno (pregunta a)

Clase asignada a cada ítem (612.069 filas) [T 1.1]:

| clase | regla | ítems |
|---|---|---:|
| MANT | `ServiceMaintenance` no nulo (= `N° Maintenance service` / `Nª Maintenance review`) | 268.690 |
| DIAG | `ServiceType = Diagnóstico` | 99.811 |
| CAMPANA_RECALL | `ServiceType` = Campañas de Servicio / Campañas De Servicio (`Service campaign`, `Recall`) | 82.543 |
| SIN_ITEM | `ServiceType` nulo (también `ServiceName` nulo) | 58.275 |
| REPAR | `ServiceType = Reparación` | 42.792 |
| OTRO | Accesorios, Alineación/Balanceo/Cubiertas, Chapa y Pintura, Lavado | 17.571 |
| PUD | Pick Up & Delivery | 16.707 |
| SERV_GRAL | Servicios Generales (Other Services, Alineación y Balanceo, ...) | 10.256 |
| MOVIL | Mobile Service, Taller Móvil | 6.527 |
| GARANTIA | `ServiceName = Guarantee` (viene bajo `ServiceType = Mantenimiento`) | 5.467 |
| ACEITE_FILTRO | `ServiceName = Oil and filter change` (Servicios Generales) | 2.601 |
| INSPECCION | `Inspección Ford`, `Revision de Viaje` (Servicios Generales) | 781 |
| CONTACTLESS | `ServiceName = Contactless service` (Mantenimiento, sin número) | 48 |

Consistencia [T 1.2]: los 268.690 ítems con `ServiceMaintenance` no nulo tienen `ServiceType = Mantenimiento`; no hay ningún ítem "Maintenance service/review" sin número; los 5.515 ítems de `ServiceType = Mantenimiento` sin número son exactamente `Guarantee` (5.467) + `Contactless service` (48). Es decir: **`ServiceMaintenance.notna()` es un identificador limpio del ítem "service del plan"**.

Combinaciones por turno [T 1.3, figura `01_taxonomia_target_combos_status.png`]: hay 262 combinaciones distintas; las 15 más frecuentes cubren 94,8 % de los turnos.

| combinación | (60) | (70) | (80) | (90) | total | % turnos |
|---|---:|---:|---:|---:|---:|---:|
| MANT | 158.565 | 18.110 | 9.564 | 2.470 | 191.019 | 38,8 |
| DIAG | 47.344 | 7.602 | 6.844 | 5.826 | 68.733 | 14,0 |
| SIN_ITEM | 127 | 58.113 | 21 | 8 | 58.271 | 11,8 |
| CAMPANA_RECALL+MANT | 32.599 | 3.771 | 1.772 | 662 | 39.034 | 7,9 |
| REPAR | 24.586 | 3.622 | 2.278 | 1.762 | 32.742 | 6,6 |
| CAMPANA_RECALL | 12.980 | 1.389 | 1.294 | 802 | 16.555 | 3,4 |
| CAMPANA_RECALL+DIAG | 7.462 | 996 | 1.295 | 938 | 10.837 | 2,2 |
| MANT+PUD | 7.428 | 1.161 | 212 | 97 | 9.037 | 1,8 |
| OTRO | 6.916 | 665 | 824 | 423 | 8.902 | 1,8 |
| DIAG+MANT | 6.750 | 848 | 382 | 293 | 8.372 | 1,7 |
| SERV_GRAL | 4.461 | 764 | 432 | 323 | 6.350 | 1,3 |
| CAMPANA_RECALL+REPAR | 3.659 | 442 | 400 | 340 | 4.897 | 1,0 |
| GARANTIA | 3.204 | 321 | 404 | 371 | 4.301 | 0,9 |
| MANT+OTRO | 3.263 | 341 | 199 | 100 | 3.938 | 0,8 |
| MANT+MOVIL | 3.370 | 157 | 122 | 58 | 3.756 | 0,8 |

(Las columnas (30) y (40) están en el apéndice.) Dos lecturas:

- El target preliminar (222.889 turnos) se compone en 71,1 % de turnos "solo mantenimiento", 14,6 % mantenimiento + campaña/recall, 3,3 % mantenimiento + pick-up & delivery, 3,0 % mantenimiento + diagnóstico [T 1.5]. Que el mantenimiento venga acompañado de un recall no cambia que el mantenimiento se hizo: se cuenta como objetivo y el acompañante queda como feature.
- 58.271 turnos no tienen ningún ítem tipado y 58.113 de ellos están cancelados (57,4 % de todas las cancelaciones) [T 6.2]: **para más de la mitad de las cancelaciones no se sabe qué servicio se había reservado**, lo que limita features del tipo "canceló un mantenimiento".

## 3. `(90) Concluido sin OS` (pregunta b)

Perfil por estado [T 2.1, figura `01_taxonomia_target_status90_perfil.png`]:

| StatusARG | % check-in | % check-out | % VehicleCurrentKM | % DaysInDealer | mediana DaysInDealer | % has_maint | % has_diag | % ScheduleReturn = Y | % otro (60) del vehículo en 30 d |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| (60) Concluido | 86,7 | 100,0 | 100,0 | 100,0 | 1 | 65,0 | 19,8 | 8,5 | 10,1 |
| (90) Concluido sin OS | 81,1 | 96,4 | 97,2 | 96,4 | 4 | 26,2 | 48,8 | 17,0 | 19,0 |
| (80) No asistio | 5,7 | 0,1 | 28,1 | 0,1 | 0 | 46,9 | 32,9 | 9,8 | 28,6 |
| (70) Cancelado | 0,0 | 0,0 | 0,0 | 0,0 | – | 25,5 | 10,3 | 0,0 | 57,5 |

- **Se parecen a los concluidos, no a los no-show**: tienen check-in (81,1 %), check-out (96,4 %) y odómetro al ingreso (97,2 %); los no-show no tienen nada de eso. La diferencia con (60) es la ausencia de orden de servicio ("sin OS") y una estadía más larga (mediana 4 días vs 1).
- **Son sobre todo diagnósticos y presupuestos**: 37,6 % solo DIAG, 15,9 % solo MANT, 11,4 % solo REPAR [T 2.2]; el doble de retornos que los (60) (17,0 % vs 8,5 %).
- Cercanía a un (60) del mismo vehículo [T 2.3, n = 15.247 con vehículo]: 16,7 % tiene un (60) en los 30 días previos, 1,4 % el mismo día, 17,4 % en los 30 días siguientes (31,7 % en ±30). Con un (60)+mantenimiento en ±30 días: 13,3 %. Es decir, **no son duplicados de un turno concluido** (menos de un tercio tiene uno cerca).
- Los 3.977 (90) con ítem de mantenimiento [T 2.4]: solo 206 (5,2 %) tienen un mantenimiento (60) en los 30 días siguientes y 542 (13,6 %) en 90 días; 75 % tiene check-in, 96,3 % tiene km. Están repartidos (el dealer con más (90) concentra 10,7 %; 6 de 95 dealers tienen más de 10 % de sus turnos en (90), 7 no tienen ninguno [T 2.5]), lo que sugiere una práctica administrativa de algunos dealers más que un error puntual.
- (Ajustado en verificación.) Que "solo 5 % tenga un (60)+mant en 30 días" **no** prueba que el service no se hizo: si se hubiera hecho sin OS, tampoco reaparecería como (60). El test útil es el número de service del *siguiente* (60)+mant del vehículo [V 2.4, 2.5, 2.8]: tras un (90)+mant, el siguiente repite el **mismo número en 22,2 %** (mediana 88 días y 8.500 km después: volvió por el mismo hito, o sea que no se había hecho), contra 5,3 % tras un (60)+mant; trae n+1 en 56,7 % (vs 77,5 %), pero eso es ambiguo porque el número es un hito de km y avanza igual se haya hecho o no el service anterior. La retención posterior de un (90)+mant (67,2 % con otro (60)+mant en 365 días) queda entre la de un (60)+mant (72,5 %) y la de un (90) sin mantenimiento (62,9 %) [V 2.7]: son clientes que siguen en la red, aunque ese service en particular no tenga OS.

**Recomendación**: `(90)` cuenta como **visita efectiva a la red** (el auto estuvo en el taller; útil como feature de recencia/contacto) y **no** como evento objetivo, ni siquiera cuando trae ítem de mantenimiento: sin OS no hay evidencia de trabajo realizado y en al menos una quinta parte el vehículo vuelve después por el mismo service. Sensibilidad: incluirlos sumaría 4.058 turnos (+1,8 %) y 626 vehículos al target [T 3.5, escenario E]. Conviene que el mentor confirme qué es operativamente un (90).

## 4. Garantía, campañas/recall, cambio de aceite y otros (pregunta c)

| clase (en turnos (60)) | turnos que la incluyen | sin ítem de mantenimiento | solo esa clase (+PUD/móvil) | vehículos (solo esa clase) | vehículos sin ningún (60)+mant |
|---|---:|---:|---:|---:|---:|
| Guarantee | 4.131 | 3.789 | 3.258 | 2.831 | 305 |
| Service campaign / Recall | 65.620 | 27.258 | 13.704 | 11.170 | 2.495 |
| Oil and filter change | 2.021 | 1.127 | 822 | 748 | 189 |
| Contactless service | 39 | 20 | 11 | 11 | 2 |
| Inspección Ford / Revision de Viaje | 486 | 414 | 302 | 293 | 94 |

[T 3.1]. Argumentos [T 3.2, 3.3, 3.4]:

- **Guarantee** (5.467 ítems, todos de 2024, 60 minutos, sin precio fijo): reparación en garantía, sin número de service, mediana de edad 16,5 meses. No es mantenimiento del plan. Además desaparece del catálogo en 2025-2026, con lo que incluirlo sesgaría el target por período.
- **Service campaign / Recall** (82.543 ítems; `Service campaign` hasta enero 2026 y `Recall` desde febrero 2026, con transición en ene-feb igual que "service" → "review": mismo `ServiceType`, renombre [V 3.3]): acción gratuita iniciada por Ford (`ServiceFordFixedPrice = 0` en los 82.543 ítems; el flag `ServiceFordFixedPriceFlag` es `Y` en las 68.316 campañas y `N` en los 14.227 recalls, otro artefacto del renombre [V 3.4]), con vehículos jóvenes (mediana 13,6 meses, 24.174 km). No mide la decisión del cliente de mantener el auto en la red. Es la clase con mayor impacto si se incluyera: +31.707 turnos y +5.903 vehículos. Se recomienda excluirla del objetivo y usarla como feature ("tuvo recall pendiente/realizado").
- **Oil and filter change** (2.601 ítems, solo 2026, 87 dealers, ninguno concentra más de 19,8 %): mediana de edad 32,8 meses y 65.496 km, pero **no son vehículos fuera del ciclo del plan** (ajustado en verificación): 49 % de los ítems son ModelYear 2024-2025, la mitad P703 [V 3.6]. En 41,8 % de los turnos viene junto con un ítem de mantenimiento (ahí ya cuenta). Los 822 turnos (60) "solo aceite y filtro" (748 vehículos; 189 sin ningún mantenimiento (60) en el período) tienen en 74,6 % un (60)+mant anterior del mismo vehículo, y el cambio de aceite cae a una mediana de **14.793 km después de ese service en P703 (p25-p75 9.206-19.712; el hito es 15.000) y 12.752 km en P375** [V 3.7]: es el momento en que tocaba el siguiente service del plan. Solo 6,1 % tiene un (60)+mant posterior (con poco seguimiento: el ítem existe desde 2026). La lectura más plausible es un *sustituto más barato del service del plan en el hito* (aparece justo cuando las primeras P703 de 2023 cumplen 3 años), no un servicio suelto. Se excluye por defecto para respetar la definición "N° Maintenance service", pero **es la decisión con más riesgo de etiquetar como churn a clientes que sí volvieron a la red** (el efecto es +0,5 % sobre todo el período pero +1,4 % de los eventos de 2026, y creciente) y va como pregunta prioritaria al mentor.
- **Contactless service** (48 ítems de 2024) e **Inspección Ford / Revisión de viaje** (781 ítems): volumen marginal, sin número de service; se excluyen.

Escenarios [T 3.5, figura `01_taxonomia_target_escenarios_target.png`]:

| definición del evento objetivo | turnos | vehículos | Δ turnos vs A |
|---|---:|---:|---:|
| A. (60) & ítem Maintenance service/review [preliminar] | 222.889 | 87.531 | 0 |
| B. A + Oil and filter change | 224.016 | 87.821 | +1.127 |
| C. B + Guarantee | 227.805 | 88.156 | +4.916 |
| D. C + Campañas/Recall | 254.596 | 93.434 | +31.707 |
| E. A + (90) con ítem mantenimiento | 226.947 | 88.157 | +4.058 |
| F. Visita efectiva: (60) o (90), cualquier ítem | 358.198 | 105.709 | +135.309 |

## 5. Numeración de `ServiceMaintenance` (pregunta d)

**5.1 El patrón 11→"1°", 13→"13°"/"3ª", 20→"20°"/"20ª"** [T 4.1]: para n = 1..10 el nombre coincide con el número. Para n = 11, 12, 14, 16, 17, 18, 19 el nombre muestra el último dígito (`1° Maintenance service` con n = 11: 5.027 ítems; `2°` con 12: 4.371; `4°` con 14: 2.849; ...). Para n = 13, 15 y 20 existe un nombre propio en la familia "service" (`13° Maintenance service` 3.467, `15°` 2.303, `20°` 3.321), pero la familia "review" también los muestra como `3ª`, `5ª` (solo `20ª` conserva el 20). Es un defecto de la tabla de nombres del catálogo (faltan las etiquetas 11-19 y se rellenan con n mod 10), no del número: el número es coherente con el kilometraje (ver 5.4).

**5.2 "Maintenance service" vs "Maintenance review" es un renombre en el tiempo, no dos catálogos** [T 4.2, 4.3, figura `01_taxonomia_target_catalogo_mes.png`]: primer ítem "review" el 2025-12-30; en enero 2026 conviven (2.477 review / 8.390 service), en febrero ya es 7.951 / 536 y desde marzo prácticamente solo "review" (10.209 / 21). Desde 2026-02 el mínimo de "review" por dealer es 92,4 % (21 de 94 dealers tienen algún residuo "service"). Las dos familias aparecen en ambas generaciones (review: P375 19.652, P703 47.493) y en todas las fuentes de agenda [T 4.4, 4.5]. Conclusión: se deben tratar como la misma clase, cosa que la regla `ServiceMaintenance.notna()` ya hace.

**5.3 ¿De qué depende n ≥ 11?** De la generación y la antigüedad, no del dealer ni de la fuente [T 4.6, 4.7]: 22,9 % de los ítems de P375 tiene n ≥ 11 vs 1,3 % en P703; por año modelo: 58,3 % (2012), 49,1 % (2017), 28,2 % (2021), 8,6 % (2023), 1,4 % (2024). Son vehículos viejos con muchos services, no un catálogo distinto.

**5.4 n es un hito de kilómetros: 15.000 km por service en P703 y 10.000 km en P375** [T 4.8, 4.9, figura `01_taxonomia_target_km_por_n.png`], medido con el odómetro al ingreso (`VehicleCurrentKM`) en turnos (60):

| n | P703 ítems | P703 mediana km ingreso | P703 mediana edad (meses) | P375 ítems | P375 mediana km ingreso | P375 mediana edad (meses) | ServiceMonth (=12n) |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 44.325 | 16.008 | 8,4 | 4.445 | 11.060 | 12,2 | 12 |
| 2 | 28.230 | 32.130 | 14,5 | 7.690 | 20.548 | 18,9 | 24 |
| 3 | 14.926 | 48.416 | 17,7 | 10.467 | 30.614 | 24,3 | 36 |
| 4 | 7.905 | 64.650 | 19,8 | 10.872 | 40.696 | 28,1 | 48 |
| 5 | 4.100 | 80.710 | 21,4 | 11.225 | 50.870 | 31,5 | 60 |
| 6 | 2.265 | 96.481 | 22,4 | 11.974 | 61.242 | 36,5 | 72 |
| 8 | 766 | 126.269 | 24,0 | 8.342 | 81.110 | 40,3 | 96 |
| 10 | 171 | 152.229 | 25,0 | 6.774 | 101.265 | 45,3 | 120 |
| 15 | 33 | 32.992 | 11,5 | 2.432 | 151.208 | 53,8 | 180 |
| 20 | 73 | 2.628 | 2,4 | 3.416 | 221.749 | 82,6 | 240 |

- P703: mediana de `VehicleCurrentKM / n` = 16.073; 75,4 % de los ítems está dentro de ±20 % de n×15.000 (solo 8,1 % de n×10.000). P375: mediana 10.161; 78,5 % dentro de ±20 % de n×10.000. **La regla "15.000 km" del tutor vale para P703; la generación anterior (P375, 2012-2023) va cada 10.000 km.** Esto es central para definir la ventana (tema de otro EDA): no se puede usar un único intervalo en km para todo el parque.
- `ServiceMonth` (= 12n) es la cadencia nominal "un service por año", pero la edad real al n-ésimo service es mucho menor: mediana (edad − ServiceMonth) = −17,5 meses; solo 24,2 % de los ítems está a ±6 meses. En P703 el 1° service se hace a los 8,4 meses (mediana) y el 2° a los 14,5: **la mayoría llega a los 15.000 km antes del año**, así que la regla "lo que ocurra primero" la dispara el km.
- (Ajustado en verificación.) Las edades por n están **sesgadas hacia abajo por censura**: los ítems de vehículos con garantía iniciada en 2025-2026 solo pueden tener edades cortas (los que tardan más todavía no llegaron). Restringiendo el 1° service P703 a la cohorte con garantía iniciada en 2024-H1 (≥ 26 meses de seguimiento, 7.316 ítems), la mediana es **9,1 meses** (p75 11,9, p90 13,8) y 77,6 % ocurre antes de los 12 meses (80,5 % en el pooled) [V 4.4, 4.5, figura `01_taxonomia_target_verif_edad_1er_service_cohorte.png`]. La distribución es bimodal: un bloque de 4 a 10 meses (llegan a 15.000 km) y un pico nítido en los 11-12 meses (los que no llegan al km y entran por la regla del año). La conclusión "el km dispara antes que el año" se mantiene, con ~78 % y no ~80 %.
- En P703 los ítems con n ≥ 11 son menos de 100 por número y tienen km bajísimos (n = 20: 2.628 km, 2,4 meses): son errores de carga del catálogo, no vehículos con 20 services. En la figura no se grafican los n de P703 con menos de 100 ítems.

**5.5 ¿Se puede confiar en `maint_number` como "n-ésimo service del vehículo"?** Como *índice de km del plan*, sí; como *contador exacto* de visitas, con ruido [T 4.10, 4.11, figura `01_taxonomia_target_delta_n.png`]:

| métrica | valor |
|---|---:|
| pares consecutivos de (60)+mant del mismo vehículo | 134.172 |
| Δn = +1 | 77,5 % |
| Δn = 0 (mismo número dos veces) | 5,3 % |
| Δn < 0 | 4,7 % |
| Δn > 1 (saltos: services hechos afuera o no registrados) | 12,5 % |
| vehículos con ≥ 2 mantenimientos (60) | 55.815 |
| ... con secuencia no decreciente | 90,7 % |
| ... con secuencia estrictamente creciente | 82,2 % |
| mediana de días entre mantenimientos consecutivos | 161 |
| mediana Δ VehicleCurrentKM cuando Δn = +1 | 12.434 (pooled; P703 16.093, P375 10.234 [V 6.2]) |
| vehículos de SALES (vendidos 2024-2026): 1er mantenimiento observado con n = 1 | 92,0 % (33.979 de 36.950) |

Implicancia: `maint_number` sirve como feature ("en qué hito del plan está el vehículo") y para inferir el próximo hito en km, pero el conteo de mantenimientos observados debe hacerse contando eventos (60)+mant, no leyendo n. Un salto Δn > 1 (12,5 %) es en sí una señal de "se saltó un service" o "lo hizo fuera de la red". (Ajustado en verificación.) Los pares con **el mismo número** se dividen en dos poblaciones [V 6.3]: a ≤ 30 días (1.087 pares) tienen Δ km mediana 0 y son el mismo service cargado dos veces (los descarta la deduplicación); a > 30 días (5.991 pares) tienen Δ km mediana de 10.000-12.400, o sea son visitas reales a un intervalo de distancia con el número mal cargado. Tras la deduplicación, Δn = 0 baja a 4,5 % y Δn = +1 sube a 78,2 % [V 6.1].

## 6. `IsReschedule` y `ScheduleReturn` (pregunta e)

**`IsReschedule`** [T 5.1, 5.2]:

| IsReschedule | (60) | (70) | (80) | (90) | (30)+(40) | total |
|---|---:|---:|---:|---:|---:|---:|
| nulo | 297.026 | 0 | 23.607 | 13.595 | 5.029 | 339.257 |
| N | 0 | 32.439 | 1 | 0 | 0 | 32.440 |
| Y | 45.665 | 68.783 | 3.629 | 1.912 | 756 | 120.745 |

- `N` aparece **solo** en cancelados y coincide 1:1 con `ScheduleStatus` crudo = `(70) Cancelado` (32.439); `Y` en cancelados coincide 1:1 con `ScheduleStatus` crudo nulo (68.782). O sea, en la fuente hay dos tipos de cancelación: la "dura" (N) y la que se produce al reprogramar (Y, el turno viejo queda cancelado y se crea uno nuevo).
- `Y` en un (60) significa "este turno nació de una reprogramación": 57,7 % tiene como turno inmediato anterior un (70) del mismo vehículo a ≤ 14 días (vs 3,0 % cuando `IsReschedule` es nulo), mediana 7 días desde el turno anterior [T 5.6]; contando cualquier (70) del vehículo en los 14 días previos (no solo el inmediato anterior) es 69,7 % vs 4,0 % [V 7.3] (ajustado en verificación).
- `Y` en un (70): 64,3 % tiene otro turno del mismo vehículo a ≤ 14 días después (71,3 % a 30 días; mediana 6 días); con `N`: 34,9 % / 44,1 % (mediana 21 días) [T 5.6].

**`ScheduleReturn`** [T 5.3-5.6, figura `01_taxonomia_target_return_lag.png`]:

| ScheduleReturn | turnos | % turno previo ≤ 30 d | % previo (60) ≤ 30 d | mediana días desde el previo | % has_maint | % has_diag | % has_repair | % Dealer como fuente |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Y | 35.172 | 98,0 | 74,2 | 15 | 14,1 | 37,4 | 30,4 | 90,6 |
| N | 345.471 | 16,9 | 3,1 | 93 | 66,3 | 20,7 | 7,8 | 76,0 |
| nulo | 111.799 (101.219 cancelados) | – | – | – | 30,8 | 10,7 | 4,1 | – |

(Las columnas "% previo" de la tabla miran solo el turno inmediato anterior del vehículo; contando cualquier (60) del vehículo en los 30 días previos, `ScheduleReturn = Y` tiene uno en 88,4 % [V 7.4].) **Sí: `ScheduleReturn = Y` es un "turno de retorno"** (segunda visita a corto plazo, generalmente por diagnóstico/reparación tras una visita concluida, cargada por el dealer). Hay 4.380 turnos (60)+mantenimiento con `ScheduleReturn = Y`: se mantienen como objetivo (un retorno que incluyó el service sigue siendo un service hecho), y la deduplicación de la sección 8 cubre los casos en que es el mismo service repetido.

Implicancias para features: `ScheduleReturn = Y` es una señal de problema no resuelto en la visita anterior (posible insatisfacción); `IsReschedule` permite separar cancelación dura de reprogramación. Ninguna de las dos define el evento objetivo.

## 7. Cancelaciones y no-show: reprogramación vs pérdida (pregunta f)

Turnos con `ScheduleDate ≤ CUTOFF − 90 días` (seguimiento completo) y existencia de un turno (60) del mismo vehículo entre 0 y N días después [T 6.1, figura `01_taxonomia_target_seguimiento.png`]:

| caso | turnos | ≤ 30 d | ≤ 60 d | ≤ 90 d | "efectivo" a 90 d |
|---|---:|---:|---:|---:|---:|
| (70) Cancelado → algún (60) | 89.858 | 57,5 % | 64,2 % | 69,1 % | 30,9 % |
| (70) & IsReschedule = Y → algún (60) | 60.286 | 66,9 % | 72,5 % | 76,6 % | 23,4 % |
| (70) & IsReschedule = N → algún (60) | 29.572 | 38,3 % | 47,2 % | 53,6 % | 46,4 % |
| (70) con ítem mant → (60)+mant | 22.620 | 39,1 % | 43,9 % | 49,7 % | 50,3 % |
| (80) No asistió → algún (60) | 24.460 | 28,6 % | 39,7 % | 47,8 % | 52,2 % |
| (80) con ítem mant → (60)+mant | 11.397 | 34,8 % | 44,3 % | 50,3 % | 49,7 % |
| (90) Concluido sin OS → algún (60) | 13.885 | 19,0 % | 31,4 % | 40,7 % | – |
| (60) Concluido → otro (60) distinto [base] | 308.816 | 10,1 % | 19,5 % | 29,5 % | – |

- Una cancelación tiene 5,7 veces más probabilidad que un turno concluido de ir seguida de un (60) en 30 días (57,5 % vs 10,1 %): en su mayoría es reprogramación. Con `IsReschedule = N` la mitad (46,4 %) no vuelve en 90 días: es la "cancelación efectiva".
- (Ajustado en verificación.) La ventana [0, N] **subestima la reprogramación**, porque el turno nuevo puede caer *antes* de la fecha cancelada: 22,3 % de las cancelaciones `Y` tienen un (60) con `IsReschedule = Y` del mismo vehículo en los 30 días anteriores, y 92,2 % tienen algún (60) en [−30, +90] [V 8.2]. Con esa ventana la cancelación efectiva `Y` es 7,8 % (no 23,4 %); para `N` es 34,0 % con [−30, +90] y 46,4 % con [0, 90] (el (60) previo de una `N` puede ser una visita anterior no relacionada, así que la cifra real está entre ambas) [V 8.1]. El no-show tiene un (60) en [−30, +90] en 57,5 %. El orden se mantiene: `N` y no-show son las pérdidas; `Y` casi nunca lo es.
- El no-show es peor señal que la cancelación: 52,2 % no tiene ningún turno concluido en 90 días. Cuando el turno perdido era un mantenimiento, solo la mitad (50,3 %) lo concreta en 90 días.
- Para el modelo: cancelaciones y no-show **no son eventos objetivo ni negativos por sí mismos**; son features de comportamiento (conteos y recencia, separando `IsReschedule` N/Y), y el desenlace lo define únicamente si aparece un (60)+mant en el horizonte.

## 8. Duplicados lógicos (pregunta g)

- **Mismo vehículo, mismo día**: 27.387 turnos son el segundo de un par del mismo día (5,6 % de los turnos con vehículo); 95,6 % en el mismo dealer [T 7.1]. La mayoría son cancelación + turno nuevo del mismo día ((70)→(60): 8.389; (60)→(70): 8.273; (70)+(70): 4.312), o sea reprogramaciones intradía, no dobles visitas. Pares (60)+(60) el mismo día: 3.443, en general con ítems distintos (p. ej. mantenimiento en un turno y recall en otro); la deduplicación de la sección 12 descarta solo 335 segundos mantenimientos del mismo día.
- **A 1-3 días**: 28.498 pares; (70)→(60): 10.517, (60)→(70): 7.485, (60)+(60): 2.217 [T 7.2].
- **Entre mantenimientos completados** [T 7.3]: de 134.172 pares consecutivos de (60)+mant del mismo vehículo, 663 están a ≤ 3 días (71,8 % con el mismo `maint_number` y 74,4 % con |Δ km| ≤ 500: claramente el mismo service cargado dos veces) y 1.538 a 4-30 días (39,7 % mismo número; pero 32,3 % con Δn = +1 y Δ km mediana 1.550, que pueden ser flotas de alto uso).

**Tratamiento propuesto** (incorporado en la regla final): (1) un solo evento objetivo por vehículo y día (se conserva el primero); (2) si dos eventos del mismo vehículo tienen el mismo `maint_number` a ≤ 30 días, se conserva el primero. Descarta 335 + 846 = 1.181 turnos (0,5 % de los candidatos) [T 11.1]. Los pares con Δn = +1 a pocos días se mantienen: no se puede afirmar que sean duplicados. Para el resto de los estados no hace falta deduplicar: los (70)/(80) se usan como conteos y el par intradía (70)+(60) es exactamente el comportamiento que queremos medir.

## 9. Turnos sin `vehicle_id` o sin `customer_id` (pregunta h)

| | (30) | (40) | (60) | (70) | (80) | (90) | total | de los cuales (60)+mant |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| sin vehicle_id | 40 | 20 | 2.066 | 1 | 510 | 260 | 2.897 (0,6 %) | 1.186 |
| sin customer_id | 96 | 59 | 6.294 | 2.110 | 611 | 228 | 9.398 (1,9 %) | 3.948 |
| sin ambos | 2 | 1 | 293 | 0 | 87 | 35 | 418 | – |

[T 8.1, 8.2]. Los turnos sin vehículo son todos de fuente `Dealer` (2.896 de 2.897), no tienen `WarrantyStartDate` ni `ModelYear` (0 %), la generación viene como "RANGER" genérico en 1.912 casos, y están repartidos en 77 dealers (el principal concentra 11,3 %): parecen turnos cargados a mano sin VIN. **Decisión: se excluyen de la tabla de eventos** (no se pueden asignar a ningún usuario-vehículo-ventana); pierden 1.186 mantenimientos (0,5 %). Los 8.980 turnos con vehículo pero sin cliente **se conservan como eventos del vehículo** (el target es por vehículo); en 5.117 de ellos el vehículo tiene `customer_id` en otro turno, así que el cliente se puede recuperar por el linkage (tema del EDA de linkage, no de este).

## 10. `Region` y `DealerStateOrZone` (pregunta i)

| Region | dealers | turnos | % turnos | 2024 | 2025 | 2026 | % (60) |
|---|---:|---:|---:|---:|---:|---:|---:|
| 60 | 80 | 408.470 | 82,95 | 134.222 | 160.804 | 113.444 | 69,2 |
| 00 | 11 | 77.931 | 15,83 | 26.105 | 31.003 | 20.823 | 70,7 |
| 31 | 1 | 5.910 | 1,20 | 2.077 | 2.291 | 1.542 | 80,1 |
| A | 3 | 131 | 0,03 | 0 | 0 | 131 | 39,7 |

[T 9.1-9.5]. Hechos verificables:

- **Ambos campos son constantes por dealer** (0 de 95 dealers con más de una `Region` o más de una `DealerStateOrZone`): son atributos del dealer, no del turno ni del vehículo. Para modelar, `dealer_id` los contiene.
- `Region` no es geográfica: los 11 dealers de `00` venden en Buenos Aires (3), Misiones (2), Santa Fe, Santa Cruz, Córdoba, Entre Ríos y 2 no aparecen en SALES; `31` es un solo dealer bonaerense; `A` son 3 dealers que solo aparecen en 2026 con 131 turnos (uno de ellos con `DealerStateOrZone` nulo). No se puede afirmar que "60 = Argentina": todos los dealers son argentinos (SALES tiene solo provincias argentinas). La hipótesis más plausible es un código de región/sistema del dealer (p. ej. red propia vs. agrupada), a confirmar con el mentor.
- `DealerStateOrZone` (1-5) sí tiene estructura geográfica aproximada de zona comercial [T 9.3]: zona 5 concentra Patagonia (Chubut, Neuquén, Santa Cruz, Tierra del Fuego) más dealers de Buenos Aires/Capital; zona 2 el Litoral/NEA (Misiones, Santa Fe, Chaco, Corrientes, Entre Ríos); zona 3 Centro/NOA (Córdoba, Catamarca, Tucumán, Santiago del Estero); zona 4 Buenos Aires (10 dealers) más Cuyo/NOA (Mendoza, Salta, Jujuy, La Pampa); zona 1 solo Buenos Aires y Capital. Dealers por zona: 15 / 17 / 18 / 23 / 20.
- Cruce de dealers: SALES tiene 107 `dealer_id`, AGENDA 95, en común 61 (34 dealers solo en agenda, 46 solo en ventas). Vale la pena confirmar con el mentor si el seudonimizado del dealer es el mismo en ambas fuentes.

## 11. Hallazgo transversal: `KM` vs `VehicleCurrentKM`

No era pregunta de este tema pero afecta la definición de ventana y a todas las features de kilometraje [T 10.1, 10.2, figura `01_taxonomia_target_km_vs_vck.png`]:

| métrica | valor |
|---|---:|
| vehículos con ≥ 2 turnos | 85.143 |
| ... con `KM` no nulo en ≥ 2 turnos / % con un único valor de `KM` | 82.347 / 100,0 % |
| ... con `VehicleCurrentKM` no nulo en ≥ 2 turnos / % con un único valor | 75.688 / 2,5 % (corregido en verificación: antes se informaba 13,3 % porque se contaban como "constantes" los vehículos con la columna nula o con un solo valor) |
| pares de turnos consecutivos (> 30 días) con `VehicleCurrentKM`: creciente / igual / decreciente | 90,9 % / 6,0 % / 3,2 % |
| último turno del vehículo: \|KM − VehicleCurrentKM\| ≤ 1.000 | 96,5 % |
| primer turno del vehículo: \|KM − VehicleCurrentKM\| ≤ 1.000 | 30,1 % |
| primer turno del vehículo: KM > VehicleCurrentKM + 1.000 | 67,0 % |

En el 1° service de P703 la mediana de `VehicleCurrentKM` es 16.008 km (p25-p75: 14.446-16.908, el pico de 15.000 km que se ve en la figura), mientras que `KM` da 31.498 (p75 48.700): `KM` es el kilometraje del vehículo al momento de la extracción (o del último dato conocido), copiado en todas sus filas. **Usar `KM` como feature al abrir una ventana pasada es leakage** (incorpora kilómetros recorridos después del scoring). El km del turno es `VehicleCurrentKM`, que existe en 100 % de los (60) y 97,2 % de los (90), pero en 0 % de los (70) y 28,1 % de los (80).

## 12. Regla final propuesta

Reproducible en pandas sobre la salida de `appointments()` (`src/repurchase/eventos.py`); es la función `regla_eventos()` del script:

```python
def regla_eventos(ap):
    out = ap.copy()
    base = out["vehicle_id"].notna() & (out["ScheduleDate"] <= CUTOFF)
    # (2) visita efectiva a la red: el auto entró al taller (check-out en 100 % de (60) y 96 % de (90))
    out["visita_red"] = base & (out["completed"] | out["completed_no_os"])
    # (1) mantenimiento programado completado: (60) Concluido + algún ítem con ServiceMaintenance no nulo
    cand = out["visita_red"] & out["completed"] & out["has_maint"]
    c = out.loc[cand, ["schedule_id", "vehicle_id", "event_date", "maint_number"]] \
           .sort_values(["vehicle_id", "event_date", "schedule_id"])
    dup_day = c.duplicated(["vehicle_id", "event_date"], keep="first")      # un evento por vehículo y día
    c1 = c[~dup_day]
    prev_date = c1.groupby("vehicle_id")["event_date"].shift(1)
    prev_n = c1.groupby("vehicle_id")["maint_number"].shift(1)
    dup_n = (c1["maint_number"] == prev_n) & ((c1["event_date"] - prev_date).dt.days <= 30)  # mismo service repetido
    keep = set(c1.loc[~dup_n, "schedule_id"])
    out["mant_completado"] = cand & out["schedule_id"].isin(keep)
    return out
```

donde `completed = StatusARG == '(60) Concluido'`, `completed_no_os = StatusARG == '(90) Concluido sin OS'`, `has_maint` = algún ítem con `ServiceMaintenance` no nulo y `event_date = EffectiveCheckinDate` **cuando está a ±45 días de `ScheduleDate`** (si no, o si es nulo, `ScheduleDate`; en el target hay 79 turnos con check-in a más de 45 días del turno que caen en `ScheduleDate`). Nota de verificación: la regla (2) compara cada evento con el anterior *por fecha*, aunque ese anterior ya haya sido marcado duplicado (efecto cadena); una variante que compara con el último evento *conservado* descarta 836 en vez de 846 (10 eventos de diferencia, 220.532 vs 220.522) [V 1.1]. Es irrelevante para el volumen; se deja la versión actual por simplicidad.

Conteos [T 11.1, 11.2]:

| | turnos | vehículos |
|---|---:|---:|
| **(2) visita_red**: (60) o (90), con vehicle_id, ScheduleDate ≤ CUTOFF | **355.872** | **105.709** |
| candidatos a objetivo: (60) & has_maint (definición preliminar) | 222.889 | 87.531 |
| − excluidos por no tener vehicle_id | 1.186 | – |
| − descartados: segundo (60)+mant del mismo vehículo el mismo día | 335 | 330 |
| − descartados: mismo maint_number que el anterior a ≤ 30 días | 846 | 800 |
| **(1) mant_completado (evento objetivo)** | **220.522** | **87.531** |

Por año de `event_date`: 2024: 73.361 mantenimientos / 119.536 visitas; 2025: 87.153 / 142.805; 2026 (hasta el 25/8): 60.008 / 93.531.

Fecha del evento [T 11.4]: el target tiene `EffectiveCheckinDate` en 88,4 % y `EffectiveCheckoutDate` en 100 %; el check-in coincide con `ScheduleDate` en 84,3 % y difiere más de 7 días en 0,5 % (49 casos con check-in > 30 días antes del turno y 55 con > 30 días después, que parecen errores de carga); el check-out cae entre 0 y 3 días después de `event_date` en 82,9 %. La definición preliminar de `event_date` es razonable; si se quiere una sola fuente sin nulos, `EffectiveCheckoutDate` es la alternativa (sería "fecha en que el service quedó terminado").

Casos borde y decisión [T 11.3]:

| caso borde | turnos | decisión |
|---|---:|---|
| (60) con ítem mantenimiento + otros ítems (recall, diagnóstico, PUD...) | 64.371 | objetivo; los demás ítems son features |
| (60) solo campaña/recall | 13.704 | visita, no objetivo |
| (60) solo Guarantee | 3.258 | visita, no objetivo |
| (60) solo Oil and filter change | 822 | visita, no objetivo (consultar con el mentor) |
| (60) solo Contactless service | 11 | visita, no objetivo |
| (60) solo Inspección Ford / Revisión de viaje | 302 | visita, no objetivo |
| (60) solo diagnóstico / reparación / otros | 87.706 | visita, no objetivo |
| (90) con ítem mantenimiento | 4.058 | visita, no objetivo (sin OS) |
| (90) sin ítem mantenimiento | 11.449 | visita, no objetivo |
| (40) En progreso con check-in y ScheduleDate ≤ CUTOFF | 1.825 | censurado: no usar como negativo |
| (30) Agendado (3.321 con fecha posterior al CUTOFF) | 3.953 | nada; feature "turno futuro reservado" |
| (70) Cancelado | 101.222 | nada como evento; feature (separar IsReschedule N/Y) |
| (80) No asistió | 27.237 | nada como evento; feature |
| Sin vehicle_id | 2.897 | excluir de eventos |
| Con vehicle_id, sin customer_id | 8.980 | evento del vehículo; cliente por linkage |
| Segundo (60)+mant del mismo vehículo el mismo día | 335 | un solo evento (se conserva el primero) |
| (60)+mant con el mismo maint_number que el anterior a ≤ 30 días | 846 | un solo evento (se conserva el primero) |
| (60)+mant sin EffectiveCheckinDate | 26.213 | objetivo; event_date = ScheduleDate |
| (60)+mant con ScheduleReturn = Y | 4.380 | objetivo |
| (60)+mant con maint_number menor que el anterior del vehículo | 6.264 | objetivo; maint_number es ruidoso como contador |

## 13. Implicancias para target, ventana y features

- **Target**: `mant_completado` como está arriba. La sensibilidad de volumen relevante es campañas/recall (+14 % de eventos si se incluyera), y el argumento para excluirlas es sólido (gratuitas, iniciadas por Ford, no miden la decisión del cliente). La sensibilidad de *significado* relevante es `Oil and filter change` (ajustado en verificación): poco volumen (+0,5 % del período, +1,4 % de los eventos de 2026), pero son vehículos que estaban en el plan y vuelven en el hito de km por un service más barato; si negocio lo considera "mantenimiento en la red", hay que sumarlo al target (escenario B) para no fabricar churn en 2026. Churn = 1 si no aparece ningún `mant_completado` del vehículo dentro del horizonte posterior al scoring.
- **Ventana** (tema del EDA 02, se señala sin redefinir): el hito de km es 15.000 km en P703 y 10.000 km en P375; el 1° service de P703 llega a los 8,4 meses de mediana, antes del año. El km al abrir la ventana debe construirse con `VehicleCurrentKM` del último evento (nunca con `KM`), proyectado con la tasa de uso del vehículo.
- **Features que este EDA habilita**: `visita_red` (recencia y conteo de contactos con la red, incluye (90)); conteos de (70) separados por `IsReschedule` N/Y y de (80); `ScheduleReturn = Y` como señal de problema no resuelto; `maint_number` del último service y saltos Δn > 1 (services saltados o hechos fuera de la red); recalls realizados/pendientes; fuente del turno. Todas calculables al momento del scoring con `ScheduleDate`/`event_date` anteriores al mismo.
- **Censura**: (40) En progreso abiertos al corte (1.825 con check-in) y (30) Agendado con fecha futura (3.321) indican intención de volver pero no un resultado: las ventanas cuyo horizonte incluye el CUTOFF no pueden etiquetarse.

## 14. Problemas de calidad de datos

1. `KM` es un snapshot del vehículo copiado en todas sus filas (100 % constante): no usar como feature histórica; el km por visita es `VehicleCurrentKM` (nulo en cancelados y en 72 % de los no-show).
2. 19.554 filas ítem totalmente duplicadas (3,1 %) en el extracto crudo; se eliminan antes de agregar.
3. 58.271 turnos sin ningún ítem tipado, 58.113 cancelados: no se sabe qué reservaban en 57 % de las cancelaciones.
4. `ServiceName` con números incorrectos para `ServiceMaintenance` 11-19 (muestra n mod 10) y en la familia "review" también para 13 y 15; usar siempre el número.
5. Renombres del catálogo en 2026: "Maintenance service" → "Maintenance review" (ene-feb 2026), "Service campaign" → "Recall" (2026), aparición de "Oil and filter change" (solo 2026) y desaparición de "Guarantee" (solo 2024). Cualquier feature por nombre de servicio debe usar clases, no nombres.
6. En P703 hay ítems con n = 11-20 y menos de 100 casos por número, con km incompatibles (n = 20 a 2.628 km): errores de carga; para P703 conviene acotar `maint_number` a 1-10 o marcarlo como sospechoso.
7. 2.897 turnos sin `vehicle_id` (todos de fuente Dealer, sin garantía ni año modelo) y 9.398 sin `customer_id`.
8. `EffectiveCheckinDate` con valores anómalos: mínimo 2001-10-12, 4 filas ítem anteriores a 2024; 49 eventos objetivo con check-in > 30 días antes del turno y 55 con > 30 días después [T 11.4].
9. 4 turnos con dos `StatusARG` distintos entre sus ítems ((70) y (80)); irrelevante en volumen.
10. `dealer_id`: 34 dealers solo en agenda y 46 solo en ventas; solo 61 en común.

## 15. Preguntas para el mentor

1. ¿"Mantenimiento programado" para negocio es exactamente el ítem `N° Maintenance service/review` (`ServiceMaintenance` no nulo)? ¿`Oil and filter change` (2026, 2.601 ítems; 3 de cada 4 turnos "solo aceite" son de vehículos que venían haciendo services del plan y vuelven ~15.000 km después del último) es una oferta nueva de 2026 que reemplaza al service del plan (p. ej. para vehículos fuera de garantía) o un servicio suelto? Si es lo primero, tiene que contar como retorno.
2. ¿Qué es operativamente `(90) Concluido sin OS`? ¿El vehículo se atendió sin abrir orden de servicio (p. ej. presupuesto rechazado, recall sin repuesto) o es un cierre administrativo? Confirmar que no debe contar como retorno.
3. Confirmar los intervalos de plan por generación: 15.000 km / 12 meses para P703 y 10.000 km / 12 meses para P375 (los datos muestran exactamente eso). ¿Aplica algo distinto a Raptor?
4. ¿Por qué `ServiceMaintenance` 11-19 se muestra con los nombres 1°-9°? ¿El catálogo tiene solo 10 (+13, 15, 20) etiquetas?
5. `IsReschedule`: ¿confirma que `N` = cancelación del cliente/dealer y `Y` = turno reprogramado (cancelación automática del turno original)? ¿Existe la fecha de cancelación en la fuente (`CancellationReason` viene 100 % nulo)?
6. `ScheduleReturn = Y`: ¿es "retorno por el mismo problema" (garantía de reparación) o cualquier segunda visita a corto plazo?
7. `Region` (60 / 00 / 31 / A): ¿qué codifica? Es constante por dealer y no es geográfico. ¿`DealerStateOrZone` es la zona comercial de Ford Argentina?
8. `KM`: ¿es el último odómetro conocido del vehículo a la fecha de la extracción? Si es así, no puede formar parte del dataset de scoring histórico; ¿se puede reextraer como km al turno o se confirma que `VehicleCurrentKM` es ese dato?
9. Turnos sin `vehicle_id` (2.897) y `dealer_id` que no cruzan entre SALES y AGENDA (34 + 46): ¿es un tema del seudonimizado o son dealers distintos (venta vs. posventa)?
