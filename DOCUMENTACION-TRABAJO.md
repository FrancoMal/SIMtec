# Documentación del trabajo — SIMtec / FIC III Desafío 1

**Última actualización:** 2026-09-19
**Desafío:** Data-Driven Repurchase based on Service Retention
**Entrega oficial:** un único PDF, por mail, **25/09/2026 23:59** · Trials Day **02/10**

---

## 1. Qué pide el desafío

La fuente autoritativa es `Dataset/Ficha_Técnica_FIC3_Data_Strategy_2026_08.docx`.
**Manda sobre cualquier otra interpretación**, incluido lo que digan los documentos de
trabajo de este repo.

Resumen del pedido: para cada usuario con al menos un vehículo dentro de la ventana de
servicio, estimar la **probabilidad de churn** — no completar el próximo mantenimiento
programado en la red oficial dentro del horizonte definido por negocio.

- **Unidad de observación:** usuario–vehículo (VIN)–ventana.
- Cuando un usuario tiene más de un VIN, la solución debe permitir una **vista
  consolidada** sin perder el riesgo específico de cada vehículo.
- **Output mínimo:** `customer_id` seudonimizado, `vehicle_id` seudonimizado, fecha de
  scoring, probabilidad entre 0 y 1, segmento de riesgo y principales drivers.
- **Casos censurados:** las ventanas cuyo horizonte todavía no finalizó **no** pueden
  usarse como churn confirmado.
- **Restricción dura:** ninguna variable posterior a la fecha de scoring puede usarse
  como feature.

### Los nueve criterios de evaluación

1. Correcta formulación de población, ventana y target
2. Ausencia de data leakage y calidad de la validación temporal
3. Poder predictivo: ROC-AUC y **especialmente PR-AUC**, recall/precision sobre churn,
   lift por deciles, recall dentro de una capacidad de contacto definida
4. Calibración de probabilidades
5. Explicabilidad de los drivers
6. Accionabilidad e integración al proceso
7. Viabilidad técnica y reproducibilidad
8. Carácter innovador
9. Claridad del power pitch

Los criterios **1 y 2 son los primeros de la lista** y es donde más se juega.

---

## 2. Marco de trabajo adoptado

Desde el 19/09 el trabajo sigue **`PROMPT_MAESTRO_v2.2.md`**: un bloque `[CORE]` de 14
reglas que se carga siempre, nueve módulos que se activan por ruteo (`DESIGN`, `CODE`,
`REPO`, `AUDIT`, `DIAGNÓSTICO`, `ROADMAP`, `PROMPT`, `DOCUMENTOS`, `BITÁCORA`) y un
`[ANEXO A]` de perfil que se completa por proyecto.

Complementa `guia-github-para-amigo/`, con ocho documentos sobre configuración del
repositorio, pipeline de seguridad, protección de ramas, flujo de pull request, issues,
buenas prácticas, plantillas y CODEOWNERS.

**Regla dura del repo** (también en `Status.md`): ninguna IA ejecuta `git add`,
`git commit` ni `git push`. Puede crear y editar archivos y sugerir cuándo conviene
commitear; **el commit lo hace una persona del equipo**, revisando antes qué se sube.

---

## 3. Los datos

En `Dataset/`, versionados con **Git LFS** por su tamaño:

| Archivo | Tamaño | Contenido |
|---|---:|---|
| `ranger_service_agenda_arg_2024_2026 1.csv` | 281,8 MB | Turnos y servicios de Agenda Ford |
| `ranger_sales_arg_2024_2026.csv` | 11,5 MB | Ventas Ranger Argentina |
| `Ficha_Técnica_FIC3_Data_Strategy_2026_08.docx` | 70 KB | Consigna oficial |

Extractos seudonimizados, sin PII: los campos VIN, persona, turno y dealer están
reemplazados por IDs seudonimizados consistentes. **Repo privado del equipo = entorno
autorizado del challenge. No replicar fuera de acá.**

---

## 4. Contrato de población, ventana y target

Documento completo: `CONTRATO_POBLACION_VENTANA_TARGET_v0.1.md`.

### Universo reconstruido

| | Cantidad |
|---|---:|
| Relaciones usuario–VIN–ventana elegibles | 131.051 |
| Con etiqueta utilizable | 91.370 |
| — de las cuales, churn | 42.733 |
| Sin madurez suficiente (excluidas) | 30.446 |
| Resultado indeterminado | 9.235 |

**Tasa base: 46,77 %** (42.733 / 91.370).

Es **condicional al contrato y al retorno observable en Agenda**: no es una tasa oficial
de abandono de toda la red. Desde 2025, sobre etiquetas utilizables, es 48,96 %.

### Sensibilidad al horizonte

Sobre la **misma cohorte madura**, mover los días de gracia cambia el resultado:

| Gracia | Tasa de churn |
|---:|---:|
| 30 días | 62,91 % |
| 90 días | 46,22 % |
| 120 días | 42,18 % |

**Veinte puntos de diferencia solo por el horizonte.** Esto explica por qué dos
formulaciones distintas del mismo problema pueden dar números incomparables, y por qué el
criterio 1 del jurado pesa tanto.

El horizonte no se elige por la tasa que queda más linda, sino por **cuándo la red
todavía puede actuar a tiempo**: con 120 días el número mejora, pero el aviso llega
cuando el cliente ya se fue.

---

## 5. Riesgos identificados

**ALTO — Evaluación previamente observada.** En una vuelta anterior se miraron datos de
prueba y se iteró sobre eso. Reiniciar el código **no elimina ese antecedente**. Hay que
declarar qué períodos fueron examinados y, si no queda uno independiente, presentar la
evidencia como retrospectiva y proponer validación prospectiva.

**ALTO — Disponibilidad histórica incierta.** Una fecha de evento anterior **no prueba**
que el valor estuviera disponible en ese momento. Hay campos que son fotos tomadas al
extraer los datos, no valores históricos. Sospechosos detectados en la vuelta previa:
`KM` y `ConnectedStatusARG`. Requiere barrido campo por campo.

**MEDIO — Dispersión de esfuerzo.** Dashboard, presentación ampliada y mejoras para el
Trials Day van **después** de asegurar el PDF. Los criterios 1 y 2 no se recortan.

---

## 6. Estado y próximos pasos

- [x] Marco de trabajo adoptado y perfil del proyecto completado
- [x] Perfilado de solo lectura de los datasets
- [x] Contrato de población, ventana y target con números verificados
- [x] Sensibilidad al horizonte medida sobre la misma cohorte
- [ ] Resolver las cinco definiciones pendientes con criterio propio y supuesto documentado
- [ ] Inventario de disponibilidad histórica campo por campo (criterio 2)
- [ ] Declarar períodos observados vs. limpios
- [ ] Pipeline de features, modelo, evaluación temporal
- [ ] Explicabilidad, ranking priorizado, propuesta de activación
- [ ] PDF final

---

## 7. Trabajo previo, como referencia

En `desafio-1-repurchase-propensity/` hay documentación de una vuelta anterior. **Queda
como referencia, no como punto de partida.** Sirve para no repetir errores ya
identificados — principalmente los dos riesgos ALTOS de arriba.
