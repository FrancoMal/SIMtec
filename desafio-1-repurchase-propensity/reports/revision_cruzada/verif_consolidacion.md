# Chequeo del consolidador: AUC y lift@10 % sobre los vehículos-mes comunes

Test mensual de fable: 25,612 ventanas; test de astra: 23,740; comunes (merge 1:1 por vehicle_id + scoring_date): 9,322.

| etiqueta | AUC fable | AUC astra | ΔAUC | lift@10 % fable | lift@10 % astra | Δlift |
|---|---|---|---|---|---|---|
| de fable | 0.6893 | 0.6461 | +0.0432 | 1.2739 | 1.2504 | +0.0236 |
| de astra | 0.6839 | 0.6587 | +0.0251 | 1.2450 | 1.2365 | +0.0084 |

Bootstrap por cliente (300 réplicas, 8,639 clientes, semilla 7) de la diferencia fable − astra:

| diferencia | media | IC95 |
|---|---|---|
| ΔAUC etiqueta fable | +0.044 | [+0.034, +0.054] |
| ΔAUC etiqueta astra | +0.026 | [+0.016, +0.035] |
| Δlift@10 % etiqueta fable | +0.017 | [-0.009, +0.046] |
| Δlift@10 % etiqueta astra | +0.005 | [-0.014, +0.026] |

Lectura: la ventaja de fable en ROC-AUC es significativa con las dos etiquetas; en lift@10 % los IC incluyen 0, así que el "1,24 vs 1,20" del documento (medido sobre poblaciones distintas) no se sostiene como ventaja sobre los mismos vehículos-mes. Coincide con verif_artefacto_y_comparacion.md.