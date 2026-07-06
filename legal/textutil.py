"""Utilidades de texto, fechas, montos e identificadores."""

from __future__ import annotations

import re
import unicodedata
import uuid
from typing import Any, Optional

import pandas as pd

from .config import NO_DETECTADO


def normalizar_nombre(nombre: str) -> str:
    """Minúsculas, sin tildes, sin dobles espacios ni símbolos."""
    if not isinstance(nombre, str):
        return ""
    texto = unicodedata.normalize("NFKD", nombre)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = texto.lower()
    texto = re.sub(r"[^a-z0-9ñ\s]", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


def parsear_fecha(valor: Any) -> Optional[pd.Timestamp]:
    """Convierte a Timestamp (dayfirst). None si no es una fecha válida."""
    if valor is None:
        return None
    if isinstance(valor, str):
        v = valor.strip()
        if not v or v.lower() in ("null", "none", "nat", NO_DETECTADO.lower()):
            return None
        valor = v
    try:
        ts = pd.to_datetime(valor, dayfirst=True, errors="coerce")
    except (ValueError, TypeError):
        return None
    if pd.isna(ts):
        return None
    return ts.normalize()


def formatear_fecha(valor: Any) -> str:
    """DD/MM/YYYY o cadena vacía."""
    ts = parsear_fecha(valor)
    return ts.strftime("%d/%m/%Y") if ts is not None else ""


def parsear_monto(valor: Any) -> Optional[float]:
    """Convierte montos con formato chileno ('$1.234.567,89') a float."""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return None
    if isinstance(valor, (int, float)):
        return float(valor)
    texto = str(valor).strip()
    if not texto or texto == NO_DETECTADO:
        return None
    texto = re.sub(r"[^\d,\.\-]", "", texto)
    if not texto:
        return None
    # Formato chileno: punto como separador de miles, coma decimal
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    elif texto.count(".") > 1:
        texto = texto.replace(".", "")
    elif "." in texto:
        entero, _, dec = texto.rpartition(".")
        if len(dec) == 3 and entero:  # 1.234 → mil doscientos...
            texto = entero.replace(".", "") + dec
    try:
        return float(texto)
    except ValueError:
        return None


def formatear_monto(valor: Any, moneda: str = "CLP") -> str:
    """Formatea un monto según la moneda ($ 1.234.567 / US$ / UF)."""
    monto = parsear_monto(valor)
    if monto is None:
        return NO_DETECTADO
    if moneda == "UF":
        cuerpo = f"{monto:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return f"UF {cuerpo}"
    simbolo = "US$" if moneda == "USD" else "$"
    if monto == int(monto):
        cuerpo = f"{int(monto):,}".replace(",", ".")
    else:
        cuerpo = f"{monto:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{simbolo} {cuerpo}"


def sanitizar_nombre_archivo(texto: str) -> str:
    """Nombre de archivo seguro: sin espacios, tildes ni símbolos."""
    texto = unicodedata.normalize("NFKD", str(texto))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"[^A-Za-z0-9_-]+", "_", texto)
    return re.sub(r"_+", "_", texto).strip("_") or "archivo"


def uid(prefijo: str) -> str:
    """ID único corto con prefijo, ej. CASO-1A2B3C4D."""
    return f"{prefijo}-{uuid.uuid4().hex[:8].upper()}"


def valor_o_no_detectado(valor: Any) -> str:
    """Retorna el valor como texto, o NO_DETECTADO si está vacío/nulo."""
    if valor is None:
        return NO_DETECTADO
    if isinstance(valor, float) and pd.isna(valor):
        return NO_DETECTADO
    texto = str(valor).strip()
    if not texto or texto.lower() in ("nan", "none", "null", "nat"):
        return NO_DETECTADO
    return texto


def es_verdadero(valor: Any) -> bool:
    """Interpreta booleanos que pueden venir como texto desde Excel."""
    if isinstance(valor, bool):
        return valor
    return str(valor).strip().lower() in ("true", "1", "si", "sí", "verdadero")
