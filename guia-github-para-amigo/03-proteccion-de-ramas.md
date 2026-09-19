# 3. Protección de ramas

En `Settings > Rules > Rulesets` o `Settings > Branches`, crear una regla para `main`.

## Valores recomendados para `main`

- exigir Pull Request antes de mergear;
- exigir al menos 1 aprobación de otra persona;
- exigir que los aprobadores no sean quien abrió el PR;
- exigir que los checks `Gitleaks - secretos`, `Semgrep - SAST` y `Trivy - vulnerabilidades críticas` estén verdes;
- exigir que la rama esté actualizada antes del merge;
- descartar aprobaciones obsoletas cuando cambie el código;
- exigir revisión de CODEOWNERS cuando corresponda;
- bloquear push directo;
- bloquear force push;
- bloquear eliminación de `main`;
- permitir merge sólo con estrategia definida por el equipo, preferentemente squash para cambios pequeños.

No habilitar excepciones generales. Si una persona administradora necesita saltarse la regla por una emergencia, debe dejar registro del motivo, del riesgo aceptado y de la corrección posterior.

## Protección de ramas de trabajo

Usar nombres como:

```text
feature/nombre-corto
fix/nombre-del-error
security/actualizar-dependencia
docs/nombre-del-cambio
```

No crear ramas permanentes por persona. Borrar la rama después del merge, salvo que se necesite conservarla por una razón documentada.

## Verificación

Abrir un PR de prueba y comprobar que:

1. aparecen los tres checks;
2. no se puede mergear con un check rojo;
3. no se puede hacer push directo a `main`;
4. un cambio posterior al aprobado vuelve a pedir revisión si así se configuró;
5. el deploy no corre desde una rama que no sea `main`.

