@echo off
setlocal EnableExtensions
title Sistema de Personerias y Demandas Ejecutivas

rem ==================================================================
rem  Lanzador para Windows - doble clic para abrir la aplicacion.
rem  Este archivo NO usa bloques con parentesis: soporta rutas con
rem  espacios, tildes, OneDrive y parentesis como "(1)".
rem  Si la ventana se cierra sola sin mostrar nada, use
rem  INICIAR_APP_SEGURO.bat. Diagnostico: DIAGNOSTICO.bat
rem ==================================================================

set "PROYECTO=(desconocida)"
set "PYVER=Python no detectado"
set "PYTHON_CMD="

rem --- Paso 0: ubicarse en la carpeta real de este archivo ------------
cd /d "%~dp0" 2>nul
if exist "%~nx0" goto :carpeta_ok
echo ==================================================================
echo  [ERROR] Paso 0: no se pudo entrar a la carpeta del proyecto.
echo ==================================================================
echo  Carpeta esperada: "%~dp0"
echo  Que hacer: mueva la carpeta del proyecto a una ruta accesible,
echo  por ejemplo Documentos, y vuelva a intentar.
echo.
pause
exit /b 1

:carpeta_ok
set "PROYECTO=%CD%"
set "LOG=%PROYECTO%\registro_instalacion.txt"
echo ==================================================================
echo  Sistema de Personerias y Demandas Ejecutivas
echo  Carpeta del proyecto: "%PROYECTO%"
echo ==================================================================
echo.

rem --- Paso 1: archivos del proyecto ----------------------------------
if exist "app.py" goto :app_presente
if exist "requirements.txt" goto :falta_app
goto :zip_no_extraido

:app_presente
if exist "requirements.txt" goto :archivos_ok
goto :falta_requirements

:zip_no_extraido
echo ==================================================================
echo  [ERROR] Debe extraer el ZIP antes de ejecutar la aplicacion.
echo ==================================================================
echo.
echo  No se encontraron app.py ni requirements.txt junto a este archivo.
echo  Esto ocurre al hacer doble clic DENTRO del ZIP sin extraerlo.
echo.
echo  Como corregirlo:
echo   1. Cierre esta ventana.
echo   2. Clic derecho sobre el archivo ZIP descargado.
echo   3. Elija "Extraer todo..." y presione Extraer.
echo   4. Abra la carpeta extraida y doble clic en INICIAR_APP.bat
echo.
echo  Carpeta actual: "%PROYECTO%"
echo.
pause
exit /b 1

:falta_app
set "PASO=1 - Verificacion de archivos"
set "CAUSA=Falta el archivo app.py en la carpeta del proyecto."
set "SOLUCION=Vuelva a extraer el ZIP COMPLETO, sin copiar archivos sueltos."
goto :error

:falta_requirements
set "PASO=1 - Verificacion de archivos"
set "CAUSA=Falta el archivo requirements.txt en la carpeta del proyecto."
set "SOLUCION=Vuelva a extraer el ZIP COMPLETO, sin copiar archivos sueltos."
goto :error

:archivos_ok
if exist "bootstrap.py" goto :bootstrap_ok
set "PASO=1 - Verificacion de archivos"
set "CAUSA=Falta el archivo bootstrap.py en la carpeta del proyecto."
set "SOLUCION=Vuelva a extraer el ZIP COMPLETO, sin copiar archivos sueltos."
goto :error

:bootstrap_ok
echo [%DATE% %TIME%] INICIO lanzador>>"%LOG%"

rem --- Paso 2: detectar Python (primero py -3, luego python) ----------
py -3 --version >nul 2>nul
if not errorlevel 1 set "PYTHON_CMD=py -3"
if defined PYTHON_CMD goto :python_ok
python --version >nul 2>nul
if not errorlevel 1 set "PYTHON_CMD=python"
if defined PYTHON_CMD goto :python_ok

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
echo  Carpeta actual: "%PROYECTO%"
echo.
pause
exit /b 1

:python_ok
for /f "delims=" %%v in ('%PYTHON_CMD% --version 2^>^&1') do set "PYVER=%%v"
echo Python detectado: %PYVER%
echo [%DATE% %TIME%] Paso 2 OK - %PYVER%>>"%LOG%"

rem --- Paso 3: instalar y ejecutar via bootstrap.py -------------------
rem  bootstrap.py decide la ubicacion del entorno virtual: si la ruta
rem  del proyecto es larga usa una ruta corta externa en LOCALAPPDATA
rem  para evitar fallas de pip por el limite MAX_PATH de Windows.
%PYTHON_CMD% bootstrap.py
if errorlevel 1 goto :fallo_bootstrap
echo.
echo La aplicacion se cerro normalmente.
pause
exit /b 0

:fallo_bootstrap
set "PASO=3 - Instalacion o ejecucion (bootstrap.py)"
set "CAUSA=Revise el mensaje especifico impreso mas arriba por el instalador."
set "SOLUCION=Ejecute DIAGNOSTICO.bat y revise registro_instalacion.txt. Si un Excel de database esta abierto, cierrelo y reintente."
goto :error

rem --- Bloque de error (sin parentesis; variables precalculadas) ------
:error
set "INFO_APP=NO ENCONTRADO"
if exist "app.py" set "INFO_APP=presente"
set "INFO_REQ=NO ENCONTRADO"
if exist "requirements.txt" set "INFO_REQ=presente"
set "INFO_VENV=no creado en el proyecto"
if exist ".venv\Scripts\python.exe" set "INFO_VENV=existe (.venv local)"
echo [%DATE% %TIME%] ERROR %PASO%>>"%LOG%" 2>nul
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
echo  Carpeta del proyecto : "%PROYECTO%"
echo  Version de Python    : %PYVER%
echo  app.py               : %INFO_APP%
echo  requirements.txt     : %INFO_REQ%
echo  Entorno virtual local: %INFO_VENV%
echo  Registro guardado en : registro_instalacion.txt
echo.
echo  Diagnostico completo: doble clic en DIAGNOSTICO.bat
echo.
pause
exit /b 1
