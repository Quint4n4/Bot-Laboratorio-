"""Completados — historial de eventos terminados con heatmap por día."""
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import streamlit as st
import plotly.graph_objects as go

from db import SessionLocal, Event, User
from theme import inject_css, COLORS, CATEGORY_COLORS, CATEGORY_LABELS


inject_css()
telegram_id = st.session_state.get("telegram_id")
if not telegram_id:
    st.error("Sesión expirada"); st.stop()


with SessionLocal() as db:
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    tz = ZoneInfo(user.timezone if user and user.timezone else "America/Mexico_City")
    cutoff = datetime.utcnow() - timedelta(days=60)
    completados = db.query(Event).filter(
        Event.user_telegram_id == telegram_id,
        Event.status == "completed",
        Event.start_datetime >= cutoff,
    ).order_by(Event.start_datetime.desc()).all()


# ── Render header ──────────────────────────────────────────────────
st.markdown("# Completados")
st.markdown(
    f'<p class="subhead">Últimos 60 días — {len(completados)} eventos terminados</p>',
    unsafe_allow_html=True,
)


if not completados:
    st.markdown('<div class="empty">Aún no has completado ningún evento.</div>', unsafe_allow_html=True)
    st.stop()


# ── Gráfica de tendencia por día ───────────────────────────────────
por_dia = defaultdict(int)
hoy = datetime.utcnow().date()
for i in range(60):
    por_dia[hoy - timedelta(days=i)] = 0
for e in completados:
    d = e.start_datetime.date()
    if d in por_dia:
        por_dia[d] += 1

dias_ordenados = sorted(por_dia.keys())
xs = [d.strftime("%d/%m") for d in dias_ordenados]
ys = [por_dia[d] for d in dias_ordenados]

fig = go.Figure()
fig.add_trace(go.Bar(
    x=xs, y=ys,
    marker_color=COLORS["ink"],
    marker_line_width=0,
    hovertemplate="%{x}<br><b>%{y}</b> completados<extra></extra>",
))
fig.update_layout(
    plot_bgcolor=COLORS["surface"],
    paper_bgcolor=COLORS["surface"],
    font_family="Inter",
    font_color=COLORS["ink_soft"],
    margin=dict(l=20, r=20, t=20, b=40),
    height=240,
    showlegend=False,
    xaxis=dict(
        showgrid=False,
        tickfont_size=10,
        tickangle=-45,
        tickmode="array",
        tickvals=xs[::5],
    ),
    yaxis=dict(
        gridcolor=COLORS["border_soft"],
        gridwidth=1,
        zeroline=False,
        tickfont_size=10,
        tickfont_family="JetBrains Mono",
    ),
    bargap=0.4,
)
st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


# ── Distribución por categoría (rosquilla discreta) ────────────────
st.markdown("## Por categoría")

por_cat = defaultdict(int)
for e in completados:
    por_cat[e.category or "otros"] += 1

categorias_orden = [c for c in CATEGORY_LABELS if por_cat.get(c, 0) > 0]
labels = [CATEGORY_LABELS[c] for c in categorias_orden]
values = [por_cat[c] for c in categorias_orden]
colores = [CATEGORY_COLORS[c] for c in categorias_orden]

if categorias_orden:
    cols = st.columns([1, 1])
    with cols[0]:
        donut = go.Figure(data=[go.Pie(
            labels=labels, values=values, hole=0.65,
            marker=dict(colors=colores, line=dict(color="#FFFFFF", width=2)),
            textposition="outside",
            textinfo="label+percent",
            textfont=dict(family="Inter", size=12, color=COLORS["ink"]),
            hovertemplate="<b>%{label}</b><br>%{value} completados<extra></extra>",
        )])
        donut.update_layout(
            paper_bgcolor=COLORS["surface"],
            margin=dict(l=20, r=20, t=20, b=20),
            height=260,
            showlegend=False,
            annotations=[dict(
                text=f"<b>{sum(values)}</b><br><span style='font-size:11px;color:#A3A3A3'>total</span>",
                x=0.5, y=0.5, showarrow=False,
                font=dict(family="JetBrains Mono", size=22, color=COLORS["ink"]),
            )],
        )
        st.plotly_chart(donut, use_container_width=True, config={"displayModeBar": False})

    with cols[1]:
        for cat, cnt in sorted(por_cat.items(), key=lambda x: -x[1]):
            color = CATEGORY_COLORS.get(cat, COLORS["ink_muted"])
            label = CATEGORY_LABELS.get(cat, "Otros")
            st.markdown(
                f'<div style="display:flex;justify-content:space-between;align-items:center;'
                f'padding:10px 0;border-bottom:1px solid {COLORS["border_soft"]};">'
                f'<span><span class="cat-dot" style="background:{color}"></span>{label}</span>'
                f'<span style="font-family:JetBrains Mono;font-variant-numeric:tabular-nums;'
                f'font-weight:500;">{cnt}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )


# ── Lista de eventos completados ───────────────────────────────────
st.markdown("## Detalle")

# Agrupar por día
por_fecha = defaultdict(list)
for e in completados:
    local_dt = e.start_datetime.replace(tzinfo=timezone.utc).astimezone(tz)
    por_fecha[local_dt.date()].append((e, local_dt))

for fecha in sorted(por_fecha.keys(), reverse=True):
    label_dia = fecha.strftime("%A %d/%m").capitalize()
    st.markdown(f'<h3 style="margin-top:2rem;margin-bottom:0.75rem;">{label_dia}</h3>', unsafe_allow_html=True)
    for ev, local_dt in por_fecha[fecha]:
        hora      = local_dt.strftime("%I:%M %p").lstrip("0")
        cat       = ev.category or "otros"
        cat_color = CATEGORY_COLORS.get(cat, COLORS["ink_muted"])
        cat_label = CATEGORY_LABELS.get(cat, "Otros")
        st.markdown(
            f'<div class="event-card">'
            f'<div class="event-time">{hora}</div>'
            f'<div class="event-title">'
            f'<span class="cat-dot" style="background:{cat_color}"></span>{ev.title}'
            f'</div>'
            f'<div class="event-meta">{cat_label}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
