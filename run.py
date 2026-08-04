"""
run.py - Punto de entrada para desarrollo
=========================================
Arranca el servidor de desarrollo de Flask:

    python run.py

En PRODUCCIÓN no se usa este fichero; se sirve con un servidor WSGI:

    gunicorn "app:create_app()"
"""

from app import create_app

app = create_app()

if __name__ == "__main__":
    # host 127.0.0.1 = accesible solo desde tu equipo (seguro por defecto).
    # Para alcanzarlo desde otros dispositivos de tu red usa host="0.0.0.0"
    # de forma consciente. El modo debug lo decide la configuración (.env).
    app.run(host="127.0.0.1", port=5000)
