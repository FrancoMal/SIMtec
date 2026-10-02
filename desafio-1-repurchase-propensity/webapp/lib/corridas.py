"""Corridas en segundo plano: una a la vez, con log en vivo, cancelación e historial.

Corren en el propio proyecto (cwd = desafio-1-repurchase-propensity) con el mismo Python que ejecuta la webapp.
Las salidas que generan están en .gitignore, así que recalcular no modifica nada versionado.
Cada corrida vive en webapp/corridas/<id>/ con log.txt y estado.json.
"""
from __future__ import annotations

import ctypes
import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from lib.fuentes import CORRIDAS, REPO, WEBAPP
from lib.datasets import activo as dataset_activo

EDA = tuple(sorted(f"scripts/eda/{p.name}" for p in (REPO / "scripts" / "eda").glob("*.py")))


@dataclass(frozen=True)
class Tarea:
    clave: str
    titulo: str
    scripts: tuple[str, ...]
    duracion: str           # medida en una corrida desde cero
    que_hace: str
    necesita_pipeline: bool = True


TAREAS = [
    Tarea("pipeline", "Pipeline completo", ("scripts/run_pipeline.py",), "~1,5 min",
          "Datos crudos → ventanas → modelo → scoring y SHAP → prioridad de contacto por cliente. Es lo primero que hay que correr: "
          "sin esto la demo no tiene datos.", necesita_pipeline=False),
    Tarea("contacto", "Segunda etapa: priorizar contactos", ("scripts/run_contacto.py",), "~5 s",
          "Reúne Alto + Medio, aplica las reglas operativas y consolida por cliente usando el scoring ya calculado."),
    Tarea("eda", "Análisis exploratorio", EDA, "~9 min",
          "Los 13 análisis exploratorios con su verificación independiente (informes, tablas y figuras)."),
    Tarea("notebooks", "Notebooks de evidencia", ("scripts/build_notebooks.py",), "~1 min",
          "Genera y ejecuta los tres notebooks (EDA, target y ventanas, modelo)."),
    Tarea("diccionario", "Diccionario del dataset", ("scripts/diccionario_dataset.py",), "~5 s",
          "Documenta las columnas del dataset analítico."),
    Tarea("sensibilidad", "Sensibilidad de la ventana", ("scripts/sensibilidad_ventana.py",), "~3 min",
          "Prueba 36 combinaciones de reglas de ventana y horizonte."),
    Tarea("ablaciones", "Ablaciones", ("scripts/ablaciones.py",), "~1 min",
          "Nueve variantes del modelo sobre el mismo test (leakage y robustez)."),
]
TODO = Tarea("todo", "Recalcular todo (sin el informe)",
             ("scripts/run_pipeline.py",) + EDA + ("scripts/build_notebooks.py", "scripts/diccionario_dataset.py",
                                                   "scripts/sensibilidad_ventana.py", "scripts/ablaciones.py"),
             "~15 min", "Todo lo anterior, en orden. No regenera el informe.", necesita_pipeline=False)
POR_CLAVE = {t.clave: t for t in TAREAS + [TODO]}
EJECUTOR = WEBAPP / "lib" / "ejecutor.py"


def pipeline_corrido() -> bool:
    return (dataset_activo()["resultados"] / "data" / "processed" / "scores_actuales.parquet").exists()


def _vivo(pid: int | None) -> bool:
    if not pid:
        return False
    if os.name != "nt":
        try:
            os.kill(int(pid), 0)
            return True
        except OSError:
            return False
    k = ctypes.windll.kernel32
    k.OpenProcess.restype = ctypes.c_void_p
    k.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_bool, ctypes.c_ulong]
    k.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
    k.CloseHandle.argtypes = [ctypes.c_void_p]
    h = k.OpenProcess(0x1000, False, int(pid))  # PROCESS_QUERY_LIMITED_INFORMATION
    if not h:
        return False
    code = ctypes.c_ulong()
    k.GetExitCodeProcess(h, ctypes.byref(code))
    k.CloseHandle(h)
    return code.value == 259  # STILL_ACTIVE


def _guardar(carpeta: Path, e: dict):
    e = {k: v for k, v in e.items() if k != "carpeta"}
    (carpeta / "estado.json").write_text(json.dumps(e, ensure_ascii=False, indent=1), encoding="utf8")


def _leer(carpeta: Path) -> dict | None:
    try:
        e = json.loads((carpeta / "estado.json").read_text(encoding="utf8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    e["carpeta"] = str(carpeta)
    recien = time.time() - e.get("inicio", 0) < 15 and not e.get("pid")
    if e.get("fin") is None and not recien and not _vivo(e.get("pid")):  # murió sin avisar
        e["fin"], e["codigo"] = e.get("inicio"), "interrumpida"
        _guardar(carpeta, e)
    return e


def historial(todos: bool = False) -> list[dict]:
    if not CORRIDAS.exists():
        return []
    out = [_leer(c) for c in sorted(CORRIDAS.iterdir(), reverse=True) if c.is_dir()]
    elegido = dataset_activo()["id"]
    return [e for e in out if e and (todos or e.get("dataset_id", "original") == elegido)]


def activa() -> dict | None:
    return next((e for e in historial(todos=True) if e.get("fin") is None), None)


def lanzar(clave: str) -> dict:
    if activa():
        raise RuntimeError("Ya hay una corrida en curso: esperá a que termine o cancelala.")
    t = POR_CLAVE[clave]
    d = dataset_activo()
    if d["id"] != "original" and clave not in ("pipeline", "contacto"):
        raise RuntimeError("Para los datasets cargados están disponibles el Pipeline completo y la segunda etapa.")
    if t.necesita_pipeline and not pipeline_corrido():
        raise RuntimeError("Primero hay que correr el pipeline completo.")
    carpeta = CORRIDAS / f"{time.strftime('%Y%m%d-%H%M%S')}_{clave}"
    carpeta.mkdir(parents=True)
    _guardar(carpeta, {"clave": clave, "titulo": t.titulo, "scripts": list(t.scripts), "cwd": str(REPO),
                       "dataset_id": d["id"], "dataset_nombre": d["nombre"], "params": str(d["params"]),
                       "raw": str(d["raw"]), "resultados": str(d["resultados"]), "cutoff": d["cutoff"],
                       "inicio": time.time(), "fin": None, "codigo": None, "pid": None})
    (carpeta / "log.txt").write_text(f"Dataset: {d['nombre']} ({d['id']})\nDatos: {d['raw']}\n"
                                     f"Resultados: {d['resultados']}\nCorte: {d['cutoff']}\n"
                                     f"$ {' && '.join(t.scripts)}\n  (en {REPO}, con {sys.executable})\n",
                                     encoding="utf8")
    env = {**os.environ, "PYTHONPATH": "src", "PYTHONIOENCODING": "utf8", "PYTHONDONTWRITEBYTECODE": "1",
           "PYTHONUNBUFFERED": "1", "MPLBACKEND": "Agg", "SIMTEC_DATASET": str(d["raw"]),
           "SIMTEC_OUTPUT_DIR": str(d["resultados"]), "SIMTEC_CUTOFF": d["cutoff"]}
    flags = (0x00000200 | 0x08000000) if os.name == "nt" else 0  # nuevo grupo de procesos, sin ventana
    subprocess.Popen([sys.executable, str(EJECUTOR), str(carpeta), *t.scripts], cwd=str(REPO), env=env,
                     creationflags=flags, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, close_fds=True)
    for _ in range(50):  # el ejecutor escribe su PID al arrancar
        e = _leer(carpeta)
        if e and e.get("pid"):
            return e
        time.sleep(0.1)
    return _leer(carpeta) or {}


def cancelar(e: dict):
    if e.get("pid"):
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(e["pid"]), "/T", "/F"], capture_output=True)
        else:
            os.killpg(os.getpgid(int(e["pid"])), 9)
    carpeta = Path(e["carpeta"])
    e2 = _leer(carpeta) or e
    e2["fin"], e2["codigo"] = time.time(), "cancelada"
    _guardar(carpeta, e2)
    with open(carpeta / "log.txt", "a", encoding="utf8") as f:
        f.write("\n--- cancelada desde la webapp ---\n")


def log(e: dict, ultimas: int = 400) -> str:
    try:
        lineas = (Path(e["carpeta"]) / "log.txt").read_text(encoding="utf8", errors="replace").splitlines()
    except FileNotFoundError:
        return ""
    return "\n".join(lineas[-ultimas:])
