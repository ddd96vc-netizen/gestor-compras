"""
config.py - Configuración de la aplicación
==========================================
Toda la configuración sensible (clave de sesión, contraseña) se lee de
variables de entorno definidas en un fichero `.env`. NUNCA se escriben
secretos directamente en el código fuente.
"""

import os
from datetime import timedelta


class BaseConfig:
    """Configuración común a todos los entornos."""

    # Clave para firmar la cookie de sesión.
    # Sin valor por defecto a propósito: si falta en producción, la app
    # se niega a arrancar (ver create_app, Parte 3).
    SECRET_KEY = os.environ.get("SECRET_KEY")

    # Contraseña de acceso (definida en .env, jamás en el código).
    APP_PASSWORD = os.environ.get("APP_PASSWORD", "")

    # --- Sesión ---
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)
    SESSION_COOKIE_HTTPONLY = True       # la cookie no es accesible desde JavaScript
    SESSION_COOKIE_SAMESITE = "Lax"      # ayuda a mitigar CSRF en navegación cross-site

    # --- Rate limiting (Flask-Limiter) ---
    RATELIMIT_STORAGE_URI = "memory://"  # en memoria; para varios procesos usar Redis

    # --- Subida de imágenes (escaneo de tickets) ---
    MAX_CONTENT_LENGTH = 20 * 1024 * 1024  # 20 MB máximo por foto (el navegador ya la reduce antes de subirla)

    @staticmethod
    def init_app(app):
        """Hook opcional para inicialización específica de cada entorno."""
        pass


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SESSION_COOKIE_SECURE = False         # en local no hay HTTPS


class ProductionConfig(BaseConfig):
    DEBUG = False
    SESSION_COOKIE_SECURE = True          # exige servir la app por HTTPS


class TestingConfig(BaseConfig):
    TESTING = True
    DEBUG = False
    WTF_CSRF_ENABLED = False              # desactiva CSRF dentro de los tests
    APP_PASSWORD = "test-password"
    SECRET_KEY = "clave-solo-para-tests"


config_por_nombre = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
