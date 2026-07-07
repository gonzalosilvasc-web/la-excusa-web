# ⚖️ Sistema de Personerías y Demandas Ejecutivas

Sistema interno para estudios jurídicos de cobranza judicial chilena:
gestiona personerías/mandatos (Banco Santander, GRC y otros), modelos Word
del estudio, documentos del banco por caso, y genera demandas ejecutivas en
Word con un **revisor jurídico que bloquea la descarga si detecta
inconsistencias críticas** entre cuerpo y petitorio.

Funciona **100 % en su computador**: sin base de datos externa, sin internet
(salvo la instalación inicial y la IA opcional). Sus documentos nunca salen
de su máquina, a menos que usted autorice expresamente la extracción con IA.

---

## 🚀 Instalación y uso (no necesita saber de computación)

### Paso 1 — Instale Python (solo la primera vez)

1. Entre a **https://www.python.org/downloads/** y presione el botón amarillo
   grande "Download Python".
2. Abra el instalador descargado.
3. **MUY IMPORTANTE:** antes de presionar "Install Now", **marque la casilla
   de abajo que dice "Add Python to PATH"**.
4. Presione "Install Now" y espere a que termine.

*Recomendado: Python 3.11 o 3.12 (3.13 también funciona).*

### Paso 2 — Descargue y extraiga el sistema

1. Descargue el ZIP del proyecto (link al final de este documento o el que
   le hayan entregado).
2. Vaya a su carpeta **Descargas**, haga **clic derecho** sobre el ZIP y
   elija **"Extraer todo…"** → **Extraer**.
3. ⚠️ **No haga doble clic en los archivos DENTRO del ZIP sin extraer** — no
   funcionará (y la app se lo dirá).

### ⚠️ Reglas de oro en Windows (léalas antes de abrir)

1. **Primero extraiga el ZIP.** Clic derecho sobre el ZIP → "Extraer todo…".
2. **NO ejecute la app desde dentro del ZIP** — no funcionará (y la app se lo
   advertirá con un mensaje).
3. Abra la carpeta extraída y haga **doble clic en `INICIAR_APP.bat`**.
4. **La primera instalación puede demorar varios minutos.** No cierre la
   ventana negra mientras instala.
5. Si Windows muestra una advertencia azul ("Windows protegió su PC"),
   presione **"Más información"** y luego **"Ejecutar de todas formas"**.
6. Si algo falla, haga **doble clic en `DIAGNOSTICO.bat`** y **copie el
   resultado de la pantalla** para pedir soporte.

### Paso 3 — Abra la aplicación

Dentro de la carpeta extraída, haga **doble clic en `INICIAR_APP.bat`**.

- La **primera vez** se abre una ventana negra que instala todo
  automáticamente. Tarda varios minutos. **No la cierre.**
- Al terminar, la aplicación **se abre sola en su navegador**
  (dirección: `http://localhost:8501`).
- Las **siguientes veces** abre directo en segundos.

**Para cerrar la app:** cierre la ventana negra.
**Consejo:** clic derecho sobre `INICIAR_APP.bat` → "Enviar a" →
"Escritorio (crear acceso directo)" para abrirla siempre desde el escritorio.

---

## 🆘 Solución de problemas

**Windows muestra "Windows protegió su PC" / advertencia azul (SmartScreen):**
presione **"Más información"** y luego **"Ejecutar de todas formas"**. Es su
propio archivo descargado; Windows lo advierte solo porque no está firmado.

**Aparece "Python no está instalado":** vuelva al Paso 1 y, al instalar,
**marque la casilla "Add Python to PATH"**. Luego cierre la ventana y haga
doble clic de nuevo en `INICIAR_APP.bat`.

**Aparece "Debe extraer el ZIP antes de ejecutar la aplicación":** está
ejecutando el archivo desde dentro del ZIP. Haga clic derecho sobre el ZIP →
"Extraer todo…" → abra la carpeta extraída → doble clic en `INICIAR_APP.bat`.

**La ventana muestra un error:** la ventana **no se cierra sola** — lea el
bloque "[ERROR]": indica qué falló, en qué paso, y qué hacer. Para un chequeo
completo, haga **doble clic en `DIAGNOSTICO.bat`** y copie la pantalla si
necesita ayuda.

**"El archivo está abierto en otro programa (probablemente Excel)":** tiene
abierto alguno de los Excel de la carpeta `database/` (por ejemplo
`mandatos.xlsx`). Ciérrelo en Excel y vuelva a intentar la operación. La app
nunca corrompe datos: siempre respalda antes de escribir.

**La instalación falló a medias:** borre la carpeta `.venv` que está dentro
del proyecto y vuelva a hacer doble clic en `INICIAR_APP.bat`.

**Está dentro de OneDrive y algo falla:** pause temporalmente la
sincronización de OneDrive o mueva la carpeta del proyecto a Documentos.

---

## 🤖 ¿Necesito una API key? (No)

**La app funciona completa sin ninguna API key**, en modo manual: usted
escribe los datos de mandatos, pagarés y partes en formularios. La barra
lateral mostrará "OCR/IA: ❌ no configurado" — es normal.

Si más adelante quiere **extracción automática de datos desde los PDF con
IA**, necesita: (1) una API key de OpenAI o de Google, y (2) hacer esto una
sola vez:

1. En la carpeta del proyecto, copie el archivo `.env.example` y renombre la
   copia a `.env` (exactamente así, con el punto).
2. Ábralo con el Bloc de notas y pegue su clave, por ejemplo:
   `OPENAI_API_KEY=sk-su-clave-aqui`
3. Instale las dependencias de IA: abra la ventana negra del proyecto
   (`DIAGNOSTICO.bat` le indica el comando) o pida ayuda técnica para correr:
   `.venv\Scripts\python.exe -m pip install -r requirements-ia.txt`
4. Vuelva a abrir la app.

Las claves **nunca** se suben al repositorio ni van dentro del código. Antes
de enviar cualquier documento a la IA externa, la app le pedirá confirmar una
**advertencia de confidencialidad** (los documentos bancarios son sensibles:
úsela solo si cuenta con autorización).

---

## 📁 Qué contiene el proyecto

```
INICIAR_APP.bat       ← doble clic para abrir la app (Windows)
DIAGNOSTICO.bat       ← doble clic si algo falla (chequeo completo)
iniciar_app.sh        ← lanzador para Mac/Linux
app.py                ← la aplicación (9 pestañas)
legal/                ← lógica jurídica (mandatos, casos, generador, revisor)
requirements.txt      ← dependencias (instalación automática)
requirements-ia.txt   ← dependencias OPCIONALES de IA
check_install.py      ← verificador de instalación y seguridad
.env.example          ← plantilla para configurar API keys (opcional)
TEST_REPORT.md        ← informe de pruebas ejecutadas
database/             ← SUS DATOS (se crea sola; nunca se sube a internet)
```

Los datos (Excels, PDFs de mandatos, documentos de casos, demandas
generadas y respaldos) viven solo en `database/`, en su computador. Para
respaldar todo, basta copiar esa carpeta.

## 🧭 Las 9 pestañas

1. **Personerías** — busca el mandato vigente a la fecha del pagaré y genera
   el texto legal de personería.
2. **Carga Mandatos** — indexa escrituras de mandato (bloquea si no hay
   facultad para suscribir pagarés).
3. **Modelos** — biblioteca de modelos Word con placeholders `{{VARIABLE}}`.
4. **Nuevo Caso** — crea el caso y recibe los documentos del banco.
5. **Extracción** — registra pagarés/mutuos/cartolas y obligados (manual o IA).
6. **Generador** — arma la demanda completa con vista previa editable.
7. **Revisor** — 17 controles cuerpo–petitorio; los errores críticos
   **bloquean la descarga** y explican cómo corregirse.
8. **Historial** — demandas generadas, con descarga.
9. **Auditoría** — registro de todas las acciones.

## ⚠️ Advertencia de confidencialidad y uso legal

- Este sistema **asiste** al abogado; **no reemplaza su revisión
  profesional**. Todo texto generado debe cotejarse contra los títulos y
  escrituras originales antes de presentarse a tribunales.
- La app **no inventa datos**: lo que no consta queda `NO_DETECTADO` y, si es
  crítico, bloquea la generación hasta que un humano lo complete.
- Los documentos de clientes son confidenciales: manténgalos solo en esta
  máquina y no active la IA externa sin autorización del estudio.
