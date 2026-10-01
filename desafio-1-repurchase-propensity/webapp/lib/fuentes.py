"""Rutas de la webapp y lectura (con caché) de las salidas del proyecto.

La webapp vive dentro del proyecto (desafio-1-repurchase-propensity/webapp) y por defecto lee la carpeta padre:
no hace falta configurar nada. SIMTEC_REPO permite apuntarla a otra copia del proyecto.
Las salidas (data/, reports/figures, reports/modelo, reports/eda, notebooks) NO vienen en el repo: se generan
con las corridas. Mientras no existan, las páginas lo dicen y mandan a "Corridas".
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.dont_write_bytecode = True

WEBAPP = Path(__file__).resolve().parents[1]
REPO = Path(os.environ.get("SIMTEC_REPO", WEBAPP.parent)).resolve()
CORRIDAS = WEBAPP / "corridas"            # logs y estado de las corridas (ignorado por git)
ENTREGABLES = REPO.parent / "entregables"  # documentos finales versionados en la raíz del repo


def rutas() -> dict[str, Path]:
    r = REPO
    return {"raiz": r, "data": r / "data", "processed": r / "data" / "processed", "models": r / "data" / "models",
            "interim": r / "data" / "interim", "reports": r / "reports", "figures": r / "reports" / "figures",
            "modelo": r / "reports" / "modelo", "docs": r / "docs"}


def mtime(p: Path) -> float:
    try:
        return p.stat().st_mtime
    except FileNotFoundError:
        return 0.0


@st.cache_data(show_spinner=False)
def _leer_parquet(path: str, _mt: float) -> pd.DataFrame:
    return pd.read_parquet(path)


@st.cache_data(show_spinner=False)
def _leer_csv(path: str, _mt: float) -> pd.DataFrame:
    return pd.read_csv(path)


@st.cache_data(show_spinner=False)
def _leer_texto(path: str, _mt: float) -> str:
    return Path(path).read_text(encoding="utf8")


def scores() -> pd.DataFrame:
    p = rutas()["processed"] / "scores_actuales.parquet"
    return _leer_parquet(str(p), mtime(p))


def csv(p: Path) -> pd.DataFrame:
    return _leer_csv(str(p), mtime(p))


def texto(p: Path) -> str:
    return _leer_texto(str(p), mtime(p))


SALIDAS_PIPELINE = ["data/processed/scores_actuales.parquet", "data/models/metricas_test.csv",
                    "data/models/capacidad_LightGBM_calibrado.csv", "data/models/info.json",
                    "reports/modelo/resumen.md", "reports/figures/modelo/ganancia.png"]


def requiere(*relativas: str, que: str = "el pipeline completo"):
    """Si faltan salidas, explica qué correr y corta la página (en vez de romperse)."""
    faltan = [x for x in relativas if not (REPO / x).exists()]
    if faltan:
        st.warning(f"Todavía no hay resultados para mostrar en esta página. Primero hay que correr **{que}** "
                   "desde **Corridas** (el repositorio no trae salidas generadas: se recalculan en cada máquina).",
                   icon="⏳")
        st.page_link("paginas/corridas.py", label="Ir a Corridas", icon="⚙️")
        with st.expander("Archivos que faltan"):
            st.code("\n".join(faltan), language=None)
        st.stop()


def etiqueta_fuente():
    st.caption(f"Resultados calculados en esta máquina · proyecto: `{REPO}`")


def pct(x: float, dec: int = 0) -> str:
    return f"{x * 100:.{dec}f} %".replace(".", ",")


def miles(x: float) -> str:
    return f"{x:,.0f}".replace(",", ".")
