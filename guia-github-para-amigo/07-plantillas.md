# 7. Plantillas para copiar

## `.github/pull_request_template.md`

```markdown
## Qué cambia

<!-- Explicar el cambio en pocas líneas. -->

## Issue relacionado

Closes #

## Cómo se probó

- [ ] Tests automatizados
- [ ] Prueba manual
- [ ] No aplica (explicar)

## Seguridad y datos

- [ ] No agregué secretos ni datos sensibles.
- [ ] Revisé permisos, validaciones y logs.
- [ ] No cambia migraciones ni configuración de producción.
- [ ] Si cambia, describir rollback:

## Checklist

- [ ] El PR tiene alcance acotado.
- [ ] Actualicé documentación si corresponde.
- [ ] Los checks de CI están verdes.
- [ ] Agregué capturas si cambia la interfaz.
```

## `.github/ISSUE_TEMPLATE/bug_report.md`

```markdown
---
name: Reporte de bug
about: Informar un comportamiento incorrecto
title: "[BUG] "
labels: [bug]
---

## Descripción

## Entorno y versión

## Pasos para reproducir

1.
2.
3.

## Resultado esperado

## Resultado actual

## Evidencia sanitizada

<!-- Nunca incluir tokens, contraseñas ni datos personales. -->
```

## `.github/ISSUE_TEMPLATE/task.md`

```markdown
---
name: Tarea
about: Trabajo planificado
title: "[TASK] "
labels: [feature]
---

## Objetivo

## Criterios de aceptación

- [ ]

## Dependencias o riesgos

## Fuera de alcance
```

