# TEST_REPORT — Auditoría final de instalación y estabilidad

**Fecha de ejecución:** 06/07/2026
**Entorno de pruebas:** Linux (contenedor), Python 3.11.15, Streamlit 1.58.0
**Suite automatizada:** `python tests/test_flujo.py` → **52/52 verificaciones PASAN**
**Verificador:** `python check_install.py` → **todos los chequeos OK** (incluye seguridad)

> **Nota de transparencia sobre Windows:** el entorno de pruebas es Linux, por
> lo que el doble clic literal de `INICIAR_APP.bat` no puede ejecutarse aquí
> (no hay Windows ni Wine disponibles). El `.bat` se validó con: (a) revisión
> estática completa (CRLF, ASCII puro sin tildes que rompan CMD, paréntesis
> balanceados, todas las rutas entre comillas, `cd /d "%~dp0"`, `pause` en
> TODAS las salidas de error), y (b) ejecución real de `iniciar_app.sh`, que
> implementa exactamente la misma lógica paso a paso, en todos los escenarios
> de falla y de éxito. El primer doble clic en un Windows real del usuario es
> la única verificación pendiente; cualquier falla mostrará el bloque de
> diagnóstico y la ventana quedará abierta.

## Pruebas obligatorias

| # | Prueba | Resultado | Evidencia | Observaciones / Corrección aplicada |
|---|--------|-----------|-----------|--------------------------------------|
| 1 | Instalación limpia desde ZIP | **PASA** | ZIP generado con `git archive` desde la rama final → extraído en carpeta nueva → ejecutado SOLO el lanzador → creó `.venv`, instaló dependencias, sirvió la app (HTTP 200 en ~35 s) y la interfaz completa se verificó en un navegador Chromium real (título, 9 pestañas, barra de estado). Raíz del ZIP verificada: los 11 archivos requeridos presentes. | El lanzador imprime la versión de Python detectada y la carpeta del proyecto al inicio. |
| 2 | Ruta compleja (espacios/tildes/OneDrive) | **PASA** | Toda la prueba 1 se ejecutó dentro de `…/OneDrive - Estudio Jurídico/Descargas Peñá/sistema-personerias-demandas` (espacios + tildes + eñes). | `.bat`/`.sh`: todas las rutas van entre comillas; el `.bat` es ASCII puro para evitar problemas de codificación en CMD. |
| 3 | Sin API key | **PASA** | Instalación y ejecución completas sin `OPENAI_API_KEY` ni `GOOGLE_API_KEY`: la app arranca, muestra "OCR/IA: ❌ no configurado", y el mensaje de extracción es "No hay API key configurada. Puede ingresar los datos manualmente." Toda la suite (mandatos, casos, demandas) corre sin API. | Corrección adicional: los SDKs de IA se movieron a `requirements-ia.txt` (opcionales) para que la instalación base jamás falle por ellos; si hay API key pero falta el SDK, la app lo explica con el comando exacto. |
| 4 | Falta Python | **PASA** | Ejecutado `iniciar_app.sh` con un PATH sin Python: bloque de error claro — "Paso que falló: 2 - Detección de Python / Qué debe hacer: Instálelo desde python.org…". El `.bat` tiene la misma rama (`where python` / `where py`) con instrucciones de instalación y "Add Python to PATH", terminando en `pause`. | También se valida versión mínima 3.10 con mensaje propio. |
| 5 | Falta `requirements.txt` | **PASA** | Carpeta de prueba solo con lanzador + `app.py`: bloque de error "Falta el archivo requirements.txt… Vuelva a extraer el ZIP COMPLETO", con ruta del proyecto y ubicaciones de archivos; exit 1 sin cierre abrupto. Misma rama en el `.bat` con `pause`. | — |
| 6 | Falta `app.py` | **PASA** | Carpeta de prueba solo con lanzador + `requirements.txt`: bloque de error "Falta el archivo app.py…", diagnóstico completo. Caso adicional: si faltan AMBOS archivos → mensaje "Debe extraer el ZIP antes de ejecutar la aplicación" con pasos para extraer. | La detección de ZIP-no-extraído se probó explícitamente (carpeta solo con el lanzador). |
| 7 | Excel abierto | **PASA** | Suite §9: `PermissionError` al reemplazar `mandatos.xlsx` → `ExcelAbiertoError`: "…está abierto en otro programa (probablemente Excel). Cierre el archivo y vuelva a intentar."; el archivo original quedó intacto (escritura atómica: temporal → validación → reemplazo). Todos los flujos de guardado de la UI capturan esta excepción. | Simulado interceptando `os.replace` (en Linux no existe el bloqueo de archivos de Excel). |
| 8 | Datos de ejemplo (mandato/modelo/caso/demanda) | **PASA** | (a) Botón "Cargar datos de ejemplo" pulsado en navegador real → métrica Mandatos = 3; búsqueda "maria soto perez" → personería vigente encontrada y texto legal generado (verificado en pantalla). (b) Suite §3–§5: mandato guardado con PDF, modelo Word cargado con 19 placeholders detectados, caso creado con carpeta e instrumento/parte, y demanda `.docx` generada en `generated_demands/` sin placeholders residuales. | Modelo base de fábrica incluido para que la generación funcione sin cargar modelos propios. |
| 9 | Revisor jurídico (bloqueos) | **PASA** | Suite §6–§8, todos con bloqueo de descarga y explicación con "cómo corregirlo": placeholders pendientes (`{{FALTA_ESTE_DATO}}` indicado por nombre); comentarios internos `[EA1.1]`, `[COMPLETAR]`, `xxx`, `pendiente`, `revisar` (cada uno probado); avalista en el cuerpo ausente del petitorio; demandada en el petitorio sin respaldo en el cuerpo; monto contra avalista superior a los títulos que garantizó; y además: campo crítico `NO_DETECTADO`, personería posterior al título, USD sin equivalencia en pesos, caso sin títulos ejecutivos. | El revisor opera sobre el texto del Word realmente renderizado + los datos estructurados. |
| 10 | Auditoría | **PASA** | Suite §10: `audit_log.xlsx` registra CARGA_MANDATO, CREACION_CASO, ALTA_INSTRUMENTO, ALTA_PARTE, GENERACION_DEMANDA, GENERACION_BLOQUEADA_REVISION y DESCARGA_DEMANDA. Respaldos con timestamp en `database/backups/` antes de cada escritura. | — |
| 11 | Seguridad / confidencialidad | **PASA** | `check_install.py`: `git ls-files` confirma que NO hay `.env`, `database/`, PDFs ni Excels versionados; sin documentos sueltos en la raíz; `.gitignore` verificado automáticamente (excluye `.env`, `database/`, `*.xlsx`, `*.pdf`, respaldos, temporales). El ZIP final contiene solo código y documentación. La UI exige checkbox de autorización + advertencia de confidencialidad antes de enviar documentos a IA externa. | Los únicos Excel/PDF del sistema se crean localmente en `database/` (excluida de git) al primer arranque. |

## Verificaciones adicionales de la auditoría

- **`check_install.py` ampliado y ejecutado:** Python (con aviso para 3.13+),
  archivos y carpetas, **permisos de escritura reales**, dependencias
  críticas + IA opcionales, autocreación de `database/`, cobertura de
  `.gitignore`, escaneo de archivos sensibles versionados y Streamlit
  ejecutable → **todo OK, exit 0**.
- **`DIAGNOSTICO.bat` creado:** chequea Python, pip, venv, permisos de
  escritura, archivos y ejecuta `check_install.py`; siempre termina en
  `pause`. Validado estáticamente (ASCII, CRLF, paréntesis balanceados).
- **Arranque sin excepciones:** `streamlit.testing.v1.AppTest` ejecuta
  `app.py` completo tras la auditoría → 0 excepciones.
- **`.bat` saneado:** 0 bytes no-ASCII, CRLF en 160 líneas, paréntesis
  balanceados, sin expansión retardada (soporta rutas con `!` y especiales).
- **Sin rutas absolutas ni credenciales:** todas las rutas derivan de
  `Path(__file__)`/`%~dp0`; API keys solo por variables de entorno/.env local.

## Correcciones aplicadas en esta auditoría

1. Mensajes de error del lanzador diferenciados (antes, la falta de un solo
   archivo mostraba el mensaje genérico de ZIP; ahora cada caso tiene el suyo)
   y bloque de diagnóstico completo (paso, causa, solución, ruta, versión de
   Python, ubicación de `app.py` y `requirements.txt`).
2. Dependencias de IA separadas a `requirements-ia.txt` para blindar la
   instalación base (con mensaje claro en la app si falta el SDK).
3. `check_install.py` ampliado (escritura, seguridad, `.gitignore`).
4. `DIAGNOSTICO.bat` nuevo.
5. README reescrito para usuario no técnico con solución de problemas
   (SmartScreen, Python, ZIP, Excel abierto, OneDrive, `.venv` corrupto).

**Conclusión:** las 11 pruebas obligatorias PASAN en este entorno. Único
punto no ejecutable aquí: el doble clic físico en un Windows real (lógica
equivalente probada; ante cualquier falla la ventana queda abierta con
diagnóstico y existe `DIAGNOSTICO.bat`).
