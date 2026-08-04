"""
test_repositorio.py - Tests del CRUD de tickets y productos
"""

from app import repositorio


# ----------------------------------------------------------------------
# Crear y leer
# ----------------------------------------------------------------------

def test_crear_y_obtener_ticket(conn):
    ticket_id = repositorio.crear_ticket(conn, "Mercadona", "2025-03-01T12:00", [
        {"nombre": "Leche", "precio": "1.20", "categoria": "Lacteos"},
        {"nombre": "Pan", "precio": "0.80"},
    ])
    ticket = repositorio.obtener_ticket(conn, ticket_id)

    assert ticket is not None
    assert ticket["tienda"] == "Mercadona"
    assert ticket["num_productos"] == 2
    assert ticket["total"] == 2.00
    assert ticket["fecha"] == "2025-03-01 12:00:00"          # normalizada a ISO
    assert ticket["fecha_input"] == "2025-03-01T12:00"       # lista para el <input>


def test_obtener_ticket_inexistente_devuelve_none(conn):
    assert repositorio.obtener_ticket(conn, "no-existe") is None


def test_id_de_ticket_es_unico(conn):
    """Dos tickets con la misma tienda y fecha NO colisionan (bug antiguo)."""
    id1 = repositorio.crear_ticket(conn, "Mercadona", "2025-03-01T12:00",
                                   [{"nombre": "A", "precio": "1.00"}])
    id2 = repositorio.crear_ticket(conn, "Mercadona", "2025-03-01T12:00",
                                   [{"nombre": "B", "precio": "1.00"}])
    assert id1 != id2


def test_producto_sin_nombre_se_ignora(conn):
    ticket_id = repositorio.crear_ticket(conn, "Tienda", "2025-03-01T12:00", [
        {"nombre": "Válido", "precio": "1.00"},
        {"nombre": "   ", "precio": "5.00"},        # se descarta
        {"nombre": None, "precio": "9.00"},         # se descarta
    ])
    ticket = repositorio.obtener_ticket(conn, ticket_id)
    assert ticket["num_productos"] == 1
    assert ticket["total"] == 1.00


# ----------------------------------------------------------------------
# Dinero
# ----------------------------------------------------------------------

def test_dinero_sin_errores_de_coma_flotante(conn):
    """0.10 + 0.20 debe dar 0.30 exacto (con float ingenuo sería 0.30000000004)."""
    ticket_id = repositorio.crear_ticket(conn, "Tienda", "2025-03-01T12:00", [
        {"nombre": "A", "precio": "0.10"},
        {"nombre": "B", "precio": "0.20"},
    ])
    ticket = repositorio.obtener_ticket(conn, ticket_id)
    assert ticket["total"] == 0.30


# ----------------------------------------------------------------------
# Listar
# ----------------------------------------------------------------------

def test_listar_tickets_orden_y_limite(conn_datos):
    todos = repositorio.listar_tickets(conn_datos)
    assert len(todos) == 3
    # Más recientes primero (15-ene antes que 10-ene)
    assert todos[0]["fecha_dia"] == "2025-01-15"
    assert todos[-1]["fecha_dia"] == "2025-01-10"

    limitado = repositorio.listar_tickets(conn_datos, limite=2)
    assert len(limitado) == 2


# ----------------------------------------------------------------------
# Actualizar
# ----------------------------------------------------------------------

def test_actualizar_ticket_reemplaza_productos(conn):
    ticket_id = repositorio.crear_ticket(conn, "Mercadona", "2025-03-01T12:00", [
        {"nombre": "Leche", "precio": "1.20"},
        {"nombre": "Pan", "precio": "0.80"},
    ])
    ok = repositorio.actualizar_ticket(conn, ticket_id, "Lidl", "2025-03-02T09:00", [
        {"nombre": "Agua", "precio": "0.50"},
    ])
    assert ok is True

    ticket = repositorio.obtener_ticket(conn, ticket_id)
    assert ticket["tienda"] == "Lidl"
    assert ticket["num_productos"] == 1
    assert ticket["total"] == 0.50


def test_actualizar_ticket_inexistente(conn):
    assert repositorio.actualizar_ticket(conn, "no-existe", "X", "2025-01-01T00:00", []) is False


# ----------------------------------------------------------------------
# Editar producto
# ----------------------------------------------------------------------

def test_editar_producto(conn):
    ticket_id = repositorio.crear_ticket(conn, "Tienda", "2025-03-01T12:00", [
        {"nombre": "Leche", "precio": "1.20"},
    ])
    producto_id = repositorio.obtener_ticket(conn, ticket_id)["productos"][0]["id"]

    ok = repositorio.editar_producto(conn, producto_id, "Leche entera", "1.35",
                                     categoria="Lacteos", observacion="oferta")
    assert ok is True

    ticket = repositorio.obtener_ticket(conn, ticket_id)
    prod = ticket["productos"][0]
    assert prod["nombre"] == "Leche entera"
    assert prod["precio"] == 1.35
    assert prod["categoria"] == "Lacteos"
    # El total del ticket se recalcula solo (es SUM de los productos)
    assert ticket["total"] == 1.35


# ----------------------------------------------------------------------
# Eliminar
# ----------------------------------------------------------------------

def test_eliminar_ticket_borra_productos_en_cascada(conn):
    ticket_id = repositorio.crear_ticket(conn, "Tienda", "2025-03-01T12:00", [
        {"nombre": "A", "precio": "1.00"},
        {"nombre": "B", "precio": "2.00"},
    ])
    assert repositorio.eliminar_ticket(conn, ticket_id) is True
    assert repositorio.obtener_ticket(conn, ticket_id) is None
    # No quedan productos huérfanos
    huérfanos = conn.execute(
        "SELECT COUNT(*) FROM productos WHERE ticket_id = ?", (ticket_id,)
    ).fetchone()[0]
    assert huérfanos == 0


def test_eliminar_ticket_inexistente(conn):
    assert repositorio.eliminar_ticket(conn, "no-existe") is False


# ----------------------------------------------------------------------
# Búsqueda y categorías
# ----------------------------------------------------------------------

def test_buscar_productos(conn_datos):
    resultados = repositorio.buscar_productos(conn_datos, "leche")
    assert len(resultados) == 2                          # se compró en 2 tickets
    assert all("leche" in r["nombre"].lower() for r in resultados)

    assert repositorio.buscar_productos(conn_datos, "noexiste") == []
    assert repositorio.buscar_productos(conn_datos, "") == []


def test_categorias_existentes(conn_datos):
    categorias = repositorio.categorias_existentes(conn_datos)
    assert categorias == ["Lacteos", "Pan"]              # ordenadas, sin nulos


def test_productos_por_categoria(conn_datos):
    productos = repositorio.productos_por_categoria(conn_datos, "lacteos")
    assert len(productos) == 2                            # 2 leches
    assert {p["tienda"] for p in productos} == {"Mercadona", "Carrefour"}
