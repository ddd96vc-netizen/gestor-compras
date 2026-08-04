"""
database.py - Capa de acceso a SQLite
=====================================
Gestiona la conexión a la base de datos y el esquema.

Decisiones de diseño importantes:
  - Los precios se guardan en CÉNTIMOS (enteros) para evitar los errores
    de redondeo de la coma flotante al sumar dinero.
  - Los IDs de tickets y productos son uuid4 (únicos y estables; ya no
    dependen de 'tienda_fecha', que podía colisionar).
  - El total del ticket NO se almacena: se calcula sumando los céntimos
    de sus productos, así nunca queda "desincronizado".

Las funciones `conectar`, `inicializar` y la constante `SCHEMA_SQL` no
dependen de Flask, para poder reutilizarlas desde el script de migración
y desde los tests sin un contexto de aplicación.
"""

import sqlite3
from pathlib import Path


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS tickets (
    id          TEXT PRIMARY KEY,
    tienda      TEXT NOT NULL,
    fecha       TEXT NOT NULL,            -- ISO 'YYYY-MM-DD HH:MM:SS'
    creado_en   TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS productos (
    id              TEXT PRIMARY KEY,
    ticket_id       TEXT NOT NULL,
    nombre          TEXT NOT NULL,
    cantidad        INTEGER NOT NULL DEFAULT 1 CHECK (cantidad >= 1),
    precio_centimos INTEGER NOT NULL CHECK (precio_centimos >= 0),
    importe_centimos INTEGER NOT NULL DEFAULT 0 CHECK (importe_centimos >= 0),
    categoria       TEXT,
    observacion     TEXT,
    posicion        INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (ticket_id) REFERENCES tickets(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_productos_ticket    ON productos(ticket_id);
CREATE INDEX IF NOT EXISTS idx_productos_nombre    ON productos(nombre);
CREATE INDEX IF NOT EXISTS idx_productos_categoria ON productos(categoria);
CREATE INDEX IF NOT EXISTS idx_tickets_fecha       ON tickets(fecha);

CREATE TABLE IF NOT EXISTS favoritos (
    nombre_norm   TEXT PRIMARY KEY,        -- nombre normalizado (minúsculas), evita duplicados
    nombre        TEXT NOT NULL,           -- nombre tal como se marcó (para mostrar)
    creado_en     TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


# ----------------------------------------------------------------------
# Funciones independientes de Flask (migración, tests, scripts)
# ----------------------------------------------------------------------

def conectar(ruta: str) -> sqlite3.Connection:
    """Abre una conexión configurada: filas tipo dict y claves foráneas activas."""
    Path(ruta).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(ruta)
    conn.row_factory = sqlite3.Row             # permite acceder a las columnas por nombre
    conn.execute("PRAGMA foreign_keys = ON")   # activa el ON DELETE CASCADE
    return conn


def inicializar(conn: sqlite3.Connection) -> None:
    """Crea las tablas e índices si todavía no existen, y migra el esquema
    si la base de datos ya existía de una versión anterior (sin `cantidad`)."""
    conn.executescript(SCHEMA_SQL)
    _migrar_esquema(conn)
    conn.commit()


def _migrar_esquema(conn: sqlite3.Connection) -> None:
    """Añade columnas nuevas a bases de datos creadas con un esquema antiguo.

    SQLite no soporta "ADD COLUMN IF NOT EXISTS", así que se comprueba a
    mano con PRAGMA table_info antes de intentar el ALTER TABLE.
    """
    columnas = {fila["name"] for fila in conn.execute("PRAGMA table_info(productos)")}
    if "cantidad" not in columnas:
        conn.execute(
            "ALTER TABLE productos ADD COLUMN cantidad INTEGER NOT NULL DEFAULT 1"
        )
    if "importe_centimos" not in columnas:
        conn.execute(
            "ALTER TABLE productos ADD COLUMN importe_centimos INTEGER NOT NULL DEFAULT 0"
        )
        # Para los productos ya existentes, el importe = precio unitario × cantidad.
        conn.execute(
            "UPDATE productos SET importe_centimos = precio_centimos * cantidad"
        )


# ----------------------------------------------------------------------
# Integración con Flask (se invoca desde create_app, en la Parte 3)
# ----------------------------------------------------------------------

def get_db() -> sqlite3.Connection:
    """Devuelve la conexión asociada a la petición actual (la reutiliza)."""
    from flask import g, current_app
    if "db" not in g:
        g.db = conectar(current_app.config["DATABASE"])
    return g.db


def close_db(e=None) -> None:
    """Cierra la conexión al finalizar la petición."""
    from flask import g
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_app(app) -> None:
    """Registra el cierre de conexión y añade el comando `flask init-db`."""
    import click
    from flask.cli import with_appcontext

    app.teardown_appcontext(close_db)

    @app.cli.command("init-db")
    @with_appcontext
    def init_db_command():
        """Crea las tablas de la base de datos."""
        inicializar(get_db())
        click.echo("✅ Base de datos inicializada.")
