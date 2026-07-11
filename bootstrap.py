"""Instalador y lanzador multiplataforma del sistema (solo librería estándar).

Lo invocan INICIAR_APP.bat / iniciar_app.sh tras detectar Python. Se encarga
de: elegir la ubicación del entorno virtual (externa y corta en Windows si la
ruta del proyecto es larga, evitando fallas por MAX_PATH), crearlo, instalar
dependencias, preparar Streamlit y ejecutar la aplicación, registrando cada
paso en registro_instalacion.txt.

Modos:
    python bootstrap.py                 → instala (si falta) y ejecuta la app
    python bootstrap.py --info          → muestra rutas y riesgo de ruta larga
    python bootstrap.py --diagnostico   → --info + check_install con el venv

Códigos de salida: 0 ok · 2 venv falló · 3 pip falló · 4 app terminó con error
· 5 Python demasiado antiguo.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

PROYECTO = Path(__file__).resolve().parent
REGISTRO = PROYECTO / "registro_instalacion.txt"

# Sobre este largo de ruta del proyecto (en Windows), el venv se crea en una
# ruta corta externa para que pip no falle por el límite MAX_PATH (260).
UMBRAL_RUTA_LARGA = 90


def log(mensaje: str) -> None:
    linea = f"[{datetime.now():%d/%m/%Y %H:%M:%S}] {mensaje}"
    print(linea)
    try:
        with REGISTRO.open("a", encoding="utf-8") as f:
            f.write(linea + "\n")
    except OSError:
        pass


def ruta_larga_riesgosa() -> bool:
    return os.name == "nt" and len(str(PROYECTO)) > UMBRAL_RUTA_LARGA


def ruta_venv() -> Path:
    """Ubicación del entorno virtual.

    - Si ya existe un .venv local usable, se respeta (instalaciones previas).
    - En Windows con ruta de proyecto larga: venv externo corto en
      %LOCALAPPDATA%\\LegalTechDemandas\\venvs\\<hash del proyecto>.
    - En el resto de los casos: .venv dentro del proyecto.
    """
    local = PROYECTO / ".venv"
    if python_de(local).exists():
        return local
    if ruta_larga_riesgosa():
        base = os.environ.get("LOCALAPPDATA")
        if base:
            h = hashlib.sha256(
                str(PROYECTO).lower().encode("utf-8")
            ).hexdigest()[:12]
            return Path(base) / "LegalTechDemandas" / "venvs" / h
    return local


def python_de(venv: Path) -> Path:
    if os.name == "nt":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def mostrar_info() -> Path:
    venv = ruta_venv()
    print("=" * 66)
    print(" Rutas del sistema")
    print("=" * 66)
    print(f' Carpeta del proyecto : "{PROYECTO}"')
    print(f"   Largo de la ruta   : {len(str(PROYECTO))} caracteres")
    print(f' Entorno virtual      : "{venv}"'
          + (" [existe]" if python_de(venv).exists() else " [aun no creado]"))
    if ruta_larga_riesgosa():
        print()
        print(" AVISO ruta larga: la carpeta del proyecto supera los "
              f"{UMBRAL_RUTA_LARGA} caracteres. Windows limita las rutas a 260")
        print(" caracteres (MAX_PATH) y pip puede fallar instalando en rutas")
        print(" profundas. Por eso el entorno virtual se crea automaticamente")
        print(" en la ruta corta externa indicada arriba — no necesita mover")
        print(" la carpeta del proyecto.")
    else:
        print(" Riesgo de ruta larga : NO")
    print("=" * 66)
    return venv


def preparar_streamlit() -> None:
    """Evita el prompt interactivo de email de Streamlit y las estadísticas."""
    os.environ["STREAMLIT_BROWSER_GATHER_USAGE_STATS"] = "false"
    credenciales = Path.home() / ".streamlit" / "credentials.toml"
    if not credenciales.exists():
        try:
            credenciales.parent.mkdir(parents=True, exist_ok=True)
            credenciales.write_text('[general]\nemail = ""\n', encoding="utf-8")
        except OSError:
            pass


def instalar(venv: Path) -> int:
    vpy = python_de(venv)
    if vpy.exists():
        return 0
    print()
    print("Primera ejecucion: creando entorno e instalando dependencias.")
    print("Esto puede tardar VARIOS MINUTOS. No cierre esta ventana.")
    print()
    log(f'Creando entorno virtual en "{venv}"')
    try:
        venv.parent.mkdir(parents=True, exist_ok=True)
        r = subprocess.run([sys.executable, "-m", "venv", str(venv)])
        if r.returncode != 0 or not vpy.exists():
            raise OSError(f"venv devolvio codigo {r.returncode}")
    except OSError as exc:
        log(f"FALLA creando el entorno virtual: {exc}")
        print()
        print("[ERROR] No se pudo crear el entorno virtual.")
        print(f'Intente borrar la carpeta "{venv}" y vuelva a ejecutar.')
        return 2
    log("Instalando dependencias con pip")
    pasos = [
        [str(vpy), "-m", "pip", "install", "--upgrade", "pip"],
        [str(vpy), "-m", "pip", "install", "-r",
         str(PROYECTO / "requirements.txt")],
    ]
    for cmd in pasos:
        if subprocess.run(cmd, cwd=str(PROYECTO)).returncode != 0:
            log("FALLA en pip install")
            print()
            print("[ERROR] Fallo la instalacion de dependencias.")
            print("Revise su conexion a internet. Si persiste, borre la")
            print(f'carpeta "{venv}" y vuelva a intentar.')
            return 3
    log("Dependencias instaladas correctamente")
    return 0


def ejecutar_app(venv: Path) -> int:
    preparar_streamlit()
    log("Iniciando la aplicacion (streamlit run app.py)")
    print()
    print("Iniciando la aplicacion... se abrira sola en su navegador.")
    print("Si no se abre, entre manualmente a: http://localhost:8501")
    print("Para detenerla: cierre esta ventana o presione Ctrl+C.")
    print()
    try:
        r = subprocess.run(
            [str(python_de(venv)), "-m", "streamlit", "run", "app.py"],
            cwd=str(PROYECTO),
        )
        codigo = r.returncode
    except KeyboardInterrupt:
        codigo = 0
    if codigo != 0:
        log(f"La aplicacion termino con codigo {codigo}")
        return 4
    log("La aplicacion se cerro normalmente")
    return 0


def diagnostico() -> int:
    venv = mostrar_info()
    vpy = python_de(venv)
    interprete = str(vpy) if vpy.exists() else sys.executable
    print()
    print(f' Ejecutando check_install.py con: "{interprete}"')
    print()
    return subprocess.run(
        [interprete, str(PROYECTO / "check_install.py")], cwd=str(PROYECTO)
    ).returncode


def main() -> int:
    if sys.version_info < (3, 10):
        print(f"[ERROR] Python {sys.version_info.major}.{sys.version_info.minor} "
              "es demasiado antiguo: se requiere 3.10 o superior.")
        print("Instale Python 3.11 o 3.12 desde https://www.python.org/downloads/")
        return 5

    if "--info" in sys.argv:
        mostrar_info()
        return 0
    if "--diagnostico" in sys.argv:
        return diagnostico()

    log(f'INICIO — proyecto: "{PROYECTO}" — Python {sys.version.split()[0]}')
    venv = ruta_venv()
    if ruta_larga_riesgosa():
        print()
        print("AVISO: la ruta del proyecto es larga; el entorno virtual se")
        print(f'creara en una ruta corta externa: "{venv}"')
        log(f'Ruta larga detectada; venv externo: "{venv}"')
    codigo = instalar(venv)
    if codigo != 0:
        return codigo
    return ejecutar_app(venv)


if __name__ == "__main__":
    sys.exit(main())
