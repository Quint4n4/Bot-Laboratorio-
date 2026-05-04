"""
recurrence.py - Motor de recurrencia para eventos
Calcula la siguiente ocurrencia de un evento dado su recurrence_rule.

Formatos soportados (simples, fáciles de generar por GPT):
- "daily"                  → cada día misma hora
- "weekly:MO"              → cada lunes
- "weekly:MO,WE,FR"        → lunes, miércoles y viernes
- "monthly:7"              → cada mes el día 7
- "yearly"                 → mismo día año tras año

Cualquier valor desconocido devuelve None (sin recurrencia válida).
"""
from datetime import datetime, timedelta
import calendar


_DOW_MAP = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}


def next_occurrence(rule: str, current: datetime) -> datetime | None:
    """
    Devuelve la siguiente ocurrencia de un evento DESPUÉS de `current` según `rule`.
    Mantiene la hora del día (HH:MM:SS) idéntica.
    """
    if not rule:
        return None
    rule = rule.strip().lower()

    # ── DAILY ──────────────────────────────────────────────
    if rule == "daily":
        return current + timedelta(days=1)

    # ── WEEKLY:DAYS ────────────────────────────────────────
    if rule.startswith("weekly:"):
        days_str = rule.split(":", 1)[1].upper()
        target_dows = [_DOW_MAP[d.strip()] for d in days_str.split(",") if d.strip() in _DOW_MAP]
        if not target_dows:
            return None
        # Buscar el siguiente día (de 1 a 7 días adelante) que coincida
        for delta in range(1, 8):
            candidate = current + timedelta(days=delta)
            if candidate.weekday() in target_dows:
                return candidate
        return None

    # ── MONTHLY:DAY ────────────────────────────────────────
    if rule.startswith("monthly:"):
        try:
            day = int(rule.split(":", 1)[1])
        except ValueError:
            return None
        if not (1 <= day <= 31):
            return None
        # Avanzar al mes siguiente
        year = current.year
        month = current.month + 1
        if month > 12:
            month = 1
            year += 1
        # Si el día no existe en ese mes (ej. 31 en febrero), usar el último día
        last_day = calendar.monthrange(year, month)[1]
        actual_day = min(day, last_day)
        return current.replace(year=year, month=month, day=actual_day)

    # ── YEARLY ─────────────────────────────────────────────
    if rule == "yearly":
        try:
            return current.replace(year=current.year + 1)
        except ValueError:
            # Caso 29 de febrero en año no bisiesto
            return current.replace(year=current.year + 1, day=28)

    return None


def describe_rule(rule: str) -> str:
    """Versión legible en español de un recurrence_rule (para mostrarle al usuario)."""
    if not rule:
        return ""
    rule = rule.strip().lower()
    if rule == "daily":
        return "todos los días"
    if rule.startswith("weekly:"):
        spanish = {"MO": "lunes", "TU": "martes", "WE": "miércoles",
                   "TH": "jueves", "FR": "viernes", "SA": "sábado", "SU": "domingo"}
        days = rule.split(":", 1)[1].upper().split(",")
        names = [spanish.get(d.strip(), d) for d in days]
        if len(names) == 1:
            return f"cada {names[0]}"
        return "cada " + ", ".join(names[:-1]) + f" y {names[-1]}"
    if rule.startswith("monthly:"):
        day = rule.split(":", 1)[1]
        return f"cada día {day} del mes"
    if rule == "yearly":
        return "una vez al año"
    return rule
