"""
CAMSI Dashboard — entry point.
Stack: Streamlit + SQLAlchemy + Plotly.
Auth: HMAC magic link generado por el bot.
"""
import streamlit as st

from auth import verify_token
from theme import inject_css


st.set_page_config(
    page_title="CAMSI — Dashboard",
    page_icon="●",
    layout="wide",
    initial_sidebar_state="auto",  # auto: abierto en desktop, cerrado en movil
)
inject_css()


# ── Validación del token ─────────────────────────────────────────
# El usuario llega vía /dashboard?token=...
qp = st.query_params
token = qp.get("token", "")

# Permitir reuso del token via session_state (para no perderlo entre paginas)
telegram_id = st.session_state.get("telegram_id")
if not telegram_id and token:
    telegram_id = verify_token(token)
    if telegram_id:
        st.session_state["telegram_id"] = telegram_id

if not telegram_id:
    # Pantalla de "no autorizado" — minimalista
    st.markdown("# Sesión no válida")
    st.markdown(
        '<p class="subhead">'
        'El enlace expiró o no es válido. Pídele a CAMSI un enlace nuevo '
        'escribiendo <code>/dashboard</code> en Telegram.'
        '</p>',
        unsafe_allow_html=True,
    )
    st.stop()


# ── Navegación ───────────────────────────────────────────────────
home           = st.Page("pages/home.py",           title="Inicio",         default=True)
agenda         = st.Page("pages/agenda.py",         title="Agenda")
notas          = st.Page("pages/notas.py",          title="Notas")
completados    = st.Page("pages/completados.py",    title="Completados")
conversaciones = st.Page("pages/conversaciones.py", title="Conversaciones")

pg = st.navigation([home, agenda, notas, completados, conversaciones], position="sidebar")
pg.run()
