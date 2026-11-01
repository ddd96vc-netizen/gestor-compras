"""
run.py - Punto de entrada para desarrollo
=========================================
Arranca el servidor de desarrollo de Flask:

    python run.py

En PRODUCCIÓN no se usa este fichero; se sirve con un servidor WSGI:

    gunicorn "app:create_app()"
"""

import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    # HOST=127.0.0.1 (por defecto) = accesible solo desde tu equipo.
    # HOST=0.0.0.0 en el .env = accesible desde el móvil en tu misma wifi
    # (http://IP-DEL-PC:5000), para hacer las fotos de los tickets con él.
    # El modo debug lo decide la configuración (.env).
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", 5000)))
