"""Prueba del recorrido de la demo con el Chrome del sistema: carga cada página, mide el tiempo hasta que
termina de dibujarse, saca una captura y falla si Streamlit muestra una excepción.
Uso (con la app corriendo en :8510): .venv\\Scripts\\python.exe chequeos\\recorrido.py"""
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = "http://localhost:8510"
OUT = Path(__file__).parent / "capturas"
OUT.mkdir(exist_ok=True)
PAGINAS = ["", "bandeja", "caso", "resultados", "lista", "dashboard", "evidencia", "documentos", "datasets", "corridas"]


def esperar(pg):
    pg.wait_for_selector("[data-testid='stMain']", timeout=60000)
    pg.wait_for_timeout(400)
    pg.wait_for_function("() => !document.querySelector('[data-testid=\"stStatusWidget\"]')", timeout=90000)
    pg.wait_for_timeout(600)


errores = []
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=True)
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    for nombre in PAGINAS:
        t0 = time.time()
        pg.goto(f"{URL}/{nombre}", wait_until="networkidle")
        esperar(pg)
        dt = time.time() - t0
        exc = pg.locator("[data-testid='stException']")
        n_exc = exc.count()
        if n_exc:
            errores.append((nombre or "inicio", exc.first.inner_text()[:600]))
        pg.screenshot(path=str(OUT / f"{nombre or 'inicio'}.png"), full_page=True)
        print(f"{nombre or 'inicio':12} {dt:5.1f} s  {'ERROR' if n_exc else 'ok'}")
    b.close()
for n, e in errores:
    print(f"\n--- {n} ---\n{e}")
sys.exit(1 if errores else 0)
