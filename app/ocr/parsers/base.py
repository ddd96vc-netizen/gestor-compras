"""
base.py - Clase base de los parsers de tickets
==============================================
Contiene la lógica genérica de extracción (fecha, precios, productos, total)
y las utilidades compartidas. Cada tienda concreta hereda de `ParserTicket`
y sobreescribe solo lo que necesite.

Todo esto trabaja sobre TEXTO ya extraído por el OCR: no depende de ninguna
librería de imágenes, así que se puede testear con texto de ejemplo.
"""

import re
from datetime import datetime


# --- Expresiones regulares reutilizables ---
# Separador decimal: coma o punto, y también los que usan algunos tickets o
# que el OCR confunde con ellos: apóstrofo (Deza/Zoco imprime "1'24"),
# acento agudo o asterisco ("1*05"). Tolera espacios sueltos: "1 ,16", "0' 24".
SEP_DECIMAL = r"[.,'´`*]"
# No cuenta si va seguido de una unidad: "1.25 L", "0,33 CL" son tamaños, no precios.
RE_PRECIO = re.compile(
    rf"(?<![\d.,])(\d{{1,4}}\s*{SEP_DECIMAL}\s*\d{{2}})(?!\d)(?!\s*(?:L|ML|CL|KG|GR?)\b)",
    re.IGNORECASE,
)
RE_FECHA = re.compile(r"(\d{1,2})\s*[/\-.]\s*\*?(\d{1,2})\s*[/\-.]\s*\*?(\d{4}|\d{2})(?!\d)")
# Fecha con el mes en letras: "01 NOV 26", "21 OCT/26" (fruterías, bazares).
MESES = {"ENE": 1, "FEB": 2, "MAR": 3, "ABR": 4, "MAY": 5, "JUN": 6, "JUL": 7,
         "AGO": 8, "SEP": 9, "SET": 9, "OCT": 10, "NOV": 11, "DIC": 12}
RE_FECHA_MES = re.compile(
    r"(?<!\d)(\d{1,2})\s*[/\-. ]?\s*(" + "|".join(MESES) + r")[A-Z]*\.?\s*[/\-. ]?\s*(\d{4}|\d{2})(?!\d)",
    re.IGNORECASE,
)
RE_HORA = re.compile(r"(?<!\d)([01]?\d|2[0-3])\s?[:;]\s?([0-5]\d)(?!\d)")   # 21:28 · 17;07 · 14: 13
RE_CANTIDAD_PREFIJO = re.compile(r"^\s*(\d{1,3})\s*[xX*]\s+")   # "3 x ..."  ·  "2x ..."
RE_CANTIDAD_COLUMNA = re.compile(r"(?<![\d.,'])(\d{1,3})\s*$")  # entero suelto al final
# Peso con 1 o 3 decimales justo antes de los precios ("1'5", "0,456"): producto al peso.
RE_PESO = re.compile(rf"(?<![\d.,'])(\d{{1,2}}{SEP_DECIMAL}(?:\d|\d{{3}}))\s*$")
# Precio partido por el OCR que ha perdido la coma: "1 89" -> "1,89".
RE_PRECIO_PARTIDO = re.compile(r"(?<![\d.,'*])(\d{1,3}) (\d{2})(?![\d.,'*])")
RE_TOTAL = re.compile(r"\bTOT[A-Z0-9\]\)|]*|\bPAGADO\b|\bA PAGAR\b", re.IGNORECASE)

# Sin columna de importe que lo confirme, un entero mayor que esto delante del
# precio casi nunca es una cantidad (suele ser un trozo del precio mal leído).
CANTIDAD_MAX_SIN_IMPORTE = 10

# Palabras que NO son productos (líneas a ignorar del ticket).
PALABRAS_RUIDO = {
    "TOTAL", "SUBTOTAL", "SUB-TOTAL", "IVA", "I.V.A", "BASE", "IMPONIBLE",
    "CIF", "NIF", "N.I.F", "TARJETA", "EFECTIVO", "CAMBIO", "ENTREGADO",
    "GRACIAS", "VISA", "MASTERCARD", "FACTURA", "TELEFONO", "TEL",
    "DEVOLUCION", "CUOTA", "ARTICULOS", "UNIDADES", "OPERACION", "IMPORTE",
    "AUTORIZACION", "COMERCIO", "TERMINAL", "APROBADA", "AHORRO", "REDONDEO",
    "PAGO", "CONTADO", "WWW", "HTTP", "PVP", "PAGADO", "DEVUELTO", "DESGLOSE",
    "DESCRIPCION", "DESCR", "CANTIDAD", "INPORTE", "DOMICILIO",
}


# Una palabra de ruido solo cuenta como palabra completa: "TEL" no debe
# descartar "BOTELLA", pero sí "TEL: 957..." o "IVA10%".
RE_RUIDO = re.compile(
    r"(?<![A-Z])(?:" + "|".join(sorted((re.escape(p) for p in PALABRAS_RUIDO), key=len, reverse=True)) + r")(?![A-Z])"
)


def parsear_euros(texto: str) -> float:
    """Convierte '1,20' / '1.20' / '1 ,16' / "1'24" / '1.234,56' a float (formato español)."""
    texto = re.sub(r"[\s]", "", texto.strip())
    texto = re.sub(r"['´`*]", ",", texto)       # separadores raros -> coma decimal
    if "," in texto and "." in texto:          # 1.234,56 -> el punto es de miles
        texto = texto.replace(".", "").replace(",", ".")
    elif "," in texto:                          # 1,20 -> coma decimal
        texto = texto.replace(",", ".")
    # si solo hay ".", se asume que ya es el decimal
    return round(float(texto), 2)


def formato_euros(valor: float) -> str:
    return f"{valor:.2f}".replace(".", ",")


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
        productos = self.extraer_productos(lineas)
        total = self.extraer_total(lineas)
        self.cuadrar_con_total(productos, total)
        for producto in productos:
            producto.pop("_alternativas", None)
        return {
            "tienda": self.extraer_tienda(texto, lineas),
            "fecha": self.extraer_fecha(texto),
            "productos": productos,
            "total": total,
        }

    # Máximo de líneas dudosas que se prueban al cuadrar (2^N combinaciones).
    MAX_DUDOSAS = 12

    def cuadrar_con_total(self, productos: list, total) -> None:
        """Usa el TOTAL impreso para elegir entre lecturas dudosas del OCR.

        Algunas líneas admiten dos lecturas (p. ej. "Bahamas 2  1'24": ¿2
        unidades o el "2" es parte del nombre? · "0'74  4'74": ¿el OCR leyó
        mal un dígito del importe?). Cada producto dudoso guarda sus
        alternativas en "_alternativas"; aquí se prueba la combinación que
        hace que la suma coincida con el total, cambiando lo mínimo. Si
        ninguna cuadra, se deja todo como estaba.
        """
        if not total or not productos:
            return
        suma = round(sum(p["importe"] for p in productos), 2)
        if abs(suma - total) < 0.005:
            return
        dudosos = [p for p in productos if p.get("_alternativas")][: self.MAX_DUDOSAS]
        if not dudosos:
            return
        from itertools import product as combinaciones
        base = suma - sum(p["importe"] for p in dudosos)
        mejor = None
        opciones = [[None] + p["_alternativas"] for p in dudosos]
        for eleccion in combinaciones(*opciones):
            cambios = sum(1 for e in eleccion if e is not None)
            s = base + sum(p["importe"] if e is None else e["importe"] for p, e in zip(dudosos, eleccion))
            if abs(round(s, 2) - total) < 0.005 and (mejor is None or cambios < mejor[0]):
                mejor = (cambios, eleccion)
        if mejor:
            for p, e in zip(dudosos, mejor[1]):
                if e is not None:
                    p.update(e)

    def preparar_linea(self, linea: str) -> str:
        """Gancho para reglas propias de cada tienda (por defecto no cambia nada)."""
        return linea

    # --- Utilidades ---

    def dividir_lineas(self, texto: str) -> list:
        return [linea.strip() for linea in texto.splitlines() if linea.strip()]

    def es_linea_ruido(self, linea: str) -> bool:
        return bool(RE_RUIDO.search(linea.upper()))

    def es_linea_total(self, linea: str) -> bool:
        return bool(RE_TOTAL.search(linea)) and not re.search(r"SUB-?TOTAL", linea, re.I)

    @staticmethod
    def reparar_numeros(linea: str) -> str:
        """Arregla precios que el OCR partió en la cola numérica de la línea.

        Solo toca la parte final (tras la última letra), donde están las
        columnas de cantidad/precio/importe, para no alterar el nombre
        ("PACK 6 33CL" se queda como está).
        """
        corte = 0   # posición justo después de la última letra
        for m in re.finditer(r"[^\W\d_]", linea):
            corte = m.end()
        nombre, cola = linea[:corte], linea[corte:]
        cola = RE_PRECIO_PARTIDO.sub(r"\1,\2", cola)
        return nombre + cola

    # --- Extractores (sobreescribibles por cada tienda) ---

    def extraer_tienda(self, texto: str, lineas: list) -> str:
        """Nombre de la tienda. Si la subclase fija `nombre_tienda`, se usa ese."""
        if self.nombre_tienda:
            return self.nombre_tienda
        for linea in lineas[:6]:
            letras = sum(1 for c in linea if c.isalpha())
            visibles = sum(1 for c in linea if not c.isspace())
            # Mayoría de letras: descarta cabeceras ilegibles ("Us Tf 82105 3848 Du J ,L").
            if (letras >= 4 and letras / visibles >= 0.6
                    and not RE_FECHA.search(linea) and not RE_PRECIO.search(linea)):
                return linea.title()
        return ""

    def extraer_fecha(self, texto: str) -> str:
        """Devuelve la fecha en formato 'YYYY-MM-DDTHH:MM' (para el <input>).

        Prioridad: fechas con año de 4 cifras ("16-10-2026"); después las de
        2 cifras ("27/10/26"), que se confunden con otros números ("S.A. 16"
        -> "5.4. 16"); y por último el mes en letras ("01 NOV 26").
        """
        candidatas = sorted(RE_FECHA.finditer(texto), key=lambda m: len(m.group(3)) != 4)
        candidatas += [m for m in RE_FECHA_MES.finditer(texto)]
        for mf in candidatas:
            dia, mes, anio = mf.groups()
            if not mes.isdigit():
                mes = MESES[mes[:3].upper()]
            if len(anio) == 2:
                anio = "20" + anio
            try:
                fecha = datetime(int(anio), int(mes), int(dia))
            except ValueError:
                continue
            if not 2000 <= fecha.year <= 2099:
                continue
            dia_iso = fecha.strftime("%Y-%m-%d")

            # La hora suele ir justo detrás de la fecha (o en la línea siguiente).
            mh = RE_HORA.search(texto, mf.end()) or RE_HORA.search(texto)
            if mh:
                hora, minuto = mh.groups()
                return f"{dia_iso}T{int(hora):02d}:{minuto}"
            return f"{dia_iso}T00:00"
        return ""

    def extraer_total(self, lineas: list):
        """Total impreso en el ticket (para comprobar la lectura), o None."""
        for linea in lineas:
            if not self.es_linea_total(linea):
                continue
            precios = RE_PRECIO.findall(self.reparar_numeros(linea))
            if precios:
                return max(parsear_euros(p) for p in precios)
        return None

    def extraer_productos(self, lineas: list) -> list:
        """Extrae [{nombre, precio, cantidad, importe, observacion}] de las líneas de producto.

        Modelo de 4 columnas (el formato habitual de super/tienda):

            NOMBRE  ·  CANTIDAD  ·  PRECIO UNITARIO  ·  IMPORTE TOTAL
            Salchicha PK-4    1        2,45              2,45
            Estrella Sur      2        0,58              1,16
            Muslos de pollo   1'5      4'50              6,91     <- al peso

        También reconoce el formato "prefijo" ("2 x Pilas AA   3,00").

        Autocorrección con la columna de IMPORTE (si existe):
          - Si importe = N × precio, la cantidad es N (aunque el OCR haya
            perdido el dígito de la cantidad).
          - Si no es un múltiplo exacto, es un producto al peso (o con
            descuento): se guarda el importe real y el precio por kg va a la
            observación.
        Al llegar a la línea del TOTAL se deja de buscar productos (lo que
        viene después es desglose de IVA, pago, etc.).
        """
        productos = []
        for linea_original in lineas:
            if productos and self.es_linea_total(linea_original):
                break
            if self.es_linea_ruido(linea_original):
                continue

            linea = self.reparar_numeros(self.preparar_linea(linea_original))
            precios = list(RE_PRECIO.finditer(linea))
            if not precios:
                continue  # sin precio no es una línea de producto

            producto = self._producto_desde_linea(linea, precios)
            if producto:
                productos.append(producto)
        return productos

    def _producto_desde_linea(self, linea, precios):
        cantidad = 1
        observacion = ""
        importe = None
        alternativas = []
        m_prefijo = RE_CANTIDAD_PREFIJO.match(linea)

        if m_prefijo:
            # Formato prefijo: "N x NOMBRE PRECIO"
            cantidad = int(m_prefijo.group(1))
            resto = linea[m_prefijo.end():]
            precios_resto = list(RE_PRECIO.finditer(resto))
            if not precios_resto:
                return None
            precio = parsear_euros(precios_resto[-1].group(1))
            nombre = resto[:precios_resto[-1].start()]
        else:
            # Formato de columnas: NOMBRE | CANTIDAD/PESO | PRECIO | IMPORTE
            # La columna de PRECIO es la primera cifra decimal de la fila.
            precio_match = precios[0]
            precio = parsear_euros(precio_match.group(1))
            nombre = linea[:precio_match.start()]

            peso = None
            m_peso = RE_PESO.search(nombre)
            m_cantidad = RE_CANTIDAD_COLUMNA.search(nombre)
            if m_peso:
                peso = float(re.sub(SEP_DECIMAL, ".", m_peso.group(1)))
                nombre = nombre[:m_peso.start()]
            elif m_cantidad:
                cantidad = int(m_cantidad.group(1))

            if len(precios) >= 2:
                importe = parsear_euros(precios[-1].group(1))
                cantidad_calculada = round(importe / precio) if precio > 0 else 0
                cuadra = (cantidad_calculada >= 1
                          and abs(cantidad_calculada * precio - importe) < 0.02)
                if cuadra and peso is None:
                    cantidad = cantidad_calculada
                elif peso is None and _un_digito_distinto(precio, importe):
                    # "0'74  4'74": casi seguro un dígito mal leído. Se deja
                    # como al peso, pero con la alternativa "1 × precio" para
                    # que el total decida (ver cuadrar_con_total).
                    alternativas.append({"cantidad": 1, "precio": precio, "importe": precio, "observacion": ""})
                    observacion = f"{formato_euros(precio)} €/kg"
                    cantidad, precio = 1, importe
                    importe = None
                else:
                    # Al peso (o con descuento): el dinero real es el importe.
                    detalle = f"{formato_euros(precio)} €/kg"
                    if peso:
                        detalle = f"{str(peso).replace('.', ',')} kg a {detalle}"
                    observacion = detalle
                    cantidad, precio = 1, importe
                    importe = None
            elif cantidad > CANTIDAD_MAX_SIN_IMPORTE:
                cantidad = 1   # sin importe que lo confirme, no es una cantidad fiable
            elif cantidad > 1:
                # Sin importe que lo confirme, "Bahamas 2  1'24" puede ser 2
                # unidades o parte del nombre: el total decide.
                alternativas.append({"cantidad": 1, "precio": precio, "importe": precio})

            # Si el número no era la cantidad real (p. ej. "Bahamas 2" con
            # importe = 1 × precio), es parte del nombre: se deja en su sitio.
            if m_cantidad and not m_peso and int(m_cantidad.group(1)) == cantidad:
                nombre = nombre[:m_cantidad.start()]
            elif m_cantidad and not m_peso and int(m_cantidad.group(1)) > CANTIDAD_MAX_SIN_IMPORTE:
                nombre = nombre[:m_cantidad.start()]   # basura numérica del OCR

        nombre = re.sub(r"\s{2,}", " ", nombre.strip(" .-~*:·|")).strip()
        if sum(1 for c in nombre if c.isalpha()) < 3:
            return None  # descartar líneas que no tienen un nombre real

        producto = {
            "nombre": nombre.title(),
            "precio": precio,
            "cantidad": cantidad,
            "importe": round(precio * cantidad, 2) if importe is None else importe,
            "observacion": observacion,
        }
        if alternativas:
            producto["_alternativas"] = alternativas
        return producto


def _un_digito_distinto(a: float, b: float) -> bool:
    """¿Se escriben igual salvo un dígito? (0,74 / 4,74 · 1,98 / 7,98)"""
    x, y = formato_euros(a), formato_euros(b)
    return len(x) == len(y) and sum(1 for c, d in zip(x, y) if c != d) == 1
