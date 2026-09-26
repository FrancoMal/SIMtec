"""EDA 05 - Calidad de datos, cobertura temporal y riesgos de leakage.

Genera TODAS las tablas y figuras citadas en reports/eda/05_calidad_cobertura_leakage.md.

Salidas:
- reports/eda/05_calidad_cobertura_leakage_salida.md : todas las tablas (markdown) con los numeros citados.
- reports/figures/eda/05_calidad_cobertura_leakage_*.png : figuras.

Ejecutar desde la carpeta del proyecto:
    PYTHONIOENCODING=utf8 PYTHONPATH=src .venv/Scripts/python.exe scripts/eda/05_calidad_cobertura_leakage.py

Secciones (mismo orden que el informe):
    A. Left-censoring (historia previa invisible) por fecha de scoring.
    B. Columnas snapshot vs evento (ConnectedStatusARG, KM, WarrantyStartDate, ModelYear, TMA, Region, Zona).
    C. Survey: semantica temporal de SurveyResponseDate.
    D. Turnos futuros / pendientes y flags con informacion posterior (IsReschedule, ScheduleReturn).
    E. Inconsistencias puntuales (fechas, km, precios, PersonType, Status, WSD).
    F. Turnos sin vehicle_id / customer_id.
    G. Duplicados logicos.
    H. Cobertura sales vs agenda.
    I. Sintesis: columnas con riesgo de leakage y exclusiones recomendadas.
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from repurchase import config
from repurchase.eventos import CUTOFF, appointments
from repurchase.io import load_agenda, load_sales

warnings.filterwarnings("ignore", category=FutureWarning)
pd.set_option("display.width", 250)

PREFIX = "05_calidad_cobertura_leakage"
FIG_DIR = config.FIGURES_DIR / "eda"
OUT_MD = config.REPORTS_DIR / "eda" / f"{PREFIX}_salida.md"
FIG_DIR.mkdir(parents=True, exist_ok=True)
OUT_MD.parent.mkdir(parents=True, exist_ok=True)

AG_START = pd.Timestamp("2024-01-01")
SCORING_DATES = [pd.Timestamp(x) for x in ("2024-07-01", "2025-01-01", "2025-07-01", "2026-01-01")] + [CUTOFF]

# --- Paleta (referencia validada del skill dataviz; orden fijo, no se cicla) ---
C = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
ORDINAL = ["#86b6ef", "#5598e7", "#2a78d6", "#1c5cab", "#104281"]  # rampa azul, para fechas ordenadas
INK, INK2, MUTED, GRID, AXIS, SURFACE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"
plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "xtick.color": MUTED, "ytick.color": MUTED,
    "text.color": INK, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "grid.linestyle": "-",
    "axes.spines.top": False, "axes.spines.right": False, "axes.titlesize": 11, "axes.titleweight": "bold",
    "font.size": 9, "legend.frameon": False, "figure.dpi": 130,
})

OUT: list[str] = []


def emit(*lines: str) -> None:
    for ln in lines:
        OUT.append(ln)
        print(ln)


def table(df: pd.DataFrame, floatfmt: str = ",.1f", index: bool = True,
          int_rows: list | None = None, int_cols: list | None = None) -> None:
    """Tabla markdown. `int_rows` / `int_cols` se formatean sin decimales; NaN se muestra vacio."""
    if int_rows or int_cols:
        out = df.copy().astype(object)
        for r in out.index:
            for c_ in out.columns:
                v = out.at[r, c_]
                if isinstance(v, (int, float, np.integer, np.floating)):
                    if pd.isna(v):
                        out.at[r, c_] = ""
                    elif (int_rows and r in int_rows) or (int_cols and c_ in int_cols):
                        out.at[r, c_] = f"{v:,.0f}"
                    else:
                        out.at[r, c_] = format(v, floatfmt)
        emit(out.to_markdown(index=index, disable_numparse=True), "")
    else:
        emit(df.to_markdown(floatfmt=floatfmt, index=index), "")


def pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def savefig(fig: plt.Figure, name: str) -> Path:
    p = FIG_DIR / f"{PREFIX}_{name}.png"
    fig.tight_layout()
    fig.savefig(p, bbox_inches="tight")
    plt.close(fig)
    emit(f"Figura: `{p.relative_to(config.PROJECT_DIR).as_posix()}`", "")
    return p


# =====================================================================================
# Carga
# =====================================================================================
emit(f"# Salida del script `scripts/eda/{PREFIX}.py`", "",
     f"CUTOFF = {CUTOFF.date()} ; inicio de la agenda = {AG_START.date()}", "")
sales = load_sales()
agenda = load_agenda()
ap = appointments(agenda)
apv = ap.dropna(subset=["vehicle_id"])
emit(f"sales: {len(sales):,} filas / {sales.vehicle_id.nunique():,} vehiculos. "
     f"agenda: {len(agenda):,} filas-item / {ap.shape[0]:,} turnos / {apv.vehicle_id.nunique():,} vehiculos con id. "
     f"Mantenimientos concluidos (is_completed_maintenance): {int(ap.is_completed_maintenance.sum()):,}.", "")

# =====================================================================================
# A. LEFT-CENSORING
# =====================================================================================
emit("## A. Left-censoring: historia previa invisible", "")
veh = apv.groupby("vehicle_id").agg(WSD=("WarrantyStartDate", "first"), ModelYear=("ModelYear", "first"),
                                    first_ev=("event_date", "min"), n_appt=("schedule_id", "size"))
n_wsd = int(veh.WSD.notna().sum())
emit(f"Vehiculos en agenda con id: {len(veh):,}; con WarrantyStartDate: {n_wsd:,} (nulo: {veh.WSD.isna().sum():,}). "
     f"Con WSD anterior al inicio de la agenda (historia previa invisible): {(veh.WSD < AG_START).sum():,} "
     f"({pct((veh.WSD < AG_START).mean())} de todos los vehiculos con id; {pct((veh.WSD < AG_START).sum() / n_wsd)} de los que tienen WSD); "
     f"con WSD anterior a 2023-01-01: {(veh.WSD < '2023-01-01').sum():,} ({pct((veh.WSD < '2023-01-01').mean())} de todos).", "")

cm = apv[apv.is_completed_maintenance].copy()
AGE_BINS, AGE_LABELS = [-10, 1, 2, 3, 5, 8, 40], ["<1", "1-2", "2-3", "3-5", "5-8", "8+"]
rowsA, rowsA2, dsl_by_t = [], {}, {}
for t in SCORING_DATES:
    win_days = (t - AG_START).days
    active = apv.loc[apv.event_date < t, "vehicle_id"].unique()
    prev = cm[cm.event_date < t]
    n_prev = prev.groupby("vehicle_id").size().reindex(active, fill_value=0)
    last = prev.groupby("vehicle_id").event_date.max().reindex(active)
    dsl = (t - last).dt.days.dropna()
    last_mn = prev.sort_values("event_date").groupby("vehicle_id").maint_number.last().reindex(active)
    gap = (last_mn - n_prev).dropna()
    age = ((t - veh.WSD.reindex(active)).dt.days / 365.25)
    age_b = pd.cut(age, AGE_BINS, labels=AGE_LABELS)
    dsl_by_t[t] = dsl
    rowsA.append({
        "fecha scoring t": str(t.date()), "meses observables": round(win_days / 30.44, 1),
        "vehiculos activos (>=1 turno < t)": len(active),
        "% sin mant. observado": 100 * (n_prev == 0).mean(),
        "% con 1 mant.": 100 * (n_prev == 1).mean(), "% con >=2 mant.": 100 * (n_prev >= 2).mean(),
        "mediana dias desde ult. mant.": dsl.median(), "p90 dias desde ult. mant.": dsl.quantile(0.9),
        "max observable (dias)": win_days,
        "% maint_number > n obs. (hist. invisible)": 100 * (gap > 0).mean(),
        "mediana services invisibles (gap)": gap.median(),
    })
    rowsA2[str(t.date())] = (100 * (n_prev == 0).groupby(age_b, observed=True).mean()).round(1)
A1 = pd.DataFrame(rowsA).set_index("fecha scoring t")
emit("### A1. Historia observable por fecha de scoring", "")
emit("`% sin mant. observado` = vehiculos activos sin ningun mantenimiento concluido antes de t. "
     "`gap` = maint_number del ultimo service observado menos cantidad de mantenimientos observados (services que ocurrieron antes de 2024 y no vemos).", "")
table(A1.T, floatfmt=",.1f", int_rows=["vehiculos activos (>=1 turno < t)", "mediana dias desde ult. mant.", "p90 dias desde ult. mant.",
                                        "max observable (dias)", "mediana services invisibles (gap)"])
A2 = pd.DataFrame(rowsA2)
A2.index.name = "edad del vehiculo en t (anios)"
emit("### A2. % de vehiculos activos sin mantenimiento observado, por edad y fecha de scoring", "")
table(A2)
# Truncamiento: usando la distribucion al CUTOFF (32 meses) como referencia
ref = dsl_by_t[CUTOFF]
A3 = pd.DataFrame({
    "fecha scoring t": [str(t.date()) for t in SCORING_DATES[:-1]],
    "ventana observable (dias)": [(t - AG_START).days for t in SCORING_DATES[:-1]],
    "% de la distribucion de referencia (CUTOFF) que supera la ventana": [100 * (ref > (t - AG_START).days).mean() for t in SCORING_DATES[:-1]],
}).set_index("fecha scoring t")
emit("### A3. Cota aproximada del truncamiento de 'dias desde el ultimo mantenimiento'", "")
emit("Referencia: distribucion observada al CUTOFF (ventana de 967 dias), que a su vez sigue truncada por arriba; "
     "el numero es una cota inferior de la fraccion de vehiculos cuyo verdadero 'dias desde el ultimo mantenimiento' no cabe en la ventana.", "")
table(A3, int_cols=["ventana observable (dias)"])
emit("Lectura: A3 describe el corte transversal al CUTOFF entre vehiculos con >=1 mantenimiento en 32 meses (incluye a los que no visitan la red "
     "hace mas de 6 meses); NO es la fraccion de vehiculos activos en t con recencia truncada. Esa fraccion se mide en A5 con la misma poblacion "
     "y distinta profundidad de historia.", "")
# A5: misma poblacion (activos en los ultimos 182 dias al CUTOFF), distinta profundidad de historia
act6 = apv.loc[(apv.event_date < CUTOFF) & (apv.event_date >= CUTOFF - pd.Timedelta(days=182)), "vehicle_id"].unique()
age6 = (CUTOFF - veh.WSD.reindex(act6)).dt.days / 365.25
ab6 = pd.cut(age6, AGE_BINS, labels=AGE_LABELS)
rowsA5 = []
for look in (182, 366, 547, 731, (CUTOFF - AG_START).days):
    pv = cm[(cm.event_date < CUTOFF) & (cm.event_date >= CUTOFF - pd.Timedelta(days=look))].groupby("vehicle_id").size().reindex(act6, fill_value=0)
    r = {"historia observable (dias)": look, "% sin mant. observado": 100 * (pv == 0).mean()}
    r.update((100 * (pv == 0).groupby(ab6, observed=True).mean()).round(1).to_dict())
    rowsA5.append(r)
A5 = pd.DataFrame(rowsA5).set_index("historia observable (dias)")
emit(f"### A5. Misma poblacion (vehiculos con >=1 turno en los 182 dias previos al CUTOFF, n={len(act6):,}): "
     "% sin mantenimiento observado segun la profundidad de historia, total y por edad en el CUTOFF", "")
emit("Aisla el efecto de la profundidad de historia (lo que cambia con la fecha de scoring) del efecto calendario/poblacion que mezclan A1 y A2. "
     "La diferencia entre la fila 182 y la fila 967 es la fraccion de vehiculos que un backtest con 6 meses de historia etiqueta 'sin mantenimiento' por truncamiento.", "")
table(A5)
# maint_number como proxy de historia
first = cm.sort_values("event_date").groupby("vehicle_id").first()
first["edad"] = (first.event_date - first.WarrantyStartDate).dt.days / 365.25
ct = pd.crosstab(pd.cut(first.edad, AGE_BINS, labels=AGE_LABELS), first.maint_number.clip(upper=8).astype(int))
ct.columns = [f"{c}" if c < 8 else "8+" for c in ct.columns]
ct.index.name = "edad al primer service observado"
ct.columns.name = "maint_number del primer service observado"
emit("### A4. maint_number del primer service observado vs. edad del vehiculo (proxy de historia invisible)", "")
corr = first[["maint_number", "edad"]].corr().iloc[0, 1]
emit(f"Correlacion (maint_number del primer service observado, edad en anios) = {corr:.3f}. "
     f"Vehiculos con edad > 2 anios cuyo primer service observado es el 1°: {int(((first.maint_number == 1) & (first.edad > 2)).sum()):,} "
     f"de {int((first.edad > 2).sum()):,} ({pct(((first.maint_number == 1) & (first.edad > 2)).sum() / (first.edad > 2).sum())}).", "")
table(ct, floatfmt=",.0f")
cm_s = cm.sort_values(["vehicle_id", "event_date"])
inc = (cm_s.maint_number - cm_s.groupby("vehicle_id").maint_number.shift()).dropna()
emit(f"Incremento de maint_number entre mantenimientos consecutivos del mismo vehiculo (n={len(inc):,}): "
     f"+1 en {pct((inc == 1).mean())}, +2 en {pct((inc == 2).mean())}, <=0 en {pct((inc <= 0).mean())}.", "")
# A4b: tasa de falsos positivos del proxy 'gap > 0' en vehiculos cuya historia completa es visible (WSD >= 2024-01-01)
rowsA4b = []
for t in (pd.Timestamp("2025-01-01"), CUTOFF):
    prev = cm[cm.event_date < t]
    n_prev = prev.groupby("vehicle_id").size()
    last_mn = prev.sort_values("event_date").groupby("vehicle_id").maint_number.last()
    gap = (last_mn - n_prev).dropna()
    w = veh.WSD.reindex(gap.index)
    for lab, mask in (("WSD < 2024-01-01 (historia invisible posible)", w < AG_START), ("WSD >= 2024-01-01 (toda la historia es visible)", w >= AG_START)):
        gg_ = gap[mask]
        rowsA4b.append({"fecha scoring t": str(t.date()), "grupo": lab, "vehiculos": len(gg_), "% gap > 0": 100 * (gg_ > 0).mean(),
                        "% gap >= 2": 100 * (gg_ >= 2).mean(), "% gap < 0": 100 * (gg_ < 0).mean(), "mediana gap": gg_.median()})
A4b = pd.DataFrame(rowsA4b).set_index(["fecha scoring t", "grupo"])
emit("### A4b. gap = maint_number del ultimo service - mantenimientos observados, segun si la historia previa puede ser invisible (tasa de falsos positivos del proxy)", "")
emit("En vehiculos entregados desde 2024 no hay historia invisible: un gap > 0 ahi es salto de numeracion o un service hecho fuera de la red / del extracto.", "")
table(A4b, int_cols=["vehiculos", "mediana gap"])
lab_sm = agenda[agenda.ServiceMaintenance.isin([11, 12, 13, 19])].groupby("ServiceMaintenance").ServiceName.agg(
    lambda s: ", ".join(f"{k} ({v:,})" for k, v in s.value_counts().head(3).items()))
emit("ServiceName segun ServiceMaintenance (el nombre pierde el primer digito en 11, 12, 19 y en parte de 13; el codigo numerico es el coherente con la edad del vehiculo): "
     + "; ".join(f"{int(k)} -> {v}" for k, v in lab_sm.items()) + ".", "")
med_age = cm.assign(edad=(cm.event_date - cm.WarrantyStartDate).dt.days / 365.25).groupby("maint_number").edad.median()
emit("Edad mediana (anios) al service segun maint_number: " + ", ".join(f"{int(k)}°: {v:.2f}" for k, v in med_age.items()), "")

# Figura A: censura izquierda
fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
ax = axes[0]
x = np.arange(len(AGE_LABELS)); w = 0.16
for i, (tname, col) in enumerate(A2.items()):
    ax.bar(x + (i - 2) * w, col.values, width=w - 0.02, color=ORDINAL[i], label=tname)
ax.set_xticks(x); ax.set_xticklabels(AGE_LABELS)
ax.set_xlabel("Edad del vehiculo en t (anios, segun WarrantyStartDate)")
ax.set_ylabel("% de vehiculos activos sin mantenimiento observado")
ax.set_title("Sin historia de mantenimiento observable, por edad y fecha de scoring")
ax.legend(title="fecha de scoring t", fontsize=8)
ax = axes[1]
for i, t in enumerate(SCORING_DATES):
    d = np.sort(dsl_by_t[t].values)
    ax.plot(d, np.arange(1, len(d) + 1) / len(d), color=ORDINAL[i], lw=2, label=f"{t.date()} (max {(t - AG_START).days} d)")
    ax.axvline((t - AG_START).days, color=ORDINAL[i], lw=0.8, alpha=0.6)
ax.set_xlabel("Dias desde el ultimo mantenimiento concluido (vehiculos con >=1)")
ax.set_ylabel("Fraccion acumulada de vehiculos")
ax.set_title("Distribucion truncada por la ventana observable")
ax.legend(fontsize=8)
savefig(fig, "censura_izquierda")

fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
ax = axes[0]
share = ct.div(ct.sum(axis=1), axis=0)
im = ax.imshow(share.values, cmap=matplotlib.colors.LinearSegmentedColormap.from_list("azul", ["#f4f8fd", "#cde2fb", "#6da7ec", "#256abf", "#0d366b"]), aspect="auto", vmin=0, vmax=1)
ax.set_xticks(range(share.shape[1])); ax.set_xticklabels(share.columns)
ax.set_yticks(range(share.shape[0])); ax.set_yticklabels(share.index)
ax.set_xlabel("maint_number del primer service observado"); ax.set_ylabel("Edad al primer service observado (anios)")
ax.set_title("maint_number recupera la historia invisible")
ax.grid(False)
for i in range(share.shape[0]):
    for j in range(share.shape[1]):
        v = share.values[i, j]
        if v >= 0.10:
            ax.text(j, i, f"{100 * v:.0f}%", ha="center", va="center", fontsize=8, color="white" if v > 0.5 else INK)
fig.colorbar(im, ax=ax, fraction=0.04, label="fraccion por fila")
ax = axes[1]
gaps = {}
for t in SCORING_DATES:
    prev = cm[cm.event_date < t]
    n_prev = prev.groupby("vehicle_id").size()
    last_mn = prev.sort_values("event_date").groupby("vehicle_id").maint_number.last()
    g = (last_mn - n_prev).clip(lower=-1, upper=10)
    gaps[str(t.date())] = g.value_counts(normalize=True).sort_index()
G = pd.DataFrame(gaps).fillna(0) * 100
x = np.arange(len(G)); w = 0.16
for i, (tname, col) in enumerate(G.items()):
    ax.bar(x + (i - 2) * w, col.values, width=w - 0.02, color=ORDINAL[i], label=tname)
ax.set_xticks(x); ax.set_xticklabels([("<=-1" if v == -1 else ("10+" if v == 10 else str(int(v)))) for v in G.index])
ax.set_xlabel("maint_number del ultimo service - mantenimientos observados (services invisibles)")
ax.set_ylabel("% de vehiculos con >=1 mantenimiento observado")
ax.set_title("Services previos a 2024 que no vemos, por fecha de scoring")
ax.legend(title="fecha de scoring t", fontsize=8)
savefig(fig, "historia_invisible")

# =====================================================================================
# B. SNAPSHOT vs EVENTO
# =====================================================================================
emit("## B. Columnas snapshot (foto a la extraccion) vs. evento", "")
cols = ["ConnectedStatusARG", "KM", "VehicleCurrentKM", "WarrantyStartDate", "ModelYear", "TMA",
        "ShortVehicleModelGroupTreated", "Region", "DealerStateOrZone", "dealer_id", "customer_id"]
multi = veh.index[veh.n_appt >= 2]
nu = apv[apv.vehicle_id.isin(multi)].groupby("vehicle_id")[cols].nunique(dropna=True)
nn = apv[apv.vehicle_id.isin(multi)].groupby("vehicle_id")[cols].count()
B1 = pd.DataFrame({
    "vehiculos con >=2 turnos": len(multi),
    "vehiculos con >=2 valores no nulos": (nn >= 2).sum(),
    "vehiculos con >1 valor distinto": (nu > 1).sum(),
    "% con >1 valor (sobre >=2 no nulos)": 100 * ((nu > 1).sum() / (nn >= 2).sum().replace(0, np.nan)),
})
B1.index.name = "columna"
emit("### B1. Variacion dentro de un mismo vehicle_id (solo vehiculos con >=2 turnos)", "")
table(B1, int_cols=["vehiculos con >=2 turnos", "vehiculos con >=2 valores no nulos", "vehiculos con >1 valor distinto"])
gd = agenda.groupby("dealer_id")[["Region", "DealerStateOrZone"]].nunique()
emit(f"Region y DealerStateOrZone son atributos del dealer: dealers con >1 Region = {(gd.Region > 1).sum()}, "
     f"con >1 DealerStateOrZone = {(gd.DealerStateOrZone > 1).sum()} (de {len(gd)}). Varian dentro de un vehiculo solo cuando cambia de dealer.", "")

# ConnectedStatusARG vs trimestre de WSD
vq = veh.assign(cs=apv.groupby("vehicle_id").ConnectedStatusARG.first(), q=veh.WSD.dt.to_period("Q"))
B2 = pd.crosstab(vq.q, vq.cs, normalize="index") * 100
B2 = B2.loc[B2.index >= pd.Period("2023Q1")]
B2["n vehiculos"] = vq.q.value_counts().reindex(B2.index)
B2.index = B2.index.astype(str)
B2.index.name = "trimestre de WarrantyStartDate"
emit("### B2. ConnectedStatusARG (% de vehiculos) por trimestre de WarrantyStartDate", "")
ct_my = pd.crosstab(veh.ModelYear, vq.cs, normalize="index") * 100
emit(f"'Conectado' entre vehiculos con WSD < 2023-07-01: {pct((vq.cs[vq.WSD < '2023-07-01'] == 'Conectado').mean())}; "
     f"con WSD >= 2023-07-01: {pct((vq.cs[vq.WSD >= '2023-07-01'] == 'Conectado').mean())}. "
     f"'Sin Informacion de Conectividad' para ModelYear 2026: {ct_my.loc[2026, 'Sin Información de Conectividad']:.1f}%.", "")
table(B2, int_cols=["n vehiculos"])
B2b = ap.groupby("ConnectedStatusARG")[["completed", "is_completed_maintenance", "no_show", "cancelled"]].mean() * 100
B2b.columns = ["% concluido", "% mant. concluido", "% no asistio", "% cancelado"]
emit("### B2b. Resultado del turno segun ConnectedStatusARG (sin controlar por edad; solo para mostrar que no es una senal fuerte)", "")
table(B2b)

fig, ax = plt.subplots(figsize=(10, 4))
order = ["Conectado", "No Conectado", "No tiene Conectividad", "Sin Información de Conectividad"]
bottom = np.zeros(len(B2))
for i, cat in enumerate(order):
    vals = B2[cat].values if cat in B2 else np.zeros(len(B2))
    ax.bar(B2.index, vals, bottom=bottom, color=C[i], label=cat, width=0.8, edgecolor=SURFACE, linewidth=1.5)
    bottom += vals
ax.set_ylabel("% de vehiculos"); ax.set_xlabel("Trimestre de WarrantyStartDate (entrega)")
ax.set_title("ConnectedStatusARG es una foto a la fecha de extraccion: los vehiculos recientes aun 'sin informacion'")
ax.tick_params(axis="x", rotation=45)
ax.legend(fontsize=8, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.32))
savefig(fig, "conectividad_snapshot")

# KM snapshot
g = apv.groupby("vehicle_id").agg(km_nu=("KM", "nunique"), km_nn=("KM", "count"), km_max=("KM", "max"),
                                  vck_nu=("VehicleCurrentKM", "nunique"), vck_nn=("VehicleCurrentKM", "count"), vck_max=("VehicleCurrentKM", "max"))
last_c = apv[apv.completed].sort_values("event_date").groupby("vehicle_id").VehicleCurrentKM.last()
g = g.join(last_c.rename("vck_last"))
d = ap[ap.completed & ap.KM.notna() & ap.VehicleCurrentKM.notna()].copy()
last_idx = apv[apv.completed].sort_values("event_date").groupby("vehicle_id").tail(1).index
d["es_ultimo_concluido"] = d.index.isin(last_idx)
d["km_igual"] = d.KM == d.VehicleCurrentKM
B3 = pd.DataFrame({
    "metrica": [
        "vehiculos con >=2 valores no nulos de KM cuyo KM es constante",
        "vehiculos con >=2 valores no nulos de VehicleCurrentKM que varian",
        "vehiculos cuyo KM == VehicleCurrentKM del ULTIMO turno concluido (sobre vehiculos con >=1 concluido con VCK)",
        "vehiculos cuyo KM == VehicleCurrentKM del ULTIMO turno concluido (sobre vehiculos con KM y VCK no nulos)",
        "vehiculos cuyo KM >= max(VehicleCurrentKM) (KM y VCK no nulos)",
        "turnos concluidos: KM == VehicleCurrentKM cuando el turno ES el ultimo concluido del vehiculo",
        "turnos concluidos: KM == VehicleCurrentKM cuando NO es el ultimo",
        "turnos concluidos 2024 con KM == VehicleCurrentKM",
        "turnos concluidos 2026 con KM == VehicleCurrentKM",
    ],
    "valor": [
        pct((g.km_nu[g.km_nn >= 2] == 1).mean()), pct((g.vck_nu[g.vck_nn >= 2] > 1).mean()),
        pct((g.km_max == g.vck_last)[g.vck_last.notna()].mean()),
        pct((g.km_max == g.vck_last)[g.vck_last.notna() & g.km_max.notna()].mean()),
        pct((g.km_max >= g.vck_max)[g.vck_max.notna() & g.km_max.notna()].mean()),
        pct(d.km_igual[d.es_ultimo_concluido].mean()), pct(d.km_igual[~d.es_ultimo_concluido].mean()),
        pct(d.km_igual[d.ScheduleDate.dt.year == 2024].mean()), pct(d.km_igual[d.ScheduleDate.dt.year == 2026].mean()),
    ],
}).set_index("metrica")
emit("### B3. KM es una foto del odometro a la extraccion; VehicleCurrentKM es la lectura del turno", "")
table(B3)
emit("Nulos de VehicleCurrentKM por StatusARG: " + ", ".join(f"{k}: {pct(v)}" for k, v in ap.groupby("StatusARG").VehicleCurrentKM.apply(lambda x: x.isna().mean()).items()), "")

fig, axes = plt.subplots(1, 2, figsize=(11, 4))
ax = axes[0]
byy = d.groupby([d.ScheduleDate.dt.year, "es_ultimo_concluido"]).km_igual.mean().unstack() * 100
x = np.arange(len(byy)); w = 0.36
ax.bar(x - w / 2, byy[False].values, width=w - 0.03, color=C[0], label="turno NO es el ultimo concluido del vehiculo")
ax.bar(x + w / 2, byy[True].values, width=w - 0.03, color=C[1], label="turno ES el ultimo concluido del vehiculo")
ax.set_xticks(x); ax.set_xticklabels(byy.index)
ax.set_ylabel("% de turnos concluidos con KM == VehicleCurrentKM"); ax.set_xlabel("Anio del turno")
ax.set_title("KM coincide con la lectura del turno\nsolo cuando es el ultimo turno del vehiculo (foto)")
ax.legend(fontsize=8, loc="upper left")
ax = axes[1]
diff = (d.KM - d.VehicleCurrentKM) / 1000
inrange = diff.between(-5, 120)
bins = np.linspace(-5, 120, 61)
ax.hist(diff[inrange & ~d.es_ultimo_concluido], bins=bins, color=C[0], alpha=0.9, label="no es el ultimo turno concluido")
ax.hist(diff[inrange & d.es_ultimo_concluido], bins=bins, color=C[1], alpha=0.9, label="es el ultimo turno concluido")
ax.set_xlabel("KM - VehicleCurrentKM (miles de km, solo el rango [-5, 120])"); ax.set_ylabel("Turnos concluidos")
ax.set_title("En los turnos pasados KM excede la lectura:\nson los km recorridos despues del turno")
ax.legend(fontsize=8)
emit(f"Turnos concluidos fuera del rango [-5.000, 120.000] de KM - VehicleCurrentKM (no graficados): {int((~inrange).sum()):,} de {len(d):,}.", "")
savefig(fig, "km_snapshot")

# =====================================================================================
# C. SURVEY
# =====================================================================================
emit("## C. Survey: SurveyResponseDate es ANTERIOR al turno", "")
sv = ap.dropna(subset=["SurveyResponseDate"]).copy()
lag_out = (sv.SurveyResponseDate - sv.EffectiveCheckoutDate).dt.days
lag_in = (sv.SurveyResponseDate - sv.EffectiveCheckinDate).dt.days
lag_sch = (sv.SurveyResponseDate - sv.ScheduleDate).dt.days
def q(s: pd.Series) -> dict:
    s = s.dropna()
    return {"n": len(s), "min": s.min(), "p5": s.quantile(0.05), "p25": s.quantile(0.25), "mediana": s.median(),
            "p75": s.quantile(0.75), "p95": s.quantile(0.95), "max": s.max(), "% <0": 100 * (s < 0).mean(), "% >0": 100 * (s > 0).mean()}
C1 = pd.DataFrame({"survey - checkout": q(lag_out), "survey - checkin": q(lag_in), "survey - ScheduleDate": q(lag_sch)}).T
emit(f"Turnos con survey: {len(sv):,} de {len(ap):,} ({pct(len(sv) / len(ap))}). Por StatusARG: "
     + ", ".join(f"{k}: {v:,}" for k, v in sv.StatusARG.value_counts().items()) + ".", "")
emit("### C1. Lag (dias) entre SurveyResponseDate y las fechas del mismo turno (solo turnos con ambas fechas)", "")
table(C1, int_cols=["n", "min", "p5", "p25", "mediana", "p75", "p95", "max"])
src = ap.groupby("ScheduleSource").SurveyResponseDate.apply(lambda x: x.notna().mean()) * 100
emit("% de turnos con survey por ScheduleSource: " + ", ".join(f"{k}: {v:.1f}%" for k, v in src.items()) + ".", "")
emit("Rating medio por StatusARG del turno: " + ", ".join(f"{k}: {v:.2f}" for k, v in sv.groupby("StatusARG").SurveyStarRating.mean().items()) + ".", "")
# no es la survey de la visita anterior
apx = apv.sort_values(["vehicle_id", "event_date"]).copy()
cmpl = apx[apx.completed][["vehicle_id", "EffectiveCheckoutDate"]].dropna().sort_values("EffectiveCheckoutDate")
svs = apx.dropna(subset=["SurveyResponseDate"])[["vehicle_id", "SurveyResponseDate"]].sort_values("SurveyResponseDate")
mrg = pd.merge_asof(svs, cmpl.rename(columns={"EffectiveCheckoutDate": "prev_checkout"}), left_on="SurveyResponseDate",
                    right_on="prev_checkout", by="vehicle_id", direction="backward")
lag3 = (mrg.SurveyResponseDate - mrg.prev_checkout).dt.days
emit(f"Hipotesis 'survey de la visita anterior' descartada: lag entre la survey y el ultimo checkout concluido previo del mismo vehiculo: "
     f"mediana {lag3.median():.0f} dias, solo {pct((lag3 <= 14).mean())} a <=14 dias, {pct(lag3.isna().mean())} sin visita previa.", "")
emit(f"Surveys con fecha posterior al CUTOFF: {int((ap.SurveyResponseDate > CUTOFF).sum())}; minima fecha de survey: {ap.SurveyResponseDate.min().date()}.", "")
dup_sv = sv.dropna(subset=["vehicle_id"]).duplicated(subset=["vehicle_id", "SurveyResponseDate"], keep=False)
emit(f"Turnos con survey cuyo (vehicle_id, SurveyResponseDate) se repite en otro turno del mismo vehiculo: {int(dup_sv.sum()):,} ({pct(dup_sv.mean())}), "
     "en su mayoria pares que incluyen un cancelado (re-agendamiento): la survey esta atada a la sesion de reserva, no al turno.", "")
rowsC2 = []
for t in (pd.Timestamp("2025-07-01"), pd.Timestamp("2026-01-01")):
    k = ap[(ap.ScheduleDate >= t) & (ap.SurveyResponseDate < t)]
    rowsC2.append(f"t={t.date()}: {len(k):,} turnos / {k.vehicle_id.nunique():,} vehiculos ({int(k.completed.sum()):,} luego concluidos)")
emit("Reservas futuras conocidas en t via survey (unico caso en que un turno con ScheduleDate >= t es informacion legitima en t; solo canales digitales): "
     + "; ".join(rowsC2) + ".", "")
lt = (sv.ScheduleDate - sv.SurveyResponseDate).dt.days
emit(f"Como proxy de anticipacion de la reserva (ScheduleDate - SurveyResponseDate): mediana {lt.median():.0f} dias, p75 {lt.quantile(.75):.0f}, "
     f"p90 {lt.quantile(.9):.0f}; {pct((lt <= 14).mean())} a <=14 dias y {pct((lt <= 30).mean())} a <=30 dias.", "")

fig, axes = plt.subplots(1, 2, figsize=(11, 4))
ax = axes[0]
ax.hist(lag_sch[lag_sch.between(-40, 5)], bins=np.arange(-40, 7) - 0.5, color=C[0])
ax.axvline(0, color=INK2, lw=1)
ax.set_xlabel("SurveyResponseDate - ScheduleDate (dias, solo el rango [-40, 5])"); ax.set_ylabel("Turnos con survey")
ax.set_title("La survey se responde ANTES de la fecha del turno")
ax = axes[1]
ax.hist(lag_out[lag_out.between(-60, 5)], bins=np.arange(-60, 7) - 0.5, color=C[1])
ax.axvline(0, color=INK2, lw=1)
ax.set_xlabel("SurveyResponseDate - EffectiveCheckoutDate (dias, solo el rango [-60, 5])"); ax.set_ylabel("Turnos con survey y checkout")
ax.set_title("Nunca posterior al checkout:\nno califica el servicio recibido")
emit(f"Fuera de rango en la figura: survey - ScheduleDate < -40 d: {int((lag_sch < -40).sum()):,}; survey - checkout < -60 d: {int((lag_out < -60).sum()):,}.", "")
savefig(fig, "survey_lag")

# =====================================================================================
# D. TURNOS FUTUROS / PENDIENTES / FLAGS CON INFORMACION POSTERIOR
# =====================================================================================
emit("## D. Turnos futuros, pendientes y flags que incorporan informacion posterior", "")
fut = ap[ap.ScheduleDate > CUTOFF]
pend = ap[ap.pending]
D1 = pd.DataFrame({
    "turnos": [len(fut), int((fut.StatusARG == "(30) Agendado").sum()), int((fut.StatusARG == "(70) Cancelado").sum()),
               int((fut.StatusARG == "(40) En progreso").sum()), int(fut.has_maint.sum()),
               len(pend), int((pend.ScheduleDate <= CUTOFF).sum()),
               int(((pend.ScheduleDate <= CUTOFF - pd.Timedelta(days=30))).sum()),
               int(((pend.ScheduleDate <= CUTOFF - pd.Timedelta(days=30)) & (pend.StatusARG == "(40) En progreso")).sum()),
               int(((pend.ScheduleDate <= CUTOFF - pd.Timedelta(days=30)) & (pend.StatusARG == "(30) Agendado")).sum()),
               int(((pend.ScheduleDate <= CUTOFF - pd.Timedelta(days=180))).sum())],
    "vehiculos": [fut.vehicle_id.nunique(), fut[fut.StatusARG == "(30) Agendado"].vehicle_id.nunique(), np.nan, np.nan,
                  fut[fut.has_maint].vehicle_id.nunique(), pend.vehicle_id.nunique(), pend[pend.ScheduleDate <= CUTOFF].vehicle_id.nunique(),
                  np.nan, np.nan, np.nan, np.nan],
}, index=["ScheduleDate > CUTOFF (reservas futuras)", "  de las cuales (30) Agendado", "  de las cuales (70) Cancelado",
          "  de las cuales (40) En progreso", "  con item de mantenimiento", "pendientes ((30)+(40)) en total",
          "  pendientes con ScheduleDate <= CUTOFF (atrasados)", "  pendientes con ScheduleDate <= CUTOFF-30d (stale)",
          "    (40) En progreso stale", "    (30) Agendado stale", "  pendientes con ScheduleDate <= CUTOFF-180d"])
emit("### D1. Reservas futuras y turnos pendientes", "")
emit(f"Filas-item (30) Agendado con ScheduleDate > CUTOFF en la agenda cruda: {int(((agenda.StatusARG == '(30) Agendado') & (agenda.ScheduleDate > CUTOFF)).sum()):,} "
     f"(el conteo de 4.185 del diccionario es a nivel item; a nivel turno son {int((fut.StatusARG == '(30) Agendado').sum()):,}). "
     f"Reservas futuras por mes: " + ", ".join(f"{k}: {v:,}" for k, v in fut.ScheduleDate.dt.to_period('M').value_counts().sort_index().items()) + ".", "")
table(D1, int_cols=["turnos", "vehiculos"])
en_prog = ap[ap.StatusARG == "(40) En progreso"]
emit(f"(40) En progreso: {pct(en_prog.EffectiveCheckinDate.notna().mean())} tiene check-in y {pct(en_prog.EffectiveCheckoutDate.isna().mean())} no tiene checkout: "
     f"son ordenes abiertas a la fecha de extraccion; las de mas de 30 dias nunca se cerraron en el sistema.", "")
emit(f"Ultimo check-in: {ap.EffectiveCheckinDate.max().date()}; ultimo checkout: {ap.EffectiveCheckoutDate.max().date()}; "
     f"turnos (60) Concluido con ScheduleDate > CUTOFF: {int(((ap.ScheduleDate > CUTOFF) & ap.completed).sum())}.", "")

# IsReschedule / ScheduleReturn
apx["next_ev"] = apx.groupby("vehicle_id").event_date.shift(-1)
apx["next_status"] = apx.groupby("vehicle_id").StatusARG.shift(-1)
apx["prev_ev"] = apx.groupby("vehicle_id").event_date.shift(1)
apx["prev_status"] = apx.groupby("vehicle_id").StatusARG.shift(1)
apx["next_resch"] = apx.groupby("vehicle_id").IsReschedule.shift(-1)
apx["d_next"] = (apx.next_ev - apx.event_date).dt.days
apx["d_prev"] = (apx.event_date - apx.prev_ev).dt.days
canc, comp = apx[apx.cancelled], apx[apx.completed]
rows = []
for v in ["N", "Y"]:
    x = canc[canc.IsReschedule == v]
    rows.append({"grupo": f"(70) Cancelado, IsReschedule={v}", "turnos": len(x), "% con turno posterior <=7d": 100 * (x.d_next <= 7).mean(),
                 "% con turno posterior <=30d": 100 * (x.d_next <= 30).mean(), "% con turno concluido <=30d despues": 100 * ((x.d_next <= 30) & (x.next_status == "(60) Concluido")).mean(),
                 "% con turno anterior <=30d": 100 * (x.d_prev <= 30).mean(), "% con turno anterior cancelado <=30d": 100 * ((x.d_prev <= 30) & (x.prev_status == "(70) Cancelado")).mean()})
for v, x in [("Y", comp[comp.IsReschedule == "Y"]), ("NaN", comp[comp.IsReschedule.isna()])]:
    rows.append({"grupo": f"(60) Concluido, IsReschedule={v}", "turnos": len(x), "% con turno posterior <=7d": 100 * (x.d_next <= 7).mean(),
                 "% con turno posterior <=30d": 100 * (x.d_next <= 30).mean(), "% con turno concluido <=30d despues": 100 * ((x.d_next <= 30) & (x.next_status == "(60) Concluido")).mean(),
                 "% con turno anterior <=30d": 100 * (x.d_prev <= 30).mean(), "% con turno anterior cancelado <=30d": 100 * ((x.d_prev <= 30) & (x.prev_status == "(70) Cancelado")).mean()})
for v in ["Y", "N"]:
    x = comp[comp.ScheduleReturn == v]
    rows.append({"grupo": f"(60) Concluido, ScheduleReturn={v}", "turnos": len(x), "% con turno posterior <=7d": 100 * (x.d_next <= 7).mean(),
                 "% con turno posterior <=30d": 100 * (x.d_next <= 30).mean(), "% con turno concluido <=30d despues": 100 * ((x.d_next <= 30) & (x.next_status == "(60) Concluido")).mean(),
                 "% con turno anterior <=30d": 100 * (x.d_prev <= 30).mean(), "% con turno anterior cancelado <=30d": 100 * ((x.d_prev <= 30) & (x.prev_status == "(70) Cancelado")).mean()})
D2 = pd.DataFrame(rows).set_index("grupo")
emit("### D2. IsReschedule y ScheduleReturn: que informacion codifican (misma unidad vehiculo, turnos ordenados por event_date)", "")
table(D2, int_cols=["turnos"])
cy, cn = canc[canc.IsReschedule == "Y"], canc[canc.IsReschedule == "N"]
emit(f"Cancelados con IsReschedule=Y: {pct(cy.next_ev.notna().mean())} tiene algun turno posterior (N: {pct(cn.next_ev.notna().mean())}) y en "
     f"{pct((cy.next_resch == 'Y').mean())} el turno siguiente tambien tiene IsReschedule=Y (N: {pct((cn.next_resch == 'Y').mean())}): el flag marca el par cancelado / re-agendado.", "")
rc = agenda[agenda.StatusARG == "(70) Cancelado"]
xt = pd.crosstab(rc.IsReschedule.fillna("NaN"), rc.ScheduleStatus.fillna("NaN")).stack()
emit("En filas canceladas IsReschedule es colineal con ScheduleStatus (dos vias de cancelacion del sistema de origen): "
     + "; ".join(f"IsReschedule={k[0]} & ScheduleStatus={k[1]}: {v:,}" for k, v in xt[xt > 0].items()) + ".", "")
sr = comp.groupby("ScheduleReturn")[["has_maint", "has_repair", "has_diag", "has_recall"]].mean() * 100
sr.columns = ["% con mantenimiento", "% con reparacion", "% con diagnostico", "% con campania/recall"]
emit("Composicion del turno concluido segun ScheduleReturn:", "")
table(sr)

# Figura D: turnos por mes y status alrededor del CUTOFF
mon = ap[(ap.ScheduleDate >= "2025-09-01")].groupby([ap.ScheduleDate.dt.to_period("M"), "StatusARG"]).size().unstack(fill_value=0)
st_order = ["(60) Concluido", "(70) Cancelado", "(80) No asistio", "(90) Concluido sin OS", "(30) Agendado", "(40) En progreso"]
mon = mon.reindex(columns=st_order, fill_value=0)
fig, ax = plt.subplots(figsize=(10, 4))
bottom = np.zeros(len(mon)); xl = mon.index.astype(str)
for i, st in enumerate(st_order):
    ax.bar(xl, mon[st].values, bottom=bottom, color=C[i], label=st, width=0.8, edgecolor=SURFACE, linewidth=1.5)
    bottom += mon[st].values
cut_pos = list(xl).index(str(CUTOFF.to_period("M")))
ax.axvline(cut_pos + 0.5, color=INK2, lw=1)
ax.text(cut_pos + 0.6, bottom.max() * 0.55, f"CUTOFF\n{CUTOFF.date()}", fontsize=8, color=INK2)
ax.set_ylabel("Turnos (por ScheduleDate)"); ax.set_xlabel("Mes del turno")
ax.set_title("Despues del CUTOFF solo quedan reservas (30) Agendado: 'tener turno' no es reconstruible hacia atras")
ax.tick_params(axis="x", rotation=45); ax.legend(fontsize=8, ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.3))
savefig(fig, "turnos_pendientes")

# =====================================================================================
# E. INCONSISTENCIAS
# =====================================================================================
emit("## E. Inconsistencias puntuales", "")
c = ap[ap.completed]
bad_my = (ap.ModelYear == 0) | (ap.ModelYear < 2005)
d_wsd = ap.dropna(subset=["ModelYear", "WarrantyStartDate"])
dd = d_wsd.WarrantyStartDate.dt.year - d_wsd.ModelYear
gap_ci = (ap.EffectiveCheckinDate - ap.ScheduleDate).dt.days
# odometro (VehicleCurrentKM) entre visitas concluidas consecutivas
cc = c.dropna(subset=["vehicle_id", "VehicleCurrentKM"]).sort_values(["vehicle_id", "event_date"])
cc = cc[cc.VehicleCurrentKM > 0]
cc["prev"] = cc.groupby("vehicle_id").VehicleCurrentKM.shift(); cc["prev_dt"] = cc.groupby("vehicle_id").event_date.shift()
pair = cc.dropna(subset=["prev"])
dk = pair.VehicleCurrentKM - pair.prev
days = (pair.event_date - pair.prev_dt).dt.days.clip(lower=1)
kmd = dk / days
# WSD sales vs agenda
aw = agenda.dropna(subset=["vehicle_id", "WarrantyStartDate"]).groupby("vehicle_id").WarrantyStartDate.first()
m = sales.set_index("vehicle_id")[["WarrantyStartDate", "SalesDate", "DeliveryDate"]].join(aw.rename("WSD_ag"), how="inner")
dwsd = (m.WSD_ag - m.WarrantyStartDate).dt.days
fa = apv.groupby("vehicle_id").agg(first_sched=("ScheduleDate", "min")).join(
    apv[apv.completed].groupby("vehicle_id").event_date.min().rename("first_compl")).join(aw.rename("WSD"))
x_wsd = (fa.WSD - fa.first_compl).dt.days
spd = agenda.ServicePriceDiscount
mm = agenda[agenda.ServiceMaintenance.notna()]

n_turnos, n_veh, n_sales = len(ap), apv.vehicle_id.nunique(), len(sales)
E1 = pd.DataFrame([
    ["agenda", "ModelYear = 0 o < 2005", f"{int(bad_my.sum()):,} turnos / {ap.loc[bad_my, 'vehicle_id'].nunique()} vehiculos", "flag: edad no confiable (usar WSD si existe); excluir vehiculos si tampoco hay WSD"],
    ["agenda", "ModelYear nulo", f"{int(ap.ModelYear.isna().sum()):,} turnos / {ap.loc[ap.ModelYear.isna(), 'vehicle_id'].nunique()} vehiculos con id ({int(ap.loc[ap.ModelYear.isna(), 'vehicle_id'].isna().sum()):,} sin vehicle_id)", "imputar edad por WSD; si no, flag"],
    ["agenda", "WarrantyStartDate.year - ModelYear fuera de [-1, +1]", f"{int((~dd.between(-1, 1)).sum()):,} turnos ({pct((~dd.between(-1, 1)).mean())})", "dejar con flag; la edad se calcula por WSD"],
    ["agenda", "EffectiveCheckinDate < 2024-01-01", f"{int((ap.EffectiveCheckinDate < AG_START).sum())} turnos (1 en 2001 con DaysInDealer 8.461)", "ya corregido en eventos.py: event_date usa el check-in solo si |check-in - ScheduleDate| <= 45 d"],
    ["agenda", "|EffectiveCheckinDate - ScheduleDate| > 30 dias", f"{int((gap_ci.abs() > 30).sum()):,} turnos (> 10 d: {int((gap_ci.abs() > 10).sum()):,}; > 45 d: {int((gap_ci.abs() > 45).sum()):,})", f"dejar; eventos.py usa el check-in solo si |gap| <= 45 d ({int((gap_ci.abs() > 45).sum()):,} turnos caen a ScheduleDate)"],
    ["agenda", "(60) Concluido sin EffectiveCheckinDate", f"{int((ap.completed & ap.EffectiveCheckinDate.isna()).sum()):,} turnos ({pct((ap.completed & ap.EffectiveCheckinDate.isna()).mean() / ap.completed.mean())} de los concluidos; 2024: {pct(ap[ap.completed & (ap.ScheduleDate.dt.year == 2024)].EffectiveCheckinDate.isna().mean())})", "dejar: event_date cae a ScheduleDate (coincide con el check-in el 91,7% de las veces)"],
    ["agenda", "EffectiveCheckoutDate < EffectiveCheckinDate", f"{int((ap.EffectiveCheckoutDate < ap.EffectiveCheckinDate).sum())} turnos", "dejar con flag (no afecta target)"],
    ["agenda", "(80) No asistio con EffectiveCheckinDate", f"{int((ap.no_show & ap.EffectiveCheckinDate.notna()).sum()):,} turnos ({pct((ap.no_show & ap.EffectiveCheckinDate.notna()).sum() / ap.no_show.sum())} de los no-show)", "dejar: prevalece StatusARG; flag"],
    ["agenda", "KM (snapshot) = 0 en turnos concluidos", f"{int((c.KM == 0).sum())} turnos", "no usar KM como feature (ver B3)"],
    ["agenda", "KM (snapshot) > 500.000 / > 1.000.000", f"{int((c.KM > 5e5).sum()):,} / {int((c.KM > 1e6).sum()):,} turnos concluidos", "no usar KM como feature (ver B3)"],
    ["agenda", "VehicleCurrentKM < 100 en turnos concluidos", f"{int((c.VehicleCurrentKM < 100).sum()):,} turnos ({pct((c.VehicleCurrentKM < 100).mean())}); valores tipicos 1, 10, 3, 12, 30", "corregir: tratar como nulo (placeholder)"],
    ["agenda", "VehicleCurrentKM > 500.000 / > 1.000.000 en concluidos", f"{int((c.VehicleCurrentKM > 5e5).sum()):,} / {int((c.VehicleCurrentKM > 1e6).sum()):,} turnos", "corregir: > 1.000.000 a nulo; 500k-1M flag"],
    ["agenda", "VehicleCurrentKM decrece entre visitas concluidas consecutivas (> 1.000 km)", f"{int((dk < -1000).sum()):,} pares ({pct((dk < -1000).mean())}) en {pair.loc[dk < -1000, 'vehicle_id'].nunique():,} vehiculos de {pair.vehicle_id.nunique():,}", "corregir: km acumulado por vehiculo = maximo acumulado (running max) de lecturas validas; flag por vehiculo"],
    ["agenda", "Ritmo implausible > 300 km/dia entre visitas (excluye mismo dia)", f"{int(((kmd > 300) & (days > 1)).sum()):,} pares ({pct(((kmd > 300) & (days > 1)).mean())})", "flag; recortar km/dia a p99 al construir features de uso"],
    ["agenda", "ServicePriceDiscount: no es un descuento", f"no nulo en {int(spd.notna().sum()):,} items ({pct(spd.notna().mean())}); = 0 en {int((spd == 0).sum()):,} ({int(agenda.ServiceType[spd == 0].fillna('').str.lower().eq('campañas de servicio').sum()):,} campanias; el 100% de los items con ServiceFordFixedPriceFlag=Y y precio no nulo vale 0); mediana {spd.median():,.0f}; mediana 1° service 2025Q1 {mm[(mm.ServiceMaintenance == 1) & (mm.ScheduleDate.dt.to_period('Q') == '2025Q1')].ServicePriceDiscount.median():,.0f} -> 2026Q3 {mm[(mm.ServiceMaintenance == 1) & (mm.ScheduleDate.dt.to_period('Q') == '2026Q3')].ServicePriceDiscount.median():,.0f}", "dejar solo como flag 'precio informado'; preguntar al mentor (parece precio de lista x100; informado en 44-52% de los items de mantenimiento desde 2024Q1, para el 1° service recien desde 2025Q1; 0 = item de precio fijo Ford / campania, no 'sin dato')"],
    ["agenda", "ServiceLaborCost casi vacio", f"{int(agenda.ServiceLaborCost.notna().sum()):,} items ({pct(agenda.ServiceLaborCost.notna().mean())}), todos Mantenimiento y anio 2026", "excluir columna"],
    ["sales/agenda", "WarrantyStartDate distinto entre sales y agenda (mismo vehiculo)", f"{int((dwsd.notna() & (dwsd != 0)).sum())} de {int(dwsd.notna().sum()):,} vehiculos con WSD en ambas ({pct((dwsd.notna() & (dwsd != 0)).sum() / dwsd.notna().sum())}); |dif| > 30 d: {int((dwsd.abs() > 30).sum())}; > 365 d: {int((dwsd.abs() > 365).sum())}; mediana de las diferencias {dwsd[dwsd != 0].median():.0f} d; ademas {int(dwsd.isna().sum())} con WSD nula en sales", f"dejar: usar WSD de sales cuando existe (la WSD de la agenda = DeliveryDate de sales en {pct((m.WSD_ag == m.DeliveryDate).mean())} de los casos)"],
    ["agenda", "WarrantyStartDate posterior al primer turno concluido", f"{int((x_wsd > 0).sum()):,} vehiculos; > 30 d: {int((x_wsd > 30).sum())}; > 365 d: {int((x_wsd > 365).sum())}", "dejar: edad negativa en el primer turno se recorta a 0 (PDI / entrega)"],
    ["sales", "DeliveryDate < 2020 (2013, 2015)", f"{int((sales.DeliveryDate < '2020-01-01').sum())} filas", "excluir de la poblacion 'vendidos 2024-2026' (reventa/usado)"],
    ["sales", "SalesDate > DeliveryDate", f"{int((sales.SalesDate > sales.DeliveryDate).sum())} filas (las mismas 3)", "excluir"],
    ["sales", "SalesDate > RegistrationDate", f"{int((sales.SalesDate > sales.RegistrationDate).sum()):,} filas ({pct((sales.SalesDate > sales.RegistrationDate).mean())})", "dejar: RegistrationDate no se usa; preguntar semantica"],
    ["sales", "WarrantyStartDate < DeliveryDate", f"{int((sales.WarrantyStartDate < sales.DeliveryDate).sum()):,} filas", "dejar: usar min(WSD, DeliveryDate) como inicio de vida util"],
    ["sales", "PersonType raro (25 / 29 / 30) o nulo", f"25: {int((sales.PersonType == '25').sum())}, 29: {int((sales.PersonType == '29').sum())}, 30: {int((sales.PersonType == '30').sum())}, nulo: {int(sales.PersonType.isna().sum())} (25 es 80% canal HR)", "dejar: categoria 'otro' con flag"],
    ["sales", "Status 1 / 2 / 3 (no ACCEPTED)", f"{int((sales.Status != 'ACCEPTED').sum())} filas; {int(sales[sales.Status != 'ACCEPTED'].DeliveryDate.isna().sum())} sin DeliveryDate; presencia en agenda {pct(sales[sales.Status != 'ACCEPTED'].vehicle_id.isin(agenda.vehicle_id).mean())} vs {pct(sales[sales.Status == 'ACCEPTED'].vehicle_id.isin(agenda.vehicle_id).mean())}", "excluir de la poblacion hasta que tengan DeliveryDate (venta no concretada)"],
    ["sales", "ModelShortName GLOBAL RANGER - FSAO", "1 fila (ModelYear 2013, canal UNKNOWN, sin ModelCode ni WSD)", "excluir"],
    ["sales", "dealer_id nulo / WarrantyStartDate nulo / DeliveryDate nulo", f"{int(sales.dealer_id.isna().sum())} / {int(sales.WarrantyStartDate.isna().sum())} / {int(sales.DeliveryDate.isna().sum())} filas", "dejar; WSD nulo se imputa con DeliveryDate"],
], columns=["tabla", "problema", "magnitud", "decision recomendada"]).set_index("tabla")
emit("### E1. Tabla de problemas", "")
table(E1)
E2 = pd.DataFrame({"turnos": dd.value_counts().sort_index()})
E2.index.name = "WarrantyStartDate.year - ModelYear"
emit("### E2. Coherencia WarrantyStartDate vs ModelYear (turnos)", "")
table(E2, floatfmt=",.0f")
E3 = pd.DataFrame({"turnos": gap_ci.value_counts().sort_index().reindex(range(-7, 15), fill_value=0)})
E3.index.name = "EffectiveCheckinDate - ScheduleDate (dias)"
emit("### E3. Gap check-in vs fecha del turno", "")
emit(f"Turnos con check-in: {int(gap_ci.notna().sum()):,}. Mismo dia: {pct((gap_ci == 0).sum() / gap_ci.notna().sum())}; "
     f"|gap| <= 1 dia: {pct((gap_ci.abs() <= 1).sum() / gap_ci.notna().sum())}; gap < 0: {pct((gap_ci < 0).sum() / gap_ci.notna().sum())}; "
     f"gap > 10 d: {int((gap_ci > 10).sum()):,}; gap < -10 d: {int((gap_ci < -10).sum()):,}.", "")
emit("Check-in no nulo por StatusARG: " + ", ".join(f"{k}: {pct(v)}" for k, v in ap.groupby("StatusARG").EffectiveCheckinDate.apply(lambda x: x.notna().mean()).items()) + ".", "")
table(E3, floatfmt=",.0f")
E4 = pd.DataFrame({
    "pares de visitas concluidas consecutivas (VehicleCurrentKM > 0)": [len(pair)],
    "km decrece": [int((dk < 0).sum())], "km decrece > 1.000": [int((dk < -1000).sum())], "km decrece > 10.000": [int((dk < -10000).sum())],
    "km igual": [int((dk == 0).sum())], "km/dia mediana": [kmd.median()], "km/dia p95": [kmd.quantile(0.95)], "km/dia p99": [kmd.quantile(0.99)],
    "pares > 300 km/dia (excl. mismo dia)": [int(((kmd > 300) & (days > 1)).sum())],
}).T.rename(columns={0: "valor"})
emit("### E4. Odometro (VehicleCurrentKM) entre visitas concluidas consecutivas", "")
table(E4, int_rows=["pares de visitas concluidas consecutivas (VehicleCurrentKM > 0)", "km decrece", "km decrece > 1.000", "km decrece > 10.000", "km igual", "pares > 300 km/dia (excl. mismo dia)"])
# E4b: lo mismo con placeholders (< 100) y > 1M excluidos, que es como se van a usar las lecturas
ccl = c.dropna(subset=["vehicle_id", "VehicleCurrentKM"])
ccl = ccl[ccl.VehicleCurrentKM.between(100, 1e6)].sort_values(["vehicle_id", "event_date"])
ccl["prev"] = ccl.groupby("vehicle_id").VehicleCurrentKM.shift(); ccl["prev_dt"] = ccl.groupby("vehicle_id").event_date.shift()
pl = ccl.dropna(subset=["prev"]); dkl = pl.VehicleCurrentKM - pl.prev; dl = (pl.event_date - pl.prev_dt).dt.days.clip(lower=1); kml = dkl / dl
emit(f"E4b. Lo mismo excluyendo placeholders (VehicleCurrentKM en [100, 1.000.000]): {len(pl):,} pares; retrocede > 1.000 km en {int((dkl < -1000).sum()):,} "
     f"({pct((dkl < -1000).mean())}) de {pl.loc[dkl < -1000, 'vehicle_id'].nunique():,} vehiculos; > 300 km/dia (excl. mismo dia): "
     f"{int(((kml > 300) & (dl > 1)).sum()):,} ({pct(((kml > 300) & (dl > 1)).mean())}); km/dia mediana {kml.median():.1f}, p99 {kml.quantile(.99):,.0f}.", "")
qq = mm.ScheduleDate.dt.to_period("Q")
E5 = mm.groupby(qq).ServicePriceDiscount.agg(["size", "count", lambda x: x.notna().mean() * 100, lambda x: (x == 0).sum() / max(x.notna().sum(), 1) * 100, "median"])
E5.columns = ["items de mantenimiento", "items con precio no nulo", "% no nulo", "% igual a 0 (sobre no nulos)", "mediana"]
m1 = mm[mm.ServiceMaintenance == 1]
E5["1° service: no nulos"] = m1.groupby(m1.ScheduleDate.dt.to_period("Q")).ServicePriceDiscount.count()
E5["1° service: mediana"] = m1.groupby(m1.ScheduleDate.dt.to_period("Q")).ServicePriceDiscount.median()
E5 = E5[E5["items con precio no nulo"] > 0]
E5.index = E5.index.astype(str); E5.index.name = "trimestre"
emit("### E5. ServicePriceDiscount en items de mantenimiento, por trimestre", "")
table(E5, floatfmt=",.0f")

fig, axes = plt.subplots(1, 2, figsize=(11, 4))
ax = axes[0]
vc = gap_ci[gap_ci.between(-10, 30)].value_counts().sort_index()
ax.bar(vc.index, vc.values, color=C[0], width=0.8)
ax.set_yscale("log")
ax.set_xlabel("EffectiveCheckinDate - ScheduleDate (dias, solo el rango [-10, 30])"); ax.set_ylabel("Turnos (escala log)")
ax.set_title(f"El check-in cae el mismo dia del turno\nen el {100 * (gap_ci == 0).sum() / gap_ci.notna().sum():.1f}% de los casos")
ax = axes[1]
kmd_plot = kmd[(days > 1) & kmd.between(-50, 400)]
ax.hist(kmd_plot, bins=np.linspace(-50, 400, 91), color=C[1])
ax.axvline(300, color=INK2, lw=1); ax.text(305, ax.get_ylim()[1] * 0.9, "> 300 km/dia", fontsize=8, color=INK2)
ax.set_xlabel("km/dia entre visitas concluidas consecutivas (VehicleCurrentKM, solo el rango [-50, 400])"); ax.set_ylabel("Pares de visitas")
ax.set_title(f"Ritmo de uso: mediana {kmd.median():.0f} km/dia;\ncola implausible y retrocesos (odometro mal cargado)")
emit(f"Fuera de rango en la figura (excluye mismo dia): km/dia < -50: {int(((days > 1) & (kmd < -50)).sum()):,}; km/dia > 400: {int(((days > 1) & (kmd > 400)).sum()):,}; "
     f"pares del mismo dia (no graficados): {int((days <= 1).sum()):,}. Gap check-in fuera de [-10, 30]: {int((~gap_ci.between(-10, 30) & gap_ci.notna()).sum()):,}.", "")
savefig(fig, "checkin_y_odometro")

# =====================================================================================
# F. TURNOS SIN vehicle_id / customer_id
# =====================================================================================
emit("## F. Turnos sin vehicle_id o sin customer_id", "")
nv, nc = ap[ap.vehicle_id.isna()], ap[ap.customer_id.isna()]
veh_nc = nc.vehicle_id.dropna().drop_duplicates()
F1 = pd.DataFrame({
    "sin vehicle_id": [len(nv), 100 * len(nv) / len(ap), int(nv.completed.sum()), int(nv.is_completed_maintenance.sum()), int(nv.customer_id.isna().sum()),
                       100 * nv.ModelYear.isna().mean(), 100 * nv.WarrantyStartDate.isna().mean(), 100 * nv.KM.isna().mean(), int((nv.ScheduleSource == "Dealer").sum())],
    "sin customer_id": [len(nc), 100 * len(nc) / len(ap), int(nc.completed.sum()), int(nc.is_completed_maintenance.sum()), int(nc.vehicle_id.isna().sum()),
                        100 * nc.ModelYear.isna().mean(), 100 * nc.WarrantyStartDate.isna().mean(), 100 * nc.KM.isna().mean(), int((nc.ScheduleSource == "Dealer").sum())],
}, index=["turnos", "% de turnos", "(60) Concluido", "mantenimientos concluidos", "sin el otro id tampoco", "% ModelYear nulo", "% WarrantyStartDate nulo", "% KM nulo", "origen Dealer"])
emit("### F1. Magnitud y perfil", "")
table(F1, int_rows=["turnos", "(60) Concluido", "mantenimientos concluidos", "sin el otro id tampoco", "origen Dealer"])
emit(f"Vehiculos con algun turno sin customer_id: {len(veh_nc):,}; de ellos {int(veh_nc.isin(ap[ap.customer_id.notna()].vehicle_id).sum()):,} tienen otro turno con customer_id (se puede imputar el cliente del vehiculo).", "")
emit("StatusARG de los turnos sin vehicle_id: " + ", ".join(f"{k}: {v:,}" for k, v in nv.StatusARG.value_counts().items()) + ".", "")

# =====================================================================================
# G. DUPLICADOS LOGICOS
# =====================================================================================
emit("## G. Duplicados logicos", "")
dupmask = agenda.duplicated()
emit(f"Filas identicas en la agenda cruda: {int(dupmask.sum()):,} ({pct(dupmask.mean())}), en {agenda[dupmask].schedule_id.nunique():,} schedule_id; "
     f"por StatusARG: " + ", ".join(f"{k}: {v:,}" for k, v in agenda[dupmask].StatusARG.value_counts().items()) + ". Se eliminan en `appointments()`.", "")
gsid = agenda.groupby("schedule_id")[["StatusARG", "ScheduleDate", "EffectiveCheckinDate", "KM", "vehicle_id", "customer_id", "dealer_id"]].nunique()
emit("schedule_id con >1 valor de: " + ", ".join(f"{k}: {int((v > 1).sum())}" for k, v in gsid.items()) + " (las columnas de nivel turno son consistentes).", "")
gdup = apv.groupby(["vehicle_id", "ScheduleDate"]).agg(n=("schedule_id", "nunique"), statuses=("StatusARG", lambda x: " | ".join(sorted(x))))
dup = gdup[gdup.n > 1]
G1 = dup.statuses.value_counts().head(10).rename("pares (vehiculo, fecha)").to_frame()
G1["% de los pares"] = 100 * G1["pares (vehiculo, fecha)"] / len(dup)
G1.index.name = "combinacion de StatusARG"
emit(f"### G1. Mismo vehiculo, misma ScheduleDate, distinto schedule_id: {len(dup):,} pares (vehiculo, fecha), {int(dup.n.sum()):,} turnos, "
     f"{dup.reset_index().vehicle_id.nunique():,} vehiculos", "")
table(G1, int_cols=["pares (vehiculo, fecha)"])
gc = apv[apv.completed].groupby(["vehicle_id", "event_date"]).schedule_id.nunique()
gcm = apv[apv.is_completed_maintenance].groupby(["vehicle_id", "event_date"]).schedule_id.nunique()
cm_s2 = apv[apv.is_completed_maintenance].sort_values(["vehicle_id", "event_date"])
gap_m = (cm_s2.event_date - cm_s2.groupby("vehicle_id").event_date.shift()).dt.days
same_mn = cm_s2.maint_number.eq(cm_s2.groupby("vehicle_id").maint_number.shift())
emit(f"(vehiculo, event_date) con >1 turno (60) Concluido: {int((gc > 1).sum()):,} ({int(gc[gc > 1].sum()):,} turnos); "
     f"con >1 mantenimiento concluido el mismo dia: {int((gcm > 1).sum()):,} ({int(gcm[gcm > 1].sum()):,} turnos).", "")
emit(f"Mantenimientos concluidos a <= 7 dias de otro mantenimiento concluido del mismo vehiculo: {int((gap_m <= 7).sum()):,} "
     f"(mismo maint_number: {int((same_mn & (gap_m <= 7)).sum()):,}); a <= 30 dias: {int((gap_m <= 30).sum()):,} (mismo maint_number: {int((same_mn & (gap_m <= 30)).sum()):,}); "
     f"sobre {int(gap_m.notna().sum()):,} pares consecutivos.", "")
# cancelaciones administrativas
cs = apv[apv.completed][["vehicle_id", "event_date"]].sort_values("event_date").rename(columns={"event_date": "compl_date"})
cx = apv[apv.cancelled][["schedule_id", "vehicle_id", "ScheduleDate"]].sort_values("ScheduleDate")
near = pd.merge_asof(cx, cs, left_on="ScheduleDate", right_on="compl_date", by="vehicle_id", direction="nearest")
dnear = (near.compl_date - near.ScheduleDate).dt.days
fwd = pd.merge_asof(cx, cs, left_on="ScheduleDate", right_on="compl_date", by="vehicle_id", direction="forward", tolerance=pd.Timedelta(days=30))
ns = apv[apv.no_show][["schedule_id", "vehicle_id", "ScheduleDate"]].sort_values("ScheduleDate")
nfwd = pd.merge_asof(ns, cs, left_on="ScheduleDate", right_on="compl_date", by="vehicle_id", direction="forward", tolerance=pd.Timedelta(days=30))
G2 = pd.DataFrame({
    "turnos": [len(cx), int((dnear == 0).sum()), int((dnear.abs() <= 7).sum()), int(fwd.compl_date.notna().sum()), len(ns), int(nfwd.compl_date.notna().sum())],
    "%": [100.0, 100 * (dnear == 0).mean(), 100 * (dnear.abs() <= 7).mean(), 100 * fwd.compl_date.notna().mean(), 100.0, 100 * nfwd.compl_date.notna().mean()],
}, index=["(70) Cancelado con vehicle_id", "  con un (60) Concluido del mismo vehiculo el MISMO dia", "  con un (60) Concluido a <= 7 dias (antes o despues)",
          "  seguido de un (60) Concluido dentro de 30 dias", "(80) No asistio con vehicle_id", "  seguido de un (60) Concluido dentro de 30 dias"])
emit("### G2. Cancelaciones y no-show 'administrativos' (re-agendamiento) vs. abandono", "")
table(G2, int_cols=["turnos"])

fig, axes = plt.subplots(1, 2, figsize=(11, 4))
ax = axes[0]
top = G1.iloc[::-1]
ax.barh(top.index, top["pares (vehiculo, fecha)"].values, color=C[0])
ax.set_xlabel("Pares (vehiculo, ScheduleDate) con >1 schedule_id"); ax.set_title("Mismo vehiculo y misma fecha:\ncasi siempre un cancelado + un concluido")
ax.tick_params(axis="y", labelsize=7)
ax = axes[1]
ax.hist(dnear[dnear.between(-45, 45)], bins=np.arange(-45, 47) - 0.5, color=C[1])
ax.set_xlabel("Dias entre la cancelacion y el (60) Concluido mas cercano\ndel mismo vehiculo (solo el rango [-45, 45])"); ax.set_ylabel("Turnos cancelados")
ax.set_title(f"El {100 * (dnear.abs() <= 7).mean():.0f}% de las cancelaciones tiene un turno\nconcluido del mismo vehiculo a <= 7 dias")
emit(f"Cancelaciones fuera del rango [-45, 45] o sin turno concluido del vehiculo (no graficadas): {int((~dnear.between(-45, 45)).sum()):,} de {len(dnear):,}.", "")
savefig(fig, "duplicados_cancelaciones")

# =====================================================================================
# H. COBERTURA SALES vs AGENDA
# =====================================================================================
emit("## H. Cobertura sales vs agenda", "")
in_ag = sales.vehicle_id.isin(apv.vehicle_id.unique())
age_s = (CUTOFF - sales.SalesDate).dt.days
in_cm = sales.vehicle_id.isin(cm.vehicle_id.unique())
H1 = pd.DataFrame({
    "ventas": [len(sales)] + [int((age_s > k).sum()) for k in (180, 365, 548, 730)],
    "% con >=1 turno en agenda": [100 * in_ag.mean()] + [100 * in_ag[age_s > k].mean() for k in (180, 365, 548, 730)],
    "% con >=1 mantenimiento concluido": [100 * in_cm.mean()] + [100 * in_cm[age_s > k].mean() for k in (180, 365, 548, 730)],
}, index=["todas", "> 180 dias antes del CUTOFF", "> 365 dias", "> 548 dias", "> 730 dias"])
emit("### H1. Vehiculos vendidos (sales) que aparecen en la agenda", "")
table(H1, int_cols=["ventas"])
# H1c: cobertura a exposicion fija (365 d desde la venta) por cohorte trimestral de venta
fe = apv.groupby("vehicle_id").event_date.min()
sc = sales[age_s > 365].copy(); sc["first_ev"] = sc.vehicle_id.map(fe)
sc["in365"] = ((sc.first_ev - sc.SalesDate).dt.days <= 365).fillna(False)
H1c = sc.groupby(sc.SalesDate.dt.to_period("Q")).agg(ventas=("vehicle_id", "size"), pct=("in365", "mean"))
H1c["pct"] *= 100; H1c.index = H1c.index.astype(str); H1c.index.name = "trimestre de venta"
H1c.columns = ["ventas (con >=365 d de exposicion)", "% con >=1 turno dentro de los 365 d de la venta"]
emit("### H1c. Cobertura a exposicion fija (365 dias desde la venta) por cohorte de venta: si es estable, la caida en cohortes recientes es solo falta de tiempo", "")
table(H1c, int_cols=["ventas (con >=365 d de exposicion)"])
H1b = pd.concat([
    sales[age_s > 365].groupby("BusinessUnit").vehicle_id.apply(lambda x: 100 * x.isin(apv.vehicle_id).mean()).rename("% en agenda (ventas > 365 d)"),
    sales[age_s > 365].groupby("SalesChannel").vehicle_id.apply(lambda x: 100 * x.isin(apv.vehicle_id).mean()).rename("% en agenda (ventas > 365 d)"),
    sales[age_s > 365].groupby("PersonType").vehicle_id.apply(lambda x: 100 * x.isin(apv.vehicle_id).mean()).rename("% en agenda (ventas > 365 d)"),
])
H1b = H1b.to_frame(); H1b.index.name = "segmento"
emit("### H1b. Presencia en agenda de ventas con mas de 365 dias, por segmento", "")
table(H1b)
av = veh.copy(); av["in_sales"] = av.index.isin(sales.vehicle_id)
av["TMA"] = apv.groupby("vehicle_id").TMA.first()
H2 = pd.crosstab(av.ModelYear.where(av.ModelYear >= 2022, other=-1).fillna(-2), av.in_sales)
H2.columns = ["NO en sales", "en sales"]; H2.index = [("<2022" if i == -1 else ("MY nulo" if i == -2 else str(int(i)))) for i in H2.index]
H2.index.name = "ModelYear (agenda)"
emit("### H2. Vehiculos de la agenda por ModelYear y presencia en sales", "")
table(H2, floatfmt=",.0f")
new = av[(av.ModelYear >= 2024) & ~av.in_sales]
emit(f"ModelYear >= 2024 y NO en sales: {len(new):,}; de ellos con WSD en 2023: {int((new.WSD.dt.year == 2023).sum()):,} (vendidos antes del extracto), "
     f"con WSD >= 2024-01-01: {int((new.WSD >= AG_START).sum()):,}.", "")
w = av.WSD >= AG_START
w24 = av[w & ~av.in_sales]
emit(f"Vehiculos de la agenda con WSD >= 2024-01-01: {int(w.sum()):,}; en sales {int(av[w].in_sales.sum()):,} ({pct(av[w].in_sales.mean())}); "
     f"NO en sales {len(w24):,} ({pct(1 - av[w].in_sales.mean())}), TMA: " + ", ".join(f"{k}: {v}" for k, v in w24.TMA.value_counts().head(5).items())
     + f"; WSD por anio: " + ", ".join(f"{int(k)}: {v}" for k, v in w24.WSD.dt.year.value_counts().sort_index().items()) + ".", "")
mb = sales.set_index("vehicle_id")[["SalesDate", "DeliveryDate", "WarrantyStartDate"]].join(av[["first_ev"]], how="inner")
emit(f"Vehiculos en ambas tablas: {len(mb):,}. Primer turno anterior a DeliveryDate: {int((mb.first_ev < mb.DeliveryDate).sum()):,} "
     f"({pct((mb.first_ev < mb.DeliveryDate).mean())}); mas de 30 dias antes: {int(((mb.DeliveryDate - mb.first_ev).dt.days > 30).sum())}. "
     f"Meses entre DeliveryDate y primer turno: mediana {((mb.first_ev - mb.DeliveryDate).dt.days / 30.44).median():.1f}, p90 {((mb.first_ev - mb.DeliveryDate).dt.days / 30.44).quantile(.9):.1f}.", "")
sc_map = sales.set_index("vehicle_id").customer_id
eq = apv.assign(sc=apv.vehicle_id.map(sc_map)).dropna(subset=["sc"]).assign(eq=lambda d_: d_.customer_id == d_.sc).groupby("vehicle_id").eq.any()
emit(f"Vehiculos en ambas tablas cuyo customer_id de sales aparece en al menos un turno: {pct(eq.mean())} ({int(eq.sum()):,} de {len(eq):,}).", "")

fig, axes = plt.subplots(1, 2, figsize=(11, 4))
ax = axes[0]
bym = sales.groupby(sales.SalesDate.dt.to_period("M")).vehicle_id.apply(lambda x: 100 * x.isin(apv.vehicle_id).mean())
ax.plot(bym.index.astype(str), bym.values, color=C[0], lw=2)
ax.set_ylabel("% de vendidos con >=1 turno en agenda"); ax.set_xlabel("Mes de venta")
ax.set_title("Cobertura de la agenda por cohorte de venta\n(cae en cohortes recientes: falta de tiempo)")
ax.set_xticks(range(0, len(bym), 3)); ax.set_xticklabels(bym.index.astype(str)[::3], rotation=45)
ax = axes[1]
wm = av[av.WSD >= "2023-07-01"].groupby([av.WSD.dt.to_period("Q"), "in_sales"]).size().unstack(fill_value=0)
xl = wm.index.astype(str)
ax.bar(xl, wm[True].values, color=C[0], label="en sales", width=0.8, edgecolor=SURFACE, linewidth=1.5)
ax.bar(xl, wm[False].values, bottom=wm[True].values, color=C[1], label="NO en sales", width=0.8, edgecolor=SURFACE, linewidth=1.5)
ax.set_ylabel("Vehiculos en agenda"); ax.set_xlabel("Trimestre de WarrantyStartDate")
ax.set_title("Vehiculos de la agenda por trimestre de entrega:\ndesde 2024 casi todos estan en sales")
ax.tick_params(axis="x", rotation=45); ax.legend(fontsize=8)
savefig(fig, "cobertura")

# =====================================================================================
# I. SINTESIS
# =====================================================================================
emit("## I. Sintesis: columnas con riesgo de leakage y exclusiones", "")
I1 = pd.DataFrame([
    ["KM", "snapshot del odometro a la extraccion (constante por vehiculo; = lectura del ultimo turno concluido en el 91,7%)", "NO usar como feature. Usar VehicleCurrentKM de turnos con event_date < t (running max)."],
    ["ConnectedStatusARG", "snapshot a la extraccion (constante en 99,9% de los vehiculos; 'Sin informacion' crece con la fecha de entrega)", "NO usar en backtest. En scoring actual, solo con advertencia. Alternativa segura: 'generacion con conectividad' derivada de TMA/WSD."],
    ["IsReschedule (en turnos (70) Cancelado)", "Y indica que el turno fue re-agendado: describe un evento POSTERIOR a la cancelacion", "Usar solo para cancelaciones cuyo re-agendamiento tambien es anterior a t; regla simple: ignorar el flag de cancelaciones ocurridas en los 30 dias previos a t."],
    ["IsReschedule (en turnos (60) Concluido)", "Y indica que este turno es re-agendamiento de uno anterior (pasado)", "Usable si event_date < t."],
    ["ScheduleReturn", "Y = visita de retorno a <= 30 dias de otra visita (97% tiene turno previo a <= 30 d); 85% sin item de mantenimiento", "Usable como feature si event_date < t. Para el target: no contar un retorno como 'mantenimiento programado' (pregunta al mentor)."],
    ["SurveyResponseDate / SurveyStarRating", "se responde ANTES del turno (mediana 8 dias antes de ScheduleDate; nunca despues del checkout); solo canales digitales; rating ~4,75 en todos los status", "Usable solo si SurveyResponseDate < t. Semantica: calificacion de la reserva en la app, no del servicio. Sirve como proxy de fecha de reserva (7,5% de los turnos)."],
    ["Turnos con ScheduleDate >= t (cualquier status)", "no hay fecha de creacion: no se sabe si el turno existia en t", "Excluir por completo de las features en backtest. 'Tiene turno agendado' solo en el scoring actual, como regla operativa post-modelo."],
    ["StatusARG (30)/(40) de turnos con ScheduleDate < t", "estado abierto a la extraccion; stale si ScheduleDate <= CUTOFF-30 d", "En backtest con t <= CUTOFF-30 d tratar (30)/(40) atrasados como 'no concluido' con flag; en el target, no cuentan como mantenimiento concluido."],
    ["EffectiveCheckoutDate, DaysInDealer, WorkDaysInDealer, EffectiveTerm", "resultado de la visita (posterior al check-in)", "Usables solo de turnos con EffectiveCheckoutDate < t."],
    ["customer_id de la agenda", "cambia en el 20,8% de los vehiculos (27,6% de los que tienen >=2 turnos con cliente)", "Usar el customer_id del ultimo turno con event_date < t; no usar 'alguna vez tuvo otro cliente'."],
    ["WarrantyStartDate, ModelYear, TMA, ShortVehicleModelGroupTreated", "atributos fijos del vehiculo (0-1 vehiculos con variacion)", "Usables sin restriccion (edad, generacion)."],
    ["Region, DealerStateOrZone, dealer_id", "atributos del dealer del turno; varian solo si el vehiculo cambia de dealer", "Usables como atributos del ultimo turno < t."],
    ["ServicePriceDiscount", "precio (no descuento) en escala x100; informado en ~50% de los items de mantenimiento desde 2024Q1 (1° service recien desde 2025Q1); 0 = item de precio fijo Ford / campania", "Solo como flag 'precio informado' o precio deflactado; confirmar unidad con el mentor."],
    ["ServiceLaborCost", "0,7% no nulo, solo 2026", "Excluir."],
    ["maint_number (ServiceMaintenance)", "numero de service declarado; +1 entre services consecutivos en 77,5%", "Usable como proxy de historia previa (correlacion 0,76 con la edad); tomar el maximo observado hasta t."],
], columns=["columna", "por que hay riesgo", "regla de uso"]).set_index("columna")
emit("### I1. Columnas con riesgo de leakage y regla de uso", "")
table(I1)
stale = ap.pending & (ap.ScheduleDate <= CUTOFF - pd.Timedelta(days=30))
I2 = pd.DataFrame([
    ["agenda", "filas identicas", f"{int(dupmask.sum()):,} filas-item", "excluir (ya lo hace appointments())"],
    ["agenda", "turnos sin vehicle_id", f"{len(nv):,} turnos ({int(nv.is_completed_maintenance.sum()):,} mantenimientos concluidos)", "excluir: no se pueden asignar a una unidad usuario-vehiculo"],
    ["agenda", "turnos sin customer_id pero con vehicle_id", f"{len(nc) - int(nc.vehicle_id.isna().sum()):,} turnos", "dejar: imputar customer_id del vehiculo (posible en {0:,} vehiculos)".format(int(veh_nc.isin(ap[ap.customer_id.notna()].vehicle_id).sum()))],
    ["agenda", "vehiculos con ModelYear 0/<2005 y sin WSD", f"{int(((veh.ModelYear == 0) | (veh.ModelYear < 2005)).sum())} vehiculos ({int((((veh.ModelYear == 0) | (veh.ModelYear < 2005)) & veh.WSD.isna()).sum())} sin WSD)", "excluir los sin WSD; el resto usa edad por WSD"],
    ["agenda", "vehiculos sin WSD ni ModelYear (edad desconocida)", f"{int((veh.WSD.isna() & veh.ModelYear.isna()).sum()):,} vehiculos ({int(veh.WSD.isna().sum()):,} sin WSD)", "flag edad desconocida; imputar por TMA si se quiere retener"],
    ["agenda", "check-in con fecha imposible (< 2024-01-01)", f"{int((ap.EffectiveCheckinDate < AG_START).sum())} turnos", "corregir event_date = ScheduleDate"],
    ["agenda", "VehicleCurrentKM < 100 o > 1.000.000 (concluidos)", f"{int(((c.VehicleCurrentKM < 100) | (c.VehicleCurrentKM > 1e6)).sum()):,} turnos", "corregir a nulo"],
    ["agenda", "pendientes stale ((30)/(40) con ScheduleDate <= CUTOFF-30 d)", f"{int(stale.sum()):,} turnos", "tratar como no concluidos, con flag"],
    ["agenda", "mantenimientos concluidos a <= 7 dias de otro del mismo vehiculo", f"{int((gap_m <= 7).sum()):,} turnos", "colapsar en un solo evento (queda el primero)"],
    ["agenda", "turnos con ScheduleDate > CUTOFF", f"{len(fut):,} turnos", "excluir del backtest; usar solo en la regla operativa del scoring actual"],
    ["sales", "GLOBAL RANGER / DeliveryDate < 2020 / Status != ACCEPTED", f"{int(((sales.ModelShortName != 'RANGER') | (sales.DeliveryDate < '2020-01-01') | (sales.Status != 'ACCEPTED')).sum())} filas", "excluir de la poblacion de vendidos"],
], columns=["tabla", "exclusion / correccion", "filas o vehiculos afectados", "tratamiento"]).set_index("tabla")
emit("### I2. Exclusiones y correcciones recomendadas, con conteos", "")
table(I2)

OUT_MD.write_text("\n".join(OUT), encoding="utf-8")
print(f"\nSalida escrita en {OUT_MD}")
