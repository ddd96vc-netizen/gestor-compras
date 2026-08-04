"""
seguridad.py - Control de acceso
================================
Decoradores que protegen las rutas. Hay dos versiones:

  - login_requerido      -> para vistas HTML (redirige al login).
  - login_requerido_api  -> para endpoints JSON (devuelve 401, no redirige,
                            para que el JavaScript reciba un error claro).
"""

from functools import wraps

from flask import session, redirect, url_for, flash, jsonify


def login_requerido(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("logueado"):
            flash("Debes iniciar sesión para acceder a esta página.", "error")
            return redirect(url_for("auth.login"))
        return f(*args, **kwargs)
    return wrapper


def login_requerido_api(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("logueado"):
            return jsonify(success=False, error="No autenticado"), 401
        return f(*args, **kwargs)
    return wrapper
