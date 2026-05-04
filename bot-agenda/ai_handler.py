"""
ai_handler.py - Cerebro del bot: LLM, Function Calling y Tool Calling
Agenda Bot - Asistente Personal
"""
import json
import os
from datetime import datetime, timedelta, timezone as dt_timezone
from zoneinfo import ZoneInfo

from openai import OpenAI
from sqlalchemy.orm import Session
from database import Event, User, EventType, EventStatus, Message

# Strip defensivo por si la API key viene con \n o comillas accidentales
_OPENAI_KEY = os.getenv("OPENAI_API_KEY", "").strip().strip('"').strip("'")
client = OpenAI(api_key=_OPENAI_KEY)


# ---------------------------------------------------------------------------
# Configuración de memoria conversacional
# ---------------------------------------------------------------------------
HISTORY_LIMIT = 20   # Máximo de mensajes (user+assistant) que se mantienen
                     # como contexto. Suficiente para conversaciones multi-turno
                     # sin inflar tokens.


# ---------------------------------------------------------------------------
# HELPER: Convertir hora local del usuario a UTC para guardar en BD
# ---------------------------------------------------------------------------
def _local_to_utc(iso_str: str, tz: ZoneInfo) -> datetime:
    """
    Convierte un string ISO 8601 sin timezone (generado por el LLM en hora local)
    a datetime UTC para almacenar en la base de datos.
    """
    naive = datetime.fromisoformat(iso_str)
    # Interpretar como hora local del usuario
    local_dt = naive.replace(tzinfo=tz)
    # Convertir a UTC
    return local_dt.astimezone(dt_timezone.utc).replace(tzinfo=None)


# ---------------------------------------------------------------------------
# HERRAMIENTAS (Tools) que el LLM puede ejecutar
# ---------------------------------------------------------------------------
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_event",
            "description": (
                "Crea un recordatorio, tarea o cita en la agenda del usuario. "
                "SIEMPRE verifica conflictos de horario antes de crear el evento. "
                "Si hay un evento en el mismo horario, informa al usuario y pregunta si desea continuar."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title":           {"type": "string",  "description": "Título corto del evento en español"},
                    "event_type":      {"type": "string",  "enum": ["reminder", "meeting", "task"]},
                    "start_datetime":  {"type": "string",  "description": "Hora local del usuario en ISO 8601 (sin timezone). Ejemplo: 2026-04-22T16:00:00"},
                    "end_datetime":    {"type": "string",  "description": "Hora local fin, ISO 8601. Solo para meetings."},
                    "all_day":         {"type": "boolean", "description": "True si el evento es de todo el día"},
                    "description":     {"type": "string",  "description": "Detalle opcional"},
                    "location":        {"type": "string",  "description": "Lugar fisico (direccion) o link de videollamada (Zoom, Meet, etc.)"},
                    "recurrence_rule": {"type": "string",  "description": "Si el evento se repite. Formatos: 'daily', 'weekly:MO,WE,FR', 'weekly:MO', 'monthly:7' (cada dia 7 del mes), 'yearly'. Ejemplo: 'todos los lunes a las 9' = 'weekly:MO'; 'cada dia 7 del mes pagar internet' = 'monthly:7'"},
                    "attendees":       {"type": "string",  "description": "Nombres o emails de otros participantes separados por coma. Ejemplo: 'Pedro, Maria'"},
                    "tags":            {"type": "string",  "description": "Etiquetas libres adicionales separadas por coma. Ejemplo: 'proyecto-alpha,urgente'. NO uses tags para categorias generales (eso es 'category')"},
                    "category":        {"type": "string",  "enum": ["personal", "trabajo", "salud", "finanzas", "familia", "social", "otros"], "description": "Categoria principal del evento. Inferela del contexto: 'pagar internet' = finanzas, 'cita medico' = salud, 'reporte al jefe' = trabajo, 'cumpleanos mama' = familia."},
                    "force":           {"type": "boolean", "description": "Si es True, crea el evento aunque haya conflicto"},
                },
                "required": ["title", "event_type", "start_datetime"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_event",
            "description": "Reagenda o modifica un evento existente.",
            "parameters": {
                "type": "object",
                "properties": {
                    "event_id":            {"type": "integer", "description": "ID del evento a modificar"},
                    "new_start":           {"type": "string",  "description": "Nueva fecha/hora inicio ISO 8601 en hora local"},
                    "new_end":             {"type": "string",  "description": "Nueva fecha/hora fin ISO 8601 en hora local"},
                    "new_title":           {"type": "string",  "description": "Nuevo título"},
                    "new_description":     {"type": "string",  "description": "Nuevo detalle"},
                    "new_location":        {"type": "string",  "description": "Nuevo lugar o link"},
                    "new_recurrence_rule": {"type": "string",  "description": "Nueva regla de recurrencia (o cadena vacia para quitar)"},
                    "new_attendees":       {"type": "string",  "description": "Nueva lista de participantes (CSV)"},
                    "new_tags":            {"type": "string",  "description": "Nuevos tags libres (CSV)"},
                    "new_category":        {"type": "string",  "enum": ["personal", "trabajo", "salud", "finanzas", "familia", "social", "otros"], "description": "Nueva categoria"},
                },
                "required": ["event_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "cancel_event",
            "description": "Cancela o elimina un evento de la agenda.",
            "parameters": {
                "type": "object",
                "properties": {
                    "event_id": {"type": "integer", "description": "ID del evento a cancelar"},
                },
                "required": ["event_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "complete_event",
            "description": "Marca un evento o tarea como completado.",
            "parameters": {
                "type": "object",
                "properties": {
                    "event_id": {"type": "integer"},
                },
                "required": ["event_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "snooze_event",
            "description": "Pospone un recordatorio X minutos.",
            "parameters": {
                "type": "object",
                "properties": {
                    "event_id": {"type": "integer"},
                    "minutes":  {"type": "integer", "description": "Minutos a posponer"},
                },
                "required": ["event_id", "minutes"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_agenda",
            "description": "Consulta los eventos pendientes del usuario en un rango de fechas.",
            "parameters": {
                "type": "object",
                "properties": {
                    "from_date": {"type": "string", "description": "Fecha inicio en hora local ISO 8601"},
                    "to_date":   {"type": "string", "description": "Fecha fin en hora local ISO 8601"},
                },
                "required": ["from_date", "to_date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_report",
            "description": "Genera datos para un reporte de productividad (daily, weekly, monthly).",
            "parameters": {
                "type": "object",
                "properties": {
                    "period": {"type": "string", "enum": ["daily", "weekly", "monthly"]},
                },
                "required": ["period"],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# HELPERS INTERNOS
# ---------------------------------------------------------------------------

def _check_conflicts(start_utc: datetime, end_utc: datetime, user_id: str, db: Session, exclude_id: int = None):
    """
    Verifica si hay eventos activos en el rango dado.
    Retorna lista de eventos en conflicto.
    """
    q = db.query(Event).filter(
        Event.user_telegram_id == user_id,
        Event.status == EventStatus.pending,
        Event.start_datetime < end_utc,
        (Event.end_datetime == None) | (Event.end_datetime > start_utc),
    )
    if exclude_id:
        q = q.filter(Event.id != exclude_id)
    # Para recordatorios sin end, comparar inicio exacto con margen de 15 min
    conflicts = []
    for ev in q.all():
        ev_end = ev.end_datetime or (ev.start_datetime + timedelta(minutes=15))
        if ev.start_datetime < end_utc and ev_end > start_utc:
            conflicts.append(ev)
    return conflicts


def _fmt_local(utc_dt: datetime, tz: ZoneInfo) -> str:
    """Formatea un datetime UTC a hora local incluyendo la fecha."""
    local = utc_dt.replace(tzinfo=dt_timezone.utc).astimezone(tz)
    return local.strftime("%Y-%m-%d %I:%M %p")


# ---------------------------------------------------------------------------
# EJECUTORES DE TOOLS
# ---------------------------------------------------------------------------

def _exec_create_event(args: dict, user_id: str, db: Session, tz: ZoneInfo) -> dict:
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"CREATE_EVENT args: {args}")
    try:
        start_utc = _local_to_utc(args["start_datetime"], tz)
        end_utc   = _local_to_utc(args["end_datetime"], tz) if args.get("end_datetime") else start_utc + timedelta(minutes=30)
        force     = args.get("force", False)
        logger.info(f"CREATE_EVENT start_utc={start_utc} end_utc={end_utc}")

        # Detección de conflictos (a menos que force=True)
        if not force:
            try:
                conflicts = _check_conflicts(start_utc, end_utc, user_id, db)
            except Exception as ce:
                logger.error(f"Error en _check_conflicts: {ce}", exc_info=True)
                conflicts = []  # Si falla la verificación, continuar sin conflictos

            if conflicts:
                conflict_info = [
                    {"id": c.id, "title": c.title, "start": _fmt_local(c.start_datetime, tz)}
                    for c in conflicts
                ]
                return {
                    "ok": False,
                    "conflict": True,
                    "message": "Hay uno o más eventos en ese horario.",
                    "conflicting_events": conflict_info,
                }

        event = Event(
            user_telegram_id=user_id,
            title=args["title"],
            event_type=args.get("event_type", "reminder"),
            description=args.get("description"),
            start_datetime=start_utc,
            end_datetime=_local_to_utc(args["end_datetime"], tz) if args.get("end_datetime") else None,
            all_day=args.get("all_day", False),
            location=args.get("location"),
            recurrence_rule=args.get("recurrence_rule"),
            attendees=args.get("attendees"),
            tags=args.get("tags"),
            category=args.get("category", "otros"),
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        logger.info(f"CREATE_EVENT OK id={event.id} titulo='{event.title}' utc={event.start_datetime}")
        return {
            "ok": True,
            "event_id": event.id,
            "title": event.title,
            "start_utc": str(event.start_datetime),
            "start_local": _fmt_local(event.start_datetime, tz),
        }
    except Exception as e:
        import logging as _log
        _log.getLogger(__name__).error(f"ERROR en _exec_create_event: {e}", exc_info=True)
        return {"ok": False, "error": str(e)}


def _exec_update_event(args: dict, db: Session, tz: ZoneInfo) -> dict:
    event = db.query(Event).filter(Event.id == args["event_id"]).first()
    if not event:
        return {"ok": False, "error": "Evento no encontrado"}
    
    new_start_utc = _local_to_utc(args["new_start"], tz) if args.get("new_start") else event.start_datetime
    new_end_utc   = _local_to_utc(args["new_end"], tz) if args.get("new_end") else (event.end_datetime if event.end_datetime else new_start_utc + timedelta(minutes=30))
    force         = args.get("force", False)

    # Solo checar conflictos si realmente esta cambiando el horario
    if args.get("new_start") or args.get("new_end"):
        if not force:
            try:
                conflicts = _check_conflicts(new_start_utc, new_end_utc, event.user_telegram_id, db)
                # Ignorar el mismo evento siendo actualizado
                conflicts = [c for c in conflicts if c.id != event.id]
            except Exception:
                conflicts = []

            if conflicts:
                conflict_info = [{"id": c.id, "title": c.title, "start": _fmt_local(c.start_datetime, tz)} for c in conflicts]
                return {
                    "ok": False,
                    "conflict": True,
                    "message": "Hay eventos que se empalman con este nuevo horario.",
                    "conflicting_events": conflict_info,
                }

    if args.get("new_start"):
        event.start_datetime = new_start_utc
    if args.get("new_end"):
        event.end_datetime = new_end_utc
    if args.get("new_title"):
        event.title = args["new_title"]
    if args.get("new_description"):
        event.description = args["new_description"]
    if "new_location" in args:
        event.location = args["new_location"] or None
    if "new_recurrence_rule" in args:
        event.recurrence_rule = args["new_recurrence_rule"] or None
    if "new_attendees" in args:
        event.attendees = args["new_attendees"] or None
    if "new_tags" in args:
        event.tags = args["new_tags"] or None
    if "new_category" in args:
        event.category = args["new_category"] or "otros"
    db.commit()
    return {"ok": True, "event_id": event.id}


def _exec_cancel_event(args: dict, db: Session) -> dict:
    event = db.query(Event).filter(Event.id == args["event_id"]).first()
    if not event:
        return {"ok": False, "error": "Evento no encontrado"}
    event.status = EventStatus.cancelled
    db.commit()
    return {"ok": True}


def _exec_complete_event(args: dict, db: Session) -> dict:
    event = db.query(Event).filter(Event.id == args["event_id"]).first()
    if not event:
        return {"ok": False, "error": "Evento no encontrado"}
    event.status = EventStatus.completed
    db.commit()
    return {"ok": True}


def _exec_snooze_event(args: dict, db: Session) -> dict:
    event = db.query(Event).filter(Event.id == args["event_id"]).first()
    if not event:
        return {"ok": False, "error": "Evento no encontrado"}
    event.start_datetime = event.start_datetime + timedelta(minutes=args["minutes"])
    event.status         = EventStatus.pending
    event.reminder_sent  = False
    event.followup_count = 0
    event.last_reminded_at = None
    db.commit()
    return {"ok": True, "new_time_utc": str(event.start_datetime)}


def _exec_query_agenda(args: dict, user_id: str, db: Session, tz: ZoneInfo) -> dict:
    start_utc = _local_to_utc(args["from_date"], tz)
    end_utc   = _local_to_utc(args["to_date"], tz)
    events = db.query(Event).filter(
        Event.user_telegram_id == user_id,
        Event.start_datetime >= start_utc,
        Event.start_datetime <= end_utc,
        Event.status != EventStatus.cancelled,
    ).order_by(Event.start_datetime).all()

    return {
        "events": [
            {
                "id": e.id,
                "title": e.title,
                "type": e.event_type,
                "start": _fmt_local(e.start_datetime, tz),
                "end": _fmt_local(e.end_datetime, tz) if e.end_datetime else None,
                "status": e.status,
                "location": e.location,
                "recurrence_rule": e.recurrence_rule,
                "attendees": e.attendees,
                "tags": e.tags,
                "category": e.category,
            }
            for e in events
        ]
    }


def _exec_generate_report(args: dict, user_id: str, db: Session) -> dict:
    """Usa rangos en UTC para que coincidan con los datos almacenados."""
    now    = datetime.utcnow()
    period = args["period"]
    if period == "daily":
        from_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        to_date   = now.replace(hour=23, minute=59, second=59)
    elif period == "weekly":
        from_date = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0)
        to_date   = from_date + timedelta(days=6, hours=23, minutes=59)
    else:
        from_date = now.replace(day=1, hour=0, minute=0, second=0)
        import calendar
        last_day  = calendar.monthrange(now.year, now.month)[1]
        to_date   = now.replace(day=last_day, hour=23, minute=59)

    events    = db.query(Event).filter(
        Event.user_telegram_id == user_id,
        Event.start_datetime >= from_date,
        Event.start_datetime <= to_date,
    ).all()

    completed = [e for e in events if e.status == EventStatus.completed]
    pending   = [e for e in events if e.status == EventStatus.pending]

    return {
        "period":    period,
        "total":     len(events),
        "completed": len(completed),
        "cancelled": len([e for e in events if e.status == EventStatus.cancelled]),
        "pending":   len(pending),
        "completed_list": [{"id": e.id, "title": e.title, "start": str(e.start_datetime)} for e in completed],
        "pending_list":   [{"id": e.id, "title": e.title, "start": str(e.start_datetime)} for e in pending],
    }


# ---------------------------------------------------------------------------
# DESPACHO DE TOOLS
# ---------------------------------------------------------------------------
def dispatch_tool(name: str, args: dict, user_id: str, db: Session, tz: ZoneInfo) -> str:
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"TOOL_CALL: {name} | args={args}")
    try:
        if name == "create_event":
            result = _exec_create_event(args, user_id, db, tz)
        elif name == "update_event":
            result = _exec_update_event(args, db, tz)
        elif name == "cancel_event":
            result = _exec_cancel_event(args, db)
        elif name == "complete_event":
            result = _exec_complete_event(args, db)
        elif name == "snooze_event":
            result = _exec_snooze_event(args, db)
        elif name == "query_agenda":
            result = _exec_query_agenda(args, user_id, db, tz)
        elif name == "generate_report":
            result = _exec_generate_report(args, user_id, db)
        else:
            result = {"error": f"Tool '{name}' no implementada"}
        logger.info(f"TOOL_RESULT: {name} -> {str(result)[:200]}")
    except Exception as e:
        logger.error(f"TOOL_ERROR en '{name}': {e}", exc_info=True)
        result = {"ok": False, "error": str(e)}
    return json.dumps(result, ensure_ascii=False)


# ---------------------------------------------------------------------------
# SYSTEM PROMPT ESTÁTICO
# Va al inicio del prompt para que OpenAI lo cachee. La fecha dinámica
# se inserta como mensaje aparte al final (no cacheable, pequeño).
# ---------------------------------------------------------------------------
_STATIC_SYSTEM_PROMPT = """Eres ARIA, asistente personal de agenda. Eres amable, directa y eficiente.

INSTRUCCION CRITICA: Para cualquier accion sobre la agenda (crear cita, recordatorio o tarea, consultar eventos, cancelar, reagendar, completar, generar reporte), DEBES usar SIEMPRE las herramientas disponibles. NUNCA respondas como si hubieras realizado una accion sin haber llamado la herramienta correspondiente.

REGLAS GENERALES:
1. Responde SIEMPRE en espanol. Sin palabras en ingles.
2. Cuando el usuario diga "en X minutos" calcula a partir de la FECHA Y HORA ACTUAL que se te indica abajo y suma X minutos.
3. Al confirmar una cita, di la hora en formato 12h (ej. 3:30 PM).
4. Cuando el usuario pregunte por su agenda, llama SIEMPRE a query_agenda primero.
5. NUNCA inventes ni asumas empalmes. LLAMA a create_event o update_event, y SOLO SI la herramienta retorna conflict=True, avisa al usuario y pregunta si forzar.
6. Usa el HISTORIAL DE CONVERSACION para entender referencias como "ese", "el de antes", "cancela el que te dije". Si el usuario empezo algo y vuelve, no le pidas que repita.

CATEGORIA (obligatoria al crear eventos):
Siempre incluye "category" al crear o editar un evento. Inferela del contexto:
- personal:  rutinas, hobbies, recordatorios genericos sin tema especifico
- trabajo:   reuniones laborales, deadlines, reportes, llamadas con clientes/jefe
- salud:     citas medicas, gym, nutricion, medicamentos
- finanzas:  pagos, transferencias, vencimientos, cobros, recibos (luz, internet, renta)
- familia:   cumpleanos, eventos familiares, llamadas con padres/hijos
- social:    salidas con amigos, fiestas, eventos publicos
- otros:     solo cuando ninguna otra encaje claramente
Ejemplos: "pagar internet" = finanzas | "cita con dentista" = salud |
"reporte al jefe" = trabajo | "cumple de mama" = familia | "cena con amigos" = social.

RECURRENCIA (cuando el usuario lo indica explicito):
Si el usuario dice "cada", "todos los", "siempre", agrega recurrence_rule:
- "cada dia 7 del mes pagar internet"  → recurrence_rule="monthly:7"
- "todos los lunes a las 9"            → recurrence_rule="weekly:MO"
- "lunes, miercoles y viernes"         → recurrence_rule="weekly:MO,WE,FR"
- "todos los dias"                     → recurrence_rule="daily"
- "cada ano el 15 de mayo"             → recurrence_rule="yearly"
NO inventes recurrencia si el usuario solo lo pidio una vez.

FORMATO start_datetime: ISO 8601 hora LOCAL sin timezone. Ej: 2026-04-22T16:00:00"""


# ---------------------------------------------------------------------------
# Memoria conversacional: cargar y guardar
# ---------------------------------------------------------------------------
def _load_history(user_id: str, db: Session, limit: int = HISTORY_LIMIT) -> list:
    """
    Carga los últimos `limit` mensajes (user+assistant) del usuario en orden
    cronológico (más antiguo primero), listos para concatenar en messages.
    """
    rows = (
        db.query(Message)
        .filter(Message.user_telegram_id == user_id)
        .order_by(Message.created_at.desc())
        .limit(limit)
        .all()
    )
    rows.reverse()  # cronológico ascendente para el prompt
    return [{"role": r.role, "content": r.content} for r in rows]


def _save_message(user_id: str, role: str, content: str, db: Session) -> None:
    """Guarda un mensaje en historial. Errores no fatales (memoria es nice-to-have)."""
    try:
        db.add(Message(user_telegram_id=user_id, role=role, content=content))
        db.commit()
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"No se pudo guardar el mensaje: {e}")
        db.rollback()


def reset_history(user_id: str, db: Session) -> int:
    """Borra todo el historial conversacional de un usuario. Devuelve cuántos borró."""
    n = db.query(Message).filter(Message.user_telegram_id == user_id).delete()
    db.commit()
    return n


# ---------------------------------------------------------------------------
# Modo proactivo: detectar patrones y sugerir mejoras al usuario
# ---------------------------------------------------------------------------
def analyze_patterns(user_id: str, db: Session) -> list[str]:
    """
    Analiza la actividad del usuario y devuelve una lista de sugerencias.
    Lista vacía = nada interesante que reportar.

    Patrones detectados (v1):
    - Eventos repetidos manualmente (>=3 veces en 90 días) que podrían ser recurrentes
    - Tareas pendientes desde hace >7 días (procrastinación)
    - Racha de productividad (>=70% completado en últimos 7 días)
    """
    suggestions = []
    now = datetime.utcnow()

    # ── Patrón 1: Eventos creados manualmente ≥3 veces en 90 días → sugerir recurrencia
    cutoff_90d = now - timedelta(days=90)
    eventos_recientes = db.query(Event).filter(
        Event.user_telegram_id == user_id,
        Event.created_at >= cutoff_90d,
        Event.recurrence_rule.is_(None),
    ).all()

    titulos_count: dict[str, int] = {}
    for e in eventos_recientes:
        key = e.title.strip().lower()
        titulos_count[key] = titulos_count.get(key, 0) + 1
    for titulo_lc, count in titulos_count.items():
        if count >= 3:
            # Recuperar el título original (con mayúsculas)
            original = next(
                (e.title for e in eventos_recientes if e.title.strip().lower() == titulo_lc),
                titulo_lc,
            )
            suggestions.append(
                f"💡 Has creado *{original}* {count} veces en los últimos 90 días. "
                f"¿Quieres que lo haga recurrente automáticamente?"
            )

    # ── Patrón 2: Tareas pendientes desde hace >7 días
    cutoff_7d = now - timedelta(days=7)
    stale = db.query(Event).filter(
        Event.user_telegram_id == user_id,
        Event.status == EventStatus.pending,
        Event.start_datetime < cutoff_7d,
    ).count()
    if stale >= 3:
        suggestions.append(
            f"⚠️ Tienes *{stale} tareas* pendientes desde hace más de una semana. "
            f"¿Las cancelamos o las reagendamos?"
        )

    # ── Patrón 3: Racha de productividad
    cutoff_recent = now - timedelta(days=7)
    last_week = db.query(Event).filter(
        Event.user_telegram_id == user_id,
        Event.start_datetime >= cutoff_recent,
        Event.start_datetime <= now,
    ).all()
    if len(last_week) >= 5:
        completados = sum(1 for e in last_week if e.status == EventStatus.completed)
        ratio = completados / len(last_week)
        if ratio >= 0.7:
            suggestions.append(
                f"🎉 ¡Excelente racha! Completaste *{completados} de {len(last_week)}* "
                f"eventos esta semana ({int(ratio * 100)}%)."
            )

    return suggestions


# ---------------------------------------------------------------------------
# FUNCIÓN PRINCIPAL: Procesar mensaje del usuario
# ---------------------------------------------------------------------------
def process_message(user_text: str, user_id: str, db: Session, timezone: str = "America/Mexico_City") -> str:
    """
    Procesa el texto del usuario con GPT-4o-mini + function calling.
    Mantiene memoria conversacional: carga los últimos HISTORY_LIMIT mensajes
    y guarda el nuevo intercambio al terminar.
    """
    tz      = ZoneInfo(timezone)
    now     = datetime.now(tz)
    now_str = now.strftime("%A, %d/%m/%Y %I:%M %p")

    print(f"[ARIA] process_message invocado: '{user_text[:60]}' | user={user_id} | tz={timezone}")

    # Mensaje dinámico pequeño con fecha/hora — va al final para no romper cache
    dynamic_context = f"FECHA Y HORA ACTUAL: {now_str} (zona horaria: {timezone}). " \
                      f"Si el usuario dice 'en X minutos', el start_datetime ISO 8601 es " \
                      f"{(now + timedelta(minutes=5)).strftime('%Y-%m-%dT%H:%M:%S')} para X=5."

    # Cargar historial conversacional
    history = _load_history(user_id, db)
    print(f"[ARIA] historial cargado: {len(history)} mensajes")

    # Estructura: system estático (cacheable) + historial + dynamic + nuevo user msg
    messages = [
        {"role": "system", "content": _STATIC_SYSTEM_PROMPT},
        *history,
        {"role": "system", "content": dynamic_context},
        {"role": "user",   "content": user_text},
    ]

    # Guardamos el mensaje del usuario en BD inmediatamente para que sobreviva
    # un crash en mitad del procesamiento.
    _save_message(user_id, "user", user_text, db)

    # ---------------------------------------------------------------------------
    # Bucle agéntico: el LLM puede hacer múltiples rondas de tool calls
    # ---------------------------------------------------------------------------
    MAX_ITERATIONS = 6
    final_text = ""
    for iteration in range(MAX_ITERATIONS):
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )
        msg = response.choices[0].message
        print(f"[ARIA] iter={iteration} tool_calls={bool(msg.tool_calls)} "
              f"content='{str(msg.content)[:60] if msg.content else None}'")

        # Log de cache hit (OpenAI lo expone en usage.prompt_tokens_details.cached_tokens)
        try:
            cached = response.usage.prompt_tokens_details.cached_tokens
            if cached:
                print(f"[ARIA] cache hit: {cached} tokens cacheados")
        except Exception:
            pass

        if not msg.tool_calls:
            final_text = msg.content or ""
            break

        # Ejecutar todas las herramientas que el LLM pidió
        messages.append(msg)
        for tool_call in msg.tool_calls:
            name   = tool_call.function.name
            args   = json.loads(tool_call.function.arguments)
            print(f"[ARIA] ejecutando tool: {name} | args={args}")
            result = dispatch_tool(name, args, user_id, db, tz)
            print(f"[ARIA] resultado {name}: {result[:120]}")
            messages.append({
                "role":         "tool",
                "tool_call_id": tool_call.id,
                "content":      result,
            })
    else:
        # Demasiadas iteraciones
        final_text = "Lo siento, tuve un problema procesando tu solicitud. Intenta de nuevo."

    # Guardar respuesta del asistente para que ARIA la "recuerde" en el siguiente turno
    if final_text:
        _save_message(user_id, "assistant", final_text, db)

    return final_text
