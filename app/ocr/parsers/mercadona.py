"""
mercadona.py - Parser específico de Mercadona
=============================================
EJEMPLO de parser por tienda. De momento hereda casi todo del genérico y
solo fija el nombre de la tienda (así no depende de cómo lea el OCR la
cabecera). A medida que subas tickets REALES de Mercadona y veas qué falla,
aquí se sobreescriben los métodos necesarios: p. ej. Mercadona lista las
líneas como "CANTIDAD DESCRIPCION IMPORTE" y a veces el precio unitario y el
total van en columnas distintas.

Cómo evolucionar este parser:
  1. Sube un ticket de Mercadona y mira el texto OCR en la pantalla de revisión.
  2. Si algo se extrae mal, sobreescribe aquí extraer_productos (o el método
     que falle) usando las reglas concretas de este formato.
  3. Guarda ese texto OCR como caso de test en tests/muestras_ocr/.
"""

from app.ocr.parsers.base import ParserTicket


class ParserMercadona(ParserTicket):
    palabras_clave = ("MERCADONA",)
    nombre_tienda = "Mercadona"
