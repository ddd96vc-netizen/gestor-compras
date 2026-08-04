# 🛒 SoloCompras — Gestor de Compras

Aplicación web para registrar tickets de compra, organizar productos por
categoría y analizar gastos (por tienda, por fecha y por frecuencia de
producto), con gráficos interactivos.

Construida con **Flask** y **SQLite**.

---

## De prototipo a aplicación: el refactor

Este proyecto nació como un script funcional pero frágil. Se reescribió por
completo para llevarlo a un estándar profesional. Resumen de lo que cambió:

| Antes | Después |
|-------|---------|
| Contraseña y clave de sesión **escritas en el código** | En variables de entorno (`.env`), fuera del control de versiones |
| Contraseña comparada **en texto plano** (`==`) | Hash con sal (`check_password_hash`, tiempo constante) |
| Control de intentos de login **roto y sin usar** | Rate limiting real (Flask-Limiter) |
| Formularios **sin protección CSRF** | CSRF en todos los formularios (Flask-WTF) |
| `debug=True` y `host=0.0.0.0` (debugger expuesto a la red) | Debug por configuración, `host=127.0.0.1` por defecto |
| Datos en un **JSON reescrito entero** en cada cambio (corruptible) | Base de datos **SQLite** con transacciones |
| Dinero con `float` (errores de redondeo) | Dinero en **céntimos enteros** |
| IDs `tienda_fecha` (colisionables) | **uuid** únicos para tickets y productos |
| Todo en un `app.py` de 660 líneas | **App factory + Blueprints** (auth, tickets, stats, api) |
| Lógica de negocio mezclada en las rutas | Capa de datos (`repositorio`) y de cálculo (`estadisticas`) separadas |
| Sin tests | **22 tests** con pytest |
| CSS y JS incrustados en las plantillas, XSS en el cliente | CSS/JS en sus ficheros, salida escapada de forma segura |

---

## Características

- Registro, edición y borrado de tickets con varios productos.
- Categorización de productos (con creación de categorías al vuelo).
- Búsqueda de productos y edición rápida desde un modal.
- Estadísticas: resumen general, ranking de tiendas, gasto por rango de
  fechas y análisis de frecuencia/precio por producto.
- Gráficos interactivos (Chart.js).
- Acceso protegido por contraseña.

---

## Stack

- **Backend:** Python 3, Flask
- **Base de datos:** SQLite (módulo estándar `sqlite3`)
- **Seguridad:** Flask-WTF (CSRF), Flask-Limiter, Werkzeug (hashing)
- **Frontend:** HTML + CSS + JavaScript, Chart.js
- **Tests:** pytest

---

## Estructura del proyecto

```
solocompras/
├── run.py                  # Punto de entrada (desarrollo)
├── migrar_datos.py         # Migración del antiguo JSON a SQLite
├── requirements.txt
├── pytest.ini
├── .env.example            # Plantilla de variables de entorno
├── .gitignore
├── app/
│   ├── __init__.py         # create_app() (application factory)
│   ├── config.py           # Configuración por entornos
│   ├── extensions.py       # Instancias de CSRF y Limiter
│   ├── database.py         # Conexión y esquema de SQLite
│   ├── seguridad.py        # Decoradores de login
│   ├── utilidades.py       # Helpers de dinero y fechas
│   ├── repositorio.py      # CRUD de tickets y productos
│   ├── estadisticas.py     # Cálculos estadísticos
│   ├── blueprints/         # Rutas (auth, tickets, stats, api)
│   ├── templates/          # Plantillas Jinja2
│   └── static/             # CSS y JS
└── tests/                  # Tests de pytest
```

---

## Instalación y puesta en marcha

```bash
# 1. Entorno virtual
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Dependencias
pip install -r requirements.txt

# 3. Configuración
cp .env.example .env
#    Edita .env y define:
#    - SECRET_KEY  (genérala con: python -c "import secrets; print(secrets.token_hex(32))")
#    - APP_PASSWORD

# 4. Datos
#    Opción A) Migrar desde el JSON antiguo (deja solocompras.json en la raíz):
python migrar_datos.py --reset
#    Opción B) Empezar con una base de datos vacía:
flask init-db

# 5. Arrancar
python run.py
```

La aplicación queda disponible en <http://127.0.0.1:5000>.

---

## Comandos útiles

```bash
pytest                 # Ejecutar la batería de tests
flask init-db          # Crear las tablas en una BD vacía
python run.py          # Servidor de desarrollo
```

---

## Notas de despliegue

En producción **no** se usa `run.py`. Se sirve con un servidor WSGI y se
definen las variables de entorno en el sistema (no en `.env`):

```bash
gunicorn "app:create_app()"
```

- `SECRET_KEY` es **obligatoria**: la aplicación no arranca sin ella.
- Con el entorno `production`, la cookie de sesión exige **HTTPS**
  (`SESSION_COOKIE_SECURE`), así que sírvela detrás de TLS.

---

## Decisiones de diseño

- **Dinero en céntimos:** se opera siempre con enteros y se convierte a euros
  solo al mostrar, para evitar errores de coma flotante al sumar.
- **Total calculado, no almacenado:** el total de un ticket es la suma de sus
  productos, así que nunca puede quedar desincronizado.
- **Capa de datos desacoplada de Flask:** las funciones reciben la conexión
  como parámetro, lo que permite testearlas de forma aislada.
