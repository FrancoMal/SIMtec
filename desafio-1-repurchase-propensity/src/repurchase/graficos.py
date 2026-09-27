"""Figuras estáticas (PNG) para el PDF y el dashboard.

Convenciones (paleta validada para daltonismo, marcas finas, un solo eje, grilla hairline):
- categóricas en orden fijo: azul, naranja, aqua, amarillo, magenta, verde, violeta, rojo.
- secuencial: un solo tono (azul) claro→oscuro. Estados: bueno / advertencia / serio / crítico.
"""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

CAT = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#2a78d6", "#1c5cab", "#104281", "#0d366b"]
STATUS = {"bueno": "#0ca30c", "advertencia": "#fab219", "serio": "#ec835a", "critico": "#d03b3b"}
INK, INK2, MUTED, GRID, AXIS, SURFACE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "font.family": "sans-serif", "font.sans-serif": ["Segoe UI", "DejaVu Sans", "Arial"],
    "font.size": 10, "axes.titlesize": 12, "axes.titleweight": "semibold", "axes.labelsize": 10,
    "axes.edgecolor": AXIS, "axes.linewidth": 0.8, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "grid.linestyle": "-",
    "xtick.color": MUTED, "ytick.color": MUTED, "text.color": INK, "axes.labelcolor": INK2,
    "axes.titlecolor": INK, "legend.frameon": False, "legend.fontsize": 9, "lines.linewidth": 2,
    "figure.dpi": 150, "savefig.dpi": 200, "savefig.bbox": "tight",
})


def _save(fig, path: Path | str):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path); plt.close(fig)
    return path


def gains_chart(curves: dict[str, pd.DataFrame], path, title="Curva de ganancia: churners capturados según % contactado",
                highlight: str | None = None, capacity_marks=(0.1, 0.2, 0.3)):
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.plot([0, 100], [0, 100], color=AXIS, linewidth=1, label="azar (prioridad uniforme)")
    for i, (name, g) in enumerate(curves.items()):
        lw = 2.6 if name == highlight else 1.6
        ax.plot(g["pct_contactados"] * 100, g["pct_churners_capturados"] * 100, color=CAT[i % len(CAT)],
                linewidth=lw, label=name)
        if name == highlight:
            for c in capacity_marks:
                y = float(np.interp(c, g["pct_contactados"], g["pct_churners_capturados"])) * 100
                ax.plot([c * 100], [y], marker="o", markersize=6, color=CAT[i % len(CAT)],
                        markeredgecolor=SURFACE, markeredgewidth=1.5)
                ax.annotate(f"{c:.0%} contactados → {y:.0f}% de los churners", (c * 100, y),
                            xytext=(8, -14), textcoords="offset points", fontsize=8.5, color=INK2)
    ax.set_xlabel("% de la población en ventana contactada (ordenada por score)")
    ax.set_ylabel("% de los churners reales capturados")
    ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.set_title(title)
    ax.legend(loc="lower right")
    return _save(fig, path)


def lift_chart(lift: pd.DataFrame, path, title="Tasa de churn por decil de score (test, fuera de tiempo)"):
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    base = lift["churners"].sum() / lift["n"].sum()
    ax.bar(lift["decil"], lift["tasa"] * 100, color=CAT[0], width=0.72, edgecolor=SURFACE, linewidth=2)
    ax.axhline(base * 100, color=CAT[1], linewidth=1.4)
    ax.annotate(f"tasa base {base:.0%}", (10.45, base * 100), fontsize=9, color=CAT[1], va="bottom", ha="right")
    for _, r in lift.iterrows():
        ax.annotate(f"{r['lift']:.1f}×", (r["decil"], r["tasa"] * 100), xytext=(0, 3), textcoords="offset points",
                    ha="center", fontsize=8.5, color=INK2)
    ax.set_xticks(lift["decil"]); ax.set_xlabel("decil de score (1 = mayor riesgo predicho)")
    ax.set_ylabel("% que efectivamente no volvió (churn)"); ax.set_title(title)
    ax.set_ylim(0, min(100, lift["tasa"].max() * 100 + 12))
    return _save(fig, path)


def calibration_chart(tables: dict[str, pd.DataFrame], path, title="Calibración: probabilidad declarada vs. tasa observada"):
    fig, ax = plt.subplots(figsize=(5.4, 5.0))
    ax.plot([0, 100], [0, 100], color=AXIS, linewidth=1, label="calibración perfecta")
    for i, (name, t) in enumerate(tables.items()):
        ax.plot(t["score_medio"] * 100, t["tasa_observada"] * 100, marker="o", markersize=5, color=CAT[i % len(CAT)],
                markeredgecolor=SURFACE, markeredgewidth=1.2, linewidth=1.6, label=name)
    ax.set_xlabel("probabilidad de churn predicha (promedio del bin)"); ax.set_ylabel("tasa de churn observada (%)")
    ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.set_aspect("equal"); ax.set_title(title); ax.legend(loc="upper left")
    return _save(fig, path)


def pr_chart(curves: dict[str, pd.DataFrame], base_rate: float, path, title="Precisión vs. recall sobre la clase churn (test)"):
    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    ax.axhline(base_rate * 100, color=AXIS, linewidth=1)
    ax.annotate(f"tasa base {base_rate:.0%}", (99, base_rate * 100), fontsize=8.5, color=MUTED, ha="right", va="bottom")
    for i, (name, c) in enumerate(curves.items()):
        ax.plot(c["recall"] * 100, c["precision"] * 100, color=CAT[i % len(CAT)], linewidth=1.8, label=name)
    ax.set_xlabel("recall (% de churners capturados)"); ax.set_ylabel("precisión (% de contactados que eran churners)")
    ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.set_title(title); ax.legend(loc="lower left")
    return _save(fig, path)


def importance_chart(imp: pd.DataFrame, path, names: dict | None = None, top: int = 20,
                     title="Qué pesa en el modelo (importancia SHAP media, test)", value_col="mean_abs_shap"):
    d = imp.sort_values(value_col, ascending=False).head(top).iloc[::-1]
    labels = [names.get(f, f) if names else f for f in d["feature"]]
    fig, ax = plt.subplots(figsize=(7.4, 0.32 * len(d) + 1.2))
    ax.barh(labels, d[value_col], color=CAT[0], height=0.66, edgecolor=SURFACE, linewidth=2)
    ax.set_xlabel("impacto medio en la probabilidad de churn (|SHAP|, puntos porcentuales)")
    ax.set_title(title); ax.grid(axis="y", visible=False)
    return _save(fig, path)


def monthly_volume_chart(df: pd.DataFrame, path, x="mes", y="n", title="Población en ventana por mes", ylabel="vehículos"):
    fig, ax = plt.subplots(figsize=(8, 3.6))
    ax.bar(df[x].astype(str), df[y], color=CAT[0], width=0.72, edgecolor=SURFACE, linewidth=2)
    ax.set_ylabel(ylabel); ax.set_title(title); ax.tick_params(axis="x", rotation=60, labelsize=8)
    ax.grid(axis="x", visible=False)
    return _save(fig, path)


def segment_chart(seg: pd.DataFrame, path, title="Segmentos de riesgo: tamaño y tasa de churn observada (test)"):
    fig, ax = plt.subplots(figsize=(6.4, 3.8))
    colors = {"Alto": STATUS["critico"], "Medio": STATUS["serio"], "Bajo": STATUS["bueno"]}
    ax.bar(seg["segmento"], seg["tasa_churn"] * 100, color=[colors.get(s, CAT[0]) for s in seg["segmento"]],
           width=0.6, edgecolor=SURFACE, linewidth=2)
    for _, r in seg.iterrows():
        ax.annotate(f"{r['tasa_churn']:.0%} churn\n{r['n']:,} ventanas ({r['share']:.0%})", (r["segmento"], r["tasa_churn"] * 100),
                    xytext=(0, 4), textcoords="offset points", ha="center", fontsize=9, color=INK2)
    ax.set_ylabel("% que no volvió (churn observado)"); ax.set_title(title); ax.grid(axis="x", visible=False)
    ax.set_ylim(0, min(100, seg["tasa_churn"].max() * 100 + 22))
    return _save(fig, path)
