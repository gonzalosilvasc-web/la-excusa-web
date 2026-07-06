@echo off
setlocal EnableExtensions
chcp 65001 >nul
title Sistema de Personerias y Demandas Ejecutivas

rem ==================================================================
rem  Lanzador para Windows - doble clic para abrir la aplicacion.
rem  Soporta rutas con espacios, tildes, caracteres especiales y
rem  carpetas dentro de OneDrive. Ante cualquier error la ventana
rem  queda abierta con un diagnostico completo.
rem  Diagnostico manual: doble clic en DIAGNOSTICO.bat
rem ==================================================================

rem --- Paso 0: ubicarse SIEMPRE en la carpeta real de este archivo ---
cd /d "%~dp0"
if errorlevel 1 (
    set "PASO=0 - Ubicarse en la carpeta del proyecto"
    set "CAUSA=No se pudo entrar a la carpeta: %~dp0"
    set "SOLUCION=Mueva la carpeta del proyecto a una ruta accesible (por ejemplo Documentos) y reintente."
    goto :error
)
set "PROYECTO=%CD%"
set "PYVER=(Python no detectado aun)"

echo ==================================================================
echo  Sistema de Personerias y Demandas Ejecutivas
echo  Carpeta del proyecto: %PROYECTO%
echo ==================================================================
echo.

rem --- Paso 1: detectar ZIP no extraido / archivos faltantes ---------
if not exist "app.py" if not exist "requirements.txt" (
    echo ==================================================================
    echo  [ERROR] Debe extraer el ZIP antes de ejecutar la aplicacion.
    echo ==================================================================
    echo.
    echo  No se encontraron app.py ni requirements.txt junto a este archivo.
    echo  Esto ocurre cuando se hace doble clic DENTRO del ZIP sin extraerlo.
    echo.
    echo  Como corregirlo:
    echo   1. Cierre esta ventana.
    echo   2. Clic derecho sobre el archivo ZIP descargado.
    echo   3. Elija "Extraer todo..." y presione Extraer.
    echo   4. Abra la carpeta extraida y haga doble clic en INICIAR_APP.bat
    echo.
    echo  Carpeta actual: %PROYECTO%
    echo.
    pause
    exit /b 1
)
if not exist "app.py" (
    set "PASO=1 - Verificacion de archivos del proyecto"
    set "CAUSA=Falta el archivo app.py en la carpeta del proyecto."
    set "SOLUCION=Vuelva a extraer el ZIP COMPLETO (no copie archivos sueltos) y reintente."
    goto :error
)
if not exist "requirements.txt" (
    set "PASO=1 - Verificacion de archivos del proyecto"
    set "CAUSA=Falta el archivo requirements.txt en la carpeta del proyecto."
    set "SOLUCION=Vuelva a extraer el ZIP COMPLETO (no copie archivos sueltos) y reintente."
    goto :error
)

rem --- Paso 2: detectar Python ---------------------------------------
set "PYTHON_CMD="
where python >nul 2>nul && set "PYTHON_CMD=python"
if not defined PYTHON_CMD (
    where py >nul 2>nul && set "PYTHON_CMD=py -3"
)
if not defined PYTHON_CMD (
    echo ==================================================================
    echo  [ERROR] Python no esta instalado o no esta en el PATH.
    echo ==================================================================
    echo.
    echo  Como corregirlo:
    echo   1. Descargue Python desde: https://www.python.org/downloads/
    echo   2. Al instalar, MARQUE la casilla "Add Python to PATH".
    echo   3. Termine la instalacion, cierre esta ventana y vuelva a
    echo      hacer doble clic en INICIAR_APP.bat
    echo.
    echo  Recomendado: Python 3.11 o 3.12 (3.13 tambien es compatible).
    echo  Carpeta actual: %PROYECTO%
    echo.
    pause
    exit /b 1
)
for /f "delims=" %%v in ('%PYTHON_CMD% --version 2^>^&1') do set "PYVER=%%v"
echo Python detectado: %PYVER%

%PYTHON_CMD% -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>nul
if errorlevel 1 (
    set "PASO=2 - Verificacion de version de Python"
    set "CAUSA=La version instalada (%PYVER%) es demasiado antigua. Se requiere Python 3.10 o superior."
    set "SOLUCION=Instale Python 3.11 o 3.12 desde https://www.python.org/downloads/ marcando 'Add Python to PATH'."
    goto :error
)

rem --- Paso 3: entorno virtual e instalacion de dependencias ---------
if exist ".venv\Scripts\python.exe" goto :venv_listo
echo.
echo Primera ejecucion: creando entorno e instalando dependencias.
echo Esto puede tardar varios minutos. NO cierre esta ventana.
echo.
%PYTHON_CMD% -m venv .venv
if errorlevel 1 (
    set "PASO=3 - Creacion del entorno virtual (.venv)"
    set "CAUSA=Python no pudo crear el entorno virtual."
    set "SOLUCION=Ejecute DIAGNOSTICO.bat. Si la carpeta esta en OneDrive, pruebe pausar la sincronizacion o mover el proyecto a Documentos. Borre la carpeta .venv si existe y reintente."
    goto :error
)
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    set "PASO=3 - Instalacion de dependencias (pip install -r requirements.txt)"
    set "CAUSA=Fallo la descarga o instalacion de una o mas dependencias."
    set "SOLUCION=Revise su conexion a internet, borre la carpeta .venv y vuelva a intentar. Si persiste, ejecute DIAGNOSTICO.bat y revise el mensaje de pip mas arriba."
    goto :error
)
:venv_listo

rem --- Paso 4: ejecutar la aplicacion ---------------------------------
echo.
echo Iniciando la aplicacion... se abrira sola en su navegador.
echo Si no se abre, entre manualmente a: http://localhost:8501
echo Para detener la aplicacion: cierre esta ventana o presione Ctrl+C.
echo.
".venv\Scripts\python.exe" -m streamlit run app.py
if errorlevel 1 (
    set "PASO=4 - Ejecucion de la aplicacion (streamlit run app.py)"
    set "CAUSA=La aplicacion termino con un error. Revise los mensajes de arriba."
    set "SOLUCION=Ejecute DIAGNOSTICO.bat para un chequeo completo. Si un archivo Excel de la carpeta database esta abierto, cierrelo y reintente."
    goto :error
)
echo.
echo La aplicacion se cerro normalmente.
pause
exit /b 0

rem --- Bloque de error con diagnostico completo -----------------------
:error
echo.
echo ==================================================================
echo  [ERROR] La instalacion o ejecucion NO pudo completarse.
echo ==================================================================
echo.
echo  Paso que fallo   : %PASO%
echo  Que fallo        : %CAUSA%
echo  Que debe hacer   : %SOLUCION%
echo.
echo  --- Informacion tecnica para soporte ---
echo  Carpeta del proyecto : %PROYECTO%
echo  Version de Python    : %PYVER%
if exist "app.py" (echo  app.py               : %PROYECTO%\app.py) else (echo  app.py               : NO ENCONTRADO)
if exist "requirements.txt" (echo  requirements.txt     : %PROYECTO%\requirements.txt) else (echo  requirements.txt     : NO ENCONTRADO)
if exist ".venv\Scripts\python.exe" (echo  Entorno virtual      : %PROYECTO%\.venv [existe]) else (echo  Entorno virtual      : no creado)
echo.
echo  Diagnostico completo: doble clic en DIAGNOSTICO.bat
echo.
pause
exit /b 1
