"""Notas — listado, busqueda, crear y editar las notas del usuario."""
from datetime import datetime, timezone
from html import escape
from zoneinfo import ZoneInfo

import streamlit as st

from db import SessionLocal, Note, User
from theme import inject_css, COLORS, CATEGORY_COLORS, CATEGORY_LABELS


inject_css()
telegram_id = st.session_state.get("telegram_id")
if not telegram_id:
    st.error("Sesión expirada"); st.stop()


# ── Diálogo: Nueva / editar nota ───────────────────────────────────
@st.dialog("Nueva nota", width="large")
def _crear_nota_dialog():
    title    = st.text_input("Título", placeholder="Ej: Wifi de la oficina", max_chars=200)
    content  = st.text_area("Contenido", placeholder="Escribe lo que quieres recordar...", height=160)
    cat      = st.selectbox(
        "Categoría",
        list(CATEGORY_LABELS.keys()),
        index=list(CATEGORY_LABELS.keys()).index("personal"),
        format_func=lambda x: CATEGORY_LABELS[x],
    )
    tags     = st.text_input("Etiquetas (opcional)", placeholder="wifi, oficina, contraseña")

    st.markdown("&nbsp;", unsafe_allow_html=True)
    col_a, col_b = st.columns([1, 1])
    with col_a:
        cancel = st.button("Cancelar", use_container_width=True)
    with col_b:
        guardar = st.button("Guardar nota", type="primary", use_container_width=True)

    if cancel:
        st.rerun()
    if guardar:
        if not title.strip() or not content.strip():
            st.error("El título y el contenido son obligatorios.")
            return
        with SessionLocal() as db:
            n = Note(
                user_telegram_id=telegram_id,
                title=title.strip()[:200],
                content=content.strip(),
                category=cat,
                tags=tags.strip() or None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(n)
            db.commit()
        st.success("Nota guardada.")
        st.rerun()


@st.dialog("Editar nota", width="large")
def _editar_nota_dialog(note_id: int):
    with SessionLocal() as db:
        note = db.query(Note).filter(Note.id == note_id, Note.user_telegram_id == telegram_id).first()
        if not note:
            st.error("La nota ya no existe.")
            return
        # Cargar valores
        title_default    = note.title
        content_default  = note.content
        cat_default      = note.category or "otros"
        tags_default     = note.tags or ""

    title   = st.text_input("Título", value=title_default, max_chars=200)
    content = st.text_area("Contenido", value=content_default, height=180)
    cat     = st.selectbox(
        "Categoría",
        list(CATEGORY_LABELS.keys()),
        index=list(CATEGORY_LABELS.keys()).index(cat_default if cat_default in CATEGORY_LABELS else "otros"),
        format_func=lambda x: CATEGORY_LABELS[x],
    )
    tags    = st.text_input("Etiquetas", value=tags_default)

    st.markdown("&nbsp;", unsafe_allow_html=True)
    col_a, col_b, col_c = st.columns([1, 1, 1])
    with col_a:
        cancel = st.button("Cancelar", use_container_width=True, key="ed_cancel")
    with col_b:
        delete = st.button("🗑️ Borrar", use_container_width=True, key="ed_delete")
    with col_c:
        guardar = st.button("Guardar", type="primary", use_container_width=True, key="ed_save")

    if cancel:
        st.rerun()
    if delete:
        with SessionLocal() as db:
            n = db.query(Note).filter(Note.id == note_id, Note.user_telegram_id == telegram_id).first()
            if n:
                n.archived = True
                db.commit()
        st.success("Nota borrada.")
        st.rerun()
    if guardar:
        if not title.strip() or not content.strip():
            st.error("El título y el contenido son obligatorios.")
            return
        with SessionLocal() as db:
            n = db.query(Note).filter(Note.id == note_id, Note.user_telegram_id == telegram_id).first()
            if n:
                n.title    = title.strip()[:200]
                n.content  = content.strip()
                n.category = cat
                n.tags     = tags.strip() or None
                n.updated_at = datetime.utcnow()
                db.commit()
        st.success("Nota actualizada.")
        st.rerun()


# ── Datos ──────────────────────────────────────────────────────────
with SessionLocal() as db:
    user = db.query(User).filter(User.telegram_id == telegram_id).first()
    tz = ZoneInfo(user.timezone if user and user.timezone else "America/Mexico_City")
    notas_all = (
        db.query(Note)
        .filter(Note.user_telegram_id == telegram_id, Note.archived == False)
        .order_by(Note.created_at.desc())
        .all()
    )


# ── Render ─────────────────────────────────────────────────────────
st.markdown("# Notas")
st.markdown(
    f'<p class="subhead">{len(notas_all)} nota{"s" if len(notas_all) != 1 else ""} guardada{"s" if len(notas_all) != 1 else ""}</p>',
    unsafe_allow_html=True,
)

# Acciones de cabecera
col_btn, col_search, col_cat = st.columns([1.2, 2.5, 2])
with col_btn:
    if st.button("＋  Nueva nota", use_container_width=True, type="primary"):
        _crear_nota_dialog()
with col_search:
    busqueda = st.text_input(
        " ",
        placeholder="Buscar en notas...",
        label_visibility="collapsed",
    )
with col_cat:
    cat_options = ["Todas"] + list(CATEGORY_LABELS.values())
    cat_filter = st.selectbox(
        " ", cat_options, label_visibility="collapsed", key="cat_filter"
    )

# Filtros
def _matches(n: Note) -> bool:
    if busqueda:
        q = busqueda.strip().lower()
        bag = " ".join([
            (n.title or "").lower(),
            (n.content or "").lower(),
            (n.tags or "").lower(),
        ])
        if q not in bag:
            return False
    if cat_filter != "Todas":
        # Mapear label → key
        key_map = {v: k for k, v in CATEGORY_LABELS.items()}
        target = key_map.get(cat_filter, "otros")
        if (n.category or "otros") != target:
            return False
    return True


notas = [n for n in notas_all if _matches(n)]


# ── Lista de notas ─────────────────────────────────────────────────
if not notas_all:
    st.markdown(
        '<div class="empty">Aún no tienes notas. Pulsa <strong>+ Nueva nota</strong> '
        'o pídele a CAMSI desde Telegram: <em>"Anota que el wifi es 1234"</em>.</div>',
        unsafe_allow_html=True,
    )
elif not notas:
    st.markdown(
        '<div class="empty">Ninguna nota coincide con tu búsqueda.</div>',
        unsafe_allow_html=True,
    )
else:
    # Render como cards. Cada card es clickeable para editar.
    for n in notas:
        cat       = n.category or "otros"
        cat_color = CATEGORY_COLORS.get(cat, COLORS["ink_muted"])
        cat_label = CATEGORY_LABELS.get(cat, "Otros")
        creada    = (
            n.created_at.replace(tzinfo=timezone.utc).astimezone(tz).strftime("%d/%m %I:%M %p")
            if n.created_at else ""
        )

        # Truncar contenido para preview
        preview = n.content or ""
        if len(preview) > 320:
            preview = preview[:317] + "..."

        tags_html = ""
        if n.tags:
            tags_html = (
                '<div style="margin-top:8px">'
                + "".join(
                    f'<span style="display:inline-block;font-size:11px;padding:2px 9px;'
                    f'border-radius:999px;background:#F4F4F5;color:#525252;margin-right:4px">'
                    f'{escape(t.strip())}</span>'
                    for t in (n.tags or "").split(",") if t.strip()
                )
                + "</div>"
            )

        # Render del card
        st.markdown(
            f'<div class="event-card" style="margin-bottom:12px">'
            f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:6px">'
            f'<span class="cat-dot" style="background:{cat_color}"></span>'
            f'<span style="font-size:11px;color:#A3A3A3;text-transform:uppercase;letter-spacing:0.05em">'
            f'{cat_label} · {creada}</span>'
            f'</div>'
            f'<div class="event-title" style="margin-top:0;font-size:16px;font-weight:600">'
            f'{escape(n.title)}</div>'
            f'<div class="event-meta" style="color:#525252;font-size:14px;margin-top:8px;'
            f'line-height:1.55;white-space:pre-wrap">{escape(preview)}</div>'
            f'{tags_html}'
            f'</div>',
            unsafe_allow_html=True,
        )

        # Botones debajo del card
        col_edit, col_space = st.columns([1, 5])
        with col_edit:
            if st.button("✏️ Editar", key=f"edit_{n.id}", use_container_width=True):
                _editar_nota_dialog(n.id)
