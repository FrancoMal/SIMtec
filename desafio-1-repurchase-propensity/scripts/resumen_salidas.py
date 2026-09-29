"""Imprime un cuadro resumen de las salidas de una corrida (lo llama ejecutar.bat al terminar cada opción).

Uso: python scripts/resumen_salidas.py <pipeline|notebooks|informe|diccionario|complementarios|todo> [segundos]
Muestra, para la opción, los archivos generados (fecha, tamaño, si son de esta corrida) y las cifras clave.
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANCHO = 96

SALIDAS = {
    "pipeline": [
        ("Dataset analítico", "data/processed/dataset_analitico.parquet"),
        ("Ventanas", "data/processed/ventanas.parquet"),
        ("Ranking actual (CSV)", "data/processed/scores_actuales.csv"),
        ("Ranking por usuario", "data/processed/scores_actuales_por_usuario.parquet"),
        ("Modelo LightGBM", "data/models/lgbm.txt"),
        ("Calibrador y encoders", "data/models/artefactos.joblib"),
        ("Métricas en test", "data/models/metricas_test.csv"),
        ("Resumen de la corrida", "reports/modelo/resumen.md"),
        ("Figuras del modelo", "reports/figures/modelo"),
    ],
    "notebooks": [
        ("Notebook EDA", "notebooks/01_eda.ipynb"),
        ("Notebook target y ventanas", "notebooks/02_target_y_ventanas.ipynb"),
        ("Notebook modelo", "notebooks/03_modelo.ipynb"),
    ],
    "informe": [
        ("Informe Word (template Ford)", "reports/informe_final.docx"),
        ("Informe PDF", "reports/informe_final.pdf"),
    ],
    "diccionario": [
        ("Diccionario del dataset", "docs/diccionario_dataset_analitico.md"),
    ],
    "complementarios": [
        ("Sensibilidad de ventana", "reports/modelo/sensibilidad_ventana.csv"),
        ("Ablaciones (tabla)", "reports/modelo/ablaciones.csv"),
        ("Ablaciones (informe)", "reports/modelo/ablaciones.md"),
    ],
}
SALIDAS["todo"] = SALIDAS["pipeline"] + SALIDAS["notebooks"] + SALIDAS["diccionario"] + SALIDAS["informe"]


def tam(p: Path) -> str:
    if p.is_dir():
        n = sum(1 for _ in p.glob("*") if _.is_file())
        return f"{n} archivos"
    b = p.stat().st_size
    return f"{b/1e6:.1f} MB" if b >= 1e6 else f"{b/1e3:.0f} KB"


def fila(izq: str, der: str = "") -> str:
    izq = izq[: ANCHO - 4]
    return "│ " + izq.ljust(ANCHO - 4) + " │" if not der else "│ " + (izq.ljust(ANCHO - 4 - len(der)) + der)[: ANCHO - 4] + " │"


def sep(c="─") -> str:
    return "├" + c * (ANCHO - 2) + "┤"


def fmt_n(x) -> str:
    return f"{int(x):,}".replace(",", ".")


def cifras(opcion: str) -> list[str]:
    out: list[str] = []
    if opcion in ("pipeline", "todo"):
        try:
            info = json.loads((ROOT / "data/models/info.json").read_text(encoding="utf8"))
            out.append(f"Split temporal: train {fmt_n(info['n_train'])} / valid {fmt_n(info['n_valid'])} / test {fmt_n(info['n_test'])} ventanas; "
                       f"churn en test {info['base_rate_test']*100:.1f} %")
            out.append(f"Features: {info['n_features']}  |  iteraciones: {info['best_iteration']}  |  snapshot excluido: {info['exclude_snapshot']}")
        except Exception as e:  # noqa: BLE001
            out.append(f"(sin info.json: {e})")
        try:
            import csv
            with open(ROOT / "data/models/metricas_test.csv", encoding="utf8") as h:
                rows = list(csv.DictReader(h))
            for r in rows:
                if r["modelo"].startswith("LightGBM calibrado") or r["modelo"].startswith("azar"):
                    nombre = "LightGBM calibrado" if r["modelo"].startswith("Light") else "azar (situación actual)"
                    ece = f"  ECE {float(r['ece']):.3f}" if r.get("ece") else ""
                    out.append(f"{nombre:24s} ROC-AUC {float(r['roc_auc']):.3f}  PR-AUC {float(r['pr_auc']):.3f}{ece}")
        except Exception as e:  # noqa: BLE001
            out.append(f"(sin metricas_test.csv: {e})")
        try:
            import pandas as pd
            sc = pd.read_parquet(ROOT / "data/processed/scores_actuales.parquet", columns=["segmento", "tiene_turno_agendado", "prob_churn"])
            seg = sc["segmento"].value_counts()
            out.append(f"Ranking actual: {fmt_n(len(sc))} vehículos  |  Alto {fmt_n(seg.get('Alto', 0))}  Medio {fmt_n(seg.get('Medio', 0))}  "
                       f"Bajo {fmt_n(seg.get('Bajo', 0))}  |  con turno ya agendado {fmt_n(sc['tiene_turno_agendado'].fillna(False).astype(bool).sum())}")
        except Exception as e:  # noqa: BLE001
            out.append(f"(sin scores_actuales.parquet: {e})")
    if opcion in ("notebooks", "todo"):
        try:
            for nb in sorted((ROOT / "notebooks").glob("0*.ipynb")):
                j = json.loads(nb.read_text(encoding="utf8"))
                cells = [c for c in j["cells"] if c["cell_type"] == "code"]
                errs = sum(1 for c in cells for o in c.get("outputs", []) if o.get("output_type") == "error")
                out.append(f"{nb.name:32s} {len(cells):3d} celdas de código, {errs} con error")
        except Exception as e:  # noqa: BLE001
            out.append(f"(notebooks: {e})")
    if opcion in ("informe", "todo"):
        try:
            from pypdf import PdfReader
            r = PdfReader(str(ROOT / "reports/informe_final.pdf"))
            txt = "\n".join(p.extract_text() or "" for p in r.pages)
            placeholders = [k for k in ("(Título", "Nombre del equipo", "Sección a completar", "Actualizar campo") if k in txt]
            out.append(f"PDF: {len(r.pages)} páginas" + ("" if not placeholders else f"  ATENCIÓN, placeholders del template: {placeholders}"))
            if "Apellido, Nombre" in txt:
                out.append("Portada: faltan integrantes (filas 'Apellido, Nombre' en la tabla)")
        except Exception as e:  # noqa: BLE001
            out.append(f"(pdf: {e})")
    if opcion in ("diccionario", "todo"):
        try:
            t = (ROOT / "docs/diccionario_dataset_analitico.md").read_text(encoding="utf8")
            filas = t.count("\n| `")
            import re
            m = re.search(r"\*\*Filas\*\*: ([\d.]+) ventanas, ([\d.]+) vehículos.*?churn = ([\d,]+ %)", t)
            if m:
                out.append(f"Dataset: {m.group(1)} ventanas, {m.group(2)} vehículos, churn {m.group(3)}")
            m = re.search(r"\*\*Columnas\*\*: (\d+) \((\d+) columnas de features, de las que el modelo usa (\d+)", t)
            if m:
                out.append(f"Columnas: {m.group(1)} ({m.group(2)} de features, el modelo usa {m.group(3)})")
            out.append(f"{filas} columnas documentadas (dataset + ranking)")
        except Exception as e:  # noqa: BLE001
            out.append(f"(diccionario: {e})")
    if opcion == "complementarios":
        try:
            import pandas as pd
            ab = pd.read_csv(ROOT / "reports/modelo/ablaciones.csv")
            cols = [c for c in ab.columns if "auc" in c.lower()]
            out.append(f"Ablaciones: {len(ab)} variantes evaluadas ({', '.join(cols[:2])})")
            sv = pd.read_csv(ROOT / "reports/modelo/sensibilidad_ventana.csv")
            out.append(f"Sensibilidad de ventana: {len(sv)} combinaciones de parámetros")
        except Exception as e:  # noqa: BLE001
            out.append(f"(complementarios: {e})")
    return out


def main() -> None:
    marca = ROOT / "data" / ".inicio_corrida"  # ejecutar.bat guarda acá la hora de inicio (data/ está fuera de git)
    if len(sys.argv) > 1 and sys.argv[1] == "--inicio":
        marca.parent.mkdir(exist_ok=True)
        marca.write_text(str(int(time.time())), encoding="utf8")
        return
    opcion = (sys.argv[1] if len(sys.argv) > 1 else "pipeline").lower()
    inicio = None
    args = [a for a in sys.argv[2:] if a != "--sin-inicio"]
    if args:
        inicio = float(args[0])
    elif marca.exists() and "--sin-inicio" not in sys.argv:
        try:
            inicio = float(marca.read_text(encoding="utf8").strip())
        except ValueError:
            inicio = None
    ahora = time.time()
    salidas = SALIDAS.get(opcion, [])
    print()
    print("┌" + "─" * (ANCHO - 2) + "┐")
    print(fila(f"RESUMEN DE LA CORRIDA: {opcion.upper()}", datetime.now().strftime("%Y-%m-%d %H:%M")))
    if inicio:
        print(fila(f"Duración: {(ahora - inicio)/60:.1f} min"))
    print(sep())
    print(fila("Salida", "Fecha            Tamaño   Estado"))
    print(sep("┄"))
    faltan = viejos = 0
    for nombre, rel in salidas:
        p = ROOT / rel
        if not p.exists():
            faltan += 1
            print(fila(f"{nombre}  ({rel})", "NO EXISTE"))
            continue
        m = max((f.stat().st_mtime for f in p.glob("*")), default=p.stat().st_mtime) if p.is_dir() else p.stat().st_mtime
        nuevo = inicio is None or m >= inicio - 5
        if not nuevo:
            viejos += 1
        estado = "generado ahora" if nuevo and inicio else ("ok" if nuevo else "de una corrida anterior")
        print(fila(f"{nombre}", f"{datetime.fromtimestamp(m):%d/%m %H:%M}  {tam(p):>9s}   {estado}"))
    c = cifras(opcion)
    if c:
        print(sep())
        print(fila("Cifras clave"))
        print(sep("┄"))
        for linea in c:
            print(fila(linea))
    print(sep())
    if faltan or viejos:
        print(fila(f"ATENCIÓN: {faltan} salidas faltan, {viejos} no se regeneraron en esta corrida"))
    else:
        print(fila("Todas las salidas están presentes" + (" y son de esta corrida" if inicio else "")))
    print("└" + "─" * (ANCHO - 2) + "┘")
    print()


if __name__ == "__main__":
    main()
