"""
extensions.py - Instancias de las extensiones de Flask
======================================================
Se crean aquí (sin app) y se inicializan en create_app con init_app().
Este patrón evita imports circulares: los blueprints pueden importar
`limiter` o `csrf` sin importar la factoría de la aplicación.
"""

from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Protección CSRF para todos los formularios POST/PUT/PATCH/DELETE.
csrf = CSRFProtect()

# Límite de peticiones por IP (configurado en create_app vía init_app).
limiter = Limiter(key_func=get_remote_address)
