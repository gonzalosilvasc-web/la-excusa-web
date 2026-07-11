@echo off
rem Version a prueba de fallas: ejecuta el lanzador normal y deja la
rem ventana SIEMPRE abierta al final, incluso ante un error inesperado
rem dentro del lanzador (al usar "call", el control siempre vuelve aqui).
call "%~dp0INICIAR_APP.bat"
echo.
echo Ventana segura: presione una tecla para cerrar.
pause
