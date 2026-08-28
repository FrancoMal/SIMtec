# Ford Innovation Challenge III: AI Edition — Análisis y Estrategia

> Basado en: Reglamento v3, Resumen de Desafíos, Calendario oficial y transcripción de la reunión informativa con Austral (grabación de 33 min).

---

## 1. Qué es el concurso

- Organiza **Ford Argentina** (Planta Pacheco). Tercera edición, esta vez enfocada 100% en **IA / Machine Learning**.
- Participan 6 universidades: Austral, UADE, UBA, UTN, UDESA e ITBA.
- **Equipos de 3 personas**, estudiantes regulares desde 3° año. Máximo 54 participantes (3 equipos por universidad).
- Duración del trabajo: **~3 semanas** con mentores de Ford, flexible (no es una pasantía con horario; se adapta a la cursada).
- Se espera una **prueba de concepto (PoC)** de complejidad acotada, no un producto productivo. Ford entrega los datasets (curados, chicos, con pocas variables) una vez seleccionados.

## 2. Los 3 desafíos

| # | Desafío | Problema | Tipo de ML |
|---|---------|----------|------------|
| 1 | **Repurchase Propensity** (Customer Experience) | Predecir qué clientes están por recomprar un Ford usando historial (frecuencia de cambio de auto, servicios, clics en la web, etc.) para marketing/descuentos personalizados | Clasificación / scoring de propensión sobre datos tabulares de clientes |
| 2 | **Powertrain Intelligence** | Predecir eventos de degradación de eficiencia de combustión por mal uso del cliente, con datos de vehículos conectados (mencionan ingesta de oxígeno del motor) → mantenimiento predictivo | Series temporales / detección de anomalías sobre telemetría |
| 3 | **Predictive Quality** | Con el historial de línea de producción (tiempos de ciclo, parámetros dentro de tolerancia), predecir qué unidades conviene revisar antes del Gate Release → calidad predictiva en vez de reactiva | Clasificación con clases muy desbalanceadas sobre datos industriales |

Mentores confirmados en la reunión: Nico y Cami (Powertrain), Pablo y Martina (Predictive Quality). Los de Customer Experience no estuvieron.

## 3. Fechas (según calendario oficial — la fuente más actual)

| Fecha | Evento |
|-------|--------|
| **31/8** | Cierre de inscripciones ⚠️ **(quedan ~3 días)** |
| 7/9 | Aviso de equipos seleccionados |
| 11/9 | Kick-off en Planta Pacheco (mañana, ~9 a 12; se firma el reglamento) |
| **25/9 23:59** | Entrega del PDF final por mail a umonten1@ford.com y avedia@ford.com |
| 2/10 | Trials Day en Pacheco (día completo: presentación ante jurado, feedback, ~4h para pulir; almuerzo incluido) |
| Semana del 5-9/10 | Awards / premiación en Pacheco |

> ⚠️ El video menciona fechas de agosto (cierre 17/8, kickoff 28/8) — corresponde a un cronograma anterior que se corrió. **Confiar en el calendario JPG y el reglamento.** Igual conviene reconfirmar por mail.

## 4. Cómo funciona la inscripción y la selección (clave, dicho en el video)

1. El equipo de 3 **ya tiene que estar armado** al inscribirse (no lo arma la universidad).
2. En el formulario se elige un desafío como **opción A y otro como opción B** (el reglamento habla de ordenar los 3 por preferencia).
3. Hay que subir un **video de máximo 2 minutos** explicando *cómo encararían* el desafío elegido.
   - **No evalúan la solución técnica definitiva**: evalúan cómo encaran el problema, cómo trabajan en equipo, soft skills, claridad al presentarse y comunicar.
4. Los mentores de cada desafío miran los videos y seleccionan **un equipo por universidad por desafío** → cada desafío tiene 1 equipo de cada universidad compitiendo.
5. Si un cupo queda libre, entra en juego la opción B.

## 5. Qué se evalúa y qué se gana

- **Criterio del jurado** (reglamento §8): originalidad, creatividad y uso de las herramientas enseñadas durante el concurso. Jurado = directores, gerentes y supervisores de Ford, por desafío. 1° y 2° premio por desafío.
- **Premios**: 1° puesto → experiencia en la pista de pruebas de Pacheco (manejo con pilotos, varios modelos) + merchandising + trofeo. 2° → merchandising + trofeo. Todos → certificado con horas y tareas + diploma.
- **Pasantías (el premio real)**: RRHH observa a todos durante los eventos, **independientemente de quién gane**. Más del 10% de los participantes del FIC 1 hoy son pasantes de Ford. Piden cargar el CV en el formulario — hacerlo sí o sí. Hay olas de ingreso en octubre y abril.
- **Austral**: los 3 equipos seleccionados obtienen créditos — el challenge cuenta como el "Seminario de Innovación" (materia optativa) para industrial, ciencia de datos e informática.

## 6. Cosas a tener en cuenta (riesgos y letra chica)

- ⚠️ **Cesión total de propiedad intelectual**: al entregar, ceden a Ford de forma gratuita, perpetua e irrevocable todos los derechos sobre la idea (reglamento §5.6). No presentar nada que quieran reutilizar como proyecto propio/startup.
- La entrega declara que la solución es **original e inédita**; usar librerías estándar está bien, pero no copiar una solución existente identificable.
- También se cede el uso de imagen y voz para publicidad de Ford (§9), y hay cláusula de indemnidad (§10).
- Los 3 eventos son **presenciales en Planta Pacheco** con seguro de la universidad al día. Si alguien no puede asistir a una fecha, avisar: en la reunión dijeron que "siempre se le busca la vuelta".
- El **entregable oficial es un único PDF** (25/9) — antes del Trials Day. El Trials Day sirve para presentar, recibir feedback y pulir. Confirmar con los mentores si hay re-entrega post-feedback.
- Preguntar todo por mail sin miedo: lo repitieron varias veces; los mentores aceptan consultas por mail y reuniones virtuales (o presenciales).
- No pueden participar empleados/pasantes de Ford ni familiares hasta 4° grado.

## 7. Estrategia sugerida

### 7.1 Ya — antes del 31/8 (inscripción)

1. **Armar el video de 2 min hoy o mañana.** Es el único filtro de selección. Guion sugerido:
   - 15s: quiénes somos (nombres, carreras — resaltar si somos interdisciplinarios).
   - 45s: cómo entendemos el problema (reformularlo en términos de negocio: "detectar X a tiempo vale $ porque...").
   - 45s: cómo lo encararíamos: metodología (EDA → baseline → iterar → validar → comunicar), roles en el equipo, cadencia de trabajo semanal.
   - 15s: por qué nosotros (motivación, ganas, complementariedad).
   - Consejos: cámara buena, luz, hablar los 3, sin leer. Mostrar entusiasmo y claridad > tecnicismos.
2. **Elegir bien la opción A.** Criterios:
   - **Predictive Quality** o **Powertrain**: más "ingenieriles", probablemente menos demandados por otros equipos (más chances de quedar), y los mentores presentes en la charla son de estos dos (señal de que son los desafíos "core" de planta).
   - **Repurchase Propensity**: el más estándar de data science (churn/propensity clásico) — más fácil de ejecutar bien, pero probablemente el más elegido y más difícil de diferenciarse.
   - Sugerencia: opción A = el que mejor matchee las carreras del equipo; opción B = uno de los otros dos que igual nos entusiasme (la opción B se usa de verdad).
3. Cargar CVs actualizados en el formulario (mirando pasantías).

### 7.2 Entre inscripción y kick-off (1-11/9)

- No se puede hacer feature engineering sin los datos, pero sí:
  - Repasar el stack: pandas, scikit-learn, XGBoost/LightGBM, SHAP, matplotlib. Armar un repo template con notebooks de EDA y un pipeline baseline listo para enchufar datos.
  - Estudiar el dominio del desafío asignado (ej.: para Powertrain, qué es un sensor de O2, ciclos de manejo, fuel trim; para Quality, SPC, tolerancias, cycle time; para Repurchase, uplift modeling, RFM, propensity scoring).
  - Preparar una lista de preguntas para los mentores para el kick-off (diccionario de datos, definición exacta del target, métrica que les importa, cómo se usaría la solución en producción).

### 7.3 Las 3 semanas de trabajo (11/9 → 25/9)

- **Semana 1**: EDA a fondo + baseline simple (regresión logística / árbol). Reunión temprana con mentores para validar entendimiento del target. Un baseline que funciona la semana 1 saca toda la presión.
- **Semana 2**: iterar features y modelos; medir con la métrica correcta (con clases desbalanceadas: precision/recall, PR-AUC, y sobre todo **costo de negocio**: qué cuesta un falso negativo vs. inspeccionar de más).
- **Semana 3**: congelar modelo, armar el PDF y la presentación. **No dejar el PDF para el final**: es EL entregable juzgado.
- Cadencia: 2-3 encuentros semanales cortos + trabajo asincrónico con roles claros (ej.: uno lidera datos/features, otro modelado/validación, otro negocio/comunicación — rotando para que todos entiendan todo).
- Usar a los mentores agresivamente: mail + reuniones virtuales. Los equipos que consultan bien quedan mejor vistos (RRHH mira todo).

### 7.4 Cómo diferenciarse (lo que gana según el criterio de Ford: originalidad + creatividad + herramientas)

- **Enmarcar en negocio, no en modelo.** No "logramos 0.87 de AUC" sino "con este modelo, revisando solo el 10% de las unidades capturás el 60% de los casos de riesgo, ahorrando X". Un jurado de directores y gerentes compra impacto, no hiperparámetros.
- **Explicabilidad**: SHAP / importancia de variables para contar *qué* señales anticipan el evento — a Ford le sirve más entender el patrón que el score.
- **Demo simple**: un dashboard mínimo (Streamlit) o mockup de cómo lo usaría el operario / el equipo de marketing eleva mucho la percepción sin gran costo.
- **Honestidad técnica**: mostrar validación seria (split temporal si aplica, no data leakage) y limitaciones. En una PoC, la rigurosidad diferencia de los equipos que solo tiran un notebook.
- **Propuesta de "siguiente paso"**: cerrar el PDF con cómo se escalaría a producción (más datos, monitoreo, reentrenamiento). Muestra visión.

### 7.5 Trials Day (2/10)

- Llegar con la presentación ensayada (probablemente ~10 min): problema → enfoque → resultados → impacto → próximos pasos. Que presenten los 3.
- Anotar todo el feedback del jurado y usar las 4 horas de la tarde para incorporarlo visiblemente.
- Es también el día de networking / radar de RRHH: participar, preguntar, interactuar con otros equipos y líderes.

---

## Checklist inmediato

- [ ] Definir orden de preferencia de desafíos (A y B) entre los 3
- [ ] Grabar y editar el video de 2 min
- [ ] Completar el formulario de inscripción **antes del 31/8**
- [ ] Cargar CVs
- [ ] Verificar que los 3 cumplimos requisitos (3° año+, alumno regular, seguro al día vía universidad)
- [ ] Mandar mail de consulta si algo no cierra (fechas del video vs. calendario)
