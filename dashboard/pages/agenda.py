"""Agenda — eventos próximos filtrables por categoría."""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import streamlit as st

from db import SessionLocal, Event, User
from theme import inject_css, COLORS, CATEGORY_COLORS, CATEGORY_LABELS


inject_css()
telegram_id = st.session_state.get("telegram_id")
if not telegram_id:
    st.error("Sesión expirada"); st.stop()


with SessionLocal() as db:
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    tz = ZoneInfo(user.timezone if user and user.timezone else "America/Mexico_City")
    now_utc = datetime.utcnow()
    horizon = now_utc + timedelta(days=30)

    todos = db.query(Event).filter(
        Event.user_telegram_id == telegram_id,
        Event.start_datetime >= now_utc,
        Event.start_datetime <= horizon,
        Event.status == "pending",
    ).order_by(Event.start_datetime).all()


# ── Render ─────────────────────────────────────────────────────────
st.markdown("# Agenda")
st.markdown(
    f'<p class="subhead">Próximos 30 días — {len(todos)} evento{"s" if len(todos) != 1 else ""}</p>',
    unsafe_allow_html=True,
)


# Conteo por categoría
counts = {cat: 0 for cat in CATEGORY_LABELS}
for e in todos:
    counts[e.category or "otros"] = counts.get(e.category or "otros", 0) + 1


# Filtro por categoría — pills horizontales
opciones = ["Todas"] + [
    f"{CATEGORY_LABELS[c]} · {counts[c]}"
    for c in CATEGORY_LABELS if counts[c] > 0
]
opcion_to_cat = {f"{CATEGORY_LABELS[c]} · {counts[c]}": c for c in CATEGORY_LABELS}

filtro = st.radio(" ", opciones, horizontal=True, label_visibility="collapsed")

if filtro == "Todas":
    eventos = todos
else:
    cat_seleccionada = opcion_to_cat[filtro]
    eventos = [e for e in todos if (e.category or "otros") == cat_seleccionada]


# Lista de eventos
if not eventos:
    st.markdown('<div class="empty">No hay eventos en esta categoría.</div>', unsafe_allow_html=True)
else:
    # Agrupar por día
    por_dia: dict[str, list] = {}
    for ev in eventos:
        local_dt = ev.start_datetime.replace(tzinfo=timezone.utc).astimezone(tz)
        clave = local_dt.strftime("%A %d/%m").capitalize()
        por_dia.setdefault(clave, []).append((ev, local_dt))

    for dia, items in por_dia.items():
        st.markdown(
            f'<h3 style="margin-top:2rem;margin-bottom:0.75rem;">{dia}</h3>',
            unsafe_allow_html=True,
        )
        for ev, local_dt in items:
            hora     = local_dt.strftime("%I:%M %p").lstrip("0")
            cat      = ev.category or "otros"
            cat_color = CATEGORY_COLORS.get(cat, COLORS["ink_muted"])
            cat_label = CATEGORY_LABELS.get(cat, "Otros")

            meta = []
            if ev.location:        meta.append(ev.location)
            if ev.attendees:       meta.append(f"con {ev.attendees}")
            if ev.recurrence_rule:
                from recurrence_helper import describe_rule
                meta.append(f"🔁 {describe_rule(ev.recurrence_rule)}")
            if ev.tags:            meta.append(ev.tags)
            meta_text = " · ".join(meta) if meta else cat_label

            st.markdown(
                f'<div class="event-card">'
                f'<div class="event-time">{hora}</div>'
                f'<div class="event-title">'
                f'<span class="cat-dot" style="background:{cat_color}"></span>{ev.title}'
                f'</div>'
                f'<div class="event-meta">{meta_text}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
