# EDA 03 — Verificación escéptica: retención por edad del vehículo y tasa base de churn

Objeto: `reports/eda/03_retencion_churn.md` y `scripts/eda/03_retencion_churn.py`.
Método: recálculo independiente con `scripts/eda/03_retencion_churn_verificacion.py` (asignación del año de vida por
evento en lugar de por intervalo, `groupby().shift()` en lugar de `merge_asof`, poblaciones y ponderaciones
alternativas). Tablas: `reports/eda/tables/03_retencion_churn_verificacion_*.csv`. Los ajustes ya están aplicados en el
informe original, marcados con **[verif.]**.

## Resumen

- **Ningún número del informe está mal calculado.** Los 10 bloques de afirmaciones se reproducen al decimal con código
  independiente (221.368 eventos, 73.219 índices, 72,4 % / 75,8 % / 78,7 %, 2.443/mes, 30.205 churners, etc.). El
  pipeline `merge_asof` del script original coincide exactamente con el `shift` por vehículo.
- **Cinco afirmaciones estaban bien calculadas pero mal interpretadas o sin una salvedad decisiva:** la comparación
  intra-P375 de la caída 2→3 (no robusta), la tasa base "27,6 %" (es por evento; por vehículo es 32,9 %), la cadencia
  "5-6 meses" (mediana por par de eventos, dominada por alto kilometraje; por vehículo 206 días / 22.000 km/año), el
  "número de service discrimina poco" (a igual edad discrimina muchísimo) y el "churn temporario es cambio de dueño"
  (es efecto de tiempo en riesgo).
- **Dos errores puntuales de texto:** las etiquetas de los semestres alrededor de los 36 meses (el −4,4 pp es 24→30, no
  30→36) y el sesgo de selección "+7,8 / +4,4 pp", que compara poblaciones con distinto año de garantía (dentro de la
  misma cohorte es +6,5 / +6,6 pp).
- **Una afirmación refutada:** `ServiceMaintenance = 20` no es "un código ajeno a la secuencia": es el tramo con más KM
  (246.100 mediana) y más edad (81 meses); se comporta como tope "20° o más". Los códigos 11-19 son services reales
  (KM y edad crecen monótonamente) aunque el `ServiceName` diga "1°", "2°"…
- El script original no tiene bugs de cómputo; no se modificó. Todas las correcciones fueron al `.md`.

## Tabla de veredictos

| # | Afirmación | Veredicto | Número original | Número recalculado | Nota |
|---|---|---|---|---|---|
| 1 | La retención cae con la edad de forma sostenida: pico en el 2° año, descenso hasta el 12° | **Confirmada** (con salvedad) | Cohorte 2024: 63,9 % (k=1) / 73,2 % (k=2); conocidos: 78,3 / 66,0 / 60,1 / 52,7 / 38,3 / 26,8 / 13,4 % | Idénticos con asignación por evento. Estimador alternativo con ventana previa homogénea de 12 m (`1_curva_edad`): 79,6 / 66,8 / 59,7 / 54,0 / 40,0 / 29,5 / 13,8 % | La forma de la curva es robusta al estimador. Salvedad agregada: parte del "pico en k=2" es el corte a 12 meses, porque el 1er service se concentra en los meses 12-13 (+10,6 / +7,7 pp); con un 1er año de 13 meses la tasa de k=1 sería 72,0 %. |
| 2 | "Al tercer año cae fuerte" se confirma a medias: primera caída 2→3, la mayor 5→6, sin quiebre a 36 m | **Ajustada** | 2→3: −12,4 pp; P375 −9,9; P703 −5,7. 5→6: −14,4 pp. Semestral: "−4,4 pp en 30→36, −3,8 en 36→42" | 2→3: −12,4 (conocidos) / −12,8 (ventana homogénea). 5→6: −14,4 / −14,0. P703: −5,7 / −4,2. P375: −9,9 (conocidos, ventana previa heterogénea) / −16,6 (homogénea, n=363). Semestral: 24→30 −4,4; 30→36 −3,8; 36→42 −3,8 | Las etiquetas semestrales estaban corridas un semestre (corregido). La cifra intra-P375 no es robusta: el estimador "conocidos" tiene ventana previa de 0-20 meses según el mes de garantía y las ventanas cortas seleccionan a los recién vistos (en k=3, P375: 74,5-76,0 % con 0-8 m de ventana vs 61,6-65,8 % con 9+; `1_conocidos_por_preventana`, `2_k3_P375_por_trimestre_wsd`). Conclusión de fondo (cae en el 3°, se desploma en el 5°-6°, no hay escalón a 36 m) confirmada. KM por edad: 74.798 / 98.118 / 105.366 y 32 / 48 / 55 % confirmados; son medianas por evento (sesgo hacia alto uso), se dejó la salvedad general en 2.4. |
| 3 | Tasa base tras un mantenimiento: churn 27,6 % (12 m), 24,2 % (13), 21,3 % (15); 20,4 % con cualquier visita | **Ajustada** | 73.219 índices / 48.372 vehículos; retorno 72,4 / 75,8 / 78,7 %; visita 79,6 %; excl. <30 d 71,6 / 77,8 % | Idénticos (`3_tasa_base`). **Por vehículo** (1er evento de cada uno, n=48.372): retorno 67,1 / 71,7 / 75,5 % → churn 32,9 / 28,3 / 24,5 %; visita 75,6 %. Incluir `(90) Concluido sin OS` con mantenimiento: 73,0 % (+0,6 pp) | La prevalencia depende de la unidad: 31.248 vehículos tienen 1 evento en el período, 11.799 dos, 5.325 tres o más; los de alta frecuencia pesan más por evento. Agregado al informe (sección 3 y tabla de la sección 7). Tendencia calendario agregada: retorno a 6 m cae de 46,8 % (índices jul-2024) a 40,1 % (may-2025); a 12 m 73,9 → 72,1 %. |
| 4 | Churn a 12 m por edad: 18,7 % (1er año) → 40,7 % (5°) → 64,1 % (10+); el número de service discrimina mucho menos | **Ajustada** | Por edad: 81,3 / 75,4 / 75,3 / 70,8 / 59,3 / 55,1 / 48,9 / 35,9 %. Por n° service: 64,1-75,9 % a 12 m; 27,4 % vs 54,7 % a 6 m | Por edad: idéntico (`4_por_edad`). **Edad × n° service** (`4_edad_x_maint_number_ret12m`, n≥200): 2° año de vida: 45,9 % (1er service) vs 83,0 % (3°); 3er año: 41,5 % (2°) vs 83,4 % (6°-10°); 4° año: 39,3 % vs 75,9 %; 5° año: 37,4 % vs 71,1 % | La afirmación marginal es cierta, pero engañosa: edad y n° de service se compensan. A igual edad, el n° de service separa ~40 % de ~80 %: services/años de vida es un feature de primer orden. Agregado a hallazgo 3.2 e implicancias. |
| 5 | Primer service cohorte 2024: 35,6 % no lo completa en 12 m, 28,0 % en 13, 19,1 % en 18; el aniversario lo dispara | **Confirmada** | n=22.679; 20,6 / 42,0 / 64,4 / 72,0 / 77,2 / 80,9 %; turno 87,8 %; 9,3 % nunca; +10,6 pp mes 12, +7,6 mes 13; mediana 8 m (p25 5, p75 11) | Idénticos (`5_primer_service_horizonte`): mediana 8 (p10 4, p25 5, p75 11, p90 13); incrementos 5,9 / 5,9 / **10,6** / **7,7** / 3,1 pp en meses 10-14. En días: tramos 330-360 y 360-390 concentran 8,7 % y 9,6 % de la cohorte vs 5,8-7,6 % por tramo entre 120 y 330 días (`5_dias_al_primer_service_bins30`) | Único ajuste: +7,6 → +7,7 (redondeo: 72,04 − 64,38). El pico del aniversario es real y se ve también en días, no solo en el corte mensual. La mediana de 8 meses la imprime el script pero no está en ninguna tabla; ahora está en `5_*`. |
| 6 | Medir solo con vehículos de la agenda sobreestima +7,8 pp (k=1) y +4,4 pp (k=2) | **Ajustada** | Agenda 71,7 % vs cohorte 63,9 % (k=1); 77,6 vs 73,2 % (k=2); cohorte con ≥1 turno 70,4 / 79,8 % | Misma cohorte 2024, completa vs con ≥1 turno: **+6,5 pp** (63,9 → 70,4 %, n=23.021 / 20.885) y **+6,6 pp** (73,2 → 79,8 %, n=13.263 / 12.169). La columna "agenda" k=1 mezcla garantía 2024 (70,0 %, n=20.636) y 2025 (74,1 %, n=15.037); la de k=2 incluye garantía 2023 (76,4 %) (`6_sesgo_seleccion`) | Los números originales existen en la tabla, pero comparan poblaciones con distinto año de garantía: +7,8 sobreestima y +4,4 subestima el sesgo de selección puro. Corregido el hallazgo 1.3. Cotas superiores para k≥3: confirmado como razonamiento. |
| 7 | Cadencia real ~5-6 meses, no 12: manda la regla de 15.000 km; 29,7 % de los ciclos llega a 12 m sin service | **Ajustada** | Gap mediana 161 d (p10 72, p25 106, p75 245, p90 352; n=133.837); km/año 34.080 (p25 20.519, p75 58.232); 50.193 / 169.210 = 29,7 % (35,9 % / 27,7 % por origen) | Idénticos por evento (`7_cadencia`). **Por vehículo**: gap mediano 206 d (p25 140, p75 306; n=55.776); km/año 21.909 (p25 14.549, p75 32.504; n=84.795). Tiempo mediano hasta el próximo mantenimiento sin truncar: 7 meses por evento, 9 por vehículo (`7_retorno_acumulado_evento_vs_vehiculo`). Los vehículos con ≥3 intervalos aportan el 62 % de los pares. 29,7 % confirmado | El gap por par de eventos es una muestra sesgada por longitud (un vehículo con 6 services aporta 5 gaps; uno con 1 aporta 0). "Manda el km" vale para la mitad de alto uso; para el resto opera el año. Reescritos el punto 5 del resumen, el hallazgo 2.4 y la implicancia de ventana. |
| 8 | ~2.443 vehículos/mes llegan a 12 m sin mantenimiento (≈26/concesionario); 15,1 % vuelve en 1 mes, 26,5 % en 3 | **Confirmada** (con salvedad) | 8.323 ciclos/mes; en ventana 1.893-3.219, promedio 2.443; ≤1 m 15,1 %; ≤3 m 26,5 % (22,4-31,4); origen garantía 24,1 / 38,2 %, tras mantenimiento 12,4 / 22,1 % | Idénticos (`8_poblacion_mensual`): 2.442,6/mes; ≤1 m 15,1 %; ≤3 m 26,5 %. Los 8.323 ciclos/mes son 8.290 vehículos distintos; 38.176 vehículos distintos estuvieron en ventana en los 16 meses (39.081 ciclos). Fuera del dimensionamiento: 17.973 vehículos de la agenda con garantía < 2024 y ningún mantenimiento en 2024-2026 (de 66.795) | La frase "si la ventana se definiera al vencimiento… la lista sería de ~8.300" era confusa (al vencer ya se sabe quién volvió); reescrita como flujo mensual y población si se abre antes. Cuantificada la población invisible. |
| 9 | 1 de cada 4 churners a 15 m reaparece en el año siguiente; retorno acumulado se estanca en 83,2 % a 24 m; retorno tardío viene en gran parte con cambio de dueño | **Ajustada** | 140.386 ciclos; churn 15 m 30.205 (21,5 %); reaparición 13,4 / 19,3 / 23,9 / 25,9 / 26,7 %; acumulado 71,3 / 78,3 / 80,7 / 83,2 %; 30,5 % visita no-mant.; 1,1 % turno futuro; cambio de cliente 27,5 % vs 13,2 % | Idénticos con `shift` (`9_reaparicion`; acumulado 24 m 0,713 / 0,783 / 0,807 / 0,832 con n=59.730). **Cambio de `customer_id` por meses hasta el próximo mantenimiento** (`9_cambio_cliente_por_tramo`): 0-2 m 11,1 %; 3-5 11,2 %; 6-8 13,8 %; 9-11 17,6 %; 12-14 19,4 %; 15-17 25,4 %; 18-20 29,5 %; 21+ 31,2 % | Reaparición y acumulado confirmados. La parte "en gran parte cambio de dueño" está refutada como interpretación: la tasa de cambio crece de forma continua con el tiempo transcurrido, también entre no churners (19 % a los 12-14 meses), y 3 de cada 4 retornos tardíos son del mismo `customer_id`. Hallazgo 6.3 y pregunta 8 reescritos. |
| 10 | Ford Pro, DIRECT SALES/CONSORTIUM y sobre todo HR / PersonType 25-29-30 retienen menos; F vs J no discrimina | **Confirmada** (con precisión) | F 64,9 / 72,6 %; J 64,3 / 75,2 %; Blue 65,9 / 76,9 %; Pro 59,8 / 64,1 %; ROR 66,8 / 75,8; CONSORTIUM 60,2 / 68,8; DIRECT 59,7 / 67,4; HR 18,9 / 55,6 (n=455); otro 18,2 / 55,0 (n=374); 1er service 18 m: Pro 75,4 % vs Blue 83,5 %; HR 38,2 % | Idénticos. HR × PersonType: 371 de los 455 HR son PersonType 25/29/30 y 371 de los 374 "otro" son HR (`10_hr_x_persontype`): son el mismo grupo. BU × canal k=1 (`10_bu_x_canal_k1`): Blue ROR 68,0 / CONS 62,5 / DIRECT 60,8; Pro ROR 62,5 / CONS 56,3 / DIRECT 59,5. DIRECT SALES es 83 % Ford Pro. PersonType × BU sin HR: Blue F 66,3 / J 68,0; Pro 60,4 / 60,4 | Todo confirmado; se precisó que el déficit de DIRECT SALES es el de Ford Pro (dentro de Pro, DIRECT ≈ ROR), que CONSORTIUM sí tiene un efecto propio (~−5,5 pp en ambas BU) y que F vs J tampoco discrimina dentro de cada BU. |

## Otros números del informe revisados

| Número | Estado |
|---|---|
| 221.703 turnos → 221.368 eventos (colapso vehículo-día) | Confirmado. 222.889 mantenimientos completados − 1.186 sin `vehicle_id` − 0 fuera de ventana = 221.703. |
| 3.502 turnos completados con `ServiceMaintenance = 20` | Correcto, pero el script no lo imprime (calculado aparte a nivel turno: 3.502; 3.501 con `vehicle_id` en ventana). |
| 82 mantenimientos anteriores a la garantía; 405 WSD distintas entre agenda y ventas; 1.252 / 4 / 120 sin WSD | Salen del stdout o de la tabla `0_universo_vehiculos` del script original; no recalculados (no afectan ninguna afirmación). Solo 1 vehículo tiene más de una WSD dentro de la agenda. |
| P(maint k \| maint k−1): 81,0 / 69,8 / 63,5 / 60,4 / 48,8 % | Confirmado por dos vías (`1_curva_edad`: columna `P(k\|maint k-1)` y estimador "mantenimiento en los 12 meses previos", idénticos). |
| Retorno acumulado a 24 m (59.730 ciclos) 71,3 / 78,3 / 80,7 / 83,2 % | Confirmado con `shift`. |
| Composición P703: 77 % de k=2, 12 % de k=3 | Confirmado (18.664 / 24.254 y 1.955 / 16.356). |

## Problemas metodológicos detectados (no son errores de cálculo)

1. **Estimador "conocidos antes del año k"**: la ventana previa observable va de 0 a 20 meses según el mes de inicio
   de garantía; las ventanas cortas condicionan a "visto hace días" y elevan la tasa (k=3: 74,5-76,0 % con 0-8 meses vs
   61,6-65,8 % con 9+). Como la mezcla de ventanas es parecida entre valores de k, la curva agregada no cambia (estimador
   homogéneo de 12 meses: mismas tasas ±1,5 pp), pero las comparaciones **dentro de un subgrupo** (P375 en k=2, model
   year dentro de k=3) sí se distorsionan. Para el modelo, el feature "meses desde el último turno" captura esto.
2. **Ponderación por evento**: tasa base, gaps, km/año y KM por edad están ponderados por evento; los usuarios de alto
   kilometraje (que vuelven cada 4-5 meses) pesan varias veces. Cuando la unidad sea el vehículo, las tasas cambian
   5 pp (churn 27,6 → 32,9 %) y la cadencia mediana pasa de 161 a 206 días.
3. **Drift calendario**: entre índices de jul-2024 y may-2025 el retorno a 6 m cae 6,7 pp (46,8 → 40,1 %) y el de 12 m
   1,8 pp. Los horizontes cortos son los más sensibles al período de entrenamiento.
4. **Tiempo en riesgo** en el cambio de `customer_id`: cualquier comparación "tardíos vs tempranos" debe controlar por
   meses transcurridos.

## Correcciones aplicadas a `03_retencion_churn.md`

1. Resumen ejecutivo 2 y hallazgo 2.2: etiquetas de la curva semestral (24→30 −4,4; 30→36 −3,8; 36→42 −3,8).
2. Resumen 2 y hallazgo 2.1: caída 2→3 intra-P375 marcada como no robusta; agregado el estimador de ventana previa
   homogénea (curva y caídas) y la evidencia de `1_conocidos_por_preventana`.
3. Resumen 3, sección 3 y tabla de la sección 7: tasa base por vehículo (32,9 % / 24,5 %), sensibilidad a `(90)` (+0,6 pp),
   distribución de eventos por vehículo y tendencia calendario.
4. Hallazgo 3.2, calidad de datos 6 y pregunta 7: n° de service discrimina fuertemente a igual edad; códigos 11-19 son
   services reales y el 20 es tope "20° o más".
5. Hallazgo 1.3: sesgo de selección +6,5 / +6,6 pp dentro de la misma cohorte; explicado por qué +7,8 / +4,4 mezclan
   años de garantía.
6. Resumen 5, hallazgo 2.4 e implicancia de ventana: cadencia por vehículo (206 días, 21.909 km/año, mediana 9 meses
   hasta el próximo service) y reformulación de "manda la regla de 15.000 km".
7. Resumen 7, hallazgo 6.3 y pregunta 8: cambio de `customer_id` como efecto de tiempo en riesgo.
8. Hallazgo 5.1: reescrita la frase sobre los ~8.300/mes; cuantificada la población invisible (17.973 vehículos).
9. Hallazgo 1.4 e implicancia BU/canal: HR ≡ PersonType 25/29/30 (371 vehículos); DIRECT SALES = efecto Ford Pro;
   CONSORTIUM con efecto propio; F vs J igual dentro de cada BU.
10. Hallazgo 1.1: salvedad sobre el corte a 12 meses y el "pico" en k=2. Hallazgo 4.2: +7,6 → +7,7 pp y evidencia en
    días. Implicancias: features "services / años de vida" y "prevalencia según unidad"; drift en validación temporal.
11. Encabezado y anexo: referencia al script y a las tablas de verificación.

No se modificó `scripts/eda/03_retencion_churn.py`: no se encontró ningún error de cómputo.
