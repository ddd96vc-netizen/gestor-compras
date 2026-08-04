"""
favoritos.py - Productos favoritos
==================================
  - GET /favoritos          -> listado de productos marcados con el corazón.
  - GET /favoritos/<nombre>  -> ficha con el historial completo del producto
                                (cuándo, dónde y a qué precio se compró).

El marcado/desmarcado (el corazón) se hace vía la API en api.py, para que
funcione con un clic desde cualquier página sin recargar.
"""

from flask import Blueprint, render_template, redirect, url_for, flash

from app import repositorio, estadisticas
from app.database import get_db
from app.seguridad import login_requerido

bp = Blueprint("favoritos", __name__)


@bp.route("/favoritos")
@login_requerido
def listado():
    return render_template("favoritos.html",
                           favoritos=repositorio.listar_favoritos(get_db()))


@bp.route("/favoritos/<nombre>")
@login_requerido
def detalle(nombre):
    db = get_db()
    if not repositorio.es_favorito(db, nombre):
        flash("Ese producto ya no está en tus favoritos.", "warning")
        return redirect(url_for("favoritos.listado"))

    # Reutiliza el análisis de frecuencia: historial, precios y dónde más barato.
    datos = estadisticas.frecuencia_producto(db, nombre)
    return render_template("favorito_detalle.html", nombre=nombre, datos=datos)
