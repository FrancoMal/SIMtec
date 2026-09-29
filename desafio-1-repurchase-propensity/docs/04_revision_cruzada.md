# 04 — Revisión cruzada: la solución de esta carpeta ("fable") frente a la de `G:\SIMtec-astra` ("astra")

> Segunda vuelta del desafío, 15/09/2026. Dos modelos resolvieron el mismo problema sin verse. Este documento
> (1) zanja por qué uno reporta 41,6 % de churn y el otro 78,2 %, (2) revisa el trabajo de astra con evidencia y
> (3) propone la solución combinada. Todo lo de astra se leyó en solo lectura; los cálculos de este documento están
> en `scripts/revision_cruzada/` y sus salidas en `reports/revision_cruzada/`. Ningún número es de memoria. Las
> afirmaciones fueron verificadas por cuatro revisores independientes con código propio; las correcciones que resultaron
> están incorporadas al texto y el detalle de cada veredicto está en el Anexo B.

## 0. Lo esencial en diez líneas

1. **Los dos trabajos definen la misma población** (cada mantenimiento completado abre una ventana cuando llega su
   vencimiento estimado por km y tiempo; el primer service se ancla en la entrega) **y el mismo evento** (mantenimiento
   programado completado en la red). Lo que difiere es el **horizonte**: astra etiqueta churn si no volvió **dentro del
   mes calendario del vencimiento** (mediana de 14 días después de vencer); fable si no volvió **hasta 90 días después
   del vencimiento** (ventana de 120 días abierta 30 días antes).
2. Aplicando la etiqueta de astra sobre las ventanas de fable, el churn es **79,0 %** (82,1 % si además se exige el mismo
   `customer_id`, como hace astra); aplicando la de fable sobre las ventanas de astra, **44,0 %**. Misma población, mismos
   datos: la diferencia es el horizonte. Zanjado.
3. **Entre el 40 % y el 44 % de los "churn" mensuales completa el mantenimiento antes de vencimiento + 90 días** (40,5 %
   sobre las anclas de fable, 42,9-44,2 % sobre los churn reales de astra): son clientes tardíos, no perdidos. Por eso su
   lift tiene techo 1,28 y su modelo llega a 1,20.
4. **Con la misma etiqueta mensual, el pipeline de fable ordena mejor, pero menos de lo que parece**: el 0,730 de fable y
   el 0,673 de astra están medidos sobre poblaciones distintas; sobre los mismos 9.322 vehículos-mes la ventaja en ROC-AUC
   es de 0,025 a 0,043 según la etiqueta (IC95 de la diferencia +0,02 a +0,05) y en lift@10 % no hay diferencia detectable
   (1,24-1,27 vs 1,24-1,25; el IC incluye 0). Parte de la ventaja es más historia de entrenamiento y dealer + encuestas.
   El modelo aporta algo; la etiqueta manda.
5. **Astra tenía razón en el intervalo del plan: 16.000 km / 12 meses para la Ranger nueva** (fuente oficial Ford
   Argentina), no 15.000. Fable lo corrigió en esta vuelta.
6. Astra hizo mejor la ingeniería de confianza: hashes de los crudos, 19 pruebas automáticas, casos trazables, IC por
   bootstrap, identidad tratada con cuidado, economía que descuenta incentivos a retornos orgánicos.
7. Astra tiene dos errores de definición: cuenta reparaciones en garantía como mantenimiento (3.777 turnos; 20 de ellos
   son "Contactless service") y exige que vuelva el **mismo `customer_id`** (3,1 % de sus ventanas etiquetadas, el 4,0 %
   de sus churn, son el mismo vehículo que volvió con otro id de agenda; en 4 de cada 5 casos ese id nunca se había visto
   en el vehículo, así que puede ser un cambio de usuario real y no un duplicado).
8. Fable tenía errores propios: el nominal de 15.000 km, una población que incluía vehículos sin cliente contactable,
   scoring por vehículo en vez de por lote mensual, y un PDF con cifras de una corrida anterior.
9. **Definición zanjada**: población y evento de fable con las exclusiones de identidad de astra; **scoring mensual**
   (cadencia de astra) sobre las ventanas abiertas o por abrir en el mes; **horizonte vencimiento + 90 días** (etiqueta de
   fable) como resultado primario; "no vuelve en 30 días" como resultado secundario para el tablero operativo.
10. **Solución combinada**: ventana y features de fable, disciplina de evidencia y operación de astra, y una validación
    prospectiva nueva porque los dos vimos el test antes de cerrar la definición.

---

## 1. La discrepancia 41,6 % vs 78,2 %, zanjada con números

### 1.1 Qué hace cada uno, exactamente

| Elemento | fable (`src/repurchase/ventanas.py`) | astra (`src/features.py`, `src/data.py`) |
|---|---|---|
| **Quién entra** | Todo vehículo Ranger con inicio de garantía conocido, ventas ∪ agenda. Ancla = último mantenimiento completado; si no hay, la garantía (primer service). | Vehículos conocidos antes del scoring (venta entregada o evento de agenda anterior) **con `customer_id`**, familia con regla (P703/P375; Raptor 2023 ambigua excluida) y sin "identidad ambigua". Ancla = último mantenimiento completado; si no hay, entrega o garantía. |
| **Vencimiento** | `ancla + min(365 d, K/tasa)`, K = 16.000 P703 / 10.000 P375 (15.000 hasta esta vuelta); tasa = km al ancla / edad; primer service: garantía + 300 d. | `min(ancla + 1 año, fecha_km + (km_ancla + K − km_último)/ritmo)`, K = 16.000 P703 / 10.000 P375; ritmo = mediana de hasta 3 diferencias de odómetro (cualquier visita cerrada), si no km/edad; sin ritmo: sólo calendario (primer service = entrega + 1 año). |
| **Cuándo se scorea** | Al abrir la ventana: vencimiento − 30 días (fecha propia de cada vehículo). | El 1° del mes en que cae el vencimiento (lote mensual). |
| **Qué cuenta como retorno** | Turno `(60) Concluido` con ítem numerado del plan (`ServiceMaintenance`), **del vehículo**, cualquier `customer_id`; fecha del evento = check-in (o fecha del turno). | Turno `(60) Concluido` con `ServiceType = Mantenimiento` (incluye *Guarantee*), checkout válido, **del mismo `customer_id`**; retorno anónimo → etiqueta indeterminada; fecha del evento = checkout. |
| **Horizonte** | Hasta vencimiento + 90 días (ventana de 120 días). | Hasta el último día del mes calendario (0 a 31 días después de vencer; mediana 14; el 18 % de su test tiene menos de 5 días). |
| **Preempción** | Si volvió antes de abrir la ventana (vencimiento − 30), no hay ventana. | Si volvió antes del 1° del mes, la ancla nueva reemplaza a la vieja: no hay ventana. El corte es igual o posterior al de fable: el 18 % de sus episodios preemptados volvió entre vencimiento − 30 y el vencimiento (retorno para fable). |
| **Censura** | Horizonte después de 26/07/2026 (corte − 30 d). | Ventanas de agosto 2026 y horizontes posteriores al 31/07. |
| **Resultado** | 142.558 ventanas, churn 41,6 %; test ene-mar 2026 42,6 %. | 132.869 ventanas, churn ≈ 78 %; test abr-jul 2026 78,2 %. |

Las dos poblaciones se solapan casi por completo: 76.713 vehículos en común de 77.973 (astra; 98,4 %) y 92.326 (fable);
en el mismo vehículo y la misma ancla, el vencimiento estimado coincide en la mediana (0 días; p25 −11, p75 +12) para las
anclas de mantenimiento y difiere −65 días en el primer service (garantía + 300 vs entrega + 1 año). Cruzando por vehículo
sin emparejar anclas la mediana es −1 día. No hay dos poblaciones distintas: hay una población y dos relojes.

### 1.2 La prueba: cada etiqueta sobre las ventanas del otro (`reports/revision_cruzada/01_reconciliacion.md`)

| Ventanas | Etiqueta mensual de astra | Etiqueta de fable (vencimiento −30 / +90) |
|---|---|---|
| de astra (107.557 con horizonte de fable cerrado) | **77,7 %** | **44,0 %** |
| de fable (abr-jul 2026, anclas propias; 25.829 / 11.755 con horizonte cerrado) | **79,0 %** | **46,6 %** |

El 78 % y el 42 % son la misma realidad medida a 14 y a 90 días del vencimiento. De las ventanas que la regla mensual
etiqueta como churn sobre las anclas de fable, el **40,5 % completa el mantenimiento antes de vencimiento + 90 días**
(vencimientos de abril-mayo 2026, los únicos con el horizonte de 90 días cerrado al corte; 39,9 % con el margen de 30
días de la etiqueta de fable); sobre los churn reales de astra el porcentaje es 42,9 % (abril) a 44,2 % (todo su
historial). Los otros dos ingredientes pesan poco: exigir el mismo `customer_id` suma 3,1 puntos de churn (3,1 % de sus
ventanas, 4,0 % de sus churn: el vehículo volvió con otro id) y contar *Guarantee* agrega 3.777 "mantenimientos" que no
son del plan. La convención de fecha del evento (fable check-in, astra checkout) no mueve ninguna de estas cifras más de
0,3 puntos.

Dos salvedades de población. El 44,0 % no es "la etiqueta de fable sobre la población de fable": astra sólo crea la
ventana si el vehículo no volvió antes del 1° del mes, y el 9,0 % de las ventanas evaluables de fable vuelve entre
vencimiento − 30 y el 1°; el churn de fable condicionado a no haber vuelto antes del 1° es 45,7 %, no 41,6 %. Y las cifras
de esta tabla se recalcularon sobre el `ventanas.parquet` con K = 16.000 (una primera versión de este documento citaba
80,2 % / 41,3 % / 46,5 % de la corrida con K = 15.000, justo el error que la sección 3 le critica al PDF; ver Anexo B).

### 1.3 Qué dicen la ficha técnica y el tutor, y cuál definición es la correcta

- La **ficha** define el churn como "no se observa el mantenimiento objetivo dentro del horizonte de resultado
  posterior al scoring", el scoring "al abrir la ventana, opcionalmente actualizaciones durante la ventana", y deja
  "las reglas exactas de ventana y horizonte a validar por modelo/año". El propósito declarado es "anticipar cuáles
  usuarios tienen mayor probabilidad de **no regresar a la red oficial**" y "el churn se reconoce tarde, cuando la
  ventana termina sin un mantenimiento completado".
- El **tutor** dijo "horizonte de predicción sugerido: el próximo mes (corto plazo, no a años)" y "ni antes ni después
  de cuando le toca".

Lectura honesta: **ninguno de los dos documentos fija el horizonte**; la lectura literal de "el próximo mes" es la de
astra, y la lectura de "no regresar a la red" es la de fable. La correcta es la que mide lo que Ford quiere evitar. Un
cliente que vence el 25 y viene el 5 del mes siguiente no abandonó la red; con la etiqueta mensual es un "churn"
acertado, y contactarlo habría sido capacidad desperdiciada. Con 78 % de positivos la etiqueta deja de discriminar
comportamiento y el techo del lift es 1/0,78 = 1,28: astra lo dice con todas las letras ("no corresponde prometer
capturas extraordinarias"). Con 90 días de horizonte el churn (42-44 %) ya contiene sobre todo a los que no vuelven
(19 % en 18 meses) más los muy tardíos; los propios datos de astra lo muestran: su lift sube de 1,20 a 1,56 cuando el
horizonte pasa de 30 a 90 días.

**Zanjado, con lo que cada uno tenía bien:**

| Componente | Definición correcta | De quién |
|---|---|---|
| Población | Relaciones usuario–vehículo con vencimiento estimado en el período, ancladas en el último mantenimiento completado (o entrega/garantía), **con cliente contactable e identidad no ambigua**, familia con regla de plan conocida. Los vehículos sin ningún cliente identificable se scorean pero no entran en la lista de contacto. | fable + exclusiones de astra |
| Vencimiento | `min(ancla + 365 d, ancla + K/tasa)` con **K = 16.000 km (P703, Raptor P703) / 10.000 km (P375)**, tasa individual; ritmo con el último odómetro de cualquier visita cerrada (astra) y fallback km/edad (fable). Primer service: garantía + 300 d hasta tener km de telemetría. | astra (K, odómetro) + fable (calendario del primer service) |
| Momento de scoring | **Lote mensual** el 1° de cada mes, sobre todas las ventanas abiertas o que abren ese mes (apertura = vencimiento − 30 d); features as-of el 1°. Cumple "próximo mes" y "actualizaciones durante la ventana". | astra (cadencia) + fable (apertura) |
| Evento de retorno | `(60) Concluido` con ítem numerado del plan (`ServiceMaintenance`), **del vehículo**; *Guarantee*, campañas, diagnósticos y `(90) sin OS` cuentan como visita, no como retorno. | fable |
| Horizonte primario | **Vencimiento + 90 días**; churn = no hay retorno entre la apertura y ese día. Censura con margen de 30 días antes del corte. | fable |
| Horizonte secundario (operativo) | "No vuelve en los próximos 30 días" sobre las ventanas abiertas del mes, para el tablero y para medir la campaña mes a mes. Se reporta, no se optimiza. | astra |
| Pregunta al mentor | Con cuánta anticipación quiere Ford contactar (define −30 vs −60) y cuántos días después de vencer considera perdida la oportunidad (define +60/+90/+120). | ambos |

**Donde fable estaba mal y lo dice con todas las letras**: el nominal de 15.000 km era una lectura equivocada de los
datos (el km/n medía 16,0-16,2 mil y lo interpreté como "15.000 más atraso"; la fuente oficial dice 16.000); la
población incluía vehículos sin cliente identificable (141 de 30.499 en la lista de hoy) y sin regla de identidad;
el scoring por vehículo no es un lote operativo; y el PDF que se entregó a revisión tenía cifras de una corrida
anterior (27.327 ventanas, enero-abril) mezcladas con las de la corrida siguiente (20.191, enero-marzo; hoy 19.704 con
K = 16.000).

---

## 2. Revisión crítica del trabajo de astra

### 2.1 Lo que hizo mejor que fable, y por qué importa

| Qué | Por qué es mejor |
|---|---|
| **Intervalo oficial del plan (16.000 km P703 / 10.000 P375) con fuente pública de Ford** | Fable lo infirió de los datos y erró el nominal. Al releer la misma página en esta vuelta apareció además algo útil para la activación (astra no lo menciona): Ford ya tiene descuentos por continuidad ("Con Vos": 5 % en el 2° service, 10 % en el 3°, 15 % del 4° en adelante; letra chica de precios sugeridos con vigencia mensual, 01-30/09/2026), un incentivo existente para comunicar en el contacto. |
| **Integridad y reproducibilidad demostradas**: SHA-256 de los crudos al inicio y al cierre, 19 pruebas automáticas (semántica temporal, identidad, censura, ranking, economía), casos trazables desde el CSV hasta el score | Es la prueba material de "no tocamos los datos" y de que la semántica no se rompe al refactorizar. Fable no tiene tests. |
| **Identidad**: no hereda tipo de persona ni canal del comprador cuando cambia el usuario; excluye empates de identidad; retorno anónimo → etiqueta indeterminada, no churn | Es la lectura correcta de la unidad "relación usuario–vehículo" de la ficha. Fable arrastra atributos de la venta a cualquier usuario posterior. |
| **Odómetro**: usa el último km de **cualquier visita cerrada** (no sólo mantenimientos) para proyectar el vencimiento | Más lecturas, vencimiento más actual. Fable proyecta sólo desde el km del último mantenimiento. |
| **Honestidad sobre el test**: declaró que vio una primera corrida antes de corregir ventanas, odómetro e identidad, archivó esa corrida y pidió validación prospectiva | Fable hizo lo mismo (cambió definiciones mirando métricas de test) y no lo había escrito. Corregido en este documento. |
| **Incertidumbre**: bootstrap por cliente (IC del lift 1,18-1,22), estabilidad mes a mes, clientes vistos y no vistos, cupos por dealer | Fable reporta estimaciones puntuales. |
| **Economía**: descuenta incentivos pagados a retornos orgánicos, calcula el rescate de equilibrio (3,19 %), separa margen de Ford y del dealer, no valúa cada error como una venta perdida | Más prudente y más defendible que el ROI de fable (uplift 15 % supuesto y USD 250 por service). |
| **Operación**: cupo por usuario (una flota no multiplica llamados), supresión de completados y turnos confirmados antes de contactar, validación de consentimiento en CRM | Fable tiene la vista por usuario pero el cupo es por vehículo. |
| **Diseño del piloto**: aleatorización por cliente estratificada por dealer, banda de riesgo y flota; tamaño de muestra calculado; segunda etapa para comparar políticas de selección | Más completo que el A/B por decil de fable. |

### 2.2 Lo débil o equivocado, con evidencia

1. **El horizonte mensual confunde "tarde" con "perdido"** (sección 1): 40-44 % de sus churn vuelve antes de
   vencimiento + 90; techo del lift 1,28; el modelo aprende sobre todo *cuándo* dentro del ciclo, no *si* vuelve. Su
   propia sensibilidad a 90 días (lift 1,56, churn 55,8 %) muestra que el problema es el target. Agravante: para un
   vencimiento en los últimos días del mes quedan 0-5 días de observación (el 18 % de su test tiene menos de 5 días; el
   2,7 %, menos de 1). El artefacto de calendario existe pero es moderado: el churn sube de 75,6 % (vencimiento en los
   primeros 0-5 días desde el 1°) a 81,7 % (26-31 días); ordenar sólo por "días hasta el vencimiento" da AUC 0,54 y lift
   1,05, su score correlaciona 0,09 con esa variable y el AUC de su modelo dentro de cada tramo del mes sigue en
   0,64-0,69. No invalida el modelo; invalida la etiqueta como medida de abandono. Dos efectos de población de su
   mecánica mensual que salieron de la verificación: la preempción corta el 1° del mes y no en vencimiento − 30 (12.596
   episodios, el 18,4 % de los que preempta, volvieron entre −30 y el vencimiento: retorno para fable, sin ventana para
   astra, lo que empuja su churn hacia arriba), y 3.573 episodios (2,7 % de sus ventanas) nunca se scorean porque el
   vencimiento, recalculado cada mes con odómetros nuevos, salta de "futuro" a "vencido" entre dos snapshots; 1.359 de
   ellos siguen vencidos sin ventana al cierre de los datos (churners que no cuenta).
2. **Cuenta reparaciones en garantía como mantenimiento**: `maintenance = ServiceType == 'Mantenimiento'` incluye los
   ítems *Guarantee* (3.808 turnos concluidos sin número de service, de los que efectivamente cuenta 3.777: 31 no tienen
   VIN; 20 son "Contactless service", no garantía). Sus 225.479 "mantenimientos estrictos" contra 221.703 de fable a
   nivel turno (+3.776; los 220.522 del informe 01 son a nivel vehículo-día, después de colapsar visitas partidas). La
   ficha pide "mantenimiento programado". Además fecha el evento por el **checkout** (fable por el check-in): 1.184 de
   sus churn (1,2 %) son vehículos que entraron al taller dentro del mes y salieron al siguiente (580 con checkout a
   3 días o menos del fin de mes), y 1.084 de sus "retornos" (3,9 %) ya estaban en el taller el día del scoring.
3. **Exige que vuelva el mismo `customer_id`**: en la agenda el id cambia con el canal de reserva (EDA 04: el 53 % de
   los cambios coincide con un cambio Dealer↔FordPass; al menos 1 de cada 5 cambios es la misma persona con dos ids).
   Resultado: 3,1 % de sus ventanas etiquetadas (4,0 % de sus churn) son churn a nivel usuario que a nivel vehículo son
   retornos. Salvedad: sólo en el 19,4 % de esos casos el id que volvió ya había tenido un turno con ese vehículo (4,6 %
   es el comprador); en el 77,5 % nunca se lo había visto en ese VIN, así que puede ser un cambio de usuario real y no un
   id duplicado. El evento de retorno es del vehículo; el usuario es el destinatario del contacto.
4. **Ventana del primer service anclada a 1 año de la entrega**: el primer service ocurre a 9,2 meses de mediana y el
   42 % lo hace antes de los 9 meses (EDA de fable; 9,1 meses y 49 % en la población de astra); su población de primer
   ciclo entra recién en el mes 12 (3.562 ventanas en test, churn 78 %; edad mediana al scoring 349 días), cuando ya se
   perdió la mitad de la oportunidad: de los vehículos entregados entre enero de 2024 y junio de 2025 con un mantenimiento
   observado, el 69 % lo hizo antes del 1° del mes de entrega + 1 año y nunca tuvo ventana de primer ciclo en astra.
   Fable abre a los 270 días; ninguno de los dos tiene km para individualizarla (el 29 % de las ventanas de primer ciclo
   de astra sí tiene odómetro de otra visita y vence antes).
5. **Sin concesionario como feature**: el EDA 06 muestra que el dealer es un driver estable (Spearman 0,68-0,79 entre
   años, 73 % vs 84 % de retorno entre el peor y el mejor quintil) y accionable. Astra lo usa sólo para operar.
6. **`meses_observables` como feature de tendencia**: es una constante por mes de scoring (meses desde 2024-01), es su
   5° feature por SHAP y en test toma valores que el modelo nunca vio (27-30 vs ≤ 19 en entrenamiento). No es fuga ni
   inestabilidad: el LightGBM no extrapola, los valores 27-30 caen en el último bin y el score de test es idéntico al de
   fijar la variable en su máximo de entrenamiento (trata todo el test como agosto de 2025). Codifica época, no
   comportamiento; conviene reemplazarla por "meses de historia observable del vehículo" (fable) o quitarla.
7. **Baseline débil**: su "regla de historial" tiene AUC 0,498, peor que el azar; la heurística de fable
   (antigüedad + no-shows) da 0,61. Comparar contra una regla nula exagera el mérito del modelo.
8. **Entrenamiento desde julio de 2024**: descarta el primer semestre (censura a la izquierda). Es defendible, pero la
   ablación de fable muestra que exigir historia observable no cambia el resultado (0,734 vs 0,736), y los datos de
   2024-H1 valen.
9. **Discriminación**: ROC-AUC 0,673 y lift 1,20 son bajos para el uso previsto. Con la misma etiqueta, fable llega a
   0,730 / 1,24 en su propia población, que no es la misma (sus ventanas no comunes son más fáciles: AUC 0,732, 29 % de
   primer service). Sobre los mismos 9.322 vehículos-mes: ROC-AUC 0,689 vs 0,646 con la etiqueta de fable y 0,684 vs
   0,659 con la de astra (IC95 bootstrap por cliente de la diferencia: +0,03 a +0,05 y +0,02 a +0,04), y lift@10 %
   indistinguible (1,270 vs 1,250 y 1,242 vs 1,237; los IC incluyen 0: con 78 % de positivos los dos están pegados al
   techo). Reentrenando fable con el período de astra (jul-24 a ago-25) la brecha en AUC baja a +0,032 / +0,017, y quitando
   además dealer, TMA, zona, región y encuestas queda en +0,019 / +0,003 con el lift empatado: lo que aporta es sobre
   todo dealer + encuestas (2° y 3° feature por ganancia; datos que astra tenía en los mismos crudos y eligió no usar) y
   más historia de entrenamiento (100.296 ventanas de ene-24 a nov-25 vs 61.846).

Lo que **no** pude refutar: su exigencia de checkout válido no pierde eventos (0 mantenimientos concluidos sin
checkout; 1 con checkout anterior al turno; lo que sí mueve etiquetas es usar el checkout como *fecha*, punto 2), su
etiquetado se reproduce al 100 % desde su `eventos.parquet` con la regla que describe, y su modelo no está dominado por
el calendario. Lo revisé y estaba bien.

### 2.3 Lo que fable no vio y astra sí

- El intervalo oficial (16.000 km). Los descuentos por continuidad de Ford están en la misma página, pero astra no los
  menciona: los encontró fable al releerla.
- Identidad ambigua y no heredar atributos del comprador.
- El último odómetro de cualquier visita para proyectar el vencimiento.
- Tests automáticos y hashes como evidencia de integridad.
- Intervalos de confianza y estabilidad mensual.
- Que el test ya fue mirado y hace falta una validación prospectiva.
- Cupo por usuario y supresión de turnos confirmados antes del contacto.
- El costo de subsidiar retornos orgánicos con incentivos.

---

## 3. Autocrítica de fable (lo que corregí en esta vuelta)

| Error | Corrección |
|---|---|
| Nominal 15.000 km para P703 | 16.000 km en `config/params.json` y en el código; pipeline, ablaciones, sensibilidad y notebooks re-ejecutados. Resultado prácticamente igual (ROC-AUC 0,739, PR-AUC 0,699, 142.558 ventanas, churn 41,6 %; con 15.000 eran 145.538 / 0,736: −2.980 evaluables, −487 ventanas de test, +2.429 preempted). Hecho después de la verificación: la generación `RANGER` sin sufijo (Ranger pre-T6) pasó a 10.000 km y el comentario de `ventanas.py` se corrigió; corrida definitiva: 142.637 ventanas evaluables, test 19.709, ROC-AUC 0,740, PR-AUC 0,704, ECE 0,010. |
| PDF con cifras de dos corridas | Corregido a medias. El `informe_final.md` se regeneró con la corrida final (69 de 83 cifras coinciden con `reports/modelo/resumen.md`), pero le quedan la tabla de ablaciones de §6.4 y la pregunta 1 de §11 ("15.000 km") de la corrida anterior. El PDF (`reports/informe_final.pdf`, 20:38) es anterior al `ventanas.parquet` con K = 16.000 (20:50) y sigue con 15.000 km, 20.191 ventanas de test y 0,736: es de una sola corrida, pero la vieja. No queda "27.327" ni "enero y abril" en ninguno. Hecho después de la verificación: §6.4 (ablaciones) y §11 actualizados y PDF regenerado desde el md con la corrida definitiva; el texto del PDF se verificó con pypdf (sin "27.327", "enero y abril", "15.000 km" ni cifras de corridas anteriores). |
| Sección 1 de este documento con cifras de dos corridas | La primera versión citaba 80,2 % / 41,3 % / 46,5 % / 92.838 / 76.830 / −7 d del `01_reconciliacion.md` corrido a las 20:48 con el parquet de K = 15.000, junto a 142.558 / 41,6 % de la corrida nueva. Se volvió a correr `01_reconciliacion_definiciones.py` sobre el parquet actual y se corrigió el texto (79,0 % / 40,5 % / 46,6 % / 92.326 / 76.713 / −1 d). |
| Población sin filtro de identidad | Documentado; en la solución combinada se adoptan las exclusiones de astra. |
| Scoring por vehículo | La solución combinada scorea en lote mensual. |
| Test visto durante el diseño | Declarado: cambié definiciones (KM, dedup, margen, K) mirando métricas de test. El test final no es virgen; hace falta validación prospectiva. |
| Sin tests automáticos ni hashes | Pendiente; se toma el diseño de astra. |

---

## 4. Hallazgos nuevos que salieron de mirar el trabajo del otro

1. **La diferencia entre soluciones es casi toda la etiqueta.** Con la etiqueta mensual, fable pasa de 0,739 a 0,730 de
   AUC y de lift 2,07 a 1,24: el horizonte de 30 días borra la mayor parte de la señal, no la capacidad del modelo.
2. **Los dos rankings se parecen** (Spearman 0,68 entre scores en los vehículos-mes comunes) y ambos están cerca del
   techo del lift mensual: sobre los mismos vehículos-mes el lift@10 % es indistinguible (1,27 vs 1,25; el IC de la
   diferencia incluye 0). Para diferenciarse hace falta un target con más contenido, no más árboles.
3. **El plan es 16.000 km, no 15.000**: el "atraso de ~1.000 km" del EDA era el nominal. La feature de atraso respecto
   del plan cambia de escala; el vencimiento estimado se corre 10-12 días más tarde para el P703 típico (mediana 10,
   p25 7, p75 14; 12 cuando manda la regla de km y no el tope de 365 días).
4. **Ford ya tiene un incentivo por continuidad** (5/10/15 %, en la letra chica de los precios sugeridos "Con Vos", con
   vigencia mensual): la activación no necesita inventar descuentos; necesita comunicar el que existe a quien está por
   perder la secuencia.
5. **3,1 puntos de churn por identidad** si se exige el mismo `customer_id` (3,1 % de las ventanas, 4,0 % de los churn):
   cuantifica el costo de tratar el id de agenda como identidad. No son necesariamente "falsos": en el 77,5 % de los
   casos el id que volvió nunca se había visto en ese vehículo.
6. **El artefacto de calendario de la etiqueta mensual es de 6 puntos** (75,6 % → 81,7 %) y no domina el modelo de astra
   (AUC 0,64-0,69 dentro de cada tramo del mes); la crítica válida es conceptual (tarde ≠ perdido), no de fuga.
7. **La mecánica mensual de astra deja gente afuera**: el 18 % de los episodios que preempta volvió entre vencimiento − 30
   y el vencimiento (retornos para fable), y 3.573 episodios (2,7 % de sus ventanas) nunca se scorean porque el
   vencimiento recalculado salta de "futuro" a "vencido" entre dos snapshots; 1.359 siguen vencidos sin ventana al cierre.
   Fijar el vencimiento una vez por ancla (fable) evita lo segundo.

---

## 5. Solución combinada

| Componente | Tomar de | Por qué |
|---|---|---|
| Población, ancla y evento de retorno | fable | Evento estricto del plan (sin garantía), retorno a nivel vehículo, primer service a 270-300 d. |
| Exclusiones de identidad y contactabilidad | astra | Identidad ambigua, sin cliente, familia sin regla: fuera de la lista automática. |
| Intervalos del plan y proyección de km | astra | 16.000 / 10.000 oficiales (10.000 también para la Ranger pre-T6 sin sufijo de generación); último odómetro de cualquier visita cerrada; fallback km/edad (fable); vencimiento fijado una vez por ancla (fable), para no saltear episodios. |
| Horizonte y etiqueta primaria | fable | Vencimiento + 90 d con apertura −30 d; margen de 30 d al corte. |
| Cadencia de scoring y tablero | astra | Lote el 1° de cada mes; resultado a 30 días como métrica operativa secundaria. |
| Features | fable | 86 features (atraso en km vs plan, intensidad, dealer, intervalos, flota, canal), sin `KM`, sin conectividad, sin `meses_observables` de tendencia. Sumar de astra: `dias_al_vencimiento` al 1° del mes y `dias_relacion_actual`. |
| Modelo y calibración | fable | LightGBM con early stopping e isotónica (ECE 0,017); astra usa sigmoide (ECE 0,9 %): equivalentes. |
| Evaluación | astra + fable | Split temporal con embargo (astra), recall a capacidad y lift por decil (fable), bootstrap por cliente e IC (astra), estabilidad mensual (astra), ablaciones y sensibilidad de ventana (fable). |
| Explicabilidad | ambos | SHAP con contribuciones que reconstruyen el logit (astra) y drivers en castellano (fable). |
| Operación | astra | Cupo por usuario, supresión de completados y turnos confirmados, validación CRM/consentimiento; segmentos por capacidad (fable). |
| Economía | astra | Rescate de equilibrio e incentivos a orgánicos; escenarios en vez de un ROI puntual. Sumar la asimetría de errores de fable como mensaje. |
| Piloto | astra | Aleatorización por cliente estratificada, tamaño de muestra, dos etapas (efecto del contacto; política de selección). |
| Evidencia e integridad | astra | Hashes, tests, casos trazables, corrida archivada; agregar las verificaciones adversariales del EDA de fable. |
| Documentación del target | fable | EDA en seis temas verificados y análisis de sensibilidad de 36 combinaciones. |

**Resultado esperado de la combinación** (evidencia parcial de esta vuelta): ROC-AUC ≈ 0,74 y lift@20 % ≈ 1,8 con la
etiqueta a 90 días (fable); ≈ 0,73 / 1,24 con la etiqueta mensual como vista secundaria; identidad y contactabilidad
resueltas; incertidumbre cuantificada.

---

## 6. Recomendación: por dónde seguir para tener el mejor modelo con la evidencia más sólida

1. **Cerrar la definición con el mentor** con la tabla de la sección 1.3 y dos preguntas concretas: anticipación del
   contacto (−30 / −60) y días después del vencimiento que Ford considera oportunidad perdida (+60 / +90 / +120).
   Mientras tanto, la primaria es +90 y se reportan las otras.
2. **Implementar la solución combinada** sobre el pipeline de fable: exclusiones de identidad, odómetro de cualquier
   visita, scoring en lote mensual, `dias_al_vencimiento`; portar los tests de semántica y el manifiesto SHA-256 de
   astra; bootstrap por cliente en la evaluación.
3. **Validación prospectiva**: congelar el modelo entrenado con datos hasta marzo de 2026 y evaluarlo en las ventanas
   de abril-julio 2026 con la etiqueta a 90 días **sin volver a tocar definiciones**; pedir a Ford el extracto de
   septiembre-noviembre 2026 para una segunda validación realmente ciega antes del Trials Day si es posible.
4. **Modelo del primer service** con telemetría (km real de los vehículos conectados): es la ventana con más churn y
   la única que ninguno de los dos puede individualizar.
5. **Piloto** con el diseño de astra y la segmentación por capacidad de fable; medir a 30 y a 90 días.
6. **Una sola narrativa para el jurado**: "misma población y evento, dos horizontes; elegimos el que mide abandono,
   scoreamos con la cadencia mensual, y lo probamos con evidencia que se puede rehacer".

---

## Anexo — archivos de esta revisión

- `scripts/revision_cruzada/01_reconciliacion_definiciones.py` → `reports/revision_cruzada/01_reconciliacion.md` y
  tres CSV (etiqueta cruzada por mes, artefacto de calendario). Regenerado sobre el `ventanas.parquet` con K = 16.000
  después de la verificación (la primera corrida, 20:48, usó el parquet con K = 15.000).
- `scripts/revision_cruzada/02_comparacion_misma_etiqueta.py` → `reports/revision_cruzada/02_comparacion_misma_etiqueta.md`
  (pipeline de fable con etiqueta mensual; comparación sobre vehículos-mes comunes).
- `config/params.json`: `km_by_generation` corregido a 16.000 / 10.000; nuevo `label_mode` (`ventana` | `mes_calendario`).
- Fuentes oficiales consultadas el 15/09/2026: ford.com.ar/posventa/mantenimiento-garantia/nueva-ranger/ranger-2-0-l-diesel
  ("revisión de 16.000 km ó 12 meses"; descuentos por continuidad 5/10/15 %) y el manual de garantía Ranger T6 2016
  ("Programa de mantenimiento Ford 10.000 km ó 1 año", p. 18 y tablas de p. 24/26/28). Verificadas además en la misma
  fecha (snapshots Playwright en `.playwright-mcp/`): `nueva-ranger/ranger-3-0-l-v6-diesel` y
  `nueva-ranger/ranger-raptor-3-0-l-v6-nafta` (16.000 km ó 12 meses, lo que cierra la duda sobre la Raptor P703);
  `ranger-raptor`, `ranger/ranger-3-2-l-diesel`, `ranger/ranger-2-l-diesel` y `ranger/ranger-2012-2016-3-2-l-diesel`
  (10.000 km ó 12 meses).
- Verificación independiente (cuatro revisores escépticos con código propio): `scripts/revision_cruzada/verif_*.py` →
  `reports/revision_cruzada/verif_reconciliacion.md`, `verif_codigo_astra.md`, `verif_artefacto_y_comparacion.md` y
  `verif_fuentes_y_correccion_k.md`. Veredictos consolidados en el Anexo B.

---

## Anexo B — Verificación independiente

Cuatro revisores escépticos recalcularon con código propio las afirmaciones de este documento (bloques: reconciliación
de definiciones, lectura del código de astra, artefacto de calendario y comparación de modelos, fuentes y corrección de
K). El consolidador resolvió las discrepancias volviendo a correr `01_reconciliacion_definiciones.py` sobre el parquet
actual y repitiendo el bootstrap por cliente sobre los vehículos-mes comunes (`scripts/revision_cruzada/verif_consolidacion.py`
→ `reports/revision_cruzada/verif_consolidacion.md`). Resultado: 20 afirmaciones confirmadas, 12 ajustadas, 2 refutadas
y 2 no verificadas; ninguna refutación toca la conclusión de fondo (misma población, dos relojes; el horizonte mensual
mide tardanza, no abandono). Todas las correcciones están incorporadas al texto.

| # | Afirmación (dónde estaba) | Veredicto | Original | Recalculado | Fuente |
|---|---|---|---|---|---|
| 1 | Etiqueta mensual de astra sobre las ventanas de fable, abr-jul 2026 (§0.2, §1.2) | ajustada | 80,2 % (n = 26.871) | 79,0 % (n = 25.829); 82,1 % con la regla completa de astra (mismo `customer_id`). El 80,2 % era del parquet con K = 15.000 | verif_reconciliacion (a); 01 regenerado |
| 2 | Etiqueta de fable sobre las ventanas de astra (§0.2, §1.2) | confirmada | 44,0 % (n = 107.557) | 44,0 % (107.557; 107.713 con el vencimiento normalizado a día); 43,7 % con checkout o con eventos de astra. Salvedad: condicionado a no haber vuelto antes del 1°; el equivalente en fable es 45,7 % | verif_reconciliacion (b) |
| 3 | % de churn mensuales que completan antes de vencimiento + 90 (§0.3, §1.2, §2.2.1) | ajustada | 41,3 % (abr-jul) | 40,5 % sobre anclas de fable (vencimientos abr-may; 39,9 % con el margen de 30 d); 42,9-44,2 % sobre los churn reales de astra | verif_reconciliacion (c); 01 regenerado |
| 4 | Exigir el mismo `customer_id` suma 3,1 puntos de churn (§0.7, §1.2, §4.5) | confirmada, redacción ajustada | "3,1 % de sus churn" | 3,11 puntos (3,19 en test) = 3,1 % de las ventanas = 4,0 % de los churn; etiquetas de astra reproducidas al 100 %; sólo 19,4 % de esos ids ya había estado en el vehículo | verif_reconciliacion (d); verif_codigo_astra (b) |
| 5 | Solapamiento de poblaciones y diferencia de vencimiento (§1.1) | ajustada | 92.838 / 76.830 en común; mediana −7 d "por el 15.000" | 92.326 / 76.713 (98,4 % de astra); −1 d cruzando por vehículo (n = 21.277); 0 d por la misma ancla (n = 16.993); −65 d en el primer service | verif_reconciliacion (e); 01 regenerado |
| 6 | Fable abr-jul con su propia etiqueta (tabla §1.2) | ajustada | 46,5 % (n = 12.186) | 46,6 % (n = 11.755) | verif_reconciliacion; 01 regenerado |
| 7 | `maintenance` de astra incluye *Guarantee*: 3.808 turnos; 225.479 vs 220.522 (§0.7, §1.2, §2.2.2) | ajustada | 3.808; +4.957 | 3.777 contados (31 sin VIN; 20 son "Contactless"); a nivel turno 225.479 vs 221.703 (+3.776); 220.522 es a nivel vehículo-día | verif_codigo_astra (a) |
| 8 | Retorno exige el mismo `customer_id`; anónimo → NaN; agosto sin etiqueta (§1.1) | confirmada | — | `target` reproducido al 100 % en 132.869 ventanas; 129 NaN por anonimato; 6.285 de agosto sin etiqueta | verif_codigo_astra (b) |
| 9 | Horizonte [scoring, 1° del mes siguiente); mediana 14 d tras vencer (§0.1, §1.1) | confirmada | 14 (rango 0-30) | 14 (rango 0-31); 18,1 % del test con menos de 5 d | verif_codigo_astra (c) |
| 10 | Exigir checkout válido no pierde eventos (§2.2) | confirmada | 0 / 1 | 0 / 1 con ambas definiciones. Salvedad: la fecha de checkout sí mueve etiquetas (1.184 churn entraron al taller dentro del mes; 1.084 "retornos" ya estaban en el taller el 1°) | verif_codigo_astra (d) |
| 11 | Primer ciclo anclado en entrega + 1 año sin odómetro (§1.1, §2.2.4) | confirmada | — | 100 % de las 12.933 sin odómetro; 29 % con odómetro de otra visita vence antes; test 3.562, churn 0,784 | verif_codigo_astra (e) |
| 12 | `meses_observables` constante por mes y fuera de rango en test (§2.2.6) | confirmada | 27-30 vs ≤ 20 | 26,97-29,96 vs 5,98-18,99; score idéntico al fijarla en 18,99: el modelo no extrapola | verif_codigo_astra (f) |
| 13 | Cada episodio entra una vez; preempción ≈ la de fable (§1.1) | ajustada | — | 0 duplicados; pero 12.596 (18,4 %) de los preemptados volvieron en [venc. − 30, venc.), y 3.573 episodios nunca se scorean (hallazgo nuevo) | verif_codigo_astra (g) |
| 14 | Artefacto de calendario 75,6 % → 81,7 % (§2.2.1, §4.6) | confirmada | "días 1-5" | 75,57 % / 81,67 %; el tramo es 0-5 días desde el 1° | verif_artefacto (1) |
| 15 | AUC de ordenar por días al vencimiento 0,538 (§2.2.1) | confirmada | 0,538 | 0,5383 | verif_artefacto (2) |
| 16 | Lift@10 % de la regla de calendario 1,053 (§2.2.1) | ajustada (leve) | 1,053 por mes | 1,0534 global (lo que hizo el script 01); 1,0526 por mes | verif_artefacto (3) |
| 17 | Spearman score de astra vs días al vencimiento 0,094 (§2.2.1) | confirmada | 0,094 | 0,0936; AUC de astra dentro de cada tramo 0,64-0,69 | verif_artefacto (4) |
| 18 | Fable con etiqueta mensual: 0,730 / 1,24 / n = 25.612 (§2.2.9, §4.1, §5) | confirmada | 0,730 / 1,240 | 0,7295 / 1,2399 / 25.612 (determinista) | verif_artefacto (5) |
| 19 | Comparación justa: split sin leakage, misma capacidad, merge 1:1 (§2.2.9) | confirmada con salvedad | — | Sin leakage; ceil(10 %) por mes en ambos; merge 1:1 = 9.322. Salvedad: train fable 100.296 (ene-24..nov-25) vs astra 61.846 (jul-24..ago-25); comunes = 39 % / 36 % de cada test | verif_artefacto (6) |
| 20 | "Fable rinde mejor: 0,730 vs 0,673" (§0.4, §2.2.9) | ajustada | Δ 0,057 | Poblaciones distintas (no comunes de fable: AUC 0,732, 29 % primer service); brecha comparable +0,025 a +0,043 | verif_artefacto (7) |
| 21 | Sobre los 9.322 comunes, 0,689 vs 0,646 (§0.4, §2.2.9) | ajustada | Δ 0,043 | 0,689 vs 0,646 (etiq. fable) y 0,684 vs 0,659 (etiq. astra); IC95 bootstrap por cliente [+0,034, +0,054] y [+0,016, +0,035] (reproducido por el consolidador) | verif_artefacto (8); chequeo del consolidador |
| 22 | Fable supera a astra en lift@10 % (1,24 vs 1,20) (§0.4, §2.2.9, §4.2) | refutada | 1,24 vs 1,20 | Comunes: 1,270 vs 1,250 (etiq. fable) y 1,242 vs 1,237 (etiq. astra); IC95 de la diferencia [−0,009, +0,046] y [−0,014, +0,026]: incluye 0 | verif_artefacto (9); chequeo del consolidador |
| 23 | La ventaja no se explica por asimetrías; "las 86 features aportan" (§2.2.9) | ajustada | — | Con el período de astra Δ +0,032 / +0,017; sin dealer/TMA/zona/región/encuestas +0,019 / +0,003 con lift empatado | verif_artefacto (10) |
| 24 | Astra entrenó jul-24 a ago-25 (§2.2.8) | confirmada | — | 61.846 ventanas; valid oct-nov 25; calibración ene-feb 26; embargo; test 23.740 | verif_artefacto (11) |
| 25 | Ranger nueva (P703): 16.000 km ó 12 meses (§0.5, §1.3, Anexo) | confirmada | página 2.0L Diesel | Misma frase y tabs 16 → 160 mil en 2.0L, 3.0L V6 y Raptor 3.0 V6 (cierra la duda sobre la Raptor P703) | verif_fuentes (1) |
| 26 | Ranger anterior (P375): 10.000 km ó 1 año (§1.3, Anexo) | confirmada | manual 2016 | p. 18 y tablas p. 24/26/28; sitio "Ranger (Hasta 2023)" y Raptor anterior. Salvedad: `RANGER` sin sufijo (474 ventanas) toma 16.000 por default | verif_fuentes (2) |
| 27 | km/n 16.040-16.173 y Δkm 16.138 consistentes con 16.000 (§1.3) | confirmada | 16.040-16.173 / 16.138 | 16.041-16.173 / 16.140; los datos solos no fijan el nominal, lo zanja la fuente | verif_fuentes (3) |
| 28 | El vencimiento se corre ~15 d con K = 16.000 (§4.3) | ajustada | ~15 d | mediana 10 d (p25 7, p75 14); 12 d cuando manda la regla de km | verif_fuentes (4) |
| 29 | K = 16.000 → 142.558 / 41,6 % / test 19.704 / AUC 0,739 (§1.1, §3) | confirmada | — | Idéntico reconstruyendo las ventanas; AUC 0,7391 con sklearn; con K = 15.000: 145.538 / 20.191 / 0,736 | verif_fuentes (5) |
| 30 | Descuentos por continuidad 5/10/15 % (§2.1, §4.4) | confirmada, atribución corregida | "lo que fable no vio y astra sí" | Texto legal en las 7 páginas, vigencia 01-30/09/2026; ningún archivo de astra los menciona | verif_fuentes (6) |
| 31 | md y PDF sin "27.327" ni "enero y abril" (§3) | confirmada (literal) | 0 / 0 | 0 / 0 | verif_fuentes (7) |
| 32 | md y PDF regenerados con una sola corrida (§3) | refutada (PDF) / ajustada (md) | PDF = corrida final | PDF 20:38, anterior al parquet 20:50: sigue con 15.000 / 20.191 / 0,736 (60 de 83 cifras ausentes); md: 69 de 83 coinciden, quedan §6.4 y §11 desactualizadas | verif_fuentes (8, 9) |
| 33 | Sección 1 de este documento (cifras 80,2 / 41,3 / 92.838 / 76.830 / −7 d) | ajustada | corrida K = 15.000 | Reproducidas exactamente con K = 15.000; recalculadas sobre el parquet actual (filas 1, 3, 5, 6) | verif_reconciliacion (R); 01 regenerado |
| 34 | Fecha del evento check-in (fable) vs checkout (astra) no cambia la reconciliación (implícito en §1) | confirmada | — | Ningún resultado de §1 se mueve más de 0,3 puntos; checkout − fecha fable mediana 0 d, p90 6 d | verif_reconciliacion (extra) |
| 35 | Baseline de astra AUC 0,498; heurística de fable 0,61; lift 2,07 → 1,24; Spearman 0,68 entre scores (§2.2.7, §4.1, §4.2) | no verificada en esta vuelta | — | Fuera del alcance de los cuatro bloques (el 0,684 de Spearman sí aparece en el informe 02) | — |
| 36 | Su lift sube de 1,20 a 1,56 con horizonte de 90 d (§1.3, §2.2.1) | no verificada | — | Tomado de los informes de astra; no recalculado | — |
