"""
auth.py - Autenticación
=======================
Login y logout. Mejoras frente al original:
  - La contraseña se compara con check_password_hash (hash con sal,
    tiempo constante), nunca en texto plano con ==.
  - Rate limiting REAL en el login (8 intentos por minuto y por IP),
    en lugar del control de intentos roto que nunca se llamaba.
  - session.clear() antes de iniciar sesión, para evitar fijación de sesión.
"""

from flask import (
    Blueprint, render_template, request, redirect, url_for, flash,
    session, current_app,
)
from werkzeug.security import check_password_hash

from app.extensions import limiter

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("8 per minute", methods=["POST"])
def login():
    if session.get("logueado"):
        return redirect(url_for("tickets.index"))

    if request.method == "POST":
        password = request.form.get("password", "")
        hash_guardado = current_app.config.get("APP_PASSWORD_HASH")

        if hash_guardado and check_password_hash(hash_guardado, password):
            session.clear()
            session["logueado"] = True
            session.permanent = True
            flash("Bienvenido al Gestor de Compras.", "success")
            return redirect(url_for("tickets.index"))

        flash("Contraseña incorrecta. Inténtalo de nuevo.", "error")
        return redirect(url_for("auth.login"))

    return render_template("login.html")


@bp.route("/logout")
def logout():
    session.clear()
    flash("Has cerrado sesión correctamente.", "success")
    return redirect(url_for("auth.login"))
