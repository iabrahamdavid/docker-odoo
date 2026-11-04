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
