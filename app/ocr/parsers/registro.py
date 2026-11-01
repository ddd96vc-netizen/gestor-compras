"""
registro.py - Selección del parser según la tienda
==================================================
Detecta la tienda por palabras clave en el texto OCR y elige el parser
adecuado. Para añadir una tienda nueva:
  1. Crea app/ocr/parsers/mi_tienda.py con una subclase de ParserTicket.
  2. Impórtala aquí y añádela a PARSERS_ESPECIFICOS.
Los parsers ya existentes no se tocan.
"""

from difflib import SequenceMatcher

from app.ocr.parsers.deza import ParserDeza
from app.ocr.parsers.dia import ParserDia
from app.ocr.parsers.el_jamon import ParserElJamonPintor
from app.ocr.parsers.generico import ParserGenerico
from app.ocr.parsers.mercadona import ParserMercadona

# Parsers con reglas propias (se prueban en orden).
PARSERS_ESPECIFICOS = [
    ParserMercadona(),
    ParserDia(),
    ParserDeza(),
    ParserElJamonPintor(),
]

# Parser por defecto si no se reconoce la tienda.
PARSER_GENERICO = ParserGenerico()

# Parecido mínimo para aceptar una palabra clave mal leída ("PINIR ESPINMO").
# Solo se aplica a claves largas: las cortas ("DEZA") darían falsos positivos.
SIMILITUD_CLAVE = 0.75
LARGO_MIN_APROXIMADO = 8


def _aparece_aproximada(clave: str, texto: str) -> bool:
    """¿Aparece `clave` en `texto` aunque el OCR haya cambiado alguna letra?"""
    # Ventanas algo más cortas o largas que la clave: el OCR pierde o mete letras.
    for n in range(len(clave) - 3, len(clave) + 3):
        for inicio in range(0, max(1, len(texto) - n + 1)):
            trozo = texto[inicio:inicio + n]
            if trozo[:1].isalnum() and SequenceMatcher(None, clave, trozo).ratio() >= SIMILITUD_CLAVE:
                return True
    return False


def elegir_parser(texto: str):
    mayus = " ".join(texto.upper().split())   # el OCR mete espacios dobles
    for parser in PARSERS_ESPECIFICOS:
        if any(clave in mayus for clave in parser.palabras_clave):
            return parser
    # Segunda pasada, tolerante a errores del OCR, solo en la cabecera.
    cabecera = " ".join(" ".join(texto.upper().splitlines()[:8]).split())
    for parser in PARSERS_ESPECIFICOS:
        if any(len(clave) >= LARGO_MIN_APROXIMADO and _aparece_aproximada(clave, cabecera)
               for clave in parser.palabras_clave):
            return parser
    return PARSER_GENERICO


def parsear_ticket(texto: str) -> dict:
    """Punto de entrada: texto OCR -> {tienda, fecha, productos, parser}."""
    parser = elegir_parser(texto)
    resultado = parser.parsear(texto)
    resultado["parser"] = parser.__class__.__name__   # útil para depurar
    return resultado
