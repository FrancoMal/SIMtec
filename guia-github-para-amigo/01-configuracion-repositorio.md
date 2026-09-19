# 1. Configuración inicial del repositorio

## Crear el repositorio

En GitHub:

1. Crear una organización o usar la existente.
2. Crear el repositorio con visibilidad `Private`.
3. Activar README si todavía no existe código.
4. No subir `.env`, credenciales, dumps de base de datos ni archivos generados.
5. Agregar colaboradores mediante equipos, evitando permisos individuales innecesarios.

## Permisos sugeridos

- `Admin`: sólo quienes administran la organización o el repositorio.
- `Maintain`: responsables técnicos que gestionan issues, PRs y releases.
- `Write`: desarrolladores que trabajan en ramas y PRs.
- `Triage`: personas que clasifican Issues sin modificar código.
- `Read`: consulta.

Para un proyecto chico, usar al menos una persona responsable de revisión además de quien desarrolla. Nadie debería necesitar push directo a `main`.

## Estructura mínima

```text
.
├── .github/
│   ├── workflows/
│   │   └── security.yml
│   ├── ISSUE_TEMPLATE/
│   ├── pull_request_template.md
│   └── CODEOWNERS
├── README.md
└── .gitignore
```

Copiar `02-pipeline-seguridad.yml` como `.github/workflows/security.yml` y `08-codeowners` como `.github/CODEOWNERS`.

## Secretos

En `Settings > Secrets and variables > Actions`:

- secretos generales: sólo si realmente son comunes al repositorio;
- secretos de organización: para reutilizar controles en varios repositorios;
- secretos de entorno: preferidos para producción.

Ejemplo de nombres, sin valores reales:

```text
COOLIFY_DEPLOY_WEBHOOK
COOLIFY_API_TOKEN
```

Configurar el entorno `production` y agregarle revisores requeridos. El workflow debe referenciar `environment: production` para que el job quede sujeto a esa aprobación.

Nunca imprimir secretos con `echo`, agregarlos a una URL pública, guardarlos en el código ni usar `pull_request_target` para ejecutar código no confiable con secretos.

## Etiquetas recomendadas

Crear etiquetas consistentes:

- `bug`: comportamiento incorrecto;
- `feature`: funcionalidad nueva;
- `security`: seguridad o privacidad;
- `documentation`: documentación;
- `question`: consulta pendiente;
- `priority: high`, `priority: medium`, `priority: low`;
- `status: needs-info`, `status: in-progress`, `status: blocked`.

