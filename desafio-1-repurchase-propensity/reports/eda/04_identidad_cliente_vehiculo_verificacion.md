# Verificación escéptica del EDA 04 — Identidad cliente–vehículo, transferencias, flotas y dealer

**Objeto:** `reports/eda/04_identidad_cliente_vehiculo.md` y `scripts/eda/04_identidad_cliente_vehiculo.py`.
**Método:** cada afirmación se recalculó con código propio (sin reutilizar el del script original) en `scripts/eda/04_identidad_cliente_vehiculo_verificacion.py`, que genera `reports/eda/04_identidad_cliente_vehiculo_verificacion_tablas.md` (tablas "V"). Para cada una se buscó activamente el error típico que la refutaría: confusores (n° de turnos, edad del vehículo), sesgo de población (ventana calculada sobre el "último" mantenimiento), definiciones ambiguas ("nunca vino"), truncamiento de features as-of, denominadores donde el evento no es detectable, y números citados que el script original no producía.
**Resultado global:** los 11 números centrales se reproducen exactamente; dos interpretaciones estaban mal (edad de las transferencias; coincidencia de ventanas) y se corrigieron en el script y el informe; cinco afirmaciones recibieron salvedades que cambian cómo usarlas. Ninguna corrección altera la recomendación de unidad de análisis (vehículo × ventana con cliente vigente as-of).

---

## Tabla de veredictos

| # | Afirmación | Veredicto | Número original | Número recalculado | Nota |
|---|---|---|---|---|---|
| 1 | 21,0 % de los vehículos tiene > 1 `customer_id`; 3 de 4 son cambio permanente | **confirmada con salvedad** | 23.245 / 110.551; 17.792 secuenciales (76,5 %), 5.224 alternancia, 229 ambiguos | Idénticos (V1.1, V1.2). Solo turnos concluidos: 20.462 multi-cliente, 82,0 % secuencial (V1.3) | "Permanente" es generoso: en el 36,3 % de los secuenciales el cliente nuevo tiene un solo turno, en el 8,7 % ninguno concluido, en el 4,1 % su último turno es reserva futura; solo el 84,3 % tiene turnos concluidos de ambos lados (V1.4). Salvedad agregada al hallazgo 2. |
| 2 | Una fracción grande de los cambios son artefactos de identidad por canal | **ajustada** | 52,8 % vs 15,7 % (cambio de source); 34,1 % vs 11,4 % (cruce D↔FP); 42,3 % vs 20,3 % (mezcla de canal) | Idénticos (V2.1). Baseline en vehículos de 1 cliente: 16,8 % / 12,5 %. Estratificado por n° de turnos la brecha 42,3 vs 20,3 se reduce a 14–19 pp (28,8 vs 9,3 con 2 turnos; 53,0 vs 39,0 con 9+) (V2.2 / a.6b). Prueba directa en vendidos 0 km: el comprador aparece *después* de otro id en 1.112 de 5.582 secuenciales de 2 clientes (19,9 %) = artefactos seguros (V2.3 / a.12) | La asociación con el canal no distingue artefacto de "transferencia + cambio de canal". El artefacto existe (≥ 20 % acotado con sales) pero **solo el 31,5 % de los artefactos seguros es cruce D↔FP; el 56,9 % es Dealer→Dealer** (V2.4 / a.12b): 27,9 % pre-entrega, 30,9 % un id que usa el vehículo > 180 días después (V2.5). El filtro de canal del nivel (ii) no limpia el artefacto. Texto del resumen e hallazgo 3 reescritos. |
| 3 | Transferencias 4,5–12,1 % anual; ocurren temprano (mediana 2,55 años) | **refutada en la interpretación, confirmada en los números** | 8.939 / 5.527 / 3.325 en 2025 sobre 73.701 → 12,1 / 7,5 / 4,5 %; mediana 2,55; 58,3 % entre 1 y 4 años | Idénticos (V3.1). Con denominador "≥ 2 turnos" (66.482): 5,0–13,4 % (V3.2). **Hazard por edad (V3.3/V3.4, a.8b): 1,5 % (< 1 año), 5,0 % (1–2), 6,4 % (2–3), 6,6 % (3–4), 7,3 % (4–5), 6,7 % (5–7), 5,0 % (7–10), 3,6 % (10+)** | La concentración en 1–4 años es composición: el 53 % del parque activo tiene < 2 años. La tasa por vehículo-año es una meseta de 5–8 % entre los años 1 y 7, sin pico a los 2–3 años. Se eliminó la lectura "mercado de usados líquido a los 2–3 años / justo antes del año 3"; se agregó la tabla a.8b, se cambió el panel central de la figura `_patrones.png` y se reescribió el hallazgo 5. |
| 4 | Comprador aparece 70,6 %, es el vigente 59,7 %; déficit en J y HR | **confirmada** | 29.576 / 41.906; primero 66,1 %; último 59,7 %; F 82,2 / J 54,8; HR 3,0 %; 752 de 1.060 y 387 de 656 | Idénticos (V4.1–V4.3). 371 vehículos (0,9 %) solo tienen reserva futura (último = NaN); excluyéndolos, 60,2 % | Sin cambios. |
| 5 | `es_comprador` y `mismo_dealer_que_venta` no discriminan; 49,7 % hace el 1er service en el dealer vendedor | **confirmada** | 88,2 vs 89,1 (n 8.875 / 5.885); F 87,8/86,5; J 89,1/90,4; Blue 89,6/90,2; Pro 85,2/86,7; mismo dealer 88,8 vs 89,3; 49,7 % (28.112) | Idénticos (V5.2, V5.5, V5.6). Con proxy "limpio" (siguiente mantenimiento a > 30 días; los retornos a ≤ 30 días son el 1,1 % de los eventos): 88,1 vs 88,9; mismo dealer 88,7 vs 89,1 (V5.3–V5.4) | Salvedad agregada: todos los eventos con venta son de vehículos < 2 años (1er/2do service). |
| 6 | Flotas ≠ Ford Pro ≠ PersonType J; usar tamaño de flota calculado | **confirmada con salvedad** | 1.185 compradores / 12.261 vehículos (20,6 %); Pro 79,0 % de 10–49; 56,9 % de Pro a ≤ 2; 10,1 % de Blue flota; 9.676 J (40,9 %) con 1 | Idénticos (V6.2). Con flota = sales ∪ agenda: flota 24,4 % de las ventas, Blue flota 14,0 %, Pro flota 46,5 %, J con 1 vehículo 34,9 %; 564 ventas a "1 vehículo" en sales son de clientes con ≥ 3 en agenda (V6.1) | El tamaño de flota por sales solo cuenta compras 0 km 2024-26 y subestima. Salvedad agregada al hallazgo 9: la feature debe calcularse con la unión. |
| 7 | Flotas entran menos y caen antes; condicional a un service vuelven igual o más | **confirmada con salvedad** | 1er service 15 m: 80,4 / 79,1 / 73,2 / 61,9 / 60,0; Pro 70,4 vs Blue 80,2; año 2 68,9 vs 79,2, año 3 55,5 vs 70,5, año 6 26,6 vs 40,0; g.8 85,8/85,3, 82,2/76,6, 62,1/58,4; FordPass 7,4 vs 24,9; no-show 5,8 vs 5,5 | Idénticos (V7.1, V7.2, V7.4, V7.6). g.8 robusto a medir flota con período completo en vez de as-of (3–9: 85,9/81,5/62,5 vs 1: 85,5/76,8/59,1) aunque el as-of clasifica como "1" a 2.523 eventos de flotas ≥ 3 (V7.5). **Año 1 desde sales (incluye nunca vinieron): particular 64,8 % vs flota 59,1 %; año 2: 73,5 vs 66,4 (V7.3 / c.6b)** | c.6 mostraba a la flota igual o arriba en el año 1 (73,0 vs 71,6) por sesgo de supervivencia (excluye a los que nunca vinieron, más frecuentes en flotas). Se agregó c.6b y se corrigió el texto "pierde 10 pp ya en el año 2" → ya está 5–7 pp abajo desde el año 1. |
| 8 | 46 dealers vendedores no existen en la agenda; parecen ser los mismos con otro código | **ajustada** | 107 / 95 / 61 / 46 / 34; 76,1 % / 75,7 %; 71,9 vs 70,8 %; mediana share 59 vs 57,65 %; `85cc31b84261` 1.910 / 67,1 % | Idénticos (V8.1, V8.2). **Solo 13 de 41 ausentes (65 % de sus ventas) derivan a un dealer solo-agenda; 28 derivan a un dealer que ya vende con su id; 9 destinos son compartidos por > 1 ausente; `85cc31b84261` deriva a `7fc11e64ab78`, que está en sales** (V8.3–V8.5 / d.4b). Presentes: el destino principal es él mismo en el 86 % | "Mismo dealer con otro código" es plausible para ~2/3 de las ventas de dealers ausentes; el resto parecen sucursales/puntos de venta de otro taller. Hallazgo 11 y calidad de datos reescritos. |
| 9 | 6,9 % de los clientes vigentes tienen 21,4 % de los vehículos activos; coincidencia de ventanas 7,2 % | **refutada en la segunda parte** | 78.331 / 5.415 / 19.909; 195 clientes / 1.262 vehículos / 7,2 % de 17.449 | Primera parte idéntica (V9.1). **Segunda parte: 82.140 ventanas en 2025-09 → 2026-08 (no 17.449); 10.795 (13,1 %) de 1.193 clientes con ≥ 2 el mismo mes; 11,3 % con cliente vigente al CUTOFF (V9.2). Por mes 6.342–7.648 ventanas (no 1.134–2.074) (V9.3)** | El script usaba solo el *último* mantenimiento al CUTOFF: todo vehículo que volvió corría su ventana al futuro y desaparecía del período; quedaba una población 5 veces menor y sesgada hacia los que no retornaron. Se corrigió el script (e.3–e.5 usan todos los mantenimientos; se conserva el método original como fila de trazabilidad), el resumen, el hallazgo 15 y el punto 5 de la unidad de análisis. |
| 10 | 17.173 vendidos sin turno; 74,8 % < 12 m; 3.166 elegibles que nunca vinieron (9,9 % de 31.892) | **confirmada con salvedad de definición** | 17.173; 74,8 %; mediana 6,6; 4.208 ≥ 12 m; 3.166 ≥ 15 m; 9,9 %; Blue 7,3 / Pro 15,9; DIRECT 17,0; HR 31,7; 10–49 20,8; 50+ 20,3 | Idénticos (V10.1, V10.3). Sobre los mismos 31.892: sin turno concluido 11,7 % (3.735); sin mantenimiento completado 15,9 % (5.070); sin 1er mantenimiento dentro de 15 m 22,8 % (V10.2) | "Elegible y nunca vino" = 9,9 % solo si se exige "ni un turno cancelado". Para el target la cifra relevante es 22,8 %; los 3.166 son la parte que ni figura en la agenda. Texto ajustado en el resumen y el hallazgo 16. |
| 11 | `KM` es snapshot por vehículo (100 % constante); `VehicleCurrentKM` coincide con `KM` en el último turno | **confirmada; el segundo número no lo producía el script** | 100,0 % de 82.347; VCK constante 2,5 % | 99,99 % (unos pocos vehículos con 2 valores); a nivel fila 99,99 % de 88.143 (V11.1–V11.2). **KM == VCK del último turno en 95,9 % de 101.768; == máximo VCK 92,7 %; == primer VCK solo 4,0 % (V11.3–V11.4)** | La tabla 0.2 solo medía constancia; "coincide con el último turno" no estaba en el script. Se agregó la tabla 0.3 al script original y el 95,9 % al informe. |

---

## Detalle de las dos refutaciones

### A. "Las transferencias ocurren temprano (mediana 2,55 años), justo antes de la caída del año 3"

El número es correcto y la conclusión no se sigue. La distribución de edades de las transferencias (tabla a.8) es el producto de la propensión por edad **y** de cuántos vehículos hay en cada edad. El parque activo en 2025 es joven (28,1 % < 1 año, 25,3 % 1–2 años), así que cualquier evento con tasa constante "se concentra" en 1–4 años. Dividiendo por el parque activo de cada franja (edad al 2025-07-01):

| edad | transferencias (iii) | % del total | parque activo | % del parque | tasa (iii) | tasa (iii), ≥ 2 turnos | tasa (i), ≥ 2 turnos |
|---|---:|---:|---:|---:|---:|---:|---:|
| < 1 | 313 | 9,4 | 20.567 | 28,1 | 1,5 % | 1,7 % | 9,0 % |
| 1–2 | 920 | 27,7 | 18.508 | 25,3 | 5,0 % | 5,1 % | 15,2 % |
| 2–3 | 596 | 18,0 | 9.262 | 12,7 | 6,4 % | 6,7 % | 18,2 % |
| 3–4 | 389 | 11,7 | 5.892 | 8,1 | 6,6 % | 7,0 % | 15,6 % |
| 4–5 | 357 | 10,8 | 4.917 | 6,7 | 7,3 % | 7,8 % | 14,9 % |
| 5–7 | 322 | 9,7 | 4.841 | 6,6 | 6,7 % | 7,7 % | 14,8 % |
| 7–10 | 319 | 9,6 | 6.326 | 8,7 | 5,0 % | 6,5 % | 11,5 % |
| 10+ | 101 | 3,0 | 2.776 | 3,8 | 3,6 % | 6,1 % | 10,0 % |

Meseta de 5–8 % anual entre los años 1 y 7 (nivel iii). El año 1 es bajo en parte por detección (hace falta un turno anterior). No hay señal de un momento de transferencia especial; la fracción de vehículos que ya cambió de mano crece de manera aproximadamente lineal con la edad.

### B. "195 clientes con ≥ 2 vehículos en ventana el mismo mes, 1.262 vehículos, 7,2 %"

El script calculaba la ventana como `último mantenimiento completado (al CUTOFF) + 12 meses`. Un vehículo con mantenimientos en 2024-10 y 2025-10 tiene ventana 2025-10 **y** 2026-10; el método solo contaba la segunda, así que del período 2025-09 → 2026-08 quedaban únicamente los vehículos cuyo último mantenimiento cayó ahí, es decir, mayoritariamente los que no volvieron todavía. Resultado: 17.449 "ventanas" en vez de 82.140 y una población sesgada. Recalculado con todos los mantenimientos completados (cada uno abre una ventana 12 meses después, cliente = el del turno):

| | original | corregido (cliente del turno) | corregido (cliente vigente al CUTOFF) |
|---|---:|---:|---:|
| ventanas 2025-09 → 2026-08 | 17.449 | 82.140 | 82.140 |
| de clientes con ≥ 2 el mismo mes | 1.262 | 10.795 | 9.281 |
| % coincidencia | 7,2 % | 13,1 % | 11,3 % |
| clientes con ≥ 2 el mismo mes | 195 | 1.193 | 1.002 |

La implicancia cualitativa ("la consolidación es una capa de presentación, no una unidad") se mantiene, pero la magnitud es ~1 de cada 8 ventanas, no "< 10 %", y los volúmenes mensuales para planificar contacto son 6.300–7.600, no 1.100–2.100.

---

## Otros hallazgos de la verificación (transversales)

1. **El proxy `retorno_15m` tiene 1,1 % de "retornos" a ≤ 30 días y 13,4 % a ≤ 90 días** (V5.3). Los primeros son re-visitas o duplicados; no cambian ninguna comparación de este tema (V5.4) pero conviene que el tema del target los excluya explícitamente.
2. **El tamaño de flota as-of arranca en 1 para todos en 2024-01** (truncamiento a izquierda): 2.523 eventos de clientes con ≥ 3 vehículos quedan clasificados como "1" en el proxy (V7.5). En el modelo, la feature as-of necesita un período de calentamiento o combinarse con sales.
3. **Nivel (iii) de transferencias no es "limpio":** filtra cruces de canal y flotas, pero el 57 % de los artefactos seguros son Dealer→Dealer (a.12b). Es una cota superior de transferencias reales.
4. **Dealers ausentes:** además del mapeo, 8 de 58 dealers presentes en la agenda tienen como destino principal de su primer turno a otro dealer (V8.2); la "fidelidad al vendedor" del 49,7 % (d.5) también está afectada por esa estructura de grupos.

## Cambios aplicados

**Script original (`scripts/eda/04_identidad_cliente_vehiculo.py`):** tabla 0.3 (KM vs VehicleCurrentKM del último turno); a.6b (mezcla de canal estratificada por n° de turnos); a.8b (hazard de transferencia por edad); a.12 y a.12b (posición del comprador en la secuencia; canal y timing de los artefactos seguros); c.6b (años 1–2 desde sales, incluye nunca vinieron); d.4b (naturaleza del destino de los dealers ausentes); e.3–e.5 recalculadas con todos los mantenimientos (se conserva el método original como filas "[método original]"); panel central de `_patrones.png` reemplazado por el hazard por edad. Vuelto a correr de punta a punta.

**Informe (`reports/eda/04_identidad_cliente_vehiculo.md`):** resumen ejecutivo puntos 2, 3, 7, 8, 9, 10, 11; hallazgos 2, 3, 4, 5 (reescrito), 7, 9, 10, 11, 15 (reescrito), 16; sección 7 punto 5; sección 8 puntos 1–3; nota de verificación en el encabezado.

**Script de verificación:** `scripts/eda/04_identidad_cliente_vehiculo_verificacion.py` → `reports/eda/04_identidad_cliente_vehiculo_verificacion_tablas.md`.
