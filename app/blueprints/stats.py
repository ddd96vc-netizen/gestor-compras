"""
stats.py - Estadísticas
=======================
Dashboard de estadísticas, análisis por tienda, por rango de fechas, por
frecuencia de producto y por categorías.
"""

from flask import Blueprint, render_template, request, flash

from app import estadisticas
from app.database import get_db
from app.seguridad import login_requerido

bp = Blueprint("stats", __name__)


@bp.route("/estadisticas")
@login_requerido
def dashboard():
    db = get_db()
    return render_template(
        "estadisticas.html",
        datos_generales=estadisticas.resumen_general(db),
        datos_tiendas=estadisticas.gasto_por_tienda(db),
    )


@bp.route("/estadisticas/tiendas")
@login_requerido
def tiendas():
    return render_template("estadisticas_tiendas.html",
                           datos=estadisticas.gasto_por_tienda(get_db()))


@bp.route("/estadisticas/fechas", methods=["GET", "POST"])
@login_requerido
def fechas():
    if request.method == "GET":
        return render_template("estadisticas_fechas.html", datos=None)

    fecha_inicio = request.form.get("fecha_inicio", "").strip()
    fecha_fin = request.form.get("fecha_fin", "").strip()
    if not fecha_inicio or not fecha_fin:
        flash("Debes especificar ambas fechas.", "error")
        return render_template("estadisticas_fechas.html", datos=None)

    datos = estadisticas.gastos_por_rango(get_db(), fecha_inicio, fecha_fin)
    if datos.get("error"):
        flash("El formato de fecha no es válido.", "error")
        return render_template("estadisticas_fechas.html", datos=None)

    return render_template("estadisticas_fechas.html", datos=datos)


@bp.route("/estadisticas/frecuencia", methods=["GET", "POST"])
@login_requerido
def frecuencia():
    if request.method == "GET":
        return render_template("estadisticas_frecuencia.html", datos=None)

    nombre = request.form.get("nombre_producto", "").strip()
    if not nombre:
        flash("Debes ingresar un nombre de producto.", "error")
        return render_template("estadisticas_frecuencia.html", datos=None)

    datos = estadisticas.frecuencia_producto(get_db(), nombre)
    if not datos["compras"]:
        flash(f'No se encontraron compras de "{nombre}".', "warning")

    return render_template("estadisticas_frecuencia.html", datos=datos)


@bp.route("/categorias")
@login_requerido
def categorias():
    return render_template("categorias.html",
                           stats=estadisticas.stats_categorias(get_db()))
