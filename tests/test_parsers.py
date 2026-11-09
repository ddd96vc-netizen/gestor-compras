"""
test_parsers.py - Tests de los parsers de tickets (OCR)
=======================================================
Trabajan sobre TEXTO de ejemplo (el que devolvería el OCR), así que no
necesitan ni imágenes ni EasyOCR instalado.

FLUJO DE MEJORA CONTINUA:
  Cuando un ticket real se lea mal, copia su texto OCR (lo tienes en la
  pantalla de revisión y en instance/ocr_muestras/) y añádelo aquí como un
  test nuevo. Así, al ajustar una regla para arreglarlo, te aseguras de no
  romper el parseo de los tickets que ya funcionaban.
"""

from app.ocr.parsers import parsear_ticket


TICKET_BAZAR = """BAZAR LUCKY
CALLE REAL 22
--------------------
VASO CRISTAL       1,50
2 x PILAS AA       3,00
CUADERNO A4        2,25
--------------------
TOTAL              6,75
EFECTIVO          10,00
CAMBIO             3,25
GRACIAS POR SU COMPRA
22/12/2025 21:37"""

TICKET_MERCADONA = """MERCADONA S.A.
C/ MAYOR 15
07/12/2025 21:28 OP: 1234
LECHE ENTERA        1,20
PAN INTEGRAL        0,85
3 x YOGUR NATURAL   1,50
TOTAL (5)           3,55
TARJETA BANCARIA    3,55"""

# Ticket real con formato de 4 columnas: NOMBRE | CANTIDAD | PRECIO | IMPORTE
# (así son todos los tickets de Daniel). Las líneas ya vienen reconstruidas
# por posición, tal como las devuelve lector.reconstruir_filas().
TICKET_4_COLUMNAS = """FACTURA SIMPLIFICADA 40301032339
FECHA: 04/07/2026 TPV: 01 CENTRO: 403
18:20
SALCHICHA PK-4     1   2.45   2.45
EL POTAJE          1   0.75   0.75
PARDINA ELIGES     1   0.75   0.75
ZANAH.ELIGES       1   0.89   0.89
ATUN ELIGE P-3     1   2.75   2.75
MERMEL.ELIGES      1   1.80   1.80
ZUMOS ELIGES       1   0.80   0.80
COVAP ENTERA       1   1.75   1.75
TOSTADA ELIGES     1   1.35   1.35
CROISSANTS 360     1   1.87   1.87
ESTRELLA SUR       2   0.58   1.16
FUENTEPR.500ML     1   0.30   0.30
CACAHUETE ELIG     1   0.90   0.90
BOLSA FL JAMON     1   0.15   0.15
ENSAL.MINAFLOR     1   0.79   0.79"""


def test_bazar_generico():
    r = parsear_ticket(TICKET_BAZAR)
    assert r["parser"] == "ParserGenerico"
    assert r["tienda"] == "Bazar Lucky"
    assert r["fecha"] == "2025-12-22T21:37"
    assert len(r["productos"]) == 3            # TOTAL/EFECTIVO/CAMBIO/GRACIAS fuera
    # La cantidad de las pilas se detecta como 2
    pilas = next(p for p in r["productos"] if "Pilas" in p["nombre"])
    assert pilas["cantidad"] == 2
    assert pilas["precio"] == 3.00


def test_mercadona_usa_su_parser():
    r = parsear_ticket(TICKET_MERCADONA)
    assert r["parser"] == "ParserMercadona"
    assert r["tienda"] == "Mercadona"          # nombre fijo, no depende del OCR
    assert r["fecha"] == "2025-12-07T21:28"
    assert len(r["productos"]) == 3            # TOTAL y TARJETA fuera
    yogur = next(p for p in r["productos"] if "Yogur" in p["nombre"])
    assert yogur["cantidad"] == 3
    leche = next(p for p in r["productos"] if p["nombre"].startswith("Leche"))
    assert leche["precio"] == 1.20


def test_lineas_de_ruido_se_ignoran():
    r = parsear_ticket(TICKET_BAZAR)
    nombres = " ".join(p["nombre"].lower() for p in r["productos"])
    for ruido in ("total", "efectivo", "cambio", "gracias"):
        assert ruido not in nombres


def test_precio_formato_espanol():
    from app.ocr.parsers.base import parsear_euros
    assert parsear_euros("1,20") == 1.20
    assert parsear_euros("1.20") == 1.20
    assert parsear_euros("1.234,56") == 1234.56


def test_ticket_sin_productos_no_rompe():
    r = parsear_ticket("TIENDA X\nGRACIAS POR SU VISITA")
    assert r["productos"] == []


def test_formato_4_columnas_ticket_real():
    """Caso de regresión: ticket real de 4 columnas (nombre, cantidad, precio, importe)."""
    r = parsear_ticket(TICKET_4_COLUMNAS)
    assert len(r["productos"]) == 15
    assert r["fecha"] == "2026-07-04T18:20"

    suma = round(sum(p["precio"] * p["cantidad"] for p in r["productos"]), 2)
    assert suma == 18.46

    estrella = next(p for p in r["productos"] if "Estrella" in p["nombre"])
    assert estrella["cantidad"] == 2
    assert estrella["precio"] == 0.58


def test_autocorreccion_cantidad_perdida_por_ocr():
    """Si el OCR no lee el dígito de cantidad, se recalcula con el importe total."""
    from app.ocr.parsers.base import ParserTicket
    parser = ParserTicket()
    linea_sin_cantidad = "ESTRELLA SUR   0.58   1.16"   # falta la columna "2"
    productos = parser.extraer_productos([linea_sin_cantidad])
    assert productos[0]["cantidad"] == 2
    assert productos[0]["precio"] == 0.58


def test_precio_tolera_espacios_del_ocr():
    """El OCR a veces mete un espacio antes de la coma: '1 ,16'."""
    from app.ocr.parsers.base import parsear_euros
    assert parsear_euros("1 ,16") == 1.16


# --- Tickets reales (texto OCR tal cual, de instance/ocr_muestras/) ---

TICKET_DEZA = """Deza Zoco-957456125 Deza Calidad; 5.6,
NS 66745 P Las Quemadas, 116
01-08-2026 14: 13:25 14014 Cordoba
Caja 10-003128 614051585
Descr iccicn Cøntidad Pvp Inporte
Bêtido de chocolate PULEVA botella 1'99 1'99
Bolsa reciclade 70* DEZA 48x59 6200 2 0'12 0' 24
Filetes de cerdo FACCSA ~kg - 1'6 3'95 6'12
Janoncitos de Pollo INASUR enteros 1 1 2'69 2*84
Refresco CoCh {olA 1.25 L 1'55 1'55
Tipo Base Iva Total 30*51
4% 2'78 0'11 Hetalico entregado 50
212 2'50 0'53 Devuelto 19' 49"""

TICKET_DIA = """GRUPO DIA
FACTURA SIMPLIFICADA
08-07-2026 17;07 07726 0o7726003
DESCRIPCION ARTICULO IMPORTE €
BOLSA 50* RECICLADA 0,15 €
CERVEZA LATA RAMBLER 0 46
LECHUGA   ROMANA   0,89 A
TOTAL COMPRA GRUPO DIA < 2 rne 8 ,12,<
DESGLOSES DEL IvA GRupo DiA Aeoet"""

TICKET_EL_JAMON = """4 PINTOR  EsPinosa _ F Datou 19
FECHA 3 27/07/2026   TPV : 02 CENTRO; 403
21:00
LoNCHAS   KROL 2 0,95 1 90
ATrN FeniCiA 1 1 89 1,89
NESTLf 9OOG 45 1,45
TotaL FACTURA 9,90"""


def test_deza_precios_con_apostrofo_y_al_peso():
    r = parsear_ticket(TICKET_DEZA)
    assert r["tienda"] == "Zoco"
    assert r["fecha"] == "2026-08-01T14:13"        # "14: 13:25" con espacio del OCR
    assert r["total"] == 30.51
    por_nombre = {p["nombre"].split()[0]: p for p in r["productos"]}
    assert len(r["productos"]) == 5                 # el desglose de IVA no cuenta
    assert por_nombre["Bêtido"]["precio"] == 1.99   # "botella" ya no se toma por "TEL"
    assert por_nombre["Bolsa"]["cantidad"] == 2 and por_nombre["Bolsa"]["importe"] == 0.24
    # Al peso: el dinero real es el importe y el €/kg va a la observación.
    filetes = por_nombre["Filetes"]
    assert (filetes["precio"], filetes["cantidad"]) == (6.12, 1)
    assert filetes["observacion"] == "1,6 kg a 3,95 €/kg"
    assert por_nombre["Janoncitos"]["precio"] == 2.84
    # "1.25 L" es el tamaño, no el precio.
    assert por_nombre["Refresco"]["precio"] == 1.55


def test_dia_precio_partido_y_hora_con_punto_y_coma():
    r = parsear_ticket(TICKET_DIA)
    assert r["tienda"] == "Dia"
    assert r["fecha"] == "2026-07-08T17:07"
    assert r["total"] == 8.12
    precios = [p["precio"] for p in r["productos"]]
    assert precios == [0.15, 0.46, 0.89]          # "0 46" -> 0,46


def test_el_jamon_cantidades_sin_columna_de_importe():
    r = parsear_ticket(TICKET_EL_JAMON)
    assert r["tienda"] == "El Jamon"
    assert r["fecha"] == "2026-07-27T21:00"
    lonchas, atun, nestle = r["productos"]
    assert (lonchas["cantidad"], lonchas["precio"], lonchas["importe"]) == (2, 0.95, 1.90)
    assert (atun["cantidad"], atun["precio"]) == (1, 1.89)     # "1 89" no es cantidad 89
    assert (nestle["cantidad"], nestle["precio"]) == (1, 1.45)  # "45" no es cantidad 45
    assert round(sum(p["importe"] for p in r["productos"]), 2) == 5.24


def test_precio_con_apostrofo_y_asterisco():
    from app.ocr.parsers.base import parsear_euros
    assert parsear_euros("1'24") == 1.24
    assert parsear_euros("0' 24") == 0.24
    assert parsear_euros("2*84") == 2.84


def test_tienda_reconocida_aunque_el_ocr_la_lea_mal():
    r = parsear_ticket("Pinir Espinmo 19\nFECHA 04/07/2026\nSALCHICHA 2,45 2,45")
    assert r["tienda"] == "El Jamon"
    assert parsear_ticket("MERCADOMA S.A.\nLECHE 1,20")["tienda"] == "Mercadona"
    # Las claves cortas solo valen exactas: "DEZO" no es Deza.
    assert parsear_ticket("DEZO\nLECHE 1,20")["parser"] == "ParserGenerico"
