#!/usr/bin/env bash
# ============================================================
#  Lanzador para macOS / Linux — Sistema de Personerías y
#  Demandas Ejecutivas. Uso: ./iniciar_app.sh
#  Soporta rutas con espacios y tildes.
# ============================================================
set -u
cd "$(dirname "$0")" || { echo "[ERROR] No se pudo entrar a la carpeta del proyecto."; exit 1; }

echo "============================================================"
echo " Sistema de Personerías y Demandas Ejecutivas"
echo " Carpeta: $(pwd)"
echo "============================================================"

# --- Detección de ZIP no extraído ---
if [ ! -f "app.py" ] || [ ! -f "requirements.txt" ]; then
    echo
    echo "[ERROR] Debe extraer el ZIP antes de ejecutar la aplicación."
    echo "No se encontraron app.py / requirements.txt junto a este archivo."
    echo "Extraiga el ZIP completo y vuelva a ejecutar iniciar_app.sh"
    exit 1
fi

# --- Detección de Python ---
PYTHON_CMD=""
if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD="python"
fi
if [ -z "$PYTHON_CMD" ]; then
    echo
    echo "[ERROR] Python 3 no está instalado."
    echo "Descárguelo desde https://www.python.org/downloads/"
    exit 1
fi
if ! "$PYTHON_CMD" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)'; then
    echo "[ERROR] Se requiere Python 3.10 o superior. Versión actual:"
    "$PYTHON_CMD" --version
    exit 1
fi

# --- Entorno virtual e instalación de dependencias ---
if [ ! -x ".venv/bin/python" ]; then
    echo
    echo "Primera ejecución: creando entorno e instalando dependencias."
    echo "Esto puede tardar varios minutos. No cierre esta ventana."
    "$PYTHON_CMD" -m venv .venv || { echo "[ERROR] No se pudo crear .venv"; exit 1; }
    ".venv/bin/python" -m pip install --upgrade pip
    if ! ".venv/bin/python" -m pip install -r requirements.txt; then
        echo
        echo "[ERROR] Falló la instalación de dependencias."
        echo "Revise su conexión a internet. Si persiste, borre .venv y reintente."
        exit 1
    fi
fi

# --- Ejecutar la aplicación ---
echo
echo "Iniciando la aplicación... se abrirá en su navegador."
echo "Para detenerla presione Ctrl+C."
echo
".venv/bin/python" -m streamlit run app.py
estado=$?
if [ $estado -ne 0 ]; then
    echo
    echo "[ERROR] La aplicación terminó con un error (código $estado)."
    echo "Diagnóstico: .venv/bin/python check_install.py"
fi
exit $estado
