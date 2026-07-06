"""Módulos 3 y 4: casos, documentos, instrumentos y partes (modelo jurídico)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import pandas as pd

from .config import (
    BASE_DIR,
    CASES_DIR,
    CASES_XLSX,
    INSTRUMENTS_XLSX,
    PARTIES_XLSX,
)
from .storage import append_row, read_excel_or_empty, write_excel_safe
from .textutil import sanitizar_nombre_archivo, uid

RESPONDE_TODOS = "TODOS"


def cargar_casos() -> pd.DataFrame:
    return read_excel_or_empty(CASES_XLSX)


def cargar_instrumentos(id_caso: Optional[str] = None) -> pd.DataFrame:
    df = read_excel_or_empty(INSTRUMENTS_XLSX)
    if id_caso and not df.empty:
        df = df[df["ID_Caso"] == id_caso]
    return df


def cargar_partes(id_caso: Optional[str] = None) -> pd.DataFrame:
    df = read_excel_or_empty(PARTIES_XLSX)
    if id_caso and not df.empty:
        df = df[df["ID_Caso"] == id_caso]
    return df


def crear_caso(datos: dict[str, Any]) -> dict[str, Any]:
    """Crea un caso con su carpeta propia database/cases/[ID_Caso]/."""
    id_caso = uid("CASO")
    carpeta = CASES_DIR / id_caso
    carpeta.mkdir(parents=True, exist_ok=True)
    registro = {
        "ID_Caso": id_caso,
        "Banco_Entidad": str(datos.get("Banco_Entidad", "")).strip(),
        "Tipo_Caso_Detectado": str(datos.get("Tipo_Caso_Detectado", "")).strip(),
        "Cliente_Deudor": str(datos.get("Cliente_Deudor", "")).strip(),
        "RUT_Deudor": str(datos.get("RUT_Deudor", "")).strip(),
        "Numero_Operacion": str(datos.get("Numero_Operacion", "")).strip(),
        "Fecha_Carga": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "Usuario_Carga": str(datos.get("Usuario_Carga", "")).strip() or "anonimo",
        "Estado": "ABIERTO",
        "Observaciones": str(datos.get("Observaciones", "")).strip(),
        "Ruta_Carpeta_Caso": str(carpeta.relative_to(BASE_DIR)),
    }
    append_row(CASES_XLSX, registro)
    return registro


def guardar_documento_caso(
    id_caso: str, nombre_original: str, contenido: bytes, tipo_documento: str
) -> Path:
    """Guarda un documento original dentro de la carpeta del caso."""
    carpeta = CASES_DIR / id_caso
    carpeta.mkdir(parents=True, exist_ok=True)
    sufijo = Path(nombre_original).suffix.lower() or ".pdf"
    base = sanitizar_nombre_archivo(f"{tipo_documento}_{Path(nombre_original).stem}")
    destino = carpeta / f"{base}{sufijo}"
    contador = 1
    while destino.exists():
        destino = carpeta / f"{base}_{contador}{sufijo}"
        contador += 1
    destino.write_bytes(contenido)
    return destino


def documentos_del_caso(id_caso: str) -> list[Path]:
    """Lista los documentos guardados en la carpeta del caso."""
    carpeta = CASES_DIR / id_caso
    if not carpeta.exists():
        return []
    return sorted(p for p in carpeta.iterdir() if p.is_file())


def agregar_instrumento(id_caso: str, datos: dict[str, Any]) -> dict[str, Any]:
    """Agrega un instrumento (título) al caso."""
    registro: dict[str, Any] = {
        "ID_Instrumento": uid("INST"),
        "ID_Caso": id_caso,
    }
    from .config import INSTRUMENTS_COLUMNS

    for col in INSTRUMENTS_COLUMNS:
        if col in ("ID_Instrumento", "ID_Caso"):
            continue
        registro[col] = datos.get(col, "")
    append_row(INSTRUMENTS_XLSX, registro)
    return registro


def agregar_parte(id_caso: str, datos: dict[str, Any]) -> dict[str, Any]:
    """Agrega un obligado/parte al caso."""
    registro: dict[str, Any] = {
        "ID_Parte": uid("PARTE"),
        "ID_Caso": id_caso,
    }
    from .config import PARTIES_COLUMNS

    for col in PARTIES_COLUMNS:
        if col in ("ID_Parte", "ID_Caso"):
            continue
        registro[col] = datos.get(col, "")
    append_row(PARTIES_XLSX, registro)
    return registro


def eliminar_fila(ruta_xlsx: Path, columna_id: str, valor_id: str) -> bool:
    """Elimina una fila por ID con escritura segura."""
    df = read_excel_or_empty(ruta_xlsx)
    if df.empty:
        return False
    antes = len(df)
    df = df[df[columna_id] != valor_id]
    if len(df) == antes:
        return False
    write_excel_safe(df, ruta_xlsx)
    return True


def actualizar_caso(id_caso: str, cambios: dict[str, Any]) -> bool:
    """Actualiza campos de un caso existente."""
    df = read_excel_or_empty(CASES_XLSX)
    mask = df["ID_Caso"] == id_caso
    if not mask.any():
        return False
    for k, v in cambios.items():
        if k in df.columns:
            df.loc[mask, k] = v
    write_excel_safe(df, CASES_XLSX)
    return True


def instrumentos_que_responde(parte: pd.Series | dict, instrumentos: pd.DataFrame) -> list[str]:
    """IDs de instrumentos por los que responde una parte ('TODOS' o lista separada por coma)."""
    valor = str(
        (parte.get("Responde_Por_Instrumento") if isinstance(parte, dict)
         else parte.get("Responde_Por_Instrumento", ""))
        or ""
    ).strip()
    todos = list(instrumentos["ID_Instrumento"].astype(str)) if not instrumentos.empty else []
    if not valor or valor.upper() == RESPONDE_TODOS:
        return todos
    ids = [v.strip() for v in valor.split(",") if v.strip()]
    return [i for i in ids if i in todos] or ids
