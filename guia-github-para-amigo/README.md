# Guía práctica: configurar GitHub con seguridad y buen flujo de trabajo

Esta guía explica cómo replicar en GitHub una configuración similar a la usada en el entorno de GitLab de CITED:

- repositorios privados y organizados por equipos o programas;
- ramas de trabajo y `main` protegida;
- Pull Requests obligatorios;
- pipeline de seguridad con Gitleaks, Semgrep y Trivy;
- deploy separado y protegido;
- Issues, etiquetas, respuestas y cierre con evidencia.

La guía usa nombres y secretos de ejemplo. No copiar IPs internas, tokens, UUID, contraseñas, URLs privadas ni archivos `.env`.

## Orden recomendado

1. Crear el repositorio y sus equipos.
2. Agregar la estructura de carpetas y archivos de esta guía.
3. Configurar secretos y el entorno `production`.
4. Configurar la protección de `main`.
5. Abrir un PR de prueba y verificar los checks.
6. Habilitar el deploy únicamente cuando el flujo anterior funcione.

## Archivos incluidos

| Archivo | Para qué sirve |
|---|---|
| `01-configuracion-repositorio.md` | Repositorio, permisos, etiquetas y secretos |
| `02-pipeline-seguridad.yml` | Workflow de GitHub Actions para los tres escaneos |
| `03-proteccion-de-ramas.md` | Reglas de `main` y ramas de trabajo |
| `04-flujo-pull-request.md` | Cómo trabajar, revisar y mergear un PR |
| `05-issues-y-respuestas.md` | Cómo crear, contestar, derivar y cerrar Issues |
| `06-buenas-practicas.md` | Reglas diarias de seguridad y colaboración |
| `07-plantillas.md` | Plantillas para PR, bug y tarea |
| `08-codeowners` | Ejemplo de responsables automáticos de revisión |

## Equivalencia con el GitLab original

| GitLab | GitHub |
|---|---|
| Merge Request | Pull Request |
| Protected branch | Branch protection rule o ruleset |
| GitLab CI | GitHub Actions |
| Variables CI/CD | Repository/Organization/Environment Secrets |
| Runner con tag de deploy | Runner o job de deploy asociado a `production` |
| Include de plantilla | Workflow reutilizable o archivo copiado en `.github/workflows/` |

## Criterio de éxito

Un cambio sólo llega a `main` cuando tiene PR, revisión, checks verdes y cumple las reglas de protección. Un deploy de producción sólo usa secretos del entorno protegido y se ejecuta desde `main`.

## Referencias oficiales

- [Protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches)
- [GitHub Actions: secrets](https://docs.github.com/en/actions/concepts/security/secrets)
- [Environments y deployments](https://docs.github.com/en/actions/reference/deployments-and-environments)
- [Workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax)
