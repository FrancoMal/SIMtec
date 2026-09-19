# Contrato verificable de población, ventana y target

**Versión C0.1 — 19/09/2026. Estado: propuesta computada, pendiente de validación de negocio.**
Ford Innovation Challenge III, Desafío 1 — Data-Driven Repurchase based on Service Retention.

@MODE: REPO + AUDIT + DOC/técnico  
@TASK: Perfilar las fuentes originales, proponer un contrato verificable y auditar disponibilidad temporal y exposición previa.  
@TOOLS_USED: documents:documents para lectura de la ficha; Python/pandas para cálculo en memoria; consulta de páginas oficiales de Ford para intervalos de mantenimiento. source-command-sc-analyze evaluada y descartada por estar orientada a análisis de código.

**Resultado:** bajo C0.1 hay **131.051 relaciones usuario–VIN–ventana elegibles**, correspondientes a 83.391 pares usuario–VIN, 76.188 VIN y 66.690 usuarios. **91.370 ventanas tienen etiqueta utilizable; 42.733 son churn (46,77%).** Otras 30.446 carecen de madurez suficiente y 9.235 tienen resultado indeterminado. No hay un período independiente acreditable en estos extractos.

La cifra es condicional a este contrato: **la ficha no fija el ancho de ventana, la gracia posterior al vencimiento, el margen de consolidación ni el algoritmo para proyectar kilometraje**. No existe una cifra única oficial de elegibles o de churn que pueda obtenerse sin fijarlos. No se entrenó ningún modelo ni se eligieron parámetros por su poder predictivo.

## 1. Contrato corto y contraste con la ficha

Los localizadores P77, P85, etc. son los párrafos OOXML de `Dataset/Ficha_Técnica_FIC3_Data_Strategy_2026_08.docx`, parte `word/document.xml`, contados en orden incluyendo párrafos vacíos. El DOCX no tiene números de línea estables; estos localizadores se regeneran con el comando del anexo. Las citas son de la ficha, no de SPEC ni de soluciones previas.

| Regla C0.1 | Texto autoritativo y localizador | Implementación y qué es supuesto |
|---|---|---|
| Unidad | P77: «usuario–vehículo(VIN)–ventana»; vista consolidada sin perder riesgo por VIN. | Una fila por usuario observado al scoring, VIN y ancla que origina la ventana. Varias ventanas de un mismo par son observaciones dependientes; no equivalen a clientes independientes. |
| Población | P85: «usuarios con uno o más vehículos Ranger dentro de una ventana de mantenimiento en Argentina». | Ranger presente en venta o visita histórica, con ancla, regla de plan e identidad observada no ambigua. Argentina se asume por el alcance declarado del extracto: no hay columna país. No se limita a VIN vendidos en 2024–2026 si hay historia previa de mantenimiento en Agenda. |
| Plan por versión | P85: «Las reglas exactas de ventana y horizonte deberán validarse por modelo/año antes del entrenamiento final». | **S1:** 16.000 km para `RANGER (P703)` MY2024–2026; 10.000 km para `RANGER (P375)` MY2012–2023; ambos con límite de 12 meses calendario. En primera entrega, `ModelCode` 6DC/7DC/8DC y MY>=2024 se trata provisionalmente como P703. Raptor, familia/año ambiguos y otras versiones quedan fuera del universo calculable. Mapeo sujeto a Ford. |
| Ancla | P61 menciona reglas de modelo, antigüedad y kilometraje, pero no prescribe ancla ni fallback. | **S2:** cada mantenimiento numerado completado abre un ciclo nuevo; primer ciclo desde entrega, siempre que la entrega sea >=2024-01-01 y conste la venta. No se inventa un primer ciclo para un vehículo antiguo sin mantenimiento observable. |
| Vencimiento | P61/P85 no dan fórmula de proyección de uso. | **S3:** `d = min(ancla + 12 meses, ancla + ceil(K/r))`; si no hay ritmo válido, solo calendario. `r` es la mediana de hasta los tres últimos incrementos válidos de odómetro conocidos al cerrar el ancla: separación >=7 días, incremento >0 y <=500 km/día, lecturas 100–1.000.000 km. Sin lectura actual de la extracción. El vencimiento se fija en el ancla, sin revisarlo con visitas posteriores. |
| Scoring | P85: «apertura de la ventana y, opcionalmente, actualizaciones durante la ventana»; P66: predicción antes del resultado. | **S4:** apertura y scoring a las 00:00 de `t = max(disponibilidad del ancla, d − 30 días)`. Una sola predicción por ciclo. Historial estrictamente anterior a t. No scoring mensual ni revisiones intraventana en C0.1. En 565 ventanas la anticipación es menor a 30 días porque la información del ancla impide abrir antes. |
| Disponibilidad | P91: «ninguna variable posterior a la fecha de scoring podrá utilizarse como feature». | **A1/A2/A3**, detallados en §3: hechos de venta/cierre/ingreso utilizables al día siguiente de su fecha registrada, suponiendo carga oportuna y ausencia de correcciones posteriores. **Esto no puede probarse con los CSV.** |
| Elegibilidad al abrir | P77 exige vehículo en ventana; no determina preempción, órdenes abiertas ni identidad. | **S5:** si otro mantenimiento válido completó después del ancla y antes de t, esa ventana se suprime. También se suprime si hay ingreso real anterior a t sin egreso anterior a t. Se excluye identidad desconocida/ambigua al scoring. Las reservas futuras por sí solas no excluyen: falta fecha de creación. |
| Retorno objetivo | P85: «mantenimiento programado completado en la red oficial»; excluir otros eventos según reglas de negocio. | **S6:** al menos un ítem `ServiceType=Mantenimiento`, `ServiceMaintenance` entero 1–20 y `StatusARG=(60) Concluido`, con cierre fechado válido. Fecha de evento = `EffectiveCheckoutDate`, nunca reserva ni ingreso. `(90) Concluido sin OS`, garantía sin número, campañas, diagnóstico y reparación no bastan. |
| Próximo mantenimiento y consolidación | La ficha no define deduplicación, repetición de ordinal ni `ScheduleReturn`. | **S7:** ítems se colapsan por `schedule_id`; turnos del mismo VIN con igual día de cierre forman un evento. Cuenta el siguiente evento válido en la ventana, aunque repita ordinal. `ScheduleReturn=Y` no se interpreta como retrabajo sin diccionario: un ítem numerado concluido sigue contando. Ambas decisiones requieren confirmación; no afirmar que se identificó cada mantenimiento físico sin error. |
| Horizonte y etiqueta | P85: churn=1 si no se observa mantenimiento objetivo en el horizonte posterior al scoring; churn=0 si se observa. La duración no está fijada. | **S8:** observar desde t, inclusive, hasta `h=d+90 días`, inclusive al cierre del día. Son hasta 120 días desde scoring; **90 días es gracia desde vencimiento**, no desde scoring. Churn=0 si hay retorno de la misma relación antes de una ambigüedad de identidad; churn=1 si no hay retorno ni ambigüedad en un horizonte maduro. |
| Identidad | P77 define relación usuario–VIN; P102 exige IDs consistentes, pero no explica titular, reservante ni cambios de usuario. | **S9:** usuario al scoring = único ID de la última visita cerrada anterior a t, o comprador si su registro de venta es más reciente y disponible. No se afirma titularidad. Si aparece otro ID, falta ID o un cierre de mantenimiento inconsistente antes de constatar retorno, resultado indeterminado. Si retorno e identidad ambigua coinciden el mismo día, indeterminado. No se convierte el retorno de otro usuario en churn del anterior. |
| Censura y consolidación | P85: «ventanas cuyo horizonte todavía no finalizó no podrán utilizarse como churn confirmado». No fija corte ni demora de carga. | **S10:** C=25/08/2026, máximo cierre concluido observado, **proxy de cobertura, no fecha de extracción acreditada**. Etiquetar solo si h<=C−30 días (=26/07/2026). El margen de 30 días es prudencial y no prueba completitud. Excluir también positivos de ventanas no maduras para evitar una muestra con positivos tempranos y negativos incompletos. |
| Evaluación y alcance del claim | P91 exige separación temporal; P99 prioriza formulación y ausencia de leakage. | Población del scoring no se filtra por resultado. Censurados e indeterminados se mantienen contados, fuera de la tasa binaria. El target observable es **ausencia de mantenimiento en el extracto de Agenda**, no abandono definitivo ni prueba de que no hubo servicio en otro sistema. No hay campo de baja/exportación/consentimiento. |

**Apoyo externo limitado a S1:** Ford publica 16.000 km/12 meses para la [nueva Ranger 2.0L Diesel](https://www.ford.com.ar/posventa/mantenimiento-garantia/nueva-ranger/ranger-2-0-l-diesel/) y 10.000 km/12 meses para la [Ranger 2.2L Diesel a partir de 2021](https://www.ford.com.ar/posventa/mantenimiento-garantia/ranger/ranger-2-l-diesel/), consultadas el 19/09/2026. Esto respalda esos planes, **no valida automáticamente la extensión a cada TMA/año de los CSV**, ni fija la ventana del challenge. No se adopta 15.000 km de las notas anteriores.

**Alcance incompleto cuantificado:** hay 4.750 anclas sin regla de plan; no son clientes de bajo riesgo. La proyección de primer servicio es solo calendario porque no hay telemetría histórica anterior: 17.346 ventanas elegibles usan ancla de entrega. Se suprimen ciclos ya cumplidos antes de abrir, por lo que esta cohorte no representa todos los primeros servicios reales.

**Cinco confirmaciones para el mentor antes del entrenamiento final:** (1) plan por familia/año y anticipación; (2) gracia que define oportunidad perdida; (3) significado de `ServiceMaintenance`, ordinal repetido, `ScheduleReturn` y sin OS; (4) semántica de `customer_id` y cobertura de Agenda; (5) fechas de carga/cambios y fecha efectiva de cobertura del extracto. Se puede seguir perfilando; no rotular estos puntos como reglas aprobadas.

## 2. Universo y distribución temporal

Lectura completa de ambos CSV, sin muestreo y sin ejecutar pipelines anteriores. Datos base:

- Ventas: **59.384 filas, 59.384 VIN, 45.959 usuarios, 17 columnas**, sin duplicados exactos.
- Agenda: **631.623 filas, 52 columnas, 492.442 turnos, 111.752 VIN y 105.240 usuarios no nulos**; 19.554 filas exactamente duplicadas.
- Unión de ambas fuentes: **128.925 VIN y 167.880 pares usuario–VIN no nulos observados**. Estos pares no son todavía ventanas elegibles.
- Ventas fechadas 01/01/2024–24/08/2026; turnos programados 01/01/2024–17/12/2026; cierres 02/01/2024–25/08/2026.
- Hay 3.826 turnos programados después de C: 3.321 agendados, 498 cancelados y 7 en progreso. **No son resultados futuros cerrados.**
- 4 turnos tienen estados `StatusARG` incompatibles entre ítems y se ponen en cuarentena. Las claves, fechas, odómetro y familia examinados son consistentes dentro de cada turno, incluyendo nulos.
- 221.616 turnos cumplen el evento estricto, agrupados en **221.224 eventos VIN–día**; 87 turnos candidatos a mantenimiento tienen conflictos o cronología inválida y pueden volver indeterminada una etiqueta.
- Hay 4.169 turnos concluidos clasificados como Mantenimiento sin número de mantenimiento: no entran automáticamente al evento objetivo.

El flujo de exclusiones siguiente es secuencial: un ancla se cuenta en el primer motivo aplicable. **Las anclas no son VIN únicos.**

| Paso | Cantidad |
|---|---|
| Anclas candidatas (entregas + mantenimientos VIN–día) | 280.515 |
| Sin regla de plan | 4.750 |
| Apertura posterior a C | 67.405 |
| Mantenimiento completado antes de abrir: ciclo sustituido | 70.989 |
| Ingreso sin egreso anterior al scoring: ya en taller | 4.117 |
| Sin usuario único observable al scoring | 2.203 |
| Ventanas elegibles | 131.051 |

| Estado de ventana elegible | Cantidad | Uso |
|---|---|---|
| Retorno (churn=0) | 48.637 | Etiqueta utilizable |
| No retorno (churn=1) | 42.733 | Etiqueta utilizable |
| Horizonte aún abierto al corte | 24.520 | Sin etiqueta |
| Horizonte cerrado, pero sin 30 días de consolidación | 5.926 | Sin etiqueta |
| Identidad / evento indeterminado en horizonte maduro | 9.235 | Sin etiqueta binaria |

**Tasa base = 42.733 / (48.637 + 42.733) = 46,77%.** No dividir por las 131.051 ventanas: eso trataría censurados e indeterminados como retornos.

Entre las 100.605 ventanas maduras, la indeterminación afecta a 9.235 (9,18%). Si todas fueran retorno, la tasa sería 42,48%; si todas fueran churn, 51,66%. **Es un rango extremo por etiquetas faltantes, no un intervalo de confianza**, y no resuelve errores de cobertura o taxonomía.

| Ancla | Etiquetas utilizables | Churn | Tasa |
|---|---|---|---|
| Entrega | 10.711 | 6.046 | 56,45% |
| Mantenimiento previo | 80.659 | 36.687 | 45,48% |

### Distribución mensual según fecha de scoring

| Mes | Elegibles | Etiquetadas | Churn | Tasa sobre etiquetadas | Indeterminadas | Sin madurez |
|---|---|---|---|---|---|---|
| 2024-01 | 1 | 1 | 1 | 100,00% | 0 | 0 |
| 2024-02 | 64 | 60 | 16 | 26,67% | 4 | 0 |
| 2024-03 | 219 | 204 | 57 | 27,94% | 15 | 0 |
| 2024-04 | 433 | 398 | 118 | 29,65% | 35 | 0 |
| 2024-05 | 733 | 668 | 182 | 27,25% | 65 | 0 |
| 2024-06 | 1.080 | 981 | 256 | 26,10% | 99 | 0 |
| 2024-07 | 1.321 | 1.221 | 336 | 27,52% | 100 | 0 |
| 2024-08 | 1.567 | 1.426 | 409 | 28,68% | 141 | 0 |
| 2024-09 | 1.865 | 1.717 | 512 | 29,82% | 148 | 0 |
| 2024-10 | 2.142 | 1.970 | 629 | 31,93% | 172 | 0 |
| 2024-11 | 2.401 | 2.191 | 702 | 32,04% | 210 | 0 |
| 2024-12 | 4.593 | 4.262 | 2.176 | 51,06% | 331 | 0 |
| 2025-01 | 5.244 | 4.793 | 2.463 | 51,39% | 451 | 0 |
| 2025-02 | 4.649 | 4.237 | 2.185 | 51,57% | 412 | 0 |
| 2025-03 | 5.278 | 4.727 | 2.401 | 50,79% | 551 | 0 |
| 2025-04 | 4.982 | 4.511 | 2.212 | 49,04% | 471 | 0 |
| 2025-05 | 5.426 | 4.910 | 2.393 | 48,74% | 516 | 0 |
| 2025-06 | 5.641 | 5.152 | 2.495 | 48,43% | 489 | 0 |
| 2025-07 | 6.295 | 5.666 | 2.780 | 49,06% | 629 | 0 |
| 2025-08 | 5.998 | 5.454 | 2.599 | 47,65% | 544 | 0 |
| 2025-09 | 5.738 | 5.188 | 2.635 | 50,79% | 550 | 0 |
| 2025-10 | 5.963 | 5.361 | 2.593 | 48,37% | 602 | 0 |
| 2025-11 | 5.775 | 5.264 | 2.551 | 48,46% | 511 | 0 |
| 2025-12 | 6.300 | 5.694 | 2.700 | 47,42% | 606 | 0 |
| 2026-01 | 6.157 | 5.600 | 2.763 | 49,34% | 557 | 0 |
| 2026-02 | 5.366 | 4.868 | 2.305 | 47,35% | 498 | 0 |
| 2026-03 | 6.083 | 4.845 | 2.263 | 46,71% | 528 | 710 |
| 2026-04 | 5.994 | 1 | 1 | 100,00% | 0 | 5.993 |
| 2026-05 | 5.872 | 0 | 0 | — | 0 | 5.872 |
| 2026-06 | 6.109 | 0 | 0 | — | 0 | 6.109 |
| 2026-07 | 6.588 | 0 | 0 | — | 0 | 6.588 |
| 2026-08 | 5.174 | 0 | 0 | — | 0 | 5.174 |

La única etiqueta utilizable de abril de 2026 tiene anticipación inferior a 30 días y horizonte ya maduro; **1/1 no estima una tasa mensual**. A partir de mayo no hay denominador etiquetado, no una tasa de churn de 0%.

**Arranque de historia:** 2024 aporta 16.419 ventanas elegibles y 15.099 etiquetas (35,72% churn), dominadas inicialmente por vehículos con suficiente actividad para estimar ritmo rápido. Desde 2025 hay **114.632 ventanas, 76.271 etiquetas y 48,96% churn**. Recomiendo 2024 como historia de arranque y reportar modelado desde 2025 separado; esto es una propuesta metodológica, no un nuevo test independiente. La tasa global no es estacionaria ni debe extrapolarse a cualquier mes.

### Sensibilidad del horizonte sin cambiar de población

Se toman las **85.355 ventanas maduras a +120 días**, con resultado determinable en los cuatro escenarios. Misma ventana y mismo usuario: cambia solo la gracia después del vencimiento.

| Gracia desde vencimiento | Ventanas comunes | Churn | Tasa |
|---|---|---|---|
| 30 días | 85.355 | 53.694 | 62,91% |
| 60 días | 85.355 | 44.828 | 52,52% |
| 90 días | 85.355 | 39.454 | 46,22% |
| 120 días | 85.355 | 36.007 | 42,18% |

El 46,22% de +90 en esta cohorte común difiere del 46,77% general por el denominador. Esta sensibilidad **no elige el horizonte que favorece al modelo**: muestra por qué negocio debe fijarlo.

| Otra sensibilidad | Elegibles | Etiquetadas | Churn | Tasa | Advertencia |
|---|---|---|---|---|---|
| Gracia +90, sin margen de 30 días | 131.051 | 96.728 | 45.328 | 46,86% | Agrega cohortes; no demuestra que los cierres estén completos. |
| Solo calendario, sin proyección por km | 58.945 | 38.287 | 26.173 | 68,36% | Cambia quién llega a la apertura sin haber retornado; no es una comparación sobre la misma población. |

Como referencia, un ranking aleatorio tiene lift esperado cercano a 1 y precisión cercana a la prevalencia; en una cohorte por ventanas, su recall al 10% de capacidad ronda el 10%. La operación pedida usa usuarios: antes de medir recall operativo hay que consolidar VIN y fijar cupos por usuario/dealer. No trasladar automáticamente el top-10% de ventanas al top-10% de contactos.

## 3. Inventario completo de disponibilidad histórica

**Ninguna columna del extracto prueba por sí sola su disponibilidad en el sistema en una fecha pasada.** No hay `created_at`, `updated_at`, fecha de ingesta, historia de estados ni versiones de catálogo. Separar tres relojes: fecha del hecho, fecha en que se conoció y fecha en que se extrajo. Los CSV permiten aproximar el primero, no verificar los otros dos.

Supuestos habilitantes, pendientes de confirmar:

- **A1 — venta:** usar datos de venta desde las 00:00 del día siguiente a `max(SalesDate, DeliveryDate)`, con entrega válida. Suponer que el registro y sus atributos estaban cargados entonces y no fueron sustituidos por una foto del propietario actual. No usar `Status` actual para filtrar retrospectivamente.
- **A2 — visita cerrada:** usar atributos de un turno `(60)` o `(90)` desde el día siguiente a `EffectiveCheckoutDate`, siempre que no haya conflicto de estado, tenga VIN, cierre >= ingreso real o fecha programada de respaldo, y fechas desde 01/01/2024 hasta C. `(90)` informa historia/identidad, **no retorno objetivo**. Esto supone que cierre, ítems y atributos eran conocidos y no fueron corregidos después.
- **A3 — ingreso:** `EffectiveCheckinDate < t` permite inferir que el vehículo ya había ingresado. Si no hay egreso anterior a t, no se lo incluye en contacto preventivo. Se usa la fecha del hecho, sin mirar el estado final para decidir si ocurrió el ingreso. Una orden antigua sin cierre puede excluir indefinidamente: es una limitación conservadora.
- **Convención de precisión:** se conservan los días impresos en las fuentes; las fechas `00:00+00:00` se tratan como fechas de negocio, sin restar tres horas. Scoring a las 00:00 de Argentina; cierre dentro del mismo día se considera resultado posterior al scoring. Confirmar semántica de zona horaria con Ford.

**Leyenda:** `H?` = hecho histórico utilizable solo bajo A1/A2/A3; `V?` = atributo aparentemente estable, con disponibilidad condicionada al registro de origen; `S?` = probable foto a extracción; `X` = disponibilidad o semántica desconocida, excluido; `I` = identificador para cruces, no predictor crudo; `N` = no se usa por nulidad, constancia o redundancia. El signo `?` es deliberado: no significa “sin leakage demostrado”.

El conjunto inicial de features propuesto queda acotado a edad desde entrega conocida, año/familia del vehículo, recencia/frecuencia de mantenimientos cerrados, historial observable, odómetro e intensidad anteriores, y eventualmente canal/dealer históricos. Cada agregado se recalcula con registros disponibles antes de t, también la cantidad de VIN de un usuario. **No se construyó ni entrenó todavía esa matriz de features.**

### Comprobaciones nuevas sobre los extractos

- **KM:** 103.210 VIN con valor, solo 7 con más de un valor. Entre VIN con al menos dos fechas de cierre, coincide con `VehicleCurrentKM` de la primera visita en **1.934/71.653 (2,70%)** y de la última en **68.903/71.681 (96,12%)**. Los denominadores difieren por nulos. Es evidencia fuerte de foto final; no una prueba de cómo está escrita la consulta fuente. Se excluye.
- **ConnectedStatusARG:** 111.678 de 111.752 VIN mantienen un único valor; 74 cambian. No hay fecha de activación/desactivación. La constancia sola no demuestra foto, pero no permite reconstruir conectividad pasada. Se excluye.
- **VehicleCurrentKM:** 73.813 VIN tienen varias lecturas, frente a solo 7 en KM. Es consistente con lectura por turno; falta confirmar que no sea corregida retroactivamente.
- **Encuestas:** 36.917 turnos con respuesta; 36.914 anteriores al turno, 3 del mismo día y ninguno posterior; mediana 8 días antes. La ficha no define qué mide la encuesta. No se usa como satisfacción con el mantenimiento ni se da por probado que mida la reserva.
- **Estados/cancelaciones:** falta fecha de creación del turno y de cada transición. No es válido conocer un no-show, cancelación o reprogramación simplemente porque la fecha programada sea anterior a t. Esas features quedan excluidas.
- **ServiceMonth:** todas las filas con valor cumplen `ServiceMonth = 12 × ServiceMaintenance`. No es el mes en que ocurrió un servicio.
- **Duración:** `DaysInDealer` coincide con cierre menos ingreso en 309.563/309.629 turnos comparables; `EffectiveTerm`, solo en 300.216/309.500. Se prefiere derivar duración de fechas válidas; no equiparar campos por el nombre.
- **Historia truncada:** 66.795 VIN de Agenda tienen inicio de garantía anterior a 2024. “No se observó mantenimiento anterior” no equivale a “nunca hizo mantenimiento”.
- **Identidad:** 23.245 VIN tienen más de un `customer_id` no nulo en Agenda. Puede ser cambio de reservante, usuario o dueño; el extracto no distingue esos mecanismos.

Las tablas siguientes cubren **las 69 columnas de origen**, sin omitir las descartadas. Nulos y cardinalidad corresponden a filas originales; los controles a nivel turno/VIN se indican por separado. Para cada candidata se explicita el instante habilitante y la incertidumbre.

### Ventas — 17 columnas

| Columna | Nulos / únicos no nulos | Clase | Uso propuesto | Disponibilidad y evidencia |
|---|---|---|---|---|
| `vehicle_id` | 0 / 59.384 | I | Clave de cruce; nunca predictor crudo | Registro de venta disponible según A1; no revela titularidad. |
| `customer_id` | 0 / 45.959 | I | Relación observada y consolidación, no predictor crudo | A1; se reemplaza por la última relación histórica observada, sin usar el último usuario del extracto. |
| `dealer_id` | 139 / 107 | H? | Candidato: dealer de venta; fuera del núcleo inicial | A1 y solo para la relación compradora; no confundir con dealer de servicio. |
| `PersonType` | 35 / 5 | X | Excluir del núcleo | Una fila por VIN; no hay vigencia del atributo ni historia de titularidad. |
| `Status` | 0 / 4 | X | Excluir | Estado final de venta sin fecha de transición; no filtrar ventas históricas por ACCEPTED actual. |
| `SalesType` | 59.384 / 0 | N | Excluir | 100% nulo. |
| `SalesChannel` | 0 / 5 | H? | Candidato diferido | A1 y misma relación compradora; sin evidencia de carga ni cambios posteriores. |
| `BusinessUnit` | 0 / 3 | X | Excluir del núcleo | Clasificación organizativa sin fecha de vigencia; no prueba uso histórico. |
| `SalesDate` | 0 / 933 | H? | Disponibilidad de venta y antigüedad observada | A1 usa el máximo de venta y entrega; no adelantar la aparición del registro. |
| `DeliveryDate` | 90 / 1.211 | H? | Ancla de primer ciclo y edad desde entrega | A1; requiere fecha >=2024-01-01; sin entrega no se inventa primer ciclo. |
| `RegistrationDate` | 68 / 678 | X | Excluir | No es fecha de carga; registra un hecho distinto, sin trazabilidad de actualizaciones. |
| `WarrantyStartDate` | 180 / 909 | V? | Candidato: edad desde garantía; no duración restante de garantía | Solo desde la venta A1; pendiente validar semántica. No usar retrospectivamente el dato de una visita futura. |
| `ModelYear` | 0 / 9 | V? | Año modelo y regla de familia | Solo desde A1; atributo presumiblemente estable, sin prueba de versión histórica. |
| `ModelCode` | 1 / 12 | V? | Regla provisional de primer ciclo | Solo desde A1; mapeo 6DC/7DC/8DC y año >=2024 es supuesto de identificación de P703. |
| `ModelShortName` | 0 / 2 | V? | Control de alcance Ranger | Solo desde A1; no hace falta como predictor por su baja variación. |
| `ModelName` | 0 / 39 | V? | Control de versión; excluir texto del modelo inicial | Solo desde A1; etiqueta comercial puede normalizarse al extraer. |
| `State` | 0 / 24 | X | Excluir del núcleo | Ubicación sin fecha de vigencia ni definición inequívoca: no asumir domicilio histórico. |

### Agenda — 52 columnas

| Columna | Nulos / únicos no nulos | Clase | Uso propuesto | Disponibilidad y evidencia |
|---|---|---|---|---|
| `vehicle_id` | 3.215 / 111.752 | I | Clave de VIN, no predictor crudo | A2 para relaciones históricas; permite cruzar sin revelar VIN real. |
| `customer_id` | 11.888 / 105.240 | I | Usuario observado al scoring y verificación de etiqueta | A2; no usar último ID del extracto ni interpretar cambios automáticamente como transferencias. |
| `dealer_id` | 0 / 95 | H? | Candidato: último dealer, número de dealers previos | A2; solo turnos cerrados anteriores, agregados sin resultados futuros. |
| `schedule_id` | 0 / 492.442 | I | Deduplicación de turnos, no predictor | No contiene una fecha acreditada de creación. |
| `Region` | 0 / 4 | X | Excluir del núcleo | Código categórico sin diccionario definitivo ni versión histórica; no atribuir región geográfica por intuición. |
| `DealerStateOrZone` | 104 / 5 | X | Excluir del núcleo | Código 1–5, no nombre de provincia; mapeo y vigencia no documentados. |
| `ScheduleDate` | 0 / 878 | H? | Fecha programada de turnos históricos y control | A2; NO es fecha de creación. Turnos futuros no se usan como feature. |
| `ScheduleYear` | 0 / 3 | N | Excluir por redundancia | Derivable de ScheduleDate; mismo límite temporal. |
| `ScheduleTime` | 0 / 80 | N | Excluir del núcleo | Hora prevista, no instante de alta ni evidencia de disponibilidad. |
| `ScheduleDateTime` | 0 / 39.547 | H? | Control de fecha/hora programada | A2; no habilita conocer reservas futuras al scoring. |
| `ScheduleStatus` | 77.013 / 6 | X | Excluir como feature directa | Foto de estado sin timestamp de transición; conflictos en 3 turnos. |
| `Status` | 113.437 / 5 | X | Excluir como feature directa | Estado sin timestamp de transición; no cubre cancelaciones. |
| `StatusARG` | 0 / 6 | H?/X | Taxonomía de cierre y target; conteos de completados bajo A2 | 60/90 solo con cierre fechado. Cancelación/no-show excluidos de features: no tienen fecha de transición. |
| `ScheduleSource` | 0 / 5 | H? | Candidato: canal del último turno cerrado y mezcla histórica | A2; no asignar el canal de una reserva futura. |
| `ScheduleTypeCode` | 113.437 / 1 | N | Excluir | Solo R entre no nulos; ausencia alineada con cancelaciones, sin fecha de actualización. |
| `ScheduleModalityCode` | 631.623 / 0 | N | Excluir | 100% nulo. |
| `IsReschedule` | 446.056 / 2 | X | Excluir | Sin fecha de reprogramación; conflicto dentro de un turno; mirar la fila final puede revelar una decisión posterior. |
| `ScheduleReturn` | 127.842 / 2 | X | Excluir como predictor; no altera la taxonomía primaria | Sin fecha ni definición confirmada de retorno/retrabajo. Un ítem numerado concluido cuenta por hipótesis; requiere validación. |
| `VehicleModelGroup` | 91 / 9 | V? | Control de alcance, no familia principal | Solo desde A2; normalización/fuente de versión desconocida. |
| `ShortVehicleModelGroupTreated` | 0 / 5 | V? | Familia y regla de intervalo en ancla de mantenimiento | Solo desde A2; atributo tratado, 90 VIN con más de un valor en el extracto. |
| `ModelYear` | 4.957 / 23 | V? | Año modelo y regla de intervalo | Solo desde A2; 0 VIN con múltiples valores no nulos, pero estabilidad observada no prueba disponibilidad. |
| `TMA` | 4.455 / 23 | V? | Candidato diferido de versión | Solo desde A2; 0 VIN con múltiples valores no nulos; no entrenar con códigos sin diccionario. |
| `KM` | 19.812 / 68.653 | S? | Excluir de todo backtest y del cálculo histórico de ventana | Probable foto a extracción; 7 VIN con más de un valor. Coincidencia con última lectura, no primera, en VIN multivisita. |
| `VehicleCurrentKM` | 142.868 / 134.377 | H? | Kilometraje histórico e intensidad de uso | A2; lectura entre 100 y 1.000.000; ninguna lectura del mantenimiento a predecir. Semántica de lectura del turno pendiente de confirmación. |
| `EffectiveCheckinDate` | 211.061 / 841 | H? | Identificar ingreso ya ocurrido y control cronológico | A3; fecha de hecho, no de registro. No sustituye finalización para el target. |
| `EffectiveCheckoutDate` | 154.984 / 863 | H? | Fecha de retorno, ancla y disponibilidad de hechos cerrados | A2; no usar el cierre futuro en features. Debe ser >= ingreso o fecha programada de respaldo. |
| `DaysInDealer` | 152.634 / 406 | H? | Candidato diferido de duración histórica | A2; preferir recalcular cierre menos ingreso. Coincide en 309.563/309.629 turnos comparables. |
| `WorkDaysInDealer` | 152.667 / 314 | H? | Excluir del núcleo | A2 sería necesario; calendario laboral no definido, no asumir equivalencia con días corridos. |
| `EffectiveTerm` | 215.755 / 299 | H? | Excluir del núcleo | A2 sería necesario; no equivale siempre a cierre menos ingreso (300.216/309.500). |
| `ServiceName` | 58.284 / 67 | X | Solo auditoría taxonómica; no feature de texto | Etiqueta de catálogo posiblemente normalizada a extracción; número de mantenimiento tiene prioridad. |
| `ServiceDescription` | 395.261 / 12 | X | Excluir | Texto de catálogo, no historial del cliente; no hay versión del catálogo. |
| `ServiceType` | 58.284 / 13 | H?/X | Taxonomía histórica y target bajo A2 | Mantenimiento por sí solo es insuficiente; exigir ServiceMaintenance numerado. Catálogo sin historial de cambios. |
| `ServiceMaintenance` | 353.162 / 20 | H? | Taxonomía y conteos de mantenimiento histórico | A2; enteros 1–20. No asumir que ordinal repetido es siempre nuevo servicio ni que 20 significa exactamente vigésimo. |
| `ServiceMonth` | 353.162 / 20 | N | Excluir por redundancia | Equivale a 12 × ServiceMaintenance en todos los registros con valor; no es mes calendario del evento. |
| `ServiceDuration` | 58.284 / 7 | X | Excluir | Solo 7 valores; puede ser duración normativa de catálogo, no duración realizada. |
| `ServiceIsMobile` | 561.866 / 2 | H?/X | Candidato diferido, fuera del núcleo | A2 sería necesario; atributo de ítem, no siempre único dentro del turno. |
| `ServiceFordFixedPriceFlag` | 58.284 / 2 | X | Excluir | Catálogo/precio sin fecha de vigencia; no consta valor vigente al scoring. |
| `ServiceLaborCost` | 626.920 / 128 | X | Excluir | No hay vigencia ni garantía de costo efectivamente pagado; alta ausencia. |
| `ServiceFordFixedPrice` | 522.256 / 3 | X | Excluir | Solo 3 valores no nulos; sin vigencia histórica ni unidad confirmada. |
| `ServicePriceDiscount` | 411.505 / 2.469 | X | Excluir | Nombre/unidad no bastan para interpretarlo como descuento; sin vigencia ni historial de actualización. |
| `CancellationReason` | 631.623 / 0 | N | Excluir | 100% nulo. |
| `NeededTowing` | 265.407 / 2 | H? | Candidato diferido | Solo A2; sin hora de solicitud ni garantía de que el flag estuviera antes del servicio. |
| `TowingType` | 628.969 / 2 | H? | Candidato diferido | Solo A2; códigos sin diccionario definitivo. |
| `CustomerWaiting` | 113.437 / 2 | H? | Candidato diferido | Solo A2; no usar decisión de espera de un turno futuro. |
| `LoanerVehicle` | 240.110 / 1 | N | Excluir | Solo N entre no nulos; no hay evidencia positiva de préstamo. |
| `Quicklane` | 631.623 / 0 | N | Excluir | 100% nulo. |
| `PickupDeliveryService` | 0 / 2 | H?/X | Candidato diferido | A2 y agregación any por turno: varía entre ítems de 16.691 turnos. |
| `MobileService` | 0 / 2 | H?/X | Candidato diferido | A2 y agregación any por turno: varía entre ítems de 6.320 turnos. |
| `SurveyStarRating` | 579.676 / 5 | X | Excluir del núcleo | 36.914/36.917 respuestas son anteriores al turno: no llamar satisfacción posservicio a este dato. |
| `SurveyResponseDate` | 579.676 / 993 | H? | Control de disponibilidad de encuesta, no feature inicial | Si se habilitara: respuesta < t y turno ya cerrado según A2; fecha no prueba carga ni semántica. |
| `WarrantyStartDate` | 6.317 / 5.250 | V? | Candidato: edad desde garantía conocida en un evento pasado | Solo desde A2; 1 VIN con múltiples valores no nulos. Nunca tomar la garantía de una fila futura. |
| `ConnectedStatusARG` | 0 / 4 | S? | Excluir de todo backtest | Probable foto de conectividad: 111.678/111.752 VIN constantes; sin fecha de activación/desactivación. |

## 4. Períodos observados y ausencia de test independiente

Los SHA-256 actuales coinciden exactamente con los tres del manifiesto previo de astra: `G:\SIMtec-astra\desafio-1-repurchase-propensity\reports\integridad_crudos_inicio.json:5,10,15`. Esto acredita que no estamos ante una entrega nueva de datos.

| Período de scoring / datos | Exposición documentada en la vuelta anterior | Estado actual |
|---|---|---|
| Enero–junio 2024 | EDA del extracto completo y entrenamiento de fable en la comparación mensual desde enero 2024. | Observado; no reservarlo retroactivamente como test virgen. |
| Julio 2024–agosto 2025 | Train de astra; también exploración y entrenamiento de fable. | Desarrollo. |
| Septiembre–diciembre 2025 | Train/validación de fable; selección de astra en octubre–noviembre; septiembre y diciembre figuraban como embargo pero sus cohortes/prevalencias fueron reportadas. | Un embargo temporal no equivale a datos nunca observados. |
| Enero–marzo 2026 | Test de fable, calibración de astra en enero–febrero y marzo como embargo observado. | Evaluación/calibración ya consultadas. |
| Abril–julio 2026 | Test de astra y comparación cruzada con reentrenamientos de fable. | Test observado por ambos desarrollos. |
| Agosto 2026 hasta el corte | EDA de fable sobre todo el extracto; cohorte y demo de astra el 01/08. | Observado; además no madura para el horizonte C0.1. |
| Reservas posteriores al 25/08, hasta diciembre 2026 | Ya incluidas en la exploración; el propio CSV contiene agendados, cancelados y en progreso, sin cierres posteriores. | No constituyen un holdout de resultados. |
| Eventos posteriores efectivamente completados | No entregados en estos archivos. | Única posibilidad de evaluación prospectiva nueva, todavía no disponible. |

Evidencia específica:

- `G:\SIMtec-fable\desafio-1-repurchase-propensity\reports\modelo\resumen.md:3,5`: corte 25/08/2026; train hasta 30/09/2025, validación hasta 31/12/2025, test 01/01–28/03/2026.
- `G:\SIMtec-astra\desafio-1-repurchase-propensity\reports\seleccion_congelada.json`, objeto `particiones`: train 01/07/2024–01/08/2025; validación 01/10–01/11/2025; calibración 01/01–01/02/2026; test 01/04–01/07/2026; demo 01/08/2026. Sus objetos de embargo también contienen prevalencias.
- `G:\SIMtec-fable\desafio-1-repurchase-propensity\reports\revision_cruzada\verif_artefacto_y_comparacion.md:18,23,38`: entrenamiento desde enero 2024; comparación sobre abril–julio 2026 y tres reentrenamientos.
- `G:\SIMtec-astra\desafio-1-repurchase-propensity\reports\VALIDACION.md:36`: primera corrida de test observada antes de corregir ventanas, odómetro e identidad.
- `G:\SIMtec-fable\desafio-1-repurchase-propensity\docs\04_revision_cruzada.md:229`: cambios de definición mirando métricas de test.
- `G:\SIMtec-fable\desafio-1-repurchase-propensity\reports\eda\05_calidad_cobertura_leakage.md:4,15,16`: exploración global 2024–25/08/2026 y reservas futuras.

**Conclusión sin ambigüedad: no queda ningún bloque temporal observado, con resultados maduros y no expuesto que pueda acreditarse como independiente en estos CSV.** No se afirma que cada fila haya sido inspeccionada manualmente; se afirma que no hay un período protegido documentado y que los bloques propuestos como test ya participaron del desarrollo.

Texto propuesto para el jurado:

> La evaluación que presentamos es un backtest temporal retrospectivo sobre extractos ya explorados durante el desarrollo. Respeta el orden temporal de los hechos bajo supuestos explícitos de disponibilidad, pero no constituye una prueba final independiente. Congelaremos población, ventana, features, modelo y calibración antes de recibir nuevos resultados; la generalización se confirmará con ventanas posteriores completamente observadas.

Cambiar de algoritmo, autor o etiqueta no vuelve virgen el mismo período. Un intervalo de confianza no corrige el sesgo por selección adaptativa. La evaluación nueva debe esperar que transcurran **el horizonte y el margen de consolidación**: no es defendible prometerla antes del PDF del 25/09 ni del Trials Day del 02/10.

Para backtesting futuro, exigir `h + 30 días < fecha de ajuste` en cada fold; dividir solo por fecha de scoring no basta. Separar desarrollo, selección y calibración cronológicamente, y declarar exposición previa. Para incertidumbre, agrupar por usuario/VIN, no tratar las ventanas repetidas como independientes.

## 5. Integridad y reproducción

Se ejecutaron lecturas completas y cálculos nuevos en memoria. No se importó código de las soluciones anteriores ni se ejecutó ninguna operación de Git. Única escritura de esta entrega: este documento. No se guardaron CSV derivados, modelos, scripts ni cachés de bytecode.

Entorno observado: Python 3.14.6, pandas 3.0.2 y NumPy 2.4.3. El programa incluido abajo abre las fuentes en lectura, imprime conteos agregados y verifica invariantes. No modifica el repositorio. Los resultados pueden demorar unos minutos.

Validaciones realizadas: unicidad de episodios, ancla anterior al scoring, madurez de todas las etiquetas, reconciliación completa de exclusiones, sensibilidad monotónica en la misma cohorte y correspondencia de las 69 columnas con el inventario. La comprobación adicional de la clave efectiva usuario–VIN–scoring–vencimiento–fin encontró 0 duplicados; también hubo 0 coincidencias de ancla por VIN entre entrega y mantenimiento.

@VALIDATION: El comando de reproducción de este documento terminó con `ASSERTIONS PASS` y `SOURCE_INTEGRITY PASS`; las tres huellas coinciden al inicio y al cierre. Último scoring con etiqueta madura: 02/04/2026 (único caso de abril); último scoring elegible: 25/08/2026. Los días del ritmo se calculan entre fechas de cierre; usar fecha de ingreso para representar la lectura física es una alternativa todavía no adoptada. Los umbrales de odómetro, separación y velocidad de S3 son heurísticas explícitas, no parámetros escritos por Ford.

@RISKS: ALTO — contrato y disponibilidad histórica sujetos a validación de negocio; no usar las cifras como tasa oficial de abandono de toda la red. ALTO — no hay holdout independiente. MEDIO — identidad indeterminada y cohortes recientes alteran los denominadores; reportarlos siempre.  
@NEXT: Validar con el mentor las cinco definiciones de §1 antes de cerrar el contrato para entrenamiento.  
@STATUS: Completado el perfilado y la propuesta verificable; contrato de negocio pendiente de confirmación.

### Huellas de fuentes al inicio y al cierre

| Archivo | SHA-256 |
|---|---|
| `Ficha_Técnica_FIC3_Data_Strategy_2026_08.docx` | `a99886bfb8899c206dbe8dd9ac9fa316fce73a83483e298dc010eb50e24a4cf6` |
| `ranger_sales_arg_2024_2026.csv` | `bc01f5a54a5eb10c0b72d65df39bd02f5b7da4132001a8a47c8bdd2b8b1c653e` |
| `ranger_service_agenda_arg_2024_2026 1.csv` | `0fe8bd6500864c097dfb544b9983a3bccfbfe83b65418b2c151aaa38fdb6671d` |

Las tres coinciden con la lectura inicial de esta sesión y con el manifiesto anterior. Los originales no se modificaron.

### Reproducir los conteos sin crear scripts

Desde PowerShell en `G:\SIMtec`, el comando lee el bloque Python de este mismo documento y lo ejecuta en memoria:

```powershell
python -X utf8 -B -c "from pathlib import Path; text=Path('CONTRATO_POBLACION_VENTANA_TARGET_v0.1.md').read_text(encoding='utf-8'); code=text.split(chr(10)+'# REPRODUCER_START'+chr(10),1)[1].split(chr(10)+'# REPRODUCER_END',1)[0]; exec(compile(code,'<contrato>','exec'))"
```

El cuerpo completo está en el bloque desplegable siguiente para mantener legible el contrato. Incluye los parámetros, el algoritmo, el conteo mensual y los controles ejecutados.

<details>
<summary>Programa completo de reproducción</summary>

```python
# REPRODUCER_START

import pandas as pd, numpy as np, hashlib, json, bisect, math
from pathlib import Path
from collections import Counter, defaultdict
ROOT=Path(r"G:\SIMtec")
FILES=[ROOT/"Dataset/ranger_sales_arg_2024_2026.csv",ROOT/"Dataset/ranger_service_agenda_arg_2024_2026 1.csv",next((ROOT/"Dataset").glob("*.docx"))]
HASHES={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in FILES}
s=pd.read_csv(FILES[0],dtype=pd.StringDtype(storage="python"))
a=pd.read_csv(FILES[1],dtype=pd.StringDtype(storage="python"))
def dates(x):
    return pd.to_datetime(x,format="mixed",errors="coerce",utc=True).dt.tz_localize(None).dt.normalize()
def clean(x):
    return None if pd.isna(x) else str(x)
for c in ["SalesDate","DeliveryDate","WarrantyStartDate"]:
    s[c]=dates(s[c])
for c in ["ScheduleDate","EffectiveCheckinDate","EffectiveCheckoutDate"]:
    a[c]=dates(a[c])
number=pd.to_numeric(a.ServiceMaintenance,errors="coerce")
a["_maint"]=number.between(1,20)&a.ServiceType.eq("Mantenimiento")
status_conflict=a.groupby("schedule_id").StatusARG.nunique().gt(1)
bad_ids=set(status_conflict[status_conflict].index)
q=a.drop_duplicates("schedule_id").copy()
q["_maint"]=q.schedule_id.map(a.groupby("schedule_id")._maint.any())
q["_km"]=pd.to_numeric(q.VehicleCurrentKM,errors="coerce")
q["_km"]=q["_km"].where(q["_km"].between(100,1000000))
q["_begin"]=q.EffectiveCheckinDate.fillna(q.ScheduleDate)
q["_conflict"]=q.schedule_id.isin(bad_ids)
C=q.loc[q.StatusARG.eq("(60) Concluido"),"EffectiveCheckoutDate"].max()
START=pd.Timestamp("2024-01-01")
q["_closed"]=q.StatusARG.isin(["(60) Concluido","(90) Concluido sin OS"]) & ~q._conflict & q.vehicle_id.notna() & q.EffectiveCheckoutDate.between(START,C)&q._begin.ge(START)&q.EffectiveCheckoutDate.ge(q._begin)
q["_return"]=q._closed&q._maint&q.StatusARG.eq("(60) Concluido")
valid=q.loc[q._closed].sort_values(["vehicle_id","EffectiveCheckoutDate","schedule_id"])
# Collapse simultaneous appointments; never pick one user arbitrarily.
grouped={}
cols=["vehicle_id","EffectiveCheckoutDate","customer_id","ShortVehicleModelGroupTreated","ModelYear","_km","_return","ScheduleReturn","_begin"]
for vin,d,user,family,year,km,is_return,flag,begin in valid[cols].itertuples(index=False,name=None):
    key=(vin,d)
    if key not in grouped:
        grouped[key]={"vin":vin,"date":d,"users":set(),"null_user":False,"families":set(),"years":set(),
        "kms":set(),"return":False,"return_users":set(),"return_null":False,"return_flag_y":False,"begin":begin}
    e=grouped[key]
    if pd.notna(user): e["users"].add(user)
    else: e["null_user"]=True
    if pd.notna(family): e["families"].add(family)
    if pd.notna(year): e["years"].add(float(year))
    if pd.notna(km): e["kms"].add(float(km))
    e["begin"]=min(e["begin"],begin)
    if is_return:
        e["return"]=True
        if pd.notna(user): e["return_users"].add(user)
        else: e["return_null"]=True
        if pd.notna(flag) and flag=="Y": e["return_flag_y"]=True
day=list(grouped.values())
for e in day:
    e["family"]=next(iter(e["families"])) if len(e["families"])==1 else None
    e["year"]=next(iter(e["years"])) if len(e["years"])==1 else None
    e["km"]=next(iter(e["kms"])) if len(e["kms"])==1 else None
days=defaultdict(list)
for r in day: days[r["vin"]].append(r)
uncertain=defaultdict(list)
bad=q.loc[q._maint & (q.StatusARG.eq("(60) Concluido")|q._conflict) & ~q._return & q.vehicle_id.notna()]
for r in bad.itertuples():
    d=r.EffectiveCheckoutDate if pd.notna(r.EffectiveCheckoutDate) else r.ScheduleDate
    uncertain[r.vehicle_id].append(d)
admissions=defaultdict(list)
for vin,begin,end in q.loc[q.vehicle_id.notna()&q.EffectiveCheckinDate.between(START,C),["vehicle_id","EffectiveCheckinDate","EffectiveCheckoutDate"]].itertuples(index=False,name=None):
    if pd.isna(end) or end>=begin: admissions[vin].append((begin,end))
sales={}
for r in s.itertuples():
    if pd.notna(r.DeliveryDate) and r.DeliveryDate>=START:
        family="P703" if clean(r.ModelCode) in ["6DC","7DC","8DC"] and int(r.ModelYear)>=2024 else None
        sales[r.vehicle_id]={"date":r.DeliveryDate,"available":max(r.SalesDate,r.DeliveryDate)+pd.Timedelta(days=1),
             "user":r.customer_id,"family":family}
def interval(family,year):
    if family=="RANGER (P703)" and year is not None and 2024<=year<=2026: return 16000
    if family=="RANGER (P375)" and year is not None and 2012<=year<=2023: return 10000
    return None
anchors=[]; population_counts=Counter()
for vin in sorted(set(days)|set(sales)):
    events=days.get(vin,[])
    sale=sales.get(vin)
    if sale:
        anchors.append({"vin":vin,"anchor":sale["date"],"available":sale["available"],"kind":"delivery",
                        "k":16000 if sale["family"]=="P703" else None,"rate":None})
    readings=[]; rates=[]
    for e in events:
        if e["km"] is not None:
            if readings:
                dd=(e["date"]-readings[-1][0]).days
                delta=e["km"]-readings[-1][1]
                if dd>=7 and delta>0 and delta/dd<=500: rates.append(delta/dd)
            readings.append((e["date"],e["km"]))
        if e["return"]:
            anchors.append({"vin":vin,"anchor":e["date"],"available":e["date"]+pd.Timedelta(days=1),"kind":"maintenance",
                            "k":interval(e["family"],e["year"]),"rate":float(np.median(rates[-3:])) if rates else None})
def build(horizon=90,margin=30,calendar_only=False):
    rows=[]; flow=Counter()
    for an in anchors:
        flow["anchors"]+=1
        if an["k"] is None: flow["unknown_plan"]+=1; continue
        vin=an["vin"]; anchor=an["anchor"]; events=days.get(vin,[]); sale=sales.get(vin)
        due=anchor+pd.DateOffset(years=1)
        mode="calendar"
        if not calendar_only and an["rate"] is not None:
            days_km=math.ceil(an["k"]/an["rate"])
            if days_km<(due-anchor).days:
                due=anchor+pd.Timedelta(days=days_km); mode="km"
        t=max(an["available"],due-pd.Timedelta(days=30))
        end=due+pd.Timedelta(days=horizon)
        if t>C: flow["not_open"]+=1; continue
        if t<START: flow["before_start"]+=1; continue
        # All completed maintenance after anchor and strictly before scoring cancels this candidate.
        if any(e["return"] and anchor<e["date"]<t for e in events):
            flow["superseded"]+=1; continue
        # A vehicle demonstrably already in the workshop before t is not a preventive contact.
        if any(begin<t and (pd.isna(end_date) or t<=end_date) for begin,end_date in admissions.get(vin,[])):
            flow["already_in_workshop"]+=1; continue
        prior=[e for e in events if e["date"]<t]
        if prior and (sale is None or prior[-1]["date"]>=sale["available"]-pd.Timedelta(days=1)):
            last=prior[-1]
            user=next(iter(last["users"])) if len(last["users"])==1 and not last["null_user"] else None
        elif sale and sale["available"]<=t: user=sale["user"]
        else: user=None
        if user is None: flow["unknown_user"]+=1; continue
        record={"vehicle":vin,"customer":user,"anchor":anchor,"scoring":t,"due":due,"end":end,
                "kind":an["kind"],"mode":mode,"rate_known":an["rate"] is not None,"label":None,"state":None}
        if end>C-pd.Timedelta(days=margin): record["state"]="censored"
        else:
            follow=[e for e in events if t<=e["date"]<=end]
            success=next((e["date"] for e in follow if e["return"] and e["return_users"]=={user} and not e["return_null"]),None)
            identity=next((e["date"] for e in follow if e["users"]!={user} or e["null_user"]),None)
            damaged=min([d for d in uncertain.get(vin,[]) if t<=d<=end],default=None)
            obstruction=min([d for d in [identity,damaged] if d is not None],default=None)
            if success is not None and (obstruction is None or success<obstruction):
                record["state"]="return"; record["label"]=0
            elif obstruction is not None: record["state"]="indeterminate"
            else: record["state"]="churn"; record["label"]=1
        rows.append(record)
    w=pd.DataFrame(rows)
    assert not w.duplicated(["vehicle","anchor","kind"]).any()
    assert w.scoring.le(w.end).all()
    assert w.loc[w.label.notna(),"end"].le(C-pd.Timedelta(days=margin)).all()
    flow.update(w.state.value_counts().to_dict())
    return w,dict(flow)
w,flow=build()
def summary(w):
    l=w[w.label.notna()]
    return {"eligible":len(w),"labeled":len(l),"churn":int(l.label.sum()),"rate":float(l.label.mean()),
            "customers":w.customer.nunique(),"vehicles":w.vehicle.nunique(),
            "relationships":len(w[["customer","vehicle"]].drop_duplicates()),"states":w.state.value_counts().to_dict(),
            "modes":w["mode"].value_counts().to_dict(),"kinds":w.kind.value_counts().to_dict()}
SUMMARY=summary(w)
print("CUTOFF",str(C),"FLOW",json.dumps(flow),"SUMMARY",json.dumps(SUMMARY))
temporal=w.assign(month=w.scoring.dt.strftime("%Y-%m")).groupby("month").agg(eligible=("state","size"),labeled=("label","count"),churn=("label","sum"),rate=("label","mean"))
print("TEMPORAL",temporal.to_json(orient="index"))

print("WARMUP",summary(w[w.scoring<pd.Timestamp("2025-01-01")]))
print("FROM2025",summary(w[w.scoring>=pd.Timestamp("2025-01-01")]))
print("KIND_LABELS",w.groupby("kind").agg(n=("label","count"),churn=("label","sum"),rate=("label","mean")).to_json(orient="index"))
print("OBSERVABILITY",json.dumps({"end_after_cutoff":int(w.end.gt(C).sum()),"margin_only":int((w.end.le(C)&w.end.gt(C-pd.Timedelta(days=30))).sum()),
"low_lead":int((w.due-w.scoring).dt.days.lt(30).sum()),"late_sale":int((s.SalesDate>s.DeliveryDate).sum())}))
print("MONTHLY",w.assign(month=w.scoring.dt.strftime("%Y-%m")).groupby(["month","state"]).size().unstack(fill_value=0).to_json(orient="index"))
print("EXCLUSION_RECONCILIATION",sum(flow[k] for k in ["unknown_plan","not_open","superseded","already_in_workshop","unknown_user"])+len(w),len(anchors))
print("QUALITY_CONFLICTS", {c:int(a.groupby("schedule_id")[c].nunique(dropna=False).gt(1).sum()) for c in ["vehicle_id","customer_id","EffectiveCheckinDate","EffectiveCheckoutDate","VehicleCurrentKM","ModelYear","ShortVehicleModelGroupTreated"]})
# Compare grace periods on the same fully mature population, with a stable identity for all horizons.
def outcome_for(row,grace):
    events=days.get(row.vehicle,[]); end=row.due+pd.Timedelta(days=grace); user=row.customer
    follow=[e for e in events if row.scoring<=e["date"]<=end]
    returned=[e["date"] for e in follow if e["return"] and e["return_users"]=={user} and not e["return_null"]]
    obstructed=[e["date"] for e in follow if e["users"]!={user} or e["null_user"]]
    obstructed += [d for d in uncertain.get(row.vehicle,[]) if row.scoring<=d<=end]
    if returned and (not obstructed or min(returned)<min(obstructed)): return 0
    if obstructed: return None
    return 1
common=w[w.due.add(pd.Timedelta(days=120)).le(C-pd.Timedelta(days=30))]
out=pd.DataFrame({h:[outcome_for(r,h) for r in common.itertuples()] for h in [30,60,90,120]},index=common.index).dropna()
print("SAME_COHORT_SENSITIVITY",len(out),out.sum().to_dict(),out.mean().to_dict())
assert (out[30]>=out[60]).all() and (out[60]>=out[90]).all() and (out[90]>=out[120]).all()
# A date-based invariant for every labeled relation: outcomes exist only after scoring.
assert (w.anchor<w.scoring).all()
assert (w.loc[w.label.notna(),"end"]+pd.Timedelta(days=30)<=C).all()
assert len(w)==sum(w.state.value_counts())
assert len(w)==131051 and int(w.label.sum())==42733
print("ASSERTIONS","PASS: unique episodes, anchor before scoring, label maturity, flow reconciliation, monotonic same-cohort sensitivity")

assert HASHES == {p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in FILES}
print("SOURCE_INTEGRITY", "PASS")

# REPRODUCER_END
```

</details>

### Verificar localizadores de la ficha

```powershell
python -X utf8 -B -c "from pathlib import Path; from zipfile import ZipFile; import xml.etree.ElementTree as E; p=next(Path('Dataset').glob('*.docx')); z=ZipFile(p); root=E.fromstring(z.read('word/document.xml')); ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}; print('\n'.join('P'+str(i)+': '+''.join(n.text or '' for n in p.findall('.//w:t',ns)) for i,p in enumerate(root.findall('.//w:p',ns),1) if i in [61,66,77,85,91,99,102,104]))"
```
