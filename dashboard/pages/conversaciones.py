"""Conversaciones — historial de chat con ARIA con búsqueda."""
from datetime import timezone
from zoneinfo import ZoneInfo
from html import escape

import streamlit as st

from db import SessionLocal, Message, User
from theme import inject_css, COLORS


inject_css()
telegram_id = st.session_state.get("telegram_id")
if not telegram_id:
    st.error("Sesión expirada"); st.stop()


with SessionLocal() as db:
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    tz = ZoneInfo(user.timezone if user and user.timezone else "America/Mexico_City")
    todos = (
        db.query(Message)
        .filter(Message.user_telegram_id == telegram_id)
        .order_by(Message.created_at.desc())
        .limit(200)
        .all()
    )
    todos.reverse()  # cronológico ascendente


# ── Render ─────────────────────────────────────────────────────────
st.markdown("# Conversaciones")
st.markdown(
    f'<p class="subhead">Últimos {len(todos)} mensajes con ARIA</p>',
    unsafe_allow_html=True,
)


# Búsqueda
busqueda = st.text_input(" ", placeholder="Buscar en la conversación…", label_visibility="collapsed")
if busqueda:
    busqueda_lc = busqueda.lower().strip()
    mostrados = [m for m in todos if busqueda_lc in m.content.lower()]
    st.markdown(
        f'<p class="subhead">{len(mostrados)} coincidencia{"s" if len(mostrados) != 1 else ""}</p>',
        unsafe_allow_html=True,
    )
else:
    mostrados = todos


if not mostrados:
    st.markdown('<div class="empty">No hay mensajes que mostrar.</div>', unsafe_allow_html=True)
else:
    fecha_actual = None
    for msg in mostrados:
        # Header de fecha cuando cambia
        if msg.created_at:
            local_dt = msg.created_at.replace(tzinfo=timezone.utc).astimezone(tz)
            fecha = local_dt.date()
            if fecha != fecha_actual:
                fecha_actual = fecha
                label = local_dt.strftime("%A %d/%m").capitalize()
                st.markdown(
                    f'<p style="text-align:center;color:{COLORS["ink_muted"]};font-size:12px;'
                    f'margin:24px 0 12px 0;letter-spacing:0.05em;text-transform:uppercase;">'
                    f'{label}</p>',
                    unsafe_allow_html=True,
                )
            time_str = local_dt.strftime("%I:%M %p").lstrip("0")
        else:
            time_str = ""

        role = "user" if msg.role == "user" else "assistant"
        contenido = escape(msg.content).replace("\n", "<br>")
        st.markdown(
            f'<div class="chat-row {role}">'
            f'<div>'
            f'<div class="chat-bubble {role}">{contenido}</div>'
            f'<div class="chat-time" style="text-align:{"right" if role == "user" else "left"};">'
            f'{time_str}</div>'
            f'</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
