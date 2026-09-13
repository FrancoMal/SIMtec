# Status.md — Bitácora del repo

Este archivo es la **memoria del proyecto**. Cada vez que se hace un cambio relevante (limpieza,
decisión de equipo, avance técnico, entrega, etc.) se agrega una entrada nueva arriba de todo, con
fecha y qué se hizo. No se borran entradas viejas: esto es un historial, no un resumen que se
sobreescribe.

Formato fijo de cada entrada (usar siempre esta misma estructura):

```
### YYYY-MM-DD — título corto
- **Qué se hizo**: ...
- **Estado**: (opcional, solo si aplica un semáforo/bloqueo)
- **Pendiente / próximos pasos**: ...
```

---

## ⚠️ Regla fija: ninguna IA hace commit ni push en este repo

**Ninguna IA (Claude, ChatGPT, Copilot, o cualquier otro asistente) puede ejecutar `git commit`,
`git push`, ni ninguna otra acción que modifique el historial o el remoto de este repositorio.**

- Una IA puede: proponer cambios, editar archivos localmente, y **sugerir** cuándo conviene
  commitear o pushear (por ejemplo: "esto ya está listo para un commit").
- Una IA **no puede**: decidir por su cuenta ejecutar `git add`, `git commit` o `git push`.
- El commit y el push siempre los hace una persona del equipo, revisando antes qué se sube.

Esta regla aplica a toda sesión futura de cualquier asistente que trabaje sobre este repo.

---

## Bitácora

### 2026-09-13 — Fase actual: esperando dataset de Ford + documentación de entregables
- **Qué se hizo**:
  - Se creó `desafio-1-repurchase-propensity/ENTREGABLES.md`, que cruza el **entregable oficial**
    según el Reglamento (§5: un único PDF con la idea propuesta, a umonten1@ford.com y
    avedia@ford.com antes del 25/09/2026 23:59) con los **entregables de trabajo** mencionados
    por el tutor (documento, dashboard, notebook, presentación), y deja un checklist concreto.
  - Se dejó explícito el estado actual del proyecto: **todavía no llegó el dataset de Ford**, así
    que el equipo está en fase de **investigación y planificación**, no de desarrollo. No tiene
    sentido escribir el pipeline final sin conocer la estructura real de los datos.
- **Estado**: 🟡 **Bloqueados por el dataset.** Mientras tanto, foco en dejar toda la
  documentación (SPEC, entregables, estructura de carpetas) lo más detallada posible para poder
  arrancar rápido apenas lleguen los datos.
- **Pendiente / próximos pasos**:
  - Recibir el dataset de Ford (post kick-off, sin fecha confirmada todavía).
  - Confirmar con el mentor las dudas abiertas en `SPEC.md` §2 y `ENTREGABLES.md` §5 (target
    exacto, si "documento" del tutor = PDF oficial, si dashboard/notebook se entregan o solo se
    muestran en el Trials Day).
  - Una vez llegue el dataset: EDA inicial → baseline → iterar (ver `SPEC.md` §3).

### 2026-09-13 — Notas de la reunión con el tutor (11/9) incorporadas al SPEC
- **Qué se hizo**:
  - Se agregó `desafio-1-repurchase-propensity/notas-tutor-2026-09-11.md` con las notas crudas
    (reordenadas por tema) de la interacción con el tutor del proyecto — el nexo entre Ford y el
    equipo.
  - Se actualizó `desafio-1-repurchase-propensity/SPEC.md` con lo que ya quedó definido:
    - Variables clave confirmadas: fecha del último service + kilometraje, `schedule_id`, ciclo
      de service cada 15.000 km o 1 año, datos enmascarados.
    - Posible **reframing del target**: en vez de (o además de) predecir recompra directamente,
      predecir la probabilidad de que el cliente **no vaya al service programado del próximo
      mes** — el tutor lo plantea como la causa raíz que después deriva en pérdida de recompra.
      Queda pendiente confirmar con Ford/mentores cuál es el target principal esperado.
    - Caso especial de **transferencia de titularidad** del vehículo a un nuevo dueño.
    - Confirmado que la evaluación del proyecto es por **backtesting + lift** (no opcional).
    - Entregables mencionados por el tutor: documento, dashboard, notebook, presentación
      (consistente con lo ya sabido por el reglamento).
- **Pendiente / próximos pasos**:
  - Confirmar en el kick-off/con mentores cuál de los dos targets (recompra vs. no-asistencia a
    service) es el principal.
  - Definir el criterio exacto de los "3 tipos" de cliente que mencionó el tutor.

### 2026-09-13 — Limpieza del repo y estructura base
- **Qué se hizo**:
  - Se limpió el repo para dejar solo lo relacionado al desafío asignado al equipo:
    **Repurchase Propensity** (Customer Experience).
  - Se eliminaron las carpetas `desafio-2-powertrain-intelligence/` y
    `desafio-3-predictive-quality/` (desafíos que no nos tocaron).
  - Se eliminaron `FIC3-analisis-y-estrategia.md` (análisis general de los 3 desafíos, hecho
    antes de la selección) y `Transcripcion reunion FIC III.txt` (transcripción de la reunión
    informativa general).
  - Se mantuvieron sin modificar: `Reglamento FIC 3_v3.pdf`, `Resumen Desafios FIC_3 - AI
    Edition.pdf`, `Calendario FIC III.jpg` y `desafio-1-repurchase-propensity/SPEC.md`.
  - Se agregó `ESTRUCTURA.md` con una propuesta de organización de carpetas para el trabajo del
    desafío (data/notebooks/src/app/reports).
  - Se creó este `Status.md` como bitácora del repo.
- **Pendiente / próximos pasos**:
  - Confirmar con el equipo si se adopta la estructura de `ESTRUCTURA.md`.
  - Esperar el dataset de Ford (post kick-off) para empezar EDA.
  - Decidir si se hace commit de esta limpieza (recordar: lo hace una persona, no la IA).

<!-- Nuevas entradas: agregar arriba de esta línea, con el formato ### YYYY-MM-DD — título -->
