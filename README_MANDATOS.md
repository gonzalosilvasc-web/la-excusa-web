# ⚖️ Sistema de Gestión de Personerías y Mandatos — Santander / GRC

Aplicación interna en **Python + Streamlit** para la validación, asignación,
búsqueda y almacenamiento indexado de personerías/mandatos de **Banco
Santander** y **GRC**, orientada a juicios ejecutivos chilenos.

Opera 100 % local, sin base de datos externa: la persistencia es en Excel
(`openpyxl`/`pandas`) y los PDF se indexan en el sistema de archivos.

## Estructura

```
app.py                      # Aplicación completa (Streamlit)
requirements.txt            # Dependencias
database/                   # Creada automáticamente al primer arranque
├── mandatos.xlsx           # Base de mandatos indexados
├── audit_log.xlsx          # Registro de auditoría
├── pdf_storage/            # PDFs de escrituras indexadas
└── backups/                # Respaldos automáticos con timestamp
```

Todas las carpetas y archivos se crean automáticamente si no existen.

## Instalación y ejecución local

Requiere Python 3.10 o superior.

```bash
# 1. Crear y activar un entorno virtual
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Ejecutar la aplicación
streamlit run app.py
```

La app se abre en `http://localhost:8501`. En la barra lateral hay un botón
**“Cargar datos de ejemplo”** para poblar `mandatos.xlsx` con registros de
prueba.

## Configuración del OCR multimodal (opcional)

La extracción automática de datos desde el PDF usa un LLM multimodal con
visión, configurable por variables de entorno. **Sin API key, la app funciona
igual con carga manual de datos.**

| Variable | Descripción |
|---|---|
| `OCR_PROVIDER` | `openai` o `google`. Si se omite, se autodetecta según la API key disponible. |
| `OPENAI_API_KEY` | API key de OpenAI (proveedor `openai`). |
| `GOOGLE_API_KEY` | API key de Google AI Studio (proveedor `google`/Gemini). |
| `OCR_MODEL` | Modelo a usar (opcional). Por defecto `gpt-4o` u `gemini-1.5-pro` según proveedor. |

Ejemplo (Linux/macOS):

```bash
export OCR_PROVIDER=openai
export OPENAI_API_KEY="sk-..."
streamlit run app.py
```

Ejemplo (Windows PowerShell):

```powershell
$env:OCR_PROVIDER = "google"
$env:GOOGLE_API_KEY = "AIza..."
streamlit run app.py
```

Las credenciales **nunca** se guardan en el código ni en archivos del
proyecto.

## Funcionalidades principales

**Tab 1 — Consulta / Litigación:** búsqueda fuzzy del ejecutivo
(`rapidfuzz`, `token_set_ratio > 85`), filtro por entidad y vigencia del
mandato a la fecha del pagaré, detección del caso borde de revocación el
mismo día, generación del texto legal de personería listo para la demanda y
descarga del PDF asociado.

**Tab 2 — Carga e Indexación:** subida de PDF, extracción OCR multimodal con
salida JSON estricta (incluye evaluación expresa de la **facultad para
suscribir pagarés**), formulario editable de validación humana con checkbox
obligatorio, detección de duplicados con confirmación expresa, nombre de
archivo sanitizado e ID único por mandato.

**Tab 3 — Auditoría:** vista de `audit_log.xlsx` con todas las cargas,
bloqueos y errores registrados.

**Seguridad de datos:** respaldo automático con timestamp antes de cada
escritura, escritura atómica (archivo temporal + validación + reemplazo),
manejo explícito de `PermissionError` cuando el Excel está abierto, y los
PDF ya indexados nunca se eliminan.

## ⚠️ Advertencia de uso legal

Este sistema **asiste** la búsqueda y validación de personerías, pero **no
reemplaza la revisión profesional** del mandato original ni del título
ejecutivo por parte del abogado responsable. En particular:

- El texto de personería generado debe cotejarse siempre contra la escritura
  pública original antes de incorporarlo a una demanda.
- La detección automática de la facultad para suscribir pagarés es una ayuda
  de triage: la calificación jurídica del título y del mandato corresponde
  exclusivamente al profesional a cargo.
- Ante revocaciones el mismo día de la suscripción del pagaré, verifique las
  horas de otorgamiento de los instrumentos.
