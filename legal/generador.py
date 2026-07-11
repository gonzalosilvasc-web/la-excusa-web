"""Módulo 7: generador de demandas ejecutivas en Word (docxtpl)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import pandas as pd
from docxtpl import DocxTemplate

from .casos import instrumentos_que_responde
from .config import (
    BASE_DIR,
    GENERATED_DIR,
    GENERATED_XLSX,
    NO_DETECTADO,
)
from .mandatos import texto_personeria
from .storage import append_row
from .textutil import (
    formatear_fecha,
    formatear_monto,
    parsear_monto,
    sanitizar_nombre_archivo,
    uid,
    valor_o_no_detectado,
)


def _texto_demandado(parte: pd.Series, indice: int) -> str:
    """Individualización de un demandado para el cuerpo de la demanda."""
    nombre = valor_o_no_detectado(parte.get("Nombre"))
    rut = valor_o_no_detectado(parte.get("RUT"))
    calidad = valor_o_no_detectado(parte.get("Calidad_Juridica"))
    domicilio = valor_o_no_detectado(parte.get("Domicilio"))
    return (
        f"{indice}. {nombre}, RUT {rut}, en su calidad de {calidad.lower()}, "
        f"con domicilio en {domicilio}."
    )


def _texto_instrumento(inst: pd.Series, indice: int) -> str:
    """Descripción de un título ejecutivo."""
    tipo = valor_o_no_detectado(inst.get("Tipo_Instrumento"))
    numero = valor_o_no_detectado(inst.get("Numero_Instrumento"))
    fecha = formatear_fecha(inst.get("Fecha_Suscripcion")) or NO_DETECTADO
    deudor = valor_o_no_detectado(inst.get("Deudor_Principal"))
    rut = valor_o_no_detectado(inst.get("RUT_Deudor_Principal"))
    moneda = valor_o_no_detectado(inst.get("Moneda"))
    monto = formatear_monto(inst.get("Monto_Original"), moneda if moneda != NO_DETECTADO else "CLP")
    saldo = formatear_monto(inst.get("Saldo_Insoluto"), moneda if moneda != NO_DETECTADO else "CLP")
    acreedor = valor_o_no_detectado(inst.get("Banco_Acreedor"))
    # El monto original es opcional (se omite si no consta); el saldo insoluto
    # es crítico y, si falta, queda NO_DETECTADO y bloquea la generación.
    frase_monto = f", por un monto original de {monto}" if monto != NO_DETECTADO else ""
    partes_txt = (
        f"{indice}. {tipo} N° {numero}, suscrito con fecha {fecha} por "
        f"{deudor}, RUT {rut}, a la orden de {acreedor}{frase_monto}, "
        f"cuyo saldo insoluto asciende a {saldo}."
    )
    extras: list[str] = []
    from .textutil import es_verdadero

    if es_verdadero(inst.get("Clausula_Aceleracion")):
        extras.append("contiene cláusula de aceleración")
    if es_verdadero(inst.get("Liberacion_Protesto")):
        extras.append("el suscriptor liberó al acreedor de la obligación de protesto")
    if es_verdadero(inst.get("Firmas_Autorizadas_Notarialmente")):
        extras.append("las firmas se encuentran autorizadas ante notario")
    if extras:
        partes_txt += " El título " + "; ".join(extras) + "."
    return partes_txt


def _texto_relato(instrumentos: pd.DataFrame) -> str:
    """Relato de mora/exigibilidad a partir de los instrumentos."""
    lineas: list[str] = []
    for _, inst in instrumentos.iterrows():
        numero = valor_o_no_detectado(inst.get("Numero_Instrumento"))
        fecha_mora = formatear_fecha(inst.get("Fecha_Mora")) or NO_DETECTADO
        moneda = str(inst.get("Moneda") or "CLP")
        saldo = formatear_monto(inst.get("Saldo_Insoluto"), moneda)
        # Nota jurídica: NO se afirma automáticamente que la obligación "no
        # está prescrita" — la prescripción debe evaluarla el abogado. Si se
        # incluye esa afirmación a mano, el revisor exige validación expresa.
        lineas.append(
            f"El deudor cesó en el pago de las obligaciones emanadas del título "
            f"N° {numero} a contar del {fecha_mora}, adeudando a esta parte la "
            f"suma de {saldo}, obligación líquida y actualmente exigible."
        )
    return "\n".join(lineas)


def _texto_petitorio(
    partes: pd.DataFrame,
    instrumentos: pd.DataFrame,
    total_txt: str,
) -> str:
    """Petitorio diferenciado por demandado, calidad y responsabilidad."""
    lineas = [
        "RUEGO A US. tener por interpuesta demanda ejecutiva en contra de las "
        "personas antes individualizadas, acogerla a tramitación y, en "
        "definitiva, ordenar que se despache mandamiento de ejecución y embargo "
        "en contra de:",
    ]
    ids_todos = (
        list(instrumentos["ID_Instrumento"].astype(str)) if not instrumentos.empty else []
    )
    for i, (_, parte) in enumerate(partes.iterrows(), start=1):
        nombre = valor_o_no_detectado(parte.get("Nombre"))
        rut = valor_o_no_detectado(parte.get("RUT"))
        calidad = valor_o_no_detectado(parte.get("Calidad_Juridica"))
        moneda = str(parte.get("Moneda_Responsabilidad") or "CLP")
        monto = formatear_monto(parte.get("Monto_Responsabilidad"), moneda)
        responde = instrumentos_que_responde(parte, instrumentos)
        limitacion = str(parte.get("Limitacion_Responsabilidad") or "").strip()

        linea = (
            f"{i}. {nombre}, RUT {rut}, en su calidad de {calidad.lower()}, "
            f"por la suma de {monto}"
        )
        if ids_todos and set(responde) != set(ids_todos):
            numeros = []
            for id_inst in responde:
                fila = instrumentos[instrumentos["ID_Instrumento"] == id_inst]
                if not fila.empty:
                    numeros.append(str(fila.iloc[0].get("Numero_Instrumento", id_inst)))
            detalle = ", ".join(numeros) if numeros else NO_DETECTADO
            linea += (
                f", limitada exclusivamente a las obligaciones emanadas del(los) "
                f"título(s) N° {detalle}"
            )
        if limitacion:
            linea += f" ({limitacion})"
        linea += ";"
        lineas.append(linea)

    lineas.append(
        f"todo lo anterior hasta enterar el total adeudado de {total_txt}, más "
        "intereses pactados, intereses penales y reajustes que correspondan, "
        "con expresa condenación en costas."
    )
    return "\n".join(lineas)


def _texto_documentos_otrosi(instrumentos: pd.DataFrame, docs_extra: list[str]) -> str:
    lineas: list[str] = []
    n = 1
    for _, inst in instrumentos.iterrows():
        tipo = valor_o_no_detectado(inst.get("Tipo_Instrumento"))
        numero = valor_o_no_detectado(inst.get("Numero_Instrumento"))
        lineas.append(f"{n}. {tipo} N° {numero}, en original.")
        n += 1
    for doc in docs_extra:
        if doc.strip():
            lineas.append(f"{n}. {doc.strip()}.")
            n += 1
    return "\n".join(lineas) if lineas else NO_DETECTADO


def componer_contexto(
    caso: pd.Series | dict,
    instrumentos: pd.DataFrame,
    partes: pd.DataFrame,
    mandato: Optional[pd.Series | dict],
    campos_manuales: dict[str, Any],
) -> dict[str, str]:
    """Construye el contexto completo de placeholders para el modelo Word.

    Los datos faltantes quedan como NO_DETECTADO — nunca se inventan.
    """
    get_caso = caso.get if hasattr(caso, "get") else lambda k, d="": d

    monedas = (
        instrumentos["Moneda"].fillna("CLP").astype(str).str.upper().unique().tolist()
        if not instrumentos.empty else []
    )
    moneda_ppal = monedas[0] if len(monedas) == 1 else (monedas[0] if monedas else "CLP")
    montos = [parsear_monto(v) for v in instrumentos.get("Saldo_Insoluto", pd.Series(dtype=object))]
    montos_validos = [m for m in montos if m is not None]
    total = sum(montos_validos) if montos_validos and len(montos_validos) == len(montos) else None
    total_txt = formatear_monto(total, moneda_ppal) if total is not None else NO_DETECTADO
    if len(monedas) > 1:
        total_txt += " (ATENCIÓN: instrumentos en monedas distintas, revise la suma)"

    equivalencia = str(campos_manuales.get("EQUIVALENCIA_PESOS", "")).strip()
    if moneda_ppal in ("USD", "UF") and not equivalencia:
        equivalencia = NO_DETECTADO
    elif moneda_ppal == "CLP" and not equivalencia:
        equivalencia = ""

    demandados_txt = "\n".join(
        _texto_demandado(p, i) for i, (_, p) in enumerate(partes.iterrows(), start=1)
    ) or NO_DETECTADO
    titulos_txt = "\n".join(
        _texto_instrumento(inst, i)
        for i, (_, inst) in enumerate(instrumentos.iterrows(), start=1)
    ) or NO_DETECTADO

    fechas_susc = [
        formatear_fecha(v) for v in instrumentos.get("Fecha_Suscripcion", pd.Series(dtype=object))
    ]
    fechas_venc = [
        formatear_fecha(v) for v in instrumentos.get("Fecha_Vencimiento", pd.Series(dtype=object))
    ]

    primera = instrumentos.iloc[0] if not instrumentos.empty else pd.Series(dtype=object)
    parte1 = partes.iloc[0] if not partes.empty else pd.Series(dtype=object)

    docs_extra = [
        d.strip() for d in str(campos_manuales.get("DOCUMENTOS_EXTRA", "")).split("\n") if d.strip()
    ]

    contexto: dict[str, str] = {
        "TRIBUNAL": valor_o_no_detectado(campos_manuales.get("TRIBUNAL")),
        "PROCEDIMIENTO": str(campos_manuales.get("PROCEDIMIENTO") or "ejecutivo"),
        "MATERIA": valor_o_no_detectado(
            campos_manuales.get("MATERIA") or get_caso("Tipo_Caso_Detectado", "")
        ),
        "DEMANDANTE": valor_o_no_detectado(
            campos_manuales.get("DEMANDANTE") or get_caso("Banco_Entidad", "")
        ),
        "RUT_DEMANDANTE": valor_o_no_detectado(campos_manuales.get("RUT_DEMANDANTE")),
        "REPRESENTANTE_DEMANDANTE": valor_o_no_detectado(
            campos_manuales.get("REPRESENTANTE_DEMANDANTE")
        ),
        "TEXTO_PERSONERIA": texto_personeria(mandato) if mandato is not None else NO_DETECTADO,
        "DEMANDADO_1": valor_o_no_detectado(parte1.get("Nombre") if not partes.empty else None),
        "RUT_DEMANDADO_1": valor_o_no_detectado(parte1.get("RUT") if not partes.empty else None),
        "CALIDAD_DEMANDADO_1": valor_o_no_detectado(
            parte1.get("Calidad_Juridica") if not partes.empty else None
        ),
        "DOMICILIO_DEMANDADO_1": valor_o_no_detectado(
            parte1.get("Domicilio") if not partes.empty else None
        ),
        "DEMANDADOS": demandados_txt,
        "TITULOS_EJECUTIVOS": titulos_txt,
        "MONTO_CAPITAL": total_txt,
        "MONEDA": moneda_ppal,
        "EQUIVALENCIA_PESOS": equivalencia,
        "FECHA_SUSCRIPCION": ", ".join(f for f in fechas_susc if f) or NO_DETECTADO,
        "FECHA_VENCIMIENTO": ", ".join(f for f in fechas_venc if f) or NO_DETECTADO,
        "TASA_INTERES": valor_o_no_detectado(
            primera.get("Tasa_Interes") if not instrumentos.empty else None
        ),
        "INTERESES_PENALES": valor_o_no_detectado(
            primera.get("Interes_Penal") if not instrumentos.empty else None
        ),
        "RELATO_DE_LOS_HECHOS": _texto_relato(instrumentos) or NO_DETECTADO,
        "PETITORIO": _texto_petitorio(partes, instrumentos, total_txt),
        "DOCUMENTOS_PRIMER_OTROSI": _texto_documentos_otrosi(instrumentos, docs_extra),
        "BIENES_EMBARGO": valor_o_no_detectado(campos_manuales.get("BIENES_EMBARGO")),
        "GARANTIAS": str(campos_manuales.get("GARANTIAS") or "").strip(),
        "OTROSI_PERSONERIA": (
            texto_personeria(mandato) if mandato is not None else NO_DETECTADO
        ),
        "FECHA_DEMANDA": str(
            campos_manuales.get("FECHA_DEMANDA") or datetime.now().strftime("%d/%m/%Y")
        ),
        # Validación expresa del abogado para afirmar la no-prescripción
        # (el revisor bloquea esa afirmación si este campo no es "SI").
        "PRESCRIPCION_VALIDADA": str(
            campos_manuales.get("PRESCRIPCION_VALIDADA", "")
        ).strip().upper(),
    }
    # Los bloques editados manualmente por el usuario prevalecen
    for clave, valor in campos_manuales.items():
        if clave in contexto and str(valor).strip():
            contexto[clave] = str(valor)
    return contexto


def nombre_archivo_demanda(
    banco: str, deudor: str, tipo_demanda: str, id_caso: str
) -> str:
    fecha = datetime.now().strftime("%Y-%m-%d")
    return sanitizar_nombre_archivo(
        f"DEMANDA_{banco}_{deudor}_{tipo_demanda}_{fecha}_{id_caso}"
    ) + ".docx"


def generar_demanda_docx(
    ruta_template: Path, contexto: dict[str, str], nombre_archivo: str
) -> Path:
    """Renderiza el modelo Word con el contexto y guarda en generated_demands/."""
    GENERATED_DIR.mkdir(parents=True, exist_ok=True)
    destino = GENERATED_DIR / nombre_archivo
    tpl = DocxTemplate(str(ruta_template))
    tpl.render(contexto)
    tpl.save(str(destino))
    return destino


def registrar_demanda_generada(
    id_caso: str,
    id_template: str,
    id_mandato: str,
    tipo_demanda: str,
    archivo: Path,
    contexto: dict[str, str],
    usuario: str,
    errores_criticos: int,
    advertencias: int,
    checklist_completo: bool,
) -> dict[str, Any]:
    """Indexa la demanda generada y guarda el contexto JSON para re-revisión."""
    id_demanda = uid("DDA")
    contexto_json = GENERATED_DIR / (archivo.stem + "_contexto.json")
    try:
        contexto_json.write_text(
            json.dumps(contexto, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError:
        contexto_json = Path("")
    registro = {
        "ID_Demanda": id_demanda,
        "ID_Caso": id_caso,
        "ID_Template": id_template,
        "ID_Mandato": id_mandato,
        "Tipo_Demanda": tipo_demanda,
        "Archivo": str(archivo.relative_to(BASE_DIR)),
        "Contexto_JSON": str(contexto_json.relative_to(BASE_DIR)) if contexto_json.name else "",
        "Fecha_Generacion": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "Usuario": usuario or "anonimo",
        "Errores_Criticos": errores_criticos,
        "Advertencias": advertencias,
        "Checklist_Completo": checklist_completo,
        "Estado": "GENERADA",
    }
    append_row(GENERATED_XLSX, registro)
    return registro
