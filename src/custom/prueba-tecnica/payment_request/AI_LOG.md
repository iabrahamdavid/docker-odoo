# AI_LOG — payment_request

## Herramientas
- Antigravity AI Assistant (Gemini 3.8 Flash / Claude Opus 5.5) en entorno Linux (Ubuntu).
- Git CLI / Python 3.12 / Odoo CLI runner.

## Prompts clave (3 a 5)
1. **Análisis de requerimientos y diseño de arquitectura base (Tramo A):**
   - *Prompt:* "Analiza el correo de Carolina Méndez para Distribuidora Andina C.A. y diseña el modelo payment.request con herencia mail.thread, estados, secuencias y permisos granulares cumpliendo los estándares de Odoo 18".
   - *Resultado:* Se definió la estructura del modelo, la secuencia anual `SP/%(year)s/0001` y la matriz de estados (`draft`, `submitted`, `approved`, `paid`, `rejected`).
2. **Blindaje de inmutabilidad en capa ORM (`write` y `unlink`):**
   - *Prompt:* "Diseña la protección contra modificaciones en payment.request para asegurar que una solicitud enviada no pueda ser modificada en campos críticos, permitiendo únicamente cambios de estado o chatter".
   - *Resultado:* Se implementó la sobreescritura de `write()` con lista de campos restringidos y de `unlink()` permitiendo borrado solo en `draft` y `rejected`.
3. **Aislamiento de seguridad y control de acceso estricto:**
   - *Prompt:* "Crea los grupos Solicitante, Aprobador y Tesorería en payment_request_security.xml con ir.rule donde el solicitante solo pueda consultar sus propias solicitudes y el aprobador todas, asegurando que el solicitante no pueda aprobar ni por interfaz ni llamando a action_approve()".
   - *Resultado:* Se generaron las reglas de registro y la validación en código Python con `AccessError`.
4. **Diseño de vistas modernas Odoo 18:**
   - *Prompt:* "Construye las vistas form, list y search para payment_request utilizando la sintaxis de Odoo 18 (etiqueta <list>, componente <chatter/> y modificadores nativos invisible y readonly sin attrs)".
   - *Resultado:* Vistas limpias y conformes a las directrices de `CONTEXT.md`.
5. **Auditoría de seguridad y pruebas de penetración:**
   - *Prompt:* "Verifica si un solicitante puede auto-aprobarse mediante mutación directa de datos sin presionar el botón de aprobar".
   - *Resultado:* Se detectó y bloqueó la vulnerabilidad de auto-aprobación en `create()` y `write()`.

## Lo que la IA hizo mal
- **Vulnerabilidad de auto-aprobación en ORM:** En la primera versión de `models/payment_request.py`, la IA protegió el método `action_approve()` con chequeo de grupo, pero en `write()` únicamente incluyó campos de datos (`partner_id`, `amount`, `concept`, etc.) en la lista de campos restringidos. Como `state` no estaba bloqueado, un solicitante no podía usar el botón, pero sí podía enviar una mutación directa `write({'state': 'approved'})` o crear registros con `create({'state': 'approved'})`.
- **Efecto colateral en la primera corrección:** Al intentar bloquear `name` y `state` de forma ingenua en `write()`, se impidió que el propio solicitante pudiera enviar su solicitud (`action_submit()`), ya que el envío genera la secuencia y cambia el estado a `submitted`.
- *Cómo se detectó y corrigió:* Se descubrió mediante pruebas de caja negra en `odoo shell` simulando un solicitante. La corrección definitiva exigió condicionar el cambio de `state` y `name` a usuarios aprobadores o a métodos con contexto autorizado (`allow_state_transition=True`, `system_sequence=True`), respaldándolo con pruebas unitarias específicas en `test_04_applicant_cannot_approve_or_reject`.

## Lo que escribiste tú sin IA
- Análisis del correo de Carolina Méndez identificando las 5 preguntas clave de consultoría (umbral entre pago normal y grande, modelado del jefe de área en RRHH, política de rechazo vs nueva solicitud, y fijación de tasas de cambio USD/VES).
- Criterio de auditoría técnica exigiendo verificar empíricamente cada módulo con el CLI oficial de Docker (`./odoo test`) antes de considerar cualquier tramo como completado.

---

# Tramo B — niveles de aprobación, wizards y PDF

## Herramientas
- Claude Code (Claude Opus 5.5) en VS Code sobre Linux, con acceso al repositorio y a los contenedores Docker de la instancia `prueba-tecnica`.

## Prompts clave (3 a 5)
1. **Plan antes de programar:**
   - *Prompt:* "Genera el plan con todo lo que hemos hablado, trabaja como un desarrollador senior con experiencia en Binaural; revisa los commits de binaural-dev/docker-odoo para ver cómo se manejan".
   - *Resultado:* Un plan con el diseño de cada pieza, las pruebas ligadas a cada criterio, las decisiones pendientes y los commits. De los commits de Binaural se tomó el cuerpo del mensaje (qué cambia, por qué y cómo se verificó).
2. **Ceñirse al enunciado:**
   - *Prompt:* "Realiza los cambios en base exclusivamente a los requerimientos de la prueba técnica, verifica minuciosamente y sin agregar cosas de más; cuida los commits".
   - *Resultado:* Se recortó el diseño (sin nombre ni compañía en los niveles, sin botón inteligente ni fecha en el wizard de pago) y se añadió una comprobación por commit: cada prueba nueva debe fallar al quitar la regla que cubre.
3. **Revisión de lo implementado:**
   - *Prompt:* "¿Crees que se cumple justo la prueba técnica?".
   - *Resultado:* Tabla de criterios frente a código; se identificó el único extra (cerrar la actividad al aprobar o rechazar) y se decidió mantenerlo porque, sin él, el aprobador conserva tareas ya resueltas.

## Lo que la IA hizo mal
- **Usuarios de prueba sin email:** al crear la actividad del aprobador, Odoo le notifica por correo con el solicitante como remitente; sin email falla con *"Unable to send message, please configure the sender's email address"*.
  - *Cómo se detectó:* 7 pruebas del Tramo A fallaron al ejecutar la suite; se dio email a los usuarios de prueba y se anotó como supuesto en el README.
- **Pruebas de pago que no se ejecutaban:** el `setUpClass` de la clase de pago creaba los niveles con el usuario contable de `AccountTestInvoicingCommon`, que no tiene permiso; las 4 pruebas no corrieron y el resumen del CLI mostraba "Errores: 0".
  - *Cómo se detectó:* el número de pruebas no subió (16 en vez de 20) y el log mostraba `ERROR: setUpClass`. Los niveles se crean ahora con el usuario de Tesorería.
- **Primer diseño con piezas de más:** el plan inicial incluía campos y botones que ningún criterio pide.
  - *Cómo se detectó:* lo pedí yo al exigir solo lo del enunciado; se revisó cada pieza contra los criterios.

## Lo que escribiste tú sin IA
- No escribí código ni documentación sin IA en este tramo. Mi trabajo fue dirigir y revisar:
  - Fijar el alcance: exigí ceñirse a los criterios del enunciado, lo que llevó a quitar piezas que ninguno pedía.
  - Revisar el cumplimiento: pregunté si se cumplía justo lo pedido y evalué el único extra (cerrar la actividad) antes de aceptarlo.
  - Decidir sobre el repositorio: sacar `PROGRESS_MEMORY.md` del PR del T-200, no reescribir historia y evitar commits sueltos de documentación.
  - Aprobar cada commit después de ver su contenido y su verificación.
