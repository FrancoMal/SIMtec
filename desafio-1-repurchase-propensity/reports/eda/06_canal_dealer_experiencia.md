# EDA 06 — Señales de canal, dealer, conectividad y experiencia como candidatas a features

**Script:** `scripts/eda/06_canal_dealer_experiencia.py` (corre de punta a punta en ~30 s).
**Apéndice de tablas (autogenerado, fuente de todas las cifras):** `reports/eda/06_canal_dealer_experiencia_tablas.md`.
**Figuras:** `reports/figures/eda/06_canal_dealer_experiencia_*.png`.
**Base de datos:** agenda a nivel turno (`repurchase.eventos.appointments`, 492.442 turnos) y `CUTOFF = 2026-08-25`.
**Verificación independiente:** `reports/eda/06_canal_dealer_experiencia_verificacion.md` (script `scripts/eda/06_canal_dealer_experiencia_verificacion.py`). Las correcciones que surgieron de ahí ya están incorporadas en este texto y están marcadas como *[corregido en verificación]*.

## 0. Resumen ejecutivo

1. **La etiqueta aproximada de retorno** (mantenimiento completado entre 2024-01 y 2025-05 → ¿el mismo vehículo completó otro mantenimiento en ≤15 meses?) da **78,7% de retorno / 21,3% de "churn"** sobre 109.073 turnos base de 56.826 vehículos, estable mes a mes (76,9%–80,2%). Es una etiqueta de conveniencia para comparar señales; el target definitivo (ventana + horizonte) lo fija otro tema.
2. **Las señales de este tema son de segundo orden frente a la edad del vehículo.** El año modelo tiene IV 0,29 (retorno de 46,7% en ≤2015 a 92,0% en 2025+); la mejor señal propia de este tema, la recencia del mantenimiento previo, tiene IV 0,18; el canal de agendado, 0,03; la encuesta, 0,007.
3. **Recencia e intensidad de relación con la red son las señales más fuertes y más limpias**: un vehículo cuyo turno previo fue hace >365 días retorna 50,6% vs 85,9% si fue hace 31–90 días; 0 turnos previos → 73,5% vs 5+ → 84,5%. Con la etiqueta a 15 meses parte de esto es ritmo de uso (km/año), que otro tema modela directamente.
4. **No-shows y cancelaciones previas: univariante no discriminan, pero sí lo hacen a igual intensidad de contacto** *[corregido en verificación]*. Crudo: 78,0% / 78,9% / 79,1% de retorno para 0/1/2+ no-shows previos (IV 0,000) y 77,8 → 81,5% para cancelaciones reales. Pero tener un no-show previo exige haber tenido turnos, y los turnos previos suben el retorno (0 → 5+: 73,5 → 84,5%). Dentro de cada nivel de turnos previos, el vehículo con no-show retorna sistemáticamente menos (67,0 vs 73,0% con 1 turno previo; 76,4 vs 81,1% con 3–4). En un modelo conjunto del historial, el OR ajustado es **0,73 / 0,63** (1 / 2+ no-shows) y **0,75 / 0,70** (cancelaciones reales): es una paradoja de Simpson y estas features **sí van al modelo**. Lo que sigue sin señal: el rating de la encuesta (1–2 estrellas: 80,3% vs 5 estrellas: 83,1%), pick-up & delivery, servicio móvil, cliente esperando. Y el "vehículo con problemas vuelve más" (2+ recalls previos → 88,3% vs 75,8%) es enteramente intensidad de contacto: a igual cantidad de turnos previos, recalls (OR 0,96–0,98), reparaciones (0,97) y re-visitas (0,96–1,00) no agregan nada; lo que retiene es el contacto, no el motivo.
5. **FordPass sí se asocia a mayor retorno, pero la mitad del efecto crudo es mix de generación:** 83,8% vs 77,2% Dealer sin controlar; dentro de P375 79,3 vs 74,5 (+4,8 pp), dentro de P703 88,8 vs 85,7 (+3,1 pp); OR ajustado por generación, año modelo y n° de service = 1,29. Es legítimo al scoring (canal del último turno).
6. **El dealer es una feature legítima y accionable:** la tasa de retorno por dealer es estable entre 2024 y 2025 (Pearson 0,68, Spearman 0,79 sobre 86 dealers; con vehículos disjuntos entre años, 0,64 / 0,68; residuos ajustados por mix, 0,56 / 0,71 *[agregado en verificación]*), su dispersión (desvío 5,6 pp) es 3,7 veces la que produciría el azar binomial (1,5 pp), y un target-encoding calculado en 2024 y aplicado a 2025 separa 73,3% (peor quintil) de 83,8% (mejor quintil), diferencia que se mantiene al descontar el mix de vehículos de cada quintil (−4,0 vs +4,7 pp de residuo). El 90,7% de los retornos se hacen en el mismo dealer.
7. **`ConnectedStatusARG` es un snapshot con leakage:** no varía en el tiempo (74 de 111.752 vehículos con más de un valor), "Sin Información de Conectividad" retorna 27,0% y solo el 41,4% de esos vehículos vuelve a aparecer en la agenda con cualquier status (vs 90–96% en el resto): marca vehículos que salieron del sistema, cosa que se sabe *después*. Dentro de P703, Conectado vs No tiene conectividad no discrimina (OR 0,82). Excluir o reconstruir.
8. **`SurveyStarRating` no es una encuesta post-service:** el 100% de las 36.920 respuestas son *anteriores* a la fecha del turno (mediana 8 días antes) y solo existe para turnos FordPass/Mobile/WEB (0% en Dealer). Parece una encuesta del proceso de agendado. Sin poder predictivo.
9. **Calidad/semántica de flags:** el 68% de los "(70) Cancelado" tienen `IsReschedule=Y` y el 71,9% de esos se re-agendan en ≤30 días (mediana 6 días): son reprogramaciones, no cancelaciones. `ScheduleReturn=Y` es una re-visita a mediana 15 días de otro turno (37% diagnóstico, 30% reparación). Varios "sin dato" (NeededTowing, ScheduleReturn) son artefactos del canal digital, no señal.
10. **Tendencia 2024→2026 sin quiebre de sistema:** volumen mensual sube de ~13,9k (ene-24) a ~17–18,6k turnos (2026); FordPass pasa de 9,6% a 25,5% de los turnos; no-show baja de 6,9% a 4,7%; reprogramaciones suben de 10,7% a 17,3% (jul-26) y 18,5% (ago-26) *[cifras de agosto 2026 corregidas en verificación: la versión anterior incluía las reservas del 26–31/8]*. Un cambio operativo visible: el check-in nulo entre concluidos cae de 29,4% (ene-24) a 13,1% en nov-24 y se mantiene entre 5,7% y 11,8% desde entonces. Agosto 2026 es parcial (hasta el 25) y arrastra 1.040 turnos "(40) En progreso".

## 1. Etiqueta aproximada y base

**Definición (solo para este EDA):** turno base = `is_completed_maintenance` con `event_date` en [2024-01-01, 2025-05-31] y `vehicle_id` no nulo. `retorno = 1` si el mismo vehículo tiene otro mantenimiento completado con fecha *estrictamente posterior* y ≤ `event_date + 15 meses` (acotado al CUTOFF). Un vehículo aporta tantas filas como mantenimientos completó en el período.

| Ítem | Valor |
|---|---|
| Turnos de mant. completado en el período con `vehicle_id` nulo (excluidos) | 884 |
| Turnos base | 109.073 |
| Vehículos distintos | 56.826 |
| % retorno (≤15 meses) | 78,7 |
| % no retorno (churn aproximado) | 21,3 |
| % retorno exigiendo ≥30 días al próximo mantenimiento (sensibilidad) | 78,5 |
| Turnos con horizonte truncado por CUTOFF (los de 26–31/5/2025, hasta 6 días) | 1.702 |
| Turnos cuyo "próximo mantenimiento" está a ≤1 día (probables duplicados) | 95 |
| Mediana de días al próximo mantenimiento cuando existe | 171 |

La etiqueta es estable por mes del turno base (mín. 76,9% en ene-24, máx. 80,2% en nov-24) y por mes calendario (77,9%–80,2%): no hay estacionalidad en el retorno que contamine las comparaciones.

**Por qué 884 exclusiones importan:** esos turnos tienen `vehicle_id` nulo y el 99,9% también `ModelYear` nulo; sin identidad del vehículo no se puede definir retorno, y pandas empareja NaN con NaN en el merge, lo que mezclaba historiales. En la primera corrida esto inflaba el IV de todas las features de historial (aparecía un bin "sin dato" con 0% de retorno). Queda documentado como riesgo para quien arme el dataset analítico.

**Advertencia estructural sobre la etiqueta:** un horizonte fijo de 15 meses favorece a los vehículos de alto uso (hacen el service cada ~5–6 meses) y castiga a los de bajo uso aunque cumplan el ciclo anual. Por eso las features de "intensidad" (turnos previos, mantenimientos previos, recencia) miden en parte ritmo de uso, que es el tema de otro EDA. Cuantificado en la verificación *[agregado]*: con km/año aproximado (`VehicleCurrentKM` / edad desde garantía), el retorno a 15 meses va de 62,7% (<10.000 km/año, n 10.020) a 87,7% (>50.000, n 9.639), IV 0,23, más que cualquier feature de este tema. El target definitivo, al abrir la ventana por km/tiempo, debería neutralizar ese sesgo.

## 2. Controles estructurales (no son de este tema; se usan para no confundir)

| Generación | n | Retorno % |
|---|---|---|
| P375 (generación anterior) | 76.483 | 75,3 |
| P703 (nueva generación) | 32.300 | 86,8 |
| Otro/Raptor (master data incompleta) | 290 | 54,1 |

| Año modelo | n | Retorno % |
|---|---|---|
| ≤2015 | 2.381 | 46,7 |
| 2016–18 | 8.327 | 57,8 |
| 2019–21 | 19.990 | 71,5 |
| 2022–23 | 45.785 | 81,7 |
| 2024 | 30.155 | 86,5 |
| 2025+ | 2.103 | 92,0 |

N° de service del turno base: 1° → 82,9%, 2° → 82,7%, 3° → 80,9%, 4°–5° → 77,0%, 6°–8° → 77,0%, 9°+ → 73,6%. Consistente con el insight del tutor (la asistencia cae con la edad del vehículo). Toda comparación de canal/conectividad de abajo se hace dentro de generación × año modelo.

## 3. (a) ScheduleSource — canal de agendado

**Mix por año** (turnos con `ScheduleDate ≤ CUTOFF`; figura `_fuente_mix_mensual.png`):

| Año | Dealer | FordPass | WEB | Mobile | CAF | Turnos |
|---|---|---|---|---|---|---|
| 2024 | 80,7 | 15,0 | 3,0 | 1,0 | 0,3 | 162.404 |
| 2025 | 71,2 | 22,7 | 3,9 | 1,9 | 0,3 | 194.098 |
| 2026 (hasta 25/8) | 65,2 | 25,8 | 5,4 | 3,5 | 0,1 | 132.114 |

FordPass pasa de 9,6% de los turnos en enero 2024 a 25,5% en agosto 2026 (hasta el 25). Implicancia de modelado: cualquier feature "canal" tiene drift temporal fuerte; en validación temporal el mix de test será más digital que el de train.

**Resultado del turno por fuente** (turnos resueltos: 60/70/80/90):

| Fuente | n | Concluido | Sin OS | No-show | Cancel. real (IsReschedule=N) | Reprogramación (IsReschedule=Y) |
|---|---|---|---|---|---|---|
| Dealer | 353.253 | 72,3 | 3,7 | 6,2 | 6,2 | 11,6 |
| FordPass | 102.390 | 66,6 | 2,0 | 3,9 | 7,9 | 19,6 |
| WEB | 19.474 | 60,5 | 1,2 | 4,4 | 6,5 | 27,4 |
| Mobile | 9.843 | 66,5 | 1,7 | 4,6 | 8,0 | 19,2 |
| CAF | 1.199 | 53,0 | 6,3 | 10,4 | 13,4 | 16,8 |

Los turnos digitales se **reprograman** mucho más (19,6% FordPass, 27,4% WEB vs 11,6% Dealer) pero tienen **menos no-show** (3,9% vs 6,2%). El cliente digital mueve el turno, no lo abandona.

**Retorno según la fuente del turno base** (figura `_fuente_retorno_estratos.png`):

| Fuente | n | Retorno % | Lift vs 78,7% |
|---|---|---|---|
| Dealer | 80.316 | 77,2 | 0,98 |
| FordPass | 23.187 | 83,8 | 1,07 |
| WEB | 3.809 | 80,2 | 1,02 |
| Mobile | 1.751 | 75,8 | 0,96 |

**¿FordPass = clientes más fieles o solo vehículos más nuevos?** Las dos cosas. FordPass es el 34,1% de los turnos base P703 y solo el 15,9% de los P375. Controlando:

| Estrato | Dealer % (n) | FordPass % (n) | Diferencia pp |
|---|---|---|---|
| P375 ≤2015 | 46,3 (2.056) | 54,4 (228) | +8,1 |
| P375 2016–18 | 57,3 (6.812) | 62,3 (1.129) | +5,0 |
| P375 2019–21 | 71,0 (15.738) | 74,0 (3.267) | +3,0 |
| P375 2022–23 | 80,9 (35.575) | 85,0 (7.539) | +4,1 |
| P703 2024 | 85,5 (18.600) | 88,4 (10.235) | +2,9 |
| P703 2025+ | 90,8 (1.207) | 93,1 (786) | +2,3 |

El efecto sobrevive en todos los estratos pero se achica de +6,6 pp crudos a +2 a +5 pp. Regresión logística sin penalización (n=108.731, controlando generación, año modelo y n° de service): **OR FordPass 1,29**, WEB 1,06, Mobile 0,96 (ref Dealer). IV de `ScheduleSource` = 0,028 (débil). Dato colateral de la misma regresión: controlando año modelo, un n° de service más alto *aumenta* el retorno (OR 2,6 para 9°+ vs 1°): a igual edad, el que ya hizo muchos services sigue haciéndolos.

**Patrón de nulos por canal (importante para no leer ruido como señal):**

| Fuente | NeededTowing % nulo | ScheduleReturn % nulo | SurveyStarRating % nulo | EffectiveCheckinDate % nulo |
|---|---|---|---|---|
| Dealer | 0 | 0 | 100,0 | 18,5 |
| FordPass | 68,7 | 27,9 | 62,7 | 12,7 |
| WEB | 62,7 | 28,6 | 77,6 | 19,2 |
| Mobile | 65,7 | 23,5 | 65,9 | 13,2 |

`ScheduleReturn` nulo existe solo en 2024 (10,8% de la base 2024, 0% en 2025). Por eso "sin dato" de NeededTowing retorna 83,5%: es FordPass disfrazado.

## 4. (b) ConnectedStatusARG — conectividad (snapshot)

- **Es un snapshot:** solo 74 de 111.752 vehículos tienen más de un valor a lo largo de sus turnos. Refleja el estado a la fecha de extracción, no al momento del turno.
- **Es casi la generación:** Conectado = 187.362 turnos P703 vs 1.824 P375; No Conectado = 231.709 P375 vs 3.058 P703. Solo tiene variación interna en P703 (Conectado / No tiene conectividad / Sin información).

| ConnectedStatusARG | n base | Retorno % | % con algún turno posterior (cualquier status) |
|---|---|---|---|
| Conectado | 26.877 | 87,2 | 95,6 |
| No Conectado | 70.332 | 79,3 | 90,6 |
| No tiene Conectividad | 8.940 | 64,9 | 76,4 |
| Sin Información de Conectividad | 2.924 | 27,0 | 41,4 |

**Dentro de cada generación** (figura `_conectividad_retorno.png`):

| Estrato | Conectado | No Conectado | No tiene Conectividad | Sin Información |
|---|---|---|---|---|
| P703 2024 (n 24.731 / 518 / 4.523 / 383) | 87,5 | 86,5 | 85,4 | 35,0 |
| P703 2025+ (n 1.604 / — / 449 / —) | 93,4 | — | 89,1 | — |
| P375 2022–23 (n 438 / 40.753 / 3.059 / 1.535) | 60,5 | 87,1 | 40,4 | 26,8 |
| P375 2019–21 (n — / 18.351 / 909 / 630) | — | 75,4 | 34,0 | 19,7 |

OR ajustados por año modelo dentro de P703 (ref Conectado): No Conectado 0,90, No tiene Conectividad 0,82, **Sin Información 0,08**. Dentro de P375 (ref No Conectado): Conectado 0,21, No tiene 0,11, Sin Información 0,06.

**Lectura:** la conectividad real (tener modem activo) no discrimina dentro de P703 (87,5 vs 85,4). Lo que discrimina son las categorías "raras" para cada generación (Conectado en P375, No tiene conectividad en P375, Sin información en ambas), que retornan 27–60% y cuyos vehículos en gran medida **desaparecen de la agenda** (solo 41,4% de los "Sin información" vuelve a aparecer con cualquier status vs 90–96% del resto). Eso es consistente con un estado asignado *a posteriori* a vehículos que salieron del padrón (transferencia, baja, pérdida de contacto) — el caso de "transferencia de titularidad" que mencionó el tutor. **Usarla como feature es leakage** salvo que Ford pueda reconstruir el valor a la fecha de scoring. IV crudo 0,31 (el más alto de todo el ranking) por esta razón.

## 5. (c) SurveyStarRating — encuesta

- 36.920 turnos con respuesta (7,5% del total). Distribución: 5 estrellas 31.014 (84,0%), 4: 3.736, 3: 1.309, 1: 532, 2: 329.
- **El 100% de las respuestas es anterior a `ScheduleDate`** (p5 −26 días, mediana −8, p95 −2; figura `_encuesta_retorno.png`, panel izquierdo). Ninguna respuesta el mismo día ni después.
- Tasa de respuesta por fuente: **Dealer 0,0%** (355.273 turnos), CAF 0,0%, FordPass 29,1%, Mobile 30,9%, WEB 17,9%. Por status: cancelados 8,3%, concluidos 7,6%: se responde aun cuando el turno después se cancela.
- Conclusión semántica: no es la encuesta de satisfacción del service (CSI) sino algo respondido entre el agendado digital y la fecha del turno (encuesta de la app/proceso de agendado, o un dato del turno anterior mal pegado). Hay que confirmarlo con el mentor.

| Rating del turno base | n | Retorno % |
|---|---|---|
| 1–2 | 233 | 80,3 |
| 3 | 369 | 80,2 |
| 4 | 1.149 | 81,6 |
| 5 | 8.341 | 83,1 |
| Sin respuesta | 98.981 | 78,3 |

Restringiendo a turnos digitales (donde la encuesta existe): P375 respondió 77,5% vs no respondió 79,0%; P703 89,2% vs 88,3%. Es decir, el +4,8 pp de "5 estrellas vs sin respuesta" es enteramente el efecto FordPass/generación. Rating 1–2 en P375 (n 158): 78,5%, igual que el promedio. **IV 0,007: sin poder predictivo**, ni como rating ni como "respondió". Sesgo de respuesta: 37% en FordPass en ambas generaciones, 20–28% en WEB.

## 6. (d) Dealer

95 dealers con turnos; 90 con ≥100 turnos base. Figuras `_dealer_dispersion.png`, `_dealer_lorenz.png`, `_dealer_estabilidad.png`.

**Dispersión entre dealers** (92 dealers con ≥300 turnos resueltos; retorno: 90 con ≥100 turnos base):

| Tasa | p10 | p50 | p90 |
|---|---|---|---|
| Concluido | 60,3 | 71,8 | 78,2 |
| No-show | 0,4 | 4,5 | 8,9 |
| Cancelación real | 4,6 | 6,4 | 10,2 |
| Reprogramación | 8,8 | 12,8 | 19,7 |
| Retorno (base) | 70,6 | 78,7 | 83,8 |

Un no-show de 0,4% en el p10 con 4,5% de mediana sugiere que algunos dealers no registran no-shows (los cargan como cancelación o los borran): la tasa de no-show por dealer es en parte práctica administrativa.

**Concentración:** top-10 dealers = 28,4% de los turnos, top-20 = 44,4%, dealer #1 = 4,2% (20.515 turnos), mediana 4.152 turnos por dealer, Gini 0,369. Concentración moderada: no hay un puñado de dealers que expliquen el fenómeno.

**Estabilidad 2024 → ene–may 2025** (86 dealers con ≥100 turnos base en ambos años):

| Métrica | Valor |
|---|---|
| Pearson r (retorno 2024 vs 2025) | 0,679 |
| Spearman rho | 0,791 |
| Desvío estándar observado entre dealers | 5,6 pp |
| Desvío esperado solo por ruido binomial (n medio por dealer) | 1,5 pp |
| Ratio observado / esperado | 3,71 |
| Correlación entre share P703 del dealer (sobre sus turnos resueltos) y su retorno | −0,159 (sobre turnos base: −0,05) |
| Residuo del dealer (observado − esperado por mix generación × año modelo): p10 / p90 | −7,9 / +5,2 pp |

**Salvedades agregadas en la verificación:** (i) el 65,6% de los vehículos de la base 2025 también tienen un turno base en 2024, así que la correlación 2024–2025 no es entre muestras independientes; con vehículos disjuntos (base 2025 sin turno base en 2024; 79 dealers con n ≥100 / ≥50) queda en Pearson 0,64 / Spearman 0,68, y una partición aleatoria por vehículo dentro de 2024 da 0,76 entre mitades. (ii) Los residuos ajustados por mix (generación × año modelo × n° de service) de 2024 y 2025 correlacionan 0,56 / 0,71 entre sí: lo estable no es solo el mix. (iii) Al ajustar por mix, el desvío entre dealers baja apenas de 5,6 a 5,0 pp.

**Validación fuera de tiempo:** quintiles de retorno del dealer calculados con turnos base de 2024 (dealers con ≥50), aplicados a los turnos base de ene–may 2025. Los quintiles se cortan sobre los turnos de 2025 (cada quintil tiene ~1/5 de los turnos, no 1/5 de los dealers); cortándolos por dealer el resultado es equivalente (Q1 71,4% → Q5 83,8%, IV 0,064):

| Quintil del dealer en 2024 | n (2025) | Retorno 2025 % |
|---|---|---|
| Q1 (peor) | 8.188 | 73,3 |
| Q2 | 5.956 | 73,8 |
| Q3 | 7.055 | 78,5 |
| Q4 | 6.812 | 81,7 |
| Q5 (mejor) | 6.844 | 83,8 |

IV 0,06 de esta versión honesta (vs 0,08 de `dealer_id` crudo con 90 categorías, que está inflado por cardinalidad). El efecto dealer **no es mix** (la correlación con share P703 es negativa y chica; el residuo ajustado por mix sigue yendo de −7,9 a +5,2 pp; y el retorno 2025 de cada quintil, descontado el esperado por el mix del propio quintil, va de −4,0 pp en Q1 a +4,7 pp en Q5, OR ajustado 0,78 → 1,40 vs Q3) y **es estable**: es una feature legítima y, sobre todo, un driver accionable (Ford puede intervenir sobre el dealer, no sobre el año modelo).

Extremos (n_base ≥100): dealer `5bbb50452413` retorna 59,3% (1.049 turnos base, residuo −21,1 pp) y `290e545b87fd` 58,3%; en la punta alta, `bd95dd740930` 86,9% (1.936; +8,5 pp) y `620515200d35` 87,9%. Mayores caídas interanuales: `5804ce1783a5` de 79,6% (n 373) a 51,4% (n 183), −28,3 pp; `290e545b87fd` de 67,4% a 43,8%. Los dos pierden también volumen en 2025: candidatos a "dealer en problemas" que un tablero de seguimiento debería levantar.

**Fidelidad al dealer:** de los 85.821 retornos, el 90,7% se hace en el **mismo** dealer. El churn a la red y el churn al dealer son casi la misma cosa; la acción de retención tiene dueño natural.

## 7. (e) Servicios de conveniencia y atributos del turno base

Figura `_conveniencia_retorno.png`. Retorno por categoría (base completa, promedio 78,7%):

| Feature | Categoría | n | Retorno % | Dif. pp | Comentario |
|---|---|---|---|---|---|
| Pick-up & delivery | sí / no | 3.493 / 105.580 | 80,0 / 78,6 | +1,3 | Sin señal |
| Servicio móvil | sí / no | 1.406 / 107.667 | 78,3 / 78,7 | −0,4 | Sin señal |
| Cliente esperó | Y / N | 913 / 108.160 | 77,4 / 78,7 | −1,2 | Sin señal; Y raro |
| Necesitó remolque | Y / N | 45 / 89.543 | 66,7 / 77,6 | −12,0 | n=45, anecdótico. "Sin dato" (19.485) = 83,5% es artefacto FordPass |
| Precio fijo Ford en el turno | sí / no | 24.080 / 84.993 | 81,5 / 77,9 | +2,9 | Débil; correlaciona con services de menor n° |
| IsReschedule (turno nacido de reprogramación) | Y / nulo | 13.815 / 95.258 | 79,7 / 78,5 | +1,1 | Sin señal |
| ScheduleReturn (re-visita) | Y / N | 2.049 / 99.040 | 84,0 / 78,2 | +5,4 | Raro en mantenimientos; ver historial |
| DaysInDealer | 0 / 1 / 2–3 / 4–7 / 8–14 / 15–30 / 31+ | 55.957 / 17.112 / 12.006 / 11.686 / 6.567 / 4.102 / 1.565 | 79,9 / 77,4 / 77,8 / 77,5 / 77,6 / 76,6 / 76,0 | −3,9 (0 vs 31+) | Escalón en 0 vs ≥1 día; plano entre 1 y 14 (77,4–77,8); OR ajustado 31+ vs 0 = 0,77; 78 casos negativos |
| ServiceDuration máx. del ítem | 60 / 120 min | 92.675 / 14.071 | 79,0 / 76,4 | −2,6 | Proxy del tipo de service |
| Ítems del turno | 1 / 2 / 3+ | 78.198 / 27.701 / 3.174 | 78,0 / 80,6 / 78,2 | +2,6 | Sin señal |
| Incluye diagnóstico | sí / no | 4.397 / 104.676 | 72,8 / 78,9 | −6,1 | La única señal negativa del bloque; sobrevive dentro de generación (P375 69,2 vs 75,6; P703 83,9 vs 86,9) y ajustada (OR 0,82) |
| Incluye reparación | sí / no | 823 / 108.250 | 79,6 / 78,7 | +0,9 | Sin señal |
| Incluye campaña/recall | sí / no | 21.226 / 87.847 | 82,0 / 77,9 | +4,1 | Débil positivo |
| DealerStateOrZone | 1 / 2 / 3 / 4 / 5 | 10.499 / 22.759 / 22.139 / 30.484 / 23.192 | 73,7 / 79,8 / 79,2 / 80,0 / 77,7 | −6,3 (zona 1) | Zona 1 retorna menos |
| Region | 00 / 31 / 60 | 17.315 / 1.808 / 89.950 | 79,5 / 86,2 / 78,4 | +7,8 (31) | 31 es chica |

**¿Las demoras largas reducen el retorno?** Apenas: de 79,9% con 0 días en el taller a 76,0% con 31+ (IV 0,006); la curva no es monótona (77,4 → 77,8 → 77,5 → 77,6 entre 1 y 14 días), lo que separa es "se lo llevó el mismo día" vs "quedó en el taller". La demora no es el driver de churn en estos datos. Una lectura posible: `DaysInDealer` mide cierre administrativo de la OS más que tiempo real del cliente sin auto (hay 78 valores negativos y 1.565 turnos base con 31+ días para un mantenimiento programado).

**Semántica empírica de dos flags ambiguos** (toda la agenda):

| Flag | n | Mediana días desde turno previo | % turno previo concluido | % incluye mant. / diag. / reparación |
|---|---|---|---|---|
| ScheduleReturn = Y | 35.172 | 15 (p90 27) | 74,8 | 14,1 / 37,4 / 30,4 |
| ScheduleReturn = N | 345.471 | 93 (p90 274) | 49,5 | 66,3 / 20,7 / 7,8 |

`ScheduleReturn=Y` es un **retorno al taller a las ~2 semanas** de una visita concluida, mayormente por diagnóstico o reparación: un "comeback". Es una señal de experiencia (algo no quedó bien) mucho más interpretable que la encuesta.

| Grupo | n | % con turno siguiente ≤30 días | Mediana días al siguiente | % turno previo cancelado |
|---|---|---|---|---|
| (70) Cancelado con IsReschedule=Y | 68.783 | 71,9 | 6 | 21,3 |
| (70) Cancelado con IsReschedule=N | 32.439 | 44,5 | 21 | 21,7 |
| (60) Concluido con IsReschedule=Y | 45.665 | 49,7 | 14 | 67,0 |
| (60) Concluido con IsReschedule nulo | 297.026 | 15,1 | 99 | 9,2 |

**Implicancia:** de los 101.222 turnos cancelados, 68.783 (68%) son reprogramaciones (el cliente re-agenda a mediana 6 días). Como el turno de reemplazo puede tener fecha *anterior* a la del cancelado, la medida completa es "otro turno del mismo vehículo a ≤30 días en cualquier dirección": 99,0% en `IsReschedule=Y` (y 0% sin ningún otro turno) vs 69,7% en `IsReschedule=N` (5,8% sin ningún otro turno) *[agregado en verificación]*. Es decir, ni siquiera la "cancelación real" es abandono en la mayoría de los casos. Contar "cancelaciones" sin separar `IsReschedule` sobreestima el abandono ×3. Recomiendo que el dataset analítico lleve `cancel_true` y `cancel_resched` como dos features distintas.

## 8. (f) Historia de comportamiento previa al turno base

El historial arranca el 2024-01-01 (truncamiento a izquierda). Las tablas usan la sub-base con turno base en ene–may 2025 (≥12 meses de lookback): **n=35.248, retorno 78,1%**. Figura `_historia_retorno.png`.

| Feature (conteo previo al turno base) | 0 | 1 | 2+ | Lectura |
|---|---|---|---|---|
| No-shows | 78,0 (31.051) | 78,9 (3.436) | 79,1 (761) | Univariante sin señal (IV 0,000) **pero OR ajustado 0,73 / 0,63** (ver abajo) |
| Cancelaciones reales (IsReschedule=N) | 77,8 (29.652) | 79,4 (4.546) | 81,5 (1.050) | Univariante levemente positiva (IV 0,002) **pero OR ajustado 0,75 / 0,70** |
| Reprogramaciones | 76,8 (24.628) | 80,2 (6.954) | 82,5 (3.666) | Univariante positiva (IV 0,014); OR ajustado 0,81 / 0,76 |
| Diagnósticos concluidos | 77,8 (26.617) | 78,8 (6.087) | 79,4 (2.544) | Univariante sin señal (IV 0,001); OR ajustado 0,86 / 0,75 |
| Reparaciones concluidas | 77,6 (31.669) | 83,1 (3.035) | 81,1 (544) | Univariante positiva (+5,5 pp, IV 0,009); OR ajustado 0,97 / 0,78 |
| Campañas/recalls concluidos | 75,8 (27.620) | 85,3 (5.088) | 88,3 (2.540) | Univariante **positiva fuerte** (+12,5 pp, IV 0,075); OR ajustado 0,96 / 0,98: es intensidad de contacto |
| Re-visitas (ScheduleReturn=Y) | 77,4 (30.487) | 82,2 (3.428) | 83,9 (1.333) | Univariante positiva (IV 0,012); OR ajustado 0,96 / 1,00 |

**Ajuste por intensidad de contacto** *[agregado en verificación]*. Todos los conteos de arriba tienen un confusor común: para tener un no-show, un recall o una reparación previa hay que haber tenido turnos previos, y los turnos previos son el predictor más fuerte del bloque (0 → 5+: 73,5 → 84,5%). La comparación limpia es *a igual cantidad de turnos previos, ¿alguno fue un no-show?*:

| Turnos previos | Sin no-show previo | Con no-show previo | Dif. pp |
|---|---|---|---|
| 1 | 73,0 (n 6.433) | 67,0 (n 294) | −6,0 |
| 2 | 77,4 (5.364) | 72,8 (485) | −4,6 |
| 3–4 | 81,1 (6.974) | 76,4 (1.159) | −4,7 |
| 5+ | 85,0 (5.882) | 83,0 (2.259) | −2,0 |

Modelo conjunto del historial (logística sin penalización, n 35.134, sub-base 2025, controlando generación, año modelo y n° de service; ref = 0 en cada conteo, 91–180 días en recencia):

| Feature | OR (1) | OR (2+) | OR sin controlar turnos previos ni recencia |
|---|---|---|---|
| No-shows previos | 0,73 | 0,63 | 0,96 / 0,83 |
| Cancelaciones reales previas | 0,75 | 0,70 | 0,99 / 1,00 |
| Reprogramaciones previas | 0,81 | 0,76 | 1,16 / 1,22 |
| Diagnósticos previos | 0,86 | 0,75 | 1,04 / 1,05 |
| Reparaciones previas | 0,97 | 0,78 | 1,25 / 0,98 |
| Recalls previos | 0,96 | 0,98 | 1,26 / 1,43 |
| Re-visitas previas | 0,96 | 1,00 | 1,17 / 1,09 |
| Turnos previos (1 / 2 / 3–4 / 5+) | 1,00 / 1,32 / 1,72 / 2,70 | | |
| Recencia (≤30 / 31–90 / 181–365 / >365 / sin previo) | 0,91 / 1,14 / 0,75 / 0,40 / 0,53 | | |

Lectura: **cada contacto previo suma; un contacto que fue no-show, cancelación o reprogramación suma menos que uno concluido**, y el motivo del contacto (recall, reparación, re-visita) no agrega nada por sí mismo. El IV univariante de no-shows y cancelaciones es ~0 porque los dos efectos (más contacto, contacto fallido) se cancelan: es una paradoja de Simpson, no ausencia de señal.

| Feature | Bins → retorno % (n) | IV |
|---|---|---|
| Mantenimientos completados previos (desde 2024-01) | 0: 73,7 (11.493) · 1: 75,0 (10.130) · 2: 82,0 (6.392) · 3+: 86,1 (7.233) | 0,092 |
| Turnos previos de cualquier tipo | 0: 73,5 (6.398) · 1: 72,7 (6.727) · 2: 77,1 (5.849) · 3–4: 80,5 (8.133) · 5+: 84,5 (8.141) | 0,071 |
| Usó canal digital alguna vez antes | 0: 76,2 (25.396) · 1+: 83,0 (9.852) | 0,034 |
| Días desde el turno previo (cualquier tipo) | ≤30: 80,5 (5.713) · 31–90: 85,9 (5.526) · 91–180: 82,3 (9.656) · 181–365: 71,8 (7.071) · >365: 50,6 (884) · sin previo: 73,5 (6.398) | 0,147 |
| Días desde el mantenimiento previo | ≤30: 83,2 (310) · 31–90: 88,8 (3.787) · 91–180: 84,6 (10.155) · 181–365: 74,4 (8.332) · >365: 55,5 (1.171) · sin previo: 73,7 (11.493) | 0,180 |

**Tres lecturas para el jurado:**

1. **"¿Un auto con problemas vuelve más o menos?" Univariante, más; a igual cantidad de contactos, igual.** *[corregido en verificación]* Reparaciones, recalls y re-visitas previas suben el retorno crudo (+5 a +12 pp), pero el efecto desaparece al controlar por cantidad de turnos previos (OR 0,96–1,00). Lo que sostiene la relación es el contacto con el taller, cualquiera sea el motivo; el que se aleja es el que no tuvo *ningún* motivo para pasar. Las campañas/recalls generan contacto, y eso vale, pero con estos datos no se puede afirmar que retengan más que cualquier otra visita.
2. **Los no-shows y cancelaciones previas sí anticipan churn, pero solo se ve al ajustar por intensidad.** *[corregido en verificación]* Crudo no discriminan (IV 0,000 y 0,002); a igual cantidad de turnos previos restan 2 a 6 pp, y en el modelo conjunto tienen OR 0,63–0,75. Un modelo multivariante las va a usar; un ranking univariante las descarta por error. Dos salvedades: el historial se mide hasta el último service, no hasta la apertura de la ventana (un no-show *dentro* de la ventana actual es otra feature, probablemente más fuerte, que requiere el target definitivo); y los no-shows previos son en general de ciclos anteriores (mediana 169 días antes del turno base; solo 16,6% a ≤30 días).
3. **La recencia es la señal más fuerte del tema**, con forma de U invertida: 31–90 días es el pico (85,9%), 181–365 baja a 71,8% y >365 se desploma a 50,6%. "Sin turno previo" (73,5%) mezcla dos poblaciones: si el turno base es el **1er service**, 83,1% (n 4.720, vehículo nuevo); si es 2° o posterior, **46,8%** (n 1.678, vehículo que reaparece tras >12 meses de ausencia). Separarlas es obligatorio: "no hay historia" significa cosas opuestas según la edad del vehículo. Salvedad de censura a izquierda *[agregada en verificación]*: el bin ">365" solo es alcanzable para turnos base con más de 12 meses de historia observable (88 casos en ene-25, 252 en may-25), y "sin turno previo / 2° o posterior" es en la práctica el mismo fenómeno (ausencia > lookback) truncado; en el dataset definitivo, con más historia, ambos bins se van a redistribuir. La señal es robusta a la definición de "contacto": midiendo recencia solo sobre turnos concluidos el IV sube de 0,147 a 0,191.

## 9. (g) Estacionalidad y tendencia

Figuras `_estacionalidad_volumen.png` y `_estacionalidad_tasas.png`; tabla mensual completa en el apéndice.

| Año (turnos resueltos) | n | No-show | Cancel. real | Reprogramación | Concluido |
|---|---|---|---|---|---|
| 2024 | 162.316 | 5,9 | 7,0 | 12,7 | 71,2 |
| 2025 | 193.901 | 5,7 | 6,6 | 13,6 | 70,7 |
| 2026 (hasta 25/8) | 129.942 | 5,1 | 6,3 | 16,5 | 69,3 |

*[Corregido en verificación: las tablas mensuales y anuales ahora excluyen los turnos con `ScheduleDate` posterior al CUTOFF (26–31/8/2026: 1.903 agendados, 5 en progreso y 351 cancelados). La versión anterior los incluía en agosto 2026, lo que inflaba el volumen (15.293 vs 13.034), la tasa de reprogramación (20,3% vs 18,5%) y el % FordPass (26,4% vs 25,5%) de ese mes.]*

- **Volumen:** de 13.857 turnos en ene-24 a 17.203 en jul-25 y 18.593 en mar-26 (+34%). Mantenimientos completados por mes: 6.396 (ene-24) → 8.925 (ene-26). Consistente con el crecimiento del parque P703. Meses flojos: junio (11.042 en 2024, 15.062 en 2025) y febrero.
- **No-show** cae de 6,9% (ene-24) a 4,7% (ago-26). **Reprogramaciones** suben de 10,7% a 17,3% (jul-26) y 18,5% (ago-26, parcial). Cancelación real entre 5,7% y 8,0% mensual, con leve baja (anual: 7,0 → 6,6 → 6,3). La tasa de "concluido" baja 2 pp en tres años sobre todo por el aumento de reprogramaciones, no por abandono.
- **Nada raro en 2026 en volumen**, pero tres efectos de borde: (i) agosto 2026 es parcial (hasta el 25) y tiene 1.040 turnos "(40) En progreso" y 337 "(30) Agendado" ya vencidos, que no son churn sino turnos sin cerrar; (ii) 1.903 turnos agendados para el resto de agosto y 1.386 para septiembre son reservas futuras; (iii) cualquier etiqueta con horizonte que termine después de ~mayo 2026 está censurada.
- **Cambio operativo detectado:** el % de turnos concluidos **sin `EffectiveCheckinDate`** cae de 29,4% (ene-24) a 20,4% (oct-24), 13,1% (nov-24) y 10,7% (dic-24); en 2025 oscila entre 6,5% y 11,8% y en 2026 entre 5,7% y 9,2%. Algo cambió en la carga del check-in a fines de 2024. Como `event_date` usa check-in si existe y `ScheduleDate` si no, el impacto es mínimo (mediana 0 días de diferencia), pero cualquier feature derivada del check-in (por ejemplo, demora entre turno y llegada) tiene un sesgo por período.
- Retorno de la etiqueta por mes calendario del turno base: 77,9%–80,2%, sin estacionalidad.

## 10. Tabla de features candidatas y ranking

**Métrica:** Information Value, IV = Σᵢ (p_retᵢ − p_churnᵢ)·ln(p_retᵢ / p_churnᵢ), donde p_retᵢ es la fracción de los que retornan que cae en el bin i y p_churnᵢ la de los que no. Convención usual: <0,02 nulo, 0,02–0,1 débil, 0,1–0,3 medio, >0,3 fuerte. Depende del binning y se infla con muchas categorías. "dif pp" = tasa máxima − mínima entre bins con n ≥300. Historial sobre la sub-base 2025 (n 35.248); el resto sobre la base completa (n 109.073). Figura `_iv_ranking.png`.

| # | Feature | IV | dif pp | Riesgo / comentario |
|---|---|---|---|---|
| — | `ConnectedStatusARG` | 0,314 | 60,2 | **Leakage** (snapshot post-hoc). Excluir |
| — | Año modelo (control) | 0,294 | 45,3 | No es de este tema |
| 1 | Días desde el mantenimiento previo | 0,180 | 33,3 | Legítima; se solapa con ritmo de uso (tema km) |
| 2 | Días desde el turno previo (cualquier tipo) | 0,147 | 35,3 | Legítima; separar "1er service" de "reaparece" |
| — | Generación (control) | 0,114 | 11,5 | No es de este tema |
| 3 | N° de mantenimientos previos | 0,092 | 12,4 | Legítima; truncada a 2024-01 |
| 4 | N° de recalls/campañas previas | 0,075 | 12,5 | Legítima, pero el IV es intensidad de contacto: OR ajustado por turnos previos 0,96 |
| 5 | N° de turnos previos (cualquier tipo) | 0,071 | 11,8 | Legítima; el driver detrás de 3, 4 y 9; OR 2,7 (5+ vs 0) en el modelo conjunto |
| 6 | Dealer (target encoding fuera de tiempo) | 0,060 | 10,5 | Legítima, estable, accionable. `dealer_id` crudo da 0,08 pero está inflado (90 categorías) |
| 7 | Usó canal digital alguna vez | 0,034 | 6,8 | Legítima; parte es mix P703 |
| 8 | ScheduleSource del último turno | 0,028 | 8,0 | Legítima; OR ajustado FordPass 1,29 |
| 9 | Reprogramaciones previas / re-visitas previas | 0,014 / 0,012 | 5,7 / 6,5 | Legítimas, débiles |
| 10 | DealerStateOrZone / incluye recall / precio fijo | 0,011 / 0,010 / 0,009 | 6,3 / 4,1 / 3,6 | Legítimas, débiles |
| × | Rating de encuesta | 0,007 | 4,8 | Sin señal; semántica dudosa |
| × | DaysInDealer / WorkDaysInDealer | 0,006 | 3,9 | Sin señal práctica |
| × | Incluye diagnóstico | 0,005 | 6,1 | Única negativa del bloque turno; débil |
| 11 | Cancelaciones reales previas | 0,002 | 3,7 | **IV univariante engañoso**: OR ajustado 0,75 / 0,70 a igual n de turnos previos. Llevar al modelo *[corregido]* |
| 12 | No-shows previos | 0,000 | 1,1 | **IV univariante engañoso**: OR ajustado 0,73 / 0,63. Llevar al modelo *[corregido]* |
| × | PUD, móvil, cliente esperó, remolque, garantía, ítems, duración | ≤0,004 | ≤4 | Sin señal o n chico |

Las filas 1–8, 11 y 12 son las que recomiendo llevar al pipeline de features desde este tema. Todas son computables a la fecha de scoring con datos anteriores a esa fecha. El ranking por IV univariante es orientativo: en el bloque de historial las features están fuertemente correlacionadas entre sí a través de la cantidad de turnos previos, y el signo de varias (no-shows, cancelaciones, reprogramaciones) se invierte al ajustar.

## 11. Implicancias para target, ventana y features

- **Target/ventana:** la etiqueta a 15 meses fijos confunde "cumple el ciclo" con "usa mucho el auto". La ventana definitiva por km/tiempo (otro tema) debería normalizarlo; cuando esté, conviene re-correr este script cambiando solo la construcción de `base`/`ret` (está aislada en la sección 1) para ver cuánto cambian los IV de recencia e intensidad.
- **Momento de cálculo del historial:** acá se mide hasta el último service. En producción se mide hasta la apertura de la ventana, con lo que aparecen features nuevas que este EDA no puede evaluar: turno agendado y no cumplido *dentro* de la ventana, reprogramaciones del turno de la ventana, contacto digital reciente. Son probablemente las más fuertes para el horizonte corto (~1 mes) que quiere el tutor.
- **Features a construir (todas exclusivas a la fecha de scoring):** `dias_desde_ultimo_mant`, `dias_desde_ultimo_turno`, `n_mant_previos`, `n_turnos_previos`, `n_recalls_previos`, `n_reparaciones_previas`, `n_revisitas_previas` (ScheduleReturn=Y), `n_reprogramaciones_previas` y `n_cancelaciones_reales_previas` (separadas por IsReschedule), `n_no_shows_previos` (univariante no discrimina, pero a igual n de turnos previos tiene OR 0,63–0,73: entra junto con `n_turnos_previos`, nunca sola), `tasa_no_show_previa` (= no-shows / turnos previos: 79,1% de retorno con 0% vs 68,1% con >50%), `fuente_ultimo_turno`, `alguna_vez_digital`, `dealer_te` (target encoding regularizado calculado solo con datos anteriores al período de scoring), `zona_dealer`, `primer_service` (bandera para interpretar "sin historia").
- **Features a excluir o cuarentenar:** `ConnectedStatusARG` (leakage), `SurveyStarRating`/`SurveyResponseDate` (sin señal y semántica dudosa), `NeededTowing`, `CustomerWaiting`, `LoanerVehicle` (constante), `ServicePriceDiscount` (valores dudosos, no analizados acá).
- **Segmentación "3 tipos de cliente" (pedido del tutor):** con estos datos se sostiene una partición por relación con la red: (i) *nuevo / 1er service* (sin historia, retorno alto); (ii) *activo* (turno en los últimos 180 días: 80–86%); (iii) *distanciado* (>180 días sin contacto o reaparece tras >12 meses: 47–72%). Es interpretable, accionable y consistente con la curva del tercer año del tutor.
- **Accionabilidad:** el dealer es la palanca más concreta que sale de este tema: los dealers del quintil inferior retornan 73,3% vs 83,8% en el superior con la misma mezcla de vehículos, y el 90,7% de los clientes que vuelven lo hacen al mismo dealer. Un ranking de riesgo por cliente que se entregue **por dealer**, junto con el retorno del propio dealer vs su esperado por mix, es un entregable directo.

## 12. Problemas de calidad de datos

1. **884 turnos de mantenimiento completado sin `vehicle_id`** (0,8% del período), casi todos sin `ModelYear` ni generación válida. Excluirlos del dataset analítico y documentarlo; el merge por NaN los mezcla entre sí.
2. **`IsReschedule` cambia el sentido de "cancelado":** 68.783 de 101.222 cancelaciones son reprogramaciones (71,9% re-agendadas en ≤30 días). Nulo en el 88,6% de los turnos Dealer de la base (mantenimientos concluidos): la ausencia no significa "no reprogramado" sino "no informado".
3. **`ScheduleReturn` nulo solo en turnos digitales y solo en 2024** (27,9% de los turnos FordPass de la base; 10,8% de la base 2024 vs 0% de la base 2025): la variable se empezó a poblar para canales digitales durante 2024.
4. **`NeededTowing` nulo en 63–69% de los turnos digitales y 0% en Dealer**: los "sin dato" replican el canal.
5. **`SurveyResponseDate` siempre anterior al turno y solo en canales digitales**: no es una encuesta del service. Semántica a confirmar.
6. **`ConnectedStatusARG` es snapshot** y su categoría "Sin Información" marca vehículos que dejan de aparecer (41,4% con algún turno posterior vs 90–96%). Dos datos más que apoyan la lectura de "asignado a posteriori" *[agregados en verificación]*: su participación entre los turnos base cae de 5,1% (1T 2024) a 0,6% (2T 2025), como corresponde a un estado que se adquiere después de dejar de venir (los turnos más viejos tuvieron más tiempo para "irse"); y el último evento de esos vehículos se concentra en 2024 (77% vs 3,5% en "Conectado"). En cambio, solo el 10,9% tiene más de un `customer_id` en la agenda (vs 29–37% en el resto): no parece transferencia de titularidad visible en la red, sino salida del padrón. "No tiene Conectividad" en P375 (3.968 turnos base, 38,9% de retorno) y "Conectado" en P375 (542, 54,4%) son categorías anómalas para esa generación con el mismo comportamiento de desaparición parcial (76,4% con turno posterior).
7. **`DaysInDealer`:** 78 valores negativos en la base y cola larga (1.565 turnos base con 31+ días).
8. **Check-in nulo entre concluidos cae de 29,4% (ene-24) a 10,7% (dic-24)** y queda entre 5,7% y 11,8% después: cambio de proceso; sesgo por período en cualquier feature de check-in. En todo el período, el 11,8% de los mantenimientos completados no tiene check-in.
9. **No-show por dealer con p10 = 0,4%**: algunos dealers no registran no-shows; la tasa por dealer mezcla comportamiento del cliente con práctica administrativa.
10. **Agosto 2026 parcial** (hasta el 25) con 1.040 turnos "En progreso" y 337 "Agendado" ya vencidos; reservas futuras hasta diciembre 2026 (1.903 + 1.386 + 32 agendados, más 498 ya cancelados con fecha futura). Censura para cualquier ventana que cierre después de ~mayo 2026. Cualquier tabla mensual por `ScheduleDate` tiene que filtrar `<= CUTOFF`, si no agosto 2026 queda inflado con reservas.
11. **Master data del vehículo:** 290 turnos base con grupo "RANGER"/"RANGER RAPTOR" sin año modelo (retorno 54,1%): probablemente registros con VIN mal decodificado.

## 13. Preguntas para el mentor

1. ¿Qué mide exactamente `SurveyStarRating`? Se responde siempre *antes* del turno (mediana 8 días) y solo en turnos FordPass/WEB/Mobile. ¿Es la encuesta de la app de agendado? ¿Existe la encuesta CSI post-service y se puede incorporar?
2. ¿Cómo se calcula `ConnectedStatusARG` y a qué fecha? ¿"Sin Información de Conectividad" corresponde a vehículos dados de baja del padrón o transferidos? ¿Se puede reconstruir el valor a una fecha histórica (as-of)?
3. ¿`IsReschedule=Y` en un turno cancelado significa que ese turno fue reemplazado por otro (el nuevo `schedule_id`)? ¿Hay un vínculo explícito entre el turno cancelado y el reprogramado?
4. ¿`ScheduleReturn=Y` es lo que Ford llama "retorno al taller" (comeback)? ¿Se usa como KPI de calidad del dealer?
5. ¿Qué pasó con la carga del check-in a fines de 2024 (de 29% de concluidos sin check-in a <10%)? ¿Hubo cambio de sistema o de instructivo?
6. ¿La red registra los no-shows de forma homogénea? Hay dealers con 0,4% y otros con 12,8%.
7. Para el target definitivo: ¿un turno agendado pero no cumplido *dentro* de la ventana se considera churn, o la ventana sigue abierta hasta el horizonte? (Define si "no-show en ventana" es feature o parte del target.)
8. ¿Los dealers con caídas fuertes de retorno entre 2024 y 2025 (por ejemplo −28 pp con menos volumen) tuvieron cambios conocidos (cierre, cambio de dueño, obras)? Serviría para validar que el efecto dealer es real.
9. ¿Los `dealer_id` de agenda y de ventas son el mismo catálogo? (95 en agenda, 107 en ventas.) ¿Se puede saber la zona/provincia del dealer para cruzar con `State` de ventas?
10. Los vehículos "Sin Información de Conectividad" casi no cambian de `customer_id` en la agenda (10,9% vs 29–37%): ¿ese estado se asigna cuando el vehículo sale del padrón de Ford Argentina (baja, exportación, siniestro) más que cuando cambia de dueño? ¿Existe la fecha en que se asignó?

## Anexo — Figuras generadas

| Archivo | Contenido |
|---|---|
| `06_canal_dealer_experiencia_fuente_mix_mensual.png` | Mix de fuente de agendado por mes, 2024-01 → 2026-08 |
| `06_canal_dealer_experiencia_fuente_retorno_estratos.png` | Retorno por fuente dentro de generación × año modelo |
| `06_canal_dealer_experiencia_conectividad_retorno.png` | Retorno por conectividad dentro de cada generación |
| `06_canal_dealer_experiencia_encuesta_retorno.png` | Timing de la encuesta y retorno por rating |
| `06_canal_dealer_experiencia_dealer_dispersion.png` | Dispersión de tasas por dealer (p10/p50/p90) |
| `06_canal_dealer_experiencia_dealer_lorenz.png` | Curva de concentración del volumen por dealer |
| `06_canal_dealer_experiencia_dealer_estabilidad.png` | Retorno por dealer 2024 vs 2025 (tamaño = n) |
| `06_canal_dealer_experiencia_conveniencia_retorno.png` | Retorno por atributos del turno base |
| `06_canal_dealer_experiencia_historia_retorno.png` | Retorno por historial previo (sub-base 2025) |
| `06_canal_dealer_experiencia_estacionalidad_volumen.png` | Turnos por mes y status |
| `06_canal_dealer_experiencia_estacionalidad_tasas.png` | No-show, cancelación real, reprogramación y sin OS por mes |
| `06_canal_dealer_experiencia_iv_ranking.png` | Ranking de features por IV |

Reproducir: `PYTHONIOENCODING=utf8 PYTHONPATH=src .venv/Scripts/python.exe scripts/eda/06_canal_dealer_experiencia.py` desde la carpeta del proyecto.
