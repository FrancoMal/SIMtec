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
