"""Ablaciones para la defensa: ¿qué pasa con el desempeño fuera de tiempo si...?

- se sacan las categóricas de alta cardinalidad (concesionario, versión TMA)?  -> robustez / no sobreajuste
- se incluye ConnectedStatusARG (foto a la extracción)?                       -> cuánto "ayuda" un leakage suave
- se usa la columna KM (foto por vehículo) como km del evento?                -> demostrar el leakage detectado en el EDA
- se sacan todas las features de ventas (sólo agenda)?                        -> qué aporta cruzar con ventas
- sólo primer service / sólo services siguientes                              -> desempeño por tipo de ventana
Guarda reports/modelo/ablaciones.csv y .md. Uso: PYTHONIOENCODING=utf8 PYTHONPATH=src .venv/Scripts/python.exe scripts/ablaciones.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from repurchase import config  # noqa: E402
from repurchase.eventos import appointments  # noqa: E402
from repurchase.features import build_features  # noqa: E402
from repurchase.io import load_sales  # noqa: E402
from repurchase.modelo import LABEL, SplitConfig, run_training  # noqa: E402
from repurchase.ventanas import WindowParams, build_windows  # noqa: E402

SALES_COLS = ["in_sales", "person_type", "business_unit", "sales_channel", "sales_state", "is_buyer",
              "same_dealer_as_sale", "fleet_size_sales"]
HIGH_CARD = ["last_maint_dealer", "tma", "sales_state"]


def metrics_row(name, res, note=""):
    m = res["metrics"].loc["LightGBM calibrado (isotónica)"]
    cap = res["tables"]["LightGBM calibrado (isotónica)"]["capacity"]
    r20 = cap.loc[cap["capacidad_pct"] == 0.2, "recall"].iloc[0]
    return {"variante": name, "n_test": int(m["n"]), "churn_test": round(m["base_rate"], 3), "roc_auc": round(m["roc_auc"], 4),
            "pr_auc": round(m["pr_auc"], 4), "ece": round(m["ece"], 4), "recall_top20": round(r20, 3),
            "n_features": res["info"]["n_features"], "nota": note}


def main():
    cfg = json.loads((config.PROJECT_DIR / "config/params.json").read_text(encoding="utf8"))
    split = SplitConfig(**cfg["split"])
    data = pd.read_parquet(config.PROCESSED_DIR / "dataset_analitico.parquet")
    out = config.MODELS_DIR / "ablaciones"
    rows = []

    base = run_training(data, split, out_dir=out / "base", exclude_snapshot=True)
    rows.append(metrics_row("base (pipeline)", base, "features completas, sin ConnectedStatus"))

    d = data.drop(columns=[c for c in HIGH_CARD if c in data.columns])
    rows.append(metrics_row("sin concesionario / versión / provincia", run_training(d, split, out_dir=out / "sin_altacard"),
                            "robustez: sin categóricas de alta cardinalidad"))

    rows.append(metrics_row("con ConnectedStatusARG (snapshot)", run_training(data, split, out_dir=out / "con_snapshot", exclude_snapshot=False),
                            "leakage suave: estado de conectividad a la fecha de extracción"))

    d = data.drop(columns=[c for c in SALES_COLS if c in data.columns])
    rows.append(metrics_row("sólo agenda (sin features de ventas)", run_training(d, split, out_dir=out / "solo_agenda"),
                            "qué aporta cruzar con la base de ventas"))

    d = data[data["months_observable"] >= 6]
    rows.append(metrics_row("exige ≥ 6 meses de historia observable", run_training(d, split, out_dir=out / "hist6m"),
                            "mitigación de la censura a la izquierda (EDA 05): descarta ventanas con historia corta"))

    d = data.drop(columns=[c for c in ["n_surveys", "min_rating", "last_rating", "mean_rating", "days_since_last_survey"] if c in data.columns])
    rows.append(metrics_row("sin encuestas", run_training(d, split, out_dir=out / "sin_encuesta"),
                            "EDA 06: la encuesta es previa al turno y sin señal"))

    for kind, name in [("warranty", "sólo primer service"), ("maintenance", "sólo services siguientes")]:
        d = data[data["anchor_type"] == kind]
        rows.append(metrics_row(name, run_training(d, split, out_dir=out / f"solo_{kind}"), "modelo entrenado y evaluado sólo en ese tipo de ventana"))

    # Demostración del leakage: km del evento tomado de la columna KM (foto por vehículo)
    appt = appointments(); sales = load_sales()
    p_leak = WindowParams.from_dict({**cfg["ventana"], "km_source": "km"})
    w = build_windows(appt, sales, p_leak)
    ev = w[w["status"] == "evaluable"]
    f = build_features(ev, appt, sales).merge(ev[["window_id", LABEL]], on="window_id")
    # build_features usa VehicleCurrentKM siempre; para la ablación reemplazamos las features de km por la foto
    km_snap = appt.dropna(subset=["vehicle_id"]).groupby("vehicle_id")["KM"].first()
    f["last_km"] = f["vehicle_id"].map(km_snap)
    f["last_maint_km"] = f["last_km"]
    rows.append(metrics_row("LEAKAGE: columna KM como km del evento", run_training(f, split, out_dir=out / "leak_km"),
                            "ventanas y features con la foto de km a la extracción: AUC inflado artificialmente"))

    df = pd.DataFrame(rows)
    (config.REPORTS_DIR / "modelo").mkdir(parents=True, exist_ok=True)
    df.to_csv(config.REPORTS_DIR / "modelo" / "ablaciones.csv", index=False)
    (config.REPORTS_DIR / "modelo" / "ablaciones.md").write_text("# Ablaciones (test fuera de tiempo, LightGBM calibrado)\n\n" + df.to_markdown(index=False) + "\n", encoding="utf8")
    print(df.to_string())


if __name__ == "__main__":
    main()
