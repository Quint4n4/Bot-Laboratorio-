"""
paquetes.py
-----------
Define los paquetes de estudios predefinidos del laboratorio OPLAB.

Para AGREGAR o MODIFICAR un paquete, edita este archivo directamente.
Los nombres de los estudios deben coincidir con los del catálogo (conocimiento.md).
"""

PAQUETES = {
    "1": {
        "nombre": "Biometr",
        "emoji": "🔵",
        "descripcion": "Revisión general de rutina",
        "estudios": [
            "BIOMETRÍA HEMÁTICA",
            "GLUCOSA",
            "UREA SERICA",
            "CREATININA",
            "EXAMEN GENERAL DE ORINA",
        ],
    },
    "2": {
        "nombre": "Paquete Control Metabólico",
        "emoji": "🟢",
        "descripcion": "Control de diabetes y lípidos",
        "estudios": [
            "BIOMETRÍA HEMÁTICA",
            "GLUCOSA",
            "HEMOGLOBINA GLUCOSILADA (HBA1C)",
            "COLESTEROL",
            "TRIGLICÉRIDOS",
            "HDL COLESTEROL",
            "LDL COLESTEROL",
        ],
    },
    "3": {
        "nombre": "Paquete Perfil Hepático",
        "emoji": "🟡",
        "descripcion": "Evaluación de función del hígado",
        "estudios": [
            "PERFIL HEPÁTICO BÁSICO",
            "BILIRRUBINA DIRECTA",
            "ALBUMINA",
            "TIEMPO DE PROTROMBINA (TP)",
        ],
    },
    "4": {
        "nombre": "Paquete Hormonal Femenino",
        "emoji": "🟣",
        "descripcion": "Panel hormonal reproductivo",
        "estudios": [
            "HORMONA FOLICULO ESTIMULANTE",
            "HORMONA LUTEINIZANTE",
            "ESTRADIOL SERICO",
            "PROGESTERONA",
            "PROLACTINA",
        ],
    },
    "5": {
        "nombre": "Paquete Tiroides",
        "emoji": "🟠",
        "descripcion": "Evaluación de función tiroidea",
        "estudios": [
            "TSH",
            "T3 LIBRE",
            "T4 LIBRE",
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
    lineas.append("Responde con el *número* del paquete que deseas, o escribe / dicta los estudios específicos que necesitas.")
    return "\n".join(lineas)


def get_paquete(numero: str) -> dict | None:
    """Devuelve el paquete por número, o None si no existe."""
    return PAQUETES.get(numero.strip())
