@echo off
chcp 65001 >nul
title Sistema de Personerias - Santander / GRC
cd /d "%~dp0"

echo ============================================
echo  Sistema de Gestion de Personerias
echo ============================================
echo.

where python >/dev/null 2>nul
if errorlevel 1 (
    echo [ERROR] Python no esta instalado o no esta en el PATH.
    echo.
    echo Descarguelo desde: https://www.python.org/downloads/
    echo IMPORTANTE: durante la instalacion marque "Add Python to PATH".
    echo.
    pause
    exit /b 1
)

if not exist ".venv" (
    echo Primera ejecucion: creando entorno e instalando dependencias...
    echo Esto puede tardar unos minutos. Solo ocurre una vez.
    echo.
    python -m venv .venv
    call ".venv\Scripts\activate.bat"
    python -m pip install --upgrade pip
    pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo [ERROR] Fallo la instalacion de dependencias. Revise su conexion a internet.
        pause
        exit /b 1
    )
) else (
    call ".venv\Scripts\activate.bat"
)

echo.
echo Iniciando la aplicacion... se abrira en su navegador.
echo Para detenerla, cierre esta ventana o presione Ctrl+C.
echo.
streamlit run app.py
pause
