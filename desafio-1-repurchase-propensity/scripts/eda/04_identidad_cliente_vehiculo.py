"""EDA 04 — Identidad cliente–vehículo, transferencias, flotas y dealer.

Genera todas las tablas (stdout + reports/eda/04_identidad_cliente_vehiculo_tablas.md) y figuras
(reports/figures/eda/04_identidad_cliente_vehiculo_*.png) citadas en reports/eda/04_identidad_cliente_vehiculo.md.

Secciones:
  a) vehículos con >1 customer_id en agenda: patrón temporal (secuencial / alternancia / ambiguo),
     diagnóstico de artefactos de identidad por canal de reserva, transferencias por año y edad del vehículo.
  b) comprador (sales.customer_id) vs cliente de agenda: cruce con PersonType, BusinessUnit, canal; retorno.
  c) flotas: vehículos por customer_id (sales y agenda), Ford Pro vs flota, comportamiento de service.
  d) dealer: overlap de ids, primer service en el dealer vendedor, cambio de dealer vs retorno.
  e) vista consolidada por usuario: clientes con >=2 vehículos activos y con >=2 vehículos en ventana el mismo mes.
  f) vehículos vendidos que nunca aparecen en la agenda: antigüedad al CUTOFF.
  g) evidencia univariante de las features propuestas sobre un proxy de retorno (retorno_15m).

Proxy de retorno usado para las comparaciones univariantes (NO es el target oficial, es un stand-in):
  retorno_15m = dado un mantenimiento programado completado en la fecha d (d <= CUTOFF - 456 días),
  existe otro mantenimiento programado completado del mismo vehículo en (d, d + 456 días].
  456 días = 15 meses = ventana de 12 meses + 3 meses de tolerancia.

Uso (desde la carpeta del proyecto):
  PYTHONIOENCODING=utf8 PYTHONPATH=src .venv/Scripts/python.exe scripts/eda/04_identidad_cliente_vehiculo.py
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from repurchase import config
from repurchase.eventos import CUTOFF, appointments
from repurchase.io import load_sales

# ----------------------------------------------------------------------------------------------
# Configuración
# ----------------------------------------------------------------------------------------------
PREFIX = "04_identidad_cliente_vehiculo"
FIG_DIR = config.FIGURES_DIR / "eda"
FIG_DIR.mkdir(parents=True, exist_ok=True)
TABLES_MD = config.REPORTS_DIR / "eda" / f"{PREFIX}_tablas.md"
TABLES_MD.parent.mkdir(parents=True, exist_ok=True)

H_DAYS = 456  # 15 meses: horizonte del proxy de retorno
FLEET_MIN = 3  # definición de flota: >= 3 vehículos por customer_id
AGENDA_START = pd.Timestamp("2024-01-01")
DAYS_PER_MONTH = 30.44
DAYS_PER_YEAR = 365.25

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 60)
plt.rcParams.update({"figure.dpi": 110, "axes.grid": True, "grid.alpha": 0.3, "font.size": 9})

_md_buffer = io.StringIO()


def T(title: str, obj, note: str | None = None) -> None:
    """Imprime un objeto (DataFrame/Series/str) como tabla markdown y lo acumula para el archivo de tablas."""
    print(f"\n### {title}")
    if isinstance(obj, pd.Series):
        obj = obj.to_frame()
    if isinstance(obj, pd.DataFrame):
        txt = obj.to_markdown()
    else:
        txt = str(obj)
    print(txt)
    if note:
        print(f"_{note}_")
    _md_buffer.write(f"\n### {title}\n\n{txt}\n")
    if note:
        _md_buffer.write(f"\n_{note}_\n")


def mask(s: str) -> str:
    """Anonimiza un hash para los ejemplos del informe (ya está enmascarado, pero se acorta igual)."""
    return f"{s[:4]}…{s[-2:]}" if isinstance(s, str) else str(s)


def pct(x: float) -> str:
    return f"{100 * x:.1f}%"


# ----------------------------------------------------------------------------------------------
# Carga
# ----------------------------------------------------------------------------------------------
print("Cargando turnos (appointments) y ventas...")
ap = appointments()
sales = load_sales()
print(f"turnos: {len(ap):,}  ventas: {len(sales):,}  CUTOFF={CUTOFF.date()}")

# Base de trabajo: turnos con vehicle_id y customer_id no nulos, ordenados en el tiempo.
n_no_veh = ap["vehicle_id"].isna().sum()
n_no_cust = ap["customer_id"].isna().sum()
a = ap.dropna(subset=["vehicle_id", "customer_id"]).sort_values(["vehicle_id", "event_date", "schedule_id"]).reset_index(drop=True)
T("0.1 Cobertura de identificadores en turnos", pd.DataFrame({
    "turnos": [len(ap), int(n_no_veh), int(n_no_cust), len(a)],
}, index=["total", "sin vehicle_id", "sin customer_id", "con ambos (base de trabajo)"]))

# Chequeo transversal (no es de este tema pero salió en los ejemplos): ¿KM es el odómetro del turno o un snapshot por vehículo?
_kmchk = ap.dropna(subset=["vehicle_id"]).groupby("vehicle_id").agg(
    km_nu=("KM", "nunique"), km_nn=("KM", "count"), vck_nu=("VehicleCurrentKM", "nunique"), vck_nn=("VehicleCurrentKM", "count"))
T("0.2 ¿KM y VehicleCurrentKM varían entre turnos del mismo vehículo? (vehículos con >=2 valores no nulos)", pd.DataFrame({
    "vehículos evaluados": [int((_kmchk["km_nn"] >= 2).sum()), int((_kmchk["vck_nn"] >= 2).sum())],
    "% con un único valor (constante)": [pct((_kmchk.loc[_kmchk["km_nn"] >= 2, "km_nu"] <= 1).mean()),
                                         pct((_kmchk.loc[_kmchk["vck_nn"] >= 2, "vck_nu"] <= 1).mean())],
}, index=["KM", "VehicleCurrentKM"]), note="Si KM es constante por vehículo, es un snapshot al momento de la extracción (último odómetro conocido) y NO puede usarse como feature as-of.")
del _kmchk
# ¿Ese snapshot es el odómetro del ÚLTIMO turno con VehicleCurrentKM? (agregado en la verificación: la tabla 0.2 solo medía constancia)
_h = ap.dropna(subset=["vehicle_id", "VehicleCurrentKM"]).sort_values(["vehicle_id", "event_date", "schedule_id"])
_lv = _h.groupby("vehicle_id").agg(vck_last=("VehicleCurrentKM", "last"), vck_first=("VehicleCurrentKM", "first"),
                                   vck_max=("VehicleCurrentKM", "max"), km=("KM", "first"), n=("VehicleCurrentKM", "size")).dropna(subset=["km"])
T("0.3 ¿KM coincide con VehicleCurrentKM del último turno con odómetro? (vehículos con KM y >=1 VehicleCurrentKM)", pd.DataFrame({
    "vehículos": [len(_lv), int((_lv["km"] == _lv["vck_last"]).sum()), int((_lv["km"] == _lv["vck_max"]).sum()),
                  int((_lv.loc[_lv["n"] >= 2, "km"] == _lv.loc[_lv["n"] >= 2, "vck_first"]).sum())],
    "pct": [pct(1), pct((_lv["km"] == _lv["vck_last"]).mean()), pct((_lv["km"] == _lv["vck_max"]).mean()),
            pct((_lv.loc[_lv["n"] >= 2, "km"] == _lv.loc[_lv["n"] >= 2, "vck_first"]).mean())],
}, index=["vehículos con KM y VehicleCurrentKM", "KM == VehicleCurrentKM del ÚLTIMO turno", "KM == máximo VehicleCurrentKM",
          "KM == VehicleCurrentKM del PRIMER turno (solo vehículos con >=2 valores)"]))
del _h, _lv

# Cliente / dealer / fecha del turno anterior del mismo vehículo (cualquier estado).
a["prev_cust"] = a.groupby("vehicle_id")["customer_id"].shift()
a["prev_dealer"] = a.groupby("vehicle_id")["dealer_id"].shift()
a["prev_src"] = a.groupby("vehicle_id")["ScheduleSource"].shift()
a["prev_date"] = a.groupby("vehicle_id")["event_date"].shift()
a["switch"] = a["prev_cust"].notna() & (a["prev_cust"] != a["customer_id"])
a["same_day_switch"] = a["switch"] & (a["event_date"] == a["prev_date"])

# Clientes distintos por vehículo y vehículos distintos por cliente (totales de la agenda).
n_cust_veh = a.groupby("vehicle_id")["customer_id"].nunique()
n_veh_cust = a.groupby("customer_id")["vehicle_id"].nunique()
n_veh_cust_sales = sales.groupby("customer_id")["vehicle_id"].nunique()

# WarrantyStartDate por vehículo desde la agenda (primer valor no nulo) y desde sales.
wsd_agenda = a.groupby("vehicle_id")["WarrantyStartDate"].first()
sales_idx = sales.set_index("vehicle_id")

# ==============================================================================================
# a) Vehículos con más de un customer_id
# ==============================================================================================
print("\n\n==================== a) VEHÍCULOS CON >1 CUSTOMER_ID ====================")
multi_ids = n_cust_veh[n_cust_veh > 1].index
m = a[a["vehicle_id"].isin(multi_ids)].copy()
g = m.groupby("vehicle_id").agg(
    n_cust=("customer_id", "nunique"),
    n_switch=("switch", "sum"),
    n_same_day=("same_day_switch", "sum"),
    n_turnos=("schedule_id", "size"),
    n_maint_ok=("is_completed_maintenance", "sum"),
)
g["patron"] = np.select(
    [(g["n_switch"] == g["n_cust"] - 1) & (g["n_same_day"] == 0),
     (g["n_switch"] == g["n_cust"] - 1) & (g["n_same_day"] > 0)],
    ["secuencial (cambio permanente)", "ambiguo (cambio el mismo día)"],
    default="alternancia (uso compartido)",
)
T("a.1 Vehículos por cantidad de customer_id distintos en la agenda",
  n_cust_veh.value_counts().sort_index().rename("vehículos").to_frame().assign(
      pct=lambda d: (d["vehículos"] / d["vehículos"].sum()).map(pct)))
pat = g["patron"].value_counts().rename("vehículos").to_frame()
pat["pct_multi"] = (pat["vehículos"] / pat["vehículos"].sum()).map(pct)
T("a.2 Patrón temporal de los vehículos multi-cliente", pat,
  note=f"{len(g):,} vehículos con >1 customer_id; {int(m['switch'].sum()):,} cambios de cliente entre turnos consecutivos.")
T("a.3 Patrón temporal por cantidad de clientes", pd.crosstab(g["n_cust"].clip(upper=5), g["patron"]))

# --- Diagnóstico: ¿los cambios de cliente son transferencias o artefactos de identidad por canal?
sw = m[m["switch"]]
ns = m[m["prev_cust"].notna() & ~m["switch"]]
diag = pd.DataFrame({
    "en cambio de cliente": [
        (sw["prev_src"] != sw["ScheduleSource"]).mean(),
        (sw["prev_dealer"] != sw["dealer_id"]).mean(),
        ((sw["prev_src"] == "Dealer") & (sw["ScheduleSource"] == "FordPass")).mean()
        + ((sw["prev_src"] == "FordPass") & (sw["ScheduleSource"] == "Dealer")).mean(),
        sw["customer_id"].map(n_veh_cust).ge(FLEET_MIN).mean(),
        sw["prev_cust"].map(n_veh_cust).ge(FLEET_MIN).mean(),
    ],
    "en turnos consecutivos sin cambio": [
        (ns["prev_src"] != ns["ScheduleSource"]).mean(),
        (ns["prev_dealer"] != ns["dealer_id"]).mean(),
        ((ns["prev_src"] == "Dealer") & (ns["ScheduleSource"] == "FordPass")).mean()
        + ((ns["prev_src"] == "FordPass") & (ns["ScheduleSource"] == "Dealer")).mean(),
        ns["customer_id"].map(n_veh_cust).ge(FLEET_MIN).mean(),
        ns["prev_cust"].map(n_veh_cust).ge(FLEET_MIN).mean(),
    ],
}, index=["cambia ScheduleSource", "cambia dealer_id", "cruce Dealer<->FordPass",
          f"cliente nuevo tiene >={FLEET_MIN} vehículos", f"cliente anterior tiene >={FLEET_MIN} vehículos"])
T("a.4 Qué acompaña a un cambio de customer_id (pares de turnos consecutivos, vehículos multi-cliente)",
  diag.map(pct), note=f"n cambios = {len(sw):,}; n pares sin cambio = {len(ns):,}")
T("a.5 Canal del turno anterior vs canal del turno donde cambia el cliente",
  pd.crosstab(sw["prev_src"], sw["ScheduleSource"], margins=True))

a["is_fp"] = a["ScheduleSource"].eq("FordPass")
src_v = a.groupby("vehicle_id")["is_fp"].agg(["min", "max", "size"])
both_src = src_v[(~src_v["min"]) & (src_v["max"])].index
one_src = src_v[(src_v["min"] == src_v["max"]) & (src_v["size"] >= 2)].index
T("a.6 Multi-cliente según mezcla de canales del vehículo (vehículos con >=2 turnos)", pd.DataFrame({
    "vehículos": [len(both_src), len(one_src)],
    "% con >1 customer_id": [pct(n_cust_veh.loc[both_src].gt(1).mean()), pct(n_cust_veh.loc[one_src].gt(1).mean())],
}, index=["mezcla FordPass y no-FordPass", "un solo tipo de canal"]))
# Confusor: más turnos => más chance de mezclar canal Y de acumular ids. Se estratifica por n° de turnos (agregado en la verificación).
_vs = src_v.loc[src_v["size"] >= 2].copy()
_vs["mezcla"] = np.where(_vs.index.isin(both_src), "mezcla FP y no-FP", "un solo tipo de canal")
_vs["multi"] = n_cust_veh.reindex(_vs.index).gt(1)
_vs["n_turnos"] = pd.cut(_vs["size"], [1, 2, 3, 5, 8, 10**6], labels=["2", "3", "4-5", "6-8", "9+"])
_t = _vs.pivot_table(index="n_turnos", columns="mezcla", values="multi", aggfunc=["mean", "size"], observed=True)
T("a.6b % multi-cliente según mezcla de canal, estratificado por n° de turnos del vehículo",
  _t["mean"].map(pct).add_prefix("% multi | ").join(_t["size"].add_prefix("n ")),
  note="La brecha se reduce de 22 pp (sin estratificar) a 14-19 pp dentro de cada franja de turnos, pero no desaparece.")
del _vs, _t

# --- Transferencias: niveles de confianza
sw = sw.assign(
    cruce_canal=((sw["prev_src"] == "Dealer") & (sw["ScheduleSource"] == "FordPass"))
    | ((sw["prev_src"] == "FordPass") & (sw["ScheduleSource"] == "Dealer")),
    nuevo_flota=sw["customer_id"].map(n_veh_cust).ge(FLEET_MIN),
    viejo_flota=sw["prev_cust"].map(n_veh_cust).ge(FLEET_MIN),
)
seq_ids = g.index[g["patron"].str.startswith("secuencial")]
sw_seq = sw[sw["vehicle_id"].isin(seq_ids)].copy()
sw_seq["nivel"] = np.select(
    [~sw_seq["cruce_canal"] & ~sw_seq["nuevo_flota"] & ~sw_seq["viejo_flota"], ~sw_seq["cruce_canal"]],
    ["(iii) estricta: sin cruce de canal y ambos clientes <3 vehículos", "(ii) sin cruce Dealer<->FordPass"],
    default="(i) solo secuencial",
)
# Un vehículo secuencial puede tener más de un cambio (3+ clientes); se cuenta por cambio (= transferencia).
sw_seq["anio"] = sw_seq["event_date"].dt.year
sw_seq["edad_veh_anios"] = (sw_seq["event_date"] - sw_seq["vehicle_id"].map(wsd_agenda)).dt.days / DAYS_PER_YEAR
sw_seq["gap_dias"] = (sw_seq["event_date"] - sw_seq["prev_date"]).dt.days
niveles = ["(i) solo secuencial", "(ii) sin cruce Dealer<->FordPass",
           "(iii) estricta: sin cruce de canal y ambos clientes <3 vehículos"]
acum = {}
for i, nv in enumerate(niveles):
    sub = sw_seq[sw_seq["nivel"].isin(niveles[i:])]
    acum[nv] = {"transferencias": len(sub), "vehículos": sub["vehicle_id"].nunique(),
                "2024": int((sub["anio"] == 2024).sum()), "2025": int((sub["anio"] == 2025).sum()),
                "2026 (hasta 25/8)": int((sub["anio"] == 2026).sum()),
                "gap mediano (días)": float(sub["gap_dias"].median()),
                "edad mediana (años)": round(float(sub["edad_veh_anios"].median()), 2)}
T("a.7 Transferencias probables por nivel de confianza (acumulativo) y por año del cambio",
  pd.DataFrame(acum).T,
  note="Año = fecha del primer turno del cliente nuevo. 2024 subestima (no se ven turnos previos a 2024-01) y 2026 es parcial.")
strict = sw_seq[sw_seq["nivel"] == niveles[2]]
edad_bins = [-1, 1, 2, 3, 4, 5, 7, 10, 100]
edad_lbl = ["<1", "1-2", "2-3", "3-4", "4-5", "5-7", "7-10", "10+"]
T("a.8 Edad del vehículo (años desde WarrantyStartDate) al momento de la transferencia (nivel iii)",
  pd.cut(strict["edad_veh_anios"], edad_bins, labels=edad_lbl).value_counts().sort_index().rename("transferencias").to_frame()
  .assign(pct=lambda d: (d["transferencias"] / d["transferencias"].sum()).map(pct)),
  note=f"n = {len(strict):,}; sin WarrantyStartDate: {int(strict['edad_veh_anios'].isna().sum()):,}")
# Tasa anual aproximada: transferencias estrictas en 2025 sobre vehículos con actividad en 2025.
veh_2025 = a.loc[a["event_date"].dt.year == 2025, "vehicle_id"].nunique()
T("a.9 Tasa anual aproximada de transferencia (2025, nivel iii)", pd.DataFrame({
    "valor": [int((strict["anio"] == 2025).sum()), veh_2025,
              pct((strict["anio"] == 2025).sum() / veh_2025)]},
    index=["transferencias 2025", "vehículos con algún turno en 2025", "tasa"]))

# Hazard por edad (agregado en la verificación): la distribución de edades de las transferencias (a.8) hereda la composición del
# parque activo (más de la mitad tiene < 2 años). Lo comparable es transferencias / vehículos activos en cada franja de edad.
_act25 = a.loc[a["event_date"].dt.year == 2025, "vehicle_id"].unique()
_act25_2 = a.loc[(a["event_date"].dt.year == 2025) & a["vehicle_id"].map(a.groupby("vehicle_id").size()).ge(2), "vehicle_id"].unique()
_edad_mid = lambda ids: pd.cut((pd.Timestamp("2025-07-01") - wsd_agenda.reindex(ids)).dt.days / DAYS_PER_YEAR, edad_bins, labels=edad_lbl)
_den = _edad_mid(_act25).value_counts().sort_index()
_den2 = _edad_mid(_act25_2).value_counts().sort_index()
_num3 = pd.cut(strict.loc[strict["anio"] == 2025, "edad_veh_anios"], edad_bins, labels=edad_lbl).value_counts().sort_index()
_num1 = pd.cut(sw_seq.loc[sw_seq["anio"] == 2025, "edad_veh_anios"], edad_bins, labels=edad_lbl).value_counts().sort_index()
hazard = pd.DataFrame({
    "transferencias 2025 (iii)": _num3, "% de las transferencias (iii)": (_num3 / _num3.sum()).map(pct),
    "vehículos activos 2025": _den, "% del parque activo": (_den / _den.sum()).map(pct),
    "tasa (iii) por vehículo-año": (_num3 / _den).map(pct),
    "tasa (iii) sobre activos con >=2 turnos": (_num3 / _den2).map(pct),
    "tasa (i) sobre activos con >=2 turnos": (_num1 / _den2).map(pct),
})
T("a.8b Tasa de transferencia 2025 por edad del vehículo (transferencias / vehículos activos en 2025 en esa franja de edad)", hazard,
  note="Edad del parque medida al 2025-07-01. La tasa por vehículo-año es una meseta entre los años 1 y 7: la concentración de a.8 en 1-4 años "
       "refleja que el parque observado es joven, no una mayor propensión a transferirse a los 2-3 años.")

# Test de artefacto con vehículos vendidos 0 km (agregado en la verificación): el comprador es el primer dueño por construcción, así que si
# en un vehículo secuencial de 2 clientes el comprador aparece DESPUÉS de otro id, ese otro id no es un dueño anterior.
_seq2 = g.index[(g["patron"].str.startswith("secuencial")) & (g["n_cust"] == 2)]
_d2 = a[a["vehicle_id"].isin(_seq2)]
_chk = pd.DataFrame({"first": _d2.groupby("vehicle_id")["customer_id"].first(), "last": _d2.groupby("vehicle_id")["customer_id"].last()})
_chk["buyer"] = sales_idx["customer_id"].reindex(_chk.index)
_chk = _chk[_chk["buyer"].notna()]
_chk["caso"] = np.select([_chk["buyer"] == _chk["first"], _chk["buyer"] == _chk["last"]],
                         ["comprador primero, otro después (transferencia o artefacto)", "otro primero, comprador después (artefacto seguro)"],
                         default="comprador no aparece")
T("a.12 Vehículos VENDIDOS 2024-26, secuenciales con 2 clientes: posición del comprador en la secuencia",
  _chk["caso"].value_counts().rename("vehículos").to_frame().assign(pct=lambda d: (d["vehículos"] / d["vehículos"].sum()).map(pct)))
_art = _chk.index[_chk["caso"].str.startswith("otro primero")]
_sw_art = sw[sw["vehicle_id"].isin(_art)]
_fo = a[a["vehicle_id"].isin(_art)].groupby("vehicle_id").agg(first_date=("event_date", "min"), first_maint=("has_maint", "first"))
_fo["dias_vs_entrega"] = (_fo["first_date"] - sales_idx["DeliveryDate"].reindex(_fo.index)).dt.days
T("a.12b Los 'artefactos seguros': canal del cambio y momento del primer turno del id 'otro' respecto de DeliveryDate", pd.DataFrame({
    "vehículos": [len(_art), int(_sw_art["cruce_canal"].sum()), int(((_sw_art["prev_src"] == "Dealer") & (_sw_art["ScheduleSource"] == "Dealer")).sum()),
                  int((_fo["dias_vs_entrega"] < 0).sum()), int(_fo["dias_vs_entrega"].between(0, 30).sum()), int((_fo["dias_vs_entrega"] > 180).sum()),
                  int(_fo["first_maint"].sum())],
    "pct": [pct(1), pct(_sw_art["cruce_canal"].mean()), pct(((_sw_art["prev_src"] == "Dealer") & (_sw_art["ScheduleSource"] == "Dealer")).mean()),
            pct((_fo["dias_vs_entrega"] < 0).mean()), pct(_fo["dias_vs_entrega"].between(0, 30).mean()), pct((_fo["dias_vs_entrega"] > 180).mean()),
            pct(_fo["first_maint"].mean())],
}, index=["artefactos seguros", "el cambio es cruce Dealer<->FordPass", "el cambio es Dealer -> Dealer", "1er turno del 'otro' ANTES de la entrega (pre-entrega)",
          "0-30 días después de la entrega", "> 180 días después de la entrega", "1er turno del 'otro' incluye ítem de mantenimiento"]),
  note="Solo un tercio de los artefactos seguros es un cruce Dealer<->FordPass: el filtro de canal del nivel (ii) no limpia los artefactos Dealer->Dealer "
       "(mismo dueño con dos ids cargados por el dealer, o comprador-empresa y chofer).")
del _seq2, _d2, _chk, _art, _sw_art, _fo

# --- Ejemplos anonimizados
cols_ex = ["event_date", "customer_id", "dealer_id", "ScheduleSource", "StatusARG", "maint_number", "KM"]


def ejemplo(vid: str) -> pd.DataFrame:
    x = m.loc[m["vehicle_id"] == vid, cols_ex].copy()
    x["event_date"] = x["event_date"].dt.date
    x["customer_id"] = x["customer_id"].map(mask)
    x["dealer_id"] = x["dealer_id"].map(mask)
    return x.reset_index(drop=True)


rng = np.random.default_rng(4)
strict_2c = strict[strict["vehicle_id"].map(g["n_cust"]) == 2]
ex_seq = rng.choice(strict_2c["vehicle_id"].unique(), 2, replace=False)
ex_alt = rng.choice(g.index[(g["patron"].str.startswith("alternancia")) & (g["n_cust"] == 2) & (g["n_turnos"].between(4, 8))], 2, replace=False)
for i, v in enumerate(ex_seq, 1):
    T(f"a.10.{i} Ejemplo de cambio permanente (transferencia probable) — vehículo {mask(v)}", ejemplo(v))
for i, v in enumerate(ex_alt, 1):
    T(f"a.11.{i} Ejemplo de alternancia (uso compartido / flota / chofer) — vehículo {mask(v)}", ejemplo(v))

# --- Figura 1
fig, axes = plt.subplots(1, 3, figsize=(14, 4))
pat_plot = g["patron"].value_counts()
axes[0].barh(pat_plot.index, pat_plot.values, color=["#1f4e79", "#c0504d", "#9bbb59"][: len(pat_plot)])
for y, v in enumerate(pat_plot.values):
    axes[0].text(v, y, f" {v:,}", va="center")
axes[0].set_title(f"Patrón temporal de los {len(g):,} vehículos con >1 cliente")
axes[0].set_xlabel("vehículos")
axes[0].invert_yaxis()
_hz = (_num3 / _den * 100)
axes[1].bar(_hz.index.astype(str), _hz.values, color="#1f4e79", label="tasa de transferencia (iii) por vehículo-año")
ax1b = axes[1].twinx()
ax1b.plot(_hz.index.astype(str), (_den / _den.sum() * 100).values, color="#c0504d", marker="o", label="% del parque activo 2025")
ax1b.set_ylabel("% del parque activo 2025")
ax1b.grid(False)
axes[1].set_title("Transferencias 2025 (nivel iii) por edad del vehículo:\ntasa por vehículo-año vs composición del parque")
axes[1].set_xlabel("edad al 2025-07-01 (años desde WarrantyStartDate)")
axes[1].set_ylabel("transferencias / vehículos activos (%)")
h1, l1 = axes[1].get_legend_handles_labels()
h2, l2 = ax1b.get_legend_handles_labels()
axes[1].legend(h1 + h2, l1 + l2, fontsize=7, loc="upper right")
yr = pd.DataFrame({nv: sw_seq[sw_seq["nivel"].isin(niveles[i:])]["anio"].value_counts().sort_index()
                   for i, nv in enumerate(niveles)}).fillna(0)
yr.columns = ["(i) secuencial", "(ii) sin cruce canal", "(iii) estricta"]
yr.plot.bar(ax=axes[2], color=["#9bbb59", "#4f81bd", "#1f4e79"])
axes[2].set_title("Transferencias probables por año")
axes[2].set_xlabel("año del cambio (2026 parcial)")
axes[2].set_ylabel("transferencias")
axes[2].tick_params(axis="x", rotation=0)
fig.tight_layout()
fig.savefig(FIG_DIR / f"{PREFIX}_patrones.png")
plt.close(fig)

# ==============================================================================================
# b) Comprador vs cliente de agenda
# ==============================================================================================
print("\n\n==================== b) COMPRADOR VS CLIENTE DE AGENDA ====================")
s = sales[["vehicle_id", "customer_id", "dealer_id", "PersonType", "BusinessUnit", "SalesChannel",
           "WarrantyStartDate", "SalesDate"]].rename(columns={"customer_id": "buyer_id", "dealer_id": "sale_dealer"})
custs_veh = a.groupby("vehicle_id")["customer_id"].agg(lambda x: frozenset(x))
first_cust = a.groupby("vehicle_id")["customer_id"].first()
last_cust = a[a["event_date"] <= CUTOFF].groupby("vehicle_id")["customer_id"].last()
both = s[s["vehicle_id"].isin(custs_veh.index)].copy()
both["comprador_en_agenda"] = [b in c for b, c in zip(both["buyer_id"], both["vehicle_id"].map(custs_veh))]
both["comprador_es_primero"] = both["buyer_id"].values == both["vehicle_id"].map(first_cust).values
both["comprador_es_ultimo"] = both["buyer_id"].values == both["vehicle_id"].map(last_cust).values
both["n_cust_agenda"] = both["vehicle_id"].map(n_cust_veh)
agenda_custs = set(a["customer_id"].unique())
both["comprador_en_agenda_otro_veh"] = both["buyer_id"].isin(agenda_custs)
both["cliente_agenda_es_flota"] = both["vehicle_id"].map(last_cust).map(n_veh_cust).ge(FLEET_MIN)
T("b.1 Vehículos vendidos con turnos: ¿el comprador aparece en la agenda de ese vehículo?", pd.DataFrame({
    "vehículos": [len(both), int(both["comprador_en_agenda"].sum()), int(both["comprador_es_primero"].sum()),
                  int(both["comprador_es_ultimo"].sum()),
                  int((~both["comprador_en_agenda"] & both["comprador_en_agenda_otro_veh"]).sum())],
    "pct": [pct(1), pct(both["comprador_en_agenda"].mean()), pct(both["comprador_es_primero"].mean()),
            pct(both["comprador_es_ultimo"].mean()),
            pct((~both["comprador_en_agenda"] & both["comprador_en_agenda_otro_veh"]).sum() / (~both["comprador_en_agenda"]).sum())],
}, index=["vendidos y con turnos (customer_id no nulo)", "comprador aparece en la agenda del vehículo",
          "comprador es el PRIMER cliente de la agenda", "comprador es el ÚLTIMO cliente (vigente al CUTOFF)",
          "comprador NO aparece en este vehículo pero sí en otros (sobre los que no aparecen)"]))


def tasa_por(df: pd.DataFrame, by: str, flag: str, nombre: str) -> pd.DataFrame:
    out = df.groupby(by, observed=True)[flag].agg(n="size", tasa="mean")
    out[nombre] = out["tasa"].map(pct)
    return out.drop(columns="tasa")


T("b.2 Comprador en agenda según PersonType del comprador", tasa_por(both, "PersonType", "comprador_en_agenda", "% comprador en agenda"))
T("b.3 Comprador en agenda según BusinessUnit", tasa_por(both, "BusinessUnit", "comprador_en_agenda", "% comprador en agenda"))
T("b.4 Comprador en agenda según SalesChannel", tasa_por(both, "SalesChannel", "comprador_en_agenda", "% comprador en agenda"))
T("b.5 PersonType x BusinessUnit (vehículos vendidos con turnos): % comprador en agenda",
  pd.crosstab(both["PersonType"], both["BusinessUnit"], values=both["comprador_en_agenda"], aggfunc="mean").map(lambda v: pct(v) if pd.notna(v) else ""))
T("b.6 Cuando el comprador NO aparece: ¿el cliente vigente del vehículo es una flota (>=3 vehículos en agenda)?",
  tasa_por(both.assign(k=np.where(both["comprador_en_agenda"], "comprador aparece", "comprador no aparece")), "k",
           "cliente_agenda_es_flota", "% cliente vigente es flota"))
hr = sales[sales["SalesChannel"] == "HR"]
p25 = sales[sales["PersonType"] == "25"]
T("b.7 Concentración de compradores en canal HR y PersonType 25", pd.DataFrame({
    "ventas": [len(hr), len(p25)],
    "compradores distintos": [hr["customer_id"].nunique(), p25["customer_id"].nunique()],
    "ventas del comprador más frecuente": [int(hr["customer_id"].value_counts().iloc[0]), int(p25["customer_id"].value_counts().iloc[0])],
    "mismo id top en ambos": [hr["customer_id"].value_counts().index[0] == p25["customer_id"].value_counts().index[0]] * 2,
}, index=["SalesChannel = HR", "PersonType = 25"]))

# Figura 2
fig, axes = plt.subplots(1, 2, figsize=(11, 4))
b2 = both[both["PersonType"].isin(["F", "J"])]
ct = pd.crosstab(b2["PersonType"], b2["BusinessUnit"], values=b2["comprador_en_agenda"], aggfunc="mean")
ct.plot.bar(ax=axes[0], color=["#1f4e79", "#c0504d"])
axes[0].set_ylim(0, 1)
axes[0].set_title("% de vehículos donde el comprador aparece en la agenda")
axes[0].set_xlabel("PersonType del comprador (F física, J jurídica)")
axes[0].set_ylabel("proporción")
axes[0].tick_params(axis="x", rotation=0)
for cont in axes[0].containers:
    axes[0].bar_label(cont, fmt="%.2f")
ct2 = pd.crosstab(both["n_cust_agenda"].clip(upper=3), both["comprador_en_agenda"], normalize="index")
ct2.columns = ["comprador no aparece", "comprador aparece"]
ct2.plot.bar(ax=axes[1], stacked=True, color=["#c0504d", "#1f4e79"])
axes[1].set_title("Comprador en agenda según clientes distintos del vehículo")
axes[1].set_xlabel("customer_id distintos en la agenda (3 = 3 o más)")
axes[1].set_ylabel("proporción")
axes[1].tick_params(axis="x", rotation=0)
fig.tight_layout()
fig.savefig(FIG_DIR / f"{PREFIX}_comprador.png")
plt.close(fig)

# ==============================================================================================
# c) Flotas
# ==============================================================================================
print("\n\n==================== c) FLOTAS ====================")
bins_f = [0, 1, 2, 9, 49, 10**6]
lbl_f = ["1", "2", "3-9", "10-49", "50+"]


def fleet_cat(n: pd.Series) -> pd.Series:
    return pd.cut(n, bins_f, labels=lbl_f)


dist = pd.DataFrame({
    "clientes en sales": fleet_cat(n_veh_cust_sales).value_counts().sort_index(),
    "vehículos en sales": n_veh_cust_sales.groupby(fleet_cat(n_veh_cust_sales), observed=True).sum(),
    "clientes en agenda": fleet_cat(n_veh_cust).value_counts().sort_index(),
    "vehículos en agenda": n_veh_cust.groupby(fleet_cat(n_veh_cust), observed=True).sum(),
})
dist.loc["total"] = dist.sum()
T("c.1 Distribución de vehículos por customer_id (tamaño de flota) en sales y en agenda", dist,
  note=f"Flota = customer_id con >={FLEET_MIN} vehículos. En sales: {int((n_veh_cust_sales >= FLEET_MIN).sum()):,} clientes flota con "
       f"{int(n_veh_cust_sales[n_veh_cust_sales >= FLEET_MIN].sum()):,} vehículos ({pct(n_veh_cust_sales[n_veh_cust_sales >= FLEET_MIN].sum() / len(sales))} de las ventas). "
       f"En agenda: {int((n_veh_cust >= FLEET_MIN).sum()):,} clientes flota con {int(n_veh_cust[n_veh_cust >= FLEET_MIN].sum()):,} vehículos-cliente.")
top = n_veh_cust.sort_values(ascending=False).head(8)
top_df = pd.DataFrame({
    "customer_id": [mask(c) for c in top.index],
    "vehículos": top.values,
    "dealers distintos": [a.loc[a["customer_id"] == c, "dealer_id"].nunique() for c in top.index],
    "% turnos canal Dealer": [pct(a.loc[a["customer_id"] == c, "ScheduleSource"].eq("Dealer").mean()) for c in top.index],
    "% turnos concluidos": [pct(a.loc[a["customer_id"] == c, "completed"].mean()) for c in top.index],
    "es comprador en sales": [c in set(sales["customer_id"]) for c in top.index],
    "vehículos comprados en sales": [int(n_veh_cust_sales.get(c, 0)) for c in top.index],
}).set_index("customer_id")
T("c.2 Los 8 customer_id con más vehículos en la agenda", top_df)

sales["tam_flota_sales"] = sales["customer_id"].map(n_veh_cust_sales)
sales["flota_cat"] = fleet_cat(sales["tam_flota_sales"])
T("c.3 Ventas: tamaño de flota del comprador x BusinessUnit", pd.crosstab(sales["flota_cat"], sales["BusinessUnit"], margins=True))
T("c.4 Ventas: % Ford Pro según tamaño de flota, y % de cada BusinessUnit que es flota (>=3)", pd.concat([
    pd.crosstab(sales["flota_cat"], sales["BusinessUnit"], normalize="index").map(pct),
], axis=1), note="Ford Pro entre compradores de 1 vehículo: " + pct(sales.loc[sales['flota_cat'] == '1', 'BusinessUnit'].eq('Ford Pro').mean())
   + "; Ford Pro que son flota (>=3): " + pct(sales.loc[sales['BusinessUnit'] == 'Ford Pro', 'tam_flota_sales'].ge(FLEET_MIN).mean())
   + "; Ford Blue que son flota: " + pct(sales.loc[sales['BusinessUnit'] == 'Ford Blue', 'tam_flota_sales'].ge(FLEET_MIN).mean()))
T("c.5 Ventas: tamaño de flota x PersonType", pd.crosstab(sales["flota_cat"], sales["PersonType"], margins=True))

# --- Comportamiento de service por flota (agenda): categoría del cliente vigente del vehículo
veh = pd.DataFrame({"cust_vigente": last_cust})
veh["tam_flota"] = veh["cust_vigente"].map(n_veh_cust)
veh["flota_cat"] = fleet_cat(veh["tam_flota"])
veh["wsd"] = wsd_agenda.reindex(veh.index)
veh["business_unit"] = sales_idx["BusinessUnit"].reindex(veh.index)

# Tasa de mantenimiento completado por año de vida, solo años de vida enteramente observados en [2024-01-01, CUTOFF].
cm = a[a["is_completed_maintenance"] & (a["event_date"] <= CUTOFF)].copy()
cm["wsd"] = cm["vehicle_id"].map(wsd_agenda)
cm["anio_vida"] = np.floor((cm["event_date"] - cm["wsd"]).dt.days / DAYS_PER_YEAR).astype("float") + 1
maint_years = cm.dropna(subset=["anio_vida"]).groupby(["vehicle_id", "anio_vida"]).size().rename("n_maint")
rows = []
vw = veh.dropna(subset=["wsd"])
for k in range(1, 9):
    start = vw["wsd"] + pd.to_timedelta((k - 1) * DAYS_PER_YEAR, unit="D")
    end = vw["wsd"] + pd.to_timedelta(k * DAYS_PER_YEAR, unit="D")
    ok = (start >= AGENDA_START) & (end <= CUTOFF)
    sub = vw[ok].copy()
    sub["anio_vida"] = float(k)
    rows.append(sub)
yl = pd.concat(rows)
yl = yl.join(maint_years, on=["vehicle_id", "anio_vida"])
yl["hizo_maint"] = yl["n_maint"].fillna(0).gt(0)
yl["grupo"] = np.where(yl["tam_flota"] >= FLEET_MIN, "flota (>=3)", np.where(yl["tam_flota"] == 2, "2 vehículos", "particular (1)"))
tab_yl = yl.pivot_table(index="anio_vida", columns="grupo", values="hizo_maint", aggfunc=["mean", "size"])
tab_yl_fmt = tab_yl["mean"].map(pct).add_prefix("% ").join(tab_yl["size"].add_prefix("n "))
T("c.6 % de vehículos con >=1 mantenimiento programado completado en cada año de vida (años enteramente observados), por grupo",
  tab_yl_fmt, note="Población: vehículos con al menos un turno en 2024-2026 (sesgo de supervivencia: no incluye vehículos que dejaron de venir antes de 2024). "
                   "Año de vida k = [WSD + (k-1) años, WSD + k años).")
# Sesgo de supervivencia en los años 1-2 (agregado en la verificación): desde SALES se puede incluir a los vendidos que NUNCA tuvieron turno.
# Grupo = tamaño de flota del comprador combinando sales y agenda (vehículos distintos del customer_id en cualquiera de las dos tablas).
_pares = pd.concat([sales[["customer_id", "vehicle_id"]], a[["customer_id", "vehicle_id"]]]).drop_duplicates()
_nv_comb = _pares.groupby("customer_id")["vehicle_id"].nunique()
_sold = sales.dropna(subset=["WarrantyStartDate"]).set_index("vehicle_id")
_sold["tam_comb"] = _sold["customer_id"].map(_nv_comb)
_sold["grupo"] = np.where(_sold["tam_comb"] >= FLEET_MIN, "flota (>=3)", np.where(_sold["tam_comb"] == 2, "2 vehículos", "particular (1)"))
_rows = []
for k in (1, 2):
    _end = _sold["WarrantyStartDate"] + pd.to_timedelta(k * DAYS_PER_YEAR, unit="D")
    _sub = _sold[(_sold["WarrantyStartDate"] >= AGENDA_START) & (_end <= CUTOFF)].copy()
    _sub["anio_vida"] = float(k)
    _sub["hizo_maint"] = pd.MultiIndex.from_arrays([_sub.index, _sub["anio_vida"]]).isin(maint_years.index)
    _rows.append(_sub)
_yl2 = pd.concat(_rows)
_t2 = _yl2.pivot_table(index="anio_vida", columns="grupo", values="hizo_maint", aggfunc=["mean", "size"])
T("c.6b Años de vida 1 y 2 desde SALES (incluye vendidos que nunca tuvieron turno; flota = sales ∪ agenda)",
  _t2["mean"].map(pct).add_prefix("% ").join(_t2["size"].add_prefix("n ")),
  note="Comparar con c.6: al incluir a los que nunca vinieron, la flota ya está 5-6 pp por debajo del particular en el año 1 (c.6 la mostraba igual o arriba).")
del _pares, _nv_comb, _sold, _rows, _yl2, _t2

# Nivel turno: no-show, cancelación, canal, por grupo de flota del cliente del turno.
a["tam_flota_cliente_turno"] = a["customer_id"].map(n_veh_cust)
a["grupo_flota"] = np.where(a["tam_flota_cliente_turno"] >= FLEET_MIN, "flota (>=3)", np.where(a["tam_flota_cliente_turno"] == 2, "2 vehículos", "particular (1)"))
ap_h = a[a["event_date"] <= CUTOFF]
turnos = ap_h.groupby("grupo_flota").agg(
    turnos=("schedule_id", "size"),
    no_show=("no_show", "mean"), cancelado=("cancelled", "mean"), concluido=("completed", "mean"),
    con_mantenimiento=("has_maint", "mean"), FordPass=("ScheduleSource", lambda x: x.eq("FordPass").mean()),
    Dealer=("ScheduleSource", lambda x: x.eq("Dealer").mean()), reprogramado=("IsReschedule", lambda x: x.eq("Y").mean()),
)
T("c.7 Turnos hasta el CUTOFF por grupo de flota del cliente: estado y canal",
  turnos.assign(**{c: turnos[c].map(pct) for c in turnos.columns if c != "turnos"}))

# Figura 3
fig, axes = plt.subplots(1, 2, figsize=(12, 4))
(tab_yl["mean"] * 100).plot(ax=axes[0], marker="o")
axes[0].set_title("% con mantenimiento completado por año de vida\n(años enteramente observados 2024-01 → 2026-08)")
axes[0].set_xlabel("año de vida del vehículo")
axes[0].set_ylabel("% de vehículos")
axes[0].set_ylim(0, 100)
(turnos[["no_show", "cancelado", "FordPass"]] * 100).plot.bar(ax=axes[1], color=["#c0504d", "#f79646", "#1f4e79"])
axes[1].set_title("Turnos: no-show, cancelación y reserva por FordPass")
axes[1].set_xlabel("grupo de flota del cliente del turno")
axes[1].set_ylabel("% de turnos")
axes[1].tick_params(axis="x", rotation=0)
for cont in axes[1].containers:
    axes[1].bar_label(cont, fmt="%.1f")
fig.tight_layout()
fig.savefig(FIG_DIR / f"{PREFIX}_flotas.png")
plt.close(fig)

# ==============================================================================================
# d) Dealer
# ==============================================================================================
print("\n\n==================== d) DEALER ====================")
ds = set(sales["dealer_id"].dropna())
da = set(a["dealer_id"].dropna())
T("d.1 Overlap de dealer_id entre sales y agenda", pd.DataFrame({
    "valor": [len(ds), len(da), len(ds & da), len(ds - da), len(da - ds),
              pct(sales["dealer_id"].isin(da).mean()), pct(a["dealer_id"].isin(ds).mean())]},
    index=["dealers en sales", "dealers en agenda", "ids en ambas", "solo sales", "solo agenda",
           "% ventas cuyo dealer está en agenda", "% turnos cuyo dealer está en sales"]))
sales["dealer_en_agenda"] = sales["dealer_id"].isin(da)
sales["veh_en_agenda"] = sales["vehicle_id"].isin(set(ap["vehicle_id"].dropna()))
T("d.2 ¿La ausencia del dealer vendedor en la agenda explica que el vehículo no aparezca? (% vehículos vendidos con algún turno)",
  tasa_por(sales, "dealer_en_agenda", "veh_en_agenda", "% vehículos con turnos"))

# Diagnóstico de mapeo: para cada dealer vendedor, concentración del dealer del primer turno.
first_dealer = a.groupby("vehicle_id")["dealer_id"].first()
sd = sales[["vehicle_id", "dealer_id"]].dropna().assign(first_dealer=lambda d: d["vehicle_id"].map(first_dealer)).dropna()
conc = sd.groupby("dealer_id").apply(lambda d: pd.Series({
    "vehículos": len(d), "top dealer agenda = mismo id": pct((d["first_dealer"] == d.name).mean()),
    "share del dealer agenda más frecuente": pct(d["first_dealer"].value_counts(normalize=True).iloc[0]),
}), include_groups=False)
conc["dealer en agenda"] = conc.index.isin(da)
conc_sum = conc.groupby("dealer en agenda").agg(
    dealers=("vehículos", "size"),
    share_top_mediana=("share del dealer agenda más frecuente", lambda x: np.median(x.str.rstrip("%").astype(float))),
)
T("d.3 Concentración del dealer del primer turno según el dealer vendedor esté o no en la agenda (mediana del share del dealer más frecuente, %)",
  conc_sum, note="Si un dealer vendedor ausente de la agenda concentra sus vehículos en un único dealer de agenda, probablemente sea el mismo dealer con otro código.")
T("d.4 Los 10 dealers vendedores ausentes de la agenda con más ventas", conc[~conc["dealer en agenda"]].sort_values("vehículos", ascending=False).head(10))
# ¿El destino principal de un dealer ausente es un dealer que existe SOLO en la agenda (candidato a "mismo dealer, otro código") o uno que ya
# vende con su propio id (sucursal / punto de venta de otro grupo)? (agregado en la verificación)
_top = sd.groupby("dealer_id")["first_dealer"].agg(lambda x: x.value_counts().index[0]).rename("top_dest")
_ab = conc[~conc["dealer en agenda"]].join(_top)
_ab["top_solo_agenda"] = _ab["top_dest"].isin(da - ds)
_ab["share_top_num"] = _ab["share del dealer agenda más frecuente"].str.rstrip("%").astype(float)
_shared = _ab.groupby("top_dest").size()
_pres = conc.index[conc["dealer en agenda"]]
T("d.4b Dealers vendedores ausentes: naturaleza de su destino principal", pd.DataFrame({"valor": [
    len(_ab), int(_ab["vehículos"].sum()), int(_ab["top_solo_agenda"].sum()), pct(_ab.loc[_ab["top_solo_agenda"], "vehículos"].sum() / _ab["vehículos"].sum()),
    int(_ab["top_dest"].nunique()), int((_shared > 1).sum()), int((_ab["share_top_num"] >= 50).sum()),
    pct((_top.reindex(_pres).values == _pres.values).mean()),
    pct(conc.loc[_pres, "top dealer agenda = mismo id"].str.rstrip("%").astype(float).ge(50).mean())]},
    index=["dealers ausentes con ventas rastreables", "  ventas", "  cuyo destino principal es un dealer SOLO-agenda (34)", "  % de sus ventas",
           "  destinos principales distintos", "  destinos compartidos por >1 dealer ausente", "  con share del destino principal >= 50 %",
           "dealers presentes cuyo destino principal es él mismo", "dealers presentes con >= 50 % de sus primeros turnos en él mismo"]),
  note="'Mismo dealer con otro código' es plausible solo para los ausentes que derivan a un dealer solo-agenda; los que derivan a un dealer que ya vende con su id son más bien puntos de venta / sucursales de otro taller.")
del _top, _ab, _shared

# Primer service en el dealer vendedor.
fm = cm.groupby("vehicle_id").agg(first_maint_dealer=("dealer_id", "first"), first_maint_date=("event_date", "min"))
b2 = s.merge(fm, left_on="vehicle_id", right_index=True, how="inner")
b2["mismo_dealer_1er_maint"] = b2["sale_dealer"] == b2["first_maint_dealer"]
b2["mismo_dealer_1er_turno"] = b2["sale_dealer"] == b2["vehicle_id"].map(first_dealer)
b2["dealer_venta_en_agenda"] = b2["sale_dealer"].isin(da)
T("d.5 % de vehículos vendidos cuyo primer mantenimiento completado / primer turno ocurre en el dealer que los vendió", pd.DataFrame({
    "vehículos": [len(b2), int(b2["dealer_venta_en_agenda"].sum())],
    "% 1er mantenimiento en dealer vendedor": [pct(b2["mismo_dealer_1er_maint"].mean()), pct(b2.loc[b2["dealer_venta_en_agenda"], "mismo_dealer_1er_maint"].mean())],
    "% 1er turno (cualquiera) en dealer vendedor": [pct(b2["mismo_dealer_1er_turno"].mean()), pct(b2.loc[b2["dealer_venta_en_agenda"], "mismo_dealer_1er_turno"].mean())],
}, index=["todos los vendidos con mantenimiento completado", "solo si el dealer vendedor está en la agenda"]))
T("d.6 % 1er mantenimiento en el dealer vendedor por BusinessUnit y PersonType (dealer vendedor en agenda)",
  pd.concat([tasa_por(b2[b2["dealer_venta_en_agenda"]], "BusinessUnit", "mismo_dealer_1er_maint", "% mismo dealer"),
             tasa_por(b2[b2["dealer_venta_en_agenda"]], "PersonType", "mismo_dealer_1er_maint", "% mismo dealer")]))

# ==============================================================================================
# g) Features as-of y proxy de retorno (se calcula antes de e/f porque d y b lo usan)
# ==============================================================================================
print("\n\n==================== g) FEATURES AS-OF Y PROXY DE RETORNO ====================")
# n_clientes_distintos_vehiculo as-of: primera aparición del par (vehículo, cliente) acumulada.
a["nuevo_par_vc"] = ~a.duplicated(["vehicle_id", "customer_id"])
a["n_clientes_asof"] = a.groupby("vehicle_id")["nuevo_par_vc"].cumsum()
a["primer_cliente"] = a["vehicle_id"].map(first_cust)
a["fecha_1ra_aparicion_par"] = a.groupby(["vehicle_id", "customer_id"])["event_date"].transform("min")
a["meses_desde_transferencia"] = np.where(
    a["customer_id"] != a["primer_cliente"], (a["event_date"] - a["fecha_1ra_aparicion_par"]).dt.days / DAYS_PER_MONTH, np.nan)
# tamaño_flota_cliente as-of: vehículos distintos vistos con ese cliente hasta la fecha.
a_c = a[["customer_id", "vehicle_id", "event_date"]].sort_values(["customer_id", "event_date"])
a_c["nuevo_par_cv"] = ~a_c.duplicated(["customer_id", "vehicle_id"])
a["tam_flota_asof"] = a_c.groupby("customer_id")["nuevo_par_cv"].cumsum().reindex(a.index)
del a_c
# comprador / dealer de venta
a["buyer_id"] = a["vehicle_id"].map(sales_idx["customer_id"])
a["sale_dealer"] = a["vehicle_id"].map(sales_idx["dealer_id"])
a["es_comprador"] = np.select([a["buyer_id"].isna(), a["customer_id"] == a["buyer_id"]], ["sin venta", "comprador"], default="otro")
a["mismo_dealer_que_venta"] = np.select(
    [a["sale_dealer"].isna() | ~a["sale_dealer"].isin(da), a["dealer_id"] == a["sale_dealer"]],
    ["sin venta / dealer no en agenda", "sí"], default="no")
a["cambio_de_dealer"] = np.select([a["prev_dealer"].isna(), a["prev_dealer"] != a["dealer_id"]], ["primer turno", "sí"], default="no")
# Dealer del mantenimiento completado anterior (cambio de dealer entre services, no entre turnos cualesquiera).
cm_all = a[a["is_completed_maintenance"]].copy()
cm_all["prev_maint_dealer"] = cm_all.groupby("vehicle_id")["dealer_id"].shift()
cm_all["next_maint_date"] = cm_all.groupby("vehicle_id")["event_date"].shift(-1)
cm_all["cambio_dealer_vs_maint_anterior"] = np.select(
    [cm_all["prev_maint_dealer"].isna(), cm_all["prev_maint_dealer"] != cm_all["dealer_id"]], ["primer mantenimiento", "sí"], default="no")
ev = cm_all[(cm_all["event_date"] <= CUTOFF - pd.Timedelta(days=H_DAYS)) & (cm_all["event_date"] >= AGENDA_START)].copy()
ev["retorno_15m"] = (ev["next_maint_date"] - ev["event_date"]).dt.days.le(H_DAYS).fillna(False)
base_rate = ev["retorno_15m"].mean()
T("g.0 Proxy de retorno: eventos elegibles", pd.DataFrame({"valor": [
    len(ev), ev["vehicle_id"].nunique(), str(ev["event_date"].min().date()), str(ev["event_date"].max().date()), pct(base_rate)]},
    index=["mantenimientos completados con d <= CUTOFF - 456 días", "vehículos", "primer evento", "último evento", "retorno_15m base"]))

ev["n_clientes_asof_cat"] = ev["n_clientes_asof"].clip(upper=3).astype(int).astype(str).replace({"3": "3+"})
ev["tam_flota_asof_cat"] = pd.cut(ev["tam_flota_asof"], [0, 1, 2, 9, 10**6], labels=["1", "2", "3-9", "10+"]).astype(str)
ev["meses_desde_transf_cat"] = pd.cut(ev["meses_desde_transferencia"], [-0.01, 3, 6, 12, 1000], labels=["0-3", "3-6", "6-12", "12+"]).astype(str).replace({"nan": "sin transferencia"})
ev["tam_flota_sales_cat"] = fleet_cat(ev["vehicle_id"].map(sales_idx["customer_id"]).map(n_veh_cust_sales)).astype(str).replace({"nan": "sin venta"})
ev["business_unit"] = ev["vehicle_id"].map(sales_idx["BusinessUnit"]).fillna("sin venta")
ev["person_type"] = ev["vehicle_id"].map(sales_idx["PersonType"]).fillna("sin venta")
ev["n_maint_cat"] = ev["maint_number"].clip(upper=6).fillna(-1).astype(int).astype(str).replace({"6": "6+", "-1": "s/n"})

features = [
    ("es_comprador", "es_comprador"),
    ("n_clientes_distintos_vehiculo (as-of)", "n_clientes_asof_cat"),
    ("tamaño_flota_cliente (agenda, as-of)", "tam_flota_asof_cat"),
    ("tamaño_flota_comprador (sales)", "tam_flota_sales_cat"),
    ("mismo_dealer_que_venta", "mismo_dealer_que_venta"),
    ("cambio_de_dealer (vs turno anterior)", "cambio_de_dealer"),
    ("cambio_de_dealer (vs mantenimiento anterior)", "cambio_dealer_vs_maint_anterior"),
    ("meses_desde_transferencia", "meses_desde_transf_cat"),
    ("BusinessUnit (sales)", "business_unit"),
    ("PersonType (sales)", "person_type"),
    ("n° de mantenimiento del evento", "n_maint_cat"),
]
uni_rows = []
for nombre, col in features:
    gg = ev.groupby(col, observed=True)["retorno_15m"].agg(n="size", tasa="mean")
    for lvl, r in gg.iterrows():
        uni_rows.append({"feature": nombre, "nivel": lvl, "n eventos": int(r["n"]), "retorno_15m": r["tasa"], "lift vs base": r["tasa"] / base_rate})
uni = pd.DataFrame(uni_rows)
uni_fmt = uni.assign(retorno_15m=uni["retorno_15m"].map(pct), **{"lift vs base": uni["lift vs base"].round(3)}).set_index(["feature", "nivel"])
T("g.1 Retorno a 15 meses (proxy) por nivel de cada feature candidata", uni_fmt,
  note=f"Base = {pct(base_rate)} sobre {len(ev):,} eventos. Lift = tasa del nivel / tasa base.")
# Rango de discriminación por feature (max - min entre niveles con n >= 500).
rng_tab = (uni[uni["n eventos"] >= 500].groupby("feature")["retorno_15m"].agg(["min", "max"]).assign(rango_pp=lambda d: 100 * (d["max"] - d["min"]))
           .sort_values("rango_pp", ascending=False))
T("g.2 Rango de retorno entre niveles (puntos porcentuales, niveles con n >= 500)", rng_tab.assign(min=rng_tab["min"].map(pct), max=rng_tab["max"].map(pct), rango_pp=rng_tab["rango_pp"].round(1)))
# Cruces relevantes
T("g.3 Retorno por es_comprador x PersonType del comprador (solo vendidos)",
  ev[ev["es_comprador"] != "sin venta"].pivot_table(index="person_type", columns="es_comprador", values="retorno_15m", aggfunc=["mean", "size"])
  .pipe(lambda t: t["mean"].map(pct).add_prefix("% ").join(t["size"].add_prefix("n "))))
T("g.4 Retorno por es_comprador x BusinessUnit (solo vendidos)",
  ev[ev["es_comprador"] != "sin venta"].pivot_table(index="business_unit", columns="es_comprador", values="retorno_15m", aggfunc=["mean", "size"])
  .pipe(lambda t: t["mean"].map(pct).add_prefix("% ").join(t["size"].add_prefix("n "))))
T("g.5 Retorno por tamaño de flota (agenda as-of) x n° de mantenimiento",
  ev.pivot_table(index="n_maint_cat", columns="tam_flota_asof_cat", values="retorno_15m", aggfunc="mean").map(lambda v: pct(v) if pd.notna(v) else ""))
T("g.6 Retorno según mismo dealer que venta x cambio de dealer vs mantenimiento anterior (solo vendidos con dealer en agenda)",
  ev[ev["mismo_dealer_que_venta"] != "sin venta / dealer no en agenda"].pivot_table(
      index="cambio_dealer_vs_maint_anterior", columns="mismo_dealer_que_venta", values="retorno_15m", aggfunc=["mean", "size"])
  .pipe(lambda t: t["mean"].map(pct).add_prefix("% ").join(t["size"].add_prefix("n "))))
# Sensibilidad: mismo análisis con horizonte 12 meses.
ev["retorno_12m"] = (ev["next_maint_date"] - ev["event_date"]).dt.days.le(365).fillna(False)
base12 = ev["retorno_12m"].mean()
sens_rows = []
for nombre, col in features[:8]:
    gg = ev.groupby(col, observed=True)["retorno_12m"].agg(n="size", tasa="mean")
    for lvl, r in gg.iterrows():
        sens_rows.append({"feature": nombre, "nivel": lvl, "n eventos": int(r["n"]), "retorno_12m": pct(r["tasa"]), "lift vs base": round(r["tasa"] / base12, 3)})
T("g.7 Sensibilidad: retorno a 12 meses por nivel (mismas features)", pd.DataFrame(sens_rows).set_index(["feature", "nivel"]),
  note=f"Base retorno_12m = {pct(base12)}.")

# Estratificación por edad del vehículo al evento: neutraliza el confundidor "vendido en 2024-26 = vehículo nuevo".
ev["edad_evento"] = (ev["event_date"] - ev["vehicle_id"].map(wsd_agenda)).dt.days / DAYS_PER_YEAR
ev["edad_cat"] = pd.cut(ev["edad_evento"], [-1, 2, 4, 100], labels=["<2 años", "2-4 años", "4+ años"]).astype(str).replace({"nan": "sin WSD"})
T("g.8.0 Retorno a 15 m por edad del vehículo al evento (confundidor principal)",
  ev.groupby("edad_cat")["retorno_15m"].agg(n="size", tasa="mean").assign(tasa=lambda d: d["tasa"].map(pct)))
strat_feats = [("n_clientes_distintos_vehiculo (as-of)", "n_clientes_asof_cat"), ("tamaño_flota_cliente (agenda, as-of)", "tam_flota_asof_cat"),
               ("cambio_de_dealer (vs mantenimiento anterior)", "cambio_dealer_vs_maint_anterior"), ("meses_desde_transferencia", "meses_desde_transf_cat"),
               ("es_comprador", "es_comprador"), ("mismo_dealer_que_venta", "mismo_dealer_que_venta")]
strat = []
for nombre, col in strat_feats:
    t = ev[ev["edad_cat"] != "sin WSD"].pivot_table(index=col, columns="edad_cat", values="retorno_15m", aggfunc=["mean", "size"], observed=True)
    out = t["mean"].map(lambda v: pct(v) if pd.notna(v) else "").add_prefix("% ").join(t["size"].fillna(0).astype(int).add_prefix("n "))
    out.index = pd.MultiIndex.from_product([[nombre], out.index.astype(str)], names=["feature", "nivel"])
    strat.append(out)
T("g.8 Retorno a 15 m por nivel de cada feature, estratificado por edad del vehículo al evento", pd.concat(strat),
  note="Comparar niveles dentro de cada columna (misma franja de edad). Los niveles 'sin venta' concentran vehículos viejos.")

# Figura 6: retorno por feature
plot_feats = [f for f in features if f[1] in ("es_comprador", "n_clientes_asof_cat", "tam_flota_asof_cat", "mismo_dealer_que_venta",
                                                 "cambio_dealer_vs_maint_anterior", "meses_desde_transf_cat")]
fig, axes = plt.subplots(2, 3, figsize=(14, 7))
for ax, (nombre, col) in zip(axes.ravel(), plot_feats):
    gg = ev.groupby(col, observed=True)["retorno_15m"].agg(n="size", tasa="mean")
    ax.bar(gg.index.astype(str), gg["tasa"] * 100, color="#1f4e79")
    ax.axhline(base_rate * 100, color="#c0504d", ls="--", label=f"base {base_rate*100:.1f}%")
    for i, (lvl, r) in enumerate(gg.iterrows()):
        ax.text(i, r["tasa"] * 100 + 1, f"{r['tasa']*100:.1f}%\nn={int(r['n']):,}", ha="center", fontsize=7)
    ax.set_title(nombre, fontsize=9)
    ax.set_ylim(0, 105)
    ax.set_ylabel("% retorno 15 m")
    ax.tick_params(axis="x", labelsize=7, rotation=15)
    ax.legend(fontsize=7, loc="lower right")
fig.suptitle("Retorno a 15 meses (proxy) según features de identidad, flota y dealer — mantenimientos completados 2024-01 → 2025-05")
fig.tight_layout()
fig.savefig(FIG_DIR / f"{PREFIX}_features.png")
plt.close(fig)

# Figura 4: dealer
fig, axes = plt.subplots(1, 2, figsize=(11, 4))
dd = b2[b2["dealer_venta_en_agenda"]].groupby("BusinessUnit")["mismo_dealer_1er_maint"].mean() * 100
axes[0].bar(dd.index, dd.values, color=["#1f4e79", "#c0504d"])
for i, v in enumerate(dd.values):
    axes[0].text(i, v + 1, f"{v:.1f}%", ha="center")
axes[0].set_ylim(0, 100)
axes[0].set_title("% de vehículos con 1er mantenimiento en el dealer vendedor\n(dealer vendedor presente en la agenda)")
axes[0].set_ylabel("% de vehículos")
g6 = ev[ev["mismo_dealer_que_venta"] != "sin venta / dealer no en agenda"].pivot_table(
    index="cambio_dealer_vs_maint_anterior", columns="mismo_dealer_que_venta", values="retorno_15m", aggfunc="mean") * 100
g6.plot.bar(ax=axes[1], color=["#c0504d", "#1f4e79"])
axes[1].axhline(base_rate * 100, color="grey", ls="--", label="base")
axes[1].set_title("Retorno a 15 m según cambio de dealer y mismo dealer que venta")
axes[1].set_xlabel("¿cambió de dealer respecto del mantenimiento anterior?")
axes[1].set_ylabel("% retorno 15 m")
axes[1].set_ylim(0, 100)
axes[1].tick_params(axis="x", rotation=0)
axes[1].legend(title="mismo dealer que venta", fontsize=8)
for cont in axes[1].containers:
    axes[1].bar_label(cont, fmt="%.1f")
fig.tight_layout()
fig.savefig(FIG_DIR / f"{PREFIX}_dealer.png")
plt.close(fig)

# ==============================================================================================
# e) Vista consolidada por usuario
# ==============================================================================================
print("\n\n==================== e) VISTA CONSOLIDADA POR USUARIO ====================")
act = a[(a["event_date"] >= "2025-01-01") & (a["event_date"] <= CUTOFF)]
veh_act_cust = act.groupby("customer_id")["vehicle_id"].nunique()
# Cliente vigente por vehículo (último turno <= CUTOFF) y vehículos por cliente vigente.
veh_vig = last_cust.rename("cust_vigente").to_frame()
veh_vig["activo_2025_26"] = veh_vig.index.isin(set(act["vehicle_id"]))
vig_cnt = veh_vig[veh_vig["activo_2025_26"]].groupby("cust_vigente").size()
T("e.1 Clientes con varios vehículos (actividad 2025-01-01 → CUTOFF)", pd.DataFrame({"valor": [
    int(len(veh_act_cust)), int((veh_act_cust >= 2).sum()), int(veh_act_cust[veh_act_cust >= 2].sum()),
    pct(veh_act_cust[veh_act_cust >= 2].sum() / veh_act_cust.sum()),
    int(len(vig_cnt)), int((vig_cnt >= 2).sum()), int(vig_cnt[vig_cnt >= 2].sum()), pct(vig_cnt[vig_cnt >= 2].sum() / vig_cnt.sum())]},
    index=["customer_id con algún turno 2025-26", "  de los cuales con >=2 vehículos (cualquier turno)", "  vehículos-cliente en esos clientes",
           "  % de los pares vehículo-cliente activos", "clientes VIGENTES (último turno) con vehículos activos 2025-26",
           "  de los cuales con >=2 vehículos vigentes", "  vehículos en esos clientes", "  % de los vehículos activos"]))
T("e.2 Distribución de vehículos activos 2025-26 por cliente vigente", fleet_cat(vig_cnt).value_counts().sort_index().rename("clientes").to_frame()
  .assign(vehículos=vig_cnt.groupby(fleet_cat(vig_cnt), observed=True).sum()))

# Ventana aproximada: mantenimiento completado + 12 meses -> mes calendario.
# CORRECCIÓN (verificación): la versión original usaba solo el ÚLTIMO mantenimiento de cada vehículo al CUTOFF. Eso excluye del período a todo
# vehículo que volvió (su "último" corre la ventana al futuro) y deja una población sesgada hacia los que NO volvieron (17.449 vehículos-ventana
# en 2025-09 → 2026-08 contra 82.140 reales). Ahora cada mantenimiento completado abre una ventana 12 meses después; el cliente es el vigente
# al momento de ese mantenimiento (el del turno), que es lo que se conocería al abrir la ventana.
PER0, PER1 = pd.Period("2025-09", "M"), pd.Period("2026-08", "M")
win = cm[["vehicle_id", "customer_id", "event_date"]].copy()
win["mes_ventana"] = (win["event_date"] + pd.DateOffset(months=12)).dt.to_period("M")
win = win.drop_duplicates(["vehicle_id", "mes_ventana"])
cm_month = win.groupby(["customer_id", "mes_ventana"])["vehicle_id"].nunique().rename("n_veh").reset_index()
multi_m = cm_month[cm_month["n_veh"] >= 2]
in_per = win["mes_ventana"].between(PER0, PER1)
last12 = multi_m[multi_m["mes_ventana"].between(PER0, PER1)]
# Versión original (solo último mantenimiento, cliente vigente al CUTOFF) se conserva para trazabilidad del cambio.
_wl = cm.groupby("vehicle_id")["event_date"].max().to_frame("d")
_wl["cust"] = last_cust.reindex(_wl.index)
_wl["mes"] = (_wl["d"] + pd.DateOffset(months=12)).dt.to_period("M")
_gl = _wl.dropna(subset=["cust"]).groupby(["cust", "mes"]).size()
_gl_p = _gl[(_gl.index.get_level_values("mes") >= PER0) & (_gl.index.get_level_values("mes") <= PER1)]
T("e.3 Clientes con >=2 vehículos que entran en ventana (mantenimiento completado + 12 meses) el mismo mes", pd.DataFrame({"valor": [
    int(len(win)), int(win["vehicle_id"].nunique()), int(multi_m["customer_id"].nunique()), int(len(multi_m)), int(multi_m["n_veh"].sum()),
    pct(multi_m["n_veh"].sum() / len(win)), int(in_per.sum()), int(last12["customer_id"].nunique()), int(last12["n_veh"].sum()),
    pct(last12["n_veh"].sum() / in_per.sum()),
    int(_wl["mes"].between(PER0, PER1).sum()), int(_gl_p[_gl_p >= 2].sum()), pct(_gl_p[_gl_p >= 2].sum() / _wl["mes"].between(PER0, PER1).sum())]},
    index=["ventanas (mantenimiento completado + 12 m), todas", "  vehículos", "clientes con >=2 vehículos en ventana el mismo mes (alguna vez)",
           "  pares (cliente, mes) con >=2 vehículos", "  vehículos-ventana involucrados", "  % de todas las ventanas",
           "ventanas en 2025-09 → 2026-08", "  clientes con >=2 vehículos el mismo mes en ese período", "  vehículos-ventana involucrados",
           "  % de las ventanas del período", "[método original] ventanas 2025-09 → 2026-08 usando solo el ÚLTIMO mantenimiento",
           "[método original]   vehículos de clientes con >=2 el mismo mes", "[método original]   % coincidencia"]),
  note="El método original (solo último mantenimiento) daba 195 clientes / 1.262 vehículos / 7,2 %: subestimaba la población de ventanas ~5 veces.")
T("e.4 Distribución de vehículos por (cliente, mes de ventana) cuando hay >=2",
  multi_m["n_veh"].clip(upper=10).value_counts().sort_index().rename("pares cliente-mes").to_frame())
mm = win.groupby("mes_ventana").size().rename("vehículos en ventana")
mm2 = multi_m.groupby("mes_ventana")["n_veh"].sum().rename("de clientes con >=2 el mismo mes")
mm3 = _wl.groupby("mes").size().rename("[método original] solo último mantenimiento")
T("e.5 Vehículos que entran en ventana por mes (2025-09 → 2026-12)", pd.concat([mm, mm2, mm3], axis=1).fillna(0).astype(int).loc["2025-09":"2026-12"],
  note="Los meses > 2026-08 son ventanas ya definidas (mantenimientos de 2025-09 → 2026-08) cuyo retorno todavía no se puede observar: se listan como proyección de carga.")
del _wl, _gl, _gl_p

# ==============================================================================================
# f) Vendidos que nunca aparecen en la agenda
# ==============================================================================================
print("\n\n==================== f) VENDIDOS QUE NUNCA APARECEN EN LA AGENDA ====================")
sales["meses_desde_wsd"] = (CUTOFF - sales["WarrantyStartDate"]).dt.days / DAYS_PER_MONTH
so = sales[~sales["veh_en_agenda"]]
si = sales[sales["veh_en_agenda"]]
bins_m = [-1, 3, 6, 9, 12, 15, 18, 24, 36, 1000]
lbl_m = ["0-3", "3-6", "6-9", "9-12", "12-15", "15-18", "18-24", "24-36", "36+"]
fdist = pd.DataFrame({
    "nunca en agenda": pd.cut(so["meses_desde_wsd"], bins_m, labels=lbl_m).value_counts().sort_index(),
    "con turnos": pd.cut(si["meses_desde_wsd"], bins_m, labels=lbl_m).value_counts().sort_index(),
})
fdist["% nunca en agenda (fila)"] = (fdist["nunca en agenda"] / fdist.sum(axis=1)).map(pct)
T("f.1 Meses desde WarrantyStartDate al CUTOFF: vehículos vendidos sin ningún turno vs con turnos", fdist,
  note=f"Sin turno: {len(so):,} vehículos ({so['customer_id'].nunique():,} compradores); sin WarrantyStartDate: {int(so['WarrantyStartDate'].isna().sum())}.")
T("f.2 Resumen de los vendidos sin turno", pd.DataFrame({"valor": [
    len(so), pct((so["meses_desde_wsd"] < 12).mean()), int((so["meses_desde_wsd"] >= 12).sum()), int((so["meses_desde_wsd"] >= 15).sum()),
    pct((so["meses_desde_wsd"] >= 15).mean()), pct((sales["meses_desde_wsd"] >= 15).sum() and (so["meses_desde_wsd"] >= 15).sum() / (sales["meses_desde_wsd"] >= 15).sum()),
    float(so["meses_desde_wsd"].median().round(1))]},
    index=["vehículos vendidos sin turno", "% con < 12 meses desde WSD (todavía no les tocaba)", "con >= 12 meses (ventana vencida)",
           "con >= 15 meses (ventana + tolerancia vencida = 'elegible y nunca vino')", "% con >= 15 meses",
           "% que representan sobre TODOS los vendidos con >= 15 meses", "mediana de meses desde WSD"]))
so15 = sales[sales["meses_desde_wsd"] >= 15]
T("f.3 Entre vendidos con >= 15 meses: % que nunca tuvo un turno, por segmento", pd.concat([
    tasa_por(so15.assign(nunca=~so15["veh_en_agenda"]), "PersonType", "nunca", "% nunca vino"),
    tasa_por(so15.assign(nunca=~so15["veh_en_agenda"]), "BusinessUnit", "nunca", "% nunca vino"),
    tasa_por(so15.assign(nunca=~so15["veh_en_agenda"]), "SalesChannel", "nunca", "% nunca vino"),
    tasa_por(so15.assign(nunca=~so15["veh_en_agenda"]), "flota_cat", "nunca", "% nunca vino"),
    tasa_por(so15.assign(nunca=~so15["veh_en_agenda"]), "dealer_en_agenda", "nunca", "% nunca vino"),
]))
# Primer mantenimiento dentro de 15 meses desde WSD (R1) para vendidos con >= 15 meses.
so15 = so15.assign(first_maint=so15["vehicle_id"].map(fm["first_maint_date"]))
so15["r1_15m"] = ((so15["first_maint"] - so15["WarrantyStartDate"]).dt.days <= H_DAYS).fillna(False)
T("f.4 Vendidos con >= 15 meses: % con 1er mantenimiento programado completado dentro de los 15 meses desde WSD", pd.concat([
    tasa_por(so15, "BusinessUnit", "r1_15m", "% 1er service en 15 m"), tasa_por(so15, "PersonType", "r1_15m", "% 1er service en 15 m"),
    tasa_por(so15, "flota_cat", "r1_15m", "% 1er service en 15 m")]),
  note=f"Total: {pct(so15['r1_15m'].mean())} sobre {len(so15):,} vehículos.")

# Figura 5
fig, ax = plt.subplots(figsize=(9, 4))
fdist[["nunca en agenda", "con turnos"]].plot.bar(ax=ax, color=["#c0504d", "#1f4e79"])
ax.set_title("Vehículos vendidos: meses desde WarrantyStartDate al CUTOFF (25/8/2026)")
ax.set_xlabel("meses desde WarrantyStartDate")
ax.set_ylabel("vehículos")
ax.tick_params(axis="x", rotation=0)
ax.axvline(3.5, color="grey", ls="--")
ax.text(3.6, ax.get_ylim()[1] * 0.9, "12 meses: ventana vencida", fontsize=8)
fig.tight_layout()
fig.savefig(FIG_DIR / f"{PREFIX}_nunca_vino.png")
plt.close(fig)

# ==============================================================================================
# Cierre
# ==============================================================================================
hdr = (f"# Tablas generadas por scripts/eda/{PREFIX}.py\n\nCUTOFF = {CUTOFF.date()}; proxy retorno_15m = otro mantenimiento completado en "
       f"{H_DAYS} días; flota = >= {FLEET_MIN} vehículos por customer_id.\n")
TABLES_MD.write_text(hdr + _md_buffer.getvalue(), encoding="utf-8")
print(f"\nTablas guardadas en {TABLES_MD}")
print("Figuras:", sorted(p.name for p in FIG_DIR.glob(f"{PREFIX}_*.png")))
