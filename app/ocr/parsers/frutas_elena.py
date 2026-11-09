"""
frutas_elena.py - Parser de "Frutas y Verduras Elena" (Av. Aeropuerto 9)
========================================================================
Ticket de frutería SIN nombres de producto. Cada artículo ocupa 2 líneas:

    1   0.00%                    <- nº de artículo + IVA (se ignora)
        0,480   1,99   0,96      <- kg · €/kg · importe
    7   0.00%
      + 1 un x   2,70   2,70     <- por unidades: cantidad · precio · importe

La fecha va con el mes en letras ("01/NOV/26") y la hora aparte ("HORA: 18:28").
El OCR suele meter espacios en los números ("0 , 480", "1 99"), así que se
leen los números de la cola de la línea de derecha a izquierda y se
comprueba que kg × €/kg = importe.
"""

import re

from app.ocr.parsers.base import ParserTicket, formato_euros

NOMBRE_PESO = "Fruta/verdura"
NOMBRE_UNIDAD = "Artículo por unidad"

RE_UNIDADES = re.compile(r"(\d+)\s*un\b", re.IGNORECASE)
RE_IVA_LINEA = re.compile(r"^\s*\d?\s*0\s*[.,]\s*0\s*[0O]", re.IGNORECASE)   # "1 0.00%"


def _tokens(linea: str) -> list:
    """Números de la línea, uniendo "0 , 480" -> "0,480" y "1 . 99" -> "1,99"."""
    linea = re.sub(r"\s*[,.]\s*", ",", linea)
    return re.findall(r"\d+(?:,\d+)?", linea)


def _tomar_euros(tokens: list):
    """Saca de la cola un importe con 2 decimales ("1,99" o "1 99"). None si no hay."""
    if not tokens:
        return None
    ultimo = tokens[-1]
    if "," in ultimo:
        ent, dec = ultimo.split(",", 1)
        if len(dec) == 2:
            tokens.pop()
            return int(ent or 0) + int(dec) / 100
        return None
    # Coma perdida: "1 99" -> 1,99
    if len(ultimo) == 2 and len(tokens) >= 2 and "," not in tokens[-2] and len(tokens[-2]) <= 2:
        tokens.pop()
        ent = tokens.pop()
        return int(ent) + int(ultimo) / 100
    return None


def _tomar_kilos(tokens: list):
    """Peso con 3 decimales ("0,480" o "1 090"). None si no hay."""
    if not tokens:
        return None
    ultimo = tokens[-1]
    if "," in ultimo:
        ent, dec = ultimo.split(",", 1)
        if len(dec) == 3:
            tokens.pop()
            return int(ent or 0) + int(dec) / 1000
        return None
    if len(ultimo) == 3 and len(tokens) >= 2 and "," not in tokens[-2] and len(tokens[-2]) == 1:
        tokens.pop()
        ent = tokens.pop()
        return int(ent) + int(ultimo) / 1000
    return None


class ParserFrutasElena(ParserTicket):
    palabras_clave = ("VERDURAS ELENA", "TEYUN", "AEROPUERTO 9")
    nombre_tienda = "Frutas y Verduras Elena"

    def extraer_productos(self, lineas: list) -> list:
        productos = []
        dentro = False
        for linea in lineas:
            mayus = linea.upper()
            if not dentro:
                dentro = "HORA" in mayus
                continue
            if self.es_linea_total(linea):
                break

            tokens = _tokens(linea)
            importe = _tomar_euros(tokens)
            precio = _tomar_euros(tokens)
            if not importe or not precio:
                continue

            m_un = RE_UNIDADES.search(linea)
            if m_un:
                cantidad = int(m_un.group(1)) or 1
                productos.append({
                    "nombre": NOMBRE_UNIDAD, "precio": round(precio, 2),
                    "cantidad": cantidad, "importe": round(importe, 2), "observacion": "",
                })
                continue

            if RE_IVA_LINEA.match(linea) and importe < 0.01:
                continue
            kilos = _tomar_kilos(tokens)
            if kilos is None or abs(kilos * precio - importe) > 0.02:
                kilos = importe / precio   # peso perdido o mal leído: se deduce
            productos.append({
                "nombre": NOMBRE_PESO,
                "precio": round(importe, 2),
                "cantidad": 1,
                "importe": round(importe, 2),
                "observacion": f"{kilos:.3f}".replace(".", ",") + f" kg a {formato_euros(precio)} €/kg",
            })
        return productos
