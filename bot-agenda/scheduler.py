"""
scheduler.py - Motor de tareas en segundo plano (APScheduler)
Agenda Bot - Asistente Personal
"""
import asyncio
import logging
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session

from database import Event, User, EventStatus, SessionLocal
from pdf_generator import generate_daily_briefing, generate_evening_wrapup

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

# Se inyecta globalmente la instancia del bot de Telegram
_bot_instance = None

def set_bot(bot):
    global _bot_instance
    _bot_instance = bot


# ---------------------------------------------------------------------------
# REVISAR RECORDATORIOS PENDIENTES (cada 30 segundos)
# ---------------------------------------------------------------------------

FOLLOWUP_MESSAGES = [
    "Oye, ¡aún tienes esto pendiente! 👆 No lo olvides.",
    "¡Eh! Todavía espero que completes esta tarea. 😤",
    "Sigo aquí... tu tarea sigue pendiente. ¿La atiendes? 📌",
    "¡Insisto! Esta tarea no se va a completar sola. 😅",
    "Llevas un rato ignorándome. ¿Quieres posponerla o ya la completaste? 🙏",
    "Última llamada por ahora: esta tarea sigue abierta. ¡Avísame cuando la hagas! ⏰",
]

async def check_due_reminders():
    """Revisa la BD y envía recordatorios cuya hora ya llegó (UTC)."""
    if not _bot_instance:
        return

    db: Session = SessionLocal()
    try:
        now_utc = datetime.utcnow()

        # 1. Recordatorios nuevos cuya hora ya llegó
        due_events = db.query(Event).filter(
            Event.start_datetime <= now_utc,
            Event.status == EventStatus.pending,
            Event.reminder_sent == False,
        ).all()

        for event in due_events:
            user = db.query(User).filter(User.telegram_id == event.user_telegram_id).first()
            if not user:
                continue

            tipo_icon = {"reminder": "⏰", "meeting": "📅", "task": "✅"}.get(event.event_type, "📌")
            text = f"{tipo_icon} *Recordatorio:* {event.title}"
            if event.description:
                text += f"\n_{event.description}_"

            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Listo",   callback_data=f"complete:{event.id}"),
                InlineKeyboardButton("⏰ +15 min", callback_data=f"snooze15:{event.id}"),
                InlineKeyboardButton("❌ Cancelar",callback_data=f"cancel:{event.id}"),
            ]])

            await _bot_instance.send_message(
                chat_id=event.user_telegram_id,
                text=text,
                parse_mode="Markdown",
                reply_markup=keyboard,
            )

            if user.voice_replies:
                from voice_handler import text_to_speech
                audio_path = await text_to_speech(
                    f"Recordatorio: {event.title}.",
                    voice=user.voice_persona or "nova",
                )
                with open(audio_path, "rb") as f:
                    await _bot_instance.send_voice(chat_id=event.user_telegram_id, voice=f)
                os.unlink(audio_path)

            event.reminder_sent    = True
            event.last_reminded_at = now_utc
            event.followup_count   = 0
            db.commit()

        # 2. Follow-ups: eventos que ya se notificaron pero siguen sin completar
        followup_events = db.query(Event).filter(
            Event.start_datetime <= now_utc,
            Event.status == EventStatus.pending,
            Event.reminder_sent == True,
            Event.last_reminded_at != None,
            Event.followup_count < len(FOLLOWUP_MESSAGES),
        ).all()

        for event in followup_events:
            # Enviar follow-up cada 60 segundos tras el recordatorio inicial
            seconds_since = (now_utc - event.last_reminded_at).total_seconds()
            if seconds_since < 60:
                continue

            user = db.query(User).filter(User.telegram_id == event.user_telegram_id).first()
            if not user:
                continue

            idx  = event.followup_count % len(FOLLOWUP_MESSAGES)
            msg  = f"🔔 *{event.title}*\n{FOLLOWUP_MESSAGES[idx]}"

            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Listo",   callback_data=f"complete:{event.id}"),
                InlineKeyboardButton("⏰ +15 min", callback_data=f"snooze15:{event.id}"),
                InlineKeyboardButton("❌ Cancelar",callback_data=f"cancel:{event.id}"),
            ]])

            await _bot_instance.send_message(
                chat_id=event.user_telegram_id,
                text=msg,
                parse_mode="Markdown",
                reply_markup=keyboard,
            )

            event.last_reminded_at = now_utc
            event.followup_count  += 1
            db.commit()

    except Exception as e:
        logger.error(f"Error en check_due_reminders: {e}", exc_info=True)
    finally:
        db.close()



# ---------------------------------------------------------------------------
# MORNING BRIEFING (diario a la hora configurada)
# ---------------------------------------------------------------------------
async def morning_briefing():
    """Envía el resumen matutino con PDF a todos los usuarios activos."""
    if not _bot_instance:
        return

    db: Session = SessionLocal()
    try:
        users = db.query(User).all()
        for user in users:
            tz  = ZoneInfo(user.timezone or "America/Mexico_City")
            now = datetime.now(tz)

            # Solo ejecutar si es la hora del morning del usuario
            if now.hour != user.morning_hour:
                continue

            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day   = now.replace(hour=23, minute=59, second=59)

            events = db.query(Event).filter(
                Event.user_telegram_id == user.telegram_id,
                Event.start_datetime >= start_of_day,
                Event.start_datetime <= end_of_day,
                Event.status == EventStatus.pending,
            ).order_by(Event.start_datetime).all()

            events_list = [
                {"title": e.title, "start": str(e.start_datetime), "type": e.event_type, "description": e.description}
                for e in events
            ]

            # Generar PDF del briefing
            pdf_path = generate_daily_briefing(events_list, user.full_name or "Tú", now)

            msg = f"☀️ *¡Buenos días!* Tienes *{len(events)}* evento(s) para hoy. Te adjunto tu agenda del día. 📄"
            await _bot_instance.send_message(chat_id=user.telegram_id, text=msg, parse_mode="Markdown")

            with open(pdf_path, "rb") as f:
                await _bot_instance.send_document(
                    chat_id=user.telegram_id,
                    document=f,
                    filename=f"agenda_{now.strftime('%Y%m%d')}.pdf",
                    caption="Aquí está tu itinerario de hoy 📋",
                )
            os.unlink(pdf_path)

            # Audio de buenos días (si habilitado)
            if user.voice_replies:
                from voice_handler import text_to_speech
                if events:
                    speech = f"Buenos días. Tienes {len(events)} evento{'s' if len(events) > 1 else ''} para hoy. El primero es {events[0].title}. Te envié la agenda completa en el documento adjunto."
                else:
                    speech = "Buenos días. No tienes eventos programados para hoy. ¡Buen día libre!"
                audio_path = await text_to_speech(speech, voice=user.voice_persona or "nova")
                with open(audio_path, "rb") as f:
                    await _bot_instance.send_voice(chat_id=user.telegram_id, voice=f)
                os.unlink(audio_path)

    except Exception as e:
        logger.error(f"Error en morning_briefing: {e}")
    finally:
        db.close()


# ---------------------------------------------------------------------------
# EVENING WRAP-UP (diario a la hora configurada)
# ---------------------------------------------------------------------------
async def evening_wrapup():
    """Envía el resumen nocturno con PDF a todos los usuarios activos."""
    if not _bot_instance:
        return

    db: Session = SessionLocal()
    try:
        users = db.query(User).all()
        for user in users:
            tz  = ZoneInfo(user.timezone or "America/Mexico_City")
            now = datetime.now(tz)

            if now.hour != user.evening_hour:
                continue

            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_of_day   = now.replace(hour=23, minute=59, second=59)

            all_events  = db.query(Event).filter(
                Event.user_telegram_id == user.telegram_id,
                Event.start_datetime >= start_of_day,
                Event.start_datetime <= end_of_day,
            ).all()

            completed = [e for e in all_events if e.status == EventStatus.completed]
            pending   = [e for e in all_events if e.status == EventStatus.pending]

            completed_list = [{"title": e.title, "start": str(e.start_datetime)} for e in completed]
            pending_list   = [{"title": e.title, "start": str(e.start_datetime)} for e in pending]

            pdf_path = generate_evening_wrapup(completed_list, pending_list, user.full_name or "Tú", now)

            msg = (
                f"🌙 *Resumen del día*\n"
                f"✅ Completados: *{len(completed)}*\n"
                f"⏳ Pendientes: *{len(pending)}*\n\n"
                f"Te adjunto el reporte completo 📄"
            )
            await _bot_instance.send_message(chat_id=user.telegram_id, text=msg, parse_mode="Markdown")
            with open(pdf_path, "rb") as f:
                await _bot_instance.send_document(
                    chat_id=user.telegram_id,
                    document=f,
                    filename=f"wrapup_{now.strftime('%Y%m%d')}.pdf",
                    caption="Resumen nocturno 🌙",
                )
            os.unlink(pdf_path)

            if user.voice_replies:
                from voice_handler import text_to_speech
                speech = f"Resumen del día. Completaste {len(completed)} tarea{'s' if len(completed) != 1 else ''}. Quedaron {len(pending)} pendiente{'s' if len(pending) != 1 else ''}. ¡Que descanses!"
                audio_path = await text_to_speech(speech, voice=user.voice_persona or "nova")
                with open(audio_path, "rb") as f:
                    await _bot_instance.send_voice(chat_id=user.telegram_id, voice=f)
                os.unlink(audio_path)

    except Exception as e:
        logger.error(f"Error en evening_wrapup: {e}")
    finally:
        db.close()


# ---------------------------------------------------------------------------
# INICIALIZACIÓN DEL SCHEDULER
# ---------------------------------------------------------------------------
def start_scheduler(bot):
    set_bot(bot)
    # Revisar recordatorios cada 30 segundos
    scheduler.add_job(check_due_reminders, "interval", seconds=30, id="check_reminders")
    # Revisar briefing cada hora (la función internamente verifica si es la hora correcta)
    scheduler.add_job(morning_briefing,    "interval", hours=1,    id="morning_briefing")
    scheduler.add_job(evening_wrapup,      "interval", hours=1,    id="evening_wrapup")
    scheduler.start()
    logger.info("✅ Scheduler iniciado.")
