"""
test_favoritos.py - Tests de los productos favoritos
"""

from app import repositorio


def _ticket_con_leche(conn):
    repositorio.crear_ticket(conn, "Mercadona", "2025-01-10T10:00", [
        {"nombre": "Leche", "precio": "1.20"},
        {"nombre": "Pan", "precio": "0.80"},
    ])
    repositorio.crear_ticket(conn, "Carrefour", "2025-01-20T18:00", [
        {"nombre": "Leche", "precio": "1.50"},
    ])


def test_alternar_favorito(conn):
    _ticket_con_leche(conn)
    assert repositorio.es_favorito(conn, "Leche") is False
    assert repositorio.alternar_favorito(conn, "Leche") is True
    assert repositorio.es_favorito(conn, "Leche") is True
    assert repositorio.alternar_favorito(conn, "Leche") is False
    assert repositorio.es_favorito(conn, "Leche") is False


def test_favorito_no_se_duplica_ni_distingue_mayusculas(conn):
    _ticket_con_leche(conn)
    repositorio.alternar_favorito(conn, "Leche")
    # Mismo producto con otro formato -> lo quita (no crea un segundo)
    repositorio.alternar_favorito(conn, "  LECHE ")
    assert repositorio.es_favorito(conn, "leche") is False
    repositorio.alternar_favorito(conn, "Leche")
    assert len(repositorio.nombres_favoritos(conn)) == 1


def test_listar_favoritos_con_resumen(conn):
    _ticket_con_leche(conn)
    repositorio.alternar_favorito(conn, "Leche")
    lista = repositorio.listar_favoritos(conn)
    assert len(lista) == 1
    leche = lista[0]
    assert leche["nombre"] == "Leche"
    assert leche["veces"] == 2
    assert leche["precio_min"] == 1.20
    assert leche["ultima_fecha"] == "2025-01-20"


def test_marca_favorito_en_productos(conn):
    _ticket_con_leche(conn)
    repositorio.alternar_favorito(conn, "Leche")
    resultados = repositorio.buscar_productos(conn, "leche")
    assert all(r["favorito"] for r in resultados)
    # Un producto no marcado no aparece como favorito
    pan = repositorio.buscar_productos(conn, "pan")
    assert all(p["favorito"] is False for p in pan)


def test_listar_favoritos_vacio(conn):
    assert repositorio.listar_favoritos(conn) == []


def test_marcar_favorito_al_crear_ticket(conn):
    from app import repositorio as repo
    repo.crear_ticket(conn, "Mercadona", "2025-01-10T10:00", [
        {"nombre": "Leche", "precio": "1.20", "favorito": "1"},
        {"nombre": "Pan", "precio": "0.80", "favorito": "0"},
    ])
    assert repo.es_favorito(conn, "Leche") is True
    assert repo.es_favorito(conn, "Pan") is False


def test_favorito_sobrevive_si_queda_otra_compra(conn):
    from app import repositorio as repo
    t1 = repo.crear_ticket(conn, "Mercadona", "2025-01-10T10:00",
                           [{"nombre": "Leche", "precio": "1.20", "favorito": "1"}])
    repo.crear_ticket(conn, "Carrefour", "2025-01-20T18:00",
                      [{"nombre": "Leche", "precio": "1.50"}])
    repo.eliminar_ticket(conn, t1)          # aún queda una compra de Leche
    assert repo.es_favorito(conn, "Leche") is True


def test_favorito_se_limpia_cuando_no_quedan_compras(conn):
    from app import repositorio as repo
    t1 = repo.crear_ticket(conn, "Mercadona", "2025-01-10T10:00",
                           [{"nombre": "Leche", "precio": "1.20", "favorito": "1"}])
    repo.eliminar_ticket(conn, t1)          # era la única compra
    assert repo.es_favorito(conn, "Leche") is False


def test_favorito_huerfano_al_editar(conn):
    from app import repositorio as repo
    t1 = repo.crear_ticket(conn, "Lidl", "2025-02-01T10:00",
                           [{"nombre": "Yogur", "precio": "0.90", "favorito": "1"}])
    repo.actualizar_ticket(conn, t1, "Lidl", "2025-02-01T10:00",
                           [{"nombre": "Agua", "precio": "0.50"}])
    assert repo.es_favorito(conn, "Yogur") is False
