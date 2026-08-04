"""
estadisticas.py - Cálculos estadísticos sobre las compras
=========================================================
Todo el dinero se opera en céntimos (enteros) y se convierte a euros solo
al final, para que las sumas no acumulen errores de coma flotante.

Como en el repositorio, cada función recibe la conexión `conn`.
"""

from datetime import datetime

from app.utilidades import a_euros, partes_fecha


def _totales_por_ticket(conn):
    """Filas (id, tienda, fecha, total_cents) con el total de cada ticket."""
    return conn.execute(
        """SELECT t.id, t.tienda, t.fecha,
                  COALESCE(SUM(p.importe_centimos), 0) AS total_cents
           FROM tickets t
           LEFT JOIN productos p ON p.ticket_id = t.id
           GROUP BY t.id"""
    ).fetchall()


def resumen_general(conn) -> dict:
    """Totales generales: gasto, nº de tickets/productos, promedios y extremos."""
    filas = _totales_por_ticket(conn)
    num_tickets = len(filas)
    num_productos = conn.execute("SELECT COUNT(*) FROM productos").fetchone()[0]

    if num_tickets == 0:
        return {
            "total": 0.0, "num_tickets": 0, "num_productos": 0,
            "promedio_ticket": 0.0, "promedio_producto": 0.0,
            "ticket_mas_caro": None, "ticket_mas_barato": None,
        }

    total_cents = sum(f["total_cents"] for f in filas)
    mas_caro = max(filas, key=lambda f: f["total_cents"])
    mas_barato = min(filas, key=lambda f: f["total_cents"])

    def _resumen(f):
        dia, _ = partes_fecha(f["fecha"])
        return {"tienda": f["tienda"], "fecha_dia": dia, "total": a_euros(f["total_cents"])}

    return {
        "total": a_euros(total_cents),
        "num_tickets": num_tickets,
        "num_productos": num_productos,
        "promedio_ticket": round(total_cents / num_tickets / 100, 2),
        "promedio_producto": round(total_cents / num_productos / 100, 2) if num_productos else 0.0,
        "ticket_mas_caro": _resumen(mas_caro),
        "ticket_mas_barato": _resumen(mas_barato),
    }


def gasto_por_tienda(conn) -> dict:
    """Gasto agrupado por tienda, ordenado de mayor a menor, con porcentajes."""
    filas = conn.execute(
        """SELECT t.tienda, COALESCE(SUM(p.importe_centimos), 0) AS total_cents
           FROM tickets t
           LEFT JOIN productos p ON p.ticket_id = t.id
           GROUP BY t.tienda
           ORDER BY total_cents DESC"""
    ).fetchall()

    total_general = sum(f["total_cents"] for f in filas)
    tiendas = []
    for f in filas:
        pct = (f["total_cents"] / total_general * 100) if total_general else 0
        tiendas.append({
            "nombre": f["tienda"],
            "total": a_euros(f["total_cents"]),
            "porcentaje": round(pct, 1),
        })

    return {
        "tiendas": tiendas,
        "tienda_top": tiendas[0] if tiendas else None,
        "total_general": a_euros(total_general),
    }


def gastos_por_rango(conn, fecha_inicio, fecha_fin) -> dict:
    """Gasto en un rango de fechas (ambas en formato 'YYYY-MM-DD', inclusive)."""
    try:
        datetime.strptime(fecha_inicio, "%Y-%m-%d")
        datetime.strptime(fecha_fin, "%Y-%m-%d")
    except (TypeError, ValueError):
        return {
            "error": "Formato de fecha inválido",
            "fecha_inicio": fecha_inicio, "fecha_fin": fecha_fin,
            "tickets": [], "total": 0.0, "num_tickets": 0, "promedio": 0.0,
        }

    filas = conn.execute(
        """SELECT t.id, t.tienda, t.fecha,
                  COALESCE(SUM(p.importe_centimos), 0) AS total_cents,
                  COUNT(p.id) AS num_productos
           FROM tickets t
           LEFT JOIN productos p ON p.ticket_id = t.id
           WHERE date(t.fecha) BETWEEN ? AND ?
           GROUP BY t.id
           ORDER BY t.fecha""",
        (fecha_inicio, fecha_fin),
    ).fetchall()

    tickets = []
    total_cents = 0
    for f in filas:
        dia, _ = partes_fecha(f["fecha"])
        tickets.append({
            "id": f["id"],
            "tienda": f["tienda"],
            "fecha_dia": dia,
            "total": a_euros(f["total_cents"]),
            "num_productos": f["num_productos"],
        })
        total_cents += f["total_cents"]

    n = len(tickets)
    return {
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "tickets": tickets,
        "total": a_euros(total_cents),
        "num_tickets": n,
        "promedio": round(total_cents / n / 100, 2) if n else 0.0,
    }


def frecuencia_producto(conn, nombre) -> dict:
    """Analiza con qué frecuencia y a qué precio se compra un producto."""
    nombre = (nombre or "").strip()
    vacio = {
        "nombre_busqueda": nombre, "compras": [], "frecuencia": 0,
        "precio_promedio": 0.0, "precio_minimo": 0.0, "precio_maximo": 0.0,
        "diferencia": 0.0, "tiendas_distintas": [], "tienda_mas_barata": None,
        "promedios_tiendas": {},
    }
    if not nombre:
        return vacio

    patron = f"%{nombre.lower()}%"
    filas = conn.execute(
        """SELECT p.nombre, p.cantidad, p.precio_centimos, p.categoria, p.observacion,
                  t.tienda, t.fecha
           FROM productos p
           JOIN tickets t ON t.id = p.ticket_id
           WHERE lower(p.nombre) LIKE ?
           ORDER BY t.fecha DESC""",
        (patron,),
    ).fetchall()

    if not filas:
        return vacio

    compras = []
    precios = []                     # céntimos (precio UNITARIO, no el importe)
    por_tienda = {}                  # tienda -> [céntimos]
    for f in filas:
        dia, _ = partes_fecha(f["fecha"])
        compras.append({
            "fecha_dia": dia,
            "tienda": f["tienda"],
            "cantidad": f["cantidad"],
            "precio": a_euros(f["precio_centimos"]),
            "nombre_completo": f["nombre"],
            "categoria": f["categoria"] or "Sin categoría",
            "observacion": f["observacion"] or "",
        })
        precios.append(f["precio_centimos"])
        por_tienda.setdefault(f["tienda"], []).append(f["precio_centimos"])

    promedios_tiendas = {
        tienda: a_euros(round(sum(cs) / len(cs)))
        for tienda, cs in por_tienda.items()
    }
    tienda_barata = min(por_tienda.items(), key=lambda kv: sum(kv[1]) / len(kv[1]))

    return {
        "nombre_busqueda": nombre,
        "compras": compras,
        "frecuencia": len(compras),
        "precio_promedio": round(sum(precios) / len(precios) / 100, 2),
        "precio_minimo": a_euros(min(precios)),
        "precio_maximo": a_euros(max(precios)),
        "diferencia": a_euros(max(precios) - min(precios)),
        "tiendas_distintas": sorted(por_tienda.keys()),
        "tienda_mas_barata": {
            "nombre": tienda_barata[0],
            "promedio": a_euros(round(sum(tienda_barata[1]) / len(tienda_barata[1]))),
        },
        "promedios_tiendas": promedios_tiendas,
    }


def stats_categorias(conn) -> dict:
    """Resumen por categoría: {categoria: {cantidad, total}}.

    Los productos sin categoría se agrupan bajo 'Sin categoría'.
    """
    filas = conn.execute(
        """SELECT COALESCE(NULLIF(TRIM(categoria), ''), 'Sin categoría') AS cat,
                  COUNT(*) AS cantidad,
                  COALESCE(SUM(importe_centimos), 0) AS total_cents
           FROM productos
           GROUP BY cat
           ORDER BY total_cents DESC"""
    ).fetchall()

    return {
        f["cat"]: {"cantidad": f["cantidad"], "total": a_euros(f["total_cents"])}
        for f in filas
    }
