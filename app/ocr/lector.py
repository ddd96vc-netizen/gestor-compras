"""
lector.py - OCR: imagen -> texto
================================
Envuelve el motor de OCR (EasyOCR) con import PEREZOSO: la librería solo se
carga la primera vez que se usa de verdad. Así la aplicación arranca aunque
EasyOCR no esté instalado, y solo falla (con un mensaje claro) si intentas
escanear un ticket sin haberlo instalado.

RECONSTRUCCIÓN DE FILAS
=======================
Muchos tickets españoles son tablas: "NOMBRE  CANTIDAD  PRECIO  IMPORTE" en
la misma línea, pero con columnas separadas por bastante espacio. EasyOCR
detecta cada columna como un bloque de texto independiente, y si solo le
pides el texto (sin posición) los va soltando en el orden en que los
detectó, no en el orden real de la fila -> el nombre y el precio de un
mismo producto acaban en "líneas" distintas y desordenadas.

Para evitarlo, pedimos también la posición (bounding box) de cada bloque,
los agrupamos por altura (misma fila) y dentro de cada fila los ordenamos
de izquierda a derecha. Eso reconstruye la línea tal como está impresa en
el ticket, que es lo que necesitan los parsers de app/ocr/parsers/.
"""


class OcrNoDisponible(RuntimeError):
    """Se lanza cuando el motor de OCR no está instalado."""


_lector = None


def _obtener_lector():
    """Crea (una sola vez) el lector de EasyOCR en español."""
    global _lector
    if _lector is None:
        try:
            import easyocr
        except ImportError as e:
            raise OcrNoDisponible(
                "EasyOCR no está instalado. Instala las dependencias de OCR con:\n"
                "    pip install -r requirements-ocr.txt"
            ) from e
        # ['es'] = español · gpu=False = CPU.
        # OJO: la PRIMERA vez descarga el modelo (~64 MB) y tarda un rato.
        _lector = easyocr.Reader(["es"], gpu=False)
    return _lector


# Lado mayor con el que se pasa la foto al OCR. Las fotos de móvil (4000 px)
# son lentísimas en CPU y no se leen mejor; con ~2000 px el texto del ticket
# sigue teniendo de sobra.
LADO_MAX = 2000


def preparar_imagen(ruta_imagen):
    """Abre la foto y la deja lista para el OCR (devuelve un array de numpy).

      - Aplica la rotación EXIF: el móvil guarda la foto "tumbada" y anota en
        los metadatos que hay que girarla. EasyOCR no lee esos metadatos, así
        que sin esto lee el ticket de lado y devuelve basura.
      - Escala de grises + autocontraste: el papel térmico sale grisáceo.
      - Reduce las fotos enormes a LADO_MAX píxeles.
    """
    import numpy as np
    from PIL import Image, ImageOps

    with Image.open(ruta_imagen) as img:
        img = ImageOps.exif_transpose(img)
        img = img.convert("L")
        if max(img.size) > LADO_MAX:
            img.thumbnail((LADO_MAX, LADO_MAX), Image.LANCZOS)
        img = ImageOps.autocontrast(img, cutoff=1)
        return np.array(img)


def extraer_texto(ruta_imagen) -> str:
    """Devuelve el texto de la imagen, reconstruido en filas (ver docstring del módulo)."""
    lector = _obtener_lector()
    # detail=1 -> cada resultado es (bbox, texto, confianza), con la posición.
    resultados = lector.readtext(preparar_imagen(ruta_imagen), detail=1, paragraph=False)
    filas = reconstruir_filas(resultados)
    return "\n".join(filas)


def reconstruir_filas(resultados, tolerancia_y=None) -> list:
    """Agrupa bloques de texto en filas por altura y los ordena por posición horizontal.

    `resultados` es la salida cruda de EasyOCR: lista de (bbox, texto, confianza),
    donde bbox son las 4 esquinas del rectángulo detectado.

    `tolerancia_y`: margen en píxeles para considerar dos bloques "de la misma
    fila". Si no se indica (caso normal), se calcula SOLO a partir del tamaño
    del texto detectado en la propia foto (una fracción de su altura media).
    Un valor fijo no sirve: una foto de móvil puede tener miles de píxeles de
    alto y letras de 40-50px, así que la tolerancia tiene que escalar con la
    resolución real de la imagen, no ser un número fijo.

    Se aísla en una función independiente (sin depender de EasyOCR) para
    poder testear la lógica de agrupamiento con datos de ejemplo.
    """
    bloques = []
    for bbox, texto, _confianza in resultados:
        xs = [punto[0] for punto in bbox]
        ys = [punto[1] for punto in bbox]
        bloques.append({
            "x": min(xs),
            "x2": max(xs),
            "xc": (min(xs) + max(xs)) / 2,
            "y": (min(ys) + max(ys)) / 2,
            "alto": max(ys) - min(ys),
            "texto": texto,
        })

    if not bloques:
        return []

    alturas = sorted(b["alto"] for b in bloques if b["alto"] > 0)
    alto_tipico = alturas[len(alturas) // 2] if alturas else 20  # mediana

    auto = tolerancia_y is None
    if auto:
        # 65% de la altura del texto: agrupa bloques de una misma fila aunque
        # estén ligeramente descuadrados (por ángulo de la foto o desenfoque),
        # sin llegar a fundir dos filas distintas entre sí.
        tolerancia_y = max(alto_tipico * 0.65, 8)

        # Foto inclinada: las columnas de la derecha (precios) quedan más
        # altas o más bajas que el nombre y se cruzan con la fila vecina.
        # Se estima la pendiente y se "endereza" la altura de cada bloque.
        pendiente = estimar_inclinacion(bloques, alto_tipico)
        if pendiente:
            for b in bloques:
                b["y"] -= pendiente * b["xc"]

    filas = _agrupar_por_anclas(bloques, tolerancia_y) if auto else None
    if not filas:
        filas = _agrupar_en_cadena(bloques, tolerancia_y)

    lineas = []
    for fila in filas:
        fila.sort(key=lambda b: b["x"])           # izquierda a derecha
        lineas.append(" ".join(b["texto"] for b in fila))
    return lineas


def _agrupar_en_cadena(bloques, tolerancia_y) -> list:
    """Agrupado clásico: ordena por altura y une lo que esté a menos de `tolerancia_y`."""
    bloques = sorted(bloques, key=lambda b: b["y"])
    filas, fila_actual, y_referencia = [], [], None
    for bloque in bloques:
        if y_referencia is None or abs(bloque["y"] - y_referencia) <= tolerancia_y:
            fila_actual.append(bloque)
            # Media móvil: si la fila está algo inclinada, el margen se ajusta con ella.
            y_referencia = bloque["y"] if y_referencia is None else (y_referencia + bloque["y"]) / 2
        else:
            filas.append(fila_actual)
            fila_actual = [bloque]
            y_referencia = bloque["y"]
    if fila_actual:
        filas.append(fila_actual)
    return filas


# Los bloques que empiezan en el primer 30 % del ancho del ticket son
# "anclas" (el nombre del producto, "TOTAL", "Tipo"...).
ZONA_ANCLA = 0.30


def _agrupar_por_anclas(bloques, tolerancia_y):
    """Agrupado anclado en la columna izquierda.

    En tickets con líneas muy juntas el agrupado en cadena se "contagia":
    un precio a medio camino entre dos filas las une y acaban 3-4 productos
    en una sola línea. Aquí cada fila nace de un bloque de la izquierda y
    cada bloque de la derecha (cantidad, precio, importe) se asigna a la
    fila MÁS CERCANA, sin cadenas. Lo que no está cerca de ninguna fila se
    agrupa aparte con el método clásico.
    """
    x_min = min(b["x"] for b in bloques)
    x_max = max(b["x2"] for b in bloques)
    limite = x_min + (x_max - x_min) * ZONA_ANCLA
    anclas = sorted((b for b in bloques if b["x"] <= limite), key=lambda b: b["y"])
    if len(anclas) < 3:
        return None

    filas = []   # cada fila: {"y": altura media de sus anclas, "bloques": [...]}
    for ancla in anclas:
        # Trozos del mismo nombre ("Bo 1se" + "reciclada") van a la misma fila:
        # están a la misma altura y uno empieza donde acaba el otro.
        if filas and (
            abs(ancla["y"] - filas[-1]["y"]) <= tolerancia_y * 0.6
            or (abs(ancla["y"] - filas[-1]["y"]) <= tolerancia_y
                and ancla["x"] >= max(b["x2"] for b in filas[-1]["bloques"]) - 5)
        ):
            fila = filas[-1]
            fila["bloques"].append(ancla)
            fila["y"] = sum(b["y"] for b in fila["bloques"]) / len(fila["bloques"])
        else:
            filas.append({"y": ancla["y"], "bloques": [ancla]})

    sueltos = []
    for bloque in bloques:
        if bloque["x"] <= limite:
            continue
        cercana = min(filas, key=lambda f: abs(f["y"] - bloque["y"]))
        if abs(cercana["y"] - bloque["y"]) <= tolerancia_y:
            cercana["bloques"].append(bloque)
        else:
            sueltos.append(bloque)

    grupos = [f["bloques"] for f in filas] + (_agrupar_en_cadena(sueltos, tolerancia_y) if sueltos else [])
    grupos.sort(key=lambda g: sum(b["y"] for b in g) / len(g))
    return grupos


def _nitidez_filas(bloques, pendiente, alto_tipico) -> float:
    """Cuánto se alinean en filas los bloques si se endereza con `pendiente`.

    Suma, para cada pareja de bloques separados en horizontal (columnas
    distintas), una campana según lo cerca que queden en altura una vez
    corregidos. Con la inclinación correcta el nombre y sus precios quedan
    a la misma altura y la suma es máxima.
    """
    import math
    sigma2 = 2 * (alto_tipico / 6) ** 2
    separacion = 3 * alto_tipico
    total = 0.0
    for i, a in enumerate(bloques):
        ya = a["y"] - pendiente * a["xc"]
        for b in bloques[i + 1:]:
            if abs(a["xc"] - b["xc"]) < separacion:
                continue
            d = ya - (b["y"] - pendiente * b["xc"])
            total += math.exp(-d * d / sigma2)
    return total


def estimar_inclinacion(bloques, alto_tipico, maximo=0.08, pasos=41) -> float:
    """Pendiente (px de alto por px de ancho) de las filas del ticket, o 0.

    EasyOCR devuelve cajas rectas, así que no da el ángulo; se busca la
    pendiente que mejor alinea los bloques en filas. Solo se aplica si mejora
    claramente a "sin inclinación" (si no, se devuelve 0 y nada cambia).
    """
    if len(bloques) < 6:
        return 0.0
    base = _nitidez_filas(bloques, 0.0, alto_tipico)
    mejor, mejor_pendiente = base, 0.0
    for i in range(pasos):
        pendiente = -maximo + 2 * maximo * i / (pasos - 1)
        valor = _nitidez_filas(bloques, pendiente, alto_tipico)
        if valor > mejor:
            mejor, mejor_pendiente = valor, pendiente
    return mejor_pendiente if mejor > base * 1.05 else 0.0
