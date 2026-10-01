"""Corre uno o varios scripts del proyecto, en orden, y deja constancia de cuándo terminó y cómo.

Lo lanza corridas.lanzar() como proceso independiente: sigue corriendo aunque se cierre o recargue la página,
y al terminar escribe el código de salida en estado.json. Si un script falla, no corre los siguientes.
Uso: python ejecutor.py <carpeta_de_la_corrida> <script1.py> [<script2.py> ...]
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

carpeta, scripts = Path(sys.argv[1]), sys.argv[2:]
estado_path = carpeta / "estado.json"


def leer():
    return json.loads(estado_path.read_text(encoding="utf8"))


def guardar(e):
    estado_path.write_text(json.dumps(e, ensure_ascii=False, indent=1), encoding="utf8")


e = leer()
e["pid"] = os.getpid()  # sólo el ejecutor escribe su PID: la cancelación mata este árbol de procesos
guardar(e)
codigo = 0
with open(carpeta / "log.txt", "a", encoding="utf8", errors="replace") as log:
    for i, script in enumerate(scripts, 1):
        if len(scripts) > 1:
            log.write(f"\n===== [{i}/{len(scripts)}] {script} =====\n")
            log.flush()
        proc = subprocess.Popen([sys.executable, "-u", script], cwd=e["cwd"], stdout=log, stderr=subprocess.STDOUT)
        codigo = proc.wait()
        if codigo != 0:
            log.write(f"\n*** {script} terminó con error (código {codigo}); no se corren los siguientes ***\n")
            break
e = leer()
if e.get("fin") is None:  # si se canceló, la cancelación ya dejó su estado
    e["fin"], e["codigo"] = time.time(), codigo
    guardar(e)
