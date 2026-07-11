#!/usr/bin/env bash
# ==================================================================
#  Lanzador para macOS / Linux — Sistema de Personerías y Demandas
#  Ejecutivas. Uso: ./iniciar_app.sh
#  Soporta rutas con espacios, tildes y paréntesis como "(1)".
#  La instalación (venv + pip + arranque) la realiza bootstrap.py.
# ==================================================================
set -u
cd "$(dirname "$0")" || { echo "[ERROR] No se pudo entrar a la carpeta del proyecto."; exit 1; }
PROYECTO="$(pwd)"

echo "=================================================================="
echo " Sistema de Personerías y Demandas Ejecutivas"
echo " Carpeta del proyecto: \"$PROYECTO\""
echo "=================================================================="

# --- Paso 1: archivos del proyecto ---
if [ ! -f "app.py" ] && [ ! -f "requirements.txt" ]; then
    echo
    echo "[ERROR] Debe extraer el ZIP antes de ejecutar la aplicación."
    echo "No se encontraron app.py ni requirements.txt junto a este archivo."
    echo "Extraiga el ZIP completo y vuelva a ejecutar iniciar_app.sh"
    exit 1
fi
for f in app.py requirements.txt bootstrap.py; do
    if [ ! -f "$f" ]; then
        echo
        echo "[ERROR] Falta el archivo $f en la carpeta del proyecto."
        echo "Vuelva a extraer el ZIP COMPLETO (no copie archivos sueltos)."
        exit 1
    fi
done

# --- Paso 2: Python ---
PYTHON_CMD=""
if command -v python3 >/dev/null 2>&1; then PYTHON_CMD="python3";
elif command -v python >/dev/null 2>&1; then PYTHON_CMD="python"; fi
if [ -z "$PYTHON_CMD" ]; then
    echo
    echo "[ERROR] Python 3 no está instalado."
    echo "Instálelo desde https://www.python.org/downloads/ (recomendado 3.11 o 3.12)."
    exit 1
fi
echo "Python detectado: $("$PYTHON_CMD" --version 2>&1)"

# --- Paso 3: instalar y ejecutar (bootstrap valida versión mínima) ---
"$PYTHON_CMD" bootstrap.py
estado=$?
if [ $estado -ne 0 ]; then
    echo
    echo "[ERROR] La instalación o ejecución terminó con código $estado."
    echo "Revise los mensajes de arriba y registro_instalacion.txt."
    echo "Diagnóstico completo: $PYTHON_CMD bootstrap.py --diagnostico"
fi
exit $estado
