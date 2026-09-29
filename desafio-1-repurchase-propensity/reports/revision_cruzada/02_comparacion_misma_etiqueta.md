# Comparación con la misma etiqueta (mensual, de astra)

Parámetros: {"cycle_days": 365, "km_interval": 16000, "km_by_generation": {"RANGER (P703)": 16000, "RANGER RAPTOR (P703)": 16000, "RANGER (P375)": 10000, "RANGER RAPTOR": 10000}, "lead_days": 30, "horizon_days": 90, "min_gap_days": 90, "first_due_days": 300, "anchor": "last_maintenance", "km_source": "current", "min_history_days": 0, "split_visit_days": 30, "label_margin_days": 0, "label_mode": "mes_calendario"}

Ventanas evaluables con etiqueta mensual: 150,691; churn 0.789
| scoring_date   |   size |   mean |
|:---------------|-------:|-------:|
| 2024Q1         |   3736 |  0.848 |
| 2024Q2         |   8437 |  0.764 |
| 2024Q3         |  13546 |  0.786 |
| 2024Q4         |  13038 |  0.779 |
| 2025Q1         |  14693 |  0.779 |
| 2025Q2         |  16770 |  0.791 |
| 2025Q3         |  17514 |  0.791 |
| 2025Q4         |  18721 |  0.795 |
| 2026Q1         |  18624 |  0.788 |
| 2026Q2         |  18955 |  0.796 |
| 2026Q3         |   6657 |  0.797 |

## Resultado del pipeline de fable con la etiqueta mensual (test abr-jul 2026)

n = 25,612; churn 0.796; ROC-AUC 0.730; AP 0.907; lift@10 % (por mes) 1.240; lift@20 % 1.200
Regresión logística de fable, misma etiqueta: ROC-AUC 0.672; lift@10 % 1.170
Referencia astra (su test abr-jul 2026, n = 23.740, churn 0,782): ROC-AUC 0,673; AP 0,877; lift@10 % 1,20 (IC95 1,18-1,22).

Por mes:
| scoring_date   |    n |   churn |   roc_auc |   lift10 |
|:---------------|-----:|--------:|----------:|---------:|
| 2026-04        | 6259 |   0.794 |     0.728 |    1.237 |
| 2026-05        | 6339 |   0.79  |     0.73  |    1.232 |
| 2026-06        | 6357 |   0.805 |     0.727 |    1.235 |
| 2026-07        | 6657 |   0.797 |     0.732 |    1.255 |

Horizonte 60 d desde el 1° (n=18,955, churn 0.637): ROC-AUC 0.729; lift@10 % 1.513   (astra: 60 d churn 0,638 / lift 1,41; 90 d churn 0,558 / lift 1,56)

Horizonte 90 d desde el 1° (n=12,598, churn 0.520): ROC-AUC 0.710; lift@10 % 1.764   (astra: 60 d churn 0,638 / lift 1,41; 90 d churn 0,558 / lift 1,56)

## Vehículos-mes scoreados por ambos en abr-jul 2026: 9,322

Etiquetas coinciden en 96.6% de los casos (difieren por mismo-usuario, Guarantee y vencimientos distintos).
- fable (LightGBM calibrado): con la etiqueta de fable ROC-AUC 0.689, lift@10 % 1.269; con la etiqueta de astra ROC-AUC 0.684, lift@10 % 1.242
- astra (LightGBM_31 calibrado): con la etiqueta de fable ROC-AUC 0.646, lift@10 % 1.250; con la etiqueta de astra ROC-AUC 0.659, lift@10 % 1.237
Correlación de Spearman entre los dos scores: 0.684