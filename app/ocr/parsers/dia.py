"""
dia.py - Parser de DIA
======================
Solo fija el nombre de la tienda. Los productos usan el formato genérico
("DESCRIPCION   IMPORTE" con la letra del tipo de IVA al final), que la
clase base ya entiende.
"""

from app.ocr.parsers.base import ParserTicket


class ParserDia(ParserTicket):
    palabras_clave = ("GRUPO DIA", "DIA RETAIL")
    nombre_tienda = "Dia"
