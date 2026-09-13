# Entregables — Desafío 1 (Repurchase Propensity)

Este archivo junta, en un solo lugar, **qué hay que entregar, a quién, cuándo y con qué
contenido**, cruzando lo que dice el Reglamento oficial con lo que agregó el tutor en la reunión
del 11/9. Se actualiza a medida que se confirmen detalles con los mentores.

## 1. Entregable oficial (obligatorio — Reglamento §5)

Esto es lo único que el Reglamento exige formalmente, y de lo único que depende quedar en pie en
el concurso:

| Ítem | Detalle |
|---|---|
| **Formato** | Un **único archivo PDF** con una explicación detallada de la idea propuesta (Reglamento §5.1.1). |
| **Cómo se envía** | Por mail a **umonten1@ford.com** y **avedia@ford.com** (Reglamento §5.2). |
| **Fecha límite** | **25/09/2026, 23:59** (Reglamento §5.2 y calendario oficial). |
| **Quién lo evalúa** | Jurado del desafío: directores, gerentes y supervisores de Ford (Reglamento §5.3). |
| **Criterio de evaluación** | Originalidad, creatividad y uso de las herramientas enseñadas durante el concurso (Reglamento §8.1). |

> ⚠️ No hay reenvío automático post Trials Day salvo que los mentores lo confirmen — el PDF es el
> entregable que se juzga. Ver el checklist inmediato al final de este archivo.

### Contenido sugerido del PDF

Ya está desarrollado en detalle en [`SPEC.md` §7](./SPEC.md#7-estructura-del-pdf-final):
resumen ejecutivo, entendimiento del problema, datos y EDA, metodología, resultados (curva de
lift + métricas), señales predictoras (SHAP), segmentos accionables + demo, ROI estimado,
limitaciones y roadmap.

## 2. Entregables de trabajo mencionados por el tutor (11/9)

El tutor mencionó cuatro ítems clave para el proceso, que no necesariamente son el mismo archivo
que el PDF oficial, sino piezas de apoyo para construirlo y para el Trials Day:

| Ítem | Para qué sirve | Dónde vive en este repo |
|---|---|---|
| **Documento** | Probablemente el PDF oficial del Reglamento (ver §1), o un documento técnico intermedio de trabajo. **Confirmar con el mentor si es lo mismo.** | `SPEC.md` §7 (estructura) |
| **Dashboard** | Demo interactiva (ej. Streamlit) para mostrar la "bandeja de clientes priorizados" — ya estaba previsto en `SPEC.md` §5-6. | `desafio-1-repurchase-propensity/app/` (a crear cuando haya datos) |
| **Notebook** | Evidencia técnica del análisis: EDA, features, modelado, validación. | `desafio-1-repurchase-propensity/notebooks/` (a crear cuando haya datos) |
| **Presentación** | Para el Trials Day (2/10): problema → enfoque → resultados → impacto → próximos pasos, ~10 min, hablan los 3. | A definir — probablemente slides separadas del PDF |

## 3. Fechas clave (fuente: `Calendario FIC III.jpg` + Reglamento §4.2)

| Fecha | Evento | Estado |
|---|---|---|
| 11/09/2026 | Kick-off en Planta Pacheco (firma del Reglamento, asignación de mentores) | ✅ Ya ocurrió |
| **25/09/2026 23:59** | Entrega del PDF final (único entregable oficial) | ⬜ Pendiente |
| 02/10/2026 | Trials Day en Pacheco: presentación de avances + feedback + tiempo para pulir | ⬜ Pendiente |
| Semana del 05/10/2026 | Awards / premiación | ⬜ Pendiente |

## 4. Bloqueante actual

**Todavía no tenemos el dataset de Ford.** Hasta que llegue, el trabajo del equipo está en fase
de **investigación y planificación** (definir target, features hipotéticas, preguntas para el
mentor, armar el repo template) y no de desarrollo — no tiene sentido escribir el pipeline final
sin conocer la estructura real de los datos. Ver `Status.md` para el estado actualizado de esta
espera.

## 5. Checklist de entregables

- [ ] Confirmar con el mentor si "documento" (tutor) = PDF oficial (Reglamento) o son cosas
      distintas.
- [ ] Confirmar si el dashboard/notebook se entregan junto con el PDF o solo se muestran en el
      Trials Day.
- [ ] Recibir el dataset de Ford.
- [ ] EDA inicial sobre el dataset real.
- [ ] Baseline funcionando.
- [ ] Notebook de modelado + SHAP.
- [ ] Dashboard/demo mínimo.
- [ ] Redactar el PDF final (usar la estructura de `SPEC.md` §7).
- [ ] Armar la presentación para el Trials Day.
- [ ] Enviar el PDF a umonten1@ford.com y avedia@ford.com antes del 25/09/2026 23:59.
