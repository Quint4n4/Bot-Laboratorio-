"""Versión legible en español de un recurrence_rule. Espejo de bot-agenda/recurrence.py."""


def describe_rule(rule: str) -> str:
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
