"""Nombre oficial de cada tienda (app/tiendas.py)."""

import pytest

from app import repositorio
from app.tiendas import tienda_canonica, normalizar_tiendas


@pytest.mark.parametrize("leido, oficial", [
    ("El Jamon (Pintor)", "El Jamon"),
    ("Proxy (EL Jamon)", "El Jamon"),
    ("El Jamon (Proxy)", "El Jamon"),
    ("Jamon", "El Jamon"),
    ("El Jamón (cercaTrabajo)", "El Jamon"),
    ("4 Pintor  Espinosa _ F Datou 19", "El Jamon"),
    ("Chino Proxi", "Chino Verduras Fiel"),
    ("Chino Proxy", "Chino Verduras Fiel"),
    ("Chino Proxi (El Jamo)", "Chino Verduras Fiel"),
    ("Chino Cosas Proxi", "Chino Articul"),
    ("Chino GranviaParque", "Chino Articul"),
    ("Chino Zoco", "Chino Zoco"),
    ("Proxy", "Proxi"),
    ("proxi", "Proxi"),
    ("DIA", "Dia"),
    ("Grupo Dia", "Dia"),
    ("Coviran Lin", "Coviran Lin"),
    ("Coviran", "Coviran Lin"),
    ("  Zoco  ", "Zoco"),
])
def test_tienda_canonica(leido, oficial):
    assert tienda_canonica(leido) == oficial


def test_al_guardar_se_usa_el_nombre_oficial(conn):
    tid = repositorio.crear_ticket(conn, "Proxy (El Jamon)", "2026-11-01 10:00",
                                   [{"nombre": "Pan", "precio": "1"}])
    assert conn.execute("SELECT tienda FROM tickets WHERE id = ?", (tid,)).fetchone()[0] == "El Jamon"


def test_normalizar_tiendas_guardadas(conn):
    conn.execute("INSERT INTO tickets (id, tienda, fecha) VALUES ('a', 'DIA', '2026-01-01 10:00:00')")
    conn.execute("INSERT INTO tickets (id, tienda, fecha) VALUES ('b', 'Chino Proxy', '2026-01-02 10:00:00')")
    conn.execute("INSERT INTO tickets (id, tienda, fecha) VALUES ('c', 'Zoco', '2026-01-03 10:00:00')")
    cambios = normalizar_tiendas(conn)
    assert sorted(c[1] for c in cambios) == ["Chino Verduras Fiel", "Dia"]
    assert normalizar_tiendas(conn) == []          # segunda vez: nada que cambiar
