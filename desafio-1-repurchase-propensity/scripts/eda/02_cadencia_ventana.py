"""EDA 02 — Cadencia de mantenimiento (tiempo y km) y parámetros empíricos de la ventana.

Evento objetivo: ``is_completed_maintenance`` (turno (60) Concluido con al menos un ítem de mantenimiento
programado), tal como lo define ``repurchase.eventos``. Acá no se redefine; si algo no cierra se señala.

Genera:
- reports/eda/02_cadencia_ventana_tablas.md  (todas las tablas citadas en el informe, en markdown)
- reports/figures/eda/02_cadencia_ventana_*.png

Uso (desde la carpeta del proyecto):
    PYTHONIOENCODING=utf8 PYTHONPATH=src .venv/Scripts/python.exe scripts/eda/02_cadencia_ventana.py
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
from repurchase.io import load_sales  # noqa: E402

# --------------------------------------------------------------------------------------------------
# Configuración
# --------------------------------------------------------------------------------------------------
T0 = time.time()
PREFIX = "02_cadencia_ventana"
FIG_DIR = config.FIGURES_DIR / "eda"
FIG_DIR.mkdir(parents=True, exist_ok=True)
TABLES_MD = config.REPORTS_DIR / "eda" / f"{PREFIX}_tablas.md"
TABLES_MD.parent.mkdir(parents=True, exist_ok=True)

START = pd.Timestamp("2024-01-01")  # inicio del extracto de agenda
KM_MIN_VALIDO = 100  # lecturas de odómetro por debajo de esto se consideran inválidas (auto 0 km no va a service)
KM_MAX_VALIDO = 1_000_000  # por encima, físicamente implausible para el parque
RATE_MIN, RATE_MAX = 2_000, 150_000  # km/año plausibles
MESES = 30.4375  # días por mes (365.25/12)
DIAS_18M = 548  # 18 meses en días
Q = [0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95]
QNAMES = ["p5", "p10", "p25", "p50", "p75", "p90", "p95"]
PALETA = {"P703": "#1f5fa8", "P375": "#d9822b", "Otro": "#7f7f7f"}

plt.rcParams.update({"figure.dpi": 110, "savefig.dpi": 130, "axes.grid": True, "grid.alpha": 0.3,
                     "font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9})

_md_parts: list[str] = []


def log(msg: str) -> None:
    print(f"[{time.time() - T0:6.0f}s] {msg}", flush=True)


def fmt(v, dec: int = 0) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return ""
    if isinstance(v, (int, np.integer)) or dec == 0:
        return f"{int(round(float(v))):,}".replace(",", ".")
    return f"{float(v):,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def df_to_md(df: pd.DataFrame, dec: dict | int = 0, index: bool = True) -> str:
    """DataFrame -> tabla markdown con formato numérico rioplatense (punto de miles, coma decimal)."""
    d = df.copy()
    if index:
        d = d.reset_index()
    cols = list(d.columns)
    lines = ["| " + " | ".join(str(c) for c in cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, row in d.iterrows():
        cells = []
        for c in cols:
            v = row[c]
            if isinstance(v, (float, int, np.integer, np.floating)) and not isinstance(v, bool):
                dd = dec.get(c, 0) if isinstance(dec, dict) else dec
                cells.append(fmt(v, dd))
            else:
                cells.append(str(v))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def add_table(title: str, df: pd.DataFrame, dec: dict | int = 0, index: bool = True, note: str = "") -> None:
    md = f"### {title}\n\n" + df_to_md(df, dec, index) + ("\n\n" + note if note else "") + "\n"
    _md_parts.append(md)
    print("\n" + md)


def add_kv(title: str, items: dict, note: str = "") -> None:
    """Tabla clave-valor con decimales por fila: items = {etiqueta: valor | (valor, decimales)}."""
    rows = []
    for k, v in items.items():
        val, dec = v if isinstance(v, tuple) else (v, 0)
        rows.append({"métrica": k, "valor": fmt(val, dec)})
    add_table(title, pd.DataFrame(rows), index=False, note=note)


def pct_table(groups: dict[str, pd.Series], dec: int = 0) -> pd.DataFrame:
    rows = {}
    for name, s in groups.items():
        s = s.dropna()
        if len(s) == 0:
            continue
        qs = s.quantile(Q).values
        rows[name] = dict(n=len(s), **dict(zip(QNAMES, qs)), media=s.mean())
    return pd.DataFrame(rows).T


def savefig(name: str) -> None:
    p = FIG_DIR / f"{PREFIX}_{name}.png"
    plt.tight_layout()
    plt.savefig(p)
    plt.close()
    log(f"figura -> {p.relative_to(config.PROJECT_DIR)}")


def gen_map(s: pd.Series) -> pd.Series:
    out = pd.Series("Otro", index=s.index, dtype="str")
    out[s.str.contains("P703", na=False)] = "P703"
    out[s.str.contains("P375", na=False)] = "P375"
    return out


def my_group(my: pd.Series) -> pd.Series:
    bins = [0, 2015, 2019, 2022, 2023, 2024, 2026]
    labels = ["<=2015", "2016-2019", "2020-2022", "2023", "2024", "2025-2026"]
    return pd.cut(my, bins=bins, labels=labels).astype("str").replace("nan", "s/d")


# --------------------------------------------------------------------------------------------------
# Carga
# --------------------------------------------------------------------------------------------------
log("cargando turnos (appointments) y ventas")
ap = appointments()
sales = load_sales()
sales_idx = sales.set_index("vehicle_id")[["BusinessUnit", "PersonType", "WarrantyStartDate", "SalesDate"]]
sales_idx.columns = ["BusinessUnit", "PersonType", "WSD_sales", "SalesDate"]
ap["gen"] = gen_map(ap["ShortVehicleModelGroupTreated"])
log(f"turnos: {fmt(len(ap))}  mantenimientos completados: {fmt(int(ap.is_completed_maintenance.sum()))}")

# --------------------------------------------------------------------------------------------------
# c) KM vs VehicleCurrentKM — qué es cada columna
# --------------------------------------------------------------------------------------------------
log("c) KM vs VehicleCurrentKM")
nul = ap.groupby("StatusARG").agg(
    turnos=("schedule_id", "size"),
    KM_nulo_pct=("KM", lambda s: 100 * s.isna().mean()),
    VehicleCurrentKM_nulo_pct=("VehicleCurrentKM", lambda s: 100 * s.isna().mean()),
    Checkin_nulo_pct=("EffectiveCheckinDate", lambda s: 100 * s.isna().mean()),
)
add_table("c1. Nulos de KM, VehicleCurrentKM y check-in por estado del turno (todos los turnos)", nul,
          dec={"KM_nulo_pct": 1, "VehicleCurrentKM_nulo_pct": 1, "Checkin_nulo_pct": 1})

ap_s = ap.sort_values(["vehicle_id", "event_date", "schedule_id"])
per_veh = ap_s.groupby("vehicle_id").agg(
    n_turnos=("schedule_id", "size"), km_nunique=("KM", "nunique"), km_max=("KM", "max"),
    vck_nunique=("VehicleCurrentKM", "nunique"), vck_max=("VehicleCurrentKM", "max"),
)
last_vck = ap_s.dropna(subset=["VehicleCurrentKM"]).groupby("vehicle_id").tail(1).set_index("vehicle_id")
add_kv("c2. KM es un atributo del vehículo (snapshot), VehicleCurrentKM es el odómetro del evento", {
    "vehículos en agenda": len(per_veh),
    "vehículos con KM constante (<=1 valor distinto)": int((per_veh.km_nunique <= 1).sum()),
    "% vehículos con KM constante": (100 * (per_veh.km_nunique <= 1).mean(), 2),
    "vehículos con >1 valor de KM": int((per_veh.km_nunique > 1).sum()),
    "vehículos con >=2 turnos": int((per_veh.n_turnos >= 2).sum()),
    "vehículos con >=2 turnos y >1 valor de VehicleCurrentKM": int(((per_veh.n_turnos >= 2) & (per_veh.vck_nunique > 1)).sum()),
    "vehículos con alguna lectura VehicleCurrentKM": len(last_vck),
    "% KM == VehicleCurrentKM de la última visita con lectura": (100 * (last_vck.KM == last_vck.VehicleCurrentKM).mean(), 1),
    "% KM >= VehicleCurrentKM de la última visita con lectura": (100 * (last_vck.KM >= last_vck.VehicleCurrentKM).mean(), 1),
    "% KM == max(VehicleCurrentKM) del vehículo": (100 * (per_veh.km_max == per_veh.vck_max).mean(), 1),
}, note="Lectura: `KM` no varía entre turnos del mismo vehículo y coincide con el `VehicleCurrentKM` de la última visita "
        "con lectura. Es el 'último km conocido' a la fecha de extracción, NO el km del turno.")

# Km al evento: VehicleCurrentKM sobre mantenimientos completados
mc = ap[ap.is_completed_maintenance].copy()
vck = mc["VehicleCurrentKM"]
add_kv("c3. Valores anómalos de km en mantenimientos completados", {
    "mantenimientos completados": len(mc),
    "VehicleCurrentKM nulo": int(vck.isna().sum()),
    "VehicleCurrentKM < 100 (inválido)": int((vck < KM_MIN_VALIDO).sum()),
    "VehicleCurrentKM == 1": int((vck == 1).sum()),
    "VehicleCurrentKM > 500.000": int((vck > 500_000).sum()),
    "VehicleCurrentKM > 1.000.000 (inválido)": int((vck > KM_MAX_VALIDO).sum()),
    "KM (snapshot) nulo": int(mc.KM.isna().sum()),
    "KM == 0": int((mc.KM == 0).sum()),
    "KM > 500.000": int((mc.KM > 500_000).sum()),
    "event_date < 2024-01-01 (check-in anómalo)": int((mc.event_date < START).sum()),
    "event_date > CUTOFF": int((mc.event_date > CUTOFF).sum()),
})

# --------------------------------------------------------------------------------------------------
# Base de mantenimientos completados (M): una fila por vehículo-día
# --------------------------------------------------------------------------------------------------
log("armando base M de mantenimientos completados")
M = mc[(mc.event_date >= START) & (mc.event_date <= CUTOFF)].copy()
M = M.sort_values(["vehicle_id", "event_date", "maint_number", "schedule_id"])
n_before = len(M)
M = M.drop_duplicates(["vehicle_id", "event_date"], keep="first")
n_dedup = n_before - len(M)
M["km_evento"] = M["VehicleCurrentKM"].where(M["VehicleCurrentKM"].between(KM_MIN_VALIDO, KM_MAX_VALIDO))
# WSD: agenda, con fallback a sales
M = M.join(sales_idx, on="vehicle_id")
M["in_sales"] = M["BusinessUnit"].notna()
M["WSD"] = M["WarrantyStartDate"].fillna(M["WSD_sales"])
M["edad_meses"] = (M["event_date"] - M["WSD"]).dt.days / MESES
M["edad_anios"] = (M["event_date"] - M["WSD"]).dt.days / 365.25
M["my_grp"] = my_group(M["ModelYear"])
M["PersonType"] = M["PersonType"].where(M["PersonType"].isin(["F", "J"]), "otro/s.d.")
# km previo / siguiente dentro del vehículo
g = M.groupby("vehicle_id")
M["prev_date"] = g["event_date"].shift(1)
M["prev_km"] = g["km_evento"].shift(1)
M["prev_n"] = g["maint_number"].shift(1)
M["orden"] = g.cumcount() + 1
M["n_veh"] = g["event_date"].transform("size")
M["d_dias"] = (M["event_date"] - M["prev_date"]).dt.days
M["d_km"] = M["km_evento"] - M["prev_km"]
log(f"M: {fmt(len(M))} eventos ({fmt(n_dedup)} duplicados vehículo-día colapsados), {fmt(M.vehicle_id.nunique())} vehículos")
add_kv("m0. Base M: mantenimientos completados usados en este EDA", {
    "turnos en agenda (schedule_id)": len(ap),
    "mantenimientos completados (is_completed_maintenance)": len(mc),
    "  con event_date fuera de [2024-01-01, CUTOFF]": int(len(mc) - ((mc.event_date >= START) & (mc.event_date <= CUTOFF)).sum()),
    "  filas colapsadas por repetirse vehículo + event_date": n_dedup,
    "eventos en M": len(M),
    "vehículos en M": int(M.vehicle_id.nunique()),
    "  de los cuales en sales": int(M.groupby("vehicle_id").in_sales.first().sum()),
    "eventos con km_evento válido (100 <= VehicleCurrentKM <= 1.000.000)": int(M.km_evento.notna().sum()),
    "eventos con WSD (agenda o sales)": int(M.WSD.notna().sum()),
})

wsd_veh = mc.groupby("vehicle_id")["WarrantyStartDate"].agg(["nunique", "first"]).join(sales_idx["WSD_sales"], how="inner")
wsd_ok = wsd_veh.dropna(subset=["first", "WSD_sales"])
add_kv("c5. WarrantyStartDate: consistencia dentro de la agenda y contra sales (vehículos con mantenimiento completado)", {
    "vehículos con mantenimiento completado": int(mc.vehicle_id.nunique()),
    "  con WarrantyStartDate nulo en todos sus turnos": int((mc.groupby("vehicle_id")["WarrantyStartDate"].count() == 0).sum()),
    "  con >1 WarrantyStartDate distinto en agenda": int((mc.groupby("vehicle_id")["WarrantyStartDate"].nunique() > 1).sum()),
    "vehículos también en sales (con WSD en ambas)": len(wsd_ok),
    "% WSD agenda == WSD sales": (100 * (wsd_ok["first"] == wsd_ok["WSD_sales"]).mean(), 1),
    "% |WSD agenda − WSD sales| > 30 días": (100 * ((wsd_ok["first"] - wsd_ok["WSD_sales"]).dt.days.abs() > 30).mean(), 2),
    "eventos de M con edad negativa (event_date < WSD)": int((M.edad_meses < 0).sum()),
    "eventos de M con WSD nulo": int(M.WSD.isna().sum()),
})
pairs = M.dropna(subset=["prev_date"]).copy()
add_kv("c4. Consistencia del odómetro entre mantenimientos consecutivos del mismo vehículo", {
    "pares consecutivos (mismo vehículo)": len(pairs),
    "pares con km_evento en ambos": int(pairs.d_km.notna().sum()),
    "d_km < 0 (odómetro decrece)": int((pairs.d_km < 0).sum()),
    "% d_km < 0": (100 * (pairs.d_km < 0).sum() / pairs.d_km.notna().sum(), 1),
    "d_km == 0 (mismo km repetido)": int((pairs.d_km == 0).sum()),
    "% d_km == 0": (100 * (pairs.d_km == 0).sum() / pairs.d_km.notna().sum(), 1),
    "d_dias < 30": int((pairs.d_dias < 30).sum()),
    "% d_dias < 30": (100 * (pairs.d_dias < 30).mean(), 1),
    "d_dias < 30 y d_km <= 0 (misma visita partida)": int(((pairs.d_dias < 30) & (pairs.d_km <= 0)).sum()),
    "d_km > 100.000 en un intervalo": int((pairs.d_km > 100_000).sum()),
})

# Figura c: nulos por estado + KM - VCK_last
fig, axes = plt.subplots(1, 2, figsize=(11, 3.8))
nul[["KM_nulo_pct", "VehicleCurrentKM_nulo_pct", "Checkin_nulo_pct"]].plot.bar(ax=axes[0], color=["#7f7f7f", "#1f5fa8", "#d9822b"])
axes[0].set_title("Nulos por estado del turno (%)")
axes[0].set_xlabel("StatusARG")
axes[0].set_ylabel("% nulo")
axes[0].legend(["KM", "VehicleCurrentKM", "EffectiveCheckinDate"], fontsize=8)
axes[0].tick_params(axis="x", rotation=30)
dif = (last_vck.KM - last_vck.VehicleCurrentKM).clip(-50_000, 50_000)
axes[1].hist(dif.dropna(), bins=100, color="#1f5fa8")
axes[1].set_yscale("log")
axes[1].set_title("KM (snapshot) − VehicleCurrentKM de la última visita (±50.000)")
axes[1].set_xlabel("diferencia en km")
axes[1].set_ylabel("vehículos (log)")
savefig("km_vs_vehiclecurrentkm")

# --------------------------------------------------------------------------------------------------
# d) Tasa de uso (km/año) por vehículo — se calcula antes de a) porque a) la usa para terciles
# --------------------------------------------------------------------------------------------------
log("d) tasa de uso")
lastM = M[M.km_evento.notna()].groupby("vehicle_id").tail(1).copy()
lastM = lastM[lastM.edad_anios >= 0.25]
lastM["rate_A"] = lastM.km_evento / lastM.edad_anios
rateA = lastM.set_index("vehicle_id")["rate_A"]
rateA_valid = rateA[rateA.between(RATE_MIN, RATE_MAX)]
# Método B: pendiente entre primera y última visita con km válido y monotónico, span >= 90 días
firstM = M[M.km_evento.notna()].groupby("vehicle_id").head(1).set_index("vehicle_id")
lastK = M[M.km_evento.notna()].groupby("vehicle_id").tail(1).set_index("vehicle_id")
span_d = (lastK.event_date - firstM.event_date).dt.days
span_km = lastK.km_evento - firstM.km_evento
rateB = (span_km / (span_d / 365.25))[(span_d >= 90) & (span_km > 0)]
rateB_valid = rateB[rateB.between(RATE_MIN, RATE_MAX)]
add_kv("d1. Cobertura de los dos métodos de tasa de uso", {
    "vehículos con tasa A (km_evento / años desde WSD, edad >= 3 meses)": len(rateA),
    "  de los cuales fuera de [2.000, 150.000] km/año": int((~rateA.between(RATE_MIN, RATE_MAX)).sum()),
    "vehículos con tasa B (pendiente 1ª→última visita, >= 90 días, km creciente)": len(rateB),
    "  de los cuales fuera de [2.000, 150.000] km/año": int((~rateB.between(RATE_MIN, RATE_MAX)).sum()),
})
add_table("d2. Distribución de la tasa de uso (km/año) por método",
          pct_table({"A: km acumulado / edad": rateA_valid, "B: pendiente entre visitas": rateB_valid}))
both = pd.concat([rateA_valid.rename("A"), rateB_valid.rename("B")], axis=1).dropna()
ratio = both.B / both.A
add_kv("d3. Concordancia entre métodos de tasa de uso", {
    "vehículos con ambos métodos": len(both),
    "correlación de Spearman A vs B": (both.corr(method="spearman").iloc[0, 1], 3),
    "mediana de B/A": (ratio.median(), 3),
    "p25 de B/A": (ratio.quantile(0.25), 3),
    "p75 de B/A": (ratio.quantile(0.75), 3),
    "% con |B/A − 1| <= 0,25": (100 * ((ratio - 1).abs() <= 0.25).mean(), 1),
    "mediana |B − A| (km/año)": (both.B - both.A).abs().median(),
})

# por generación y por PersonType / BusinessUnit (sales)
veh_attr = M.groupby("vehicle_id").agg(gen=("gen", "first"), BusinessUnit=("BusinessUnit", "first"),
                                        PersonType=("PersonType", "first"), in_sales=("in_sales", "first"),
                                        my_grp=("my_grp", "first"))
ra = veh_attr.join(rateA_valid.rename("rate")).dropna(subset=["rate"])
grp = {f"gen {k}": v.rate for k, v in ra.groupby("gen")}
grp.update({f"BU {k}": v.rate for k, v in ra[ra.in_sales].groupby("BusinessUnit")})
grp.update({f"PersonType {k}": v.rate for k, v in ra[ra.in_sales].groupby("PersonType")})
add_table("d4. Tasa de uso (método A, km/año) por generación y, para vehículos en sales, por BusinessUnit y PersonType",
          pct_table(grp))
terc_cut = rateA_valid.quantile([1 / 3, 2 / 3]).values
ra["tercil_uso"] = pd.cut(ra.rate, [-np.inf, terc_cut[0], terc_cut[1], np.inf],
                          labels=[f"bajo (<{fmt(terc_cut[0])})", f"medio", f"alto (>{fmt(terc_cut[1])})"]).astype("str")
log(f"terciles de uso: {terc_cut.round(0)}")

fig, axes = plt.subplots(1, 2, figsize=(11, 3.8))
axes[0].hist(rateA_valid.clip(0, 80_000), bins=80, color="#1f5fa8", alpha=0.7, label="A: km acumulado / edad")
axes[0].hist(rateB_valid.clip(0, 80_000), bins=80, color="#d9822b", alpha=0.5, label="B: pendiente entre visitas")
for t in terc_cut:
    axes[0].axvline(t, color="k", ls="--", lw=0.8)
axes[0].set_title("Tasa de uso por vehículo (km/año, recortado a 80.000)")
axes[0].set_xlabel("km/año")
axes[0].set_ylabel("vehículos")
axes[0].legend(fontsize=8)
smp = both.sample(min(20_000, len(both)), random_state=1)
axes[1].scatter(smp.A, smp.B, s=2, alpha=0.3, color="#1f5fa8")
axes[1].plot([0, 80_000], [0, 80_000], "k--", lw=0.8)
axes[1].set_xlim(0, 80_000)
axes[1].set_ylim(0, 80_000)
axes[1].set_title("Método A vs método B (muestra de 20.000 vehículos)")
axes[1].set_xlabel("A: km acumulado / edad (km/año)")
axes[1].set_ylabel("B: pendiente entre visitas (km/año)")
savefig("tasa_uso")

# --------------------------------------------------------------------------------------------------
# a) Intervalos entre mantenimientos consecutivos (días y km)
# --------------------------------------------------------------------------------------------------
log("a) intervalos entre mantenimientos consecutivos")
P = pairs.copy()
P = P.join(ra[["tercil_uso"]], on="vehicle_id")
P_km = P[(P.d_km > 0)]  # km válido y creciente
a_days = {"global": P.d_dias}
a_days.update({f"gen {k}": v.d_dias for k, v in P.groupby("gen")})
a_days.update({f"MY {k}": v.d_dias for k, v in P.groupby("my_grp")})
a_days.update({f"uso {k}": v.d_dias for k, v in P.dropna(subset=["tercil_uso"]).groupby("tercil_uso")})
a_days.update({f"BU {k}": v.d_dias for k, v in P[P.in_sales].groupby("BusinessUnit")})
a_days.update({f"PersonType {k}": v.d_dias for k, v in P[P.in_sales].groupby("PersonType")})
add_table("a1. Días entre mantenimientos completados consecutivos (vehículos con >= 2)", pct_table(a_days),
          note=f"Base: {fmt(len(P))} pares consecutivos de {fmt(P.vehicle_id.nunique())} vehículos. "
               f"Los grupos BU/PersonType usan solo vehículos presentes en sales (ventas 2024-2026, casi todos P703).")
a_km = {"global": P_km.d_km}
a_km.update({f"gen {k}": v.d_km for k, v in P_km.groupby("gen")})
a_km.update({f"MY {k}": v.d_km for k, v in P_km.groupby("my_grp")})
a_km.update({f"uso {k}": v.d_km for k, v in P_km.dropna(subset=["tercil_uso"]).groupby("tercil_uso")})
a_km.update({f"BU {k}": v.d_km for k, v in P_km[P_km.in_sales].groupby("BusinessUnit")})
a_km.update({f"PersonType {k}": v.d_km for k, v in P_km[P_km.in_sales].groupby("PersonType")})
add_table("a2. Km entre mantenimientos completados consecutivos (pares con odómetro válido y creciente)", pct_table(a_km),
          note=f"Base: {fmt(len(P_km))} pares (se excluyen {fmt(len(P) - len(P_km))} pares con km nulo, repetido o decreciente).")
# distribución de la cantidad de mantenimientos por vehículo
nv = M.groupby("vehicle_id").size()
a3 = nv.value_counts().sort_index().rename("vehículos").to_frame()
a3["%"] = 100 * a3["vehículos"] / a3["vehículos"].sum()
a3.index.name = "mantenimientos completados 2024-01→2026-08"
add_table("a3. Cantidad de mantenimientos completados por vehículo en el extracto", a3.head(12), dec={"%": 1})
# a4. Censura por la derecha: un par sólo existe si el siguiente mantenimiento ya ocurrió antes del CUTOFF, así que los
# intervalos largos están subrepresentados en a1. Se recalcula sobre anclas con 18 meses de seguimiento garantizado.
M["dias_next"] = (M.groupby("vehicle_id")["event_date"].shift(-1) - M["event_date"]).dt.days
M["fu_dias"] = (CUTOFF - M["event_date"]).dt.days
M["tercil_uso_veh"] = M.vehicle_id.map(ra["tercil_uso"])
A4 = M[M.fu_dias >= DIAS_18M]
rows = []
for name, sel_p, sel_a in [("global", P.index, A4.index), ("gen P703", P.index[P.gen == "P703"], A4.index[A4.gen == "P703"]),
                           ("gen P375", P.index[P.gen == "P375"], A4.index[A4.gen == "P375"])] + \
                          [(f"uso {t}", P.index[P.tercil_uso == t], A4.index[A4.tercil_uso_veh == t]) for t in sorted(ra.tercil_uso.unique())]:
    pn = P.loc[sel_p, "d_dias"]
    an = A4.loc[sel_a, "dias_next"]
    ret18 = an.le(DIAS_18M)
    rows.append({"grupo": name, "pares ingenuos": len(pn), "mediana ingenua (d)": pn.median(), "% > 365 d ingenuo": 100 * (pn > 365).mean(),
                 "anclas con 18 m de seguimiento": len(an), "% retorna en 18 m": 100 * ret18.mean(),
                 "mediana entre retornos en 18 m (d)": an[ret18].median(), "% > 365 d entre retornos en 18 m": 100 * (an[ret18] > 365).mean(),
                 "mediana incondicional (sin retorno = censurado)": an.fillna(10_000).median()})
add_table("a4. Días entre mantenimientos: pares ingenuos (a1) vs anclas con 18 meses de seguimiento garantizado (corrige la censura)",
          pd.DataFrame(rows), dec={"% > 365 d ingenuo": 1, "% retorna en 18 m": 1, "% > 365 d entre retornos en 18 m": 1}, index=False,
          note="La tabla a1 sólo ve intervalos que ya cerraron antes del CUTOFF (sesgo hacia intervalos cortos). Con seguimiento garantizado "
               "la mediana entre retornos sube poco, pero el 19 % que no vuelve en 18 meses no aparece en a1. 'Mediana incondicional' trata "
               "el no-retorno como un intervalo mayor a 548 d.")

fig, axes = plt.subplots(1, 2, figsize=(11, 3.8))
for gname, col in [("P703", PALETA["P703"]), ("P375", PALETA["P375"])]:
    s = P[P.gen == gname].d_dias.clip(0, 600)
    axes[0].hist(s, bins=60, alpha=0.6, color=col, label=f"{gname} (n={fmt(len(s))})".replace(",", "."), density=True)
    s = P_km[P_km.gen == gname].d_km.clip(0, 40_000)
    axes[1].hist(s, bins=80, alpha=0.6, color=col, label=f"{gname} (n={fmt(len(s))})".replace(",", "."), density=True)
axes[0].axvline(365, color="k", ls="--", lw=0.8)
axes[0].set_title("Días entre mantenimientos consecutivos (recortado a 600)")
axes[0].set_xlabel("días")
axes[0].set_ylabel("densidad")
axes[0].legend(fontsize=8)
for k in (10_000, 15_000):
    axes[1].axvline(k, color="k", ls="--", lw=0.8)
axes[1].set_title("Km entre mantenimientos consecutivos (recortado a 40.000)")
axes[1].set_xlabel("km")
axes[1].set_ylabel("densidad")
axes[1].legend(fontsize=8)
savefig("hist_intervalos")

# --------------------------------------------------------------------------------------------------
# b) maint_number x km al evento y x edad en meses: ¿10.000 o 15.000 km? ¿12 n meses?
# --------------------------------------------------------------------------------------------------
log("b) maint_number x km y x edad")
b0 = M.maint_number.value_counts(dropna=False).sort_index().rename("eventos").to_frame()
b0.index = b0.index.map(lambda v: "s/d" if pd.isna(v) else str(int(v)))
b0.index.name = "maint_number (ServiceMaintenance)"
add_table("b0. Distribución del número de service en los mantenimientos completados (base M)", b0.T, index=True,
          note="El salto de 19 a 20 sugiere que 20 funciona como tope ('20 o más').")
B = M[M.maint_number.between(1, 20) & M.gen.isin(["P703", "P375"])].copy()
B["km_por_n"] = B.km_evento / B.maint_number
B["meses_por_n"] = B.edad_meses / B.maint_number
rows = []
for gname, gb in B.groupby("gen"):
    for n, gn in gb.groupby("maint_number"):
        if n > 12:
            continue
        rows.append({"gen": gname, "n° service": int(n), "eventos": len(gn),
                     "km p25": gn.km_evento.quantile(0.25), "km mediana": gn.km_evento.median(), "km p75": gn.km_evento.quantile(0.75),
                     "km/n mediana": gn.km_por_n.median(),
                     "edad meses p25": gn.edad_meses.quantile(0.25), "edad meses mediana": gn.edad_meses.median(),
                     "edad meses p75": gn.edad_meses.quantile(0.75), "meses/n mediana": gn.meses_por_n.median()})
b1 = pd.DataFrame(rows)
add_table("b1. Km al evento y edad del vehículo por número de service (ServiceMaintenance) y generación",
          b1, dec={"edad meses p25": 1, "edad meses mediana": 1, "edad meses p75": 1, "meses/n mediana": 1}, index=False,
          note="`km/n` = km al evento dividido el número de service: si el plan fuera cada K km, converge a K. "
               "`meses/n` converge a 12 sólo si la regla de tiempo fuera la que manda. OJO: para P703 la edad está truncada por "
               f"construcción (el p1 de WSD es {M[M.gen == 'P703'].WSD.quantile(0.01).date()}, ningún P703 supera ~"
               f"{(CUTOFF - M[M.gen == 'P703'].WSD.quantile(0.01)).days / MESES:.0f} meses), así que a n alto sólo llegan los de uso "
               f"extremo (n = 10: tasa mediana {fmt(B[(B.gen == 'P703') & (B.maint_number == 10)].eval('km_evento / edad_anios').median())} km/año); "
               "`meses/n` para n >= 5 en P703 no es evidencia de nada. La evidencia limpia contra 12·n es n = 1 (8,4 meses) y Δdías n→n+1 (b2).")
# incremento entre services consecutivos en numeración (n -> n+1)
cons = P_km[(P_km.maint_number == P_km.prev_n + 1) & P_km.gen.isin(["P703", "P375"])]
b2 = {}
for gname, gb in cons.groupby("gen"):
    b2[f"{gname} Δkm (n→n+1)"] = gb.d_km
    b2[f"{gname} Δdías (n→n+1)"] = gb.d_dias
add_table("b2. Incremento de km y de días entre services con numeración consecutiva (n → n+1)", pct_table(b2),
          note=f"Base: {fmt(len(cons))} pares con numeración consecutiva ({100 * len(cons) / len(P_km):.1f}% de los pares con km válido).")
# distribución del km del 1° service en vehículos MY>=2024 (flota nueva)
s1 = B[(B.maint_number == 1) & (B.ModelYear >= 2024) & B.km_evento.notna()]
bins = [0, 5_000, 8_000, 10_000, 12_000, 15_000, 18_000, 20_000, 30_000, np.inf]
b3 = pd.cut(s1.km_evento, bins).value_counts(normalize=True).sort_index().rename("% de 1° services").to_frame() * 100
b3.index = b3.index.astype("str")
b3.index.name = "km al 1° service (MY >= 2024)"
add_table(f"b3. Km al 1° service en la flota nueva (ModelYear >= 2024, n={fmt(len(s1))})", b3, dec=1)
# salto de numeración: qué pasa con los pares no consecutivos
jump = P.maint_number - P.prev_n
b4 = jump.value_counts().sort_index().rename("pares").to_frame()
b4["%"] = 100 * b4.pares / b4.pares.sum()
b4 = b4[(b4.index >= -3) & (b4.index <= 5)]
b4.index = b4.index.map(lambda v: str(int(v)))
b4.loc["< -3"] = [int((jump < -3).sum()), 100 * (jump < -3).mean()]
b4.loc["> 5"] = [int((jump > 5).sum()), 100 * (jump > 5).mean()]
b4.loc["negativo (total)"] = [int((jump < 0).sum()), 100 * (jump < 0).mean()]
b4.loc[">= +2 (total)"] = [int((jump >= 2).sum()), 100 * (jump >= 2).mean()]
b4.index.name = "maint_number − maint_number previo"
add_table("b4. Salto de numeración entre mantenimientos consecutivos observados (distribución completa)", b4, dec={"%": 1},
          note="Un salto de +2 o más PUEDE significar que el service intermedio no está en el extracto (hecho fuera de la red, "
               "antes de 2024-01 o no registrado); 0 o negativo indica numeración inconsistente. Ver b5: sólo la mitad de los saltos +2 "
               "tiene un Δkm compatible con un intervalo doble.")
# b5. ¿El salto de numeración es un intervalo doble real? Δkm por salto, y 'doble' medido por km (Δkm >= 1,5 K) sin mirar la numeración.
Pj = P_km[P_km.gen.isin(["P703", "P375"])].assign(jump=jump)
rows = []
for gname, K in [("P703", 15_000), ("P375", 10_000)]:
    for j in [0, 1, 2, 3, 4]:
        s = Pj[(Pj.gen == gname) & (Pj.jump == j)]
        rows.append({"gen": gname, "salto": j, "pares": len(s), "Δkm p25": s.d_km.quantile(0.25), "Δkm mediana": s.d_km.median(),
                     "Δkm p75": s.d_km.quantile(0.75), "Δkm mediana / K": s.d_km.median() / K, "Δdías mediana": s.d_dias.median(),
                     "% Δkm en [1,5K, 2,5K]": 100 * s.d_km.between(1.5 * K, 2.5 * K).mean()})
    s = Pj[Pj.gen == gname]
    dbl, j2 = s.d_km >= 1.5 * K, s.jump >= 2
    rows.append({"gen": gname, "salto": "todos", "pares": len(s), "Δkm mediana": s.d_km.median(), "Δkm mediana / K": s.d_km.median() / K,
                 "Δdías mediana": s.d_dias.median(), "% Δkm >= 1,5K (doble por km)": 100 * dbl.mean(), "% salto >= +2": 100 * j2.mean(),
                 "% doble por km entre salto +1": 100 * dbl[s.jump == 1].mean(), "% doble por km entre salto >= +2": 100 * dbl[j2].mean()})
add_table("b5. Δkm según el salto de numeración, y 'intervalo doble' medido por km (Δkm >= 1,5·K_gen)", pd.DataFrame(rows),
          dec={"Δkm mediana / K": 2, "% Δkm en [1,5K, 2,5K]": 1, "% Δkm >= 1,5K (doble por km)": 1, "% salto >= +2": 1,
               "% doble por km entre salto +1": 1, "% doble por km entre salto >= +2": 1}, index=False,
          note="Si el salto +2 fuera siempre un service hecho afuera, Δkm mediana / K sería ≈ 2; es ≈ 1,6 y sólo ~46 % cae en [1,5K, 2,5K]: "
               "la mitad de los saltos es ruido de numeración. Medido por km, el intervalo doble es el 7,9 % de los pares P703 y el 18,5 % de P375.")

for var, fname, ylabel, ylim in [("km_evento", "box_km_por_service", "km al evento", 200_000),
                                 ("edad_meses", "box_edad_por_service", "edad del vehículo al evento (meses)", 120)]:
    fig, axes = plt.subplots(1, 2, figsize=(12, 4), sharey=True)
    for ax, gname in zip(axes, ["P703", "P375"]):
        sub = B[(B.gen == gname) & (B.maint_number <= 10)]
        data = [sub[sub.maint_number == n][var].dropna().values for n in range(1, 11)]
        ax.boxplot(data, whis=(5, 95), showfliers=False, positions=range(1, 11), widths=0.6,
                   patch_artist=True, boxprops=dict(facecolor=PALETA[gname], alpha=0.5), medianprops=dict(color="k"))
        K = 15_000 if gname == "P703" else 10_000
        if var == "km_evento":
            ax.plot(range(1, 11), [K * n for n in range(1, 11)], "k--", lw=0.9, label=f"{fmt(K)} km × n")
            ax.plot(range(1, 11), [10_000 * n if gname == "P703" else 15_000 * n for n in range(1, 11)], ":", color="gray", lw=0.9,
                    label=f"{fmt(10_000 if gname == 'P703' else 15_000)} km × n")
        else:
            ax.plot(range(1, 11), [12 * n for n in range(1, 11)], "k--", lw=0.9, label="12 meses × n")
        ax.set_ylim(0, ylim)
        ax.set_title(f"{gname}: {ylabel} por n° de service")
        ax.set_xlabel("n° de service (ServiceMaintenance)")
        ax.legend(fontsize=8, loc="upper left")
    axes[0].set_ylabel(ylabel)
    savefig(fname)

# --------------------------------------------------------------------------------------------------
# e) Cohorte de ventas 2024: tiempo al 1° mantenimiento y del 1° al 2°
# --------------------------------------------------------------------------------------------------
log("e) cohorte 2024")
coh = sales[(sales.WarrantyStartDate.dt.year == 2024)].copy()
firstM_all = M.groupby("vehicle_id").agg(first_date=("event_date", "first"), first_n=("maint_number", "first"),
                                          first_km=("km_evento", "first"))
secondM = M[M.orden == 2].set_index("vehicle_id")["event_date"].rename("second_date")
coh = coh.join(firstM_all, on="vehicle_id").join(secondM, on="vehicle_id")
coh["t1_meses"] = (coh.first_date - coh.WarrantyStartDate).dt.days / MESES
coh["t12_meses"] = (coh.second_date - coh.first_date).dt.days / MESES
coh["fu_meses"] = (CUTOFF - coh.WarrantyStartDate).dt.days / MESES
coh["fu1_meses"] = (CUTOFF - coh.first_date).dt.days / MESES
hor = [6, 9, 12, 15, 18]
rows = []
for h in hor:
    den = coh[coh.fu_meses >= h]
    rows.append({"horizonte (meses)": h, "vehículos con seguimiento >= h": len(den),
                 "% con 1° mantenimiento dentro de h": 100 * (den.t1_meses <= h).mean()})
e1 = pd.DataFrame(rows).set_index("horizonte (meses)")
add_table(f"e1. Cohorte WarrantyStartDate 2024 (n={fmt(len(coh))} vehículos en sales): % que completó el 1° mantenimiento "
          f"en la red dentro de h meses", e1, dec={"% con 1° mantenimiento dentro de h": 1},
          note=f"{fmt(int(coh.first_date.notna().sum()))} de {fmt(len(coh))} ({100 * coh.first_date.notna().mean():.1f}%) tienen al menos "
               f"un mantenimiento completado hasta el CUTOFF; seguimiento mínimo de la cohorte: {coh.fu_meses.min():.1f} meses. "
               f"El 1° evento observado está numerado como 1° service en el "
               f"{100 * (coh.first_n == 1).sum() / coh.first_date.notna().sum():.1f}% de los casos con evento "
               f"({100 * (coh.first_n == 2).sum() / coh.first_date.notna().sum():.1f}% como 2°, "
               f"{100 * (coh.first_n >= 3).sum() / coh.first_date.notna().sum():.1f}% como 3° o más); "
               f"{fmt(int((coh.t1_meses < 0).sum()))} vehículos tienen el 1° mantenimiento antes del WarrantyStartDate.")
rows = []
c1 = coh.dropna(subset=["first_date"])
for h in hor:
    den = c1[c1.fu1_meses >= h]
    rows.append({"horizonte (meses)": h, "vehículos con seguimiento >= h desde el 1°": len(den),
                 "% con 2° mantenimiento dentro de h": 100 * (den.t12_meses <= h).mean()})
e2 = pd.DataFrame(rows).set_index("horizonte (meses)")
add_table("e2. Misma cohorte: del 1° al 2° mantenimiento completado", e2, dec={"% con 2° mantenimiento dentro de h": 1},
          note=f"SESGO DE SELECCIÓN: sólo tienen h meses de seguimiento tras el 1° los que hicieron el 1° temprano. El subconjunto con "
               f">= 18 m tiene t1 mediana {c1[c1.fu1_meses >= 18].t1_meses.median():.1f} meses vs {c1.t1_meses.median():.1f} en todos los que "
               f"hicieron el 1°; ver e4. La comparación limpia WSD→1° vs 1°→2° es a 12 meses (mismo horizonte, denominador casi completo).")
# e4. ¿cuánto pesa la selección? retorno al 2° (12 m) según cuánto tardó el 1°
c12 = c1[c1.fu1_meses >= 12].copy()
c12["t1_bucket"] = pd.cut(c12.t1_meses, [-1, 4, 6, 8, 10, 12, 15, 30], labels=["<= 4", "4-6", "6-8", "8-10", "10-12", "12-15", "> 15"])
rows = []
for b, s in c12.groupby("t1_bucket", observed=True):
    rows.append({"meses WSD → 1° (bucket)": str(b), "n (seguimiento >= 12 m tras el 1°)": len(s),
                 "% con 2° dentro de 12 m": 100 * (s.t12_meses <= 12).mean(), "% que además tiene seguimiento >= 18 m": 100 * (s.fu1_meses >= 18).mean()})
add_table("e4. Cohorte 2024: retorno al 2° mantenimiento (12 m) según cuánto tardó el 1°", pd.DataFrame(rows),
          dec={"% con 2° dentro de 12 m": 1, "% que además tiene seguimiento >= 18 m": 1}, index=False,
          note="El retraso del 1° service predice fuerte el retorno al 2° (91 % si el 1° fue a <= 4 meses, 47 % si fue a 12-15). "
               "Es una feature ('retraso del service anterior'), y explica por qué el 91,5 % a 18 m de e2 está inflado.")
add_table("e3. Cohorte 2024: percentiles del tiempo (meses) WSD→1° y 1°→2°, y km al 1° service",
          pct_table({"meses WSD → 1°": coh.t1_meses[coh.t1_meses >= 0],
                     "meses 1° → 2° (seguimiento >= 18 m)": c1[c1.fu1_meses >= 18].t12_meses,
                     "km al 1° mantenimiento": coh.first_km}, dec=1), dec={"n": 0, **{q: 1 for q in QNAMES}, "media": 1})

fig, ax = plt.subplots(figsize=(7.5, 4))
xs = np.arange(0, 24.1, 0.25)
den = coh[coh.fu_meses >= 20]
ax.plot(xs, [100 * (den.t1_meses <= x).mean() for x in xs], color="#1f5fa8", label=f"WSD → 1° mantenimiento (n={fmt(len(den))})".replace(",", "."))
den2 = c1[c1.fu1_meses >= 18]
ax.plot(xs, [100 * (den2.t12_meses <= x).mean() for x in xs], color="#d9822b", label=f"1° → 2° mantenimiento (n={fmt(len(den2))}, seg. ≥ 18 m)".replace(",", "."))
for h in (6, 12, 18):
    ax.axvline(h, color="k", ls=":", lw=0.7)
ax.set_xlabel("meses desde el ancla")
ax.set_ylabel("% acumulado que completó el mantenimiento")
ax.set_title("Cohorte de ventas con WarrantyStartDate en 2024: curvas acumuladas")
ax.set_ylim(0, 100)
ax.legend(fontsize=8, loc="lower right")
savefig("cohorte2024_curvas")

# --------------------------------------------------------------------------------------------------
# f) Propuesta empírica de ventana: due_date y retraso real
# --------------------------------------------------------------------------------------------------
log("f) ventana empírica")
CICLO_DIAS = 365
rate_pop = ra.groupby("gen").rate.median()  # tasa poblacional por generación (fallback / cold start)
log(f"tasa mediana por generación: {rate_pop.round(0).to_dict()}")

W = M[M.gen.isin(["P703", "P375"])].copy()
W["next_date"] = W.groupby("vehicle_id")["event_date"].shift(-1)
W = W[W.event_date + pd.Timedelta(days=DIAS_18M) <= CUTOFF].copy()  # seguimiento completo de 18 meses
W["rate_i"] = (W.km_evento / W.edad_anios).where((W.edad_anios >= 0.25) & W.km_evento.notna())
W["rate_i"] = W["rate_i"].where(W.rate_i.between(RATE_MIN, RATE_MAX))
W["rate_fallback"] = W.rate_i.isna()
W["rate_i"] = W.rate_i.fillna(W.gen.map(rate_pop))
# tasa reciente: pendiente del último intervalo (si hay visita previa con km válido y >= 30 días); si no, tasa acumulada
W["rate_rec"] = (W.d_km / (W.d_dias / 365.25)).where((W.d_dias >= 30) & (W.d_km > 0))
W["rate_rec"] = W.rate_rec.where(W.rate_rec.between(RATE_MIN, RATE_MAX)).fillna(W.rate_i)
W["tiene_rate_rec"] = (W.d_dias >= 30) & (W.d_km > 0)
W["dias_a_retorno"] = (W.next_date - W.event_date).dt.days
W["retorna_18m"] = W.dias_a_retorno.le(DIAS_18M)


def due_dias(df: pd.DataFrame, K, ciclo: int = CICLO_DIAS, rate_col: str = "rate_i") -> pd.Series:
    """Días desde el ancla hasta due_date. K=None -> sólo tiempo. K='gen' -> 15k P703 / 10k P375."""
    if K is None:
        return pd.Series(float(ciclo), index=df.index)
    Kv = df.gen.map({"P703": 15_000, "P375": 10_000}) if K == "gen" else float(K)
    dias_km = Kv / df[rate_col] * 365.25
    return np.minimum(dias_km, ciclo)


REGLAS = {"sólo tiempo (365 d)": (None, "rate_i"), "K = 10.000": (10_000, "rate_i"), "K = 15.000": (15_000, "rate_i"),
          "K por generación (15k P703 / 10k P375)": ("gen", "rate_i"),
          "K por generación, tasa reciente": ("gen", "rate_rec")}
RECOMENDADA = "K por generación (15k P703 / 10k P375)"
HORIZ = [0, 30, 60, 90, 120, 150, 180]
APERT = -30
f1_rows, f2_rows, delays = [], [], {}
for rname, (K, rcol) in REGLAS.items():
    dd = due_dias(W, K, rate_col=rcol)
    delay = W.dias_a_retorno - dd  # retraso real (días) respecto del due
    binds_time = (dd >= CICLO_DIAS - 1e-9)
    ret = W.retorna_18m
    dl = delay[ret]
    delays[rname] = dl
    f1_rows.append({"regla": rname, "ventanas": len(W), "% retorna en 18 m": 100 * ret.mean(),
                    "% ventanas donde manda el tope de 365 d": 100 * binds_time.mean(),
                    "due mediana (días desde ancla)": dd.median(),
                    **{q: dl.quantile(qq) for q, qq in zip(QNAMES, Q)},
                    "% retornos antes de due-30": 100 * (dl < -30).mean(),
                    "% retornos antes de due-60": 100 * (dl < -60).mean(),
                    "% retornos antes de due-90": 100 * (dl < -90).mean()})
    for h in HORIZ:
        abiertas = ~(delay < APERT)  # no volvió antes de la apertura (o no volvió nunca)
        churn_h = ~(delay <= h)  # no volvió hasta due+h (incluye no retorno)
        f2_rows.append({"regla": rname, "horizonte H (días tras due)": h,
                        "% retornos (18 m) capturados hasta due+H": 100 * (dl <= h).mean(),
                        "% churn incondicional (no volvió hasta due+H)": 100 * churn_h.mean(),
                        f"% churn entre ventanas abiertas en due{APERT:+d}": 100 * churn_h[abiertas].mean(),
                        "ventanas abiertas": int(abiertas.sum())})
f1 = pd.DataFrame(f1_rows).set_index("regla")
add_table(f"f1. Retraso real (días) del siguiente mantenimiento respecto del due_date, por regla (ventanas ancladas en "
          f"mantenimientos completados con 18 meses de seguimiento, n={fmt(len(W))}; retornos dentro de 18 m)",
          f1, dec={c: 1 for c in f1.columns if c.startswith("%")},
          note=f"due_date = ancla + min(365 d, K / tasa_i × 365,25); tasa_i = km al evento / edad del vehículo en el ancla "
               f"(sin información posterior al ancla); fallback a la mediana de la generación en el "
               f"{100 * W.rate_fallback.mean():.1f}% de las ventanas. La variante 'tasa reciente' usa la pendiente del último "
               f"intervalo (disponible en el {100 * W.tiene_rate_rec.mean():.1f}% de las ventanas; si no, la acumulada). "
               f"Retraso negativo = volvió antes del due.")
f2 = pd.DataFrame(f2_rows)
add_table("f2. Sensibilidad al horizonte H: % de retornos capturados y prevalencia de churn resultante, por regla", f2,
          dec={c: 1 for c in f2.columns if c.startswith("%")}, index=False)
# f3: por generación con la regla recomendada
dd = due_dias(W, "gen")
delay = W.dias_a_retorno - dd
rows = []
for gname, idx in W.groupby("gen").groups.items():
    dl = delay.loc[idx][W.retorna_18m.loc[idx]]
    ab = ~(delay.loc[idx] < APERT)
    r = {"gen": gname, "ventanas": len(idx), "% retorna en 18 m": 100 * W.retorna_18m.loc[idx].mean(),
         "% manda tope 365 d": 100 * (dd.loc[idx] >= CICLO_DIAS - 1e-9).mean(), "due mediana (días)": dd.loc[idx].median(),
         **{q: dl.quantile(qq) for q, qq in zip(QNAMES, Q)}}
    for h in (60, 90, 120):
        r[f"% capturado H={h}"] = 100 * (dl <= h).mean()
        r[f"% churn abiertas H={h}"] = 100 * (~(delay.loc[idx] <= h))[ab].mean()
    rows.append(r)
f3 = pd.DataFrame(rows).set_index("gen")
add_table("f3. Regla 'K por generación': retraso y sensibilidad por generación", f3,
          dec={c: 1 for c in f3.columns if c.startswith("%")})
# f4: primer service (cold start) en la cohorte de ventas 2024: ancla WSD, km 0, tasa poblacional P703
c0 = coh[coh.fu_meses >= 18].copy()
c0["dias_a_1"] = (c0.first_date - c0.WarrantyStartDate).dt.days
c0 = c0[c0.dias_a_1.isna() | (c0.dias_a_1 >= 0)]
c0["ret18"] = c0.dias_a_1.le(DIAS_18M)
rate_seg = ra[ra.in_sales].groupby(["BusinessUnit", "PersonType"]).rate.median()
c0["rate_seg"] = [rate_seg.get((b, t), rate_pop["P703"]) for b, t in zip(c0.BusinessUnit, c0.PersonType.where(c0.PersonType.isin(["F", "J"]), "otro/s.d."))]
c0["dd_seg"] = np.minimum(365.0, 15_000 / c0.rate_seg * 365.25)
add_table("f4a. Tasa de uso mediana (km/año) por segmento BusinessUnit × PersonType usada para el arranque en frío",
          rate_seg.rename("km/año").to_frame())
rows = []
for rname, dd0 in {"sólo tiempo (365 d)": 365.0, "K = 15.000 con tasa poblacional P703": min(365.0, 15_000 / rate_pop["P703"] * 365.25),
                   "K = 10.000 con tasa poblacional P703": min(365.0, 10_000 / rate_pop["P703"] * 365.25),
                   "K = 15.000 con tasa por segmento BU × PersonType": c0.dd_seg}.items():
    dl_all = c0.dias_a_1 - dd0
    dl = dl_all[c0.ret18]
    ab = ~(dl_all < APERT)
    if not np.isscalar(dd0):
        dd0 = float(dd0.median())
    r = {"regla (1° service, ancla WSD)": rname, "due (días desde WSD, mediana)": dd0, "ventanas": len(c0),
         "% retorna en 18 m": 100 * c0.ret18.mean(), **{q: dl.quantile(qq) for q, qq in zip(QNAMES, Q)}}
    for h in (60, 90, 120, 180):
        r[f"% capturado H={h}"] = 100 * (dl <= h).mean()
        r[f"% churn abiertas H={h}"] = 100 * (~(dl_all <= h))[ab].mean()
    rows.append(r)
f4 = pd.DataFrame(rows).set_index("regla (1° service, ancla WSD)")
add_table("f4. Primer service (arranque en frío): cohorte ventas 2024 anclada en WarrantyStartDate", f4,
          dec={c: 1 for c in f4.columns if c.startswith("%")},
          note="Sin km previo no hay tasa individual: el due se calcula con la tasa mediana poblacional de P703 o, en la última fila, "
               "con la mediana del segmento BusinessUnit × PersonType del vehículo (tabla f4a).")
# f5: retraso por tercil de uso con la regla recomendada (¿la tasa individual centra bien?)
Wt = W.join(ra[["tercil_uso"]], on="vehicle_id")
rows = []
for t, idx in Wt.dropna(subset=["tercil_uso"]).groupby("tercil_uso").groups.items():
    dl = delay.loc[idx][W.retorna_18m.loc[idx]]
    rows.append({"tercil de uso": t, "ventanas": len(idx), "% retorna en 18 m": 100 * W.retorna_18m.loc[idx].mean(),
                 **{q: dl.quantile(qq) for q, qq in zip(QNAMES, Q)}})
add_table("f5. Regla 'K por generación': retraso por tercil de tasa de uso", pd.DataFrame(rows).set_index("tercil de uso"),
          dec={"% retorna en 18 m": 1})

rows = []
for rname in (RECOMENDADA, "K por generación, tasa reciente"):
    K, rcol = REGLAS[rname]
    dd = due_dias(W, K, rate_col=rcol)
    delay = W.dias_a_retorno - dd
    ret = W.retorna_18m
    for A in (-90, -60, -30, 0):
        for H in (60, 90, 120):
            abiertas = ~(delay < A)
            dentro = (delay >= A) & (delay <= H)
            rows.append({"regla": rname, "apertura (días vs due)": A, "horizonte H": H, "largo ventana (días)": H - A,
                         "% ventanas abiertas": 100 * abiertas.mean(),
                         "% retornos (18 m) dentro de [apertura, due+H]": 100 * dentro[ret].mean(),
                         "% retornos antes de la apertura": 100 * (delay[ret] < A).mean(),
                         "% churn entre abiertas (no vuelve hasta due+H)": 100 * (~(delay <= H))[abiertas].mean()})
f6 = pd.DataFrame(rows)
add_table("f6. Grilla apertura × horizonte: cobertura de retornos y prevalencia de churn entre ventanas abiertas", f6,
          dec={c: 1 for c in f6.columns if c.startswith("%")}, index=False,
          note="Una ventana está 'abierta' si el vehículo no volvió antes de la apertura (o no volvió nunca en 18 m). "
               "'Churn entre abiertas' es la prevalencia del target que vería el modelo al abrir la ventana.")
dd = due_dias(W, "gen")
delay = W.dias_a_retorno - dd
# f7. Tasa reciente vs acumulada SIN diluir: sólo en las ventanas donde la reciente existe (en f1 la reciente cae a la
# acumulada en el 63 % de las ventanas, así que la comparación de f1 subestima cualquier diferencia).
Ws = W[W.tiene_rate_rec & W.rate_rec.notna()]
rows = []
for name, rcol in [("acumulada (km al ancla / edad)", "rate_i"), ("reciente (pendiente del último intervalo)", "rate_rec")]:
    dds = due_dias(Ws, "gen", rate_col=rcol)
    dls = Ws.dias_a_retorno - dds
    dlr = dls[Ws.retorna_18m]
    ab = ~(dls < APERT)
    rows.append({"tasa": name, "ventanas (sólo con tasa reciente)": len(Ws), "p10": dlr.quantile(0.1), "p50": dlr.median(), "p90": dlr.quantile(0.9),
                 "mediana |retraso| (d)": dlr.abs().median(), "% |retraso| <= 30 d": 100 * (dlr.abs() <= 30).mean(),
                 "% |retraso| <= 60 d": 100 * (dlr.abs() <= 60).mean(), "% ventanas abiertas en due-30": 100 * ab.mean(),
                 "% retornos antes de due-30": 100 * (dlr < APERT).mean(), "% capturado hasta due+90": 100 * (dlr <= 90).mean(),
                 "% churn abiertas H=90": 100 * (~(dls <= 90))[ab].mean()})
add_table("f7. Tasa reciente vs acumulada comparadas sólo en las ventanas donde la reciente existe (comparación no diluida)",
          pd.DataFrame(rows), dec={c: 1 for c in ["% |retraso| <= 30 d", "% |retraso| <= 60 d", "% ventanas abiertas en due-30",
                                                  "% retornos antes de due-30", "% capturado hasta due+90", "% churn abiertas H=90"]}, index=False,
          note="Este subconjunto (vehículos con >= 2 visitas con km) está sesgado hacia los de más uso; por eso el retraso es más angosto que en f1. "
               "La conclusión es la misma: la tasa reciente no centra ni angosta mejor que la acumulada.")
# f8. La prevalencia de f2/f6 sale de anclas 2024-01→2025-02, con 75 % de P375; la población de 2026 es 70 % P703.
mix26 = M[M.event_date >= "2026-01-01"].gen.value_counts(normalize=True)
prev_gen = {gname: 100 * (~(delay.loc[idx] <= 90))[~(delay.loc[idx] < APERT)].mean() for gname, idx in W.groupby("gen").groups.items()}
add_kv("f8. Prevalencia de churn entre abiertas (apertura due-30, H=90) reponderada a la mezcla de generaciones de 2026", {
    "% P703 entre las ventanas evaluadas (anclas 2024-01→2025-02)": (100 * (W.gen == "P703").mean(), 1),
    "% P703 entre los mantenimientos de 2026-01→08": (100 * mix26.get("P703", 0), 1),
    "prevalencia observada (mezcla de las ventanas evaluadas)": (100 * (~(delay <= 90))[~(delay < APERT)].mean(), 1),
    "prevalencia P703": (prev_gen["P703"], 1),
    "prevalencia P375": (prev_gen["P375"], 1),
    "prevalencia reponderada a la mezcla de 2026": (mix26.get("P703", 0) * prev_gen["P703"] + mix26.get("P375", 0) * prev_gen["P375"], 1),
})

fig, axes = plt.subplots(1, 2, figsize=(12, 4))
xs = np.arange(-365, 200, 1)
for (rname, dl), col in zip(delays.items(), ["#7f7f7f", "#d9822b", "#2ca02c", "#1f5fa8", "#9467bd"]):
    axes[0].plot(xs, [100 * (dl <= x).mean() for x in xs], label=rname, color=col)
axes[0].axvline(0, color="k", lw=0.8)
axes[0].axvspan(APERT, 90, color="#1f5fa8", alpha=0.08)
axes[0].set_title("Retraso del siguiente mantenimiento respecto del due_date (ECDF, retornos en 18 m)")
axes[0].set_xlabel("días respecto del due_date (negativo = antes)")
axes[0].set_ylabel("% acumulado de retornos")
axes[0].legend(fontsize=7, loc="upper left")
for (rname, sub), col in zip(f2.groupby("regla", sort=False), ["#7f7f7f", "#d9822b", "#2ca02c", "#1f5fa8", "#9467bd"]):
    axes[1].plot(sub["horizonte H (días tras due)"], sub["% retornos (18 m) capturados hasta due+H"], "-o", ms=3, color=col, label=f"{rname}: capturado")
    axes[1].plot(sub["horizonte H (días tras due)"], sub[f"% churn entre ventanas abiertas en due{APERT:+d}"], "--s", ms=3, color=col, label=f"{rname}: churn (abiertas)")
axes[1].set_title(f"Sensibilidad al horizonte H (apertura en due{APERT:+d} d)")
axes[1].set_xlabel("H: días después del due_date")
axes[1].set_ylabel("%")
axes[1].set_ylim(0, 100)
axes[1].legend(fontsize=6, ncol=2, loc="lower right")
savefig("ventana_retraso_sensibilidad")

# --------------------------------------------------------------------------------------------------
# g) Estacionalidad
# --------------------------------------------------------------------------------------------------
log("g) estacionalidad")
M["mes"] = M.event_date.dt.to_period("M")
mensual = M.groupby("mes").size().rename("mantenimientos").to_frame()
mensual["P703"] = M[M.gen == "P703"].groupby("mes").size()
mensual["P375"] = M[M.gen == "P375"].groupby("mes").size()
mensual["dias_habiles"] = [np.busday_count(p.start_time.date(), (p.end_time + pd.Timedelta(days=1)).date()) for p in mensual.index]
# agosto 2026 está incompleto (hasta el 25): días hábiles hasta el CUTOFF
mensual.loc[pd.Period("2026-08", "M"), "dias_habiles"] = np.busday_count(pd.Timestamp("2026-08-01").date(), (CUTOFF + pd.Timedelta(days=1)).date())
mensual["por_dia_habil"] = mensual.mantenimientos / mensual.dias_habiles
mensual.index = mensual.index.astype("str")
add_table("g1. Volumen mensual de mantenimientos completados (2024-01 → 2026-08; agosto 2026 hasta el 25)", mensual,
          dec={"por_dia_habil": 1})
idx = M[M.event_date.dt.year.isin([2024, 2025])].copy()
idx["anio"] = idx.event_date.dt.year
idx["mes_num"] = idx.event_date.dt.month
tab = idx.groupby(["anio", "mes_num"]).size().unstack("anio")
tab = tab.join(mensual.set_index(pd.Index([pd.Period(m, "M") for m in mensual.index]))["dias_habiles"].rename("dh").to_frame().assign(
    anio=lambda d: [p.year for p in d.index], mes_num=lambda d: [p.month for p in d.index]).pivot(index="mes_num", columns="anio", values="dh")[[2024, 2025]].rename(columns={2024: "dh2024", 2025: "dh2025"}))
g2 = pd.DataFrame({"2024": tab[2024], "2025": tab[2025]})
g2["índice 2024 (media=100)"] = 100 * tab[2024] / tab[2024].mean()
g2["índice 2025 (media=100)"] = 100 * tab[2025] / tab[2025].mean()
g2["índice medio"] = (g2["índice 2024 (media=100)"] + g2["índice 2025 (media=100)"]) / 2
pdh = pd.DataFrame({2024: tab[2024] / tab["dh2024"], 2025: tab[2025] / tab["dh2025"]})
g2["índice medio por día hábil"] = 100 * ((pdh[2024] / pdh[2024].mean()) + (pdh[2025] / pdh[2025].mean())) / 2
# Índice con la tendencia removida: el volumen crece ~1,3 % mensual, así que un índice "media anual = 100" infla jul-dic y
# deprime ene-jun. Regresión log(mantenimientos / día hábil) = a + b·t + efecto_mes sobre los 31 meses completos (2024-01→2026-07).
full = mensual[mensual.index < "2026-08"].copy()
full["t"] = np.arange(len(full))
full["m"] = [int(s[5:7]) for s in full.index]
yv = np.log(full.mantenimientos / full.dias_habiles).values
Xv = np.column_stack([np.ones(len(full)), full.t.values] + [(full.m.values == k).astype(float) for k in range(2, 13)])
beta, *_ = np.linalg.lstsq(Xv, yv, rcond=None)
seas = np.r_[0.0, beta[2:]]
g2["índice sin tendencia (regresión, por día hábil, 2024-01→2026-07)"] = 100 * np.exp(seas - seas.mean())
resid = pd.DataFrame({"anio": [int(s[:4]) for s in full.index], "mes": full.m.values, "r": 100 * (yv - Xv @ beta)}).pivot(index="mes", columns="anio", values="r")
g2 = g2.join(resid.rename(columns=lambda c: f"residuo % {c}"))
g2.index.name = "mes del año"
add_table("g2. Índice estacional por mes del año: crudo (2024 y 2025) y con la tendencia removida (2024-01→2026-07)", g2,
          dec={c: 1 for c in g2.columns if "índice" in c or "residuo" in c},
          note=f"Tendencia estimada: {100 * (np.exp(beta[1]) - 1):.2f} % mensual por día hábil (≈ {100 * (np.exp(12 * beta[1]) - 1):.0f} % anual). "
               "El índice crudo mezcla tendencia y estacionalidad; el de regresión es el que hay que leer. Los residuos por año dicen si el "
               "efecto de un mes es sistemático (mismo signo todos los años) o de un solo año.")

fig, axes = plt.subplots(1, 2, figsize=(12, 4))
x = pd.PeriodIndex(mensual.index, freq="M").to_timestamp()
axes[0].plot(x, mensual.mantenimientos, "-o", ms=3, color="k", label="total")
axes[0].plot(x, mensual.P703, "-", color=PALETA["P703"], label="P703")
axes[0].plot(x, mensual.P375, "-", color=PALETA["P375"], label="P375")
axes[0].set_title("Mantenimientos completados por mes (2024-01 → 2026-08, agosto parcial)")
axes[0].set_ylabel("turnos")
axes[0].legend(fontsize=8)
axes[1].bar(np.arange(1, 13) - 0.27, g2["índice medio"], width=0.27, color="#9fb5cf", label="crudo (2024-25, media anual = 100)")
axes[1].bar(np.arange(1, 13), g2["índice medio por día hábil"], width=0.27, color="#d9822b", label="crudo por día hábil")
axes[1].bar(np.arange(1, 13) + 0.27, g2["índice sin tendencia (regresión, por día hábil, 2024-01→2026-07)"], width=0.27, color="#1f5fa8",
            label="sin tendencia (regresión, por día hábil)")
axes[1].axhline(100, color="k", lw=0.8)
axes[1].set_ylim(70, 125)
axes[1].set_xticks(range(1, 13))
axes[1].set_xticklabels(["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"])
axes[1].set_title("Índice estacional por mes del año (media = 100): el crudo mezcla tendencia")
axes[1].set_ylabel("índice")
axes[1].legend(fontsize=8)
savefig("estacionalidad")

# --------------------------------------------------------------------------------------------------
# Resumen de parámetros recomendados (números que se citan en el informe)
# --------------------------------------------------------------------------------------------------
add_kv("r1. Resumen de parámetros empíricos", {
    "K P703 (km entre services, mediana Δkm n→n+1)": cons[cons.gen == "P703"].d_km.median(),
    "K P375 (km entre services, mediana Δkm n→n+1)": cons[cons.gen == "P375"].d_km.median(),
    "días entre services mediana P703": P[P.gen == "P703"].d_dias.median(),
    "días entre services mediana P375": P[P.gen == "P375"].d_dias.median(),
    "% pares con > 365 días entre services (ingenuo, censurado)": (100 * (P.d_dias > 365).mean(), 1),
    "% > 365 días entre retornos en 18 m (anclas con seguimiento garantizado)": (100 * (A4.dias_next[A4.dias_next.le(DIAS_18M)] > 365).mean(), 1),
    "% anclas sin retorno en 18 m": (100 * A4.dias_next.gt(DIAS_18M).mean() + 100 * A4.dias_next.isna().mean(), 1),
    "mediana días entre services, incondicional (anclas con seguimiento)": A4.dias_next.fillna(10_000).median(),
    "tasa de uso mediana (km/año, método A)": rateA_valid.median(),
    "tasa de uso mediana P703": rate_pop.get("P703", np.nan),
    "tasa de uso mediana P375": rate_pop.get("P375", np.nan),
    "regla K por generación: retraso p10 (días)": delays[RECOMENDADA].quantile(0.10),
    "regla K por generación: retraso p50 (días)": delays[RECOMENDADA].quantile(0.50),
    "regla K por generación: retraso p90 (días)": delays[RECOMENDADA].quantile(0.90),
    "regla sólo tiempo: retraso p50 (días)": delays["sólo tiempo (365 d)"].quantile(0.50),
})

TABLES_MD.write_text(
    f"# Tablas generadas por `scripts/eda/{PREFIX}.py`\n\n"
    f"Generado automáticamente. CUTOFF = {CUTOFF.date()}. No editar a mano: el informe "
    f"`{PREFIX}.md` cita estos números.\n\n" + "\n".join(_md_parts), encoding="utf-8")
log(f"tablas -> {TABLES_MD.relative_to(config.PROJECT_DIR)}")
log("listo")
