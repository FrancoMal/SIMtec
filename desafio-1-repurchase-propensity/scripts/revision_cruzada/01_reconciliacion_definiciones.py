"""Revisión cruzada: reconciliación de las dos definiciones de población / evento / horizonte.

Solución "fable" (esta carpeta) vs solución "astra" (G:\\SIMtec-astra, SOLO LECTURA).
Aplica la etiqueta de cada uno sobre las ventanas del otro para demostrar que la diferencia 78 % vs 42 % es de
definición (horizonte) y no de datos, y cuantifica los artefactos de cada definición.

Salida: reports/revision_cruzada/01_reconciliacion.md + tablas CSV. No escribe nada fuera de esta carpeta.
Uso: PYTHONIOENCODING=utf8 PYTHONPATH=src .venv/Scripts/python.exe scripts/revision_cruzada/01_reconciliacion_definiciones.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from repurchase import config  # noqa: E402
from repurchase.eventos import CUTOFF, appointments  # noqa: E402
from repurchase.io import load_agenda  # noqa: E402
from repurchase.ventanas import WindowParams, maintenance_events  # noqa: E402

ASTRA = Path(r"G:\SIMtec-astra\desafio-1-repurchase-propensity")
OUT = config.REPORTS_DIR / "revision_cruzada"
OUT.mkdir(parents=True, exist_ok=True)
OBS_ASTRA = pd.Timestamp("2026-08-01")   # observed_until de astra (exclusivo)
lines = []


def log(s=""):
    print(s, flush=True); lines.append(s)


def month_start(s):
    return s.dt.to_period("M").dt.to_timestamp()


# ------------------------------------------------------------------ datos
appt = appointments()
cfg = json.loads((config.PROJECT_DIR / "config/params.json").read_text(encoding="utf8"))
params = WindowParams.from_dict(cfg["ventana"])
maint = maintenance_events(appt, params)[["vehicle_id", "event_date"]].sort_values("event_date")
mine = pd.read_parquet(config.PROCESSED_DIR / "ventanas.parquet")
astra = pd.read_parquet(ASTRA / "data/processed/ventanas.parquet")
astra_test = pd.read_parquet(ASTRA / "data/processed/test_predicciones.parquet")
astra_events = pd.read_parquet(ASTRA / "data/processed/eventos.parquet")


def has_maint_between(df, vid_col, start_col, end_col, inclusive_start=True, inclusive_end=True):
    """¿Hay un mantenimiento completado (eventos de fable, nivel vehículo) en el intervalo?"""
    d = df[[vid_col, start_col, end_col]].reset_index(drop=True).copy()
    d["_i"] = np.arange(len(d))
    m = maint.rename(columns={"vehicle_id": vid_col})
    j = d.merge(m, on=vid_col, how="left")
    lo = j["event_date"] >= j[start_col] if inclusive_start else j["event_date"] > j[start_col]
    hi = j["event_date"] <= j[end_col] if inclusive_end else j["event_date"] < j[end_col]
    hit = j.loc[lo & hi, "_i"].unique()
    return pd.Series(np.isin(d["_i"], hit), index=df.index)


log("# Reconciliación de definiciones (fable vs astra)\n")
log(f"Corte de datos: {CUTOFF.date()}. Eventos objetivo de fable: {len(maint):,} mantenimientos completados.")

# ------------------------------------------------------------------ A. lo que reporta astra, releído de su parquet
log("\n## A. Población y etiqueta de astra, releídas de su `ventanas.parquet`\n")
a = astra.copy()
a["mes"] = a["scoring_date"].dt.to_period("M")
tab = a.groupby("mes").agg(ventanas=("row_id", "size"), churn_mes=("target", "mean"), churn_vin=("target_vin", "mean"),
                           churn_60d=("target_60d", "mean"), churn_90d=("target_90d", "mean"),
                           sin_label=("target", lambda s: s.isna().sum()))
log(tab.round(3).to_markdown())
tst = a[a["scoring_date"].between("2026-04-01", "2026-07-01") & a["target"].notna()]
log(f"\nTest astra (abr-jul 2026): {len(tst):,} ventanas, churn mensual {tst['target'].mean():.3f}; "
    f"por VIN {tst['target_vin'].mean():.3f}; 60 d {tst['target_60d'].mean():.3f} (n={tst['target_60d'].notna().sum():,}); "
    f"90 d {tst['target_90d'].mean():.3f} (n={tst['target_90d'].notna().sum():,})")
dd = (tst["due_date"] - tst["scoring_date"]).dt.days
log(f"Posición del vencimiento dentro del mes (test astra): mediana {dd.median():.0f} días desde el 1°, p25 {dd.quantile(.25):.0f}, p75 {dd.quantile(.75):.0f}. "
    f"Días de observación DESPUÉS del vencimiento: mediana {(tst['window_end'] - tst['due_date']).dt.days.median():.0f}.")

# ------------------------------------------------------------------ B. etiqueta de astra aplicada a las anclas de fable
log("\n## B. Etiqueta mensual de astra aplicada a las ventanas de fable\n")
w = mine[mine["status"].isin(["evaluable", "censurada", "preempted"])].copy()
w["scoring_A"] = month_start(w["due_date"])
w["end_A"] = w["scoring_A"] + pd.offsets.MonthBegin(1)
w = w[w["end_A"] <= OBS_ASTRA].copy()
# elegible según astra: no volvió entre el ancla y el 1° del mes del vencimiento
w["volvio_antes"] = has_maint_between(w, "vehicle_id", "anchor_date", "scoring_A", inclusive_start=False, inclusive_end=False)
elig = w[~w["volvio_antes"]].copy()
elig["retorno_mes"] = has_maint_between(elig, "vehicle_id", "scoring_A", "end_A", True, False)
elig["churn_A"] = (~elig["retorno_mes"]).astype(float)
elig["retorno_120"] = has_maint_between(elig, "vehicle_id", "scoring_date", "horizon_end", False, True)
elig["churn_F"] = (~elig["retorno_120"]).astype(float)
elig["mes_due"] = elig["due_date"].dt.to_period("M")
res_b = elig.groupby("mes_due").agg(ventanas=("window_id", "size"), churn_mensual_astra=("churn_A", "mean"),
                                    churn_120d_fable=("churn_F", "mean"))
sel = res_b.loc[(res_b.index >= "2026-04") & (res_b.index <= "2026-07")]
log("Ventanas de fable (anclas y vencimientos de fable), etiquetadas con la regla de astra (mes calendario del "
    "vencimiento, scoring el 1°) y con la de fable (vencimiento −30 / +90):\n")
log(res_b.loc[res_b.index >= "2025-01"].round(3).to_markdown())
e_tst = elig[elig["mes_due"].astype(str).between("2026-04", "2026-07")]
log(f"\nAbr-jul 2026 sobre anclas de fable: n={len(e_tst):,}; churn mensual (regla astra) = {e_tst['churn_A'].mean():.3f}; "
    f"churn 120 d (regla fable, sólo horizontes cerrados) = {e_tst.loc[e_tst['horizon_end'] <= CUTOFF, 'churn_F'].mean():.3f} "
    f"(n={int((e_tst['horizon_end'] <= CUTOFF).sum()):,})")
# de los "churn mensuales", ¿cuántos vuelven dentro de los 90 días posteriores al vencimiento?
late = e_tst[(e_tst["churn_A"] == 1) & (e_tst["horizon_end"] <= CUTOFF)]
log(f"De los etiquetados churn por la regla mensual (abr-jul), {1 - late['churn_F'].mean():.1%} completa el mantenimiento "
    f"antes de vencimiento + 90 días: son 'tardíos', no 'perdidos'.")

# ------------------------------------------------------------------ C. etiqueta de fable aplicada a las ventanas de astra
log("\n## C. Etiqueta de fable (vencimiento −30 / +90, nivel vehículo) aplicada a las ventanas de astra\n")
b = astra[astra["target"].notna()].copy()
b["open_F"] = b[["scoring_date"]].assign(o=b["due_date"] - pd.Timedelta(days=30)).max(axis=1)
b["end_F"] = b["due_date"] + pd.Timedelta(days=90)
b = b[b["end_F"] <= CUTOFF - pd.Timedelta(days=30)].copy()
b["retorno_F"] = has_maint_between(b, "vehicle_id", "open_F", "end_F", True, True)
b["churn_F"] = (~b["retorno_F"]).astype(float)
b["mes"] = b["scoring_date"].dt.to_period("M")
res_c = b.groupby("mes").agg(ventanas=("row_id", "size"), churn_mensual_astra=("target", "mean"),
                             churn_90d_astra=("target_90d", "mean"), churn_120d_fable=("churn_F", "mean"))
log(res_c.loc[res_c.index >= "2025-01"].round(3).to_markdown())
log(f"\nTotal ventanas de astra con horizonte de fable cerrado: {len(b):,}; churn mensual {b['target'].mean():.3f} → "
    f"churn a vencimiento+90 (fable) {b['churn_F'].mean():.3f}. Con la etiqueta 90 d de astra (desde el 1° del mes, mismo "
    f"usuario): {b['target_90d'].mean():.3f}.")
# identidad: cuánto churn mensual de astra es "el mismo vehículo volvió con otro customer_id"
same_vs_vin = astra[astra["target"].notna() & astra["target_vin"].notna()]
log(f"Etiqueta 'mismo usuario' vs 'mismo vehículo' (astra, todas las ventanas etiquetadas): churn {same_vs_vin['target'].mean():.3f} vs "
    f"{same_vs_vin['target_vin'].mean():.3f}: {(same_vs_vin['target'] - same_vs_vin['target_vin']).mean():.1%} de las ventanas son "
    f"retornos del mismo VIN con otro `customer_id` contados como churn.")

# ------------------------------------------------------------------ D. artefacto de calendario en la etiqueta mensual
log("\n## D. Artefacto de calendario: churn mensual según la posición del vencimiento dentro del mes (test astra)\n")
t = astra_test.copy()
t["dias_al_venc"] = (t["due_date"] - t["scoring_date"]).dt.days
t["bucket"] = pd.cut(t["dias_al_venc"], [-1, 5, 10, 15, 20, 25, 31], labels=["0-5", "6-10", "11-15", "16-20", "21-25", "26-31"])
tab_d = t.groupby("bucket", observed=True).agg(ventanas=("row_id", "size"), churn=("target", "mean"), score_medio=("score", "mean"))
log(tab_d.round(3).to_markdown())
from sklearn.metrics import roc_auc_score  # noqa: E402
auc_model = roc_auc_score(t["target"], t["score"])
auc_cal = roc_auc_score(t["target"], t["dias_al_venc"])
def lift10(df, col):
    k = int(np.ceil(len(df) * .1)); top = df.sort_values(col, ascending=False).head(k)
    return top["target"].mean() / df["target"].mean()
log(f"\nROC-AUC del modelo de astra en su test: {auc_model:.3f}. ROC-AUC de ordenar SOLO por 'días hasta el vencimiento' "
    f"(cuanto más tarde en el mes, más 'churn'): {auc_cal:.3f}. Lift@10 % del modelo {lift10(t, 'score'):.3f} vs "
    f"lift@10 % de la regla de calendario {lift10(t, 'dias_al_venc'):.3f}.")
corr = t[["score", "dias_al_venc"]].corr(method="spearman").iloc[0, 1]
log(f"Correlación de Spearman entre el score de astra y los días hasta el vencimiento: {corr:.3f}.")

# ------------------------------------------------------------------ E. definición del evento en astra: checkout y Guarantee
log("\n## E. Evento objetivo de astra: efecto de exigir checkout válido y de contar 'Guarantee'\n")
ag = load_agenda()
ag = ag.drop_duplicates()
# sólo turnos con vehicle_id: los 1.186 sin VIN no los usa ninguna de las dos soluciones (verif_codigo_astra)
comp = appt[appt["is_completed_maintenance"] & appt["vehicle_id"].notna()]
raw = ag[ag["schedule_id"].isin(comp["schedule_id"])].drop_duplicates("schedule_id")[["schedule_id", "ScheduleDate", "EffectiveCheckoutDate"]]
no_checkout = raw["EffectiveCheckoutDate"].isna().sum()
before = (raw["EffectiveCheckoutDate"] < raw["ScheduleDate"]).sum()
log(f"Mantenimientos completados (fable): {len(raw):,}. Sin EffectiveCheckoutDate: {no_checkout:,} ({no_checkout/len(raw):.1%}); "
    f"checkout anterior a la fecha del turno: {before:,} ({before/len(raw):.1%}). Astra los descarta como 'finalización no acreditada': "
    f"pierde {no_checkout + before:,} eventos ({(no_checkout+before)/len(raw):.1%}) como anclas y como retornos.")
g = ag[ag["ServiceType"].eq("Mantenimiento") & ag["StatusARG"].eq("(60) Concluido")]
per = g.groupby("schedule_id")["ServiceMaintenance"].apply(lambda s: s.notna().any())
only_guarantee = (~per).sum()
log(f"Turnos concluidos con ítem ServiceType=Mantenimiento pero SIN número de service (sólo 'Guarantee'/'Contactless'): "
    f"{only_guarantee:,}. Astra los cuenta como mantenimiento; fable no (son reparaciones en garantía).")
n_astra_maint = int((astra_events["maintenance"] & astra_events["valid_complete"]).sum())
log(f"Mantenimientos 'estrictos' de astra (maintenance & valid_complete): {n_astra_maint:,} vs {len(maint):,} de fable.")

# ------------------------------------------------------------------ F. poblaciones: solapamiento de vehículos y anclas
log("\n## F. Solapamiento de poblaciones\n")
va, vf = set(astra["vehicle_id"]), set(mine.loc[mine["status"].isin(["evaluable", "censurada"]), "vehicle_id"])
log(f"Vehículos con al menos una ventana: astra {len(va):,}, fable {len(vf):,}, en común {len(va & vf):,}.")
a24 = astra[astra["scoring_date"].between("2026-04-01", "2026-07-01")]
f24 = mine[(mine["status"] != "fuera_de_rango") & mine["due_date"].between("2026-04-01", "2026-07-31")]
log(f"Abr-jul 2026: vehículos con vencimiento en astra {a24['vehicle_id'].nunique():,} vs con vencimiento en fable {f24['vehicle_id'].nunique():,}; "
    f"en común {len(set(a24['vehicle_id']) & set(f24['vehicle_id'])):,}.")
jj = a24[["vehicle_id", "due_date"]].merge(f24[["vehicle_id", "due_date"]], on="vehicle_id", suffixes=("_astra", "_fable"))
jj["diff"] = (jj["due_date_fable"] - jj["due_date_astra"]).dt.days
k_cfg = cfg["ventana"].get("km_by_generation", {})
k_p703 = f"{k_cfg.get('RANGER (P703)', cfg['ventana'].get('km_interval')):,.0f}".replace(",", ".")
log(f"Diferencia de vencimiento estimado (fable − astra) para el mismo vehículo, abr-jul 2026: mediana {jj['diff'].median():.0f} días, "
    f"p25 {jj['diff'].quantile(.25):.0f}, p75 {jj['diff'].quantile(.75):.0f} (n={len(jj):,}; merge por vehicle_id, "
    f"cruza ventanas de anclas distintas cuando un vehículo tiene más de una en el período). "
    f"Astra usa 16.000 km (P703) y ritmo reciente; fable {k_p703} km (config/params.json) y tasa acumulada.")

(OUT / "01_reconciliacion.md").write_text("\n".join(lines), encoding="utf8")
res_b.to_csv(OUT / "01_etiqueta_astra_sobre_ventanas_fable.csv")
res_c.to_csv(OUT / "01_etiqueta_fable_sobre_ventanas_astra.csv")
tab_d.to_csv(OUT / "01_artefacto_calendario.csv")
print("\nguardado en", OUT)
