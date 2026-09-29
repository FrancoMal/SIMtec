# Reconciliación de definiciones (fable vs astra)

Corte de datos: 2026-08-25. Eventos objetivo de fable: 220,522 mantenimientos completados.

## A. Población y etiqueta de astra, releídas de su `ventanas.parquet`

| mes     |   ventanas |   churn_mes |   churn_vin |   churn_60d |   churn_90d |   sin_label |
|:--------|-----------:|------------:|------------:|------------:|------------:|------------:|
| 2024-07 |       3283 |       0.751 |       0.723 |       0.571 |       0.472 |           5 |
| 2024-08 |       3488 |       0.743 |       0.714 |       0.586 |       0.48  |           3 |
| 2024-09 |       3539 |       0.767 |       0.738 |       0.597 |       0.502 |           1 |
| 2024-10 |       3776 |       0.745 |       0.72  |       0.578 |       0.494 |           2 |
| 2024-11 |       3627 |       0.743 |       0.714 |       0.589 |       0.509 |           0 |
| 2024-12 |       3845 |       0.757 |       0.733 |       0.601 |       0.496 |           5 |
| 2025-01 |       4650 |       0.758 |       0.731 |       0.601 |       0.53  |           4 |
| 2025-02 |       4279 |       0.782 |       0.749 |       0.63  |       0.551 |           2 |
| 2025-03 |       4812 |       0.794 |       0.767 |       0.656 |       0.567 |           1 |
| 2025-04 |       4931 |       0.779 |       0.747 |       0.635 |       0.568 |           2 |
| 2025-05 |       5013 |       0.776 |       0.741 |       0.647 |       0.555 |           4 |
| 2025-06 |       5146 |       0.798 |       0.765 |       0.643 |       0.553 |           2 |
| 2025-07 |       5712 |       0.773 |       0.739 |       0.631 |       0.555 |           6 |
| 2025-08 |       5784 |       0.785 |       0.75  |       0.646 |       0.56  |           2 |
| 2025-09 |       5693 |       0.783 |       0.752 |       0.642 |       0.558 |           4 |
| 2025-10 |       5827 |       0.782 |       0.746 |       0.653 |       0.575 |           8 |
| 2025-11 |       5646 |       0.805 |       0.772 |       0.65  |       0.56  |           6 |
| 2025-12 |       5959 |       0.783 |       0.754 |       0.629 |       0.541 |          10 |
| 2026-01 |       6376 |       0.774 |       0.732 |       0.641 |       0.549 |          19 |
| 2026-02 |       5498 |       0.817 |       0.789 |       0.647 |       0.569 |           7 |
| 2026-03 |       5937 |       0.783 |       0.748 |       0.623 |       0.536 |          13 |
| 2026-04 |       5747 |       0.776 |       0.744 |       0.629 |       0.546 |           6 |
| 2026-05 |       6001 |       0.796 |       0.76  |       0.651 |       0.569 |           9 |
| 2026-06 |       5718 |       0.78  |       0.749 |       0.632 |     nan     |           6 |
| 2026-07 |       6297 |       0.777 |       0.745 |     nan     |     nan     |           2 |
| 2026-08 |       6285 |     nan     |     nan     |     nan     |     nan     |        6285 |

Test astra (abr-jul 2026): 23,740 ventanas, churn mensual 0.782; por VIN 0.750; 60 d 0.638 (n=17,424); 90 d 0.558 (n=11,706)
Posición del vencimiento dentro del mes (test astra): mediana 16 días desde el 1°, p25 8, p75 23. Días de observación DESPUÉS del vencimiento: mediana 14.

## B. Etiqueta mensual de astra aplicada a las ventanas de fable

Ventanas de fable (anclas y vencimientos de fable), etiquetadas con la regla de astra (mes calendario del vencimiento, scoring el 1°) y con la de fable (vencimiento −30 / +90):

| mes_due   |   ventanas |   churn_mensual_astra |   churn_120d_fable |
|:----------|-----------:|----------------------:|-------------------:|
| 2025-01   |       4807 |                 0.75  |              0.437 |
| 2025-02   |       4750 |                 0.796 |              0.484 |
| 2025-03   |       5150 |                 0.79  |              0.465 |
| 2025-04   |       5386 |                 0.778 |              0.461 |
| 2025-05   |       5847 |                 0.792 |              0.459 |
| 2025-06   |       5585 |                 0.795 |              0.465 |
| 2025-07   |       5907 |                 0.784 |              0.468 |
| 2025-08   |       5913 |                 0.783 |              0.465 |
| 2025-09   |       5896 |                 0.779 |              0.461 |
| 2025-10   |       5901 |                 0.786 |              0.473 |
| 2025-11   |       6710 |                 0.807 |              0.454 |
| 2025-12   |       6221 |                 0.778 |              0.446 |
| 2026-01   |       6311 |                 0.776 |              0.457 |
| 2026-02   |       5744 |                 0.814 |              0.474 |
| 2026-03   |       6569 |                 0.776 |              0.46  |
| 2026-04   |       6344 |                 0.783 |              0.464 |
| 2026-05   |       6340 |                 0.79  |              0.469 |
| 2026-06   |       6429 |                 0.796 |              0.538 |
| 2026-07   |       6716 |                 0.79  |              0.666 |

Abr-jul 2026 sobre anclas de fable: n=25,829; churn mensual (regla astra) = 0.790; churn 120 d (regla fable, sólo horizontes cerrados) = 0.466 (n=11,755)
De los etiquetados churn por la regla mensual (abr-jul), 40.5% completa el mantenimiento antes de vencimiento + 90 días: son 'tardíos', no 'perdidos'.

## C. Etiqueta de fable (vencimiento −30 / +90, nivel vehículo) aplicada a las ventanas de astra

| mes     |   ventanas |   churn_mensual_astra |   churn_90d_astra |   churn_120d_fable |
|:--------|-----------:|----------------------:|------------------:|-------------------:|
| 2025-01 |       4646 |                 0.758 |             0.53  |              0.432 |
| 2025-02 |       4277 |                 0.782 |             0.551 |              0.451 |
| 2025-03 |       4811 |                 0.794 |             0.567 |              0.467 |
| 2025-04 |       4929 |                 0.779 |             0.568 |              0.456 |
| 2025-05 |       5009 |                 0.776 |             0.555 |              0.45  |
| 2025-06 |       5144 |                 0.798 |             0.553 |              0.45  |
| 2025-07 |       5706 |                 0.773 |             0.555 |              0.449 |
| 2025-08 |       5782 |                 0.785 |             0.56  |              0.452 |
| 2025-09 |       5689 |                 0.783 |             0.558 |              0.455 |
| 2025-10 |       5819 |                 0.782 |             0.575 |              0.461 |
| 2025-11 |       5640 |                 0.805 |             0.56  |              0.443 |
| 2025-12 |       5949 |                 0.783 |             0.541 |              0.438 |
| 2026-01 |       6357 |                 0.774 |             0.549 |              0.438 |
| 2026-02 |       5491 |                 0.817 |             0.569 |              0.465 |
| 2026-03 |       5924 |                 0.783 |             0.536 |              0.437 |
| 2026-04 |       4842 |                 0.767 |             0.545 |              0.448 |

Total ventanas de astra con horizonte de fable cerrado: 107,557; churn mensual 0.777 → churn a vencimiento+90 (fable) 0.440. Con la etiqueta 90 d de astra (desde el 1° del mes, mismo usuario): 0.542.
Etiqueta 'mismo usuario' vs 'mismo vehículo' (astra, todas las ventanas etiquetadas): churn 0.779 vs 0.748: 3.1% de las ventanas son retornos del mismo VIN con otro `customer_id` contados como churn.

## D. Artefacto de calendario: churn mensual según la posición del vencimiento dentro del mes (test astra)

| bucket   |   ventanas |   churn |   score_medio |
|:---------|-----------:|--------:|--------------:|
| 0-5      |       4102 |   0.756 |         0.779 |
| 6-10     |       3818 |   0.756 |         0.78  |
| 11-15    |       3828 |   0.78  |         0.783 |
| 16-20    |       3711 |   0.775 |         0.782 |
| 21-25    |       4228 |   0.807 |         0.807 |
| 26-31    |       4053 |   0.817 |         0.811 |

ROC-AUC del modelo de astra en su test: 0.673. ROC-AUC de ordenar SOLO por 'días hasta el vencimiento' (cuanto más tarde en el mes, más 'churn'): 0.538. Lift@10 % del modelo 1.200 vs lift@10 % de la regla de calendario 1.053.
Correlación de Spearman entre el score de astra y los días hasta el vencimiento: 0.094.

## E. Evento objetivo de astra: efecto de exigir checkout válido y de contar 'Guarantee'

Mantenimientos completados (fable): 221,703. Sin EffectiveCheckoutDate: 0 (0.0%); checkout anterior a la fecha del turno: 1 (0.0%). Astra los descarta como 'finalización no acreditada': pierde 1 eventos (0.0%) como anclas y como retornos.
Turnos concluidos con ítem ServiceType=Mantenimiento pero SIN número de service (sólo 'Guarantee'/'Contactless'): 3,808. Astra los cuenta como mantenimiento; fable no (son reparaciones en garantía).
Mantenimientos 'estrictos' de astra (maintenance & valid_complete): 225,479 vs 220,522 de fable.

## F. Solapamiento de poblaciones

Vehículos con al menos una ventana: astra 77,973, fable 92,326, en común 76,713.
Abr-jul 2026: vehículos con vencimiento en astra 23,281 vs con vencimiento en fable 34,328; en común 17,850.
Diferencia de vencimiento estimado (fable − astra) para el mismo vehículo, abr-jul 2026: mediana -1 días, p25 -24, p75 11 (n=21,277; merge por vehicle_id, cruza ventanas de anclas distintas cuando un vehículo tiene más de una en el período). Astra usa 16.000 km (P703) y ritmo reciente; fable 16.000 km (config/params.json) y tasa acumulada.