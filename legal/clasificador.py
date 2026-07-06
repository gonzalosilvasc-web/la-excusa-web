"""Módulo 6: identificación del tipo de demanda y sugerencia de modelo."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .textutil import es_verdadero


def clasificar_caso(
    instrumentos: pd.DataFrame, partes: pd.DataFrame
) -> dict[str, Any]:
    """Analiza los datos del caso y sugiere el tipo de demanda.

    Retorna: tipo_sugerido, razon, confianza, alternativas, bloqueo (si no hay
    títulos ejecutivos).
    """
    resultado: dict[str, Any] = {
        "tipo_sugerido": None,
        "razon": "",
        "confianza": "baja",
        "alternativas": [],
        "bloqueo": False,
    }

    if instrumentos.empty:
        resultado["bloqueo"] = True
        resultado["razon"] = (
            "El caso no tiene títulos ejecutivos registrados. Debe ingresar al "
            "menos un instrumento (pagaré, mutuo, etc.) antes de generar la demanda."
        )
        return resultado

    tipos = instrumentos["Tipo_Instrumento"].astype(str).str.strip().str.lower()
    monedas = instrumentos["Moneda"].astype(str).str.strip().str.upper()
    n_pagares = int((tipos == "pagare").sum())
    n_mutuos = int((tipos == "mutuo").sum())

    calidades = (
        partes["Calidad_Juridica"].astype(str).str.strip().str.lower()
        if not partes.empty else pd.Series(dtype=str)
    )
    hay_avalistas = calidades.isin(
        ("avalista", "fiador", "codeudor solidario")
    ).any()
    hay_tercero_poseedor = (calidades == "tercero poseedor").any()

    obs = " ".join(instrumentos["Observaciones"].fillna("").astype(str)).lower()
    hay_hipoteca = "hipotec" in obs or bool(
        instrumentos.get("Garantia_Hipotecaria", pd.Series(dtype=object)).apply(es_verdadero).any()
        if "Garantia_Hipotecaria" in instrumentos.columns else False
    )
    hay_prenda = "prenda" in obs

    razones: list[str] = []

    if hay_tercero_poseedor:
        tipo = "Desposeimiento de tercer poseedor"
        razones.append("Existe una parte registrada como tercero poseedor.")
        confianza = "media"
        alternativas = ["Demanda ejecutiva con hipoteca", "Cobro de mutuo hipotecario"]
    elif n_mutuos >= 1:
        tipo = "Cobro de mutuo hipotecario" if hay_hipoteca else "Cobro de mutuo con cartola"
        razones.append(
            f"El caso contiene {n_mutuos} mutuo(s)"
            + (" con garantía hipotecaria." if hay_hipoteca else ".")
        )
        confianza = "alta" if n_pagares == 0 else "media"
        alternativas = ["Demanda ejecutiva con hipoteca", "Otros"]
    elif n_pagares >= 1 and (hay_hipoteca or hay_prenda):
        tipo = "Demanda ejecutiva con garantías"
        razones.append("Hay pagaré(s) junto a garantías (hipoteca/prenda).")
        confianza = "media"
        alternativas = ["Demanda ejecutiva con hipoteca", "Demanda ejecutiva con prenda"]
    elif n_pagares > 1:
        tipo = "Cobro de múltiples pagarés"
        razones.append(f"El caso contiene {n_pagares} pagarés.")
        confianza = "alta"
        alternativas = ["Cobro de pagaré con avalistas/codeudores"]
    elif n_pagares == 1:
        moneda = monedas.iloc[0] if len(monedas) else "CLP"
        if hay_avalistas:
            tipo = "Cobro de pagaré con avalistas/codeudores"
            razones.append("Hay un pagaré con avalistas, fiadores o codeudores.")
            confianza = "alta"
            alternativas = [
                "Cobro de pagaré en dólares" if moneda == "USD" else "Cobro de pagaré en pesos"
            ]
        elif moneda == "USD":
            tipo = "Cobro de pagaré en dólares"
            razones.append("Hay un único pagaré expresado en dólares.")
            confianza = "alta"
            alternativas = ["Cobro de pagaré en pesos"]
        else:
            tipo = "Cobro de pagaré en pesos"
            razones.append(f"Hay un único pagaré en {moneda or 'CLP'}.")
            confianza = "alta"
            alternativas = ["Cobro de pagaré con avalistas/codeudores"]
    else:
        tipo = "Otros"
        razones.append("Los instrumentos registrados no calzan con un patrón conocido.")
        confianza = "baja"
        alternativas = ["Gestión preparatoria"]

    if hay_avalistas and tipo not in (
        "Cobro de pagaré con avalistas/codeudores",
        "Desposeimiento de tercer poseedor",
    ):
        razones.append("Además existen avalistas/fiadores/codeudores registrados.")

    resultado.update(
        tipo_sugerido=tipo,
        razon=" ".join(razones),
        confianza=confianza,
        alternativas=alternativas,
    )
    return resultado


def sugerir_template(
    templates: pd.DataFrame, tipo_demanda: str, entidad: str, moneda: str
) -> dict[str, Any]:
    """Sugiere el modelo Word más compatible desde templates.xlsx."""
    resultado: dict[str, Any] = {"sugerido": None, "alternativos": [], "razon": ""}
    if templates.empty:
        resultado["razon"] = "No hay modelos cargados en la biblioteca."
        return resultado

    activos = templates[
        templates["Activo"].astype(str).str.lower().isin(("true", "1", "si", "sí"))
    ].copy()
    if activos.empty:
        resultado["razon"] = "No hay modelos activos con placeholders utilizables."
        return resultado

    def puntaje(fila: pd.Series) -> int:
        p = 0
        if str(fila.get("Tipo_Demanda", "")).strip().lower() == tipo_demanda.strip().lower():
            p += 10
        if str(fila.get("Banco_Entidad", "")).strip().lower() in (
            entidad.strip().lower(), "genérico", "generico", ""
        ):
            p += 3
        if str(fila.get("Moneda", "")).strip().upper() in (moneda.strip().upper(), ""):
            p += 2
        return p

    activos["_p"] = activos.apply(puntaje, axis=1)
    activos = activos.sort_values("_p", ascending=False)
    mejor = activos.iloc[0]
    resultado["sugerido"] = mejor
    resultado["alternativos"] = activos.iloc[1:4].to_dict("records")
    if mejor["_p"] >= 10:
        resultado["razon"] = (
            f"El modelo «{mejor['Nombre_Template']}» coincide con el tipo de "
            f"demanda «{tipo_demanda}»."
        )
    else:
        resultado["razon"] = (
            f"No hay un modelo exacto para «{tipo_demanda}»; se sugiere el más "
            f"compatible: «{mejor['Nombre_Template']}». Revise si corresponde."
        )
    return resultado
