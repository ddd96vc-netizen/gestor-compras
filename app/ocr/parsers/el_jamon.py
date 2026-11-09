"""
el_jamon.py - Parsers de los supermercados El Jamón
===================================================
Formato de 4 columnas (NOMBRE · CANTIDAD · PRECIO · IMPORTE), el que
entiende la clase base. Aquí van las reglas propias de la cadena:

  - ParserElJamon: cualquier tienda El Jamón. La cabecera a veces sale
    ilegible en la foto, así que también se reconoce por el pie del ticket
    ("SERVICIO A DOMICILIO GRATIS A PARTIR DE 50 EUROS") y por el teléfono
    de atención al cliente (959645060).
  - ParserElJamonPintor: la de C/ Pintor Espinosa (se guarda con otro nombre).

El total viene como "TOTAL FACTURA 7.03" y el OCR a veces lee "fOTAl".
"""

import re

from app.ocr.parsers.base import ParserTicket

RE_TOTAL_FACTURA = re.compile(r"\b[TF7]O[TI]A[L1I]\b.*\bFACTURA\b|\bTOTAL\b", re.IGNORECASE)


class ParserElJamon(ParserTicket):
    palabras_clave = ("EL JAMON", "959645060", "DOMICILIO GRATIS", "PARTIR DE 50 EUROS")
    nombre_tienda = "El Jamon"

    def es_linea_total(self, linea: str) -> bool:
        return bool(RE_TOTAL_FACTURA.search(linea)) or super().es_linea_total(linea)


class ParserElJamonPintor(ParserElJamon):
    palabras_clave = ("PINTOR ESPINOSA",)
    nombre_tienda = "El Jamon (Pintor)"
