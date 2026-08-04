"""
conftest.py - Fixtures compartidas por los tests
================================================
Usan una base de datos SQLite en memoria, así cada test arranca limpio
y no toca ningún fichero real.
"""

import pytest

from app.database import conectar, inicializar
from app import repositorio


@pytest.fixture
def conn():
    """Conexión a una BD en memoria con el esquema ya creado."""
    c = conectar(":memory:")
    inicializar(c)
    yield c
    c.close()


@pytest.fixture
def conn_datos(conn):
    """BD con tres tickets de ejemplo para los tests de lectura/estadísticas.

    Resumen de los datos:
      - Mercadona (10-ene): Leche 1.20, Pan 0.80   -> total 2.00
      - Carrefour (12-ene): Leche 1.50             -> total 1.50
      - Mercadona (15-ene): Huevos 2.00            -> total 2.00
    Gasto total: 5.50 € en 3 tickets y 4 productos.
    """
    repositorio.crear_ticket(conn, "Mercadona", "2025-01-10T10:00", [
        {"nombre": "Leche", "precio": "1.20", "categoria": "Lacteos"},
        {"nombre": "Pan", "precio": "0.80", "categoria": "Pan", "observacion": "barra"},
    ])
    repositorio.crear_ticket(conn, "Carrefour", "2025-01-12T18:30", [
        {"nombre": "Leche", "precio": "1.50", "categoria": "Lacteos"},
    ])
    repositorio.crear_ticket(conn, "Mercadona", "2025-01-15T09:00", [
        {"nombre": "Huevos", "precio": "2.00"},
    ])
    return conn
