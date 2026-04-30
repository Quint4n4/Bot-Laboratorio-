import asyncio
import os
import tempfile
from telegram import Update
from telegram.ext import Application, ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler

from config import settings
from rag import generate_rag_response, transcribe_audio
from pdf_service import create_quote_pdf
from paquetes import get_menu_text, get_paquete, PAQUETES
from db import init_db, save_cotizacion

# ─────────────────────────────────────────────────────────────
# Estados
# ─────────────────────────────────────────────────────────────
ESPERANDO_ESTUDIOS, ESPERANDO_NOMBRE, ESPERANDO_DESCARTE, ESPERANDO_ACLARACION = range(4)

PALABRAS_SI = {"si", "sí", "yes", "descartar", "descarta", "omitir", "eliminar",
               "s", "dale", "ok", "okay", "adelante", "continuar", "continúa"}

# ─────────────────────────────────────────────────────────────
# /start
# ─────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    menu = get_menu_text()
    await update.message.reply_text(
        "👋 ¡Hola! Soy tu asistente de cotizaciones de *OPLAB*.\n\n"
        "Puedes elegir un paquete predefinido o pedir estudios específicos:\n\n"
        f"{menu}",
        parse_mode="Markdown"
    )
    return ESPERANDO_ESTUDIOS

# ─────────────────────────────────────────────────────────────
# Helpers internos
# ─────────────────────────────────────────────────────────────
def _calcular_total(cotizacion: list) -> float:
    return sum(float(c.get("precio", 0)) for c in cotizacion)

def _calcular_total_min(cotizacion: list) -> float:
    return sum(float(c.get("precio_min", c.get("precio", 0))) for c in cotizacion)

async def _pedir_nombre(update: Update, cotizacion: list) -> int:
    """Guarda ia_json final y pide el nombre del paciente."""
    return ESPERANDO_NOMBRE

async def _enviar_descarte(update: Update, cotizacion_valida: list, no_encontrados: list) -> int:
    nombres_nf = ", ".join(f"*{e}*" for e in no_encontrados)
    nombres_ok = ", ".join(c.get("estudio", "") for c in cotizacion_valida)
    await update.message.reply_text(
        f"⚠️ No encontré en el catálogo: {nombres_nf}\n\n"
        f"✅ Estudios confirmados: *{nombres_ok}*\n\n"
        "¿Qué deseas hacer?\n"
        "• Responde *Sí* para descartarlo y continuar con los demás.\n"
        "• O escribe el *nombre correcto* del estudio.",
        parse_mode="Markdown"
    )
    return ESPERANDO_DESCARTE

async def _enviar_aclaracion(update: Update, ambiguos: list, cotizacion_ok: list) -> int:
    """Pide aclaración para el primer estudio ambiguo pendiente."""
    primero = ambiguos[0]
    solicitado = primero.get("solicitado", "")
    opciones = primero.get("opciones", [])
    opciones_txt = "\n".join(f"  • *{o}*" for o in opciones)
    nombres_ok = ", ".join(c.get("estudio", "") for c in cotizacion_ok)

    msg = f"🔎 Para *{solicitado}* existen varias opciones en el catálogo:\n{opciones_txt}\n\n¿Cuál deseas incluir?"
    if nombres_ok:
        msg += f"\n\n_(Ya confirmados: {nombres_ok})_"
    await update.message.reply_text(msg, parse_mode="Markdown")
    return ESPERANDO_ACLARACION

# ─────────────────────────────────────────────────────────────
# Núcleo compartido de procesamiento
# ─────────────────────────────────────────────────────────────
async def _procesar_texto(update: Update, context: ContextTypes.DEFAULT_TYPE, user_text: str) -> int:
    chat_id = update.message.chat_id

    if "history" not in context.user_data:
        context.user_data["history"] = []
    context.user_data["history"].append(f"Usuario: {user_text}")
    historial = "\n".join(context.user_data["history"][-6:])

    msg = await update.message.reply_text("⏳ Procesando cotización...")

    try:
        ia = generate_rag_response(historial)
        context.user_data["history"].append(f"Bot: {ia.get('mensaje', '')}")
        await context.bot.delete_message(chat_id=chat_id, message_id=msg.message_id)
        return await _evaluar_resultado(update, context, ia)

    except Exception as e:
        print("Error en RAG:", e)
        import traceback; traceback.print_exc()
        await context.bot.delete_message(chat_id=chat_id, message_id=msg.message_id)
        await update.message.reply_text("❌ Error de procesamiento. Intenta de nuevo.")
        return ESPERANDO_ESTUDIOS

async def _evaluar_resultado(update: Update, context: ContextTypes.DEFAULT_TYPE, ia: dict) -> int:
    """
    Evalúa el JSON de la IA y decide el siguiente estado:
    - Todo resuelto → ESPERANDO_NOMBRE
    - Hay ambiguos pendientes → ESPERANDO_ACLARACION  
    - Hay no encontrados con válidos → ESPERANDO_DESCARTE
    - Ninguno encontrado → ESPERANDO_ESTUDIOS
    """
    cotizacion     = ia.get("cotizacion", [])
    ambiguos       = ia.get("ambiguos", [])
    no_encontrados = ia.get("no_encontrados", [])
    genera_pdf     = ia.get("genera_pdf", False)

    # ── CASO 1: Todo perfecto ────────────────────────────────
    if genera_pdf and cotizacion and not ambiguos and not no_encontrados:
        total = _calcular_total(cotizacion)
        total_min = _calcular_total_min(cotizacion)
        context.user_data["ia_json"] = {"cotizacion": cotizacion, "total": total, "total_min": total_min, "genera_pdf": True}
        await update.message.reply_text(
            f"{ia.get('mensaje', '¡Listo!')}\n\n"
            "📝 Por favor escríbeme el *NOMBRE COMPLETO DEL PACIENTE* para generar el PDF:",
            parse_mode="Markdown"
        )
        return ESPERANDO_NOMBRE

    # ── CASO 2: Hay ambigüedad en algún estudio ──────────────
    if ambiguos:
        # Guardar lo que ya se confirmó y la cola de ambiguos pendientes
        context.user_data["cotizacion_confirmada"] = cotizacion  # los que sí se resolvieron
        context.user_data["ambiguos_pendientes"]   = ambiguos
        context.user_data["no_encontrados"]        = no_encontrados
        return await _enviar_aclaracion(update, ambiguos, cotizacion)

    # ── CASO 3: Estudios no encontrados, pero hay válidos ────
    if no_encontrados and cotizacion:
        context.user_data["cotizacion_valida"]  = cotizacion
        context.user_data["no_encontrados"]     = no_encontrados
        context.user_data["total_valido"]       = _calcular_total(cotizacion)
        context.user_data["total_min_valido"]   = _calcular_total_min(cotizacion)
        context.user_data["ia_json_parcial"]    = {
            "cotizacion": cotizacion,
            "total": context.user_data["total_valido"],
            "total_min": context.user_data["total_min_valido"],
            "genera_pdf": True
        }
        return await _enviar_descarte(update, cotizacion, no_encontrados)

    # ── CASO 4: Nada encontrado ──────────────────────────────
    if no_encontrados and not cotizacion:
        nombres = ", ".join(f"*{e}*" for e in no_encontrados)
        await update.message.reply_text(
            f"❌ No encontré ninguno de estos estudios: {nombres}\n\n"
            "Verifica los nombres e intenta de nuevo.",
            parse_mode="Markdown"
        )
        return ESPERANDO_ESTUDIOS

    # ── CASO 5: Respuesta genérica sin cotización ────────────
    await update.message.reply_text(ia.get("mensaje", "No entendí la solicitud. Intenta de nuevo."))
    return ESPERANDO_ESTUDIOS

# ─────────────────────────────────────────────────────────────
# Handler: Texto
# ─────────────────────────────────────────────────────────────
async def handle_studies_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    return await _procesar_texto(update, context, update.message.text.strip())

# ─────────────────────────────────────────────────────────────
# Handler: Voz
# ─────────────────────────────────────────────────────────────
async def handle_voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    chat_id = update.message.chat_id
    msg = await update.message.reply_text("🎙️ Transcribiendo audio...")
    try:
        tg_file = await context.bot.get_file(update.message.voice.file_id)
        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            tmp_path = tmp.name
        await tg_file.download_to_drive(tmp_path)
        user_text = transcribe_audio(tmp_path)
        os.unlink(tmp_path)

        await context.bot.delete_message(chat_id=chat_id, message_id=msg.message_id)
        await update.message.reply_text(f"🎤 *Escuché:* _{user_text}_", parse_mode="Markdown")
        return await _procesar_texto(update, context, user_text)
    except Exception as e:
        print("Error en voz:", e)
        await context.bot.delete_message(chat_id=chat_id, message_id=msg.message_id)
        await update.message.reply_text("❌ No pude entender el audio. Intenta de nuevo o escríbelo.")
        return ESPERANDO_ESTUDIOS

# ─────────────────────────────────────────────────────────────
# Handler: Aclaración de ambigüedad
# ─────────────────────────────────────────────────────────────
async def handle_aclaracion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """El usuario eligió una opción de entre las ambiguas."""
    respuesta = update.message.text.strip()
    chat_id = update.message.chat_id

    ambiguos_pendientes  = context.user_data.get("ambiguos_pendientes", [])
    cotizacion_confirmada = context.user_data.get("cotizacion_confirmada", [])
    no_encontrados       = context.user_data.get("no_encontrados", [])

    if not ambiguos_pendientes:
        return ESPERANDO_ESTUDIOS

    actual = ambiguos_pendientes[0]
    opciones = actual.get("opciones", [])

    # Pedirle a GPT que resuelva cuál eligió
    msg_wait = await update.message.reply_text("⏳ Verificando tu elección...")
    try:
        consulta = (
            f"El usuario está eligiendo entre estas opciones del catálogo: {opciones}.\n"
            f"El usuario respondió: '{respuesta}'.\n"
            f"Determina cuál opción eligió y ponla en 'identificados'."
        )
        ia = generate_rag_response(consulta)
        await context.bot.delete_message(chat_id=chat_id, message_id=msg_wait.message_id)

        nuevo_estudio = ia.get("cotizacion", [])
        if not nuevo_estudio:
            await update.message.reply_text(
                f"No pude identificar tu elección. Por favor escribe el nombre exacto:\n"
                + "\n".join(f"• *{o}*" for o in opciones),
                parse_mode="Markdown"
            )
            return ESPERANDO_ACLARACION

        # Agregar el estudio elegido a la cotización confirmada
        cotizacion_confirmada.extend(nuevo_estudio)
        ambiguos_pendientes.pop(0)  # Resolver este ambiguo

        context.user_data["cotizacion_confirmada"] = cotizacion_confirmada
        context.user_data["ambiguos_pendientes"]   = ambiguos_pendientes

        # ¿Quedan más ambiguos?
        if ambiguos_pendientes:
            return await _enviar_aclaracion(update, ambiguos_pendientes, cotizacion_confirmada)

        # ¿Quedan no encontrados?
        if no_encontrados:
            context.user_data["cotizacion_valida"] = cotizacion_confirmada
            context.user_data["total_valido"] = _calcular_total(cotizacion_confirmada)
            context.user_data["ia_json_parcial"] = {
                "cotizacion": cotizacion_confirmada,
                "total": context.user_data["total_valido"],
                "genera_pdf": True
            }
            return await _enviar_descarte(update, cotizacion_confirmada, no_encontrados)

        # Todo resuelto → pedir nombre
        total = _calcular_total(cotizacion_confirmada)
        total_min = _calcular_total_min(cotizacion_confirmada)
        context.user_data["ia_json"] = {
            "cotizacion": cotizacion_confirmada,
            "total": total,
            "total_min": total_min,
            "genera_pdf": True
        }
        nombres = ", ".join(c.get("estudio", "") for c in cotizacion_confirmada)
        await update.message.reply_text(
            f"✅ Perfecto. Cotización con: *{nombres}*\n\n"
            "📝 Por favor escríbeme el *NOMBRE COMPLETO DEL PACIENTE* para generar el PDF:",
            parse_mode="Markdown"
        )
        return ESPERANDO_NOMBRE

    except Exception as e:
        print("Error en aclaracion:", e)
        await context.bot.delete_message(chat_id=chat_id, message_id=msg_wait.message_id)
        await update.message.reply_text("❌ Error procesando tu elección. Intenta de nuevo.")
        return ESPERANDO_ACLARACION

# ─────────────────────────────────────────────────────────────
# Handler: Descarte de estudio no encontrado
# ─────────────────────────────────────────────────────────────
async def handle_descarte(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    respuesta = update.message.text.strip().lower()
    cotizacion_valida = context.user_data.get("cotizacion_valida", [])

    # ── El usuario descarta → continuar con los que sí están ─
    if respuesta in PALABRAS_SI:
        if not cotizacion_valida:
            await update.message.reply_text("No quedan estudios. Escríbeme nuevos estudios para comenzar.")
            return ESPERANDO_ESTUDIOS

        total = _calcular_total(cotizacion_valida)
        total_min = _calcular_total_min(cotizacion_valida)
        context.user_data["ia_json"] = {
            "cotizacion": cotizacion_valida,
            "total": total,
            "total_min": total_min,
            "genera_pdf": True
        }
        nombres = ", ".join(c.get("estudio", "") for c in cotizacion_valida)
        await update.message.reply_text(
            f"✅ Continuamos con: *{nombres}*\n\n"
            "📝 Por favor escríbeme el *NOMBRE COMPLETO DEL PACIENTE* para generar el PDF:",
            parse_mode="Markdown"
        )
        return ESPERANDO_NOMBRE

    # ── El usuario escribe un nombre alternativo ──────────────
    nuevo_nombre = update.message.text.strip()
    msg_wait = await update.message.reply_text(f"⏳ Buscando *{nuevo_nombre}*...", parse_mode="Markdown")

    try:
        # Consultamos SOLO el nuevo estudio (no re-procesamos todo)
        ia = generate_rag_response(f"Quiero cotizar únicamente: {nuevo_nombre}")
        await context.bot.delete_message(
            chat_id=update.message.chat_id, message_id=msg_wait.message_id
        )

        nuevo_encontrado  = ia.get("cotizacion", [])
        nuevo_ambiguo     = ia.get("ambiguos", [])
        nuevo_no_encontrado = ia.get("no_encontrados", [])

        if nuevo_encontrado:
            # Combinar con los ya confirmados y seguir
            cotizacion_total = cotizacion_valida + nuevo_encontrado
            total = _calcular_total(cotizacion_total)
            total_min = _calcular_total_min(cotizacion_total)
            context.user_data["ia_json"] = {
                "cotizacion": cotizacion_total,
                "total": total,
                "total_min": total_min,
                "genera_pdf": True
            }
            nombres = ", ".join(c.get("estudio", "") for c in cotizacion_total)
            await update.message.reply_text(
                f"✅ ¡Encontrado! Cotización completa con: *{nombres}*\n\n"
                "📝 Por favor escríbeme el *NOMBRE COMPLETO DEL PACIENTE* para generar el PDF:",
                parse_mode="Markdown"
            )
            return ESPERANDO_NOMBRE

        if nuevo_ambiguo:
            # Hay ambigüedad en el nuevo nombre
            context.user_data["cotizacion_confirmada"] = cotizacion_valida
            context.user_data["ambiguos_pendientes"]   = nuevo_ambiguo
            context.user_data["no_encontrados"]        = []
            return await _enviar_aclaracion(update, nuevo_ambiguo, cotizacion_valida)

        # Sigue sin encontrarse
        await update.message.reply_text(
            f"⚠️ No encontré *{nuevo_nombre}* en el catálogo.\n\n"
            "• Responde *Sí* para descartarlo y continuar con los demás.\n"
            "• O escribe otro nombre.",
            parse_mode="Markdown"
        )
        return ESPERANDO_DESCARTE

    except Exception as e:
        print("Error en descarte:", e)
        await update.message.reply_text("❌ Error buscando el estudio. Intenta de nuevo.")
        return ESPERANDO_DESCARTE

# ─────────────────────────────────────────────────────────────
# Handler: Nombre del paciente → generar PDF
# ─────────────────────────────────────────────────────────────
async def handle_patient_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    patient_name = update.message.text
    chat_id = update.message.chat_id
    ia_json = context.user_data.get("ia_json")

    if not ia_json:
        await update.message.reply_text("La sesión caducó. ¿Qué estudios quieres cotizar?")
        return ESPERANDO_ESTUDIOS

    msg = await update.message.reply_text(
        f"📄 Generando cotización para *{patient_name}*...", parse_mode="Markdown"
    )
    try:
        import time
        unique_id = f"{chat_id}_{int(time.time())}"
        pdf_path = await create_quote_pdf(ia_json, patient_name, f"cotizacion_{unique_id}.pdf")
        internal_pdf_path = await create_quote_pdf(ia_json, patient_name, f"cotizacion_interna_{unique_id}.pdf", is_internal=True)
        await context.bot.delete_message(chat_id=chat_id, message_id=msg.message_id)

        with open(pdf_path, "rb") as f_ext, open(internal_pdf_path, "rb") as f_int:
            await context.bot.send_document(
                chat_id=chat_id,
                document=f_ext,
                filename=f"Cotizacion_{patient_name.replace(' ', '_')}.pdf",
                caption="✅ Adjunto la cotización oficial en PDF para el paciente."
            )
            await context.bot.send_document(
                chat_id=chat_id,
                document=f_int,
                filename=f"INTERNO_Laboratorio_{patient_name.replace(' ', '_')}.pdf",
                caption="🔒 Adjunto el reporte contable interno (Costo Maquila Desglosado)."
            )
        import os as _os
        _os.unlink(pdf_path)
        _os.unlink(internal_pdf_path)

        try:
            await save_cotizacion(
                chat_id,
                patient_name,
                ia_json["cotizacion"],
                ia_json["total"],
                ia_json.get("total_min", 0),
            )
        except Exception as db_err:
            print("DB audit error (non-fatal):", db_err)

        context.user_data.clear()

    except Exception as e:
        print("Error PDF:", e)
        import traceback; traceback.print_exc()
        await context.bot.delete_message(chat_id=chat_id, message_id=msg.message_id)
        await update.message.reply_text("❌ Error al generar el PDF. Revisa la consola.")

    return ESPERANDO_ESTUDIOS

# ─────────────────────────────────────────────────────────────
# /cancel
# ─────────────────────────────────────────────────────────────
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Cancelado. 🔄 Escríbeme nuevos estudios cuando quieras.")
    context.user_data.clear()
    return ESPERANDO_ESTUDIOS

# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────
async def _post_init(application: Application) -> None:
    await init_db()


def main():
    print("🚀 Levantando Bot OPLAB...")
    app = ApplicationBuilder().token(settings.TELEGRAM_BOT_TOKEN).post_init(_post_init).build()

    text_filter  = filters.TEXT & (~filters.COMMAND)
    voice_filter = filters.VOICE

    conv = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(text_filter, handle_studies_query),
            MessageHandler(voice_filter, handle_voice_message),
        ],
        states={
            ESPERANDO_ESTUDIOS: [
                MessageHandler(text_filter, handle_studies_query),
                MessageHandler(voice_filter, handle_voice_message),
            ],
            ESPERANDO_ACLARACION: [
                MessageHandler(text_filter, handle_aclaracion),
                MessageHandler(voice_filter, handle_voice_message),
            ],
            ESPERANDO_DESCARTE: [
                MessageHandler(text_filter, handle_descarte),
                MessageHandler(voice_filter, handle_voice_message),
            ],
            ESPERANDO_NOMBRE: [
                MessageHandler(text_filter, handle_patient_name),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )

    app.add_handler(conv)
    print("🟢 Bot listo: texto ✍️ | voz 🎤 | ambigüedad 🔎 | descarte 🗑️")
    app.run_polling()

if __name__ == "__main__":
    main()
