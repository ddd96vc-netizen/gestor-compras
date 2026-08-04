"""
base.py - Clase base de los parsers de tickets
==============================================
Contiene la lógica genérica de extracción (fecha, precios, productos) y
las utilidades compartidas. Cada tienda concreta hereda de `ParserTicket`
y sobreescribe solo lo que necesite.

Todo esto trabaja sobre TEXTO ya extraído por el OCR: no depende de ninguna
librería de imágenes, así que se puede testear con texto de ejemplo.
"""

import re
from datetime import datetime


# --- Expresiones regulares reutilizables ---
# Tolerante a espacios sueltos que a veces mete el OCR: "1 ,16" también cuenta.
RE_PRECIO = re.compile(r"(\d{1,4}\s*[.,]\s*\d{2})\b")     # 1,20 · 1.20 · 1 ,16
RE_FECHA = re.compile(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{2,4})")   # 07/12/2025
RE_HORA = re.compile(r"\b(\d{1,2}):(\d{2})\b")           # 21:28
RE_CANTIDAD_PREFIJO = re.compile(r"^\s*(\d{1,3})\s*[xX*]\s*")   # "3 x ..."  ·  "2x ..."
RE_CANTIDAD_COLUMNA = re.compile(r"(?<!\d)(\d{1,3})\s*$")       # entero suelto al final

# Palabras que NO son productos (líneas a ignorar del ticket).
PALABRAS_RUIDO = {
    "TOTAL", "SUBTOTAL", "SUB-TOTAL", "IVA", "I.V.A", "BASE", "IMPONIBLE",
    "CIF", "NIF", "N.I.F", "TARJETA", "EFECTIVO", "CAMBIO", "ENTREGADO",
    "GRACIAS", "VISA", "MASTERCARD", "FACTURA", "TELEFONO", "TEL",
    "DEVOLUCION", "CUOTA", "ARTICULOS", "UNIDADES", "OPERACION", "IMPORTE",
    "AUTORIZACION", "COMERCIO", "TERMINAL", "APROBADA", "AHORRO", "REDONDEO",
    "PAGO", "CONTADO", "WWW", "HTTP", "PVP",
}


def parsear_euros(texto: str) -> float:
    """Convierte '1,20' / '1.20' / '1 ,16' / '1.234,56' a float (formato español)."""
    texto = texto.strip().replace(" ", "")
    if "," in texto and "." in texto:          # 1.234,56 -> el punto es de miles
        texto = texto.replace(".", "").replace(",", ".")
    elif "," in texto:                          # 1,20 -> coma decimal
        texto = texto.replace(",", ".")
    # si solo hay ".", se asume que ya es el decimal
    return round(float(texto), 2)


class ParserTicket:
    """
    Parser base. Una tienda concreta hereda de aquí y ajusta lo que necesite.

    Atributos que las subclases suelen definir:
      - palabras_clave: tuplas de texto que identifican la tienda en el OCR.
      - nombre_tienda:  nombre "limpio" a rellenar (evita depender del OCR).
    """

    palabras_clave: tuple = ()
    nombre_tienda: str | None = None

    def parsear(self, texto: str) -> dict:
        lineas = self.dividir_lineas(texto)
        return {
            "tienda": self.extraer_tienda(texto, lineas),
            "fecha": self.extraer_fecha(texto),
            "productos": self.extraer_productos(lineas),
        }

    # --- Utilidades ---

    def dividir_lineas(self, texto: str) -> list:
        return [linea.strip() for linea in texto.splitlines() if linea.strip()]

    def es_linea_ruido(self, linea: str) -> bool:
        mayus = linea.upper()
        return any(palabra in mayus for palabra in PALABRAS_RUIDO)

    # --- Extractores (sobreescribibles por cada tienda) ---

    def extraer_tienda(self, texto: str, lineas: list) -> str:
        """Nombre de la tienda. Si la subclase fija `nombre_tienda`, se usa ese."""
        if self.nombre_tienda:
            return self.nombre_tienda
        for linea in lineas[:6]:
            letras = sum(1 for c in linea if c.isalpha())
            if letras >= 3 and not RE_FECHA.search(linea):
                return linea.title()
        return ""

    def extraer_fecha(self, texto: str) -> str:
        """Devuelve la fecha en formato 'YYYY-MM-DDTHH:MM' (para el <input>)."""
        mf = RE_FECHA.search(texto)
        if not mf:
            return ""
        dia, mes, anio = mf.groups()
        if len(anio) == 2:
            anio = "20" + anio
        try:
            fecha = datetime(int(anio), int(mes), int(dia))
        except ValueError:
            return ""
        dia_iso = fecha.strftime("%Y-%m-%d")

        mh = RE_HORA.search(texto)
        if mh:
            hora, minuto = mh.groups()
            return f"{dia_iso}T{int(hora):02d}:{minuto}"
        return f"{dia_iso}T00:00"

    def extraer_productos(self, lineas: list) -> list:
        """Extrae [{nombre, precio, cantidad}] de las líneas que parezcan productos.

        Modelo de 4 columnas (el formato habitual de super/tienda):

            NOMBRE  ·  CANTIDAD  ·  PRECIO UNITARIO  ·  IMPORTE TOTAL
            Salchicha PK-4    1        2,45              2,45
            Estrella Sur      2        0,58              1,16

        También reconoce el formato "prefijo" ("2 x Pilas AA   3,00"), por si
        algún ticket lo trae así.

        Autocorrección: cuando hay columna de IMPORTE, se usa para comprobar
        que cantidad × precio cuadra. Si no cuadra (p. ej. el OCR "perdió" el
        dígito de la cantidad), se recalcula la cantidad a partir del importe,
        que suele leerse mejor por ser el número más grande y más a la derecha.
        """
        productos = []
        for linea in lineas:
            if self.es_linea_ruido(linea):
                continue

            precios = list(RE_PRECIO.finditer(linea))
            if not precios:
                continue  # sin precio no es una línea de producto

            cantidad = 1
            m_prefijo = RE_CANTIDAD_PREFIJO.match(linea)

            if m_prefijo:
                # Formato prefijo: "N x NOMBRE PRECIO"
                cantidad = int(m_prefijo.group(1))
                resto = linea[m_prefijo.end():]
                precios_resto = list(RE_PRECIO.finditer(resto))
                if not precios_resto:
                    continue
                precio_match = precios_resto[-1]
                nombre = resto[:precio_match.start()]
            else:
                # Formato de 4 columnas: NOMBRE | CANTIDAD | PRECIO | IMPORTE
                # La columna de PRECIO es la primera cifra decimal de la fila.
                precio_match = precios[0]
                nombre = linea[:precio_match.start()]

                m_cantidad = RE_CANTIDAD_COLUMNA.search(nombre)
                if m_cantidad:
                    cantidad = int(m_cantidad.group(1))
                    nombre = nombre[:m_cantidad.start()]

                # Autocorrección con la columna de IMPORTE (si existe).
                if len(precios) >= 2:
                    precio_unitario = parsear_euros(precio_match.group(1))
                    importe = parsear_euros(precios[-1].group(1))
                    if precio_unitario > 0:
                        cantidad_calculada = round(importe / precio_unitario)
                        cuadra = abs(cantidad_calculada * precio_unitario - importe) < 0.02
                        if cantidad_calculada >= 1 and cuadra:
                            cantidad = cantidad_calculada

            nombre = re.sub(r"\s{2,}", " ", nombre.strip(" .-*:·")).strip()
            if len(nombre) < 2 or not any(c.isalpha() for c in nombre):
                continue  # descartar líneas que no tienen un nombre real

            productos.append({
                "nombre": nombre.title(),
                "precio": parsear_euros(precio_match.group(1)),
                "cantidad": cantidad,
            })
        return productos
