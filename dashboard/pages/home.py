"""Home — KPIs grandes, agenda de hoy, sugerencias proactivas."""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import streamlit as st

from db import SessionLocal, Event, User
from theme import inject_css, COLORS, CATEGORY_COLORS, CATEGORY_LABELS


inject_css()
telegram_id = st.session_state.get("telegram_id")
if not telegram_id:
    st.error("Sesión expirada"); st.stop()


# ── Datos ─────────────────────────────────────────────────────────
with SessionLocal() as db:
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    tz = ZoneInfo(user.timezone if user and user.timezone else "America/Mexico_City")
    now_local = datetime.now(tz)
    now_utc   = datetime.utcnow()

    today_start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end_local   = now_local.replace(hour=23, minute=59, second=59)
    today_start_utc   = today_start_local.astimezone(timezone.utc).replace(tzinfo=None)
    today_end_utc     = today_end_local.astimezone(timezone.utc).replace(tzinfo=None)

    # KPI 1: Eventos pendientes hoy
    today_count = db.query(Event).filter(
        Event.user_telegram_id == telegram_id,
        Event.start_datetime >= today_start_utc,
        Event.start_datetime <= today_end_utc,
        Event.status == "pending",
    ).count()

    # KPI 2: Completados últimos 7 días
    week_start = now_utc - timedelta(days=7)
    completed_week = db.query(Event).filter(
        Event.user_telegram_id == telegram_id,
        Event.status == "completed",
        Event.start_datetime >= week_start,
    ).count()

    # KPI 3: Pendientes totales
    pending_total = db.query(Event).filter(
        Event.user_telegram_id == telegram_id,
        Event.status == "pending",
    ).count()

    # KPI 4: Streak (días consecutivos hasta hoy con ≥1 completado)
    last_30 = db.query(Event).filter(
        Event.user_telegram_id == telegram_id,
        Event.status == "completed",
        Event.start_datetime >= now_utc - timedelta(days=30),
    ).all()
    completed_dates = {e.start_datetime.date() for e in last_30}
    streak = 0
    cursor = now_utc.date()
    while cursor in completed_dates:
        streak += 1
        cursor -= timedelta(days=1)

    # Eventos de hoy (lista)
    today_events = db.query(Event).filter(
        Event.user_telegram_id == telegram_id,
        Event.start_datetime >= today_start_utc,
        Event.start_datetime <= today_end_utc,
        Event.status == "pending",
    ).order_by(Event.start_datetime).all()

    # Próximos eventos (después de hoy, próximos 30 días)
    horizon = now_utc + timedelta(days=30)
    upcoming_events = db.query(Event).filter(
        Event.user_telegram_id == telegram_id,
        Event.start_datetime > today_end_utc,
        Event.start_datetime <= horizon,
        Event.status == "pending",
    ).order_by(Event.start_datetime).limit(5).all()

    # Distribución por categoría (todos los pendientes)
    all_pending = db.query(Event).filter(
        Event.user_telegram_id == telegram_id,
        Event.status == "pending",
    ).all()
    cat_counts: dict[str, int] = {}
    for e in all_pending:
        cat_counts[e.category or "otros"] = cat_counts.get(e.category or "otros", 0) + 1


# ── Render ─────────────────────────────────────────────────────────
st.markdown("# Inicio")
saludo_dia = now_local.strftime("%A, %d de %B").capitalize()
st.markdown(f'<p class="subhead">{saludo_dia}</p>', unsafe_allow_html=True)

# KPI grid (4 columnas)
def kpi_card(label, value, delta):
    return (
        f'<div class="kpi-card">'
        f'<div class="kpi-label">{label}</div>'
        f'<div class="kpi-value">{value}</div>'
        f'<div class="kpi-delta">{delta}</div>'
        f'</div>'
    )

c1, c2, c3, c4 = st.columns(4, gap="medium")
c1.markdown(kpi_card("Hoy",        str(today_count),    "eventos pendientes"), unsafe_allow_html=True)
c2.markdown(kpi_card("Semana",     str(completed_week), "completados (7 días)"), unsafe_allow_html=True)
c3.markdown(kpi_card("Pendientes", str(pending_total),  "totales"), unsafe_allow_html=True)
c4.markdown(kpi_card("Racha",      str(streak),         f"día{'s' if streak != 1 else ''} seguidos"), unsafe_allow_html=True)


# ── Agenda de hoy ──────────────────────────────────────────────────
st.markdown("## Agenda de hoy")

if not today_events:
    st.markdown(
        '<div class="empty">Sin eventos pendientes. Día libre.</div>',
        unsafe_allow_html=True,
    )
else:
    for ev in today_events:
        local_dt = ev.start_datetime.replace(tzinfo=timezone.utc).astimezone(tz)
        hora     = local_dt.strftime("%I:%M %p").lstrip("0")
        cat      = (ev.category or "otros")
        cat_color = CATEGORY_COLORS.get(cat, COLORS["ink_muted"])
        cat_label = CATEGORY_LABELS.get(cat, "Otros")

        meta = []
        if ev.location:        meta.append(ev.location)
        if ev.attendees:       meta.append(f"con {ev.attendees}")
        if ev.recurrence_rule:
            from recurrence_helper import describe_rule
            meta.append(describe_rule(ev.recurrence_rule))
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


# ── Próximos eventos (después de hoy) ──────────────────────────────
if upcoming_events:
    st.markdown("## Próximos")
    from recurrence_helper import describe_rule
    for ev in upcoming_events:
        local_dt = ev.start_datetime.replace(tzinfo=timezone.utc).astimezone(tz)
        fecha    = local_dt.strftime("%a %d/%m · %I:%M %p").lstrip("0")
        cat      = ev.category or "otros"
        cat_color = CATEGORY_COLORS.get(cat, COLORS["ink_muted"])
        cat_label = CATEGORY_LABELS.get(cat, "Otros")
        meta = [cat_label]
        if ev.recurrence_rule:
            meta.append(describe_rule(ev.recurrence_rule))
        meta_text = " · ".join(meta)

        st.markdown(
            f'<div class="event-card">'
            f'<div class="event-time">{fecha}</div>'
            f'<div class="event-title">'
            f'<span class="cat-dot" style="background:{cat_color}"></span>{ev.title}'
            f'</div>'
            f'<div class="event-meta">{meta_text}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


# ── Distribución por categoría ─────────────────────────────────────
if cat_counts and sum(cat_counts.values()) > 0:
    st.markdown("## Por categoría")
    total = sum(cat_counts.values())
    sorted_cats = sorted(cat_counts.items(), key=lambda x: -x[1])
    for cat, n in sorted_cats:
        color = CATEGORY_COLORS.get(cat, COLORS["ink_muted"])
        label = CATEGORY_LABELS.get(cat, "Otros")
        pct = int(n / total * 100)
        st.markdown(
            f'<div style="display:flex;align-items:center;justify-content:space-between;'
            f'padding:10px 16px;background:#FFFFFF;border:1px solid {COLORS["border"]};'
            f'border-radius:10px;margin-bottom:6px;">'
            f'<span><span class="cat-dot" style="background:{color}"></span>{label}</span>'
            f'<span style="font-family:JetBrains Mono;font-variant-numeric:tabular-nums;'
            f'color:{COLORS["ink_soft"]};font-size:13px;">'
            f'<strong style="color:{COLORS["ink"]};">{n}</strong> · {pct}%'
            f'</span>'
            f'</div>',
            unsafe_allow_html=True,
        )


# ── Sugerencias proactivas ─────────────────────────────────────────
st.markdown("## Sugerencias")

# Re-implementa analyze_patterns con el modelo local (sin importar el bot)
def _analyze(telegram_id: str) -> list[str]:
    from sqlalchemy import func
    out = []
    with SessionLocal() as db:
        # Recurrencia detectada
        cutoff_90d = datetime.utcnow() - timedelta(days=90)
        recientes = db.query(Event).filter(
            Event.user_telegram_id == telegram_id,
            Event.created_at >= cutoff_90d,
            Event.recurrence_rule.is_(None),
        ).all()
        counts = {}
        for e in recientes:
            k = e.title.strip().lower()
            counts[k] = counts.get(k, 0) + 1
        for k, n in counts.items():
            if n >= 3:
                original = next((e.title for e in recientes if e.title.strip().lower() == k), k)
                out.append(f"<strong>{original}</strong> creado {n} veces en 90 días — podrías hacerlo recurrente.")

        # Stale > 7 días
        stale = db.query(Event).filter(
            Event.user_telegram_id == telegram_id,
            Event.status == "pending",
            Event.start_datetime < datetime.utcnow() - timedelta(days=7),
        ).count()
        if stale >= 3:
            out.append(f"<strong>{stale} tareas</strong> pendientes desde hace más de una semana.")

        # Streak
        last_week = db.query(Event).filter(
            Event.user_telegram_id == telegram_id,
            Event.start_datetime >= datetime.utcnow() - timedelta(days=7),
        ).all()
        if len(last_week) >= 5:
            done = sum(1 for e in last_week if e.status == "completed")
            ratio = done / len(last_week)
            if ratio >= 0.7:
                out.append(f"Excelente racha: <strong>{done} de {len(last_week)}</strong> eventos completados ({int(ratio * 100)}%).")
    return out


tips = _analyze(telegram_id)
if not tips:
    st.markdown(
        '<div class="empty">No hay patrones que destacar. Todo en orden.</div>',
        unsafe_allow_html=True,
    )
else:
    for t in tips:
        st.markdown(f'<div class="tip-card">{t}</div>', unsafe_allow_html=True)
