"""Dónde es más barato y lo que más compras (estadisticas.py)."""

from datetime import date

from app import estadisticas, repositorio


def _ticket(conn, tienda, fecha, *productos):
    repositorio.crear_ticket(conn, tienda, fecha, [
        {"nombre": n, "precio": p, "cantidad": c} for n, p, c in productos
    ])


def test_comparar_precios_tienda_barata_y_ahorro(conn):
    _ticket(conn, "Zoco", "2026-01-01T10:00", ("Leche", "1.00", 2), ("Pan", "0.50", 1))
    _ticket(conn, "Dia", "2026-01-05T10:00", ("leche ", "1.30", 1))
    _ticket(conn, "Dia", "2026-01-09T10:00", ("Pan", "0.50", 1))
    _ticket(conn, "Zoco", "2026-01-10T10:00", ("Todo", "20.00", 1))   # no es un producto

    datos = estadisticas.comparar_precios(conn)
    nombres = [p["nombre"] for p in datos["productos"]]
    assert "Todo" not in nombres
    leche = next(p for p in datos["productos"] if p["nombre"].lower().startswith("leche"))
    assert leche["barata"] == "Zoco" and leche["precio_barato"] == 1.00
    assert leche["cara"] == "Dia" and leche["precio_caro"] == 1.30
    assert leche["ahorro"] == 0.30            # solo la leche de Dia se pagó de más
    assert leche["pct_mas_caro"] == 30
    assert datos["ahorro_total"] == 0.30


def test_diferencia_enorme_se_marca_como_otro_tamano(conn):
    _ticket(conn, "Zoco", "2026-01-01T10:00", ("Arroz", "1.00", 1))
    _ticket(conn, "Dia", "2026-01-02T10:00", ("Arroz", "3.30", 1))
    datos = estadisticas.comparar_precios(conn)
    assert datos["productos"][0]["sospechoso"] is True
    assert datos["ahorro_total"] == 0         # no cuenta para el ahorro


def test_ranking_de_tiendas(conn):
    for i, (nombre, zoco, dia) in enumerate([("A", "1.00", "1.20"), ("B", "2.00", "2.20"), ("C", "1.00", "1.10")]):
        _ticket(conn, "Zoco", f"2026-01-0{i + 1}T10:00", (nombre, zoco, 1))
        _ticket(conn, "Dia", f"2026-01-0{i + 1}T12:00", (nombre, dia, 1))
    ranking = estadisticas.comparar_precios(conn)["ranking_tiendas"]
    assert [r["tienda"] for r in ranking] == ["Zoco", "Dia"]
    assert ranking[0]["indice"] < 100 < ranking[1]["indice"]
    assert ranking[0]["veces_mas_barata"] == 3


def test_mas_comprados_y_te_toca(conn):
    for dia in ("2026-01-01", "2026-01-11", "2026-01-21"):          # cada 10 días
        _ticket(conn, "Zoco", f"{dia}T10:00", ("Huevos", "2.00", 1), ("Bolsa", "0.10", 1))
    _ticket(conn, "Dia", "2026-01-15T10:00", ("Lomo", "9.00", 1))

    datos = estadisticas.productos_mas_comprados(conn, hoy=date(2026, 2, 5))
    assert datos["por_veces"][0]["nombre"] == "Huevos"
    assert datos["por_veces"][0]["veces"] == 3 and datos["por_veces"][0]["cada_dias"] == 10
    assert datos["por_gasto"][0]["nombre"] == "Lomo"
    assert all(p["nombre"] != "Bolsa" for p in datos["por_veces"])
    assert [p["nombre"] for p in datos["toca_comprar"]] == ["Huevos"]   # 15 días sin comprar

    # Mucho tiempo sin comprarlo = lo has dejado, ya no "toca".
    lejos = estadisticas.productos_mas_comprados(conn, hoy=date(2026, 6, 1))
    assert lejos["toca_comprar"] == []


def test_paginas_cargan(client_logueado):
    for url in ("/estadisticas/precios", "/estadisticas/productos", "/estadisticas/meses", "/estadisticas"):
        r = client_logueado.get(url)
        assert r.status_code == 200, url


def test_nombres_del_mismo_producto_se_unen(conn):
    _ticket(conn, "Proxi", "2026-01-01T10:00", ("Cerveza CruzCampo", "0.85", 1))
    _ticket(conn, "El Jamon", "2026-01-02T10:00", ("Cruzcampo", "1.05", 1))
    _ticket(conn, "Dia", "2026-01-03T10:00", ("Leche", "0.83", 1))
    _ticket(conn, "Zoco", "2026-01-04T10:00", ("Leche Covap", "1.75", 1))   # otra marca: NO se une
    nombres = {p["nombre"].lower() for p in estadisticas.comparar_precios(conn)["productos"]}
    assert len(nombres) == 1 and "leche" not in nombres


def test_evolucion_mensual(conn):
    _ticket(conn, "Zoco", "2026-01-10T10:00", ("Lomo", "10.00", 1))
    _ticket(conn, "Zoco", "2026-03-05T10:00", ("Lomo", "20.00", 1))      # febrero sin compras
    _ticket(conn, "Dia", "2026-04-02T10:00", ("Pan", "3.00", 1))
    d = estadisticas.evolucion_mensual(conn, hoy=date(2026, 4, 15))
    assert [m["mes"] for m in d["meses"]] == ["2026-01", "2026-02", "2026-03", "2026-04"]
    assert d["meses"][1]["total"] == 0
    assert d["media"] == 10.00                     # (10 + 0 + 20) / 3, sin el mes en curso
    assert d["meses"][2]["vs_media"] == 100
    assert d["actual"]["prevision"] == 6.00        # 3 € en 15 días de 30
    assert d["peor"]["mes"] == "2026-03" and d["mejor"]["mes"] == "2026-02"
