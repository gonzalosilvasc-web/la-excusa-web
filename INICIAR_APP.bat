@echo off
setlocal EnableExtensions
chcp 65001 >nul
title Sistema de Personerias y Demandas Ejecutivas

rem ============================================================
rem  Lanzador para Windows - doble clic para abrir la aplicacion
rem  Soporta rutas con espacios, tildes y carpetas OneDrive.
rem ============================================================

rem Ubicarse SIEMPRE en la carpeta real de este archivo (%~dp0)
cd /d "%~dp0"
if errorlevel 1 (
    echo [ERROR] No se pudo entrar a la carpeta del proyecto:
    echo   %~dp0
    echo.
    pause
    exit /b 1
)

echo ============================================================
echo  Sistema de Personerias y Demandas Ejecutivas
echo  Carpeta: %CD%
echo ============================================================
echo.

rem --- Deteccion de ZIP no extraido -------------------------------
rem Si faltan los archivos del proyecto junto al .bat, lo mas probable
rem es que el usuario hizo doble clic DENTRO del ZIP sin extraerlo
rem (Windows extrae solo el .bat a una carpeta temporal).
if not exist "app.py" goto :zip_no_extraido
if not exist "requirements.txt" goto :zip_no_extraido
goto :zip_ok

:zip_no_extraido
echo ============================================================
echo  [ERROR] Debe extraer el ZIP antes de ejecutar la aplicacion.
echo ============================================================
echo.
echo  No se encontraron app.py / requirements.txt junto a este archivo.
echo.
echo  Como corregirlo:
echo   1. Cierre esta ventana.
echo   2. Clic derecho sobre el archivo ZIP descargado.
echo   3. Elija "Extraer todo..." y presione Extraer.
echo   4. Abra la carpeta extraida y haga doble clic en INICIAR_APP.bat
echo.
pause
exit /b 1

:zip_ok

rem --- Deteccion de Python ----------------------------------------
set "PYTHON_CMD="
where python >/dev/null 2>/dev/null && set "PYTHON_CMD=python"
if not defined PYTHON_CMD (
    where py >/dev/null 2>/dev/null && set "PYTHON_CMD=py -3"
)
if not defined PYTHON_CMD (
    echo ============================================================
    echo  [ERROR] Python no esta instalado o no esta en el PATH.
    echo ============================================================
    echo.
    echo  Como corregirlo:
    echo   1. Descargue Python desde: https://www.python.org/downloads/
    echo   2. Al instalar, MARQUE la casilla "Add Python to PATH".
    echo   3. Termine la instalacion y vuelva a hacer doble clic aqui.
    echo.
    pause
    exit /b 1
)

rem Verificar version minima 3.10
%PYTHON_CMD% -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >/dev/null 2>nul
if errorlevel 1 (
    echo [ERROR] Se requiere Python 3.10 o superior.
    %PYTHON_CMD% --version
    echo Instale una version reciente desde https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

rem --- Entorno virtual e instalacion de dependencias --------------
if not exist ".venv\Scripts\python.exe" (
    echo Primera ejecucion: creando entorno e instalando dependencias.
    echo Esto puede tardar varios minutos. NO cierre esta ventana.
    echo.
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 (
        echo [ERROR] No se pudo crear el entorno virtual .venv
        echo Revise que Python este bien instalado.
        echo.
        pause
        exit /b 1
    )
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo [ERROR] Fallo la instalacion de dependencias.
        echo Revise su conexion a internet y vuelva a intentar.
        echo Si el problema persiste, borre la carpeta .venv y reintente.
        echo.
        pause
        exit /b 1
    )
)

rem --- Ejecutar la aplicacion --------------------------------------
echo.
echo Iniciando la aplicacion... se abrira en su navegador.
echo Para detenerla: cierre esta ventana o presione Ctrl+C.
echo.
".venv\Scripts\python.exe" -m streamlit run app.py
if errorlevel 1 (
    echo.
    echo [ERROR] La aplicacion termino con un error. Revise los mensajes
    echo de arriba. Puede ejecutar el diagnostico con:
    echo   .venv\Scripts\python.exe check_install.py
    echo.
)
pause
