# Desafío 1 — Retención de service / propensión de recompra (Ford Innovation Challenge III)

Predicción, para cada usuario–vehículo Ranger que entra en su ventana de mantenimiento, de la probabilidad de **no
completar el próximo mantenimiento programado en la red oficial** (churn de service), con ranking priorizado,
segmentos accionables y explicación por vehículo. Definición oficial en la ficha técnica de Ford; lectura completa en
`docs/00_lectura_del_desafio.md`.

## Cómo correr todo

Atajo en Windows: doble clic en `ejecutar.bat` (menú) o `ejecutar.bat pipeline|notebooks|informe|diccionario|dashboard|todo` desde una consola. Requiere el `.venv` del paso 1.

```bash
# 1) entorno (una vez)
uv venv --python 3.12 .venv && uv pip install --python .venv/Scripts/python.exe -r requirements.txt

# 2) pipeline completo: CSV crudos -> parquet -> ventanas -> features -> modelo -> scoring actual -> figuras
PYTHONIOENCODING=utf8 PYTHONPATH=src .venv/Scripts/python.exe scripts/run_pipeline.py

# 3) análisis complementarios
PYTHONIOENCODING=utf8 PYTHONPATH=src .venv/Scripts/python.exe scripts/sensibilidad_ventana.py   # parámetros de ventana
PYTHONIOENCODING=utf8 PYTHONPATH=src .venv/Scripts/python.exe scripts/ablaciones.py             # robustez y leakage
PYTHONIOENCODING=utf8 PYTHONPATH=src .venv/Scripts/python.exe scripts/eda/01_taxonomia_target.py  # (idem 02..06)

# 4) notebooks de evidencia (se generan y ejecutan desde el pipeline)
PYTHONIOENCODING=utf8 PYTHONPATH=src .venv/Scripts/python.exe scripts/build_notebooks.py

# 5) dashboard
PYTHONPATH=src .venv/Scripts/python.exe -m streamlit run app/app.py

# 6) informe oficial: docx sobre el template de Ford + PDF (usa Word instalado para actualizar el índice y exportar)
PYTHONIOENCODING=utf8 .venv/Scripts/python.exe scripts/build_informe_docx.py
# (versión larga en markdown → PDF, sin template): .venv/Scripts/python.exe scripts/build_pdf.py docs/informe_final.md reports/informe_final_md.pdf
```

Los datos crudos viven en la carpeta compartida `G:\SIMtec\Dataset` y son **solo lectura** (`src/repurchase/config.py`).
Todo lo generado queda en `data/` (fuera de git), `reports/` y `docs/`.

## Estructura

| Carpeta | Qué hay |
|---|---|
| `src/repurchase/` | `io` (carga y tipado), `eventos` (agenda a nivel turno + evento objetivo), `ventanas` (población–ventana–target), `features` (as-of, sin leakage), `modelo` (split temporal, LightGBM, calibración), `evaluacion` (lift, recall a capacidad, calibración), `explicabilidad` (SHAP), `negocio` (segmentos, ROI), `graficos` |
| `scripts/` | `run_pipeline.py` (todo), `sensibilidad_ventana.py`, `ablaciones.py`, `build_notebooks.py`, `build_informe_docx.py` (informe sobre el template oficial), `diccionario_dataset.py`, `build_pdf.py`, `eda/` (seis análisis reproducibles + verificaciones), `revision_cruzada/` (reconciliación de definiciones y comparación con la otra solución) |
| `config/` | `params.json` (ventana, split, segmentos), `negocio.json` (supuestos de ROI) |
| `reports/` | `eda/` (informes + tablas), `modelo/` (resumen de la corrida, ROI, sensibilidad, ablaciones), `revision_cruzada/` (evidencia de la segunda vuelta), `figures/` |
| `docs/` | `00_lectura_del_desafio.md`, `01_hallazgos_eda.md`, `02_decisiones_y_descartes.md`, `03_pitch_trials_day.md`, `04_revision_cruzada.md` (comparación con la solución de `G:\SIMtec-astra`), `diccionario_dataset_analitico.md` (columna por columna del dataset analítico y del ranking), `informe_final.md` |
| `notebooks/` | `01_eda`, `02_target_y_ventanas`, `03_modelo` (ejecutados) |
| `app/` | dashboard Streamlit (bandeja de contacto priorizada, ficha por vehículo, vista por usuario y por concesionario) |
| `data/` | `interim/` parquet tipados, `processed/` ventanas, dataset analítico y scores actuales, `models/` artefactos (no se versiona) |

## Regla del repo

Ninguna IA hace `git add`, `git commit` ni `git push`. Los commits los hace una persona del equipo.
