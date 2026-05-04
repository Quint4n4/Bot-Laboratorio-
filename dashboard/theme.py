"""
theme.py — Paleta y estilos del dashboard ARIA
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
#MainMenu, footer, header[data-testid="stHeader"] { visibility: hidden; height: 0; }

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
</style>
"""


def inject_css():
    """Llama una sola vez al inicio de cada página."""
    import streamlit as st
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)
