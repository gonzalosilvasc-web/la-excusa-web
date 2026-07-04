"""
Sistema de Gestión de Personerías / Mandatos — Banco Santander & GRC
====================================================================
Aplicación interna para la validación, asignación, búsqueda y almacenamiento
indexado de personerías/mandatos destinados a juicios ejecutivos chilenos.

Ejecución local:
    streamlit run app.py

ADVERTENCIA LEGAL: Este sistema asiste la búsqueda y validación de
personerías, pero NO reemplaza la revisión profesional del mandato
original ni del título ejecutivo por parte del abogado responsable.
"""

from __future__ import annotations

import base64
import json
import os
import re
import shutil
import unicodedata
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

import pandas as pd
import streamlit as st
from rapidfuzz import fuzz

# ---------------------------------------------------------------------------
# Configuración y constantes
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
DATABASE_DIR = BASE_DIR / "database"
PDF_STORAGE_DIR = DATABASE_DIR / "pdf_storage"
BACKUPS_DIR = DATABASE_DIR / "backups"
TMP_DIR = DATABASE_DIR / "tmp"
MANDATOS_XLSX = DATABASE_DIR / "mandatos.xlsx"
AUDIT_LOG_XLSX = DATABASE_DIR / "audit_log.xlsx"

ENTIDADES = ["Banco Santander", "GRC"]

MANDATOS_COLUMNS = [
    "ID_Mandato",
    "Nombre_Ejecutivo",
    "Nombre_Ejecutivo_Normalizado",
    "Entidad_Representada",
    "Fecha_Otorgamiento",
    "Fecha_Revocacion",
    "Notario_Titular",
    "Ciudad_Notaria",
    "Repertorio",
    "Facultad_Pagare",
    "PDF_Path",
    "Fecha_Carga",
    "Usuario_Carga",
    "Observaciones",
]

AUDIT_COLUMNS = [
    "Fecha_Hora",
    "Accion",
    "Usuario",
    "ID_Mandato",
    "Entidad_Representada",
    "Nombre_Ejecutivo",
    "Resultado",
    "Observaciones",
]

FUZZY_THRESHOLD = 85

TEXTO_PERSONERIA = (
    "La personería de don/doña {nombre} para actuar en representación de "
    "{entidad}, consta en la escritura pública de fecha {fecha_otorgamiento}, "
    "otorgada en la Notaría de {ciudad} de don/doña {notario}, bajo el "
    "repertorio N° {repertorio}, copia de la cual se acompaña en un otrosí "
    "de esta presentación."
)

MSG_REVOCACION_MISMO_DIA = (
    "Atención: El mandato fue revocado el mismo día de la suscripción. "
    "Verifique horas de los instrumentos antes de usar esta personería."
)

MSG_SIN_FACULTAD_PAGARE = (
    "El mandato escaneado no contiene facultad expresa para suscribir pagarés "
    "o títulos de crédito. No se recomienda usar esta personería para juicio "
    "ejecutivo fundado en pagaré."
)

OCR_PROMPT = """Eres un abogado experto en derecho civil y comercial chileno, especializado en análisis de escrituras públicas de mandato y personerías bancarias.

Analiza el documento PDF adjunto (una escritura pública de mandato/personería) y extrae los datos solicitados.

REQUISITO LEGAL CRÍTICO: Debes evaluar expresamente si el mandato contiene facultad para suscribir pagarés, títulos de crédito, reconocer deudas, aceptar letras de cambio, suscribir instrumentos mercantiles o facultades equivalentes. Retorna "Facultad_Pagare" como booleano true/false y transcribe textualmente la cláusula pertinente en "Texto_Facultad_Pagare".

Responde ÚNICAMENTE con un objeto JSON válido, sin texto adicional, sin markdown y sin bloques de código, con exactamente esta estructura:

{
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
}

Reglas:
- "Entidad_Representada" debe ser "Banco Santander" o "GRC" si corresponde a alguna de ellas; de lo contrario, el nombre literal de la entidad.
- Si un dato no aparece en el documento, deja el campo como cadena vacía (o null para Fecha_Revocacion).
- "Confianza_Extraccion" refleja tu certeza global: "alta", "media" o "baja".
- En "Observaciones_Modelo" anota cualquier ambigüedad, ilegibilidad o riesgo detectado."""


# ---------------------------------------------------------------------------
# Inicialización de estructura de archivos
# ---------------------------------------------------------------------------

def ensure_structure() -> None:
    """Crea carpetas y archivos Excel base si no existen."""
    for folder in (DATABASE_DIR, PDF_STORAGE_DIR, BACKUPS_DIR, TMP_DIR):
        folder.mkdir(parents=True, exist_ok=True)
    if not MANDATOS_XLSX.exists():
        _write_excel_safe(pd.DataFrame(columns=MANDATOS_COLUMNS), MANDATOS_XLSX)
    if not AUDIT_LOG_XLSX.exists():
        _write_excel_safe(pd.DataFrame(columns=AUDIT_COLUMNS), AUDIT_LOG_XLSX)


# ---------------------------------------------------------------------------
# Utilidades de normalización y fechas
# ---------------------------------------------------------------------------

def normalizar_nombre(nombre: str) -> str:
    """Normaliza un nombre: minúsculas, sin tildes, sin dobles espacios ni símbolos."""
    if not isinstance(nombre, str):
        return ""
    texto = unicodedata.normalize("NFKD", nombre)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = texto.lower()
    texto = re.sub(r"[^a-z0-9ñ\s]", " ", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def parsear_fecha(valor: Any) -> Optional[pd.Timestamp]:
    """Convierte un valor arbitrario a Timestamp (dayfirst). Retorna None si no es válido."""
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        return None
    try:
        ts = pd.to_datetime(valor, dayfirst=True, errors="coerce")
    except (ValueError, TypeError):
        return None
    if pd.isna(ts):
        return None
    return ts.normalize()


def formatear_fecha(valor: Any) -> str:
    """Formatea una fecha como DD/MM/YYYY, o cadena vacía si es nula."""
    ts = parsear_fecha(valor)
    return ts.strftime("%d/%m/%Y") if ts is not None else ""


def sanitizar_nombre_archivo(texto: str) -> str:
    """Elimina espacios, tildes y símbolos incompatibles para nombres de archivo."""
    texto = unicodedata.normalize("NFKD", str(texto))
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"[^A-Za-z0-9_-]+", "_", texto)
    return re.sub(r"_+", "_", texto).strip("_")


def generar_id_mandato() -> str:
    """Genera un ID único corto para el mandato."""
    return f"MND-{uuid.uuid4().hex[:8].upper()}"


# ---------------------------------------------------------------------------
# Persistencia segura en Excel
# ---------------------------------------------------------------------------

def _write_excel_safe(df: pd.DataFrame, destino: Path) -> None:
    """Escritura atómica: escribe en archivo temporal, valida y reemplaza el original.

    Lanza PermissionError si el archivo está abierto/bloqueado.
    """
    destino.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = destino.with_name(f".{destino.stem}_{uuid.uuid4().hex[:6]}.tmp.xlsx")
    try:
        df.to_excel(tmp_path, index=False, engine="openpyxl")
        # Validar que el archivo temporal quedó bien escrito antes de reemplazar
        verificacion = pd.read_excel(tmp_path, engine="openpyxl")
        if len(verificacion) != len(df):
            raise IOError(
                f"Validación fallida al escribir {destino.name}: "
                f"se esperaban {len(df)} filas y se leyeron {len(verificacion)}."
            )
        os.replace(tmp_path, destino)
    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass


def crear_backup(archivo: Path) -> Optional[Path]:
    """Copia el archivo a database/backups/ con timestamp. Retorna la ruta del backup."""
    if not archivo.exists():
        return None
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    destino = BACKUPS_DIR / f"{archivo.stem}_backup_{timestamp}{archivo.suffix}"
    try:
        shutil.copy2(archivo, destino)
        return destino
    except OSError as exc:
        st.warning(f"No se pudo crear el respaldo de {archivo.name}: {exc}")
        return None


@st.cache_data(show_spinner=False)
def _leer_excel_cacheado(ruta: str, mtime: float) -> pd.DataFrame:
    """Lectura cacheada por ruta + fecha de modificación."""
    return pd.read_excel(ruta, engine="openpyxl", dtype={"Repertorio": str})


def cargar_mandatos() -> pd.DataFrame:
    """Carga mandatos.xlsx con tipos normalizados. Retorna DataFrame vacío si falla."""
    try:
        if not MANDATOS_XLSX.exists():
            return pd.DataFrame(columns=MANDATOS_COLUMNS)
        df = _leer_excel_cacheado(str(MANDATOS_XLSX), MANDATOS_XLSX.stat().st_mtime).copy()
    except PermissionError:
        st.error(
            "No se puede leer `mandatos.xlsx` porque está abierto en otro programa "
            "(probablemente Excel). Cierre el archivo e intente nuevamente."
        )
        return pd.DataFrame(columns=MANDATOS_COLUMNS)
    except (OSError, ValueError) as exc:
        st.error(f"Error al leer la base de mandatos: {exc}")
        return pd.DataFrame(columns=MANDATOS_COLUMNS)

    for col in MANDATOS_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA
    df["Fecha_Otorgamiento"] = pd.to_datetime(
        df["Fecha_Otorgamiento"], dayfirst=True, errors="coerce"
    )
    df["Fecha_Revocacion"] = pd.to_datetime(
        df["Fecha_Revocacion"], dayfirst=True, errors="coerce"
    )
    return df[MANDATOS_COLUMNS]


def guardar_mandatos(df: pd.DataFrame) -> bool:
    """Respalda y guarda mandatos.xlsx de forma segura. Retorna True si tuvo éxito."""
    try:
        crear_backup(MANDATOS_XLSX)
        _write_excel_safe(df, MANDATOS_XLSX)
        _leer_excel_cacheado.clear()
        return True
    except PermissionError:
        st.error(
            "No se pudo guardar `mandatos.xlsx` porque está abierto en otro programa "
            "(probablemente Excel). Cierre el archivo y vuelva a intentar."
        )
        return False
    except (OSError, IOError, ValueError) as exc:
        st.error(f"Error al guardar la base de mandatos: {exc}")
        return False


def registrar_auditoria(
    accion: str,
    usuario: str,
    id_mandato: str,
    entidad: str,
    nombre_ejecutivo: str,
    resultado: str,
    observaciones: str = "",
) -> None:
    """Registra una acción en database/audit_log.xlsx (con respaldo previo)."""
    fila = {
        "Fecha_Hora": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "Accion": accion,
        "Usuario": usuario or "anonimo",
        "ID_Mandato": id_mandato,
        "Entidad_Representada": entidad,
        "Nombre_Ejecutivo": nombre_ejecutivo,
        "Resultado": resultado,
        "Observaciones": observaciones,
    }
    try:
        if AUDIT_LOG_XLSX.exists():
            log = pd.read_excel(AUDIT_LOG_XLSX, engine="openpyxl")
        else:
            log = pd.DataFrame(columns=AUDIT_COLUMNS)
        log = pd.concat([log, pd.DataFrame([fila])], ignore_index=True)
        crear_backup(AUDIT_LOG_XLSX)
        _write_excel_safe(log, AUDIT_LOG_XLSX)
    except PermissionError:
        st.warning(
            "No se pudo escribir el registro de auditoría porque `audit_log.xlsx` "
            "está abierto en otro programa. Ciérrelo para no perder trazabilidad."
        )
    except (OSError, IOError, ValueError) as exc:
        st.warning(f"No se pudo registrar la auditoría: {exc}")


# ---------------------------------------------------------------------------
# Lógica de búsqueda de personerías (Tab 1)
# ---------------------------------------------------------------------------

def buscar_personeria(
    df: pd.DataFrame,
    nombre_input: str,
    entidad_input: str,
    fecha_pagare: date,
) -> dict[str, Any]:
    """Busca la personería vigente aplicando fuzzy matching y reglas de vigencia.

    Retorna un dict con:
        - "vigente": Series del mandato más reciente vigente, o None.
        - "mismo_dia": DataFrame de mandatos revocados el mismo día del pagaré.
    """
    resultado: dict[str, Any] = {"vigente": None, "mismo_dia": pd.DataFrame()}
    if df.empty:
        return resultado

    fecha_pagare_ts = pd.Timestamp(fecha_pagare)
    nombre_norm = normalizar_nombre(nombre_input)
    if not nombre_norm:
        return resultado

    df = df.copy()
    df["_score"] = df["Nombre_Ejecutivo_Normalizado"].apply(
        lambda x: fuzz.token_set_ratio(nombre_norm, normalizar_nombre(str(x)))
        if pd.notna(x)
        else 0
    )

    candidatos = df[
        (df["_score"] > FUZZY_THRESHOLD)
        & (df["Entidad_Representada"] == entidad_input)
        & (df["Fecha_Otorgamiento"].notna())
        & (df["Fecha_Otorgamiento"] <= fecha_pagare_ts)
    ]
    if candidatos.empty:
        return resultado

    # Caso borde: revocación el mismo día de la suscripción del pagaré
    mismo_dia = candidatos[candidatos["Fecha_Revocacion"] == fecha_pagare_ts]
    resultado["mismo_dia"] = mismo_dia

    vigentes = candidatos[
        candidatos["Fecha_Revocacion"].isna()
        | (candidatos["Fecha_Revocacion"] > fecha_pagare_ts)
    ]
    if not vigentes.empty:
        vigentes = vigentes.sort_values("Fecha_Otorgamiento", ascending=False)
        resultado["vigente"] = vigentes.iloc[0]
    return resultado


# ---------------------------------------------------------------------------
# Extracción OCR multimodal (Tab 2)
# ---------------------------------------------------------------------------

def ocr_disponible() -> tuple[bool, str]:
    """Indica si hay un proveedor OCR configurado y cuál."""
    provider = os.environ.get("OCR_PROVIDER", "").strip().lower()
    if provider == "openai" and os.environ.get("OPENAI_API_KEY"):
        return True, "openai"
    if provider in ("google", "gemini") and os.environ.get("GOOGLE_API_KEY"):
        return True, "google"
    if not provider:
        # Autodetección por API key disponible
        if os.environ.get("OPENAI_API_KEY"):
            return True, "openai"
        if os.environ.get("GOOGLE_API_KEY"):
            return True, "google"
    return False, ""


def _parsear_json_llm(texto: str) -> dict[str, Any]:
    """Extrae y parsea el objeto JSON de la respuesta del LLM."""
    texto = texto.strip()
    # Remover posibles bloques de código markdown
    texto = re.sub(r"^```(?:json)?\s*|\s*```$", "", texto, flags=re.MULTILINE).strip()
    inicio, fin = texto.find("{"), texto.rfind("}")
    if inicio == -1 or fin == -1 or fin <= inicio:
        raise ValueError("La respuesta del modelo no contiene un objeto JSON.")
    return json.loads(texto[inicio : fin + 1])


def _extraer_con_openai(pdf_bytes: bytes, filename: str) -> str:
    """Envía el PDF a un modelo multimodal de OpenAI y retorna la respuesta cruda."""
    from openai import OpenAI

    client = OpenAI()  # Lee OPENAI_API_KEY del entorno
    modelo = os.environ.get("OCR_MODEL", "gpt-4o")
    pdf_b64 = base64.b64encode(pdf_bytes).decode("utf-8")
    respuesta = client.chat.completions.create(
        model=modelo,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "file",
                        "file": {
                            "filename": filename,
                            "file_data": f"data:application/pdf;base64,{pdf_b64}",
                        },
                    },
                    {"type": "text", "text": OCR_PROMPT},
                ],
            }
        ],
        temperature=0,
    )
    return respuesta.choices[0].message.content or ""


def _extraer_con_google(pdf_bytes: bytes) -> str:
    """Envía el PDF a un modelo multimodal de Google (Gemini) y retorna la respuesta cruda."""
    import google.generativeai as genai

    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
    modelo = os.environ.get("OCR_MODEL", "gemini-1.5-pro")
    model = genai.GenerativeModel(modelo)
    respuesta = model.generate_content(
        [{"mime_type": "application/pdf", "data": pdf_bytes}, OCR_PROMPT],
        generation_config={"temperature": 0},
    )
    return respuesta.text or ""


def extract_mandato_data(pdf_path: str) -> dict[str, Any]:
    """Extrae los datos del mandato desde un PDF usando un LLM multimodal.

    El proveedor se configura vía variables de entorno (OCR_PROVIDER,
    OPENAI_API_KEY, GOOGLE_API_KEY, OCR_MODEL). Retorna un dict con los campos
    del esquema de extracción; incluye la clave "_error" si algo falló.
    """
    disponible, provider = ocr_disponible()
    if not disponible:
        return {"_error": "No hay proveedor OCR configurado (falta API key)."}

    ruta = Path(pdf_path)
    try:
        pdf_bytes = ruta.read_bytes()
    except (OSError, FileNotFoundError) as exc:
        return {"_error": f"No se pudo leer el PDF: {exc}"}

    try:
        if provider == "openai":
            crudo = _extraer_con_openai(pdf_bytes, ruta.name)
        else:
            crudo = _extraer_con_google(pdf_bytes)
    except ImportError as exc:
        return {
            "_error": f"Falta instalar el SDK del proveedor '{provider}': {exc}. "
            "Revise requirements.txt."
        }
    except Exception as exc:  # Errores de red/API del proveedor externo
        return {"_error": f"Error al llamar a la API de {provider}: {exc}"}

    try:
        datos = _parsear_json_llm(crudo)
    except (ValueError, json.JSONDecodeError) as exc:
        return {"_error": f"No se pudo interpretar la respuesta del modelo: {exc}"}

    datos.setdefault("Confianza_Extraccion", "baja")
    datos.setdefault("Observaciones_Modelo", "")
    return datos


# ---------------------------------------------------------------------------
# Duplicados y datos de ejemplo
# ---------------------------------------------------------------------------

def detectar_duplicados(
    df: pd.DataFrame,
    entidad: str,
    nombre_normalizado: str,
    fecha_otorgamiento: Optional[pd.Timestamp],
    repertorio: str,
) -> pd.DataFrame:
    """Busca posibles duplicados por entidad + nombre normalizado + fecha + repertorio."""
    if df.empty:
        return pd.DataFrame()
    rep_norm = str(repertorio).strip().lower()
    mask = (
        (df["Entidad_Representada"] == entidad)
        & (df["Nombre_Ejecutivo_Normalizado"].fillna("") == nombre_normalizado)
        & (df["Repertorio"].fillna("").astype(str).str.strip().str.lower() == rep_norm)
    )
    if fecha_otorgamiento is not None:
        mask &= df["Fecha_Otorgamiento"] == fecha_otorgamiento
    return df[mask]


def cargar_datos_ejemplo() -> bool:
    """Inserta mandatos de ejemplo en la base (solo para pruebas)."""
    ejemplos = [
        {
            "Nombre_Ejecutivo": "María Fernanda Soto Pérez",
            "Entidad_Representada": "Banco Santander",
            "Fecha_Otorgamiento": "15/03/2022",
            "Fecha_Revocacion": None,
            "Notario_Titular": "Juan Ricardo San Martín Urrejola",
            "Ciudad_Notaria": "Santiago",
            "Repertorio": "12345-2022",
            "Facultad_Pagare": True,
            "Observaciones": "Dato de ejemplo — mandato vigente.",
        },
        {
            "Nombre_Ejecutivo": "Pedro Antonio Rojas Díaz",
            "Entidad_Representada": "Banco Santander",
            "Fecha_Otorgamiento": "10/01/2020",
            "Fecha_Revocacion": "20/06/2023",
            "Notario_Titular": "Iván Torrealba Acevedo",
            "Ciudad_Notaria": "Santiago",
            "Repertorio": "9876-2020",
            "Facultad_Pagare": True,
            "Observaciones": "Dato de ejemplo — mandato revocado en 2023.",
        },
        {
            "Nombre_Ejecutivo": "Carolina Andrea Muñoz Lagos",
            "Entidad_Representada": "GRC",
            "Fecha_Otorgamiento": "05/08/2021",
            "Fecha_Revocacion": None,
            "Notario_Titular": "Patricio Raby Benavente",
            "Ciudad_Notaria": "Valparaíso",
            "Repertorio": "4455-2021",
            "Facultad_Pagare": True,
            "Observaciones": "Dato de ejemplo — mandato vigente GRC.",
        },
    ]
    df = cargar_mandatos()
    filas = []
    for e in ejemplos:
        filas.append(
            {
                "ID_Mandato": generar_id_mandato(),
                "Nombre_Ejecutivo": e["Nombre_Ejecutivo"],
                "Nombre_Ejecutivo_Normalizado": normalizar_nombre(e["Nombre_Ejecutivo"]),
                "Entidad_Representada": e["Entidad_Representada"],
                "Fecha_Otorgamiento": parsear_fecha(e["Fecha_Otorgamiento"]),
                "Fecha_Revocacion": parsear_fecha(e["Fecha_Revocacion"]),
                "Notario_Titular": e["Notario_Titular"],
                "Ciudad_Notaria": e["Ciudad_Notaria"],
                "Repertorio": e["Repertorio"],
                "Facultad_Pagare": e["Facultad_Pagare"],
                "PDF_Path": "",
                "Fecha_Carga": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                "Usuario_Carga": "sistema_ejemplo",
                "Observaciones": e["Observaciones"],
            }
        )
    df = pd.concat([df, pd.DataFrame(filas)], ignore_index=True)
    return guardar_mandatos(df)


# ---------------------------------------------------------------------------
# UI — Tab 1: Consulta de personerías / litigación
# ---------------------------------------------------------------------------

def render_tab_consulta() -> None:
    st.subheader("🔎 Consulta de personerías para litigación")

    col1, col2, col3 = st.columns(3)
    with col1:
        fecha_pagare = st.date_input(
            "Fecha de suscripción del pagaré",
            value=date.today(),
            format="DD/MM/YYYY",
        )
    with col2:
        nombre_input = st.text_input(
            "Nombre del ejecutivo",
            placeholder="Ej: María Fernanda Soto Pérez",
        )
    with col3:
        entidad_input = st.selectbox("Entidad", ENTIDADES)

    if not st.button("Buscar personería", type="primary"):
        return
    if not nombre_input.strip():
        st.error("Debe ingresar el nombre del ejecutivo para buscar.")
        return

    df = cargar_mandatos()
    resultado = buscar_personeria(df, nombre_input, entidad_input, fecha_pagare)

    # Caso borde: revocación el mismo día
    if not resultado["mismo_dia"].empty:
        st.warning(MSG_REVOCACION_MISMO_DIA)
        st.dataframe(
            _preparar_vista(resultado["mismo_dia"]),
            use_container_width=True,
            hide_index=True,
        )

    mandato = resultado["vigente"]
    if mandato is None:
        st.error(
            "No se encontró personería vigente para esos parámetros "
            f"(ejecutivo: “{nombre_input}”, entidad: {entidad_input}, "
            f"fecha pagaré: {fecha_pagare.strftime('%d/%m/%Y')})."
        )
        return

    st.success(
        f"Personería vigente encontrada: **{mandato['Nombre_Ejecutivo']}** — "
        f"{mandato['Entidad_Representada']} | Otorgada el "
        f"{formatear_fecha(mandato['Fecha_Otorgamiento'])} | "
        f"Repertorio N° {mandato['Repertorio']} | ID {mandato['ID_Mandato']}"
    )

    st.dataframe(
        _preparar_vista(pd.DataFrame([mandato])),
        use_container_width=True,
        hide_index=True,
    )

    if not _es_verdadero(mandato.get("Facultad_Pagare")):
        st.error(
            "Este mandato está registrado SIN facultad expresa para suscribir "
            "pagarés. Revise el instrumento original antes de usarlo en un "
            "juicio ejecutivo fundado en pagaré."
        )

    st.markdown("**Texto legal para la demanda:**")
    st.code(
        TEXTO_PERSONERIA.format(
            nombre=mandato["Nombre_Ejecutivo"],
            entidad=mandato["Entidad_Representada"],
            fecha_otorgamiento=formatear_fecha(mandato["Fecha_Otorgamiento"]),
            ciudad=mandato["Ciudad_Notaria"],
            notario=mandato["Notario_Titular"],
            repertorio=mandato["Repertorio"],
        ),
        language=None,
    )

    pdf_path = str(mandato.get("PDF_Path") or "").strip()
    if pdf_path and pdf_path.lower() != "nan":
        ruta_pdf = BASE_DIR / pdf_path if not Path(pdf_path).is_absolute() else Path(pdf_path)
        if ruta_pdf.exists():
            try:
                st.download_button(
                    "⬇️ Descargar PDF del mandato",
                    data=ruta_pdf.read_bytes(),
                    file_name=ruta_pdf.name,
                    mime="application/pdf",
                )
            except OSError as exc:
                st.warning(f"No se pudo leer el PDF asociado: {exc}")
        else:
            st.info("El mandato tiene una ruta de PDF registrada, pero el archivo no existe.")
    else:
        st.info("Este mandato no tiene un PDF asociado en el sistema.")

    st.warning(
        "El texto de personería generado debe ser revisado contra el título "
        "original antes de ser incorporado a una demanda."
    )


def _preparar_vista(df: pd.DataFrame) -> pd.DataFrame:
    """Prepara un DataFrame legible para mostrar en pantalla."""
    vista = df[
        [
            "ID_Mandato",
            "Nombre_Ejecutivo",
            "Entidad_Representada",
            "Fecha_Otorgamiento",
            "Fecha_Revocacion",
            "Notario_Titular",
            "Ciudad_Notaria",
            "Repertorio",
            "Facultad_Pagare",
            "Observaciones",
        ]
    ].copy()
    vista["Fecha_Otorgamiento"] = vista["Fecha_Otorgamiento"].apply(formatear_fecha)
    vista["Fecha_Revocacion"] = vista["Fecha_Revocacion"].apply(
        lambda v: formatear_fecha(v) or "Vigente"
    )
    return vista


def _es_verdadero(valor: Any) -> bool:
    """Interpreta valores booleanos que pueden venir como texto desde Excel."""
    if isinstance(valor, bool):
        return valor
    return str(valor).strip().lower() in ("true", "1", "si", "sí", "verdadero")


# ---------------------------------------------------------------------------
# UI — Tab 2: Carga e indexación de mandatos
# ---------------------------------------------------------------------------

def render_tab_carga() -> None:
    st.subheader("📥 Carga e indexación de mandatos (administración)")

    disponible, provider = ocr_disponible()
    if disponible:
        st.info(f"Extracción OCR multimodal habilitada (proveedor: **{provider}**).")
    else:
        st.info(
            "No hay API key de OCR configurada (OPENAI_API_KEY / GOOGLE_API_KEY). "
            "Puede cargar los datos del mandato manualmente."
        )

    archivo = st.file_uploader("Escritura de mandato (PDF)", type=["pdf"])
    col_u, col_o = st.columns(2)
    with col_u:
        usuario_carga = st.text_input("Usuario que carga (opcional)")
    with col_o:
        observaciones_carga = st.text_input("Observaciones (opcional)")

    if archivo is None:
        st.caption("Suba un PDF para comenzar. Sin PDF también puede registrar datos manuales abajo.")
    else:
        # Guardar el PDF subido en un archivo temporal para procesarlo
        if st.session_state.get("_tmp_pdf_name") != archivo.name:
            tmp_pdf = TMP_DIR / f"upload_{uuid.uuid4().hex[:8]}.pdf"
            try:
                tmp_pdf.write_bytes(archivo.getvalue())
                st.session_state["_tmp_pdf_path"] = str(tmp_pdf)
                st.session_state["_tmp_pdf_name"] = archivo.name
                st.session_state.pop("extraccion", None)
            except OSError as exc:
                st.error(f"No se pudo guardar temporalmente el PDF: {exc}")
                return

        if disponible and st.button("🤖 Extraer datos con OCR multimodal", type="primary"):
            with st.spinner("Analizando la escritura con el modelo multimodal…"):
                datos = extract_mandato_data(st.session_state["_tmp_pdf_path"])
            if "_error" in datos:
                st.error(datos["_error"])
                registrar_auditoria(
                    accion="OCR_FALLIDO",
                    usuario=usuario_carga,
                    id_mandato="",
                    entidad="",
                    nombre_ejecutivo="",
                    resultado="ERROR",
                    observaciones=datos["_error"],
                )
            else:
                st.session_state["extraccion"] = datos

    extraccion: dict[str, Any] = st.session_state.get("extraccion", {})

    if extraccion:
        confianza = str(extraccion.get("Confianza_Extraccion", "baja")).lower()
        emoji = {"alta": "🟢", "media": "🟡", "baja": "🔴"}.get(confianza, "🔴")
        st.markdown(f"**Confianza de extracción:** {emoji} {confianza.upper()}")
        if extraccion.get("Observaciones_Modelo"):
            st.caption(f"Observaciones del modelo: {extraccion['Observaciones_Modelo']}")

        facultad = bool(extraccion.get("Facultad_Pagare"))
        if not facultad:
            st.error(MSG_SIN_FACULTAD_PAGARE)
            registrar_auditoria(
                accion="INDEXACION_BLOQUEADA_SIN_FACULTAD",
                usuario=usuario_carga,
                id_mandato="",
                entidad=str(extraccion.get("Entidad_Representada", "")),
                nombre_ejecutivo=str(extraccion.get("Nombre_Ejecutivo", "")),
                resultado="BLOQUEADO",
                observaciones="OCR detectó ausencia de facultad para suscribir pagarés.",
            )
        else:
            st.success("El modelo detectó facultad para suscribir pagarés. Revise el texto extraído:")
            st.code(extraccion.get("Texto_Facultad_Pagare", "") or "(sin texto extraído)", language=None)

    st.divider()
    st.markdown("### Revisión y validación de datos")
    st.caption("Corrija los campos según el mandato original antes de guardar.")

    entidad_default = str(extraccion.get("Entidad_Representada", "")).strip()
    entidad_idx = ENTIDADES.index(entidad_default) if entidad_default in ENTIDADES else 0

    with st.form("form_mandato"):
        nombre = st.text_input(
            "Nombre del ejecutivo *", value=str(extraccion.get("Nombre_Ejecutivo", "") or "")
        )
        entidad = st.selectbox("Entidad representada *", ENTIDADES, index=entidad_idx)
        c1, c2 = st.columns(2)
        with c1:
            fecha_otorg_txt = st.text_input(
                "Fecha de otorgamiento (DD/MM/YYYY) *",
                value=str(extraccion.get("Fecha_Otorgamiento", "") or ""),
            )
        with c2:
            fecha_revoc_txt = st.text_input(
                "Fecha de revocación (DD/MM/YYYY, vacío si vigente)",
                value=str(extraccion.get("Fecha_Revocacion") or "").replace("null", ""),
            )
        c3, c4 = st.columns(2)
        with c3:
            notario = st.text_input(
                "Notario titular *", value=str(extraccion.get("Notario_Titular", "") or "")
            )
        with c4:
            ciudad = st.text_input(
                "Ciudad de la notaría *", value=str(extraccion.get("Ciudad_Notaria", "") or "")
            )
        repertorio = st.text_input(
            "Repertorio N° *", value=str(extraccion.get("Repertorio", "") or "")
        )
        facultad_pagare = st.checkbox(
            "El mandato contiene facultad expresa para suscribir pagarés / títulos de crédito",
            value=bool(extraccion.get("Facultad_Pagare", False)),
        )
        confirmado = st.checkbox(
            "Confirmo que revisé el mandato original y validé que los datos extraídos son correctos."
        )
        enviado = st.form_submit_button("💾 Guardar mandato", type="primary")

    if enviado:
        _procesar_guardado(
            nombre=nombre,
            entidad=entidad,
            fecha_otorg_txt=fecha_otorg_txt,
            fecha_revoc_txt=fecha_revoc_txt,
            notario=notario,
            ciudad=ciudad,
            repertorio=repertorio,
            facultad_pagare=facultad_pagare,
            confirmado=confirmado,
            usuario_carga=usuario_carga,
            observaciones_carga=observaciones_carga,
        )

    # Confirmación diferida de duplicados
    pendiente = st.session_state.get("pendiente_duplicado")
    if pendiente:
        st.warning(
            "⚠️ Se detectó un posible duplicado (misma entidad, ejecutivo, fecha de "
            "otorgamiento y repertorio). Revise los registros existentes:"
        )
        st.dataframe(
            _preparar_vista(pd.DataFrame(pendiente["duplicados"])),
            use_container_width=True,
            hide_index=True,
        )
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("✅ Guardar de todos modos", type="primary"):
                _guardar_registro(pendiente["registro"])
                st.session_state.pop("pendiente_duplicado", None)
        with col_b:
            if st.button("❌ Cancelar guardado"):
                registrar_auditoria(
                    accion="CARGA_CANCELADA_DUPLICADO",
                    usuario=pendiente["registro"]["Usuario_Carga"],
                    id_mandato="",
                    entidad=pendiente["registro"]["Entidad_Representada"],
                    nombre_ejecutivo=pendiente["registro"]["Nombre_Ejecutivo"],
                    resultado="CANCELADO",
                    observaciones="El usuario canceló tras la advertencia de duplicado.",
                )
                st.session_state.pop("pendiente_duplicado", None)
                st.info("Guardado cancelado.")


def _procesar_guardado(
    nombre: str,
    entidad: str,
    fecha_otorg_txt: str,
    fecha_revoc_txt: str,
    notario: str,
    ciudad: str,
    repertorio: str,
    facultad_pagare: bool,
    confirmado: bool,
    usuario_carga: str,
    observaciones_carga: str,
) -> None:
    """Valida el formulario y guarda (o deja pendiente por duplicado)."""
    if not confirmado:
        st.error(
            "Debe marcar la casilla de confirmación de revisión del mandato "
            "original antes de guardar."
        )
        return

    faltantes = [
        etiqueta
        for etiqueta, valor in [
            ("Nombre del ejecutivo", nombre),
            ("Fecha de otorgamiento", fecha_otorg_txt),
            ("Notario titular", notario),
            ("Ciudad de la notaría", ciudad),
            ("Repertorio", repertorio),
        ]
        if not str(valor).strip()
    ]
    if faltantes:
        st.error(f"Complete los campos obligatorios: {', '.join(faltantes)}.")
        return

    fecha_otorg = parsear_fecha(fecha_otorg_txt)
    if fecha_otorg is None:
        st.error("La fecha de otorgamiento no es válida. Use el formato DD/MM/YYYY.")
        return
    fecha_revoc = parsear_fecha(fecha_revoc_txt)
    if fecha_revoc_txt.strip() and fecha_revoc is None:
        st.error("La fecha de revocación no es válida. Use el formato DD/MM/YYYY o déjela vacía.")
        return
    if fecha_revoc is not None and fecha_revoc < fecha_otorg:
        st.error("La fecha de revocación no puede ser anterior a la fecha de otorgamiento.")
        return

    if not facultad_pagare:
        st.error(MSG_SIN_FACULTAD_PAGARE)
        registrar_auditoria(
            accion="INDEXACION_BLOQUEADA_SIN_FACULTAD",
            usuario=usuario_carga,
            id_mandato="",
            entidad=entidad,
            nombre_ejecutivo=nombre,
            resultado="BLOQUEADO",
            observaciones="Intento de guardado con Facultad_Pagare = False.",
        )
        return

    registro = {
        "ID_Mandato": generar_id_mandato(),
        "Nombre_Ejecutivo": nombre.strip(),
        "Nombre_Ejecutivo_Normalizado": normalizar_nombre(nombre),
        "Entidad_Representada": entidad,
        "Fecha_Otorgamiento": fecha_otorg,
        "Fecha_Revocacion": fecha_revoc,
        "Notario_Titular": notario.strip(),
        "Ciudad_Notaria": ciudad.strip(),
        "Repertorio": str(repertorio).strip(),
        "Facultad_Pagare": True,
        "PDF_Path": "",
        "Fecha_Carga": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "Usuario_Carga": usuario_carga.strip() or "anonimo",
        "Observaciones": observaciones_carga.strip(),
    }

    df = cargar_mandatos()
    duplicados = detectar_duplicados(
        df, entidad, registro["Nombre_Ejecutivo_Normalizado"], fecha_otorg, registro["Repertorio"]
    )
    if not duplicados.empty:
        st.session_state["pendiente_duplicado"] = {
            "registro": registro,
            "duplicados": duplicados.to_dict("records"),
        }
        st.rerun()

    _guardar_registro(registro)


def _guardar_registro(registro: dict[str, Any]) -> None:
    """Persiste el PDF (si existe), agrega la fila a mandatos.xlsx y audita."""
    # 1) Mover el PDF temporal a pdf_storage con nombre indexado
    tmp_pdf = st.session_state.get("_tmp_pdf_path")
    if tmp_pdf and Path(tmp_pdf).exists():
        fecha_tag = registro["Fecha_Otorgamiento"].strftime("%Y-%m-%d")
        nombre_pdf = sanitizar_nombre_archivo(
            f"{registro['Entidad_Representada']}_{fecha_tag}_REP_"
            f"{registro['Repertorio']}_{registro['ID_Mandato'].split('-')[-1]}"
        ) + ".pdf"
        destino_pdf = PDF_STORAGE_DIR / nombre_pdf
        try:
            shutil.copy2(tmp_pdf, destino_pdf)
            registro["PDF_Path"] = str(destino_pdf.relative_to(BASE_DIR))
        except OSError as exc:
            st.error(f"No se pudo guardar el PDF en el repositorio: {exc}")
            registrar_auditoria(
                accion="CARGA_FALLIDA_PDF",
                usuario=registro["Usuario_Carga"],
                id_mandato=registro["ID_Mandato"],
                entidad=registro["Entidad_Representada"],
                nombre_ejecutivo=registro["Nombre_Ejecutivo"],
                resultado="ERROR",
                observaciones=str(exc),
            )
            return

    # 2) Agregar la fila con escritura segura (backup + archivo temporal)
    df = cargar_mandatos()
    df = pd.concat([df, pd.DataFrame([registro])], ignore_index=True)
    if not guardar_mandatos(df):
        registrar_auditoria(
            accion="CARGA_FALLIDA_EXCEL",
            usuario=registro["Usuario_Carga"],
            id_mandato=registro["ID_Mandato"],
            entidad=registro["Entidad_Representada"],
            nombre_ejecutivo=registro["Nombre_Ejecutivo"],
            resultado="ERROR",
            observaciones="Fallo al escribir mandatos.xlsx.",
        )
        return

    # 3) Auditoría de la carga exitosa
    registrar_auditoria(
        accion="CARGA_MANDATO",
        usuario=registro["Usuario_Carga"],
        id_mandato=registro["ID_Mandato"],
        entidad=registro["Entidad_Representada"],
        nombre_ejecutivo=registro["Nombre_Ejecutivo"],
        resultado="OK",
        observaciones=registro["Observaciones"],
    )

    # 4) Limpiar estado de la sesión
    for clave in ("extraccion", "_tmp_pdf_path", "_tmp_pdf_name", "pendiente_duplicado"):
        st.session_state.pop(clave, None)

    st.success(
        f"✅ Mandato guardado correctamente con ID **{registro['ID_Mandato']}**"
        + (f" — PDF indexado en `{registro['PDF_Path']}`." if registro["PDF_Path"] else ".")
    )


# ---------------------------------------------------------------------------
# UI — Tab 3: Auditoría (solo lectura)
# ---------------------------------------------------------------------------

def render_tab_auditoria() -> None:
    st.subheader("🧾 Registro de auditoría")
    try:
        if AUDIT_LOG_XLSX.exists():
            log = pd.read_excel(AUDIT_LOG_XLSX, engine="openpyxl")
            if log.empty:
                st.info("Aún no hay registros de auditoría.")
            else:
                st.dataframe(
                    log.sort_index(ascending=False),
                    use_container_width=True,
                    hide_index=True,
                )
        else:
            st.info("Aún no existe el archivo de auditoría.")
    except PermissionError:
        st.error("`audit_log.xlsx` está abierto en otro programa. Ciérrelo para visualizarlo.")
    except (OSError, ValueError) as exc:
        st.error(f"No se pudo leer el registro de auditoría: {exc}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(
        page_title="Gestión de Personerías — Santander / GRC",
        page_icon="⚖️",
        layout="wide",
    )
    ensure_structure()

    st.title("⚖️ Sistema de Gestión de Personerías y Mandatos")
    st.caption("Banco Santander / GRC — Juicios ejecutivos chilenos · Uso interno")

    with st.sidebar:
        st.markdown("### ℹ️ Información")
        total = len(cargar_mandatos())
        st.metric("Mandatos indexados", total)
        disponible, provider = ocr_disponible()
        st.markdown(
            f"**OCR multimodal:** {'✅ ' + provider if disponible else '❌ no configurado'}"
        )
        st.divider()
        if st.button("Cargar datos de ejemplo"):
            if cargar_datos_ejemplo():
                st.success("Datos de ejemplo cargados.")
                st.rerun()
        st.divider()
        st.warning(
            "**Advertencia legal:** Este sistema asiste la búsqueda y validación "
            "de personerías, pero no reemplaza la revisión profesional del "
            "mandato ni del título ejecutivo por el abogado responsable."
        )

    tab1, tab2, tab3 = st.tabs(
        ["🔎 Consulta / Litigación", "📥 Carga e Indexación", "🧾 Auditoría"]
    )
    with tab1:
        render_tab_consulta()
    with tab2:
        render_tab_carga()
    with tab3:
        render_tab_auditoria()


if __name__ == "__main__":
    main()
