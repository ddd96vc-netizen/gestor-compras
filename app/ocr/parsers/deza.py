"""
deza.py - Parser de Deza (supermercado "Zoco")
==============================================
Deza imprime los decimales con apóstrofo ("1'24") y los productos al peso
como "NOMBRE  1'5  4'50  6'91" (kg · €/kg · importe). Ambas cosas ya las
resuelve la clase base. Reglas propias de Deza:

  - Importe con un dígito repetido por el OCR: "0'12  0' 224" -> "0'24".
"""

import re

from app.ocr.parsers.base import ParserTicket

# "0' 224" al final de la línea: apóstrofo + 3 cifras con las dos primeras iguales.
RE_DIGITO_DOBLE = re.compile(r"(\d)\s*'\s*(\d)\2(\d)\s*$")


class ParserDeza(ParserTicket):
    palabras_clave = ("DEZA",)   # "ZOCO" no: también tienes "Chino Zoco"
    nombre_tienda = "Zoco"

    def preparar_linea(self, linea: str) -> str:
        return RE_DIGITO_DOBLE.sub(r"\1'\2\3", linea)
