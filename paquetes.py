"""
paquetes.py
-----------
Paquetes de estudios predefinidos de OPLAB.
Para modificar un paquete edita este archivo y haz git push.
LOS NOMBRES DE ESTUDIOS DEBEN COINCIDIR EXACTAMENTE CON EL CATÁLOGO.
"""

PAQUETES = {
    "1": {
        "nombre": "Check-up General",
        "emoji": "🔵",
        "descripcion": "Revisión completa de salud",
        "estudios": [
            "BIOMETRÍA HEMÁTICA",
            "QUÍMICA SANGUÍNEA 12 ELEMENTOS (QS6 Y LÍPIDOS)",  # QS6 + Lípidos
            "PROTEINA C REACTIVA ULTRASENSIBLE (hsCRP)",  # PCR ultrasensible
            "EXAMEN GENERAL DE ORINA",
            "HEMOGLOBINA GLICADA",  # Hemoglobina glicosilada
            "PERFIL HEPÁTICO BÁSICO",
            "PERFIL REUMÁTICO",  # Perfil Reumatoide
            "PERFIL TIROIDEO (8 ELEMENTOS)",
        ],
    },
    "2": {
        "nombre": "Estudios de Gabinete y Especiales",
        "emoji": "🟡",
        "descripcion": "Electrocardiograma, ultrasonidos y densitometría",
        # ⚠️ Estos estudios SON DE GABINETE. No los tienes en el catálogo de laboratorio actual.
        # Serán marcados como "no encontrados" por el bot hasta que los agregues a conocimiento.md
        "estudios": [
            "ELECTROCARDIOGRAMA",
            "ULTRASONIDO HEPÁTICO",
            "ULTRASONIDO RENAL",
            "DENSITOMETRÍA ÓSEA",
        ],
    },
    "3": {
        "nombre": "Perfil TORCH IgG / IgM",
        "emoji": "🟠",
        "descripcion": "Citomegalovirus y Virus Epstein-Barr",
        "estudios": [
            "PERFIL DE TORCH CUALITATIVO (IgG/IgM)",  # Incluye Citomegalovirus y Epstein-Barr
        ],
    },
    "4": {
        "nombre": "Perfil Hormonal Femenino",
        "emoji": "🟣",
        "descripcion": "Panel hormonal reproductivo completo",
        "estudios": [
            "HORMONA LUTEINIZANTE",
            "HORMONA FOLICULO ESTIMULANTE",
            "HORMONA ESTIMULANTE DE TIROIDES",
            "ESTRADIOL SERICO",
            "PROGESTERONA",
            "PROLACTINA",
            "TESTOSTERONA TOTAL",
            "TESTOSTERONA LIBRE (QUIMIOLUMINISCENCIA)",
            # "SULFATO DE DHEA" <- No existe en tu documento conocimiento.md. 
            # Agrégalo en tu PDF/conocimiento.md si deseas que el bot lo cotice.
        ],
    },
}


def get_menu_text() -> str:
    """Genera el texto del menú de paquetes para mostrar al usuario."""
    lineas = ["📦 *PAQUETES DE ESTUDIOS DISPONIBLES:*\n"]
    for num, p in PAQUETES.items():
        estudios_txt = "\n".join(f"   • {e.title()}" for e in p["estudios"])
        lineas.append(
            f"{p['emoji']} *{num}. {p['nombre']}*\n"
            f"   _{p['descripcion']}_\n"
            f"{estudios_txt}\n"
        )
    lineas.append(
        "Responde con el *número* del paquete, o ✍️ escribe / 🎤 dicta los estudios que necesitas."
    )
    return "\n".join(lineas)


def get_paquete(numero: str) -> dict | None:
    """Devuelve el paquete por número, o None si no existe."""
    return PAQUETES.get(numero.strip())
