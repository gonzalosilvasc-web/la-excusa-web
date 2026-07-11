@echo off
setlocal EnableExtensions
title Diagnostico - Sistema de Personerias y Demandas

rem ==================================================================
rem  DIAGNOSTICO.bat - chequeo completo del entorno. No usa bloques
rem  con parentesis: funciona en rutas con espacios, tildes y "(1)".
rem  Solo crea un archivo temporal de prueba de escritura que borra.
rem ==================================================================

cd /d "%~dp0" 2>nul
echo ==================================================================
echo  DIAGNOSTICO DEL SISTEMA
echo  Carpeta: "%CD%"
echo  Fecha  : %DATE% %TIME%
echo ==================================================================
echo.

echo --- 1. Ruta del proyecto ---
echo La ruta actual, con espacios, tildes o parentesis, es soportada.
echo Largo y riesgo de ruta larga: se detallan en la seccion 6.
echo.

echo --- 2. Archivos del proyecto ---
set "F_APP=[FALLA] app.py NO ENCONTRADO - extraiga el ZIP completo"
if exist "app.py" set "F_APP=[OK]    app.py"
echo %F_APP%
set "F_REQ=[FALLA] requirements.txt NO ENCONTRADO"
if exist "requirements.txt" set "F_REQ=[OK]    requirements.txt"
echo %F_REQ%
set "F_BOOT=[FALLA] bootstrap.py NO ENCONTRADO"
if exist "bootstrap.py" set "F_BOOT=[OK]    bootstrap.py"
echo %F_BOOT%
set "F_CHK=[FALLA] check_install.py NO ENCONTRADO"
if exist "check_install.py" set "F_CHK=[OK]    check_install.py"
echo %F_CHK%
set "F_LEGAL=[FALLA] carpeta legal\ NO ENCONTRADA"
if exist "legal" set "F_LEGAL=[OK]    carpeta legal\"
echo %F_LEGAL%
echo.

echo --- 3. Python ---
set "PYTHON_CMD="
py -3 --version >nul 2>nul
if not errorlevel 1 set "PYTHON_CMD=py -3"
if defined PYTHON_CMD goto :python_ok
python --version >nul 2>nul
if not errorlevel 1 set "PYTHON_CMD=python"
if defined PYTHON_CMD goto :python_ok
echo [FALLA] Python no esta instalado o no esta en el PATH.
echo         Instale desde https://www.python.org/downloads/
echo         marcando la casilla "Add Python to PATH".
goto :fin

:python_ok
for /f "delims=" %%v in ('%PYTHON_CMD% --version 2^>^&1') do echo [OK]    %%v - comando: %PYTHON_CMD%
echo.

echo --- 4. pip ---
%PYTHON_CMD% -m pip --version 2>nul
if errorlevel 1 echo [FALLA] pip no disponible - reinstale Python
if not errorlevel 1 echo [OK]    pip disponible
echo.

echo --- 5. Permisos de escritura ---
echo prueba > "_test_escritura.tmp" 2>nul
if not exist "_test_escritura.tmp" goto :sin_escritura
del "_test_escritura.tmp" >nul 2>nul
echo [OK]    Se puede escribir en la carpeta del proyecto
goto :escritura_lista
:sin_escritura
echo [FALLA] NO se puede escribir en esta carpeta.
echo         Mueva el proyecto a Documentos o ejecute desde otra ubicacion.
:escritura_lista
echo.

echo --- 6. Rutas, entorno virtual, dependencias y seguridad ---
echo Ejecutando bootstrap.py --diagnostico
echo   - muestra ruta del proyecto, ruta real del venv y riesgo MAX_PATH
echo   - corre check_install.py con el Python del venv si existe
echo.
%PYTHON_CMD% bootstrap.py --diagnostico

:fin
echo.
echo ==================================================================
echo  Fin del diagnostico. Copie esta pantalla si necesita soporte.
echo ==================================================================
pause
