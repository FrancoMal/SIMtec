# Notas — reunión con el tutor (11/9/2026)

> Fuente: notas tomadas por Teo durante la interacción con el tutor del proyecto (nexo entre
> Ford y el equipo). Texto reordenado por tema para que sea legible, sin agregar interpretación
> propia — eso va en `SPEC.md`. Se conserva acá como registro primario de lo que dijo el tutor.

## Objetivo de negocio / framing

- Segmentar a los clientes en **3 tipos**.
- El proyecto se tiene que "vender" — no alcanza con el modelo, importa cómo se comunica.
- Idea de "recaptar al vendedor": reconectar al cliente con el concesionario/vendedor.
- Insight de negocio clave: a medida que pasan los años, el cliente deja de ir al service; al
  tercer año la curva de asistencia al service cae fuerte. Por la falta de servicios, el cliente
  percibe menor calidad del vehículo, y al percibir menor calidad se aleja de la marca.
- Si el cliente deja de ir a la concesionaria (por el motivo que sea), ahí se pierde la
  recompra — la visita a la concesionaria es el punto de contacto crítico.

## Sobre el dataset

- Todos los datos están **enmascarados** (anonimizados).
- Variables clave: **fecha del último service** y **kilometraje** → con esto se infiere el
  patrón de uso del cliente y cuándo le correspondería el próximo service.
- El dataset detalla **varios motivos** por los que un cliente entra al service (no es un único
  motivo).
- Hay un campo **`schedule_id`** (o similar) que es importante — probablemente identifica el
  service programado/agendado.
- Ciclo de service típico: **cada 15.000 km o 1 año** (lo que ocurra primero).
- Hay que poder identificar si el cliente que va al service **es el mismo que compró el auto**
  originalmente (o no).
- Caso de **transferencia de titularidad**: el cliente que compró le transfiere el auto a un
  nuevo dueño. Si ese nuevo dueño acepta los términos y consiente compartir sus datos, "vuelve a
  la rueda" (vuelve a entrar como cliente activo en el sistema/dataset).
- Buscar patrones cruzando los datos disponibles; también influyen factores no capturados
  directamente en el dataset como la psicología del comprador y la situación económica general.

## Reframing del target (importante)

- Lo que más importa predecir es la **probabilidad de que el cliente NO vaya al service** cuando
  le corresponde — no solo "va a recomprar sí/no".
- El timing importa: **ni antes ni después** de cuando le toca el service según su patrón de uso.
- Si el cliente no va al service en la ventana que le corresponde, pierde satisfacción, y eso es
  lo que hace que después no vuelva a comprar.
- Horizonte de predicción sugerido: **el próximo mes** (predicción de corto plazo, no a años).
- Con el patrón de uso (fecha de último service + kilometraje) se puede clasificar a cada cliente
  en los 3 tipos de segmento mencionados arriba.

## Cómo se va a evaluar el modelo

- Se va a evaluar con **backtesting**, midiendo el **lift** de los modelos.
- Criterio de éxito: el modelo funciona si lo que predice está acorde con lo que efectivamente
  pasó en la realidad (validación contra datos históricos).

## Idea de intervención (para diferenciarse)

- Pensar un "agente" que, en base a los patrones de uso reconocidos, permita mejorar el
  porcentaje de recompra — por ejemplo: si se contacta a un grupo específico de clientes, ver si
  se puede subir cierto porcentaje de asistencia/recompra. (Esto es, en esencia, la misma idea de
  uplift modeling que ya estaba en `SPEC.md` §6, ahora confirmada como algo que le interesa al
  tutor.)
- El objetivo final es **incentivar al comprador a ir al service**, identificando proactivamente
  cuándo le toca, para mejorar su experiencia y así favorecer que vuelva a comprar.

## Entregables mencionados

- Documento.
- Dashboard.
- Notebook.
- Presentación.

(Consistente con lo que ya se sabía por el reglamento: PDF final + demo/dashboard + presentación
en el Trials Day.)
