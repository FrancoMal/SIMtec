"""Markdown -> HTML (con estilo) -> PDF vía Chrome/Edge headless.

Uso: .venv/Scripts/python.exe scripts/build_pdf.py docs/informe_final.md reports/informe_final.pdf
Las rutas de imágenes relativas al .md se resuelven a file:// absolutas. Los ``<h1>`` fuerzan salto de página
(salvo el primero). Requiere Chrome o Edge instalado (se busca en las rutas estándar de Windows).
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import markdown

CSS = """
@page { size: A4; margin: 18mm 16mm 18mm 16mm; }
html { font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif; font-size: 10.5pt; color: #0b0b0b; line-height: 1.42; }
body { max-width: 100%; }
h1 { font-size: 20pt; margin: 0 0 6pt 0; color: #0b0b0b; border-bottom: 2px solid #2a78d6; padding-bottom: 4pt; }
h1.pb { page-break-before: always; }
h2 { font-size: 14pt; margin: 16pt 0 6pt 0; color: #184f95; }
h3 { font-size: 11.5pt; margin: 12pt 0 4pt 0; color: #0b0b0b; }
p { margin: 5pt 0; text-align: justify; }
ul, ol { margin: 4pt 0 6pt 0; padding-left: 18pt; }
li { margin: 2pt 0; }
table { border-collapse: collapse; margin: 6pt 0 10pt 0; font-size: 9pt; width: 100%; page-break-inside: avoid; }
th, td { border: 1px solid #c3c2b7; padding: 3pt 5pt; text-align: left; vertical-align: top; }
th { background: #eef4fc; font-weight: 600; }
tr:nth-child(even) td { background: #fafaf8; }
img { max-width: 92%; max-height: 100mm; width: auto; height: auto; display: block; margin: 6pt auto; page-break-inside: avoid; }
h2, h3 { page-break-after: avoid; }
p.caption + h2, p.caption + h3 { margin-top: 14pt; }
figure { margin: 8pt 0; page-break-inside: avoid; }
figcaption, .caption { font-size: 8.5pt; color: #52514e; text-align: center; margin-top: -2pt; }
blockquote { border-left: 3px solid #2a78d6; margin: 6pt 0; padding: 2pt 10pt; color: #52514e; background: #f7f9fc; }
code { font-family: Consolas, "Courier New", monospace; font-size: 9pt; background: #f2f2ef; padding: 0 3px; border-radius: 3px; }
pre { background: #f2f2ef; padding: 6pt 8pt; border-radius: 4px; font-size: 8.5pt; overflow-x: hidden; white-space: pre-wrap; }
hr { border: 0; border-top: 1px solid #e1e0d9; margin: 12pt 0; }
.portada { text-align: center; margin-top: 120pt; }
.portada h1 { border: 0; font-size: 26pt; }
.portada p { text-align: center; font-size: 12pt; color: #52514e; }
.kpi { display: inline-block; width: 30%; margin: 4pt 1%; padding: 8pt; border: 1px solid #e1e0d9; border-radius: 6px; text-align: center; }
.kpi .v { font-size: 20pt; font-weight: 600; color: #184f95; }
.kpi .l { font-size: 8.5pt; color: #52514e; }
.small { font-size: 8.5pt; color: #52514e; }
"""

BROWSERS = [
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
]


def md_to_html(md_path: Path) -> str:
    text = md_path.read_text(encoding="utf8")
    html = markdown.markdown(text, extensions=["tables", "fenced_code", "toc", "attr_list", "md_in_html", "sane_lists"])
    base = md_path.parent.resolve()

    def fix_src(m):
        src = m.group(1)
        if re.match(r"^(https?:|file:|data:)", src):
            return m.group(0)
        return f'src="{(base / src).resolve().as_uri()}"'

    html = re.sub(r'src="([^"]+)"', fix_src, html)
    # salto de página antes de cada h1 salvo el primero
    parts = html.split("<h1")
    if len(parts) > 2:
        html = parts[0] + "<h1" + parts[1] + "".join('<h1 class="pb"' + p for p in parts[2:])
    return f"<!doctype html><html lang='es'><head><meta charset='utf-8'><style>{CSS}</style></head><body>{html}</body></html>"


def html_to_pdf(html_path: Path, pdf_path: Path) -> None:
    exe = next((b for b in BROWSERS if b.exists()), None)
    if exe is None:
        raise RuntimeError("No se encontró Chrome ni Edge para imprimir el PDF")
    cmd = [str(exe), "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--run-all-compositor-stages-before-draw",
           "--virtual-time-budget=10000", f"--print-to-pdf={pdf_path.resolve()}", html_path.resolve().as_uri()]
    subprocess.run(cmd, check=True, capture_output=True, timeout=180)


def build(md_path: str, pdf_path: str) -> Path:
    md_p, pdf_p = Path(md_path), Path(pdf_path)
    pdf_p.parent.mkdir(parents=True, exist_ok=True)
    html_p = pdf_p.with_suffix(".html")
    html_p.write_text(md_to_html(md_p), encoding="utf8")
    html_to_pdf(html_p, pdf_p)
    return pdf_p


if __name__ == "__main__":
    out = build(sys.argv[1], sys.argv[2])
    print("PDF:", out, f"({out.stat().st_size / 1024:.0f} KB)")
