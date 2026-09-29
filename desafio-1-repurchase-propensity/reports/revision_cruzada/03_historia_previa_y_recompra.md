# Historia previa a 2024 y recompra observable

## 1. Fuentes
Archivos en la carpeta compartida: 3 (ventas CSV, agenda CSV, ficha técnica docx). No hay CRM, DMS, campañas, web ni telemetría.

## 2. Qué hay antes de 2024
Agenda: turnos con ScheduleDate < 2024-01-01: 0 de 492,442 turnos. Check-ins con fecha < 2024: 4 filas (errores de carga: 2001 y 2023). Ventas con SalesDate < 2024: 0 de 59,384.
Vehículos en agenda: 111,752; con inicio de garantía anterior a 2024: 66,795 (59.8%); con garantía anterior a 2023: 46,629; con garantía anterior a 2020: 23,663. Sin garantía informada: 1,257.
Ventas 2024-26 cuyo vehículo NO aparece en la agenda: 17,173 de 59,384.

Vehículos con garantía anterior a 2024 y al menos un mantenimiento en 2024-26: 48,822. Número de service del PRIMER mantenimiento observado: 1° → 11,284 (23.1%); 2°-5° → 19,104 (39.1%); 6° o más → 18,434 (37.8%); sin número → 0.
De esos, con más de 2 años de antigüedad al primer mantenimiento observado: 26,260; de ellos el 98.1% arranca con un service numerado ≥ 2° (evidencia de services previos en el plan).
Vehículos con garantía anterior a 2024 que aparecen en la agenda pero SIN ningún mantenimiento completado en 2024-26: 17,973 (sólo diagnósticos, campañas, cancelaciones o no-shows).
Clientes (customer_id) en agenda: 104,524; cuyos vehículos son TODOS anteriores a 2024: 60,183 (57.6%). Para ellos no hay ningún evento propio antes de 2024: sólo se sabe que poseen un Ford entregado antes.

## 3. Recompra observable
Ventas: 59,384 vehículos, 45,959 compradores; con ≥2 vehículos: 3,534 (7.7%), que compran 16,959 vehículos. Por tipo: F (físicas) 1,139, J (jurídicas) 2,374, otros 21.
Con compras separadas ≥ 90 días (compra secuencial, no flota simultánea): 2,225 compradores; personas físicas: 934; separadas ≥ 365 días: 1,359.
Compradores con exactamente 2 vehículos: 2,349; 3-9: 1,011; 10 o más: 174 (máximo 1,149).

Recompra por cruce agenda→ventas: ventas 2024-26 cuyo comprador ya había pasado por la agenda con OTRO Ranger (entregado al menos un año antes) antes de la fecha de compra: 12,239 ventas (20.6%), 6,192 compradores; personas físicas: 4,389.
Dueños de Ranger anteriores a 2024 vistos en la agenda: 67,006; de ellos compraron una Ranger 0 km en 2024-26 después de su primer turno: 5,523 (8.2%). Es una tasa base de recompra observable, sólo Ranger→Ranger y sólo dentro de 2024-26.
Por año del primer turno observado (menos seguimiento en 2026):
|    y |   size |   mean |
|-----:|-------:|-------:|
| 2023 |      2 |  0.5   |
| 2024 |  48430 |  0.107 |
| 2025 |  13396 |  0.024 |
| 2026 |   5178 |  0.004 |