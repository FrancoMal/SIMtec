"""Genera y ejecuta los notebooks de evidencia técnica a partir del pipeline (src/repurchase).

Los notebooks son la "vista narrativa" del código de src/: no duplican lógica, la llaman. Se ejecutan con
nbconvert para que queden con outputs y puedan abrirse sin correr nada.

Uso: PYTHONIOENCODING=utf8 PYTHONPATH=src .venv/Scripts/python.exe scripts/build_notebooks.py [--no-execute]
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
NB_DIR = ROOT / "notebooks"
PY = sys.executable

SETUP = '''import sys, json, warnings
from pathlib import Path
warnings.filterwarnings("ignore")
ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
sys.path.insert(0, str(ROOT / "src"))
import numpy as np, pandas as pd
pd.set_option("display.width", 200); pd.set_option("display.max_columns", 60)
from IPython.display import Image, Markdown, display
from repurchase import config
from repurchase.eventos import appointments, CUTOFF
from repurchase.io import load_sales, load_agenda
print("cutoff de datos:", CUTOFF.date())'''


def md(text):
    return nbf.v4.new_markdown_cell(text.strip())


def code(text):
    return nbf.v4.new_code_cell(text.strip())


def fig(rel, caption=""):
    return code(f'display(Image(filename=str(ROOT / "{rel}"), width=900)); display(Markdown("*{caption}*"))')


def nb_01_eda():
    cells = [
        md("""# 01 — Datos y hallazgos del análisis exploratorio

Extractos seudonimizados de Ford Argentina: **ventas Ranger 2024-2026** (`ranger_sales_arg_2024_2026.csv`, una fila por
vehículo vendido) y **Agenda Ford 2024-2026** (`ranger_service_agenda_arg_2024_2026 1.csv`, una fila por ítem de servicio
dentro de un turno, todo el parque Ranger). Los datos crudos son solo lectura; acá se leen los parquet tipados de
`data/interim/` (generados por `src/repurchase/io.py`).

El análisis completo, con scripts reproducibles y verificación independiente, está en `reports/eda/` y en
`docs/01_hallazgos_eda.md`. Este notebook muestra lo esencial."""),
        code(SETUP),
        md("## 1. Tamaño y grano de las tablas"),
        code('''sales = load_sales(); agenda = load_agenda(); appt = appointments(agenda)
print(f"ventas: {len(sales):,} vehículos, {sales.customer_id.nunique():,} clientes, {sales.SalesDate.min().date()} → {sales.SalesDate.max().date()}")
print(f"agenda: {len(agenda):,} ítems, {appt.shape[0]:,} turnos, {agenda.vehicle_id.nunique():,} vehículos, {agenda.dealer_id.nunique()} concesionarios")
print("estado de los turnos:"); display(appt.StatusARG.value_counts().to_frame("turnos"))
print("mantenimientos programados completados:", int(appt.is_completed_maintenance.sum()))'''),
        md("## 2. La regla de mantenimiento real: por kilómetros y distinta por generación"),
        fig("reports/figures/eda/02_cadencia_ventana_box_km_por_service.png",
            "Km al n-ésimo service: P703 sigue 15.000 × n; P375 sigue 10.000 × n. El plan es por km, no anual."),
        fig("reports/figures/eda/02_cadencia_ventana_hist_intervalos.png",
            "Días y km entre mantenimientos consecutivos: mediana 161 días; km bimodal (10.300 P375 / 16.200 P703)."),
        md("## 3. La columna `KM` es una foto por vehículo, no el km del turno (leakage)"),
        code('''g = agenda.groupby("vehicle_id").agg(km_unicos=("KM", "nunique"), vck_unicos=("VehicleCurrentKM", "nunique"), turnos=("schedule_id", "nunique"))
print("vehículos con un único valor de KM en todos sus turnos:", f"{(g.km_unicos <= 1).mean():.2%}")
print("vehículos con ≥2 turnos y más de un VehicleCurrentKM:", f"{(g[g.turnos >= 2].vck_unicos > 1).mean():.2%}")'''),
        md("## 4. Retención por edad del vehículo y tasa base de churn"),
        fig("reports/figures/eda/03_retencion_churn_curva_edad.png", "Curva de retención por año de vida del vehículo."),
        md("## 5. Cohorte de ventas 2024: primer service"),
        fig("reports/figures/eda/02_cadencia_ventana_cohorte2024_curvas.png",
            "64,5 % hizo el 1° service en la red dentro de 12 meses; 80,9 % en 18. El mayor churn está en la primera ventana."),
        md("## 6. Sensibilidad de la ventana"),
        fig("reports/figures/eda/02_cadencia_ventana_ventana_retraso_sensibilidad.png",
            "Retraso real del retorno respecto del vencimiento estimado, según regla. La regla 'solo tiempo' queda 200 días tarde."),
    ]
    return cells


def nb_02_target():
    cells = [
        md("""# 02 — Población, ventana y target (definición reproducible)

**Unidad:** usuario–vehículo–ventana. **Ancla:** cada mantenimiento programado completado en la red (o el inicio de garantía
para el primer service). **Vencimiento:** `due = ancla + min(365 días, K_gen / tasa_uso)` con K = 15.000 km (P703) /
10.000 km (P375) y tasa de uso = km al ancla / edad del vehículo. **Apertura de ventana y scoring:** `due − 30 días`.
**Horizonte:** `due + 90 días`. **Target:** `churn = 1` si no hay mantenimiento programado completado entre la apertura y el
cierre del horizonte. Ventanas cuyo horizonte no cerró antes del cutoff quedan **censuradas** (no se usan para entrenar;
son la población a scorear hoy). Implementación: `src/repurchase/ventanas.py`; parámetros: `config/params.json`."""),
        code(SETUP),
        code('''from repurchase.ventanas import WindowParams, build_windows
cfg = json.loads((ROOT / "config/params.json").read_text(encoding="utf8"))
params = WindowParams.from_dict(cfg["ventana"]); print(params.to_dict())
win = build_windows(params=params)
display(win.status.value_counts().to_frame("ventanas"))'''),
        md("""Estados: `evaluable` (label conocido), `censurada` (horizonte abierto al cutoff), `preempted` (el vehículo volvió antes
de que abriera la ventana: nunca estuvo en ventana, no se scorea), `fuera_de_rango` (scoring antes de 2024), `futura`
(scoring después del cutoff)."""),
        code('''ev = win[win.status == "evaluable"]
print(f"ventanas evaluables: {len(ev):,}   vehículos: {ev.vehicle_id.nunique():,}   churn: {ev.label_churn.mean():.1%}")
display(ev.groupby(ev.scoring_date.dt.to_period("Q")).label_churn.agg(["size", "mean"]).rename(columns={"size": "ventanas", "mean": "churn"}))
display(ev.groupby("binding_rule").label_churn.agg(["size", "mean"]).rename(columns={"size": "ventanas", "mean": "churn"}))
display(ev.groupby("anchor_type").label_churn.agg(["size", "mean"]).rename(columns={"size": "ventanas", "mean": "churn"}))'''),
        md("## Chequeo anti-leakage: nada posterior al scoring entra como feature"),
        code('''from repurchase.features import build_features
f = build_features(ev.sample(20000, random_state=0))
# Todas las recencias son positivas: el último evento usado es estrictamente anterior al scoring.
chk = {c: int((f[c] <= 0).sum()) for c in ["days_since_last_appt", "days_since_last_maint", "days_since_last_visit", "days_since_last_survey"]}
print("features de recencia con valor <= 0 (debe ser 0 en todas):", chk)
print("ventanas donde la primera lectura de km posterior al scoring se filtró: 0 por construcción (merge_asof backward estricto)")'''),
        md("## Sensibilidad de la definición a sus parámetros"),
        code('''p = ROOT / "reports/modelo/sensibilidad_ventana.csv"
if p.exists():
    s = pd.read_csv(p)
    display(s[["km_by_generation", "lead_days", "horizon_days", "first_due_days", "anchor", "km_source", "n_evaluables", "churn_rate", "pct_preempted", "pct_piso", "captura_retornos_18m", "mediana_dias_retorno_vs_due"]].round(3))
else:
    print("correr scripts/sensibilidad_ventana.py")'''),
    ]
    return cells


def nb_03_modelo():
    cells = [
        md("""# 03 — Modelo, validación temporal, calibración y explicabilidad

Pipeline: `scripts/run_pipeline.py` → `src/repurchase/modelo.py`. Split **temporal** por fecha de scoring: entrenamiento
con ventanas abiertas hasta `train_end`, calibración (isotónica) en el período siguiente, evaluación en ventanas
posteriores cuyo horizonte cerró antes del cutoff. Baselines: azar (prioridad uniforme = situación actual), heurística de
reglas y regresión logística."""),
        code(SETUP),
        code('''from repurchase.modelo import LABEL, SplitConfig, run_training
data = pd.read_parquet(config.PROCESSED_DIR / "dataset_analitico.parquet")
cfg = json.loads((ROOT / "config/params.json").read_text(encoding="utf8"))
print("dataset analítico:", data.shape)
res = run_training(data, SplitConfig(**cfg["split"]), out_dir=config.MODELS_DIR / "notebook_run", exclude_snapshot=cfg["modelo"]["exclude_snapshot"])
display(res["metrics"].round(4))
print(json.dumps({k: v for k, v in res["info"].items() if k != "lgb_params"}, indent=2, ensure_ascii=False))'''),
        md("## Curva de ganancia, lift por decil, calibración"),
        fig("reports/figures/modelo/ganancia.png", "Contactando al 20 % de mayor score se captura ~36 % de los churners (vs 20 % al azar)."),
        fig("reports/figures/modelo/lift_deciles.png", "Tasa de churn observada por decil de score en test."),
        fig("reports/figures/modelo/calibracion.png", "La probabilidad declarada coincide con la tasa observada."),
        code('''display(res["tables"]["LightGBM calibrado (isotónica)"]["capacity"].round(3))
display(res["tables"]["LightGBM calibrado (isotónica)"]["lift"].round(3))'''),
        md("## Qué explica el riesgo (SHAP global) y por qué cada vehículo (SHAP local)"),
        fig("reports/figures/modelo/shap_global.png", "Importancia media |SHAP| en test."),
        code('''from repurchase.explicabilidad import shap_values, local_drivers, global_importance
X = res["X_test"].iloc[:3000]
sv = shap_values(res["booster"], X)
display(global_importance(sv, X).head(15)[["nombre", "mean_abs_shap"]])
drv = local_drivers(sv, X)
ejemplo = pd.concat([res["test_scored"].iloc[:3000][["vehicle_id", "p_lgbm_cal", LABEL]].reset_index(drop=True), drv[["driver_1", "driver_2", "driver_3"]].reset_index(drop=True)], axis=1)
display(ejemplo.sort_values("p_lgbm_cal", ascending=False).head(10))'''),
        md("## Desempeño por subgrupo (generación, primer service vs. siguientes)"),
        code('''from sklearn.metrics import roc_auc_score, average_precision_score
te = data.loc[res["masks"][2]].reset_index(drop=True).copy(); te["p"] = res["test_scored"]["p_lgbm_cal"].values
rows = []
for col in ["generation", "anchor_type", "business_unit", "person_type"]:
    for k, g in te.groupby(col, dropna=False):
        if len(g) >= 500 and g[LABEL].nunique() == 2:
            rows.append({"grupo": f"{col} = {k}", "n": len(g), "churn": g[LABEL].mean(), "roc_auc": roc_auc_score(g[LABEL], g.p), "pr_auc": average_precision_score(g[LABEL], g.p)})
display(pd.DataFrame(rows).round(3))'''),
        md("## Segmentos accionables y ROI (supuestos explícitos en `config/negocio.json`)"),
        code('''display(pd.read_csv(ROOT / "reports/modelo/segmentos_test.csv").round(3))
display(pd.read_csv(ROOT / "reports/modelo/roi_por_capacidad.csv").round(2))'''),
    ]
    return cells


def write(nb_name, cells):
    nb = nbf.v4.new_notebook(); nb["cells"] = cells
    nb["metadata"]["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    path = NB_DIR / nb_name
    nbf.write(nb, path)
    return path


def main(execute: bool):
    NB_DIR.mkdir(exist_ok=True)
    paths = [write("01_eda.ipynb", nb_01_eda()), write("02_target_y_ventanas.ipynb", nb_02_target()),
             write("03_modelo.ipynb", nb_03_modelo())]
    if execute:
        for p in paths:
            print("ejecutando", p.name, flush=True)
            subprocess.run([PY, "-m", "jupyter", "nbconvert", "--to", "notebook", "--execute", "--inplace",
                            "--ExecutePreprocessor.timeout=1800", str(p)], check=True, cwd=str(NB_DIR))
    print("listo:", [p.name for p in paths])


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--no-execute", action="store_true")
    main(not ap.parse_args().no_execute)
