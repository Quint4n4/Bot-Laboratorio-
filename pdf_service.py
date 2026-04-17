import os
import base64
import datetime
from jinja2 import Environment, FileSystemLoader
from playwright.async_api import async_playwright

def _logo_base64() -> str:
    """Convierte Logo.png a base64 para incrustar directamente en HTML (evita bloqueo de file:// en Playwright)."""
    logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Logo.png")
    if not os.path.exists(logo_path):
        return ""
    with open(logo_path, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
    ext = os.path.splitext(logo_path)[1].lstrip(".").lower()
    mime = "png" if ext == "png" else "jpeg"
    return f"data:image/{mime};base64,{encoded}"

def _get_preparacion(nombre_estudio: str) -> list[str]:
    """
    Devuelve las instrucciones de preparación más importantes para un estudio dado.
    Basadas en guías de NOM-007-SSA3, Sociedad Mexicana de Patología Clínica y recomendaciones generales.
    """
    nombre = nombre_estudio.upper()

    # ─── Glucosa y metabolismo ─────────────────────────────
    if any(k in nombre for k in ["GLUCOSA", "QUÍMICA SANGUÍNE", "INSULINA", "HOMA", "HBA1C", "HEMOGLOBINA GLICADA", "DIABETES"]):
        return [
            "Ayuno mínimo de 8 a 12 horas antes de la toma. Solo puede tomar agua pura.",
            "No suspender medicamentos habituales sin consultar al médico.",
            "Evitar ejercicio intenso el día anterior.",
            "No fumar ni masticar chicle antes de la muestra.",
        ]

    # ─── Perfil de lípidos / colesterol ───────────────────
    if any(k in nombre for k in ["LÍPID", "COLESTEROL", "TRIGLICÉR", "HDL", "LDL", "VLDL"]):
        return [
            "Ayuno estricto de 12 horas. Solo agua pura permitida.",
            "Evitar alcohol 72 horas antes del estudio.",
            "No realizar ejercicio intenso 24 horas antes.",
            "Mantener la dieta habitual los 3 días previos (no iniciar nuevas dietas).",
        ]

    # ─── Biometría hemática / sangre completa ─────────────
    if any(k in nombre for k in ["BIOMETRÍA", "HEMATOLOG", "HEMOGRAMA", "ERITROCITO", "RETICULOCITO"]):
        return [
            "No requiere ayuno para la toma de muestra.",
            "Informar si está tomando anticoagulantes o medicamentos que afecten la coagulación.",
            "Mantener presión suave en el sitio de punción al menos 2 minutos.",
        ]

    # ─── Orina ────────────────────────────────────────────
    if any(k in nombre for k in ["ORINA", "UROCULTIVO", "MICROALBUMIN", "PROTEÍNAS TOTALES EN ORINA", "DEPURACIÓN"]):
        return [
            "Usar preferentemente la primera orina de la mañana (más concentrada).",
            "Realizar aseo íntimo con agua y jabón neutro antes de la recolección.",
            "Descartar el primer chorro de orina y recolectar el 'chorro medio' en frasco estéril.",
            "Entregar la muestra dentro de la primera hora tras la recolección.",
            "Para orina de 24 horas: recolectar toda la orina durante 24 h en recipiente grande y refrigerar.",
        ]

    # ─── Perfil hepático / función hepática ───────────────
    if any(k in nombre for k in ["HEPÁTIC", "BILIRRUBINA", "TRANSAMINASA", "TGO", "TGP", "GAMMA", "FOSFATASA", "ALBUMIN"]):
        return [
            "Ayuno de 8 horas previo a la toma.",
            "Evitar alcohol al menos 72 horas antes.",
            "Informar si toma algún medicamento hepatotóxico (analgésicos, antibióticos, etc.).",
        ]

    # ─── Tiroides ─────────────────────────────────────────
    if any(k in nombre for k in ["TSH", "T3", "T4", "TIROIDEO", "TIROIDES", "TIROGLOBULINA"]):
        return [
            "Idealmente realizar la toma entre las 7:00 y 10:00 am (el TSH varía durante el día).",
            "No es necesario ayuno, pero se recomienda no comer en exceso antes.",
            "Informar si recibe tratamiento con levotiroxina u otros medicamentos para la tiroides.",
        ]

    # ─── Hormonas / reproducción ──────────────────────────
    if any(k in nombre for k in ["HORMONA", "FSH", "LH", "ESTRADIOL", "PROGESTERONA", "PROLACTINA", "TESTOSTERONA",
                                   "ANTI-MULLERIANA", "GINECOLÓG"]):
        return [
            "Indicar el día del ciclo menstrual (se requiere en días 2-5 del ciclo para FSH/LH/Estradiol).",
            "No es necesario ayuno estricto, pero se recomienda la toma en ayunas.",
            "Evitar actividad física intensa y relaciones sexuales el día previo para testosterona.",
        ]

    # ─── Coagulación ──────────────────────────────────────
    if any(k in nombre for k in ["COAGULACIÓN", "TP ", "TPT", "INR", "TIEMPO DE SANGRADO", "DÍMERO"]):
        return [
            "Informar si toma anticoagulantes (warfarina, heparina, dabigatrán, etc.).",
            "La muestra se toma en tubo azul (citrato de sodio); se debe llenar EXACTAMENTE hasta la marca.",
            "No agitar el tubo con fuerza; invertir suavemente 5-6 veces para mezclar.",
        ]

    # ─── Heces ────────────────────────────────────────────
    if any(k in nombre for k in ["HECES", "COPROCULTIVO", "COPROPARASIT", "SANGRE OCULTA", "ROTAVIRUS", "CALPROTECTINA"]):
        return [
            "Recolectar muestra del tamaño de una nuez (1 cucharadita) en frasco estéril.",
            "Evitar que la muestra tenga contacto con agua del inodoro, orina o papel higiénico.",
            "Para sangre oculta: evitar carne roja, verduras con peroxidasa (betabel, rábano) y vitamina C 3 días antes.",
            "Entregar la muestra al laboratorio dentro de las 2 horas de recolección.",
        ]

    # ─── Esperma / semen ──────────────────────────────────
    if any(k in nombre for k in ["ESPERMA", "SEMINOGRAMA", "ESPERMATO"]):
        return [
            "Abstinencia sexual estricta de 3 a 5 días (ni más ni menos).",
            "Recolectar la muestra completa por masturbación en frasco estéril de boca ancha.",
            "No usar lubricantes ni condones para la recolección.",
            "Entregar la muestra al laboratorio antes de 30-45 minutos, manteniéndola a temperatura corporal.",
        ]

    # ─── Cultivos / exudados ──────────────────────────────
    if any(k in nombre for k in ["CULTIVO", "EXUDADO", "HEMOCULTIVO", "UROCULTIVO"]):
        return [
            "No tomar antibióticos al menos 72 horas antes de la toma (consultar con el médico).",
            "Para exudado faríngeo: ayuno total previo a la toma (sin agua, sin lavado de dientes).",
            "Para exudado vaginal: no relaciones sexuales 48 h antes, sin lavados internos ni óvulos, fuera del período menstrual.",
            "La muestra debe manejarse en el medio de transporte indicado y entregarse de inmediato.",
        ]

    # ─── Marcadores tumorales ─────────────────────────────
    if any(k in nombre for k in ["PSA", "CA 125", "CA-15", "CA-19", "AFP", "CEA", "CARCINOEMBRIONARIO"]):
        return [
            "No realizar actividad física intensa, ciclismo ni relaciones sexuales 48 horas antes (especialmente para PSA).",
            "No es necesario ayuno estricto.",
            "Informar si tuvo algún procedimiento urológico o biopsia reciente.",
        ]

    # ─── Serología / infecciones ──────────────────────────
    if any(k in nombre for k in ["VIH", "SÍFILIS", "VDRL", "HEPATITIS", "DENGUE", "COVID", "VPH", "CLAMIDIA"]):
        return [
            "No requiere ayuno para la mayoría de estas pruebas.",
            "Informar al personal de salud sobre tratamientos actuales.",
            "En caso de COVID o pruebas nasales: no sonarse la nariz 15 minutos antes del hisopado.",
        ]

    # ─── Biopsia / histopatología ─────────────────────────
    if any(k in nombre for k in ["BIOPSIA", "HISTOPATOLÓG", "PIEZA QUIRÚRG"]):
        return [
            "La muestra debe enviarse en frasco con formol al 10% proporcionado por el médico tratante.",
            "No congelar ni refrigerar el tejido antes de fijarlo.",
            "Identificar claramente el frasco con nombre del paciente, médico y fecha.",
        ]

    # ─── Citología ────────────────────────────────────────
    if any(k in nombre for k in ["CITOLOGÍA", "PAPANICOLAOU", "PAPILOMA"]):
        return [
            "No tener relaciones sexuales 48 horas antes.",
            "No usar tampones, cremas, óvulos ni lubricantes vaginales 48 horas antes.",
            "Fuera del período menstrual (esperar al menos 5 días después).",
            "No hacerse el estudio si tiene infección vaginal activa; tratar primero.",
        ]

    # ─── Gasometría ───────────────────────────────────────
    if any(k in nombre for k in ["GASOMETRÍA"]):
        return [
            "La muestra es de sangre arterial; se realiza en el consultorio o laboratorio clínico.",
            "Mantener respiración normal durante la toma (no hiperventilar).",
            "Si usa oxígeno suplementario, el médico indicará si debe suspenderse antes.",
        ]

    # ─── Default ──────────────────────────────────────────
    return [
        "Acudir en ayuno de al menos 4 horas si su médico no indica lo contrario.",
        "Informar al personal de laboratorio sobre medicamentos que esté tomando.",
        "Llegar descansado y bien hidratado (agua pura está permitida).",
    ]

async def create_quote_pdf(ia_json: dict, patient_name: str, output_filename: str = "cotizacion.pdf") -> str:
    """
    Toma los datos extraídos de la IA y del Paciente y genera un PDF usando Chromium Headless.
    Página 1: Tabla de cotización con logo, fecha e info institucional.
    Página 2: Recomendaciones de preparación para cada estudio.
    """
    
    # 1. Fecha dinámica en español
    meses_espanol = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio",
                     "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
    hoy = datetime.date.today()
    fecha_formateada = f"{hoy.day:02d} de {meses_espanol[hoy.month - 1]} del {hoy.year}"
    
    # 2. Logo embebido en base64 (funciona siempre en Playwright)
    logo_data = _logo_base64()
    
    # 3. Configurar Jinja2
    template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template("cotizacion.html")
    
    # 4. Preparar items + recomendaciones de preparación
    lista_cotizacion = ia_json.get("cotizacion", [])
    total = ia_json.get("total", 0)
    
    items = []
    for c in lista_cotizacion:
        nombre = c.get("estudio", c.get("nombre", "Estudio Desconocido"))
        precio = c.get("precio", 0)
        recomendacion = c.get("recomendacion", "")
        tiempo = c.get("tiempo", "")
        preparacion = _get_preparacion(nombre)
        
        items.append({
            "nombre": nombre,
            "precio": f"{float(precio):.2f}",
            "recomendacion": recomendacion,
            "tiempo": tiempo,
            "preparacion": preparacion
        })
    
    # 5. Renderizar HTML
    rendered_html = template.render(
        logo_data=logo_data,
        fecha=fecha_formateada,
        paciente_nombre=patient_name,
        items=items,
        total=f"{float(total):.2f}"
    )
    
    # 6. Generar PDF con Playwright
    output_path = os.path.abspath(output_filename)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_content(rendered_html, wait_until="domcontentloaded")
        
        await page.pdf(
            path=output_path,
            format="Letter",
            print_background=True,
            display_header_footer=False,
            margin={"top": "1.5cm", "bottom": "1.5cm", "left": "2cm", "right": "2cm"}
        )
        await browser.close()
        
    return output_path
