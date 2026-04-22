"""
pdf_generator.py - Generación de reportes y resúmenes en PDF
Agenda Bot - Asistente Personal
Usa la fuente Arial del sistema Windows para soporte completo de Unicode.
"""
import os
import tempfile
from datetime import datetime
from fpdf import FPDF

# Fuentes del sistema Windows (soporte Unicode completo)
FONTS_DIR   = r"C:\Windows\Fonts"
FONT_NORMAL = os.path.join(FONTS_DIR, "arial.ttf")
FONT_BOLD   = os.path.join(FONTS_DIR, "arialbd.ttf")
FONT_ITALIC = os.path.join(FONTS_DIR, "ariali.ttf")

# Paleta de colores
BRAND_COLOR   = (41, 98, 255)
ACCENT_COLOR  = (16, 185, 129)
WARNING_COLOR = (245, 158, 11)
DANGER_COLOR  = (239, 68, 68)
BG_LIGHT      = (245, 247, 250)
BG_DARK       = (30, 41, 59)
TEXT_DARK     = (30, 41, 59)
TEXT_MUTED    = (100, 116, 139)
WHITE         = (255, 255, 255)

# Símbolos Unicode (disponibles con Arial)
ICON_OK       = "\u2713"   # ✓
ICON_PENDING  = "\u25cb"   # ○
ICON_CANCEL   = "\u2715"   # ✕
ICON_BULLET   = "\u2022"   # •
ICON_ARROW    = "\u279c"   # ➜
ICON_STAR     = "\u2605"   # ★
ICON_CLOCK    = "(@)"      # fallback reloj


def _fmt_time(iso_str: str) -> str:
    """Convierte ISO 8601 a formato 12h: 3:30 PM."""
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%I:%M %p").lstrip("0")
    except Exception:
        return iso_str


def _fmt_date_time(iso_str: str) -> str:
    """Convierte ISO 8601 a fecha + hora 12h: 21/04  3:30 PM."""
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%d/%m  %I:%M %p").lstrip("0")
    except Exception:
        return iso_str


class AgendaPDF(FPDF):
    def __init__(self, title: str):
        super().__init__()
        # Registrar fuentes Unicode
        self.add_font("Arial",  style="",  fname=FONT_NORMAL)
        self.add_font("Arial",  style="B", fname=FONT_BOLD)
        self.add_font("Arial",  style="I", fname=FONT_ITALIC)
        self.report_title = title
        self.set_auto_page_break(auto=True, margin=22)
        self.add_page()

    def header(self):
        # Barra superior
        self.set_fill_color(*BRAND_COLOR)
        self.rect(0, 0, 210, 20, "F")
        self.set_font("Arial", "B", 13)
        self.set_text_color(*WHITE)
        self.set_y(5)
        self.cell(0, 10, "ARIA  \u2014  Asistente de Agenda Personal", align="C")
        self.ln(22)

        # Titulo
        self.set_font("Arial", "B", 18)
        self.set_text_color(*BRAND_COLOR)
        self.cell(0, 10, self.report_title, align="C")
        self.ln(7)

        # Linea
        self.set_draw_color(*BRAND_COLOR)
        self.set_line_width(0.8)
        self.line(15, self.get_y(), 195, self.get_y())
        self.ln(6)

    def footer(self):
        self.set_y(-14)
        self.set_font("Arial", "I", 8)
        self.set_text_color(*TEXT_MUTED)
        self.cell(
            0, 8,
            f"Generado por ARIA  \u2014  {datetime.now().strftime('%d/%m/%Y  %I:%M %p')}  \u2014  P\u00e1gina {self.page_no()}",
            align="C",
        )

    def section_title(self, title: str):
        self.ln(2)
        self.set_fill_color(*BG_LIGHT)
        self.set_draw_color(*BRAND_COLOR)
        self.set_line_width(0)
        # Barra lateral de color
        self.set_fill_color(*BRAND_COLOR)
        self.rect(15, self.get_y(), 2, 8, "F")
        self.set_fill_color(*BG_LIGHT)
        self.rect(17, self.get_y(), 178, 8, "F")
        self.set_font("Arial", "B", 11)
        self.set_text_color(*TEXT_DARK)
        self.set_x(22)
        self.cell(0, 8, title, ln=True)
        self.ln(3)

    def stat_box(self, label: str, value: str, color: tuple, icon: str = ""):
        x_start = self.get_x()
        y_start = self.get_y()
        box_w, box_h = 58, 26

        # Sombra suave
        self.set_fill_color(220, 225, 235)
        self.rect(x_start + 1, y_start + 1, box_w, box_h, "F")

        # Caja principal
        self.set_fill_color(*color)
        self.rect(x_start, y_start, box_w, box_h, "F")

        # Número grande
        self.set_font("Arial", "B", 24)
        self.set_text_color(*WHITE)
        self.set_xy(x_start, y_start + 2)
        self.cell(box_w, 14, value, align="C")

        # Etiqueta
        self.set_font("Arial", "", 8)
        self.set_xy(x_start, y_start + 16)
        self.cell(box_w, 8, label.upper(), align="C")

        # Avanzar a la siguiente caja
        self.set_xy(x_start + box_w + 5, y_start)

    def event_row(self, icon: str, time_str: str, title: str, color: tuple, indent: int = 5):
        self.set_x(15 + indent)
        # Icono con color
        self.set_font("Arial", "B", 11)
        self.set_text_color(*color)
        self.cell(7, 7, icon)
        # Hora en gris
        self.set_font("Arial", "I", 9)
        self.set_text_color(*TEXT_MUTED)
        self.cell(28, 7, time_str)
        # Titulo del evento
        self.set_font("Arial", "", 10)
        self.set_text_color(*TEXT_DARK)
        self.cell(0, 7, title, ln=True)


# ---------------------------------------------------------------------------
# FUNCIONES EXPORTADAS
# ---------------------------------------------------------------------------

def generate_daily_briefing(events: list, user_name: str, date: datetime) -> str:
    """Genera el PDF con el briefing matutino del dia."""
    weekdays_es = {
        "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miercoles",
        "Thursday": "Jueves", "Friday": "Viernes", "Saturday": "Sabado", "Sunday": "Domingo",
    }
    day_name = weekdays_es.get(date.strftime("%A"), date.strftime("%A"))
    title = f"Buenos dias, {user_name}"
    pdf = AgendaPDF(title)

    # Subtitulo con fecha
    pdf.set_font("Arial", "I", 11)
    pdf.set_text_color(*TEXT_MUTED)
    pdf.cell(0, 6, f"{day_name} {date.strftime('%d/%m/%Y')}  \u2014  {len(events)} evento(s) programado(s)", align="C", ln=True)
    pdf.ln(5)

    pdf.section_title("Tu agenda de hoy")

    if not events:
        pdf.set_font("Arial", "I", 11)
        pdf.set_text_color(*TEXT_MUTED)
        pdf.set_x(20)
        pdf.cell(0, 10, "No tienes eventos programados para hoy. \u00a1Dia libre!", ln=True)
    else:
        for ev in events:
            tipo = ev.get("type", "reminder")
            icon  = {"reminder": ICON_CLOCK, "meeting": ICON_STAR, "task": ICON_ARROW}.get(tipo, ICON_BULLET)
            color = {"reminder": WARNING_COLOR, "meeting": BRAND_COLOR, "task": ACCENT_COLOR}.get(tipo, TEXT_DARK)
            time_str = _fmt_time(ev.get("start", ""))
            pdf.event_row(icon, time_str, ev.get("title", "Sin titulo"), color)

            if ev.get("description"):
                pdf.set_x(35)
                pdf.set_font("Arial", "I", 8)
                pdf.set_text_color(*TEXT_MUTED)
                pdf.cell(0, 5, str(ev["description"]), ln=True)
        pdf.ln(2)

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    tmp.close()
    pdf.output(tmp.name)
    return tmp.name


def generate_evening_wrapup(completed: list, pending: list, user_name: str, date: datetime) -> str:
    """Genera el PDF con el wrap-up nocturno."""
    total = len(completed) + len(pending)
    pct   = int(len(completed) / total * 100) if total > 0 else 0
    pdf   = AgendaPDF(f"Resumen del dia \u2014 {date.strftime('%d/%m/%Y')}")

    # Barra de progreso textual
    pdf.set_font("Arial", "", 10)
    pdf.set_text_color(*TEXT_MUTED)
    pdf.cell(0, 6, f"Productividad del dia: {pct}% completado", align="C", ln=True)
    pdf.ln(4)

    pdf.section_title("Resumen de productividad")
    pdf.ln(3)
    pdf.stat_box("Completadas", str(len(completed)), ACCENT_COLOR)
    pdf.stat_box("Pendientes",  str(len(pending)),   WARNING_COLOR)
    pdf.stat_box("Total",       str(total),           BRAND_COLOR)
    pdf.ln(33)

    if completed:
        pdf.section_title(f"Completadas  ({len(completed)})")
        for ev in completed:
            pdf.event_row(ICON_OK, _fmt_time(ev.get("start", "")), ev.get("title", ""), ACCENT_COLOR)
        pdf.ln(2)

    if pending:
        pdf.section_title(f"Pendientes  ({len(pending)})")
        for ev in pending:
            pdf.event_row(ICON_PENDING, _fmt_time(ev.get("start", "")), ev.get("title", ""), WARNING_COLOR)
        pdf.ln(2)

    # Nota de cierre
    if pending:
        pdf.set_font("Arial", "I", 9)
        pdf.set_text_color(*TEXT_MUTED)
        pdf.set_x(15)
        pdf.cell(0, 8, f"  Tienes {len(pending)} tarea(s) sin completar. Puedes reprogramarlas para mañana.", ln=True)

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    tmp.close()
    pdf.output(tmp.name)
    return tmp.name


def generate_productivity_report(report_data: dict, period: str) -> str:
    """Genera el PDF con el reporte de productividad (daily/weekly/monthly)."""
    period_labels = {"daily": "Diario", "weekly": "Semanal", "monthly": "Mensual"}
    pdf = AgendaPDF(f"Reporte de Productividad \u2014 {period_labels.get(period, period)}")

    total     = report_data.get("total", 0)
    completed = report_data.get("completed", 0)
    pending   = report_data.get("pending", 0)
    pct       = int(completed / total * 100) if total > 0 else 0

    # Porcentaje
    pdf.set_font("Arial", "B", 13)
    pdf.set_text_color(*ACCENT_COLOR)
    pdf.cell(0, 7, f"Eficiencia: {pct}%  \u2014  {completed} de {total} tareas completadas", align="C", ln=True)
    pdf.ln(4)

    pdf.section_title("Estadisticas generales")
    pdf.ln(3)
    pdf.stat_box("Total",       str(total),     BRAND_COLOR)
    pdf.stat_box("Completadas", str(completed), ACCENT_COLOR)
    pdf.stat_box("Pendientes",  str(pending),   WARNING_COLOR)
    pdf.ln(33)

    completed_list = report_data.get("completed_list", [])
    if completed_list:
        pdf.section_title(f"Eventos completados  ({len(completed_list)})")
        for ev in completed_list:
            pdf.event_row(ICON_OK, _fmt_date_time(ev.get("start", "")), ev.get("title", ""), ACCENT_COLOR)
        pdf.ln(2)

    pending_list = report_data.get("pending_list", [])
    if pending_list:
        pdf.section_title(f"Pendientes / Sin completar  ({len(pending_list)})")
        for ev in pending_list:
            pdf.event_row(ICON_PENDING, _fmt_date_time(ev.get("start", "")), ev.get("title", ""), WARNING_COLOR)
        pdf.ln(2)

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    tmp.close()
    pdf.output(tmp.name)
    return tmp.name
