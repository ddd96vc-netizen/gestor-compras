"""
test_estadisticas.py - Tests de los cálculos estadísticos
"""

from app import estadisticas


def test_resumen_general(conn_datos):
    r = estadisticas.resumen_general(conn_datos)
    assert r["total"] == 5.50
    assert r["num_tickets"] == 3
    assert r["num_productos"] == 4
    assert r["promedio_ticket"] == round(5.50 / 3, 2)         # 1.83
    assert r["ticket_mas_caro"]["total"] == 2.00
    assert r["ticket_mas_barato"]["total"] == 1.50


def test_resumen_general_sin_datos(conn):
    r = estadisticas.resumen_general(conn)
    assert r["total"] == 0.0
    assert r["num_tickets"] == 0
    assert r["ticket_mas_caro"] is None


def test_gasto_por_tienda(conn_datos):
    datos = estadisticas.gasto_por_tienda(conn_datos)
    assert datos["total_general"] == 5.50

    # Mercadona (2.00 + 2.00 = 4.00) debe ir primera
    assert datos["tienda_top"]["nombre"] == "Mercadona"
    assert datos["tienda_top"]["total"] == 4.00

    # Los porcentajes suman ~100
    assert round(sum(t["porcentaje"] for t in datos["tiendas"])) == 100


def test_gastos_por_rango(conn_datos):
    # Rango que incluye solo los dos primeros tickets (10 y 12 de enero)
    datos = estadisticas.gastos_por_rango(conn_datos, "2025-01-10", "2025-01-12")
    assert datos["num_tickets"] == 2
    assert datos["total"] == 3.50                            # 2.00 + 1.50

    # Rango vacío
    vacio = estadisticas.gastos_por_rango(conn_datos, "2025-02-01", "2025-02-28")
    assert vacio["num_tickets"] == 0
    assert vacio["total"] == 0.0


def test_gastos_por_rango_fecha_invalida(conn_datos):
    datos = estadisticas.gastos_por_rango(conn_datos, "fecha-mala", "2025-01-12")
    assert "error" in datos


def test_frecuencia_producto(conn_datos):
    datos = estadisticas.frecuencia_producto(conn_datos, "leche")
    assert datos["frecuencia"] == 2
    assert datos["precio_minimo"] == 1.20
    assert datos["precio_maximo"] == 1.50
    assert datos["diferencia"] == 0.30
    assert sorted(datos["tiendas_distintas"]) == ["Carrefour", "Mercadona"]
    # Mercadona (1.20) es más barata que Carrefour (1.50) para la leche
    assert datos["tienda_mas_barata"]["nombre"] == "Mercadona"


def test_frecuencia_producto_inexistente(conn_datos):
    datos = estadisticas.frecuencia_producto(conn_datos, "caviar")
    assert datos["frecuencia"] == 0
    assert datos["compras"] == []


def test_stats_categorias(conn_datos):
    stats = estadisticas.stats_categorias(conn_datos)
    # Lacteos: Leche 1.20 + Leche 1.50 = 2.70 en 2 productos
    assert stats["Lacteos"]["cantidad"] == 2
    assert stats["Lacteos"]["total"] == 2.70
    # Huevos no tenía categoría -> 'Sin categoría'
    assert "Sin categoría" in stats
    assert stats["Sin categoría"]["cantidad"] == 1
