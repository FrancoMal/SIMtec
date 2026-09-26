"""EDA 03 — Retención por edad del vehículo y tasa base de churn.

Genera todas las tablas (reports/eda/tables/03_retencion_churn_*.csv) y figuras
(reports/figures/eda/03_retencion_churn_*.png) citadas en reports/eda/03_retencion_churn.md.

Secciones:
  A) Curva de retención por año de vida (k = 1..12) con tres estimadores y desagregaciones.
  B) Verificación del insight del tutor ("al tercer año cae fuerte") y quiebre a los 36 meses.
  C) Tasa base de churn bajo horizontes alternativos (10..15 meses) tras un mantenimiento completado.
  D) Cohorte de ventas 2024: tiempo hasta el primer mantenimiento.
  E) Población en ventana por mes (12 meses desde el último mantenimiento o desde la garantía).
  F) Recurrencia: churn temporario vs definitivo.

Ejecutar desde la raíz del proyecto:
  PYTHONIOENCODING=utf8 PYTHONPATH=src .venv/Scripts/python.exe scripts/eda/03_retencion_churn.py
"""
from __future__ import annotations

import warnings

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from repurchase import config  # noqa: E402
from repurchase.eventos import CUTOFF, appointments  # noqa: E402
from repurchase.io import load_sales  # noqa: E402

warnings.filterwarnings("ignore", category=pd.errors.PerformanceWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

PREFIX = "03_retencion_churn"
FIG_DIR = config.FIGURES_DIR / "eda"
TAB_DIR = config.REPORTS_DIR / "eda" / "tables"
FIG_DIR.mkdir(parents=True, exist_ok=True)
TAB_DIR.mkdir(parents=True, exist_ok=True)

START = pd.Timestamp("2024-01-01")          # inicio de la ventana observada
IDX_START = pd.Timestamp("2024-07-01")      # inicio de eventos índice para tasa base (sección C)
H_MAX = 15                                  # meses de seguimiento garantizados en sección C / F
IDX_END = CUTOFF - pd.DateOffset(months=H_MAX)  # 2025-05-25: último evento índice con 15 meses completos

plt.rcParams.update({
    "figure.dpi": 130, "savefig.dpi": 130, "font.size": 10, "axes.titlesize": 11,
    "axes.grid": True, "grid.alpha": 0.3, "axes.spines.top": False, "axes.spines.right": False,
})
PALETTE = ["#1f4e79", "#c0504d", "#4f9d69", "#e8a33d", "#7b5ea7", "#5c8ab8", "#8c8c8c", "#b8860b"]


# ----------------------------------------------------------------------------------------------
# utilidades
# ----------------------------------------------------------------------------------------------
def save_table(df: pd.DataFrame, name: str, floatfmt: str = ".3f", index: bool = True) -> None:
    path = TAB_DIR / f"{PREFIX}_{name}.csv"
    df.to_csv(path, index=index, encoding="utf-8")
    print(f"\n### {name}  ->  {path.name}")
    print(df.to_markdown(index=index, floatfmt=floatfmt))


def savefig(fig, name: str) -> None:
    path = FIG_DIR / f"{PREFIX}_{name}.png"
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
    print(f"[fig] {path.name}")


def add_months(s: pd.Series, n: int) -> pd.Series:
    return s + pd.DateOffset(months=n)


def months_between(a: pd.Series, b: pd.Series) -> pd.Series:
    """Meses completos entre a y b (b >= a). NaN si alguno es NaT."""
    m = (b.dt.year - a.dt.year) * 12 + (b.dt.month - a.dt.month) - (b.dt.day < a.dt.day).astype(int)
    return m.astype("float").where(a.notna() & b.notna())


def next_event_after(base: pd.DataFrame, events: pd.DataFrame, col: str) -> pd.Series:
    """Primer evento (events: vehicle_id, event_date) estrictamente posterior a base['start'], alineado a base.index."""
    left = base[["vehicle_id", "start"]].reset_index().sort_values("start")
    right = events.rename(columns={"event_date": col}).sort_values(col)
    out = pd.merge_asof(left, right, left_on="start", right_on=col, by="vehicle_id",
                        direction="forward", allow_exact_matches=False)
    return out.set_index("index")[col].reindex(base.index)


def rate_table(df: pd.DataFrame, by: list[str], flags: list[str]) -> pd.DataFrame:
    g = df.groupby(by, observed=True)
    out = g.size().rename("n").to_frame()
    for f in flags:
        out[f] = g[f].mean()
    return out


# ----------------------------------------------------------------------------------------------
# 0) carga y tabla de vehículos
# ----------------------------------------------------------------------------------------------
print("=" * 100)
print("0) CARGA")
print("=" * 100)
ap = appointments()
ap = ap[ap["vehicle_id"].notna()].copy()
sales = load_sales()
print(f"turnos con vehicle_id: {len(ap):,}  | ventas: {len(sales):,}  | CUTOFF={CUTOFF.date()}  IDX_END={IDX_END.date()}")

# eventos dentro de la ventana observada
ev = ap[(ap["event_date"] >= START) & (ap["event_date"] <= CUTOFF)]
print(f"turnos fuera de [{START.date()}, {CUTOFF.date()}] excluidos: {len(ap) - len(ev):,} "
      f"(de los cuales concluidos: {int((ap['completed'] & ~ap.index.isin(ev.index)).sum())})")
cm_all = ev[ev["is_completed_maintenance"]][["vehicle_id", "event_date", "maint_number", "customer_id", "KM"]]
cm = cm_all.sort_values(["vehicle_id", "event_date", "maint_number"]).drop_duplicates(["vehicle_id", "event_date"])
print(f"mantenimientos completados en ventana: {len(cm_all):,} turnos; {len(cm):,} tras colapsar mismo vehículo-día")
vis = ev[ev["completed"]][["vehicle_id", "event_date"]].drop_duplicates()
vis_nomaint = ev[ev["completed"] & ~ev["has_maint"]][["vehicle_id", "event_date"]].drop_duplicates()
any_appt = ap[["vehicle_id", "ScheduleDate"]].rename(columns={"ScheduleDate": "event_date"}).drop_duplicates()

# tabla de vehículos = agenda ∪ ventas
va = ap.groupby("vehicle_id").agg(
    wsd_ag=("WarrantyStartDate", "first"), gen_ag=("ShortVehicleModelGroupTreated", "first"),
    my_ag=("ModelYear", "first"), zone=("DealerStateOrZone", "first"),
    n_appt=("schedule_id", "size"), first_seen=("ScheduleDate", "min"),
)
sv = sales.drop_duplicates("vehicle_id").set_index("vehicle_id")[[
    "WarrantyStartDate", "SalesDate", "PersonType", "BusinessUnit", "SalesChannel", "ModelCode", "ModelYear"]]
sv.columns = ["wsd_sales", "SalesDate", "PersonType", "BusinessUnit", "SalesChannel", "ModelCode", "my_sales"]
veh = va.join(sv, how="outer")
veh["in_agenda"] = veh["n_appt"].notna()
veh["in_sales"] = veh["SalesDate"].notna()
veh["grupo"] = np.select([veh["in_agenda"] & veh["in_sales"], veh["in_agenda"]], ["ambas tablas", "solo agenda"], "solo ventas")
veh["wsd"] = veh["wsd_ag"].fillna(veh["wsd_sales"])
gen_map = {"RANGER (P703)": "P703", "RANGER RAPTOR (P703)": "P703", "RANGER (P375)": "P375"}
code_gen = veh["ModelCode"].fillna("").map(lambda c: "P703" if c.endswith("DC") or c == "TA1" else ("P375" if c[-2:] in ("BC", "BB") else "otro"))
veh["gen"] = veh["gen_ag"].map(gen_map).fillna(code_gen).fillna("otro")
veh["model_year"] = veh["my_ag"].fillna(veh["my_sales"].astype("float"))
veh["my_grp"] = pd.cut(veh["model_year"], [0, 2015, 2019, 2022, 2023, 2024, 2030],
                       labels=["≤2015", "2016-2019", "2020-2022", "2023", "2024", "2025-2026"])
veh["zone"] = veh["zone"].fillna("sin dato")
veh["PersonType"] = veh["PersonType"].where(veh["PersonType"].isin(["F", "J"]), "otro (25/29/30/NaN)").where(veh["in_sales"])
# cohorte de ventas 2024: vendidos en 2024 con garantía iniciada dentro de la ventana (excluye 4 unidades con WSD 2015-2023)
veh["cohorte_2024"] = veh["SalesDate"].dt.year.eq(2024) & (veh["wsd"] >= START)
veh = veh.reset_index().rename(columns={"index": "vehicle_id"})

resumen_veh = pd.DataFrame({
    "vehículos": veh.groupby("grupo").size(),
    "con WarrantyStartDate": veh.groupby("grupo")["wsd"].apply(lambda x: x.notna().sum()),
    "cohorte ventas 2024": veh.groupby("grupo")["cohorte_2024"].sum(),
})
resumen_veh.loc["total"] = resumen_veh.sum()
save_table(resumen_veh, "0_universo_vehiculos", floatfmt=".0f")
print("Generación por grupo:\n", pd.crosstab(veh["grupo"], veh["gen"]).to_string())
print(f"WSD agenda vs ventas (vehículos en ambas): iguales en "
      f"{(veh['wsd_ag'] == veh['wsd_sales']).sum():,} de {(veh['wsd_ag'].notna() & veh['wsd_sales'].notna()).sum():,}")
# cobertura cruzada por año de inicio de garantía: ¿la tabla de ventas cubre todo el parque 2024+ que ve la red?
wy = veh["wsd"].dt.year
cov = pd.DataFrame({
    "en agenda": veh[veh["in_agenda"]].groupby(wy).size(),
    "en agenda y NO en ventas": veh[veh["in_agenda"] & ~veh["in_sales"]].groupby(wy).size(),
    "en ventas": veh[veh["in_sales"]].groupby(wy).size(),
    "en ventas y NO en agenda": veh[veh["in_sales"] & ~veh["in_agenda"]].groupby(wy).size(),
}).reindex([2023, 2024, 2025, 2026]).fillna(0).astype(int)
cov["% agenda sin venta"] = cov["en agenda y NO en ventas"] / cov["en agenda"]
cov["% ventas sin agenda"] = cov["en ventas y NO en agenda"] / cov["en ventas"]
save_table(cov, "0_cobertura_por_anio_garantia", floatfmt=".3f")
n_pre_wsd = int((cm.merge(veh[["vehicle_id", "wsd"]], on="vehicle_id")["event_date"] < cm.merge(veh[["vehicle_id", "wsd"]], on="vehicle_id")["wsd"]).sum())
print(f"mantenimientos completados con fecha ANTERIOR al inicio de garantía del vehículo: {n_pre_wsd:,}")

# ----------------------------------------------------------------------------------------------
# A) curva de retención por año de vida
# ----------------------------------------------------------------------------------------------
print("\n" + "=" * 100)
print("A) RETENCIÓN POR AÑO DE VIDA")
print("=" * 100)
vk = veh[veh["wsd"].notna()].copy()
rows = []
for k in range(1, 13):
    st = add_months(vk["wsd"], 12 * (k - 1))
    en = add_months(vk["wsd"], 12 * k)
    ok = (st >= START) & (en <= CUTOFF)
    rows.append(pd.DataFrame({"vehicle_id": vk.loc[ok, "vehicle_id"], "k": k, "start": st[ok], "end": en[ok]}))
life = pd.concat(rows, ignore_index=True)
life = life.merge(veh[["vehicle_id", "grupo", "gen", "my_grp", "zone", "PersonType", "BusinessUnit", "SalesChannel",
                       "cohorte_2024", "first_seen", "in_agenda"]], on="vehicle_id", how="left")


def flag_in_interval(life_df: pd.DataFrame, events: pd.DataFrame, name: str) -> pd.Series:
    m = life_df[["vehicle_id", "start", "end"]].reset_index().merge(events, on="vehicle_id", how="inner")
    hit = m[(m["event_date"] >= m["start"]) & (m["event_date"] < m["end"])]["index"].unique()
    return pd.Series(life_df.index.isin(hit), index=life_df.index, name=name)


life["maint"] = flag_in_interval(life, cm, "maint")
life["visita"] = flag_in_interval(life, vis, "visita")
life["turno"] = flag_in_interval(life, any_appt, "turno")
# conocido por la red antes de empezar el año k (evita el sesgo "está en agenda porque vino en ese año")
life["conocido_antes"] = life["first_seen"].notna() & (life["first_seen"] < life["start"])
# retención condicional: mantenimiento en k-1 (solo si k-1 también está observado)
prev = life[["vehicle_id", "k", "maint"]].copy()
prev["k"] += 1
life = life.merge(prev.rename(columns={"maint": "maint_prev"}), on=["vehicle_id", "k"], how="left")

print(f"vehículo-años observados completos: {len(life):,} de {life['vehicle_id'].nunique():,} vehículos")

# A.1 estimadores
est_naive = rate_table(life, ["k"], ["maint", "visita", "turno"]).rename(columns={"maint": "maint_todos", "visita": "visita_todos", "turno": "turno_todos"})
est_known = rate_table(life[life["conocido_antes"]], ["k"], ["maint", "visita"]).rename(columns={"n": "n_conocidos", "maint": "maint_conocidos", "visita": "visita_conocidos"})
est_coh = rate_table(life[life["cohorte_2024"]], ["k"], ["maint", "visita"]).rename(columns={"n": "n_cohorte24", "maint": "maint_cohorte24", "visita": "visita_cohorte24"})
cond = life[life["maint_prev"].notna()].copy()
cond["maint_prev"] = cond["maint_prev"].astype(bool)
est_cond = pd.DataFrame({
    "n_con_maint_k-1": cond[cond["maint_prev"]].groupby("k").size(),
    "P(maint k | maint k-1)": cond[cond["maint_prev"]].groupby("k")["maint"].mean(),
    "n_sin_maint_k-1": cond[~cond["maint_prev"]].groupby("k").size(),
    "P(maint k | sin maint k-1)": cond[~cond["maint_prev"]].groupby("k")["maint"].mean(),
})
tabA = est_naive.join(est_known).join(est_coh).join(est_cond)
tabA["caída_pp_conocidos"] = (tabA["maint_conocidos"].diff() * 100).round(1)
save_table(tabA, "A_curva_edad", floatfmt=".3f")

# A.2 desagregaciones (estimador "conocidos antes" para k>=2; cohorte de ventas 2024 para k<=2)
known = life[life["conocido_antes"]]
for col, nm in [("gen", "A_por_generacion"), ("my_grp", "A_por_modelyear"), ("zone", "A_por_zona"), ("grupo", "A_por_grupo_tabla")]:
    t = known.pivot_table(index="k", columns=col, values="maint", aggfunc=["size", "mean"], observed=True)
    t.columns = [f"{'n' if a == 'size' else 'tasa'}_{b}" for a, b in t.columns]
    save_table(t, nm, floatfmt=".3f")
coh = life[life["cohorte_2024"]]
for col, nm in [("PersonType", "A_cohorte24_persontype"), ("BusinessUnit", "A_cohorte24_businessunit"),
                ("SalesChannel", "A_cohorte24_saleschannel"), ("gen", "A_cohorte24_generacion"), ("grupo", "A_cohorte24_grupo_tabla")]:
    t = coh.pivot_table(index="k", columns=col, values="maint", aggfunc=["size", "mean"], observed=True)
    t.columns = [f"{'n' if a == 'size' else 'tasa'}_{b}" for a, b in t.columns]
    save_table(t, nm, floatfmt=".3f")

# A.3 sesgo de selección en k=1 y k=2: agenda-based vs cohorte completa
bias_rows = []
for k in (1, 2):
    lk = life[life["k"] == k]
    bias_rows.append({
        "k": k,
        "agenda (ambas+solo agenda)": lk[lk["in_agenda"]]["maint"].mean(), "n_agenda": int(lk["in_agenda"].sum()),
        "cohorte 2024 completa": lk[lk["cohorte_2024"]]["maint"].mean(), "n_cohorte": int(lk["cohorte_2024"].sum()),
        "cohorte 2024 con ≥1 turno": lk[lk["cohorte_2024"] & lk["in_agenda"]]["maint"].mean(),
        "conocidos antes del año k": lk[lk["conocido_antes"]]["maint"].mean(), "n_conocidos": int(lk["conocido_antes"].sum()),
    })
save_table(pd.DataFrame(bias_rows).set_index("k"), "A_sesgo_seleccion", floatfmt=".3f")

# A.4 curva semestral (para ver si hay quiebre a los 36 meses) — estimador "conocidos antes"
rows = []
for h in range(1, 25):
    st = add_months(vk["wsd"], 6 * (h - 1))
    en = add_months(vk["wsd"], 6 * h)
    ok = (st >= START) & (en <= CUTOFF)
    rows.append(pd.DataFrame({"vehicle_id": vk.loc[ok, "vehicle_id"], "h": h, "start": st[ok], "end": en[ok]}))
sem = pd.concat(rows, ignore_index=True).merge(veh[["vehicle_id", "gen", "first_seen", "cohorte_2024"]], on="vehicle_id")
sem["maint"] = flag_in_interval(sem, cm, "maint")
sem["conocido_antes"] = sem["first_seen"].notna() & (sem["first_seen"] < sem["start"])
sem["edad_meses_fin"] = sem["h"] * 6
semk = sem[sem["conocido_antes"]]
tab_sem = rate_table(semk, ["edad_meses_fin"], ["maint"]).rename(columns={"maint": "tasa_semestre"})
tab_sem_gen = semk.pivot_table(index="edad_meses_fin", columns="gen", values="maint", aggfunc="mean", observed=True).add_prefix("tasa_")
tab_sem = tab_sem.join(tab_sem_gen)
tab_sem["caída_pp"] = (tab_sem["tasa_semestre"].diff() * 100).round(1)
save_table(tab_sem, "A_curva_semestral", floatfmt=".3f")

# ----------------------------------------------------------------------------------------------
# B) insight del tutor: ¿cae fuerte al tercer año? ¿coincide con 100.000 km?
# ----------------------------------------------------------------------------------------------
print("\n" + "=" * 100)
print("B) INSIGHT DEL TUTOR")
print("=" * 100)
drops = tabA[["n_conocidos", "maint_conocidos"]].copy()
drops["caída_pp_vs_k-1"] = (drops["maint_conocidos"].diff() * 100).round(1)
drops["caída_relativa_%"] = (drops["maint_conocidos"].pct_change() * 100).round(1)
kmax = drops["caída_pp_vs_k-1"].idxmin()
print(f"Mayor caída absoluta (estimador conocidos): k={kmax} ({drops.loc[kmax, 'caída_pp_vs_k-1']} pp)")
save_table(drops, "B_caidas_por_k", floatfmt=".3f")

# km al momento del mantenimiento por año de vida (¿100.000 km alrededor del 3er año?)
cmk = cm.merge(veh[["vehicle_id", "wsd", "gen"]], on="vehicle_id")
cmk = cmk[cmk["wsd"].notna() & (cmk["event_date"] >= cmk["wsd"])]
cmk["k"] = (months_between(cmk["wsd"], cmk["event_date"]) // 12 + 1).clip(upper=12)
tab_km = cmk.groupby("k").agg(
    n=("KM", "size"), km_p25=("KM", lambda x: x.quantile(.25)), km_mediana=("KM", "median"), km_p75=("KM", lambda x: x.quantile(.75)),
    pct_km_ge_100k=("KM", lambda x: (x >= 100_000).mean()), pct_km_ge_150k=("KM", lambda x: (x >= 150_000).mean()),
    maint_number_mediana=("maint_number", "median"),
)
save_table(tab_km, "B_km_por_edad", floatfmt=".2f")
# km/año implícito y tiempo entre services
cmk["km_por_anio"] = cmk["KM"] / ((cmk["event_date"] - cmk["wsd"]).dt.days / 365.25).clip(lower=0.25)
gap = cm.groupby("vehicle_id")["event_date"].diff().dt.days
tab_gap = pd.DataFrame({
    "km/año implícito (KM / edad)": cmk["km_por_anio"].describe(percentiles=[.1, .25, .5, .75, .9]),
    "días entre mantenimientos consecutivos": gap.describe(percentiles=[.1, .25, .5, .75, .9]),
})
save_table(tab_gap, "B_km_anio_y_gap", floatfmt=".0f")

# ----------------------------------------------------------------------------------------------
# C) tasa base de churn según horizonte
# ----------------------------------------------------------------------------------------------
print("\n" + "=" * 100)
print("C) TASA BASE SEGÚN HORIZONTE (eventos índice: mantenimientos completados entre "
      f"{IDX_START.date()} y {IDX_END.date()})")
print("=" * 100)
idx = cm[(cm["event_date"] >= IDX_START) & (cm["event_date"] <= IDX_END)].copy().rename(columns={"event_date": "start"})
idx = idx.merge(veh[["vehicle_id", "wsd", "gen", "grupo"]], on="vehicle_id", how="left")
idx["next_maint"] = next_event_after(idx, cm, "next_maint")
idx["next_visita"] = next_event_after(idx, vis, "next_visita")
idx["next_no_maint"] = next_event_after(idx, vis_nomaint, "next_no_maint")
idx["edad_anios"] = (months_between(idx["wsd"], idx["start"]) // 12)
idx["edad_grp"] = pd.cut(idx["edad_anios"], [-1, 0, 1, 2, 3, 4, 5, 9, 99],
                         labels=["0 (1er año)", "1", "2", "3", "4", "5", "6-9", "10+"])
idx["maint_grp"] = pd.cut(idx["maint_number"], [0, 1, 2, 3, 4, 5, 6, 8, 10, 19, 20],
                          labels=["1", "2", "3", "4", "5", "6", "7-8", "9-10", "11-19", "20"])
HORIZ = [3, 6, 9, 10, 11, 12, 13, 14, 15]
for h in HORIZ:
    lim = add_months(idx["start"], h)
    idx[f"maint_{h}m"] = idx["next_maint"].notna() & (idx["next_maint"] <= lim)
    idx[f"visita_{h}m"] = idx["next_visita"].notna() & (idx["next_visita"] <= lim)
idx["dias_a_next"] = (idx["next_maint"] - idx["start"]).dt.days
print(f"eventos índice: {len(idx):,} en {idx['vehicle_id'].nunique():,} vehículos; sin WSD: {idx['wsd'].isna().sum():,}")
print(f"próximo mantenimiento a <30 días del índice: {(idx['dias_a_next'] < 30).sum():,} "
      f"({(idx['dias_a_next'] < 30).mean() * 100:.1f}% de los índices)")

tabC = pd.DataFrame({
    "horizonte_meses": HORIZ,
    "volvió_a_mantenimiento": [idx[f"maint_{h}m"].mean() for h in HORIZ],
    "churn_mantenimiento": [1 - idx[f"maint_{h}m"].mean() for h in HORIZ],
    "volvió_cualquier_visita_concluida": [idx[f"visita_{h}m"].mean() for h in HORIZ],
    "churn_red": [1 - idx[f"visita_{h}m"].mean() for h in HORIZ],
}).set_index("horizonte_meses")
# sensibilidad: ignorar retornos a <30 días (posibles duplicados / retrabajos)
for h in (12, 15):
    lim = add_months(idx["start"], h)
    strict = idx["next_maint"].notna() & (idx["next_maint"] <= lim) & (idx["dias_a_next"] >= 30)
    tabC.loc[h, "volvió_maint_excl_<30d"] = strict.mean()
tabC["n"] = len(idx)
save_table(tabC, "C_tasa_base_horizonte", floatfmt=".3f")

tabC_edad = rate_table(idx, ["edad_grp"], [f"maint_{h}m" for h in (6, 9, 12, 13, 15)] + ["visita_12m", "visita_15m"])
save_table(tabC_edad, "C_tasa_base_por_edad", floatfmt=".3f")
tabC_mn = rate_table(idx, ["maint_grp"], [f"maint_{h}m" for h in (6, 9, 12, 13, 15)] + ["visita_12m", "visita_15m"])
save_table(tabC_mn, "C_tasa_base_por_maint_number", floatfmt=".3f")
tabC_gen = rate_table(idx, ["gen"], [f"maint_{h}m" for h in (6, 12, 15)] + ["visita_15m"])
save_table(tabC_gen, "C_tasa_base_por_generacion", floatfmt=".3f")
tabC_grp = rate_table(idx, ["grupo"], [f"maint_{h}m" for h in (6, 12, 15)] + ["visita_15m"])
save_table(tabC_grp, "C_tasa_base_por_grupo_tabla", floatfmt=".3f")
# distribución del tiempo hasta el próximo mantenimiento (para los que volvieron en 15 meses)
tabC_gapq = idx.loc[idx["maint_15m"], "dias_a_next"].describe(percentiles=[.1, .25, .5, .75, .9]).to_frame("días hasta próximo mant. (volvieron ≤15m)")
save_table(tabC_gapq, "C_dias_hasta_proximo", floatfmt=".0f")

# curva mensual de retorno (1..15 meses) por grupo de edad
curve_rows = []
for h in range(1, 16):
    lim = add_months(idx["start"], h)
    hit_m = idx["next_maint"].notna() & (idx["next_maint"] <= lim)
    hit_v = idx["next_visita"].notna() & (idx["next_visita"] <= lim)
    r = {"h": h, "total_maint": hit_m.mean(), "total_visita": hit_v.mean()}
    for g, sub in idx.groupby("edad_grp", observed=True):
        r[f"edad_{g}"] = hit_m[sub.index].mean()
    curve_rows.append(r)
curveC = pd.DataFrame(curve_rows).set_index("h")
save_table(curveC, "C_curva_retorno_mensual", floatfmt=".3f")

# ----------------------------------------------------------------------------------------------
# D) cohorte de ventas 2024: primer mantenimiento
# ----------------------------------------------------------------------------------------------
print("\n" + "=" * 100)
print("D) COHORTE VENTAS 2024 — PRIMER MANTENIMIENTO")
print("=" * 100)
coh = veh[veh["cohorte_2024"]].copy()
coh["start"] = coh["wsd"]
n_coh_total = len(coh)
coh = coh[add_months(coh["wsd"], 18) <= CUTOFF]
print(f"cohorte ventas 2024 con WSD: {n_coh_total:,}; con 18 meses de seguimiento completos (WSD ≤ {(CUTOFF - pd.DateOffset(months=18)).date()}): {len(coh):,}")
coh["first_maint"] = next_event_after(coh, cm, "first_maint")
cm1 = cm[cm["maint_number"] == 1][["vehicle_id", "event_date"]]
coh["first_maint1"] = next_event_after(coh, cm1, "first_maint1")
coh["first_visita"] = next_event_after(coh, vis, "first_visita")
coh["first_turno"] = next_event_after(coh, any_appt, "first_turno")
HD = [6, 9, 12, 13, 15, 18]
for h in HD:
    lim = add_months(coh["wsd"], h)
    coh[f"maint_{h}m"] = coh["first_maint"].notna() & (coh["first_maint"] <= lim)
    coh[f"maint1_{h}m"] = coh["first_maint1"].notna() & (coh["first_maint1"] <= lim)
    coh[f"visita_{h}m"] = coh["first_visita"].notna() & (coh["first_visita"] <= lim)
    coh[f"turno_{h}m"] = coh["first_turno"].notna() & (coh["first_turno"] <= lim)
tabD = pd.DataFrame({
    "horizonte_meses": HD,
    "≥1 mantenimiento completado": [coh[f"maint_{h}m"].mean() for h in HD],
    "1° mantenimiento (maint_number=1)": [coh[f"maint1_{h}m"].mean() for h in HD],
    "≥1 visita concluida (cualquier tipo)": [coh[f"visita_{h}m"].mean() for h in HD],
    "≥1 turno (cualquier estado)": [coh[f"turno_{h}m"].mean() for h in HD],
}).set_index("horizonte_meses")
tabD["n"] = len(coh)
save_table(tabD, "D_cohorte24_primer_service", floatfmt=".3f")
for col, nm in [("PersonType", "D_cohorte24_por_persontype"), ("BusinessUnit", "D_cohorte24_por_businessunit"),
                ("SalesChannel", "D_cohorte24_por_saleschannel"), ("gen", "D_cohorte24_por_generacion")]:
    t = rate_table(coh, [col], ["maint_12m", "maint_13m", "maint_15m", "maint_18m", "visita_18m"])
    save_table(t, nm, floatfmt=".3f")
coh["meses_a_1er_maint"] = months_between(coh["wsd"], coh["first_maint"])
curveD = pd.DataFrame({"mes": range(1, 19)})
curveD["total"] = [coh["first_maint"].notna().mul(coh["first_maint"] <= add_months(coh["wsd"], m)).mean() for m in curveD["mes"]]
for col in ("BusinessUnit", "PersonType"):
    for g, sub in coh.groupby(col, observed=True):
        curveD[f"{col}={g}"] = [(sub["first_maint"].notna() & (sub["first_maint"] <= add_months(sub["wsd"], m))).mean() for m in curveD["mes"]]
curveD = curveD.set_index("mes")
save_table(curveD, "D_cohorte24_curva_acumulada", floatfmt=".3f")
print("meses hasta el 1er mantenimiento (los que lo hicieron ≤18m):\n",
      coh.loc[coh["maint_18m"], "meses_a_1er_maint"].describe(percentiles=[.1, .25, .5, .75, .9]).round(1).to_string())

# ----------------------------------------------------------------------------------------------
# E) población en ventana por mes
# ----------------------------------------------------------------------------------------------
print("\n" + "=" * 100)
print("E) POBLACIÓN QUE CUMPLE 12 MESES SIN MANTENIMIENTO, POR MES")
print("=" * 100)
# ciclos: (i) desde cada mantenimiento completado observado; (ii) desde WSD para vehículos con WSD >= START
cyc_m = cm[["vehicle_id", "event_date", "customer_id"]].rename(columns={"event_date": "start", "customer_id": "cust_idx"})
cyc_m["origen"] = "tras un mantenimiento"
cyc_w = veh.loc[veh["wsd"] >= START, ["vehicle_id", "wsd"]].rename(columns={"wsd": "start"})
cyc_w["origen"] = "desde inicio de garantía (nunca fue)"
cyc_w["cust_idx"] = np.nan
cyc = pd.concat([cyc_m, cyc_w], ignore_index=True)
cyc["next_maint"] = next_event_after(cyc, cm, "next_maint")
cyc["due12"] = add_months(cyc["start"], 12)
cyc = cyc[cyc["due12"] <= CUTOFF].copy()
cyc["mes"] = cyc["due12"].dt.to_period("M")
cyc["volvió_antes_12m"] = cyc["next_maint"].notna() & (cyc["next_maint"] < cyc["due12"])
cyc["llegó_a_12m_sin_service"] = ~cyc["volvió_antes_12m"]
cyc["seguimiento_1m_completo"] = add_months(cyc["due12"], 1) <= CUTOFF
cyc["seguimiento_3m_completo"] = add_months(cyc["due12"], 3) <= CUTOFF
cyc["seguimiento_6m_completo"] = add_months(cyc["due12"], 6) <= CUTOFF
cyc["volvió_≤1m_después"] = cyc["next_maint"].notna() & (cyc["next_maint"] <= add_months(cyc["due12"], 1)) & cyc["llegó_a_12m_sin_service"]
cyc["volvió_≤3m_después"] = cyc["next_maint"].notna() & (cyc["next_maint"] <= add_months(cyc["due12"], 3)) & cyc["llegó_a_12m_sin_service"]
cyc["volvió_≤6m_después"] = cyc["next_maint"].notna() & (cyc["next_maint"] <= add_months(cyc["due12"], 6)) & cyc["llegó_a_12m_sin_service"]
cyc["volvió_hasta_cutoff"] = cyc["next_maint"].notna() & cyc["llegó_a_12m_sin_service"]
cyc = cyc[cyc["mes"] >= pd.Period("2025-01", "M")]
g = cyc.groupby("mes")
tabE = pd.DataFrame({
    "ciclos_que_vencen": g.size(),
    "volvieron_antes_12m": g["volvió_antes_12m"].sum(),
    "en_ventana_12m_sin_service": g["llegó_a_12m_sin_service"].sum(),
})
tabE["pct_en_ventana"] = tabE["en_ventana_12m_sin_service"] / tabE["ciclos_que_vencen"]
w = cyc[cyc["llegó_a_12m_sin_service"]]
gw = w.groupby("mes")
tabE["de_los_en_ventana: volvió_≤1m"] = gw["volvió_≤1m_después"].mean().where(gw["seguimiento_1m_completo"].all())
tabE["de_los_en_ventana: volvió_≤3m"] = gw["volvió_≤3m_después"].mean().where(gw["seguimiento_3m_completo"].all())
tabE["de_los_en_ventana: volvió_≤6m"] = gw["volvió_≤6m_después"].mean().where(gw["seguimiento_6m_completo"].all())
tabE["de_los_en_ventana: volvió_hasta_cutoff"] = gw["volvió_hasta_cutoff"].mean()
tabE["vehículos_únicos_en_ventana"] = gw["vehicle_id"].nunique()
tabE.index = tabE.index.astype(str)
save_table(tabE, "E_poblacion_mensual", floatfmt=".3f")
tabE_or = cyc.groupby(["origen"]).agg(
    ciclos=("vehicle_id", "size"), en_ventana=("llegó_a_12m_sin_service", "sum"),
    pct_en_ventana=("llegó_a_12m_sin_service", "mean"),
)
wf = w[w["seguimiento_3m_completo"]]
tabE_or["volvió_≤1m (seguim. completo)"] = w[w["seguimiento_1m_completo"]].groupby("origen")["volvió_≤1m_después"].mean()
tabE_or["volvió_≤3m (seguim. completo)"] = wf.groupby("origen")["volvió_≤3m_después"].mean()
tabE_or["volvió_hasta_cutoff"] = w.groupby("origen")["volvió_hasta_cutoff"].mean()
save_table(tabE_or, "E_poblacion_por_origen", floatfmt=".3f")
# promedio mensual de 2025 (meses completos con seguimiento 3m) para dimensionar capacidad
full = tabE[tabE["de_los_en_ventana: volvió_≤3m"].notna()]
print(f"Meses con seguimiento de 3 meses completo: {full.index[0]} → {full.index[-1]}; "
      f"promedio mensual en ventana: {full['en_ventana_12m_sin_service'].mean():,.0f} vehículos "
      f"(ciclos que vencen: {full['ciclos_que_vencen'].mean():,.0f}); "
      f"retorno ≤1m promedio: {full['de_los_en_ventana: volvió_≤1m'].mean():.3f}; "
      f"retorno ≤3m promedio: {full['de_los_en_ventana: volvió_≤3m'].mean():.3f}")

# ----------------------------------------------------------------------------------------------
# F) recurrencia: churn temporario vs definitivo
# ----------------------------------------------------------------------------------------------
print("\n" + "=" * 100)
print("F) RECURRENCIA TRAS 15 MESES SIN MANTENIMIENTO")
print("=" * 100)
cyc_all = pd.concat([cyc_m, cyc_w], ignore_index=True)
cyc_all["next_maint"] = next_event_after(cyc_all, cm, "next_maint")
cyc_all["next_no_maint"] = next_event_after(cyc_all, vis_nomaint, "next_no_maint")
cyc_all["mark15"] = add_months(cyc_all["start"], 15)
ch = cyc_all[(cyc_all["mark15"] <= CUTOFF) & (cyc_all["start"] >= START)].copy()
ch["churn15"] = ch["next_maint"].isna() | (ch["next_maint"] > ch["mark15"])
print(f"ciclos con 15 meses completos de seguimiento: {len(ch):,}; churn a 15 meses: {ch['churn15'].sum():,} ({ch['churn15'].mean():.3f})")
chu = ch[ch["churn15"]].copy()
chu["seguimiento_extra_meses"] = months_between(chu["mark15"], pd.Series(CUTOFF, index=chu.index))
chu["reapareció"] = chu["next_maint"].notna()
chu["meses_tras_mark15"] = months_between(chu["mark15"], chu["next_maint"])
chu["visita_no_maint_después_idx"] = chu["next_no_maint"].notna()
pend = ap[ap["pending"] & (ap["ScheduleDate"] > CUTOFF)]["vehicle_id"].unique()
chu["turno_futuro_agendado"] = chu["vehicle_id"].isin(pend)
rows = []
for h in (3, 6, 9, 12, 15):
    sub = chu[chu["seguimiento_extra_meses"] >= h]
    rows.append({"meses_extra_de_seguimiento": h, "n_churners_observables": len(sub),
                 "reaparecieron_≤h": (sub["meses_tras_mark15"] <= h).mean()})
tabF = pd.DataFrame(rows).set_index("meses_extra_de_seguimiento")
save_table(tabF, "F_reaparicion", floatfmt=".3f")
tabF2 = pd.DataFrame({
    "churners a 15m": [len(chu)],
    "reaparecieron con mantenimiento (hasta CUTOFF)": [chu["reapareció"].mean()],
    "tuvieron visita concluida NO mantenimiento tras el índice": [chu["visita_no_maint_después_idx"].mean()],
    "tienen turno futuro agendado (> CUTOFF)": [chu["turno_futuro_agendado"].mean()],
    "seguimiento extra mediano (meses)": [chu["seguimiento_extra_meses"].median()],
}).T.rename(columns={0: "valor"})
save_table(tabF2, "F_churners_resumen", floatfmt=".3f")
tabF_or = chu.groupby("origen").agg(n=("vehicle_id", "size"), reapareció=("reapareció", "mean"),
                                   visita_no_maint=("visita_no_maint_después_idx", "mean"), turno_futuro=("turno_futuro_agendado", "mean"))
save_table(tabF_or, "F_por_origen", floatfmt=".3f")

# cambio de cliente al reaparecer (transferencia de titularidad) — solo ciclos tras un mantenimiento
cust_next = cm_all.sort_values(["vehicle_id", "event_date"]).drop_duplicates(["vehicle_id", "event_date"])[["vehicle_id", "event_date", "customer_id"]]
ret = ch[ch["origen"] == "tras un mantenimiento"].dropna(subset=["next_maint"]).merge(
    cust_next.rename(columns={"event_date": "next_maint", "customer_id": "cust_next"}), on=["vehicle_id", "next_maint"], how="left")
ret["cambio_cliente"] = ret["cust_idx"].notna() & ret["cust_next"].notna() & (ret["cust_idx"] != ret["cust_next"])
tabF_cust = ret.groupby("churn15").agg(n_volvieron=("vehicle_id", "size"), pct_cambio_customer_id=("cambio_cliente", "mean"))
tabF_cust.index = tabF_cust.index.map({False: "volvió ≤15m", True: "volvió >15m (churn temporario)"})
save_table(tabF_cust, "F_cambio_cliente", floatfmt=".3f")

# retorno acumulado 1..24 meses para índices con 24 meses de seguimiento (2024-01-01 .. CUTOFF-24m)
idx24 = cyc_all[(cyc_all["start"] >= START) & (add_months(cyc_all["start"], 24) <= CUTOFF)]
rows = []
for h in range(1, 25):
    lim = add_months(idx24["start"], h)
    hit = idx24["next_maint"].notna() & (idx24["next_maint"] <= lim)
    r = {"h": h, "total": hit.mean()}
    for o, sub in idx24.groupby("origen"):
        r[o] = hit[sub.index].mean()
    rows.append(r)
curveF = pd.DataFrame(rows).set_index("h")
curveF["n"] = len(idx24)
save_table(curveF.loc[[3, 6, 9, 12, 15, 18, 21, 24]], "F_retorno_acumulado_24m", floatfmt=".3f")
curveF.to_csv(TAB_DIR / f"{PREFIX}_F_retorno_acumulado_24m_completa.csv")

# ----------------------------------------------------------------------------------------------
# FIGURAS
# ----------------------------------------------------------------------------------------------
print("\n" + "=" * 100)
print("FIGURAS")
print("=" * 100)

# 1) curva de retención por edad (la figura del pitch)
fig, axes = plt.subplots(1, 2, figsize=(13, 5))
ax = axes[0]
ax.plot(tabA.index, tabA["maint_todos"] * 100, "o--", color=PALETTE[6], label="Todos los vehículos con garantía (agenda ∪ ventas; sesgado)")
# k=1 del estimador "conocidos" (n=1.295, turno previo al inicio de garantía) no es representativo: se omite en la figura.
conoc_plot = tabA["maint_conocidos"].where(tabA.index >= 2)
ax.plot(tabA.index, conoc_plot * 100, "o-", color=PALETTE[0], lw=2.5, label="Vehículos ya conocidos por la red antes del año k (k ≥ 2)")
ax.plot(tabA.index, tabA["maint_cohorte24"] * 100, "s-", color=PALETTE[1], lw=2.5, label="Cohorte ventas 2024 (población completa)")
for k, r in tabA.iterrows():
    if pd.notna(conoc_plot.loc[k]):
        ax.annotate(f"{r['maint_conocidos'] * 100:.0f}%", (k, r["maint_conocidos"] * 100), textcoords="offset points", xytext=(0, 7), ha="center", fontsize=8, color=PALETTE[0])
    if pd.notna(r["maint_cohorte24"]):
        ax.annotate(f"{r['maint_cohorte24'] * 100:.0f}%", (k, r["maint_cohorte24"] * 100), textcoords="offset points", xytext=(0, -13), ha="center", fontsize=8, color=PALETTE[1])
ax.set_xticks(range(1, 13)); ax.set_ylim(0, 100)
ax.set_xlabel("Año de vida del vehículo (k = entre aniversario k-1 y k de inicio de garantía)")
ax.set_ylabel("% de vehículos con ≥1 mantenimiento completado en el año k")
ax.set_title("Retención en la red oficial por año de vida")
ax.legend(fontsize=8, loc="upper right")
ax = axes[1]
ax.plot(tabA.index, tabA["P(maint k | maint k-1)"] * 100, "o-", color=PALETTE[2], lw=2.5, label="Hizo mantenimiento en el año k-1")
ax.plot(tabA.index, tabA["P(maint k | sin maint k-1)"] * 100, "o-", color=PALETTE[3], lw=2.5, label="NO hizo mantenimiento en el año k-1")
for k, r in tabA.iterrows():
    if pd.notna(r["P(maint k | maint k-1)"]):
        ax.annotate(f"{r['P(maint k | maint k-1)'] * 100:.0f}%", (k, r["P(maint k | maint k-1)"] * 100), textcoords="offset points", xytext=(0, 7), ha="center", fontsize=8, color=PALETTE[2])
    if pd.notna(r["P(maint k | sin maint k-1)"]):
        ax.annotate(f"{r['P(maint k | sin maint k-1)'] * 100:.0f}%", (k, r["P(maint k | sin maint k-1)"] * 100), textcoords="offset points", xytext=(0, -13), ha="center", fontsize=8, color=PALETTE[3])
ax.set_xticks(range(1, 13)); ax.set_ylim(0, 100)
ax.set_xlabel("Año de vida del vehículo (k)")
ax.set_ylabel("% con ≥1 mantenimiento completado en el año k")
ax.set_title("Retención condicional al comportamiento del año anterior")
ax.legend(fontsize=8, loc="upper right")
savefig(fig, "curva_edad")

# 2) desagregaciones (estimador conocidos)
fig, axes = plt.subplots(2, 2, figsize=(13, 9))
for ax, (col, title) in zip(axes.ravel(), [("gen", "Por generación"), ("my_grp", "Por ModelYear"), ("zone", "Por DealerStateOrZone"), ("grupo", "Por presencia en tablas")]):
    t = known.pivot_table(index="k", columns=col, values="maint", aggfunc="mean", observed=True)
    n = known.pivot_table(index="k", columns=col, values="maint", aggfunc="size", observed=True)
    for i, c in enumerate(t.columns):
        ok = n[c] >= 200
        ax.plot(t.index[ok], t[c][ok] * 100, "o-", color=PALETTE[i % len(PALETTE)], label=str(c))
    ax.set_xticks(range(1, 13)); ax.set_ylim(0, 100)
    ax.set_title(f"{title} — conocidos antes del año k (puntos con n≥200)")
    ax.set_xlabel("Año de vida (k)"); ax.set_ylabel("% con ≥1 mantenimiento en el año")
    ax.legend(fontsize=8)
savefig(fig, "curva_edad_grupos")

# 3) cohorte ventas 2024 por atributos de venta (k=1 y k=2)
fig, axes = plt.subplots(1, 3, figsize=(14, 4.5))
for ax, col in zip(axes, ["PersonType", "BusinessUnit", "SalesChannel"]):
    t = life[life["cohorte_2024"]].pivot_table(index=col, columns="k", values="maint", aggfunc="mean", observed=True) * 100
    n = life[life["cohorte_2024"]].pivot_table(index=col, columns="k", values="maint", aggfunc="size", observed=True)
    t = t.loc[n[1] >= 100, [1, 2]]
    t.plot.bar(ax=ax, color=[PALETTE[0], PALETTE[1]], rot=0)
    for p in ax.patches:
        ax.annotate(f"{p.get_height():.0f}", (p.get_x() + p.get_width() / 2, p.get_height()), ha="center", va="bottom", fontsize=8)
    ax.set_ylim(0, 100); ax.set_title(f"Cohorte ventas 2024 — por {col}"); ax.set_xlabel(""); ax.set_ylabel("% con ≥1 mantenimiento en el año k")
    ax.legend(title="Año de vida", labels=[f"k={c}" for c in t.columns], fontsize=8)
savefig(fig, "cohorte24_atributos")

# 4) curva semestral + caídas
fig, axes = plt.subplots(1, 2, figsize=(13, 4.8))
ax = axes[0]
ax.plot(tab_sem.index, tab_sem["tasa_semestre"] * 100, "o-", color=PALETTE[0], lw=2.5, label="Todos (conocidos antes del semestre)")
for i, c in enumerate([c for c in tab_sem.columns if c.startswith("tasa_P")]):
    ax.plot(tab_sem.index, tab_sem[c] * 100, "o--", color=PALETTE[i + 1], label=c.replace("tasa_", ""))
ax.axvline(36, color="grey", ls=":", lw=1); ax.text(36.5, 5, "36 meses", fontsize=8, color="grey")
ax.set_xlabel("Edad del vehículo al cierre del semestre (meses)"); ax.set_ylabel("% con ≥1 mantenimiento en el semestre")
ax.set_title("Retención por semestre de vida"); ax.legend(fontsize=8)
ax.set_xticks(tab_sem.index[::2]); ax.set_ylim(0, 100)
ax = axes[1]
ax.bar(drops.index, drops["caída_pp_vs_k-1"].fillna(0), color=[PALETTE[1] if v == drops["caída_pp_vs_k-1"].min() else PALETTE[6] for v in drops["caída_pp_vs_k-1"]])
for k, v in drops["caída_pp_vs_k-1"].items():
    if pd.notna(v):
        ax.annotate(f"{v:+.1f}", (k, v), ha="center", va="top" if v < 0 else "bottom", fontsize=8)
ax.set_xticks(range(1, 13)); ax.set_xlabel("Año de vida (k)"); ax.set_ylabel("Cambio en la tasa vs. año k-1 (puntos porcentuales)")
ax.set_title("¿Dónde está la mayor caída? (estimador conocidos)")
savefig(fig, "quiebre_tercer_anio")

# 5) tasa base según horizonte
fig, axes = plt.subplots(1, 2, figsize=(13, 4.8))
ax = axes[0]
ax.plot(curveC.index, curveC["total_maint"] * 100, "o-", color=PALETTE[0], lw=2.5, label="Volvió a hacer un mantenimiento")
ax.plot(curveC.index, curveC["total_visita"] * 100, "s--", color=PALETTE[2], lw=2, label="Volvió a la red (cualquier visita concluida)")
for h in (6, 12, 15):
    ax.annotate(f"{curveC.loc[h, 'total_maint'] * 100:.0f}%", (h, curveC.loc[h, "total_maint"] * 100), textcoords="offset points", xytext=(0, -14), ha="center", fontsize=9, color=PALETTE[0])
ax.axvline(12, color="grey", ls=":", lw=1)
ax.set_xlabel("Meses desde el mantenimiento índice"); ax.set_ylabel("% de eventos índice con retorno ≤ h meses")
ax.set_title(f"Retorno acumulado tras un mantenimiento (n={len(idx):,} eventos)"); ax.legend(fontsize=8); ax.set_ylim(0, 100)
ax.set_xticks(range(1, 16))
ax = axes[1]
for i, c in enumerate([c for c in curveC.columns if c.startswith("edad_")]):
    ax.plot(curveC.index, curveC[c] * 100, "o-", color=PALETTE[i % len(PALETTE)], label=c.replace("edad_", "edad ") + " años")
ax.axvline(12, color="grey", ls=":", lw=1)
ax.set_xlabel("Meses desde el mantenimiento índice"); ax.set_ylabel("% con próximo mantenimiento ≤ h meses")
ax.set_title("Retorno acumulado por edad del vehículo al evento"); ax.legend(fontsize=8, ncol=2); ax.set_ylim(0, 100)
ax.set_xticks(range(1, 16))
savefig(fig, "tasa_base_horizonte")

# 6) cohorte 2024: tiempo al primer mantenimiento
fig, ax = plt.subplots(figsize=(8.5, 5))
ax.plot(curveD.index, curveD["total"] * 100, "o-", color=PALETTE[0], lw=2.5, label=f"Cohorte completa (n={len(coh):,})")
for i, c in enumerate([c for c in curveD.columns if c != "total"]):
    ax.plot(curveD.index, curveD[c] * 100, "--", color=PALETTE[i + 1], label=c)
for h in (12, 18):
    ax.annotate(f"{curveD.loc[h, 'total'] * 100:.0f}%", (h, curveD.loc[h, "total"] * 100), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=9)
ax.axvline(12, color="grey", ls=":", lw=1)
ax.set_xlabel("Meses desde el inicio de garantía"); ax.set_ylabel("% de la cohorte con ≥1 mantenimiento completado")
ax.set_title("Cohorte de ventas 2024: tiempo hasta el primer mantenimiento"); ax.legend(fontsize=8); ax.set_ylim(0, 100)
ax.set_xticks(range(1, 19))
savefig(fig, "cohorte24_primer_service")

# 7) población mensual en ventana
fig, ax = plt.subplots(figsize=(12, 5))
x = np.arange(len(tabE))
ax.bar(x, tabE["volvieron_antes_12m"], color=PALETTE[6], label="Volvieron antes de los 12 meses (no entran en ventana)")
ax.bar(x, tabE["en_ventana_12m_sin_service"], bottom=tabE["volvieron_antes_12m"], color=PALETTE[1], label="Cumplen 12 meses sin mantenimiento (población en ventana)")
for i, v in enumerate(tabE["en_ventana_12m_sin_service"]):
    ax.annotate(f"{int(v):,}".replace(",", "."), (i, tabE["ciclos_que_vencen"].iloc[i]), ha="center", va="bottom", fontsize=7, color=PALETTE[1])
ax.set_xticks(x); ax.set_xticklabels(tabE.index, rotation=60, fontsize=8)
ax.set_ylabel("Ciclos que cumplen 12 meses en el mes")
ax.set_title("Población que cumple 12 meses desde su último mantenimiento (o desde la garantía), por mes")
ax2 = ax.twinx()
ax2.plot(x, tabE["de_los_en_ventana: volvió_≤3m"] * 100, "o-", color=PALETTE[0], label="% de los en ventana que volvió en ≤3 meses (solo meses con seguimiento completo)")
ax2.set_ylim(0, 60); ax2.set_ylabel("% que volvió en ≤3 meses"); ax2.grid(False)
h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
ax.legend(h1 + h2, l1 + l2, fontsize=8, loc="upper left")
savefig(fig, "poblacion_mensual")

# 8) recurrencia
fig, axes = plt.subplots(1, 2, figsize=(13, 4.8))
ax = axes[0]
ax.plot(curveF.index, curveF["total"] * 100, "o-", color=PALETTE[0], lw=2.5, label="Todos los ciclos")
for i, o in enumerate([c for c in curveF.columns if c not in ("total", "n")]):
    ax.plot(curveF.index, curveF[o] * 100, "--", color=PALETTE[i + 1], label=o)
for h in (12, 15, 24):
    ax.annotate(f"{curveF.loc[h, 'total'] * 100:.0f}%", (h, curveF.loc[h, "total"] * 100), textcoords="offset points", xytext=(0, 8), ha="center", fontsize=9)
ax.axvline(15, color="grey", ls=":", lw=1)
ax.set_xlabel("Meses desde el inicio del ciclo"); ax.set_ylabel("% con próximo mantenimiento ≤ h meses")
ax.set_title(f"Retorno acumulado a 24 meses (ciclos iniciados hasta {(CUTOFF - pd.DateOffset(months=24)).date()}, n={len(idx24):,})")
ax.legend(fontsize=8); ax.set_ylim(0, 100); ax.set_xticks(range(0, 25, 3))
ax = axes[1]
ax.bar(tabF.index.astype(str), tabF["reaparecieron_≤h"] * 100, color=PALETTE[3])
for i, (h, r) in enumerate(tabF.iterrows()):
    ax.annotate(f"{r['reaparecieron_≤h'] * 100:.1f}%\n(n={int(r['n_churners_observables']):,})", (i, r["reaparecieron_≤h"] * 100), ha="center", va="bottom", fontsize=8)
ax.set_xlabel("Meses adicionales de seguimiento después del mes 15"); ax.set_ylabel("% de churners (15 m) que reaparecieron")
ax.set_title("Churn temporario: reaparición después de 15 meses sin mantenimiento"); ax.set_ylim(0, 40)
savefig(fig, "recurrencia")

print("\nListo.")
