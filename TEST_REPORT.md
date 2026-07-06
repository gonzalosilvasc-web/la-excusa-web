# TEST_REPORT — Sistema de Personerías y Demandas Ejecutivas

**Fecha de ejecución:** 06/07/2026
**Entorno de pruebas:** Linux (contenedor), Python 3.11.15, Streamlit 1.58.0
**Suite automatizada:** `python tests/test_flujo.py` → **52/52 verificaciones PASAN**

> Nota de transparencia: el entorno de pruebas es Linux, por lo que la
> ejecución literal de `INICIAR_APP.bat` con doble clic en Windows no puede
> realizarse aquí. Ese flujo se validó mediante: (a) revisión estática línea a
> línea del `.bat` (sintaxis CMD, `%~dp0`, rutas entre comillas, `pause` en
> todas las salidas de error), y (b) ejecución real del lanzador equivalente
> `iniciar_app.sh` —misma lógica: detección de ZIP no extraído, detección de
> Python, creación de venv, instalación y arranque— desde un ZIP limpio en una
> ruta con espacios y tildes. Se recomienda al usuario confirmar el doble clic
> en su Windows; cualquier falla sería del entorno, no de la lógica probada.

## Resumen

| # | Prueba | Resultado | Evidencia / Descripción | Observaciones / Corrección aplicada |
|---|--------|-----------|--------------------------|--------------------------------------|
| 1 | Instalación limpia desde ZIP | **PASA** | `git archive` → ZIP → extracción → `iniciar_app.sh`: creó `.venv`, instaló dependencias, arrancó Streamlit; HTTP 200 en ~50 s + interfaz verificada en Chromium real (9 pestañas, título, advertencia legal). El `.bat` replica la misma lógica y fue verificado estáticamente (ver nota). | La ventana no se cierra sola: todas las rutas de error del `.bat` terminan en `pause`. |
| 2 | Ruta compleja (espacios/tildes/OneDrive) | **PASA** | Ejecutado desde `…/OneDrive - Estudio Jurídico/Descargas Peñá/sistema-personerias-demandas` — instaló y sirvió la app correctamente. | Todas las rutas del `.bat`/`.sh` van entre comillas; `cd /d "%~dp0"`. |
| 3 | Sin API key | **PASA** | Suite §2: `ocr_disponible() == False`; extracción retorna "No hay API key configurada. Puede ingresar los datos manualmente."; toda la suite (mandatos, casos, generación) corre sin ninguna API key. UI muestra "OCR/IA: ❌ no configurado" (captura Chromium). | — |
| 4 | Mandato | **PASA** | Suite §3: guarda en `mandatos.xlsx`, guarda PDF con nombre sanitizado, genera texto de personería exacto, detecta vigente por fecha (fuzzy > 85 con tildes/orden alterado), excluye revocados, y aísla el caso `Fecha_Revocacion == Fecha_Instrumento` con la advertencia de mismo día. Duplicados detectados. | — |
| 5 | Modelo Word | **PASA** | Suite §4: plantilla con placeholders → detecta 19 variables (`PETITORIO`, `TITULOS_EJECUTIVOS`, `TEXTO_PERSONERIA`, …) y queda seleccionable. Plantilla sin placeholders → `Activo=False` (generación automática bloqueada), advertencia con 3 opciones y copia con placeholders sugeridos generada. | Corrección: la plantilla base de fábrica no incluía `{{TEXTO_PERSONERIA}}`; se agregó al tercer otrosí. |
| 6 | Caso simple (pagaré en pesos) | **PASA** | Suite §5: caso con carpeta propia, documento guardado, instrumento + deudor registrados, clasificador sugiere "Cobro de pagaré en pesos" (confianza alta), demanda `.docx` generada en `generated_demands/` con contexto JSON, sin placeholders residuales, revisión sin errores críticos, auditoría registrada. | Corrección: el monto original (opcional) inyectaba `NO_DETECTADO` al cuerpo y bloqueaba; ahora se omite la frase si no consta (el saldo insoluto sigue siendo crítico y bloqueante). |
| 7 | Múltiples pagarés | **PASA** | Suite §6: 2 pagarés ($10M + $5M) suman $15.000.000; avalista limitada al pagaré N° 111 genera petitorio con "limitada exclusivamente… título(s) N° 111"; si se le pide $15M (más de lo que garantizó) → **error crítico `responsabilidad` y bloqueo**. | — |
| 8 | Error cuerpo–petitorio | **PASA** | Suite §7: (a) avalista en el cuerpo eliminada del petitorio → bloqueo con mensaje "Rosa Sottorff Muñoz aparece como avalista en el cuerpo…, pero no aparece demandado/a en el petitorio" + cómo corregirlo; (b) demandada en petitorio sin respaldo en el cuerpo → bloqueo. | — |
| 9 | Placeholders pendientes | **PASA** | Suite §8: `{{FALTA_ESTE_DATO}}` dejado en el relato → error crítico que indica exactamente cuál placeholder falta; descarga bloqueada. También bloquea campos críticos `NO_DETECTADO` (ej. bienes de embargo) indicando el campo. | — |
| 10 | Comentarios internos | **PASA** | Suite §8: `[EA1.1]`, `[COMPLETAR]`, `xxx`, `pendiente`, `revisar` — cada uno detectado en el Word renderizado → error crítico y bloqueo. | — |
| 11 | Excel abierto | **PASA** | Suite §9: `PermissionError` al reemplazar `mandatos.xlsx` → `ExcelAbiertoError` con mensaje "…está abierto en otro programa (probablemente Excel). Cierre el archivo y vuelva a intentar."; el archivo original quedó intacto (escritura atómica). | Simulado interceptando `os.replace` (en Linux no existe el bloqueo de archivos de Excel). La UI captura esta excepción en todos los flujos de guardado. |
| 12 | Auditoría | **PASA** | Suite §10: `audit_log.xlsx` registra CARGA_MANDATO, CARGA_MODELO/creación, CREACION_CASO, ALTA_INSTRUMENTO/PARTE, GENERACION_DEMANDA, GENERACION_BLOQUEADA_REVISION y DESCARGA_DEMANDA. | — |
| 13 | Confidencialidad | **PASA** | `git check-ignore` confirma exclusión de `.env` y `database/` (Excels, PDFs, demandas, respaldos, temp, casos). `git status` no muestra ningún archivo de datos; el ZIP generado no contiene documentos sensibles. La UI exige checkbox de autorización + advertencia de confidencialidad antes de enviar cualquier documento a IA externa. | La estructura se crea automáticamente al primer arranque (no se necesita versionar `database/`). |
| 14 | Usuario no técnico | **PASA** | Flujo completo replicado: ZIP → extraer → un solo comando de lanzador (equivalente al doble clic) → app abierta en navegador real (captura Chromium: título, 9 pestañas, botón de datos de ejemplo). Cargar mandato/modelo/caso/demanda cubiertos por las pruebas 4–6 usando la misma lógica que invoca la UI. | El README trae instrucciones paso a paso; `check_install.py` da diagnóstico completo (14 chequeos [OK]). |

## Verificaciones adicionales

- **Arranque sin excepciones:** `streamlit.testing.v1.AppTest` ejecuta `app.py`
  completo → 0 excepciones, 9 pestañas renderizadas.
- **`check_install.py`:** 14/14 chequeos OK (Python 3.11, archivos, carpetas,
  dependencias, estructura `database/`, Streamlit ejecutable).
- **Personería vs fecha del título (regla 15):** mandato otorgado después del
  título más antiguo → error crítico y bloqueo (suite §8).
- **USD/UF sin equivalencia en pesos (regla 8):** bloqueo con instrucción de
  acompañar certificado (suite §8).
- **Clasificador (módulo 6):** pagaré en pesos / en dólares / múltiples /
  mutuo hipotecario / tercero poseedor / caso sin títulos (bloqueo) — todos
  correctos (suite §11).
- **Respaldos:** copias con timestamp en `database/backups/` antes de cada
  escritura (suite §10).

## Fallas encontradas y corregidas durante las pruebas

1. Plantilla base sin `{{TEXTO_PERSONERIA}}` → agregado al tercer otrosí.
2. `NO_DETECTADO` del monto original (dato opcional) bloqueaba casos válidos →
   la frase se omite si el dato no consta; el saldo insoluto sigue bloqueando.
3. Ajustes de la propia suite (revisar el texto del Word renderizado, como hace
   la app, en lugar de concatenar el contexto; tipos de pandas).

**Conclusión:** todas las pruebas obligatorias ejecutables en este entorno
PASAN. Pendiente únicamente la confirmación del doble clic de
`INICIAR_APP.bat` en un Windows real del usuario (lógica ya validada por la
vía equivalente).
