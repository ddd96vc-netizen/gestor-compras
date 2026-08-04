"""
registro.py - Selección del parser según la tienda
==================================================
Detecta la tienda por palabras clave en el texto OCR y elige el parser
adecuado. Para añadir una tienda nueva:
  1. Crea app/ocr/parsers/mi_tienda.py con una subclase de ParserTicket.
  2. Impórtala aquí y añádela a PARSERS_ESPECIFICOS.
Los parsers ya existentes no se tocan.
"""

from app.ocr.parsers.generico import ParserGenerico
from app.ocr.parsers.mercadona import ParserMercadona

# Parsers con reglas propias (se prueban en orden).
PARSERS_ESPECIFICOS = [
    ParserMercadona(),
]

# Parser por defecto si no se reconoce la tienda.
PARSER_GENERICO = ParserGenerico()


def elegir_parser(texto: str):
    mayus = texto.upper()
    for parser in PARSERS_ESPECIFICOS:
        if any(clave in mayus for clave in parser.palabras_clave):
            return parser
    return PARSER_GENERICO


def parsear_ticket(texto: str) -> dict:
    """Punto de entrada: texto OCR -> {tienda, fecha, productos, parser}."""
    parser = elegir_parser(texto)
    resultado = parser.parsear(texto)
    resultado["parser"] = parser.__class__.__name__   # útil para depurar
    return resultado
