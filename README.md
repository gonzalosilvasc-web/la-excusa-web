# ⚖️ Sistema de Personerías y Demandas Ejecutivas

Sistema interno en **Python + Streamlit** para estudios jurídicos de cobranza
judicial chilena. Permite gestionar personerías/mandatos (Banco Santander,
GRC y otros), cargar modelos Word del estudio, ingresar documentos del banco
por caso, extraer datos (con IA opcional o manualmente), identificar el tipo
de demanda, generar la demanda ejecutiva en Word y **bloquear la descarga
final si existen inconsistencias críticas** entre cuerpo y petitorio.

Opera 100 % local: sin base de datos externa (Excel + carpetas) y los
documentos reales nunca salen de su computador, salvo que usted autorice
expresamente la extracción con IA externa.

## 🚀 Cómo usarla (usuario no técnico)

1. **Instale Python** (una sola vez): [python.org/downloads](https://www.python.org/downloads/)
   — en Windows **marque la casilla "Add Python to PATH"** al instalar.
2. **Descargue este proyecto como ZIP** y **extráigalo** (clic derecho →
   "Extraer todo…"). No lo ejecute desde dentro del ZIP.
3. Entre a la carpeta extraída y haga **doble clic en `INICIAR_APP.bat`**
   (Windows) o ejecute `./iniciar_app.sh` (Mac/Linux).
4. La primera vez instala todo automáticamente (varios minutos); luego la
   app se abre sola en su navegador (`http://localhost:8501`).

Si algo falla, la ventana **no se cierra sola**: muestra el error y cómo
corregirlo. Diagnóstico completo: `python check_install.py`.

## 📁 Estructura

```
app.py                  Interfaz Streamlit (9 módulos en pestañas)
legal/                  Núcleo: mandatos, plantillas, casos, extracción,
                        clasificador, generador y revisor jurídico
check_install.py        Verificador de instalación
INICIAR_APP.bat         Lanzador Windows (doble clic)
iniciar_app.sh          Lanzador Mac/Linux
requirements.txt        Dependencias
.env.example            Plantilla de variables de entorno (copiar a .env)
TEST_REPORT.md          Informe de pruebas funcionales
database/               Datos locales (SE CREA SOLA; excluida de git)
├── mandatos.xlsx         Personerías indexadas
├── templates.xlsx        Índice de modelos Word
├── cases.xlsx            Casos
├── instruments.xlsx      Títulos ejecutivos por caso
├── parties.xlsx          Obligados por caso (deudores, avalistas…)
├── generated_demands.xlsx  Índice de demandas generadas
├── audit_log.xlsx        Auditoría de todas las acciones
├── pdf_storage/          PDFs de mandatos
├── templates/            Modelos Word del estudio
├── cases/[ID_Caso]/      Documentos originales de cada caso
├── generated_demands/    Demandas .docx generadas (+ contexto JSON)
├── backups/              Respaldos automáticos con timestamp
└── temp/                 Archivos temporales
```

## 🧭 Módulos (pestañas)

1. **Personerías** — búsqueda fuzzy del ejecutivo (rapidfuzz > 85), vigencia
   a la fecha del instrumento, caso borde de revocación el mismo día y texto
   legal de personería listo para la demanda.
2. **Carga Mandatos** — PDF + extracción IA opcional con validación humana
   obligatoria; bloquea la indexación si el mandato no tiene facultad para
   suscribir pagarés; detección de duplicados.
3. **Modelos** — biblioteca de modelos Word con detección automática de
   placeholders `{{VARIABLE}}`; si un modelo no tiene placeholders, la
   generación automática queda bloqueada y se ofrece una copia con
   placeholders sugeridos. Incluye un modelo base de fábrica.
4. **Nuevo Caso** — crea el caso con carpeta propia y recibe todos los
   documentos del banco (pagarés, mutuos, cartolas, certificados, etc.).
5. **Extracción** — extracción IA por tipo de documento (pagaré/mutuo/
   cartola) con **advertencia de confidencialidad y autorización expresa**,
   o ingreso manual; registro estructurado de instrumentos y partes con
   fuente documental (documento/página/texto).
6. **Generador** — clasifica el caso, sugiere tipo de demanda y modelo,
   selecciona personería vigente, compone todos los bloques (comparecencia,
   títulos, relato, petitorio diferenciado por calidad y responsabilidad,
   otrosíes) con vista previa editable.
7. **Revisor** — control de concordancia cuerpo–petitorio (17 reglas):
   demandados en ambas secciones, sumas de montos, responsabilidad limitada
   de avalistas, equivalencia USD/UF, intereses y costas, documentos del
   primer otrosí, placeholders sin completar, marcas internas
   (`[COMPLETAR]`, `xxx`, `pendiente`…), vigencia de la personería a la
   fecha del título, etc. **Los errores críticos bloquean la descarga.**
8. **Historial** — demandas generadas con descarga.
9. **Auditoría** — registro completo de acciones.

## 🔐 Regla suprema: la app no inventa

Si un dato no consta en los documentos ni fue ingresado manualmente, queda
como `NO_DETECTADO`. Si es crítico, la generación final se **bloquea** hasta
que un humano lo complete. Antes de descargar, además, debe aprobarse un
checklist legal obligatorio de 8 puntos.

## 🤖 IA opcional (variables de entorno)

Sin API key la app funciona completa en modo manual. Para habilitar la
extracción automática, copie `.env.example` a `.env` y complete:

| Variable | Descripción |
|---|---|
| `OCR_PROVIDER` | `openai` o `google` (vacío = autodetección) |
| `OPENAI_API_KEY` | API key de OpenAI |
| `GOOGLE_API_KEY` | API key de Google AI Studio (Gemini) |
| `OCR_MODEL` | Modelo (opcional; por defecto `gpt-4o` / `gemini-1.5-pro`) |

Las claves **nunca** van en el código ni al repositorio (`.env` está en
`.gitignore`). Antes de enviar cualquier documento a un proveedor externo,
la app exige confirmar la advertencia de confidencialidad.

## 🛡️ Seguridad de datos

- Respaldo automático con timestamp en `database/backups/` antes de cada
  escritura de Excel.
- Escritura atómica: archivo temporal → validación → reemplazo.
- Manejo explícito de archivos Excel abiertos (mensaje claro para cerrarlos).
- `database/` completa excluida de git: los PDFs de clientes, Excels y
  demandas generadas permanecen solo en su máquina.

## ⚠️ Advertencia de uso legal

Este sistema **asiste** la búsqueda, validación y redacción, pero **no
reemplaza la revisión profesional** del abogado responsable. Todo texto de
personería, título y demanda generada debe cotejarse contra los documentos
originales antes de presentarse a tribunales. La calificación jurídica del
título, de las calidades de los obligados y de los montos demandados
corresponde exclusivamente al profesional a cargo.
