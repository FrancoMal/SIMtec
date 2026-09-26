"""EDA 06 — Señales de canal, dealer, conectividad y experiencia como candidatas a features.

Genera:
- reports/eda/06_canal_dealer_experiencia_tablas.md  (apéndice con TODAS las tablas citadas en el informe)
- reports/figures/eda/06_canal_dealer_experiencia_*.png

Etiqueta APROXIMADA de retorno (solo para análisis univariante; el target definitivo lo fija otro tema):
    base    = turnos con is_completed_maintenance y event_date en [2024-01-01, 2025-05-31]
    retorno = el mismo vehículo completó otro mantenimiento programado con event_date estrictamente posterior
              y dentro de los 15 meses siguientes (horizonte observable hasta CUTOFF = 2026-08-25).

Ejecutar desde la carpeta del proyecto:
    PYTHONIOENCODING=utf8 PYTHONPATH=src .venv/Scripts/python.exe scripts/eda/06_canal_dealer_experiencia.py
"""
from __future__ import annotations

import warnings

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from scipy import stats  # noqa: E402
from sklearn.linear_model import LogisticRegression  # noqa: E402

from repurchase import config  # noqa: E402
from repurchase.eventos import CUTOFF, appointments  # noqa: E402
from repurchase.io import load_agenda  # noqa: E402

warnings.filterwarnings("ignore", category=FutureWarning)

PREFIX = "06_canal_dealer_experiencia"
FIG_DIR = config.FIGURES_DIR / "eda"
FIG_DIR.mkdir(parents=True, exist_ok=True)
TAB_PATH = config.REPORTS_DIR / "eda" / f"{PREFIX}_tablas.md"
TAB_PATH.parent.mkdir(parents=True, exist_ok=True)

BASE_START = pd.Timestamp("2024-01-01")
BASE_END = pd.Timestamp("2025-05-31")
HORIZON = pd.DateOffset(months=15)
MIN_N_BIN = 300  # n mínimo de un bin para reportar su tasa en el ranking

# Paleta (referencia validada del skill dataviz; orden fijo, nunca ciclado)
C = {
    "blue": "#2a78d6", "orange": "#eb6834", "aqua": "#1baf7a", "yellow": "#eda100",
    "magenta": "#e87ba4", "green": "#008300", "violet": "#4a3aa7", "red": "#e34948",
    "gray": "#8f8e8a", "grid": "#e6e5e1", "ink": "#0b0b0b", "ink2": "#52514e",
}
SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
plt.rcParams.update({
    "figure.dpi": 130, "savefig.dpi": 130, "font.size": 9, "axes.titlesize": 10, "axes.labelsize": 9,
    "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": C["ink2"],
    "axes.grid": True, "grid.color": C["grid"], "grid.linewidth": 0.8, "axes.axisbelow": True,
    "legend.frameon": False, "figure.facecolor": "white",
})


# ----------------------------------------------------------------------------------------------------
# Utilidades de reporte
# ----------------------------------------------------------------------------------------------------
class Report:
    def __init__(self):
        self.parts: list[str] = []

    def h(self, text: str, level: int = 2):
        self.parts.append(f"\n{'#' * level} {text}\n")

    def p(self, text: str):
        self.parts.append(text + "\n")

    def table(self, df: pd.DataFrame, title: str | None = None, index: bool = True):
        if title:
            self.parts.append(f"\n**{title}**\n")
        self.parts.append(md_table(df, index=index) + "\n")

    def write(self, path):
        head = (f"# Apéndice de tablas — EDA 06 (canal, dealer, conectividad y experiencia)\n\n"
                f"Generado automáticamente por `scripts/eda/{PREFIX}.py`. Todas las cifras del informe "
                f"`reports/eda/{PREFIX}.md` salen de acá. Decimales con coma; n con punto de miles.\n")
        path.write_text(head + "".join(self.parts), encoding="utf-8")


def fnum(x) -> str:
    if x is None or x is pd.NA or (isinstance(x, float) and np.isnan(x)):
        return "s/d"
    if isinstance(x, (bool, np.bool_)):
        return "sí" if x else "no"
    if isinstance(x, (int, np.integer)):
        return f"{int(x):,}".replace(",", ".")
    if isinstance(x, (float, np.floating)):
        if abs(x) >= 1000:
            return f"{x:,.0f}".replace(",", ".")
        return f"{x:.3f}".rstrip("0").rstrip(".").replace(".", ",") if abs(x) < 10 else f"{x:.1f}".replace(".", ",")
    return str(x)


def md_table(df: pd.DataFrame, index: bool = True) -> str:
    d = df.copy()
    if index:
        d = d.reset_index()
    cols = [str(c) for c in d.columns]
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join(["---"] * len(cols)) + "|"]
    for row in d.itertuples(index=False, name=None):  # itertuples conserva el tipo de cada columna
        lines.append("| " + " | ".join(fnum(v) for v in row) + " |")
    return "\n".join(lines)


def pct(x: float) -> float:
    return round(100 * x, 1)


def rate_table(df: pd.DataFrame, col: str, target: str = "ret", order=None, min_n: int = 1) -> pd.DataFrame:
    """n, % retorno, lift relativo vs promedio de df, por categoría de col (NaN = 'sin dato')."""
    s = df[col]
    if isinstance(s.dtype, pd.CategoricalDtype):
        s = s.astype(object)
    s = s.where(s.notna(), "sin dato")
    overall = df[target].mean()
    g = df.groupby(s, observed=True)[target].agg(n="size", retorno="mean")
    if order is not None:
        g = g.reindex([o for o in order if o in g.index])
    g = g[g["n"] >= min_n]
    g["retorno_pct"] = (100 * g["retorno"]).round(1)
    g["lift"] = (g["retorno"] / overall).round(3)
    g["dif_pp"] = (100 * (g["retorno"] - overall)).round(1)
    g.index.name = col
    return g[["n", "retorno_pct", "lift", "dif_pp"]]


def information_value(df: pd.DataFrame, col: str, target: str = "ret") -> tuple[float, int]:
    """IV = sum_i (p_ret_i - p_churn_i) * ln(p_ret_i / p_churn_i); bins = categorías (NaN propio bin).
    p_ret_i = share de los que retornan que caen en el bin i (idem churn). Corrección +0,5 en celdas vacías."""
    s = df[col]
    if isinstance(s.dtype, pd.CategoricalDtype):
        s = s.astype(object)
    s = s.where(s.notna(), "sin dato")
    ct = pd.crosstab(s, df[target]).reindex(columns=[True, False], fill_value=0).astype(float)
    ct = ct + 0.5
    p_ret = ct[True] / ct[True].sum()
    p_churn = ct[False] / ct[False].sum()
    iv = float(((p_ret - p_churn) * np.log(p_ret / p_churn)).sum())
    return round(iv, 4), int(len(ct))


def strat_table(df: pd.DataFrame, col: str, strata: list[str], target: str = "ret", min_n: int = 200) -> pd.DataFrame:
    """Tasa de retorno por categoría de col dentro de cada estrato (celdas con n>=min_n)."""
    d = df.copy()
    for s in strata:
        if isinstance(d[s].dtype, pd.CategoricalDtype):
            d[s] = d[s].astype(object)
    d[col] = d[col].astype(object).where(d[col].notna(), "sin dato")
    g = d.groupby(strata + [col], observed=True)[target].agg(["size", "mean"])
    g = g[g["size"] >= min_n]
    out = g["mean"].mul(100).round(1).unstack(col)
    n_out = g["size"].unstack(col).astype("Int64")
    out.columns = [f"{c} %" for c in out.columns]
    n_out.columns = [f"{c} n" for c in n_out.columns]
    return pd.concat([out, n_out], axis=1)


def kv_table(pairs: list[tuple[str, object]], name: str = "valor") -> pd.DataFrame:
    """Tabla clave→valor con dtype object para que los enteros no se conviertan en float."""
    return pd.DataFrame({name: pd.Series([v for _, v in pairs], index=[k for k, _ in pairs], dtype=object)})


def adjusted_or(df: pd.DataFrame, factors: dict[str, str], target: str = "ret") -> pd.DataFrame:
    """Odds ratios ajustados de una regresión logística sin penalización (sklearn).
    factors = {columna: categoría de referencia}. Sin errores estándar: es descriptivo, no inferencial."""
    d = df[list(factors) + [target]].dropna().copy()
    X_parts, names = [], []
    for col, ref in factors.items():
        s = d[col].astype(str)
        for lvl in sorted(s.unique()):
            if lvl == ref:
                continue
            X_parts.append((s == lvl).astype(float).values)
            names.append(f"{col}={lvl} (ref {ref})")
    X = np.column_stack(X_parts)
    y = d[target].astype(int).values
    lr = LogisticRegression(penalty=None, max_iter=2000)
    lr.fit(X, y)
    return pd.DataFrame({"OR ajustado": np.exp(lr.coef_[0]).round(3)}, index=names), len(d)


def save(fig, name: str):
    fig.tight_layout()
    fig.savefig(FIG_DIR / f"{PREFIX}_{name}.png", bbox_inches="tight")
    plt.close(fig)


def dotplot(ax, tab: pd.DataFrame, overall: float, title: str):
    """Tasa de retorno por categoría (puntos) con n a la derecha; línea vertical = promedio."""
    y = np.arange(len(tab))[::-1]
    ax.hlines(y, overall * 100, tab["retorno_pct"], color=C["grid"], linewidth=2)
    ax.scatter(tab["retorno_pct"], y, s=36, color=C["blue"], zorder=3, edgecolor="white", linewidth=1)
    ax.axvline(overall * 100, color=C["ink2"], linewidth=1)
    ax.set_yticks(y)
    ax.set_yticklabels([f"{i}  (n={fnum(int(n))})" for i, n in zip(tab.index, tab["n"])])
    ax.set_xlabel("Tasa de retorno aproximada (%)")
    ax.set_title(title, loc="left")
    ax.grid(axis="y", visible=False)


# ----------------------------------------------------------------------------------------------------
# 0. Carga y enriquecimiento a nivel turno
# ----------------------------------------------------------------------------------------------------
R = Report()
ag = load_agenda()
ap = appointments(ag)
dur = ag.drop_duplicates().groupby("schedule_id")["ServiceDuration"].agg(dur_max="max", dur_sum="sum")
del ag
ap = ap.merge(dur, left_on="schedule_id", right_index=True, how="left")

ap["cancel_true"] = ap["cancelled"] & ap["IsReschedule"].eq("N")
ap["cancel_resched"] = ap["cancelled"] & ap["IsReschedule"].eq("Y")
ap["return_visit"] = ap["ScheduleReturn"].eq("Y")
ap["digital"] = ap["ScheduleSource"].isin(["FordPass", "WEB", "Mobile"])
ap["diag_done"] = ap["completed"] & ap["has_diag"]
ap["repair_done"] = ap["completed"] & ap["has_repair"]
ap["recall_done"] = ap["completed"] & ap["has_recall"]
ap["resolved"] = ap["StatusARG"].isin(["(60) Concluido", "(70) Cancelado", "(80) No asistio", "(90) Concluido sin OS"])
ap["gen"] = ap["ShortVehicleModelGroupTreated"].map({
    "RANGER (P703)": "P703", "RANGER (P375)": "P375", "RANGER RAPTOR (P703)": "Otro/Raptor",
    "RANGER": "Otro/Raptor", "RANGER RAPTOR": "Otro/Raptor",
}).fillna("Otro/Raptor")
MY_BINS = [-np.inf, 2015, 2018, 2021, 2023, 2024, np.inf]
MY_LABELS = ["<=2015", "2016-18", "2019-21", "2022-23", "2024", "2025+"]
ap["my_bin"] = pd.cut(ap["ModelYear"], MY_BINS, labels=MY_LABELS).astype(object)

# Historial EXCLUSIVO por vehículo (todo lo ocurrido en turnos anteriores, orden event_date, schedule_id).
ap = ap.sort_values(["vehicle_id", "event_date", "schedule_id"]).reset_index(drop=True)
gv = ap.groupby("vehicle_id", sort=False)
hist_flags = {
    "no_show": "no_show", "cancel_true": "cancel_true", "cancel_resched": "cancel_resched",
    "diag": "diag_done", "repair": "repair_done", "recall": "recall_done", "return_visit": "return_visit",
    "maint": "is_completed_maintenance", "digital": "digital",
}
for name, flag in hist_flags.items():
    f = ap[flag].astype("int32")
    ap[f"prev_{name}"] = f.groupby(ap["vehicle_id"], sort=False).cumsum() - f
ap["prev_turnos"] = gv.cumcount()
ap["prev_date"] = gv["event_date"].shift(1)
ap["days_since_prev"] = (ap["event_date"] - ap["prev_date"]).dt.days
tmp = ap["event_date"].where(ap["is_completed_maintenance"])
ap["prev_maint_date"] = tmp.groupby(ap["vehicle_id"], sort=False).shift(1)
ap["prev_maint_date"] = ap["prev_maint_date"].groupby(ap["vehicle_id"], sort=False).ffill()
ap["days_since_prev_maint"] = (ap["event_date"] - ap["prev_maint_date"]).dt.days
del tmp

# Próximo mantenimiento completado con fecha ESTRICTAMENTE posterior (fechas únicas por vehículo).
# Solo vehículos identificados: pandas empareja NaN con NaN en merge, lo que mezclaría turnos de vehículos distintos.
md = (ap.loc[ap["is_completed_maintenance"] & ap["vehicle_id"].notna(), ["vehicle_id", "event_date"]].drop_duplicates()
      .sort_values(["vehicle_id", "event_date"]))
md["next_maint_date"] = md.groupby("vehicle_id")["event_date"].shift(-1)
# Sensibilidad: próximo mantenimiento a >= 30 días (merge_asof hacia adelante).
md30 = md[["vehicle_id", "event_date"]].copy()
md30["key"] = md30["event_date"] + pd.Timedelta(days=30)
md30 = md30.sort_values("key")
right = md[["vehicle_id", "event_date"]].rename(columns={"event_date": "next_maint_30"}).sort_values("next_maint_30")
md30 = pd.merge_asof(md30, right, left_on="key", right_on="next_maint_30", by="vehicle_id", direction="forward")
md = md.merge(md30[["vehicle_id", "event_date", "next_maint_30"]], on=["vehicle_id", "event_date"], how="left")

# ----------------------------------------------------------------------------------------------------
# 1. Base y etiqueta aproximada
# ----------------------------------------------------------------------------------------------------
base_all = ap[ap["is_completed_maintenance"] & ap["event_date"].between(BASE_START, BASE_END)]
n_base_vnull = int(base_all["vehicle_id"].isna().sum())
pct_vnull_my_null = pct(base_all.loc[base_all["vehicle_id"].isna(), "ModelYear"].isna().mean())
pct_maint_no_checkin = pct(ap.loc[ap["is_completed_maintenance"], "EffectiveCheckinDate"].isna().mean())
base = base_all[base_all["vehicle_id"].notna()].copy()
del base_all
base = base.merge(md, on=["vehicle_id", "event_date"], how="left")
base["horizon_end"] = base["event_date"] + HORIZON
base["horizon_trunc"] = base["horizon_end"] > CUTOFF
base["ret"] = base["next_maint_date"].notna() & (base["next_maint_date"] <= base["horizon_end"].clip(upper=CUTOFF))
base["ret30"] = base["next_maint_30"].notna() & (base["next_maint_30"] <= base["horizon_end"].clip(upper=CUTOFF))
base["gap_next"] = (base["next_maint_date"] - base["event_date"]).dt.days
base["base_year"] = base["event_date"].dt.year
base["survey_grp"] = pd.cut(base["SurveyStarRating"], [0, 2, 3, 4, 5], labels=["1-2", "3", "4", "5"]).astype(object)
base["survey_grp"] = base["survey_grp"].where(base["survey_grp"].notna(), "sin respuesta")
base["maint_bin"] = pd.cut(base["maint_number"], [0, 1, 2, 3, 5, 8, 99],
                           labels=["1", "2", "3", "4-5", "6-8", "9+"]).astype(object)
OVERALL = base["ret"].mean()

R.h("1. Base y etiqueta aproximada de retorno", 2)
lab = kv_table([
    ("turnos de mant. completado 2024-01→2025-05 con vehicle_id NULO (excluidos de la base)", n_base_vnull),
    ("% de esos excluidos con ModelYear también nulo", pct_vnull_my_null),
    ("% de mantenimientos completados (todo el período) sin EffectiveCheckinDate", pct_maint_no_checkin),
    ("turnos base (mant. completado 2024-01→2025-05, vehículo identificado)", len(base)),
    ("vehículos distintos en la base", int(base["vehicle_id"].nunique())),
    ("% retorno (<=15 meses)", pct(OVERALL)), ("% no retorno (churn aprox.)", pct(1 - OVERALL)),
    ("% retorno exigiendo >=30 días al próximo mantenimiento", pct(base["ret30"].mean())),
    ("turnos con horizonte truncado por CUTOFF (hasta 6 días)", int(base["horizon_trunc"].sum())),
    ("turnos cuyo próximo mant. está a <=1 día", int((base["gap_next"] <= 1).sum())),
    ("turnos cuyo próximo mant. está a <30 días", int((base["gap_next"] < 30).sum())),
    ("mediana de días al próximo mantenimiento (si existe)", int(base["gap_next"].median())),
])
R.table(lab, "Resumen de la base y la etiqueta", index=True)
bym = base.groupby(base["event_date"].dt.to_period("M").astype(str))["ret"].agg(n="size", retorno="mean")
bym["retorno_pct"] = (100 * bym["retorno"]).round(1)
R.table(bym[["n", "retorno_pct"]], "Estabilidad de la etiqueta por mes del turno base")
# Cuánto de la etiqueta a 15 meses es ritmo de uso (agregado en la verificación): km/año aproximado del vehículo
# = VehicleCurrentKM del turno base / edad en años desde WarrantyStartDate (solo edad > 6 meses).
_age_y = (base["event_date"] - base["WarrantyStartDate"]).dt.days / 365.25
base["km_anio_bin"] = pd.cut(np.where(_age_y > 0.5, base["VehicleCurrentKM"] / _age_y, np.nan),
                             [0, 10000, 20000, 30000, 50000, np.inf], labels=["<10k", "10-20k", "20-30k", "30-50k", "50k+"]).astype(object)
R.table(rate_table(base, "km_anio_bin", order=["<10k", "10-20k", "20-30k", "30-50k", "50k+", "sin dato"]),
        "Retorno a 15 meses según km/año aproximado del vehículo (VehicleCurrentKM / edad desde garantía): la etiqueta a horizonte fijo premia el alto uso")
R.p(f"IV de km/año (bins) sobre la base: {fnum(information_value(base, 'km_anio_bin')[0])} — mayor que cualquier feature de este tema.")
R.h("2. Confusores estructurales (generación, año modelo, n° de service) — no son de este tema, se usan como control", 2)
R.table(rate_table(base, "gen"), "Retorno por generación")
R.table(rate_table(base, "my_bin", order=MY_LABELS + ["sin dato"]), "Retorno por año modelo (bins)")
R.table(strat_table(base, "my_bin", ["gen"]), "Retorno por generación × año modelo (% y n)")
R.table(rate_table(base, "maint_bin", order=["1", "2", "3", "4-5", "6-8", "9+", "sin dato"]), "Retorno por número de service del turno base")

# ----------------------------------------------------------------------------------------------------
# 3. (a) ScheduleSource
# ----------------------------------------------------------------------------------------------------
R.h("3. (a) ScheduleSource — canal de agendado", 2)
obs = ap[ap["ScheduleDate"] <= CUTOFF].copy()
obs["year"] = obs["ScheduleDate"].dt.year
mix = pd.crosstab(obs["year"].astype(str), obs["ScheduleSource"])
mix_pct = (100 * mix.div(mix.sum(axis=1), axis=0)).round(1)
mix_pct["turnos"] = mix.sum(axis=1)
R.table(mix_pct, "Mix de fuente por año (% de turnos con ScheduleDate <= CUTOFF; 2026 hasta el 25/8)")
miss = base.groupby("ScheduleSource")[["NeededTowing", "ScheduleReturn", "IsReschedule", "EffectiveCheckinDate", "SurveyStarRating"]].agg(
    lambda s: round(100 * s.isna().mean(), 1))
miss.columns = [f"{c} % nulo" for c in miss.columns]
miss.insert(0, "n", base.groupby("ScheduleSource").size())
R.table(miss, "Patrón de nulos por fuente en la base: los 'sin dato' de varias columnas son un artefacto del canal, no una señal")
miss_y = base.groupby(base["event_date"].dt.year.astype(str))[["NeededTowing", "ScheduleReturn"]].agg(lambda s: round(100 * s.isna().mean(), 1))
miss_y.columns = [f"{c} % nulo" for c in miss_y.columns]
R.table(miss_y, "Nulos de NeededTowing y ScheduleReturn por año del turno base")
res = ap[ap["resolved"] & (ap["ScheduleDate"] <= CUTOFF)]
st = res.groupby("ScheduleSource").agg(
    n=("schedule_id", "size"), concluido=("completed", "mean"), concluido_sin_os=("completed_no_os", "mean"),
    no_show=("no_show", "mean"), cancel_real=("cancel_true", "mean"), cancel_reprog=("cancel_resched", "mean"))
for c in st.columns[1:]:
    st[c] = (100 * st[c]).round(1)
R.table(st, "Resultado del turno por fuente (% sobre turnos resueltos: 60/70/80/90). cancel_real = (70) con IsReschedule=N; cancel_reprog = (70) con IsReschedule=Y")
src_order = ["Dealer", "FordPass", "WEB", "Mobile", "CAF"]
R.table(rate_table(base, "ScheduleSource", order=src_order), "Retorno según la fuente del turno base (último mantenimiento)")
R.table(pd.crosstab(base["ScheduleSource"], base["gen"], normalize="columns").mul(100).round(1),
        "Composición de fuente dentro de cada generación en la base (% columna)")
R.table(strat_table(base, "ScheduleSource", ["gen"]), "Retorno por fuente dentro de cada generación")
R.table(strat_table(base, "ScheduleSource", ["gen", "my_bin"]), "Retorno por fuente dentro de generación × año modelo (celdas n>=200)")
b2 = base[base["gen"].isin(["P703", "P375"]) & base["ScheduleSource"].isin(["Dealer", "FordPass", "WEB", "Mobile"]) & base["my_bin"].notna()]
ors, n_or = adjusted_or(b2, {"ScheduleSource": "Dealer", "gen": "P375", "my_bin": "2022-23", "maint_bin": "1"})
R.table(ors, f"Odds ratios ajustados (logística sin penalización, n={fnum(n_or)}): fuente controlando generación, año modelo y n° de service")
R.table(rate_table(base, "digital"), "Retorno según si el turno base fue por canal digital (FordPass/WEB/Mobile)")
iv_src = information_value(base, "ScheduleSource")[0]
R.p(f"IV de ScheduleSource sobre la base: {fnum(iv_src)}.")

# Figura: mix mensual de fuente
mm = pd.crosstab(obs["ScheduleDate"].dt.to_period("M").astype(str), obs["ScheduleSource"])
mm = mm.div(mm.sum(axis=1), axis=0) * 100
fig, ax = plt.subplots(figsize=(9, 3.8))
cols = ["Dealer", "FordPass", "WEB", "Mobile", "CAF"]
colors = [C["blue"], C["orange"], C["aqua"], C["yellow"], C["gray"]]
bottom = np.zeros(len(mm))
x = np.arange(len(mm))
for c_, col_ in zip(cols, colors):
    ax.bar(x, mm[c_].values, bottom=bottom, color=col_, width=0.8, label=c_, edgecolor="white", linewidth=0.6)
    bottom += mm[c_].values
ax.set_xticks(x[::3])
ax.set_xticklabels(mm.index[::3], rotation=45, ha="right")
ax.set_ylabel("% de turnos del mes")
ax.set_title("Mix de fuente de agendado por mes (todos los turnos, ScheduleDate <= 25/8/2026)", loc="left")
ax.legend(ncol=5, loc="upper center", bbox_to_anchor=(0.5, -0.32))
ax.grid(axis="x", visible=False)
save(fig, "fuente_mix_mensual")

# Figura: retorno por fuente dentro de gen × año modelo
fig, axes = plt.subplots(1, 2, figsize=(10, 3.8), sharey=True)
for ax, g_ in zip(axes, ["P375", "P703"]):
    d = base[(base["gen"] == g_) & base["ScheduleSource"].isin(["Dealer", "FordPass", "WEB"])]
    t = d.groupby(["my_bin", "ScheduleSource"], observed=True)["ret"].agg(["size", "mean"])
    t = t[t["size"] >= 200]["mean"].mul(100).unstack("ScheduleSource").reindex(MY_LABELS)
    for src, col_ in zip(["Dealer", "FordPass", "WEB"], [C["blue"], C["orange"], C["aqua"]]):
        if src in t:
            ax.plot(t.index, t[src], marker="o", markersize=5, linewidth=2, color=col_, label=src)
    ax.set_title(f"Generación {g_}", loc="left")
    ax.set_xlabel("Año modelo")
    ax.tick_params(axis="x", rotation=30)
axes[0].set_ylabel("Tasa de retorno aproximada (%)")
axes[0].legend(title="Fuente del turno base")
fig.suptitle("Retorno por fuente de agendado, controlando generación y año modelo (celdas n>=200)", x=0.01, ha="left")
save(fig, "fuente_retorno_estratos")

# ----------------------------------------------------------------------------------------------------
# 4. (b) ConnectedStatusARG
# ----------------------------------------------------------------------------------------------------
R.h("4. (b) ConnectedStatusARG — conectividad (snapshot)", 2)
nun = ap.groupby("vehicle_id")["ConnectedStatusARG"].nunique()
R.p(f"Vehículos con más de un valor de ConnectedStatusARG a lo largo de sus turnos: {fnum(int((nun > 1).sum()))} "
    f"de {fnum(len(nun))} → la columna es un snapshot a la fecha de extracción, no un estado histórico.")
R.table(pd.crosstab(ap["ConnectedStatusARG"], ap["gen"]), "Turnos por conectividad × generación (toda la agenda)")
conn_order = ["Conectado", "No Conectado", "No tiene Conectividad", "Sin Información de Conectividad"]
R.table(rate_table(base, "ConnectedStatusARG", order=conn_order), "Retorno por conectividad (base)")
R.table(strat_table(base, "ConnectedStatusARG", ["gen"]), "Retorno por conectividad dentro de cada generación")
R.table(strat_table(base, "ConnectedStatusARG", ["gen", "my_bin"]), "Retorno por conectividad dentro de generación × año modelo (celdas n>=200)")
# Chequeo del bloque "Sin Información": ¿desaparecen del sistema?
base["any_later"] = False
later = ap[ap["ScheduleDate"] > BASE_START][["vehicle_id", "event_date"]]
last_evt = ap.groupby("vehicle_id")["event_date"].max().rename("last_event_vehicle")
base = base.merge(last_evt, left_on="vehicle_id", right_index=True, how="left")
base["any_later"] = base["last_event_vehicle"] > base["event_date"]
si = base.groupby("ConnectedStatusARG").agg(
    n=("ret", "size"), retorno=("ret", "mean"), algun_turno_posterior=("any_later", "mean"),
    customer_null=("customer_id", lambda s: s.isna().mean()), anio_modelo_mediana=("ModelYear", "median"))
for c in ["retorno", "algun_turno_posterior", "customer_null"]:
    si[c] = (100 * si[c]).round(1)
R.table(si.reindex(conn_order), "Diagnóstico de 'Sin Información': % con algún turno posterior (cualquier status), % customer_id nulo, año modelo mediano")
# OR dentro de cada generación (un modelo conjunto es inestable: Conectado ≈ P703 y No Conectado ≈ P375).
ors_p703, n_p703 = adjusted_or(base[(base["gen"] == "P703") & base["my_bin"].notna()],
                               {"ConnectedStatusARG": "Conectado", "my_bin": "2024"})
R.table(ors_p703, f"Odds ratios ajustados de conectividad DENTRO de P703 (n={fnum(n_p703)}), ref Conectado, controlando año modelo")
ors_p375, n_p375 = adjusted_or(base[(base["gen"] == "P375") & base["my_bin"].notna()],
                               {"ConnectedStatusARG": "No Conectado", "my_bin": "2022-23"})
R.table(ors_p375, f"Odds ratios ajustados de conectividad DENTRO de P375 (n={fnum(n_p375)}), ref No Conectado, controlando año modelo")

fig, ax = plt.subplots(figsize=(8, 3.6))
t = base[base["gen"].isin(["P375", "P703"])].groupby(["gen", "ConnectedStatusARG"], observed=True)["ret"].agg(["size", "mean"])
t = t.reset_index()
labels = [c.replace("Sin Información de Conectividad", "Sin información") for c in conn_order]
xg = np.arange(len(conn_order))
w = 0.36
for i, (g_, col_) in enumerate([("P375", C["blue"]), ("P703", C["orange"])]):
    d = t[t["gen"] == g_].set_index("ConnectedStatusARG").reindex(conn_order)
    vals = d["mean"].mul(100)
    ax.bar(xg + (i - 0.5) * w, vals, width=w - 0.04, color=col_, label=g_, edgecolor="white")
    for xi, (v, n) in enumerate(zip(vals, d["size"])):
        if not np.isnan(v):
            ax.text(xi + (i - 0.5) * w, v + 1.5, f"n={fnum(int(n))}", ha="center", fontsize=7, color=C["ink2"])
ax.set_xticks(xg)
ax.set_xticklabels(labels)
ax.set_ylabel("Tasa de retorno aproximada (%)")
ax.set_ylim(0, 100)
ax.axhline(OVERALL * 100, color=C["ink2"], linewidth=1)
ax.legend(title="Generación")
ax.set_title("Retorno por conectividad (snapshot) dentro de cada generación — línea: promedio de la base", loc="left")
ax.grid(axis="x", visible=False)
save(fig, "conectividad_retorno")

# ----------------------------------------------------------------------------------------------------
# 5. (c) SurveyStarRating
# ----------------------------------------------------------------------------------------------------
R.h("5. (c) SurveyStarRating — encuesta", 2)
sv = ap[ap["SurveyResponseDate"].notna()]
lag = (sv["SurveyResponseDate"] - sv["ScheduleDate"]).dt.days
timing = pd.DataFrame({"valor": [len(sv), pct((lag < 0).mean()), pct((lag == 0).mean()), pct((lag > 0).mean()),
                                 int(lag.quantile(.05)), int(lag.median()), int(lag.quantile(.95))]},
                      index=["turnos con encuesta respondida", "% respondida ANTES de ScheduleDate",
                             "% respondida el mismo día", "% respondida DESPUÉS", "p5 de (respuesta − ScheduleDate) en días",
                             "mediana", "p95"])
R.table(timing, "Timing de la respuesta a la encuesta respecto de la fecha del turno")
sr = ap["SurveyStarRating"].map(lambda v: "sin respuesta" if pd.isna(v) else str(int(v))).value_counts().rename("turnos").to_frame()
R.table(sr, "Distribución del rating (todos los turnos)")
rr = ap[ap["ScheduleDate"] <= CUTOFF].groupby("ScheduleSource")["SurveyStarRating"].agg(n="size", respondio=lambda s: s.notna().mean())
rr["respondio_pct"] = (100 * rr["respondio"]).round(1)
R.table(rr[["n", "respondio_pct"]], "Tasa de respuesta a la encuesta por fuente (todos los turnos <= CUTOFF)")
rs = ap.groupby("StatusARG")["SurveyStarRating"].agg(n="size", respondio=lambda s: s.notna().mean())
rs["respondio_pct"] = (100 * rs["respondio"]).round(1)
R.table(rs[["n", "respondio_pct"]], "Tasa de respuesta por status del turno")
surv_order = ["1-2", "3", "4", "5", "sin respuesta"]
R.table(rate_table(base, "survey_grp", order=surv_order), "Retorno por grupo de rating del turno base")
R.table(strat_table(base, "survey_grp", ["gen"]), "Retorno por rating dentro de cada generación")
base["respondio"] = base["SurveyStarRating"].notna()
bias = base.groupby(["gen", "ScheduleSource"], observed=True)["respondio"].agg(n="size", respondio=lambda s: s.mean())
bias = bias[bias["n"] >= 200]
bias["respondio_pct"] = (100 * bias["respondio"]).round(1)
R.table(bias[["n", "respondio_pct"]], "Sesgo de respuesta: % que respondió por generación × fuente (base, celdas n>=200)")
dig = base[base["digital"] & base["gen"].isin(["P375", "P703"])].copy()
dig["respondio_f"] = np.where(dig["respondio"], "respondió", "no respondió")
R.table(strat_table(dig, "respondio_f", ["gen"], min_n=100),
        "Solo turnos base por canal digital (donde la encuesta existe): retorno según respondió o no, por generación")
R.table(strat_table(dig, "survey_grp", ["gen"], min_n=100),
        "Solo turnos base por canal digital: retorno por rating, por generación")
iv_sv = information_value(base, "survey_grp")[0]
R.p(f"IV de survey_grp sobre la base: {fnum(iv_sv)}.")

fig, axes = plt.subplots(1, 2, figsize=(10, 3.6))
axes[0].hist(lag.clip(-60, 10), bins=np.arange(-60, 12, 2), color=C["blue"], edgecolor="white")
axes[0].set_title("Días entre respuesta a la encuesta y fecha del turno (recortado a [-60, 10])", loc="left")
axes[0].set_xlabel("SurveyResponseDate − ScheduleDate (días)")
axes[0].set_ylabel("Turnos con encuesta")
t = rate_table(base, "survey_grp", order=surv_order)
dotplot(axes[1], t, OVERALL, "Retorno por rating del turno base (línea: promedio)")
save(fig, "encuesta_retorno")

# ----------------------------------------------------------------------------------------------------
# 6. (d) Dealer
# ----------------------------------------------------------------------------------------------------
R.h("6. (d) Dealer", 2)
dl = res.groupby("dealer_id").agg(
    n_turnos=("schedule_id", "size"), concluido=("completed", "mean"), no_show=("no_show", "mean"),
    cancel_real=("cancel_true", "mean"), cancel_reprog=("cancel_resched", "mean"), share_p703=("gen", lambda s: s.eq("P703").mean()))
db = base.groupby("dealer_id").agg(n_base=("ret", "size"), retorno=("ret", "mean"))
dl = dl.join(db, how="left")
R.p(f"Dealers con turnos resueltos: {fnum(len(dl))}; con >=100 turnos base: {fnum(int((dl['n_base'] >= 100).sum()))}.")
disp = {}
big = dl[dl["n_turnos"] >= 300]
for c in ["concluido", "no_show", "cancel_real", "cancel_reprog"]:
    q = big[c].quantile([.1, .5, .9]).mul(100).round(1)
    disp[c] = [len(big), q[.1], q[.5], q[.9]]
q = dl.loc[dl["n_base"] >= 100, "retorno"].quantile([.1, .5, .9]).mul(100).round(1)
disp["retorno (n_base>=100)"] = [int((dl["n_base"] >= 100).sum()), q[.1], q[.5], q[.9]]
disp = pd.DataFrame(disp, index=["dealers", "p10 %", "p50 %", "p90 %"]).T
disp["dealers"] = disp["dealers"].astype(int)
R.table(disp, "Dispersión entre dealers de las tasas (dealers con >=300 turnos resueltos)")
# Concentración
vol = dl["n_turnos"].sort_values(ascending=False)
cum = vol.cumsum() / vol.sum()
gini = 1 - 2 * np.trapezoid(np.concatenate([[0], np.sort(vol.values).cumsum() / vol.sum()]), dx=1 / len(vol))
conc = kv_table([("% turnos en el top-10 dealers", pct(cum.iloc[9])), ("% turnos en el top-20", pct(cum.iloc[19])),
                 ("% turnos del dealer #1", pct(vol.iloc[0] / vol.sum())), ("Gini del volumen", round(float(gini), 3)),
                 ("turnos del dealer #1", int(vol.iloc[0])), ("mediana de turnos por dealer", int(vol.median()))])
R.table(conc, "Concentración del volumen de turnos resueltos por dealer")
# Estabilidad 2024 vs 2025
dy = base.groupby(["dealer_id", "base_year"])["ret"].agg(["size", "mean"]).unstack("base_year")
dy.columns = [f"{a}_{b}" for a, b in dy.columns]
dy = dy[(dy["size_2024"] >= 100) & (dy["size_2025"] >= 100)]
r_p = stats.pearsonr(dy["mean_2024"], dy["mean_2025"])
r_s = stats.spearmanr(dy["mean_2024"], dy["mean_2025"])
# ¿La dispersión observada excede el ruido binomial?
dd = dl[dl["n_base"] >= 100]
sd_obs = dd["retorno"].std()
sd_bin = np.sqrt((OVERALL * (1 - OVERALL) / dd["n_base"]).mean())
r_mix = stats.pearsonr(dd["share_p703"], dd["retorno"])
# Mezcla ajustada: retorno del dealer vs esperado según gen × my_bin
exp_rate = base.groupby(["gen", "my_bin"], observed=True)["ret"].transform("mean")
base["ret_exp"] = exp_rate
adj = base.groupby("dealer_id").agg(n_base=("ret", "size"), obs=("ret", "mean"), esp=("ret_exp", "mean"))
adj = adj[adj["n_base"] >= 100]
adj["resid_pp"] = (100 * (adj["obs"] - adj["esp"])).round(1)
# Target encoding FUERA DE TIEMPO: tasa de retorno del dealer en 2024 → quintiles aplicados a la base ene–may 2025.
te24 = base[base["base_year"] == 2024].groupby("dealer_id")["ret"].agg(n24="size", rate24="mean")
te24 = te24[te24["n24"] >= 50]
b25 = base[base["base_year"] == 2025].merge(te24, left_on="dealer_id", right_index=True, how="left")
b25["dealer_te_2024"] = pd.qcut(b25["rate24"], 5, labels=["Q1 (peor 2024)", "Q2", "Q3", "Q4", "Q5 (mejor 2024)"]).astype(object)
te_tab = rate_table(b25, "dealer_te_2024", order=["Q1 (peor 2024)", "Q2", "Q3", "Q4", "Q5 (mejor 2024)", "sin dato"])
iv_te = information_value(b25[b25["dealer_te_2024"].notna()], "dealer_te_2024")[0]
R.table(te_tab, f"Validación fuera de tiempo del efecto dealer: retorno en ene–may 2025 según quintil de retorno del dealer en 2024 (IV={fnum(iv_te)})")
stab = kv_table([("dealers con >=100 turnos base en 2024 y en 2025", len(dy)), ("Pearson r (retorno 2024 vs 2025)", round(r_p[0], 3)),
                 ("Spearman rho", round(r_s[0], 3)), ("desvío estándar observado entre dealers (pp)", pct(sd_obs)),
                 ("desvío esperado por ruido binomial (pp)", pct(sd_bin)), ("ratio observado/esperado", round(sd_obs / sd_bin, 2)),
                 ("Pearson r entre share P703 del dealer y su retorno", round(r_mix[0], 3)),
                 ("p10 del residuo (obs − esperado por mix gen×año) en pp", round(float(adj["resid_pp"].quantile(.1)), 1)),
                 ("p90 del residuo en pp", round(float(adj["resid_pp"].quantile(.9)), 1))])
R.table(stab, "Estabilidad y señal del efecto dealer")
top = dl[dl["n_base"] >= 100].sort_values("retorno")
show = pd.concat([top.head(5), top.tail(5)])
show_t = show.copy()
for c in ["concluido", "no_show", "cancel_real", "cancel_reprog", "share_p703", "retorno"]:
    show_t[c] = (100 * show_t[c]).round(1)
show_t["n_base"] = show_t["n_base"].astype("Int64")
show_t = show_t.join(adj[["resid_pp"]])
R.table(show_t, "5 dealers con menor y 5 con mayor retorno (n_base>=100); resid_pp = retorno − esperado por mix")
dy2 = dy.copy()
dy2["cambio_pp"] = (100 * (dy2["mean_2025"] - dy2["mean_2024"])).round(1)
dy2["retorno_2024_pct"] = (100 * dy2["mean_2024"]).round(1)
dy2["retorno_2025_pct"] = (100 * dy2["mean_2025"]).round(1)
dy2 = dy2.rename(columns={"size_2024": "n_2024", "size_2025": "n_2025"})[["n_2024", "n_2025", "retorno_2024_pct", "retorno_2025_pct", "cambio_pp"]]
dy2[["n_2024", "n_2025"]] = dy2[["n_2024", "n_2025"]].astype("Int64")
R.table(pd.concat([dy2.nsmallest(3, "cambio_pp"), dy2.nlargest(3, "cambio_pp")]),
        "Mayores caídas y subas interanuales de retorno por dealer (2024 → ene–may 2025, dealers con n>=100 en ambos años)")
# Un vehículo puede tener dos mantenimientos concluidos el mismo día (schedule_id distintos): se toma el primero
# para no duplicar filas en el merge (sin el drop_duplicates, n quedaba en 85.928 en vez de 85.821).
next_dl = (ap.loc[ap["is_completed_maintenance"], ["vehicle_id", "event_date", "dealer_id"]]
           .drop_duplicates(["vehicle_id", "event_date"])
           .rename(columns={"event_date": "next_maint_date", "dealer_id": "next_dealer"}))
same = base[base["ret"]].merge(next_dl, on=["vehicle_id", "next_maint_date"], how="left")
same_share = (same["next_dealer"] == same["dealer_id"]).mean()
R.p(f"Entre los turnos base que retornan, el próximo mantenimiento se hace en el MISMO dealer en el "
    f"{fnum(pct(same_share))}% de los casos (n={fnum(len(same))}).")
iv_dl = information_value(base[base["dealer_id"].isin(dl.index[dl["n_base"] >= 100])], "dealer_id")[0]
R.p(f"IV de dealer_id (dealers con n_base>=100, {fnum(int((dl['n_base'] >= 100).sum()))} categorías): {fnum(iv_dl)}. "
    f"Ojo: el IV de una variable de alta cardinalidad está inflado por el n de categorías.")

fig, axes = plt.subplots(1, 5, figsize=(12, 3.4))
for ax, (c, lab_) in zip(axes, [("concluido", "Concluido"), ("no_show", "No-show"), ("cancel_real", "Cancelación real"),
                                ("cancel_reprog", "Reprogramación"), ("retorno", "Retorno (base)")]):
    d = big[c] if c != "retorno" else dl.loc[dl["n_base"] >= 100, c]
    rng = np.random.default_rng(6)
    ax.scatter(rng.normal(0, 0.06, len(d)), d * 100, s=18, color=C["blue"], alpha=0.7, edgecolor="white", linewidth=0.5)
    qs = d.quantile([.1, .5, .9]) * 100
    ax.hlines(qs, -0.25, 0.25, color=C["ink2"], linewidth=1)
    ax.set_xlim(-0.5, 0.5)
    ax.set_xticks([])
    ax.set_title(lab_, loc="left")
    ax.grid(axis="x", visible=False)
axes[0].set_ylabel("% por dealer (líneas: p10/p50/p90)")
fig.suptitle("Dispersión entre dealers (>=300 turnos resueltos; retorno: >=100 turnos base)", x=0.01, ha="left")
save(fig, "dealer_dispersion")

fig, ax = plt.subplots(figsize=(4.6, 4.2))
xs = np.arange(1, len(vol) + 1) / len(vol) * 100
ax.plot(np.concatenate([[0], xs]), np.concatenate([[0], cum.values * 100]), color=C["blue"], linewidth=2)
ax.plot([0, 100], [0, 100], color=C["grid"], linewidth=1)
ax.set_xlabel("% de dealers (ordenados de mayor a menor volumen)")
ax.set_ylabel("% acumulado de turnos resueltos")
ax.set_title(f"Concentración de volumen: top-10 = {fnum(pct(cum.iloc[9]))}% de los turnos", loc="left")
save(fig, "dealer_lorenz")

fig, ax = plt.subplots(figsize=(5.2, 4.6))
ax.scatter(dy["mean_2024"] * 100, dy["mean_2025"] * 100, s=(dy["size_2024"] + dy["size_2025"]) / 40,
           color=C["blue"], alpha=0.65, edgecolor="white", linewidth=0.8)
lo, hi = 45, 100
ax.plot([lo, hi], [lo, hi], color=C["grid"], linewidth=1)
ax.set_xlim(lo, hi)
ax.set_ylim(lo, hi)
ax.set_xlabel("Retorno de turnos base de 2024 (%)")
ax.set_ylabel("Retorno de turnos base de ene–may 2025 (%)")
ax.set_title(f"Retorno por dealer, 2024 vs 2025 (r={r_p[0]:.2f}, rho={r_s[0]:.2f}, n={len(dy)} dealers)", loc="left")
save(fig, "dealer_estabilidad")

# ----------------------------------------------------------------------------------------------------
# 7. (e) Servicios de conveniencia y atributos del turno base
# ----------------------------------------------------------------------------------------------------
R.h("7. (e) Conveniencia y atributos del turno base", 2)
# Semántica empírica de dos flags ambiguos, sobre TODA la agenda a nivel turno.
ap["next_date"] = gv["event_date"].shift(-1)
ap["days_to_next"] = (ap["next_date"] - ap["event_date"]).dt.days
ap["prev_status"] = gv["StatusARG"].shift(1)
sem_rows = []
for v in ["Y", "N"]:
    x = ap[ap["ScheduleReturn"].eq(v)]
    sem_rows.append({"flag": f"ScheduleReturn={v}", "n": len(x),
                     "mediana días desde turno previo": x["days_since_prev"].median(),
                     "p90 días desde turno previo": x["days_since_prev"].quantile(.9),
                     "% turno previo concluido": pct(x["prev_status"].eq("(60) Concluido").mean()),
                     "% incluye mantenimiento": pct(x["has_maint"].mean()), "% incluye diagnóstico": pct(x["has_diag"].mean()),
                     "% incluye reparación": pct(x["has_repair"].mean())})
R.table(pd.DataFrame(sem_rows).set_index("flag"), "Semántica empírica de ScheduleReturn (toda la agenda): Y = re-visita a pocos días de otro turno, mayormente diagnóstico/reparación")
sem2 = []
for lab_, m in [("Cancelado con IsReschedule=Y", ap["cancel_resched"]), ("Cancelado con IsReschedule=N", ap["cancel_true"]),
                ("Concluido con IsReschedule=Y", ap["completed"] & ap["IsReschedule"].eq("Y")),
                ("Concluido con IsReschedule nulo", ap["completed"] & ap["IsReschedule"].isna())]:
    x = ap[m]
    sem2.append({"grupo": lab_, "n": len(x), "% con turno siguiente a <=30 días": pct((x["days_to_next"] <= 30).mean()),
                 "mediana días al turno siguiente": x["days_to_next"].median(),
                 "% turno previo cancelado": pct(x["prev_status"].eq("(70) Cancelado").mean()),
                 "mediana días desde turno previo": x["days_since_prev"].median()})
R.table(pd.DataFrame(sem2).set_index("grupo"), "Semántica empírica de IsReschedule (toda la agenda): (70) con Y = reprogramación (se re-agenda enseguida); (60) con Y = turno nacido de una reprogramación")
DAYS_BINS = [-np.inf, -1, 0, 1, 3, 7, 14, 30, np.inf]
DAYS_LABELS = ["<0", "0", "1", "2-3", "4-7", "8-14", "15-30", "31+"]
base["days_bin"] = pd.cut(base["DaysInDealer"], DAYS_BINS, labels=DAYS_LABELS).astype(object)
base["wdays_bin"] = pd.cut(base["WorkDaysInDealer"], DAYS_BINS, labels=DAYS_LABELS).astype(object)
base["dur_bin"] = base["dur_max"].map(lambda v: "sin dato" if pd.isna(v) else f"{int(v)} min")
base["items_bin"] = base["n_items"].clip(upper=3).map({1: "1", 2: "2", 3: "3+"})
base["IsReschedule_f"] = base["IsReschedule"].where(base["IsReschedule"].notna(), "sin dato")
base["ScheduleReturn_f"] = base["ScheduleReturn"].where(base["ScheduleReturn"].notna(), "sin dato")
base["CustomerWaiting_f"] = base["CustomerWaiting"].where(base["CustomerWaiting"].notna(), "sin dato")
base["NeededTowing_f"] = base["NeededTowing"].where(base["NeededTowing"].notna(), "sin dato")
conv_feats = [
    ("has_pud", "Pick-up & delivery en el turno", None), ("has_mobile", "Servicio móvil en el turno", None),
    ("CustomerWaiting_f", "Cliente esperó en el dealer", ["Y", "N", "sin dato"]),
    ("NeededTowing_f", "Necesitó remolque", ["Y", "N", "sin dato"]),
    ("has_fixed_price", "Algún ítem con precio fijo Ford", None),
    ("IsReschedule_f", "Turno reprogramado (IsReschedule)", ["Y", "sin dato"]),
    ("ScheduleReturn_f", "Re-visita (ScheduleReturn)", ["Y", "N", "sin dato"]),
    ("days_bin", "DaysInDealer (días en el taller)", DAYS_LABELS + ["sin dato"]),
    ("wdays_bin", "WorkDaysInDealer (días hábiles)", DAYS_LABELS + ["sin dato"]),
    ("dur_bin", "Duración máx. del ítem (ServiceDuration)", ["30 min", "50 min", "60 min", "80 min", "100 min", "120 min", "130 min", "sin dato"]),
    ("items_bin", "Cantidad de ítems del turno", ["1", "2", "3+"]),
    ("has_diag", "Turno incluye diagnóstico", None), ("has_repair", "Turno incluye reparación", None),
    ("has_recall", "Turno incluye campaña/recall", None), ("has_guarantee", "Turno incluye garantía", None),
    ("Region", "Region", None), ("DealerStateOrZone", "DealerStateOrZone", None),
]
conv_rows = []
for col, lab_, order in conv_feats:
    t = rate_table(base, col, order=order)
    t.insert(0, "feature", lab_)
    t.index.name = "categoria"
    conv_rows.append(t.reset_index())
conv_tab = pd.concat(conv_rows, ignore_index=True)
R.table(conv_tab, "Retorno por categoría — conveniencia y atributos del turno base", index=False)

fig, axes = plt.subplots(2, 3, figsize=(12, 7))
panels = [("days_bin", "DaysInDealer"), ("dur_bin", "ServiceDuration (máx. ítem)"), ("ScheduleReturn_f", "ScheduleReturn"),
          ("IsReschedule_f", "IsReschedule"), ("has_fixed_price", "Precio fijo Ford"), ("has_repair", "Incluye reparación")]
conv_order = {c: o for c, _, o in conv_feats}
for ax, (col, lab_) in zip(axes.ravel(), panels):
    dotplot(ax, rate_table(base, col, order=conv_order.get(col)), OVERALL, lab_)
fig.suptitle("Retorno aproximado según atributos del turno base (línea: promedio de la base)", x=0.01, ha="left")
save(fig, "conveniencia_retorno")

# ----------------------------------------------------------------------------------------------------
# 8. (f) Historia de comportamiento previa al turno base
# ----------------------------------------------------------------------------------------------------
R.h("8. (f) Historia de comportamiento previa al turno base", 2)
R.p("El historial arranca el 2024-01-01 (truncamiento a izquierda): un turno base de marzo 2024 tiene 2 meses de "
    "historia observable y uno de mayo 2025, 16. Por eso las tablas de esta sección usan la sub-base con "
    "event_date >= 2025-01-01 (>=12 meses de lookback); se reporta también la base completa como contraste.")
hb = base[base["event_date"] >= "2025-01-01"].copy()
OVERALL_H = hb["ret"].mean()
R.p(f"Sub-base con >=12 meses de historia: n={fnum(len(hb))}, retorno {fnum(pct(OVERALL_H))}%.")


def cnt_bin(s: pd.Series, top: int = 2) -> pd.Series:
    labels = [str(i) for i in range(top)] + [f"{top}+"]
    return s.clip(upper=top).map({i: labels[i] for i in range(top + 1)})


REC_BINS = [-np.inf, 30, 90, 180, 365, np.inf]
REC_LABELS = ["<=30", "31-90", "91-180", "181-365", ">365"]
for d in (hb, base):
    d["h_no_show"] = cnt_bin(d["prev_no_show"])
    d["h_cancel_true"] = cnt_bin(d["prev_cancel_true"])
    d["h_cancel_resched"] = cnt_bin(d["prev_cancel_resched"])
    d["h_diag"] = cnt_bin(d["prev_diag"])
    d["h_repair"] = cnt_bin(d["prev_repair"])
    d["h_recall"] = cnt_bin(d["prev_recall"])
    d["h_return_visit"] = cnt_bin(d["prev_return_visit"])
    d["h_maint"] = cnt_bin(d["prev_maint"], top=3)
    d["h_turnos"] = pd.cut(d["prev_turnos"], [-1, 0, 1, 2, 4, np.inf], labels=["0", "1", "2", "3-4", "5+"]).astype(object)
    d["h_digital"] = cnt_bin(d["prev_digital"], top=1)
    d["h_recency"] = pd.cut(d["days_since_prev"], REC_BINS, labels=REC_LABELS).astype(object)
    d["h_recency"] = d["h_recency"].where(d["h_recency"].notna(), "sin turno previo")
    d["h_recency_maint"] = pd.cut(d["days_since_prev_maint"], REC_BINS, labels=REC_LABELS).astype(object)
    d["h_recency_maint"] = d["h_recency_maint"].where(d["h_recency_maint"].notna(), "sin mant. previo")
hist_feats = [
    ("h_no_show", "N° no-shows previos", ["0", "1", "2+"]),
    ("h_cancel_true", "N° cancelaciones reales previas (IsReschedule=N)", ["0", "1", "2+"]),
    ("h_cancel_resched", "N° reprogramaciones previas (cancelado con IsReschedule=Y)", ["0", "1", "2+"]),
    ("h_diag", "N° diagnósticos concluidos previos", ["0", "1", "2+"]),
    ("h_repair", "N° reparaciones concluidas previas", ["0", "1", "2+"]),
    ("h_recall", "N° campañas/recalls concluidos previos", ["0", "1", "2+"]),
    ("h_return_visit", "N° re-visitas previas (ScheduleReturn=Y)", ["0", "1", "2+"]),
    ("h_maint", "N° mantenimientos completados previos (desde 2024-01)", ["0", "1", "2", "3+"]),
    ("h_turnos", "N° turnos previos de cualquier tipo", ["0", "1", "2", "3-4", "5+"]),
    ("h_digital", "Usó canal digital en algún turno previo", ["0", "1+"]),
    ("h_recency", "Días desde el turno previo (cualquier tipo)", REC_LABELS + ["sin turno previo"]),
    ("h_recency_maint", "Días desde el mantenimiento completado previo", REC_LABELS + ["sin mant. previo"]),
]
hist_rows = []
for col, lab_, order in hist_feats:
    t = rate_table(hb, col, order=order)
    t.insert(0, "feature", lab_)
    t.index.name = "categoria"
    tb = rate_table(base, col, order=order)[["n", "retorno_pct"]].rename(columns={"n": "n_base_completa", "retorno_pct": "retorno_pct_base_completa"})
    t = t.join(tb)
    hist_rows.append(t.reset_index())
hist_tab = pd.concat(hist_rows, ignore_index=True)
R.table(hist_tab, "Retorno por historial previo (sub-base >=12 meses de lookback; últimas 2 columnas: base completa)", index=False)
hb["primer_service"] = np.where(hb["maint_number"] == 1, "1er service", "2° o posterior")
R.table(strat_table(hb, "h_recency", ["primer_service"], min_n=100),
        "Recencia del turno previo × si el turno base es el primer service (sub-base 2025): separa 'vehículo nuevo' de 'vuelve tras ausencia'")
# Ajuste por intensidad de contacto (agregado en la verificación): tener un no-show previo implica haber tenido
# turnos previos, y los turnos previos suben el retorno. La comparación cruda 0/1/2+ mezcla los dos efectos.
hb["ns_any"] = np.where(hb["prev_no_show"] > 0, "con no-show previo", "sin no-show previo")
ns_strat = hb[hb["prev_turnos"] >= 1].groupby(["h_turnos", "ns_any"], observed=True)["ret"].agg(n="size", retorno="mean")
ns_strat["retorno_pct"] = (100 * ns_strat["retorno"]).round(1)
ns_strat = ns_strat[["n", "retorno_pct"]].unstack("ns_any")
ns_strat.columns = [f"{a} ({b})" for a, b in ns_strat.columns]
R.table(ns_strat,
        "Retorno según no-show previo DENTRO de cada nivel de turnos previos (sub-base 2025, >=1 turno previo): "
        "a igual cantidad de contactos, el que tuvo un no-show retorna menos")
hist_factors = {"h_no_show": "0", "h_cancel_true": "0", "h_cancel_resched": "0", "h_recall": "0", "h_repair": "0",
                "h_diag": "0", "h_return_visit": "0", "h_turnos": "0", "h_recency": "91-180",
                "gen": "P375", "my_bin": "2022-23", "maint_bin": "1"}
ors_h, n_h = adjusted_or(hb[hb["gen"].isin(["P375", "P703"]) & hb["my_bin"].notna()], hist_factors)
ors_h = ors_h[~ors_h.index.str.startswith(("gen=", "my_bin=", "maint_bin="))]
R.table(ors_h, f"Modelo conjunto del historial (logística sin penalización, n={fnum(n_h)}): OR de cada feature controlando por "
               f"todas las demás + generación, año modelo y n° de service")
ors_h0, n_h0 = adjusted_or(hb[hb["gen"].isin(["P375", "P703"]) & hb["my_bin"].notna()],
                           {k: v for k, v in hist_factors.items() if k not in ("h_turnos", "h_recency")})
ors_h0 = ors_h0[~ors_h0.index.str.startswith(("gen=", "my_bin=", "maint_bin="))]
R.table(ors_h0, f"Mismo modelo SIN turnos previos ni recencia (n={fnum(n_h0)}): el efecto 'crudo' de cada feature neto solo de la edad del vehículo")

fig, axes = plt.subplots(2, 3, figsize=(12, 7))
panels = [("h_no_show", "No-shows previos"), ("h_cancel_true", "Cancelaciones reales previas"),
          ("h_repair", "Reparaciones previas"), ("h_diag", "Diagnósticos previos"),
          ("h_recency", "Días desde el turno previo"), ("h_turnos", "Turnos previos (cualquier tipo)")]
hmap = {c: o for c, _, o in hist_feats}
for ax, (col, lab_) in zip(axes.ravel(), panels):
    dotplot(ax, rate_table(hb, col, order=hmap[col]), OVERALL_H, lab_)
fig.suptitle("Retorno según historial previo (sub-base ene–may 2025, >=12 meses de lookback; línea: promedio)", x=0.01, ha="left")
save(fig, "historia_retorno")

# ----------------------------------------------------------------------------------------------------
# 9. (g) Estacionalidad y tendencia
# ----------------------------------------------------------------------------------------------------
R.h("9. (g) Estacionalidad y tendencia", 2)
ap["ym"] = ap["ScheduleDate"].dt.to_period("M").astype(str)
# Solo turnos con ScheduleDate <= CUTOFF: los del 26–31/8/2026 son reservas futuras (se tabulan aparte más abajo)
# y, si se incluyen, inflan el volumen y la tasa de reprogramación de agosto 2026.
win = ap[(ap["ScheduleDate"] >= "2024-01-01") & (ap["ScheduleDate"] <= CUTOFF)]
mon = pd.crosstab(win["ym"], win["StatusARG"])
mon["total"] = mon.sum(axis=1)
mon_res = win[win["resolved"]].groupby("ym").agg(
    resueltos=("schedule_id", "size"), no_show=("no_show", "mean"), cancel_real=("cancel_true", "mean"),
    cancel_reprog=("cancel_resched", "mean"), concluido=("completed", "mean"), sin_os=("completed_no_os", "mean"))
for c in mon_res.columns[1:]:
    mon_res[c] = (100 * mon_res[c]).round(1)
mon_res["mant_completados"] = win[win["is_completed_maintenance"]].groupby("ym").size()
mon_res["checkin_nulo_en_concluidos_pct"] = win[win["completed"]].groupby("ym")["EffectiveCheckinDate"].apply(lambda s: round(100 * s.isna().mean(), 1))
mon_res["fordpass_pct"] = win.groupby("ym")["ScheduleSource"].apply(lambda s: round(100 * s.eq("FordPass").mean(), 1))
R.table(mon, "Turnos por mes (ScheduleDate) y status, 2024-01 → 2026-08 (agosto 2026 parcial: hasta el 25)")
R.table(mon_res, "Tasas mensuales sobre turnos resueltos, volumen de mantenimientos completados, % check-in nulo y % FordPass")
fut = ap[ap["ScheduleDate"] > CUTOFF]
R.table(pd.crosstab(fut["ym"], fut["StatusARG"]), "Turnos con ScheduleDate posterior al CUTOFF (reservas futuras)")
yr = win[win["resolved"]].copy()
yr["year"] = yr["ScheduleDate"].dt.year.astype(str)
yt = yr.groupby("year").agg(resueltos=("schedule_id", "size"), no_show=("no_show", "mean"), cancel_real=("cancel_true", "mean"),
                            cancel_reprog=("cancel_resched", "mean"), concluido=("completed", "mean"))
for c in yt.columns[1:]:
    yt[c] = (100 * yt[c]).round(1)
R.table(yt, "Tasas anuales sobre turnos resueltos (2026 hasta el 25/8)")
# Estacionalidad de la etiqueta por mes calendario (mismo mes de 2024 y 2025 juntos)
bym2 = base.groupby(base["event_date"].dt.month.astype(str).str.zfill(2))["ret"].agg(n="size", retorno="mean")
bym2["retorno_pct"] = (100 * bym2["retorno"]).round(1)
bym2.index.name = "mes calendario del turno base"
R.table(bym2[["n", "retorno_pct"]], "Retorno por mes calendario del turno base (2024 y ene–may 2025 combinados)")

fig, ax = plt.subplots(figsize=(10, 4))
order_st = ["(60) Concluido", "(90) Concluido sin OS", "(80) No asistio", "(70) Cancelado", "(40) En progreso", "(30) Agendado"]
cols_st = [C["blue"], C["aqua"], C["orange"], C["yellow"], C["magenta"], C["gray"]]
x = np.arange(len(mon))
bottom = np.zeros(len(mon))
for s_, col_ in zip(order_st, cols_st):
    v = mon[s_].values if s_ in mon else np.zeros(len(mon))
    ax.bar(x, v, bottom=bottom, color=col_, width=0.8, label=s_, edgecolor="white", linewidth=0.6)
    bottom += v
ax.set_xticks(x[::3])
ax.set_xticklabels(mon.index[::3], rotation=45, ha="right")
ax.set_ylabel("Turnos por mes (ScheduleDate)")
ax.set_title("Volumen mensual de turnos por status (agosto 2026 parcial: hasta el 25)", loc="left")
ax.legend(ncol=6, loc="upper center", bbox_to_anchor=(0.5, -0.28), fontsize=8)
ax.grid(axis="x", visible=False)
save(fig, "estacionalidad_volumen")

fig, ax = plt.subplots(figsize=(10, 3.8))
x = np.arange(len(mon_res))
for c_, lab_, col_ in [("no_show", "No-show", C["orange"]), ("cancel_real", "Cancelación real (IsReschedule=N)", C["red"]),
                       ("cancel_reprog", "Reprogramación (cancelado con IsReschedule=Y)", C["yellow"]),
                       ("sin_os", "Concluido sin OS", C["aqua"])]:
    ax.plot(x, mon_res[c_].values, marker="o", markersize=4, linewidth=2, color=col_, label=lab_)
ax.set_xticks(x[::3])
ax.set_xticklabels(mon_res.index[::3], rotation=45, ha="right")
ax.set_ylabel("% de turnos resueltos del mes")
ax.set_title("Tasas mensuales de no-show, cancelación real, reprogramación y concluido sin OS", loc="left")
ax.legend(ncol=2, loc="upper center", bbox_to_anchor=(0.5, -0.3), fontsize=8)
save(fig, "estacionalidad_tasas")

# ----------------------------------------------------------------------------------------------------
# 10. Ranking de features candidatas por IV
# ----------------------------------------------------------------------------------------------------
R.h("10. Ranking univariante de features candidatas (Information Value)", 2)
R.p("IV = Σ_i (p_ret_i − p_churn_i)·ln(p_ret_i / p_churn_i), con p_ret_i = fracción de los que retornan que cae en "
    "el bin i y p_churn_i la fracción de los que no retornan. Umbrales usuales: <0,02 nulo; 0,02–0,1 débil; "
    "0,1–0,3 medio; >0,3 fuerte. Depende del binning y se infla con muchas categorías (dealer_id). "
    "'dif_pp' = tasa máxima − tasa mínima entre bins con n>=300. Las features de historial se calculan sobre la "
    "sub-base con >=12 meses de lookback; el resto sobre la base completa.")
COMMENTS = {
    "gen": "CONTROL (no es de este tema). Generación del vehículo; confunde a canal y conectividad.",
    "my_bin": "CONTROL. Año modelo; el driver estructural más fuerte de la base.",
    "maint_bin": "CONTROL. N° de service del turno base (edad del vehículo en services).",
    "ScheduleSource": "Legítima al scoring (fuente del último turno). Parte del efecto es mix P703/año modelo: ver OR ajustado.",
    "digital": "Resumen de ScheduleSource. Misma advertencia de mix.",
    "ConnectedStatusARG": "SNAPSHOT a la extracción. 'Sin Información' concentra vehículos que desaparecen del sistema: riesgo alto de leakage. Usar solo Conectado vs No tiene dentro de P703, o excluir.",
    "survey_grp": "Encuesta respondida ANTES del turno (probablemente del agendado). Cobertura ~7%: la señal es 'respondió' más que el rating. Verificar semántica con el mentor.",
    "dealer_id": "Estable entre años (ver r 2024 vs 2025). Alta cardinalidad: usar como target encoding con regularización o efecto aleatorio. Parte es mix de generación.",
    "has_pud": "Legítima. n chico.", "has_mobile": "Legítima. n chico.", "CustomerWaiting_f": "Legítima. Y es raro.",
    "NeededTowing_f": "Legítima. Y es raro; NaN es mayoría (no informado).",
    "has_fixed_price": "Legítima. Precio fijo Ford en el turno base.",
    "IsReschedule_f": "Legítima. Y = el turno base nació de una reprogramación.",
    "ScheduleReturn_f": "Legítima. Y = re-visita a <=30 días de otro turno; en la base es raro (los mantenimientos no suelen ser re-visitas).",
    "days_bin": "Legítima si se conoce el checkout antes del scoring. Valores negativos y >30 son errores de carga.",
    "wdays_bin": "Idem DaysInDealer.", "dur_bin": "Legítima. Duración nominal del ítem, proxy del tipo de service.",
    "items_bin": "Legítima. Cantidad de ítems del turno base.",
    "has_diag": "Legítima. Mantenimiento + diagnóstico en el mismo turno.", "has_repair": "Legítima. Mantenimiento + reparación.",
    "has_recall": "Legítima. Mantenimiento + campaña.", "has_guarantee": "Legítima. n chico.",
    "Region": "Legítima; casi constante (60 domina).", "DealerStateOrZone": "Legítima; zona del dealer.",
    "h_no_show": "Legítima (historial). IV univariante ~0 por confusión con intensidad: a igual n de turnos previos, OR ajustado ~0,7. Truncada a izquierda: solo desde 2024-01.",
    "h_cancel_true": "Legítima (historial). Cancelación real = IsReschedule=N. Idem no-shows: OR ajustado ~0,75 pese a IV ~0.",
    "h_cancel_resched": "Legítima (historial). Reprogramaciones.",
    "h_diag": "Legítima (historial).", "h_repair": "Legítima (historial).", "h_recall": "Legítima (historial).",
    "h_return_visit": "Legítima (historial). Re-visitas a <=30 días.",
    "h_maint": "Legítima (historial) pero correlacionada con intensidad de uso/km: cruzar con tema de uso.",
    "h_turnos": "Legítima (historial). Intensidad de relación con la red.",
    "h_digital": "Legítima (historial). Usó FordPass/WEB/Mobile alguna vez.",
    "h_recency": "Legítima (historial). Recencia del último turno de cualquier tipo antes del base.",
    "h_recency_maint": "Legítima (historial). Recencia del mantenimiento previo = ritmo de uso. Se solapa con tema de uso/km.",
}
rank_rows = []
feat_sets = [(base, ["gen", "my_bin", "maint_bin", "ScheduleSource", "digital", "ConnectedStatusARG", "survey_grp",
                     "has_pud", "has_mobile", "CustomerWaiting_f", "NeededTowing_f", "has_fixed_price", "IsReschedule_f",
                     "ScheduleReturn_f", "days_bin", "wdays_bin", "dur_bin", "items_bin", "has_diag", "has_repair",
                     "has_recall", "has_guarantee", "Region", "DealerStateOrZone"]),
             (hb, [c for c, _, _ in hist_feats])]
for d, feats in feat_sets:
    for col in feats:
        iv, nb = information_value(d, col)
        t = rate_table(d, col, min_n=MIN_N_BIN)
        rank_rows.append({"feature": col, "n": len(d), "n_bins": nb, "IV": iv,
                          "tasa_max_pct": t["retorno_pct"].max(), "tasa_min_pct": t["retorno_pct"].min(),
                          "dif_pp": round(t["retorno_pct"].max() - t["retorno_pct"].min(), 1),
                          "comentario": COMMENTS.get(col, "")})
d_dl = base[base["dealer_id"].isin(dl.index[dl["n_base"] >= 100])]
t = rate_table(d_dl, "dealer_id", min_n=100)
rank_rows.append({"feature": "dealer_id", "n": len(d_dl), "n_bins": int(t.shape[0]), "IV": iv_dl,
                  "tasa_max_pct": t["retorno_pct"].max(), "tasa_min_pct": t["retorno_pct"].min(),
                  "dif_pp": round(t["retorno_pct"].max() - t["retorno_pct"].min(), 1), "comentario": COMMENTS["dealer_id"]})
t = te_tab[te_tab["n"] >= MIN_N_BIN]
rank_rows.append({"feature": "dealer_te_2024", "n": int(te_tab["n"].sum()), "n_bins": int(te_tab.shape[0]), "IV": iv_te,
                  "tasa_max_pct": t["retorno_pct"].max(), "tasa_min_pct": t["retorno_pct"].min(),
                  "dif_pp": round(t["retorno_pct"].max() - t["retorno_pct"].min(), 1),
                  "comentario": "Target encoding del dealer calculado en 2024 y evaluado en 2025 (fuera de tiempo): versión honesta de dealer_id."})
rank = pd.DataFrame(rank_rows).sort_values("IV", ascending=False).reset_index(drop=True)
R.table(rank, "Ranking de features por IV (incluye los controles para dimensionar)", index=False)

fig, ax = plt.subplots(figsize=(8, 8))
rk = rank.sort_values("IV")
is_ctrl = rk["feature"].isin(["gen", "my_bin", "maint_bin"])
is_leak = rk["feature"].isin(["ConnectedStatusARG", "dealer_id"])
colors = np.where(is_ctrl, C["gray"], np.where(is_leak, C["red"], C["blue"]))
ax.barh(rk["feature"], rk["IV"], color=colors, height=0.6)
for thr in (0.02, 0.1, 0.3):
    ax.axvline(thr, color=C["ink2"], linewidth=0.8, linestyle=":")
ax.set_xlabel("Information Value (gris: controles estructurales; rojo: snapshot con leakage o IV inflado por cardinalidad)")
ax.set_title("Poder discriminante univariante de las features candidatas (líneas: 0,02 / 0,1 / 0,3)", loc="left")
ax.grid(axis="y", visible=False)
save(fig, "iv_ranking")

R.write(TAB_PATH)
print(f"OK: tablas en {TAB_PATH}")
print(f"OK: figuras {PREFIX}_*.png en {FIG_DIR}")
print(rank[["feature", "IV", "dif_pp"]].head(15).to_string(index=False))
