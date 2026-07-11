"""Módulo 1: gestión y consulta de personerías/mandatos."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

import pandas as pd
from rapidfuzz import fuzz

from .config import (
    FUZZY_THRESHOLD,
    MANDATOS_XLSX,
    PDF_STORAGE_DIR,
    TEXTO_PERSONERIA_TPL,
)
from .storage import append_row, read_excel_or_empty, write_excel_safe
from .textutil import (
    formatear_fecha,
    normalizar_nombre,
    parsear_fecha,
    sanitizar_nombre_archivo,
    uid,
)


def cargar_mandatos() -> pd.DataFrame:
    """Carga mandatos.xlsx con fechas normalizadas."""
    df = read_excel_or_empty(MANDATOS_XLSX)
    df["Fecha_Otorgamiento"] = pd.to_datetime(
        df["Fecha_Otorgamiento"], dayfirst=True, errors="coerce"
    )
    df["Fecha_Revocacion"] = pd.to_datetime(
        df["Fecha_Revocacion"], dayfirst=True, errors="coerce"
    )
    return df


def buscar_personeria(
    df: pd.DataFrame,
    nombre_input: str,
    entidad_input: str,
    fecha_instrumento: date,
) -> dict[str, Any]:
    """Busca la personería vigente a la fecha del instrumento.

    Retorna {"vigente": Series|None, "mismo_dia": DataFrame, "ambiguos": DataFrame}.
    Si el nombre buscado coincide con MÁS DE UNA persona distinta, no se elige
    ninguna: se retorna "ambiguos" para exigir un nombre más específico (regla
    de seguridad jurídica — nunca citar la personería de la persona equivocada).
    """
    resultado: dict[str, Any] = {
        "vigente": None, "mismo_dia": pd.DataFrame(), "ambiguos": pd.DataFrame(),
    }
    nombre_norm = normalizar_nombre(nombre_input)
    if df.empty or not nombre_norm:
        return resultado

    fecha_ts = pd.Timestamp(fecha_instrumento)
    df = df.copy()
    df["_score"] = df["Nombre_Ejecutivo_Normalizado"].apply(
        lambda x: fuzz.token_set_ratio(nombre_norm, normalizar_nombre(str(x)))
        if pd.notna(x) else 0
    )
    candidatos = df[
        (df["_score"] > FUZZY_THRESHOLD)
        & (df["Entidad_Representada"] == entidad_input)
        & (df["Fecha_Otorgamiento"].notna())
        & (df["Fecha_Otorgamiento"] <= fecha_ts)
    ]
    if candidatos.empty:
        return resultado

    resultado["mismo_dia"] = candidatos[candidatos["Fecha_Revocacion"] == fecha_ts]

    vigentes = candidatos[
        candidatos["Fecha_Revocacion"].isna()
        | (candidatos["Fecha_Revocacion"] > fecha_ts)
    ]
    if not vigentes.empty:
        personas = (
            vigentes["Nombre_Ejecutivo_Normalizado"].astype(str).str.strip().unique()
        )
        if len(personas) > 1:
            resultado["ambiguos"] = vigentes
            return resultado
        resultado["vigente"] = (
            vigentes.sort_values("Fecha_Otorgamiento", ascending=False).iloc[0]
        )
    return resultado


def texto_personeria(mandato: pd.Series | dict) -> str:
    """Genera el texto legal exacto de personería para la demanda."""
    get = mandato.get if isinstance(mandato, dict) else lambda k: mandato.get(k, "")
    return TEXTO_PERSONERIA_TPL.format(
        nombre=get("Nombre_Ejecutivo"),
        entidad=get("Entidad_Representada"),
        fecha_otorgamiento=formatear_fecha(get("Fecha_Otorgamiento")),
        ciudad=get("Ciudad_Notaria"),
        notario=get("Notario_Titular"),
        repertorio=get("Repertorio"),
    )


def detectar_duplicados(
    df: pd.DataFrame,
    entidad: str,
    nombre_normalizado: str,
    fecha_otorgamiento: Optional[pd.Timestamp],
    repertorio: str,
) -> pd.DataFrame:
    """Posibles duplicados por entidad + nombre + fecha + repertorio."""
    if df.empty:
        return pd.DataFrame()
    rep = str(repertorio).strip().lower()
    mask = (
        (df["Entidad_Representada"] == entidad)
        & (df["Nombre_Ejecutivo_Normalizado"].fillna("") == nombre_normalizado)
        & (df["Repertorio"].fillna("").astype(str).str.strip().str.lower() == rep)
    )
    if fecha_otorgamiento is not None:
        mask &= df["Fecha_Otorgamiento"] == fecha_otorgamiento
    return df[mask]


def guardar_mandato(
    datos: dict[str, Any],
    pdf_temporal: Optional[Path] = None,
) -> dict[str, Any]:
    """Persiste un mandato (y su PDF si existe). Retorna el registro guardado."""
    id_mandato = uid("MND")
    fecha_otorg = parsear_fecha(datos.get("Fecha_Otorgamiento"))
    registro = {
        "ID_Mandato": id_mandato,
        "Nombre_Ejecutivo": str(datos.get("Nombre_Ejecutivo", "")).strip(),
        "Nombre_Ejecutivo_Normalizado": normalizar_nombre(
            str(datos.get("Nombre_Ejecutivo", ""))
        ),
        "Entidad_Representada": str(datos.get("Entidad_Representada", "")).strip(),
        "Fecha_Otorgamiento": fecha_otorg,
        "Fecha_Revocacion": parsear_fecha(datos.get("Fecha_Revocacion")),
        "Notario_Titular": str(datos.get("Notario_Titular", "")).strip(),
        "Ciudad_Notaria": str(datos.get("Ciudad_Notaria", "")).strip(),
        "Repertorio": str(datos.get("Repertorio", "")).strip(),
        "Facultad_Pagare": bool(datos.get("Facultad_Pagare", False)),
        "Texto_Facultad_Pagare": str(datos.get("Texto_Facultad_Pagare", "")).strip(),
        "PDF_Path": "",
        "Fecha_Carga": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "Usuario_Carga": str(datos.get("Usuario_Carga", "")).strip() or "anonimo",
        "Observaciones": str(datos.get("Observaciones", "")).strip(),
    }

    if pdf_temporal is not None and pdf_temporal.exists():
        fecha_tag = fecha_otorg.strftime("%Y-%m-%d") if fecha_otorg is not None else "sin-fecha"
        nombre_pdf = sanitizar_nombre_archivo(
            f"{registro['Entidad_Representada']}_{fecha_tag}_REP_"
            f"{registro['Repertorio']}_{id_mandato.split('-')[-1]}"
        ) + ".pdf"
        destino = PDF_STORAGE_DIR / nombre_pdf
        PDF_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        import shutil

        shutil.copy2(pdf_temporal, destino)
        from .config import BASE_DIR

        registro["PDF_Path"] = str(destino.relative_to(BASE_DIR))

    append_row(MANDATOS_XLSX, registro)
    return registro
