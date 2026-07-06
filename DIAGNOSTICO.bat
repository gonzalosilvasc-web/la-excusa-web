@echo off
setlocal EnableExtensions
chcp 65001 >nul
title Diagnostico - Sistema de Personerias y Demandas

rem ==================================================================
rem  DIAGNOSTICO.bat - chequeo completo del entorno de la aplicacion.
rem  No modifica nada (solo crea un archivo temporal de prueba de
rem  escritura que luego borra). La ventana siempre queda abierta.
rem ==================================================================

cd /d "%~dp0"
echo ==================================================================
echo  DIAGNOSTICO DEL SISTEMA
echo  Carpeta: %CD%
echo  Fecha  : %DATE% %TIME%
echo ==================================================================
echo.

echo --- 1. Archivos del proyecto ---
if exist "app.py" (echo [OK]    app.py) else (echo [FALLA] app.py NO ENCONTRADO - extraiga el ZIP completo)
if exist "requirements.txt" (echo [OK]    requirements.txt) else (echo [FALLA] requirements.txt NO ENCONTRADO)
if exist "check_install.py" (echo [OK]    check_install.py) else (echo [FALLA] check_install.py NO ENCONTRADO)
if exist "legal" (echo [OK]    carpeta legal\) else (echo [FALLA] carpeta legal\ NO ENCONTRADA)
echo.

echo --- 2. Python ---
set "PYTHON_CMD="
where python >nul 2>nul && set "PYTHON_CMD=python"
if not defined PYTHON_CMD (
    where py >nul 2>nul && set "PYTHON_CMD=py -3"
)
if not defined PYTHON_CMD (
    echo [FALLA] Python no esta instalado o no esta en el PATH.
    echo         Instale desde https://www.python.org/downloads/ marcando "Add Python to PATH".
    goto :fin
)
for /f "delims=" %%v in ('%PYTHON_CMD% --version 2^>^&1') do echo [OK]    %%v  (comando: %PYTHON_CMD%)
echo.

echo --- 3. pip ---
%PYTHON_CMD% -m pip --version 2>nul && (echo [OK]    pip disponible) || (echo [FALLA] pip no disponible - reinstale Python)
echo.

echo --- 4. Entorno virtual ---
if exist ".venv\Scripts\python.exe" (
    echo [OK]    .venv existe
    set "APP_PY=.venv\Scripts\python.exe"
) else (
    echo [AVISO] .venv aun no existe - se creara al ejecutar INICIAR_APP.bat
    set "APP_PY=%PYTHON_CMD%"
)
echo.

echo --- 5. Permisos de escritura ---
echo prueba > "_test_escritura.tmp" 2>nul
if exist "_test_escritura.tmp" (
    del "_test_escritura.tmp" >nul 2>nul
    echo [OK]    Se puede escribir en la carpeta del proyecto
) else (
    echo [FALLA] NO se puede escribir en esta carpeta.
    echo         Mueva el proyecto a Documentos o ejecute desde otra ubicacion.
)
echo.

echo --- 6. Dependencias, carpetas y verificacion completa ---
echo (ejecutando check_install.py ...)
echo.
%APP_PY% check_install.py
echo.

:fin
echo ==================================================================
echo  Fin del diagnostico. Copie esta pantalla si necesita soporte.
echo ==================================================================
pause
