# Estructura de carpetas sugerida

Propuesta de organización para el repo, pensada para el desafío **Repurchase Propensity**
(clasificación / scoring sobre datos tabulares de clientes). Es solo una sugerencia: el equipo
decide si la adopta tal cual o la ajusta.

```
SIMtec/
├── Reglamento FIC 3_v3.pdf              # se deja como está
├── Resumen Desafios FIC_3 - AI Edition.pdf  # se deja como está
├── Calendario FIC III.jpg               # se deja como está
├── Status.md                            # bitácora del proyecto (no se borra nunca)
├── ESTRUCTURA.md                        # este archivo
├── .gitignore
│
└── desafio-1-repurchase-propensity/
    ├── SPEC.md                          # enfoque técnico ya definido (se deja como está)
    │
    ├── data/                            # NO se versiona (ver .gitignore) — datos que mande Ford
    │   ├── raw/                         # datos originales, sin tocar
    │   └── processed/                   # datasets limpios / con features, listos para modelar
    │
    ├── notebooks/                       # exploración y prototipado
    │   ├── 01_eda.ipynb
    │   ├── 02_features.ipynb
    │   └── 03_modelado.ipynb
    │
    ├── src/                             # código reutilizable, importable desde notebooks o scripts
    │   ├── data/                        # carga y limpieza de datos
    │   ├── features/                    # feature engineering (RFM, ciclo de vida del vehículo, etc.)
    │   ├── models/                      # entrenamiento, calibración, inferencia
    │   └── evaluation/                  # métricas, curva de lift, SHAP
    │
    ├── app/                             # demo Streamlit (bandeja de clientes priorizados)
    │
    ├── reports/                         # figuras, gráficos y el PDF final del entregable
    │   └── figures/
    │
    ├── requirements.txt
    └── train.py                         # pipeline baseline end-to-end (CSV → modelo → métricas)
```

## Por qué esta organización

- **`data/` fuera de git**: los datasets que entrega Ford no se versionan (ya está contemplado en
  `.gitignore`). Cada uno los coloca localmente en `data/raw/`.
- **`notebooks/` vs `src/`**: los notebooks son para explorar y mostrar resultados; todo lo que se
  reutilice (features, funciones de entrenamiento) se migra a `src/` para no duplicar código entre
  notebooks.
- **`app/`**: separado porque es el demo/producto final (Streamlit), no parte del pipeline de
  modelado.
- **`reports/`**: todo lo visual y el documento final que se entrega el 25/9, en un solo lugar.

## Cómo aplicarla

Este archivo describe la estructura sugerida; las carpetas dentro de
`desafio-1-repurchase-propensity/` todavía no están creadas (no tiene sentido crear `data/` o
`notebooks/` vacíos hasta que arranquemos con el dataset). Cuando el equipo lo confirme, se
scaffoldean con archivos `.gitkeep` donde haga falta.
