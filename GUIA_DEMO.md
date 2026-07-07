# 🎯 Guía de demostración — presentación a gerencia

Guion de ~10 minutos para presentar el sistema, con todo pre-cargado para
que no haya que tipear casi nada frente a la audiencia.

## Antes de la reunión (checklist, 10 minutos antes)

1. ✅ Abra la app (doble clic en `INICIAR_APP.bat`) **antes** de la reunión y
   déjela corriendo. Minimice la ventana negra.
2. ✅ En la barra lateral, presione **"Cargar datos de ejemplo"** (una vez).
   Esto crea 3 personerías ficticias y un caso de demostración completo
   ("Comercial Los Álamos Limitada", operación DEMO-2024-001).
3. ✅ Verifique que la barra lateral muestre: Mandatos 3 · Casos 1.
4. ✅ Cierre cualquier Excel abierto de la carpeta `database/`.
5. ✅ Tenga Word instalado para abrir la demanda generada al final.
6. ✅ Pantalla: zoom del navegador al 100–110%, cierre pestañas ajenas.

> Todos los datos de ejemplo son **ficticios**. Dígalo expresamente en la
> presentación para evitar confusiones.

## Guion sugerido (6 pasos)

### 1. El problema (30 segundos, sin la app)
"Hoy, para cada demanda ejecutiva, el equipo busca la personería vigente a
mano, copia textos de demandas anteriores y revisa a ojo que el petitorio
coincida con los títulos. Cada error de esos se traduce en una demanda
observada o rechazada."

### 2. Personerías (2 minutos) — pestaña 🔎 Personerías
- Fecha de suscripción: deje la de hoy. Ejecutivo: escriba **"maria soto"**
  (así, sin tildes ni apellido completo — muestre que igual lo encuentra).
- Entidad: Banco Santander → **Buscar personería**.
- Muestre: encontró el mandato vigente, y el **texto legal listo para pegar
  en la demanda** (el párrafo de personería con notaría y repertorio).
- Frase clave: "El sistema valida la vigencia del mandato **a la fecha del
  pagaré**, no a la de hoy — incluso advierte si fue revocado el mismo día."

### 3. El caso de demostración (1 minuto) — pestaña 🧠 Extracción
- Seleccione el caso "Comercial Los Álamos Limitada".
- Muestre la tabla: un pagaré de $15 millones de saldo, un deudor principal
  y una avalista, **cada dato con su fuente documental** (documento y cita).
- Frase clave: "El sistema nunca inventa un dato: lo que no consta en los
  documentos queda marcado como NO_DETECTADO y bloquea la generación."

### 4. Generar la demanda (3 minutos) — pestaña ⚙️ Generador
- Seleccione el caso. Muestre que el sistema **clasificó solo** el tipo de
  demanda ("Cobro de pagaré con avalistas/codeudores") y sugirió el modelo.
- En "Personería del ejecutante" ya viene el nombre de la ejecutiva
  (lo tomó del pagaré) → **Buscar personería vigente** → la encuentra.
- Complete solo 2 campos: Tribunal ("S.J.L. en lo Civil de Santiago") y
  Bienes para embargo ("Bienes muebles del domicilio de la demandada").
- **Componer demanda** → muestre la vista previa editable: comparecencia,
  títulos, relato, **petitorio diferenciado** (deudora por el total,
  avalista limitada a su pagaré).

### 5. El diferenciador: el revisor jurídico (2 minutos)
- Presione **"Revisar concordancia jurídica"** → aprueba.
- Ahora el momento clave de la demo: **borre a la avalista del petitorio**
  (edite el cuadro PETITORIO y elimine su línea) → presione revisar de nuevo.
- El sistema **bloquea la descarga** y explica: "Rosa Andrea Sottorff Muñoz
  aparece como avalista en el cuerpo… pero no aparece demandada en el
  petitorio", con la instrucción de cómo corregirlo.
- Frase clave: "Este es el control que evita demandas inconsistentes: **17
  reglas de concordancia** entre cuerpo y petitorio, y si hay un error
  crítico, el Word simplemente no se puede descargar."
- Vuelva a componer (botón Componer) para restaurar el texto, revise de
  nuevo → aprueba.

### 6. Cierre (1 minuto)
- Marque el **checklist legal de 8 puntos** → **Generar demanda final** →
  **Descargar** → abra el Word: formato limpio, personería citada, petitorio
  correcto.
- Muestre la pestaña 🧾 **Auditoría**: cada acción quedó registrada,
  incluido el bloqueo que provocamos.
- Cierre: "Todo corre **local**: ningún documento del banco sale de este
  computador. La IA de extracción es opcional y exige autorización expresa.
  Y la regla número uno del diseño: **el sistema asiste al abogado, nunca lo
  reemplaza** — por eso el checklist final es obligatorio."

## Preguntas probables y respuestas

- **"¿Dónde quedan los datos?"** → Solo en este computador, carpeta
  `database/`. Nada se sube a internet. Respaldo automático antes de cada
  escritura.
- **"¿Y si el dato del pagaré está mal?"** → Todo campo es editable y exige
  validación humana con checkbox; además cada dato registra su fuente
  (documento, página, cita textual).
- **"¿Sirve para nuestros modelos Word?"** → Sí: la pestaña Modelos indexa
  los formatos del estudio con placeholders; si un modelo no los tiene, el
  sistema lo detecta y entrega una copia guía.
- **"¿Puede inventar algo la IA?"** → La extracción con IA es opcional,
  exige autorización expresa por la confidencialidad, todo pasa por
  formulario editable, y lo que no consta queda NO_DETECTADO y **bloquea**
  la generación. El texto final siempre lo aprueba un abogado.

## Si algo falla durante la demo (plan B)

- La app no responde → cierre la ventana negra y doble clic en
  `INICIAR_APP.bat` de nuevo (tarda segundos, ya está instalada).
- Mensaje de "Excel abierto" → cierre el Excel y repita la acción.
- Sin tiempo para generar en vivo → la pestaña 🗃️ **Historial** conserva
  las demandas generadas en los ensayos: descargue una y muéstrela.

**Ensaye el flujo completo al menos una vez antes de la reunión.**
