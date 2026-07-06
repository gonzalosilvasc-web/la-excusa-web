"""Configuración central: rutas, columnas, constantes y textos legales."""

from __future__ import annotations

from pathlib import Path

# --- Rutas (relativas a la raíz del proyecto, nunca absolutas hardcodeadas) ---
BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_DIR = BASE_DIR / "database"
PDF_STORAGE_DIR = DATABASE_DIR / "pdf_storage"
TEMPLATES_DIR = DATABASE_DIR / "templates"
GENERATED_DIR = DATABASE_DIR / "generated_demands"
BACKUPS_DIR = DATABASE_DIR / "backups"
TEMP_DIR = DATABASE_DIR / "temp"
CASES_DIR = DATABASE_DIR / "cases"

MANDATOS_XLSX = DATABASE_DIR / "mandatos.xlsx"
TEMPLATES_XLSX = DATABASE_DIR / "templates.xlsx"
CASES_XLSX = DATABASE_DIR / "cases.xlsx"
INSTRUMENTS_XLSX = DATABASE_DIR / "instruments.xlsx"
PARTIES_XLSX = DATABASE_DIR / "parties.xlsx"
GENERATED_XLSX = DATABASE_DIR / "generated_demands.xlsx"
AUDIT_LOG_XLSX = DATABASE_DIR / "audit_log.xlsx"

ALL_DIRS = [
    DATABASE_DIR, PDF_STORAGE_DIR, TEMPLATES_DIR, GENERATED_DIR,
    BACKUPS_DIR, TEMP_DIR, CASES_DIR,
]

# --- Valor centinela: la app NUNCA inventa datos ---
NO_DETECTADO = "NO_DETECTADO"

# --- Entidades ---
ENTIDADES = ["Banco Santander", "GRC", "Banco de Chile"]
OPCION_OTRA_ENTIDAD = "Otra (especificar)"

MONEDAS = ["CLP", "USD", "UF"]

# --- Umbral de coincidencia fuzzy para nombres ---
FUZZY_THRESHOLD = 85

# --- Tipos de demanda ---
TIPOS_DEMANDA = [
    "Cobro de pagaré en pesos",
    "Cobro de pagaré en dólares",
    "Cobro de múltiples pagarés",
    "Cobro de pagaré con avalistas/codeudores",
    "Cobro de mutuo hipotecario",
    "Cobro de mutuo con cartola",
    "Desposeimiento de tercer poseedor",
    "Demanda ejecutiva con hipoteca",
    "Demanda ejecutiva con prenda",
    "Demanda ejecutiva con garantías",
    "Gestión preparatoria",
    "Otros",
]

# --- Tipos de documento por caso ---
TIPOS_DOCUMENTO = [
    "Pagaré",
    "Mutuo hipotecario",
    "Cartola de pago",
    "Liquidación de deuda",
    "Certificado de deuda",
    "Certificado de dólar",
    "Certificado de UF",
    "Escritura de hipoteca",
    "Escritura de prenda",
    "Mandato / personería",
    "Informe legal",
    "Otro antecedente",
]

TIPOS_INSTRUMENTO = ["Pagare", "Mutuo", "Otro"]

CALIDADES_JURIDICAS = [
    "Deudor principal",
    "Avalista",
    "Fiador",
    "Codeudor solidario",
    "Tercero poseedor",
]

# --- Columnas de cada Excel ---
MANDATOS_COLUMNS = [
    "ID_Mandato", "Nombre_Ejecutivo", "Nombre_Ejecutivo_Normalizado",
    "Entidad_Representada", "Fecha_Otorgamiento", "Fecha_Revocacion",
    "Notario_Titular", "Ciudad_Notaria", "Repertorio", "Facultad_Pagare",
    "Texto_Facultad_Pagare", "PDF_Path", "Fecha_Carga", "Usuario_Carga",
    "Observaciones",
]

TEMPLATES_COLUMNS = [
    "ID_Template", "Nombre_Template", "Tipo_Demanda", "Banco_Entidad",
    "Moneda", "Numero_Titulos", "Tiene_Hipoteca", "Tiene_Prenda",
    "Tiene_Avalistas", "Tiene_Codeudores", "Tipo_Instrumento",
    "Ruta_Template", "Placeholders_Detectados", "Fecha_Carga",
    "Usuario_Carga", "Observaciones", "Activo",
]

CASES_COLUMNS = [
    "ID_Caso", "Banco_Entidad", "Tipo_Caso_Detectado", "Cliente_Deudor",
    "RUT_Deudor", "Numero_Operacion", "Fecha_Carga", "Usuario_Carga",
    "Estado", "Observaciones", "Ruta_Carpeta_Caso",
]

INSTRUMENTS_COLUMNS = [
    "ID_Instrumento", "ID_Caso", "Tipo_Instrumento", "Numero_Instrumento",
    "Fecha_Suscripcion", "Fecha_Vencimiento", "Fecha_Mora", "Banco_Acreedor",
    "Entidad_Acreedora", "Nombre_Ejecutivo_Suscriptor", "Deudor_Principal",
    "RUT_Deudor_Principal", "Monto_Original", "Saldo_Insoluto", "Moneda",
    "Equivalencia_Pesos", "Tasa_Interes", "Interes_Penal",
    "Clausula_Aceleracion", "Liberacion_Protesto",
    "Firmas_Autorizadas_Notarialmente", "Domicilio_Competencia",
    "Fuente_Documento", "Fuente_Pagina", "Fuente_Texto", "Observaciones",
]

PARTIES_COLUMNS = [
    "ID_Parte", "ID_Caso", "ID_Instrumento", "Nombre", "RUT", "Tipo_Parte",
    "Calidad_Juridica", "Responde_Por_Instrumento", "Monto_Responsabilidad",
    "Moneda_Responsabilidad", "Limitacion_Responsabilidad", "Domicilio",
    "Fuente_Documento", "Fuente_Pagina", "Fuente_Texto", "Observaciones",
]

GENERATED_COLUMNS = [
    "ID_Demanda", "ID_Caso", "ID_Template", "ID_Mandato", "Tipo_Demanda",
    "Archivo", "Contexto_JSON", "Fecha_Generacion", "Usuario",
    "Errores_Criticos", "Advertencias", "Checklist_Completo", "Estado",
]

AUDIT_COLUMNS = [
    "Fecha_Hora", "Usuario", "Accion", "ID_Caso", "ID_Mandato",
    "ID_Template", "Resultado", "Observaciones",
]

EXCEL_SCHEMAS: dict[str, list[str]] = {
    str(MANDATOS_XLSX): MANDATOS_COLUMNS,
    str(TEMPLATES_XLSX): TEMPLATES_COLUMNS,
    str(CASES_XLSX): CASES_COLUMNS,
    str(INSTRUMENTS_XLSX): INSTRUMENTS_COLUMNS,
    str(PARTIES_XLSX): PARTIES_COLUMNS,
    str(GENERATED_XLSX): GENERATED_COLUMNS,
    str(AUDIT_LOG_XLSX): AUDIT_COLUMNS,
}

# --- Placeholders estándar soportados en modelos Word ---
PLACEHOLDERS_ESTANDAR = [
    "TRIBUNAL", "PROCEDIMIENTO", "MATERIA", "DEMANDANTE", "RUT_DEMANDANTE",
    "REPRESENTANTE_DEMANDANTE", "TEXTO_PERSONERIA", "DEMANDADO_1",
    "RUT_DEMANDADO_1", "CALIDAD_DEMANDADO_1", "DOMICILIO_DEMANDADO_1",
    "DEMANDADOS", "TITULOS_EJECUTIVOS", "MONTO_CAPITAL", "MONEDA",
    "EQUIVALENCIA_PESOS", "FECHA_SUSCRIPCION", "FECHA_VENCIMIENTO",
    "TASA_INTERES", "INTERESES_PENALES", "RELATO_DE_LOS_HECHOS",
    "PETITORIO", "DOCUMENTOS_PRIMER_OTROSI", "BIENES_EMBARGO", "GARANTIAS",
    "OTROSI_PERSONERIA", "FECHA_DEMANDA",
]

# --- Texto legal de personería ---
TEXTO_PERSONERIA_TPL = (
    "La personería de don/doña {nombre} para actuar en representación de "
    "{entidad}, consta en la escritura pública de fecha {fecha_otorgamiento}, "
    "otorgada en la Notaría de {ciudad} de don/doña {notario}, bajo el "
    "repertorio N° {repertorio}, copia de la cual se acompaña en un otrosí "
    "de esta presentación."
)

MSG_REVOCACION_MISMO_DIA = (
    "Atención: El mandato fue revocado el mismo día de la suscripción. "
    "Verifique horas de los instrumentos antes de usar esta personería."
)

MSG_SIN_FACULTAD_PAGARE = (
    "El mandato escaneado no contiene facultad expresa para suscribir pagarés "
    "o títulos de crédito. No se recomienda usar esta personería para juicio "
    "ejecutivo fundado en pagaré."
)

MSG_CONFIDENCIALIDAD = (
    "Advertencia de confidencialidad: los documentos pueden contener "
    "información bancaria, comercial o personal sensible. Solo use "
    "extracción automática con IA externa si cuenta con autorización para "
    "ello. En caso contrario, utilice el modo manual."
)

ADVERTENCIA_LEGAL = (
    "Este sistema asiste la búsqueda, validación y redacción, pero NO "
    "reemplaza la revisión profesional del abogado responsable. Todo "
    "documento generado debe cotejarse con los títulos originales antes de "
    "su presentación."
)

# --- Patrones de comentarios internos prohibidos en la demanda final ---
PATRONES_PROHIBIDOS: list[tuple[str, str]] = [
    (r"\{\{\s*[\w\.]+\s*\}\}", "Placeholder sin completar"),
    (r"\[\s*[A-Z]{1,6}\d*(?:\.\d+)*\s*\]", "Marca interna tipo [EA1.1]"),
    (r"\[\s*COMPLETAR\s*\]", "Marca [COMPLETAR]"),
    (r"\bxxx+\b", "Marcador 'xxx'"),
    (r"\bpendiente\b", "Palabra 'pendiente' (posible nota interna)"),
    (r"\brevisar\b", "Palabra 'revisar' (posible nota interna)"),
    (NO_DETECTADO, "Dato NO_DETECTADO sin resolver"),
]

# --- Checklist legal obligatorio previo a la descarga ---
CHECKLIST_LEGAL = [
    "Confirmo que revisé que el cuerpo coincide con el petitorio.",
    "Confirmo que los demandados coinciden con los obligados del título.",
    "Confirmo que los montos coinciden con los títulos y cartolas.",
    "Confirmo que la personería corresponde a la fecha de suscripción del instrumento.",
    "Confirmo que los documentos acompañados coinciden con el primer otrosí.",
    "Confirmo que los bienes señalados para embargo corresponden jurídicamente.",
    "Confirmo que no quedan placeholders sin completar.",
    "Confirmo que revisé manualmente el Word generado.",
]
