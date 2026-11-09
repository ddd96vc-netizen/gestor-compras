"""
tiendas.py - Un solo nombre por tienda
======================================
La misma tienda acababa guardada con muchos nombres ("El Jamon (Pintor)",
"Proxy (El Jamon)", "Jamon"...), y eso partía las estadísticas. Aquí se
decide el nombre "oficial" de cada tienda. Se aplica:

  - al guardar o editar un ticket (repositorio.crear_ticket / actualizar_ticket);
  - a los tickets ya guardados, con el comando:  flask normalizar-tiendas

Reglas (en orden, la primera que encaja gana):
  1. Chino de artículos/utilidades -> "Chino Articul"   (Granvía Parque, "Cosas")
  2. Chino + Proxi/Proxy           -> "Chino Verduras Fiel"
  3. Cualquier otro chino          -> se deja tal cual  ("Chino Zoco")
  4. Todo lo que diga Jamón, o la dirección de Pintor Espinosa -> "El Jamon"
  5. Proxi / Proxy                 -> "Proxi"
  6. Dia / DIA / Grupo Dia         -> "Dia"
  7. Coviran / Coviran Lin         -> "Coviran Lin"   (es la misma tienda)

Para añadir una tienda nueva, añade una regla a REGLAS.
"""

import re
import unicodedata


def _clave(nombre: str) -> str:
    """Minúsculas, sin acentos y con los espacios colapsados."""
    texto = unicodedata.normalize("NFKD", nombre or "")
    texto = "".join(c for c in texto if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+", " ", texto).strip()


def _es_chino(n): return "chino" in n
def _menciona_proxi(n): return re.search(r"\bprox[iy]\b", n) is not None


# (condición sobre el nombre normalizado, nombre oficial o None = dejar tal cual)
REGLAS = [
    (lambda n: _es_chino(n) and ("cosas" in n or "granvia" in n or "articul" in n), "Chino Articul"),
    (lambda n: _es_chino(n) and _menciona_proxi(n), "Chino Verduras Fiel"),
    (lambda n: _es_chino(n), None),
    (lambda n: "jamon" in n or "pintor espinosa" in n, "El Jamon"),
    (lambda n: n in ("proxi", "proxy"), "Proxi"),
    (lambda n: n in ("dia", "grupo dia"), "Dia"),
    (lambda n: n.startswith("coviran"), "Coviran Lin"),
]


def tienda_canonica(nombre: str) -> str:
    """Nombre oficial de la tienda (o el mismo, limpio, si ninguna regla encaja)."""
    limpio = re.sub(r"\s+", " ", (nombre or "")).strip()
    n = _clave(limpio)
    for condicion, oficial in REGLAS:
        if condicion(n):
            return oficial or limpio
    return limpio


def normalizar_tiendas(conn) -> list:
    """Aplica tienda_canonica a todos los tickets guardados.

    Devuelve la lista de cambios [(nombre_antes, nombre_despues, nº tickets)].
    """
    cambios = []
    filas = conn.execute("SELECT tienda, COUNT(*) AS n FROM tickets GROUP BY tienda").fetchall()
    with conn:
        for f in filas:
            nuevo = tienda_canonica(f["tienda"])
            if nuevo != f["tienda"]:
                conn.execute("UPDATE tickets SET tienda = ? WHERE tienda = ?", (nuevo, f["tienda"]))
                cambios.append((f["tienda"], nuevo, f["n"]))
    return cambios
