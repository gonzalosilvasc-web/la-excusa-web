# TEST_REPORT — Auditoría final de instalación y estabilidad

**Fecha de ejecución:** 07/07/2026
**Entorno de pruebas:** Linux (contenedor), Python 3.11.15, Streamlit 1.58.0, Wine 9.0
**Suite automatizada:** `python tests/test_flujo.py` → **52/52 verificaciones PASAN**
**Verificador:** `python check_install.py` → **todos los chequeos OK, exit 0**

## ⚠️ Declaración sobre la validación en Windows

> **Validación directa en Windows real: NO EJECUTADA.**
> **Validación equivalente realizada en Wine/Linux: PASA.**

Wine **no reemplaza una prueba real en Windows**. El doble clic de
`INICIAR_APP.bat` en un Windows físico sigue siendo la única verificación
definitiva y queda pendiente para el primer uso del usuario. Lo que sí se
ejecutó de manera verificable:

- **Wine (cmd.exe real de Wine 9.0):** los 4 escenarios de error del `.bat`
  (ZIP no extraído, falta `app.py`, falta `requirements.txt`, falta Python)
  y `DIAGNOSTICO.bat`, todos con el mensaje correcto, diagnóstico completo y
  `pause` final. Incluye una carpeta con espacios y tilde ("sin python á").
- **Límite de Wine en este entorno:** el flujo completo (crear venv +
  instalar + abrir la app) requiere Python de Windows dentro de Wine; la
  política de red del contenedor bloquea la descarga del instalador desde
  python.org (403), por lo que ese tramo NO se ejecutó bajo Wine. Ese mismo
  tramo se validó con `iniciar_app.sh` (lógica idéntica paso a paso) en la
  instalación limpia desde ZIP.

### Bugs reales encontrados GRACIAS a Wine (y corregidos)

1. **Paréntesis sin escapar dentro de un bloque `if`:** el texto
   `(3.13 tambien es compatible)` en un `echo` cortaba el bloque — esto
   **también fallaría en Windows real**. Corregido (texto sin paréntesis).
2. **`errorlevel` heredado de `chcp`:** el chequeo posterior a `cd /d` podía
   disparar un falso error de Paso 0. Corregido: tras el `cd` se verifica la
   existencia del propio lanzador (`%~nx0`), método inmune a ese problema.
3. **Operadores `&&`/`||`:** el cmd de Wine ejecuta ambas ramas (bug de
   Wine, no de Windows). Se eliminaron TODOS los `&&`/`||` de ambos `.bat`
   en favor de `if errorlevel` / `if exist` / `if defined`, cuyo
   comportamiento es idéntico y documentado en Windows real — el `.bat`
   quedó más robusto y además verificable bajo Wine.

## Pruebas obligatorias

| # | Prueba | Resultado | Evidencia | Observaciones / Corrección aplicada |
|---|--------|-----------|-----------|--------------------------------------|
| 1 | Instalación limpia desde ZIP | **PASA** (Linux; Windows real NO EJECUTADA) | ZIP `git archive` de la versión final → extraído en carpeta nueva → SOLO el lanzador → `.venv` creado, dependencias instaladas, app sirviendo HTTP 200 en ~45 s; interfaz verificada antes en Chromium real (9 pestañas, datos de ejemplo, búsqueda de personería con texto legal). Raíz del ZIP verificada: 10 archivos requeridos presentes (+`requirements-ia.txt`, `legal/`, `tests/`). | Rama feliz del `.bat` no ejecutable bajo Wine por bloqueo de red al instalador de Python; equivalente `.sh` idéntico paso a paso. |
| 2 | Ruta compleja (espacios/tildes/OneDrive) | **PASA** | Instalación completa dentro de `…/OneDrive - Estudio Jurídico/Descargas Peñá/…` (Linux) y escenario Wine en carpeta `sin python á` — ambas rutas navegadas correctamente. | `.bat` ASCII puro, CRLF, todas las rutas entre comillas, `cd /d "%~dp0"`, sin expansión retardada (soporta `!` en rutas). |
| 3 | Sin API key | **PASA** | App instalada y ejecutada sin `OPENAI_API_KEY`/`GOOGLE_API_KEY`: muestra "OCR/IA: ❌ no configurado" y "No hay API key configurada. Puede ingresar los datos manualmente."; toda la suite corre sin API. | SDKs de IA opcionales en `requirements-ia.txt`: la instalación base no puede fallar por ellos. |
| 4 | Falta Python | **PASA (Wine + Linux)** | **Wine:** `.bat` completo sin Python → "[ERROR] Python no esta instalado o no esta en el PATH" + pasos de instalación + "Add Python to PATH" + carpeta actual + `pause` ("Press any key…"). **Linux:** `.sh` con PATH sin Python → mismo bloque de diagnóstico. | Detección según spec: primero `py -3 --version`, luego `python --version`, más chequeo de versión mínima 3.10 con mensaje propio. |
| 5 | Falta `requirements.txt` | **PASA (Wine + Linux)** | **Wine:** mensaje "Falta el archivo requirements.txt…", ubicaciones de archivos (app.py presente / requirements NO ENCONTRADO), `pause`, sin cierre abrupto. **Linux:** `.sh` idéntico. | — |
| 6 | Falta `app.py` | **PASA (Wine + Linux)** | **Wine:** mensaje "Falta el archivo app.py…" con diagnóstico completo y `pause`. Caso adicional ambos-faltan → "Debe extraer el ZIP antes de ejecutar la aplicacion" con pasos de extracción (probado bajo Wine). **Linux:** `.sh` idéntico. | — |
| 7 | Excel abierto | **PASA** | Suite §9: `PermissionError` → `ExcelAbiertoError`: "…está abierto en otro programa (probablemente Excel). Cierre el archivo y vuelva a intentar."; archivo original intacto (escritura atómica). Toda la UI captura esta excepción. | Simulado interceptando `os.replace` (Linux no tiene bloqueo de Excel). |
| 8 | Datos de ejemplo (mandato/modelo/caso/demanda) | **PASA** | Navegador real: botón "Cargar datos de ejemplo" → métrica Mandatos = 3; búsqueda "maria soto perez" → personería vigente + texto legal en pantalla. Suite §3–§5: mandato con PDF, modelo Word con 19 placeholders, caso con carpeta/instrumento/parte, demanda `.docx` generada sin placeholders residuales. | Modelo base de fábrica incluido. |
| 9 | Revisor jurídico (bloqueos) | **PASA** | Suite §6–§8 con bloqueo + "cómo corregirlo" en cada caso: placeholder pendiente (indicado por nombre); `[EA1.1]`, `[COMPLETAR]`, `xxx`, `pendiente`, `revisar`; avalista en cuerpo ausente del petitorio; demandada en petitorio sin respaldo en el cuerpo; monto contra avalista superior a los títulos que garantizó; campo crítico `NO_DETECTADO`; personería posterior al título; USD sin equivalencia; caso sin títulos. | Revisión sobre el texto del Word realmente renderizado + datos estructurados. |
| 10 | Auditoría | **PASA** | Suite §10: `audit_log.xlsx` registra carga de mandato, creación de caso, altas de instrumento/parte, generación, bloqueo por revisión y descarga final. Respaldos con timestamp antes de cada escritura. | — |
| 11 | Seguridad / confidencialidad | **PASA** | `check_install.py` (automatizado): `git ls-files` sin `.env`/`database/`/PDFs/Excels versionados; sin documentos sueltos en la raíz; `.gitignore` cubre `.env`, `database/`, `*.xlsx`, `*.pdf`, respaldos y temporales. ZIP final solo con código y documentación. Gate de confidencialidad + autorización expresa antes de usar IA externa. | — |

## Cumplimiento de los 17 requisitos del `.bat`

`@echo off` ✓ · `setlocal` ✓ · `cd /d "%~dp0"` al inicio ✓ · imprime
`Carpeta del proyecto: %CD%` ✓ · verifica `app.py` ✓ · verifica
`requirements.txt` ✓ · Python vía `py -3 --version` con respaldo
`python --version` ✓ · mensaje claro + `pause` si no hay Python ✓ · `.venv`
dentro del proyecto ✓ · activación del venv con rutas entre comillas
(`call ".venv\Scripts\activate.bat"`) ✓ · `pip install --upgrade pip` ✓ ·
`pip install -r requirements.txt` ✓ · `python -m streamlit run app.py` ✓ ·
toda falla va a la sección `:error` con `pause` ✓ · nunca se cierra solo
ante error ✓ (verificado bajo Wine: "Press any key…") · rutas con espacios/
tildes/OneDrive ✓ · `DIAGNOSTICO.bat` separado que imprime ruta, app.py,
requirements.txt, versión de Python, versión de pip, `.venv`, permisos de
escritura y ejecuta `check_install.py` ✓ (ejecutado bajo Wine).

## Verificaciones adicionales

- `streamlit.testing.v1.AppTest`: `app.py` completo sin excepciones.
- `.bat` finales: 0 bytes no-ASCII, CRLF, paréntesis balanceados, sin `&&`/`||`.
- Sin rutas absolutas ni credenciales en el código (rutas por
  `Path(__file__)`/`%~dp0`; claves solo por entorno/.env local).

**Conclusión:** todas las pruebas obligatorias ejecutables PASAN, incluidas
las ejecuciones reales del `.bat` bajo Wine en sus rutas de error.
**La validación directa en Windows real NO fue ejecutada** (no disponible en
este entorno) — el primer doble clic del usuario es la verificación
definitiva; ante cualquier falla la ventana queda abierta con diagnóstico y
`DIAGNOSTICO.bat` entrega el reporte completo para soporte.
