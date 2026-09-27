"""Sensibilidad de la definición de ventana/target a sus parámetros.

Para cada combinación de parámetros reporta: ventanas evaluables, tasa de churn, % de ventanas "preempted"
(el vehículo volvió antes de que abriera la ventana: señal de que la regla vence demasiado tarde), % de
ventanas donde manda el piso (señal de que la regla de km vence demasiado temprano), y, para quienes
vuelven dentro de 18 meses del ancla, qué % de esos retornos cae dentro del horizonte (captura).
Opcionalmente entrena un LightGBM rápido para ver la estabilidad del poder predictivo (NO se elige el
target por AUC: eso sería circular; se reporta solo como control).

Uso: PYTHONIOENCODING=utf8 PYTHONPATH=src .venv/Scripts/python.exe scripts/sensibilidad_ventana.py [--train]
"""
from __future__ import annotations

import argparse
import itertools
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from repurchase import config  # noqa: E402
from repurchase.eventos import appointments  # noqa: E402
from repurchase.io import load_sales  # noqa: E402
from repurchase.ventanas import WindowParams, build_windows  # noqa: E402

K_GEN = (("RANGER (P703)", 16000.0), ("RANGER RAPTOR (P703)", 16000.0), ("RANGER (P375)", 10000.0), ("RANGER RAPTOR", 10000.0))  # oficial Ford AR
K_15 = (("RANGER (P703)", 15000.0), ("RANGER RAPTOR (P703)", 15000.0), ("RANGER (P375)", 10000.0))  # la hipótesis inicial del EDA (15k P703)
K_10 = (("RANGER (P703)", 16000.0), ("RANGER RAPTOR (P703)", 16000.0), ("RANGER (P375)", 16000.0))  # 16k para todo el parque
K_TIME = (("RANGER (P703)", 1e9), ("RANGER RAPTOR (P703)", 1e9), ("RANGER (P375)", 1e9), ("RANGER RAPTOR", 1e9))  # solo tope anual
GRID = {
    "km_by_generation": [K_GEN, K_15, K_10, K_TIME],
    "lead_days": [30, 60],
    "horizon_days": [60, 90, 120, 180],
    "first_due_days": [300],
    "anchor": ["last_maintenance"],
}
EXTRA = [  # variantes puntuales fuera de la grilla
    dict(km_by_generation=K_GEN, lead_days=30, horizon_days=90, label_mode="mes_calendario", label_margin_days=0),  # definición astra
    dict(km_by_generation=K_GEN, lead_days=30, horizon_days=90, first_due_days=270),
    dict(km_by_generation=K_GEN, lead_days=30, horizon_days=90, first_due_days=365),
    dict(km_by_generation=K_GEN, lead_days=30, horizon_days=90, anchor="plan"),
    dict(km_by_generation=K_GEN, lead_days=30, horizon_days=90, km_source="km"),  # ablacion: KM snapshot (leakage)
]


def resumen(w: pd.DataFrame, p: WindowParams) -> dict:
    ev = w[w["status"] == "evaluable"]
    n_all = (w["status"] != "fuera_de_rango").sum()
    # captura: entre ventanas con retorno observable dentro de 18 meses del ancla (evaluables + preempted con
    # next_maint), qué fracción de retornos cae en (scoring, horizon_end]
    cand = w[w["status"].isin(["evaluable", "preempted"]) & w["next_maint_date"].notna()].copy()
    cand = cand[(cand["next_maint_date"] - cand["anchor_date"]).dt.days <= 548]
    in_h = (cand["next_maint_date"] > cand["scoring_date"]) & (cand["next_maint_date"] <= cand["horizon_end"])
    d = p.to_dict(); d["km_by_generation"] = "|".join(f"{k.split()[-1]}={int(v)}" for k, v in d["km_by_generation"].items())
    return {**d, "n_evaluables": len(ev), "churn_rate": ev["label_churn"].mean(),
            "pct_preempted": (w["status"] == "preempted").sum() / max(n_all, 1),
            "pct_piso": (ev["binding_rule"] == "piso").mean(), "pct_km": (ev["binding_rule"] == "km").mean(),
            "captura_retornos_18m": in_h.mean(), "n_retornos_18m": len(cand),
            "mediana_dias_retorno_vs_due": ev.loc[ev["label_churn"] == 0, "days_next_vs_due"].median()}


def quick_auc(w: pd.DataFrame, appt, sales) -> dict:
    import lightgbm as lgb
    from sklearn.metrics import average_precision_score, roc_auc_score
    from repurchase.features import build_features
    from repurchase.modelo import LABEL, SplitConfig, feature_columns, prepare_matrix, temporal_split
    ev = w[w["status"] == "evaluable"]
    f = build_features(ev, appt, sales).merge(ev[["window_id", LABEL]], on="window_id")
    tr, va, te = temporal_split(f, SplitConfig())
    cols = feature_columns(f)
    Xtr, cats = prepare_matrix(f.loc[tr], cols); Xte, _ = prepare_matrix(f.loc[te], cols, cats)
    b = lgb.train(dict(objective="binary", learning_rate=0.05, num_leaves=63, min_data_in_leaf=200, verbose=-1,
                       feature_fraction=0.8, seed=1, num_threads=8), lgb.Dataset(Xtr, f.loc[tr, LABEL]), 400)
    p = b.predict(Xte)
    return {"auc_test": roc_auc_score(f.loc[te, LABEL], p), "pr_auc_test": average_precision_score(f.loc[te, LABEL], p),
            "n_test": int(te.sum())}


def main(train: bool):
    appt = appointments(); sales = load_sales()
    rows = []
    keys = list(GRID)
    combos = [dict(zip(keys, vals)) for vals in itertools.product(*GRID.values())] + EXTRA
    for kw in combos:
        p = WindowParams(**kw)
        t0 = time.time()
        w = build_windows(appt, sales, p)
        r = resumen(w, p)
        if train:
            r.update(quick_auc(w, appt, sales))
        r["seg"] = round(time.time() - t0, 1)
        rows.append(r)
        print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items()}, flush=True)
    out = pd.DataFrame(rows)
    out_path = config.REPORTS_DIR / "modelo" / "sensibilidad_ventana.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False)
    print("guardado en", out_path)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--train", action="store_true")
    main(ap.parse_args().train)
