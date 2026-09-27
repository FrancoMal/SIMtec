"""Métricas de evaluación orientadas a la decisión de negocio.

Además de ROC-AUC / PR-AUC (criterio 3 de la ficha), lo que importa operativamente es: si contacto al X %
de la población en ventana (capacidad finita), ¿qué fracción de los churners atrapo? (recall a capacidad),
¿cuántos contactos por churner? (precisión) y ¿la probabilidad declarada es real? (calibración).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.metrics import (average_precision_score, brier_score_loss, log_loss, precision_recall_curve,
                             roc_auc_score)


def summary_metrics(y: np.ndarray, p: np.ndarray) -> dict:
    y = np.asarray(y, dtype=float); p = np.asarray(p, dtype=float)
    out = {
        "n": int(len(y)),
        "base_rate": float(y.mean()),
        "roc_auc": float(roc_auc_score(y, p)),
        "pr_auc": float(average_precision_score(y, p)),
    }
    es_prob = bool((p >= 0).all() and (p <= 1).all())
    if es_prob:  # las métricas probabilísticas solo tienen sentido para scores en [0, 1]
        out["brier"] = float(brier_score_loss(y, p))
        out["log_loss"] = float(log_loss(y, np.clip(p, 1e-6, 1 - 1e-6)))
        out["ece"] = float(calibration_table(y, p)["ece"])
    else:
        out["brier"] = out["log_loss"] = out["ece"] = np.nan
    return out


def lift_table(y: np.ndarray, p: np.ndarray, n_bins: int = 10) -> pd.DataFrame:
    """Decil 1 = mayor score. Lift = tasa del decil / tasa base. cum_recall = % de churners capturados."""
    df = pd.DataFrame({"y": np.asarray(y, dtype=float), "p": np.asarray(p, dtype=float)})
    df = df.sort_values("p", ascending=False).reset_index(drop=True)
    df["decil"] = (np.arange(len(df)) * n_bins // len(df)) + 1
    base = df["y"].mean()
    t = df.groupby("decil").agg(n=("y", "size"), churners=("y", "sum"), p_medio=("p", "mean"), tasa=("y", "mean"))
    t["lift"] = t["tasa"] / base
    t["cum_churners"] = t["churners"].cumsum()
    t["cum_recall"] = t["cum_churners"] / df["y"].sum()
    t["cum_n"] = t["n"].cumsum()
    t["cum_precision"] = t["cum_churners"] / t["cum_n"]
    t["cum_lift"] = t["cum_precision"] / base
    return t.reset_index()


def recall_at_capacity(y: np.ndarray, p: np.ndarray, fractions=(0.05, 0.1, 0.2, 0.3, 0.4, 0.5)) -> pd.DataFrame:
    df = pd.DataFrame({"y": np.asarray(y, dtype=float), "p": np.asarray(p, dtype=float)})
    df = df.sort_values("p", ascending=False).reset_index(drop=True)
    total = df["y"].sum(); base = df["y"].mean()
    rows = []
    for f in fractions:
        k = max(1, int(round(f * len(df))))
        top = df.iloc[:k]
        rows.append({"capacidad_pct": f, "contactados": k, "churners_capturados": int(top["y"].sum()),
                     "recall": top["y"].sum() / total, "precision": top["y"].mean(),
                     "lift": top["y"].mean() / base, "umbral_score": float(top["p"].iloc[-1])})
    return pd.DataFrame(rows)


def recall_at_monthly_capacity(df: pd.DataFrame, k_per_month: int, p_col: str = "p", y_col: str = "y",
                               date_col: str = "scoring_date") -> dict:
    """Capacidad absoluta por mes de scoring: contacto los k de mayor score de cada mes."""
    d = df[[date_col, p_col, y_col]].copy()
    d["mes"] = pd.to_datetime(d[date_col]).dt.to_period("M")
    caught = 0; contacted = 0; total = d[y_col].sum()
    for _, g in d.groupby("mes"):
        top = g.sort_values(p_col, ascending=False).head(k_per_month)
        caught += top[y_col].sum(); contacted += len(top)
    return {"k_por_mes": k_per_month, "contactados": int(contacted), "churners_capturados": int(caught),
            "recall": float(caught / total) if total else np.nan,
            "precision": float(caught / contacted) if contacted else np.nan,
            "meses": int(d["mes"].nunique())}


def calibration_table(y: np.ndarray, p: np.ndarray, n_bins: int = 10) -> dict:
    """Bins de igual cantidad (cuantiles). ECE = promedio ponderado de |tasa observada - score medio|."""
    df = pd.DataFrame({"y": np.asarray(y, dtype=float), "p": np.asarray(p, dtype=float)})
    df["bin"] = pd.qcut(df["p"].rank(method="first"), n_bins, labels=False)
    t = df.groupby("bin").agg(n=("y", "size"), score_medio=("p", "mean"), tasa_observada=("y", "mean"))
    t["gap"] = (t["tasa_observada"] - t["score_medio"]).abs()
    ece = float((t["gap"] * t["n"]).sum() / t["n"].sum())
    return {"table": t.reset_index(), "ece": ece}


def precision_recall_points(y: np.ndarray, p: np.ndarray) -> pd.DataFrame:
    pr, rc, th = precision_recall_curve(y, p)
    return pd.DataFrame({"precision": pr[:-1], "recall": rc[:-1], "umbral": th})


def gains_curve(y: np.ndarray, p: np.ndarray, n_points: int = 101) -> pd.DataFrame:
    df = pd.DataFrame({"y": np.asarray(y, dtype=float), "p": np.asarray(p, dtype=float)})
    df = df.sort_values("p", ascending=False).reset_index(drop=True)
    cum = df["y"].cumsum() / df["y"].sum()
    xs = np.linspace(0, 1, n_points)
    idx = np.clip((xs * len(df)).astype(int) - 1, 0, len(df) - 1)
    ys = np.where(xs == 0, 0.0, cum.values[idx])
    return pd.DataFrame({"pct_contactados": xs, "pct_churners_capturados": ys})
