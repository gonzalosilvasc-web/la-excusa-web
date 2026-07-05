#!/usr/bin/env bash
# Lanzador para macOS / Linux — Sistema de Gestión de Personerías
# Uso: doble clic (si el sistema lo permite) o en terminal: ./iniciar_app.sh
set -e
cd "$(dirname "$0")"

echo "============================================"
echo " Sistema de Gestión de Personerías"
echo "============================================"

if ! command -v python3 >/dev/null 2>&1; then
    echo "[ERROR] Python 3 no está instalado."
    echo "Descárguelo desde https://www.python.org/downloads/"
    exit 1
fi

if [ ! -d ".venv" ]; then
    echo "Primera ejecución: creando entorno e instalando dependencias..."
    echo "Esto puede tardar unos minutos. Solo ocurre una vez."
    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install --upgrade pip
    pip install -r requirements.txt
else
    source .venv/bin/activate
fi

echo
echo "Iniciando la aplicación... se abrirá en su navegador."
echo "Para detenerla presione Ctrl+C."
echo
streamlit run app.py
