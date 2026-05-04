"""
main.py - Punto de entrada del Bot de Agenda en Telegram
Agenda Bot - Asistente Personal (ARIA)
"""
import hashlib
import hmac
import logging
import os
import tempfile
import time

from dotenv import load_dotenv
load_dotenv()

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

from database import init_db, SessionLocal, User, Event, EventStatus
from ai_handler import process_message, reset_history, analyze_patterns
from voice_handler import transcribe_voice, text_to_speech
from scheduler import start_scheduler
from pdf_generator import generate_productivity_report
from ai_handler import _exec_generate_report

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------
def get_or_create_user(telegram_id: str, full_name: str, db) -> User:
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    if not user:
        user = User(telegram_id=telegram_id, full_name=full_name)
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def _cache_text_for_button(context: ContextTypes.DEFAULT_TYPE, text: str) -> str:
    """
    Guarda el texto en bot_data con un id corto y devuelve el id.
    Mantiene solo los últimos 200 textos para no crecer en memoria.
    """
    import secrets
    short_id = secrets.token_urlsafe(6)
    cache = context.bot_data.setdefault("text_cache", {})
    cache[short_id] = text
    if len(cache) > 200:
        # Quitar el más viejo (dicts mantienen orden de inserción en Py 3.7+)
        oldest = next(iter(cache))
        cache.pop(oldest, None)
    return short_id


async def send_text_and_voice(update: Update, user: User, text: str, parse_mode: str = "Markdown",
                              context: ContextTypes.DEFAULT_TYPE = None):
    """
    Manda la respuesta como audio (voz consistente de ElevenLabs) con un botón
    'Ver texto' para revelar la transcripción. Si voice_replies=False, manda solo texto.
    """
    if not user.voice_replies:
        await update.effective_message.reply_text(text, parse_mode=parse_mode)
        return

    audio_path = await text_to_speech(
        text.replace("*", "").replace("_", ""),
        voice=user.voice_persona or "aria",
    )

    # Botón inline para revelar el texto on-demand
    reply_markup = None
    if context is not None:
        short_id = _cache_text_for_button(context, text)
        reply_markup = InlineKeyboardMarkup([[
            InlineKeyboardButton("📝 Ver texto", callback_data=f"txt:{short_id}")
        ]])

    with open(audio_path, "rb") as f:
        await update.effective_message.reply_voice(voice=f, reply_markup=reply_markup)
    os.unlink(audio_path)


# ---------------------------------------------------------------------------
# /start
# ---------------------------------------------------------------------------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id  = str(update.effective_user.id)
    name     = update.effective_user.first_name or "amigo"
    db       = SessionLocal()
    user     = get_or_create_user(user_id, name, db)
    db.close()

    welcome = (
        f"👋 ¡Hola, *{name}*! Soy *ARIA*, tu asistente personal de agenda.\n\n"
        "Puedo ayudarte a:\n"
        "• ⏰ Crear recordatorios y citas\n"
        "• 📅 Consultar tu agenda del día\n"
        "• 🔄 Reagendar o cancelar eventos\n"
        "• 📊 Generarte reportes en PDF\n"
        "• 🎙️ Entender mensajes de voz\n\n"
        "Simplemente escríbeme (o mándame una nota de voz) lo que necesitas.\n"
        "Por ejemplo: _'Recuérdame en 10 minutos tomar agua'_ o _'¿Qué tengo para mañana?'_\n\n"
        "Usa /ayuda para ver todos los comandos disponibles."
    )
    await send_text_and_voice(update, user, welcome, context=context)


# ---------------------------------------------------------------------------
# /ayuda
# ---------------------------------------------------------------------------
async def cmd_ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📋 *Comandos disponibles:*\n\n"
        "• /agenda — Ver tu agenda de hoy\n"
        "• /semana — Ver agenda de los próximos 7 días\n"
        "• /reporte — Reporte de productividad (diario/semanal/mensual)\n"
        "• /voz — Activar/desactivar respuestas en audio\n"
        "• /perfil — Ver y cambiar tu configuración\n"
        "• /sugerencias — Patrones detectados y consejos\n"
        "• /dashboard — Abrir el dashboard web\n"
        "• /olvidar — Borrar el historial conversacional\n"
        "• /cancelar — Salir del modo edición\n\n"
        "💬 *O simplemente escríbeme lo que necesitas en lenguaje natural:*\n"
        "_'Agéndame una junta el martes a las 3 PM'_\n"
        "_'Cancela mi cita del viernes'_\n"
        "_'¿Tengo algo pendiente para mañana?'_\n"
        "_'Hazme un reporte de la semana'_"
    )
    await update.effective_message.reply_text(text, parse_mode="Markdown")


# ---------------------------------------------------------------------------
# /agenda — Agenda del día
# ---------------------------------------------------------------------------
async def cmd_agenda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    db = SessionLocal()
    user = get_or_create_user(user_id, update.effective_user.first_name, db)

    from datetime import datetime
    from zoneinfo import ZoneInfo
    tz  = ZoneInfo(user.timezone or "America/Mexico_City")
    now = datetime.now(tz)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end   = now.replace(hour=23, minute=59, second=59)

    events = db.query(Event).filter(
        Event.user_telegram_id == user_id,
        Event.start_datetime >= start,
        Event.start_datetime <= end,
        Event.status == EventStatus.pending,
    ).order_by(Event.start_datetime).all()
    db.close()

    if not events:
        await send_text_and_voice(update, user, "📭 No tienes eventos pendientes para hoy. ¡Día libre! 🎉", context=context)
        return

    # Cabecera
    await update.effective_message.reply_text(
        f"📅 *Tu agenda de hoy* — {len(events)} evento{'s' if len(events) > 1 else ''}",
        parse_mode="Markdown",
    )

    # Cada evento como mensaje independiente con sus botones
    cat_emoji = {
        "personal": "🏠", "trabajo": "💼", "salud": "❤️",
        "finanzas": "💰", "familia": "👨‍👩‍👧", "social": "🎉", "otros": "📌",
    }
    type_emoji = {"reminder": "⏰", "meeting": "📅", "task": "✅"}

    from recurrence import describe_rule
    for ev in events:
        hora = ev.start_datetime.strftime("%I:%M %p").lstrip("0")
        icon = type_emoji.get(ev.event_type, "•")
        cat  = cat_emoji.get(ev.category or "otros", "📌")
        text = f"{icon} `{hora}` — *{ev.title}*  {cat}\n_ID: {ev.id}_"

        meta = []
        if ev.location:        meta.append(f"📍 {ev.location}")
        if ev.attendees:       meta.append(f"👥 {ev.attendees}")
        if ev.recurrence_rule: meta.append(f"🔁 {describe_rule(ev.recurrence_rule)}")
        if ev.tags:            meta.append(f"🏷️ {ev.tags}")
        if meta:
            text += "\n" + " · ".join(meta)

        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅",       callback_data=f"complete:{ev.id}"),
            InlineKeyboardButton("⏰+15",    callback_data=f"snooze15:{ev.id}"),
            InlineKeyboardButton("📝 Editar",callback_data=f"edit:{ev.id}"),
            InlineKeyboardButton("❌",       callback_data=f"cancel:{ev.id}"),
        ]])

        await update.effective_message.reply_text(
            text, parse_mode="Markdown", reply_markup=keyboard,
        )

    if user.voice_replies:
        speech = f"Tienes {len(events)} evento{'s' if len(events) > 1 else ''} para hoy."
        audio_path = await text_to_speech(speech, voice=user.voice_persona or "nova")
        with open(audio_path, "rb") as f:
            await update.effective_message.reply_voice(voice=f)
        os.unlink(audio_path)


# ---------------------------------------------------------------------------
# /semana — Agenda de los próximos 7 días
# ---------------------------------------------------------------------------
async def cmd_semana(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    db = SessionLocal()
    user = get_or_create_user(user_id, update.effective_user.first_name, db)

    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo
    tz  = ZoneInfo(user.timezone or "America/Mexico_City")
    now = datetime.now(tz)
    end = now + timedelta(days=7)

    events = db.query(Event).filter(
        Event.user_telegram_id == user_id,
        Event.start_datetime >= now,
        Event.start_datetime <= end,
        Event.status == EventStatus.pending,
    ).order_by(Event.start_datetime).all()
    db.close()

    if not events:
        await update.effective_message.reply_text("📭 No tienes eventos en los próximos 7 días.")
        return

    lines = ["📅 *Eventos próximos (7 días):*\n"]
    for ev in events:
        fecha = ev.start_datetime.strftime("%a %d/%m  %I:%M %p")
        icon  = {"reminder": "⏰", "meeting": "📅", "task": "✅"}.get(ev.event_type, "•")
        line  = f"{icon} `{fecha}` — {ev.title}"
        bits = []
        if ev.location:        bits.append(f"📍 {ev.location}")
        if ev.recurrence_rule: bits.append(f"🔁 {ev.recurrence_rule}")
        if bits:
            line += "  _(" + ", ".join(bits) + ")_"
        lines.append(line)

    await update.effective_message.reply_text("\n".join(lines), parse_mode="Markdown")


# ---------------------------------------------------------------------------
# /reporte — Reporte de productividad con opciones
# ---------------------------------------------------------------------------
async def cmd_reporte(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📅 Hoy",   callback_data="report:daily")],
        [InlineKeyboardButton("📆 Esta semana",  callback_data="report:weekly")],
        [InlineKeyboardButton("🗓️ Este mes",     callback_data="report:monthly")],
    ])
    await update.effective_message.reply_text(
        "📊 ¿Qué período quieres reportar?",
        reply_markup=keyboard,
    )


# ---------------------------------------------------------------------------
# /dashboard — Genera URL firmada al dashboard web
# ---------------------------------------------------------------------------
def _get_env_tolerant(name: str, default: str = "") -> str:
    """
    Lee una variable de entorno tolerando whitespace tanto en el NOMBRE
    como en el VALOR. Cubre el caso comun de pegar un espacio invisible
    al crear variables en Railway u otras plataformas.
    """
    target = name.strip().upper()
    for key, val in os.environ.items():
        if key.strip().upper() == target:
            return val.strip().strip('"').strip("'")
    return default


def _make_dashboard_token(telegram_id: str, ttl_hours: int = 24) -> str | None:
    secret = _get_env_tolerant("DASHBOARD_SECRET")
    if not secret:
        return None
    expires = int(time.time()) + ttl_hours * 3600
    payload = f"{telegram_id}:{expires}"
    sig = hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}:{sig}"


async def cmd_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    token = _make_dashboard_token(user_id)

    if not token:
        await update.effective_message.reply_text(
            "⚠️ El dashboard no está configurado. Falta `DASHBOARD_SECRET` en las variables de entorno.",
            parse_mode="Markdown",
        )
        return

    base_url = _get_env_tolerant("DASHBOARD_URL") or "https://aria-dashboard.streamlit.app"
    full_url = f"{base_url}/?token={token}"

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔗 Abrir dashboard", url=full_url)
    ]])
    await update.effective_message.reply_text(
        "📊 *Tu dashboard personal*\n\n"
        "Este enlace es exclusivo para ti y expira en *24 horas*. "
        "Pídeme uno nuevo cuando lo necesites con `/dashboard`.",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )


# ---------------------------------------------------------------------------
# /sugerencias — Análisis proactivo de patrones
# ---------------------------------------------------------------------------
async def cmd_sugerencias(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    db = SessionLocal()
    try:
        sugerencias = analyze_patterns(user_id, db)
    finally:
        db.close()

    if not sugerencias:
        await update.effective_message.reply_text(
            "✨ Todo se ve bien, no detecté patrones que valga la pena mejorar."
        )
        return

    text = "🤖 *Sugerencias detectadas:*\n\n" + "\n\n".join(sugerencias)
    await update.effective_message.reply_text(text, parse_mode="Markdown")


# ---------------------------------------------------------------------------
# /cancelar — Salir del modo edición (o cualquier flujo conversacional)
# ---------------------------------------------------------------------------
async def cmd_cancelar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    had_edit = context.user_data.pop("editing_event_id", None)
    if had_edit:
        await update.effective_message.reply_text("✅ Cancelé el modo edición.")
    else:
        await update.effective_message.reply_text("No hay nada que cancelar.")


# ---------------------------------------------------------------------------
# /olvidar — Borrar el historial conversacional del usuario
# ---------------------------------------------------------------------------
async def cmd_olvidar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    db = SessionLocal()
    try:
        n = reset_history(user_id, db)
    finally:
        db.close()
    await update.effective_message.reply_text(
        f"🧠 Olvidé nuestra conversación previa ({n} mensaje{'s' if n != 1 else ''} borrado{'s' if n != 1 else ''}). Empezamos de cero."
    )


# ---------------------------------------------------------------------------
# /voz — Toggle de respuestas de voz
# ---------------------------------------------------------------------------
async def cmd_voz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    db      = SessionLocal()
    user    = get_or_create_user(user_id, update.effective_user.first_name, db)
    user.voice_replies = not user.voice_replies
    db.commit()
    estado = "activadas ✅" if user.voice_replies else "desactivadas ❌"
    db.close()
    await update.effective_message.reply_text(f"🎙️ Respuestas de voz {estado}.")


# ---------------------------------------------------------------------------
# /perfil — Configuración del usuario
# ---------------------------------------------------------------------------
async def cmd_perfil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    db = SessionLocal()
    user = get_or_create_user(user_id, update.effective_user.first_name, db)
    db.close()

    # Voces de OpenAI TTS disponibles
    from voice_handler import OPENAI_VOICES
    voices = OPENAI_VOICES

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(
            f"{'▶️ ' if user.voice_persona == v else '  '}{desc}",
            callback_data=f"setvoice:{v}"
        )]
        for v, desc in voices.items()
    ])

    text = (
        f"⚙️ *Tu perfil:*\n\n"
        f"• Zona horaria: `{user.timezone}`\n"
        f"• Voz actual: `{user.voice_persona}` (OpenAI TTS-1-HD)\n"
        f"• Briefing matutino: `{user.morning_hour:02d}:00`\n"
        f"• Wrap-up nocturno: `{user.evening_hour:02d}:00`\n"
        f"• Respuestas de voz: `{'Activadas ✅' if user.voice_replies else 'Desactivadas ❌'}`\n\n"
        "🎙️ *Elige la voz de ARIA:*"
    )
    await update.effective_message.reply_text(text, parse_mode="Markdown", reply_markup=keyboard)


# ---------------------------------------------------------------------------
# HANDLER: Mensajes de texto libres
# ---------------------------------------------------------------------------
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    db      = SessionLocal()
    user    = get_or_create_user(user_id, update.effective_user.first_name, db)
    user_text = update.effective_message.text

    await update.effective_message.reply_chat_action("typing")

    # ── Modo edición de evento ────────────────────────────────
    editing_id = context.user_data.pop("editing_event_id", None)
    if editing_id:
        edit_prompt = (
            f"El usuario quiere editar el evento con event_id={editing_id}. "
            f"Su instrucción es: '{user_text}'. "
            f"Llama update_event con event_id={editing_id} y los campos que correspondan."
        )
        response = process_message(edit_prompt, user_id, db, timezone=user.timezone or "America/Mexico_City")
    else:
        response = process_message(user_text, user_id, db, timezone=user.timezone or "America/Mexico_City")

    await send_text_and_voice(update, user, response, context=context)
    db.close()


# ---------------------------------------------------------------------------
# HANDLER: Notas de voz
# ---------------------------------------------------------------------------
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    db      = SessionLocal()
    user    = get_or_create_user(user_id, update.effective_user.first_name, db)
    print(f"[VOICE] Mensaje de voz recibido de user={user_id}")

    try:
        await update.effective_message.reply_chat_action("typing")

        # Descargar el archivo de voz
        voice_file = await update.effective_message.voice.get_file()
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".ogg")
        tmp.close()
        await voice_file.download_to_drive(tmp.name)
        print(f"[VOICE] Audio descargado en {tmp.name}")

        # Transcribir con Whisper
        transcribed = await transcribe_voice(tmp.name)
        os.unlink(tmp.name)
        print(f"[VOICE] Transcripción: '{transcribed}'")

        await update.effective_message.reply_text(f"🎙️ _Entendí:_ \"{transcribed}\"", parse_mode="Markdown")

        # Procesar con IA
        response = process_message(transcribed, user_id, db, timezone=user.timezone or "America/Mexico_City")

        await send_text_and_voice(update, user, response, context=context)
        db.close()

    except Exception as e:
        logger.error(f"[VOICE] Error procesando voz: {e}", exc_info=True)
        print(f"[VOICE] ERROR: {e}")
        try:
            await update.effective_message.reply_text(f"❌ Error al procesar el audio: `{str(e)[:150]}`", parse_mode="Markdown")
        except Exception:
            pass
        try:
            db.close()
        except Exception:
            pass



# ---------------------------------------------------------------------------
# HANDLER: Botones Inline (callbacks)
# ---------------------------------------------------------------------------
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    user_id = str(query.from_user.id)
    data    = query.data
    db      = SessionLocal()
    user    = get_or_create_user(user_id, query.from_user.first_name, db)

    await query.answer()

    try:
        # --- Ver texto del audio ---
        if data.startswith("txt:"):
            short_id = data.split(":", 1)[1]
            text = context.bot_data.get("text_cache", {}).get(short_id)
            if text:
                await query.edit_message_reply_markup(reply_markup=None)
                await query.message.reply_text(text, parse_mode="Markdown")
            else:
                await query.message.reply_text("⚠️ No pude recuperar el texto (el bot se reinició desde que recibiste este audio).")
            return

        # --- Editar evento (modo conversacional) ---
        if data.startswith("edit:"):
            event_id = int(data.split(":")[1])
            event = db.query(Event).filter(Event.id == event_id).first()
            if not event:
                await query.message.reply_text("❌ Ese evento ya no existe.")
                return
            # Guardar el contexto de edición
            context.user_data["editing_event_id"] = event_id
            await query.message.reply_text(
                f"✏️ Editando *{event.title}*\n\n"
                "Dime qué quieres cambiar en lenguaje natural. Ejemplos:\n"
                "• _'cambia la hora a las 11 AM'_\n"
                "• _'reagéndalo para el viernes'_\n"
                "• _'cambia el título a Junta semanal'_\n"
                "• _'agrégale ubicación: Sala 3'_\n\n"
                "Escribe /cancelar para salir del modo edición.",
                parse_mode="Markdown",
            )
            return

        # --- Completar evento ---
        if data.startswith("complete:"):
            event_id = int(data.split(":")[1])
            event = db.query(Event).filter(Event.id == event_id).first()
            if event:
                event.status = EventStatus.completed
                db.commit()
                await query.edit_message_reply_markup(reply_markup=None)
                await query.message.reply_text(f"✅ *Listo!* _{event.title}_ marcado como completado.", parse_mode="Markdown")

        # --- Snooze 15 min ---
        elif data.startswith("snooze15:"):
            event_id = int(data.split(":")[1])
            event = db.query(Event).filter(Event.id == event_id).first()
            if event:
                from datetime import timedelta
                event.start_datetime = event.start_datetime + timedelta(minutes=15)
                event.status         = EventStatus.pending
                event.reminder_sent  = False
                db.commit()
                await query.edit_message_reply_markup(reply_markup=None)
                await query.message.reply_text(f"⏰ _{event.title}_ pospuesto 15 minutos.", parse_mode="Markdown")

        # --- Cancelar evento ---
        elif data.startswith("cancel:"):
            event_id = int(data.split(":")[1])
            event = db.query(Event).filter(Event.id == event_id).first()
            if event:
                event.status = EventStatus.cancelled
                db.commit()
                await query.edit_message_reply_markup(reply_markup=None)
                await query.message.reply_text(f"❌ _{event.title}_ cancelado.", parse_mode="Markdown")

        # --- Reporte ---
        elif data.startswith("report:"):
            period = data.split(":")[1]
            period_label = {"daily": "Hoy", "weekly": "Esta semana", "monthly": "Este mes"}

            rd = _exec_generate_report({"period": period}, user_id, db)

            await query.message.reply_text(
                f"📊 *Reporte — {period_label.get(period, period)}*\n"
                f"Total: *{rd['total']}*  •  ✅ {rd['completed']}  •  ⏳ {rd['pending']}",
                parse_mode="Markdown",
            )
            pdf_path = generate_productivity_report(rd, period)
            with open(pdf_path, "rb") as f:
                await query.message.reply_document(
                    document=f,
                    filename=f"reporte_{period}.pdf",
                    caption="📄 Aquí está tu reporte de productividad",
                )
            os.unlink(pdf_path)

        # --- Cambiar voz ---
        elif data.startswith("setvoice:"):
            voice = data.split(":")[1]
            user.voice_persona = voice
            db.commit()
            await query.edit_message_reply_markup(reply_markup=None)
            await query.message.reply_text(f"🎙️ Voz cambiada a *{voice.capitalize()}*.", parse_mode="Markdown")
            audio_path = await text_to_speech("¡Hola! Esta soy yo con mi nueva voz. ¿Te gusta?", voice=voice)
            with open(audio_path, "rb") as f:
                await query.message.reply_voice(voice=f)
            os.unlink(audio_path)

    except Exception as e:
        logger.error(f"Error en callback '{data}': {e}", exc_info=True)
        try:
            await query.message.reply_text(f"❌ Error: `{str(e)[:200]}`", parse_mode="Markdown")
        except Exception:
            pass
    finally:
        db.close()


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        raise ValueError("❌ TELEGRAM_TOKEN no definido en .env")

    init_db()

    app = Application.builder().token(token).build()

    # Comandos
    app.add_handler(CommandHandler("start",   cmd_start))
    app.add_handler(CommandHandler("ayuda",   cmd_ayuda))
    app.add_handler(CommandHandler("agenda",  cmd_agenda))
    app.add_handler(CommandHandler("semana",  cmd_semana))
    app.add_handler(CommandHandler("reporte", cmd_reporte))
    app.add_handler(CommandHandler("voz",         cmd_voz))
    app.add_handler(CommandHandler("perfil",      cmd_perfil))
    app.add_handler(CommandHandler("olvidar",     cmd_olvidar))
    app.add_handler(CommandHandler("sugerencias", cmd_sugerencias))
    app.add_handler(CommandHandler("cancelar",    cmd_cancelar))
    app.add_handler(CommandHandler("dashboard",   cmd_dashboard))

    # Mensajes libres
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))

    # Callbacks de botones
    app.add_handler(CallbackQueryHandler(handle_callback))

    async def on_startup(application):
        start_scheduler(application)
        logger.info("🚀 ARIA Bot iniciado. Esperando mensajes...")

    app.post_init = on_startup

    logger.info("🚀 Arrancando ARIA Bot...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
