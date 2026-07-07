@echo off
rem Version a prueba de fallas: mantiene la ventana SIEMPRE abierta,
rem incluso si INICIAR_APP.bat tuviera un error inesperado.
cmd /k call "%~dp0INICIAR_APP.bat"
