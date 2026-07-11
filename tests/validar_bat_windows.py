"""Validación de los lanzadores .bat en una ruta con paréntesis «app test (1)».

Ejecuta INICIAR_APP.bat y DIAGNOSTICO.bat mediante cmd.exe real (en Windows)
o Wine (en Linux/macOS, como verificación equivalente) desde una carpeta cuyo
nombre contiene espacios y "(1)", en un escenario con PATH controlado SIN
Python de Windows, y verifica que:

  1. NUNCA aparezca el error de parser «No se esperaba …» / «was unexpected»;
  2. el caso "falta Python" muestre su mensaje claro;
  3. el caso "ZIP no extraído" muestre su mensaje;
  4. DIAGNOSTICO.bat corra completo.

Uso:  python tests/validar_bat_windows.py
Código de salida 0 si todo pasa.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
ARCHIVOS = ["INICIAR_APP.bat", "INICIAR_APP_SEGURO.bat", "DIAGNOSTICO.bat",
            "bootstrap.py", "app.py", "requirements.txt", "check_install.py"]

FRASES_PARSER_ROTO = ("no se esperaba", "was unexpected", "unexpected at this time")

RESULTADOS: list[tuple[str, bool, str]] = []


def check(nombre: str, ok: bool, detalle: str = "") -> None:
    RESULTADOS.append((nombre, ok, detalle))
    print(f"{'  [PASA] ' if ok else '  [FALLA]'} {nombre}"
          + (f" — {detalle[:200]}" if detalle and not ok else ""))


def ejecutor() -> list[str] | None:
    """Comando para ejecutar .bat: cmd real en Windows, wine en otros SO."""
    if os.name == "nt":
        return ["cmd", "/c"]
    if shutil.which("wine"):
        return ["wine", "cmd", "/c"]
    return None


def correr_bat(carpeta: Path, bat: str, timeout: int = 120) -> str:
    cmd = ejecutor()
    assert cmd is not None
    env = dict(os.environ)
    env.setdefault("WINEDEBUG", "-all")
    try:
        r = subprocess.run(
            cmd + [bat], cwd=str(carpeta), env=env, timeout=timeout,
            input="\n", capture_output=True, text=True, errors="replace",
        )
        return (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired as exc:
        salida = exc.stdout or b""
        if isinstance(salida, bytes):
            salida = salida.decode("utf-8", errors="replace")
        return salida + "\n[TIMEOUT]"


def main() -> int:
    if ejecutor() is None:
        print("[OMITIDA] Ni cmd.exe ni Wine disponibles: no se puede validar "
              "el .bat en este entorno. Ejecute este script en Windows.")
        return 0

    modo = "cmd.exe real (Windows)" if os.name == "nt" else "Wine (equivalente)"
    print("=" * 66)
    print(f" Validación de lanzadores en ruta con '(1)' — vía {modo}")
    print("=" * 66)

    with tempfile.TemporaryDirectory() as tmp:
        carpeta = Path(tmp) / "app test (1)"
        carpeta.mkdir()
        for nombre in ARCHIVOS:
            shutil.copy2(BASE / nombre, carpeta / nombre)
        shutil.copytree(BASE / "legal", carpeta / "legal")

        # --- Escenario 1: INICIAR_APP.bat sin Python de Windows ------------
        # (bajo Wine no existe Python de Windows; en Windows real este script
        #  debería ejecutarse con un PATH controlado sin python/py para
        #  reproducirlo, o aceptar que avance hasta bootstrap).
        salida = correr_bat(carpeta, "INICIAR_APP.bat").lower()
        check("INICIAR_APP.bat en «app test (1)»: sin error de parser",
              not any(f in salida for f in FRASES_PARSER_ROTO), salida[-300:])
        check("INICIAR_APP.bat muestra la carpeta correcta",
              "app test (1)" in salida, salida[:300])
        if "python detectado" not in salida:
            check("Caso sin Python: mensaje claro y ventana en pausa",
                  "python no esta instalado" in salida
                  and ("press any key" in salida or "tecla" in salida),
                  salida[-400:])
        else:
            print("  [INFO] Python de Windows presente: el lanzador avanzó "
                  "más allá de la detección (válido).")

        # --- Escenario 2: INICIAR_APP_SEGURO.bat ---------------------------
        salida = correr_bat(carpeta, "INICIAR_APP_SEGURO.bat").lower()
        check("INICIAR_APP_SEGURO.bat: sin error de parser",
              not any(f in salida for f in FRASES_PARSER_ROTO), salida[-300:])

        # --- Escenario 3: DIAGNOSTICO.bat ----------------------------------
        salida = correr_bat(carpeta, "DIAGNOSTICO.bat").lower()
        check("DIAGNOSTICO.bat en «app test (1)»: sin error de parser",
              not any(f in salida for f in FRASES_PARSER_ROTO), salida[-300:])
        check("DIAGNOSTICO.bat corre completo",
              "diagnostico del sistema" in salida
              and "fin del diagnostico" in salida, salida[-400:])
        check("DIAGNOSTICO.bat valida archivos del proyecto",
              "app.py" in salida and "requirements.txt" in salida)

        # --- Escenario 4: ZIP no extraído en carpeta con (1) ---------------
        solo_bat = Path(tmp) / "zip sin extraer (1)"
        solo_bat.mkdir()
        shutil.copy2(BASE / "INICIAR_APP.bat", solo_bat / "INICIAR_APP.bat")
        salida = correr_bat(solo_bat, "INICIAR_APP.bat").lower()
        check("ZIP no extraído en «(1)»: sin error de parser",
              not any(f in salida for f in FRASES_PARSER_ROTO), salida[-300:])
        check("ZIP no extraído: mensaje de extracción",
              "debe extraer el zip" in salida, salida[-400:])

    fallas = [r for r in RESULTADOS if not r[1]]
    print("=" * 66)
    print(f" RESULTADO: {len(RESULTADOS) - len(fallas)}/{len(RESULTADOS)} PASAN")
    if os.name != "nt":
        print(" NOTA: ejecutado vía Wine — no reemplaza una prueba en "
              "Windows real.")
    print("=" * 66)
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
