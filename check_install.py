"""Verificador de instalación y seguridad del sistema.

Ejecución:  python check_install.py
Revisa archivos, carpetas, versión de Python, dependencias críticas,
permisos de escritura, Streamlit ejecutable, y que el proyecto no
contenga documentos sensibles ni claves versionadas.
Termina con código 0 si todo está OK.
"""

from __future__ import annotations

import importlib
import subprocess
import sys
import uuid
from pathlib import Path

BASE = Path(__file__).resolve().parent

ARCHIVOS_REQUERIDOS = [
    "app.py", "requirements.txt", "INICIAR_APP.bat", "iniciar_app.sh",
    "DIAGNOSTICO.bat", ".env.example", ".gitignore", "README.md",
]
CARPETAS_APP = ["legal"]
DEPENDENCIAS = ["streamlit", "pandas", "openpyxl", "rapidfuzz", "docxtpl", "docx"]
GITIGNORE_DEBE_EXCLUIR = [".env", "database/", "*.xlsx", "*.pdf", "backups", "temp"]

OK = "  [OK]  "
FAIL = "  [FALLA]"
WARN = "  [AVISO]"


def _check_python() -> int:
    v = sys.version_info
    if v >= (3, 10):
        print(f"{OK} Python {v.major}.{v.minor}.{v.micro}")
        if v >= (3, 13):
            print(f"{WARN} Python {v.major}.{v.minor} es muy reciente; si alguna "
                  "dependencia fallara, use Python 3.11 o 3.12 (recomendado).")
        return 0
    print(f"{FAIL} Python {v.major}.{v.minor} — se requiere 3.10 o superior.")
    return 1


def _check_archivos() -> int:
    errores = 0
    for nombre in ARCHIVOS_REQUERIDOS:
        if (BASE / nombre).exists():
            print(f"{OK} Archivo {nombre}")
        else:
            print(f"{FAIL} Falta el archivo {nombre}")
            errores += 1
    for carpeta in CARPETAS_APP:
        if (BASE / carpeta).is_dir():
            print(f"{OK} Carpeta {carpeta}/")
        else:
            print(f"{FAIL} Falta la carpeta {carpeta}/")
            errores += 1
    return errores


def _check_escritura() -> int:
    prueba = BASE / f"_test_escritura_{uuid.uuid4().hex[:6]}.tmp"
    try:
        prueba.write_text("prueba", encoding="utf-8")
        prueba.unlink()
        print(f"{OK} Permisos de escritura en la carpeta del proyecto")
        return 0
    except OSError as exc:
        print(f"{FAIL} No se puede escribir en la carpeta del proyecto: {exc}")
        print("        Mueva el proyecto a una carpeta con permisos (ej. Documentos).")
        return 1


def _check_dependencias() -> int:
    errores = 0
    for dep in DEPENDENCIAS:
        try:
            importlib.import_module(dep)
            print(f"{OK} Dependencia {dep}")
        except ImportError:
            print(f"{FAIL} Falta la dependencia {dep} — "
                  "ejecute: pip install -r requirements.txt")
            errores += 1
    for dep_ia in ("openai", "google.generativeai"):
        try:
            importlib.import_module(dep_ia)
            print(f"{OK} Dependencia opcional de IA {dep_ia} (instalada)")
        except ImportError:
            print(f"{WARN} Dependencia opcional de IA {dep_ia} no instalada "
                  "(la app funciona igual en modo manual).")
    return errores


def _check_estructura() -> int:
    try:
        sys.path.insert(0, str(BASE))
        from legal.storage import ensure_structure

        ensure_structure()
        print(f"{OK} Estructura database/ creada/verificada automáticamente")
        return 0
    except Exception as exc:  # noqa: BLE001 - se reporta cualquier fallo
        print(f"{FAIL} No se pudo crear la estructura database/: {exc}")
        return 1


def _check_gitignore() -> int:
    errores = 0
    ruta = BASE / ".gitignore"
    if not ruta.exists():
        print(f"{FAIL} No existe .gitignore")
        return 1
    contenido = ruta.read_text(encoding="utf-8")
    for patron in GITIGNORE_DEBE_EXCLUIR:
        base = patron.rstrip("/")
        if base in contenido:
            print(f"{OK} .gitignore excluye {patron}")
        else:
            print(f"{FAIL} .gitignore NO excluye {patron}")
            errores += 1
    return errores


def _check_sensibles() -> int:
    """Verifica que no haya documentos reales ni claves versionadas."""
    errores = 0
    if (BASE / ".env").exists():
        print(f"{WARN} Existe un archivo .env local (correcto que sea local; "
              "verifique que NUNCA se suba al repositorio).")
    # Archivos versionados (si hay repositorio git disponible)
    try:
        r = subprocess.run(
            ["git", "ls-files"], cwd=BASE, capture_output=True, text=True, timeout=30,
        )
        if r.returncode == 0:
            sensibles = [
                f for f in r.stdout.splitlines()
                if f == ".env" or f.startswith("database/")
                or f.lower().endswith((".pdf", ".xlsx"))
            ]
            if sensibles:
                print(f"{FAIL} Archivos sensibles VERSIONADOS en git: {sensibles}")
                errores += 1
            else:
                print(f"{OK} Git no versiona .env, database/, PDFs ni Excels")
        else:
            print(f"{WARN} Sin repositorio git (instalación desde ZIP) — "
                  "no aplica chequeo de archivos versionados.")
    except (OSError, subprocess.TimeoutExpired):
        print(f"{WARN} git no disponible — no aplica chequeo de versionado.")
    # Documentos sueltos fuera de database/ (no deberían venir en el ZIP)
    sueltos = [
        p.name for p in BASE.iterdir()
        if p.is_file() and p.suffix.lower() in (".pdf", ".xlsx")
    ]
    if sueltos:
        print(f"{FAIL} Documentos .pdf/.xlsx sueltos en la raíz del proyecto: {sueltos}")
        errores += 1
    else:
        print(f"{OK} Sin documentos .pdf/.xlsx sueltos en la raíz")
    return errores


def _check_streamlit() -> int:
    try:
        r = subprocess.run(
            [sys.executable, "-m", "streamlit", "--version"],
            capture_output=True, text=True, timeout=60,
        )
        if r.returncode == 0:
            print(f"{OK} Streamlit ejecutable ({r.stdout.strip()})")
            return 0
        print(f"{FAIL} Streamlit no responde: {r.stderr.strip()[:200]}")
        return 1
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"{FAIL} No se pudo ejecutar Streamlit: {exc}")
        return 1


def revisar() -> int:
    print("=" * 62)
    print(" Verificación de instalación — Sistema de Demandas")
    print("=" * 62)
    errores = 0
    errores += _check_python()
    errores += _check_archivos()
    errores += _check_escritura()
    errores += _check_dependencias()
    errores += _check_estructura()
    errores += _check_gitignore()
    errores += _check_sensibles()
    errores += _check_streamlit()
    print("=" * 62)
    if errores == 0:
        print(" RESULTADO: TODO OK. Abra la app con doble clic en "
              "INICIAR_APP.bat (Windows) o ./iniciar_app.sh (Mac/Linux).")
    else:
        print(f" RESULTADO: {errores} problema(s) detectado(s). "
              "Corrija lo indicado arriba y vuelva a ejecutar este chequeo.")
    print("=" * 62)
    return errores


if __name__ == "__main__":
    sys.exit(1 if revisar() else 0)
