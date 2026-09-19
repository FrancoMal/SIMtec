# 4. Flujo de Pull Request

## Antes de programar

1. Buscar si ya existe un Issue relacionado.
2. Si el cambio es relevante, crear o asignarse el Issue.
3. Definir alcance y criterio de aceptación.
4. Crear una rama desde `main` actualizada.

```bash
git switch main
git pull --ff-only origin main
git switch -c feature/nombre-corto
```

## Durante el trabajo

- hacer commits pequeños y explicativos;
- no mezclar refactor, funcionalidad y cambios de formato sin necesidad;
- no subir secretos;
- agregar o actualizar pruebas;
- ejecutar localmente los checks relevantes;
- mantener el PR enfocado.

```bash
git add .
git commit -m "Agrega validación de inscripción"
git push -u origin feature/nombre-corto
```

## Cómo abrir el PR

El título debe explicar el cambio. La descripción debe incluir:

- qué problema resuelve;
- qué se modificó;
- cómo se probó;
- riesgos o migraciones;
- capturas si cambia la interfaz;
- vínculo al Issue, por ejemplo `Closes #123` si el PR lo resuelve.

Asignar revisores y etiquetas. No pedir aprobación sin que el PR esté listo, salvo que se marque expresamente como Draft.

## Cómo revisar

La revisión debe concentrarse en comportamiento, seguridad, datos, errores y mantenibilidad. Comentar sobre el código, no sobre la persona.

- `Approve`: está listo.
- `Request changes`: hay un problema que debe resolverse.
- comentario normal: observación o pregunta que no bloquea.

Quien abre el PR responde cada comentario indicando qué hizo o por qué propone otra solución. Luego vuelve a solicitar revisión.

## Merge

Mergear sólo cuando el PR tenga aprobaciones, checks verdes y no haya conversaciones relevantes sin resolver. Después:

```bash
git switch main
git pull --ff-only origin main
```

Verificar el deploy, el endpoint principal y los logs. No alcanza con que el job diga `success` si la aplicación no funciona.

