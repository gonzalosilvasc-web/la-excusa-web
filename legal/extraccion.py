"""Módulo 5: extracción inteligente de datos con OCR/LLM multimodal.

Regla suprema: NUNCA inventar. Si un dato no consta en el documento, el modelo
debe dejarlo vacío o como NO_DETECTADO. Los proveedores se configuran solo por
variables de entorno (nunca credenciales en el código).
"""

from __future__ import annotations

import base64
import json
import os
import re
from pathlib import Path
from typing import Any

from .config import NO_DETECTADO

ESQUEMA_PAGARE = """{
  "Tipo_Instrumento": "Pagare",
  "Numero_Pagare": "",
  "Banco_Acreedor": "",
  "Entidad_Acreedora": "",
  "Nombre_Ejecutivo_Suscriptor": "",
  "Fecha_Suscripcion": "DD/MM/YYYY",
  "Lugar_Suscripcion": "",
  "Deudor_Principal": "",
  "RUT_Deudor_Principal": "",
  "Representante_Deudor": "",
  "Avalistas_Fiadores_Codeudores": [
    {"Nombre": "", "RUT": "", "Calidad": "", "Responde_Por": "",
     "Monto_Responsabilidad": "", "Fuente_Texto": ""}
  ],
  "Monto_Original": "",
  "Saldo_Insoluto": "",
  "Moneda": "CLP/USD/UF",
  "Fecha_Vencimiento": "",
  "Numero_Cuotas": "",
  "Cuotas_Pagadas": "",
  "Cuotas_Impagas": "",
  "Fecha_Mora": "",
  "Tasa_Interes": "",
  "Interes_Penal": "",
  "Clausula_Aceleracion": true,
  "Liberacion_Protesto": true,
  "Domicilio_Competencia": "",
  "Firmas_Autorizadas_Notarialmente": true,
  "Observaciones": ""
}"""

ESQUEMA_MUTUO = """{
  "Tipo_Instrumento": "Mutuo",
  "Numero_Operacion": "",
  "Banco_Acreedor": "",
  "Deudor_Principal": "",
  "RUT_Deudor_Principal": "",
  "Fecha_Escritura": "",
  "Notaria": "",
  "Notario": "",
  "Repertorio": "",
  "Monto_Original": "",
  "Saldo_Insoluto": "",
  "Moneda": "CLP/USD/UF",
  "Cuotas": "",
  "Cuotas_Impagas": "",
  "Fecha_Mora": "",
  "Garantia_Hipotecaria": true,
  "Inmuebles_Hipotecados": [],
  "Domicilio_Competencia": "",
  "Observaciones": ""
}"""

ESQUEMA_CARTOLA = """{
  "Numero_Operacion": "",
  "Fecha_Cartola": "",
  "Saldo_Insoluto": "",
  "Cuotas_Impagas": [],
  "Fecha_Primer_Incumplimiento": "",
  "Monto_Adeudado": "",
  "Moneda": "",
  "Observaciones": ""
}"""

ESQUEMA_MANDATO = """{
  "Nombre_Ejecutivo": "",
  "Entidad_Representada": "",
  "Fecha_Otorgamiento": "DD/MM/YYYY",
  "Fecha_Revocacion": "DD/MM/YYYY o null",
  "Notario_Titular": "",
  "Ciudad_Notaria": "",
  "Repertorio": "",
  "Facultad_Pagare": true,
  "Texto_Facultad_Pagare": "",
  "Confianza_Extraccion": "alta/media/baja",
  "Observaciones_Modelo": ""
}"""

ESQUEMAS: dict[str, str] = {
    "pagare": ESQUEMA_PAGARE,
    "mutuo": ESQUEMA_MUTUO,
    "cartola": ESQUEMA_CARTOLA,
    "mandato": ESQUEMA_MANDATO,
}

_PROMPT_BASE = """Eres un abogado experto en derecho civil, comercial y bancario chileno, especializado en títulos ejecutivos y juicio ejecutivo.

Analiza el documento adjunto ({tipo_doc}) y extrae los datos solicitados.

REGLA CRÍTICA — NO INVENTAR: si un dato NO consta expresamente en el documento, deja el campo como cadena vacía o "{no_detectado}". NUNCA inventes nombres, montos, fechas, tasas, personerías, notarías, repertorios, domicilios, calidades jurídicas ni montos de responsabilidad.

Para cada campo relevante, cuando sea posible, incluye además en el objeto "fuentes" la referencia documental con esta forma:
{{"campo": "<nombre_campo>", "valor": "<valor>", "fuente_documento": "<nombre archivo>", "fuente_pagina": "<n° página>", "fuente_texto": "<cita textual breve>", "confianza": "alta/media/baja"}}

Responde ÚNICAMENTE con un objeto JSON válido, sin texto adicional ni bloques markdown, con exactamente esta estructura (más una clave opcional "fuentes" que sea lista de referencias):

{esquema}"""


def ocr_disponible() -> tuple[bool, str]:
    """(disponible, proveedor) según variables de entorno."""
    provider = os.environ.get("OCR_PROVIDER", "").strip().lower()
    if provider == "openai" and os.environ.get("OPENAI_API_KEY"):
        return True, "openai"
    if provider in ("google", "gemini") and os.environ.get("GOOGLE_API_KEY"):
        return True, "google"
    if not provider:
        if os.environ.get("OPENAI_API_KEY"):
            return True, "openai"
        if os.environ.get("GOOGLE_API_KEY"):
            return True, "google"
    return False, ""


def _parsear_json_llm(texto: str) -> dict[str, Any]:
    """Extrae el objeto JSON de la respuesta del modelo."""
    texto = re.sub(r"^```(?:json)?\s*|\s*```$", "", texto.strip(), flags=re.MULTILINE).strip()
    inicio, fin = texto.find("{"), texto.rfind("}")
    if inicio == -1 or fin <= inicio:
        raise ValueError("La respuesta del modelo no contiene un objeto JSON.")
    return json.loads(texto[inicio : fin + 1])


def _llamar_openai(pdf_bytes: bytes, filename: str, prompt: str) -> str:
    from openai import OpenAI

    client = OpenAI()  # OPENAI_API_KEY desde el entorno
    modelo = os.environ.get("OCR_MODEL", "gpt-4o")
    pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")
    resp = client.chat.completions.create(
        model=modelo,
        temperature=0,
        messages=[{
            "role": "user",
            "content": [
                {"type": "file", "file": {
                    "filename": filename,
                    "file_data": f"data:application/pdf;base64,{pdf_b64}",
                }},
                {"type": "text", "text": prompt},
            ],
        }],
    )
    return resp.choices[0].message.content or ""


def _llamar_google(pdf_bytes: bytes, prompt: str) -> str:
    import google.generativeai as genai

    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    modelo = os.environ.get("OCR_MODEL", "gemini-1.5-pro")
    model = genai.GenerativeModel(modelo)
    resp = model.generate_content(
        [{"mime_type": "application/pdf", "data": pdf_bytes}, prompt],
        generation_config={"temperature": 0},
    )
    return resp.text or ""


def extract_document_data(pdf_path: str, tipo_documento: str) -> dict[str, Any]:
    """Extrae datos estructurados de un documento según su tipo.

    tipo_documento ∈ {"pagare", "mutuo", "cartola", "mandato"}.
    Retorna el dict extraído; incluye "_error" si algo falló.
    """
    disponible, provider = ocr_disponible()
    if not disponible:
        return {"_error": "No hay API key configurada. Puede ingresar los datos manualmente."}

    esquema = ESQUEMAS.get(tipo_documento.lower())
    if esquema is None:
        return {"_error": f"Tipo de documento sin esquema de extracción: {tipo_documento}"}

    ruta = Path(pdf_path)
    try:
        contenido = ruta.read_bytes()
    except (OSError, FileNotFoundError) as exc:
        return {"_error": f"No se pudo leer el documento: {exc}"}

    prompt = _PROMPT_BASE.format(
        tipo_doc=tipo_documento, esquema=esquema, no_detectado=NO_DETECTADO
    )
    try:
        if provider == "openai":
            crudo = _llamar_openai(contenido, ruta.name, prompt)
        else:
            crudo = _llamar_google(contenido, prompt)
    except ImportError:
        return {
            "_error": (
                f"El SDK del proveedor '{provider}' no está instalado. Las "
                "dependencias de IA son opcionales: instálelas con "
                "«pip install -r requirements-ia.txt» o use el modo manual."
            )
        }
    except Exception as exc:  # errores de red/API externas
        return {"_error": f"Error al llamar a la API de {provider}: {exc}"}

    try:
        datos = _parsear_json_llm(crudo)
    except (ValueError, json.JSONDecodeError) as exc:
        return {"_error": f"No se pudo interpretar la respuesta del modelo: {exc}"}

    datos["_fuente_documento"] = ruta.name
    return datos


def extract_mandato_data(pdf_path: str) -> dict[str, Any]:
    """Compatibilidad: extracción específica de mandatos/personerías."""
    return extract_document_data(pdf_path, "mandato")
