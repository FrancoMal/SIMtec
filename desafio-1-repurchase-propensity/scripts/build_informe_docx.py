"""Genera el informe oficial sobre el template de Ford (Template_Informe_Solucion_FIC_III.docx) y lo exporta a PDF.

- Conserva portada, logo, estilos, numeración y pie de página del template.
- Reemplaza el índice estático por un campo TOC y lo actualiza con Word (COM) antes de exportar; en Linux/macOS
  lo hace LibreOffice (scripts/exportar_pdf_libreoffice.py) y el .docx queda con el índice marcado para actualizar.
- El contenido vive en este script (secciones del template: Descripción del Desafío, Descripción de la Solución
  [Resumen Ejecutivo, Especificaciones Técnicas, Información Complementaria, Seguridad y Privacidad], Factibilidad
  Económica, Valor Diferencial e Innovación, Trabajo Futuro, Conclusiones).

Uso: PYTHONIOENCODING=utf8 .venv/Scripts/python.exe scripts/build_informe_docx.py   (Linux: .venv/bin/python)
Salidas: reports/informe_final.docx y reports/informe_final.pdf
"""
from __future__ import annotations

import re
import shutil
import struct
import subprocess
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = next((p for p in (ROOT.parent / "Template_Informe_Solucion_FIC_III.docx",
                             ROOT.parent / "Dataset" / "Template_Informe_Solucion_FIC_III.docx") if p.is_file()),
                ROOT.parent / "Template_Informe_Solucion_FIC_III.docx")
OUT_DOCX = ROOT / "reports" / "informe_final.docx"
OUT_PDF = ROOT / "reports" / "informe_final.pdf"
FIG = ROOT / "reports" / "figures"
TEXT_W = 8934          # ancho útil en twips (A4 con los márgenes del template)
EMU_PER_TWIP = 635

# ------------------------------------------------------------------ helpers de XML
_media: list[tuple[str, Path]] = []
_rels: list[str] = []
_docpr = [100]


def runs(text: str, size: int = 20, italic: bool = False, extra: str = "") -> str:
    """Texto con **negrita** inline. Tamaño en medios puntos."""
    out = []
    for i, part in enumerate(text.split("**")):
        if not part:
            continue
        b = "<w:b/><w:bCs/>" if i % 2 == 1 else ""
        it = "" if italic else '<w:i w:val="0"/><w:iCs w:val="0"/>'
        out.append(f'<w:r><w:rPr>{b}{it}{extra}<w:sz w:val="{size}"/><w:szCs w:val="{size}"/></w:rPr>'
                   f'<w:t xml:space="preserve">{escape(part)}</w:t></w:r>')
    return "".join(out)


def P(text: str, size: int = 20, before: int = 90, align: str = "both", left: int = 170, right: int = 120) -> str:
    return (f'<w:p><w:pPr><w:pStyle w:val="BodyText"/><w:spacing w:before="{before}" w:line="264" w:lineRule="auto"/>'
            f'<w:ind w:left="{left}" w:right="{right}"/><w:jc w:val="{align}"/></w:pPr>{runs(text, size)}</w:p>')


def H3(text: str) -> str:
    return ('<w:p><w:pPr><w:pStyle w:val="Heading3"/><w:numPr><w:ilvl w:val="2"/><w:numId w:val="2"/></w:numPr>'
            '<w:tabs><w:tab w:val="left" w:pos="840"/></w:tabs><w:spacing w:before="240"/><w:ind w:left="840" w:hanging="670"/></w:pPr>'
            f'<w:r><w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p>')


def H4(text: str) -> str:
    return (f'<w:p><w:pPr><w:pStyle w:val="Heading4"/><w:spacing w:before="200"/><w:ind w:left="170"/></w:pPr>'
            f'<w:r><w:rPr><w:b/><w:bCs/><w:i w:val="0"/><w:sz w:val="21"/></w:rPr><w:t xml:space="preserve">{escape(text)}</w:t></w:r></w:p>')


def BUL(text: str, size: int = 20) -> str:
    return (f'<w:p><w:pPr><w:pStyle w:val="ListParagraph"/><w:numPr><w:ilvl w:val="0"/><w:numId w:val="4"/></w:numPr>'
            f'<w:spacing w:before="50" w:line="259" w:lineRule="auto"/><w:ind w:left="560" w:right="120" w:hanging="220"/><w:jc w:val="both"/></w:pPr>{runs(text, size)}</w:p>')


def PAGEBREAK() -> str:
    return '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'


def TABLE(rows: list[list[str]], widths: list[int], header: bool = True, size: int = 17, align_first_left: bool = True) -> str:
    total = sum(widths); assert total <= TEXT_W - 170, f"tabla demasiado ancha: {total}"
    tblpr = ('<w:tblPr><w:tblW w:w="0" w:type="auto"/><w:tblInd w:w="170" w:type="dxa"/>'
             '<w:tblBorders><w:top w:val="single" w:sz="4" w:space="0" w:color="7F7F7F"/><w:left w:val="single" w:sz="4" w:space="0" w:color="7F7F7F"/>'
             '<w:bottom w:val="single" w:sz="4" w:space="0" w:color="7F7F7F"/><w:right w:val="single" w:sz="4" w:space="0" w:color="7F7F7F"/>'
             '<w:insideH w:val="single" w:sz="4" w:space="0" w:color="7F7F7F"/><w:insideV w:val="single" w:sz="4" w:space="0" w:color="7F7F7F"/></w:tblBorders>'
             '<w:tblLayout w:type="fixed"/><w:tblCellMar><w:left w:w="60" w:type="dxa"/><w:right w:w="60" w:type="dxa"/></w:tblCellMar></w:tblPr>')
    grid = "<w:tblGrid>" + "".join(f'<w:gridCol w:w="{w}"/>' for w in widths) + "</w:tblGrid>"
    body = []
    for r, row in enumerate(rows):
        is_h = header and r == 0
        cells = []
        for c, (txt, w) in enumerate(zip(row, widths)):
            shade = '<w:shd w:val="clear" w:color="auto" w:fill="EDEDED"/>' if is_h else ""
            jc = "left" if (c == 0 and align_first_left) or is_h else "left"
            t = f"**{txt}**" if is_h else txt
            cells.append(f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/>{shade}</w:tcPr>'
                         f'<w:p><w:pPr><w:pStyle w:val="TableParagraph"/><w:spacing w:before="20" w:after="20" w:line="220" w:lineRule="auto"/>'
                         f'<w:ind w:left="40"/><w:jc w:val="{jc}"/></w:pPr>{runs(t, size)}</w:p></w:tc>')
        trpr = '<w:trPr><w:cantSplit/><w:tblHeader/></w:trPr>' if is_h else '<w:trPr><w:cantSplit/></w:trPr>'
        body.append(f"<w:tr>{trpr}{''.join(cells)}</w:tr>")
    return f"<w:tbl>{tblpr}{grid}{''.join(body)}</w:tbl>" + P("", size=8, before=20)


def png_size(path: Path) -> tuple[int, int]:
    with open(path, "rb") as h:
        h.read(16); w, hh = struct.unpack(">II", h.read(8))
    return w, hh


def FIGURE(rel: str, caption: str, width_twips: int = 8200) -> str:
    path = FIG / rel
    w, h = png_size(path)
    cx = width_twips * EMU_PER_TWIP; cy = int(cx * h / w)
    n = len(_media) + 1
    rid = f"rIdFig{n}"
    _media.append((f"media/fig{n}.png", path)); _rels.append(rid)
    _docpr[0] += 1; did = _docpr[0]
    drawing = (f'<w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="{cx}" cy="{cy}"/>'
               f'<wp:effectExtent l="0" t="0" r="0" b="0"/><wp:docPr id="{did}" name="Figura {n}"/>'
               '<wp:cNvGraphicFramePr><a:graphicFrameLocks xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" noChangeAspect="1"/></wp:cNvGraphicFramePr>'
               '<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
               f'<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:nvPicPr><pic:cNvPr id="{did}" name="Figura {n}"/><pic:cNvPicPr/></pic:nvPicPr>'
               f'<pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
               f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic>'
               '</a:graphicData></a:graphic></wp:inline></w:drawing>')
    fig_p = (f'<w:p><w:pPr><w:keepNext/><w:spacing w:before="120"/><w:ind w:left="170"/><w:jc w:val="center"/></w:pPr>'
             f'<w:r><w:rPr><w:noProof/></w:rPr>{drawing}</w:r></w:p>')
    cap_p = (f'<w:p><w:pPr><w:pStyle w:val="Caption"/><w:spacing w:before="40" w:after="160"/><w:ind w:left="170" w:right="120"/><w:jc w:val="center"/></w:pPr>'
             f'{runs(f"Figura {n}. {caption}", 16, italic=True)}</w:p>')
    return fig_p + cap_p


# ------------------------------------------------------------------ contenido
def contenido() -> dict[str, str]:
    S = {}
    S["desafio"] = "".join([
        P("**Desafío 1 — Data-Driven Repurchase based on Service Retention: predicción de retorno a la red oficial en ventana de servicio.** Área: Customer Experience & Data Strategy, Posventa / Retención de Servicio. Mentor y SPOC: Facundo Bertolosso."),
        P("Ford quiere construir relaciones que duren toda la vida del cliente, y cada interacción de posventa es la que convierte una compra en lealtad. Hoy, cuando un vehículo entra en su ventana de mantenimiento, la red lo contacta con reglas de tiempo, kilometraje y vencimiento que identifican elegibilidad pero no distinguen el riesgo individual: dos usuarios reciben el mismo tratamiento aunque uno vuelva solo y el otro esté por abandonar la red. El churn se reconoce tarde, cuando la ventana termina sin un mantenimiento programado completado."),
        P("La ficha técnica del desafío pide un modelo que, **para cada usuario con al menos un vehículo dentro de la ventana de servicio, estime la probabilidad de churn**, definida como no completar el próximo mantenimiento programado en la red oficial dentro del horizonte definido por negocio. La unidad de observación es usuario–vehículo (VIN)–ventana, con vista consolidada por usuario cuando tiene varios VIN. El output mínimo es: customer_id y vehicle_id seudonimizados, fecha de scoring, probabilidad entre 0 y 1, segmento de riesgo y principales drivers. Restricciones: ninguna variable posterior a la fecha de scoring puede ser feature, validación separada por fecha, probabilidades calibradas, explicabilidad auditable y reproducibilidad. Se evalúan nueve criterios: formulación de población, ventana y target; ausencia de leakage y validación temporal; poder predictivo (ROC-AUC y especialmente PR-AUC, precisión y recall sobre churn, lift por deciles, recall a capacidad de contacto); calibración; explicabilidad; accionabilidad e integración; viabilidad y reproducibilidad; innovación; y claridad del pitch."),
        P("**Datos recibidos**: dos extractos seudonimizados de BigQuery. Ventas Ranger Argentina 2024-2026 (59.384 vehículos 0 km, 45.959 compradores) y Agenda Ford 2024-2026 (631.623 ítems de servicio que consolidan en 492.442 turnos de 111.752 vehículos de todo el parque Ranger, 95 concesionarios). Corte de datos: 25/08/2026. No hay CRM, DMS, campañas, web ni telemetría."),
        P("Nota sobre el título: el resumen público habla de \"Repurchase Propensity\". La ficha técnica lo precisa como retención de service, porque el service es el punto de contacto que sostiene la recompra. En el dataset no existe una variable de recompra; sí existe, y la usamos como evidencia complementaria, el cruce entre dueños de Ranger vistos en la agenda y compradores posteriores de una 0 km (sección 2.2)."),
    ])

    S["resumen"] = "".join([
        P("**Qué hace.** Cada mes, unos 6.000 a 7.000 vehículos Ranger entran en su ventana de mantenimiento en Argentina y cuatro de cada diez no vuelven a la red oficial dentro de ella. Construimos un modelo que, cuando cada vehículo entra en ventana, estima la probabilidad calibrada de que **no complete su mantenimiento programado en la red dentro de los 120 días siguientes**, explica por qué con sus tres drivers principales y ordena la población para que la capacidad finita de contacto de los concesionarios vaya primero a quien más lo necesita. El resultado es una bandeja priorizada por vehículo con vista consolidada por usuario, tres segmentos con acción y canal definidos, y un tablero que la red puede operar."),
        P("**Cómo lo resuelve.** La ventana de cada vehículo se deriva de los datos y se valida contra el plan oficial de Ford, que es por kilómetros (16.000 km en la Ranger nueva, 10.000 km en la anterior) y no anual. Las features usan sólo información anterior al scoring: detectamos y excluimos dos columnas que son fotos del presente copiadas al pasado. El modelo (LightGBM calibrado) se entrenó con ventanas hasta septiembre de 2025 y se evaluó fuera de tiempo en enero-marzo de 2026."),
        P("**Qué logra.** ROC-AUC 0,74 y PR-AUC 0,70 sobre una tasa base de 43 %, con error de calibración de 1 punto. Contactando al 20 % de mayor riesgo se alcanza al 36 % de los que iban a abandonar, 1,8 veces más que con la priorización uniforme actual; con 3.000 contactos por mes, al 65 %. Con supuestos conservadores, priorizar con el modelo recupera un 80 % más de services que el mismo esfuerzo repartido al azar."),
        P("**Por qué es viable.** Usa sólo las dos fuentes que Ford ya tiene en BigQuery, corre en minutos con software abierto, se integra a Service Leads y Service Reminder con el output mínimo de la ficha, y su impacto se mide con un piloto aleatorizado antes de escalar. Es reproducible con un comando y fue verificado por análisis independientes."),
    ])

    S["especificaciones"] = "".join([
        H3("Datos y hallazgos que cambian el problema"),
        P("Agenda Ford tiene una fila por ítem de servicio dentro de un turno; consolidada a nivel turno: 342.691 concluidos, 101.222 cancelados (en su mayoría reprogramaciones), 27.237 no-shows. **222.889 turnos son mantenimientos programados completados**, el evento que define el retorno. El análisis exploratorio se hizo en seis temas, cada uno con un script reproducible y una verificación adversarial independiente que recalculó las cifras; sus hallazgos principales:"),
        BUL("**El plan es por kilómetros y difiere por generación.** El kilometraje al n-ésimo service converge a 16.000 × n en la Ranger P703 y a 10.000 × n en la P375 (Figura 1), en línea con el plan oficial publicado por Ford Argentina (16.000 km ó 12 meses; 10.000 km ó 1 año). La mediana entre mantenimientos consecutivos es de 165 a 200 días; alrededor del 10 % de los retornos tarda más de un año. Una regla de \"un año\" abre la ventana cuando el 86 % de los clientes ya vino."),
        BUL("**El primer service concentra el riesgo.** De los compradores de 2024, el 64,5 % hizo el primer mantenimiento en la red dentro de 12 meses y el 80,9 % dentro de 18; el 19 % no volvió. A 12 meses, el churn del primer service (36 %) supera al del segundo (25 %). A igual edad del vehículo, el número de services acumulados separa retornos del 40 % y del 80 %."),
        BUL("**La retención cae con la edad de forma sostenida** (Figura 2): 66 % en el tercer año, 53 % en el quinto, 38 % en el sexto, cuando la mediana del parque supera los 100.000 km. \"Cae al tercer año\" es cierto a medias: la caída es gradual y el escalón mayor está entre el 5° y el 6° año."),
        BUL("**Dos columnas son fotos, no historia.** KM es idéntico en todos los turnos de un vehículo (99,99 %) e igual al último odómetro cargado; ConnectedStatusARG tampoco varía y \"Sin información de conectividad\" marca vehículos que ya salieron del sistema. Usarlas infla el rendimiento con información que no existe al momento de decidir (sección 2.2.4). El km real de cada visita es VehicleCurrentKM."),
        BUL("**Lo que engaña en crudo.** Los no-shows previos parecen no separar nada (78 % de retorno con 0, 1 o 2 o más), pero es una paradoja de Simpson: quien tuvo un no-show tuvo turnos, y tener turnos es el predictor más fuerte. A igual cantidad de turnos, un no-show baja el retorno (67 % vs 73 %). La encuesta de estrellas es previa al turno y no aporta. Sí separan: la recencia (turno previo hace más de un año: 51 % de retorno; hace 1 a 3 meses: 86 %), FordPass (+3 a +5 puntos dentro de cada generación) y el concesionario (estable entre años; 73 % vs 84 % de retorno entre el peor y el mejor quintil)."),
        BUL("**La identidad del cliente es imperfecta.** El 21 % de los vehículos tiene más de un customer_id y la mitad de esos cambios coincide con un cambio de canal de reserva. Las flotas entran menos a la red (62 % vs 80 % hacen el primer service en 15 meses) pero, una vez adentro, vuelven igual."),
        FIGURE("eda/02_cadencia_ventana_box_km_por_service.png", "Km al n-ésimo service por generación: el plan es 16.000 × n (P703) y 10.000 × n (P375)."),
        FIGURE("eda/03_retencion_churn_curva_edad.png", "Proporción de vehículos con al menos un mantenimiento en la red en cada año de vida."),

        H3("Población, ventana y target"),
        P("La ficha deja las reglas exactas de ventana y horizonte \"a validar por modelo/año\". Las definimos empíricamente y las dejamos parametrizadas (config/params.json)."),
        TABLE([
            ["Elemento", "Definición", "Justificación"],
            ["Unidad", "usuario – vehículo – ventana", "Lo pide la ficha; el riesgo es del vehículo, la acción es sobre el usuario"],
            ["Ancla", "último mantenimiento programado completado en la red; inicio de garantía para el primer service", "Reproduce cómo \"le toca\" a cada vehículo"],
            ["Tasa de uso", "km al ancla / edad del vehículo al ancla (mediana de la generación si no hay km)", "Disponible en el 96 % de las anclas; concuerda con la pendiente entre visitas (Spearman 0,90)"],
            ["Vencimiento", "ancla + min(365 días, K / tasa de uso), K = 16.000 km (P703) / 10.000 km (P375); primer service: garantía + 300 días", "Centra el retraso real del retorno cerca del vencimiento"],
            ["Apertura y scoring", "vencimiento − 30 días", "80 % de las ventanas abiertas; horizonte corto"],
            ["Horizonte", "vencimiento + 90 días", "Captura el 84 % de los retornos de quienes vuelven en 18 meses"],
            ["Target", "churn = 1 si no hay mantenimiento completado entre la apertura y el cierre del horizonte", "Definición de la ficha"],
            ["Censura", "ventanas cuyo horizonte no cerró 30 días antes del corte: no se etiquetan; son la población a scorear hoy", "Definición de la ficha"],
            ["Población resultante", "142.637 ventanas evaluables (2024-2026), churn 41,6 %; 35.190 ventanas abiertas al corte", "Quedan fuera 17.973 vehículos entregados antes de 2024 sin ningún mantenimiento en 2024-26: no tienen ancla observable"],
        ], [1500, 3700, 3400]),
        P("**Alternativas descartadas con números** (36 combinaciones de parámetros probadas): la regla de \"un año\" produce 58 % de churn y sólo el 18 % de los retornos caen dentro de la ventana; los aniversarios del plan, 76 % de churn y 17 % de captura; un único K para todo el parque corre el vencimiento un mes tarde en la P375 o lo adelanta en la P703; abrir a −60 días captura más retornos a costa de una ventana de 150 días; un horizonte de +60 días etiqueta como churn a muchos que vuelven tarde (47 %), y +180 entrega el resultado siete meses después, tarde para medir (Figura 3)."),
        P("**Contraste con una solución independiente.** Un segundo equipo de análisis resolvió el mismo desafío sin ver este trabajo y llegó a la misma población y al mismo evento, pero con un horizonte de un mes calendario, lo que da 78 % de churn. Aplicando cada etiqueta sobre las ventanas del otro se demostró que la diferencia es sólo el horizonte (79,0 % vs 44,0 %) y que entre el 40 % y el 44 % de los \"churn\" mensuales completa el mantenimiento antes de vencimiento + 90 días: son clientes tardíos, no perdidos. Adoptamos el horizonte de 90 días como resultado primario, la cadencia mensual de scoring como operación, y dejamos al negocio la validación final de ambos parámetros."),
        FIGURE("eda/02_cadencia_ventana_ventana_retraso_sensibilidad.png", "Retraso del retorno real respecto del vencimiento estimado, según regla. La regla por generación centra el retorno; la regla anual queda 200 días tarde."),

        H3("Features y seguridad temporal"),
        P("Para una ventana con fecha de scoring t sólo entran turnos con fecha anterior a t y encuestas respondidas antes de t. Se implementa con acumulados por vehículo y uniones temporales estrictas (merge_asof hacia atrás sin coincidencia exacta), y un notebook verifica que ninguna recencia sea menor o igual a cero. Ochenta y seis features en nueve grupos: recencia (días desde el último mantenimiento, turno y visita), frecuencia e intensidad (mantenimientos por año observado, visitas, diagnósticos, reparaciones, recalls), patrón de uso (km/año, atraso en km respecto del plan, services salteados), ciclo de vida (antigüedad, n° de service, generación, versión), canal (último canal, proporción FordPass), concesionario (concesionario y zona del último mantenimiento, cambios de dealer), relación (tamaño de flota, vehículos del cliente, cambios de cliente), venta (unidad de negocio, tipo de persona, canal, provincia) y geometría de la ventana (qué regla vence primero, días al vencimiento)."),
        P("**Anti-leakage.** Sin KM ni ConnectedStatusARG (fotos a la extracción), sin turnos futuros (no hay fecha de creación del turno; \"ya tiene turno\" se usa como regla operativa posterior al modelo), sin ServiceMonth (nominal). Historia previa a 2024 invisible: el 60 % del parque tiene garantía anterior al inicio de la agenda; se mitiga con la antigüedad, el n° de service y \"meses de historia observable\" como features, y se verificó por ablación que no distorsiona el resultado."),

        H3("Modelo, validación temporal y calibración"),
        P("**Modelo.** LightGBM (gradient boosting) con categóricas nativas y early stopping. Baselines: azar (= prioridad uniforme actual), una heurística de reglas (antigüedad + no-shows) y una regresión logística con 24 features. **Validación temporal.** Entrenamiento con ventanas abiertas hasta el 30/09/2025 (102.040), calibración isotónica en octubre-diciembre de 2025 (20.888), evaluación en ventanas abiertas entre enero y marzo de 2026 cuyo horizonte cerró al menos 30 días antes del corte (19.709). Una validación cruzada aleatoria mezclaría ventanas del mismo vehículo y ocultaría el cambio de composición del parque (la P375 cae de 5.856 a 2.009 mantenimientos mensuales mientras la P703 sube de 437 a 5.625)."),
        TABLE([
            ["Modelo (test: 19.709 ventanas, churn 42,6 %)", "ROC-AUC", "PR-AUC", "Brier", "ECE"],
            ["Azar (prioridad uniforme, situación actual)", "0,497", "0,422", "0,335", "0,255"],
            ["Heurística de reglas", "0,609", "0,518", "—", "—"],
            ["Regresión logística (calibrada)", "0,674", "0,596", "0,222", "0,018"],
            ["**LightGBM calibrado**", "**0,740**", "**0,704**", "**0,199**", "**0,010**"],
        ], [4300, 1100, 1100, 1100, 1000]),
        P("**Lo que importa operativamente es el recall a capacidad de contacto**: si la red puede llamar al X % de la población en ventana, ¿a qué fracción de los churners alcanza? Con 3.000 contactos humanos por mes en toda la red, el modelo alcanza al 65 % de los churners con una precisión del 61 %."),
        TABLE([
            ["Capacidad", "Contactados", "Churners alcanzados", "Recall", "Precisión", "Lift vs azar"],
            ["5 %", "985", "969", "11,5 %", "98 %", "2,3×"],
            ["10 %", "1.971", "1.742", "20,7 %", "88 %", "2,1×"],
            ["**20 %**", "**3.942**", "**3.055**", "**36,4 %**", "**78 %**", "**1,8×**"],
            ["30 %", "5.913", "4.118", "49,0 %", "70 %", "1,6×"],
            ["50 %", "9.854", "5.826", "69,4 %", "59 %", "1,4×"],
        ], [1300, 1500, 1900, 1200, 1300, 1400]),
        FIGURE("modelo/ganancia.png", "Curva de ganancia en test: porcentaje de churners reales alcanzados según el porcentaje de la población contactada.", 6400),
        FIGURE("modelo/lift_deciles.png", "Tasa de churn observada por decil de score. El decil 1 tiene 88 % de churn; el 10, 14 %.", 6400),
        FIGURE("modelo/calibracion.png", "Probabilidad declarada vs tasa observada por decil. ECE = 0,010: cuando el modelo dice 70 %, siete de cada diez no vuelven.", 5000),
        P("**Robustez y leakage (ablaciones sobre el mismo test).** El modelo no depende de categóricas de alta cardinalidad ni de las features de ventas (que aportan población, no ranking); exigir seis meses de historia observable no cambia el resultado; incluir la conectividad \"foto\" empeora fuera de tiempo; usar KM como km del evento infla el ROC-AUC a 0,813 y rompe la calibración: un resultado que no se puede sostener en producción."),
        TABLE([
            ["Variante", "ROC-AUC", "PR-AUC", "ECE", "Lectura"],
            ["Modelo base", "0,740", "0,704", "0,010", "—"],
            ["Sin concesionario, versión ni provincia", "0,738", "0,700", "0,017", "No depende de categóricas de alta cardinalidad"],
            ["Sólo agenda (sin features de ventas)", "0,739", "0,700", "0,011", "Ventas aporta población, no ranking"],
            ["Exige ≥ 6 meses de historia observable", "0,738", "0,702", "0,013", "La censura a la izquierda no distorsiona"],
            ["Sin encuestas", "0,735", "0,698", "0,013", "La encuesta no aporta"],
            ["Con ConnectedStatusARG (foto)", "0,730", "0,689", "0,029", "Un leakage suave empeora fuera de tiempo"],
            ["Con KM (foto) como km del evento", "0,813", "0,802", "0,056", "Rendimiento inflado con información futura"],
            ["Sólo primer service (n = 3.562)", "0,805", "0,835", "0,025", "El primer service es más predecible"],
            ["Sólo services siguientes (n = 16.147)", "0,721", "0,636", "0,013", "—"],
        ], [3300, 1000, 1000, 900, 2400]),

        H3("Qué explica el riesgo"),
        P("La importancia global (SHAP, Figura 7) y los tres drivers por vehículo cuentan la misma historia en términos de negocio: **ciclo de vida** (versión, generación, antigüedad, n° de service: el riesgo crece con la edad del vehículo), **intensidad de la relación** (mantenimientos por año observado, visitas: el cliente que viene seguido, sigue viniendo), **uso y atraso** (km/día, km de atraso del último service respecto del plan: quien llegó tarde al último service tiene más chance de no llegar al próximo), **flota** (las flotas grandes entran menos a la red) y **concesionario** (un driver accionable, con dispersión real y estable entre años). Para cada vehículo el sistema entrega los tres drivers con mayor peso en lenguaje llano, por ejemplo \"días entre los dos últimos mantenimientos = 312 (↑ riesgo)\" o \"sin registro en la red\" para quien nunca pasó por un concesionario."),
        FIGURE("modelo/shap_global.png", "Importancia media (SHAP) de las features en test.", 7200),

        H3("Segmentos accionables, activación e integración"),
        TABLE([
            ["Segmento", "Tamaño", "Churn (test)", "% churners", "Acción", "Canal"],
            ["Alto", "20 %", "78 %", "36 %", "Llamado del asesor de service dentro de las 48 h de abrir la ventana con oferta concreta: el descuento por continuidad que Ford ya tiene (5 % en el 2° service, 10 % en el 3°, 15 % del 4° en adelante), precio fijo, turno con retiro y entrega", "Service Leads (dealer)"],
            ["Medio", "30 %", "47 %", "33 %", "Recordatorio personalizado con turno sugerido y beneficio liviano; segundo toque a los 10 días si no agenda", "FordPass / WhatsApp (Customer Tweet)"],
            ["Bajo", "50 %", "26 %", "31 %", "Recordatorio estándar automático", "Service Reminder"],
        ], [1100, 800, 900, 1000, 3400, 1500]),
        P("**Reglas operativas alrededor del modelo.** El vehículo que ya tiene turno agendado sale de la lista (1.791 de los 30.504 de hoy). La bandeja muestra los días restantes de horizonte: un vehículo con 10 días de margen se prioriza distinto que uno con 90. Un cliente con varios vehículos en ventana recibe un único contacto con la lista de sus unidades (en el último año, unos 1.200 clientes tuvieron dos o más vehículos entrando en ventana el mismo mes). Las relaciones sin cliente identificable o con identidad ambigua se scorean pero no entran en la lista automática: se resuelven en CRM. El scoring se corre en lote el primer día de cada mes sobre las ventanas abiertas o que abren ese mes; el modelo se re-entrena cada trimestre con las ventanas cerradas."),
        P("**Población de hoy** (corte 25/08/2026): 30.504 vehículos, 22.255 en ventana y 8.249 que entran en los próximos 30 días. Alto: 6.100; Medio: 9.152; Bajo: 15.252 (Figura 8 para el volumen mensual). **Integración**: BigQuery genera la población en ventana; el pipeline Python produce el score versionado con el output mínimo de la ficha; Service Leads y Service Reminder reciben customer_id, vehicle_id, fecha de scoring, probabilidad, segmento y drivers; CRM valida identidad, consentimiento y turnos vigentes antes de contactar. La medición se hace por decil de riesgo, acción, concesionario y período, como pide la ficha."),
        FIGURE("modelo/volumen_mensual.png", "Vehículos que entran en ventana por mes: dimensiona la capacidad de contacto necesaria.", 7600),
        TABLE([
            ["Campo del output", "Contenido"],
            ["customer_id, vehicle_id", "identificadores seudonimizados"],
            ["fecha_scoring, fecha_apertura_ventana, vencimiento_estimado, cierre_horizonte, dias_restantes_horizonte", "geometría de la ventana"],
            ["prob_churn", "probabilidad calibrada (0-1)"],
            ["segmento", "Alto / Medio / Bajo"],
            ["driver_1 a driver_3", "principales drivers con dirección (↑/↓ riesgo)"],
            ["tiene_turno_agendado, fecha_turno_agendado, prioridad", "reglas operativas y ranking"],
        ], [4300, 4300]),

        H3("Recompra observable: evidencia complementaria"),
        P("Aunque el target es la retención de service, el dataset permite observar recompra Ranger→Ranger: el customer_id persiste entre ventas y entre ventas y agenda. 12.239 ventas de 2024-26 (20,6 %) son de compradores que ya usaban otra Ranger, entregada al menos un año antes y vista en la agenda antes de comprar (6.192 compradores, 4.389 personas físicas). De 33.391 dueños de Ranger anteriores a 2024 vistos en la agenda en el primer semestre de 2024, el 6,4 % compró una Ranger 0 km dentro de los 12 meses y el 11,2 % dentro de 24. Con esos positivos se puede entrenar un segundo modelo, complementario, que mida el vínculo service–recompra que motiva el desafío (sección 5)."),

        H3("Reproducibilidad"),
        P("Todo el trabajo corre con un comando (scripts/run_pipeline.py) en unos tres minutos: carga y tipado de los CSV, consolidación de la agenda a nivel turno, construcción de ventanas y target, features, entrenamiento, calibración, evaluación temporal, SHAP, segmentos, ROI y scoring de la población actual. Los parámetros de ventana y de negocio están en archivos de configuración; los análisis exploratorios, la sensibilidad de la ventana, las ablaciones y la comparación con la solución independiente son scripts propios. Tres notebooks ejecutados sirven de evidencia técnica y un dashboard permite operar la bandeja. Entorno: Python 3.12, pandas, scikit-learn, LightGBM, SHAP, Streamlit."),
    ])

    S["complementaria"] = "".join([
        P("En el .zip que acompaña este informe se adjuntan los entregables que no caben en el documento:"),
        BUL("**Dataset analítico documentado y definición reproducible del target**: config/params.json, src/repurchase/ventanas.py, docs/01_hallazgos_eda.md y docs/02_decisiones_y_descartes.md."),
        BUL("**Pipeline de features, modelo entrenado y evaluación temporal**: src/repurchase/, scripts/run_pipeline.py, data/models/ (modelo, calibrador, métricas), reports/modelo/ (resumen de la corrida, lift por decil, calibración, ROI, sensibilidad, ablaciones)."),
        BUL("**Explicación global e individual**: reports/figures/modelo/shap_global.png y los drivers por vehículo en el ranking."),
        BUL("**Ranking priorizado**: data/processed/scores_actuales.csv (30.504 vehículos con el output mínimo de la ficha) y la vista consolidada por usuario."),
        BUL("**Propuesta de activación y demo**: app/app.py (dashboard Streamlit con bandeja, ficha por vehículo, vista por usuario y por concesionario) y docs/03_pitch_trials_day.md."),
        BUL("**Evidencia**: reports/eda/ (seis análisis con verificación independiente), notebooks/ (tres notebooks ejecutados), reports/revision_cruzada/ (comparación con la solución independiente y su verificación)."),
        P("Figuras adicionales disponibles en reports/figures/: curvas del primer service de la cohorte 2024, precisión-recall, segmentos, distribución de intervalos, tasa de uso, estacionalidad, identidad y flotas, censura a la izquierda y snapshot de conectividad."),
    ])

    S["seguridad"] = "".join([
        P("La solución no introduce un riesgo de ciberseguridad nuevo: corre dentro del entorno analítico que Ford ya opera (GCP BigQuery y Python), no expone endpoints externos, no envía datos a servicios de terceros y no utiliza modelos generativos ni texto libre para calcular el riesgo. El análisis se hizo contra los marcos de referencia habituales: la **Ley 25.326 de Protección de Datos Personales** y su autoridad de aplicación (AAIP), **ISO/IEC 27001** (gestión de seguridad de la información), **NIST Cybersecurity Framework 2.0** y **NIST AI Risk Management Framework** (riesgos específicos de sistemas de IA), y las listas de riesgos de OWASP para machine learning."),
        TABLE([
            ["Riesgo", "Evaluación", "Mitigación"],
            ["Reidentificación de personas a partir de los IDs", "Bajo. Los datos llegan seudonimizados con hash salado cuyo salt no se comparte; no hay VIN, documento, nombre, contacto, patente ni dealer real.", "El pipeline nunca intenta desanonimizar; el output usa los mismos IDs seudonimizados y la resolución a un contacto real ocurre sólo dentro del CRM de Ford, con control de acceso."],
            ["Fuga o difusión de los extractos", "Medio si se copian fuera del entorno.", "Los crudos son de sólo lectura y no se replican; los derivados con IDs quedan fuera del repositorio de código (.gitignore) y del PDF; la integridad de los crudos se verifica por hash; el .zip de entrega contiene sólo IDs seudonimizados y se comparte por los canales autorizados."],
            ["Uso indebido de los scores (contactos no consentidos, discriminación)", "Medio.", "El score prioriza, no decide: antes de contactar, CRM valida consentimiento (Ley 25.326, art. 5), turnos vigentes e identidad; no se usan atributos protegidos; las acciones son comerciales y opcionales para el cliente; acceso por roles y registro de uso en BigQuery / Service Leads."],
            ["Fuga temporal (features con información futura)", "Alto si no se controla; es el riesgo técnico principal del desafío.", "Features estrictamente anteriores al scoring; columnas snapshot (KM, conectividad) excluidas; ablaciones que demuestran el efecto; validación temporal con embargo y margen de censura."],
            ["Deriva y degradación del modelo", "Medio: la composición del parque cambia mes a mes.", "Re-entrenamiento trimestral, monitoreo de churn por generación y de las features, umbral de rentabilidad revisable, regla de respaldo (priorización actual) si el score se degrada."],
            ["Cadena de suministro de software", "Bajo.", "Dependencias abiertas y conocidas (pandas, scikit-learn, LightGBM, SHAP) con versiones fijadas; código revisable; sin componentes que salgan a internet en ejecución."],
            ["Manipulación de datos de entrada (poisoning)", "Bajo: los datos provienen de sistemas transaccionales internos.", "Controles de calidad al cargar (duplicados exactos, odómetros absurdos, estados contradictorios) y comparación de hashes de origen."],
        ], [2300, 2300, 4000]),
        P("Ningún dato del challenge se envió a servicios externos durante el desarrollo; la asistencia de herramientas de IA se usó sobre código y documentación, y todos los resultados provienen de ejecutar código sobre los datos recibidos dentro del entorno autorizado."),
    ])

    S["economica"] = "".join([
        P("**Herramientas.** La solución no requiere adquirir software: usa BigQuery (ya en uso en Ford como fuente analítica), Python con librerías de código abierto (pandas, scikit-learn, LightGBM, SHAP, Streamlit) y los canales de consumo existentes (Service Leads, Service Reminder, FordPass). El cómputo mensual es marginal: la población en ventana es de unos 30.000 vehículos y el pipeline completo corre en minutos en una máquina virtual chica."),
        TABLE([
            ["Concepto", "Estimación (USD, supuestos)", "Naturaleza"],
            ["Integración del score a Service Leads / Reminder y a la vista de CRM (esquema del output, tabla en BigQuery, vista por usuario)", "15.000 a 25.000", "Una vez; 2 a 3 sprints de un ingeniero de datos con un analista de Posventa"],
            ["Cómputo y almacenamiento (BigQuery scheduled queries, VM para el lote mensual)", "500 a 1.500 por año", "Recurrente"],
            ["Mantenimiento: re-entrenamiento trimestral, monitoreo, ajuste de reglas", "12.000 a 18.000 por año (≈ 0,2 de un científico de datos)", "Recurrente"],
            ["Piloto de 90 días (contactos adicionales, ~3.000 por mes a USD 3)", "≈ 27.000", "Una vez, y es el costo que el modelo prioriza"],
        ], [4300, 2100, 2200]),
        P("**Beneficio.** Supuestos declarados y editables (Ford los reemplaza por sus números): uplift del contacto 15 % (fracción de churners que un llamado con oferta recupera; referencia 10-25 %), valor de un service retenido USD 250 (margen del mantenimiento más valor futuro atribuible: siguientes services, repuestos fuera de garantía, lealtad), costo de un contacto humano USD 3."),
        TABLE([
            ["Capacidad", "Contactos", "Services recuperados con modelo", "Con priorización uniforme", "Ganancia incremental"],
            ["10 %", "1.971", "261", "126", "+107 %"],
            ["**20 %**", "**3.942**", "**458**", "**252**", "**+82 %**"],
            ["30 %", "5.913", "618", "378", "+63 %"],
            ["50 %", "9.854", "874", "630", "+39 %"],
        ], [1300, 1400, 2300, 2100, 1500]),
        P("Sobre las 19.709 ventanas de los tres meses de test, contactar al 20 % con modelo en lugar de al azar vale unos USD 52.000 de margen incremental; anualizado, del orden de USD 200.000 con estos supuestos conservadores, sin contar el efecto sobre la recompra. Contra un costo del primer año de USD 30.000 a 45.000 más el piloto, la inversión se recupera en el primer trimestre de operación. El modelo sigue siendo rentable con un uplift del 5 % y un valor de USD 100 por service; el umbral de rentabilidad de un contacto humano es p ≥ 0,08, así que casi toda la población \"vale\" un recordatorio digital y sólo el segmento Alto justifica un llamado."),
        P("**Cuánto cuesta equivocarse.** Un falso positivo (contactar a quien iba a volver) cuesta un llamado y, si se ofrece un incentivo, subsidia un retorno orgánico: por eso el incentivo se prueba sólo si su contribución incremental supera su costo. Un falso negativo (no contactar a quien se va) cuesta el service y, acumulado, el cliente. La asimetría, cercana a 80 a 1 con estos supuestos, es la razón para contactar a todo el segmento Alto y no economizar llamados en la cola."),
        P("**Cómo se mide.** Piloto de 90 días: dentro de cada decil de riesgo, mitad de los clientes reciben la acción del segmento y mitad el proceso actual, con asignación aleatoria por cliente (todos sus vehículos en el mismo brazo) y estratificada por concesionario. Se mide mantenimiento completado a 30 y a 120 días por decil, acción, concesionario y mes. Con 6.000 a 7.000 ventanas por mes, un uplift de 5 puntos se detecta en dos meses."),
    ])

    S["innovacion"] = "".join([
        P("La innovación de esta propuesta no está en el algoritmo, que es el estándar de la industria, sino en cómo se definió el problema y en la evidencia con la que se sostiene:"),
        BUL("**Una ventana por vehículo derivada de los datos y validada contra el plan oficial.** En lugar de una regla de calendario, cada vehículo tiene su vencimiento estimado por generación y ritmo de uso propio; la sensibilidad a 36 combinaciones de parámetros y el contraste con una solución independiente muestran que el horizonte es la decisión que más importa, y por qué."),
        BUL("**Detección y demostración de dos fugas de información** (KM y conectividad) que inflan el rendimiento aparente. Se cuantificó el efecto (0,813 vs 0,740 de ROC-AUC) y se muestra al jurado como evidencia de rigor, no como resultado."),
        BUL("**Probabilidades calibradas y drivers en castellano por vehículo**, para que el asesor de service entienda por qué ese cliente está primero, con reglas operativas explícitas (turno ya agendado, días restantes, un contacto por usuario)."),
        BUL("**Hallazgos de negocio contraintuitivos con evidencia**: el plan es por kilómetros y no anual; el primer service concentra el churn; los no-shows sólo pesan junto con la cantidad de turnos; el concesionario es un driver estable y accionable; Ford ya tiene un incentivo por continuidad para comunicar."),
        BUL("**Recompra medible dentro del dataset**, que abre un segundo modelo directo sobre el objetivo de largo plazo del desafío."),
        BUL("**Verificación adversarial de todo el análisis**: cada informe fue recalculado por un revisor independiente con código propio; las afirmaciones que no resistieron se corrigieron y quedaron registradas. La revisión cruzada con la solución independiente se hizo con el mismo estándar."),
    ])

    S["futuro"] = "".join([
        P("**Pasos para continuar.** (1) Validar con Posventa las dos reglas que fijan el horizonte: con cuánta anticipación conviene contactar (−30 o −60 días) y cuántos días después del vencimiento Ford considera perdida la oportunidad (+60, +90 o +120). (2) Incorporar las exclusiones de identidad y el cupo por usuario al pipeline, tests automáticos de seguridad temporal y hashes de integridad de los datos de origen, e intervalos de confianza por bootstrap en la evaluación. (3) Validación prospectiva: congelar el modelo entrenado hasta marzo de 2026 y evaluarlo sobre las ventanas de abril a julio de 2026 sin volver a tocar definiciones; pedir un extracto nuevo para una segunda validación ciega. (4) Piloto aleatorizado de 90 días e integración a Service Leads y Service Reminder. (5) Kilometraje de telemetría de los vehículos conectados para individualizar la ventana del primer service, que hoy es imprecisa (±140 días) y es la que más churn concentra. (6) Segundo modelo de recompra Ranger→Ranger sobre los dueños activos, para medir el vínculo service–recompra. (7) Con los datos del piloto, un modelo de uplift que priorice a quién conviene contactar y no sólo a quién se va."),
        P("**Replicabilidad.** La solución depende sólo de dos tablas que Ford tiene para toda su gama y toda la región (ventas y agenda), de un plan de mantenimiento por modelo y de una tasa de uso por vehículo. Extenderla a otros modelos es cambiar el intervalo del plan en la configuración; extenderla a otro país, apuntar a las mismas tablas de BigQuery. El código está parametrizado, documentado y se ejecuta con un comando; los supuestos económicos están en un archivo aparte para que cada mercado ponga los suyos."),
    ])

    S["conclusiones"] = "".join([
        P("Ford pierde cuatro de cada diez mantenimientos en ventana porque le habla igual a todos. Esta propuesta convierte la población elegible en una lista priorizada con probabilidad calibrada, segmento y explicación por vehículo, construida con una definición de ventana y target derivada de los datos y alineada con el plan oficial de mantenimiento. Evaluada fuera de tiempo, alcanza al 36 % de los churners con el 20 % de los contactos y al 65 % con 3.000 contactos por mes, con probabilidades que coinciden con la realidad observada."),
        P("El valor para Ford es operativo y medible: mejor uso de la capacidad de contacto de la red, más services completados, y un punto de contacto sostenido que protege la recompra. Los próximos pasos concretos son validar el horizonte con Posventa, integrar el score a Service Leads y Service Reminder, correr el piloto aleatorizado de 90 días y medir por decil, acción, concesionario y mes. Todo lo necesario para hacerlo está en el .zip adjunto y se reproduce con un comando."),
    ])
    return S


# ------------------------------------------------------------------ ensamblado sobre el template
def build():
    src = zipfile.ZipFile(TEMPLATE)
    parts = {n: src.read(n) for n in src.namelist()}
    xml = parts["word/document.xml"].decode("utf8")
    S = contenido()

    # portada (los textos vienen partidos en varios runs: se reemplaza el párrafo entero por su paraId)
    def replace_para_by_id(xml, para_id, new_text, size=None):
        m = re.search(r'<w:p [^>]*w14:paraId="' + para_id + r'".*?</w:p>', xml, flags=re.S)
        assert m, para_id
        p = m.group(0)
        ppr = re.search(r"<w:pPr>.*?</w:pPr>", p, flags=re.S).group(0)
        sz = f'<w:sz w:val="{size}"/>' if size else ""
        newp = f'<w:p>{ppr}<w:r><w:rPr><w:b/><w:w w:val="105"/>{sz}</w:rPr><w:t xml:space="preserve">{escape(new_text)}</w:t></w:r></w:p>'
        return xml.replace(p, newp)

    xml = replace_para_by_id(xml, "6FAF6FE3", "Desafío 1: Data-Driven Repurchase based on Service Retention", size=24)
    xml = replace_para_by_id(xml, "6FAF6FE4", "Equipo: SIMtec")
    # integrantes: primera fila con Franco; las otras quedan como placeholders para completar
    tbl = re.search(r"<w:tbl>.*?</w:tbl>", xml, flags=re.S).group(0)
    rows = [r for r in re.findall(r"<w:tr[ >].*?</w:tr>", tbl, flags=re.S) if "Apellido," in r]
    r1 = rows[0]
    r1n = r1.replace("<w:t>Apellido,</w:t>", "<w:t>Malfetano,</w:t>").replace("<w:t>Nombre</w:t>", "<w:t>Franco Tomás</w:t>")
    r1n = r1n.replace("<w:t>correo@dominio.edu.ar</w:t>", "<w:t>franmalfe@gmail.com</w:t>")
    xml = xml.replace(r1, r1n, 1)

    # índice: reemplazar las entradas estáticas por un campo TOC
    toc_entries = re.findall(r'<w:p[ >](?:(?!</w:p>).)*?<w:pStyle w:val="TOC\d"/>.*?</w:p>', xml, flags=re.S)
    assert toc_entries
    toc_field = ('<w:p><w:pPr><w:pStyle w:val="TOC1"/><w:tabs><w:tab w:val="right" w:leader="dot" w:pos="8901"/></w:tabs><w:ind w:left="170"/></w:pPr>'
                 '<w:r><w:fldChar w:fldCharType="begin" w:dirty="true"/></w:r><w:r><w:instrText xml:space="preserve"> TOC \\o "1-3" \\h \\z \\u \\b cuerpo_informe </w:instrText></w:r>'
                 '<w:r><w:fldChar w:fldCharType="separate"/></w:r><w:r><w:t>Actualizar campo (F9) para generar el índice.</w:t></w:r><w:r><w:fldChar w:fldCharType="end"/></w:r></w:p>')
    xml = xml.replace(toc_entries[0], toc_field, 1)
    for e in toc_entries[1:]:
        xml = xml.replace(e, "", 1)

    # cuerpo: reemplazar los párrafos placeholder que siguen a cada encabezado
    def section(xml, heading_bookmark, new_body, drop_until_next_heading=True):
        m = re.search(r'<w:p[ >](?:(?!</w:p>).)*?w:name="' + heading_bookmark + r'".*?</w:p>', xml, flags=re.S)
        assert m, heading_bookmark
        start = m.end()
        nxt = re.search(r'<w:p[ >](?:(?!</w:p>).)*?<w:pStyle w:val="Heading\d"/>', xml[start:], flags=re.S)
        end = start + (nxt.start() if nxt else xml[start:].find("<w:sectPr"))
        return xml[:start] + new_body + xml[end:]

    xml = section(xml, "Descripción_del_Desafío", S["desafio"])
    xml = section(xml, "Resumen_Ejecutivo_de_la_Solución", S["resumen"])
    xml = section(xml, "Especificaciones_Técnicas", S["especificaciones"])
    xml = section(xml, "Información_Complementaria", S["complementaria"])
    xml = section(xml, "Seguridad_y_Ergonomía", S["seguridad"])
    xml = section(xml, "Factibilidad_Económica", S["economica"])
    xml = section(xml, "Valor_Diferencial_e_Innovación", S["innovacion"])
    xml = section(xml, "Trabajo_Futuro", S["futuro"])
    xml = section(xml, "Conclusiones", S["conclusiones"])
    # "Descripción de la Solución" (H1) no tiene cuerpo propio en el template: queda como está.

    # saltos de página antes de cada Heading1 (Índice incluido) para que cada sección arranque en hoja nueva
    def add_pagebreaks(xml):
        out = []; pos = 0
        for i, m in enumerate(re.finditer(r'<w:p[ >](?:(?!</w:p>).)*?<w:pStyle w:val="Heading1"/>.*?</w:p>', xml, flags=re.S)):
            out.append(xml[pos:m.start()])
            if i > 0:
                out.append(PAGEBREAK())
            if i == 1:
                out.append('<w:bookmarkStart w:id="900" w:name="cuerpo_informe"/>')
            out.append(m.group(0)); pos = m.end()
        out.append(xml[pos:])
        return "".join(out)
    xml = add_pagebreaks(xml)
    xml = xml.replace("<w:lastRenderedPageBreak/>", "")
    k = xml.rfind("<w:sectPr")  # el sectPr del cuerpo (la portada tiene el suyo dentro de un párrafo)
    xml = xml[:k] + '<w:bookmarkEnd w:id="900"/>' + xml[k:]

    parts["word/document.xml"] = xml.encode("utf8")

    # relaciones e imágenes
    rels = parts["word/_rels/document.xml.rels"].decode("utf8")
    add = "".join(f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="{target}"/>'
                  for rid, (target, _) in zip(_rels, _media))
    parts["word/_rels/document.xml.rels"] = rels.replace("</Relationships>", add + "</Relationships>").encode("utf8")
    for target, path in _media:
        parts["word/" + target] = path.read_bytes()
    ct = parts["[Content_Types].xml"].decode("utf8")
    if 'Extension="png"' not in ct:
        ct = ct.replace("</Types>", '<Default Extension="png" ContentType="image/png"/></Types>')
    parts["[Content_Types].xml"] = ct.encode("utf8")

    # viñetas propias (numId 4)
    num = parts["word/numbering.xml"].decode("utf8")
    abs_ = ('<w:abstractNum w:abstractNumId="9"><w:multiLevelType w:val="hybridMultilevel"/>'
            '<w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="bullet"/><w:lvlText w:val="•"/><w:lvlJc w:val="left"/>'
            '<w:pPr><w:ind w:left="560" w:hanging="220"/></w:pPr><w:rPr><w:rFonts w:ascii="Palatino Linotype" w:hAnsi="Palatino Linotype"/></w:rPr></w:lvl></w:abstractNum>')
    num = num.replace("<w:num ", abs_ + "<w:num ", 1)
    num = num.replace("</w:numbering>", '<w:num w:numId="4"><w:abstractNumId w:val="9"/></w:num></w:numbering>')
    parts["word/numbering.xml"] = num.encode("utf8")

    OUT_DOCX.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUT_DOCX, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in parts.items():
            z.writestr(name, data)
    print("docx:", OUT_DOCX, f"({OUT_DOCX.stat().st_size/1024:.0f} KB), figuras: {len(_media)}")


def _python_con_uno() -> str | None:
    """Un intérprete que pueda `import uno` (el del .venv normalmente no; el del sistema sí, con python3-uno)."""
    for py in (sys.executable, shutil.which("python3"), "/usr/bin/python3",
               "/Applications/LibreOffice.app/Contents/Resources/python"):
        if py and Path(py).exists() and subprocess.run([py, "-c", "import uno"], capture_output=True).returncode == 0:
            return py
    return None


def export_pdf_libreoffice():
    """Actualiza el índice y exporta a PDF con LibreOffice (Linux/macOS)."""
    py = _python_con_uno()
    if not py:
        sys.exit("Falta el módulo uno de LibreOffice. En Ubuntu/Debian: sudo apt install libreoffice-writer python3-uno")
    r = subprocess.run([py, str(ROOT / "scripts" / "exportar_pdf_libreoffice.py"), str(OUT_DOCX), str(OUT_PDF)],
                       capture_output=True, text=True, timeout=300)
    print(r.stdout.strip(), r.stderr.strip()[-1000:])
    if r.returncode != 0:
        sys.exit("Falló la exportación a PDF con LibreOffice.")


def export_pdf():
    """Actualiza el índice y exporta a PDF con Word (COM) en Windows, o con LibreOffice en el resto."""
    if sys.platform != "win32":
        export_pdf_libreoffice()
        return
    ps = f'''
$word = New-Object -ComObject Word.Application
$word.Visible = $false; $word.DisplayAlerts = 0
$doc = $word.Documents.Open("{OUT_DOCX}")
$doc.Fields.Update() | Out-Null
foreach ($t in $doc.TablesOfContents) {{ $t.Update() }}
$doc.Save()
$doc.ExportAsFixedFormat("{OUT_PDF}", 17)
"paginas: " + $doc.ComputeStatistics(2)
$doc.Close(0); $word.Quit()
'''
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True, timeout=300)
    print(r.stdout.strip(), r.stderr.strip()[:500])


if __name__ == "__main__":
    build()
    export_pdf()
    print("pdf:", OUT_PDF, f"({OUT_PDF.stat().st_size/1024:.0f} KB)")
