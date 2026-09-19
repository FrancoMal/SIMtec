# 5. Issues: crear, contestar y cerrar

## Cómo crear un Issue útil

Un Issue debe permitir que otra persona entienda el problema sin una conversación privada adicional.

Incluir:

- título concreto: `Login devuelve 500 al usar contraseña vencida`;
- contexto y versión;
- pasos para reproducir;
- resultado esperado;
- resultado actual;
- evidencia sanitizada: logs, capturas o request sin tokens;
- impacto y prioridad;
- criterio de aceptación.

No incluir contraseñas, tokens, datos personales ni URLs con credenciales. Un incidente de seguridad no debe quedar con detalles sensibles en un Issue público: usar el canal privado definido por el equipo.

## Cómo contestar un Issue

La primera respuesta debería confirmar recepción y ordenar el siguiente paso:

```text
Gracias por reportarlo. Lo reproducimos en [entorno/versión] y confirmamos [síntoma].
Queda priorizado como [prioridad]. El próximo paso es [acción] y lo tomamos [persona/equipo].
Actualizamos este Issue cuando tengamos evidencia o una fecha concreta.
```

Si falta información:

```text
Para reproducirlo necesitamos: versión, pasos exactos y un ejemplo sanitizado.
No envíes credenciales ni tokens. Lo dejamos como `status: needs-info` hasta recibir esos datos.
```

Si no se puede reproducir:

```text
No pudimos reproducirlo con la versión [X] y los pasos indicados. Probamos [resumen].
¿Podés confirmar [dato]? Si no aparece nueva evidencia, lo cerraremos como no reproducible.
```

## Estados recomendados

- nuevo: recibido y sin clasificar;
- needs-info: falta información del reportante;
- triaged: confirmado, con prioridad y responsable;
- in-progress: hay trabajo en curso;
- blocked: depende de una decisión o tercero;
- done: resuelto y verificado;
- won't-fix / duplicate / not reproducible: cierre con explicación.

## Cómo cerrar

Cerrar sólo dejando una respuesta final con:

- causa o motivo del cierre;
- PR, commit, release o decisión relacionada;
- entorno y evidencia de verificación;
- limitaciones conocidas;
- pasos posteriores, si quedan.

Ejemplo:

```text
Resuelto en el PR #145 y publicado en la versión 2.3.1.
Verificado en staging con los casos A, B y C. El Issue queda cerrado.
```

Si un PR realmente resuelve el Issue, usar `Closes #123` para mantener la trazabilidad automática.

