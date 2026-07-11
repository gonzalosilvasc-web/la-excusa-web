"""Módulo 8: control de concordancia cuerpo–petitorio y revisor jurídico.

Cada hallazgo indica nivel (CRITICO bloquea la descarga), ubicación,
explicación y cómo corregirlo.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

import pandas as pd

from .casos import instrumentos_que_responde
from .config import NO_DETECTADO, PATRONES_PROHIBIDOS
from .textutil import (
    es_verdadero,
    formatear_fecha,
    normalizar_nombre,
    parsear_fecha,
    parsear_monto,
)

CRITICO = "CRITICO"
ADVERTENCIA = "ADVERTENCIA"

# Campos del contexto que jamás pueden quedar vacíos o NO_DETECTADO
CAMPOS_CRITICOS = [
    "TRIBUNAL", "DEMANDANTE", "TEXTO_PERSONERIA", "DEMANDADOS",
    "TITULOS_EJECUTIVOS", "MONTO_CAPITAL", "RELATO_DE_LOS_HECHOS",
    "PETITORIO", "DOCUMENTOS_PRIMER_OTROSI", "BIENES_EMBARGO",
    "REPRESENTANTE_DEMANDANTE",
]

_SUFIJOS_SOCIEDAD = ("spa", "s a", "sa", "ltda", "limitada", "eirl", "e i r l")


@dataclass
class Hallazgo:
    nivel: str
    regla: str
    ubicacion: str
    explicacion: str
    correccion: str

    def __str__(self) -> str:
        etiqueta = "Error crítico" if self.nivel == CRITICO else "Advertencia"
        return (
            f"{etiqueta} [{self.regla}] — {self.ubicacion}: {self.explicacion} "
            f"Cómo corregirlo: {self.correccion}"
        )


@dataclass
class ResultadoRevision:
    hallazgos: list[Hallazgo] = field(default_factory=list)

    @property
    def criticos(self) -> list[Hallazgo]:
        return [h for h in self.hallazgos if h.nivel == CRITICO]

    @property
    def advertencias(self) -> list[Hallazgo]:
        return [h for h in self.hallazgos if h.nivel == ADVERTENCIA]

    @property
    def bloquea_descarga(self) -> bool:
        return bool(self.criticos)


def _contiene_nombre(texto: str, nombre: str) -> bool:
    """True si el nombre (normalizado) aparece dentro del texto normalizado."""
    n_texto = normalizar_nombre(texto)
    n_nombre = normalizar_nombre(nombre)
    return bool(n_nombre) and n_nombre in n_texto


def _es_sociedad(nombre: str) -> bool:
    n = normalizar_nombre(nombre)
    return any(n.endswith(" " + s) or n.endswith(s) for s in _SUFIJOS_SOCIEDAD if s)


def revisar_demanda(
    contexto: dict[str, str],
    instrumentos: pd.DataFrame,
    partes: pd.DataFrame,
    mandato: Optional[dict[str, Any] | pd.Series],
    texto_final_docx: str = "",
) -> ResultadoRevision:
    """Ejecuta todas las reglas de concordancia. CRITICO bloquea la descarga."""
    r = ResultadoRevision()
    petitorio = str(contexto.get("PETITORIO", ""))
    cuerpo = "\n".join(
        str(contexto.get(k, ""))
        for k in ("DEMANDADOS", "TITULOS_EJECUTIVOS", "RELATO_DE_LOS_HECHOS")
    )
    otrosi_docs = str(contexto.get("DOCUMENTOS_PRIMER_OTROSI", ""))
    texto_total = texto_final_docx or "\n".join(str(v) for v in contexto.values())

    # --- Regla 0: debe existir al menos un título y un demandado ---
    if instrumentos.empty:
        r.hallazgos.append(Hallazgo(
            CRITICO, "titulos", "Instrumentos del caso",
            "El caso no tiene títulos ejecutivos registrados.",
            "Registre al menos un pagaré, mutuo u otro título en el módulo de casos.",
        ))
    if partes.empty:
        r.hallazgos.append(Hallazgo(
            CRITICO, "demandados", "Partes del caso",
            "El caso no tiene demandados/obligados registrados.",
            "Registre al menos el deudor principal en el módulo de casos.",
        ))

    # --- Reglas 1 y 2: demandados en cuerpo vs petitorio (ambas direcciones) ---
    for _, parte in partes.iterrows():
        nombre = str(parte.get("Nombre") or "").strip()
        calidad = str(parte.get("Calidad_Juridica") or "obligado")
        if not nombre:
            r.hallazgos.append(Hallazgo(
                CRITICO, "cuerpo-petitorio", "Partes del caso",
                "Hay una parte registrada sin nombre.",
                "Complete el nombre de la parte o elimínela.",
            ))
            continue
        en_cuerpo = _contiene_nombre(cuerpo, nombre)
        en_petitorio = _contiene_nombre(petitorio, nombre)
        if en_cuerpo and not en_petitorio:
            r.hallazgos.append(Hallazgo(
                CRITICO, "cuerpo-petitorio", "Petitorio",
                f"{nombre} aparece como {calidad.lower()} en el cuerpo de la "
                "demanda, pero no aparece demandado/a en el petitorio.",
                f"Agregue a {nombre} al petitorio o elimínelo/a del cuerpo si no corresponde.",
            ))
        elif en_petitorio and not en_cuerpo:
            r.hallazgos.append(Hallazgo(
                CRITICO, "cuerpo-petitorio", "Cuerpo de la demanda",
                f"{nombre} aparece demandado/a en el petitorio, pero no tiene "
                "respaldo en el cuerpo de la demanda.",
                f"Individualice a {nombre} en el cuerpo (y en los títulos) o "
                "elimínelo/a del petitorio.",
            ))
        elif not en_cuerpo and not en_petitorio:
            r.hallazgos.append(Hallazgo(
                CRITICO, "cuerpo-petitorio", "Cuerpo y petitorio",
                f"{nombre} está registrado/a como {calidad.lower()} del caso, "
                "pero no aparece ni en el cuerpo ni en el petitorio.",
                f"Incluya a {nombre} en la demanda o elimine la parte del caso.",
            ))

    # --- Regla 3 y 7: suma de montos cuerpo vs petitorio/total ---
    monedas = (
        instrumentos["Moneda"].fillna("CLP").astype(str).str.upper().unique().tolist()
        if not instrumentos.empty else []
    )
    if not instrumentos.empty and len(monedas) == 1:
        saldos = [parsear_monto(v) for v in instrumentos["Saldo_Insoluto"]]
        if all(s is not None for s in saldos):
            suma = sum(s for s in saldos if s is not None)
            total_ctx = parsear_monto(contexto.get("MONTO_CAPITAL", ""))
            if total_ctx is not None and abs(total_ctx - suma) > 1:
                r.hallazgos.append(Hallazgo(
                    CRITICO, "montos", "Monto capital",
                    f"La suma de los saldos insolutos de los títulos "
                    f"({suma:,.0f}) no coincide con el monto capital indicado "
                    f"en la demanda ({total_ctx:,.0f}).",
                    "Corrija los saldos de los instrumentos o el monto total de la demanda.",
                ))
        else:
            r.hallazgos.append(Hallazgo(
                CRITICO, "montos", "Instrumentos del caso",
                "Hay títulos sin saldo insoluto registrado; no es posible "
                "verificar la suma total demandada.",
                "Complete el saldo insoluto de todos los instrumentos.",
            ))

    # --- Reglas 4, 5 y 17: responsabilidad limitada por instrumento ---
    ids_todos = (
        set(instrumentos["ID_Instrumento"].astype(str)) if not instrumentos.empty else set()
    )
    for _, parte in partes.iterrows():
        nombre = str(parte.get("Nombre") or "").strip()
        if not nombre:
            continue
        responde = instrumentos_que_responde(parte, instrumentos)
        limitado = bool(ids_todos) and set(responde) != ids_todos

        # Monto pedido vs responsabilidad según instrumentos que garantiza
        monto_parte = parsear_monto(parte.get("Monto_Responsabilidad"))
        if monto_parte is not None and not instrumentos.empty and len(monedas) == 1:
            saldos_resp = [
                parsear_monto(
                    instrumentos.loc[
                        instrumentos["ID_Instrumento"] == i, "Saldo_Insoluto"
                    ].iloc[0]
                )
                for i in responde
                if (instrumentos["ID_Instrumento"] == i).any()
            ]
            if all(s is not None for s in saldos_resp) and saldos_resp:
                tope = sum(s for s in saldos_resp if s is not None)
                if monto_parte - tope > 1:
                    r.hallazgos.append(Hallazgo(
                        CRITICO, "responsabilidad", "Petitorio",
                        f"A {nombre} se le pide {monto_parte:,.0f}, monto "
                        f"superior al que corresponde según los títulos que "
                        f"garantiza ({tope:,.0f}).",
                        "Ajuste el monto de responsabilidad de la parte o su "
                        "lista de instrumentos garantizados.",
                    ))

        if limitado:
            numeros = []
            for id_inst in responde:
                fila = instrumentos[instrumentos["ID_Instrumento"] == id_inst]
                if not fila.empty:
                    numeros.append(str(fila.iloc[0].get("Numero_Instrumento", "")).strip())
            faltan = [n for n in numeros if n and n not in petitorio]
            if faltan or not any(
                pal in normalizar_nombre(petitorio) for pal in ("limitada", "exclusivamente")
            ):
                r.hallazgos.append(Hallazgo(
                    CRITICO, "responsabilidad-limitada", "Petitorio",
                    f"{nombre} responde solo por ciertos títulos "
                    f"(N° {', '.join(n for n in numeros if n) or NO_DETECTADO}), pero el "
                    "petitorio no limita expresamente su responsabilidad a esos títulos.",
                    "Indique en el petitorio los números de los títulos por los "
                    "que responde esta parte, con la expresión 'limitada exclusivamente'.",
                ))

    # --- Regla 6: sociedad suscriptora vs persona natural demandada ---
    deudores_titulo = (
        [str(v or "") for v in instrumentos["Deudor_Principal"]]
        if not instrumentos.empty else []
    )
    for _, parte in partes.iterrows():
        calidad = normalizar_nombre(str(parte.get("Calidad_Juridica") or ""))
        nombre = str(parte.get("Nombre") or "").strip()
        if calidad == "deudor principal" and nombre:
            respaldo = any(_contiene_nombre(d, nombre) or _contiene_nombre(nombre, d)
                           for d in deudores_titulo if d.strip())
            if deudores_titulo and not respaldo:
                sociedad = next((d for d in deudores_titulo if _es_sociedad(d)), "")
                extra = (
                    f" El título aparece suscrito por «{sociedad}»; un representante "
                    "solo puede demandarse personalmente si comparece como avalista, "
                    "fiador o codeudor." if sociedad else ""
                )
                r.hallazgos.append(Hallazgo(
                    CRITICO, "calidad-juridica", "Demandados",
                    f"{nombre} figura como deudor principal, pero no coincide con "
                    f"el suscriptor de ningún título del caso.{extra}",
                    "Verifique la calidad jurídica de esta parte o corrija el "
                    "deudor principal del instrumento.",
                ))

    # --- Regla 8: equivalencia en pesos para USD/UF ---
    moneda_ctx = str(contexto.get("MONEDA", "CLP")).upper()
    if moneda_ctx in ("USD", "UF"):
        equiv = str(contexto.get("EQUIVALENCIA_PESOS", "")).strip()
        if not equiv or equiv == NO_DETECTADO:
            r.hallazgos.append(Hallazgo(
                CRITICO, "moneda", "Equivalencia en pesos",
                f"La demanda está expresada en {moneda_ctx} pero no indica su "
                "equivalencia en pesos.",
                "Ingrese la equivalencia en pesos (con el certificado de "
                "dólar/UF correspondiente) en el generador.",
            ))

    # --- Regla 9: intereses y costas pedidos en el petitorio ---
    pet_norm = normalizar_nombre(petitorio)
    if "interes" not in pet_norm:
        r.hallazgos.append(Hallazgo(
            CRITICO, "petitorio", "Petitorio",
            "El petitorio no solicita los intereses pactados/penales.",
            "Agregue la petición de intereses al petitorio.",
        ))
    if "costas" not in pet_norm:
        r.hallazgos.append(Hallazgo(
            CRITICO, "petitorio", "Petitorio",
            "El petitorio no solicita la condena en costas.",
            "Agregue la petición de costas al petitorio.",
        ))

    # --- Regla 10: documentos del primer otrosí vs títulos del cuerpo ---
    for _, inst in instrumentos.iterrows():
        numero = str(inst.get("Numero_Instrumento") or "").strip()
        if numero and numero != NO_DETECTADO and numero not in otrosi_docs:
            r.hallazgos.append(Hallazgo(
                CRITICO, "otrosi-documentos", "Primer otrosí",
                f"El título N° {numero} descrito en el cuerpo no aparece "
                "acompañado en el primer otrosí.",
                "Agregue el documento al primer otrosí o elimine el título del cuerpo.",
            ))

    # --- Regla 11: bienes para embargo ---
    bienes = str(contexto.get("BIENES_EMBARGO", "")).strip()
    if bienes and bienes != NO_DETECTADO:
        r.hallazgos.append(Hallazgo(
            ADVERTENCIA, "embargo", "Segundo otrosí",
            "Verifique que los bienes señalados para embargo pertenezcan a "
            "demandados o garantes, según corresponda.",
            "Coteje los bienes con los antecedentes de dominio del caso.",
        ))

    # --- Reglas 12 y 13: placeholders sin completar y comentarios internos ---
    for patron, descripcion in PATRONES_PROHIBIDOS:
        for m in re.finditer(patron, texto_total, flags=re.IGNORECASE):
            fragmento = m.group(0)
            r.hallazgos.append(Hallazgo(
                CRITICO, "texto-prohibido", "Documento generado",
                f"{descripcion}: se encontró «{fragmento}» en el texto de la demanda.",
                "Complete o elimine esa marca antes de generar la versión final.",
            ))
            break  # un hallazgo por patrón basta para bloquear; evita ruido

    # --- Regla 13-bis: afirmación de prescripción sin validación expresa ---
    # "No prescrita" es una calificación jurídica que debe evaluar el abogado
    # caso a caso; el sistema jamás la genera solo y, si aparece escrita a
    # mano, exige la validación manual expresa del generador.
    afirmacion_prescripcion = re.search(
        r"no\s+(?:se\s+encuentra\s+|esta\s+|está\s+|ha\s+)?prescrit[ao]",
        texto_total, flags=re.IGNORECASE,
    )
    prescripcion_validada = str(
        contexto.get("PRESCRIPCION_VALIDADA", "")
    ).strip().upper() == "SI"
    if afirmacion_prescripcion and not prescripcion_validada:
        r.hallazgos.append(Hallazgo(
            CRITICO, "prescripcion", "Cuerpo de la demanda",
            "La demanda afirma que la obligación no está prescrita, pero esa "
            "calificación jurídica no fue validada expresamente por el abogado.",
            "Evalúe personalmente la prescripción y marque la casilla de "
            "validación de prescripción en el generador, o elimine la "
            "afirmación del texto.",
        ))

    # --- Regla 14: campos críticos vacíos ---
    for campo in CAMPOS_CRITICOS:
        valor = str(contexto.get(campo, "")).strip()
        if not valor or valor == NO_DETECTADO:
            r.hallazgos.append(Hallazgo(
                CRITICO, "campo-critico", campo,
                f"El campo crítico {campo} está vacío o quedó como {NO_DETECTADO}.",
                f"Complete {campo} manualmente en el generador (la app no "
                "inventa datos jurídicos).",
            ))

    # --- Regla 15: personería vs fecha de suscripción del título ---
    if mandato is not None and not instrumentos.empty:
        get = mandato.get if hasattr(mandato, "get") else lambda k, d=None: d
        f_otorg = parsear_fecha(get("Fecha_Otorgamiento"))
        f_revoc = parsear_fecha(get("Fecha_Revocacion"))
        fechas = [parsear_fecha(v) for v in instrumentos["Fecha_Suscripcion"]]
        fechas_validas = [f for f in fechas if f is not None]
        if not fechas_validas or any(f is None for f in fechas):
            r.hallazgos.append(Hallazgo(
                CRITICO, "personeria-fecha", "Instrumentos",
                "Hay títulos sin fecha de suscripción; no es posible validar la "
                "vigencia de la personería a esa fecha.",
                "Complete la fecha de suscripción de todos los instrumentos.",
            ))
        else:
            f_min, f_max = min(fechas_validas), max(fechas_validas)
            if f_otorg is None:
                r.hallazgos.append(Hallazgo(
                    CRITICO, "personeria-fecha", "Personería",
                    "El mandato seleccionado no tiene fecha de otorgamiento.",
                    "Complete la fecha de otorgamiento del mandato.",
                ))
            elif f_otorg > f_min:
                r.hallazgos.append(Hallazgo(
                    CRITICO, "personeria-fecha", "Personería",
                    f"La personería fue otorgada el {formatear_fecha(f_otorg)}, "
                    f"con posterioridad a la suscripción del título más antiguo "
                    f"({formatear_fecha(f_min)}).",
                    "Use un mandato vigente a la fecha de suscripción del título.",
                ))
            if f_revoc is not None:
                if f_revoc < f_max:
                    r.hallazgos.append(Hallazgo(
                        CRITICO, "personeria-fecha", "Personería",
                        f"El mandato fue revocado el {formatear_fecha(f_revoc)}, "
                        f"antes de la suscripción de al menos un título "
                        f"({formatear_fecha(f_max)}).",
                        "Seleccione una personería vigente a la fecha de cada título.",
                    ))
                elif any(f == f_revoc for f in fechas_validas):
                    r.hallazgos.append(Hallazgo(
                        ADVERTENCIA, "personeria-fecha", "Personería",
                        "El mandato fue revocado el mismo día de la suscripción "
                        "de un título. Verifique horas de los instrumentos.",
                        "Coteje las horas de otorgamiento y suscripción.",
                    ))
    elif mandato is None:
        r.hallazgos.append(Hallazgo(
            CRITICO, "personeria", "Personería",
            "No se seleccionó una personería para la demanda.",
            "Busque y seleccione un mandato vigente en el generador.",
        ))

    # --- Regla 16: afirmaciones críticas con fuente documental ---
    if not instrumentos.empty:
        sin_fuente = instrumentos[
            instrumentos["Fuente_Documento"].fillna("").astype(str).str.strip() == ""
        ]
        if not sin_fuente.empty:
            r.hallazgos.append(Hallazgo(
                ADVERTENCIA, "fuentes", "Instrumentos",
                f"{len(sin_fuente)} instrumento(s) no tienen fuente documental "
                "registrada (documento/página/texto).",
                "Registre la fuente de cada dato o valide manualmente contra el "
                "título original.",
            ))

    return r
