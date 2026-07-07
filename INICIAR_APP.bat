@echo off
setlocal EnableExtensions
title Sistema de Personerias y Demandas Ejecutivas

rem ==================================================================
rem  Lanzador para Windows - doble clic para abrir la aplicacion.
rem  Si la ventana se cierra sola sin mostrar nada, use
rem  INICIAR_APP_SEGURO.bat (mantiene la ventana abierta siempre).
rem  Diagnostico manual: doble clic en DIAGNOSTICO.bat
rem ==================================================================

rem --- Paso 0: ubicarse SIEMPRE en la carpeta real de este archivo ---
set "PROYECTO=(desconocida)"
set "PYVER=(Python no detectado aun)"
cd /d "%~dp0" 2>nul
if not exist "%~nx0" (
    set "PASO=0 - Ubicarse en la carpeta del proyecto"
    set "CAUSA=No se pudo entrar a la carpeta: %~dp0"
    set "SOLUCION=Mueva la carpeta del proyecto a una ruta accesible, por ejemplo Documentos, y reintente."
    goto :error
)
set "PROYECTO=%CD%"
set "LOG=%PROYECTO%\registro_instalacion.txt"
echo [%DATE% %TIME%] INICIO - carpeta: %PROYECTO%>>"%LOG%"

echo ==================================================================
echo  Sistema de Personerias y Demandas Ejecutivas
echo  Carpeta del proyecto: %PROYECTO%
echo ==================================================================
echo.

rem --- Aviso de ruta demasiado larga (limite MAX_PATH de Windows) ----
if not "%PROYECTO:~150,1%"=="" (
    echo  [AVISO] La ruta de esta carpeta es MUY LARGA y Windows puede
    echo  fallar al instalar. Si algo falla, mueva esta carpeta a
    echo  C:\demandas o a Documentos con un nombre corto y reintente.
    echo.
    echo [%DATE% %TIME%] AVISO ruta larga>>"%LOG%"
)

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
    set "SOLUCION=Vuelva a extraer el ZIP COMPLETO, sin copiar archivos sueltos, y reintente."
    goto :error
)
if not exist "requirements.txt" (
    set "PASO=1 - Verificacion de archivos del proyecto"
    set "CAUSA=Falta el archivo requirements.txt en la carpeta del proyecto."
    set "SOLUCION=Vuelva a extraer el ZIP COMPLETO, sin copiar archivos sueltos, y reintente."
    goto :error
)
echo [%DATE% %TIME%] Paso 1 OK - archivos presentes>>"%LOG%"

rem --- Paso 2: detectar Python ---------------------------------------
set "PYTHON_CMD="
py -3 --version >nul 2>nul
if not errorlevel 1 set "PYTHON_CMD=py -3"
if not defined PYTHON_CMD (
    python --version >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=python"
)
if not defined PYTHON_CMD (
    echo [%DATE% %TIME%] Paso 2 FALLA - sin Python>>"%LOG%"
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
    echo  Recomendado: Python 3.11 o 3.12. Tambien es compatible 3.13.
    echo  Carpeta actual: %PROYECTO%
    echo.
    pause
    exit /b 1
)
for /f "delims=" %%v in ('%PYTHON_CMD% --version 2^>^&1') do set "PYVER=%%v"
echo Python detectado: %PYVER%
echo [%DATE% %TIME%] Paso 2 OK - %PYVER% via %PYTHON_CMD%>>"%LOG%"

%PYTHON_CMD% -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>nul
if errorlevel 1 (
    set "PASO=2 - Verificacion de version de Python"
    set "CAUSA=La version instalada %PYVER% es demasiado antigua. Se requiere Python 3.10 o superior."
    set "SOLUCION=Instale Python 3.11 o 3.12 desde https://www.python.org/downloads/ marcando 'Add Python to PATH'."
    goto :error
)

rem --- Paso 3: entorno virtual e instalacion de dependencias ---------
if exist ".venv\Scripts\python.exe" goto :venv_listo
echo.
echo Primera ejecucion: creando entorno e instalando dependencias.
echo Esto puede tardar VARIOS MINUTOS. NO cierre esta ventana.
echo.
echo [%DATE% %TIME%] Paso 3 - creando .venv>>"%LOG%"
%PYTHON_CMD% -m venv .venv
if errorlevel 1 (
    echo [%DATE% %TIME%] Paso 3 FALLA - venv>>"%LOG%"
    set "PASO=3 - Creacion del entorno virtual .venv"
    set "CAUSA=Python no pudo crear el entorno virtual."
    set "SOLUCION=Ejecute DIAGNOSTICO.bat. Si la carpeta esta en OneDrive, pause la sincronizacion o mueva el proyecto a Documentos. Borre la carpeta .venv si existe y reintente."
    goto :error
)
echo [%DATE% %TIME%] Paso 3 - instalando dependencias>>"%LOG%"
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo [%DATE% %TIME%] Paso 3 FALLA - pip install>>"%LOG%"
    set "PASO=3 - Instalacion de dependencias con pip"
    set "CAUSA=Fallo la descarga o instalacion de una o mas dependencias."
    set "SOLUCION=Revise su conexion a internet, borre la carpeta .venv y vuelva a intentar. Si persiste, ejecute DIAGNOSTICO.bat y revise el mensaje de pip mas arriba."
    goto :error
)
echo [%DATE% %TIME%] Paso 3 OK - dependencias instaladas>>"%LOG%"
:venv_listo

rem --- Paso 4: activar el entorno virtual (rutas siempre entre comillas)
call ".venv\Scripts\activate.bat"
if errorlevel 1 (
    set "PASO=4 - Activacion del entorno virtual"
    set "CAUSA=No se pudo activar el entorno virtual .venv"
    set "SOLUCION=Borre la carpeta .venv y vuelva a ejecutar INICIAR_APP.bat"
    goto :error
)

rem --- Paso 5: evitar que Streamlit pida un Email y bloquee todo ------
rem  En el primer arranque Streamlit pregunta un email en la consola y
rem  NO abre el navegador hasta que se responda. Se omite creando la
rem  credencial vacia por adelantado.
if not exist "%USERPROFILE%\.streamlit" mkdir "%USERPROFILE%\.streamlit" >nul 2>nul
if not exist "%USERPROFILE%\.streamlit\credentials.toml" (
    echo [general]>"%USERPROFILE%\.streamlit\credentials.toml"
    echo email = "">>"%USERPROFILE%\.streamlit\credentials.toml"
)
set "STREAMLIT_BROWSER_GATHER_USAGE_STATS=false"

rem --- Paso 6: ejecutar la aplicacion ---------------------------------
echo.
echo Iniciando la aplicacion... se abrira sola en su navegador.
echo Si no se abre, entre manualmente a: http://localhost:8501
echo Para detener la aplicacion: cierre esta ventana o presione Ctrl+C.
echo.
echo [%DATE% %TIME%] Paso 6 - lanzando streamlit>>"%LOG%"
python -m streamlit run app.py
if errorlevel 1 (
    echo [%DATE% %TIME%] Paso 6 FALLA - streamlit termino con error>>"%LOG%"
    set "PASO=6 - Ejecucion de la aplicacion con streamlit"
    set "CAUSA=La aplicacion termino con un error. Revise los mensajes de arriba."
    set "SOLUCION=Ejecute DIAGNOSTICO.bat para un chequeo completo. Si un archivo Excel de la carpeta database esta abierto, cierrelo y reintente."
    goto :error
)
echo [%DATE% %TIME%] FIN normal>>"%LOG%"
echo.
echo La aplicacion se cerro normalmente.
pause
exit /b 0

rem --- Bloque de error con diagnostico completo -----------------------
:error
echo [%DATE% %TIME%] ERROR paso: %PASO% causa: %CAUSA%>>"%LOG%" 2>nul
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
echo  Se guardo un registro en: registro_instalacion.txt
echo  Diagnostico completo: doble clic en DIAGNOSTICO.bat
echo.
pause
exit /b 1
