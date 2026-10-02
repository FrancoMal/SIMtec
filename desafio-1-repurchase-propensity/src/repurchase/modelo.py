"""Entrenamiento, calibración y evaluación temporal.

Diseño:
- Split TEMPORAL por fecha de scoring (criterio 2 de la ficha): train ≤ train_end < valid ≤ valid_end < test.
- Baselines de referencia: (a) prioridad uniforme = azar (lo que hace Ford hoy según la ficha), (b) heurística
  de reglas (antigüedad del vehículo + no-shows), (c) regresión logística con pocas features.
- Modelo principal: LightGBM con early stopping en valid; calibración isotónica ajustada en valid (nunca en
  test); métricas finales en test.
- Explicabilidad: SHAP (TreeExplainer) global y por registro.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import joblib
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from . import config
from .evaluacion import (calibration_table, gains_curve, lift_table, recall_at_capacity, summary_metrics)
from .features import CATEGORICAL, ID_COLS

LABEL = "label_churn"
SNAPSHOT_COLS = ["connected_status"]  # foto al momento de la extracción: se excluye por default (leakage suave)
HIGH_CARD = ["last_maint_dealer", "tma"]  # se dejan como categóricas de LightGBM (maneja alta cardinalidad)

LR_NUMERIC = ["days_since_last_maint", "days_since_last_appt", "n_maint", "n_noshow", "n_cancel", "cancel_rate",
              "vehicle_age_years", "km_per_year", "last_maint_number", "fordpass_share", "is_first_service",
              "n_recall", "n_diag", "n_repair", "months_observable", "n_customer_changes", "last_maint_late_days",
              "mean_interval_days", "fleet_size_sales", "last_rating"]
LR_CATEG = ["generation", "business_unit", "last_source", "binding_rule"]


@dataclass
class SplitConfig:
    train_end: str = "2025-09-30"
    valid_end: str = "2025-12-31"

    def to_dict(self):
        return asdict(self)


def feature_columns(df: pd.DataFrame, exclude_snapshot: bool = True) -> list[str]:
    drop = set(ID_COLS) | {LABEL, "label_no_visit", "status", "customer_id_at_scoring", "window_n",
                           "next_maint_date", "next_maint_km", "days_next_vs_due", "next_visit_date",
                           "horizon_end", "first_seen"}
    if exclude_snapshot:
        drop |= set(SNAPSHOT_COLS)
    return [c for c in df.columns if c not in drop]


def prepare_matrix(df: pd.DataFrame, cols: list[str], categories: dict | None = None):
    X = df[cols].copy()
    cats = {}
    for c in cols:
        if c in CATEGORICAL:
            if categories is not None and c in categories:
                X[c] = pd.Categorical(X[c].astype(object), categories=categories[c])
            else:
                X[c] = X[c].astype(object).astype("category")
            cats[c] = list(X[c].cat.categories)
        else:
            X[c] = pd.to_numeric(X[c], errors="coerce").astype(float)
    return X, cats


def temporal_split(df: pd.DataFrame, split: SplitConfig):
    d = pd.to_datetime(df["scoring_date"])
    tr = d <= pd.Timestamp(split.train_end)
    va = (d > pd.Timestamp(split.train_end)) & (d <= pd.Timestamp(split.valid_end))
    te = d > pd.Timestamp(split.valid_end)
    return tr.values, va.values, te.values


# --------------------------------------------------------------------------------------------------
# Modelos
# --------------------------------------------------------------------------------------------------
def heuristic_score(df: pd.DataFrame) -> np.ndarray:
    """Regla "a mano" que un analista podría usar hoy: más viejo, más no-shows/cancelaciones, menos historia
    de mantenimiento => más riesgo. Sirve para mostrar el lift incremental del modelo."""
    age = df["vehicle_age_years"].fillna(df["vehicle_age_years"].median())
    ns = df["n_noshow"].fillna(0) + 0.5 * df["n_cancel"].fillna(0)
    nm = df["n_maint"].fillna(0)
    first = df["is_first_service"].fillna(0)
    s = 0.25 * age.clip(0, 10) + 0.6 * ns.clip(0, 5) - 0.3 * nm.clip(0, 5) + 0.8 * first
    return s.values


def fit_logreg(train: pd.DataFrame) -> Pipeline:
    num = [c for c in LR_NUMERIC if c in train.columns]
    cat = [c for c in LR_CATEG if c in train.columns]
    pre = ColumnTransformer([
        ("num", Pipeline([("imp", SimpleImputer(strategy="median")), ("sc", StandardScaler())]), num),
        ("cat", Pipeline([("imp", SimpleImputer(strategy="constant", fill_value="NA")),
                          ("oh", OneHotEncoder(handle_unknown="ignore", min_frequency=50))]), cat),
    ])
    model = Pipeline([("pre", pre), ("lr", LogisticRegression(max_iter=2000, C=0.5))])
    Xtr = train[num + cat].copy()
    for c in cat:
        Xtr[c] = Xtr[c].astype(object)
    model.fit(Xtr, train[LABEL].values)
    model.lr_columns_ = num + cat
    return model


def predict_logreg(model: Pipeline, df: pd.DataFrame) -> np.ndarray:
    cols = list(model.lr_columns_)
    X = df[cols].copy()
    for c in cols:
        if c in LR_CATEG:
            X[c] = X[c].astype(object)
    return model.predict_proba(X)[:, 1]


LGB_PARAMS = dict(objective="binary", learning_rate=0.03, num_leaves=63, min_data_in_leaf=200,
                  feature_fraction=0.8, bagging_fraction=0.8, bagging_freq=1, lambda_l2=5.0,
                  cat_smooth=50, cat_l2=10, max_cat_to_onehot=8, verbose=-1, seed=42, num_threads=8)


def fit_lgbm(Xtr, ytr, Xva, yva, params: dict | None = None, rounds: int = 3000):
    params = {**LGB_PARAMS, **(params or {})}
    dtr = lgb.Dataset(Xtr, label=ytr, free_raw_data=False)
    dva = lgb.Dataset(Xva, label=yva, reference=dtr, free_raw_data=False)
    booster = lgb.train(params, dtr, num_boost_round=rounds, valid_sets=[dva],
                        callbacks=[lgb.early_stopping(150, verbose=False), lgb.log_evaluation(0)])
    return booster


def fit_calibrator(p_valid: np.ndarray, y_valid: np.ndarray) -> IsotonicRegression:
    iso = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
    iso.fit(p_valid, y_valid)
    return iso


# --------------------------------------------------------------------------------------------------
# Corrida completa
# --------------------------------------------------------------------------------------------------
def evaluate_all(y: np.ndarray, scores: dict[str, np.ndarray]) -> tuple[pd.DataFrame, dict]:
    rows, tables = [], {}
    for name, p in scores.items():
        m = summary_metrics(y, p); m["modelo"] = name
        rows.append(m)
        tables[name] = {"lift": lift_table(y, p), "capacity": recall_at_capacity(y, p),
                        "calibration": calibration_table(y, p)["table"], "gains": gains_curve(y, p)}
    return pd.DataFrame(rows).set_index("modelo"), tables


def run_training(data: pd.DataFrame, split: SplitConfig = SplitConfig(), out_dir: Path | None = None,
                 exclude_snapshot: bool = True, lgb_params: dict | None = None) -> dict:
    """data = ventanas evaluables con features y label. Devuelve artefactos y métricas; persiste en out_dir."""
    out_dir = Path(out_dir or config.MODELS_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    data = data[data[LABEL].notna()].reset_index(drop=True)
    tr, va, te = temporal_split(data, split)
    for nombre, mascara in (("entrenamiento", tr), ("calibración", va), ("evaluación", te)):
        if not mascara.any() or data.loc[mascara, LABEL].nunique() < 2:
            raise ValueError(f"El período de {nombre} necesita ventanas evaluables con retornos y abandonos. "
                             "Revisá las fechas elegidas o cargá un dataset con más historia.")
    cols = feature_columns(data, exclude_snapshot=exclude_snapshot)
    Xtr, cats = prepare_matrix(data.loc[tr], cols)
    Xva, _ = prepare_matrix(data.loc[va], cols, cats)
    Xte, _ = prepare_matrix(data.loc[te], cols, cats)
    ytr, yva, yte = (data.loc[m, LABEL].values for m in (tr, va, te))

    booster = fit_lgbm(Xtr, ytr, Xva, yva, lgb_params)
    p_va_raw = booster.predict(Xva, num_iteration=booster.best_iteration)
    p_te_raw = booster.predict(Xte, num_iteration=booster.best_iteration)
    iso = fit_calibrator(p_va_raw, yva)
    p_te = iso.predict(p_te_raw)

    lr = fit_logreg(data.loc[tr])
    p_te_lr_raw = predict_logreg(lr, data.loc[te])
    iso_lr = fit_calibrator(predict_logreg(lr, data.loc[va]), yva)
    p_te_lr = iso_lr.predict(p_te_lr_raw)

    rng = np.random.default_rng(0)
    scores = {
        "azar (prioridad uniforme, situación actual)": rng.random(len(yte)),
        "heurística de reglas": heuristic_score(data.loc[te]),
        "regresión logística (calibrada)": p_te_lr,
        "LightGBM sin calibrar": p_te_raw,
        "LightGBM calibrado (isotónica)": p_te,
    }
    metrics, tables = evaluate_all(yte, scores)

    # Importancia (gain) e info de la corrida
    imp = pd.DataFrame({"feature": booster.feature_name(),
                        "gain": booster.feature_importance("gain"),
                        "split": booster.feature_importance("split")}).sort_values("gain", ascending=False)
    imp["gain_pct"] = imp["gain"] / imp["gain"].sum()

    info = {
        "split": split.to_dict(), "n_train": int(tr.sum()), "n_valid": int(va.sum()), "n_test": int(te.sum()),
        "base_rate_train": float(ytr.mean()), "base_rate_valid": float(yva.mean()), "base_rate_test": float(yte.mean()),
        "best_iteration": int(booster.best_iteration), "n_features": len(cols), "exclude_snapshot": exclude_snapshot,
        "lgb_params": {**LGB_PARAMS, **(lgb_params or {})},
        "test_scoring_range": [str(data.loc[te, "scoring_date"].min().date()), str(data.loc[te, "scoring_date"].max().date())],
    }
    booster.save_model(str(out_dir / "lgbm.txt"))
    joblib.dump({"calibrator": iso, "columns": cols, "categories": cats, "logreg": lr, "calibrator_lr": iso_lr,
                 "split": split.to_dict()}, out_dir / "artefactos.joblib")
    metrics.to_csv(out_dir / "metricas_test.csv")
    imp.to_csv(out_dir / "importancia.csv", index=False)
    (out_dir / "info.json").write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf8")
    for name, t in tables.items():
        slug = name.split(" (")[0].replace(" ", "_")
        t["lift"].to_csv(out_dir / f"lift_{slug}.csv", index=False)
        t["capacity"].to_csv(out_dir / f"capacidad_{slug}.csv", index=False)
        t["calibration"].to_csv(out_dir / f"calibracion_{slug}.csv", index=False)
    test_scored = data.loc[te, ["window_id", "vehicle_id", "customer_id", "scoring_date", LABEL]].copy()
    test_scored["p_lgbm_raw"] = p_te_raw; test_scored["p_lgbm_cal"] = p_te; test_scored["p_logreg"] = p_te_lr
    test_scored.to_parquet(out_dir / "test_scored.parquet", index=False)
    return {"booster": booster, "calibrator": iso, "columns": cols, "categories": cats, "logreg": lr,
            "metrics": metrics, "tables": tables, "importance": imp, "info": info, "masks": (tr, va, te),
            "test_scored": test_scored, "X_test": Xte, "y_test": yte}


def predict_calibrated(artefacts_dir: Path, df: pd.DataFrame) -> np.ndarray:
    art = joblib.load(Path(artefacts_dir) / "artefactos.joblib")
    booster = lgb.Booster(model_file=str(Path(artefacts_dir) / "lgbm.txt"))
    X, _ = prepare_matrix(df, art["columns"], art["categories"])
    return art["calibrator"].predict(booster.predict(X, num_iteration=booster.best_iteration))
