"""Prueba de interacción: bandeja -> caso guiado, y una corrida en segundo plano sin congelar la navegación.
Uso (con la app corriendo en :8510): .venv\\Scripts\\python.exe chequeos\\interaccion.py"""
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = "http://localhost:8510"
OUT = Path(__file__).parent / "capturas"


def quieta(pg, t=90000):
    pg.wait_for_selector("[data-testid='stMain']", timeout=t)
    pg.wait_for_timeout(500)
    pg.wait_for_function("() => !document.querySelector('[data-testid=\"stStatusWidget\"]')", timeout=t)
    pg.wait_for_timeout(500)


with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=True)
    pg = b.new_page(viewport={"width": 1440, "height": 900})

    # 1) bandeja -> elegir la fila 3 -> caso guiado muestra ese vehículo
    pg.goto(f"{URL}/bandeja"); quieta(pg)
    grid = pg.locator("[data-testid='stDataFrame']").first
    box = grid.bounding_box()
    pg.mouse.click(box["x"] + 18, box["y"] + 36 + 35 * 2 + 17)  # casilla de la tercera fila
    quieta(pg)
    elegido = pg.locator("[data-testid='stAlertContentSuccess']").inner_text()
    vid = elegido.split("**")[-1] if "**" in elegido else elegido.split("Elegido:")[1].split("·")[0].strip()
    pg.get_by_role("button", name="Ver el caso contado").click(); quieta(pg)
    valor = pg.locator("input[aria-label='Vehículo']").input_value()
    print("bandeja -> caso:", "OK" if valor == vid else f"FALLA ({vid!r} vs {valor!r})", "|", vid)
    pg.screenshot(path=str(OUT / "caso_elegido.png"))

    # 2) lanzar el pipeline desde la web y navegar mientras corre
    pg.goto(f"{URL}/corridas"); quieta(pg)
    pg.get_by_role("button", name="Correr (~1 min)").first.click()
    pg.wait_for_timeout(4000)
    print("en curso visible:", pg.get_by_text("En curso").count() > 0)
    for pagina in ("bandeja", "caso", "resultados", "inicio"):
        t0 = time.time(); pg.goto(f"{URL}/{pagina}"); quieta(pg)
        print(f"  navegar a {pagina:10} mientras corre: {time.time() - t0:4.1f} s")
    pg.goto(f"{URL}/corridas"); quieta(pg)
    pg.screenshot(path=str(OUT / "corridas_en_curso.png"), full_page=True)
    t0 = time.time()
    while pg.get_by_text("En curso").count() and time.time() - t0 < 240:
        pg.wait_for_timeout(3000)
    quieta(pg)
    print("terminó en la vista sin recargar:", pg.get_by_text("En curso").count() == 0)
    pg.get_by_role("button", name="Comparar ahora").click(); quieta(pg)
    print("comparación:", pg.locator("[data-testid='stAlertContentSuccess'], [data-testid='stAlertContentWarning']").last.inner_text())
    pg.screenshot(path=str(OUT / "corridas_final.png"), full_page=True)
    b.close()
