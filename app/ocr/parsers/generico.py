"""
generico.py - Parser por defecto
================================
Se usa cuando el ticket no coincide con ninguna tienda con reglas propias.
Hereda toda la lógica genérica de ParserTicket sin cambios.
"""

from app.ocr.parsers.base import ParserTicket


class ParserGenerico(ParserTicket):
    pass
