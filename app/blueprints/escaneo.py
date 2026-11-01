"""
escaneo.py - Alta de ticket desde una foto
==========================================
Flujo:
  1. El usuario sube una foto del ticket.
  2. Se extrae el texto con OCR y se parsea según la tienda.
  2b. Se completa con tu historial (nombre habitual, categoría, favorito):
      ver app/ocr/sugerencias.py.
  3. Se muestra el formulario de "nuevo ticket" YA RELLENADO con lo detectado,
     para que el usuario revise, corrija y guarde. No se guarda nada de forma
     automática: el guardado usa la ruta y la lógica de siempre.

El texto OCR crudo se guarda en instance/ocr_muestras/ para poder depurar y
crear tests cuando un ticket se lea mal.
"""

import os
import uuid
from datetime import datetime

from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, current_app,
)
from werkzeug.utils import secure_filename

from app import repositorio
from app.database import get_db
from app.seguridad import login_requerido
from app.ocr.lector import extraer_texto, OcrNoDisponible
from app.ocr.parsers import parsear_ticket
from app.ocr.sugerencias import completar

bp = Blueprint("escaneo", __name__)

EXTENSIONES_OK = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


@bp.route("/nuevo_ticket/foto", methods=["GET", "POST"])
@login_requerido
def desde_foto():
    if request.method == "GET":
        return render_template("escanear_ticket.html")

    archivo = request.files.get("foto")
    if not archivo or not archivo.filename:
        flash("Selecciona una foto del ticket.", "error")
        return redirect(url_for("escaneo.desde_foto"))

    ext = os.path.splitext(archivo.filename)[1].lower()
    if ext not in EXTENSIONES_OK:
        flash("Formato no admitido. Sube una imagen JPG, PNG o WEBP.", "error")
        return redirect(url_for("escaneo.desde_foto"))

    ruta = _guardar_temporal(archivo, ext)
    try:
        texto = extraer_texto(ruta)
    except OcrNoDisponible:
        flash("El lector de tickets (OCR) no está instalado. Revisa el README "
              "para activarlo.", "error")
        return redirect(url_for("escaneo.desde_foto"))
    except Exception as e:  # noqa: BLE001 - queremos un mensaje amable ante cualquier fallo
        current_app.logger.warning("Fallo de OCR: %s", e)
        flash("No se pudo leer la imagen. Prueba con otra foto más nítida.", "error")
        return redirect(url_for("escaneo.desde_foto"))
    finally:
        _borrar(ruta)

    _guardar_muestra(texto)
    db = get_db()
    datos = completar(db, parsear_ticket(texto), texto)

    if not datos["productos"]:
        flash("No se detectaron productos en la foto. Puedes rellenarlos a mano.", "warning")
    else:
        suma = round(sum(p["importe"] for p in datos["productos"]), 2)
        datos["suma"] = suma
        datos["cuadra"] = datos["total"] is None or abs(suma - datos["total"]) < 0.02

    return render_template(
        "nuevo_ticket.html",
        categorias=repositorio.categorias_existentes(db),
        prefill=datos,
        texto_ocr=texto,
    )


# ----------------------------------------------------------------------
# Auxiliares
# ----------------------------------------------------------------------

def _guardar_temporal(archivo, ext) -> str:
    carpeta = os.path.join(current_app.instance_path, "uploads")
    os.makedirs(carpeta, exist_ok=True)
    ruta = os.path.join(carpeta, secure_filename(f"{uuid.uuid4().hex}{ext}"))
    archivo.save(ruta)
    return ruta


def _borrar(ruta) -> None:
    try:
        os.remove(ruta)
    except OSError:
        pass


def _guardar_muestra(texto) -> None:
    """Guarda el texto OCR crudo para depurar y crear tests más adelante."""
    carpeta = os.path.join(current_app.instance_path, "ocr_muestras")
    os.makedirs(carpeta, exist_ok=True)
    nombre = datetime.now().strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:6] + ".txt"
    with open(os.path.join(carpeta, nombre), "w", encoding="utf-8") as f:
        f.write(texto)
