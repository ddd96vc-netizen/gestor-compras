"""
el_jamon.py - Parser de El Jamón (tienda de C/ Pintor Espinosa)
==============================================================
Formato de 4 columnas (NOMBRE · CANTIDAD · PRECIO · IMPORTE), el que
entiende la clase base. Solo se fija el nombre de la tienda: la cabecera
del ticket no dice "El Jamón", solo la dirección.
"""

from app.ocr.parsers.base import ParserTicket


class ParserElJamonPintor(ParserTicket):
    palabras_clave = ("PINTOR ESPINOSA",)
    nombre_tienda = "El Jamon (Pintor)"
