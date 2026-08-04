"""
tickets.py - Gestión de tickets
===============================
Dashboard, alta, listado, detalle, edición, borrado y búsqueda.

Las rutas son "finas": validan la entrada y delegan toda la lógica en el
repositorio y en las estadísticas. Mantienen las mismas URLs que la versión
original para no romper los enlaces de las plantillas.
"""

from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, current_app,
)

from app import repositorio, estadisticas
from app.database import get_db
from app.seguridad import login_requerido

bp = Blueprint("tickets", __name__)


def _productos_desde_form(form):
    """Reconstruye la lista de productos a partir de los arrays del formulario."""
    nombres = form.getlist("producto_nombre[]")
    cantidades = form.getlist("producto_cantidad[]")
    precios = form.getlist("producto_precio[]")
    importes = form.getlist("producto_importe[]")
    categorias = form.getlist("producto_categoria[]")
    observaciones = form.getlist("producto_observacion[]")
    favoritos = form.getlist("producto_favorito[]")

    productos = []
    for i, nombre in enumerate(nombres):
        if not nombre.strip():
            continue
        productos.append({
            "nombre": nombre,
            "cantidad": cantidades[i] if i < len(cantidades) else None,
            "precio": precios[i] if i < len(precios) else 0,
            "importe": importes[i] if i < len(importes) else None,
            "categoria": categorias[i] if i < len(categorias) else None,
            "observacion": observaciones[i] if i < len(observaciones) else None,
            "favorito": favoritos[i] if i < len(favoritos) else "0",
        })
    return productos


# ----------------------------------------------------------------------
# Dashboard
# ----------------------------------------------------------------------

@bp.route("/")
@login_requerido
def index():
    db = get_db()
    resumen = estadisticas.resumen_general(db)
    return render_template(
        "index.html",
        tickets=repositorio.listar_tickets(db, limite=5),
        total_tickets=resumen["num_tickets"],
        total_gastado=resumen["total"],
        promedio_ticket=resumen["promedio_ticket"],
    )


# ----------------------------------------------------------------------
# Alta
# ----------------------------------------------------------------------

@bp.route("/nuevo_ticket", methods=["GET", "POST"])
@login_requerido
def nuevo_ticket():
    db = get_db()
    if request.method == "GET":
        return render_template("nuevo_ticket.html",
                               categorias=repositorio.categorias_existentes(db),
                               prefill=None, texto_ocr=None)

    tienda = request.form.get("tienda", "").strip()
    fecha = request.form.get("fecha", "").strip()
    if not tienda or not fecha:
        flash("Tienda y fecha son obligatorios.", "error")
        return redirect(url_for("tickets.nuevo_ticket"))

    productos = _productos_desde_form(request.form)
    if not productos:
        flash("Debes agregar al menos un producto.", "error")
        return redirect(url_for("tickets.nuevo_ticket"))

    try:
        repositorio.crear_ticket(db, tienda, fecha, productos)
    except (ValueError, TypeError) as e:
        current_app.logger.warning("Error al crear ticket: %s", e)
        flash("Revisa los datos: la fecha o algún precio no son válidos.", "error")
        return redirect(url_for("tickets.nuevo_ticket"))

    flash("Ticket creado correctamente.", "success")
    return redirect(url_for("tickets.ver_tickets"))


# ----------------------------------------------------------------------
# Listado y detalle
# ----------------------------------------------------------------------

@bp.route("/ver_tickets")
@login_requerido
def ver_tickets():
    return render_template("ver_tickets.html",
                           tickets=repositorio.listar_tickets(get_db()))


@bp.route("/ticket/<ticket_id>")
@login_requerido
def detalle(ticket_id):
    ticket = repositorio.obtener_ticket(get_db(), ticket_id)
    if ticket is None:
        flash("Ticket no encontrado.", "error")
        return redirect(url_for("tickets.ver_tickets"))
    return render_template("ticket_detalle.html", ticket=ticket)


# ----------------------------------------------------------------------
# Edición
# ----------------------------------------------------------------------

@bp.route("/editar_ticket/<ticket_id>", methods=["GET", "POST"])
@login_requerido
def editar(ticket_id):
    db = get_db()
    ticket = repositorio.obtener_ticket(db, ticket_id)
    if ticket is None:
        flash("Ticket no encontrado.", "error")
        return redirect(url_for("tickets.ver_tickets"))

    if request.method == "GET":
        return render_template("editar_ticket.html", ticket=ticket,
                               categorias=repositorio.categorias_existentes(db))

    tienda = request.form.get("tienda", "").strip()
    fecha = request.form.get("fecha", "").strip()
    if not tienda or not fecha:
        flash("Tienda y fecha son obligatorios.", "error")
        return redirect(url_for("tickets.editar", ticket_id=ticket_id))

    productos = _productos_desde_form(request.form)
    try:
        repositorio.actualizar_ticket(db, ticket_id, tienda, fecha, productos)
    except (ValueError, TypeError) as e:
        current_app.logger.warning("Error al actualizar ticket: %s", e)
        flash("Revisa los datos: la fecha o algún precio no son válidos.", "error")
        return redirect(url_for("tickets.editar", ticket_id=ticket_id))

    flash("Ticket actualizado correctamente.", "success")
    return redirect(url_for("tickets.detalle", ticket_id=ticket_id))


# ----------------------------------------------------------------------
# Borrado
# ----------------------------------------------------------------------

@bp.route("/eliminar_ticket/<ticket_id>", methods=["POST"])
@login_requerido
def eliminar(ticket_id):
    if repositorio.eliminar_ticket(get_db(), ticket_id):
        flash("Ticket eliminado.", "success")
    else:
        flash("Ticket no encontrado.", "error")
    return redirect(url_for("tickets.ver_tickets"))


# ----------------------------------------------------------------------
# Búsqueda
# ----------------------------------------------------------------------

@bp.route("/buscar_producto", methods=["GET", "POST"])
@login_requerido
def buscar_producto():
    if request.method == "GET":
        return render_template("buscar_producto.html", resultados=None)

    termino = request.form.get("nombre_producto", "").strip()
    if not termino:
        flash("Debes ingresar un nombre para buscar.", "error")
        return render_template("buscar_producto.html", resultados=None)

    resultados = repositorio.buscar_productos(get_db(), termino)
    return render_template("buscar_producto.html", resultados=resultados, termino=termino)
