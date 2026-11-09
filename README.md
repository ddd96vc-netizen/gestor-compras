# 🛒 SoloCompras — Gestor de Compras

Aplicación web para registrar tickets de compra **haciéndoles una foto con el
móvil**, organizar productos por categoría, marcar favoritos y analizar gastos
(por tienda, por fecha y por frecuencia de producto) con gráficos interactivos.

Construida con **Flask**, **SQLite** y **EasyOCR**.

---

## Características

- **Escaneo de tickets por foto (OCR):** subes la foto y la app rellena el
  formulario con la tienda, la fecha, la hora, los productos, las cantidades
  y los precios. Tú solo revisas y guardas: nunca se guarda nada sin tu
  confirmación.
- **Aprende de tu historial:** si el ticket dice "Bebida refrescante ALTEZA
  Bahamas" y tú ese producto lo guardas como "Bebida Bahamas" en la categoría
  "Líquidos", la próxima vez lo propone así (nombre, categoría y favorito).
- **Favoritos:** marca productos con el corazón y consulta su ficha: cuándo,
  dónde y a qué precio lo compraste, y dónde salió más barato.
- Registro, edición y borrado de tickets con varios productos.
- Categorías (con creación al vuelo), búsqueda de productos y edición rápida
  desde un modal.
- Estadísticas: resumen general, ranking de tiendas, gasto por rango de
  fechas y análisis de frecuencia y precio por producto (Chart.js).
- Acceso protegido por contraseña. Se puede usar desde el móvil en la misma
  wifi para hacer las fotos directamente.

---

## Escaneo por foto: cómo funciona

```
foto ──► EasyOCR ──► reconstrucción de filas ──► parser de la tienda ──► historial ──► formulario
         (cajas)     (enderezar + agrupar)       (reglas propias)       (sugerencias)   (revisar y guardar)
```

1. **OCR** (`app/ocr/lector.py`): EasyOCR devuelve cada bloque de texto con
   su posición. En un ticket el nombre y el precio de un producto salen como
   bloques separados, así que se **reconstruyen las filas**:
   - se corrige la **inclinación** de las fotos torcidas antes de agrupar;
   - cada fila se ancla en la columna izquierda (el nombre) y se le juntan
     los bloques de su misma altura, de izquierda a derecha.
2. **Parser por tienda** (`app/ocr/parsers/`): se detecta la tienda por
   palabras clave (tolerando letras mal leídas) y se aplican sus reglas.

   | Tienda | Particularidades |
   |--------|------------------|
   | Mercadona | Formato de tabla estándar |
   | Dia | Formato propio |
   | Deza / Zoco | Precios con apóstrofo (`1'24`, `0' 224`) y productos al peso |
   | El Jamón | Cualquier tienda de la cadena (por el pie o el teléfono); la de Pintor Espinosa tiene reglas propias |
   | Frutas y Verduras Elena | El ticket no trae nombres: cada línea va como "Fruta/verdura" con los kilos en la observación |
   | Genérico | Cualquier otra tienda |

   Reglas comunes (`base.py`): fechas numéricas y con el mes en letras
   (`01 NOV 26`), con preferencia por el año de 4 cifras; hora; precios con
   coma, punto, apóstrofo o asterisco; precios partidos por el OCR (`1 89`);
   cantidades y pesos. Si una lectura es ambigua, se elige la combinación que
   **cuadra con el total impreso** del ticket.
3. **Sugerencias** (`app/ocr/sugerencias.py`): busca en los tickets ya
   guardados el producto más parecido y completa el nombre, la categoría, el
   favorito y, si hace falta, la tienda.

El texto OCR crudo de cada foto se guarda en `instance/ocr_muestras/` para
depurar y convertir en test los tickets que se lean mal.

### Añadir una tienda nueva

1. Crea `app/ocr/parsers/mi_tienda.py` con una subclase de `ParserTicket` y
   sobreescribe solo lo que cambie.
2. Regístrala en `PARSERS_ESPECIFICOS` (`app/ocr/parsers/registro.py`).
3. Guarda la salida cruda de EasyOCR de una foto real en `tests/datos_ocr/`
   y añade una línea a `CASOS` en `tests/test_fotos_reales.py` con la tienda,
   la fecha, el total y el número de productos esperados.

---

## De prototipo a aplicación: el refactor

Este proyecto nació como un script funcional pero frágil. Se reescribió por
completo para llevarlo a un estándar profesional:

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
| Todo en un `app.py` de 660 líneas | **App factory + Blueprints** (auth, tickets, escaneo, favoritos, stats, api) |
| Lógica de negocio mezclada en las rutas | Capa de datos (`repositorio`) y de cálculo (`estadisticas`) separadas |
| Sin tests | **57 tests** con pytest, incluidos tickets reales completos |
| CSS y JS incrustados en las plantillas, XSS en el cliente | CSS/JS en sus ficheros, salida escapada de forma segura |

---

## Stack

- **Backend:** Python 3.11, Flask
- **Base de datos:** SQLite (módulo estándar `sqlite3`)
- **OCR:** EasyOCR (PyTorch) + Pillow, opcional
- **Seguridad:** Flask-WTF (CSRF), Flask-Limiter, Werkzeug (hashing)
- **Frontend:** HTML + CSS + JavaScript, Chart.js
- **Tests:** pytest

---

## Estructura del proyecto

```
gestor-compras/
├── run.py                  # Punto de entrada (desarrollo)
├── migrar_datos.py         # Migración del antiguo JSON a SQLite
├── requirements.txt        # Dependencias base
├── requirements-ocr.txt    # Dependencias del escaneo por foto (pesadas)
├── pytest.ini
├── .env.example            # Plantilla de variables de entorno
├── app/
│   ├── __init__.py         # create_app() (application factory)
│   ├── config.py           # Configuración por entornos
│   ├── extensions.py       # Instancias de CSRF y Limiter
│   ├── database.py         # Conexión y esquema de SQLite
│   ├── seguridad.py        # Decoradores de login
│   ├── utilidades.py       # Helpers de dinero y fechas
│   ├── repositorio.py      # CRUD de tickets, productos y favoritos
│   ├── estadisticas.py     # Cálculos estadísticos
│   ├── blueprints/         # Rutas: auth, tickets, escaneo, favoritos, stats, api
│   ├── ocr/
│   │   ├── lector.py       # EasyOCR + reconstrucción de filas
│   │   ├── sugerencias.py  # Completar con el historial
│   │   └── parsers/        # Un parser por tienda + base y genérico
│   ├── templates/          # Plantillas Jinja2
│   └── static/             # CSS y JS
└── tests/
    ├── datos_ocr/          # Salida cruda de EasyOCR de tickets reales
    └── test_*.py
```

---

## Instalación y puesta en marcha

```bash
# 1. Entorno virtual (Python 3.11)
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Dependencias
pip install -r requirements.txt
pip install -r requirements-ocr.txt   # solo si vas a escanear fotos (tarda: trae PyTorch)

# 3. Configuración
cp .env.example .env            # Windows: copy .env.example .env
#    Edita .env y define:
#    - SECRET_KEY  (genérala con: python -c "import secrets; print(secrets.token_hex(32))")
#    - APP_PASSWORD
#    - HOST=0.0.0.0 si quieres abrirla desde el móvil en tu wifi

# 4. Datos
#    Opción A) Migrar desde el JSON antiguo (deja solocompras.json en la raíz):
python migrar_datos.py --reset
#    Opción B) Empezar con una base de datos vacía:
flask init-db

# 5. Arrancar
python run.py
```

La aplicación queda en <http://127.0.0.1:5000>. Con `HOST=0.0.0.0`, desde el
móvil se abre en `http://IP-DEL-PC:5000`.

La primera vez que escanees un ticket, EasyOCR descarga su modelo de español
(unos 64 MB). Sin las dependencias de OCR la app funciona igual; solo el
escaneo muestra un aviso con cómo instalarlas.

---

## Comandos útiles

```bash
pytest                 # Ejecutar los tests (no necesitan EasyOCR)
flask init-db          # Crear las tablas en una BD vacía
python run.py          # Servidor de desarrollo
```

---

## Notas de despliegue

En producción **no** se usa `run.py`. Se sirve con un servidor WSGI y las
variables de entorno se definen en el sistema (no en `.env`):

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
- **OCR opcional y perezoso:** EasyOCR solo se importa al escanear, así la app
  arranca rápido y no exige instalar PyTorch para usarla.
- **El OCR propone, el usuario decide:** el ticket escaneado llega como
  formulario rellenado; se guarda por la misma ruta que un ticket manual.
- **Tests con tickets reales sin fotos:** se guarda la salida cruda del OCR
  (cajas y texto), así el camino completo se prueba en milisegundos y sin
  subir imágenes al repositorio. Los datos personales de los tickets (nombre
  del cajero, número de tarjeta) se anonimizan antes de añadirlos.
