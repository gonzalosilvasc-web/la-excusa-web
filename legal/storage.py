"""Persistencia segura en Excel: estructura, backups, escritura atómica y auditoría."""

from __future__ import annotations

import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

from .config import (
    ALL_DIRS,
    AUDIT_COLUMNS,
    AUDIT_LOG_XLSX,
    BACKUPS_DIR,
    EXCEL_SCHEMAS,
)


class ExcelAbiertoError(Exception):
    """El archivo Excel está abierto/bloqueado por otro programa."""

    def __init__(self, archivo: Path) -> None:
        self.archivo = archivo
        super().__init__(
            f"No se puede escribir «{archivo.name}» porque está abierto en otro "
            "programa (probablemente Excel). Cierre el archivo y vuelva a intentar."
        )


def ensure_structure() -> None:
    """Crea todas las carpetas y Excels base si no existen."""
    for carpeta in ALL_DIRS:
        carpeta.mkdir(parents=True, exist_ok=True)
    for ruta_str, columnas in EXCEL_SCHEMAS.items():
        ruta = Path(ruta_str)
        if not ruta.exists():
            write_excel_safe(pd.DataFrame(columns=columnas), ruta, backup=False)


def write_excel_safe(df: pd.DataFrame, destino: Path, backup: bool = True) -> None:
    """Escritura atómica: temporal → validación → reemplazo. Respaldo previo opcional.

    Lanza ExcelAbiertoError si el archivo está bloqueado.
    """
    destino.parent.mkdir(parents=True, exist_ok=True)
    if backup:
        crear_backup(destino)
    tmp = destino.with_name(f".{destino.stem}_{uuid.uuid4().hex[:6]}.tmp.xlsx")
    try:
        df.to_excel(tmp, index=False, engine="openpyxl")
        verificacion = pd.read_excel(tmp, engine="openpyxl")
        if len(verificacion) != len(df):
            raise IOError(
                f"Validación fallida al escribir {destino.name}: se esperaban "
                f"{len(df)} filas y se leyeron {len(verificacion)}."
            )
        try:
            os.replace(tmp, destino)
        except PermissionError as exc:
            raise ExcelAbiertoError(destino) from exc
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


def read_excel_or_empty(ruta: Path) -> pd.DataFrame:
    """Lee un Excel garantizando todas las columnas de su esquema."""
    columnas = EXCEL_SCHEMAS.get(str(ruta), [])
    try:
        if not ruta.exists():
            return pd.DataFrame(columns=columnas)
        df = pd.read_excel(ruta, engine="openpyxl")
    except PermissionError as exc:
        raise ExcelAbiertoError(ruta) from exc
    for col in columnas:
        if col not in df.columns:
            df[col] = pd.NA
    if not columnas:
        return df
    # Conservar columnas extra agregadas manualmente por el usuario en Excel
    # (reordenadas al final) en vez de descartarlas en la próxima escritura.
    extras = [c for c in df.columns if c not in columnas]
    return df[columnas + extras]


def append_row(ruta: Path, fila: dict) -> None:
    """Agrega una fila a un Excel con escritura segura."""
    df = read_excel_or_empty(ruta)
    df = pd.concat([df, pd.DataFrame([fila])], ignore_index=True)
    write_excel_safe(df, ruta)


# Respaldos máximos conservados; los más antiguos se depuran automáticamente
# para que database/backups/ no crezca sin límite (un respaldo por escritura).
MAX_BACKUPS = 300


def crear_backup(archivo: Path) -> Optional[Path]:
    """Copia con timestamp a database/backups/. None si el original no existe."""
    if not archivo.exists():
        return None
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    destino = BACKUPS_DIR / f"{archivo.stem}_backup_{timestamp}{archivo.suffix}"
    try:
        BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
        shutil.copy2(archivo, destino)
        _depurar_backups()
        return destino
    except OSError:
        return None


def _depurar_backups() -> None:
    """Elimina los respaldos más antiguos por sobre MAX_BACKUPS."""
    try:
        respaldos = sorted(
            BACKUPS_DIR.glob("*_backup_*"), key=lambda p: p.name, reverse=True
        )
        for antiguo in respaldos[MAX_BACKUPS:]:
            antiguo.unlink()
    except OSError:
        pass


def registrar_auditoria(
    accion: str,
    usuario: str = "",
    id_caso: str = "",
    id_mandato: str = "",
    id_template: str = "",
    resultado: str = "OK",
    observaciones: str = "",
) -> bool:
    """Registra una acción en audit_log.xlsx. Retorna False si no pudo escribir."""
    fila = {
        "Fecha_Hora": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "Usuario": usuario or "anonimo",
        "Accion": accion,
        "ID_Caso": id_caso,
        "ID_Mandato": id_mandato,
        "ID_Template": id_template,
        "Resultado": resultado,
        "Observaciones": observaciones,
    }
    try:
        df = read_excel_or_empty(AUDIT_LOG_XLSX)
        df = pd.concat([df, pd.DataFrame([fila])], ignore_index=True)
        write_excel_safe(df, AUDIT_LOG_XLSX)
        return True
    except ExcelAbiertoError:
        return False
    except (OSError, IOError, ValueError):
        return False


def leer_auditoria() -> pd.DataFrame:
    return read_excel_or_empty(AUDIT_LOG_XLSX)
