"""
api.py - API JSON
=================
Endpoints que consume el JavaScript (edición rápida de productos, datos
para los gráficos, etc.).

Notas de seguridad:
  - Usan login_requerido_api: si no hay sesión devuelven 401 JSON, no un
    redirect (así el fetch del navegador recibe un error claro).
  - El endpoint POST está protegido por CSRF: el JavaScript debe enviar la
    cabecera 'X-CSRFToken' (se añade en las plantillas de la Parte 4).
  - Ya no se devuelven trazas de excepción al cliente (el original hacía
    str(e), filtrando detalles internos).
"""

from flask import Blueprint, jsonify, request

from app import repositorio, estadisticas
from app.database import get_db
from app.seguridad import login_requerido_api

bp = Blueprint("api", __name__, url_prefix="/api")


@bp.route("/editar_producto", methods=["POST"])
@login_requerido_api
def editar_producto():
    data = request.get_json(silent=True) or {}

    requeridos = ["producto_id", "nombre", "precio"]
    faltan = [campo for campo in requeridos if campo not in data]
    if faltan:
        return jsonify(success=False,
                       message=f"Faltan campos: {', '.join(faltan)}"), 400

    try:
        actualizado = repositorio.editar_producto(
            get_db(),
            data["producto_id"],
            data.get("nombre"),
            data.get("precio"),
            cantidad=data.get("cantidad"),
            importe=data.get("importe"),
            categoria=data.get("categoria"),
            observacion=data.get("observacion"),
        )
    except (ValueError, TypeError):
        return jsonify(success=False, message="El precio no es válido."), 400

    if not actualizado:
        return jsonify(success=False, message="Producto no encontrado."), 404

    return jsonify(success=True, message="Producto actualizado correctamente.")


@bp.route("/tickets")
@login_requerido_api
def tickets():
    return jsonify(repositorio.listar_tickets(get_db()))


@bp.route("/tickets/<ticket_id>")
@login_requerido_api
def ticket(ticket_id):
    t = repositorio.obtener_ticket(get_db(), ticket_id)
    if t is None:
        return jsonify(error="Ticket no encontrado"), 404
    return jsonify(t)


@bp.route("/productos_categoria/<categoria>")
@login_requerido_api
def productos_categoria(categoria):
    productos = repositorio.productos_por_categoria(get_db(), categoria)
    return jsonify(success=True, categoria=categoria,
                   productos=productos, total=len(productos))


@bp.route("/estadisticas/resumen")
@login_requerido_api
def estadisticas_resumen():
    db = get_db()
    return jsonify(
        total_gastado=estadisticas.resumen_general(db),
        tiendas=estadisticas.gasto_por_tienda(db),
    )


@bp.route("/favoritos/alternar", methods=["POST"])
@login_requerido_api
def alternar_favorito():
    data = request.get_json(silent=True) or {}
    nombre = (data.get("nombre") or "").strip()
    if not nombre:
        return jsonify(success=False, message="Falta el nombre del producto."), 400
    favorito = repositorio.alternar_favorito(get_db(), nombre)
    return jsonify(success=True, favorito=favorito)
