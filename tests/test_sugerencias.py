"""
test_sugerencias.py - Completar el ticket escaneado con el historial
====================================================================
"""

from app import repositorio
from app.ocr.sugerencias import completar, buscar_parecido, cargar_historial


def _historial(conn):
    repositorio.crear_ticket(conn, "Zoco", "2026-08-01T13:25", [
        {"nombre": "Bebida Bahamas", "precio": "1.24", "categoria": "Liquidos"},
        {"nombre": "Higado de pollo", "precio": "1.98", "categoria": "Carnes", "favorito": "1"},
        {"nombre": "Atun Claro", "precio": "4.15", "categoria": "Carnes"},
        {"nombre": "No me acuerdo", "precio": "1.00", "categoria": "Verduras"},
    ])
    repositorio.crear_ticket(conn, "Coviran Lin", "2026-08-02T10:00", [
        {"nombre": "Pan", "precio": "0.50", "categoria": "Pan"},
    ])


def test_usa_nombre_categoria_y_favorito_del_historial(conn):
    _historial(conn)
    datos = {"parser": "ParserDeza", "tienda": "Zoco", "productos": [
        {"nombre": "Bebida Refrescante Alteza Bahanas 2", "precio": 1.24, "cantidad": 1},
        {"nombre": "Higado De Poljo Inasur Tarrina", "precio": 1.98, "cantidad": 1},
        {"nombre": "Tún Claro A/ Natura) Alteza", "precio": 4.15, "cantidad": 1},
    ]}
    completar(conn, datos)
    bebida, higado, atun = datos["productos"]
    assert (bebida["nombre"], bebida["categoria"]) == ("Bebida Bahamas", "Liquidos")
    assert bebida["nombre_leido"] == "Bebida Refrescante Alteza Bahanas 2"
    assert higado["nombre"] == "Higado de pollo" and higado["favorito"] is True
    assert atun["nombre"] == "Atun Claro"


def test_no_confunde_palabras_que_solo_se_parecen(conn):
    _historial(conn)
    historial = cargar_historial(conn)
    parecido, cobertura = buscar_parecido("Lono De Cerdo Faccsa Fijeteado", historial)
    assert not (parecido and parecido["nombre"] == "No me acuerdo" and cobertura == 1.0)


def test_producto_desconocido_se_queda_como_se_leyo(conn):
    _historial(conn)
    datos = {"parser": "ParserGenerico", "tienda": "", "productos": [
        {"nombre": "Detergente Liquido", "precio": 3.0, "cantidad": 1},
    ]}
    completar(conn, datos)
    p = datos["productos"][0]
    assert p["nombre"] == "Detergente Liquido"
    assert p["categoria"] is None and p["favorito"] is False


def test_reconoce_tienda_guardada_en_la_cabecera(conn):
    _historial(conn)
    datos = {"parser": "ParserGenerico", "tienda": "Supermercados C0v1", "productos": []}
    completar(conn, datos, "COVIRAN\nLIN S.L.\nC/ Mayor 3\n01/08/2026")
    assert datos["tienda"] == "Coviran Lin"
