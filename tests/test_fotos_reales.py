"""
test_fotos_reales.py - Tickets reales completos (cajas del OCR -> productos)
===========================================================================
En tests/datos_ocr/ está la salida CRUDA de EasyOCR (cajas + texto) de fotos
reales. Así se prueba todo el camino (reconstruir filas + parser + cuadre con
el total) sin necesitar las fotos ni EasyOCR.

Para añadir un ticket que se lea mal: guarda su salida cruda como JSON aquí y
añade una línea a CASOS con lo que debería salir.
"""

import json
from pathlib import Path

import pytest

from app.ocr.lector import reconstruir_filas
from app.ocr.parsers import parsear_ticket

DATOS = Path(__file__).parent / "datos_ocr"

# archivo, tienda, fecha, total, nº de productos
CASOS = [
    ("el_jamon_granvia_2026-10-27", "El Jamon", "2026-10-27T20:28", 7.03, 4),
    ("deza_torcido_2026-11-03", "Zoco", "2026-11-03T19:14", 26.69, 11),
    ("elena_2026-11-01", "Frutas y Verduras Elena", "2026-11-01T18:28", 7.97, 7),
    ("elena_2026-10-21", "Frutas y Verduras Elena", "2026-10-21T20:30", 4.87, 2),
    ("el_jamon_pintor_2026-10-15", "El Jamon", "2026-10-15T20:46", 3.64, 2),
    ("deza_2026-10-16", "Zoco", "2026-10-16", 29.89, 13),
    ("elena_2026-10-19", "Frutas y Verduras Elena", "2026-10-19T17:12", 9.25, 7),
]


def _leer(nombre):
    resultados = json.loads((DATOS / f"{nombre}.json").read_text(encoding="utf-8"))
    return parsear_ticket("\n".join(reconstruir_filas(resultados)))


@pytest.mark.parametrize("nombre, tienda, fecha, total, n_productos", CASOS)
def test_ticket_real(nombre, tienda, fecha, total, n_productos):
    datos = _leer(nombre)
    assert datos["tienda"] == tienda
    assert datos["fecha"].startswith(fecha)
    assert datos["total"] == total
    assert len(datos["productos"]) == n_productos
    assert round(sum(p["importe"] for p in datos["productos"]), 2) == total


def test_elena_guarda_peso_y_precio_por_kilo():
    productos = _leer("elena_2026-11-01")["productos"]
    assert productos[0]["observacion"] == "0,480 kg a 1,99 €/kg"
    assert productos[-1]["nombre"] == "Artículo por unidad"
    assert productos[-1]["importe"] == 2.70


def test_deza_cuadre_corrige_digito_y_cantidad():
    productos = {p["nombre"][:7]: p for p in _leer("deza_2026-10-16")["productos"]}
    assert productos["Chicles"]["importe"] == 0.74      # el OCR leyó 4'74
    assert productos["Bebida "]["cantidad"] == 1        # "Bahamas 2" es el nombre
    assert productos["Bolsa R"]["cantidad"] == 2        # "0' 224" -> 0'24
