"""EDA 01 - Taxonomía de eventos de la Agenda y definición de "mantenimiento programado completado".

Genera TODAS las tablas y figuras citadas en reports/eda/01_taxonomia_target.md:
- tablas  -> reports/eda/01_taxonomia_target_tablas.md (apéndice generado) + stdout
- figuras -> reports/figures/eda/01_taxonomia_target_*.png

Ejecutar desde la carpeta del proyecto:
    PYTHONIOENCODING=utf8 PYTHONPATH=src .venv/Scripts/python.exe scripts/eda/01_taxonomia_target.py

No modifica los datos crudos ni los parquet de data/interim.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from repurchase import config
from repurchase.eventos import CUTOFF, appointments
from repurchase.io import load_agenda, load_sales

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 60)

FIG_DIR = config.FIGURES_DIR / "eda"
FIG_DIR.mkdir(parents=True, exist_ok=True)
TABLES_MD = config.REPORTS_DIR / "eda" / "01_taxonomia_target_tablas.md"
TABLES_MD.parent.mkdir(parents=True, exist_ok=True)
PREFIX = "01_taxonomia_target_"

S60, S90, S80, S70, S30, S40 = (
    "(60) Concluido", "(90) Concluido sin OS", "(80) No asistio", "(70) Cancelado", "(30) Agendado", "(40) En progreso",
)
STATUS_ORDER = [S30, S40, S60, S70, S80, S90]

_sections: list[str] = []


def emit(title: str, obj, note: str | None = None) -> None:
    """Imprime y acumula una tabla (DataFrame/Series) o texto en el apéndice markdown."""
    print(f"\n### {title}")
    if isinstance(obj, pd.Series):
        obj = obj.to_frame()
    if isinstance(obj, pd.DataFrame):
        body = obj.to_markdown()
    else:
        body = str(obj)
    print(body)
    if note:
        print(note)
    _sections.append(f"### {title}\n\n{body}\n" + (f"\n{note}\n" if note else ""))


def savefig(fig, name: str) -> Path:
    path = FIG_DIR / f"{PREFIX}{name}.png"
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    print(f"[fig] {path}")
    return path


def pct(x: float) -> str:
    return f"{100 * x:.1f}%"


# ---------------------------------------------------------------------------------------------
# 0. Carga
# ---------------------------------------------------------------------------------------------
raw = load_agenda()
n_raw = len(raw)
a = raw.drop_duplicates().reset_index(drop=True)
n_dup = n_raw - len(a)
del raw
sales = load_sales()
ap = appointments(a)  # una fila por schedule_id, flags de eventos.py

emit("0.1 Volumen", pd.DataFrame({
    "valor": [n_raw, n_dup, len(a), a["schedule_id"].nunique(), len(ap), a["vehicle_id"].nunique(), str(CUTOFF.date())]
}, index=["filas agenda (ítems)", "filas totalmente duplicadas eliminadas", "filas ítem tras dedup",
          "turnos (schedule_id)", "filas tabla appointments()", "vehículos con turno", "CUTOFF"]))

st_tab = ap["StatusARG"].value_counts().reindex(STATUS_ORDER).to_frame("turnos")
st_tab["%"] = (100 * st_tab["turnos"] / len(ap)).round(1)
emit("0.2 Turnos por StatusARG", st_tab)

# Columnas de nivel turno que varían dentro de un schedule_id (control de la agregación de eventos.py)
lvl = ["vehicle_id", "customer_id", "dealer_id", "StatusARG", "ScheduleDate", "ScheduleSource", "IsReschedule",
       "ScheduleReturn", "KM", "VehicleCurrentKM", "EffectiveCheckinDate", "EffectiveCheckoutDate", "DaysInDealer"]
nun = a.groupby("schedule_id")[lvl].nunique(dropna=False)
emit("0.3 schedule_id con más de un valor en columnas de nivel turno", (nun > 1).sum().to_frame("schedule_ids con >1 valor"),
     note="StatusARG varía en 4 turnos (mezcla (70)/(80) en ítems sin tipo): irrelevante en volumen.")

# ---------------------------------------------------------------------------------------------
# 1. Taxonomía de ítems y combinaciones por turno  (pregunta a)
# ---------------------------------------------------------------------------------------------
st = a["ServiceType"].fillna("SIN_TIPO")
name = a["ServiceName"].fillna("")
a["item_class"] = np.select(
    [
        a["ServiceMaintenance"].notna(),
        name.eq("Guarantee"),
        name.eq("Contactless service"),
        st.str.lower().eq("campañas de servicio"),
        st.eq("Diagnóstico"),
        st.eq("Reparación"),
        name.eq("Oil and filter change"),
        name.isin(["Inspección Ford", "Revision de Viaje"]),
        st.eq("Servicios Generales"),
        st.eq("Pick Up & Delivery"),
        st.isin(["Mobile Service", "Taller Móvil"]),
        st.eq("SIN_TIPO"),
    ],
    ["MANT", "GARANTIA", "CONTACTLESS", "CAMPANA_RECALL", "DIAG", "REPAR", "ACEITE_FILTRO", "INSPECCION",
     "SERV_GRAL", "PUD", "MOVIL", "SIN_ITEM"],
    default="OTRO",  # Accesorios, Alineación/Balanceo/Cubiertas, Chapa y Pintura, Lavado
)
cls_tab = (a.groupby(["item_class", "ServiceType"], dropna=False).size().reset_index(name="ítems")
           .sort_values("ítems", ascending=False))
cls_tab["ServiceType"] = cls_tab["ServiceType"].fillna("(nulo)")
emit("1.1 Clase de ítem asignada a cada ServiceType (filas ítem, tras dedup)", cls_tab.reset_index(drop=True))

# chequeo: todo ítem con ServiceMaintenance no nulo es ServiceType Mantenimiento y viceversa (menos Guarantee/Contactless)
chk = pd.DataFrame({
    "ítems con ServiceMaintenance no nulo": [a["ServiceMaintenance"].notna().sum()],
    "... de los cuales ServiceType != Mantenimiento": [(a["ServiceMaintenance"].notna() & ~a["ServiceType"].eq("Mantenimiento")).sum()],
    "ítems 'Maintenance service/review' sin número": [(name.str.contains("Maintenance (?:service|review)", regex=True) & a["ServiceMaintenance"].isna()).sum()],
    "ítems ServiceType Mantenimiento sin número (Guarantee+Contactless)": [(a["ServiceType"].eq("Mantenimiento") & a["ServiceMaintenance"].isna()).sum()],
}).T.rename(columns={0: "n"})
emit("1.2 Consistencia ServiceMaintenance vs ServiceName/ServiceType", chk)

item_sets = a.groupby("schedule_id")["item_class"].agg(lambda s: frozenset(s))
ap = ap.set_index("schedule_id")
ap["combo"] = item_sets.map(lambda s: "+".join(sorted(s)))
for c in ["MANT", "GARANTIA", "CONTACTLESS", "CAMPANA_RECALL", "DIAG", "REPAR", "ACEITE_FILTRO", "INSPECCION",
          "SERV_GRAL", "PUD", "MOVIL", "OTRO", "SIN_ITEM"]:
    ap[f"i_{c}"] = item_sets.map(lambda s, c=c: c in s)
ap = ap.reset_index()
assert (ap["i_MANT"] == ap["has_maint"]).all(), "has_maint de eventos.py no coincide con la clase MANT"

combo_ct = pd.crosstab(ap["combo"], ap["StatusARG"]).reindex(columns=STATUS_ORDER, fill_value=0)
combo_ct["total"] = combo_ct.sum(axis=1)
combo_ct["% turnos"] = (100 * combo_ct["total"] / len(ap)).round(1)
combo_top = combo_ct.sort_values("total", ascending=False).head(15)
emit("1.3 Las 15 combinaciones de ítems más frecuentes por turno y su StatusARG",
     combo_top, note=f"Combinaciones distintas: {combo_ct.shape[0]}. Las 15 primeras cubren {pct(combo_top['total'].sum() / len(ap))} de los turnos.")

fig, ax = plt.subplots(figsize=(11, 6.5))
plot_df = combo_top[STATUS_ORDER].iloc[::-1]
left = np.zeros(len(plot_df))
for s_ in STATUS_ORDER:
    ax.barh(plot_df.index, plot_df[s_], left=left, label=s_)
    left += plot_df[s_].values
ax.set_xlabel("Turnos")
ax.set_ylabel("Combinación de ítems del turno")
ax.set_title("Las 15 combinaciones de ítems más frecuentes, por estado del turno")
ax.legend(loc="lower right", fontsize=8)
savefig(fig, "combos_status")

# Definición preliminar
icm = ap["is_completed_maintenance"]
emit("1.4 Definición preliminar is_completed_maintenance = (60) Concluido & algún ítem con ServiceMaintenance", pd.DataFrame({
    "turnos": [icm.sum(), ap["completed"].sum(), (ap["completed"] & ~ap["has_maint"]).sum()],
    "vehículos": [ap.loc[icm, "vehicle_id"].nunique(), ap.loc[ap["completed"], "vehicle_id"].nunique(),
                  ap.loc[ap["completed"] & ~ap["has_maint"], "vehicle_id"].nunique()],
}, index=["(60) & has_maint  [target preliminar]", "(60) cualquier ítem", "(60) sin ítem de mantenimiento"]))

# Composición del target preliminar por combo
tcomb = ap.loc[icm, "combo"].value_counts().head(10).to_frame("turnos")
tcomb["%"] = (100 * tcomb["turnos"] / icm.sum()).round(1)
emit("1.5 Composición del target preliminar por combinación de ítems (top 10)", tcomb)

# ---------------------------------------------------------------------------------------------
# 2. (90) Concluido sin OS  (pregunta b)
# ---------------------------------------------------------------------------------------------
cols_nn = ["EffectiveCheckinDate", "EffectiveCheckoutDate", "KM", "VehicleCurrentKM", "DaysInDealer", "SurveyStarRating"]
nn = ap.groupby("StatusARG")[cols_nn].agg(lambda s: s.notna().mean()).reindex(STATUS_ORDER)
nn.columns = [f"% no nulo {c}" for c in cols_nn]
nn = (100 * nn).round(1)
nn["mediana DaysInDealer"] = ap.groupby("StatusARG")["DaysInDealer"].median().reindex(STATUS_ORDER)
nn["% has_maint"] = (100 * ap.groupby("StatusARG")["has_maint"].mean().reindex(STATUS_ORDER)).round(1)
nn["% has_recall"] = (100 * ap.groupby("StatusARG")["has_recall"].mean().reindex(STATUS_ORDER)).round(1)
nn["% has_diag"] = (100 * ap.groupby("StatusARG")["has_diag"].mean().reindex(STATUS_ORDER)).round(1)
nn["% ScheduleReturn=Y"] = (100 * ap.groupby("StatusARG")["ScheduleReturn"].agg(lambda s: s.eq("Y").mean()).reindex(STATUS_ORDER)).round(1)
emit("2.1 Perfil de cada StatusARG: presencia de fechas efectivas, km, días en taller y tipo de ítems", nn)

n90 = ap[ap["completed_no_os"]]
c90 = n90["combo"].value_counts().head(10).to_frame("turnos")
c90["%"] = (100 * c90["turnos"] / len(n90)).round(1)
emit("2.2 (90) Concluido sin OS: combinaciones de ítems (top 10)", c90)

# Seguimiento: existe un turno (60) del mismo vehículo a +-N días
ev = ap[ap["vehicle_id"].notna()].copy()
comp = ev.loc[ev["completed"], ["schedule_id", "vehicle_id", "event_date"]].rename(columns={"event_date": "cdate", "schedule_id": "csid"})
compm = ev.loc[ev["is_completed_maintenance"], ["schedule_id", "vehicle_id", "event_date"]].rename(columns={"event_date": "cdate", "schedule_id": "csid"})


def lag_to_completed(sub: pd.DataFrame, ref: pd.DataFrame, lo: int, hi: int) -> pd.Series:
    """Para cada turno de `sub`, True si existe OTRO turno en `ref` del mismo vehículo con lag en [lo, hi] días."""
    x = sub[["schedule_id", "vehicle_id", "event_date"]].merge(ref, on="vehicle_id", how="inner")
    x["dd"] = (x["cdate"] - x["event_date"]).dt.days
    ok = x.loc[(x["dd"] >= lo) & (x["dd"] <= hi) & (x["csid"] != x["schedule_id"]), "schedule_id"].unique()
    return sub["schedule_id"].isin(ok)


n90v = ev[ev["completed_no_os"]]
rows = []
for lo, hi in [(-30, -1), (0, 0), (1, 30), (-30, 30), (1, 90)]:
    rows.append({"ventana (días)": f"[{lo}, {hi}]",
                 "turnos (90) con un (60) del mismo vehículo": int(lag_to_completed(n90v, comp, lo, hi).sum()),
                 "turnos (90) con un (60)+mantenimiento": int(lag_to_completed(n90v, compm, lo, hi).sum())})
t90 = pd.DataFrame(rows).set_index("ventana (días)")
t90["% (60)"] = (100 * t90.iloc[:, 0] / len(n90v)).round(1)
t90["% (60)+mant"] = (100 * t90.iloc[:, 1] / len(n90v)).round(1)
emit(f"2.3 (90) con vehicle_id (n={len(n90v)}): ¿hay un turno concluido del mismo vehículo cerca?", t90)

n90m = n90v[n90v["has_maint"]]
t90m = pd.DataFrame({
    "n": [len(n90m)],
    "vehículos": [n90m["vehicle_id"].nunique()],
    "con (60)+mant en (0,30]": [int(lag_to_completed(n90m, compm, 1, 30).sum())],
    "con (60)+mant en [-30,-1]": [int(lag_to_completed(n90m, compm, -30, -1).sum())],
    "con (60)+mant el mismo día": [int(lag_to_completed(n90m, compm, 0, 0).sum())],
    "con (60)+mant en (0,90]": [int(lag_to_completed(n90m, compm, 1, 90).sum())],
    "% checkin no nulo": [round(100 * n90m["EffectiveCheckinDate"].notna().mean(), 1)],
    "% VehicleCurrentKM no nulo": [round(100 * n90m["VehicleCurrentKM"].notna().mean(), 1)],
    "mediana DaysInDealer": [n90m["DaysInDealer"].median()],
}).T.rename(columns={0: "valor"})
emit("2.4 (90) que incluían un ítem de mantenimiento", t90m)

sh90 = ap.groupby("dealer_id")["completed_no_os"].mean()
emit("2.5 (90) como % de los turnos de cada dealer", pd.DataFrame({
    "valor": [len(sh90), round(100 * sh90.median(), 1), round(100 * sh90.max(), 1), int((sh90 > 0.10).sum()), int((sh90 == 0).sum()),
              round(100 * n90["dealer_id"].value_counts(normalize=True).iloc[0], 1)]
}, index=["dealers", "mediana % (90) por dealer", "máximo % (90) por dealer", "dealers con >10% de (90)", "dealers sin (90)",
          "% de los (90) que concentra el dealer con más (90)"]))

# Figura: perfil comparado (60)/(80)/(90)/(70)
obs = ev[ev["ScheduleDate"] <= CUTOFF - pd.Timedelta(days=90)]
fu30 = {}
for s_ in [S60, S70, S80, S90]:
    sub = obs[obs["StatusARG"].eq(s_)]
    lo = 1 if s_ == S60 else 0
    fu30[s_] = lag_to_completed(sub, comp, lo, 30).mean()
prof = pd.DataFrame({
    "Check-in registrado": ap.groupby("StatusARG")["EffectiveCheckinDate"].agg(lambda s: s.notna().mean()),
    "Check-out registrado": ap.groupby("StatusARG")["EffectiveCheckoutDate"].agg(lambda s: s.notna().mean()),
    "Km al ingreso (VehicleCurrentKM)": ap.groupby("StatusARG")["VehicleCurrentKM"].agg(lambda s: s.notna().mean()),
    "Incluye ítem de mantenimiento": ap.groupby("StatusARG")["has_maint"].mean(),
    "Otro turno concluido en 30 días": pd.Series(fu30),
}).reindex([S60, S90, S80, S70])
fig, ax = plt.subplots(figsize=(10, 5))
xs = np.arange(len(prof.columns)); w = 0.2
for i, s_ in enumerate(prof.index):
    ax.bar(xs + (i - 1.5) * w, 100 * prof.loc[s_].values, width=w, label=s_)
ax.set_xticks(xs); ax.set_xticklabels(prof.columns, rotation=15, ha="right", fontsize=9)
ax.set_ylabel("% de turnos"); ax.set_title("Perfil de los estados (60), (90), (80) y (70): ¿el auto entró al taller?")
ax.legend(fontsize=8)
savefig(fig, "status90_perfil")
emit("2.6 Datos de la figura status90_perfil (%)", (100 * prof).round(1))

# ---------------------------------------------------------------------------------------------
# 3. Garantía, campañas/recall, aceite y filtro, otros  (pregunta c)
# ---------------------------------------------------------------------------------------------
c60 = ap[ap["completed"]]
aux = {"PUD", "MOVIL"}
rows = []
for c, label in [("GARANTIA", "Guarantee"), ("CAMPANA_RECALL", "Service campaign / Recall"),
                 ("ACEITE_FILTRO", "Oil and filter change"), ("CONTACTLESS", "Contactless service"),
                 ("INSPECCION", "Inspección Ford / Revision de Viaje")]:
    only = item_sets.reindex(c60["schedule_id"]).map(lambda s, c=c: c in s and s <= ({c} | aux)).values
    rows.append({
        "clase": label,
        "turnos (60) que la incluyen": int(c60[f"i_{c}"].sum()),
        "... sin ítem de mantenimiento": int((c60[f"i_{c}"] & ~c60["has_maint"]).sum()),
        "... solo esa clase (+PUD/móvil)": int(only.sum()),
        "vehículos (solo esa clase)": int(c60.loc[only, "vehicle_id"].nunique()),
        "vehículos sin ningún (60)+mant": int(len(set(c60.loc[only, "vehicle_id"].dropna()) - set(c60.loc[c60["has_maint"], "vehicle_id"].dropna()))),
    })
emit("3.1 Turnos (60) Concluido que cambiarían de clase según se incluya cada familia en el target", pd.DataFrame(rows).set_index("clase"))

gi = a[name.eq("Guarantee")]
oi = a[name.eq("Oil and filter change")]
ri = a[st.str.lower().eq("campañas de servicio")]
mi_all = a[a["ServiceMaintenance"].notna()]
fam_tab = pd.DataFrame({
    "Guarantee": [len(gi), gi["ScheduleDate"].dt.year.value_counts().sort_index().to_dict(),
                  round(((gi["ScheduleDate"] - gi["WarrantyStartDate"]).dt.days / 30.44).median(), 1),
                  gi["VehicleCurrentKM"].median(), gi["ServiceDuration"].value_counts().to_dict(), gi["ServiceFordFixedPriceFlag"].value_counts().to_dict()],
    "Oil and filter change": [len(oi), oi["ScheduleDate"].dt.year.value_counts().sort_index().to_dict(),
                              round(((oi["ScheduleDate"] - oi["WarrantyStartDate"]).dt.days / 30.44).median(), 1),
                              oi["VehicleCurrentKM"].median(), oi["ServiceDuration"].value_counts().to_dict(), oi["ServiceFordFixedPriceFlag"].value_counts().to_dict()],
    "Campañas/Recall": [len(ri), ri["ScheduleDate"].dt.year.value_counts().sort_index().to_dict(),
                        round(((ri["ScheduleDate"] - ri["WarrantyStartDate"]).dt.days / 30.44).median(), 1),
                        ri["VehicleCurrentKM"].median(), ri["ServiceDuration"].value_counts().to_dict(), ri["ServiceFordFixedPriceFlag"].value_counts().to_dict()],
    "Maintenance service/review": [len(mi_all), mi_all["ScheduleDate"].dt.year.value_counts().sort_index().to_dict(),
                                   round(((mi_all["ScheduleDate"] - mi_all["WarrantyStartDate"]).dt.days / 30.44).median(), 1),
                                   mi_all["VehicleCurrentKM"].median(), mi_all["ServiceDuration"].value_counts().to_dict(), mi_all["ServiceFordFixedPriceFlag"].value_counts().to_dict()],
}, index=["ítems", "ítems por año", "mediana edad (meses desde WarrantyStart)", "mediana VehicleCurrentKM", "ServiceDuration", "FordFixedPriceFlag"])
emit("3.2 Perfil de las familias candidatas (filas ítem)", fam_tab)
emit("3.3 'Service campaign' vs 'Recall' por año (mismo ServiceType, cambio de nombre en 2026)",
     pd.crosstab(ri["ServiceName"], ri["ScheduleDate"].dt.year))
emit("3.4 'Oil and filter change': % de turnos que además traen ítem de mantenimiento",
     pd.DataFrame({"valor": [round(100 * ap.loc[ap["i_ACEITE_FILTRO"], "has_maint"].mean(), 1), oi["dealer_id"].nunique(),
                             round(100 * oi["dealer_id"].value_counts(normalize=True).iloc[0], 1)]},
                  index=["% turnos con Oil&filter que también tienen mantenimiento", "dealers que lo usan", "% del dealer que más lo usa"]))

# Escenarios de target
scen = {
    "A. (60) & ítem Maintenance service/review [preliminar]": ap["completed"] & ap["has_maint"],
    "B. A + Oil and filter change": ap["completed"] & (ap["has_maint"] | ap["i_ACEITE_FILTRO"]),
    "C. B + Guarantee": ap["completed"] & (ap["has_maint"] | ap["i_ACEITE_FILTRO"] | ap["i_GARANTIA"]),
    "D. C + Campañas/Recall": ap["completed"] & (ap["has_maint"] | ap["i_ACEITE_FILTRO"] | ap["i_GARANTIA"] | ap["i_CAMPANA_RECALL"]),
    "E. A + (90) con ítem mantenimiento": (ap["completed"] | ap["completed_no_os"]) & ap["has_maint"],
    "F. Visita efectiva: (60) o (90), cualquier ítem": ap["completed"] | ap["completed_no_os"],
}
scen_tab = pd.DataFrame({
    "turnos": {k: int(v.sum()) for k, v in scen.items()},
    "vehículos": {k: ap.loc[v, "vehicle_id"].nunique() for k, v in scen.items()},
})
scen_tab["Δ turnos vs A"] = scen_tab["turnos"] - scen_tab.loc[scen_tab.index[0], "turnos"]
scen_tab["Δ vehículos vs A"] = scen_tab["vehículos"] - scen_tab.loc[scen_tab.index[0], "vehículos"]
emit("3.5 Escenarios de definición del evento objetivo: turnos y vehículos que cumplen", scen_tab)
fig, ax = plt.subplots(figsize=(10, 4.5))
ax.barh(scen_tab.index[::-1], scen_tab["turnos"][::-1], color="#4c72b0")
for i, (k, v) in enumerate(scen_tab["turnos"][::-1].items()):
    ax.text(v + 2000, i, f"{v:,}".replace(",", "."), va="center", fontsize=9)
ax.set_xlabel("Turnos que cumplen la definición"); ax.set_title("Escenarios de definición del evento objetivo")
ax.set_xlim(0, scen_tab["turnos"].max() * 1.18)
savefig(fig, "escenarios_target")

# ---------------------------------------------------------------------------------------------
# 4. Numeración de ServiceMaintenance  (pregunta d)
# ---------------------------------------------------------------------------------------------
mi = a[a["ServiceMaintenance"].notna()].copy()
mi["familia"] = np.where(mi["ServiceName"].str.contains("review"), "Maintenance review", "Maintenance service")
mi["n"] = mi["ServiceMaintenance"].astype(int)
map_tab = pd.crosstab(mi["n"], mi["ServiceName"])
map_tab = map_tab.apply(lambda r: ", ".join(f"{c} ({r[c]})" for c in map_tab.columns if r[c] > 0), axis=1).to_frame("ServiceName (ítems)")
emit("4.1 ServiceMaintenance (número) -> ServiceName observado", map_tab)

mon = mi[mi["ScheduleDate"] >= "2025-10-01"]
emit("4.2 Familia del catálogo por mes de turno (cambio de 'service' a 'review')",
     pd.crosstab(mon["ScheduleDate"].dt.to_period("M").astype(str), mon["familia"]),
     note=f"Primer ítem 'review': {mi.loc[mi['familia'].eq('Maintenance review'), 'ScheduleDate'].min().date()}; "
          f"último ítem 'service': {mi.loc[mi['familia'].eq('Maintenance service'), 'ScheduleDate'].max().date()}.")
fam_month = pd.crosstab(mi["ScheduleDate"].dt.to_period("M").astype(str), mi["familia"])
fig, ax = plt.subplots(figsize=(11, 4))
fam_month.plot(kind="bar", stacked=True, ax=ax, width=0.85, color=["#4c72b0", "#dd8452"])
ax.set_xlabel("Mes del turno"); ax.set_ylabel("Ítems de mantenimiento"); ax.set_title("Catálogo 'Maintenance service' vs 'Maintenance review' por mes")
ax.tick_params(axis="x", labelsize=7)
savefig(fig, "catalogo_mes")

d_fam = mi.groupby("dealer_id")["familia"].agg(lambda s: s.eq("Maintenance review").mean())
d_fam26 = mi[mi["ScheduleDate"] >= "2026-02-01"].groupby("dealer_id")["familia"].agg(lambda s: s.eq("Maintenance review").mean())
emit("4.3 ¿La familia depende del dealer, de la generación o de la fuente?", pd.DataFrame({
    "valor": [round(d_fam.median(), 3), round(d_fam.quantile(0.1), 3), round(d_fam.quantile(0.9), 3),
              round(d_fam26.min(), 3), int((d_fam26 < 0.99).sum()), len(d_fam26)]
}, index=["mediana % review por dealer (todo el período)", "p10 % review por dealer", "p90 % review por dealer",
          "mínimo % review por dealer desde 2026-02", "dealers con <99% review desde 2026-02", "dealers con ítems desde 2026-02"]))
emit("4.4 Familia x generación (ítems)", pd.crosstab(mi["familia"], mi["ShortVehicleModelGroupTreated"]))
emit("4.5 Familia x ScheduleSource (ítems)", pd.crosstab(mi["familia"], mi["ScheduleSource"]))

mi["n>=11"] = mi["n"] >= 11
gen_hi = pd.crosstab(mi["ShortVehicleModelGroupTreated"], mi["n>=11"])
gen_hi["% n>=11"] = (100 * gen_hi[True] / gen_hi.sum(axis=1)).round(1)
emit("4.6 Ítems con ServiceMaintenance >= 11 por generación", gen_hi)
my = mi[mi["ModelYear"].between(2012, 2026)]
my_hi = my.groupby("ModelYear")["n>=11"].agg(["size", "mean"]); my_hi.columns = ["ítems", "% n>=11"]; my_hi["% n>=11"] = (100 * my_hi["% n>=11"]).round(1)
emit("4.7 % de ítems con n >= 11 por ModelYear", my_hi.T)

# n vs km real al ingreso (VehicleCurrentKM) y vs edad, solo (60)
mc = mi[mi["StatusARG"].eq(S60)].copy()
mc["edad_m"] = (mc["ScheduleDate"] - mc["WarrantyStartDate"]).dt.days / 30.44
p703 = mc[mc["ShortVehicleModelGroupTreated"].eq("RANGER (P703)")]
p375 = mc[mc["ShortVehicleModelGroupTreated"].eq("RANGER (P375)")]
km_n = pd.DataFrame({
    "P703 ítems": p703.groupby("n").size(),
    "P703 mediana VehicleCurrentKM": p703.groupby("n")["VehicleCurrentKM"].median().round(0),
    "P703 mediana edad (meses)": p703.groupby("n")["edad_m"].median().round(1),
    "P375 ítems": p375.groupby("n").size(),
    "P375 mediana VehicleCurrentKM": p375.groupby("n")["VehicleCurrentKM"].median().round(0),
    "P375 mediana edad (meses)": p375.groupby("n")["edad_m"].median().round(1),
    "ServiceMonth (=12n)": 12 * np.arange(1, 21),
}, index=pd.Index(range(1, 21), name="n"))
emit("4.8 Número de service vs km real al ingreso y edad del vehículo, turnos (60)", km_n)
r703 = (p703["VehicleCurrentKM"] / (p703["n"] * 15000)).between(0.8, 1.2).mean()
r375 = (p375["VehicleCurrentKM"] / (p375["n"] * 10000)).between(0.8, 1.2).mean()
r703b = (p703["VehicleCurrentKM"] / (p703["n"] * 10000)).between(0.8, 1.2).mean()
r375b = (p375["VehicleCurrentKM"] / (p375["n"] * 15000)).between(0.8, 1.2).mean()
mc["diff_edad_servicemonth"] = mc["edad_m"] - mc["ServiceMonth"]
emit("4.9 ¿n es un hito de km o de meses?", pd.DataFrame({"valor": [
    round((p703["VehicleCurrentKM"] / p703["n"]).median(), 0), pct(r703), pct(r703b),
    round((p375["VehicleCurrentKM"] / p375["n"]).median(), 0), pct(r375), pct(r375b),
    round(mc["diff_edad_servicemonth"].median(), 1), pct((mc["diff_edad_servicemonth"].abs() <= 6).mean()),
]}, index=["P703: mediana VehicleCurrentKM / n", "P703: % ítems con VehicleCurrentKM dentro de ±20% de n×15.000",
           "P703: % dentro de ±20% de n×10.000", "P375: mediana VehicleCurrentKM / n",
           "P375: % ítems dentro de ±20% de n×10.000", "P375: % dentro de ±20% de n×15.000",
           "mediana (edad en meses − ServiceMonth)", "% ítems con |edad − ServiceMonth| <= 6 meses"]))
fig, ax = plt.subplots(figsize=(9, 5))
ns = np.arange(1, 21)
p703_med = km_n["P703 mediana VehicleCurrentKM"].where(km_n["P703 ítems"] >= 100)  # n>=11 en P703: <100 ítems, no se grafica
ax.plot(ns, p703_med, "o-", label="P703 (mediana km al ingreso; solo n con >= 100 ítems)")
ax.plot(ns, km_n["P375 mediana VehicleCurrentKM"], "s-", label="P375 (mediana km al ingreso)")
ax.plot(ns, ns * 15000, "--", color="gray", label="n × 15.000 km")
ax.plot(ns, ns * 10000, ":", color="gray", label="n × 10.000 km")
ax.set_xlabel("ServiceMaintenance (n)"); ax.set_ylabel("VehicleCurrentKM (mediana)"); ax.set_xticks(ns)
ax.set_title("El número de service es un hito de kilometraje: 15.000 km (P703) y 10.000 km (P375)")
ax.legend()
savefig(fig, "km_por_n")

# Secuencia observada por vehículo
cmv = ev[ev["is_completed_maintenance"] & ev["maint_number"].notna()].sort_values(["vehicle_id", "event_date", "schedule_id"]).copy()
g = cmv.groupby("vehicle_id")
cmv["obs_rank"] = g.cumcount() + 1
cmv["prev_n"] = g["maint_number"].shift(1)
cmv["prev_date"] = g["event_date"].shift(1)
cmv["prev_km"] = g["VehicleCurrentKM"].shift(1)
cmv["delta_n"] = cmv["maint_number"] - cmv["prev_n"]
cmv["delta_dias"] = (cmv["event_date"] - cmv["prev_date"]).dt.days
cmv["delta_km"] = cmv["VehicleCurrentKM"] - cmv["prev_km"]
pairs = cmv[cmv["delta_n"].notna()]
nveh2 = (g.size() >= 2).sum()
mono = g["maint_number"].agg(lambda s: s.is_monotonic_increasing)
strict = g["maint_number"].agg(lambda s: s.is_monotonic_increasing and s.is_unique)
seq_tab = pd.DataFrame({"valor": [
    len(pairs), pct(pairs["delta_n"].eq(1).mean()), pct(pairs["delta_n"].eq(0).mean()), pct((pairs["delta_n"] < 0).mean()),
    pct((pairs["delta_n"] > 1).mean()), int(nveh2), pct(mono[g.size() >= 2].mean()), pct(strict[g.size() >= 2].mean()),
    int(pairs["delta_dias"].median()), int(pairs.loc[pairs["delta_n"].eq(1), "delta_km"].median()),
]}, index=["pares consecutivos de (60)+mant del mismo vehículo", "% con Δn = +1", "% con Δn = 0 (mismo número)", "% con Δn < 0",
           "% con Δn > 1 (saltos)", "vehículos con >= 2 (60)+mant", "% de esos vehículos con secuencia no decreciente",
           "% con secuencia estrictamente creciente", "mediana días entre mantenimientos consecutivos",
           "mediana Δ VehicleCurrentKM cuando Δn = +1"])
emit("4.10 ¿maint_number se comporta como 'n-ésimo service del vehículo'?", seq_tab)
fig, ax = plt.subplots(figsize=(8, 4))
vc = pairs["delta_n"].clip(-5, 6).value_counts().sort_index()
ax.bar([str(int(i)) if -5 < i < 6 else ("≤-5" if i <= -5 else "≥6") for i in vc.index], vc.values, color="#4c72b0")
ax.set_xlabel("Δ ServiceMaintenance entre mantenimientos consecutivos (mismo vehículo)"); ax.set_ylabel("Pares")
ax.set_title("Diferencia de número de service entre mantenimientos completados consecutivos")
savefig(fig, "delta_n")

first = cmv[cmv["obs_rank"].eq(1)].merge(sales[["vehicle_id", "SalesDate"]], on="vehicle_id", how="inner")
first_tab = first["maint_number"].value_counts().sort_index().head(8).to_frame("vehículos")
first_tab["%"] = (100 * first_tab["vehículos"] / len(first)).round(1)
emit(f"4.11 Primer mantenimiento observado en vehículos vendidos 2024-2026 (SALES, n={len(first)}): número de service", first_tab.T)

# ---------------------------------------------------------------------------------------------
# 5. IsReschedule y ScheduleReturn  (pregunta e)
# ---------------------------------------------------------------------------------------------
emit("5.1 IsReschedule x StatusARG (turnos)", pd.crosstab(ap["IsReschedule"].fillna("(nulo)"), ap["StatusARG"], margins=True).reindex(columns=STATUS_ORDER + ["All"]))
raw_status = a.groupby("schedule_id")["ScheduleStatus"].first()
ap["ScheduleStatus_raw"] = ap["schedule_id"].map(raw_status).fillna("(nulo)")
emit("5.2 Cancelados: ScheduleStatus crudo x IsReschedule", pd.crosstab(ap.loc[ap["cancelled"], "ScheduleStatus_raw"], ap.loc[ap["cancelled"], "IsReschedule"].fillna("(nulo)")))
emit("5.3 ScheduleReturn x StatusARG (turnos)", pd.crosstab(ap["ScheduleReturn"].fillna("(nulo)"), ap["StatusARG"], margins=True).reindex(columns=STATUS_ORDER + ["All"]))
emit("5.4 ScheduleReturn x ScheduleSource", pd.crosstab(ap["ScheduleReturn"].fillna("(nulo)"), ap["ScheduleSource"]))
rt = ap.groupby(ap["ScheduleReturn"].fillna("(nulo)"))[["has_maint", "has_diag", "has_repair", "has_recall", "has_guarantee"]].mean()
emit("5.5 ScheduleReturn: tipo de ítems (%)", (100 * rt).round(1))

v = ev.sort_values(["vehicle_id", "ScheduleDate", "schedule_id"]).copy()
gv = v.groupby("vehicle_id")
v["d_prev"] = (v["ScheduleDate"] - gv["ScheduleDate"].shift(1)).dt.days
v["d_next"] = (gv["ScheduleDate"].shift(-1) - v["ScheduleDate"]).dt.days
v["prev_status"] = gv["StatusARG"].shift(1)
v["next_status"] = gv["StatusARG"].shift(-1)


def lag_profile(mask: pd.Series, label: str) -> dict:
    s = v[mask]
    return {
        "grupo": label, "turnos": len(s),
        "% con turno previo <=14d": pct((s["d_prev"] <= 14).mean()),
        "% con turno previo <=30d": pct((s["d_prev"] <= 30).mean()),
        "% previo (60) <=30d": pct((s["prev_status"].eq(S60) & (s["d_prev"] <= 30)).mean()),
        "% previo (70) <=14d": pct((s["prev_status"].eq(S70) & (s["d_prev"] <= 14)).mean()),
        "mediana d_prev": s["d_prev"].median(),
        "% con turno posterior <=14d": pct((s["d_next"] <= 14).mean()),
        "% con turno posterior <=30d": pct((s["d_next"] <= 30).mean()),
        "mediana d_next": s["d_next"].median(),
    }


lag_tab = pd.DataFrame([
    lag_profile(v["ScheduleReturn"].eq("Y"), "ScheduleReturn = Y"),
    lag_profile(v["ScheduleReturn"].eq("N"), "ScheduleReturn = N"),
    lag_profile(v["IsReschedule"].eq("Y") & v["completed"], "IsReschedule = Y & (60)"),
    lag_profile(v["IsReschedule"].isna() & v["completed"], "IsReschedule nulo & (60)"),
    lag_profile(v["IsReschedule"].eq("Y") & v["cancelled"], "IsReschedule = Y & (70)"),
    lag_profile(v["IsReschedule"].eq("N") & v["cancelled"], "IsReschedule = N & (70)"),
]).set_index("grupo")
emit("5.6 Semántica empírica: distancia al turno anterior / posterior del mismo vehículo", lag_tab)
fig, ax = plt.subplots(figsize=(9, 4.5))
bins = np.arange(0, 62, 2)
for lab, m_, col in [("ScheduleReturn = Y", v["ScheduleReturn"].eq("Y"), "#dd8452"), ("ScheduleReturn = N", v["ScheduleReturn"].eq("N"), "#4c72b0")]:
    ax.hist(v.loc[m_, "d_prev"].dropna().clip(upper=60), bins=bins, density=True, alpha=0.6, label=lab, color=col)
ax.set_xlabel("Días desde el turno anterior del mismo vehículo (truncado a 60)"); ax.set_ylabel("Densidad")
ax.set_title("ScheduleReturn = Y es una visita de retorno: casi siempre hay un turno previo en el mes")
ax.legend()
savefig(fig, "return_lag")

# ---------------------------------------------------------------------------------------------
# 6. Cancelaciones y no-show: reprogramación vs pérdida  (pregunta f)
# ---------------------------------------------------------------------------------------------
canc = obs[obs["cancelled"]]; ns_ = obs[obs["no_show"]]
rows = []
for label, sub, ref in [
    ("(70) Cancelado -> algún (60)", canc, comp),
    ("(70) Cancelado -> (60)+mant", canc, compm),
    ("(70) & IsReschedule=Y -> algún (60)", canc[canc["IsReschedule"].eq("Y")], comp),
    ("(70) & IsReschedule=N -> algún (60)", canc[canc["IsReschedule"].eq("N")], comp),
    ("(70) con ítem mant -> (60)+mant", canc[canc["has_maint"]], compm),
    ("(80) No asistió -> algún (60)", ns_, comp),
    ("(80) No asistió -> (60)+mant", ns_, compm),
    ("(80) con ítem mant -> (60)+mant", ns_[ns_["has_maint"]], compm),
    ("(90) Concluido sin OS -> algún (60)", obs[obs["completed_no_os"]], comp),
    ("(60) Concluido -> otro (60) [base]", obs[obs["completed"]], comp),
]:
    lo = 1 if label.startswith("(60)") else 0
    r = {"caso": label, "turnos": len(sub)}
    for h in (30, 60, 90):
        r[f"% con seguimiento <= {h} d"] = pct(lag_to_completed(sub, ref, lo, h).mean())
    rows.append(r)
fu_tab = pd.DataFrame(rows).set_index("caso")
emit(f"6.1 Turnos con ScheduleDate <= CUTOFF-90d: % con un turno concluido del mismo vehículo dentro de N días (0..N)", fu_tab,
     note="Para (60) se exige otro turno distinto con lag >= 1 día. 'Cancelación efectiva' = 100% menos el valor a 90 días.")

# curva acumulada 0..90
fig, ax = plt.subplots(figsize=(9, 5))
days = np.arange(0, 91)
for label, sub, col in [("(70) Cancelado, IsReschedule=Y", canc[canc["IsReschedule"].eq("Y")], "#dd8452"),
                        ("(70) Cancelado, IsReschedule=N", canc[canc["IsReschedule"].eq("N")], "#c44e52"),
                        ("(80) No asistió", ns_, "#8172b2"), ("(90) Concluido sin OS", obs[obs["completed_no_os"]], "#55a868"),
                        ("(60) Concluido (otro turno)", obs[obs["completed"]], "#4c72b0")]:
    lo = 1 if label.startswith("(60)") else 0
    x = sub[["schedule_id", "vehicle_id", "event_date"]].merge(comp, on="vehicle_id", how="inner")
    x["dd"] = (x["cdate"] - x["event_date"]).dt.days
    x = x[(x["dd"] >= lo) & (x["csid"] != x["schedule_id"])]
    mind = x.groupby("schedule_id")["dd"].min()
    curve = [(mind <= d).sum() / len(sub) for d in days]
    ax.plot(days, 100 * np.array(curve), label=label, color=col)
ax.set_xlabel("Días desde el turno"); ax.set_ylabel("% con un turno (60) posterior del mismo vehículo")
ax.set_title("Seguimiento: ¿cuánto tarda en aparecer un turno concluido después de cancelar / no asistir?")
ax.legend(fontsize=8); ax.grid(alpha=0.3)
savefig(fig, "seguimiento")

sin_item = (ap["combo"].eq("SIN_ITEM")).map({True: "sin ítem", False: "con ítem"}).rename("ítems del turno")
emit("6.2 Turnos sin ningún ítem tipado (ServiceType nulo) por StatusARG",
     pd.crosstab(sin_item, ap["StatusARG"], margins=True).reindex(columns=STATUS_ORDER + ["All"]),
     note="Casi todos los turnos sin ítem son cancelaciones: no se sabe qué servicio tenían reservado.")

# ---------------------------------------------------------------------------------------------
# 7. Duplicados lógicos  (pregunta g)
# ---------------------------------------------------------------------------------------------
v["prev_sid"] = gv["schedule_id"].shift(1); v["prev_dealer"] = gv["dealer_id"].shift(1)
sd = v[v["d_prev"].eq(0)]; w3 = v[v["d_prev"].between(1, 3)]
emit("7.1 Turnos del mismo vehículo el MISMO día: estado del turno previo x estado del turno", pd.crosstab(sd["prev_status"], sd["StatusARG"]).reindex(index=STATUS_ORDER, columns=STATUS_ORDER, fill_value=0),
     note=f"Pares mismo día: {len(sd)} ({pct(len(sd) / len(v))} de los turnos con vehículo); mismo dealer en {pct((sd['prev_dealer'] == sd['dealer_id']).mean())}.")
emit("7.2 Turnos del mismo vehículo a 1-3 días: estado previo x estado", pd.crosstab(w3["prev_status"], w3["StatusARG"]).reindex(index=STATUS_ORDER, columns=STATUS_ORDER, fill_value=0),
     note=f"Pares a 1-3 días: {len(w3)}.")
p3 = pairs[pairs["delta_dias"] <= 3]; p30 = pairs[pairs["delta_dias"] <= 30]; p430 = pairs[pairs["delta_dias"].between(4, 30)]
dup_tab = pd.DataFrame({
    "pares (60)+mant consecutivos": [len(p3), len(p430), len(p30)],
    "% mismo maint_number": [pct(p3["delta_n"].eq(0).mean()), pct(p430["delta_n"].eq(0).mean()), pct(p30["delta_n"].eq(0).mean())],
    "% Δn = +1": [pct(p3["delta_n"].eq(1).mean()), pct(p430["delta_n"].eq(1).mean()), pct(p30["delta_n"].eq(1).mean())],
    "% |Δ VehicleCurrentKM| <= 500": [pct((p3["delta_km"].abs() <= 500).mean()), pct((p430["delta_km"].abs() <= 500).mean()), pct((p30["delta_km"].abs() <= 500).mean())],
    "mediana Δ VehicleCurrentKM": [p3["delta_km"].median(), p430["delta_km"].median(), p30["delta_km"].median()],
}, index=["<= 3 días", "4 a 30 días", "<= 30 días"])
emit(f"7.3 Mantenimientos completados consecutivos del mismo vehículo muy cercanos en el tiempo (de {len(pairs)} pares)", dup_tab)

# ---------------------------------------------------------------------------------------------
# 8. Turnos sin vehicle_id / customer_id  (pregunta h)
# ---------------------------------------------------------------------------------------------
miss = pd.DataFrame({
    "sin vehicle_id": pd.crosstab(ap["vehicle_id"].isna(), ap["StatusARG"]).reindex(columns=STATUS_ORDER).loc[True],
    "sin customer_id": pd.crosstab(ap["customer_id"].isna(), ap["StatusARG"]).reindex(columns=STATUS_ORDER).loc[True],
    "sin ambos": pd.crosstab(ap["vehicle_id"].isna() & ap["customer_id"].isna(), ap["StatusARG"]).reindex(columns=STATUS_ORDER).loc[True],
}).T
miss["total"] = miss.sum(axis=1)
emit("8.1 Turnos sin identificador por StatusARG", miss)
veh_has_cust = ap[ap["vehicle_id"].notna()].groupby("vehicle_id")["customer_id"].agg(lambda x: x.notna().any())
nov = ap[ap["vehicle_id"].isna()]
emit("8.2 Detalle de los faltantes", pd.DataFrame({"valor": [
    (ap["vehicle_id"].isna() & ap["is_completed_maintenance"]).sum(),
    (ap["customer_id"].isna() & ap["is_completed_maintenance"]).sum(),
    nov["ScheduleSource"].value_counts().to_dict(),
    nov["ShortVehicleModelGroupTreated"].value_counts().to_dict(),
    pct(nov["WarrantyStartDate"].notna().mean()), pct(nov["ModelYear"].notna().mean()),
    nov["dealer_id"].nunique(), pct(nov["dealer_id"].value_counts(normalize=True).iloc[0]),
    int(ap.loc[ap["customer_id"].isna() & ap["vehicle_id"].notna(), "vehicle_id"].map(veh_has_cust).sum()),
    ap[ap["customer_id"].isna()]["dealer_id"].nunique(), pct(ap[ap["customer_id"].isna()]["dealer_id"].value_counts(normalize=True).iloc[0]),
]}, index=["(60)+mant sin vehicle_id", "(60)+mant sin customer_id", "sin vehicle_id: ScheduleSource", "sin vehicle_id: generación",
           "sin vehicle_id: % con WarrantyStartDate", "sin vehicle_id: % con ModelYear", "sin vehicle_id: dealers", "sin vehicle_id: % del dealer principal",
           "sin customer_id pero el vehículo tiene customer_id en otro turno", "sin customer_id: dealers", "sin customer_id: % del dealer principal"]))

# ---------------------------------------------------------------------------------------------
# 9. Region y DealerStateOrZone  (pregunta i)
# ---------------------------------------------------------------------------------------------
dr = ap.groupby("dealer_id").agg(turnos=("schedule_id", "size"), n_region=("Region", "nunique"), n_zona=("DealerStateOrZone", "nunique"))
reg_tab = pd.DataFrame({
    "dealers": ap.groupby("Region")["dealer_id"].nunique(),
    "turnos": ap["Region"].value_counts(),
    "% turnos": (100 * ap["Region"].value_counts(normalize=True)).round(2),
    "turnos 2024": pd.crosstab(ap["Region"], ap["ScheduleDate"].dt.year)[2024],
    "turnos 2025": pd.crosstab(ap["Region"], ap["ScheduleDate"].dt.year)[2025],
    "turnos 2026": pd.crosstab(ap["Region"], ap["ScheduleDate"].dt.year)[2026],
    "% concluido (60)": (100 * ap.groupby("Region")["completed"].mean()).round(1),
})
emit("9.1 Region: dealers y turnos", reg_tab, note=f"Dealers con más de una Region: {(dr['n_region'] > 1).sum()}; con más de una DealerStateOrZone: {(dr['n_zona'] > 1).sum()} (de {len(dr)}).")
emit("9.2 Region x DealerStateOrZone (turnos)", pd.crosstab(ap["Region"], ap["DealerStateOrZone"].fillna("(nulo)"), margins=True))
dstate = sales.groupby("dealer_id")["State"].agg(lambda x: x.value_counts().index[0])
dr["zona"] = ap.groupby("dealer_id")["DealerStateOrZone"].agg(lambda s: s.value_counts().index[0] if s.notna().any() else "(nulo)")
dr["region"] = ap.groupby("dealer_id")["Region"].agg(lambda s: s.value_counts().index[0])
dr["provincia_sales"] = dr.index.map(dstate).fillna("(dealer sin ventas en SALES)")
emit("9.3 DealerStateOrZone del dealer x provincia principal de sus ventas (SALES)", pd.crosstab(dr["provincia_sales"], dr["zona"]))
emit("9.4 Region del dealer x provincia principal de sus ventas (SALES)", pd.crosstab(dr["provincia_sales"], dr["region"]))
emit("9.5 dealer_id: cruce SALES vs AGENDA", pd.DataFrame({"valor": [
    sales["dealer_id"].nunique(), ap["dealer_id"].nunique(), len(set(sales["dealer_id"].dropna()) & set(ap["dealer_id"])),
    len(set(ap["dealer_id"]) - set(sales["dealer_id"].dropna())), len(set(sales["dealer_id"].dropna()) - set(ap["dealer_id"]))
]}, index=["dealers en SALES", "dealers en AGENDA", "en ambas", "solo AGENDA", "solo SALES"]))

# ---------------------------------------------------------------------------------------------
# 10. KM vs VehicleCurrentKM (hallazgo transversal: KM es un snapshot del vehículo)
# ---------------------------------------------------------------------------------------------
e2 = v[v["vehicle_id"].isin(gv.size()[gv.size() >= 2].index)].copy()
g2 = e2.groupby("vehicle_id")
e2["prev_vck"] = g2["VehicleCurrentKM"].shift(1); e2["prev_km"] = g2["KM"].shift(1)
pv = e2[e2["VehicleCurrentKM"].notna() & e2["prev_vck"].notna() & (e2["d_prev"] > 30)]
pk = e2[e2["KM"].notna() & e2["prev_km"].notna() & (e2["d_prev"] > 30)]
last = gv.tail(1); last = last[last["KM"].notna() & last["VehicleCurrentKM"].notna()]
firstt = gv.head(1); firstt = firstt[firstt["KM"].notna() & firstt["VehicleCurrentKM"].notna()]
# Constancia medida SOLO entre vehículos con >= 2 valores no nulos de la columna (si no, los vehículos con la columna
# nula o con un único valor cuentan como "constantes" y distorsionan el porcentaje; verificación EDA 01).
km_ok = g2["KM"].count() >= 2
vck_ok = g2["VehicleCurrentKM"].count() >= 2
km_tab = pd.DataFrame({"valor": [
    int((g2.size()).shape[0]), int(km_ok.sum()), pct((g2["KM"].nunique()[km_ok] == 1).mean()),
    int(vck_ok.sum()), pct((g2["VehicleCurrentKM"].nunique()[vck_ok] == 1).mean()),
    len(pk), pct((pk["KM"] == pk["prev_km"]).mean()), len(pv), pct((pv["VehicleCurrentKM"] > pv["prev_vck"]).mean()),
    pct((pv["VehicleCurrentKM"] == pv["prev_vck"]).mean()), pct((pv["VehicleCurrentKM"] < pv["prev_vck"]).mean()),
    pct(((last["KM"] - last["VehicleCurrentKM"]).abs() <= 1000).mean()), pct(((firstt["KM"] - firstt["VehicleCurrentKM"]).abs() <= 1000).mean()),
    pct(((firstt["KM"] - firstt["VehicleCurrentKM"]) > 1000).mean()),
]}, index=["vehículos con >= 2 turnos", "... con KM no nulo en >= 2 turnos", "% de esos con un único valor de KM",
           "... con VehicleCurrentKM no nulo en >= 2 turnos", "% de esos con un único valor de VehicleCurrentKM",
           "pares consecutivos (>30 d) con KM en ambos", "% con KM idéntico", "pares consecutivos (>30 d) con VehicleCurrentKM en ambos",
           "% VehicleCurrentKM creciente", "% igual", "% decreciente", "último turno: % |KM − VehicleCurrentKM| <= 1.000",
           "primer turno: % |KM − VehicleCurrentKM| <= 1.000", "primer turno: % KM > VehicleCurrentKM + 1.000"])
emit("10.1 KM es un atributo del vehículo (snapshot al último dato), VehicleCurrentKM es el odómetro al ingreso", km_tab)
n1 = ap[ap["is_completed_maintenance"] & ap["maint_number"].eq(1) & ap["ShortVehicleModelGroupTreated"].eq("RANGER (P703)")]
emit("10.2 P703, 1° service completado: cuantiles de KM vs VehicleCurrentKM", pd.DataFrame({
    "KM": n1["KM"].quantile([.1, .25, .5, .75, .9]).round(0), "VehicleCurrentKM": n1["VehicleCurrentKM"].quantile([.1, .25, .5, .75, .9]).round(0)}).T)
fig, ax = plt.subplots(figsize=(9, 4.5))
bins = np.arange(0, 100001, 2500)
ax.hist(n1["VehicleCurrentKM"].clip(upper=100000), bins=bins, alpha=0.65, label="VehicleCurrentKM (odómetro al ingreso)", color="#4c72b0")
ax.hist(n1["KM"].clip(upper=100000), bins=bins, alpha=0.55, label="KM (snapshot del vehículo)", color="#dd8452")
ax.axvline(15000, color="gray", ls="--", lw=1); ax.text(15500, ax.get_ylim()[1] * 0.9, "15.000 km", fontsize=8, color="gray")
ax.set_xlabel("Kilómetros (truncado a 100.000)"); ax.set_ylabel("Turnos"); ax.set_title("1° service completado en Ranger P703: KM vs VehicleCurrentKM")
ax.legend()
savefig(fig, "km_vs_vck")

# ---------------------------------------------------------------------------------------------
# 11. REGLA FINAL PROPUESTA
# ---------------------------------------------------------------------------------------------


def regla_eventos(ap: pd.DataFrame) -> pd.DataFrame:
    """Aplica la regla final sobre la tabla de turnos (una fila por schedule_id, salida de appointments()).

    Devuelve la misma tabla con:
      - ``visita_red``:   (60) Concluido o (90) Concluido sin OS, con vehicle_id y ScheduleDate <= CUTOFF.
      - ``mant_completado``: visita_red & StatusARG == (60) & algún ítem 'Maintenance service/review'
        (ServiceMaintenance no nulo), deduplicado: un evento por vehículo y día; y si dos eventos del
        mismo vehículo tienen el mismo maint_number a <= 30 días, se conserva el primero.
      - ``dup_mant``: marca de los eventos descartados por la deduplicación.
    """
    out = ap.copy()
    base = out["vehicle_id"].notna() & (out["ScheduleDate"] <= CUTOFF)
    out["visita_red"] = base & (out["completed"] | out["completed_no_os"])
    cand = out["visita_red"] & out["completed"] & out["has_maint"]
    c = out.loc[cand, ["schedule_id", "vehicle_id", "event_date", "maint_number"]].sort_values(
        ["vehicle_id", "event_date", "schedule_id"])
    # (1) un evento por vehículo y día
    dup_day = c.duplicated(["vehicle_id", "event_date"], keep="first")
    c1 = c[~dup_day]
    # (2) mismo maint_number a <= 30 días del anterior conservado -> duplicado
    prev_date = c1.groupby("vehicle_id")["event_date"].shift(1)
    prev_n = c1.groupby("vehicle_id")["maint_number"].shift(1)
    dup_n = (c1["maint_number"] == prev_n) & ((c1["event_date"] - prev_date).dt.days <= 30)
    keep = set(c1.loc[~dup_n, "schedule_id"])
    out["mant_completado"] = cand & out["schedule_id"].isin(keep)
    out["dup_mant_dia"] = out["schedule_id"].isin(c.loc[dup_day, "schedule_id"])
    out["dup_mant_n30"] = out["schedule_id"].isin(c1.loc[dup_n, "schedule_id"])
    out["dup_mant"] = out["dup_mant_dia"] | out["dup_mant_n30"]
    return out


evf = regla_eventos(ap)
cand_all = evf["completed"] & evf["has_maint"]
sin_veh = cand_all & evf["vehicle_id"].isna()
final_rows = [
    ("(2) visita_red: (60) o (90), con vehicle_id, ScheduleDate <= CUTOFF", evf["visita_red"]),
    ("candidatos a objetivo: (60) & has_maint (definición preliminar)", cand_all),
    ("  − excluidos por no tener vehicle_id", sin_veh),
    ("  − descartados: segundo (60)+mant del mismo vehículo el mismo día", evf["dup_mant_dia"]),
    ("  − descartados: mismo maint_number que el anterior a <= 30 días", evf["dup_mant_n30"]),
    ("(1) mant_completado (evento objetivo)", evf["mant_completado"]),
]
final_tab = pd.DataFrame({"turnos": [int(m.sum()) for _, m in final_rows],
                          "vehículos": [evf.loc[m, "vehicle_id"].nunique() for _, m in final_rows]},
                         index=[k for k, _ in final_rows])
emit("11.1 Regla final: conteo de turnos y vehículos", final_tab)
byyear = evf.groupby(evf["event_date"].dt.year)[["visita_red", "mant_completado"]].sum()
emit("11.2 Eventos por año (event_date)", byyear)

# Casos borde (los textos con cifras se calculan, no se tipean)
mask_only = lambda c: item_sets.reindex(ap["schedule_id"]).map(lambda s, c=c: c in s and s <= ({c} | aux)).values
n30_fut = int((ap["StatusARG"].eq(S30) & (ap["ScheduleDate"] > CUTOFF)).sum())
canc_n_eff = 1 - lag_to_completed(canc[canc["IsReschedule"].eq("N")], comp, 0, 90).mean()
ns_eff = 1 - lag_to_completed(ns_, comp, 0, 90).mean()
edge = pd.DataFrame([
    ("(60) con ítem mantenimiento + otros ítems (recall, diagnóstico, PUD...)", int((ap["completed"] & ap["has_maint"] & ap["n_items"].gt(1)).sum()), "objetivo", "el mantenimiento se hizo; los demás ítems son features"),
    ("(60) solo campaña/recall", int((ap["completed"] & mask_only("CAMPANA_RECALL")).sum()), "visita, no objetivo", "gratuito, iniciado por Ford; no es mantenimiento programado"),
    ("(60) solo Guarantee", int((ap["completed"] & mask_only("GARANTIA")).sum()), "visita, no objetivo", "reparación en garantía, sin número de service"),
    ("(60) solo Oil and filter change", int((ap["completed"] & mask_only("ACEITE_FILTRO")).sum()), "visita, no objetivo (consultar)", "cambio de aceite fuera del plan; aparece solo en 2026"),
    ("(60) solo Contactless service", int((ap["completed"] & mask_only("CONTACTLESS")).sum()), "visita, no objetivo", "48 ítems en 2024, sin número de service"),
    ("(60) solo Inspección Ford / Revisión de viaje", int((ap["completed"] & mask_only("INSPECCION")).sum()), "visita, no objetivo", "inspección, no mantenimiento del plan"),
    ("(60) solo diagnóstico / reparación / otros", int((ap["completed"] & ~ap["has_maint"] & ~ap["i_CAMPANA_RECALL"] & ~ap["i_GARANTIA"] & ~ap["i_ACEITE_FILTRO"] & ~ap["i_CONTACTLESS"] & ~ap["i_INSPECCION"]).sum()), "visita, no objetivo", "contacto con la red (feature de relación)"),
    ("(90) Concluido sin OS con ítem mantenimiento", int((ap["completed_no_os"] & ap["has_maint"]).sum()), "visita, no objetivo", "sin orden de servicio: no hay evidencia de trabajo facturado"),
    ("(90) Concluido sin OS sin ítem mantenimiento", int((ap["completed_no_os"] & ~ap["has_maint"]).sum()), "visita, no objetivo", "el auto entró (check-out en 96%), pero no hubo OS"),
    ("(40) En progreso con check-in y ScheduleDate <= CUTOFF", int((ap["StatusARG"].eq(S40) & ap["EffectiveCheckinDate"].notna() & (ap["ScheduleDate"] <= CUTOFF)).sum()), "censurado", "abierto al corte; puede terminar en (60); no usar como negativo"),
    ("(30) Agendado", int(ap["StatusARG"].eq(S30).sum()), "nada (feature 'turno futuro')", f"reserva pendiente; {n30_fut} con fecha posterior al CUTOFF"),
    ("(70) Cancelado", int(ap["cancelled"].sum()), "nada como evento; feature", f"IsReschedule=Y suele reprogramarse; =N es cancelación efectiva en {pct(canc_n_eff)} a 90 d"),
    ("(80) No asistió", int(ap["no_show"].sum()), "nada como evento; feature", f"{pct(ns_eff)} no vuelve en 90 días"),
    ("Sin vehicle_id", int(ap["vehicle_id"].isna().sum()), "excluir de eventos", "no se puede asignar a un usuario-vehículo-ventana"),
    ("Con vehicle_id pero sin customer_id", int((ap["vehicle_id"].notna() & ap["customer_id"].isna()).sum()), "evento del vehículo", "el target es por vehículo; el customer se resuelve por linkage"),
    ("Segundo (60)+mant del mismo vehículo el mismo día", int(evf["dup_mant_dia"].sum()), "un solo evento (se conserva el primero)", "duplicado administrativo"),
    ("(60)+mant con el mismo maint_number que el anterior a <= 30 días", int(evf["dup_mant_n30"].sum()), "un solo evento (se conserva el primero)", "mismo service registrado dos veces"),
    ("(60)+mant sin EffectiveCheckinDate", int((ap["completed"] & ap["has_maint"] & ap["EffectiveCheckinDate"].isna()).sum()), "objetivo; event_date = ScheduleDate", "check-out siempre presente en (60)"),
    ("(60)+mant con ScheduleReturn = Y", int((ap["completed"] & ap["has_maint"] & ap["ScheduleReturn"].eq("Y")).sum()), "objetivo", "retorno que incluyó mantenimiento; dedup cubre repeticiones"),
    ("(60)+mant con maint_number menor que el anterior del vehículo", int((pairs["delta_n"] < 0).sum()), "objetivo", "maint_number es ruidoso como contador; no invalida el evento"),
], columns=["caso borde", "turnos", "decisión", "motivo"]).set_index("caso borde")
emit("11.3 Casos borde y decisión", edge)

# Fecha del evento: event_date (check-in, si no ScheduleDate) vs EffectiveCheckoutDate en el target
tgt = evf[evf["mant_completado"]]
d_ci = (tgt["EffectiveCheckinDate"] - tgt["ScheduleDate"]).dt.days
d_co = (tgt["EffectiveCheckoutDate"] - tgt["event_date"]).dt.days
emit("11.4 Fecha del evento objetivo: check-in vs check-out vs ScheduleDate", pd.DataFrame({"valor": [
    pct(tgt["EffectiveCheckinDate"].notna().mean()), pct(tgt["EffectiveCheckoutDate"].notna().mean()),
    pct(d_ci.eq(0).mean()), pct(d_ci.abs().gt(7).mean()), int(d_ci.lt(-30).sum()), int(d_ci.gt(30).sum()),
    pct(d_co.between(0, 3).mean()), pct(d_co.gt(30).mean()), int(tgt["event_date"].lt("2024-01-01").sum()),
    str(a["EffectiveCheckinDate"].min().date()), int((a["EffectiveCheckinDate"] < "2024-01-01").sum()),
]}, index=["% con EffectiveCheckinDate", "% con EffectiveCheckoutDate", "% check-in el mismo día que ScheduleDate",
           "% |check-in − ScheduleDate| > 7 días", "check-in más de 30 días ANTES de ScheduleDate", "check-in más de 30 días DESPUÉS de ScheduleDate",
           "% check-out entre 0 y 3 días después de event_date", "% check-out > 30 días después de event_date", "eventos con event_date anterior a 2024-01-01",
           "mínimo EffectiveCheckinDate en la agenda (filas ítem)", "filas ítem con EffectiveCheckinDate anterior a 2024-01-01"]))

# ---------------------------------------------------------------------------------------------
# Apéndice de tablas
# ---------------------------------------------------------------------------------------------
header = ("# Apéndice generado: tablas del EDA 01 (taxonomía de eventos y target)\n\n"
          f"Generado por `scripts/eda/01_taxonomia_target.py` sobre `data/interim/agenda.parquet` "
          f"({n_raw} filas, {n_dup} duplicadas eliminadas) y `sales.parquet`. CUTOFF = {CUTOFF.date()}.\n\n")
TABLES_MD.write_text(header + "\n".join(_sections), encoding="utf-8")
print(f"\n[ok] tablas -> {TABLES_MD}")
print(f"[ok] figuras -> {FIG_DIR}/{PREFIX}*.png")
