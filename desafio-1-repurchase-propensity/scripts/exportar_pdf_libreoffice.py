"""Exporta un .docx a PDF con LibreOffice (equivalente Linux/macOS del paso con Word COM).

Abre el documento en un LibreOffice headless, actualiza campos e índices (el TOC que deja build_informe_docx.py),
exporta a PDF e informa la cantidad de páginas. El .docx no se modifica.

Necesita un Python con el módulo `uno` (en Ubuntu/Debian: paquete python3-uno; suele ser /usr/bin/python3,
no el del .venv). build_informe_docx.py lo busca solo.

Uso: python3 scripts/exportar_pdf_libreoffice.py entrada.docx salida.pdf
"""
from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

import uno
from com.sun.star.beans import PropertyValue


def props(**kw):
    out = []
    for k, v in kw.items():
        p = PropertyValue()
        p.Name, p.Value = k, v
        out.append(p)
    return tuple(out)


def main(docx: Path, pdf: Path) -> None:
    if not docx.is_file():
        sys.exit(f"No existe {docx}")
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        sys.exit("No se encontró LibreOffice (soffice). Instalarlo con: sudo apt install libreoffice-writer python3-uno")
    pipe = f"simtec_{uuid.uuid4().hex}"
    with tempfile.TemporaryDirectory() as perfil:
        # perfil propio: no choca con un LibreOffice que el usuario tenga abierto
        proc = subprocess.Popen([soffice, "--headless", "--invisible", "--nologo", "--norestore", "--nodefault",
                                 f"-env:UserInstallation={Path(perfil).as_uri()}",
                                 f"--accept=pipe,name={pipe};urp;StarOffice.ComponentContext"],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        desktop = None
        try:
            resolver = uno.getComponentContext().ServiceManager.createInstanceWithContext(
                "com.sun.star.bridge.UnoUrlResolver", uno.getComponentContext())
            for _ in range(120):
                try:
                    ctx = resolver.resolve(f"uno:pipe,name={pipe};urp;StarOffice.ComponentContext")
                    break
                except Exception:
                    if proc.poll() is not None:
                        sys.exit("LibreOffice terminó antes de aceptar la conexión.")
                    time.sleep(0.5)
            else:
                sys.exit("No se pudo conectar con LibreOffice (timeout).")
            desktop = ctx.ServiceManager.createInstanceWithContext("com.sun.star.frame.Desktop", ctx)
            doc = desktop.loadComponentFromURL(docx.resolve().as_uri(), "_blank", 0, props(Hidden=True))
            try:
                # Word respeta el switch \\b del TOC (sólo el cuerpo); LibreOffice no, así que el título
                # "Índice" entraría en su propio índice. Se lo baja a texto normal (el .docx no se guarda).
                par = doc.getText().createEnumeration()
                while par.hasMoreElements():
                    p = par.nextElement()
                    if p.supportsService("com.sun.star.text.Paragraph") and p.getString().strip() == "Índice" \
                            and p.getPropertyValue("OutlineLevel") > 0:
                        p.setPropertyValue("OutlineLevel", 0)
                doc.getTextFields().refresh()
                # dos pasadas: la primera arma el índice, la segunda corrige los números de página que éste desplaza
                for _ in range(2):
                    idx = doc.getDocumentIndexes()
                    for i in range(idx.getCount()):
                        idx.getByIndex(i).update()
                    doc.refresh()
                pdf.parent.mkdir(parents=True, exist_ok=True)
                doc.storeToURL(pdf.resolve().as_uri(), props(FilterName="writer_pdf_Export"))
                paginas = doc.getCurrentController().getPropertyValue("PageCount")
                print(f"paginas: {paginas}")
            finally:
                doc.close(True)
        finally:
            if desktop is not None:
                try:
                    desktop.terminate()
                except Exception:
                    pass  # la conexión se corta al cerrar LibreOffice
            try:
                proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid, signal.SIGKILL)  # soffice es un wrapper: matar todo el grupo


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(Path(sys.argv[1]), Path(sys.argv[2]))
