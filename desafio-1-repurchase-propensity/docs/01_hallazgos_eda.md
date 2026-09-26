# 01 — Hallazgos integrados del EDA: qué dicen los datos sobre población, ventana, target y features

> Síntesis de los seis temas de EDA (`reports/eda/01_*.md` a `06_*.md`), cada uno verificado de forma
> adversarial por un segundo análisis (`reports/eda/0N_*_verificacion.md`). Todas las cifras de este documento
> salen de esos informes ya corregidos; cuando un número cambió en la verificación se cita el corregido. Las
> referencias entre corchetes indican el informe y la tabla o sección de origen (p. ej. [02 f2] = EDA 02, tabla f2).
> Datos: agenda Ford 2024-01-01 → 2026-08-25 (CUTOFF) y ventas 2024-01-01 → 2026-08-24. Las contradicciones
> entre informes y cómo se resolvieron están en el Anexo A.

Este documento alimenta tres cosas: la definición reproducible del target (sección 3), el pipeline de features
(sección 5) y el capítulo "Datos y EDA" del PDF (secciones 1, 2 y 9). Lo que se decidió a partir de esto está en
`docs/02_decisiones_y_descartes.md`.

---

## 1. Resumen ejecutivo (lo que el jurado tiene que saber)

1. **El dataset es transaccional y grande, no una foto por cliente**: 631.623 filas-ítem de agenda (19.554
   duplicadas exactas) que colapsan a **492.442 turnos de 111.752 vehículos** (todo el parque Ranger que pasó por
   la red 2024-2026, ModelYear 2005-2026) y **59.384 ventas 0 km** (45.959 compradores). Universo de vehículos:
   128.925 (42.211 en ambas tablas, 69.541 sólo agenda, 17.173 sólo ventas) [01 §1; 03 §0].
2. **El evento objetivo es limpio y reproducible**: turno `(60) Concluido` con al menos un ítem con
   `ServiceMaintenance` no nulo (el service numerado del plan). Con `vehicle_id`, fecha ≤ CUTOFF y deduplicación
   quedan **220.522 mantenimientos completados en 87.531 vehículos** (73.361 en 2024, 87.153 en 2025, 60.008 en
   2026 hasta el 25/8) [01 T11.1]. Garantía, campañas/recalls (+31.707 turnos si se contaran), diagnósticos y
   `(90) Concluido sin OS` (+4.058) no cuentan como retorno; sí como "visita a la red" (355.872 turnos) [01 T3.5].
3. **El plan de mantenimiento real es por kilómetros y difiere por generación: 15.000 km en Ranger P703 (nueva) y
   10.000 km en P375 (anterior)**. El odómetro al n-ésimo service converge a 16.040-16.173 × n (P703) y
   10.125-10.330 × n (P375); el incremento entre services consecutivos es 16.138 km / 10.330 km de mediana. El tope
   de "1 año" manda sólo en el 8,8 % de los ciclos [02 b1, b2, f1].
4. **El parque usa mucho el vehículo (21.514 km/año de mediana; p25 14.616, p75 31.307), así que el service
   "toca" cada ~5-6 meses, no cada 12**: mediana de 165 días entre retornos con 18 meses de seguimiento (P703 195,
   P375 154); el 9,5 % de los retornos tarda más de 365 días; el 19,2 % de los vehículos no vuelve en 18 meses
   [02 a4, d2]. Ford Pro (28.312 km/año) y personas jurídicas (28.406) usan más que Ford Blue (23.390) y físicas
   (22.455); el intervalo en km no depende del segmento, el intervalo en días sí [02 a1, a2, d4].
5. **La ventana empírica recomendada** ancla en el último mantenimiento, vence en
   `min(365 d, K_gen / tasa_uso)`, **abre 30 días antes y cierra 90 días después del vencimiento** (120 días de
   ventana). Con eso el retraso real del retorno tiene mediana +7 días (p10 −85, p90 +129), el 80,4 % de las
   ventanas está abierta al scoring, se captura el 84,3 % de los retornos y la **prevalencia de churn entre ventanas
   abiertas es 39,7 % (P703 31,6 %, P375 42,4 %; 34,8 % reponderando a la mezcla de 2026)** [02 f1, f2, f6, f8].
   La regla "sólo 1 año" queda descartada: abre 200 días después de la mediana de retorno y el 85,9 % de los
   clientes ya volvió antes de que la ventana abra [02 f1].
6. **El mayor riesgo está en el primer service**: de los 0 km vendidos en 2024, el 35,6 % no completó ningún
   mantenimiento en 12 meses desde la garantía, 28,0 % en 13, 19,1 % en 18; el 9,3 % nunca pisó la red. El
   aniversario dispara el service (+10,6 pp en el mes 12, +7,7 pp en el 13) y la mediana es 9,1-9,2 meses en las
   cohortes con seguimiento completo [03 T7; 02 e1; 01 V4.4]. Esa ventana no puede individualizarse sin km previo.
7. **La retención cae con la edad de forma sostenida y se desploma en el 5°-6° año, no "en el tercero"**:
   63,9 % de los 0 km 2024 hace un mantenimiento en su 1er año de vida, 73,2 % en el 2°; entre vehículos conocidos
   por la red: 78,3 % (año 2), 66,0 % (3), 60,1 % (4), 52,7 % (5), 38,3 % (6), 13,4 % (12). La caída 2→3 (−12,4 pp)
   es en buena parte mezcla de generaciones (dentro de P703: −4,2 a −5,7 pp); la mayor caída es 5→6 (−14,4 pp) y no
   hay escalón a los 36 meses [03 T1, T3]. Churn a 12 meses tras un mantenimiento: 18,7 % (1er año de vida) →
   40,7 % (5°) → 64,1 % (10+) [03 T5].
8. **Tres columnas son fotos a la fecha de extracción y usarlas es leakage**: `KM` (constante en el 99,99 % de los
   vehículos, igual al odómetro del último turno en el 95,5-95,9 %), `ConnectedStatusARG` (74 de 111.752
   vehículos cambian; "Sin Información" retorna 27 % y marca vehículos que desaparecen del sistema) y "tiene turno
   agendado" (no hay fecha de creación del turno). El odómetro por visita es `VehicleCurrentKM` (0 % nulo en
   concluidos, 100 % en cancelados). `SurveyStarRating` se responde antes del turno (mediana 8 días) y sólo en
   canales digitales: no es la encuesta post-service y no predice (IV 0,007) [05 B3, B2, D1, C1; 06 §4-5].
9. **Las señales de comportamiento más fuertes son recencia e intensidad de contacto con la red**: retorno 85,9 %
   si el último turno fue hace 31-90 días vs 50,6 % si fue hace más de 365; a igual cantidad de turnos previos, un
   no-show previo resta 2-6 pp (OR ajustado 0,63-0,73) y una cancelación dura 0,70-0,75 (paradoja de Simpson: en
   univariante no se ven). El dealer es una feature estable y accionable (Spearman 0,79 entre años; peor quintil
   73,3 % vs mejor 83,8 %; 90,7 % de los retornos van al mismo dealer). FordPass suma poco pero real (OR 1,29) y
   crece de 15 % a 26 % de los turnos [06 §6-8, §10].
10. **El cliente no es una clave estable, el vehículo sí**: el 21,0 % de los vehículos tiene más de un
    `customer_id`, al menos el 19,9 % de esos cambios son la misma persona con dos ids, el comprador es el cliente
    vigente en sólo el 59,7 % de los vehículos vendidos, y que vaya el comprador u otro no cambia el retorno (88,2 %
    vs 89,1 %). Las flotas (≥ 3 vehículos, 20,6-24,4 % de las ventas) entran menos a la red (1er service 60-62 % vs
    80,4 %) pero, una vez adentro, vuelven igual. La unidad correcta es **vehículo × ventana con el cliente vigente
    como atributo** [04 §1-3, §7].

---

## 2. Qué contradice o corrige lo que decía el SPEC original y el tutor

| Lo que decía el SPEC / el tutor | Lo que muestran los datos | Fuente |
|---|---|---|
| **Target = propensión a recomprar** (SPEC §1, §3). | No hay ninguna variable de recompra: ventas tiene una fila por vehículo 0 km 2024-2026 y sólo 3.534 clientes compran más de uno (mayormente flotas). La ficha técnica oficial redefine el target como **no completar el próximo mantenimiento programado en la red** dentro del horizonte; eso sí es observable: 220.522 eventos objetivo. | `docs/00` §1; [01 T11.1] |
| **"Dataset curado, chico, pocas variables"** (SPEC §2). | 631.623 filas-ítem y 59.384 ventas, transaccionales, con 49 columnas útiles en agenda. El dataset analítico (vehículo × ventana) hay que construirlo; no viene armado. | [01 §1; 05] |
| **Habrá clics / navegación web** (SPEC §2). | No hay. Lo más cercano es `ScheduleSource` (FordPass 15,0 % de los turnos en 2024 → 25,8 % en 2026; WEB 3-5 %; Mobile 1-3,5 %). | [06 §3] |
| **Regla de service: "cada 15.000 km o 1 año, lo que ocurra primero"** (tutor). | Cierto para la generación nueva y sólo como nominal: **P703 = 15.000 km, P375 = 10.000 km**, y en la práctica manda el km: el tope de 365 días decide sólo el 8,8 % de los ciclos. El 1° service de P703 llega a 9,1 meses de mediana (77,6 % antes del año) y el intervalo entre services es 165 días de mediana. Usar 15.000 km para todo el parque corre el vencimiento 33 días tarde en P375 (51,6 % de los retornos antes de abrir la ventana). `ServiceMonth = 12·n` es el plan nominal anual y no describe la edad real (sólo 24,2 % de los ítems a ±6 meses). | [02 b1, b2, f1; 01 T4.8, V4.4] |
| **"Al tercer año la asistencia al service cae fuerte"** (tutor). | A medias. La primera caída grande es 2→3 (78,3 → 66,0 %, −12,4 pp) pero está inflada por composición (el año 2 es 77 % P703 y el año 3 es 88 % P375); dentro de P703 es −4,2 a −5,7 pp. No hay escalón a los 36 meses (−3,8 pp por semestre igual que los vecinos). La caída mayor es del 5° al 6° año (52,7 → 38,3 %, −14,4 pp), cuando la mediana del parque supera 100.000 km. Y **el riesgo más alto no está en el año 3 sino en el primer service** (35,6 % sin service a 12 meses). | [03 T1, T3, §2.2, T7] |
| **"3 tipos de cliente"** (tutor). | Los datos no muestran tres grupos naturales; muestran **cuatro ejes que separan el riesgo**, cada uno con un corte en tres: (a) ritmo de uso (terciles 16.875 / 27.347 km/año: churn a 18 m 12,4 / 18,2 / 32,0 %); (b) edad del vehículo (≤3 años retorno a 15 m ≥ 75 %, 4-6 años 56-64 %, 7+ ≤ 56 %); (c) relación reciente con la red (1er service sin historia 83,1 %; activo ≤ 180 días 80-86 %; distanciado > 180 días o reaparece 47-72 %); (d) tamaño de flota (1 vehículo: 1er service 80,4 %; 2-9: 73-79 %; 10+: 60-62 %). La ficha pide "segmento de riesgo": se recomienda definirlo por el score y la capacidad de contacto, y describir los segmentos con esos ejes. | [02 f5; 03 §8; 06 §11; 04 §7] |
| **Horizonte: "el próximo mes"** (tutor). | Si "próximo mes" se cuenta desde que el vehículo cumple 12 meses sin service, el 84,9 % no vuelve en ese mes (73,5 % en 3 meses): el target sería la clase mayoritaria. Quien va a ir el mes que viene en general todavía no reservó (anticipación de reserva mediana 8 días, 97,3 % ≤ 30 días). La ventana tiene que **abrirse antes del vencimiento estimado por km** (due − 30) y el resultado medirse hasta due + 90; el "mes" del tutor se respeta como **frecuencia de re-scoring** y, si negocio lo exige, como re-corte "no vuelve en 30 días" sobre ventanas abiertas. | [03 T8, §5.2; 05 C1; 02 §6.4] |
| **"Fecha del último service y kilometraje" como variables clave** (tutor). | Correcto, pero el kilometraje utilizable **no es `KM`** (foto a la extracción: constante en 99,99 % de los vehículos; en el 1° service de P703 da 31.498 km cuando el odómetro real era 16.008). Es `VehicleCurrentKM` de turnos anteriores al scoring, con limpieza. Usar `KM` infla el ROC-AUC fuera de tiempo (ablación en `docs/02`). | [01 T10.1; 02 c1-c2; 05 B3] |
| **Transferencia de titularidad: "el nuevo dueño vuelve a entrar como cliente activo"** (tutor). | El cambio de `customer_id` existe (21,0 % de los vehículos) pero **al menos 1 de cada 5 es artefacto** (mismo dueño con dos ids: el comprador aparece *después* de otro id en el 19,9 % de los vendidos con cambio) y la tasa de transferencia probable es una meseta de 5-8 % anual entre los años 1 y 7 (no un pico a los 2-3 años). Los retornos tardíos no son "en gran parte" cambio de dueño: 3 de cada 4 vuelven con el mismo id. | [04 a.12, a.8b; 03 §6.3] |
| **"Distinguir si el que va al service es el que compró"** (tutor). | Se puede (70,6 % de los vehículos vendidos tienen al comprador en su agenda; 82,2 % en personas físicas, 54,8 % en jurídicas, 3,0 % en canal HR), pero **no discrimina el retorno** (88,2 % vs 89,1 %). Vale como atributo de contacto, no como driver. | [04 b.1-b.5, g.1] |
| **Priorización actual "uniforme por reglas de tiempo/km/vencimiento"** (ficha). | Sólo el 29,7 % de los ciclos llega a los 12 meses sin service (el resto ya volvió antes por km); una lista de "vehículos que cumplen 12 meses sin service" tiene ~2.443 vehículos/mes (≈ 26 por concesionario) y el 84,9 % de ellos no vuelve en el mes siguiente: la regla de calendario llega tarde. | [03 §2.4, T8] |
| **Evaluación por backtesting con lift** (tutor y ficha). | Coincide; el EDA detectó los riesgos concretos de ese backtest: censura a la izquierda (59,8 % del parque entregado antes de 2024), columnas snapshot, turnos futuros y drift de composición (P375 5.856 → 2.009 mantenimientos/mes; P703 437 → 5.625). Sección 7. | [05 A; 02 g1] |

---

## 3. Definición propuesta de población, ventana, horizonte y target

### 3.1 Evento objetivo: `mant_completado` (regla reproducible, [01 §12])

Sobre la agenda colapsada a turno (`appointments()` en `src/repurchase/eventos.py`):

1. `StatusARG == '(60) Concluido'` **y** algún ítem con `ServiceMaintenance` no nulo (`has_maint`). Los 268.690
   ítems con número tienen `ServiceType = Mantenimiento`; no existe ningún "Maintenance service/review" sin número;
   los 5.515 ítems de Mantenimiento sin número son Guarantee (5.467) y Contactless (48) [01 T1.2].
2. `vehicle_id` no nulo y `ScheduleDate ≤ CUTOFF`.
3. `event_date = EffectiveCheckinDate` si está a ±45 días de `ScheduleDate`, si no `ScheduleDate` (328 turnos caen
   a `ScheduleDate` por esa regla; 4 check-in anteriores a 2024 quedan neutralizados) [05 E1].
4. Deduplicación: un solo evento por vehículo y día (se conserva el primero: −335) y, si dos eventos consecutivos
   del mismo vehículo repiten `maint_number` a ≤ 30 días, se conserva el primero (−846; esos pares tienen Δkm
   mediana 0, son el mismo service cargado dos veces; los pares con mismo número a > 30 días tienen Δkm 10.000-12.400
   y son visitas reales) [01 T7.3, V6.3].

| paso | turnos | vehículos |
|---|---:|---:|
| candidatos `(60)` & `has_maint` | 222.889 | 87.531 |
| − sin `vehicle_id` | −1.186 | |
| − segundo mantenimiento del mismo vehículo el mismo día | −335 | |
| − mismo `maint_number` que el anterior a ≤ 30 días | −846 | |
| **`mant_completado`** | **220.522** | **87.531** |

Sensibilidades de definición, para reportar y no para adoptar [01 T3.5]:

| variante | Δ eventos | por qué no se adopta |
|---|---:|---|
| + `(90) Concluido sin OS` con ítem de mantenimiento | +4.058 (+1,8 %) | sin orden de servicio no hay evidencia de trabajo; tras un (90)+mant el siguiente service repite el mismo número en 22,2 % (vs 5,3 % tras un (60)+mant) [01 V2.8] |
| + `Oil and filter change` (sólo 2026) | +1.127 (+0,5 %; +1,4 % de los eventos 2026) | por definición no es el service numerado, **pero** 74,6 % de los turnos "solo aceite" vienen de vehículos que hacían el plan y caen a 14.793 km del service anterior (P703): puede ser un sustituto del hito. Pregunta prioritaria al mentor; si negocio lo cuenta, entra al target (escenario B) |
| + Guarantee | +4.916 | reparación en garantía, sólo 2024 |
| + campañas / Recall | +31.707 (+14 %) | gratuitas, iniciadas por Ford; no miden la decisión del cliente |
| colapsar además mantenimientos a ≤ 7 días (EDA 05) | −218 (0,10 %) | 52 de esos 218 tienen Δn = +1 (pueden ser flotas de alto uso); la regla del EDA 01 ya captura los duplicados con mismo número (Anexo A.3) |

**Visita a la red** (`visita_red`, sólo para features): `(60)` o `(90)` con `vehicle_id` y fecha ≤ CUTOFF:
355.872 turnos / 105.709 vehículos [01 T11.1]. `(90)` es una visita real (check-out en 96,4 %, odómetro en
97,2 %, mediana 4 días en taller) mayormente de diagnóstico (48,8 %) [01 T2.1].

### 3.2 Población

Unidad **vehículo × ventana** (sección 4). Entra en la población todo vehículo Ranger (P703 o P375, incluye Raptor)
con `vehicle_id`, fecha de inicio de garantía (`WarrantyStartDate`; fallback `DeliveryDate` de ventas; = fecha de
entrega en el 98,8 % de los casos [05 H2]) y al menos una de estas dos anclas:

- **Ancla "último mantenimiento"**: cada `mant_completado` del vehículo abre la ventana siguiente.
- **Ancla "inicio de garantía"** (primer service): vehículos con WSD ≥ 2024-01-01 (en ventas o en agenda) que aún
  no tienen ningún `mant_completado`. Esto incluye a los 17.173 vendidos que nunca tuvieron un turno (74,8 % con
  menos de 12 meses de garantía; 3.166 con ≥ 15 meses son el 9,9 % de los vendidos elegibles y son churn legítimo,
  no defecto de cobertura) [04 f.1-f.2; 05 H1]. Los 1.495 vehículos entregados desde 2024 que no están en ventas
  (3,4 %) entran con la WSD de la agenda [05 H2].

Se excluyen: 2.897 turnos sin `vehicle_id`; 28 vehículos con `ModelYear` inválido y sin WSD; 110 filas de ventas
(3 con `DeliveryDate` 2013/2015, 107 con `Status ≠ ACCEPTED`, 1 "GLOBAL RANGER") [05 I2]. Los vehículos con
garantía anterior a 2024 y ningún mantenimiento en 2024-2026 (17.973 de 66.795) no tienen ancla observable y quedan
fuera del backtest (sección 7) [03 §5.1]. Canal HR y PersonType 25/29/30 (371 vehículos, un único comprador con
752 ventas HR, retención 18-19 % en el 1er año) se **marcan** y se decide con el mentor si son población [03 §1.4;
04 b.7].

### 3.3 Ventana, vencimiento, apertura y horizonte

Regla (parámetros en `config/params.json`, implementada en `src/repurchase/ventanas.py`):

```
tasa_uso     = km_ancla / edad_ancla                 km = VehicleCurrentKM limpio; edad desde WSD
                                                     fallback: mediana de la generación (4,1 % de las ventanas)
K_gen        = 15.000 km (P703, Raptor P703) / 10.000 km (P375)
vencimiento  = ancla + min(365 d, K_gen / tasa_uso × 365,25)   (piso ancla + 90 d, ver nota)
primer service (sin km previo): vencimiento = WSD + 300 d
apertura = scoring = vencimiento − 30 d
cierre del horizonte           = vencimiento + 90 d              (ventana de 120 días)
```

| parámetro | valor | evidencia | alternativa descartada y por qué |
|---|---|---|---|
| K (km del ciclo) | 15.000 P703 / 10.000 P375 | km/n 16.0-16.2k y 10.1-10.3k; Δkm 16.138 / 10.330; retraso mediano del retorno respecto del vencimiento **+7 d** [02 b1, b2, f1] | K = 15.000 para todos: retraso mediano −33 d, 51,6 % de los P375 ya volvió antes de abrir. K = 10.000 para todos: adelanta 20 d el P703, p90 +155 d. Δkm empírico (16.138) en vez de nominal: mueve 17 días, no cambia nada |
| tope en días | 365 | manda en 8,8 % de las ventanas (P703 11,3 %); 9,5 % de los retornos tarda > 365 d; pico secundario de retornos en 350-370 d [02 a4, f1] | sin tope: el p10 de uso (9.924 km/año) esperaría 1,5 años; tope 270 d: marcaría como tardíos a los que siguen la regla anual exacta |
| tasa de uso | acumulada (km al ancla / edad) | disponible en 95,9 % de las ventanas; Spearman 0,895 con la pendiente entre visitas; 78,5 % de los vehículos a ±25 % [02 d3] | tasa reciente (último intervalo): mediana de \|retraso\| 31 vs 30 d, existe sólo en 37,4 % de las ventanas [02 f7] |
| apertura | vencimiento − 30 d | 80,4 % de las ventanas abiertas; 24,3 % de los retornos ocurren antes (clientes que no necesitan contacto) [02 f6] | −60 d: 88,3 % abiertas y churn 36,2 %, pero ventana de 150 d, más lejos del "próximo mes". Depende del lead time que necesite el dealer (pregunta al mentor) |
| horizonte | vencimiento + 90 d | captura 84,3 % de los retornos a 18 m; churn entre abiertas 39,7 % [02 f2] | +60: 77,1 % capturado, 46,9 % churn (etiqueta como churn a muchos tardíos). +120: 88,9 % / 35,1 % (sensibilidad a reportar). +180: 94,5 % pero el resultado llega 210 días después |
| primer service | WSD + 300 d (abre a 270 d, cierra a 390 d ≈ 12,8 meses) | mediana real 9,1-9,2 m; el aniversario concentra el 1° service (+10,6 pp en el mes 12, +7,7 en el 13); a 13 m ya lo hizo el 72,0 % [03 T7; 02 e1] | sólo tiempo 365 d: retraso mediano −99 d, churn entre abiertas 46,4 %; K / tasa poblacional: p10-p90 del retraso −104 / +172 d (no centra) [02 f4] |
| ancla | último `mant_completado` | reproduce cómo "le toca" a cada vehículo según su uso | aniversarios del plan (12·n desde garantía): el plan no es anual (sección 2) |

Nota sobre el piso `ancla + 90 d` (`min_gap_days`): es una salvaguarda de implementación contra tasas de uso
ruidosas en vehículos jóvenes; **no fue evaluada en el EDA** y conviene reportar su sensibilidad.

Con la regla completa sobre 86.484 ventanas totalmente observadas (anclas 2024-01 → 2025-02): retraso del retorno
p10 −85 / p25 −28 / **p50 +7** / p75 +54 / p90 +129 días; churn incondicional a +90 = 31,9 % = 19,2 % que no
vuelve en 18 meses + 12,7 % que vuelve después de due + 90 [02 f1, f2]. En el pipeline implementado, sobre todas
las ventanas evaluables 2024-2026 (incluye primer service y anclas 2025-2026), la prevalencia es 41,7 % (152.764
ventanas; `reports/modelo/sensibilidad_ventana.csv`), coherente con el 39,7 % del EDA una vez que se suman las
ventanas de primer service (≈ 47 % en el pipeline; cuenta aproximada desde la cohorte 0 km 2024: con apertura a 9
meses el 42,0 % ya vino y a 13 meses el 72,0 %, así que entre abiertas queda ≈ 0,28 / 0,58 = 48 %) [03 T7].

### 3.4 Target y censura

- **`churn = 1`** si no existe ningún `mant_completado` del vehículo con `event_date` en `(apertura, cierre]`;
  **`churn = 0`** si existe. Un `mant_completado` entre el ancla y la apertura cierra la ventana antes de abrir
  ("preempted": 24,3 % de los retornos en el EDA; 19 % de las anclas en el pipeline): no se scorea ni se etiqueta.
- **Censura**: una ventana es etiquetable sólo si `cierre ≤ CUTOFF − 30 d` (margen por órdenes `(40) En progreso`
  abiertas al corte: 1.832 turnos, 687 con más de 30 días) [05 D1]. Las ventanas con cierre posterior son la
  población del scoring actual, no negativos.
- `(30) Agendado` (3.953; 3.321 con fecha posterior al CUTOFF), `(40)`, `(70)` y `(80)` **nunca** cuentan como
  retorno. Un `(30)` futuro es una regla operativa post-modelo ("ya reservó", 3.263 vehículos hoy), no una feature
  [05 D1].
- Sensibilidades a reportar con el mismo dato: horizonte +120 (churn 35,1 %); apertura −60 (36,2 %); escenario B
  (aceite) y E ((90)+mant) del target; re-corte mensual "no vuelve en 30 días desde t" sobre ventanas abiertas si
  negocio insiste en el mes [02 §6.4].

### 3.5 Prevalencias según definición (para que el jurado no mezcle)

| formulación | población | churn | fuente |
|---|---|---:|---|
| Ventana empírica (due − 30 → due + 90), entre ventanas abiertas | 69.548 ventanas, anclas 2024-01 → 2025-02 | **39,7 %** (P703 31,6 / P375 42,4; 34,8 % a mezcla 2026) | [02 f2, f8] |
| Ídem, en el pipeline sobre todas las ventanas evaluables 2024-2026 | 152.764 | 41,7 % | `sensibilidad_ventana.csv` |
| No completa el próximo mantenimiento en 12 meses tras el último (por evento) | 73.219 eventos jul-24 → may-25 | 27,6 % (13 m 24,2; 15 m 21,3) | [03 T4] |
| Ídem, un evento por vehículo | 48.372 vehículos | 32,9 % (15 m 24,5) | [03 §3] |
| Ídem, por edad del vehículo (12 m) | 1er año / 5° / 10+ | 18,7 / 40,7 / 64,1 % | [03 T5] |
| No hace el 1er service en 12 / 13 / 18 m desde la garantía | cohorte 0 km 2024 (22.679) | 35,6 / 28,0 / 19,1 % | [03 T7] |
| No vuelve en 1 / 3 meses tras cumplir 12 meses sin service | ~2.443 vehículos/mes | 84,9 / 73,5 % | [03 T8] |
| No vuelve nunca en 24 meses | ciclos activos | ≈ 16,8 % | [03 §6.2] |

---

## 4. Unidad de análisis y tratamiento de cliente, vehículo, transferencias y flotas

**Unidad: vehículo × ventana**, con **cliente vigente** = `customer_id` del último turno del vehículo con fecha
anterior al scoring, como atributo (no como clave), y `sales.customer_id` como "comprador original". Razones:

1. El vehículo es la entidad estable: el 21,0 % de los vehículos (23.245 de 110.551) tiene más de un `customer_id`
   y el 76,5 % de esos casos es un cambio secuencial (A sólo antes, B sólo después) [04 a.1-a.2].
2. Usar `customer_id` como clave partiría historiales de un mismo dueño: en los vendidos 0 km con cambio, el
   comprador aparece *después* de otro id en el 19,9 % (1.112 de 5.582), artefactos seguros; el 52,8 % de los
   cambios coincide con un cambio de canal de reserva (vs 15,7 % en pares sin cambio) y el 34,1 % es un cruce
   Dealer ↔ FordPass, pero el 57 % de los artefactos seguros es Dealer → Dealer, así que filtrar por canal no los
   limpia [04 a.4, a.12, a.12b].
3. El comprador ya no es el vigente en el 40,3 % de los vehículos vendidos (59,7 % vigente; F 82,2 %, J 54,8 %,
   HR 3,0 %) y `es_comprador` no discrimina (88,2 % vs 89,1 % de retorno a 15 m) [04 b.1, g.1].
4. Transferencias probables en 2025: entre 3.325 (criterio estricto) y 8.939 (laxo) sobre 73.701 vehículos activos
   (4,5-12,1 %); tasa por vehículo-año en meseta de 5-8 % entre los años 1 y 7 [04 a.7, a.8b]. Al abrir una ventana
   en el año 3, del orden del 15 % de los vehículos ya cambió de cliente. El primer service post-cambio (0-3 meses)
   vuelve 3-10 pp menos que los siguientes [04 g.8].
5. Vista consolidada por usuario: 5.415 clientes vigentes (6,9 %) tienen 19.909 vehículos activos (21,4 %); en
   2025-09 → 2026-08, el 13,1 % de las ventanas (10.795 de 82.140) pertenece a 1.193 clientes con ≥ 2 vehículos en
   ventana el mismo mes. Es una capa de presentación (agrupar por cliente vigente, mostrar el máximo y la lista por
   vehículo), no un cambio de unidad [04 e.1-e.5].
6. Flotas ≠ Ford Pro ≠ PersonType J: 1.185 compradores con ≥ 3 vehículos concentran 12.261 ventas (20,6 %; 24,4 %
   contando también la agenda); el 56,9 % de las ventas Ford Pro son a compradores con ≤ 2 vehículos y el 40,9 % de
   las jurídicas compran uno solo. Tamaño de flota se calcula (sales ∪ agenda, as-of), no se infiere [04 c.1-c.5].
7. Flotas: entran menos (1er service en 15 m: 80,4 % con 1 vehículo, 73,2 % con 3-9, 61,9 % con 10-49, 60,0 % con
   50+; año 1 desde ventas 64,8 % particular vs 59,1 % flota) y reservan casi todo por dealer (7,4 % FordPass vs
   24,9 %), pero condicional a un service completado vuelven igual o más (85,8 vs 85,3 % en < 2 años; 82,2 vs
   76,6 % en 2-4) [04 f.4, c.6b, g.8]. 62 `customer_id` con 50+ vehículos (hasta 849, en 40-56 dealers; 3 de los 8
   mayores no compran en ventas) son un segmento aparte a confirmar (rentadoras, leasing o cliente genérico) [04 c.2].
8. Dealer: 107 ids en ventas, 95 en agenda, 61 en común; 13 de los 41 dealers vendedores ausentes derivan a un
   dealer que sólo existe en agenda (candidatos a doble código, 65 % de sus ventas); los otros 28 derivan a un dealer
   que ya vende con su id (sucursales). Sólo el 49,7 % hace el 1er mantenimiento en el dealer que lo vendió y
   `mismo_dealer_que_venta` no discrimina (88,8 vs 89,3 %) [04 d.1-d.5, g.1]. Falta una tabla de equivalencia.
9. Turnos sin `customer_id` pero con `vehicle_id` (8.980): se conservan como eventos del vehículo; en 1.760 de los
   2.961 vehículos afectados el cliente se recupera de otro turno [05 F1].

---

## 5. Features candidatas, evidencia univariante y riesgo de leakage

Todas se calculan con eventos de fecha **estrictamente anterior** a la fecha de scoring `t` (`event_date < t`,
`EffectiveCheckoutDate < t`, nada con `ScheduleDate ≥ t`). El proxy de retorno usado en los EDA 04 y 06 (otro
mantenimiento en ≤ 15 meses; base 78,7 %) sirve para comparar niveles, no para fijar la tasa base; con horizonte
fijo, el ritmo de uso es el confusor dominante (IV 0,23 sólo con km/año) [06 §1].

| grupo | features | evidencia univariante | riesgo de leakage / observaciones |
|---|---|---|---|
| **Recencia** | `dias_desde_ultimo_mant`, `dias_desde_ultimo_turno`, `dias_desde_ultima_visita` ((60)/(90)), flag `sin_mant_observado` | IV 0,18 / 0,15: retorno 88,8 % si el mantenimiento previo fue hace 31-90 d, 74,4 % a 181-365, 55,5 % a > 365; "sin turno previo" = 83,1 % si es 1er service pero 46,8 % si es 2° o posterior (vehículo que reaparece) [06 §8] | Bajo si `< t`. **Techo por censura a izquierda**: en t = 2025-01 la recencia máxima observable es 366 d; agregar `meses_observables` y no imputar recencia con un número grande [05 A1, A5] |
| **Frecuencia / intensidad** | `n_mant_previos`, `n_turnos_previos`, `n_visitas_red`, `mant_por_anio_observado`, `services_por_anio_de_vida` (= `maint_number` / edad) | mant. previos 0/1/2/3+: 73,7 / 75,0 / 82,0 / 86,1 %; turnos previos 0 → 5+: 73,5 → 84,5 % (OR 2,70); a igual edad el n° de service separa ~40 % de ~80 % (2° año de vida: 45,9 % tras el 1er service vs 83,0 % tras el 3°); hizo mantenimiento el año anterior: 81,0 vs 60,7 % (k=2), 69,8 vs 40,7 % (k=3) [06 §8; 03 §3.2, T1] | Conteos truncados en 2024-01 (sección 7); `maint_number` se toma de `ServiceMaintenance`, nunca del nombre |
| **Contactos fallidos** | `n_no_show_previos`, `n_cancel_duras` (`IsReschedule = N`), `n_reprogramaciones` (`IsReschedule = Y`), `tasa_no_show` (= no-show / turnos), `n_revisitas` (`ScheduleReturn = Y`) | Univariante ~0 (78,0 / 78,9 / 79,1 % con 0/1/2+ no-show) **por paradoja de Simpson**: a igual n° de turnos previos, con no-show 67,0 vs 73,0 % (1 turno), 76,4 vs 81,1 % (3-4); OR ajustado no-show 0,73 / 0,63, cancelación dura 0,75 / 0,70, reprogramación 0,81 / 0,76. Recalls, reparaciones y re-visitas previas no agregan a igual intensidad (OR 0,96-1,00) [06 §8] | Entran **siempre junto con `n_turnos_previos`**. `IsReschedule` en cancelados marca el par cancelado/re-agendado y la fecha de la acción no está en los datos: ignorarlo en cancelaciones de los 30 días previos a `t`. 57,4 % de las cancelaciones no dicen qué reservaban [01 T6.2; 05 D2] |
| **Patrón de uso / km** | `km_ancla` (`VehicleCurrentKM` limpio), `tasa_uso` (km/edad), `K_gen`, `dias_hasta_due`, `retraso_km_anterior` (km ancla − K·n; mediana +1.000 km en P703), `retraso_dias_anterior` (cuánto tardó el service previo vs su due), `intervalo_anterior_dias`, `intervalo_doble_km` (Δkm ≥ 1,5·K: 7,9 % de los pares P703, 18,5 % P375) | km/año aproximado: retorno 62,7 % (< 10.000) → 87,7 % (> 50.000), IV 0,23; terciles de uso: churn a 18 m 12,4 / 18,2 / 32,0 %; retorno al 2° service en 12 m 91,5 % si el 1° fue a ≤ 4 m vs 46,8 % si fue a 12-15 m [06 §1; 02 f5, e4, b5] | **`KM` prohibido** (snapshot). `VehicleCurrentKM` sólo de turnos `< t`, placeholders (< 100: 10.076 lecturas; > 1 M: 162) a nulo, running max por vehículo (5.058 retrocesos > 1.000 km sin placeholders), km/día recortado a p99 (881) [05 E1, E4b]. Nulo en 100 % de cancelados y 71,9 % de no-show |
| **Ciclo de vida** | `edad_meses` (desde WSD), `n_service` (`maint_number` del último), `es_primer_service`, `generacion` (P703/P375 por `ShortVehicleModelGroupTreated` o `ModelCode`), `ModelYear`, `TMA`, `historia_invisible` (max `maint_number` − n observados, sólo WSD < 2024) | Año modelo IV 0,29 (retorno 46,7 % ≤ 2015 → 92,0 % 2025+); churn a 12 m 18,7 % → 64,1 % por edad; P703 retiene 4,6-8,8 pp más que P375 a igual edad (edad y generación deben entrar juntas); gap de `maint_number` > 0 en 74,8 % de los vehículos con WSD < 2024 vs 4,9 % de los 0 km [06 §2; 03 T5, §1.2; 05 A4b] | Bajo (atributos fijos). En P703 los `maint_number` ≥ 11 (< 100 ítems por número, km incompatibles) son errores de carga; `ServiceMaintenance = 20` es tope "20 o más" (3.494 eventos vs 1.068 en 19) [01 §5.4; 02 b0] |
| **Canal** | `fuente_ultimo_turno`, `alguna_vez_digital`, `share_fordpass` | FordPass 83,8 % vs Dealer 77,2 % crudo; dentro de generación × año modelo +2,3 a +8,1 pp; OR 1,29 ajustado (1,35 con efecto fijo por dealer); `alguna_vez_digital` IV 0,034. Turnos digitales: menos no-show (3,9 vs 6,2 %), más reprogramación (19,6 vs 11,6 %) [06 §3] | Drift fuerte: FordPass 9,6 % de los turnos (ene-24) → 25,5 % (ago-26). Reportar métricas por canal en la validación temporal |
| **Dealer** | `dealer_te` (target encoding regularizado con datos anteriores al período de scoring), `zona_dealer` (`DealerStateOrZone`), `cambio_de_dealer` vs mantenimiento anterior | Retorno por dealer p10 / p50 / p90 = 70,6 / 78,7 / 83,8 %; desvío 5,6 pp vs 1,5 esperado por azar; estable (Spearman 0,79; 0,68 con vehículos disjuntos); quintil 2024 aplicado a 2025: 73,3 → 83,8 %; residuo ajustado por mix −7,9 / +5,2 pp; 90,7 % de los retornos en el mismo dealer; zona 1 73,7 % vs 79-80 %; cambio de dealer −2,2 / −4,3 / −7,6 pp por franja de edad [06 §6; 04 g.8] | Nunca `dealer_id` one-hot ni encoding con datos del mismo período. `Region` no se usa (constante por dealer, no geográfica; 80 dealers en "60", 11 en "00") [01 T9.1] |
| **Experiencia del turno** | `has_diag` en el último turno, `has_recall`, `has_fixed_price`, `dias_en_taller` (escalón 0 vs ≥ 1), `n_recalls_previos` | diagnóstico en el turno 72,8 vs 78,9 % (OR 0,82); precio fijo +2,9 pp; recall +4,1 pp; días en taller 0 vs 31+: 79,9 vs 76,0 % (OR 0,77) [06 §7] | Débiles. `DaysInDealer`, `EffectiveCheckoutDate`, `WorkDaysInDealer` sólo de turnos con checkout `< t`. PUD, móvil, cliente esperó, remolque: sin señal (IV ≤ 0,006); los nulos de `NeededTowing` / `ScheduleReturn` replican el canal digital: no derivar features de ellos |
| **Relación / identidad** | `tamaño_flota_cliente` (sales ∪ agenda, as-of: 1 / 2-9 / 10+), `n_clientes_distintos` (as-of), `transferencia_reciente` (< 3 meses desde la primera aparición del cliente vigente), `es_comprador`, `mismo_dealer_que_venta` | tamaño de flota: fuerte en la entrada (1er service 80,4 vs 60,0 %) y débil dentro de la red (±5 pp); transferencia reciente −3 a −10 pp; `es_comprador` y `mismo_dealer_que_venta` **no discriminan** (88,2 vs 89,1; 88,8 vs 89,3) [04 §7] | Flota as-of arranca en 1 para todos en 2024-01 (2.523 eventos de flotas ≥ 3 clasificados como 1): combinar con ventas. `n_clientes_distintos` está inflado por identidades duplicadas; preferir `n_turnos_previos`. `es_comprador` y dealer de venta quedan como atributos de contacto |
| **Estáticas de venta** | `BusinessUnit`, `PersonType`, `SalesChannel`, `State`, `ModelCode`, `SalesDate` | Ford Pro retiene 6,1 pp menos en k=1 y 12,8 pp en k=2 que Ford Blue, dentro de cada canal y PersonType; CONSORTIUM ~−5,5 pp propio; DIRECT SALES = efecto Ford Pro (83 % del canal); F vs J no discrimina (64,9 vs 64,3 %); HR / PersonType 25-29-30: 18-19 % [03 §1.4] | Disponibles sólo para el 46 % de los vehículos del universo (59.384 de 128.925; los 69.541 "solo agenda" tienen nulos estructurales) |
| **Calendario** | `mes_scoring`, `meses_observables` (= t − 2024-01-01) | Estacionalidad moderada sin tendencia: junio 90,6, enero 108,8 (media 100); tendencia +1,26 %/mes por día hábil; el retorno de la etiqueta no varía por mes (77,9-80,2 %) [02 g2; 06 §9] | `meses_observables` es una feature de censura, no de negocio: el modelo debe poder separar "sin historia porque es nuevo" de "sin historia porque el extracto no la trae" |
| **Excluidas** | `KM`, `ConnectedStatusARG`, `SurveyStarRating` / `SurveyResponseDate`, `ServiceMonth`, `ServiceName` (para el número), `ServicePriceDiscount` (×100, sólo como flag "precio informado"), `ServiceLaborCost` (0,7 % no nulo), `IsReschedule` de cancelaciones recientes, cualquier turno con `ScheduleDate ≥ t`, `Region`, `LoanerVehicle` / `CancellationReason` / `Quicklane` / `ScheduleModalityCode` / `SalesType` (100 % nulos o constantes) | `ConnectedStatusARG` IV 0,31 **por leakage** ("Sin Información" 27,0 % de retorno, 41,4 % reaparece; dentro de P703 Conectado vs No tiene: 87,5 vs 85,4 %); survey IV 0,007 [06 §4-5; 05 B2, C1] | Si se quiere conectividad, `generacion_conectada` por TMA (6DC/7DC/8DC/TA1). Survey sólo con `SurveyResponseDate < t` y presentada como calificación de la reserva; su única utilidad es estimar la anticipación de reserva (mediana 8 días) |

---

## 6. Reglas de limpieza y exclusiones (con conteos)

| # | regla | afectados | tratamiento | fuente |
|---|---|---:|---|---|
| 1 | Filas-ítem idénticas en la agenda | 19.554 (3,1 %) | eliminar antes de colapsar (ya lo hace `appointments()`) | [01; 05 G] |
| 2 | Colapso ítem → turno | 612.069 ítems → 492.442 turnos | columnas de nivel turno no varían dentro de un `schedule_id` (4 turnos con dos `StatusARG`) | [01 T0.3] |
| 3 | Turnos sin `vehicle_id` | 2.897 (1.186 mantenimientos) | excluir de eventos; todos de fuente Dealer, sin WSD ni ModelYear. Nunca hacer merges con clave nula (pandas empareja NaN con NaN e infla los historiales) | [01 T8.1; 06 §1] |
| 4 | Turnos sin `customer_id` con `vehicle_id` | 8.980 | conservar como eventos del vehículo; imputar cliente del vehículo (1.760 vehículos recuperables) | [05 F1] |
| 5 | `event_date` | 328 turnos con \|check-in − turno\| > 45 d; 45.433 concluidos sin check-in (13,3 %; 22,9 % en 2024) | check-in sólo si está a ±45 d; si no, `ScheduleDate` (coincide con el check-in el 91,7 % de las veces). El % sin check-in cae de 29,4 % (ene-24) a ~10 % (dic-24): features derivadas del check-in tienen sesgo por período | [05 E1, E3; 06 §9] |
| 6 | Deduplicación del evento objetivo | 335 mismo día + 846 mismo número a ≤ 30 d | un evento por vehículo-día; mismo `maint_number` a ≤ 30 d = duplicado | [01 §8, §12] |
| 7 | Odómetro `VehicleCurrentKM` | 10.076 lecturas < 100 (valores 1, 10, 3, 12, 30) y 162 > 1.000.000 en concluidos; 5.058 pares con retroceso > 1.000 km (2,2 %); 6.485 pares > 300 km/día (p99 881) | placeholders y > 1 M a nulo; running max por vehículo; km/día recortado a p99; imputar por tasa de uso | [05 E1, E4b; 02 c3-c4] |
| 8 | `KM` | constante por vehículo (99,99 %) | no usar en ninguna feature; sólo atributo a la fecha de extracción | [01, 02, 04, 05] |
| 9 | Inicio de vida útil | WSD nula en 1.257 vehículos de agenda; difiere de ventas en 406 de 42.150 (mediana 8 d; 25 > 30 d); 1.505 vehículos con WSD posterior al primer turno concluido; 82 mantenimientos con edad negativa | WSD de ventas (= `DeliveryDate` en 98,8 %) con fallback a agenda; edad negativa recortada a 0; excluir de tasas de uso los 82 | [05 E1, H2; 02 §9] |
| 10 | Vehículos con `ModelYear` 0 / < 2005 sin WSD | 28 | excluir | [05 I2] |
| 11 | Ventas inválidas | 110 filas (3 `DeliveryDate` 2013/2015, 107 `Status ≠ ACCEPTED`, 1 GLOBAL RANGER) | excluir de la población de vendidos | [05 I2] |
| 12 | Turnos con `ScheduleDate > CUTOFF` | 3.826 (3.321 `(30)`) | fuera del backtest; regla operativa en el scoring actual. Toda tabla mensual filtra `ScheduleDate ≤ CUTOFF` (agosto 2026 quedaba inflado con 2.259 reservas) | [05 D1; 06 §9] |
| 13 | Pendientes atrasados `(30)` / `(40)` con `ScheduleDate ≤ CUTOFF − 30 d` | 962 (687 `(40)`, 275 `(30)`); 377 con más de 180 d | no concluidos, con flag; `(40)` con check-in `< t` cuenta como ingreso al taller | [05 D1] |
| 14 | Catálogo de servicios | "Maintenance service" → "Maintenance review" (ene-feb 2026), "Service campaign" → "Recall" (2026), "Oil and filter change" sólo 2026, "Guarantee" sólo 2024; `ServiceName` muestra n mod 10 para `ServiceMaintenance` 11, 12, 14, 16-19 | clasificar ítems por clase (`ServiceMaintenance.notna()`, `ServiceType`), nunca por nombre | [01 §5.1-5.2, §14] |
| 15 | `ServiceMaintenance` en P703 ≥ 11 | < 100 ítems por número, km incompatibles (n = 20 a 2.628 km) | acotar a 1-10 o marcar sospechoso; en P375 son services reales (22,9 % de los ítems) | [01 §5.4] |
| 16 | Canal HR / PersonType 25-29-30 | 455 / 374 vehículos en la cohorte 2024 (371 en común); un comprador con 752 ventas HR | marcar "comprador desconocido"; decidir con el mentor si son población | [03 §1.4; 04 b.7] |
| 17 | Cancelaciones | 101.222; 68.783 con `IsReschedule = Y` (reprogramación: 99,0 % tiene otro turno a ±30 d); 54,1 % de todas con un concluido a ±7 d; 58.113 sin ítem tipado | construir `cancel_dura` y `reprogramacion` por separado; `cancelaciones_netas` = sin concluido a ±7 d | [01 T5.1; 05 G2; 06 §7] |
| 18 | Precio y encuesta | `ServicePriceDiscount` en escala ×100, 0 = precio fijo / campaña; `ServiceLaborCost` 4.703 ítems (2026); survey en 36.920 turnos, siempre anterior al turno | flag "precio informado"; excluir `ServiceLaborCost`; survey sólo `< t` | [05 E5, C1] |

---

## 7. Riesgos metodológicos y mitigaciones

| riesgo | evidencia | mitigación |
|---|---|---|
| **Censura a la izquierda** (la agenda empieza en 2024-01; el parque no) | 66.795 vehículos (59,8 % de los que tienen id) fueron entregados antes de 2024. A t = 2024-07 el 33,4 % de los activos no tiene mantenimiento observado y la recencia tiene techo 182 d. Sobre una misma población, 6 meses de historia etiquetan "sin mantenimiento" a un 14,4 pp más que 32 meses; con 12 meses el exceso es +4,9 pp, con 18 meses +2,0 pp, con 24 +0,8 pp. Pega en los viejos: 5-8 años 39,0 % → 14,5 % [05 A1, A5] | Fechas de scoring del backtest ≥ 2025-01-01 (mejor ≥ 2025-07-01); features de censura `meses_observables`, `edad_en_t`, `historia_invisible` (gap de `maint_number`, sólo WSD < 2024: discrimina 74,8 % vs 4,9 %); recencia con techo explícito y flag, sin imputar. Para los 17.973 vehículos con garantía < 2024 sin ningún mantenimiento 2024-2026 no hay ancla: fuera del backtest, reportados como población invisible |
| **Columnas snapshot** | `KM` (constante 99,99 %; con `KM` el ROC-AUC fuera de tiempo sube de 0,736 a 0,819 y la calibración se rompe, `docs/02`); `ConnectedStatusARG` (74 de 111.752 cambian; "Sin Información" 92,6 % de las entregas 2026Q3, 27,0 % de retorno; su participación entre turnos base cae de 5,1 % a 0,6 % por trimestre, como corresponde a un estado adquirido después de dejar de venir) [05 B; 06 §4] | Excluir ambas. Odómetro por `VehicleCurrentKM < t`. Conectividad por generación (TMA) si hace falta. Ablación explícita con y sin snapshot para mostrar al jurado el leakage evitado |
| **Turnos futuros y flags que miran adelante** | Sin `CreatedDate`: 3.826 turnos con fecha > CUTOFF sólo existen para el scoring actual; anticipación de reserva mediana 8 días (por survey). `IsReschedule` en cancelados codifica el par cancelado/re-agendado con fecha de acción desconocida [05 D1, D2] | Nada con `ScheduleDate ≥ t` en features (ni cancelados). "Ya tiene turno" como regla operativa post-modelo. Ignorar `IsReschedule` (y `ScheduleStatus` nulo) de cancelaciones en los 30 días previos a t; usar la versión "este turno concluido nació de una reprogramación" |
| **Sesgo de selección de la agenda** | La agenda sólo contiene vehículos que vinieron al menos una vez en 2024-2026. En la cohorte 2024, restringir a "≥ 1 turno" sobreestima la retención +6,5 pp (k=1) y +6,6 pp (k=2). Para k ≥ 3 no hay población completa: las tasas son cotas superiores [03 T2] | Construir la población desde ventas ∪ agenda (los 17.173 sin turno entran por WSD); presentar 63,9 % / 73,2 % como población completa y el resto como "base que la red conoce"; la forma de la curva es robusta (estimador de ventana previa homogénea: 79,6 / 66,8 / 59,7 / 54,0 / 40,0 %) |
| **Ponderación por evento vs por vehículo** | Los vehículos con ≥ 3 intervalos aportan el 62 % de los pares; churn a 12 m 27,6 % por evento vs 32,9 % por vehículo; intervalo mediano 161 d por par vs 206 d por vehículo [03 §3, §2.4] | La unidad vehículo × ventana pondera por evento por diseño (cada ventana es una decisión de contacto); reportar también la prevalencia por vehículo y validar con split por vehículo dentro del split temporal |
| **Drift de composición y de comportamiento** | Mantenimientos P375 5.856 (2024-01) → 2.009 (2026-07); P703 437 → 5.625; la mezcla de las ventanas evaluadas es 74,6 % P375 y la de 2026 es 69,6 % P703 (prevalencia 39,7 % → 34,8 %); retorno a 6 m cae de 46,8 % (índices jul-24) a 40,1 % (may-25); FordPass 15 % → 26 %; reprogramaciones 12,7 % → 16,5 %; no-show 5,9 % → 5,1 % [02 g1, f8; 03 §3; 06 §9] | Validación temporal estricta (train ≤ 2025-09, valid oct-dic 2025, test 2026); reportar métricas por generación, por canal y por tipo de ventana (primer service vs siguientes); horizontes cortos son los más sensibles al período |
| **Censura a la derecha** | Ventanas con cierre después de ~2026-07 no son etiquetables; agosto 2026 tiene 1.040 `(40)` y 337 `(30)` vencidos; los pares "ingenuos" subestiman los intervalos largos (161 vs 202 d incondicional) [06 §9; 02 a4] | Etiquetar sólo ventanas con `cierre ≤ CUTOFF − 30 d`; medir cadencia con seguimiento garantizado (18 m) |
| **Primer service sin km** | Ninguna regla centra sin odómetro previo: p10-p90 del retraso ≈ 280 d [02 f4] | Ventana aparte por tiempo (WSD + 300 d); pedir km de telemetría para vehículos Conectado; modelar con features de venta y flota (las únicas disponibles) |
| **Identidad partida y flotas as-of** | ≥ 19,9 % de los cambios de cliente son artefactos; `tamaño_flota` as-of arranca en 1 para todos en 2024-01 [04] | Cliente vigente como atributo; flota con ventas ∪ agenda; no usar "alguna vez cambió de cliente" |
| **Etiqueta con horizonte fijo confunde ciclo con uso** | Con 15 meses fijos el retorno va de 62,7 % (< 10.000 km/año) a 87,7 % (> 50.000) [06 §1] | La ventana por km/tiempo normaliza el ritmo de uso; re-medir los IV de recencia e intensidad con el target definitivo (sección 1 de `06_*.py` está aislada para eso) |
| **Efecto dealer inflado por solapamiento** | 65,6 % de los vehículos de 2025 están también en 2024 [06 §6] | Target encoding calculado sólo con períodos anteriores; validar con vehículos disjuntos (Spearman 0,68) |

---

## 8. Preguntas abiertas para el mentor (priorizadas)

**Prioridad 1 — cambian el target o la ventana**

1. **Plan oficial por generación**: ¿15.000 km / 1 año en P703 y 10.000 km / 1 año en P375? ¿Raptor difiere? Los
   datos lo muestran (km/n 16.0-16.2k vs 10.1-10.3k); conviene tenerlo por escrito.
2. **`Oil and filter change`** (2.601 ítems, sólo 2026): ¿es una oferta nueva que reemplaza al service numerado (p.
   ej. para vehículos fuera de garantía)? El 74,6 % de los turnos "solo aceite" son de vehículos que hacían el plan y
   vuelven ~15.000 km después del último service. Si cuenta como mantenimiento en la red, hay que sumarlo al target
   (+1,4 % de los eventos de 2026, creciente) para no fabricar churn.
3. **`(90) Concluido sin OS`** con ítem de mantenimiento (4.058 turnos): ¿se hizo el service sin orden o el cliente
   se fue sin hacerlo? Al menos 1 de cada 5 vuelve después por el mismo número de service.
4. **Lead time y horizonte de negocio**: ¿cuántos días antes del vencimiento necesita el dealer para que el contacto
   sirva (decide −30 vs −60)? ¿El resultado se mide por ventana (due + 90) o quieren un score mensual "no vuelve en
   30 días" sobre ventanas abiertas?
5. **Turno agendado y no cumplido dentro de la ventana**: ¿es churn o la ventana sigue abierta hasta el horizonte?
   Define si el no-show en ventana es feature o parte del target.
6. **Services fuera de la red**: el 7,9 % (P703) / 18,5 % (P375) de los intervalos son "dobles" por km. ¿Ford
   considera churn un service en taller independiente que luego vuelve, o sólo la ausencia de retorno?

**Prioridad 2 — cambian la población o la identidad**

7. **Canal HR y PersonType 25 / 29 / 30** (un comprador con 752 ventas HR; retención 18-19 % en el 1er año): ¿plan
   de empleados, cuenta institucional? ¿Entran en la población?
8. **`customer_id` de la agenda**: ¿es el titular en el sistema del dealer o la cuenta que reservó (FordPass / WEB)?
   ¿Un mismo dueño puede tener un id por canal? ¿Existe un evento formal de transferencia de titularidad?
9. **Mega-clientes** (62 ids con 50+ vehículos, hasta 849, en 40-56 dealers; 3 de los 8 mayores no compran en
   ventas): ¿rentadoras, leasing, cliente genérico del DMS? ¿Las grandes flotas tienen contratos de mantenimiento
   fuera de la red?
10. **Tabla de equivalencia de dealers** entre ventas (107) y posventa (95): 46 códigos de venta no existen en la
    agenda. ¿Qué codifica `Region` (60 / 00 / 31 / A)?
11. **Cobertura**: 1.495 vehículos entregados desde 2024 no están en ventas (3,4 %) y 1.203 con garantía 2024
    aparecen en agenda pero no en ventas: ¿otra unidad de negocio, carga posterior?

**Prioridad 3 — cambian features o producción**

12. **`KM`**: ¿es el odómetro vigente a la fecha de extracción? ¿En producción el scoring tendría odómetro actual
    (telemetría para `Conectado`)? Sería la única forma de individualizar la ventana del primer service.
13. **`ConnectedStatusARG`**: ¿a qué fecha corresponde? ¿"Sin Información de Conectividad" se asigna al salir del
    padrón (baja, exportación, siniestro)? ¿Existe historial de activación?
14. **Fecha de creación del turno** (`CreatedDate` en BigQuery): con ese campo "tiene turno agendado a la fecha t"
    pasa a ser feature válida en backtest.
15. **`IsReschedule` / `ScheduleReturn`**: ¿en qué momento se setean? ¿`Y` en cancelados = reemplazado por otro
    `schedule_id` (hay vínculo explícito)? ¿`ScheduleReturn = Y` es el "comeback" que Ford usa como KPI del dealer?
16. **Encuesta**: ¿qué mide `SurveyStarRating` (se responde 2-26 días antes del turno, sólo canal digital)? ¿Existe la
    encuesta CSI post-service?
17. **Numeración de services**: ¿por qué `ServiceMaintenance` 11-19 se muestra como "1°"-"9°"? ¿20 es "20 o más"?
    ¿El dealer numera según el plan aunque el service anterior se haya hecho afuera (gap en 4,9-10,7 % de los 0 km)?
18. **Garantía**: ¿cobertura exacta (3 años / 100.000 km) y cambios por generación? No hay quiebre a 36 meses; sí
    aceleración en el 5°-6° año cuando la mediana supera 100.000 km.
19. **Operación**: ¿qué cambió en la carga del check-in a fines de 2024 (29 % → 10 % de concluidos sin check-in)?
    ¿La red registra no-shows de forma homogénea (dealers con 0,4 % y otros con 12,8 %)? ¿Los dealers con caídas de
    −28 pp entre 2024 y 2025 tuvieron cambios conocidos?
20. **`ServicePriceDiscount`** (×100, 0 = precio fijo / campaña) y `RegistrationDate` (9.806 ventas con
    `SalesDate` posterior): semántica.

---

## 9. Índice de figuras clave para el PDF (`reports/figures/eda/`)

| archivo | qué muestra | uso sugerido |
|---|---|---|
| `01_taxonomia_target_escenarios_target.png` | volumen del evento objetivo bajo cada definición (A: 222.889 → D: 254.596) | Datos y EDA: por qué el target es el service numerado |
| `01_taxonomia_target_km_por_n.png` | odómetro al ingreso por n° de service, P703 (recta 15.000·n) y P375 (10.000·n) | Datos y EDA: el plan es por km y por generación |
| `01_taxonomia_target_verif_edad_1er_service_cohorte.png` | distribución bimodal de la edad al 1° service (cohorte 2024-H1): bloque 4-10 meses por km y pico 11-12 meses por la regla anual | Ventana del primer service |
| `01_taxonomia_target_km_vs_vck.png` | `KM` (snapshot) vs `VehicleCurrentKM` (odómetro del turno) en el 1° service | Leakage: por qué no se usa `KM` |
| `01_taxonomia_target_seguimiento.png` | % de cancelaciones / no-show / (90) seguidos de un (60) a 30-60-90 días | Semántica de cancelación vs no-show |
| `02_cadencia_ventana_hist_intervalos.png` | histogramas de días y km entre mantenimientos consecutivos, por generación (picos en ~10.300 y ~16.200 km; pico secundario en 365 d) | Cadencia real |
| `02_cadencia_ventana_tasa_uso.png` | distribución de la tasa de uso (km/año), terciles, concordancia entre métodos | Tasa de uso individual |
| `02_cadencia_ventana_cohorte2024_curvas.png` | curvas acumuladas WSD → 1° service y 1° → 2° | Primer service |
| `02_cadencia_ventana_ventana_retraso_sensibilidad.png` | ECDF del retraso del retorno según la regla de ventana; % capturado y % churn por horizonte | **Figura central de la definición de ventana** |
| `02_cadencia_ventana_estacionalidad.png` | volumen mensual por generación (recambio P375 → P703) e índice estacional sin tendencia | Drift de composición; estacionalidad |
| `03_retencion_churn_curva_edad.png` | retención por año de vida (cohorte 2024 completa y base conocida) | **Figura del pitch**: la curva de caída con la edad |
| `03_retencion_churn_quiebre_tercer_anio.png` | caídas año a año y curva semestral alrededor de 36 meses | "Cae al tercer año": qué muestran los datos |
| `03_retencion_churn_tasa_base_horizonte.png` | retorno / churn según horizonte (3 → 15 meses) | Tasa base según definición |
| `03_retencion_churn_cohorte24_primer_service.png` | % de la cohorte 0 km 2024 con 1er service por mes desde la garantía (pico en el mes 12-13) | Primer service y aniversario |
| `03_retencion_churn_poblacion_mensual.png` | vehículos que cumplen 12 meses sin service por mes y su retorno posterior | Dimensionamiento y por qué la regla de calendario llega tarde |
| `03_retencion_churn_recurrencia.png` | reaparición de churners y retorno acumulado a 24 meses | Churn temporario vs definitivo |
| `04_identidad_cliente_vehiculo_patrones.png` | patrones de cambio de cliente (secuencial / alternancia) y tasa de transferencia por edad del vehículo | Identidad y transferencias |
| `04_identidad_cliente_vehiculo_comprador.png` | % de vehículos vendidos cuyo comprador aparece en la agenda, por segmento | Comprador vs usuario |
| `04_identidad_cliente_vehiculo_flotas.png` | tasa anual de mantenimiento por año de vida: particular vs flota | Flotas |
| `04_identidad_cliente_vehiculo_nunca_vino.png` | vendidos sin ningún turno según meses desde la garantía | Población desde ventas |
| `05_calidad_cobertura_leakage_km_snapshot.png` | `KM` vs odómetro del último turno | Leakage (alternativa a la figura del EDA 01) |
| `05_calidad_cobertura_leakage_censura_izquierda.png` | historia observable según fecha de scoring; curvas acumuladas terminan en el techo | Censura a la izquierda |
| `05_calidad_cobertura_leakage_conectividad_snapshot.png` | `ConnectedStatusARG` por trimestre de entrega ("Sin Información" crece hasta 92,6 %) | Leakage de conectividad |
| `05_calidad_cobertura_leakage_survey_lag.png` | lag survey − turno (100 % anterior) | Por qué la encuesta no es post-service |
| `05_calidad_cobertura_leakage_duplicados_cancelaciones.png` | pares vehículo-fecha con más de un turno; cancelaciones seguidas de concluido | Semántica de cancelación |
| `06_canal_dealer_experiencia_historia_retorno.png` | retorno por historial previo (recencia, intensidad, contactos fallidos) | Features de comportamiento |
| `06_canal_dealer_experiencia_dealer_estabilidad.png` | retorno por dealer 2024 vs 2025 (estabilidad) | Dealer como driver accionable |
| `06_canal_dealer_experiencia_fuente_mix_mensual.png` | mix de canal de agendado por mes (FordPass 9,6 % → 25,5 %) | Drift de canal |
| `06_canal_dealer_experiencia_conectividad_retorno.png` | retorno por conectividad dentro de cada generación | Leakage de conectividad |
| `06_canal_dealer_experiencia_iv_ranking.png` | ranking de features por IV con las de leakage marcadas | Selección de features |

---

## Anexo A — Contradicciones entre informes y cómo se resolvieron

| tema | lo que decía cada informe | resolución |
|---|---|---|
| **A.1 Cadencia "5-6 meses" vs "~2 services por año / 7.500 km"** | EDA 02: intervalo mediano 161 d por par, 165 d entre retornos con seguimiento, 202 d incondicional; EDA 03: 161 d por par, 206 d por vehículo, 9 meses hasta el próximo por vehículo; EDA 05 (pregunta 10): "edad mediana 1,28 años al 2° service y 1,97 al 4° parece un ciclo de ~6 meses / 7.500 km" | No hay contradicción en los números: 161 d es la mediana por par (dominada por alto uso), 206 d por vehículo y 202 d incondicional con censura tratada. La inferencia "7.500 km" del EDA 05 es incorrecta: el intervalo en km es 16.138 (P703) / 10.330 (P375) [02 b2]; lo que acorta el intervalo en días es la tasa de uso (21.514 km/año de mediana), no el plan. Se cita 165 d (entre retornos, 18 m de seguimiento) como cadencia y 206 d por vehículo |
| **A.2 Tasa de uso 34.080 vs 21.514 km/año** | EDA 03 (B_km_anio_y_gap): 34.080 por evento; EDA 02: 21.514 por vehículo; verificación de 03: 21.909 por vehículo | El 34.080 usa `KM` (snapshot, odómetro futuro) sobre la edad al evento y está inflado (lo señala la verificación del EDA 02). Se adopta **21.514** (`VehicleCurrentKM` al último mantenimiento / edad; 85.495 vehículos), consistente con 21.909 por vehículo. No citar 34.080 |
| **A.3 Deduplicación: 1.033 vs 335 filas; regla ≤ 7 d (EDA 05) vs regla del EDA 01** | EDA 02: "se colapsan 1.033 filas vehículo + `event_date`"; EDA 01 y 03: 335 duplicados vehículo-día; EDA 05: "colapsar mantenimientos a ≤ 7 días (988 turnos)" | Recalculado (`scripts/eda/07_consistencia_sintesis.py`): los 1.033 del EDA 02 incluyen 698 filas de los 1.186 turnos sin `vehicle_id` (488 fechas distintas) tratados como un mismo vehículo; con `vehicle_id` son 335. Efecto sobre el EDA 02: un pseudo-vehículo con 488 eventos entre 133.837 pares (< 0,4 %), sin impacto en sus conclusiones. Sobre los 220.522 eventos de la regla del EDA 01, la regla "≤ 7 d" descartaría **218 más (0,10 %)**, 52 con Δn = +1 (posibles flotas de alto uso): se mantiene la regla del EDA 01, que ya elimina los duplicados con mismo número |
| **A.4 Prevalencia de churn: 21,3 / 27,6 / 32,9 / 39,7 / 41,7 / 84,9 %** | Cada informe usa una definición distinta (sección 3.5) | No son contradicciones. La prevalencia oficial es la de la ventana empírica (39,7 % entre abiertas en el EDA; 41,7 % en el pipeline con primer service y anclas 2025-26); las demás se reportan como sensibilidades con su definición |
| **A.5 "3 tipos de cliente"** | EDA 02: terciles de uso; EDA 03: edad (≤ 3 / 4-6 / 7+); EDA 04: tamaño de flota; EDA 06: relación con la red (nuevo / activo / distanciado) | Son cuatro ejes válidos, no cuatro respuestas a la misma pregunta. Sección 2: el segmento del entregable se define por score y capacidad; los ejes describen los segmentos |
| **A.6 Primer service: "abrir en el mes 11-12 con horizonte 13 meses" (EDA 03) vs "due = WSD + 270-300 d" (EDA 02)** | EDA 03 T7: pico en meses 12-13, 72,0 % a 13 m; EDA 02 f4: sólo tiempo 365 abre tarde; K/tasa poblacional no centra | Compatibles: con due = 300 d y horizonte +90, la ventana abre a 270 d (≈ 9 m, 42,0 % ya vino) y cierra a 390 d (≈ 12,8 m), que es el horizonte de 13 meses del EDA 03 y captura el pico del aniversario. Implementado en `config/params.json` (`first_due_days: 300`) |
| **A.7 KM = odómetro del último turno: 91,7 / 95,5 / 95,9 / 96,5 %** | EDA 02: 91,7 % (incluye vehículos con `KM` nulo); EDA 05: 95,5 % (último concluido, ambos no nulos); EDA 04: 95,9 % (último turno de cualquier estado); EDA 01: 96,5 % (\|dif\| ≤ 1.000 km) | Misma métrica con denominadores distintos; se cita 95,5-95,9 % con ambos valores no nulos |
| **A.8 Sesgo de selección "+7,8 / +4,4 pp" vs "+6,5 / +6,6 pp"** | EDA 03 original vs su verificación | Se usa +6,5 / +6,6 (misma cohorte 2024, completa vs con ≥ 1 turno); +7,8 / +4,4 mezclaban años de garantía |
| **A.9 `ServiceMaintenance = 20`: "código" vs "20 o más"** | EDA 03 original: "código, no 20° service"; verificación de 03, EDA 02 y 05: tope "20 o más" (km 246.100, edad 81 meses, monótono) | Tope "20 o más". Los 11-19 son services reales en P375; en P703 son errores de carga |
| **A.10 "Vehículo con problemas vuelve más" vs "no-shows no anticipan churn"** | EDA 06 original vs su verificación (paradoja de Simpson) | Los conteos de contactos fallidos sí discriminan a igual intensidad (OR 0,63-0,75); recalls / reparaciones / re-visitas no agregan a igual intensidad (OR 0,96-1,00). Sección 5 |
| **A.11 Transferencias "ocurren temprano (mediana 2,55 años)" y "retornos tardíos con cambio de dueño"** | EDA 04 original y EDA 03 original vs sus verificaciones | Refutadas: hazard plano de 5-8 %/año (composición del parque) y cambio de `customer_id` creciente con el tiempo en riesgo (11 % → 31 %), también entre no churners |
| **A.12 Región / zona** | EDA 01: constantes por dealer; EDA 05 B1: "varían en 6-9 % de los vehículos" | Compatibles: varían dentro del vehículo sólo cuando cambia de dealer; son atributos del dealer del turno |
