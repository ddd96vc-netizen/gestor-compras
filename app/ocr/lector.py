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


def extraer_texto(ruta_imagen) -> str:
    """Devuelve el texto de la imagen, reconstruido en filas (ver docstring del módulo)."""
    lector = _obtener_lector()
    # detail=1 -> cada resultado es (bbox, texto, confianza), con la posición.
    resultados = lector.readtext(str(ruta_imagen), detail=1, paragraph=False)
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
            "y": (min(ys) + max(ys)) / 2,
            "alto": max(ys) - min(ys),
            "texto": texto,
        })

    if not bloques:
        return []

    if tolerancia_y is None:
        alturas = sorted(b["alto"] for b in bloques if b["alto"] > 0)
        alto_tipico = alturas[len(alturas) // 2] if alturas else 20  # mediana
        # 65% de la altura del texto: agrupa bloques de una misma fila aunque
        # estén ligeramente descuadrados (por ángulo de la foto o desenfoque),
        # sin llegar a fundir dos filas distintas entre sí.
        tolerancia_y = max(alto_tipico * 0.65, 8)

    bloques.sort(key=lambda b: b["y"])

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

    lineas = []
    for fila in filas:
        fila.sort(key=lambda b: b["x"])           # izquierda a derecha
        lineas.append(" ".join(b["texto"] for b in fila))
    return lineas
