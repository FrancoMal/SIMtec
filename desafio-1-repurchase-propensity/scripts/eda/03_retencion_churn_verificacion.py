"""EDA 03 — Verificación independiente de las afirmaciones de reports/eda/03_retencion_churn.md.

Recalcula, con código propio (asignación de año de vida por evento, `shift` en lugar de `merge_asof`,
poblaciones alternativas), los números clave del informe 03 y agrega los controles que el script original
no hace: estimador con ventana previa homogénea de 12 meses, estadísticas ponderadas por vehículo (no por
evento), sensibilidad a "(90) Concluido sin OS", tendencia calendario, cambio de cliente controlando por
tiempo transcurrido, y descomposición BusinessUnit × canal.

Tablas: reports/eda/tables/03_retencion_churn_verificacion_*.csv

Ejecutar desde la raíz del proyecto:
  PYTHONIOENCODING=utf8 PYTHONPATH=src .venv/Scripts/python.exe scripts/eda/03_retencion_churn_verificacion.py
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd

from repurchase import config
from repurchase.eventos import CUTOFF, appointments
from repurchase.io import load_sales

warnings.filterwarnings("ignore")
TAB = config.REPORTS_DIR / "eda" / "tables"
TAB.mkdir(parents=True, exist_ok=True)
PFX = "03_retencion_churn_verificacion"
START = pd.Timestamp("2024-01-01")
IDX_START, IDX_END = pd.Timestamp("2024-07-01"), CUTOFF - pd.DateOffset(months=15)


def save(df: pd.DataFrame, name: str, fmt: str = ".3f") -> None:
    df.to_csv(TAB / f"{PFX}_{name}.csv", encoding="utf-8")
    print(f"\n### {name}")
    print(df.to_markdown(floatfmt=fmt))


def mb(a: pd.Series, b: pd.Series) -> pd.Series:
    """Meses completos entre a y b."""
    m = (b.dt.year - a.dt.year) * 12 + (b.dt.month - a.dt.month) - (b.dt.day < a.dt.day).astype(int)
    return m.astype("float").where(a.notna() & b.notna())


def addm(s: pd.Series, n: int) -> pd.Series:
    return s + pd.DateOffset(months=n)


def first_after(base: pd.DataFrame, events: pd.DataFrame, name: str) -> pd.Series:
    """Primer evento estrictamente posterior a base['start'] (por vehicle_id); alineado al índice de base."""
    left = base[["vehicle_id", "start"]].reset_index().sort_values("start")
    right = events.rename(columns={"event_date": name}).sort_values(name)
    out = pd.merge_asof(left, right, left_on="start", right_on=name, by="vehicle_id",
                        direction="forward", allow_exact_matches=False)
    return out.set_index("index")[name].reindex(base.index)


# ==============================================================================================
# 0) carga y conteos básicos
# ==============================================================================================
print("=" * 100 + "\nV0) CARGA Y CONTEOS")
ap = appointments()
n_cm_total = int(ap["is_completed_maintenance"].sum())
n_cm_sin_vid = int((ap["is_completed_maintenance"] & ap["vehicle_id"].isna()).sum())
ap = ap[ap["vehicle_id"].notna()].copy()
in_win = ap["event_date"].between(START, CUTOFF)
n_cm_fuera = int((ap["is_completed_maintenance"] & ~in_win).sum())
cm_all = ap[ap["is_completed_maintenance"] & in_win]
cm = (cm_all.sort_values(["vehicle_id", "event_date", "maint_number"])
      .drop_duplicates(["vehicle_id", "event_date"])[["vehicle_id", "event_date", "maint_number", "customer_id", "KM"]]
      .reset_index(drop=True))
cm["next_maint"] = cm.groupby("vehicle_id")["event_date"].shift(-1)
cm["cust_next"] = cm.groupby("vehicle_id")["customer_id"].shift(-1)
vis = ap[ap["completed"] & in_win][["vehicle_id", "event_date"]].drop_duplicates()
any_appt = ap[["vehicle_id", "ScheduleDate"]].rename(columns={"ScheduleDate": "event_date"}).drop_duplicates()
cm90 = ap[ap["completed_no_os"] & ap["has_maint"] & in_win][["vehicle_id", "event_date"]]
save(pd.Series({
    "turnos is_completed_maintenance (total)": n_cm_total,
    "  de los cuales sin vehicle_id": n_cm_sin_vid,
    "  de los cuales event_date fuera de ventana": n_cm_fuera,
    "mantenimientos completados en ventana (turnos)": len(cm_all),
    "  tras colapsar vehículo-día": len(cm),
    "turnos (90) Concluido sin OS con ítem de mantenimiento, en ventana": len(cm90),
    "  vehículos únicos": cm90["vehicle_id"].nunique(),
}).to_frame("valor"), "0_conteos", fmt=".0f")

sales = load_sales()
sv = sales.drop_duplicates("vehicle_id").set_index("vehicle_id")
ag = ap.groupby("vehicle_id").agg(wsd_ag=("WarrantyStartDate", "first"), n_wsd=("WarrantyStartDate", "nunique"),
                                  gen=("ShortVehicleModelGroupTreated", "first"), my=("ModelYear", "first"),
                                  first_seen=("ScheduleDate", "min"))
veh = ag.join(sv[["WarrantyStartDate", "SalesDate", "PersonType", "BusinessUnit", "SalesChannel", "ModelCode"]], how="outer")
veh.index.name = "vehicle_id"
veh["wsd"] = veh["wsd_ag"].fillna(veh["WarrantyStartDate"])
veh["in_agenda"] = veh["first_seen"].notna()
veh["in_sales"] = veh["SalesDate"].notna()
veh["coh24"] = veh["SalesDate"].dt.year.eq(2024) & (veh["wsd"] >= START)
veh["gen"] = veh["gen"].map({"RANGER (P703)": "P703", "RANGER RAPTOR (P703)": "P703", "RANGER (P375)": "P375"})
veh["gen"] = veh["gen"].fillna(veh["ModelCode"].fillna("").map(
    lambda c: "P703" if c.endswith("DC") or c == "TA1" else ("P375" if c[-2:] in ("BC", "BB") else "otro"))).fillna("otro")
veh["PersonType"] = veh["PersonType"].where(veh["PersonType"].isin(["F", "J"]) | veh["PersonType"].isna(), "otro (25/29/30)")
veh["PersonType"] = veh["PersonType"].where(~(veh["in_sales"] & veh["PersonType"].isna()), "otro (25/29/30)")
print(f"vehículos: {len(veh):,}; con WSD: {veh['wsd'].notna().sum():,}; cohorte 2024: {veh['coh24'].sum():,}; "
      f"con >1 WSD distinta en agenda: {(veh['n_wsd'] > 1).sum():,}")
veh_has_cm = set(cm["vehicle_id"])
inv = veh[veh["in_agenda"] & (veh["wsd"] < START) & ~veh.index.isin(veh_has_cm)]
print(f"vehículos en agenda con WSD < 2024 y SIN ningún mantenimiento completado en 2024-2026 (invisibles para la "
      f"población en ventana): {len(inv):,} de {int((veh['in_agenda'] & (veh['wsd'] < START)).sum()):,}")

# ==============================================================================================
# V1) curva por año de vida — asignación por evento (independiente de flag_in_interval)
# ==============================================================================================
print("\n" + "=" * 100 + "\nV1) CURVA POR AÑO DE VIDA")
cmv = cm.merge(veh[["wsd"]], left_on="vehicle_id", right_index=True)
cmv = cmv[cmv["wsd"].notna() & (cmv["event_date"] >= cmv["wsd"])]
cmv["k"] = mb(cmv["wsd"], cmv["event_date"]) // 12 + 1
has_maint_vk = cmv.groupby(["vehicle_id", "k"]).size().rename("n_maint")
vk = veh[veh["wsd"].notna()]
rows = []
for k in range(1, 13):
    st, en = addm(vk["wsd"], 12 * (k - 1)), addm(vk["wsd"], 12 * k)
    ok = (st >= START) & (en <= CUTOFF)
    rows.append(pd.DataFrame({"vehicle_id": vk.index[ok], "k": k, "start": st[ok].values}))
life = pd.concat(rows, ignore_index=True)
life = life.merge(has_maint_vk.reset_index(), on=["vehicle_id", "k"], how="left")
life["maint"] = life["n_maint"].notna()
life = life.merge(veh[["gen", "my", "first_seen", "coh24", "in_agenda", "PersonType", "BusinessUnit", "SalesChannel"]],
                  left_on="vehicle_id", right_index=True, how="left")
life["conocido"] = life["first_seen"].notna() & (life["first_seen"] < life["start"])
life["prewin_m"] = mb(pd.Series(START, index=life.index), life["start"]).clip(lower=0)  # meses observables antes de k
# estimador alternativo: activo en los 12 meses previos al año k (ventana previa completa y homogénea)
l12 = life[life["start"] >= addm(pd.Series([START]), 12).iloc[0]].copy()
l12["pre_start"] = addm(l12["start"], -12)
m = l12.reset_index()[["index", "vehicle_id", "pre_start", "start"]].merge(any_appt, on="vehicle_id")
hit = m[(m["event_date"] >= m["pre_start"]) & (m["event_date"] < m["start"])]["index"].unique()
l12["activo12"] = l12.index.isin(hit)
mm = l12.reset_index()[["index", "vehicle_id", "pre_start", "start"]].merge(cm[["vehicle_id", "event_date"]], on="vehicle_id")
hitm = mm[(mm["event_date"] >= mm["pre_start"]) & (mm["event_date"] < mm["start"])]["index"].unique()
l12["maint12prev"] = l12.index.isin(hitm)
prev = life[["vehicle_id", "k", "maint"]].assign(k=lambda d: d["k"] + 1).rename(columns={"maint": "maint_prev"})
life = life.merge(prev, on=["vehicle_id", "k"], how="left")
g = life.groupby("k")
t1 = pd.DataFrame({
    "n_todos": g.size(), "todos": g["maint"].mean(),
    "n_cohorte24": life[life["coh24"]].groupby("k").size(), "cohorte24": life[life["coh24"]].groupby("k")["maint"].mean(),
    "n_conocidos": life[life["conocido"]].groupby("k").size(), "conocidos": life[life["conocido"]].groupby("k")["maint"].mean(),
    "preventana_mediana_meses_conocidos": life[life["conocido"]].groupby("k")["prewin_m"].median(),
    "n_activo12": l12[l12["activo12"]].groupby("k").size(), "activo_12m_previos": l12[l12["activo12"]].groupby("k")["maint"].mean(),
    "n_maint12prev": l12[l12["maint12prev"]].groupby("k").size(), "maint_en_12m_previos": l12[l12["maint12prev"]].groupby("k")["maint"].mean(),
    "P(k|maint k-1)": life[life["maint_prev"] == True].groupby("k")["maint"].mean(),
    "P(k|sin maint k-1)": life[life["maint_prev"] == False].groupby("k")["maint"].mean(),
})
t1["caída_pp_conocidos"] = (t1["conocidos"].diff() * 100).round(1)
t1["caída_pp_activo12"] = (t1["activo_12m_previos"].diff() * 100).round(1)
save(t1, "1_curva_edad")

# ¿la ventana previa corta infla al estimador "conocidos"? tasa por tramo de pre-ventana, k=3 y k=6
lk = life[life["conocido"] & life["k"].isin([2, 3, 4, 5, 6])].copy()
lk["prewin_grp"] = pd.cut(lk["prewin_m"], [-1, 2, 5, 8, 11, 14, 24], labels=["0-2", "3-5", "6-8", "9-11", "12-14", "15+"])
t1b = lk.pivot_table(index="k", columns="prewin_grp", values="maint", aggfunc=["size", "mean"], observed=True)
t1b.columns = [f"{'n' if a == 'size' else 'tasa'}_{b}" for a, b in t1b.columns]
save(t1b, "1_conocidos_por_preventana")

# ==============================================================================================
# V2) caídas 2→3 y 5→6 por generación / model year; calendario
# ==============================================================================================
print("\n" + "=" * 100 + "\nV2) CAÍDAS Y COMPOSICIÓN")
kn = life[life["conocido"]]
t2 = kn.pivot_table(index="k", columns="gen", values="maint", aggfunc=["size", "mean"], observed=True)
t2.columns = [f"{'n' if a == 'size' else 'tasa'}_{b}" for a, b in t2.columns]
t2b = l12[l12["activo12"]].pivot_table(index="k", columns="gen", values="maint", aggfunc=["size", "mean"], observed=True)
t2b.columns = [f"activo12_{'n' if a == 'size' else 'tasa'}_{b}" for a, b in t2b.columns]
save(t2.join(t2b).loc[2:7], "2_caidas_por_generacion")
print(f"peso P703 en conocidos: k=2 {t2.loc[2, 'n_P703'] / kn[kn['k'] == 2].shape[0]:.3f}; k=3 {t2.loc[3, 'n_P703'] / kn[kn['k'] == 3].shape[0]:.3f}")
kn3 = kn[(kn["k"] == 3) & (kn["gen"] == "P375")].copy()
kn3["wsd_sem"] = addm(kn3["start"], -24).dt.to_period("Q").astype(str)
save(kn3.groupby("wsd_sem").agg(n=("maint", "size"), tasa=("maint", "mean"), prewin_mediana=("prewin_m", "median")), "2_k3_P375_por_trimestre_wsd")

# tendencia calendario: retorno a 12 m según mes del evento índice
cm["idx"] = cm["event_date"].between(IDX_START, IDX_END)
idx = cm[cm["idx"]].copy()
for h in (6, 12, 13, 15):
    idx[f"m{h}"] = idx["next_maint"].notna() & (idx["next_maint"] <= addm(idx["event_date"], h))
t2c = idx.groupby(idx["event_date"].dt.to_period("M")).agg(n=("m12", "size"), ret_6m=("m6", "mean"), ret_12m=("m12", "mean"), ret_15m=("m15", "mean"))
t2c.index = t2c.index.astype(str)
save(t2c, "2_retorno_por_mes_calendario")

# ==============================================================================================
# V3) tasa base tras un mantenimiento (shift en vez de merge_asof) + nivel vehículo + sensibilidad (90)
# ==============================================================================================
print("\n" + "=" * 100 + "\nV3) TASA BASE")
idx["start"] = idx["event_date"]
idx["next_vis"] = first_after(idx, vis, "next_vis")
for h in (12, 15):
    idx[f"v{h}"] = idx["next_vis"].notna() & (idx["next_vis"] <= addm(idx["start"], h))
first_idx = idx.sort_values("event_date").drop_duplicates("vehicle_id", keep="first")
# sensibilidad: contar (90) Concluido sin OS con ítem de mantenimiento como retorno
u = pd.concat([cm[["vehicle_id", "event_date"]], cm90], ignore_index=True).drop_duplicates().sort_values(["vehicle_id", "event_date"])
idx["next_incl90"] = first_after(idx, u, "next_incl90")
t3 = pd.DataFrame({
    "eventos índice (n)": [len(idx), len(first_idx)],
    "vehículos": [idx["vehicle_id"].nunique(), first_idx["vehicle_id"].nunique()],
    "retorno_12m": [idx["m12"].mean(), first_idx["m12"].mean()],
    "retorno_13m": [idx["m13"].mean(), first_idx["m13"].mean()],
    "retorno_15m": [idx["m15"].mean(), first_idx["m15"].mean()],
    "visita_12m": [idx["v12"].mean(), first_idx["v12"].mean()],
    "retorno_12m_incl_(90)": [(idx["next_incl90"].notna() & (idx["next_incl90"] <= addm(idx["start"], 12))).mean(), np.nan],
}, index=["todos los eventos (como el informe)", "primer evento por vehículo"]).T
save(t3, "3_tasa_base")
# eventos por vehículo en el período índice
save(idx.groupby("vehicle_id").size().value_counts().sort_index().rename("vehículos").to_frame().T, "3_eventos_por_vehiculo", fmt=".0f")

# ==============================================================================================
# V4) por edad y por número de service; semántica de ServiceMaintenance
# ==============================================================================================
print("\n" + "=" * 100 + "\nV4) EDAD Y N° DE SERVICE")
idx = idx.merge(veh[["wsd"]], left_on="vehicle_id", right_index=True, how="left")
idx["edad"] = mb(idx["wsd"], idx["start"]) // 12
idx["edad_grp"] = pd.cut(idx["edad"], [-1, 0, 1, 2, 3, 4, 5, 9, 99], labels=["0", "1", "2", "3", "4", "5", "6-9", "10+"])
t4 = idx.groupby("edad_grp", observed=True).agg(n=("m12", "size"), ret_12m=("m12", "mean"), ret_15m=("m15", "mean"))
t4["churn_12m"] = 1 - t4["ret_12m"]
save(t4, "4_por_edad")
# edad × número de service (¿discrimina el n° de service controlando por edad?)
idx["mn_grp"] = pd.cut(idx["maint_number"], [0, 1, 2, 3, 5, 10, 19, 20], labels=["1", "2", "3", "4-5", "6-10", "11-19", "20"])
t4b = idx.pivot_table(index="edad_grp", columns="mn_grp", values="m12", aggfunc="mean", observed=True)
n4b = idx.pivot_table(index="edad_grp", columns="mn_grp", values="m12", aggfunc="size", observed=True)
save(t4b.where(n4b >= 200), "4_edad_x_maint_number_ret12m")
raw = pd.read_parquet(config.AGENDA_PARQUET, columns=["ServiceMaintenance", "ServiceName", "KM", "StatusARG", "WarrantyStartDate", "ScheduleDate"])
raw = raw[raw["ServiceMaintenance"].notna()]
t4c = raw.groupby("ServiceMaintenance")["ServiceName"].agg(lambda s: "; ".join(f"{k} ({v:,})" for k, v in s.value_counts().head(2).items())).to_frame("ServiceName (top 2)")
ok60 = raw[raw["StatusARG"].eq("(60) Concluido")].copy()
ok60["edad_m"] = mb(ok60["WarrantyStartDate"], ok60["ScheduleDate"])
t4c["KM_mediana_(60)"] = ok60.groupby("ServiceMaintenance")["KM"].median()
t4c["edad_meses_mediana_(60)"] = ok60.groupby("ServiceMaintenance")["edad_m"].median()
t4c["n_(60)"] = ok60.groupby("ServiceMaintenance").size()
save(t4c, "4_servicemaintenance_vs_servicename", fmt=".0f")
# ¿los códigos 11-19 en vehículos jóvenes son services 11°+ reales (KM alto) o un relabel de 1°-9°?
young = idx[(idx["edad"] <= 1) & idx["maint_number"].notna()].copy()
young["mn"] = pd.cut(young["maint_number"], [0, 1, 2, 3, 5, 10, 19, 20], labels=["1", "2", "3", "4-5", "6-10", "11-19", "20"])
save(young.groupby("mn", observed=True)["KM"].describe(percentiles=[.25, .5, .75])[["count", "25%", "50%", "75%"]], "4_km_vehiculos_jovenes_por_maint_number", fmt=".0f")

# ==============================================================================================
# V5) cohorte 2024: primer service
# ==============================================================================================
print("\n" + "=" * 100 + "\nV5) COHORTE 2024 — PRIMER SERVICE")
coh = veh[veh["coh24"] & (addm(veh["wsd"], 18) <= CUTOFF)].reset_index()
coh["start"] = coh["wsd"]
fm = cmv[cmv["event_date"] > cmv["wsd"]].groupby("vehicle_id")["event_date"].min().rename("first_maint")
coh = coh.merge(fm.reset_index(), on="vehicle_id", how="left")
coh["first_turno"] = first_after(coh, any_appt, "first_turno")
t5 = pd.DataFrame({h: {"≥1 mantenimiento": (coh["first_maint"] <= addm(coh["wsd"], h)).mean(),
                       "≥1 turno cualquier estado": (coh["first_turno"] <= addm(coh["wsd"], h)).mean()} for h in (6, 9, 12, 13, 15, 18)}).T
t5["n"] = len(coh)
save(t5, "5_primer_service_horizonte")
coh["meses"] = mb(coh["wsd"], coh["first_maint"])
coh["dias"] = (coh["first_maint"] - coh["wsd"]).dt.days
print("meses hasta el 1er mantenimiento (≤18 m):", coh.loc[coh["meses"] <= 17, "meses"].describe(percentiles=[.1, .25, .5, .75, .9]).round(1).to_dict())
curve = pd.Series({m_: (coh["first_maint"] <= addm(coh["wsd"], m_)).mean() for m_ in range(1, 19)}, name="acum")
curve = curve.to_frame(); curve["incremento_pp"] = (curve["acum"].diff() * 100).round(1)
save(curve.loc[9:15], "5_curva_acumulada_9_15")
bins = list(range(0, 571, 30))
h = pd.cut(coh["dias"], bins, right=False).value_counts().sort_index()
save((h / len(coh)).rename("% de la cohorte").to_frame().assign(n=h.values), "5_dias_al_primer_service_bins30")
print(f"nunca en agenda: {int((~coh['in_agenda']).sum()):,} de {len(coh):,} ({(~coh['in_agenda']).mean():.3f}) "
      f"[cohorte completa: {int((veh['coh24'] & ~veh['in_agenda']).sum()):,} de {int(veh['coh24'].sum()):,}]")

# ==============================================================================================
# V6) sesgo de selección: comparación dentro de la misma cohorte
# ==============================================================================================
print("\n" + "=" * 100 + "\nV6) SESGO DE SELECCIÓN")
rows = []
for k in (1, 2):
    lk = life[life["k"] == k]
    c = lk[lk["coh24"]]
    a = lk[lk["in_agenda"]]
    a["wsd_year"] = addm(a["start"], -12 * (k - 1)).dt.year
    rows.append({"k": k, "cohorte24_completa": c["maint"].mean(), "n_completa": len(c),
                 "cohorte24_con_turno": c[c["in_agenda"]]["maint"].mean(), "n_con_turno": int(c["in_agenda"].sum()),
                 "sesgo_pp_misma_cohorte": (c[c["in_agenda"]]["maint"].mean() - c["maint"].mean()) * 100,
                 "agenda_todos_WSD": a["maint"].mean(), "n_agenda": len(a),
                 "agenda_WSD2024": a[a["wsd_year"] == 2024]["maint"].mean(), "n_agenda_WSD2024": int((a["wsd_year"] == 2024).sum()),
                 "agenda_WSD2025": a[a["wsd_year"] == 2025]["maint"].mean() if k == 1 else np.nan,
                 "n_agenda_WSD2025": int((a["wsd_year"] == 2025).sum()) if k == 1 else 0,
                 "agenda_WSD2023": a[a["wsd_year"] == 2023]["maint"].mean() if k == 2 else np.nan,
                 "sesgo_pp_informe": (a["maint"].mean() - c["maint"].mean()) * 100})
save(pd.DataFrame(rows).set_index("k"), "6_sesgo_seleccion")

# ==============================================================================================
# V7) cadencia: gap por evento vs por vehículo; tiempo al próximo sin truncar; km/año por vehículo
# ==============================================================================================
print("\n" + "=" * 100 + "\nV7) CADENCIA")
gap = (cm["next_maint"] - cm["event_date"]).dt.days.dropna()
gap_v = (cm["next_maint"] - cm["event_date"]).dt.days.groupby(cm["vehicle_id"]).median().dropna()
n_gaps_v = (cm["next_maint"] - cm["event_date"]).dt.days.groupby(cm["vehicle_id"]).count()
mcurve = pd.Series({h_: (idx["next_maint"].notna() & (idx["next_maint"] <= addm(idx["start"], h_))).mean() for h_ in range(1, 16)})
med_month = mcurve[mcurve >= 0.5].index.min()
cmv["km_anio"] = cmv["KM"] / ((cmv["event_date"] - cmv["wsd"]).dt.days / 365.25).clip(lower=0.25)
last_v = cmv.sort_values("event_date").drop_duplicates("vehicle_id", keep="last")
t7 = pd.DataFrame({
    "gap por evento (como el informe)": gap.describe(percentiles=[.1, .25, .5, .75, .9]),
    "gap mediano por vehículo": gap_v.describe(percentiles=[.1, .25, .5, .75, .9]),
    "km/año por evento": cmv["km_anio"].describe(percentiles=[.1, .25, .5, .75, .9]),
    "km/año por vehículo (último mant.)": last_v["km_anio"].describe(percentiles=[.1, .25, .5, .75, .9]),
})
save(t7, "7_cadencia", fmt=".0f")
print(f"mes en que el retorno acumulado tras un mantenimiento supera 50 %: {med_month} (6 m: {mcurve[6]:.3f}, 7 m: {mcurve[7]:.3f}, 8 m: {mcurve[8]:.3f})")
vcurve = pd.Series({h_: (first_idx["next_maint"].notna() & (first_idx["next_maint"] <= addm(first_idx["start"], h_))).mean() for h_ in range(1, 16)})
save(pd.DataFrame({"retorno_acum_por_evento": mcurve, "retorno_acum_por_vehículo (1er evento)": vcurve}), "7_retorno_acumulado_evento_vs_vehiculo")
print(f"mes en que el retorno acumulado supera 50 % a nivel vehículo (1er evento por vehículo): {vcurve[vcurve >= 0.5].index.min()}")
print("gaps por vehículo (n de gaps):", n_gaps_v.value_counts().sort_index().head(8).to_dict(),
      f"| vehículos con ≥3 gaps aportan {gap.groupby(cm.loc[gap.index, 'vehicle_id']).size().pipe(lambda s: s[s >= 3].sum()) / len(gap):.3f} de los gaps")

# ==============================================================================================
# V8) población mensual en ventana (12 m sin mantenimiento)
# ==============================================================================================
print("\n" + "=" * 100 + "\nV8) POBLACIÓN MENSUAL")
cyc_m = cm[["vehicle_id", "event_date", "next_maint"]].rename(columns={"event_date": "start"}).assign(origen="tras mant.")
cyc_w = veh.loc[veh["wsd"] >= START, ["wsd"]].rename(columns={"wsd": "start"}).join(fm.rename("next_maint")).reset_index().assign(origen="desde WSD")
cyc = pd.concat([cyc_m, cyc_w], ignore_index=True)
cyc["due"] = addm(cyc["start"], 12)
cyc = cyc[cyc["due"] <= CUTOFF].copy()
cyc["mes"] = cyc["due"].dt.to_period("M").astype(str)
cyc["en_ventana"] = cyc["next_maint"].isna() | (cyc["next_maint"] >= cyc["due"])
cyc["ret1"] = cyc["en_ventana"] & (cyc["next_maint"] <= addm(cyc["due"], 1))
cyc["ret3"] = cyc["en_ventana"] & (cyc["next_maint"] <= addm(cyc["due"], 3))
full = cyc[(cyc["mes"] >= "2025-01") & (cyc["mes"] <= "2026-04")]
g = full.groupby("mes")
t8 = pd.DataFrame({"ciclos_vencen": g.size(), "vehículos_distintos_vencen": g["vehicle_id"].nunique(),
                   "en_ventana": g["en_ventana"].sum(), "vehículos_distintos_en_ventana": full[full["en_ventana"]].groupby("mes")["vehicle_id"].nunique(),
                   "ret_≤1m": full[full["en_ventana"]].groupby("mes")["ret1"].mean(), "ret_≤3m": full[full["en_ventana"]].groupby("mes")["ret3"].mean()})
t8.loc["promedio"] = t8.mean()
save(t8, "8_poblacion_mensual")
print(f"vehículos distintos que estuvieron en ventana al menos una vez en 2025-01..2026-04: {full[full['en_ventana']]['vehicle_id'].nunique():,}; "
      f"ciclos en ventana: {int(full['en_ventana'].sum()):,}")
print(f"% en ventana por origen (todos los ciclos con due ≤ CUTOFF): {cyc.groupby('origen')['en_ventana'].mean().round(3).to_dict()}; "
      f"ciclos: {cyc.groupby('origen').size().to_dict()}")

# ==============================================================================================
# V9) recurrencia y cambio de cliente controlando por tiempo transcurrido
# ==============================================================================================
print("\n" + "=" * 100 + "\nV9) RECURRENCIA")
ch = cyc_m.copy()
ch = pd.concat([ch, cyc_w], ignore_index=True)
ch = ch[(ch["start"] >= START) & (addm(ch["start"], 15) <= CUTOFF)].copy()
ch["mark15"] = addm(ch["start"], 15)
ch["churn15"] = ch["next_maint"].isna() | (ch["next_maint"] > ch["mark15"])
chu = ch[ch["churn15"]].copy()
chu["extra"] = mb(chu["mark15"], pd.Series(CUTOFF, index=chu.index))
chu["m_tras"] = mb(chu["mark15"], chu["next_maint"])
t9 = pd.DataFrame([{"h": h_, "n_observables": int((chu["extra"] >= h_).sum()),
                    "reaparecieron": (chu.loc[chu["extra"] >= h_, "m_tras"] <= h_).mean()} for h_ in (3, 6, 9, 12, 15)]).set_index("h")
save(t9, "9_reaparicion")
print(f"ciclos con 15 m: {len(ch):,}; churn 15 m: {int(ch['churn15'].sum()):,} ({ch['churn15'].mean():.3f})")
c24 = ch[addm(ch["start"], 24) <= CUTOFF]
print(f"retorno acumulado (ciclos iniciados hasta {(CUTOFF - pd.DateOffset(months=24)).date()}, n={len(c24):,}): "
      + ", ".join(f"{h_} m {(c24['next_maint'].notna() & (c24['next_maint'] <= addm(c24['start'], h_))).mean():.3f}" for h_ in (12, 15, 18, 24)))
# cambio de customer_id por tiempo hasta el próximo mantenimiento (solo ciclos tras mantenimiento)
r = cm[cm["next_maint"].notna() & (cm["event_date"] >= START)].copy()
r["m_next"] = mb(r["event_date"], r["next_maint"])
r["cambio"] = r["customer_id"].notna() & r["cust_next"].notna() & (r["customer_id"] != r["cust_next"])
r["tramo"] = pd.cut(r["m_next"], [-1, 2, 5, 8, 11, 14, 17, 20, 40], labels=["0-2", "3-5", "6-8", "9-11", "12-14", "15-17", "18-20", "21+"])
save(r.groupby("tramo", observed=True).agg(n=("cambio", "size"), pct_cambio_customer_id=("cambio", "mean")), "9_cambio_cliente_por_tramo")

# ==============================================================================================
# V10) atributos de venta: HR × PersonType, BusinessUnit × canal
# ==============================================================================================
print("\n" + "=" * 100 + "\nV10) ATRIBUTOS")
c1 = life[life["coh24"] & (life["k"] == 1)]
for col in ("PersonType", "BusinessUnit", "SalesChannel"):
    print(c1.groupby(col, observed=True)["maint"].agg(["size", "mean"]).round(3).to_string())
save(pd.crosstab(c1["SalesChannel"], c1["PersonType"]), "10_hr_x_persontype", fmt=".0f")
t10 = c1.pivot_table(index="BusinessUnit", columns="SalesChannel", values="maint", aggfunc=["size", "mean"], observed=True)
t10.columns = [f"{'n' if a == 'size' else 'tasa'}_{b}" for a, b in t10.columns]
save(t10, "10_bu_x_canal_k1")
t10b = c1[c1["SalesChannel"] != "HR"].pivot_table(index="PersonType", columns="BusinessUnit", values="maint", aggfunc=["size", "mean"], observed=True)
t10b.columns = [f"{'n' if a == 'size' else 'tasa'}_{b}" for a, b in t10b.columns]
save(t10b, "10_persontype_x_bu_k1_sinHR")
print("\nListo.")
