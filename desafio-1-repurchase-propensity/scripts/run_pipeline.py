"""Pipeline de punta a punta: CSV crudos -> ventanas -> features -> modelo -> scoring actual -> figuras.

Uso (desde la carpeta del proyecto):
    PYTHONIOENCODING=utf8 PYTHONPATH=src .venv/Scripts/python.exe scripts/run_pipeline.py [--config config/params.json]
Salidas:
    data/processed/ventanas.parquet, dataset_analitico.parquet, scores_actuales.parquet/.csv
    data/models/*  (modelo, calibrador, métricas, tablas)
    reports/figures/modelo/*.png, reports/modelo/resumen.md
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from repurchase import config  # noqa: E402
from repurchase.eventos import CUTOFF, appointments  # noqa: E402
from repurchase.evaluacion import precision_recall_points, recall_at_monthly_capacity  # noqa: E402
from repurchase.explicabilidad import global_importance, local_drivers, nombre, shap_values  # noqa: E402
from repurchase.features import build_features  # noqa: E402
from repurchase.graficos import (calibration_chart, gains_chart, importance_chart, lift_chart,  # noqa: E402
                                 monthly_volume_chart, pr_chart, segment_chart)
from repurchase.io import load_sales  # noqa: E402
from repurchase.modelo import LABEL, SplitConfig, prepare_matrix, run_training  # noqa: E402
from repurchase.negocio import (resumen_segmentos, roi_por_capacidad, segmentar_por_capacidad,  # noqa: E402
                                sensibilidad_roi, umbral_rentable)
from repurchase.ventanas import WindowParams, build_windows  # noqa: E402

FIG = config.FIGURES_DIR / "modelo"
REP = config.REPORTS_DIR / "modelo"


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def main(cfg_path: str, negocio_path: str, skip_train: bool):
    cfg = json.loads(Path(cfg_path).read_text(encoding="utf8"))
    neg = json.loads(Path(negocio_path).read_text(encoding="utf8"))
    params = WindowParams.from_dict(cfg["ventana"])
    split = SplitConfig(**cfg["split"])
    FIG.mkdir(parents=True, exist_ok=True); REP.mkdir(parents=True, exist_ok=True)

    log(f"parámetros de ventana: {params.to_dict()}")
    appt = appointments(); sales = load_sales()
    win = build_windows(appt, sales, params)
    win.to_parquet(config.PROCESSED_DIR / "ventanas.parquet", index=False)
    log("ventanas por estado:\n" + win["status"].value_counts().to_string())

    # Población a scorear HOY: en ventana ahora sin mantenimiento todavía, o que entra en ventana en los
    # próximos N días. Para éstas las features se calculan con toda la información disponible al CUTOFF.
    fwd = int(cfg["scoring_actual"]["dias_hacia_adelante"])
    hoy = win[(win["status"] == "censurada") & (win["next_maint_date"].isna())].copy()
    prox = win[(win["status"] == "futura") & (win["scoring_date"] <= CUTOFF + pd.Timedelta(days=fwd))].copy()
    prox["scoring_date_original"] = prox["scoring_date"]
    prox["scoring_date"] = CUTOFF + pd.Timedelta(days=1)  # features as-of hoy
    hoy["scoring_date_original"] = hoy["scoring_date"]
    actual = pd.concat([hoy, prox], ignore_index=True)
    actual["poblacion_actual"] = np.where(actual["window_id"].isin(hoy["window_id"]), "en_ventana", "entra_en_30_dias")
    actual = actual.drop_duplicates("vehicle_id", keep="first")  # un vehículo, una fila

    ev = win[win["status"] == "evaluable"].copy()
    log(f"ventanas evaluables: {len(ev):,}  churn: {ev[LABEL].mean():.3f}   población actual: {len(actual):,}")

    log("features (evaluables)…")
    feat = build_features(ev, appt, sales)
    data = feat.merge(ev[["window_id", LABEL, "label_no_visit", "status", "window_n"]], on="window_id", how="left")
    data.to_parquet(config.PROCESSED_DIR / "dataset_analitico.parquet", index=False)
    log(f"dataset analítico: {data.shape}")

    log("features (población actual)…")
    feat_act = build_features(actual, appt, sales)
    feat_act = feat_act.merge(actual[["window_id", "poblacion_actual", "scoring_date_original", "horizon_end",
                                      "due_date"]].rename(columns={"due_date": "due_date_w"}), on="window_id", how="left")

    if skip_train:
        log("skip_train: no se reentrena"); return
    log("entrenamiento + evaluación temporal…")
    res = run_training(data, split, exclude_snapshot=cfg["modelo"]["exclude_snapshot"], lgb_params=cfg["modelo"]["lgb_params"])
    metrics = res["metrics"]; tables = res["tables"]
    log("métricas test:\n" + metrics.round(4).to_string())

    # ---------- figuras de evaluación ----------
    main_name = "LightGBM calibrado (isotónica)"
    gains_chart({k: v["gains"] for k, v in tables.items() if not k.startswith("azar")}, FIG / "ganancia.png", highlight=main_name)
    lift_chart(tables[main_name]["lift"], FIG / "lift_deciles.png")
    calibration_chart({"LightGBM sin calibrar": tables["LightGBM sin calibrar"]["calibration"],
                       "LightGBM calibrado": tables[main_name]["calibration"]}, FIG / "calibracion.png")
    yte = res["y_test"]; ts = res["test_scored"]
    pr_chart({"LightGBM calibrado": precision_recall_points(yte, ts["p_lgbm_cal"].values),
              "regresión logística": precision_recall_points(yte, ts["p_logreg"].values)}, float(yte.mean()), FIG / "precision_recall.png")

    # ---------- SHAP ----------
    log("SHAP…")
    Xte = res["X_test"]
    rng = np.random.default_rng(1)
    idx = rng.choice(len(Xte), size=min(8000, len(Xte)), replace=False)
    sv = shap_values(res["booster"], Xte.iloc[idx])
    imp = global_importance(sv, Xte.iloc[idx])
    imp.to_csv(config.MODELS_DIR / "shap_global.csv", index=False)
    importance_chart(imp, FIG / "shap_global.png", names={f: nombre(f) for f in imp["feature"]})
    drv = local_drivers(sv, Xte.iloc[idx])
    ejemplo = pd.concat([ts.iloc[idx][["window_id", "vehicle_id", "scoring_date", LABEL, "p_lgbm_cal"]].reset_index(drop=True),
                         drv.reset_index(drop=True)], axis=1)
    ejemplo.to_parquet(config.MODELS_DIR / "test_drivers_muestra.parquet", index=False)

    # ---------- segmentos y ROI en test (churners observados) ----------
    ts = ts.copy(); ts["p"] = ts["p_lgbm_cal"]
    ts["segmento"] = segmentar_por_capacidad(ts["p"], cfg["segmentos"]["top_alto"], cfg["segmentos"]["top_medio"])
    seg = resumen_segmentos(ts)
    seg.to_csv(REP / "segmentos_test.csv", index=False)
    segment_chart(seg, FIG / "segmentos.png")
    roi = roi_por_capacidad(ts, neg); roi.to_csv(REP / "roi_por_capacidad.csv", index=False)
    sens = sensibilidad_roi(ts, neg, capacidad=cfg["segmentos"]["top_alto"]); sens.to_csv(REP / "roi_sensibilidad.csv", index=False)
    cap_mes = recall_at_monthly_capacity(ts.rename(columns={LABEL: "y"}), int(neg["capacidad_contactos_mes"]))
    umbral = umbral_rentable(neg["valor_retencion_usd"], neg["uplift_contacto"], neg["costo_contacto_usd"])

    # ---------- scoring de la población actual ----------
    log("scoring población actual…")
    Xa, _ = prepare_matrix(feat_act, res["columns"], res["categories"])
    p_raw = res["booster"].predict(Xa, num_iteration=res["booster"].best_iteration)
    p_cal = res["calibrator"].predict(p_raw)
    sva = shap_values(res["booster"], Xa)
    drv_a = local_drivers(sva, Xa)
    # turno futuro ya agendado (regla operativa post-modelo)
    pend = appt[appt["pending"] & (appt["ScheduleDate"] > CUTOFF)].groupby("vehicle_id")["ScheduleDate"].min()
    out = feat_act[["window_id", "vehicle_id", "customer_id", "scoring_date_original", "due_date_w", "horizon_end",
                    "poblacion_actual", "anchor_type", "binding_rule", "vehicle_age_years", "km_per_year", "last_km",
                    "days_since_last_maint", "n_maint", "n_noshow", "n_cancel", "last_source", "last_maint_dealer",
                    "last_dealer_zone", "generation", "model_year", "business_unit", "person_type", "is_buyer",
                    "fleet_size_sales", "n_vehicles_customer_agenda", "last_rating"]].copy()
    out = out.rename(columns={"scoring_date_original": "fecha_apertura_ventana", "due_date_w": "vencimiento_estimado",
                              "horizon_end": "cierre_horizonte"})
    out["fecha_scoring"] = CUTOFF + pd.Timedelta(days=1)
    out["dias_restantes_horizonte"] = (out["cierre_horizonte"] - out["fecha_scoring"]).dt.days
    out["dias_en_ventana"] = (out["fecha_scoring"] - out["fecha_apertura_ventana"]).dt.days
    out["prob_churn"] = p_cal
    out["segmento"] = segmentar_por_capacidad(pd.Series(p_cal, index=out.index), cfg["segmentos"]["top_alto"], cfg["segmentos"]["top_medio"]).values
    out["tiene_turno_agendado"] = out["vehicle_id"].map(pend).notna()
    out["fecha_turno_agendado"] = out["vehicle_id"].map(pend)
    out = pd.concat([out.reset_index(drop=True), drv_a.reset_index(drop=True)], axis=1)
    out["prioridad"] = out["prob_churn"].rank(ascending=False, method="first").astype(int)
    out = out.sort_values("prioridad")
    out.to_parquet(config.PROCESSED_DIR / "scores_actuales.parquet", index=False)
    out.to_csv(config.PROCESSED_DIR / "scores_actuales.csv", index=False)
    # vista consolidada por usuario
    usr = (out.groupby("customer_id").agg(vehiculos_en_ventana=("vehicle_id", "size"), prob_max=("prob_churn", "max"),
                                          prob_media=("prob_churn", "mean"), algun_alto=("segmento", lambda s: (s == "Alto").any()))
              .sort_values("prob_max", ascending=False).reset_index())
    usr.to_parquet(config.PROCESSED_DIR / "scores_actuales_por_usuario.parquet", index=False)

    # volumen mensual de ventanas (dimensionamiento de capacidad)
    vol = win[win["status"].isin(["evaluable", "censurada"])].groupby(win["scoring_date"].dt.to_period("M")).size()
    vol = vol[(vol.index >= "2024-07") & (vol.index <= "2026-08")].rename("n").reset_index().rename(columns={"scoring_date": "mes"})
    vol.to_csv(REP / "volumen_mensual_ventanas.csv", index=False)
    monthly_volume_chart(vol, FIG / "volumen_mensual.png", title="Vehículos que entran en ventana por mes")

    # ---------- resumen ----------
    info = res["info"]
    md = ["# Resumen de la corrida del modelo", "",
          f"- Corrida: {time.strftime('%Y-%m-%d %H:%M')}  |  cutoff de datos: {CUTOFF.date()}",
          f"- Parámetros de ventana: `{json.dumps(params.to_dict())}`",
          f"- Split temporal: train ≤ {split.train_end} (n={info['n_train']:,}, churn {info['base_rate_train']:.1%}); "
          f"valid ≤ {split.valid_end} (n={info['n_valid']:,}, churn {info['base_rate_valid']:.1%}); "
          f"test {info['test_scoring_range'][0]} → {info['test_scoring_range'][1]} (n={info['n_test']:,}, churn {info['base_rate_test']:.1%})",
          f"- Features: {info['n_features']}  |  iteraciones LightGBM: {info['best_iteration']}  |  snapshot excluido: {info['exclude_snapshot']}",
          "", "## Métricas en test (fuera de tiempo)", "", metrics.round(4).to_markdown(), "",
          "## Recall a capacidad (LightGBM calibrado)", "", tables[main_name]["capacity"].round(3).to_markdown(index=False), "",
          f"## Capacidad mensual absoluta: {neg['capacidad_contactos_mes']:,} contactos/mes → recall {cap_mes['recall']:.1%}, precisión {cap_mes['precision']:.1%} ({cap_mes['meses']} meses de test)", "",
          "## Lift por decil (LightGBM calibrado)", "", tables[main_name]["lift"].round(3).to_markdown(index=False), "",
          "## Calibración (LightGBM calibrado)", "", tables[main_name]["calibration"].round(3).to_markdown(index=False), "",
          "## Segmentos en test", "", seg.round(3).to_markdown(index=False), "",
          f"## ROI por capacidad (supuestos: uplift {neg['uplift_contacto']:.0%}, valor USD {neg['valor_retencion_usd']}, costo contacto USD {neg['costo_contacto_usd']}; umbral rentable p ≥ {umbral:.2f})", "",
          roi.round(2).to_markdown(index=False), "", "## Sensibilidad del ROI (capacidad = segmento Alto)", "", sens.round({"uplift": 2, "ganancia_incremental_usd": 0, "beneficio_neto_modelo_usd": 0, "roi_modelo": 1}).to_markdown(index=False), "",
          "## Top 20 features (SHAP global)", "", imp.head(20)[["nombre", "mean_abs_shap"]].round(2).to_markdown(index=False), "",
          f"## Población actual scoreada: {len(out):,} vehículos ({(out['poblacion_actual']=='en_ventana').sum():,} en ventana hoy, "
          f"{(out['poblacion_actual']=='entra_en_30_dias').sum():,} entran en 30 días); {out['tiene_turno_agendado'].sum():,} ya tienen turno agendado.", "",
          out["segmento"].value_counts().rename("n").to_markdown(), ""]
    (REP / "resumen.md").write_text("\n".join(md), encoding="utf8")
    log(f"listo. resumen en {REP / 'resumen.md'}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="config/params.json")
    ap.add_argument("--negocio", default="config/negocio.json")
    ap.add_argument("--skip-train", action="store_true")
    a = ap.parse_args()
    main(a.config, a.negocio, a.skip_train)
