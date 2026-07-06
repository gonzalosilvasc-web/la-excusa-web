"""Verificador de instalación del sistema.

Ejecución:  python check_install.py
Revisa archivos, carpetas, versión de Python, dependencias críticas y que
Streamlit sea ejecutable. Termina con código 0 si todo está OK.
"""

from __future__ import annotations

import importlib
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent

ARCHIVOS_REQUERIDOS = ["app.py", "requirements.txt", "INICIAR_APP.bat", "iniciar_app.sh"]
CARPETAS_APP = ["legal"]
DEPENDENCIAS = ["streamlit", "pandas", "openpyxl", "rapidfuzz", "docxtpl", "docx"]

OK = "  [OK]  "
FAIL = "  [FALLA]"


def revisar() -> int:
    errores = 0
    print("=" * 60)
    print(" Verificación de instalación — Sistema de Demandas")
    print("=" * 60)

    # 1) Versión de Python
    v = sys.version_info
    if v >= (3, 10):
        print(f"{OK} Python {v.major}.{v.minor}.{v.micro}")
    else:
        print(f"{FAIL} Python {v.major}.{v.minor} — se requiere 3.10 o superior.")
        errores += 1

    # 2) Archivos requeridos
    for nombre in ARCHIVOS_REQUERIDOS:
        if (BASE / nombre).exists():
            print(f"{OK} Archivo {nombre}")
        else:
            print(f"{FAIL} Falta el archivo {nombre}")
            errores += 1

    # 3) Carpetas de la aplicación
    for carpeta in CARPETAS_APP:
        if (BASE / carpeta).is_dir():
            print(f"{OK} Carpeta {carpeta}/")
        else:
            print(f"{FAIL} Falta la carpeta {carpeta}/")
            errores += 1

    # 4) Dependencias críticas
    for dep in DEPENDENCIAS:
        try:
            importlib.import_module(dep)
            print(f"{OK} Dependencia {dep}")
        except ImportError:
            print(f"{FAIL} Falta la dependencia {dep} — "
                  "ejecute: pip install -r requirements.txt")
            errores += 1

    # 5) Estructura de datos (se crea sola)
    try:
        sys.path.insert(0, str(BASE))
        from legal.storage import ensure_structure

        ensure_structure()
        print(f"{OK} Estructura database/ creada/verificada")
    except Exception as exc:  # noqa: BLE001 - se reporta cualquier fallo
        print(f"{FAIL} No se pudo crear la estructura database/: {exc}")
        errores += 1

    # 6) Streamlit ejecutable
    try:
        r = subprocess.run(
            [sys.executable, "-m", "streamlit", "--version"],
            capture_output=True, text=True, timeout=60,
        )
        if r.returncode == 0:
            print(f"{OK} Streamlit ejecutable ({r.stdout.strip()})")
        else:
            print(f"{FAIL} Streamlit no responde: {r.stderr.strip()[:200]}")
            errores += 1
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"{FAIL} No se pudo ejecutar Streamlit: {exc}")
        errores += 1

    print("=" * 60)
    if errores == 0:
        print(" RESULTADO: TODO OK. Ejecute la app con doble clic en "
              "INICIAR_APP.bat (Windows) o ./iniciar_app.sh (Mac/Linux).")
    else:
        print(f" RESULTADO: {errores} problema(s) detectado(s). "
              "Corrija lo indicado arriba.")
    print("=" * 60)
    return errores


if __name__ == "__main__":
    sys.exit(1 if revisar() else 0)
