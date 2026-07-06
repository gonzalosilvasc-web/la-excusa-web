#!/usr/bin/env bash
# ==================================================================
#  Lanzador para macOS / Linux — Sistema de Personerías y Demandas
#  Ejecutivas. Uso: ./iniciar_app.sh
#  Soporta rutas con espacios, tildes y caracteres especiales.
#  Ante cualquier error muestra un diagnóstico completo.
# ==================================================================
set -u
cd "$(dirname "$0")" || { echo "[ERROR] No se pudo entrar a la carpeta del proyecto."; exit 1; }
PROYECTO="$(pwd)"
PYVER="(Python no detectado aún)"

error_final() {
    # $1 = paso, $2 = causa, $3 = solución
    echo
    echo "=================================================================="
    echo " [ERROR] La instalación o ejecución NO pudo completarse."
    echo "=================================================================="
    echo " Paso que falló   : $1"
    echo " Qué falló        : $2"
    echo " Qué debe hacer   : $3"
    echo
    echo " --- Información técnica para soporte ---"
    echo " Carpeta del proyecto : $PROYECTO"
    echo " Versión de Python    : $PYVER"
    [ -f "app.py" ] && echo " app.py               : $PROYECTO/app.py" \
                    || echo " app.py               : NO ENCONTRADO"
    [ -f "requirements.txt" ] && echo " requirements.txt     : $PROYECTO/requirements.txt" \
                              || echo " requirements.txt     : NO ENCONTRADO"
    [ -x ".venv/bin/python" ] && echo " Entorno virtual      : $PROYECTO/.venv [existe]" \
                              || echo " Entorno virtual      : no creado"
    echo
    echo " Diagnóstico completo: python3 check_install.py"
    exit 1
}

echo "=================================================================="
echo " Sistema de Personerías y Demandas Ejecutivas"
echo " Carpeta del proyecto: $PROYECTO"
echo "=================================================================="

# --- Paso 1: ZIP no extraído / archivos faltantes ---
if [ ! -f "app.py" ] && [ ! -f "requirements.txt" ]; then
    echo
    echo "[ERROR] Debe extraer el ZIP antes de ejecutar la aplicación."
    echo "No se encontraron app.py ni requirements.txt junto a este archivo."
    echo "Extraiga el ZIP completo y vuelva a ejecutar iniciar_app.sh"
    exit 1
fi
[ -f "app.py" ] || error_final "1 - Verificación de archivos" \
    "Falta el archivo app.py en la carpeta del proyecto." \
    "Vuelva a extraer el ZIP COMPLETO (no copie archivos sueltos) y reintente."
[ -f "requirements.txt" ] || error_final "1 - Verificación de archivos" \
    "Falta el archivo requirements.txt en la carpeta del proyecto." \
    "Vuelva a extraer el ZIP COMPLETO (no copie archivos sueltos) y reintente."

# --- Paso 2: Python ---
PYTHON_CMD=""
if command -v python3 >/dev/null 2>&1; then PYTHON_CMD="python3";
elif command -v python >/dev/null 2>&1; then PYTHON_CMD="python"; fi
[ -n "$PYTHON_CMD" ] || error_final "2 - Detección de Python" \
    "Python 3 no está instalado." \
    "Instálelo desde https://www.python.org/downloads/ (recomendado 3.11 o 3.12)."
PYVER="$("$PYTHON_CMD" --version 2>&1)"
echo "Python detectado: $PYVER"
"$PYTHON_CMD" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' \
    || error_final "2 - Versión de Python" \
       "La versión instalada ($PYVER) es demasiado antigua; se requiere 3.10+." \
       "Instale Python 3.11 o 3.12 desde https://www.python.org/downloads/"

# --- Paso 3: entorno virtual y dependencias ---
if [ ! -x ".venv/bin/python" ]; then
    echo
    echo "Primera ejecución: creando entorno e instalando dependencias."
    echo "Esto puede tardar varios minutos. No cierre esta ventana."
    "$PYTHON_CMD" -m venv .venv || error_final "3 - Creación del entorno virtual" \
        "Python no pudo crear la carpeta .venv." \
        "Borre la carpeta .venv si existe, verifique permisos de escritura y reintente."
    ".venv/bin/python" -m pip install --upgrade pip
    ".venv/bin/python" -m pip install -r requirements.txt \
        || error_final "3 - Instalación de dependencias" \
           "Falló la descarga o instalación de una o más dependencias." \
           "Revise su conexión a internet, borre .venv y reintente. Diagnóstico: python3 check_install.py"
fi

# --- Paso 4: ejecutar la aplicación ---
echo
echo "Iniciando la aplicación... se abrirá en su navegador."
echo "Si no se abre sola, entre a: http://localhost:8501"
echo "Para detenerla presione Ctrl+C."
echo
".venv/bin/python" -m streamlit run app.py
estado=$?
[ $estado -eq 0 ] || error_final "4 - Ejecución de la aplicación" \
    "La aplicación terminó con un error (código $estado). Revise los mensajes de arriba." \
    "Ejecute el diagnóstico (.venv/bin/python check_install.py). Si un Excel de database/ está abierto, ciérrelo y reintente."
exit 0
