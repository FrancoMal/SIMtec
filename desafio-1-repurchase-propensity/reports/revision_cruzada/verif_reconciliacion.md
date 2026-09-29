# Verificación escéptica — bloque "reconciliacion" (docs/04_revision_cruzada.md, sección 1)

> Revisor independiente, 15/09/2026. Script: `scripts/revision_cruzada/verif_reconciliacion.py` (código propio: "primer evento
> posterior a X" con `merge_asof` en vez del join many-to-many del script original; tres conjuntos de eventos: fable
> check-in/turno, fable con checkout y astra checkout+Guarantee; etiquetas de astra recalculadas desde su `eventos.parquet`;
> diferencia de vencimiento 1 a 1 por la misma ancla). Todo lo de astra y los crudos se leyeron en solo lectura.

## Resumen en cuatro líneas

1. **El método del script original está bien** (no duplica filas, los intervalos abiertos/cerrados coinciden con los de astra,
   la convención check-in vs checkout no mueve ningún resultado más de 0,3 puntos). Lo que falla es la **vigencia**: el
   informe `01_reconciliacion.md` (20:48) se corrió **antes** de regenerar `ventanas.parquet` con K = 16.000 (20:50). Reconstruí
   las ventanas con K = 15.000 y reproduje exactamente 26.871 / 80,2 %, 41,3 %, 92.838 / 76.830 y n = 21.059: la sección 1 del
   documento cita cifras de la corrida vieja mientras la sección 3 y la fila "Resultado" de 1.1 (142.558 / 41,6 %) son de la nueva.
2. Sobre el parquet actual: (a) 80,2 % pasa a **79,0 %**; (c) 41,3 % pasa a **40,5 %** y cubre vencimientos de abril-mayo, no
   abr-jul; (e) 92.838 / 76.830 pasan a **92.326 / 76.713** y la mediana de −7 días pasa a **−1 día** (0 días si se compara la
   misma ancla): la explicación "fable antes, por el 15.000" ya no aplica al pipeline actual.
3. (b) **44,0 % confirmado** y (d) **3,1 puntos confirmado** (mis etiquetas recalculadas coinciden al 100 % con las de astra).
4. La conclusión de fondo ("misma población, dos relojes; ~40-44 % de los churn mensuales son tardíos") **sobrevive** a todas
   las variantes que probé; lo que hay que corregir son los números citados y dos salvedades de redacción (abajo).

## Tabla de veredictos

| # | Afirmación (doc §1) | Veredicto | Original | Recalculado (parquet actual) | Nota |
|---|---|---|---|---|---|
| a | Etiqueta mensual de astra sobre ventanas de fable: churn abr-jul 2026 = 80,2 % | **ajustada** | 80,2 % (n = 26.871) | **79,0 %** (n = 25.829); 79,0 % con checkout; 79,0 % con eventos de astra; **82,1 %** con la regla completa de astra (mismo `customer_id`) | El 80,2 % es del parquet con K = 15.000 (reproducido exactamente). La convención de fecha no importa. El número que más se parece a "la etiqueta de astra" es 82,1 %, porque astra además exige el mismo id. |
| b | Etiqueta de fable sobre ventanas de astra: 44,0 % en 107.557 | **confirmada** | 44,0 % (n = 107.557) | **44,0 %** (n = 107.713 con el vencimiento normalizado a día; 107.557 comparando el `due_date` fraccionario de astra contra la medianoche); 43,7 % con checkout o con eventos de astra; 44,4 % con inicio exclusivo | Salvedad: las ventanas de astra sólo existen si el vehículo no volvió antes del 1° del mes; el 9,0 % de las ventanas evaluables de fable vuelve entre due−30 y el 1°. El churn de fable condicionado a eso es 45,7 %, no 41,6 %: 44,0 % vs 41,6 % no es una comparación de poblaciones iguales. |
| c | El 41,3 % de los churn mensuales de abr-jul 2026 (anclas de fable) completa el mantenimiento antes de due+90 | **ajustada** | 41,3 % (n = 9.658) | **40,5 %** (n = 9.216, horizonte ≤ 25/08 como el original); **39,9 %** con el margen de fable (≤ 26/07); sobre los churn reales de astra: 42,9 % (abril) / 43,5 % (abr-may) / 44,2 % (todo el historial) | "abr-jul" es engañoso: sólo cierran horizonte los vencimientos del 01/04 al 27/05 (o al 27/04 con margen). El rango honesto es 40-44 % y la frase de §0 ("41 % de los churn de astra") se sostiene mejor con las ventanas de astra (42,9-44,2 %) que con las de fable. |
| d | Exigir el mismo `customer_id` suma 3,1 puntos de churn | **confirmada** | 3,1 puntos (77,9 % vs 74,8 %) | **3,11 puntos** (todas), 3,19 en el test; recomputado desde `eventos.parquet`: coincide 100 % con `target` y `target_vin` | Dos salvedades: (1) §0 punto 7 dice "3,1 % de sus churn": son 3,1 % de las **ventanas** = **4,0 % de los churn**. (2) "Churn falsos por identidad" presume que es la misma persona: el id que volvió ya había tenido un turno con ese vehículo sólo en el 19,4 % de los casos (4,6 % es el comprador); en el 77,5 % nunca se lo había visto en ese VIN. A nivel vehículo el retorno es real; a nivel relación usuario-vehículo, no está demostrado que sea "falso". |
| e | Solapamiento: 76.830 en común de 77.973 (astra) y 92.838 (fable); vencimiento difiere −7 d de mediana (fable antes, por el 15.000 y la tasa acumulada) | **ajustada** | 77.973 / 92.838 / 76.830; −7 d (n = 21.059) | 77.973 (ok) / **92.326** / **76.713** (98,4 % de astra está en fable; 229 vehículos de astra no tienen ninguna ventana en fable); mediana **−1 d** con el mismo merge (n = 21.277); **0 d** 1 a 1 por la misma ancla (n = 16.993): anclas de mantenimiento 0 d (p25 −5, p75 +14), primer service **−65 d** (300 vs 365) | Conteos de la corrida vieja. La explicación "por el 15.000" quedó obsoleta: con K = 16.000 los dos vencimientos coinciden en la mediana para anclas de mantenimiento; lo único que difiere sistemáticamente es el primer service. Además el merge original es many-to-many: 4.173 de los 21.277 pares cruzan anclas distintas (mediana −33 d) y arrastran la mediana global. |

## Qué corregir en docs/04

- §1.2 (tabla y párrafo): 80,2 % → 79,0 %; 41,3 % → 40,5 % (y decir "vencimientos de abril-mayo 2026", o usar el 42,9-44,2 %
  calculado sobre las ventanas de astra, que es lo que dice §0 punto 3); 46,5 % → 46,6 %; n = 12.186 → 11.755.
- §1.1 párrafo de solapamiento: 92.838 → 92.326; 76.830 → 76.713; "−7 días de mediana (fable antes, por el 15.000 y la tasa
  acumulada)" → "−1 día con el mismo criterio; 0 días comparando la misma ancla; −65 días en el primer service (300 vs 365)".
- §0 punto 7 y §4 punto 5: "3,1 % de sus churn" → "3,1 puntos de churn (3,1 % de las ventanas, 4,0 % de los churn)"; matizar
  "falsos por identidad": sólo 1 de cada 5 ids que vuelven ya estaba asociado al vehículo.
- §1.2: agregar la salvedad de selección de (b): el 44,0 % está condicionado a no haber vuelto antes del 1°; el equivalente en
  fable es 45,7 %, no 41,6 %.
- Regenerar `01_reconciliacion.md` con el parquet actual (el script está bien; sólo hay que volver a correrlo) y sacar del
  texto hardcodeado "fable 15.000 km".
- Ironía a evitar: §3 critica al PDF por mezclar dos corridas; §1 hoy mezcla la corrida vieja (K = 15.000) con la nueva.

## Hallazgos extra

- La convención de fecha (fable check-in/turno vs astra checkout) es irrelevante para todo el bloque: checkout − fecha fable
  tiene mediana 0 d, media 2,7 d, p90 6 d, y ningún resultado se mueve más de 0,3 puntos al cambiarla.
- Contar *Guarantee* como mantenimiento (astra) tampoco mueve estas cifras: 79,0 % / 43,7 % con eventos de astra vs 79,0 % / 44,0 % con los de fable.
- Sobre las ventanas de astra hay 682 casos con churn fable = 1 y target astra = 0: son retornos que astra cuenta (Guarantee
  o checkout dentro del mes con check-in fuera) y fable no; 0,6 % de 107.713, sin efecto en la conclusión.
- El `due_date` de astra tiene fracción de día (p. ej. `2026-08-31 23:29:08`); comparar contra medianoche cambia conteos
  (107.557 vs 107.713) pero no porcentajes. Conviene normalizar antes de cruzar.
- En abr-jul 2026 fable tiene 3.257 vehículos con más de una ventana (astra 468): cualquier merge por `vehicle_id` en ese
  período cruza ventanas distintas; hay que emparejar por ancla.

---

# Evidencia: salida íntegra de `verif_reconciliacion.py`

# Verificación independiente — bloque 'reconciliacion' (sección 1 de docs/04_revision_cruzada.md)

Corrida: 2026-09-15 21:08. Corte de datos (CUTOFF fable): 2026-08-25; margen de etiqueta: 2026-07-26; observed_until astra: 2026-08-01 (exclusivo).

Archivos y mtimes (para saber sobre qué corrida se calculó cada cosa):
- `G:\SIMtec-fable\desafio-1-repurchase-propensity\data\processed\ventanas.parquet`: 2026-09-15 20:50:57
- `G:\SIMtec-fable\desafio-1-repurchase-propensity\config\params.json`: 2026-09-15 20:49:39
- `G:\SIMtec-fable\desafio-1-repurchase-propensity\reports\revision_cruzada\01_reconciliacion.md`: 2026-09-15 20:48:09
- `G:\SIMtec-fable\desafio-1-repurchase-propensity\scripts\revision_cruzada\01_reconciliacion_definiciones.py`: 2026-09-15 20:47:07
- `G:\SIMtec-astra\desafio-1-repurchase-propensity\data\processed\ventanas.parquet`: 2026-09-15 19:19:58
- `G:\SIMtec-astra\desafio-1-repurchase-propensity\data\processed\eventos.parquet`: 2026-09-15 18:55:30

K por generación en el parquet actual de fable: {16000.0: 174280, 10000.0: 173610} (params.json: {'RANGER (P703)': 16000, 'RANGER RAPTOR (P703)': 16000, 'RANGER (P375)': 10000, 'RANGER RAPTOR': 10000}).
Ventanas de fable por estado: {'evaluable': 142558, 'preempted': 59763, 'futura': 59383, 'fuera_de_rango': 50998, 'censurada': 35188}.
Eventos: fable 220,522; astra (maintenance & valid_complete) 225,479. Checkout − fecha fable en los eventos de fable: mediana 0 d, media 2.71 d, p90 6 d, > 0 en 44.5 % de los eventos.

## (a) Etiqueta mensual de astra sobre las ventanas de fable — afirmación: churn abr-jul 2026 = 80,2 %

- eventos **fable (check-in/turno)**: n=25,829, churn mensual abr-jul = **79.0 %** (por mes: 2026-04 78.3 % (n=6,344.0), 2026-05 79.0 % (n=6,340.0), 2026-06 79.6 % (n=6,429.0), 2026-07 79.0 % (n=6,716.0))
  - exigiendo customer_id no nulo en la ventana (astra descarta VIN sin cliente): n=25,700, churn = 78.9 %
- eventos **fable con fecha de checkout**: n=25,992, churn mensual abr-jul = **79.0 %** (por mes: 2026-04 78.3 % (n=6,398.0), 2026-05 79.1 % (n=6,372.0), 2026-06 79.7 % (n=6,474.0), 2026-07 79.0 % (n=6,748.0))
- eventos **astra (checkout, incl. Guarantee)**: n=25,941, churn mensual abr-jul = **79.0 %** (por mes: 2026-04 78.3 % (n=6,385.0), 2026-05 79.1 % (n=6,359.0), 2026-06 79.7 % (n=6,461.0), 2026-07 79.0 % (n=6,736.0))
- regla completa de astra (eventos astra, **mismo customer_id**, anónimo → indeterminado) sobre las ventanas de fable: churn = **82.1 %** (n etiquetadas 25,864, indeterminadas 77).
- referencia: astra en su propio test abr-jul 2026: 78.2 % (n=23,740).

## (b) Etiqueta de fable (due−30 / due+90, nivel vehículo) sobre las ventanas de astra — afirmación: 44,0 % en 107.557

Ventanas de astra con target no nulo y due+90 ≤ 2026-07-26: **107,713** con el vencimiento normalizado a día (107,557 si se compara el `due_date` fraccionario de astra contra la medianoche del 2026-07-26, como el script original); rango de scoring 2024-07 a 2026-04; churn mensual de astra en ellas: 77.7 %.
- eventos **fable (check-in/turno)**, inicio inclusivo, vencimiento normalizado a día: churn fable = **44.0 %**; inicio exclusivo: 44.4 %; con due sin normalizar (como el script original): 44.0 %
- eventos **fable con fecha de checkout**, inicio inclusivo, vencimiento normalizado a día: churn fable = **43.7 %**
- eventos **astra (checkout, incl. Guarantee)**, inicio inclusivo, vencimiento normalizado a día: churn fable = **43.7 %**
- abr 2026 solamente (único mes del test de astra con due+90 cerrado al 2026-07-26): n=4,998, churn fable = 44.6 %, churn mensual astra = 76.8 %.
- incluyendo también las ventanas con target indeterminado (NaN) de astra: n=107,825, churn fable = 44.0 %.
- con horizonte cerrado al corte sin margen (2026-08-25): n=113,516, churn fable = 44.1 %.
- consistencia: ventanas con churn fable = 1 y target astra = 0: 682 (esperado ~0: sólo por diferencia de eventos check-in vs checkout / mismo cliente).
- selección implícita: en las ventanas evaluables de fable (142,558, churn 41.6 %), 9.0 % vuelve entre la apertura (due−30) y el 1° del mes del vencimiento; astra nunca crea esas ventanas. Churn de fable condicionado a NO haber vuelto antes del 1°: **45.7 %** (n=129,673).

## (c) De los churn mensuales de abr-jul 2026 (anclas de fable), % que completa el mantenimiento antes de due+90 — afirmación: 41,3 %

- horizonte ≤ CUTOFF = 2026-08-25 (como el script original): n churn mensual = 9,216, vencimientos entre 2026-04-01 y 2026-05-27; vuelven antes de due+90: **40.5 %** (eventos fable) / 40.2 % (eventos astra).
- horizonte ≤ margen fable = 2026-07-26: n churn mensual = 4,277, vencimientos entre 2026-04-01 y 2026-04-27; vuelven antes de due+90: **39.9 %** (eventos fable) / 39.5 % (eventos astra).
- todos los churn mensuales abr-jul (n=20,398), contando sólo lo observado hasta el corte: ya volvió 32.1 % (cota inferior; jun-jul censurados).
- sobre los churn REALES de astra en su test (target=1, abr-jul 2026) con due+90 ≤ 2026-07-26: n=3,836 (vencimientos 2026-04-01 a 2026-04-27); vuelven antes de due+90: **42.9 %** (eventos fable, VIN) / 42.6 % (eventos astra, VIN).
- sobre los churn REALES de astra en su test (target=1, abr-jul 2026) con due+90 ≤ 2026-08-25: n=8,458 (vencimientos 2026-04-01 a 2026-05-27); vuelven antes de due+90: **43.5 %** (eventos fable, VIN) / 43.2 % (eventos astra, VIN).
- ídem sobre TODOS los churn de astra con due+90 ≤ 2026-07-26 (n=83,733): vuelven antes de due+90: 44.2 %.

## (d) Exigir el mismo customer_id (target vs target_vin de astra) — afirmación: suma 3,1 puntos de churn

- columnas guardadas por astra, todas las ventanas etiquetadas (n=126,455): churn mismo usuario 77.9 % vs mismo VIN 74.8 %; diferencia **3.11 puntos**; P(target=1 & vin=0) = 3.1 %; P(target=0 & vin=1) = 0 casos.
- expresado sobre los churn (no sobre las ventanas): 4.0 % de las ventanas con target=1 son retornos del mismo VIN con otro id.
- en el test de astra (abr-jul 2026, n=23,740): 78.2 % vs 75.0 %, diferencia 3.19 puntos.
- recomputo independiente desde eventos.parquet: coincide con `target` en 100.0 % de las filas y con `target_vin` en 100.0 %; churn recalculado 77.9 % vs 74.7 % → diferencia 3.19 puntos.
- de esas 3,936 ventanas 'churn por identidad': el id que volvió ya había tenido un turno con ese vehículo antes del scoring en 19.4 %; es el comprador de la venta en 4.6 %; nunca visto en ese vehículo en 77.5 %.

## (e) Solapamiento de poblaciones y diferencia de vencimiento — afirmación: 76.830 en común de 77.973 (astra) y 92.838 (fable); mediana −7 d en abr-jul 2026

- astra: 77,973 vehículos con ventana (todas, incl. ago-2026 y target NaN); 75,423 con al menos una ventana etiquetada.
- fable: 92,326 (evaluable+censurada, como el script original); 96,050 (+preempted); 111,003 (todo salvo fuera_de_rango, incl. futuras).
- en común: astra(todas) ∩ fable(eval+cens) = **76,713** (98.4 % de astra, 83.1 % de fable); astra(todas) ∩ fable(+preempted) = 77,576; astra ∩ fable(todo) = 77,744.
- vehículos de astra sin NINGUNA ventana en fable: 229.
- abr-jul 2026: vehículos con vencimiento en astra 23,281 (23,763 ventanas) vs fable 34,328 (37,950 ventanas); en común 17,850.
- (i) merge por vehicle_id como el script original: n pares = 21,277 (vehículos con >1 ventana en abr-jul: astra 468, fable 3,257); diff fable − astra: mediana **-1 d**, p25 -23, p75 12, media -6.3.
- (ii) 1 a 1 por la misma ancla (|Δancla| ≤ 45 d, par más cercano): n = 16,993; diff fable − astra: mediana **0 d**, p25 -11, p75 12, media -1.9; Δancla (fable − astra) mediana 0 d, media -1.3 d.
  - ancla fable `maintenance` / astra sin_mantenimiento_previo=0: n=15,370, mediana 0 d, p25 -5, p75 14
  - ancla fable `warranty` / astra sin_mantenimiento_previo=1: n=1,623, mediana -65 d, p25 -65, p75 -65
  - anclas de mantenimiento, familia astra P375: n=5,734, mediana 1 d (regla fable: {'km': 0.78, 'tiempo': 0.12, 'piso': 0.11})
  - anclas de mantenimiento, familia astra P703: n=9,266, mediana 0 d (regla fable: {'km': 0.8, 'tiempo': 0.13, 'piso': 0.08})
  - anclas de mantenimiento, familia astra RAPTOR_P703: n=370, mediana 0 d (regla fable: {'km': 0.78, 'tiempo': 0.15, 'piso': 0.07})
- (iii) parte atribuible a la convención de fecha (fable ancla en check-in/turno, astra en checkout): mediana de Δancla en los pares = 0 d; el resto de la diferencia proviene de K (16.000 en ambos hoy), del ritmo (tasa acumulada vs mediana de diferencias) y del primer service (300 d vs 1 año).
- (iv) pares con anclas distintas (|Δancla| > 45 d) que el merge original mezcla: 4,173 de 21,277; su diff mediana -33 d (p25 -65, p75 5).

## Extra: etiqueta de fable sobre sus propias ventanas abr-jul 2026 (tabla 1.2 del doc: 46,5 %, n=12.186)

- horizonte ≤ 2026-08-25 (script original): n=11,755, churn fable (due−30/+90) = 46.6 %.
- horizonte ≤ 2026-07-26 (margen de fable): n=5,488, churn fable (due−30/+90) = 46.8 %.

## R. Reproducción con las ventanas de fable reconstruidas con K = 15.000 (P703), como estaban cuando corrió el script original

El informe `01_reconciliacion.md` (20:48) es anterior a `params.json` (20:49) y al `ventanas.parquet` actual (20:50). Se reconstruyen las ventanas con K=15.000 en memoria y se aplica exactamente el mismo código de esta verificación.
- **parquet actual (K=16.000)**: (a) n=25,829, churn mensual abr-jul = 79.0 %; (c) n churn=9,216, vuelven antes de due+90 = 40.5 %; (e) vehículos fable eval+cens = 92,326, en común con astra = 76,713; diff due (merge por vehicle_id, n=21,277) mediana -1 d, p25 -23, p75 12; 1 a 1 misma ancla (n=16,993) mediana 0 d.
- **reconstrucción con K=15.000**: (a) n=26,871, churn mensual abr-jul = 80.2 %; (c) n churn=9,658, vuelven antes de due+90 = 41.3 %; (e) vehículos fable eval+cens = 92,838, en común con astra = 76,830; diff due (merge por vehicle_id, n=21,059) mediana -6 d, p25 -26, p75 9; 1 a 1 misma ancla (n=16,895) mediana -4 d.
