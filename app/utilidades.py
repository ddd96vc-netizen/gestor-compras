"""
utilidades.py - Funciones auxiliares compartidas
================================================
Conversión de dinero (euros <-> céntimos) y normalización de fechas.
Centralizadas aquí para no repetir lógica en el repositorio, las
estadísticas y las rutas.
"""

from datetime import datetime


# ----------------------------------------------------------------------
# Dinero
# ----------------------------------------------------------------------

def a_centimos(euros) -> int:
    """Convierte un precio en euros a céntimos (entero).

    Lanza ValueError/TypeError si el valor no es numérico, para que la
    capa que llama pueda mostrar un error de validación.
    """
    return int(round(float(euros) * 100))


def a_euros(centimos) -> float:
    """Convierte céntimos (entero) a euros, redondeado a 2 decimales."""
    return round((centimos or 0) / 100, 2)


def a_cantidad(valor) -> int:
    """Convierte el campo de cantidad a un entero >= 1.

    Si el campo viene vacío, None, o no es un número válido, se asume que
    se compró 1 unidad (es el valor por defecto que se le muestra al usuario).
    """
    if valor is None or str(valor).strip() == "":
        return 1
    try:
        cantidad = int(float(valor))
    except (TypeError, ValueError):
        return 1
    return cantidad if cantidad >= 1 else 1


# ----------------------------------------------------------------------
# Texto
# ----------------------------------------------------------------------

def limpiar(texto):
    """Recorta espacios y devuelve None si la cadena queda vacía."""
    if texto is None:
        return None
    texto = str(texto).strip()
    return texto or None


# ----------------------------------------------------------------------
# Fechas
# ----------------------------------------------------------------------

# Formatos aceptados al recibir una fecha (el <input datetime-local>
# envía 'YYYY-MM-DDTHH:MM'). Todos se normalizan a 'YYYY-MM-DD HH:MM:SS'.
_FORMATOS_ENTRADA = (
    "%Y-%m-%dT%H:%M",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%Y-%m-%d",
)


def normalizar_fecha(valor: str) -> str:
    """Normaliza cualquier fecha de entrada a ISO 'YYYY-MM-DD HH:MM:SS'.

    Lanza ValueError si el formato no se reconoce.
    """
    valor = (valor or "").strip()
    for formato in _FORMATOS_ENTRADA:
        try:
            return datetime.strptime(valor, formato).strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
    raise ValueError(f"Formato de fecha no reconocido: {valor!r}")


def partes_fecha(fecha_iso: str):
    """Descompone una fecha ISO en (día, valor_para_input).

    - día:               'YYYY-MM-DD'           (para mostrar en tablas)
    - valor_para_input:  'YYYY-MM-DDTHH:MM'     (para <input datetime-local>)
    """
    dia = fecha_iso[:10]
    hora_min = fecha_iso[11:16] if len(fecha_iso) >= 16 else "00:00"
    return dia, f"{dia}T{hora_min}"
