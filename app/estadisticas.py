"""
estadisticas.py - Cálculos estadísticos sobre las compras
=========================================================
Todo el dinero se opera en céntimos (enteros) y se convierte a euros solo
al final, para que las sumas no acumulen errores de coma flotante.

Como en el repositorio, cada función recibe la conexión `conn`.
"""

import calendar
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import date, datetime
from statistics import median

from app.utilidades import a_euros, partes_fecha


def _totales_por_ticket(conn):
    """Filas (id, tienda, fecha, total_cents) con el total de cada ticket."""
    return conn.execute(
        """SELECT t.id, t.tienda, t.fecha,
                  COALESCE(SUM(p.importe_centimos), 0) AS total_cents
           FROM tickets t
           LEFT JOIN productos p ON p.ticket_id = t.id
           GROUP BY t.id"""
    ).fetchall()


def resumen_general(conn) -> dict:
    """Totales generales: gasto, nº de tickets/productos, promedios y extremos."""
    filas = _totales_por_ticket(conn)
    num_tickets = len(filas)
    num_productos = conn.execute("SELECT COUNT(*) FROM productos").fetchone()[0]

    if num_tickets == 0:
        return {
            "total": 0.0, "num_tickets": 0, "num_productos": 0,
            "promedio_ticket": 0.0, "promedio_producto": 0.0,
            "ticket_mas_caro": None, "ticket_mas_barato": None,
        }

    total_cents = sum(f["total_cents"] for f in filas)
    mas_caro = max(filas, key=lambda f: f["total_cents"])
    mas_barato = min(filas, key=lambda f: f["total_cents"])

    def _resumen(f):
        dia, _ = partes_fecha(f["fecha"])
        return {"tienda": f["tienda"], "fecha_dia": dia, "total": a_euros(f["total_cents"])}

    return {
        "total": a_euros(total_cents),
        "num_tickets": num_tickets,
        "num_productos": num_productos,
        "promedio_ticket": round(total_cents / num_tickets / 100, 2),
        "promedio_producto": round(total_cents / num_productos / 100, 2) if num_productos else 0.0,
        "ticket_mas_caro": _resumen(mas_caro),
        "ticket_mas_barato": _resumen(mas_barato),
    }


def gasto_por_tienda(conn) -> dict:
    """Gasto agrupado por tienda, ordenado de mayor a menor, con porcentajes."""
    filas = conn.execute(
        """SELECT t.tienda, COALESCE(SUM(p.importe_centimos), 0) AS total_cents
           FROM tickets t
           LEFT JOIN productos p ON p.ticket_id = t.id
           GROUP BY t.tienda
           ORDER BY total_cents DESC"""
    ).fetchall()

    total_general = sum(f["total_cents"] for f in filas)
    tiendas = []
    for f in filas:
        pct = (f["total_cents"] / total_general * 100) if total_general else 0
        tiendas.append({
            "nombre": f["tienda"],
            "total": a_euros(f["total_cents"]),
            "porcentaje": round(pct, 1),
        })

    return {
        "tiendas": tiendas,
        "tienda_top": tiendas[0] if tiendas else None,
        "total_general": a_euros(total_general),
    }


def gastos_por_rango(conn, fecha_inicio, fecha_fin) -> dict:
    """Gasto en un rango de fechas (ambas en formato 'YYYY-MM-DD', inclusive)."""
    try:
        datetime.strptime(fecha_inicio, "%Y-%m-%d")
        datetime.strptime(fecha_fin, "%Y-%m-%d")
    except (TypeError, ValueError):
        return {
            "error": "Formato de fecha inválido",
            "fecha_inicio": fecha_inicio, "fecha_fin": fecha_fin,
            "tickets": [], "total": 0.0, "num_tickets": 0, "promedio": 0.0,
        }

    filas = conn.execute(
        """SELECT t.id, t.tienda, t.fecha,
                  COALESCE(SUM(p.importe_centimos), 0) AS total_cents,
                  COUNT(p.id) AS num_productos
           FROM tickets t
           LEFT JOIN productos p ON p.ticket_id = t.id
           WHERE date(t.fecha) BETWEEN ? AND ?
           GROUP BY t.id
           ORDER BY t.fecha""",
        (fecha_inicio, fecha_fin),
    ).fetchall()

    tickets = []
    total_cents = 0
    for f in filas:
        dia, _ = partes_fecha(f["fecha"])
        tickets.append({
            "id": f["id"],
            "tienda": f["tienda"],
            "fecha_dia": dia,
            "total": a_euros(f["total_cents"]),
            "num_productos": f["num_productos"],
        })
        total_cents += f["total_cents"]

    n = len(tickets)
    return {
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "tickets": tickets,
        "total": a_euros(total_cents),
        "num_tickets": n,
        "promedio": round(total_cents / n / 100, 2) if n else 0.0,
    }


def frecuencia_producto(conn, nombre) -> dict:
    """Analiza con qué frecuencia y a qué precio se compra un producto."""
    nombre = (nombre or "").strip()
    vacio = {
        "nombre_busqueda": nombre, "compras": [], "frecuencia": 0,
        "precio_promedio": 0.0, "precio_minimo": 0.0, "precio_maximo": 0.0,
        "diferencia": 0.0, "tiendas_distintas": [], "tienda_mas_barata": None,
        "promedios_tiendas": {},
    }
    if not nombre:
        return vacio

    patron = f"%{nombre.lower()}%"
    filas = conn.execute(
        """SELECT p.nombre, p.cantidad, p.precio_centimos, p.categoria, p.observacion,
                  t.tienda, t.fecha
           FROM productos p
           JOIN tickets t ON t.id = p.ticket_id
           WHERE lower(p.nombre) LIKE ?
           ORDER BY t.fecha DESC""",
        (patron,),
    ).fetchall()

    if not filas:
        return vacio

    compras = []
    precios = []                     # céntimos (precio UNITARIO, no el importe)
    por_tienda = {}                  # tienda -> [céntimos]
    for f in filas:
        dia, _ = partes_fecha(f["fecha"])
        compras.append({
            "fecha_dia": dia,
            "tienda": f["tienda"],
            "cantidad": f["cantidad"],
            "precio": a_euros(f["precio_centimos"]),
            "nombre_completo": f["nombre"],
            "categoria": f["categoria"] or "Sin categoría",
            "observacion": f["observacion"] or "",
        })
        precios.append(f["precio_centimos"])
        por_tienda.setdefault(f["tienda"], []).append(f["precio_centimos"])

    promedios_tiendas = {
        tienda: a_euros(round(sum(cs) / len(cs)))
        for tienda, cs in por_tienda.items()
    }
    tienda_barata = min(por_tienda.items(), key=lambda kv: sum(kv[1]) / len(kv[1]))

    return {
        "nombre_busqueda": nombre,
        "compras": compras,
        "frecuencia": len(compras),
        "precio_promedio": round(sum(precios) / len(precios) / 100, 2),
        "precio_minimo": a_euros(min(precios)),
        "precio_maximo": a_euros(max(precios)),
        "diferencia": a_euros(max(precios) - min(precios)),
        "tiendas_distintas": sorted(por_tienda.keys()),
        "tienda_mas_barata": {
            "nombre": tienda_barata[0],
            "promedio": a_euros(round(sum(tienda_barata[1]) / len(tienda_barata[1]))),
        },
        "promedios_tiendas": promedios_tiendas,
    }


def stats_categorias(conn) -> dict:
    """Resumen por categoría: {categoria: {cantidad, total}}.

    Los productos sin categoría se agrupan bajo 'Sin categoría'.
    """
    filas = conn.execute(
        """SELECT COALESCE(NULLIF(TRIM(categoria), ''), 'Sin categoría') AS cat,
                  COUNT(*) AS cantidad,
                  COALESCE(SUM(importe_centimos), 0) AS total_cents
           FROM productos
           GROUP BY cat
           ORDER BY total_cents DESC"""
    ).fetchall()

    return {
        f["cat"]: {"cantidad": f["cantidad"], "total": a_euros(f["total_cents"])}
        for f in filas
    }


# ----------------------------------------------------------------------
# Productos: lo que más compras y dónde sale más barato
# ----------------------------------------------------------------------
# El mismo producto se agrupa por su nombre normalizado (sin mayúsculas,
# acentos ni signos). Las tiendas ya llegan unificadas (app/tiendas.py).

# Entradas que no son un producto (tickets apuntados de golpe): no cuentan
# para comparar precios ni para los rankings de productos.
GENERICOS = {
    "todo", "compra entera", "compra grande", "varios articulos", "no me acuerdo",
    "cervezas y patatas", "fruta verdura", "frutas", "varios",
}
# Se comparan de precio, pero no aportan nada al ranking de "lo que más compras".
FUERA_DEL_RANKING = {"bolsa", "bolsas", "bolsa reciclada"}
# Si una tienda cobra 2,5 veces más que otra, seguramente es otro tamaño de paquete.
RATIO_SOSPECHOSO = 2.5


# Nombres que son SEGURO el mismo producto (erratas, singular/plural, con o sin
# "de"). Solo afecta a las estadísticas: los tickets guardados no se tocan.
# Ante la duda, NO se une (p. ej. "leche" y "leche covap" son marcas distintas).
MISMO_PRODUCTO = {
    "cerveza cruzcampo": "cruzcampo",
    "higad de pollo": "higado de pollo",
    "higado pollo": "higado de pollo",
    "chuleta cabezada": "chuletas cabezada",
    "chuleta de cerdo": "chuletas de cerdo",
    "chuletas cerdo": "chuletas de cerdo",
    "filete de cerdo": "filetes de cerdo",
    "lomo cerdo": "lomo de cerdo",
    "lomo de credo marinado": "lomo de cerdo marinado",
    "muslos pollo": "muslos de pollo",
    "jamoncitos pollo": "jamoncitos de pollo",
    "panceta chicharones": "panceta chicharrones",
    "torreznos chicharron": "torreznos chicharrones",
    "chicharron": "chicharrones",
    "salchicha": "salchichas",
    "lenteja": "lentejas",
    "lenteja cocida": "lentejas cocidas",
    "lenteja cocidas": "lentejas cocidas",
    "garbanzo": "garbanzos",
    "cebolla": "cebollas",
    "manzana": "manzanas",
    "naranja": "naranjas",
    "platano": "platanos",
    "ajos": "ajo",
    "mayones": "mayonesa",
    "caldo chino": "caldos chinos",
    "arros rueda": "arroz rueda",
    "spaguetti": "spaghetti",
    "spaguetis": "spaghetti",
    "pure tomate": "pure de tomate",
    "tortillas de patatas": "tortilla de patatas",
    "yogur": "yogurt",
    "yogur griego": "yogurt griego",
    "yogur liquido": "yogurt liquido",
    "leche covao": "leche covap",
    "pan hotdog": "pan hot dogs",
    "batidochocolate": "batido de chocolate",
    "refresco bahama": "refresco bahamas",
    "nectar bahamas": "bahamas nectar",
    "pasta de diente": "pasta dientes",
    "cerveza cov": "cerveza coviran",
}


def clave_producto(nombre) -> str:
    """'Leche  Covap!' y 'leche covap' -> 'leche covap' (y aplica MISMO_PRODUCTO)."""
    texto = unicodedata.normalize("NFKD", nombre or "")
    texto = "".join(c for c in texto if not unicodedata.combining(c)).lower()
    texto = re.sub(r"[^a-z0-9ñ]+", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return MISMO_PRODUCTO.get(texto, texto)


def _compras_por_producto(conn) -> dict:
    """{clave: {"nombres": Counter, "compras": [dict...]}} sin las entradas genéricas."""
    filas = conn.execute(
        """SELECT p.nombre, p.cantidad, p.precio_centimos, p.importe_centimos, p.categoria,
                  t.tienda, t.fecha
           FROM productos p JOIN tickets t ON t.id = p.ticket_id
           ORDER BY t.fecha"""
    ).fetchall()
    productos = defaultdict(lambda: {"nombres": Counter(), "compras": []})
    for f in filas:
        clave = clave_producto(f["nombre"])
        if not clave or clave in GENERICOS:
            continue
        productos[clave]["nombres"][f["nombre"].strip()] += 1
        productos[clave]["compras"].append({
            "tienda": f["tienda"],
            "fecha": f["fecha"][:10],
            "cantidad": f["cantidad"] or 1,
            "precio": f["precio_centimos"],
            "importe": f["importe_centimos"],
            "categoria": (f["categoria"] or "").strip(),
        })
    return productos


def comparar_precios(conn) -> dict:
    """Productos comprados en 2 o más tiendas: precio medio en cada una, la más
    barata, cuánto te habrías ahorrado comprándolo siempre allí y qué tienda es
    más barata en general (índice 100 = precio medio entre tus tiendas)."""
    productos = []
    indices = defaultdict(list)            # tienda -> [índice por producto]
    veces_barata = Counter()
    for info in _compras_por_producto(conn).values():
        por_tienda = defaultdict(list)
        for c in info["compras"]:
            por_tienda[c["tienda"]].append(c)
        if len(por_tienda) < 2:
            continue

        tiendas = []
        for tienda, cs in por_tienda.items():
            tiendas.append({
                "tienda": tienda,
                "media_cents": sum(c["precio"] for c in cs) / len(cs),
                "ultimo": a_euros(cs[-1]["precio"]),
                "ultima_fecha": cs[-1]["fecha"],
                "veces": len(cs),
            })
        tiendas.sort(key=lambda t: t["media_cents"])
        barata, cara = tiendas[0], tiendas[-1]
        ratio = cara["media_cents"] / barata["media_cents"] if barata["media_cents"] else 0
        ahorro = sum(max(0, c["precio"] - barata["media_cents"]) * c["cantidad"] for c in info["compras"])
        sospechoso = ratio >= RATIO_SOSPECHOSO

        media_producto = sum(t["media_cents"] for t in tiendas) / len(tiendas)
        if not sospechoso and media_producto:
            for t in tiendas:
                indices[t["tienda"]].append(t["media_cents"] / media_producto * 100)
            veces_barata[barata["tienda"]] += 1

        for t in tiendas:
            t["media"] = a_euros(round(t.pop("media_cents")))
        productos.append({
            "nombre": info["nombres"].most_common(1)[0][0],
            "tiendas": tiendas,
            "barata": barata["tienda"],
            "precio_barato": barata["media"],
            "cara": cara["tienda"],
            "precio_caro": cara["media"],
            "ratio": round(ratio, 2),
            "pct_mas_caro": round((ratio - 1) * 100),
            "ahorro": a_euros(round(ahorro)),
            "compras": len(info["compras"]),
            "sospechoso": sospechoso,
        })

    productos.sort(key=lambda p: (p["sospechoso"], -p["ahorro"], p["nombre"].lower()))
    ranking = sorted(
        ({"tienda": t, "indice": round(sum(v) / len(v)), "productos": len(v),
          "veces_mas_barata": veces_barata[t]}
         for t, v in indices.items() if len(v) >= 3),
        key=lambda r: r["indice"],
    )
    return {
        "productos": productos,
        "ahorro_total": round(sum(p["ahorro"] for p in productos if not p["sospechoso"]), 2),
        "num_productos": len(productos),
        "ranking_tiendas": ranking,
    }


def productos_mas_comprados(conn, limite=20, hoy=None) -> dict:
    """Ranking de productos por veces y por gasto, cada cuántos días los compras
    y cuáles te toca comprar ya (llevas más días que tu ritmo habitual)."""
    hoy = hoy or date.today()
    favoritos = {clave_producto(f["nombre_norm"])
                 for f in conn.execute("SELECT nombre_norm FROM favoritos")}

    lista = []
    for clave, info in _compras_por_producto(conn).items():
        if clave in FUERA_DEL_RANKING:
            continue
        cs = info["compras"]
        dias = sorted({c["fecha"] for c in cs})
        fechas = [date.fromisoformat(d) for d in dias]
        huecos = [(b - a).days for a, b in zip(fechas, fechas[1:])]
        cada = round(median(huecos)) if len(huecos) >= 2 else None
        desde = (hoy - fechas[-1]).days
        categorias = Counter(c["categoria"] for c in cs if c["categoria"])
        lista.append({
            "nombre": info["nombres"].most_common(1)[0][0],
            "veces": len(dias),
            "unidades": sum(c["cantidad"] for c in cs),
            "gasto": a_euros(sum(c["importe"] for c in cs)),
            "precio_medio": a_euros(round(sum(c["precio"] for c in cs) / len(cs))),
            "ultima": dias[-1],
            "dias_desde": desde,
            "cada_dias": cada,
            "toca": cada is not None and desde >= cada,
            "tiendas": sorted({c["tienda"] for c in cs}),
            "categoria": categorias.most_common(1)[0][0] if categorias else "Sin categoría",
            "favorito": clave in favoritos,
        })

    por_veces = sorted(lista, key=lambda p: (-p["veces"], -p["gasto"]))[:limite]
    por_gasto = sorted(lista, key=lambda p: -p["gasto"])[:limite]
    # Solo productos habituales (3+ días distintos) y no abandonados: llevas
    # entre 1 y 2 veces tu ritmo habitual sin comprarlo.
    toca = sorted(
        (p for p in lista if p["toca"] and p["veces"] >= 3 and p["dias_desde"] <= 2 * p["cada_dias"]),
        key=lambda p: p["dias_desde"] / p["cada_dias"], reverse=True,
    )
    return {
        "por_veces": por_veces,
        "por_gasto": por_gasto,
        "toca_comprar": toca,
        "num_productos": len(lista),
    }


# ----------------------------------------------------------------------
# Evolución mes a mes
# ----------------------------------------------------------------------
MESES_CORTOS = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]
CATEGORIAS_EN_GRAFICO = 6        # las demás se juntan en "Otras"


def _etiqueta_mes(mes: str) -> str:
    """'2026-03' -> 'mar 26'."""
    return f"{MESES_CORTOS[int(mes[5:7]) - 1]} {mes[2:4]}"


def evolucion_mensual(conn, hoy=None) -> dict:
    """Gasto por mes (total, tickets, ticket medio y por categoría), la media de
    los meses completos y cómo va el mes actual frente a esa media."""
    hoy = hoy or date.today()
    mes_actual = hoy.strftime("%Y-%m")
    filas = conn.execute(
        """SELECT substr(t.fecha, 1, 7) AS mes, t.id AS ticket,
                  COALESCE(NULLIF(TRIM(p.categoria), ''), 'Sin categoría') AS cat,
                  p.importe_centimos AS importe
           FROM tickets t JOIN productos p ON p.ticket_id = t.id"""
    ).fetchall()
    if not filas:
        return {"meses": [], "categorias": [], "media": 0.0, "actual": None, "mejor": None, "peor": None}

    total = defaultdict(int)
    tickets = defaultdict(set)
    por_cat = defaultdict(lambda: defaultdict(int))
    gasto_cat = Counter()
    for f in filas:
        total[f["mes"]] += f["importe"]
        tickets[f["mes"]].add(f["ticket"])
        por_cat[f["mes"]][f["cat"]] += f["importe"]
        gasto_cat[f["cat"]] += f["importe"]

    # Todos los meses entre el primero y el actual, aunque alguno no tenga compras.
    primero = min(total)
    a, m = int(primero[:4]), int(primero[5:7])
    lista_meses = []
    while f"{a:04d}-{m:02d}" <= max(max(total), mes_actual):
        lista_meses.append(f"{a:04d}-{m:02d}")
        a, m = (a + 1, 1) if m == 12 else (a, m + 1)

    top = [c for c, _ in gasto_cat.most_common(CATEGORIAS_EN_GRAFICO)]
    categorias = top + (["Otras"] if len(gasto_cat) > len(top) else [])

    meses = []
    for mes in lista_meses:
        cats = por_cat.get(mes, {})
        reparto = {c: a_euros(cats.get(c, 0)) for c in top}
        if "Otras" in categorias:
            reparto["Otras"] = a_euros(sum(v for c, v in cats.items() if c not in top))
        n = len(tickets.get(mes, ()))
        meses.append({
            "mes": mes,
            "etiqueta": _etiqueta_mes(mes),
            "total": a_euros(total.get(mes, 0)),
            "tickets": n,
            "ticket_medio": round(total.get(mes, 0) / n / 100, 2) if n else 0.0,
            "categorias": reparto,
            "en_curso": mes == mes_actual,
        })

    completos = [x for x in meses if not x["en_curso"]]
    media = round(sum(x["total"] for x in completos) / len(completos), 2) if completos else 0.0
    for x in meses:
        x["vs_media"] = round((x["total"] / media - 1) * 100) if media and not x["en_curso"] else None

    actual = next((x for x in meses if x["en_curso"]), None)
    if actual:
        dias_mes = calendar.monthrange(hoy.year, hoy.month)[1]
        actual = dict(actual)
        actual["dia"] = hoy.day
        actual["dias_mes"] = dias_mes
        actual["prevision"] = round(actual["total"] / hoy.day * dias_mes, 2)
        actual["media"] = media
        # Lo que solías llevar gastado a estas alturas del mes (media de los meses completos).
        actual["media_a_estas_alturas"] = round(media * hoy.day / dias_mes, 2)

    return {
        "meses": meses,
        "categorias": categorias,
        "media": media,
        "actual": actual,
        "mejor": min(completos, key=lambda x: x["total"]) if completos else None,
        "peor": max(completos, key=lambda x: x["total"]) if completos else None,
    }
