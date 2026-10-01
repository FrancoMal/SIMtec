"""Traduce los drivers del modelo ("antigüedad del vehículo (días) = 2,551 (↑ riesgo)") a frases en castellano
para alguien que no es data scientist. No cambia ningún valor: sólo lo expresa en unidades de negocio
(días -> años o meses, km/día -> km por año) y dice si ese motivo sube o baja el riesgo."""
from __future__ import annotations

import re


def _valor(texto: str) -> tuple[str, bool]:
    """('2,551', True) desde 'nombre = 2,551 (↑ riesgo)'. True = sube el riesgo."""
    m = re.match(r"^(.*?)=\s*(.*?)\s*\((↑|↓) riesgo\)\s*$", str(texto))
    if not m:
        return str(texto), True
    return m.group(2), m.group(3) == "↑"


def _num(v: str) -> float | None:
    try:
        return float(v.replace(",", ""))
    except ValueError:
        return None


def _f(x: float, dec: int = 0) -> str:
    return f"{x:,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def motivo(feature: str, texto: str) -> str:
    """Frase en castellano para un driver. Si la variable no tiene traducción propia, usa su nombre en castellano."""
    v, sube = _valor(texto)
    n = _num(v)
    efecto = "Esto aumenta el riesgo." if sube else "Esto lo protege."
    nombre = re.sub(r"\s*\([^)]*\)", "", str(texto).split("=")[0]).strip()  # sin unidades entre paréntesis
    if v.lower().startswith("sin registro"):
        return f"No tiene registro previo en un concesionario oficial ({nombre}). {efecto}"
    if v.lower().startswith("sin dato") or v.lower() in ("nan", "none", ""):
        return f"Falta el dato de {nombre}: el modelo trata esa ausencia como una señal. {efecto}"
    t = {
        "vehicle_age_days": lambda: f"La camioneta tiene {_f(n / 365.25, 1)} años. " + (
            "A esa edad, más clientes dejan los concesionarios oficiales." if sube else "Es joven: a esa edad los clientes suelen volver."),
        "maint_per_year_observed": lambda: f"Viene {_f(n, 1)} veces por año al service. " + (
            "Es poco para lo que la usa." if sube else "Es un cliente regular."),
        "last_interval_days": lambda: f"Entre sus dos últimos services pasaron {_f(n / 30.44)} meses. " + efecto,
        "mean_interval_days": lambda: f"En promedio pasan {_f(n / 30.44)} meses entre sus services. " + efecto,
        "std_interval_days": lambda: f"Sus visitas son {'irregulares' if sube else 'regulares'} (varían unos {_f(n)} días). " + efecto,
        "km_rate_per_day": lambda: f"La usa mucho: unos {_f(n * 365.25)} km por año. " + efecto if sube else
                                   f"Hace unos {_f(n * 365.25)} km por año. " + efecto,
        "last_maint_km_vs_plan": lambda: (f"Llegó a su último service {_f(abs(n))} km {'después' if n > 0 else 'antes'} de lo que indica el plan. " + efecto),
        "last_interval_km_vs_k": lambda: f"Su último intervalo entre services fue {_f(n, 1)} veces el del plan. " + efecto,
        "months_observable": lambda: f"Lo vemos en la agenda desde hace {_f(n)} meses. " + efecto,
        "fleet_size_sales": lambda: (f"Es una flota de {_f(n)} vehículos: las flotas entran menos a los concesionarios oficiales. " if n and n > 1
                                     else "Es un cliente particular (una sola unidad comprada). ") + efecto,
        "n_vehicles_customer_agenda": lambda: f"El cliente tiene {_f(n)} vehículos en la agenda. " + efecto,
        "last_maint_dealer": lambda: ("En su concesionario, históricamente vuelven menos clientes." if sube
                                      else "En su concesionario, históricamente los clientes vuelven más."),
        "tma": lambda: f"Su versión ({v}) " + ("tiene históricamente más abandono." if sube else "tiene históricamente menos abandono."),
        "region": lambda: f"En su región ({v}) " + ("se vuelve menos al concesionario." if sube else "se vuelve más al concesionario."),
        "sales_state": lambda: f"Compró en {v}. " + efecto,
        "last_km": lambda: f"Su último kilometraje registrado es {_f(n)} km. " + efecto,
        "days_since_last_appt": lambda: f"Su último turno fue hace {_f(n / 30.44)} meses. " + efecto,
        "days_since_last_maint": lambda: f"Su último service fue hace {_f(n / 30.44)} meses. " + efecto,
        "days_since_last_visit": lambda: f"Su última visita al concesionario fue hace {_f(n / 30.44)} meses. " + efecto,
        "n_completed": lambda: f"Completó {_f(n)} visitas en concesionarios oficiales. " + efecto,
        "fordpass_share": lambda: f"Reserva {_f(n * 100)} % de sus turnos por FordPass. " + efecto,
    }
    if feature in t and (n is not None or feature in ("last_maint_dealer", "tma", "region", "sales_state")):
        try:
            return t[feature]()
        except (TypeError, ValueError):
            pass
    nombre = str(texto).split("=")[0].strip()
    nombre = nombre[:1].upper() + nombre[1:]
    return f"{nombre}: {v}. {efecto}"


ACCION = {
    "Alto": "Contacto personal del asesor en las próximas 48 horas, con el beneficio de continuidad que Ford ya ofrece.",
    "Medio": "Recordatorio personalizado por FordPass o WhatsApp, con un turno sugerido.",
    "Bajo": "Recordatorio automático de siempre: no hace falta gastar un contacto personal.",
}
