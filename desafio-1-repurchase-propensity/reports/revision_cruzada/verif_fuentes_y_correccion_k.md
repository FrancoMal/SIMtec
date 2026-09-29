# Verificación escéptica — bloque `fuentes_y_correccion_k` (docs/04 §1.3, §2.1 y §3)

Script: `scripts/revision_cruzada/verif_fuentes_y_correccion_k.py` (salida cruda en
`reports/revision_cruzada/verif_fuentes_y_correccion_k_salida.txt`). Corrida el 15/09/2026 21:00-21:15. Todo lo de astra se
leyó en solo lectura. Fuentes externas: el PDF del manual de garantía Ranger 2016 ya descargado (texto extraído con `pypdf`) y
ocho snapshots Playwright de ford.com.ar (WebFetch devolvió HTTP 403 en todas las URL; los snapshots quedaron en
`G:\SIMtec-fable\.playwright-mcp\page-2026-09-1*.yml`).

## Tabla de veredictos

| # | Afirmación (docs/04) | Veredicto | Número original | Número recalculado | Nota |
|---|---|---|---|---|---|
| 1 | (a) Ranger nueva (P703): 16.000 km ó 12 meses, fuente ford.com.ar | **confirmada** | "revisión de 16.000 km ó 12 meses" (página Ranger 2.0L Diesel) | Snapshot 2.0L (20:46): frase literal + tabs 16/32/…/160 mil km. Además, en vivo: Ranger 3.0L V6 Diesel y Ranger Raptor 3.0 V6 nafta: misma frase y mismos tabs | El doc cita sólo la 2.0L y aplica K = 16.000 a "Raptor P703" sin fuente; ahora las dos páginas faltantes lo respaldan. Conviene agregar las URL al Anexo. |
| 2 | (a) Ranger anterior (T6/P375): 10.000 km ó 1 año, fuente manual 2016 | **confirmada** | "Programa de mantenimiento Ford 10.000 km ó 1 año" | PDF (CreationDate 2016-07-13, "FORD RANGER Garantía y Mantenimiento", motores 3.2/2.2 Duratorq y 2.5 Duratec = T6): p.18 "entre un servicio y otro no debe excederse 10.000 km ó 12 meses"; p.24/26/28 tabla "10.000 km ó 1 año, 20.000 km ó 2 años, …". Sitio actual "Ranger (Hasta 2023)" (3.2L, 2.2L, 2012-2016 3.2L) y Raptor anterior: "revisión de 10.000 km ó 12 meses", tabs 10/20/…/100 mil | Ojo al grepear el manual: en p.9 "12 meses ó 20.000 km" es la garantía del material de fricción del embrague, no el plan. Salvedad de código: la generación `RANGER` sin sufijo (474 ventanas, 267 evaluables) y 3 sin generación reciben K = 16.000 por default (`km_interval`); son Ranger pre-T6 y lo más probable es 10.000. Impacto: 0,2 % de las evaluables. |
| 3 | (b) Con K = 16.000, km/n 16.040-16.173 (P703, n = 1..7) y Δkm 16.138 son consistentes con el nominal | **confirmada** (con salvedad) | km/n 16.040-16.173; Δkm 16.138 (EDA 02 b1/b2) | Recalculado con filtros propios desde `data/interim/agenda.parquet` (turno Concluido con n° de service, un registro por vehículo-día, mismo n a ≤ 30 d descartado): km/n 16.041-16.173 (n = 1..7, 42.733 → 1.113 eventos); Δkm n→n+1 mediana 16.140 (n = 46.039). P375: 10.125-10.301; Δkm 10.332 | Diferencias ≤ 3 km con el EDA. Atraso relativo del km/n mediano: +0,3 % a +1,1 % con 16.000 vs +6,9 % a +7,8 % con 15.000; la P375 con 10.000 llega +1,3 % a +3,0 %. La consistencia es de escala: con 16.000 el P703 se atrasa como la P375; con 15.000 sería un atraso 5 veces mayor sin explicación. Los datos solos no fijan el nominal; lo zanja la fuente. |
| 4 | (b) §4.3: "el vencimiento estimado se corre ~15 días más tarde para el P703 típico" | **ajustada** | ~15 días | Mediana **10 d** (p25 7, p75 14) sobre 103.938 anclas de mantenimiento P703 reconstruidas con K = 15.000 y 16.000; 12 d cuando manda la regla de km | 1.000 km a 22.000 km/año son 16,6 días, pero el P703 mediano usa más y el tope de 365 d recorta: el corrimiento típico es de 10-12 días. |
| 5 | (c) Cambiar K a 16.000 dejó 142.558 evaluables, churn 41,6 %, test 19.704, ROC-AUC 0,739 | **confirmada** | 142.558 / 41,6 % / 19.704 / 0,739 (resumen.md) | Reconstrucción con el módulo de fable y `config/params.json`: 142.558 evaluables, churn 0,4159, censuradas 35.188, train 101.960, valid 20.894, test 19.704 (churn 0,4260) = idéntico al parquet. ROC-AUC con sklearn sobre `test_scored.parquet` (mismo conjunto de `window_id`, etiquetas iguales al parquet): **0,7391** calibrado, 0,7400 sin calibrar; PR-AUC 0,6994; recall@20 % 0,361, lift 1,81. Con K = 15.000: 145.538 / 36.397 / test 20.191 (churn 42,9 %) / train 103.842 / valid 21.505 = las cifras del PDF viejo (±1 ventana en train/valid) | El delta real del cambio de K: −2.980 evaluables, −487 ventanas de test, +2.429 preempted. El AUC 0,736 de la corrida vieja no lo re-entrené: sale de docs/02 y del PDF. "Resultado prácticamente igual" es una lectura justa. |
| 6 | (d) La página de Ford muestra descuentos por continuidad 5/10/15 % en el 2°, 3° y 4°+ service | **confirmada** | 5 % / 10 % / 15 % | Texto legal literal en las 7 páginas de modelo: «LOS PRECIOS SUGERIDOS "CON VOS" INCLUYEN LOS SIGUIENTES DESCUENTOS PROGRESIVOS, POR CONTINUIDAD EN REALIZACIÓN DE SERVICIOS, SOBRE LOS PRECIOS DE LISTAS: 2° SERVICIO 5%, 3° SERVICIO 10%, 4° SERVICIO EN ADELANTE: 15%»; «VIGENTES DESDE EL 01/09/2026 AL 30/09/2026» | Es la letra chica de precios sugeridos con vigencia mensual, "no constituyen oferta al consumidor": al citarlo conviene poner la vigencia. La atribución del §2.3 ("lo que fable no vio y astra sí: … los descuentos por continuidad") **no se sostiene**: ningún archivo de astra (md/py/json/csv/html) menciona "Con Vos", continuidad ni 5/10/15 %; astra citó la página por el intervalo, el descuento lo encontró fable al leerla. |
| 7 | (e) `informe_final.md` y `informe_final.pdf` ya no contienen "27.327" ni "enero y abril" | **confirmada** (literal) | 0 / 0 | md: 0 y 0; PDF: 0 y 0 | Literalmente cierto, pero ver #8. |
| 8 | (e) §3: "el `informe_final.md` y el PDF se regeneraron con una sola corrida" y sus cifras coinciden con `resumen.md` | **refutada** para el PDF | PDF = corrida final (K = 16.000) | `informe_final.pdf` es de las **20:38**; `ventanas.parquet` 20:50, `resumen.md` 20:54, `informe_final.md` 20:58. El PDF es de la corrida con K = 15.000: "15.000" ×7, "20.191" ×4, "145.538", "36.397", "103.841", "21.506", "42,9 %", "0,736" ×2, "ECE = 0,012", "el de menor, 14 %", "64 % de los churners" ×2, población de hoy 31.651 / 1.825 / 6.330 / 9.495 / 15.826, tabla de capacidad 1.010/2.019/4.038/6.057/10.096, ROI 267/130, 464/260, 626/390, 895/650. De 83 cifras derivadas de los artefactos de la corrida final, **60 no están en el PDF** (ninguna de 19.704, 142.558, 0,739, 0,699, 985/1.970/3.941, 261/126/455/252, 30.499, 1.791, 6.099/9.150/15.250) | El PDF es de una sola corrida, pero la anterior. Hay que regenerarlo (`scripts/build_pdf.py`) después de corregir el md (#9). |
| 9 | (e) Las cifras de `informe_final.md` coinciden con `resumen.md` | **ajustada** | — | 69 de 83 cifras coinciden (métricas §6.1, capacidad §6.2, deciles, segmentos, ROI §9, población §4 y de hoy §8, split §5). Desactualizadas: **§6.4 tabla de ablaciones** entera (md: base 0,736/0,696/0,012; sin concesionario 0,734/0,695/0,014; sólo agenda 0,734/0,698/0,013; ≥ 6 meses 0,734/0,700/0,013; sin encuestas 0,733/0,696/0,013; Connected 0,725/0,687/0,027; KM 0,814/0,804/0,060; siguientes 0,717/0,635/0,012 con n = 16.629 → `ablaciones.md` actual: 0,739/0,699/0,017; 0,737/0,698/0,013; 0,739/0,699/0,013; 0,738/0,703/0,011; 0,736/0,699/0,013; 0,729/0,686/0,028; 0,812/0,803/0,057; 0,721/0,635/0,013 con n = 16.142; "sólo primer service" 0,802/0,830/0,029, n = 3.562 no cambia). **§11 pregunta 1**: "¿Confirman el plan de 15.000 km / 1 año (P703)…?" (debe decir 16.000). **§1**: "unos 5.000 a 6.000 vehículos por mes" vs `volumen_mensual_ventanas.csv` 2026 ene-jul 6.344-7.532 (2025: 5.255-7.500); §9 dice "6.000 a 7.000". **§4**: "con 16.000 la P375 vence un mes tarde (más de la mitad ya volvió al abrir)": recalculado con K = 16.000 para todos, la P375 tiene 51,6 % de anclas preempted (✓ "más de la mitad") pero la mediana del retorno es **−63 d** respecto del vencimiento (≈ dos meses, no uno; el "un mes / 33 d" era el dato viejo con 15.000). **§8** Bajo "27 %": exacto 26,48 % (redondeo). Inconsistencia interna: §6.1 dice 0,739 y §6.4 "Modelo base 0,736" | La tabla de ablaciones y la pregunta 1 son las dos que el jurado puede notar; el resto es fino. |

## Detalle de la evidencia

### A. Manual de garantía Ranger 2016 (PDF)
65 páginas, creado 2016-07-13 con Acrobat, título de tapa "FORD RANGER Garantía y Mantenimiento", Ford Argentina S.C.A.
Piezas de mantenimiento para motores Diesel 3.2L y 2.2L Duratorq TDCi y Nafta 2.5L Duratec: es la Ranger T6 (P375).
"10.000 km ó 12 meses" en p.18 (avisos del programa), "10.000 km ó 1 año … 200.000 km ó 20 años" en las tablas de p.24, 26 y 28.
No aparece "16.000" ni "15.000" en todo el manual.

### B. ford.com.ar (Playwright, 15/09/2026 20:46 y 21:05-21:10)
| Página | Intervalo | Tabs | Descuentos "Con Vos" |
|---|---|---|---|
| nueva-ranger/ranger-2-0-l-diesel (snapshot del doc) | revisión de 16.000 km ó 12 meses | 16 → 160 mil | 5/10/15 % |
| nueva-ranger/ranger-3-0-l-v6-diesel | revisión de 16.000 km ó 12 meses | 16 → 160 mil | 5/10/15 % |
| nueva-ranger/ranger-raptor-3-0-l-v6-nafta | revisión de 16.000 km ó 12 meses | 16 → 160 mil | 5/10/15 % |
| ranger-raptor (Raptor anterior) | revisión de 10.000 km ó 12 meses | 10 → 100 mil | 5/10/15 % |
| ranger/ (índice "Ranger (Hasta 2023)") | — | — | — |
| ranger/ranger-3-2-l-diesel | revisión de 10.000 km ó 12 meses | 10 → 100 mil | 5/10/15 % |
| ranger/ranger-2-l-diesel (título: 2.2L Diesel) | revisión de 10.000 km ó 12 meses | 10 → 100 mil | 5/10/15 % |
| ranger/ranger-2012-2016-3-2-l-diesel | revisión de 10.000 km ó 12 meses | 10 → 100 mil | 5/10/15 % |

Vigencia de precios en todas: 01/09/2026 al 30/09/2026.

### C. km/n y Δkm recalculados (filtros propios)
221.703 turnos concluidos con n° de service (87.531 vehículos) → 221.290 vehículo-día → 793 duplicados (mismo n a ≤ 30 d) descartados.
P703 km/n mediana por n: 1: 16.041 · 2: 16.081 · 3: 16.150 · 4: 16.173 · 5: 16.152 · 6: 16.091 · 7: 16.127. Δkm n→n+1: 16.140 (p25 14.729, p75 17.642).
P375 km/n: 10.125-10.301 (n = 2..12). Δkm n→n+1: 10.332 (p25 9.461, p75 11.728).

### D. Reconstrucción de ventanas
| Variante | evaluables | churn | censuradas | preempted | train | valid | test | churn test |
|---|---|---|---|---|---|---|---|---|
| K = 16.000 (config actual) | 142.558 | 0,4159 | 35.188 | 59.763 | 101.960 | 20.894 | 19.704 | 0,4260 |
| `data/processed/ventanas.parquet` | 142.558 | 0,4159 | 35.188 | 59.763 | 101.960 | 20.894 | 19.704 | 0,4260 |
| K = 15.000 (config anterior) | 145.538 | 0,4164 | 36.397 | 57.334 | 103.842 | 21.505 | 20.191 | 0,4293 |
| PDF viejo del informe | 145.538 | 41,6 % | 36.397 | — | 103.841 | 21.506 | 20.191 | 42,9 % |

Corrimiento del vencimiento (K16 − K15) en anclas de mantenimiento P703: mediana 10 d (p25 7, p75 14); 12 d cuando manda km.
K = 16.000 para todo el parque (P375 incluida): anclas P375 preempted 51,6 % (vs 20,4 % con 10.000); mediana del retorno real −63 d vs vencimiento (vs 0 d); 80,0 % de los retornos antes del vencimiento (vs 49,6 %).

### E. AUC
`test_scored.parquet`: 19.704 filas, `window_id` único, mismo conjunto y mismas etiquetas que el test del parquet. ROC-AUC 0,7391 (calibrado) / 0,7400 (sin calibrar) / 0,6743 (logística); PR-AUC 0,6994; recall@20 % 0,361 (3.034 de 8.394 churners en 3.941 contactados).

### F. Otras cifras del informe contrastadas
- "unos 1.200 clientes tuvieron 2 o más vehículos entrando en ventana el mismo mes: 13 % de las ventanas" → últimos 12 meses (evaluables + censuradas con `customer_id`): 2.282 cliente-mes, 1.102 clientes distintos, 9.354 de 82.893 ventanas = 11,3 %. Aproximado; depende de qué se cuente como "cliente".
- "17.973 vehículos entregados antes de 2024 sin ningún mantenimiento" → proxy desde el parquet: 16.986 vehículos sólo con ventanas `fuera_de_rango` + 888 sin ninguna ventana = 17.874. No reproducible exacto con el parquet; no lo doy por malo.
- `sensibilidad_ventana.csv` se regeneró a las 21:03 (después de docs/04, 20:57) y ya tiene K = 16.000; el "K único" del harness es agregado (preempted 30,0 % vs 20,1 %), no por generación.

## Hallazgos que exceden el bloque pero salieron de acá
1. `reports/informe_final.pdf` es de la corrida vieja (K = 15.000); regenerarlo después de corregir el md.
2. `docs/informe_final.md`: §6.4 (ablaciones), §11 pregunta 1 (15.000), §1 (5.000-6.000/mes), §4 ("un mes tarde" → ~2 meses), §6.1 vs §6.4 (0,739 vs 0,736).
3. docs/04 §2.3 atribuye a astra los descuentos por continuidad; astra no los menciona en ningún archivo.
4. docs/04 §4.3: corrimiento ~15 d → 10-12 d.
5. `src/repurchase/ventanas.py`: la generación `RANGER` sin sufijo y las 3 sin generación toman K = 16.000 por default (`km_interval`); el comentario del campo `km_by_generation` todavía dice "EDA 02: 15k P703 / 10k P375".
6. Anexo de docs/04: sumar las URL de la V6, la Raptor nueva, la Raptor anterior y las páginas "Ranger (Hasta 2023)", que dan 16.000/12 meses y 10.000/12 meses respectivamente y cierran la duda sobre la Raptor P703.
