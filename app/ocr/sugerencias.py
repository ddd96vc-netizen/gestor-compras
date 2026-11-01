"""
sugerencias.py - Completar el ticket escaneado con tu historial
===============================================================
El OCR solo sabe lo que pone el papel ("Bebida refrescante ALTEZA Bahanas").
Pero tú ya has guardado ese producto otras veces como "Bebida Bahamas", en
la categoría "Liquidos" y quizá como favorito. Este módulo busca en los
tickets ya guardados el producto más parecido y rellena con eso:

  - nombre:    el nombre que usas tú (el leído queda en `nombre_leido`).
  - categoria: la que más le has puesto a ese producto.
  - favorito:  si lo tienes marcado con el corazón.
  - tienda:    si el parser no la reconoce, se busca entre tus tiendas.

Un producto "coincide" cuando TODAS las palabras de tu nombre guardado
aparecen (aunque sea mal escritas por el OCR) en el texto leído. Si ninguno
coincide del todo, solo se sugiere la categoría del más parecido.

No depende de Flask: recibe la conexión sqlite3, así se puede testear.
"""

import re
import unicodedata
from collections import Counter
from difflib import SequenceMatcher

from app import repositorio

SIMILITUD_PALABRA = 0.8     # parecido mínimo entre dos palabras (0-1)
COBERTURA_CATEGORIA = 0.5   # parte del nombre guardado que debe aparecer para sugerir solo categoría


def _sin_acentos(texto) -> str:
    texto = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in texto if not unicodedata.combining(c)).lower()


def palabras(texto) -> list:
    """Palabras significativas (3+ letras, sin acentos, en minúscula)."""
    return [p for p in re.findall(r"[a-zñ]+", _sin_acentos(texto)) if len(p) >= 3]


def _palabras_parecidas(a, b) -> bool:
    if a == b:
        return True
    corta, larga = sorted((a, b), key=len)
    if len(corta) < 4:
        # Palabras cortas solo exactas ("parn" de pardina no es "pan"), salvo que
        # el OCR se haya comido solo la primera letra: "tun" ~ "atun".
        return len(larga) == len(corta) + 1 and larga.endswith(corta)
    if larga.startswith(corta) and len(corta) / len(larga) > 0.6:
        return True    # abreviaturas del ticket: "mermel" ~ "mermelada" (pero no "chicha" ~ "chicharrones")
    if SequenceMatcher(None, a, b).ratio() < SIMILITUD_PALABRA:
        return False
    # Parecidas Y con la misma forma: misma inicial ("poljo" ~ "pollo"), misma
    # longitud ("nenta" ~ "menta") o una letra perdida al principio ("tun" ~ "atun").
    # Evita falsos positivos como "acuerdo" ~ "cerdo".
    return a[0] == b[0] or len(a) == len(b) or a.endswith(b) or b.endswith(a)


def _cobertura(palabras_guardado, palabras_leido) -> float:
    """Parte de las palabras del nombre guardado que aparecen en el leído."""
    if not palabras_guardado:
        return 0.0
    encontradas = sum(
        1 for g in palabras_guardado
        if any(_palabras_parecidas(g, l) for l in palabras_leido)
    )
    return encontradas / len(palabras_guardado)


# ----------------------------------------------------------------------
# Historial
# ----------------------------------------------------------------------

def cargar_historial(conn) -> list:
    """Un registro por producto distinto: nombre, categoría habitual, tiendas, veces."""
    agrupado = {}
    filas = conn.execute(
        """SELECT p.nombre, p.categoria, t.tienda
           FROM productos p JOIN tickets t ON t.id = p.ticket_id
           ORDER BY t.fecha"""          # el último nombre visto es el que se muestra
    )
    for f in filas:
        clave = repositorio._norm(f["nombre"])
        info = agrupado.setdefault(clave, {
            "nombre": f["nombre"], "categorias": Counter(), "tiendas": set(), "veces": 0,
        })
        info["nombre"] = f["nombre"]
        info["veces"] += 1
        info["tiendas"].add(_sin_acentos(f["tienda"]))
        if f["categoria"]:
            info["categorias"][f["categoria"]] += 1

    historial = []
    for clave, info in agrupado.items():
        pals = palabras(info["nombre"])
        if not pals:
            continue
        historial.append({
            "clave": clave,
            "nombre": info["nombre"],
            "palabras": pals,
            "categoria": info["categorias"].most_common(1)[0][0] if info["categorias"] else None,
            "tiendas": info["tiendas"],
            "veces": info["veces"],
        })
    return historial


def buscar_parecido(nombre_leido, historial, tienda=""):
    """Devuelve (registro del historial, cobertura) del más parecido, o (None, 0)."""
    leido = palabras(nombre_leido)
    if not leido:
        return None, 0.0
    # El OCR a veces parte una palabra en dos ("SAL CHICHA"): se prueban
    # también las parejas de palabras seguidas unidas ("salchicha").
    sueltas = re.findall(r"[a-zñ]+", _sin_acentos(nombre_leido))
    leido += [a + b for a, b in zip(sueltas, sueltas[1:]) if len(a + b) >= 5]
    tienda = _sin_acentos(tienda)

    mejor, mejor_clave = None, None
    for h in historial:
        cob = _cobertura(h["palabras"], leido)
        if cob == 0:
            continue
        # Orden de preferencia: más cobertura, más palabras coincidentes
        # (nombre más concreto), comprado en esta tienda, más veces comprado.
        clave = (cob, len(h["palabras"]), tienda in h["tiendas"], h["veces"])
        if mejor_clave is None or clave > mejor_clave:
            mejor, mejor_clave = h, clave
    return (mejor, mejor_clave[0]) if mejor else (None, 0.0)


# ----------------------------------------------------------------------
# Punto de entrada
# ----------------------------------------------------------------------

def completar(conn, datos: dict, texto_ocr: str = "") -> dict:
    """Completa en el sitio el resultado de parsear_ticket() con el historial."""
    historial = cargar_historial(conn)
    favoritos = repositorio.nombres_favoritos(conn)

    if datos.get("parser") == "ParserGenerico":
        tienda = tienda_conocida(conn, texto_ocr)
        if tienda:
            datos["tienda"] = tienda

    for p in datos.get("productos", []):
        p["nombre_leido"] = p["nombre"]
        p.setdefault("categoria", None)
        parecido, cobertura = buscar_parecido(p["nombre"], historial, datos.get("tienda", ""))
        if parecido and cobertura == 1.0:
            p["nombre"] = parecido["nombre"]
            p["categoria"] = parecido["categoria"]
        elif parecido and cobertura >= COBERTURA_CATEGORIA:
            p["categoria"] = parecido["categoria"]
        p["favorito"] = repositorio._norm(p["nombre"]) in favoritos
    return datos


def tienda_conocida(conn, texto_ocr: str):
    """Busca en la cabecera del ticket alguna de las tiendas que ya tienes guardadas."""
    cabecera = palabras(" ".join(texto_ocr.splitlines()[:8]))
    if not cabecera:
        return None
    mejor, mejor_clave = None, None
    for (tienda,) in conn.execute("SELECT DISTINCT tienda FROM tickets"):
        pals = palabras(tienda)
        if pals and _cobertura(pals, cabecera) == 1.0:
            clave = (len(pals), len(tienda))
            if mejor_clave is None or clave > mejor_clave:
                mejor, mejor_clave = tienda, clave
    return mejor
