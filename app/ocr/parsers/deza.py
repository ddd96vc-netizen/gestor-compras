"""
deza.py - Parser de Deza (supermercado "Zoco")
==============================================
Deza imprime los decimales con apóstrofo ("1'24") y los productos al peso
como "NOMBRE  1'5  4'50  6'91" (kg · €/kg · importe). Ambas cosas ya las
resuelve la clase base; aquí solo se fija el nombre con el que guardas
esta tienda.
"""

from app.ocr.parsers.base import ParserTicket


class ParserDeza(ParserTicket):
    palabras_clave = ("DEZA",)   # "ZOCO" no: también tienes "Chino Zoco"
    nombre_tienda = "Zoco"
