"""
migrar_datos.py - Migración de JSON a SQLite
============================================
Lee el antiguo `solocompras.json` y vuelca los datos en la base de datos
SQLite con el nuevo esquema:

  - IDs únicos (uuid4) para tickets y productos.
  - Precios convertidos a céntimos (enteros).
  - Fechas normalizadas a ISO 'YYYY-MM-DD HH:MM:SS'. Recupera la hora
    desde el id antiguo (p. ej. 'Proxi_2025-12-07 21:28:00') cuando el
    campo 'fecha' solo trae el día.

Uso:
    python migrar_datos.py                                    # rutas por defecto
    python migrar_datos.py --json datos.json --db instance/solocompras.db
    python migrar_datos.py --reset                            # borra y recrea la BD
"""

import argparse
import json
import re
import sys
import uuid
from datetime import datetime
from pathlib import Path

from app.database import conectar, inicializar


_PATRON_FECHA_HORA = re.compile(r"(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2}(?::\d{2})?)")
_PATRON_SOLO_FECHA = re.compile(r"(\d{4}-\d{2}-\d{2})")


def normalizar_fecha(ticket: dict) -> str:
    """Devuelve la fecha del ticket en formato ISO 'YYYY-MM-DD HH:MM:SS'.

    Prioriza el id antiguo porque suele contener la hora completa; si no
    la encuentra, usa el campo 'fecha'; como último recurso, la hora actual.
    """
    fuentes = [str(ticket.get("id", "")), str(ticket.get("fecha", ""))]

    for fuente in fuentes:
        m = _PATRON_FECHA_HORA.search(fuente)
        if m:
            fecha, hora = m.group(1), m.group(2)
            if len(hora) == 5:           # 'HH:MM' -> 'HH:MM:00'
                hora += ":00"
            return f"{fecha} {hora}"

    for fuente in fuentes:
        m = _PATRON_SOLO_FECHA.search(fuente)
        if m:
            return f"{m.group(1)} 00:00:00"

    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def a_centimos(precio) -> int:
    """Convierte un precio en euros a céntimos (entero) sin perder precisión."""
    try:
        return int(round(float(precio) * 100))
    except (TypeError, ValueError):
        return 0


def limpiar(texto):
    """Recorta espacios y devuelve None si la cadena queda vacía."""
    if texto is None:
        return None
    texto = str(texto).strip()
    return texto or None


def migrar(ruta_json: str, ruta_db: str, reset: bool = False) -> None:
    ruta_json_p = Path(ruta_json)
    if not ruta_json_p.exists():
        sys.exit(f"❌ No se encuentra el fichero JSON: {ruta_json_p}")

    with open(ruta_json_p, "r", encoding="utf-8") as f:
        tickets = json.load(f)

    if reset and Path(ruta_db).exists():
        Path(ruta_db).unlink()
        print(f"🗑️  Base de datos anterior eliminada: {ruta_db}")

    conn = conectar(str(ruta_db))
    inicializar(conn)

    # Evitar duplicar datos si la BD ya contiene tickets
    existentes = conn.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
    if existentes and not reset:
        conn.close()
        sys.exit(
            f"⚠️  La base de datos ya contiene {existentes} tickets.\n"
            f"   Usa --reset para borrarla y migrar desde cero."
        )

    n_tickets = n_productos = 0
    total_centimos = 0

    for ticket in tickets:
        ticket_id = uuid.uuid4().hex
        tienda = limpiar(ticket.get("tienda")) or "Desconocida"
        fecha = normalizar_fecha(ticket)

        conn.execute(
            "INSERT INTO tickets (id, tienda, fecha) VALUES (?, ?, ?)",
            (ticket_id, tienda, fecha),
        )
        n_tickets += 1

        for posicion, prod in enumerate(ticket.get("productos", [])):
            nombre = limpiar(prod.get("nombre"))
            if not nombre:
                continue  # se descartan productos sin nombre

            centimos = a_centimos(prod.get("precio"))
            conn.execute(
                """INSERT INTO productos
                       (id, ticket_id, nombre, precio_centimos,
                        categoria, observacion, posicion)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    uuid.uuid4().hex,
                    ticket_id,
                    nombre,
                    centimos,
                    limpiar(prod.get("categoria")),
                    limpiar(prod.get("observacion")),
                    posicion,
                ),
            )
            n_productos += 1
            total_centimos += centimos

    conn.commit()
    conn.close()

    print("✅ Migración completada")
    print(f"   Tickets migrados:   {n_tickets}")
    print(f"   Productos migrados: {n_productos}")
    print(f"   Gasto total:        {total_centimos / 100:.2f} €")
    print(f"   Base de datos:      {ruta_db}")


def main():
    parser = argparse.ArgumentParser(description="Migra solocompras.json a SQLite")
    parser.add_argument("--json", default="solocompras.json",
                        help="Ruta del JSON de origen (por defecto: solocompras.json)")
    parser.add_argument("--db", default="instance/solocompras.db",
                        help="Ruta de la base de datos SQLite de destino")
    parser.add_argument("--reset", action="store_true",
                        help="Borra la base de datos antes de migrar")
    args = parser.parse_args()
    migrar(args.json, args.db, args.reset)


if __name__ == "__main__":
    main()
