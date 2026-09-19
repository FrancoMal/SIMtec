# 6. Buenas prácticas

## Seguridad

- usar secretos de GitHub, nunca valores en el repositorio;
- rotar credenciales si alguna vez se publicaron;
- fijar permisos mínimos del `GITHUB_TOKEN`;
- actualizar dependencias y atender CVEs críticas;
- revisar especialmente cambios de autenticación, permisos, SQL, archivos y comandos del sistema;
- no ejecutar código de un PR no confiable con secretos de producción;
- mantener backups y un procedimiento de rollback.

## Git y PRs

- una rama por cambio;
- commits que puedan entenderse y revertirse;
- PRs pequeños y revisables;
- descripción orientada a evidencia;
- no aprobar cambios que no se entienden;
- documentar decisiones no obvias;
- eliminar ramas fusionadas.

## CI/CD

- hacer que los checks corran tanto en PR como en `main`;
- no ignorar fallas sin un Issue y fecha de corrección;
- usar versiones controladas de las acciones y revisarlas periódicamente;
- separar validación de deploy;
- usar un entorno `production` con aprobación y concurrencia;
- verificar la aplicación real después del deploy.

## Comunicación

- mantener las conversaciones relevantes en el PR o Issue;
- contestar preguntas aunque la respuesta sea "todavía no lo sabemos";
- distinguir hecho verificado, hipótesis y tarea pendiente;
- agradecer reportes y evitar culpar a quien reporta;
- cerrar con evidencia, no sólo con "listo".

