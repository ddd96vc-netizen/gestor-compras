"""
repositorio.py - Operaciones CRUD sobre tickets y productos
===========================================================
Cada función recibe explícitamente la conexión `conn` (sqlite3) en lugar
de usar el contexto de Flask. Así la lógica queda desacoplada del framework
y se puede testear de forma aislada.

Notas:
  - El total del ticket nunca se guarda: se calcula con SUM(importe_centimos).
  - `cantidad` es el número de unidades compradas (por defecto 1 si se deja
    vacío). `precio` es el precio UNITARIO (informativo). `importe` es el
    dinero real de la línea: por defecto precio × cantidad, pero el usuario
    puede ajustarlo (ofertas, redondeos), por eso se guarda aparte.
  - Todas las escrituras usan `with conn:` (transacción atómica: confirma
    al terminar, deshace si hay excepción).
"""

import uuid

from app.utilidades import (
    a_centimos, a_euros, a_cantidad, limpiar, normalizar_fecha, partes_fecha,
)


# ----------------------------------------------------------------------
# Conversores fila -> dict
# ----------------------------------------------------------------------

def _fila_producto(row) -> dict:
    return {
        "id": row["id"],
        "ticket_id": row["ticket_id"],
        "nombre": row["nombre"],
        "cantidad": row["cantidad"],
        "precio": a_euros(row["precio_centimos"]),
        "importe": a_euros(row["importe_centimos"]),
        # True si el importe no es exactamente precio × cantidad (fue ajustado).
        "importe_manual": row["importe_centimos"] != row["precio_centimos"] * row["cantidad"],
        "categoria": row["categoria"],
        "observacion": row["observacion"],
        "posicion": row["posicion"],
    }


def _insertar_productos(conn, ticket_id, productos):
    """Inserta una lista de productos (dicts) para un ticket dado."""
    for posicion, prod in enumerate(productos):
        nombre = limpiar(prod.get("nombre"))
        if not nombre:
            continue  # se ignoran productos sin nombre

        cantidad = a_cantidad(prod.get("cantidad"))
        precio_cents = a_centimos(prod.get("precio") or 0)
        importe_cents = _resolver_importe(prod.get("importe"), precio_cents, cantidad)

        conn.execute(
            """INSERT INTO productos
                   (id, ticket_id, nombre, cantidad, precio_centimos,
                    importe_centimos, categoria, observacion, posicion)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                uuid.uuid4().hex,
                ticket_id,
                nombre,
                cantidad,
                precio_cents,
                importe_cents,
                limpiar(prod.get("categoria")),
                limpiar(prod.get("observacion")),
                posicion,
            ),
        )


def _resolver_importe(importe_bruto, precio_cents, cantidad) -> int:
    """Importe de la línea en céntimos.

    Si el usuario indicó un importe, se usa ese (permite ajustar el total por
    ofertas o redondeos). Si viene vacío, se calcula como precio × cantidad.
    """
    if importe_bruto is None or str(importe_bruto).strip() == "":
        return precio_cents * cantidad
    try:
        return a_centimos(importe_bruto)
    except (ValueError, TypeError):
        return precio_cents * cantidad


# ----------------------------------------------------------------------
# Lectura
# ----------------------------------------------------------------------

def listar_tickets(conn, limite=None) -> list:
    """Lista de tickets (más recientes primero) con total y nº de productos.

    No incluye el detalle de productos: es para vistas de listado.
    """
    sql = """
        SELECT t.id, t.tienda, t.fecha,
               COALESCE(SUM(p.importe_centimos), 0) AS total_cents,
               COUNT(p.id) AS num_productos
        FROM tickets t
        LEFT JOIN productos p ON p.ticket_id = t.id
        GROUP BY t.id
        ORDER BY t.fecha DESC
    """
    params = ()
    if limite is not None:
        sql += " LIMIT ?"
        params = (limite,)

    tickets = []
    for row in conn.execute(sql, params):
        dia, _ = partes_fecha(row["fecha"])
        tickets.append({
            "id": row["id"],
            "tienda": row["tienda"],
            "fecha": row["fecha"],
            "fecha_dia": dia,
            "total": a_euros(row["total_cents"]),
            "num_productos": row["num_productos"],
        })
    return tickets


def obtener_ticket(conn, ticket_id):
    """Devuelve un ticket con su lista de productos, o None si no existe."""
    fila = conn.execute(
        """SELECT t.id, t.tienda, t.fecha,
                  COALESCE(SUM(p.importe_centimos), 0) AS total_cents
           FROM tickets t
           LEFT JOIN productos p ON p.ticket_id = t.id
           WHERE t.id = ?
           GROUP BY t.id""",
        (ticket_id,),
    ).fetchone()

    if fila is None:
        return None

    productos = [
        _fila_producto(r)
        for r in conn.execute(
            "SELECT * FROM productos WHERE ticket_id = ? ORDER BY posicion",
            (ticket_id,),
        )
    ]
    _marcar_favoritos(conn, productos)
    dia, input_val = partes_fecha(fila["fecha"])
    return {
        "id": fila["id"],
        "tienda": fila["tienda"],
        "fecha": fila["fecha"],
        "fecha_dia": dia,
        "fecha_input": input_val,
        "total": a_euros(fila["total_cents"]),
        "num_productos": len(productos),
        "productos": productos,
    }


def buscar_productos(conn, texto) -> list:
    """Busca productos cuyo nombre contenga `texto` (sin distinguir mayúsculas)."""
    texto = (texto or "").strip()
    if not texto:
        return []

    patron = f"%{texto.lower()}%"
    filas = conn.execute(
        """SELECT p.id, p.nombre, p.cantidad, p.precio_centimos, p.importe_centimos,
                  p.categoria, p.observacion, t.id AS ticket_id, t.tienda, t.fecha
           FROM productos p
           JOIN tickets t ON t.id = p.ticket_id
           WHERE lower(p.nombre) LIKE ?
           ORDER BY t.fecha DESC""",
        (patron,),
    )

    resultados = []
    for row in filas:
        dia, _ = partes_fecha(row["fecha"])
        resultados.append({
            "id": row["id"],
            "nombre": row["nombre"],
            "cantidad": row["cantidad"],
            "precio": a_euros(row["precio_centimos"]),
            "importe": a_euros(row["importe_centimos"]),
            "categoria": row["categoria"],
            "observacion": row["observacion"],
            "ticket_id": row["ticket_id"],
            "tienda": row["tienda"],
            "fecha_dia": dia,
        })
    _marcar_favoritos(conn, resultados)
    return resultados


def productos_por_categoria(conn, categoria) -> list:
    """Devuelve los productos de una categoría concreta."""
    filas = conn.execute(
        """SELECT p.id, p.nombre, p.cantidad, p.precio_centimos, p.importe_centimos,
                  p.categoria, p.observacion, t.tienda, t.fecha
           FROM productos p
           JOIN tickets t ON t.id = p.ticket_id
           WHERE lower(p.categoria) = lower(?)
           ORDER BY t.fecha DESC""",
        (categoria,),
    )

    resultados = []
    for row in filas:
        dia, _ = partes_fecha(row["fecha"])
        resultados.append({
            "id": row["id"],
            "nombre": row["nombre"],
            "cantidad": row["cantidad"],
            "precio": a_euros(row["precio_centimos"]),
            "importe": a_euros(row["importe_centimos"]),
            "categoria": row["categoria"],
            "observacion": row["observacion"],
            "tienda": row["tienda"],
            "fecha_dia": dia,
        })
    _marcar_favoritos(conn, resultados)
    return resultados


def categorias_existentes(conn) -> list:
    """Lista ordenada de las categorías usadas (sin nulos ni vacías)."""
    filas = conn.execute(
        """SELECT DISTINCT categoria
           FROM productos
           WHERE categoria IS NOT NULL AND TRIM(categoria) != ''
           ORDER BY categoria"""
    )
    return [row["categoria"] for row in filas]


# ----------------------------------------------------------------------
# Favoritos (marcados por NOMBRE de producto)
# ----------------------------------------------------------------------

def _norm(nombre) -> str:
    """Normaliza un nombre para comparar/agrupar (minúsculas, sin espacios extra)."""
    return " ".join((nombre or "").split()).lower()


def nombres_favoritos(conn) -> set:
    """Conjunto de nombres normalizados marcados como favoritos."""
    return {row["nombre_norm"] for row in conn.execute("SELECT nombre_norm FROM favoritos")}


def es_favorito(conn, nombre) -> bool:
    return conn.execute(
        "SELECT 1 FROM favoritos WHERE nombre_norm = ?", (_norm(nombre),)
    ).fetchone() is not None


def alternar_favorito(conn, nombre) -> bool:
    """Añade o quita un favorito por nombre. Devuelve el estado final (True = favorito)."""
    nombre = limpiar(nombre)
    if not nombre:
        return False
    norm = _norm(nombre)
    with conn:
        existe = conn.execute(
            "SELECT 1 FROM favoritos WHERE nombre_norm = ?", (norm,)
        ).fetchone()
        if existe:
            conn.execute("DELETE FROM favoritos WHERE nombre_norm = ?", (norm,))
            return False
        conn.execute(
            "INSERT INTO favoritos (nombre_norm, nombre) VALUES (?, ?)", (norm, nombre)
        )
        return True


def listar_favoritos(conn) -> list:
    """Listado de favoritos con un resumen de cada producto (veces, precio mín., última compra).

    El emparejamiento se hace en Python para que la normalización sea idéntica
    a la de `_norm` (evita descuadres con acentos que tendría lower() de SQL).
    """
    favoritos = {row["nombre_norm"]: row["nombre"]
                 for row in conn.execute("SELECT nombre_norm, nombre FROM favoritos")}
    if not favoritos:
        return []

    # Agregados por nombre normalizado a partir de todas las líneas de producto.
    agregados = {}
    filas = conn.execute(
        """SELECT p.nombre, p.precio_centimos, t.tienda, t.fecha
           FROM productos p JOIN tickets t ON t.id = p.ticket_id"""
    )
    for f in filas:
        norm = _norm(f["nombre"])
        if norm not in favoritos:
            continue
        info = agregados.setdefault(norm, {"veces": 0, "min": None, "ultima": ""})
        info["veces"] += 1
        if info["min"] is None or f["precio_centimos"] < info["min"]:
            info["min"] = f["precio_centimos"]
        if f["fecha"] > info["ultima"]:
            info["ultima"] = f["fecha"]

    resultado = []
    for norm, nombre in sorted(favoritos.items(), key=lambda kv: kv[1].lower()):
        info = agregados.get(norm, {"veces": 0, "min": None, "ultima": ""})
        resultado.append({
            "nombre": nombre,
            "veces": info["veces"],
            "precio_min": a_euros(info["min"]) if info["min"] is not None else None,
            "ultima_fecha": info["ultima"][:10] if info["ultima"] else None,
        })
    return resultado


def _marcar_favoritos(conn, productos):
    """Añade el campo booleano `favorito` a cada dict de producto de la lista."""
    favoritos = nombres_favoritos(conn)
    for p in productos:
        p["favorito"] = _norm(p["nombre"]) in favoritos
    return productos


def limpiar_favoritos_huerfanos(conn) -> int:
    """Elimina los favoritos que ya no tienen NINGUNA compra asociada.

    Se llama tras borrar un ticket o editar sus productos. Un favorito sobrevive
    mientras quede al menos una línea de producto con ese nombre; solo se quita
    cuando desaparece la última. Devuelve cuántos favoritos se eliminaron.
    """
    nombres_en_uso = {_norm(row["nombre"])
                      for row in conn.execute("SELECT DISTINCT nombre FROM productos")}
    huerfanos = [norm for norm in nombres_favoritos(conn) if norm not in nombres_en_uso]
    for norm in huerfanos:
        conn.execute("DELETE FROM favoritos WHERE nombre_norm = ?", (norm,))
    return len(huerfanos)


def _confirmar_favoritos_marcados(conn, productos):
    """Al guardar un ticket, marca como favoritos los productos con el corazón activo.

    Solo AÑADE (no quita): desmarcar aquí no borra un favorito que pueda venir de
    otra compra. La eliminación se hace desde el corazón directo o al quedar huérfano.
    """
    for prod in productos:
        marcado = str(prod.get("favorito", "")).lower() in ("1", "true", "on", "si")
        if not marcado:
            continue
        nombre = limpiar(prod.get("nombre"))
        if nombre:
            conn.execute(
                "INSERT OR IGNORE INTO favoritos (nombre_norm, nombre) VALUES (?, ?)",
                (_norm(nombre), nombre),
            )


# ----------------------------------------------------------------------
# Escritura
# ----------------------------------------------------------------------

def crear_ticket(conn, tienda, fecha, productos) -> str:
    """Crea un ticket con sus productos y devuelve el id generado.

    `productos` es una lista de dicts con claves:
    nombre, cantidad (opcional, por defecto 1), precio (unitario, en euros),
    categoria, observacion.
    """
    ticket_id = uuid.uuid4().hex
    tienda = limpiar(tienda) or "Desconocida"
    fecha_iso = normalizar_fecha(fecha)

    with conn:
        conn.execute(
            "INSERT INTO tickets (id, tienda, fecha) VALUES (?, ?, ?)",
            (ticket_id, tienda, fecha_iso),
        )
        _insertar_productos(conn, ticket_id, productos)
        _confirmar_favoritos_marcados(conn, productos)

    return ticket_id


def actualizar_ticket(conn, ticket_id, tienda, fecha, productos) -> bool:
    """Actualiza un ticket: reemplaza tienda, fecha y la lista de productos."""
    existe = conn.execute(
        "SELECT 1 FROM tickets WHERE id = ?", (ticket_id,)
    ).fetchone()
    if existe is None:
        return False

    tienda = limpiar(tienda) or "Desconocida"
    fecha_iso = normalizar_fecha(fecha)

    with conn:
        conn.execute(
            "UPDATE tickets SET tienda = ?, fecha = ? WHERE id = ?",
            (tienda, fecha_iso, ticket_id),
        )
        # Estrategia simple y robusta: borrar e insertar de nuevo.
        conn.execute("DELETE FROM productos WHERE ticket_id = ?", (ticket_id,))
        _insertar_productos(conn, ticket_id, productos)
        _confirmar_favoritos_marcados(conn, productos)
        limpiar_favoritos_huerfanos(conn)

    return True


def editar_producto(conn, producto_id, nombre, precio, cantidad=None,
                    importe=None, categoria=None, observacion=None) -> bool:
    """Edita un único producto. Devuelve True si existía y se actualizó."""
    nombre = limpiar(nombre)
    if not nombre:
        return False

    cant = a_cantidad(cantidad)
    precio_cents = a_centimos(precio or 0)
    importe_cents = _resolver_importe(importe, precio_cents, cant)

    with conn:
        cur = conn.execute(
            """UPDATE productos
               SET nombre = ?, cantidad = ?, precio_centimos = ?,
                   importe_centimos = ?, categoria = ?, observacion = ?
               WHERE id = ?""",
            (
                nombre,
                cant,
                precio_cents,
                importe_cents,
                limpiar(categoria),
                limpiar(observacion),
                producto_id,
            ),
        )
    return cur.rowcount > 0


def eliminar_ticket(conn, ticket_id) -> bool:
    """Elimina un ticket (sus productos se borran en cascada)."""
    with conn:
        cur = conn.execute("DELETE FROM tickets WHERE id = ?", (ticket_id,))
        if cur.rowcount > 0:
            limpiar_favoritos_huerfanos(conn)
    return cur.rowcount > 0
