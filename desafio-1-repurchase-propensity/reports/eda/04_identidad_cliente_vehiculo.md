# EDA 04 — Identidad cliente–vehículo, transferencias, flotas y dealer

**Script:** `scripts/eda/04_identidad_cliente_vehiculo.py` (corre de punta a punta; regenera todas las tablas en `reports/eda/04_identidad_cliente_vehiculo_tablas.md` y las figuras `reports/figures/eda/04_identidad_cliente_vehiculo_*.png`). Todas las referencias "tabla x.y" apuntan a ese archivo de tablas.
**Datos:** `appointments()` (492.442 turnos, CUTOFF 2026-08-25) y `load_sales()` (59.384 ventas).
**Verificación:** las afirmaciones clave fueron recalculadas de forma independiente en `scripts/eda/04_identidad_cliente_vehiculo_verificacion.py` (tablas "V" en `reports/eda/04_identidad_cliente_vehiculo_verificacion_tablas.md`; veredictos en `reports/eda/04_identidad_cliente_vehiculo_verificacion.md`). Las correcciones resultantes están marcadas en el texto; las tablas agregadas al script original son 0.3, a.6b, a.8b, a.12, a.12b, c.6b, d.4b y la e.3/e.5 corregidas.
**Convenciones de este informe:**
- *Flota* = `customer_id` con ≥ 3 vehículos distintos (en la tabla que corresponda).
- *Cliente vigente* de un vehículo = `customer_id` del último turno (cualquier estado) con fecha ≤ CUTOFF.
- *retorno_15m* (proxy, **no es el target oficial**): dado un mantenimiento programado completado en la fecha *d* (con *d* ≤ CUTOFF − 456 días), existe otro mantenimiento programado completado del mismo vehículo en (*d*, *d* + 456 días]. 456 días = 12 meses de ventana + 3 de tolerancia. Base: **78,5 %** sobre 105.782 eventos de 55.712 vehículos (eventos entre 2024-01-02 y 2025-05-26; tabla g.0). Sirve para comparar niveles de una feature, no para estimar el churn del negocio.

---

## Resumen ejecutivo

1. **El 21,0 % de los vehículos de la agenda (23.245 de 110.551) tiene más de un `customer_id`.** De ellos, 17.792 (76,5 %) muestran un cambio permanente (cliente A solo antes, cliente B solo después), 5.224 (22,5 %) alternan y 229 son ambiguos (tabla a.2).
2. **Una parte de esos cambios no son transferencias sino la misma persona (o el mismo dueño) con dos `customer_id`.** Evidencia directa: en los vehículos vendidos 0 km con cambio secuencial de 2 clientes, el comprador aparece *después* de otro id en el 19,9 % de los casos (1.112 de 5.582): ese otro id no puede ser un dueño anterior (tabla a.12). Evidencia indirecta: el 52,8 % de los cambios de cliente coincide con un cambio de `ScheduleSource` (contra 15,7 % en pares sin cambio) y el 34,1 % es un cruce Dealer↔FordPass (contra 11,4 %) (tabla a.4). Pero el canal no es el único mecanismo: solo un tercio de los artefactos seguros es un cruce Dealer↔FordPass y el 57 % es Dealer→Dealer (tabla a.12b), y la brecha de multi-cliente entre vehículos que mezclan canales y los que no (42,3 % vs 20,3 %) se reduce a 14–19 pp al controlar por n° de turnos (tabla a.6b).
3. **Transferencias probables: entre 3.325 (criterio estricto) y 8.939 (criterio laxo) en 2025**, es decir entre 4,5 % y 12,1 % de los 73.701 vehículos con actividad en 2025 (5,0 %–13,4 % si el denominador son los 66.482 con ≥ 2 turnos, únicos donde un cambio es detectable). La edad mediana al cambio (2,55 años) **no** significa que se transfieran más temprano: la tasa por vehículo-año es una meseta de 5–8 % entre los años 1 y 7 (1,5 % en el año 1, 6,4 % en 2–3, 7,3 % en 4–5, 6,7 % en 5–7; tabla a.8b). La concentración en 1–4 años (58,3 %) refleja que el parque observado es joven (53 % de los activos tiene < 2 años), no una mayor propensión (tablas a.7–a.9).
4. **El comprador aparece en la agenda de su vehículo en el 70,6 % de los casos** (29.576 de 41.906) y es el cliente vigente al CUTOFF solo en el 59,7 %. Personas físicas: 82,2 %; jurídicas: 54,8 %; canal HR: 3,0 % (un único `customer_id` compra 752 de las 1.060 ventas HR) (tablas b.1–b.7).
5. **Que el que va al service sea o no el comprador no cambia el retorno**: 88,2 % vs 89,1 % (tabla g.1), y tampoco cambia dentro de PersonType ni BusinessUnit (tablas g.3, g.4).
6. **Flotas ≠ Ford Pro.** Ford Pro es el 79 % de las ventas a flotas de 10–49 vehículos, pero el 56,9 % de las ventas Ford Pro son a compradores con ≤ 2 vehículos, y el 40,9 % de las jurídicas compran un solo vehículo (tablas c.3–c.5).
7. **Las flotas entran menos a la red y caen antes, pero cuando están adentro vuelven igual o más.** Primer mantenimiento completado dentro de 15 meses de la garantía: 80,4 % (1 vehículo) vs 61,9 % (10–49) y 60,0 % (50+) (tabla f.4). Tasa anual de mantenimiento: flota 68,9 % vs particular 79,2 % en el año 2, 55,5 % vs 70,5 % en el año 3 (tabla c.6; esa tabla solo incluye vehículos con algún turno, así que en el año 1 muestra a la flota igual o arriba del particular; al incluir a los vendidos que nunca vinieron la flota ya está 5–6 pp abajo en el año 1: 59,1 % vs 64,8 %, tabla c.6b). Pero, condicional a un service completado, el retorno a 15 meses de flotas es igual o mayor al de particulares dentro de cada franja de edad (tabla g.8; robusto a medir la flota con el período completo en vez de as-of).
8. **Los `dealer_id` de sales y agenda comparten espacio de hash (61 ids en común) pero 46 dealers vendedores no existen en la agenda.** Sus vehículos igual aparecen (71,9 % vs 70,8 %) y se concentran en un dealer de agenda (mediana 59 %, igual que los presentes). Pero "mismo dealer con otro código" solo se sostiene para una parte: 13 de los 41 dealers ausentes con ventas rastreables (65 % de sus ventas) tienen como destino principal un dealer que existe solo en la agenda; los otros 28 (35 % de las ventas) derivan a un dealer que ya vende con su propio id, y varios ausentes comparten destino (tablas d.1–d.4). Solo el 49,7 % de los vehículos hace el primer mantenimiento en el dealer que los vendió (tabla d.5). Ni `mismo_dealer_que_venta` (88,8 % vs 89,3 %) discrimina; `cambio_de_dealer` resta 2–8 pp según la edad (tabla g.8).
9. **Vista consolidada:** 5.415 clientes vigentes (6,9 %) concentran 19.909 vehículos activos en 2025-26 (21,4 %). De las 82.140 ventanas (mantenimiento completado + 12 meses) que abren entre 2025-09 y 2026-08, 10.795 (13,1 %) pertenecen a 1.193 clientes con ≥ 2 vehículos en ventana el mismo mes (tablas e.1–e.5). (La versión anterior de este informe decía 195 clientes / 1.262 vehículos / 7,2 %: usaba solo el *último* mantenimiento de cada vehículo, lo que excluía a todo vehículo que volvió; se corrigió.)
10. **De los 17.173 vehículos vendidos que nunca tuvieron un turno, el 74,8 % tiene menos de 12 meses desde la garantía.** Los vendidos con ≥ 15 meses **sin ningún turno** (ni cancelado) son 3.166, el 9,9 % de los 31.892 vendidos con ≥ 15 meses; sin ningún turno concluido son 11,7 %, sin ningún mantenimiento completado 15,9 %, y sin 1er mantenimiento *dentro* de los 15 meses 22,8 % (complemento de la tabla f.4). El 9,9 % sube a 15,9 % en Ford Pro, 17,0 % en DIRECT SALES y 20,3–20,8 % en flotas de 10+ vehículos (tablas f.1–f.4).
11. **Hallazgo transversal (no es de este tema, pero condiciona a todos): `KM` es constante dentro de cada vehículo en el 99,99 % de los 82.347 vehículos con ≥ 2 valores; `VehicleCurrentKM` varía en el 97,5 %.** `KM` es el último odómetro conocido (snapshot al extraer): coincide con el `VehicleCurrentKM` del último turno con odómetro en el 95,9 % de 101.768 vehículos y con el primero solo en el 4,0 % (tabla 0.3). Usarlo como feature filtra información futura (tabla 0.2).

---

## 0. Base de trabajo

| | turnos |
|---|---:|
| total | 492.442 |
| sin `vehicle_id` | 2.897 |
| sin `customer_id` | 9.398 |
| con ambos (base de trabajo) | 480.565 |

(tabla 0.1). Los 9.398 turnos sin `customer_id` quedan fuera de todo lo que sigue; hay que ver en el tema de calidad si son de algún estado o canal en particular.

---

## 1. Vehículos con más de un `customer_id` (punto a)

### Hallazgo 1 — Uno de cada cinco vehículos tiene más de un cliente

| clientes distintos | vehículos | % |
|---:|---:|---:|
| 1 | 87.306 | 79,0 % |
| 2 | 19.624 | 17,8 % |
| 3 | 3.083 | 2,8 % |
| 4 | 440 | 0,4 % |
| 5–8 | 98 | 0,1 % |

(tabla a.1; 110.551 vehículos con `customer_id` no nulo).

### Hallazgo 2 — Tres de cada cuatro casos son un cambio permanente

Clasificación por vehículo, ordenando los turnos por `event_date`: *secuencial* si cada cliente ocupa un bloque contiguo de turnos (n° de cambios = n° de clientes − 1) y ningún cambio ocurre el mismo día; *alternancia* si los clientes se intercalan; *ambiguo* si es secuencial pero el cambio es entre dos turnos del mismo día.

| patrón | vehículos | % de los multi-cliente |
|---|---:|---:|
| secuencial (cambio permanente) | 17.792 | 76,5 % |
| alternancia (uso compartido / flota / chofer) | 5.224 | 22,5 % |
| ambiguo (cambio el mismo día) | 229 | 1,0 % |

(tabla a.2, figura `04_identidad_cliente_vehiculo_patrones.png`, panel izquierdo). Con 2 clientes el 80,0 % es secuencial (15.699 de 19.624); con 4 clientes ya domina la alternancia (247 vs 187) (tabla a.3).

Salvedades (verificación): la clasificación usa todos los estados de turno. Restringida a turnos concluidos ((60) y (90)) quedan 20.462 vehículos multi-cliente y el patrón secuencial sube a 82,0 %. Pero "permanente" es una lectura generosa: en el 36,3 % de los 17.792 secuenciales el cliente nuevo tiene un solo turno, en el 8,7 % no tiene ningún turno (60) Concluido y en el 4,1 % su último turno es una reserva futura; solo en el 84,3 % ambos clientes tienen al menos un turno concluido (tabla V1.4 de la verificación).

### Hallazgo 3 — Muchos "cambios de cliente" son la misma persona con dos identificadores

Comparando el turno donde cambia el cliente con el turno anterior del mismo vehículo, y contrastando con pares consecutivos sin cambio (tabla a.4):

| qué pasa en el par de turnos | en cambio de cliente (n = 35.836) | sin cambio (n = 100.962) |
|---|---:|---:|
| cambia `ScheduleSource` | 52,8 % | 15,7 % |
| cruce Dealer↔FordPass | 34,1 % | 11,4 % |
| cambia `dealer_id` | 21,8 % | 7,4 % |
| el cliente nuevo tiene ≥ 3 vehículos | 30,2 % | 26,4 % |
| el cliente anterior tiene ≥ 3 vehículos | 37,8 % | 26,4 % |

De los 35.836 cambios, 8.734 son Dealer → FordPass y 3.472 FordPass → Dealer (tabla a.5). Y a nivel vehículo: entre los que tienen turnos FordPass **y** no-FordPass, el 42,3 % es multi-cliente; entre los que usan un solo tipo de canal, 20,3 % (tabla a.6). Esa comparación está confundida por el n° de turnos (más turnos ⇒ más chance de mezclar canal y de acumular ids): estratificada, la brecha es 28,8 % vs 9,3 % con 2 turnos, 38,7 % vs 22,1 % con 4–5 y 53,0 % vs 39,0 % con 9+ (tabla a.6b). Persiste, pero es de 14–19 pp, no de 22.

La asociación con el canal tampoco distingue por sí sola "misma persona con dos ids" de "transferencia real seguida de un cambio de canal" (el nuevo dueño se hace una cuenta FordPass). La prueba directa está en los vehículos vendidos 0 km, donde el comprador es el primer dueño por construcción: en los 5.582 secuenciales de 2 clientes con venta, el comprador aparece primero en el 57,5 %, no aparece en el 22,6 % y aparece **después** de otro id en el 19,9 % (1.112 vehículos; tabla a.12). Esos 1.112 son artefactos seguros (el otro id no es un dueño anterior): el 27,9 % es un turno anterior a `DeliveryDate` (pre-entrega, id del dealer), el 30,9 % es un id que usa el vehículo más de 180 días después de la entrega y el 41,3 % hace un mantenimiento (chofer, familiar o encargado con id propio). Y solo el 33 % de esos cambios es un cruce Dealer↔FordPass; el 57 % es Dealer→Dealer (tabla a.12b). Conclusión: el artefacto existe y se puede acotar (≥ 20 % de los cambios secuenciales en vendidos), pero el filtro "sin cruce de canal" del nivel (ii) **no lo limpia**; hay que confirmar con el mentor cómo se asigna el `customer_id` (pregunta 1).

### Hallazgo 4 — Transferencias por año: 3.325 a 8.939 en 2025 según el criterio

Se cuenta cada cambio de cliente en vehículos secuenciales (un vehículo con 3 clientes aporta 2), con tres niveles acumulativos de confianza (tabla a.7):

| nivel | cambios | vehículos | 2024 | 2025 | 2026 (al 25/8) | gap mediano (días) | edad mediana (años) |
|---|---:|---:|---:|---:|---:|---:|---:|
| (i) solo secuencial | 20.137 | 17.792 | 3.845 | 8.939 | 7.353 | 168 | 2,05 |
| (ii) + sin cruce Dealer↔FordPass | 12.991 | 11.611 | 2.623 | 5.527 | 4.841 | 168 | 2,34 |
| (iii) + ambos clientes con < 3 vehículos | 7.417 | 6.940 | 1.372 | 3.325 | 2.720 | 189 | 2,55 |

2024 subestima (no se ven los turnos previos a 2024-01 del cliente anterior) y 2026 es parcial; 2025 es el único año completo. Sobre los 73.701 vehículos con algún turno en 2025 eso da una **tasa anual de transferencia de 4,5 % (nivel iii) a 12,1 % (nivel i)** (tabla a.9). El nivel (ii) es 7,5 %. Un cambio solo es detectable en vehículos con ≥ 2 turnos: con ese denominador (66.482) la tasa es 5,0 %–13,4 %. Ojo con el nivel (iii): filtra cruces de canal y flotas, pero no los artefactos Dealer→Dealer del hallazgo 3, así que sigue siendo una cota superior de las transferencias reales.

### Hallazgo 5 — La edad al cambio (mediana 2,55 años) refleja la edad del parque, no una mayor propensión a transferirse a los 2–3 años

Edad del vehículo (años desde `WarrantyStartDate` de la agenda) al primer turno del cliente nuevo, nivel (iii), n = 7.417 (tabla a.8):

| edad | transferencias | % |
|---|---:|---:|
| < 1 | 804 | 10,9 % |
| 1–2 | 1.958 | 26,5 % |
| 2–3 | 1.541 | 20,8 % |
| 3–4 | 817 | 11,0 % |
| 4–5 | 704 | 9,5 % |
| 5–7 | 692 | 9,4 % |
| 7–10 | 656 | 8,9 % |
| 10+ | 226 | 3,1 % |

El 58,3 % de las transferencias ocurre entre 1 y 4 años, pero eso es composición, no propensión: el 53 % del parque activo en 2025 tiene < 2 años. Dividiendo las transferencias de 2025 por los vehículos activos de cada franja de edad (edad al 2025-07-01; tabla a.8b, figura `_patrones.png` panel central):

| edad | transferencias 2025 (iii) | % de las transferencias | vehículos activos 2025 | % del parque | tasa por vehículo-año (iii) | tasa (i), activos con ≥ 2 turnos |
|---|---:|---:|---:|---:|---:|---:|
| < 1 | 313 | 9,4 % | 20.567 | 28,1 % | 1,5 % | 9,0 % |
| 1–2 | 920 | 27,7 % | 18.508 | 25,3 % | 5,0 % | 15,2 % |
| 2–3 | 596 | 18,0 % | 9.262 | 12,7 % | 6,4 % | 18,2 % |
| 3–4 | 389 | 11,7 % | 5.892 | 8,1 % | 6,6 % | 15,6 % |
| 4–5 | 357 | 10,8 % | 4.917 | 6,7 % | 7,3 % | 14,9 % |
| 5–7 | 322 | 9,7 % | 4.841 | 6,6 % | 6,7 % | 14,8 % |
| 7–10 | 319 | 9,6 % | 6.326 | 8,7 % | 5,0 % | 11,5 % |
| 10+ | 101 | 3,0 % | 2.776 | 3,8 % | 3,6 % | 10,0 % |

La tasa es baja en el primer año (1,5 %; en parte porque muchos vehículos nuevos aún no tienen un segundo turno con el que detectar un cambio) y después es una **meseta de 5–8 % anual entre los años 1 y 7**, con un leve máximo en 4–5 años. No hay un pico a los 2–3 años ni una relación evidente con la caída de asistencia del año 3. Implicancia: la probabilidad de que un vehículo ya no esté en manos del comprador crece de forma aproximadamente lineal con la edad (≈ 5–7 % por año acumulado), y al abrir una ventana en el año 3 una fracción del orden del 15 % ya cambió de cliente; no hace falta modelar un "momento de transferencia" especial.

### Ejemplos anonimizados

- **Cambio permanente (tabla a.10.2):** vehículo `f0c8…9e`: turno FordPass del cliente `ca99…7b` el 2024-04-12 (concluido); después un solo cliente `d70b…31` por WEB el 2024-12-30 con el 1° service. Nivel estricto, sin cruce Dealer↔FordPass.
- **Cambio permanente (tabla a.10.1):** vehículo `b9f0…41` (374.920 km): cliente `affd…7d` un turno el 2024-03-20 y luego `fe61…93` nueve turnos concluidos entre 2024-07 y 2026-06, siempre en el mismo dealer.
- **Alternancia (tabla a.11.1):** vehículo `81a8…91`: `ea83…ed` (Dealer) y `1f52…f5` (WEB/Mobile) se intercalan durante 2024–2025 en el mismo dealer, con services 10° a 13° repartidos entre ambos: dos personas usan y agendan el mismo vehículo (empresa + chofer, o titular + cuenta digital).
- **Alternancia (tabla a.11.2):** vehículo `f005…db`: `cc21…e7` siempre por Dealer y `15c0…39` siempre por FordPass, alternando; el patrón "un id por canal" es el artefacto del hallazgo 3.

---

## 2. Comprador vs cliente de agenda (punto b)

### Hallazgo 6 — El comprador aparece en la agenda de su vehículo el 70,6 % de las veces, y es el vigente el 59,7 %

Sobre 41.906 vehículos vendidos con turnos con `customer_id` (tabla b.1):

| | vehículos | % |
|---|---:|---:|
| comprador aparece en la agenda del vehículo | 29.576 | 70,6 % |
| comprador es el PRIMER cliente de la agenda | 27.695 | 66,1 % |
| comprador es el ÚLTIMO cliente (vigente al CUTOFF) | 25.008 | 59,7 % |
| comprador no aparece en este vehículo pero sí en otros (sobre los 12.330 que no aparecen) | 4.225 | 34,3 % |

Por segmento (tablas b.2–b.5, figura `04_identidad_cliente_vehiculo_comprador.png`):

| segmento | n | % comprador en agenda |
|---|---:|---:|
| PersonType F (física) | 24.796 | 82,2 % |
| PersonType J (jurídica) | 16.721 | 54,8 % |
| PersonType 25 | 348 | 4,3 % |
| Ford Blue | 29.865 | 71,5 % |
| Ford Pro | 12.041 | 68,3 % |
| canal CONSORTIUM | 5.013 | 78,2 % |
| canal ROR | 30.847 | 73,0 % |
| canal DIRECT SALES | 5.607 | 55,7 % |
| canal HR | 439 | 3,0 % |

Las jurídicas (J) explican casi todo el déficit: el comprador es la empresa y el que agenda es otro id (chofer, encargado, sucursal). En Ford Pro la brecha entre F y J se mantiene (82,8 % vs 57,9 %; tabla b.5), así que la BusinessUnit no agrega nada por encima de PersonType.
Cuando el comprador no aparece, el cliente vigente es una flota solo en el 18,3 % de los casos (13,8 % cuando sí aparece; tabla b.6): la mayoría de los "otros" no son grandes flotas sino ids individuales distintos.

**Canal HR y PersonType 25 son un solo comprador (tabla b.7):** las 1.060 ventas HR tienen 292 compradores distintos, pero uno solo concentra 752; PersonType 25 (656 ventas) tiene el mismo id top con 387. Es casi seguro un plan de empleados o una cuenta institucional de Ford: el comprador registrado no es el usuario. Para el modelo, HR y PersonType 25 deberían tratarse como "comprador desconocido".

### Hallazgo 7 — Que vaya el comprador u otro no cambia el retorno

Sobre los eventos de mantenimiento completado en vehículos vendidos (tabla g.1, g.3, g.4):

| | comprador | otro |
|---|---:|---:|
| retorno_15m total | 88,2 % (n 8.875) | 89,1 % (n 5.885) |
| PersonType F | 87,8 % (5.911) | 86,5 % (1.988) |
| PersonType J | 89,1 % (2.964) | 90,4 % (3.834) |
| Ford Blue | 89,6 % (6.105) | 90,2 % (4.003) |
| Ford Pro | 85,2 % (2.770) | 86,7 % (1.882) |
| retorno_12m total | 81,2 % | 83,1 % |

Diferencias de ~1 pp en la dirección contraria a la intuición. `es_comprador` no es una feature de riesgo; sí es un atributo de contacto (a quién llamar). Verificado también con un proxy que ignora "retornos" a ≤ 30 días (re-visitas o turnos duplicados; son el 1,1 % de los eventos): 88,1 % vs 88,9 %. Salvedad: todos estos eventos son de vehículos < 2 años (vendidos en 2024-25 con service antes de 2025-05), así que la conclusión vale para el primer y segundo service, no para vehículos viejos.

---

## 3. Flotas (punto c)

### Hallazgo 8 — Las flotas son pocas pero pesan: 1.185 compradores con 12.261 vehículos (20,6 % de las ventas)

| vehículos por cliente | clientes en sales | vehículos en sales | clientes en agenda | vehículos-cliente en agenda |
|---|---:|---:|---:|---:|
| 1 | 42.425 | 42.425 | 92.035 | 92.035 |
| 2 | 2.349 | 4.698 | 9.306 | 18.612 |
| 3–9 | 1.011 | 4.108 | 2.808 | 11.305 |
| 10–49 | 141 | 2.638 | 313 | 5.837 |
| 50+ | 33 | 5.515 | 62 | 10.283 |
| total | 45.959 | 59.384 | 104.524 | 138.072 |

(tabla c.1). En la agenda, 62 ids con 50+ vehículos concentran 10.283 pares vehículo-cliente. Los 8 más grandes (tabla c.2) tienen entre 335 y 849 vehículos, operan en 2 a 56 dealers distintos, reservan ~100 % por canal Dealer y concluyen 58–77 % de los turnos; tres de ellos (829, 583 y 526 vehículos) **no aparecen como compradores en sales**. Pueden ser rentadoras/leasing que compran por otro canal, o un "cliente genérico" que cargan los dealers (pregunta 3).

### Hallazgo 9 — Ford Pro no es sinónimo de flota, ni PersonType J tampoco

| tamaño de flota del comprador | ventas | % Ford Pro |
|---|---:|---:|
| 1 | 42.425 | 22,3 % |
| 2 | 4.698 | 28,4 % |
| 3–9 | 4.108 | 57,7 % |
| 10–49 | 2.638 | 79,0 % |
| 50+ | 5.515 | 67,2 % |

(tablas c.3–c.4). Solo el 43,1 % de las ventas Ford Pro son a flotas (≥ 3); el 10,1 % de las Ford Blue también lo son. Y 9.676 jurídicas (40,9 % de las J) compran un solo vehículo; en 50+ hay 5.100 J, 415 PersonType 25 y ninguna F (tabla c.5). Para segmentar hay que usar el **tamaño de flota calculado**, no la BusinessUnit ni el PersonType.

Salvedad (verificación, tabla V6.1): el tamaño de flota medido solo con sales cuenta las compras 0 km de 2024-26 y subestima a quien ya tenía Rangers usadas. Combinando sales ∪ agenda (vehículos distintos del mismo `customer_id` en cualquiera de las dos tablas) la flota (≥ 3) pasa de 20,6 % a 24,4 % de las ventas, Ford Blue flota de 10,1 % a 14,0 %, Ford Pro flota de 43,1 % a 46,5 %, y las J con un solo vehículo bajan de 40,9 % a 34,9 %. 564 ventas a compradores "de 1 vehículo" en sales son de clientes con ≥ 3 en la agenda. Las conclusiones no cambian, pero la feature debe calcularse con la unión.

### Hallazgo 10 — Las flotas entran menos y caen antes; adentro, vuelven igual

**Entrada a la red** (vendidos con ≥ 15 meses desde garantía; tabla f.4): 1° mantenimiento completado dentro de 15 meses = 80,4 % (1 vehículo), 79,1 % (2), 73,2 % (3–9), 61,9 % (10–49), 60,0 % (50+). Ford Pro 70,4 % vs Ford Blue 80,2 %.

**Tasa anual de mantenimiento por año de vida** (vehículos de la agenda con `WarrantyStartDate`, solo años de vida enteramente observados entre 2024-01 y 2026-08; grupo según el cliente vigente; tabla c.6, figura `04_identidad_cliente_vehiculo_flotas.png`):

| año de vida | particular (1) | 2 vehículos | flota (≥ 3) | n particular | n flota |
|---:|---:|---:|---:|---:|---:|
| 1 | 71,6 % | 74,3 % | 73,0 % | 25.123 | 5.231 |
| 2 | 79,2 % | 78,1 % | 68,9 % | 23.462 | 5.938 |
| 3 | 70,5 % | 63,8 % | 55,5 % | 12.647 | 4.878 |
| 4 | 62,8 % | 56,2 % | 51,7 % | 9.289 | 2.523 |
| 5 | 55,5 % | 44,9 % | 47,6 % | 7.713 | 1.505 |
| 6 | 40,0 % | 32,8 % | 26,6 % | 5.436 | 830 |
| 7 | 34,9 % | 30,2 % | 23,5 % | 5.452 | 818 |
| 8 | 30,7 % | 25,1 % | 20,4 % | 6.081 | 682 |

La flota pierde 10 pp en el año 2 y 15 pp en el año 3. El "año 3" del tutor se ve en particulares como una caída de 79,2 → 70,5 → 62,8 (años 2→3→4) y el desplome fuerte es en el año 6 (55,5 → 40,0). Ojo: la población son vehículos con al menos un turno en 2024-26 (sesgo de supervivencia), así que los niveles absolutos están sobreestimados, **y en el año 1 el sesgo invierte la comparación**: la tabla muestra a la flota igual o arriba del particular (73,0 % vs 71,6 %) porque excluye a los vendidos que nunca vinieron, que son más frecuentes en flotas. Reconstruyendo los años 1 y 2 desde sales (incluye a los que nunca tuvieron turno; flota medida con sales ∪ agenda; tabla c.6b): año 1 = 64,8 % particular vs 59,1 % flota (n 23.728 / 9.380), año 2 = 73,5 % vs 66,4 % (n 8.366 / 3.004). La flota ya está 5–7 pp abajo desde el primer año.

**A nivel turno** (tabla c.7) las flotas no se diferencian en no-show (5,8 % vs 5,5 %) ni cancelación (20,9 % vs 20,6 %), pero sí en canal: 7,4 % FordPass vs 24,9 % en particulares, 82,9 % Dealer vs 69,9 %.

**Condicional a un service completado** (tabla g.8, estratificado por edad al evento): retorno_15m flota 3–9 vs particular = 85,8 % vs 85,3 % (< 2 años), 82,2 % vs 76,6 % (2–4), 62,1 % vs 58,4 % (4+). Solo las flotas 10+ con vehículos nuevos vuelven menos (82,2 % vs 85,3 %). Conclusión: el riesgo de flota está en **no entrar** y en **abandonar entre años** (que el proxy condicional no ve), no en la probabilidad de volver dado que vino.

---

## 4. Dealer (punto d)

### Hallazgo 11 — Mismo espacio de hash, pero 46 dealers vendedores no existen en la agenda

| | valor |
|---|---:|
| dealers en sales | 107 |
| dealers en agenda | 95 |
| ids en ambas | 61 |
| solo sales | 46 |
| solo agenda | 34 |
| % ventas cuyo dealer está en agenda | 76,1 % |
| % turnos cuyo dealer está en sales | 75,7 % |

(tabla d.1). La ausencia **no** explica que un vehículo no aparezca: 71,9 % de los vendidos por dealers ausentes tienen turnos, contra 70,8 % de los vendidos por dealers presentes (tabla d.2). Y los vehículos de los dealers ausentes se concentran en un dealer de agenda (mediana del share del más frecuente: 59 %, casi igual al 57,65 % de los dealers presentes, para los cuales ese "más frecuente" es él mismo en el 86 % de los casos, aunque solo el 53 % retiene ≥ 50 % de sus primeros turnos; tablas d.3–d.4b). Ejemplo: el dealer `85cc31b84261` vendió 1.910 vehículos con turnos y el 67,1 % hace su primer turno en un mismo dealer de agenda.

Pero la interpretación "mismo dealer con otro código" solo se sostiene para una parte (tabla d.4b): de los 41 dealers ausentes con ventas rastreables (10.042 vehículos), 13 derivan principalmente a un dealer que existe **solo** en la agenda (65 % de esas ventas: candidatos a doble código, p. ej. `4cc4b715e345` → 60,8 % a un solo-agenda, `d8c874bd7792` → 59,7 %), pero los otros 28 (35 % de las ventas) derivan a un dealer que **ya vende con su propio id** (p. ej. el propio `85cc31b84261` deriva a `7fc11e64ab78`, que está en sales), y 9 destinos son compartidos por más de un dealer ausente. Esos parecen puntos de venta o sucursales de un grupo con un único taller, no un id duplicado. Además la concentración es desigual: 26 de 41 tienen ≥ 50 % en un destino, pero hay ausentes con 13–17 % (tabla d.4). Se puede construir una tabla de mapeo por concentración solo para los primeros; conviene pedirla al mentor (pregunta 4).

### Hallazgo 12 — Solo la mitad hace el primer service donde compró

| | vehículos | % 1er mantenimiento en dealer vendedor | % 1er turno en dealer vendedor |
|---|---:|---:|---:|
| todos los vendidos con mantenimiento completado | 36.705 | 38,1 % | 39,1 % |
| solo si el dealer vendedor está en la agenda | 28.112 | 49,7 % | 51,1 % |

(tabla d.5). Ford Blue 48,8 %, Ford Pro 52,0 %; F 50,8 %, J 48,0 % (tabla d.6; figura `04_identidad_cliente_vehiculo_dealer.png`). Al menos la mitad de los clientes elige el taller por cercanía u otro motivo, no por fidelidad al vendedor.

### Hallazgo 13 — El dealer de venta no predice retorno; cambiar de dealer resta poco

- `mismo_dealer_que_venta`: sí 88,8 % (n 5.842) vs no 89,3 % (n 5.596) (tabla g.1). Cruzado con cambio de dealer entre services (tabla g.6): 92,4 % vs 92,4 % sin cambio; con cambio, 85,7 % (n 63) vs 90,8 % (n 238), n chicos.
- `cambio_de_dealer` (vs el mantenimiento anterior), estratificado por edad (tabla g.8): no cambió 88,3 / 82,4 / 70,3 %; cambió 86,1 / 78,1 / 62,7 % (< 2, 2–4, 4+ años). Resta 2 a 8 pp con n de 2.215 / 1.325 / 488 eventos.
- "Primer mantenimiento observado" (sin service anterior en 2024+): 83,1 / 71,1 / 50,6 %. Es en parte censura (vehículos viejos cuyo historial previo a 2024 no se ve) y en parte señal real de "nuevo en la red". Para vehículos < 2 años (donde no hay censura) sigue habiendo 5 pp de diferencia (83,1 % vs 88,3 %).

---

## 5. Vista consolidada por usuario (punto e)

### Hallazgo 14 — 6,9 % de los clientes vigentes concentran 21,4 % de los vehículos activos

| | valor |
|---|---:|
| `customer_id` con algún turno 2025-01-01 → CUTOFF | 86.580 |
| con ≥ 2 vehículos (cualquier turno) | 7.882 (9,1 %) |
| pares vehículo-cliente que cubren | 30.220 (27,7 %) |
| clientes vigentes con vehículos activos 2025-26 | 78.331 |
| con ≥ 2 vehículos vigentes | 5.415 (6,9 %) |
| vehículos activos que cubren | 19.909 (21,4 %) |

(tabla e.1). Distribución de los vigentes (tabla e.2): 4.030 clientes con 2 vehículos (8.060), 1.194 con 3–9 (4.924), 162 con 10–49 (3.086) y 29 con 50+ (3.839).

### Hallazgo 15 — Coincidencia de ventanas: 1.193 clientes con ≥ 2 vehículos el mismo mes en el último año (13,1 % de las ventanas)

**Corrección respecto de la versión anterior.** El cálculo original aproximaba la ventana como "*último* mantenimiento completado + 12 meses" y daba 195 clientes / 1.262 vehículos / 7,2 %. Eso estaba mal planteado: tomar solo el último mantenimiento al CUTOFF excluye del período a todo vehículo que volvió (su "último" corre la ventana al futuro), así que la población de "ventanas entre 2025-09 y 2026-08" quedaba en 17.449 en vez de 82.140 y sesgada hacia los que no retornaron. Ahora cada mantenimiento completado abre una ventana 12 meses después y el cliente es el del turno (el vigente al abrirse la ventana) (tabla e.3):

| | valor |
|---|---:|
| ventanas (mantenimiento completado + 12 m), todas | 216.655 (86.753 vehículos) |
| clientes con ≥ 2 vehículos en ventana el mismo mes (alguna vez) | 2.253 |
| vehículos-ventana involucrados | 29.301 (13,5 %) |
| ventanas que abren entre 2025-09 y 2026-08 | 82.140 |
| clientes con ≥ 2 vehículos en ventana el mismo mes en ese período | 1.193 |
| vehículos-ventana involucrados en ese período | 10.795 (13,1 %) |
| [método original] ventanas del período / coincidentes | 17.449 / 1.262 (7,2 %) |

De los 7.068 pares (cliente, mes) con ≥ 2 vehículos, 4.332 son de exactamente 2 y 463 de 10 o más (tabla e.4). Por mes abren entre 6.342 y 7.648 ventanas (2025-09 a 2026-08), de las cuales 794 a 984 pertenecen a clientes con otro vehículo en ventana ese mismo mes (tabla e.5). Con cliente vigente al CUTOFF en lugar del cliente del turno la coincidencia es 11,3 % (tabla V9.2 de la verificación). Implicancia: la vista consolidada afecta a ~1 de cada 8 ventanas (no a < 10 % como decía la versión anterior), pero sigue sin justificar cambiar la unidad: el score es por vehículo y la consolidación es una capa de presentación/contacto.

---

## 6. Vendidos que nunca aparecen en la agenda (punto f)

### Hallazgo 16 — Tres de cada cuatro "nunca vinieron" todavía no tenían que venir

| meses desde `WarrantyStartDate` al CUTOFF | nunca en agenda | con turnos | % nunca (fila) |
|---|---:|---:|---:|
| 0–3 | 4.648 | 541 | 89,6 % |
| 3–6 | 3.321 | 1.168 | 74,0 % |
| 6–9 | 2.696 | 2.082 | 56,4 % |
| 9–12 | 2.180 | 4.134 | 34,5 % |
| 12–15 | 1.042 | 5.500 | 15,9 % |
| 15–18 | 826 | 5.390 | 13,3 % |
| 18–24 | 1.241 | 11.186 | 10,0 % |
| 24–36 | 1.094 | 12.148 | 8,3 % |

(tabla f.1, figura `04_identidad_cliente_vehiculo_nunca_vino.png`). De los 17.173 sin turno (13.448 compradores), 74,8 % tiene < 12 meses (mediana 6,6 meses; 120 sin `WarrantyStartDate` cuentan como "no < 12"), 4.208 tienen ≥ 12 meses y **3.166 tienen ≥ 15 meses: son el 9,9 % de los 31.892 vendidos con ≥ 15 meses** (tabla f.2). Esa población no está en la agenda: si la unidad de análisis se construye solo desde la agenda, se la pierde.

Ojo con la etiqueta "elegible y nunca vino": 9,9 % es "sin ningún turno, ni siquiera cancelado". Con definiciones más cercanas al target (tabla V10.2 de la verificación, sobre los mismos 31.892): sin ningún turno concluido 11,7 % (3.735; 569 están en la agenda solo con cancelados / no-show / pendientes), sin ningún mantenimiento completado 15,9 % (5.070), y sin primer mantenimiento *dentro* de los 15 meses 22,8 % (complemento del 77,2 % de la tabla f.4). Para el target lo que importa es la última cifra; los 3.166 son solo la parte que ni siquiera figura en la agenda.

Entre los vendidos con ≥ 15 meses, % que nunca vino (tabla f.3): F 8,8 % / J 10,7 %; Ford Blue 7,3 % / Ford Pro 15,9 %; ROR 8,2 %, CONSORTIUM 9,5 %, DIRECT SALES 17,0 %, HR 31,7 %; flota 1: 7,9 %, 3–9: 13,3 %, 10–49: 20,8 %, 50+: 20,3 %; dealer vendedor en agenda 9,8 % vs ausente 10,4 % (de nuevo, la cobertura de dealers no explica nada).

---

## 7. Recomendación de unidad de análisis y features (punto g)

### Unidad de análisis

**Vehículo × ventana, con el cliente vigente al momento del scoring como atributo (no como clave).** Razones con números:

1. El 21,0 % de los vehículos cambia de `customer_id` y el 76,5 % de esos cambios es permanente (hallazgos 1–2): el vehículo es la entidad estable; el cliente hay que resolverlo "as-of" (último `customer_id` con turno ≤ fecha de scoring).
2. Una parte de los cambios es la misma persona con dos ids (hallazgo 3): usar `customer_id` como clave partiría el historial de un mismo dueño en dos.
3. El comprador ya no es el vigente en el 40,3 % de los vehículos vendidos (hallazgo 6); `sales.customer_id` es un atributo del vehículo ("comprador original"), no la identidad del usuario.
4. La población debe incluir a los vendidos sin agenda (hallazgo 16): la ventana se abre desde `WarrantyStartDate` aunque no haya turnos.
5. La vista consolidada por usuario se arma agrupando por cliente vigente (hallazgos 14–15): afecta al 21,4 % de los vehículos activos y al 13,1 % de las ventanas mensuales, y no requiere cambiar la unidad.

### Features derivadas: qué discriminan y qué no (proxy retorno_15m, tablas g.1, g.2, g.8)

| feature | evidencia univariante | veredicto |
|---|---|---|
| `es_comprador` | 88,2 % vs 89,1 %; sin diferencia dentro de F/J ni Blue/Pro | **No discrimina.** Mantener como atributo de contacto y para explicar "a quién llamar". Tratar HR y PersonType 25 como "comprador desconocido". |
| `n_clientes_distintos_vehiculo` (as-of) | 1: 85,0 / 77,1 / 58,2 %; 2: 86,6 / 81,1 / 65,5 %; 3+: 85,8 / 86,0 / 71,7 % (< 2, 2–4, 4+ años) | Más clientes ⇒ **más** retorno (+1,6 a +13,5 pp). Es señal de vehículo activo y uso mixto Dealer/FordPass, no de transferencia. Útil pero correlacionada con n° de turnos previos; preferir esa última. |
| `tamaño_flota_cliente` (agenda, as-of) | condicional a un service: 1: 85,3 / 76,6 / 58,4 %; 3–9: 85,8 / 82,2 / 62,1 %; 10+: 82,2 / 80,7 / 61,9 % | Débil dentro de la red (±5 pp). **Fuerte en la entrada** (1° service: 80,4 % vs 60,0 %) y en la curva por año de vida (−10 a −15 pp). Imprescindible para la población sin historial y para los "3 tipos de cliente". |
| `tamaño_flota_comprador` (sales) | 1: 88,6 %, 2: 89,2 %, 3–9: 88,3 %, 10–49: 86,0 %, 50+: 88,5 % | Redundante con la versión de agenda una vez adentro; usar solo para vendidos sin agenda. |
| `mismo_dealer_que_venta` | 88,8 % vs 89,3 %; calculable solo para el 76,1 % de las ventas | **No discrimina** y tiene cobertura parcial. Requiere tabla de mapeo de dealers para siquiera calcularse bien. |
| `cambio_de_dealer` (vs mantenimiento anterior) | −2,2 / −4,3 / −7,6 pp por franja de edad; n 2.215 / 1.325 / 488 | Señal modesta y consistente; incluir. "Primer mantenimiento observado" −5 pp en vehículos < 2 años (83,1 % vs 88,3 %). |
| `meses_desde_transferencia` | 0–3 meses: 85,2 / 79,3 / 62,9 %; 3–6: 87,9 / 85,7 / 73,0 %; 6–12: 87,0 / 83,3 / 72,0 % | El primer service post-cambio (0–3 meses) vuelve menos que los siguientes (−3 a −10 pp). Incluir como "transferencia reciente (< 3 meses)" y limpiar los cruces Dealer↔FordPass antes. |

Confundidor dominante: la edad del vehículo al evento (85,2 / 77,7 / 58,9 %, tabla g.8.0) y el n° de service (82,8 % en el 1° → 74,5 % en el 5°, tabla g.1). Cualquier feature de identidad se evalúa condicional a eso. Con horizonte de 12 meses las conclusiones no cambian (tabla g.7; base 72,6 %).

**Segmentación sugerida para los "3 tipos de cliente" del tutor**, con base en este tema: (1) particular con un vehículo (71,4 % de las ventas, 1° service 80,4 %), (2) flota chica 2–9 vehículos (14,8 % de las ventas; 1° service 73–79 %), (3) flota grande 10+ (13,7 % de las ventas; 1° service 60–62 %, 7,4 % de reservas por FordPass contra 24,9 % en particulares). Es una propuesta a validar con los otros temas (uso/kilometraje).

---

## 8. Problemas de calidad de datos

1. **Identidad partida (mismo dueño, dos `customer_id`):** al menos el 19,9 % de los cambios secuenciales en vehículos vendidos son artefactos seguros (el comprador aparece después de otro id; tabla a.12). Una parte va con cambio de canal (34,1 % de los cambios son cruces Dealer↔FordPass vs 11,4 % esperado), pero el 57 % de los artefactos seguros es Dealer→Dealer (tabla a.12b): el dealer carga ids distintos para el mismo vehículo (pre-entrega, chofer, familiar). Infla "transferencias" y "clientes distintos" y no se limpia filtrando por canal.
2. **`KM` es un snapshot por vehículo (99,99 % constante en 82.347 vehículos con ≥ 2 valores), no el odómetro del turno.** Coincide con el `VehicleCurrentKM` del último turno en el 95,9 % de los vehículos (tabla 0.3). `VehicleCurrentKM` sí varía (97,5 %) pero tiene 22 % de nulos. Usar `KM` como feature es leakage del futuro. (Tablas 0.2–0.3; corresponde al tema de uso/kilometraje.)
3. **Dealers con doble código o sucursales:** 46 `dealer_id` de sales no existen en la agenda y 34 de la agenda no existen en sales. 13 de los 41 ausentes con ventas rastreables (65 % de sus ventas) derivan a un dealer solo-agenda (candidatos a doble código); los otros 28 derivan a un dealer que ya vende con su id (sucursales / puntos de venta). Falta una tabla de equivalencia (tabla d.4b).
4. **9.398 turnos sin `customer_id` y 2.897 sin `vehicle_id`** (tabla 0.1).
5. **Ids "mega-cliente":** 62 `customer_id` con 50+ vehículos (hasta 849), en 40–56 dealers, 100 % canal Dealer; 3 de los 8 mayores no compran en sales. Pueden ser rentadoras, leasing o un cliente genérico del dealer.
6. **Canal HR / PersonType 25:** un solo `customer_id` compra 752 ventas HR y 387 PersonType 25; el 97 % de esos vehículos tiene otro cliente en la agenda. Los códigos 25/29/30 de PersonType no están documentados.
7. **Censura a izquierda:** la agenda empieza en 2024-01, así que "primer cliente", "primer mantenimiento observado" y "n_clientes as-of" están truncados para vehículos anteriores a 2024 (ModelYear ≤ 2023 es la mayoría del parque).

---

## 9. Preguntas para el mentor

1. ¿El `customer_id` de un turno es el titular del vehículo en el sistema del dealer o la cuenta que hizo la reserva (FordPass/WEB)? ¿Un mismo dueño puede tener un id por canal? Esto decide si el 34 % de "cambios" Dealer↔FordPass son transferencias o ruido.
2. ¿Existe un evento formal de transferencia de titularidad (cambio de dueño con consentimiento, como mencionó el tutor) que se pueda cruzar? Hoy solo se infiere por el orden de los turnos.
3. ¿Qué son los `customer_id` con cientos de vehículos en decenas de dealers que no aparecen en sales (por ejemplo 829 y 583 vehículos)? ¿Rentadoras, leasing, cliente genérico del DMS?
4. ¿Hay una tabla de equivalencia entre el `dealer_id` de ventas (107) y el de posventa (95)? Los 46 códigos de venta ausentes de la agenda parecen ser los mismos dealers con otro id.
5. ¿Qué significan PersonType 25, 29 y 30, y el canal HR? ¿Confirman que el id que compra 752 unidades HR es un plan de empleados?
6. `KM` en la agenda: ¿es el último odómetro conocido del vehículo (snapshot) o el del turno? Los datos dicen snapshot; si es así, ¿pueden proveer el odómetro histórico por turno o hay que usar `VehicleCurrentKM` (22 % nulo)?
7. Para la vista consolidada: ¿el "usuario" de la ficha es el `customer_id` del último turno, el comprador, o una cuenta FordPass? Con lo que hay, el último `customer_id` es el único vigente al scoring.
8. Flotas: ¿las grandes flotas tienen contratos de mantenimiento fuera de la red oficial (talleres propios)? Explicaría el 1° service de 60 % contra 80 % en particulares y definiría si son población objetivo o no.
