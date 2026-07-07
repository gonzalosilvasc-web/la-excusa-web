"""
Sistema Integral de Personerías y Generación Asistida de Demandas Ejecutivas
============================================================================
Banco Santander / GRC / otros — Juicios ejecutivos chilenos. Uso interno.

Ejecución local:
    streamlit run app.py

REGLA SUPREMA: la aplicación no inventa información jurídica. Si un dato no
consta en los documentos cargados ni fue ingresado por el usuario, queda como
NO_DETECTADO y, si es crítico, bloquea la generación final.

ADVERTENCIA LEGAL: este sistema asiste al abogado, pero no reemplaza su
revisión profesional del mandato, de los títulos ni de la demanda generada.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

import pandas as pd
import streamlit as st

from legal import casos as mod_casos
from legal import clasificador as mod_clasif
from legal import extraccion as mod_extr
from legal import generador as mod_gen
from legal import mandatos as mod_mand
from legal import plantillas as mod_tpl
from legal import revisor as mod_rev
from legal.config import (
    ADVERTENCIA_LEGAL,
    BASE_DIR,
    CALIDADES_JURIDICAS,
    CASES_XLSX,
    CHECKLIST_LEGAL,
    ENTIDADES,
    GENERATED_XLSX,
    INSTRUMENTS_XLSX,
    MONEDAS,
    MSG_CONFIDENCIALIDAD,
    MSG_REVOCACION_MISMO_DIA,
    MSG_SIN_FACULTAD_PAGARE,
    NO_DETECTADO,
    OPCION_OTRA_ENTIDAD,
    PARTIES_XLSX,
    TEMP_DIR,
    TIPOS_DEMANDA,
    TIPOS_DOCUMENTO,
    TIPOS_INSTRUMENTO,
)
from legal.storage import (
    ExcelAbiertoError,
    ensure_structure,
    leer_auditoria,
    read_excel_or_empty,
    registrar_auditoria,
)
from legal.textutil import (
    es_verdadero,
    formatear_fecha,
    normalizar_nombre,
    parsear_fecha,
    valor_o_no_detectado,
)

# Carga opcional de .env local (nunca se versiona)
try:
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass


# ---------------------------------------------------------------------------
# Helpers de UI
# ---------------------------------------------------------------------------

CAMPOS_EDITABLES = ("DEMANDADOS", "TITULOS_EJECUTIVOS", "RELATO_DE_LOS_HECHOS",
                    "PETITORIO", "DOCUMENTOS_PRIMER_OTROSI")


def _huella_contexto(contexto: dict[str, str]) -> str:
    """Huella del contenido de la demanda para invalidar revisiones obsoletas."""
    import hashlib

    m = hashlib.sha256()
    for k in sorted(contexto):
        m.update(f"{k}={contexto[k]}\n".encode("utf-8"))
    return m.hexdigest()


def _mostrar_error_excel(exc: ExcelAbiertoError) -> None:
    st.error(f"📛 {exc}")


def _selector_entidad(clave: str, default: str = "") -> str:
    """Selector de entidad con opción configurable 'Otra'."""
    opciones = ENTIDADES + [OPCION_OTRA_ENTIDAD]
    idx = opciones.index(default) if default in ENTIDADES else 0
    eleccion = st.selectbox("Entidad", opciones, index=idx, key=f"{clave}_sel")
    if eleccion == OPCION_OTRA_ENTIDAD:
        return st.text_input("Nombre de la otra entidad", key=f"{clave}_otra").strip()
    return eleccion


def _guardar_temporal(nombre: str, contenido: bytes) -> Path:
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    destino = TEMP_DIR / f"up_{uuid.uuid4().hex[:8]}_{Path(nombre).name}"
    destino.write_bytes(contenido)
    return destino


def _gate_confidencialidad(clave: str) -> bool:
    """Advertencia de confidencialidad previa al uso de IA externa."""
    st.warning(MSG_CONFIDENCIALIDAD)
    return st.checkbox(
        "Cuento con autorización para enviar estos documentos a un proveedor "
        "externo de IA.",
        key=f"{clave}_autorizacion",
    )


def _fecha_o_vacia(etiqueta: str, clave: str, valor: str = "") -> str:
    return st.text_input(f"{etiqueta} (DD/MM/YYYY)", value=valor, key=clave)


# ---------------------------------------------------------------------------
# TAB 1 — Consulta de personerías
# ---------------------------------------------------------------------------

def tab_consulta() -> None:
    st.subheader("🔎 Consulta de personerías para litigación")
    c1, c2, c3 = st.columns(3)
    with c1:
        fecha_instrumento = st.date_input(
            "Fecha de suscripción del pagaré/instrumento",
            value=date.today(), format="DD/MM/YYYY", key="q_fecha",
        )
    with c2:
        nombre = st.text_input("Nombre del ejecutivo", key="q_nombre")
    with c3:
        entidad = _selector_entidad("q_entidad")

    if not st.button("Buscar personería", type="primary", key="q_buscar"):
        return
    if not nombre.strip() or not entidad:
        st.error("Debe ingresar el nombre del ejecutivo y la entidad.")
        return

    try:
        df = mod_mand.cargar_mandatos()
    except ExcelAbiertoError as exc:
        _mostrar_error_excel(exc)
        return

    resultado = mod_mand.buscar_personeria(df, nombre, entidad, fecha_instrumento)

    if not resultado["mismo_dia"].empty:
        st.warning(MSG_REVOCACION_MISMO_DIA)
        st.dataframe(resultado["mismo_dia"], width="stretch", hide_index=True)

    mandato = resultado["vigente"]
    if mandato is None:
        st.error(
            "No se encontró personería vigente para esos parámetros "
            f"(ejecutivo: “{nombre}”, entidad: {entidad}, fecha: "
            f"{fecha_instrumento.strftime('%d/%m/%Y')})."
        )
        return

    st.success(
        f"Personería vigente: **{mandato['Nombre_Ejecutivo']}** — "
        f"{mandato['Entidad_Representada']} | Otorgada el "
        f"{formatear_fecha(mandato['Fecha_Otorgamiento'])} | Rep. N° "
        f"{mandato['Repertorio']} | {mandato['ID_Mandato']}"
    )
    st.dataframe(pd.DataFrame([mandato]).drop(columns=["_score"], errors="ignore"),
                 width="stretch", hide_index=True)

    if not es_verdadero(mandato.get("Facultad_Pagare")):
        st.error(
            "Este mandato está registrado SIN facultad expresa para suscribir "
            "pagarés. Revise el instrumento original antes de usarlo."
        )

    st.markdown("**Texto legal de personería:**")
    st.code(mod_mand.texto_personeria(mandato), language=None)

    pdf_rel = str(mandato.get("PDF_Path") or "").strip()
    if pdf_rel and pdf_rel.lower() != "nan":
        ruta = BASE_DIR / pdf_rel
        if ruta.exists():
            st.download_button(
                "⬇️ Descargar PDF del mandato", data=ruta.read_bytes(),
                file_name=ruta.name, mime="application/pdf", key="q_pdf",
            )
        else:
            st.info("La ruta del PDF está registrada pero el archivo no existe.")
    else:
        st.info("Este mandato no tiene PDF asociado.")

    st.warning(
        "El texto debe ser revisado contra el título original antes de "
        "incorporarse a una demanda."
    )


# ---------------------------------------------------------------------------
# TAB 2 — Carga de mandatos
# ---------------------------------------------------------------------------

def tab_carga_mandatos() -> None:
    st.subheader("📥 Carga e indexación de mandatos")

    disponible, provider = mod_extr.ocr_disponible()
    if disponible:
        st.info(f"Extracción OCR multimodal disponible (proveedor: **{provider}**).")
    else:
        st.info("No hay API key configurada. Puede ingresar los datos manualmente.")

    archivo = st.file_uploader("Escritura de mandato (PDF)", type=["pdf"], key="m_pdf")
    c1, c2 = st.columns(2)
    with c1:
        usuario = st.text_input("Usuario que carga (opcional)", key="m_usuario")
    with c2:
        observaciones = st.text_input("Observaciones (opcional)", key="m_obs")

    if archivo is not None and st.session_state.get("m_pdf_nombre") != archivo.name:
        st.session_state["m_pdf_tmp"] = str(_guardar_temporal(archivo.name, archivo.getvalue()))
        st.session_state["m_pdf_nombre"] = archivo.name
        st.session_state.pop("m_extraccion", None)

    if archivo is not None and disponible:
        autorizado = _gate_confidencialidad("m_gate")
        if st.button("🤖 Extraer datos con IA", key="m_ocr", disabled=not autorizado):
            with st.spinner("Analizando la escritura…"):
                datos = mod_extr.extract_mandato_data(st.session_state["m_pdf_tmp"])
            if "_error" in datos:
                st.error(datos["_error"])
                registrar_auditoria("OCR_MANDATO_FALLIDO", usuario,
                                    resultado="ERROR", observaciones=datos["_error"])
            else:
                st.session_state["m_extraccion"] = datos

    ext: dict[str, Any] = st.session_state.get("m_extraccion", {})
    if ext:
        conf = str(ext.get("Confianza_Extraccion", "baja")).lower()
        st.markdown(f"**Confianza de extracción:** "
                    f"{'🟢' if conf == 'alta' else '🟡' if conf == 'media' else '🔴'} {conf.upper()}")
        if ext.get("Observaciones_Modelo"):
            st.caption(f"Observaciones del modelo: {ext['Observaciones_Modelo']}")
        if not bool(ext.get("Facultad_Pagare")):
            st.error(MSG_SIN_FACULTAD_PAGARE)
            registrar_auditoria(
                "INDEXACION_BLOQUEADA_SIN_FACULTAD", usuario, resultado="BLOQUEADO",
                observaciones="OCR detectó ausencia de facultad para suscribir pagarés.",
            )
        else:
            st.success("Facultad para suscribir pagarés detectada. Texto extraído:")
            st.code(ext.get("Texto_Facultad_Pagare", "") or "(sin texto)", language=None)

    st.divider()
    st.markdown("### Revisión y validación de datos")
    with st.form("m_form"):
        nombre = st.text_input("Nombre del ejecutivo *",
                               value=str(ext.get("Nombre_Ejecutivo", "") or ""))
        entidad_def = str(ext.get("Entidad_Representada", "")).strip()
        opciones = ENTIDADES + [OPCION_OTRA_ENTIDAD]
        entidad_sel = st.selectbox(
            "Entidad representada *", opciones,
            index=opciones.index(entidad_def) if entidad_def in ENTIDADES else 0,
        )
        entidad_otra = st.text_input("Si es «Otra», especifique", value="")
        c1, c2 = st.columns(2)
        with c1:
            f_otorg = st.text_input("Fecha de otorgamiento (DD/MM/YYYY) *",
                                    value=str(ext.get("Fecha_Otorgamiento", "") or ""))
        with c2:
            f_revoc = st.text_input(
                "Fecha de revocación (vacío si vigente)",
                value=str(ext.get("Fecha_Revocacion") or "").replace("null", ""),
            )
        c3, c4 = st.columns(2)
        with c3:
            notario = st.text_input("Notario titular *",
                                    value=str(ext.get("Notario_Titular", "") or ""))
        with c4:
            ciudad = st.text_input("Ciudad de la notaría *",
                                   value=str(ext.get("Ciudad_Notaria", "") or ""))
        repertorio = st.text_input("Repertorio N° *",
                                   value=str(ext.get("Repertorio", "") or ""))
        facultad = st.checkbox(
            "El mandato contiene facultad expresa para suscribir pagarés/títulos de crédito",
            value=bool(ext.get("Facultad_Pagare", False)),
        )
        texto_facultad = st.text_area(
            "Texto de la cláusula de facultad (transcripción)",
            value=str(ext.get("Texto_Facultad_Pagare", "") or ""),
        )
        confirmado = st.checkbox(
            "Confirmo que revisé el mandato original y validé que los datos "
            "extraídos son correctos."
        )
        enviado = st.form_submit_button("💾 Guardar mandato", type="primary")

    if enviado:
        entidad = entidad_otra.strip() if entidad_sel == OPCION_OTRA_ENTIDAD else entidad_sel
        _guardar_mandato_flujo(
            nombre, entidad, f_otorg, f_revoc, notario, ciudad, repertorio,
            facultad, texto_facultad, confirmado, usuario, observaciones,
        )

    pendiente = st.session_state.get("m_dup_pendiente")
    if pendiente:
        st.warning("⚠️ Posible duplicado (misma entidad, ejecutivo, fecha y repertorio):")
        st.dataframe(pd.DataFrame(pendiente["duplicados"]),
                     width="stretch", hide_index=True)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✅ Guardar de todos modos", key="m_dup_si"):
                _persistir_mandato(pendiente["datos"])
                st.session_state.pop("m_dup_pendiente", None)
        with c2:
            if st.button("❌ Cancelar", key="m_dup_no"):
                registrar_auditoria(
                    "CARGA_MANDATO_CANCELADA_DUPLICADO",
                    pendiente["datos"].get("Usuario_Carga", ""),
                    resultado="CANCELADO",
                )
                st.session_state.pop("m_dup_pendiente", None)
                st.info("Guardado cancelado.")


def _guardar_mandato_flujo(
    nombre: str, entidad: str, f_otorg: str, f_revoc: str, notario: str,
    ciudad: str, repertorio: str, facultad: bool, texto_facultad: str,
    confirmado: bool, usuario: str, observaciones: str,
) -> None:
    if not confirmado:
        st.error("Debe marcar la casilla de confirmación antes de guardar.")
        return
    faltan = [e for e, v in [
        ("Nombre del ejecutivo", nombre), ("Entidad", entidad),
        ("Fecha de otorgamiento", f_otorg), ("Notario", notario),
        ("Ciudad", ciudad), ("Repertorio", repertorio),
    ] if not str(v).strip()]
    if faltan:
        st.error(f"Complete los campos obligatorios: {', '.join(faltan)}.")
        return
    fo = parsear_fecha(f_otorg)
    if fo is None:
        st.error("Fecha de otorgamiento inválida (use DD/MM/YYYY).")
        return
    fr = parsear_fecha(f_revoc)
    if f_revoc.strip() and fr is None:
        st.error("Fecha de revocación inválida (use DD/MM/YYYY o déjela vacía).")
        return
    if fr is not None and fr < fo:
        st.error("La revocación no puede ser anterior al otorgamiento.")
        return
    if not facultad:
        st.error(MSG_SIN_FACULTAD_PAGARE)
        registrar_auditoria(
            "INDEXACION_BLOQUEADA_SIN_FACULTAD", usuario, resultado="BLOQUEADO",
            observaciones=f"Intento de guardado sin facultad — ejecutivo {nombre}.",
        )
        return

    datos = {
        "Nombre_Ejecutivo": nombre, "Entidad_Representada": entidad,
        "Fecha_Otorgamiento": f_otorg, "Fecha_Revocacion": f_revoc,
        "Notario_Titular": notario, "Ciudad_Notaria": ciudad,
        "Repertorio": repertorio, "Facultad_Pagare": True,
        "Texto_Facultad_Pagare": texto_facultad,
        "Usuario_Carga": usuario, "Observaciones": observaciones,
    }
    try:
        df = mod_mand.cargar_mandatos()
        duplicados = mod_mand.detectar_duplicados(
            df, entidad, normalizar_nombre(nombre), fo, repertorio
        )
    except ExcelAbiertoError as exc:
        _mostrar_error_excel(exc)
        return
    if not duplicados.empty:
        st.session_state["m_dup_pendiente"] = {
            "datos": datos, "duplicados": duplicados.astype(str).to_dict("records"),
        }
        st.rerun()
    _persistir_mandato(datos)


def _persistir_mandato(datos: dict[str, Any]) -> None:
    pdf_tmp = st.session_state.get("m_pdf_tmp")
    try:
        registro = mod_mand.guardar_mandato(
            datos, Path(pdf_tmp) if pdf_tmp else None
        )
    except ExcelAbiertoError as exc:
        _mostrar_error_excel(exc)
        registrar_auditoria("CARGA_MANDATO", datos.get("Usuario_Carga", ""),
                            resultado="ERROR", observaciones=str(exc))
        return
    except (OSError, IOError, ValueError) as exc:
        st.error(f"No se pudo guardar el mandato: {exc}")
        return
    registrar_auditoria(
        "CARGA_MANDATO", registro["Usuario_Carga"],
        id_mandato=registro["ID_Mandato"], resultado="OK",
        observaciones=f"{registro['Nombre_Ejecutivo']} / {registro['Entidad_Representada']}",
    )
    for k in ("m_extraccion", "m_pdf_tmp", "m_pdf_nombre"):
        st.session_state.pop(k, None)
    st.success(f"✅ Mandato guardado con ID **{registro['ID_Mandato']}**.")


# ---------------------------------------------------------------------------
# TAB 3 — Biblioteca de modelos Word
# ---------------------------------------------------------------------------

def tab_biblioteca() -> None:
    st.subheader("📚 Biblioteca de modelos Word")

    archivo = st.file_uploader("Modelo de demanda (.docx)", type=["docx"], key="t_docx")
    with st.form("t_form"):
        nombre = st.text_input("Nombre del modelo *")
        tipo = st.selectbox("Tipo de demanda", TIPOS_DEMANDA)
        c1, c2, c3 = st.columns(3)
        with c1:
            entidad = st.text_input("Banco/Entidad", value="Genérico")
        with c2:
            moneda = st.selectbox("Moneda", MONEDAS)
        with c3:
            n_titulos = st.text_input("N° de títulos", value="1")
        c4, c5, c6, c7 = st.columns(4)
        with c4:
            hip = st.checkbox("Hipoteca")
        with c5:
            pre = st.checkbox("Prenda")
        with c6:
            ava = st.checkbox("Avalistas")
        with c7:
            cod = st.checkbox("Codeudores")
        tipo_inst = st.selectbox("Tipo de instrumento", TIPOS_INSTRUMENTO)
        usuario = st.text_input("Usuario que carga (opcional)")
        obs = st.text_input("Observaciones (opcional)")
        enviado = st.form_submit_button("💾 Guardar modelo", type="primary")

    if enviado:
        if archivo is None:
            st.error("Debe subir un archivo .docx.")
        elif not nombre.strip():
            st.error("Debe indicar el nombre del modelo.")
        else:
            tmp = _guardar_temporal(archivo.name, archivo.getvalue())
            placeholders = mod_tpl.detectar_placeholders(tmp)
            try:
                registro = mod_tpl.guardar_template(tmp, {
                    "Nombre_Template": nombre, "Tipo_Demanda": tipo,
                    "Banco_Entidad": entidad, "Moneda": moneda,
                    "Numero_Titulos": n_titulos, "Tiene_Hipoteca": hip,
                    "Tiene_Prenda": pre, "Tiene_Avalistas": ava,
                    "Tiene_Codeudores": cod, "Tipo_Instrumento": tipo_inst,
                    "Usuario_Carga": usuario, "Observaciones": obs, "Activo": True,
                })
            except ExcelAbiertoError as exc:
                _mostrar_error_excel(exc)
                return
            registrar_auditoria("CARGA_MODELO", usuario,
                                id_template=registro["ID_Template"], resultado="OK",
                                observaciones=nombre)
            if placeholders:
                st.success(
                    f"✅ Modelo guardado ({registro['ID_Template']}). "
                    f"Placeholders detectados: {', '.join(placeholders)}"
                )
            else:
                st.warning(
                    "⚠️ El modelo NO contiene placeholders {{VARIABLE}}. La "
                    "generación automática directa queda BLOQUEADA para este "
                    "modelo. Opciones:"
                )
                for op in mod_tpl.opciones_sin_placeholders():
                    st.markdown(f"- {op}")
                ruta = BASE_DIR / registro["Ruta_Template"]
                if st.session_state.get("t_ult_sin_ph") != registro["ID_Template"]:
                    st.session_state["t_ult_sin_ph"] = registro["ID_Template"]
                copia = mod_tpl.crear_copia_con_placeholders(ruta)
                st.info(
                    f"Se creó una copia con placeholders sugeridos: "
                    f"`{copia.name}` (en database/templates/). Edítela en Word "
                    "y cárguela nuevamente."
                )
                st.download_button(
                    "⬇️ Descargar copia con placeholders sugeridos",
                    data=copia.read_bytes(), file_name=copia.name, key="t_copia",
                )

    st.divider()
    st.markdown("### Modelos cargados")
    try:
        df = mod_tpl.cargar_templates()
    except ExcelAbiertoError as exc:
        _mostrar_error_excel(exc)
        return
    if df.empty:
        st.info("Aún no hay modelos en la biblioteca.")
    else:
        st.dataframe(df, width="stretch", hide_index=True)


# ---------------------------------------------------------------------------
# TAB 4 — Nuevo caso / ingreso de documentos
# ---------------------------------------------------------------------------

def tab_nuevo_caso() -> None:
    st.subheader("🗂️ Nuevo caso / ingreso de documentos")

    with st.expander("➕ Crear caso nuevo", expanded=True):
        with st.form("c_form"):
            c1, c2 = st.columns(2)
            with c1:
                deudor = st.text_input("Cliente / deudor principal *")
                rut = st.text_input("RUT del deudor")
            with c2:
                opciones = ENTIDADES + [OPCION_OTRA_ENTIDAD]
                entidad_sel = st.selectbox("Banco / entidad *", opciones)
                entidad_otra = st.text_input("Si es «Otra», especifique")
            n_operacion = st.text_input("N° de operación (opcional)")
            usuario = st.text_input("Usuario (opcional)")
            obs = st.text_input("Observaciones (opcional)")
            crear = st.form_submit_button("Crear caso", type="primary")
        if crear:
            entidad = entidad_otra.strip() if entidad_sel == OPCION_OTRA_ENTIDAD else entidad_sel
            if not deudor.strip() or not entidad:
                st.error("Debe indicar el deudor y la entidad.")
            else:
                try:
                    caso = mod_casos.crear_caso({
                        "Banco_Entidad": entidad, "Cliente_Deudor": deudor,
                        "RUT_Deudor": rut, "Numero_Operacion": n_operacion,
                        "Usuario_Carga": usuario, "Observaciones": obs,
                    })
                except ExcelAbiertoError as exc:
                    _mostrar_error_excel(exc)
                    return
                registrar_auditoria("CREACION_CASO", usuario,
                                    id_caso=caso["ID_Caso"], resultado="OK",
                                    observaciones=f"{deudor} / {entidad}")
                st.success(f"✅ Caso creado: **{caso['ID_Caso']}** "
                           f"(carpeta {caso['Ruta_Carpeta_Caso']}).")

    try:
        df_casos = mod_casos.cargar_casos()
    except ExcelAbiertoError as exc:
        _mostrar_error_excel(exc)
        return
    if df_casos.empty:
        st.info("Aún no hay casos creados.")
        return

    st.divider()
    st.markdown("### Documentos del caso")
    id_caso = st.selectbox(
        "Caso", df_casos["ID_Caso"].tolist(),
        format_func=lambda i: f"{i} — "
        f"{df_casos.loc[df_casos['ID_Caso'] == i, 'Cliente_Deudor'].iloc[0]}",
        key="c_sel",
    )
    tipo_doc = st.selectbox("Tipo de documento", TIPOS_DOCUMENTO, key="c_tipo_doc")
    archivos = st.file_uploader(
        "Documentos del banco (PDF o Word) — puede subir varios",
        type=["pdf", "docx", "doc"], accept_multiple_files=True, key="c_docs",
    )
    if archivos and st.button("Guardar documentos en el caso", type="primary", key="c_save"):
        guardados = []
        for a in archivos:
            try:
                ruta = mod_casos.guardar_documento_caso(
                    id_caso, a.name, a.getvalue(), tipo_doc
                )
                guardados.append(ruta.name)
            except OSError as exc:
                st.error(f"No se pudo guardar {a.name}: {exc}")
        if guardados:
            registrar_auditoria("CARGA_DOCUMENTOS_CASO", "", id_caso=id_caso,
                                resultado="OK",
                                observaciones=f"{len(guardados)} documento(s): "
                                + ", ".join(guardados))
            st.success(f"✅ Guardados en el caso: {', '.join(guardados)}")

    docs = mod_casos.documentos_del_caso(id_caso)
    if docs:
        st.markdown("**Documentos guardados:**")
        for d in docs:
            st.markdown(f"- `{d.name}`")
    else:
        st.caption("Este caso aún no tiene documentos.")

    st.divider()
    st.markdown("### Casos existentes")
    st.dataframe(df_casos, width="stretch", hide_index=True)


# ---------------------------------------------------------------------------
# TAB 5 — Extracción y validación de datos
# ---------------------------------------------------------------------------

def tab_extraccion() -> None:
    st.subheader("🧠 Extracción y validación de datos del caso")

    try:
        df_casos = mod_casos.cargar_casos()
    except ExcelAbiertoError as exc:
        _mostrar_error_excel(exc)
        return
    if df_casos.empty:
        st.info("Cree primero un caso en la pestaña «Nuevo Caso».")
        return

    id_caso = st.selectbox(
        "Caso", df_casos["ID_Caso"].tolist(),
        format_func=lambda i: f"{i} — "
        f"{df_casos.loc[df_casos['ID_Caso'] == i, 'Cliente_Deudor'].iloc[0]}",
        key="e_caso",
    )
    caso = df_casos[df_casos["ID_Caso"] == id_caso].iloc[0]

    # --- Extracción automática opcional ---
    disponible, provider = mod_extr.ocr_disponible()
    docs = mod_casos.documentos_del_caso(id_caso)
    with st.expander("🤖 Extracción automática con IA (opcional)"):
        if not disponible:
            st.info("No hay API key configurada. Puede ingresar los datos manualmente.")
        elif not docs:
            st.info("El caso no tiene documentos cargados.")
        else:
            st.caption(f"Proveedor configurado: {provider}")
            doc_sel = st.selectbox("Documento", [d.name for d in docs], key="e_doc")
            tipo_ext = st.selectbox(
                "Tipo de extracción", ["pagare", "mutuo", "cartola"], key="e_tipo"
            )
            autorizado = _gate_confidencialidad("e_gate")
            if st.button("Extraer datos del documento", key="e_extraer",
                         disabled=not autorizado):
                ruta = next(d for d in docs if d.name == doc_sel)
                with st.spinner("Extrayendo datos…"):
                    datos = mod_extr.extract_document_data(str(ruta), tipo_ext)
                if "_error" in datos:
                    st.error(datos["_error"])
                    registrar_auditoria("OCR_CASO_FALLIDO", "", id_caso=id_caso,
                                        resultado="ERROR",
                                        observaciones=datos["_error"])
                else:
                    st.session_state["e_extraccion"] = datos
                    registrar_auditoria("OCR_CASO", "", id_caso=id_caso,
                                        resultado="OK", observaciones=doc_sel)
        ext = st.session_state.get("e_extraccion")
        if ext:
            st.markdown("**Datos extraídos (revíselos y úselos en los formularios de abajo):**")
            st.json(ext)
            st.caption(
                "Los campos vacíos o NO_DETECTADO deben completarse manualmente "
                "contra el documento original. La app no inventa datos."
            )

    # --- Instrumentos ---
    st.divider()
    st.markdown("### 📄 Instrumentos / títulos ejecutivos")
    ext = st.session_state.get("e_extraccion", {}) or {}
    with st.form("e_form_inst"):
        c1, c2, c3 = st.columns(3)
        with c1:
            tipo_i = st.selectbox("Tipo *", TIPOS_INSTRUMENTO)
            numero = st.text_input("N° instrumento/operación *",
                                   value=str(ext.get("Numero_Pagare")
                                             or ext.get("Numero_Operacion") or ""))
            f_susc = st.text_input("Fecha suscripción (DD/MM/YYYY) *",
                                   value=str(ext.get("Fecha_Suscripcion")
                                             or ext.get("Fecha_Escritura") or ""))
            f_venc = st.text_input("Fecha vencimiento",
                                   value=str(ext.get("Fecha_Vencimiento") or ""))
            f_mora = st.text_input("Fecha de mora",
                                   value=str(ext.get("Fecha_Mora") or ""))
        with c2:
            banco = st.text_input("Banco acreedor *",
                                  value=str(ext.get("Banco_Acreedor")
                                            or caso["Banco_Entidad"]))
            ejecutivo = st.text_input("Ejecutivo suscriptor (por el banco)",
                                      value=str(ext.get("Nombre_Ejecutivo_Suscriptor") or ""))
            deudor = st.text_input("Deudor principal *",
                                   value=str(ext.get("Deudor_Principal")
                                             or caso["Cliente_Deudor"]))
            rut_deudor = st.text_input("RUT deudor principal",
                                       value=str(ext.get("RUT_Deudor_Principal")
                                                 or caso["RUT_Deudor"]))
            domicilio_comp = st.text_input("Domicilio/competencia",
                                           value=str(ext.get("Domicilio_Competencia") or ""))
        with c3:
            monto_orig = st.text_input("Monto original",
                                       value=str(ext.get("Monto_Original") or ""))
            saldo = st.text_input("Saldo insoluto *",
                                  value=str(ext.get("Saldo_Insoluto") or ""))
            moneda = st.selectbox("Moneda", MONEDAS,
                                  index=MONEDAS.index(str(ext.get("Moneda", "CLP")).upper())
                                  if str(ext.get("Moneda", "CLP")).upper() in MONEDAS else 0)
            tasa = st.text_input("Tasa de interés",
                                 value=str(ext.get("Tasa_Interes") or ""))
            penal = st.text_input("Interés penal",
                                  value=str(ext.get("Interes_Penal") or ""))
        c4, c5, c6 = st.columns(3)
        with c4:
            acel = st.checkbox("Cláusula de aceleración",
                               value=es_verdadero(ext.get("Clausula_Aceleracion")))
        with c5:
            protesto = st.checkbox("Liberación de protesto",
                                   value=es_verdadero(ext.get("Liberacion_Protesto")))
        with c6:
            firmas = st.checkbox("Firmas autorizadas ante notario",
                                 value=es_verdadero(ext.get("Firmas_Autorizadas_Notarialmente")))
        c7, c8 = st.columns(2)
        with c7:
            fuente_doc = st.text_input("Fuente: documento",
                                       value=str(ext.get("_fuente_documento") or ""))
        with c8:
            fuente_pag = st.text_input("Fuente: página")
        fuente_txt = st.text_input("Fuente: texto de respaldo")
        obs_i = st.text_input("Observaciones del instrumento")
        agregar_i = st.form_submit_button("➕ Agregar instrumento", type="primary")

    if agregar_i:
        if not numero.strip() or not deudor.strip() or not saldo.strip() or not f_susc.strip():
            st.error("Complete los campos obligatorios del instrumento "
                     "(N°, fecha suscripción, deudor y saldo insoluto).")
        elif parsear_fecha(f_susc) is None:
            st.error("Fecha de suscripción inválida (use DD/MM/YYYY).")
        else:
            try:
                reg = mod_casos.agregar_instrumento(id_caso, {
                    "Tipo_Instrumento": tipo_i, "Numero_Instrumento": numero,
                    "Fecha_Suscripcion": parsear_fecha(f_susc),
                    "Fecha_Vencimiento": parsear_fecha(f_venc),
                    "Fecha_Mora": parsear_fecha(f_mora),
                    "Banco_Acreedor": banco, "Entidad_Acreedora": banco,
                    "Nombre_Ejecutivo_Suscriptor": ejecutivo,
                    "Deudor_Principal": deudor, "RUT_Deudor_Principal": rut_deudor,
                    "Monto_Original": monto_orig, "Saldo_Insoluto": saldo,
                    "Moneda": moneda, "Equivalencia_Pesos": "",
                    "Tasa_Interes": tasa, "Interes_Penal": penal,
                    "Clausula_Aceleracion": acel, "Liberacion_Protesto": protesto,
                    "Firmas_Autorizadas_Notarialmente": firmas,
                    "Domicilio_Competencia": domicilio_comp,
                    "Fuente_Documento": fuente_doc, "Fuente_Pagina": fuente_pag,
                    "Fuente_Texto": fuente_txt, "Observaciones": obs_i,
                })
            except ExcelAbiertoError as exc:
                _mostrar_error_excel(exc)
                return
            registrar_auditoria("ALTA_INSTRUMENTO", "", id_caso=id_caso,
                                resultado="OK",
                                observaciones=f"{tipo_i} N° {numero}")
            st.success(f"✅ Instrumento agregado: {reg['ID_Instrumento']}")

    try:
        df_inst = mod_casos.cargar_instrumentos(id_caso)
    except ExcelAbiertoError as exc:
        _mostrar_error_excel(exc)
        return
    if not df_inst.empty:
        st.dataframe(df_inst, width="stretch", hide_index=True)
        borrar = st.selectbox("Eliminar instrumento",
                              ["(ninguno)"] + df_inst["ID_Instrumento"].tolist(),
                              key="e_del_inst")
        if borrar != "(ninguno)" and st.button("🗑️ Eliminar", key="e_del_inst_btn"):
            mod_casos.eliminar_fila(INSTRUMENTS_XLSX, "ID_Instrumento", borrar)
            registrar_auditoria("BAJA_INSTRUMENTO", "", id_caso=id_caso,
                                resultado="OK", observaciones=borrar)
            st.rerun()

    # --- Partes / obligados ---
    st.divider()
    st.markdown("### 👥 Partes / obligados (deudores, avalistas, fiadores…)")
    with st.form("e_form_parte"):
        c1, c2, c3 = st.columns(3)
        with c1:
            p_nombre = st.text_input("Nombre *")
            p_rut = st.text_input("RUT")
        with c2:
            p_calidad = st.selectbox("Calidad jurídica *", CALIDADES_JURIDICAS)
            p_domicilio = st.text_input("Domicilio")
        with c3:
            ids_inst = df_inst["ID_Instrumento"].tolist() if not df_inst.empty else []
            p_responde = st.multiselect(
                "Responde por instrumentos (vacío = TODOS)", ids_inst
            )
            p_monto = st.text_input("Monto de responsabilidad")
            p_moneda = st.selectbox("Moneda responsabilidad", MONEDAS)
        p_limitacion = st.text_input("Limitación de responsabilidad (texto, opcional)")
        c4, c5, c6 = st.columns(3)
        with c4:
            p_fdoc = st.text_input("Fuente: documento", key="p_fdoc")
        with c5:
            p_fpag = st.text_input("Fuente: página", key="p_fpag")
        with c6:
            p_ftxt = st.text_input("Fuente: texto", key="p_ftxt")
        p_obs = st.text_input("Observaciones de la parte")
        agregar_p = st.form_submit_button("➕ Agregar parte", type="primary")

    if agregar_p:
        if not p_nombre.strip():
            st.error("Debe indicar el nombre de la parte.")
        else:
            try:
                reg = mod_casos.agregar_parte(id_caso, {
                    "ID_Instrumento": ",".join(p_responde) if p_responde else "",
                    "Nombre": p_nombre, "RUT": p_rut,
                    "Tipo_Parte": "DEMANDADO", "Calidad_Juridica": p_calidad,
                    "Responde_Por_Instrumento": ",".join(p_responde)
                    if p_responde else mod_casos.RESPONDE_TODOS,
                    "Monto_Responsabilidad": p_monto,
                    "Moneda_Responsabilidad": p_moneda,
                    "Limitacion_Responsabilidad": p_limitacion,
                    "Domicilio": p_domicilio, "Fuente_Documento": p_fdoc,
                    "Fuente_Pagina": p_fpag, "Fuente_Texto": p_ftxt,
                    "Observaciones": p_obs,
                })
            except ExcelAbiertoError as exc:
                _mostrar_error_excel(exc)
                return
            registrar_auditoria("ALTA_PARTE", "", id_caso=id_caso, resultado="OK",
                                observaciones=f"{p_nombre} ({p_calidad})")
            st.success(f"✅ Parte agregada: {reg['ID_Parte']}")

    try:
        df_partes = mod_casos.cargar_partes(id_caso)
    except ExcelAbiertoError as exc:
        _mostrar_error_excel(exc)
        return
    if not df_partes.empty:
        st.dataframe(df_partes, width="stretch", hide_index=True)
        borrar_p = st.selectbox("Eliminar parte",
                                ["(ninguna)"] + df_partes["ID_Parte"].tolist(),
                                key="e_del_parte")
        if borrar_p != "(ninguna)" and st.button("🗑️ Eliminar parte", key="e_del_parte_btn"):
            mod_casos.eliminar_fila(PARTIES_XLSX, "ID_Parte", borrar_p)
            registrar_auditoria("BAJA_PARTE", "", id_caso=id_caso,
                                resultado="OK", observaciones=borrar_p)
            st.rerun()


# ---------------------------------------------------------------------------
# TAB 6 — Generador de demandas
# ---------------------------------------------------------------------------

def tab_generador() -> None:
    st.subheader("⚙️ Generador de demandas ejecutivas")

    try:
        df_casos = mod_casos.cargar_casos()
        df_templates = mod_tpl.cargar_templates()
    except ExcelAbiertoError as exc:
        _mostrar_error_excel(exc)
        return
    if df_casos.empty:
        st.info("Cree primero un caso con instrumentos y partes.")
        return

    id_caso = st.selectbox(
        "Caso", df_casos["ID_Caso"].tolist(),
        format_func=lambda i: f"{i} — "
        f"{df_casos.loc[df_casos['ID_Caso'] == i, 'Cliente_Deudor'].iloc[0]}",
        key="g_caso",
    )
    # Al cambiar de caso se descarta todo estado del caso anterior (contexto,
    # revisión, personería y demanda generada) para evitar mezclas.
    if st.session_state.get("g_caso_actual") != id_caso:
        for k in ("g_contexto", "g_revision", "g_revision_ok", "g_rev_hash",
                  "g_mandato", "g_generada", "g_generada_id"):
            st.session_state.pop(k, None)
        for campo in CAMPOS_EDITABLES:
            st.session_state.pop(f"g_edit_{campo}", None)
        st.session_state["g_caso_actual"] = id_caso
    caso = df_casos[df_casos["ID_Caso"] == id_caso].iloc[0]
    df_inst = mod_casos.cargar_instrumentos(id_caso)
    df_partes = mod_casos.cargar_partes(id_caso)

    # --- Clasificación ---
    clasif = mod_clasif.clasificar_caso(df_inst, df_partes)
    if clasif["bloqueo"]:
        st.error(f"⛔ {clasif['razon']}")
        registrar_auditoria("GENERACION_BLOQUEADA_SIN_TITULOS", "",
                            id_caso=id_caso, resultado="BLOQUEADO",
                            observaciones=clasif["razon"])
        return

    conf = clasif["confianza"]
    st.markdown(
        f"**Tipo de demanda sugerido:** {clasif['tipo_sugerido']} "
        f"({'🟢' if conf == 'alta' else '🟡' if conf == 'media' else '🔴'} confianza {conf})"
    )
    st.caption(f"Razón: {clasif['razon']}")
    if clasif["alternativas"]:
        st.caption(f"Alternativas: {', '.join(clasif['alternativas'])}")

    idx_tipo = TIPOS_DEMANDA.index(clasif["tipo_sugerido"]) \
        if clasif["tipo_sugerido"] in TIPOS_DEMANDA else 0
    tipo_demanda = st.selectbox("Tipo de demanda (puede cambiarlo)", TIPOS_DEMANDA,
                                index=idx_tipo, key="g_tipo")

    # --- Modelo ---
    moneda_caso = (str(df_inst["Moneda"].iloc[0]) if not df_inst.empty else "CLP")
    sug = mod_clasif.sugerir_template(df_templates, tipo_demanda,
                                      str(caso["Banco_Entidad"]), moneda_caso)
    activos = df_templates[
        df_templates["Activo"].astype(str).str.lower().isin(("true", "1", "si", "sí"))
    ]
    if activos.empty:
        st.error("No hay modelos activos con placeholders. Cargue uno en la Biblioteca.")
        return
    st.caption(f"Modelo sugerido: {sug['razon']}")
    ids_tpl = activos["ID_Template"].tolist()
    idx_tpl = ids_tpl.index(sug["sugerido"]["ID_Template"]) \
        if sug["sugerido"] is not None and sug["sugerido"]["ID_Template"] in ids_tpl else 0
    id_template = st.selectbox(
        "Modelo Word", ids_tpl, index=idx_tpl,
        format_func=lambda i: f"{i} — "
        f"{activos.loc[activos['ID_Template'] == i, 'Nombre_Template'].iloc[0]}",
        key="g_tpl",
    )
    template = activos[activos["ID_Template"] == id_template].iloc[0]

    # --- Personería ---
    st.divider()
    st.markdown("### Personería del ejecutante")
    c1, c2 = st.columns(2)
    with c1:
        ejecutivo_default = ""
        if not df_inst.empty:
            ejecutivo_default = str(df_inst["Nombre_Ejecutivo_Suscriptor"].iloc[0] or "")
        g_nombre = st.text_input("Nombre del ejecutivo (apoderado del banco)",
                                 value=ejecutivo_default, key="g_mand_nombre")
    with c2:
        fechas = [parsear_fecha(v) for v in df_inst["Fecha_Suscripcion"]] \
            if not df_inst.empty else []
        fechas_v = [f for f in fechas if f is not None]
        fecha_ref = min(fechas_v).date() if fechas_v else date.today()
        st.caption(f"Fecha de referencia (título más antiguo): "
                   f"{fecha_ref.strftime('%d/%m/%Y')}")
    if st.button("Buscar personería vigente", key="g_mand_buscar"):
        try:
            dfm = mod_mand.cargar_mandatos()
        except ExcelAbiertoError as exc:
            _mostrar_error_excel(exc)
            return
        res = mod_mand.buscar_personeria(dfm, g_nombre,
                                         str(caso["Banco_Entidad"]), fecha_ref)
        if not res["mismo_dia"].empty:
            st.warning(MSG_REVOCACION_MISMO_DIA)
        if res["vigente"] is None:
            st.error("No se encontró personería vigente para ese ejecutivo/entidad/fecha.")
            st.session_state.pop("g_mandato", None)
        else:
            st.session_state["g_mandato"] = res["vigente"].to_dict()
            # Autocompletar el representante que comparece si está vacío
            if not str(st.session_state.get("g_rep", "")).strip():
                st.session_state["g_rep"] = str(res["vigente"]["Nombre_Ejecutivo"])
    mandato = st.session_state.get("g_mandato")
    if mandato:
        st.success(
            f"Personería seleccionada: {mandato['Nombre_Ejecutivo']} — "
            f"Rep. N° {mandato['Repertorio']} "
            f"({formatear_fecha(mandato['Fecha_Otorgamiento'])})"
        )
    else:
        st.info("Aún no hay personería seleccionada (la revisión la exigirá).")

    # --- Campos manuales ---
    st.divider()
    st.markdown("### Datos de la presentación")
    c1, c2 = st.columns(2)
    with c1:
        tribunal = st.text_input("Tribunal (ej: S.J.L. en lo Civil de Santiago) *",
                                 key="g_tribunal")
        demandante = st.text_input("Demandante", value=str(caso["Banco_Entidad"]),
                                   key="g_demandante")
        rut_demandante = st.text_input("RUT demandante", key="g_rut_dem")
        st.session_state.setdefault(
            "g_rep", str(mandato["Nombre_Ejecutivo"]) if mandato else ""
        )
        representante = st.text_input(
            "Abogado/representante que comparece *", key="g_rep",
        )
    with c2:
        bienes = st.text_area("Bienes para la traba de embargo *", key="g_bienes")
        equivalencia = st.text_input(
            "Equivalencia en pesos (obligatoria si USD/UF)", key="g_equiv"
        )
        garantias = st.text_area("Otrosí de garantías (opcional)", key="g_garantias")
        docs_extra = st.text_area(
            "Documentos adicionales del primer otrosí (uno por línea)", key="g_docs_extra"
        )

    if st.button("📝 Componer demanda (vista previa)", type="primary", key="g_componer"):
        campos = {
            "TRIBUNAL": tribunal, "MATERIA": tipo_demanda,
            "DEMANDANTE": demandante, "RUT_DEMANDANTE": rut_demandante,
            "REPRESENTANTE_DEMANDANTE": representante,
            "BIENES_EMBARGO": bienes, "EQUIVALENCIA_PESOS": equivalencia,
            "GARANTIAS": garantias, "DOCUMENTOS_EXTRA": docs_extra,
        }
        contexto = mod_gen.componer_contexto(caso, df_inst, df_partes, mandato, campos)
        st.session_state["g_contexto"] = contexto
        # Refrescar los bloques editables con el nuevo contenido compuesto
        for campo in CAMPOS_EDITABLES:
            st.session_state[f"g_edit_{campo}"] = contexto[campo]
        for k in ("g_revision", "g_revision_ok", "g_rev_hash", "g_generada",
                  "g_generada_id"):
            st.session_state.pop(k, None)

    contexto = st.session_state.get("g_contexto")
    if not contexto:
        return

    st.divider()
    st.markdown("### Vista previa editable")
    st.caption(
        "Revise y edite los bloques generados. Los textos con NO_DETECTADO "
        "deben completarse con datos reales — la app no los inventa."
    )
    alturas = {"DEMANDADOS": 120, "TITULOS_EJECUTIVOS": 160,
               "RELATO_DE_LOS_HECHOS": 160, "PETITORIO": 200,
               "DOCUMENTOS_PRIMER_OTROSI": 120}
    for campo in CAMPOS_EDITABLES:
        st.session_state.setdefault(f"g_edit_{campo}", contexto[campo])
        contexto[campo] = st.text_area(campo, height=alturas[campo],
                                       key=f"g_edit_{campo}")
    st.session_state["g_contexto"] = contexto

    # Si el contenido cambió DESPUÉS de una revisión aprobada, la revisión
    # queda invalidada: nunca se genera texto distinto al revisado.
    huella_actual = _huella_contexto(contexto)
    if "g_revision" in st.session_state and \
            st.session_state.get("g_rev_hash") != huella_actual:
        st.session_state.pop("g_revision", None)
        st.session_state.pop("g_revision_ok", None)
        st.info(
            "El contenido de la demanda cambió después de la última revisión. "
            "Vuelva a ejecutar la revisión jurídica antes de generar."
        )

    # --- Revisión jurídica ---
    st.divider()
    if st.button("⚖️ Revisar concordancia jurídica", type="primary", key="g_revisar"):
        ruta_tpl = BASE_DIR / str(template["Ruta_Template"])
        texto_final = ""
        try:
            TEMP_DIR.mkdir(parents=True, exist_ok=True)
            preview = TEMP_DIR / f"preview_{id_caso}.docx"
            from docxtpl import DocxTemplate

            tpl = DocxTemplate(str(ruta_tpl))
            tpl.render(contexto)
            tpl.save(str(preview))
            texto_final = mod_tpl.texto_completo_docx(preview)
        except Exception as exc:
            st.error(f"No se pudo renderizar la vista previa del modelo: {exc}")
            return
        revision = mod_rev.revisar_demanda(contexto, df_inst, df_partes,
                                           mandato, texto_final)
        st.session_state["g_revision"] = revision
        st.session_state["g_revision_ok"] = not revision.bloquea_descarga
        st.session_state["g_rev_hash"] = _huella_contexto(contexto)
        if revision.bloquea_descarga:
            registrar_auditoria(
                "GENERACION_BLOQUEADA_REVISION", "", id_caso=id_caso,
                id_template=str(template["ID_Template"]), resultado="BLOQUEADO",
                observaciones=f"{len(revision.criticos)} error(es) crítico(s)",
            )

    revision = st.session_state.get("g_revision")
    if revision is None:
        st.info("Ejecute la revisión jurídica para habilitar la generación final.")
        return

    if revision.criticos:
        st.error(
            f"⛔ Se detectaron {len(revision.criticos)} error(es) crítico(s). "
            "La descarga final está BLOQUEADA hasta corregirlos."
        )
        for h in revision.criticos:
            st.error(f"**Error crítico [{h.regla}] — {h.ubicacion}:** "
                     f"{h.explicacion}\n\n➡️ *Cómo corregirlo:* {h.correccion}")
    for h in revision.advertencias:
        st.warning(f"**Advertencia [{h.regla}] — {h.ubicacion}:** "
                   f"{h.explicacion} ➡️ {h.correccion}")
    if not revision.criticos:
        st.success("✅ Revisión aprobada: sin errores críticos.")

    if revision.bloquea_descarga:
        return

    # --- Checklist legal obligatorio ---
    st.divider()
    st.markdown("### ✅ Checklist legal obligatorio")
    checks = [st.checkbox(item, key=f"g_chk_{i}") for i, item in enumerate(CHECKLIST_LEGAL)]
    checklist_ok = all(checks)
    if not checklist_ok:
        st.info("Debe marcar TODOS los puntos del checklist para generar la demanda final.")

    usuario_gen = st.text_input("Usuario que genera (opcional)", key="g_usuario")
    if st.button("📄 Generar demanda final (.docx)", type="primary",
                 key="g_generar", disabled=not checklist_ok):
        ruta_tpl = BASE_DIR / str(template["Ruta_Template"])
        nombre = mod_gen.nombre_archivo_demanda(
            str(caso["Banco_Entidad"]), str(caso["Cliente_Deudor"]),
            tipo_demanda, id_caso,
        )
        try:
            archivo = mod_gen.generar_demanda_docx(ruta_tpl, contexto, nombre)
            registro = mod_gen.registrar_demanda_generada(
                id_caso, str(template["ID_Template"]),
                str(mandato["ID_Mandato"]) if mandato else "",
                tipo_demanda, archivo, contexto, usuario_gen,
                len(revision.criticos), len(revision.advertencias), True,
            )
        except ExcelAbiertoError as exc:
            _mostrar_error_excel(exc)
            return
        except Exception as exc:
            st.error(f"No se pudo generar la demanda: {exc}")
            registrar_auditoria("GENERACION_DEMANDA", usuario_gen, id_caso=id_caso,
                                resultado="ERROR", observaciones=str(exc))
            return
        mod_casos.actualizar_caso(id_caso, {
            "Tipo_Caso_Detectado": tipo_demanda, "Estado": "DEMANDA_GENERADA",
        })
        registrar_auditoria(
            "GENERACION_DEMANDA", usuario_gen, id_caso=id_caso,
            id_mandato=str(mandato["ID_Mandato"]) if mandato else "",
            id_template=str(template["ID_Template"]), resultado="OK",
            observaciones=archivo.name,
        )
        st.session_state["g_generada"] = str(archivo)
        st.session_state["g_generada_id"] = registro["ID_Demanda"]

    generada = st.session_state.get("g_generada")
    if generada and Path(generada).exists():
        st.success(f"✅ Demanda generada: `{Path(generada).name}` "
                   f"(ID {st.session_state.get('g_generada_id', '')})")
        st.download_button(
            "⬇️ Descargar demanda final", data=Path(generada).read_bytes(),
            file_name=Path(generada).name,
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            key="g_descargar",
            on_click=lambda: registrar_auditoria(
                "DESCARGA_DEMANDA", "", id_caso=id_caso, resultado="OK",
                observaciones=Path(generada).name,
            ),
        )
        st.warning(ADVERTENCIA_LEGAL)


# ---------------------------------------------------------------------------
# TAB 7 — Revisor jurídico (re-revisión de demandas generadas)
# ---------------------------------------------------------------------------

def tab_revisor() -> None:
    st.subheader("⚖️ Revisor jurídico")
    st.caption(
        "Re-ejecuta el control de concordancia cuerpo–petitorio sobre una "
        "demanda ya generada, usando el contexto guardado y los datos del caso."
    )
    try:
        df_gen = read_excel_or_empty(GENERATED_XLSX)
    except ExcelAbiertoError as exc:
        _mostrar_error_excel(exc)
        return
    if df_gen.empty:
        st.info("Aún no hay demandas generadas.")
        return

    id_dda = st.selectbox(
        "Demanda generada", df_gen["ID_Demanda"].tolist(),
        format_func=lambda i: f"{i} — "
        f"{Path(str(df_gen.loc[df_gen['ID_Demanda'] == i, 'Archivo'].iloc[0])).name}",
        key="r_dda",
    )
    fila = df_gen[df_gen["ID_Demanda"] == id_dda].iloc[0]

    if st.button("Re-ejecutar revisión", type="primary", key="r_run"):
        import json as _json

        ctx_path = BASE_DIR / str(fila["Contexto_JSON"])
        if not str(fila["Contexto_JSON"]).strip() or not ctx_path.exists():
            st.error("No se encontró el contexto JSON de esta demanda.")
            return
        try:
            contexto = _json.loads(ctx_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            st.error(f"No se pudo leer el contexto: {exc}")
            return
        id_caso = str(fila["ID_Caso"])
        df_inst = mod_casos.cargar_instrumentos(id_caso)
        df_partes = mod_casos.cargar_partes(id_caso)
        mandato = None
        if str(fila["ID_Mandato"]).strip():
            dfm = mod_mand.cargar_mandatos()
            fm = dfm[dfm["ID_Mandato"] == str(fila["ID_Mandato"])]
            if not fm.empty:
                mandato = fm.iloc[0].to_dict()
        archivo = BASE_DIR / str(fila["Archivo"])
        texto = mod_tpl.texto_completo_docx(archivo) if archivo.exists() else ""
        revision = mod_rev.revisar_demanda(contexto, df_inst, df_partes, mandato, texto)
        registrar_auditoria("RE_REVISION_DEMANDA", "", id_caso=id_caso,
                            resultado="BLOQUEADO" if revision.bloquea_descarga else "OK",
                            observaciones=f"{id_dda}: {len(revision.criticos)} críticos, "
                            f"{len(revision.advertencias)} advertencias")
        if revision.criticos:
            st.error(f"⛔ {len(revision.criticos)} error(es) crítico(s):")
            for h in revision.criticos:
                st.error(f"**[{h.regla}] {h.ubicacion}:** {h.explicacion} "
                         f"➡️ {h.correccion}")
        for h in revision.advertencias:
            st.warning(f"**[{h.regla}] {h.ubicacion}:** {h.explicacion}")
        if not revision.criticos:
            st.success("✅ Sin errores críticos.")


# ---------------------------------------------------------------------------
# TAB 8 — Historial de demandas
# ---------------------------------------------------------------------------

def tab_historial() -> None:
    st.subheader("🗃️ Demandas generadas / historial")
    try:
        df = read_excel_or_empty(GENERATED_XLSX)
    except ExcelAbiertoError as exc:
        _mostrar_error_excel(exc)
        return
    if df.empty:
        st.info("Aún no hay demandas generadas.")
        return
    st.dataframe(df.sort_index(ascending=False),
                 width="stretch", hide_index=True)
    id_dda = st.selectbox("Descargar demanda", df["ID_Demanda"].tolist(), key="h_dda")
    fila = df[df["ID_Demanda"] == id_dda].iloc[0]
    ruta = BASE_DIR / str(fila["Archivo"])
    if ruta.exists():
        st.download_button(
            f"⬇️ Descargar {ruta.name}", data=ruta.read_bytes(),
            file_name=ruta.name,
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            key="h_down",
        )
    else:
        st.error("El archivo de esta demanda no existe en el disco.")


# ---------------------------------------------------------------------------
# TAB 9 — Auditoría
# ---------------------------------------------------------------------------

def tab_auditoria() -> None:
    st.subheader("🧾 Registro de auditoría")
    try:
        log = leer_auditoria()
    except ExcelAbiertoError as exc:
        _mostrar_error_excel(exc)
        return
    if log.empty:
        st.info("Aún no hay registros de auditoría.")
    else:
        st.dataframe(log.sort_index(ascending=False),
                     width="stretch", hide_index=True)


# ---------------------------------------------------------------------------
# Datos de ejemplo
# ---------------------------------------------------------------------------

def cargar_datos_ejemplo() -> None:
    """Datos ficticios de demostración. Es idempotente: puede presionarse el
    botón varias veces sin crear duplicados."""
    ejemplos = [
        ("María Fernanda Soto Pérez", "Banco Santander", "15/03/2019", None,
         "Juan Ricardo San Martín Urrejola", "Santiago", "12345-2019"),
        ("Pedro Antonio Rojas Díaz", "Banco Santander", "10/01/2020", "20/06/2023",
         "Iván Torrealba Acevedo", "Santiago", "9876-2020"),
        ("Carolina Andrea Muñoz Lagos", "GRC", "05/08/2021", None,
         "Patricio Raby Benavente", "Valparaíso", "4455-2021"),
    ]
    df_m = mod_mand.cargar_mandatos()
    for nom, ent, fo, fr, notario, ciudad, rep in ejemplos:
        ya_existe = not mod_mand.detectar_duplicados(
            df_m, ent, normalizar_nombre(nom), parsear_fecha(fo), rep
        ).empty
        if ya_existe:
            continue
        mod_mand.guardar_mandato({
            "Nombre_Ejecutivo": nom, "Entidad_Representada": ent,
            "Fecha_Otorgamiento": fo, "Fecha_Revocacion": fr,
            "Notario_Titular": notario, "Ciudad_Notaria": ciudad,
            "Repertorio": rep, "Facultad_Pagare": True,
            "Texto_Facultad_Pagare": "El mandatario podrá suscribir, aceptar y "
            "renovar pagarés y demás títulos de crédito (texto de ejemplo).",
            "Usuario_Carga": "sistema_ejemplo",
            "Observaciones": "Dato de ejemplo ficticio.",
        })

    # Caso de demostración completo, listo para generar una demanda
    df_c = mod_casos.cargar_casos()
    if not df_c.empty and (df_c["Numero_Operacion"] == "DEMO-2024-001").any():
        return
    caso = mod_casos.crear_caso({
        "Banco_Entidad": "Banco Santander",
        "Cliente_Deudor": "Comercial Los Álamos Limitada",
        "RUT_Deudor": "76.111.222-3",
        "Numero_Operacion": "DEMO-2024-001",
        "Usuario_Carga": "sistema_ejemplo",
        "Observaciones": "Caso de demostración con datos ficticios.",
    })
    id_caso = caso["ID_Caso"]
    inst1 = mod_casos.agregar_instrumento(id_caso, {
        "Tipo_Instrumento": "Pagare", "Numero_Instrumento": "296134",
        "Fecha_Suscripcion": parsear_fecha("10/05/2022"),
        "Fecha_Mora": parsear_fecha("01/02/2024"),
        "Banco_Acreedor": "Banco Santander", "Entidad_Acreedora": "Banco Santander",
        "Nombre_Ejecutivo_Suscriptor": "María Fernanda Soto Pérez",
        "Deudor_Principal": "Comercial Los Álamos Limitada",
        "RUT_Deudor_Principal": "76.111.222-3",
        "Monto_Original": "20000000", "Saldo_Insoluto": "15000000",
        "Moneda": "CLP", "Tasa_Interes": "1,2% mensual",
        "Interes_Penal": "máximo convencional",
        "Clausula_Aceleracion": True, "Liberacion_Protesto": True,
        "Firmas_Autorizadas_Notarialmente": True,
        "Domicilio_Competencia": "Santiago",
        "Fuente_Documento": "pagare_296134.pdf", "Fuente_Pagina": "1",
        "Fuente_Texto": "«…prometo pagar a la orden de Banco Santander…»",
        "Observaciones": "Instrumento de demostración.",
    })
    mod_casos.agregar_parte(id_caso, {
        "Nombre": "Comercial Los Álamos Limitada", "RUT": "76.111.222-3",
        "Tipo_Parte": "DEMANDADO", "Calidad_Juridica": "Deudor principal",
        "Responde_Por_Instrumento": "TODOS",
        "Monto_Responsabilidad": "15000000", "Moneda_Responsabilidad": "CLP",
        "Domicilio": "Av. Providencia 1234, oficina 501, Providencia, Santiago",
        "Fuente_Documento": "pagare_296134.pdf",
    })
    mod_casos.agregar_parte(id_caso, {
        "Nombre": "Rosa Andrea Sottorff Muñoz", "RUT": "9.999.999-9",
        "Tipo_Parte": "DEMANDADO", "Calidad_Juridica": "Avalista",
        "Responde_Por_Instrumento": inst1["ID_Instrumento"],
        "Monto_Responsabilidad": "15000000", "Moneda_Responsabilidad": "CLP",
        "Domicilio": "Los Aromos 45, Ñuñoa, Santiago",
        "Fuente_Documento": "pagare_296134.pdf",
    })


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    st.set_page_config(
        page_title="Personerías y Demandas Ejecutivas",
        page_icon="⚖️", layout="wide",
    )
    try:
        ensure_structure()
        mod_tpl.registrar_plantilla_base_si_falta()
    except ExcelAbiertoError as exc:
        st.error(f"📛 {exc}")
    except (OSError, IOError) as exc:
        st.error(f"No se pudo inicializar la estructura de datos: {exc}")

    st.title("⚖️ Sistema de Personerías y Demandas Ejecutivas")
    st.caption("Santander / GRC / otros — Juicios ejecutivos chilenos · Uso interno")

    with st.sidebar:
        st.markdown("### ℹ️ Estado")
        try:
            st.metric("Mandatos", len(read_excel_or_empty(
                mod_mand.MANDATOS_XLSX)))
            st.metric("Casos", len(read_excel_or_empty(CASES_XLSX)))
            st.metric("Demandas generadas", len(read_excel_or_empty(GENERATED_XLSX)))
        except ExcelAbiertoError:
            st.warning("Hay un Excel abierto en otro programa.")
        disponible, provider = mod_extr.ocr_disponible()
        st.markdown(f"**OCR/IA:** {'✅ ' + provider if disponible else '❌ no configurado'}")
        st.divider()
        if st.button("Cargar datos de ejemplo"):
            try:
                cargar_datos_ejemplo()
                st.success("Datos de ejemplo cargados.")
                st.rerun()
            except ExcelAbiertoError as exc:
                _mostrar_error_excel(exc)
        st.divider()
        st.warning(f"**Advertencia legal:** {ADVERTENCIA_LEGAL}")

    tabs = st.tabs([
        "🔎 Personerías", "📥 Carga Mandatos", "📚 Modelos",
        "🗂️ Nuevo Caso", "🧠 Extracción", "⚙️ Generador",
        "⚖️ Revisor", "🗃️ Historial", "🧾 Auditoría",
    ])
    with tabs[0]:
        tab_consulta()
    with tabs[1]:
        tab_carga_mandatos()
    with tabs[2]:
        tab_biblioteca()
    with tabs[3]:
        tab_nuevo_caso()
    with tabs[4]:
        tab_extraccion()
    with tabs[5]:
        tab_generador()
    with tabs[6]:
        tab_revisor()
    with tabs[7]:
        tab_historial()
    with tabs[8]:
        tab_auditoria()


if __name__ == "__main__":
    main()
