"""
__init__.py - Application factory
=================================
create_app() construye y configura la aplicación Flask. Centralizar la
creación permite tener varias configuraciones (development / production /
testing) y facilita los tests.
"""

import os
import secrets

from dotenv import load_dotenv

# Cargar las variables de .env ANTES de leer la configuración, para que
# las clases de config (que leen os.environ) reciban los valores.
load_dotenv()

from flask import Flask, render_template, redirect, request, url_for, flash

from app.config import config_por_nombre
from app import database
from app.extensions import csrf, limiter


def create_app(nombre_config=None):
    app = Flask(__name__)

    nombre_config = nombre_config or os.environ.get("FLASK_CONFIG", "default")
    app.config.from_object(config_por_nombre.get(nombre_config, config_por_nombre["default"]))

    _configurar_clave_secreta(app)
    _configurar_password(app)
    _configurar_base_datos(app)

    # --- Extensiones ---
    csrf.init_app(app)
    limiter.init_app(app)
    database.init_app(app)

    # Crea las tablas si no existen y migra el esquema si venía de una
    # versión anterior (p. ej. bases de datos creadas antes de añadir la
    # columna 'cantidad'). Así no hace falta acordarse de `flask init-db`.
    with app.app_context():
        database.inicializar(database.get_db())

    # --- Blueprints (import diferido para evitar imports circulares) ---
    from app.blueprints.auth import bp as auth_bp
    from app.blueprints.tickets import bp as tickets_bp
    from app.blueprints.stats import bp as stats_bp
    from app.blueprints.api import bp as api_bp
    from app.blueprints.escaneo import bp as escaneo_bp
    from app.blueprints.favoritos import bp as favoritos_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(tickets_bp)
    app.register_blueprint(stats_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(escaneo_bp)
    app.register_blueprint(favoritos_bp)

    _registrar_manejadores_error(app)

    return app


# ----------------------------------------------------------------------
# Configuración auxiliar
# ----------------------------------------------------------------------

def _configurar_clave_secreta(app):
    """Garantiza que haya SECRET_KEY. En producción es obligatoria."""
    if app.config.get("SECRET_KEY"):
        return
    if app.config.get("DEBUG"):
        app.config["SECRET_KEY"] = secrets.token_hex(32)
        app.logger.warning(
            "SECRET_KEY no definida: se usa una temporal. Las sesiones se "
            "invalidarán al reiniciar. Define SECRET_KEY en .env."
        )
    else:
        raise RuntimeError(
            "SECRET_KEY no está definida. Configúrala en .env antes de "
            "arrancar en producción."
        )


def _configurar_password(app):
    """Hashea la contraseña de acceso una sola vez, al arrancar.

    La contraseña en claro solo vive en .env (fuera del control de versiones);
    en memoria se guarda únicamente su hash.
    """
    from werkzeug.security import generate_password_hash

    password = app.config.get("APP_PASSWORD") or ""
    if password:
        app.config["APP_PASSWORD_HASH"] = generate_password_hash(password)
    else:
        app.config["APP_PASSWORD_HASH"] = None
        if not app.config.get("TESTING"):
            app.logger.warning(
                "APP_PASSWORD no definida: el acceso quedará bloqueado hasta "
                "configurarla en .env."
            )


def _configurar_base_datos(app):
    """Fija la ruta de la base de datos (carpeta instance/ por defecto)."""
    os.makedirs(app.instance_path, exist_ok=True)
    ruta = os.environ.get("DATABASE_PATH") or os.path.join(app.instance_path, "solocompras.db")
    app.config["DATABASE"] = ruta


def _registrar_manejadores_error(app):
    """Páginas de error. A diferencia del código original, NO exigen login."""
    from flask_wtf.csrf import CSRFError

    @app.errorhandler(404)
    def no_encontrado(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def error_servidor(e):
        return render_template("errors/500.html"), 500

    @app.errorhandler(429)
    def demasiadas_peticiones(e):
        return render_template("errors/429.html",
                               descripcion=getattr(e, "description", "")), 429

    @app.errorhandler(413)
    def imagen_demasiado_grande(e):
        flash("La imagen es demasiado grande (máximo 10 MB).", "error")
        return redirect(request.referrer or url_for("escaneo.desde_foto"))

    @app.errorhandler(CSRFError)
    def csrf_invalido(e):
        flash("La sesión del formulario ha caducado. Vuelve a intentarlo.", "error")
        return redirect(request.referrer or url_for("tickets.index"))
