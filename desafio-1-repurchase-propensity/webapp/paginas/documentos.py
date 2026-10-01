"""Documentos finales versionados en la carpeta entregables/ de la raíz del repo, para descargar.
No hay botón para regenerar el informe: scripts/build_informe_docx.py produce la versión anterior y necesita Word."""
import streamlit as st

from lib.fuentes import ENTREGABLES

st.title("Documentos")
st.caption(f"Carpeta: `{ENTREGABLES}`. Se descargan tal como están; esta página no genera ni modifica nada.")
MIME = {".pdf": "application/pdf", ".md": "text/markdown",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation"}
archivos = sorted(p for p in ENTREGABLES.glob("*") if p.is_file()) if ENTREGABLES.exists() else []
if not archivos:
    st.info("No hay documentos en la carpeta entregables/ del repo.")
for p in archivos:
    a, b = st.columns([3, 1])
    tam = f"{p.stat().st_size / 1024:,.0f} KB".replace(",", ".")
    a.markdown(f"**{p.name}**  \n{tam}")
    b.download_button("Descargar", p.read_bytes(), file_name=p.name, mime=MIME.get(p.suffix.lower(),
                      "application/octet-stream"), key=str(p))
