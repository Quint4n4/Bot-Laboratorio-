"""
theme.py — Paleta y estilos del dashboard CAMSI
Diseño: Exaggerated Minimalism + monocromo + un solo acento.
Typography: Inter (UI) + JetBrains Mono (números tabulares).
"""

# ── Paleta principal: monocromo + 1 acento ──────────────────────────
COLORS = {
    "bg":          "#FAFAFA",   # Background suave
    "surface":     "#FFFFFF",   # Cards, paneles
    "border":      "#E5E5E5",   # Bordes sutiles
    "border_soft": "#F0F0F0",   # Gridlines en charts
    "ink":         "#0A0A0A",   # Texto primario (casi negro)
    "ink_soft":    "#525252",   # Texto secundario
    "ink_muted":   "#A3A3A3",   # Captions, helpers
    "accent":      "#3B82F6",   # Único acento — links, KPIs destacados
}

# ── Categorías: dots de color para identificación rápida ────────────
# Tonos low-saturation, suficiente contraste, accesibles
CATEGORY_COLORS = {
    "personal": "#6366F1",  # indigo
    "trabajo":  "#0891B2",  # cyan
    "salud":    "#DC2626",  # rojo
    "finanzas": "#16A34A",  # verde
    "familia":  "#DB2777",  # rosa
    "social":   "#EA580C",  # naranja
    "otros":    "#71717A",  # gris
}

CATEGORY_LABELS = {
    "personal": "Personal",
    "trabajo":  "Trabajo",
    "salud":    "Salud",
    "finanzas": "Finanzas",
    "familia":  "Familia",
    "social":   "Social",
    "otros":    "Otros",
}


# ── CSS global inyectado en todas las páginas ───────────────────────
GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

/* Base */
html, body, [class*="css"], .main {
    font-family: 'Inter', system-ui, -apple-system, sans-serif !important;
    color: #0A0A0A;
    background: #FAFAFA;
    -webkit-font-smoothing: antialiased;
}

/* Hide Streamlit chrome para look pro */
#MainMenu, footer { visibility: hidden; height: 0; }

/* Header transparente pero NO oculto, asi se mantiene el toggle del sidebar visible */
header[data-testid="stHeader"] {
    background: transparent !important;
    box-shadow: none !important;
}

/* Asegurar que el control de colapsar/expandir el sidebar siempre sea visible */
[data-testid="collapsedControl"],
button[kind="header"] {
    display: block !important;
    visibility: visible !important;
    opacity: 1 !important;
}

/* Container principal: mucho whitespace */
.block-container {
    padding-top: 3rem !important;
    padding-bottom: 5rem !important;
    max-width: 1100px;
}

/* Headings: jerarquía por tamaño y peso, no por color */
h1 {
    font-weight: 700 !important;
    letter-spacing: -0.025em;
    font-size: 2.5rem !important;
    line-height: 1.1;
    color: #0A0A0A;
    margin-bottom: 0.25em !important;
}
h2 {
    font-weight: 600 !important;
    letter-spacing: -0.015em;
    font-size: 1.5rem !important;
    color: #0A0A0A;
    margin-top: 2.5rem !important;
    margin-bottom: 1rem !important;
}
h3 {
    font-weight: 500 !important;
    font-size: 1rem !important;
    color: #525252;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

p, li, div { color: #0A0A0A; }
.subhead { color: #525252; font-size: 1rem; margin-top: -8px; margin-bottom: 1.5rem; }

/* Fix: la regla universal de arriba pinta el texto interno de los botones de
   negro, lo cual los deja invisibles sobre el fondo negro del primary.
   Forzar el color correcto en todo el contenido interno del boton.        */
.stButton button[kind="primary"],
.stButton button[kind="primary"] *,
.stButton button[kind="primary"] p,
.stButton button[kind="primary"] div,
.stButton button[kind="primary"] span {
    color: #FFFFFF !important;
}
.stButton button[kind="secondary"],
.stButton button[kind="secondary"] *,
.stButton button[kind="secondary"] p,
.stButton button[kind="secondary"] div,
.stButton button[kind="secondary"] span {
    color: #0A0A0A !important;
}

/* ── KPI cards ──────────────────────────────────────── */
.kpi-card {
    background: #FFFFFF;
    border: 1px solid #E5E5E5;
    border-radius: 14px;
    padding: 24px 28px;
    height: 100%;
    transition: border-color 200ms ease;
}
.kpi-card:hover { border-color: #0A0A0A; }
.kpi-label {
    font-size: 11px;
    font-weight: 500;
    color: #525252;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 12px;
}
.kpi-value {
    font-family: 'JetBrains Mono', ui-monospace, monospace;
    font-size: 40px;
    font-weight: 600;
    color: #0A0A0A;
    font-variant-numeric: tabular-nums;
    line-height: 1;
}
.kpi-delta {
    font-size: 13px;
    color: #A3A3A3;
    margin-top: 12px;
    font-weight: 400;
}

/* ── Event cards ────────────────────────────────────── */
.event-card {
    background: #FFFFFF;
    border: 1px solid #E5E5E5;
    border-radius: 12px;
    padding: 18px 22px;
    margin-bottom: 10px;
    transition: border-color 200ms ease;
}
.event-card:hover { border-color: #0A0A0A; }
.event-time {
    font-family: 'JetBrains Mono', monospace;
    font-size: 13px;
    font-weight: 500;
    color: #525252;
    font-variant-numeric: tabular-nums;
    letter-spacing: 0.02em;
}
.event-title {
    font-size: 16px;
    font-weight: 500;
    color: #0A0A0A;
    margin-top: 6px;
    line-height: 1.4;
}
.event-meta {
    font-size: 13px;
    color: #A3A3A3;
    margin-top: 6px;
}
.cat-dot {
    display: inline-block;
    width: 8px; height: 8px;
    border-radius: 50%;
    margin-right: 10px;
    vertical-align: middle;
}
.cat-pill {
    display: inline-block;
    font-size: 11px;
    padding: 3px 10px;
    border-radius: 999px;
    font-weight: 500;
    letter-spacing: 0.02em;
    text-transform: lowercase;
    color: #FFFFFF;
}

/* ── Suggestions card ──────────────────────────────── */
.tip-card {
    background: #FFFFFF;
    border: 1px solid #E5E5E5;
    border-radius: 12px;
    padding: 18px 22px;
    margin-bottom: 10px;
    color: #0A0A0A;
    line-height: 1.55;
    font-size: 14px;
}
.tip-card strong { color: #0A0A0A; font-weight: 600; }

/* ── Chat bubbles ──────────────────────────────────── */
.chat-row { display: flex; margin-bottom: 12px; align-items: flex-start; }
.chat-row.user { justify-content: flex-end; }
.chat-bubble {
    max-width: 75%;
    padding: 12px 18px;
    border-radius: 16px;
    font-size: 14px;
    line-height: 1.5;
}
.chat-bubble.user {
    background: #0A0A0A;
    color: #FAFAFA;
    border-bottom-right-radius: 4px;
}
.chat-bubble.assistant {
    background: #FFFFFF;
    color: #0A0A0A;
    border: 1px solid #E5E5E5;
    border-bottom-left-radius: 4px;
}
.chat-time {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px;
    color: #A3A3A3;
    margin-top: 4px;
    font-variant-numeric: tabular-nums;
}

/* ── Streamlit overrides ───────────────────────────── */
.stTabs [data-baseweb="tab-list"] { gap: 4px; border-bottom: none; margin-bottom: 1.5rem; }
.stTabs [data-baseweb="tab"] {
    padding: 8px 18px;
    font-size: 14px;
    font-weight: 500;
    background: transparent !important;
    border-radius: 999px;
    color: #525252;
    border: 1px solid transparent;
}
.stTabs [aria-selected="true"] {
    background: #0A0A0A !important;
    color: #FFFFFF !important;
}

.stRadio > div { gap: 8px; flex-wrap: wrap; }
.stRadio label {
    background: #FFFFFF;
    border: 1px solid #E5E5E5;
    border-radius: 999px;
    padding: 6px 14px !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    cursor: pointer;
    transition: all 150ms ease;
}

/* Botones primarios: negro tinta, no azul */
.stButton button[kind="primary"] {
    background: #0A0A0A !important;
    color: #FFFFFF !important;
    border: 1px solid #0A0A0A !important;
    border-radius: 10px !important;
    padding: 10px 18px !important;
    font-weight: 500 !important;
    font-size: 14px !important;
    transition: opacity 150ms ease;
}
.stButton button[kind="primary"]:hover {
    background: #525252 !important;
    border-color: #525252 !important;
    opacity: 1 !important;
}
.stButton button[kind="secondary"] {
    background: #FFFFFF !important;
    color: #0A0A0A !important;
    border: 1px solid #E5E5E5 !important;
    border-radius: 10px !important;
    padding: 10px 18px !important;
    font-weight: 500 !important;
    font-size: 14px !important;
}
.stButton button[kind="secondary"]:hover {
    border-color: #0A0A0A !important;
}

/* Form inputs limpios */
.stTextInput input, .stTextArea textarea, .stSelectbox > div, .stDateInput input, .stTimeInput input {
    border-radius: 10px !important;
    border-color: #E5E5E5 !important;
    font-size: 14px !important;
}
.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: #0A0A0A !important;
    box-shadow: none !important;
}

/* Modal/Dialog */
[data-testid="stDialog"] {
    border-radius: 16px !important;
}

/* Expanders como cards minimalistas */
[data-testid="stExpander"] {
    background: #FFFFFF;
    border: 1px solid #E5E5E5 !important;
    border-radius: 10px !important;
    margin-bottom: 8px !important;
    transition: border-color 200ms ease;
    box-shadow: none !important;
}
[data-testid="stExpander"]:hover { border-color: #0A0A0A !important; }
[data-testid="stExpander"] summary {
    padding: 14px 18px !important;
    font-size: 14px !important;
    font-weight: 500 !important;
    color: #0A0A0A !important;
    font-family: 'JetBrains Mono', monospace;
    font-variant-numeric: tabular-nums;
    letter-spacing: 0.01em;
}
[data-testid="stExpander"] summary:hover { color: #0A0A0A !important; }
[data-testid="stExpander"] details[open] summary {
    border-bottom: 1px solid #F0F0F0;
}
[data-testid="stExpander"] [data-testid="stExpanderDetails"] {
    padding: 0 18px 12px 18px !important;
}
[data-testid="stExpander"] svg { color: #A3A3A3 !important; }

hr {
    border: none;
    border-top: 1px solid #E5E5E5;
    margin: 2.5rem 0 !important;
}

/* Scrollbar refinada */
::-webkit-scrollbar { width: 8px; height: 8px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #E5E5E5; border-radius: 4px; }
::-webkit-scrollbar-thumb:hover { background: #A3A3A3; }

/* Empty state */
.empty {
    text-align: center;
    padding: 48px 24px;
    color: #A3A3A3;
    font-size: 14px;
    background: #FFFFFF;
    border: 1px dashed #E5E5E5;
    border-radius: 12px;
}

/* Reduced motion */
@media (prefers-reduced-motion: reduce) {
    * { transition: none !important; animation: none !important; }
}

/* ════════════════════════════════════════════════════════════
   RESPONSIVE — Movil
   Estrategia: sidebar como drawer SIEMPRE expandido por defecto,
   superpuesto al contenido. En lugar de pelear con el toggle nativo
   de Streamlit (cuyo selector cambia entre versiones), forzamos:
   1) sidebar visible al cargar
   2) cuando el usuario lo colapsa, queda completamente oculto
   3) un toggle FORCED VISIBLE con varios selectores como respaldo
   ════════════════════════════════════════════════════════════ */
@media (max-width: 768px) {
    /* Container principal con menos padding en movil */
    .block-container {
        padding-top: 1.2rem !important;
        padding-bottom: 3rem !important;
        padding-left: 1rem !important;
        padding-right: 1rem !important;
        max-width: 100% !important;
    }

    /* Tipografia mas chica para que entre */
    h1 {
        font-size: 1.9rem !important;
        line-height: 1.15;
    }
    h2 {
        font-size: 1.25rem !important;
        margin-top: 1.5rem !important;
    }

    /* KPI cards: una columna en lugar de 4 */
    .kpi-card {
        padding: 16px 18px;
        margin-bottom: 8px;
    }
    .kpi-value {
        font-size: 28px;
    }
    .kpi-label {
        font-size: 10px;
    }

    /* Cards de eventos / notas mas compactos */
    .event-card {
        padding: 14px 16px;
    }
    .event-title {
        font-size: 15px;
    }

    /* ─── Sidebar como DRAWER overlay ─────────────────────────────
       Cubre el contenido cuando esta abierto. Aria-expanded=true
       (default) lo muestra. False lo oculta totalmente.        */
    [data-testid="stSidebar"] {
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        width: 82vw !important;
        max-width: 320px !important;
        height: 100vh !important;
        height: 100dvh !important;
        z-index: 999 !important;
        background: #FFFFFF !important;
        box-shadow: 4px 0 24px rgba(0, 0, 0, 0.18) !important;
        border-right: 1px solid #E5E5E5 !important;
        transition: transform 250ms ease !important;
    }

    /* Sidebar expandido visible (default tras initial_sidebar_state=expanded) */
    [data-testid="stSidebar"][aria-expanded="true"] {
        transform: translateX(0) !important;
    }
    /* Sidebar colapsado: lo metemos fuera completamente */
    [data-testid="stSidebar"][aria-expanded="false"] {
        transform: translateX(-110%) !important;
    }

    /* ─── Toggle del sidebar (FORCED VISIBLE con multiples selectores)
       Streamlit cambia el data-testid entre versiones; aplicamos a varios. */
    [data-testid="collapsedControl"],
    [data-testid="stSidebarCollapsedControl"],
    [data-testid="stSidebarCollapseButton"],
    button[kind="header"],
    button[kind="headerNoPadding"] {
        position: fixed !important;
        top: 0.6rem !important;
        left: 0.6rem !important;
        z-index: 1000 !important;
        background: #0A0A0A !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 0 !important;
        width: 48px !important;
        height: 48px !important;
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        align-items: center !important;
        justify-content: center !important;
        box-shadow: 0 4px 14px rgba(0, 0, 0, 0.25) !important;
    }

    /* El icono interior del toggle blanco */
    [data-testid="collapsedControl"] svg,
    [data-testid="stSidebarCollapsedControl"] svg,
    button[kind="header"] svg {
        color: #FFFFFF !important;
        fill: #FFFFFF !important;
        stroke: #FFFFFF !important;
        width: 22px !important;
        height: 22px !important;
    }

    /* Espaciado superior en el contenido principal para que el toggle no tape */
    section[data-testid="stMain"] .block-container {
        padding-top: 4rem !important;
    }

    /* Forms y selects con altura adecuada para touch */
    .stTextInput input,
    .stTextArea textarea,
    .stSelectbox > div,
    .stDateInput input,
    .stTimeInput input {
        font-size: 16px !important; /* Evita que iOS haga zoom al focus */
        padding: 10px 12px !important;
    }

    /* Botones primarios mas grandes en movil */
    .stButton button {
        padding: 12px 18px !important;
        font-size: 15px !important;
        min-height: 44px !important;
    }

    /* Tabs sin padding lateral excesivo */
    .stTabs [data-baseweb="tab-list"] {
        overflow-x: auto;
        flex-wrap: nowrap !important;
    }

    /* Expanders (categorias) un poco mas compactos */
    [data-testid="stExpander"] summary {
        padding: 12px 14px !important;
        font-size: 13px !important;
    }
}

/* Celulares muy pequenos */
@media (max-width: 480px) {
    h1 { font-size: 1.6rem !important; }
    h2 { font-size: 1.1rem !important; }
    .kpi-value { font-size: 24px; }
    .block-container {
        padding-left: 0.7rem !important;
        padding-right: 0.7rem !important;
    }
}
</style>
"""


def inject_css():
    """Llama una sola vez al inicio de cada página."""
    import streamlit as st
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
