"""Verificación independiente (escéptica) del EDA 02 — cadencia de mantenimiento y parámetros de la ventana.

Recalcula desde cero, con código propio, las afirmaciones clave de ``reports/eda/02_cadencia_ventana.md`` y busca
los errores típicos: censura por la derecha en intervalos, selección por seguimiento, comparaciones diluidas
(tasa reciente vs acumulada), índice estacional contaminado por tendencia, joins que duplican, etc.

Genera: reports/eda/02_cadencia_ventana_verificacion_tablas.md (todas las tablas V*, citadas en el informe de
verificación) y reports/figures/eda/02_cadencia_ventana_verif_*.png.

Uso (desde la carpeta del proyecto):
    PYTHONIOENCODING=utf8 PYTHONPATH=src .venv/Scripts/python.exe scripts/eda/02_cadencia_ventana_verificacion.py
"""
from __future__ import annotations

import time

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from repurchase import config  # noqa: E402
from repurchase.eventos import CUTOFF, appointments  # noqa: E402
from repurchase.io import load_agenda, load_sales  # noqa: E402

T0 = time.time()
PREFIX = "02_cadencia_ventana_verif"
FIG_DIR = config.FIGURES_DIR / "eda"
OUT_MD = config.REPORTS_DIR / "eda" / "02_cadencia_ventana_verificacion_tablas.md"
START = pd.Timestamp("2024-01-01")
D18 = 548
MESES = 30.4375
Q = [0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95]
QN = ["p5", "p10", "p25", "p50", "p75", "p90", "p95"]
_parts: list[str] = []


def log(m):
    print(f"[{time.time() - T0:5.0f}s] {m}", flush=True)


def fmt(v, dec=0):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return ""
    if dec == 0:
        return f"{int(round(float(v))):,}".replace(",", ".")
    return f"{float(v):,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def md(df: pd.DataFrame, dec=0, index=True) -> str:
    d = df.reset_index() if index else df.copy()
    cols = list(d.columns)
    out = ["| " + " | ".join(map(str, cols)) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, r in d.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            if isinstance(v, (float, int, np.integer, np.floating)) and not isinstance(v, bool):
                cells.append(fmt(v, dec.get(c, 0) if isinstance(dec, dict) else dec))
            else:
                cells.append(str(v))
        out.append("| " + " | ".join(cells) + " |")
    return "\n".join(out)


def table(title, df, dec=0, index=True, note=""):
    s = f"### {title}\n\n{md(df, dec, index)}\n" + (f"\n{note}\n" if note else "")
    _parts.append(s)
    print("\n" + s)


def kv(title, items: dict, note=""):
    rows = [{"métrica": k, "valor": fmt(*(v if isinstance(v, tuple) else (v, 0)))} for k, v in items.items()]
    table(title, pd.DataFrame(rows), index=False, note=note)


def pct(groups: dict, dec=0):
    rows = {}
    for k, s in groups.items():
        s = pd.Series(s).dropna()
        if len(s):
            rows[k] = dict(n=len(s), **dict(zip(QN, s.quantile(Q).values)), media=s.mean())
    return pd.DataFrame(rows).T


def gen_of(s):
    g = pd.Series("Otro", index=s.index, dtype="str")
    g[s.str.contains("P703", na=False)] = "P703"
    g[s.str.contains("P375", na=False)] = "P375"
    return g


# ==================================================================================================
# V0. Carga y sanidad de joins
# ==================================================================================================
log("carga")
ap = appointments()
sales = load_sales()
kv("V0. Sanidad: unicidad de claves usadas en joins", {
    "sales: filas": len(sales), "sales: vehicle_id únicos": sales.vehicle_id.nunique(),
    "appointments: filas": len(ap), "appointments: schedule_id únicos": ap.schedule_id.nunique(),
})
assert sales.vehicle_id.is_unique, "vehicle_id no es único en sales: los joins duplicarían filas"
ap["gen"] = gen_of(ap["ShortVehicleModelGroupTreated"])

# Base M propia: mantenimiento completado, 1 fila por vehículo-día
mc = ap[ap.is_completed_maintenance & ap.event_date.between(START, CUTOFF)]
M = (mc.sort_values(["vehicle_id", "event_date", "maint_number", "schedule_id"])
       .drop_duplicates(["vehicle_id", "event_date"]).copy())
sidx = sales.set_index("vehicle_id")
M["WSD"] = M.WarrantyStartDate.fillna(M.vehicle_id.map(sidx.WarrantyStartDate))
M["BU"] = M.vehicle_id.map(sidx.BusinessUnit)
M["PT"] = M.vehicle_id.map(sidx.PersonType)
M["km"] = M.VehicleCurrentKM.where(M.VehicleCurrentKM.between(100, 1_000_000))
M["edad_a"] = (M.event_date - M.WSD).dt.days / 365.25
g = M.groupby("vehicle_id")
M["prev_date"], M["prev_km"], M["prev_n"] = g.event_date.shift(1), g.km.shift(1), g.maint_number.shift(1)
M["next_date"] = g.event_date.shift(-1)
M["d_dias"] = (M.event_date - M.prev_date).dt.days
M["d_km"] = M.km - M.prev_km
M["dias_next"] = (M.next_date - M.event_date).dt.days
M["fu"] = (CUTOFF - M.event_date).dt.days  # seguimiento disponible tras el evento
kv("V0b. Base M reconstruida", {"mantenimientos completados en rango": len(mc), "eventos M (dedupe vehículo-día)": len(M),
                                "vehículos": M.vehicle_id.nunique(), "eventos con km válido": int(M.km.notna().sum())})
P = M.dropna(subset=["prev_date"]).copy()

# ==================================================================================================
# V1. ¿15.000 / 10.000 km? ¿12·n meses?  (afirmación 1)
# ==================================================================================================
log("V1")
B = M[M.gen.isin(["P703", "P375"]) & M.maint_number.between(1, 20)]
rows = []
for (gname, n), s in B.groupby(["gen", "maint_number"]):
    if n <= 12:
        rows.append({"gen": gname, "n": int(n), "eventos": len(s), "km mediana": s.km.median(),
                     "km/n": (s.km / n).median(), "edad meses mediana": (s.edad_a * 12).median(),
                     "meses/n": (s.edad_a * 12 / n).median()})
table("V1a. km/n y meses/n por generación y n° de service (recalculado)", pd.DataFrame(rows),
      dec={"edad meses mediana": 1, "meses/n": 1}, index=False)
cons = P[(P.maint_number == P.prev_n + 1) & (P.d_km > 0) & P.gen.isin(["P703", "P375"])]
table("V1b. Δkm y Δdías entre services con numeración consecutiva (recalculado)",
      pct({f"{gname} Δkm": s.d_km for gname, s in cons.groupby("gen")} | {f"{gname} Δdías": s.d_dias for gname, s in cons.groupby("gen")}))
# Truncamiento: ¿qué edad máxima puede tener un P703 en el extracto?
wsd_p703 = M[M.gen == "P703"].WSD
age_max_p703 = (CUTOFF - wsd_p703.quantile(0.01)).days / MESES
s1 = B[(B.maint_number == 1) & (B.ModelYear >= 2024) & B.km.notna()]
kv("V1c. Sesgo de truncamiento en 'edad al n-ésimo service' y km al 1° service (MY>=2024)", {
    "P703: edad máxima posible al CUTOFF (meses, p1 de WSD)": (age_max_p703, 1),
    "P703: eventos con n=10": int(((B.gen == "P703") & (B.maint_number == 10)).sum()),
    "P703 n=10: tasa de uso mediana (km/año) de esos vehículos": (B[(B.gen == "P703") & (B.maint_number == 10)].eval("km / edad_a").median(), 0),
    "P703 n=1: edad mediana (meses)": ((B[(B.gen == "P703") & (B.maint_number == 1)].edad_a * 12).median(), 1),
    "P703 n=1: % con edad > 11,5 meses": (100 * (B[(B.gen == "P703") & (B.maint_number == 1)].edad_a * 12 > 11.5).mean(), 1),
    "1° service MY>=2024: n": len(s1),
    "1° service MY>=2024: % en (15.000, 18.000]": (100 * s1.km.between(15_000.01, 18_000).mean(), 1),
    "1° service MY>=2024: % en (12.000, 15.000]": (100 * s1.km.between(12_000.01, 15_000).mean(), 1),
    "1° service MY>=2024: % <= 10.000": (100 * (s1.km <= 10_000).mean(), 1),
}, note=f"P703 WSD p1 = {wsd_p703.quantile(0.01).date()}. Ningún P703 puede tener más de ~{age_max_p703:.0f} meses: "
        "el 'meses/n' para n alto está truncado por construcción (solo llegan a n=10 los de uso extremo).")

# ==================================================================================================
# V2. Tope anual y censura por la derecha  (afirmación 2)
# ==================================================================================================
log("V2")
W0 = M[M.gen.isin(["P703", "P375"]) & (M.fu >= D18)].copy()  # anclas con 18 m de seguimiento
ret = W0.dias_next.le(D18)
naive = P.d_dias
adj = W0.dias_next[ret]
# mediana incondicional (no-retorno tratado como > 548): válida porque > 50% retorna
unc = W0.dias_next.fillna(10_000)
kv("V2a. Intervalos > 365 días: ingenuo (todos los pares) vs con 18 m de seguimiento garantizado", {
    "pares ingenuos (todos)": len(naive), "  mediana días": naive.median(), "  % > 365 d": (100 * (naive > 365).mean(), 1),
    "anclas con seguimiento >= 548 d (P703/P375)": len(W0), "  % que retorna en 18 m": (100 * ret.mean(), 1),
    "  mediana días al siguiente, entre retornos en 18 m": adj.median(),
    "  % > 365 d entre retornos en 18 m": (100 * (adj > 365).mean(), 1),
    "  % > 365 d o sin retorno en 18 m (sobre todas las anclas)": (100 * ((W0.dias_next > 365) | W0.dias_next.isna()).mean(), 1),
    "  mediana incondicional (no-retorno = censurado > 548 d)": unc.median(),
    "  p75 incondicional": unc.quantile(0.75),
    "anclas con seguimiento >= 730 d: % > 365 d entre retornos en 24 m": (100 * (M[(M.fu >= 730) & M.dias_next.le(730)].dias_next > 365).mean(), 1),
})
rows = []
for gname, s in W0.groupby("gen"):
    r_ = s.dias_next.le(D18)
    rows.append({"gen": gname, "anclas": len(s), "% retorna 18 m": 100 * r_.mean(), "mediana días (retornos)": s.dias_next[r_].median(),
                 "p90 días (retornos)": s.dias_next[r_].quantile(0.9), "% > 365 d (retornos)": 100 * (s.dias_next[r_] > 365).mean(),
                 "mediana incondicional": s.dias_next.fillna(10_000).median()})
table("V2b. Lo mismo por generación", pd.DataFrame(rows), dec={"% retorna 18 m": 1, "% > 365 d (retornos)": 1}, index=False)

# ==================================================================================================
# V3. KM snapshot vs VehicleCurrentKM  (afirmación 3)
# ==================================================================================================
log("V3")
ag = load_agenda()[["vehicle_id", "schedule_id", "KM", "VehicleCurrentKM", "StatusARG", "ServiceMaintenance", "ServiceName"]]
km_nu = ag.groupby("vehicle_id").KM.nunique()
aps = ap.sort_values(["vehicle_id", "event_date", "schedule_id"])
has = aps.dropna(subset=["VehicleCurrentKM"])
last = has.groupby("vehicle_id").tail(1).set_index("vehicle_id")
last_comp = has[has.completed].groupby("vehicle_id").tail(1).set_index("vehicle_id")
mism = last[last.KM != last.VehicleCurrentKM]
kv("V3a. KM es constante por vehículo (nivel ítem, agenda cruda) y coincide con el último VehicleCurrentKM", {
    "vehículos (agenda cruda)": len(km_nu), "  con KM constante (nunique <= 1)": int((km_nu <= 1).sum()),
    "  % constante": (100 * (km_nu <= 1).mean(), 2),
    "vehículos con alguna lectura VCK": len(last),
    "  % KM == VCK última visita (cualquier estado)": (100 * (last.KM == last.VehicleCurrentKM).mean(), 1),
    "  % KM == VCK última visita (60) Concluido": (100 * (last_comp.KM == last_comp.VehicleCurrentKM).mean(), 1),
    "  % KM == VCK de alguna visita del vehículo": (100 * has.assign(eq=has.KM == has.VehicleCurrentKM).groupby("vehicle_id").eq.any().mean(), 1),
    "vehículos KM != VCK última": len(mism),
    "  de ellos KM nulo": int(mism.KM.isna().sum()),
    "  de ellos VCK última inválida (<100 o >1e6)": int((~mism.VehicleCurrentKM.between(100, 1_000_000)).sum()),
    "  de ellos KM > VCK última (dato más nuevo que la agenda)": int((mism.KM > mism.VehicleCurrentKM).sum()),
    "  de ellos KM < VCK última": int((mism.KM < mism.VehicleCurrentKM).sum()),
})
nul = ap.groupby("StatusARG").agg(turnos=("schedule_id", "size"), vck_nulo_pct=("VehicleCurrentKM", lambda s: 100 * s.isna().mean()),
                                  km_nulo_pct=("KM", lambda s: 100 * s.isna().mean()))
table("V3b. Nulos de VehicleCurrentKM y KM por StatusARG (recalculado)", nul, dec=1)

# ==================================================================================================
# V4. Tasa de uso: método A vs B; tasa reciente vs acumulada en la ventana (afirmación 4)
# ==================================================================================================
log("V4")
Mk = M[M.km.notna() & (M.edad_a >= 0.25)]
lastA = Mk.groupby("vehicle_id").tail(1).set_index("vehicle_id")
rateA = (lastA.km / lastA.edad_a)
rateA = rateA[rateA.between(2_000, 150_000)]
fk = M[M.km.notna()].groupby("vehicle_id").agg(d0=("event_date", "first"), k0=("km", "first"), d1=("event_date", "last"), k1=("km", "last"))
span = (fk.d1 - fk.d0).dt.days
rateB = ((fk.k1 - fk.k0) / (span / 365.25))[(span >= 90) & (fk.k1 > fk.k0)]
rateB = rateB[rateB.between(2_000, 150_000)]
both = pd.concat([rateA.rename("A"), rateB.rename("B")], axis=1).dropna()
# Tasa "a la extracción" con el snapshot KM (lo que usa el informe 03): KM / edad al CUTOFF
veh = M.groupby("vehicle_id").agg(KM=("KM", "first"), WSD=("WSD", "first"), gen=("gen", "first"), BU=("BU", "first"), PT=("PT", "first"))
veh["edad_cut"] = (CUTOFF - veh.WSD).dt.days / 365.25
rate_snap = (veh.KM / veh.edad_cut)[(veh.edad_cut >= 0.25) & veh.KM.between(100, 1_000_000)]
rate_snap = rate_snap[rate_snap.between(2_000, 150_000)]
kv("V4a. Tasa de uso: métodos A y B recalculados; y la variante 'KM snapshot / edad al CUTOFF'", {
    "A: vehículos": len(rateA), "A: mediana km/año": rateA.median(), "A: p25": rateA.quantile(0.25), "A: p75": rateA.quantile(0.75),
    "B: vehículos": len(rateB), "B: mediana km/año": rateB.median(),
    "ambos: n": len(both), "Spearman A-B": (both.corr(method="spearman").iloc[0, 1], 3),
    "mediana B/A": ((both.B / both.A).median(), 3), "% |B/A-1| <= 0,25": (100 * ((both.B / both.A - 1).abs() <= 0.25).mean(), 1),
    "KM snapshot / edad al CUTOFF: vehículos": len(rate_snap), "  mediana km/año": rate_snap.median(),
    "  Spearman vs A (vehículos con ambos)": (pd.concat([rateA.rename("A"), rate_snap.rename("S")], axis=1).dropna().corr(method="spearman").iloc[0, 1], 3),
})
ra = veh.join(rateA.rename("rate")).dropna(subset=["rate"])
table("V4b. Tasa A por segmento (recalculado)", pct({"P703": ra[ra.gen == "P703"].rate, "P375": ra[ra.gen == "P375"].rate,
                                                   "Ford Blue": ra[ra.BU == "Ford Blue"].rate, "Ford Pro": ra[ra.BU == "Ford Pro"].rate,
                                                   "PersonType F": ra[ra.PT == "F"].rate, "PersonType J": ra[ra.PT == "J"].rate}))

# Ventanas (reconstrucción propia) — se usan en V4c y V5
W = W0.copy()
rate_pop = ra.groupby("gen").rate.median()
W["rate_i"] = (W.km / W.edad_a).where((W.edad_a >= 0.25) & W.km.notna())
W["rate_i"] = W.rate_i.where(W.rate_i.between(2_000, 150_000))
W["fallback"] = W.rate_i.isna()
W["rate_i"] = W.rate_i.fillna(W.gen.map(rate_pop))
W["rate_rec"] = (W.d_km / (W.d_dias / 365.25)).where((W.d_dias >= 30) & (W.d_km > 0))
W["rate_rec"] = W.rate_rec.where(W.rate_rec.between(2_000, 150_000))
W["has_rec"] = W.rate_rec.notna()
W["K"] = W.gen.map({"P703": 15_000, "P375": 10_000})
W["due"] = np.minimum(365.0, W.K / W.rate_i * 365.25)
W["due_rec"] = np.minimum(365.0, W.K / W.rate_rec.fillna(W.rate_i) * 365.25)
W["due_blend"] = np.minimum(365.0, W.K / ((W.rate_rec.fillna(W.rate_i) + W.rate_i) / 2) * 365.25)
W["delay"] = W.dias_next - W.due
W["delay_rec"] = W.dias_next - W.due_rec
W["delay_blend"] = W.dias_next - W.due_blend
W["ret18"] = W.dias_next.le(D18)
sub = W[W.has_rec]
rows = []
for name, col in [("acumulada (km/edad)", "delay"), ("reciente (pendiente último intervalo)", "delay_rec"), ("promedio de ambas", "delay_blend")]:
    d = sub[col][sub.ret18]
    ab = ~(sub[col] < -30)
    rows.append({"tasa": name, "ventanas (subconjunto con tasa reciente)": len(sub), "p10": d.quantile(0.1), "p50": d.median(), "p90": d.quantile(0.9),
                 "mediana |retraso|": d.abs().median(), "% |retraso| <= 30 d": 100 * (d.abs() <= 30).mean(), "% |retraso| <= 60 d": 100 * (d.abs() <= 60).mean(),
                 "% abiertas a due-30": 100 * ab.mean(), "% retornos antes de due-30": 100 * (d < -30).mean(),
                 "% capturado hasta due+90": 100 * (d <= 90).mean(), "% churn abiertas H=90": 100 * (~(sub[col] <= 90))[ab].mean()})
table("V4c. Tasa reciente vs acumulada, comparadas SOLO en las ventanas donde la reciente existe (comparación no diluida)",
      pd.DataFrame(rows), dec={c: 1 for c in ["% |retraso| <= 30 d", "% |retraso| <= 60 d", "% abiertas a due-30", "% retornos antes de due-30",
                                            "% capturado hasta due+90", "% churn abiertas H=90"]}, index=False,
      note=f"La tabla f1 del informe original compara 'acumulada' contra 'reciente con fallback a acumulada' sobre TODAS las ventanas; "
           f"como la reciente existe solo en el {100 * W.has_rec.mean():.1f}% de ellas, la diferencia queda diluida. Acá se compara sobre ese subconjunto.")

# ==================================================================================================
# V5. Ventana recomendada: reconstrucción independiente (afirmación 5)
# ==================================================================================================
log("V5")
d_ret = W.delay[W.ret18]
ab = ~(W.delay < -30)
churn90 = ~(W.delay <= 90)
kv("V5a. Regla K por generación, apertura due-30, horizonte due+90 (recalculado)", {
    "ventanas": len(W), "% retorna en 18 m": (100 * W.ret18.mean(), 1), "% fallback a tasa poblacional": (100 * W.fallback.mean(), 1),
    "% manda el tope 365 d": (100 * (W.due >= 365 - 1e-9).mean(), 1), "due mediana (d)": W.due.median(),
    "retraso p10": d_ret.quantile(0.1), "retraso p25": d_ret.quantile(0.25), "retraso p50": d_ret.median(), "retraso p75": d_ret.quantile(0.75), "retraso p90": d_ret.quantile(0.9),
    "% ventanas abiertas a due-30": (100 * ab.mean(), 1), "% retornos antes de due-30": (100 * (d_ret < -30).mean(), 1),
    "% retornos capturados hasta due+90": (100 * (d_ret <= 90).mean(), 1), "  hasta due+60": (100 * (d_ret <= 60).mean(), 1), "  hasta due+120": (100 * (d_ret <= 120).mean(), 1),
    "% churn incondicional H=90": (100 * churn90.mean(), 1), "% churn entre abiertas H=90": (100 * churn90[ab].mean(), 1),
    "  H=60": (100 * (~(W.delay <= 60))[ab].mean(), 1), "  H=120": (100 * (~(W.delay <= 120))[ab].mean(), 1),
    "descomposición: % no vuelve en 18 m": (100 * (~W.ret18).mean(), 1), "descomposición: % tardíos (vuelve entre due+90 y 18 m)": (100 * (W.ret18 & (W.delay > 90)).mean(), 1),
})
rows = []
for gname, s in W.groupby("gen"):
    a_ = ~(s.delay < -30)
    rows.append({"gen": gname, "ventanas": len(s), "% retorna 18 m": 100 * s.ret18.mean(), "% tope 365": 100 * (s.due >= 365 - 1e-9).mean(),
                 "due mediana": s.due.median(), "retraso p50": s.delay[s.ret18].median(), "retraso p90": s.delay[s.ret18].quantile(0.9),
                 "% abiertas": 100 * a_.mean(), "% churn abiertas H=90": 100 * (~(s.delay <= 90))[a_].mean()})
table("V5b. Por generación (recalculado)", pd.DataFrame(rows), dec={c: 1 for c in ["% retorna 18 m", "% tope 365", "% abiertas", "% churn abiertas H=90"]}, index=False)
# Sensibilidad: 'retornos' a < 30 días del ancla (visitas partidas / re-trabajos) y ventanas con ancla en 2024 vs 2025
early = W.dias_next < 30
W2 = W[~early]
a2 = ~(W2.delay < -30)
kv("V5c. Sensibilidad: excluir 'retornos' a menos de 30 días del ancla", {
    "ventanas con siguiente mantenimiento a < 30 d": int(early.sum()), "  % del total": (100 * early.mean(), 1),
    "  de ellas con km <= km del ancla (visita partida)": int((early & (W.groupby("vehicle_id").km.shift(-1) <= W.km)).sum()),
    "sin ellas: % churn entre abiertas H=90": (100 * (~(W2.delay <= 90))[a2].mean(), 1),
    "sin ellas: % retornos antes de due-30": (100 * (W2.delay[W2.ret18] < -30).mean(), 1),
    "sin ellas: retraso p50": W2.delay[W2.ret18].median(),
})
W["anio_ancla"] = W.event_date.dt.year
rows = []
for (y, gname), s in W.groupby(["anio_ancla", "gen"]):
    a_ = ~(s.delay < -30)
    rows.append({"año ancla": y, "gen": gname, "ventanas": len(s), "% retorna 18 m": 100 * s.ret18.mean(), "% churn abiertas H=90": 100 * (~(s.delay <= 90))[a_].mean()})
table("V5d. Prevalencia por año del ancla y generación (¿drift?)", pd.DataFrame(rows), dec={"% retorna 18 m": 1, "% churn abiertas H=90": 1}, index=False)

# ==================================================================================================
# V6. Cohorte 2024: primer service y selección en 1°→2° (afirmación 6)
# ==================================================================================================
log("V6")
coh = sales[sales.WarrantyStartDate.dt.year == 2024].copy()
first = M.groupby("vehicle_id").agg(d1=("event_date", "first"), km1=("km", "first"), n1=("maint_number", "first"))
second = M[M.groupby("vehicle_id").cumcount() == 1].set_index("vehicle_id").event_date.rename("d2")
coh = coh.join(first, on="vehicle_id").join(second, on="vehicle_id")
coh["t1"] = (coh.d1 - coh.WarrantyStartDate).dt.days / MESES
coh["t12"] = (coh.d2 - coh.d1).dt.days / MESES
coh["fu"] = (CUTOFF - coh.WarrantyStartDate).dt.days / MESES
coh["fu1"] = (CUTOFF - coh.d1).dt.days / MESES
c1 = coh.dropna(subset=["d1"])
kv("V6a. Cohorte WSD 2024 (recalculado)", {
    "vehículos": len(coh), "seguimiento mínimo (meses)": (coh.fu.min(), 1),
    "% 1° mant. <= 12 m": (100 * (coh.t1 <= 12).mean(), 1), "% <= 18 m": (100 * (coh.t1 <= 18).mean(), 1), "% hasta CUTOFF": (100 * coh.d1.notna().mean(), 1),
    "mediana meses WSD->1°": (coh.t1[coh.t1 >= 0].median(), 1), "mediana km al 1°": coh.km1.median(),
    "% 1° evento con maint_number == 1": (100 * (c1.n1 == 1).mean(), 1),
    "1°->2°: n con seguimiento >= 12 m": int((c1.fu1 >= 12).sum()), "  % 2° <= 12 m": (100 * (c1[c1.fu1 >= 12].t12 <= 12).mean(), 1),
    "1°->2°: n con seguimiento >= 18 m": int((c1.fu1 >= 18).sum()), "  % 2° <= 18 m": (100 * (c1[c1.fu1 >= 18].t12 <= 18).mean(), 1),
    "  t1 mediana (meses) de ese subconjunto": (c1[c1.fu1 >= 18].t1.median(), 1), "  t1 mediana de todos los que hicieron el 1°": (c1.t1.median(), 1),
})
# Selección: retorno al 2° (12 m) según cuándo hicieron el 1°
c12 = c1[c1.fu1 >= 12].copy()
c12["t1_bucket"] = pd.cut(c12.t1, [-1, 4, 6, 8, 10, 12, 15, 30], labels=["<=4", "4-6", "6-8", "8-10", "10-12", "12-15", ">15"])
rows = []
for b, s in c12.groupby("t1_bucket", observed=True):
    rows.append({"meses WSD->1° (bucket)": str(b), "n (seg. >= 12 m tras el 1°)": len(s), "% 2° <= 12 m": 100 * (s.t12 <= 12).mean(),
                 "% con seg. >= 18 m": 100 * (s.fu1 >= 18).mean()})
table("V6b. Retorno al 2° service (12 m) según cuánto tardó el 1°: selección del subconjunto con 18 m de seguimiento",
      pd.DataFrame(rows), dec={"% 2° <= 12 m": 1, "% con seg. >= 18 m": 1}, index=False,
      note="Los vehículos con 18 m de seguimiento tras el 1° son los que hicieron el 1° temprano (t1 chico), que retornan más: "
           "el 91,5 % 'del 1° al 2° en 18 m' está sesgado hacia arriba. La comparación limpia es a 12 m: 64,5 % (WSD→1°) vs 75,4 % (1°→2°).")

# ==================================================================================================
# V7. Intervalo en km vs días por segmento, controlando generación y numeración consecutiva (afirmación 7)
# ==================================================================================================
log("V7")
c7 = cons[(cons.gen == "P703") & cons.BU.notna()]
rows = []
for lab, s in [("Ford Blue", c7[c7.BU == "Ford Blue"]), ("Ford Pro", c7[c7.BU == "Ford Pro"]), ("PersonType F", c7[c7.PT == "F"]), ("PersonType J", c7[c7.PT == "J"])]:
    rows.append({"segmento (P703, n→n+1, en sales)": lab, "pares": len(s), "Δkm p25": s.d_km.quantile(0.25), "Δkm mediana": s.d_km.median(), "Δkm p75": s.d_km.quantile(0.75),
                 "Δdías p25": s.d_dias.quantile(0.25), "Δdías mediana": s.d_dias.median(), "Δdías p75": s.d_dias.quantile(0.75)})
table("V7. Δkm y Δdías por segmento, solo P703 con numeración consecutiva (control de generación e intervalos dobles)", pd.DataFrame(rows), index=False)

# ==================================================================================================
# V8. Estacionalidad: índice crudo vs índice con tendencia removida (afirmación 8)
# ==================================================================================================
log("V8")
mens = M.groupby(M.event_date.dt.to_period("M")).size().rename("n").to_frame()
mens["dh"] = [np.busday_count(p.start_time.date(), (p.end_time + pd.Timedelta(days=1)).date()) for p in mens.index]
mens.loc[pd.Period("2026-08", "M"), "dh"] = np.busday_count(pd.Timestamp("2026-08-01").date(), (CUTOFF + pd.Timedelta(days=1)).date())
full = mens[mens.index < pd.Period("2026-08", "M")].copy()  # 31 meses completos
full["t"] = np.arange(len(full))
full["m"] = [p.month for p in full.index]
y = np.log(full.n / full.dh).values
X = np.column_stack([np.ones(len(full)), full.t.values] + [(full.m.values == k).astype(float) for k in range(2, 13)])
beta, *_ = np.linalg.lstsq(X, y, rcond=None)
seas = np.r_[0.0, beta[2:]]
seas_idx = 100 * np.exp(seas - seas.mean())
resid = y - X @ beta
# índice crudo del informe original (2024 y 2025, media anual = 100)
raw = {}
for yr in (2024, 2025):
    s = full[[p.year == yr for p in full.index]].n
    raw[yr] = 100 * s.values / s.mean()
raw_idx = (raw[2024] + raw[2025]) / 2
# ratio a media móvil centrada 2x12 (descomposición clásica), promedio por mes
ma = full.n.rolling(12, center=True).mean().rolling(2).mean().shift(-1)
ratio = (full.n / ma)
ratio_m = pd.Series(ratio.values, index=full.m.values).groupby(level=0).mean()
ratio_idx = 100 * ratio_m / ratio_m.mean()
g8 = pd.DataFrame({"mes": ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"],
                   "índice crudo (orig., 2024-25)": raw_idx,
                   "índice regresión: tendencia lineal + mes, por día hábil (2024-01→2026-07)": seas_idx,
                   "índice ratio a media móvil 2×12 (crudo)": ratio_idx.reindex(range(1, 13)).values})
table("V8a. Índice estacional: crudo vs con la tendencia removida", g8, dec=1, index=False,
      note=f"Tendencia estimada: {100 * (np.exp(beta[1]) - 1):.2f} % mensual por día hábil (≈ {100 * (np.exp(12 * beta[1]) - 1):.0f} % anual). "
           f"El índice crudo del informe original no remueve la tendencia, por lo que infla jul-dic y deprime ene-jun.")
rows = []
for yr in (2024, 2025, 2026):
    s = full[[p.year == yr for p in full.index]]
    rows.append({"año": yr, **{f"{k}": v for k, v in zip(g8.mes, (s.n / s.dh).reindex(range(len(s))).values if False else [np.nan] * 12)}})
# residuos por año y mes (tras tendencia+estacionalidad) para ver si junio/enero son consistentes
res_tab = pd.DataFrame({"año": [p.year for p in full.index], "mes": full.m.values, "resid %": 100 * resid}).pivot(index="mes", columns="año", values="resid %")
res_tab.index = g8.mes.values
table("V8b. Residuo (%) por año y mes tras quitar tendencia y estacionalidad: ¿junio/enero son sistemáticos?", res_tab, dec=1)

fig, ax = plt.subplots(figsize=(8, 3.8))
x = np.arange(1, 13)
ax.bar(x - 0.27, g8.iloc[:, 1], width=0.27, color="#7f7f7f", label="crudo (informe original)")
ax.bar(x, g8.iloc[:, 2], width=0.27, color="#1f5fa8", label="regresión: tendencia + mes (por día hábil)")
ax.bar(x + 0.27, g8.iloc[:, 3], width=0.27, color="#d9822b", label="ratio a media móvil 2×12")
ax.axhline(100, color="k", lw=0.8)
ax.set_xticks(x)
ax.set_xticklabels(g8.mes)
ax.set_ylim(70, 125)
ax.set_ylabel("índice (media = 100)")
ax.set_title("Índice estacional de mantenimientos completados: con y sin remover la tendencia")
ax.legend(fontsize=8)
ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(FIG_DIR / f"{PREFIX}_estacionalidad_detrended.png", dpi=130)
plt.close()

# ==================================================================================================
# V9. Saltos de numeración e 'intervalos dobles' (afirmación 9)
# ==================================================================================================
log("V9")
jump = (P.maint_number - P.prev_n)
jt = jump.value_counts().sort_index().rename("pares").to_frame()
jt["%"] = 100 * jt.pares / jt.pares.sum()
jt.index = jt.index.map(lambda v: str(int(v)))
jt.loc["< -3"] = [int((jump < -3).sum()), 100 * (jump < -3).mean()]
jt.loc["> 5"] = [int((jump > 5).sum()), 100 * (jump > 5).mean()]
jt.loc["nulo"] = [int(jump.isna().sum()), 100 * jump.isna().mean()]
table("V9a. Distribución completa del salto de maint_number (recalculado)", jt[[i in [str(k) for k in range(-3, 6)] + ["< -3", "> 5", "nulo"] for i in jt.index]], dec={"%": 1})
Pk = P[(P.d_km > 0) & P.gen.isin(["P703", "P375"])].assign(jump=jump)
rows = []
for gname, K in [("P703", 15_000), ("P375", 10_000)]:
    for j in [-1, 0, 1, 2, 3, 4]:
        s = Pk[(Pk.gen == gname) & (Pk.jump == j)]
        if len(s):
            rows.append({"gen": gname, "salto": j, "pares": len(s), "Δkm p25": s.d_km.quantile(0.25), "Δkm mediana": s.d_km.median(), "Δkm p75": s.d_km.quantile(0.75),
                         "Δkm mediana / K": s.d_km.median() / K, "Δdías mediana": s.d_dias.median(),
                         "% Δkm en [1,5K, 2,5K]": 100 * s.d_km.between(1.5 * K, 2.5 * K).mean()})
table("V9b. ¿El salto +2 es un 'intervalo doble'? Δkm por salto de numeración y generación",
      pd.DataFrame(rows), dec={"Δkm mediana / K": 2, "% Δkm en [1,5K, 2,5K]": 1}, index=False)
n20 = M.maint_number.value_counts()
it = ag[ag.ServiceMaintenance.notna()]
it_name_n = it.ServiceName.str.extract(r"^(\d+)")[0].astype(float)
ct = pd.crosstab(it.ServiceMaintenance.astype(int), (it_name_n == it.ServiceMaintenance).map({True: "nombre == n", False: "nombre != n"}))
ct["% nombre != n"] = 100 * ct.get("nombre != n", 0) / ct.sum(axis=1)
ct = ct.join(it.groupby(it.ServiceMaintenance.astype(int)).ServiceName.agg(lambda s: s.value_counts().index[0]).rename("nombre más frecuente"))
table("V9c. ServiceMaintenance vs número que dice ServiceName (nivel ítem, agenda cruda)", ct, dec={"% nombre != n": 1})
kv("V9d. Tope 20", {"eventos M con maint_number 19": int(n20.get(19, 0)), "eventos M con maint_number 20": int(n20.get(20, 0)),
                    "km mediana en n=20 (P375)": M[(M.maint_number == 20) & (M.gen == "P375")].km.median(),
                    "km mediana en n=19 (P375)": M[(M.maint_number == 19) & (M.gen == "P375")].km.median()})

OUT_MD.write_text("# Tablas de la verificación independiente del EDA 02\n\nGenerado por `scripts/eda/02_cadencia_ventana_verificacion.py`. "
                  f"CUTOFF = {CUTOFF.date()}.\n\n" + "\n".join(_parts), encoding="utf-8")
log(f"tablas -> {OUT_MD.relative_to(config.PROJECT_DIR)}")
log("listo")

# ==================================================================================================
# V10. Chequeos adicionales que surgieron de la verificación
# ==================================================================================================
log("V10")
# a) terciles de uso con seguimiento garantizado (a1 del original usa todos los pares: censura)
tc = rateA.quantile([1 / 3, 2 / 3]).values
W["tercil"] = pd.cut(W.vehicle_id.map(rateA), [-np.inf, tc[0], tc[1], np.inf], labels=["bajo", "medio", "alto"]).astype("str")
rows = []
for t, s in W[W.tercil != "nan"].groupby("tercil"):
    r_ = s.dias_next.le(D18)
    rows.append({"tercil de uso": t, "anclas (18 m seg.)": len(s), "% retorna 18 m": 100 * r_.mean(), "mediana días (retornos)": s.dias_next[r_].median(),
                 "mediana incondicional": s.dias_next.fillna(10_000).median(), "% > 365 d (retornos)": 100 * (s.dias_next[r_] > 365).mean(),
                 "pares ingenuos: mediana días": P[P.vehicle_id.map(rateA).pipe(lambda r: pd.cut(r, [-np.inf, tc[0], tc[1], np.inf], labels=["bajo", "medio", "alto"]).astype("str")) == t].d_dias.median()})
table("V10a. Días entre mantenimientos por tercil de uso: pares ingenuos vs anclas con 18 m de seguimiento", pd.DataFrame(rows),
      dec={"% retorna 18 m": 1, "% > 365 d (retornos)": 1}, index=False)
# b) prevalencia reponderada a la mezcla de generaciones de 2026
mix26 = M[M.event_date >= "2026-01-01"].gen.value_counts(normalize=True)
prev_gen = {gname: 100 * (~(s.delay <= 90))[~(s.delay < -30)].mean() for gname, s in W.groupby("gen")}
kv("V10b. Prevalencia de churn entre abiertas (H=90) reponderada a la mezcla P703/P375 de 2026", {
    "mezcla ventanas evaluadas: % P703": (100 * (W.gen == "P703").mean(), 1),
    "mezcla mantenimientos 2026-01→08: % P703": (100 * mix26.get("P703", 0), 1),
    "prevalencia observada (mezcla 2024-25)": (100 * (~(W.delay <= 90))[~(W.delay < -30)].mean(), 1),
    "prevalencia reponderada a mezcla 2026": (mix26.get("P703", 0) * prev_gen["P703"] + mix26.get("P375", 0) * prev_gen["P375"], 1),
})
# c) arranque en frío (f4): retraso con K=15.000 y tasa poblacional P703
c0 = coh[(coh.fu >= 18) & (coh.t1.isna() | (coh.t1 >= 0))].copy()
c0["d1d"] = (c0.d1 - c0.WarrantyStartDate).dt.days
due0 = min(365.0, 15_000 / rate_pop["P703"] * 365.25)
dl0 = (c0.d1d - due0)[c0.d1d.le(D18)]
kv("V10c. Primer service, ancla WSD, K=15.000 con tasa poblacional P703 (recalculado)", {
    "ventanas": len(c0), "due (d)": due0, "retraso p10": dl0.quantile(0.1), "retraso p50": dl0.median(), "retraso p90": dl0.quantile(0.9),
    "sólo tiempo (365 d): retraso p10": (c0.d1d - 365)[c0.d1d.le(D18)].quantile(0.1), "  p50": (c0.d1d - 365)[c0.d1d.le(D18)].median(), "  p90": (c0.d1d - 365)[c0.d1d.le(D18)].quantile(0.9),
})
# d) intervalos dobles medidos por km (independiente de la numeración)
rows = []
for gname, K in [("P703", 15_000), ("P375", 10_000)]:
    s = Pk[Pk.gen == gname]
    dbl = s.d_km >= 1.5 * K
    j2 = s.jump >= 2
    rows.append({"gen": gname, "pares km válido": len(s), "% Δkm >= 1,5K (intervalo doble por km)": 100 * dbl.mean(), "% salto >= +2": 100 * j2.mean(),
                 "% ambos": 100 * (dbl & j2).mean(), "% Δkm >= 1,5K entre salto +1": 100 * dbl[s.jump == 1].mean(), "% Δkm >= 1,5K entre salto >= +2": 100 * dbl[j2].mean(),
                 "% salto >= +2 entre Δkm >= 1,5K": 100 * j2[dbl].mean()})
table("V10d. 'Intervalos dobles' por km (Δkm >= 1,5·K) vs por salto de numeración", pd.DataFrame(rows), dec=1, index=False)
# e) etiqueta del 1° evento en la cohorte 2024: denominadores
kv("V10e. Cohorte 2024: '% del 1° evento etiquetado como 1° service' según denominador", {
    "sobre toda la cohorte (21.290, sin evento cuenta como no)": (100 * (coh.n1 == 1).mean(), 1),
    "sobre los que tienen evento (18.317)": (100 * (c1.n1 == 1).mean(), 1),
    "1° evento con n1 == 2": (100 * (c1.n1 == 2).mean(), 1), "1° evento con n1 >= 3": (100 * (c1.n1 >= 3).mean(), 1), "1° evento con n1 nulo": (100 * c1.n1.isna().mean(), 1),
})
OUT_MD.write_text("# Tablas de la verificación independiente del EDA 02\n\nGenerado por `scripts/eda/02_cadencia_ventana_verificacion.py`. "
                  f"CUTOFF = {CUTOFF.date()}.\n\n" + "\n".join(_parts), encoding="utf-8")
log("V10 listo")
