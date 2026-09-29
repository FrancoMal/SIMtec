# Verificación escéptica — bloque "artefacto_y_comparacion" (docs/04 §2.2 y §4)

Script: `scripts/revision_cruzada/verif_artefacto_y_comparacion.py` (salida completa en
`verif_artefacto_y_comparacion_log.md`, reentrenos en `verif_artefacto_y_comparacion_reentrenos.csv`). Todo se recalculó
con código propio a partir de `G:\SIMtec-astra\...\data\processed\test_predicciones.parquet` / `ventanas.parquet` (solo
lectura) y de una reconstrucción independiente de las ventanas y features mensuales de fable. Los modelos reentrenados se
guardaron en el scratchpad, no en `data/models`.

## Tabla de veredictos

| # | Afirmación (docs/04) | Veredicto | Original | Recalculado | Nota |
|---|---|---|---|---|---|
| 1 | Test de astra: churn 75,6 % con vencimiento en días 0-5 → 81,7 % en días 26-31 | **confirmada** | 75,6 % / 81,7 % | 75,57 % (n=4.102) / 81,67 % (n=4.053) | §2.2 dice "días 1-5" y §4 "0-5": el bucket es 0-5 días *desde el 1°* (vence entre el 1 y el 6). Por día del mes 1-5 → 26-31 da 75,3 % → 81,8 %. El gradiente aparece en los 4 meses (jul-26 más plano: 76,0 → 79,7). |
| 2 | Ordenar sólo por días al vencimiento da ROC-AUC 0,538 | **confirmada** | 0,538 | 0,5383 (0,5385 con la columna float `dias_al_vencimiento` de astra) | Por mes: 0,527-0,554. |
| 3 | …y lift@10 % 1,053 (capacidad 10 % por mes, redondeo hacia arriba) | **ajustada** (leve) | 1,053 | global/arbitrario 1,0534; por mes 1,0526 (arbitrario) / 1,0522 (valor esperado); 1,058 con la columna float sin empates | El script 01 calculó el top 10 % **global** de los 4 meses, no por mes como dice el documento; los días son enteros y hay 221-242 filas empatadas en el umbral de cada mes. La diferencia es ≤ 0,005 y no cambia la conclusión. |
| 4 | Spearman entre el score de astra y los días al vencimiento 0,094 | **confirmada** | 0,094 | 0,0936 (0,0917 con la columna float) | Además: el AUC del modelo de astra *dentro* de cada bucket de calendario es 0,64-0,69 (no cae a 0,5): el modelo no está dominado por el calendario. |
| 5 | Pipeline de fable con etiqueta mensual: ROC-AUC 0,730, lift@10 % 1,24, n=25.612, abr-jul 2026 | **confirmada** | 0,730 / 1,240 / 25.612 | 0,7295 / 1,2399 / 25.612 (Spearman 1,000 entre el score guardado y el reentrenado: corrida determinista) | El score isotónico tiene sólo 95 valores distintos: en julio hay 722 filas empatadas en p=1,0 para 666 cupos. El lift no depende del desempate (arbitrario 1,2399; por score crudo 1,2404; valor esperado 1,2403) porque el churn dentro del empate es homogéneo. Lift@20 % 1,200. |
| 6 | La comparación es justa: mismos meses, misma regla de capacidad, sin leakage en el split, merge correcto | **confirmada con salvedad** | — | Train scoring ene-24..nov-25 (horizonte máx 30/11/25) < valid dic-25..mar-26 (horizonte máx 31/3/26) < test abr-jul 26; features as-of estrictas (todas las `days_since_*` > 0); ceil(10 %) por mes en ambos (`lift_monthly` ≡ `select_capacity` de astra); merge 1:1 verificado con `validate="one_to_one"` (ids de 16 caracteres en ambos): 9.322 | Salvedad 1: períodos de entrenamiento distintos: fable ajusta LightGBM con 100.296 ventanas (ene-24..nov-25) vs astra 61.846 (jul-24..ago-25): fable usa 3 meses más recientes y 6 más antiguos. Salvedad 2: los comunes son sólo el 39 % del test de astra y el 36 % del de fable (6.501 vehículos del test de astra los scorea fable en otro mes por vencimientos distintos). Menor: 826 ventanas donde el vehículo volvió justo el 1° del mes, fable las excluye como *preempted* y astra las contaría como retorno. |
| 7 | "Con la misma etiqueta el pipeline de fable rinde mejor: 0,730 vs 0,673; lift 1,24 vs 1,20" (§0.4, §2.2.9, §4.1) | **ajustada** | 0,730 vs 0,673 (Δ 0,057) | En los no comunes fable tiene AUC 0,732 (n=16.290, churn 0,836; el 29 % son ventanas de primer service ancladas en garantía que astra no tiene ese mes) vs 0,689 en los comunes | Son poblaciones distintas; la brecha comparable es la de los comunes (+0,025 a +0,043 en AUC), no 0,057. En lift, ver fila 9. |
| 8 | Sobre los 9.322 vehículos-mes comunes, fable 0,689 vs astra 0,646 | **ajustada** | 0,689 vs 0,646 (Δ 0,043) | Exactos: 0,6893 vs 0,6461 con la etiqueta de fable para ambos; 0,6839 vs 0,6587 con la de astra (Δ 0,025); cada uno con la suya 0,689 vs 0,659 (Δ 0,030). Bootstrap por cliente (300 réplicas, 8.640 clientes), IC95 de ΔAUC: [+0,033, +0,054] (etiq. fable) y [+0,015, +0,037] (etiq. astra) | El documento elige el par más favorable (la etiqueta de fable para el modelo de astra, que fue entrenado con la suya). La ventaja en AUC es real y significativa en cualquiera de las dos etiquetas, pero vale 0,025-0,043, no "0,043". Las etiquetas coinciden 96,6 %; con `target_vin` de astra coinciden 99,3 %: la discrepancia es casi toda identidad (mismo usuario), no Guarantee ni vencimientos. |
| 9 | Ventaja de fable en lift@10 % (implícita en "1,24 vs 1,20") | **refutada** sobre los mismos vehículos-mes | 1,24 vs 1,20 | Comunes: 1,270 vs 1,250 (etiq. fable), 1,242 vs 1,237 (etiq. astra). IC95 Δlift: [−0,007, +0,050] y [−0,013, +0,025] | En lift@10 % no hay diferencia detectable entre los dos modelos sobre el mismo conjunto. El "1,24 vs 1,20" compara poblaciones distintas. Ambos están cerca del techo 1/0,78 = 1,28, como dice §4.2. |
| 10 | La ventaja no se explica por asimetrías (período de train, features) | **ajustada** | "El modelo aporta; la etiqueta manda" | Reentrenando fable con el período de astra (jul-24..ago-25, 69.727 ventanas, valid oct-nov 25 + ene-feb 26): en su población 0,7216 / 1,236; en comunes 0,678 / 0,675 vs astra 0,646 / 0,659 (Δ +0,032 / +0,017). Quitando además dealer, TMA, zona, región y encuestas: 0,7046 / 1,18 en su población; comunes 0,665 / 0,662 (Δ +0,019 / +0,003); lift 1,261 / 1,238 vs 1,250 / 1,237 | La ventaja en AUC sobrevive al período de entrenamiento pero se achica, y con la etiqueta de astra casi desaparece al quitar dealer y encuestas (2° y 3° feature por ganancia: 9,7 % y 7,9 %). Astra tenía esos datos (mismos crudos) y eligió no usar el dealer como feature; no son features "imposibles", pero la frase "las 86 features aportan" debería decir que lo que aporta es sobre todo dealer + encuestas + más historia de entrenamiento. `days_to_due_at_scoring` (el artefacto de calendario) pesa 1,6 %. |
| 11 | Astra entrenó jul-24 a ago-25 | **confirmada** | jul-24..ago-25 | train 61.846 ventanas con etiqueta (scoring 2024-07-01..2025-08-01); valid oct-nov 25 (11.459); calibración ene-feb 26 (11.848); embargo sep-25, dic-25, mar-26 (17.562); test abr-jul 26 (23.740) | Releído de `src/modeling.py::split_name` sobre su `ventanas.parquet`. 300 árboles fijos, sin early stopping; selección por AP en valid. |

## Cómo se verificó cada cosa

**A. Artefacto de calendario.** `dias = (due_date − scoring_date).days` sobre el test de astra (23.740 filas, 4 meses,
sin duplicados por vehículo-mes, sin target nulo). El 74,6 % de los vencimientos de astra tiene componente horaria (proyecta
días fraccionales); truncar a entero no cambia el orden entre días distintos y la AUC/Spearman apenas se mueven (0,5383 vs
0,5385; 0,0936 vs 0,0917). Buckets `pd.cut([-1,5,10,15,20,25,31])` como el script 01, más una tabla por día del mes y otra
por mes de scoring. Lift@10 % con tres reglas de desempate (los días son enteros: hay más de 200 empates en el umbral cada
mes). AUC del modelo de astra dentro de cada bucket como control por calendario.

**B. Comparación.** Se reconstruyeron las ventanas mensuales de fable (`label_mode=mes_calendario`, `label_margin_days=0`,
cutoff 31/7/2026): 150.691 evaluables, churn 0,7893 (igual al informe 02). Se verificó por assert que el scoring es el 1°,
el horizonte es fin de mes, el vencimiento cae en el mes de scoring, la etiqueta equivale a "hubo mantenimiento entre el 1°
(exclusivo) y fin de mes (inclusivo)", no hay duplicados vehículo-mes, no se solapan horizontes entre particiones y todas las
features de recencia son estrictamente positivas. Se reentrenó tres veces con `run_training` de fable: (1) el split del
informe 02 (reproduce 0,7295 / 1,2399 exactos), (2) el período de astra, (3) el período de astra sin dealer/TMA/zona/
región/encuestas. El cara a cara sobre los 9.322 comunes usa el merge `(vehicle_id, scoring_date)` con `validate=
"one_to_one"`, los dos scores (isotónico de fable con desempate por score crudo; sigmoide de astra) y las dos etiquetas, y un
bootstrap por `customer_id` de astra (300 réplicas) de las diferencias pareadas.

## Qué queda en pie y qué no

- **En pie**: el artefacto de calendario existe y es moderado (6 puntos), no domina el modelo de astra; el pipeline de fable
  con la etiqueta mensual da 0,730 / 1,24 en su población; el split no tiene leakage; la regla de capacidad es la misma; el
  merge es correcto; sobre los mismos vehículos-mes fable ordena mejor en AUC (+0,015 a +0,054 según etiqueta, IC95).
- **Ajustado**: "0,730 vs 0,673" y "0,689 vs 0,646" son los pares más favorables a fable; la brecha honesta en AUC sobre los
  comunes es 0,025-0,043 con el mismo período de train de fable, 0,017-0,032 con el período de astra, y 0,003-0,019 sin
  dealer/encuestas. Parte de la ventaja es más historia de entrenamiento y parte son features que astra tenía y no usó.
- **Refutado**: que fable tenga ventaja en lift@10 % sobre los mismos vehículos-mes. Los IC de la diferencia incluyen 0 con
  las dos etiquetas. Con 78 % de positivos los dos modelos están pegados al techo de 1,28 y el lift no distingue.
- **Sugerencia de redacción para docs/04**: en §0.4 y §2.2.9 reemplazar "0,730 vs 0,673; lift 1,24 vs 1,20" por "sobre los
  mismos 9.322 vehículos-mes, AUC 0,68-0,69 vs 0,65-0,66 (IC95 de la diferencia +0,02 a +0,05) y lift@10 % indistinguible
  (1,24-1,27 vs 1,24-1,25)"; en §2.2.1 unificar "días 1-5" con "0-5 días desde el 1°".
