# AI_LOG — payment_request

## Herramientas
- Antigravity AI Assistant (Gemini 3.8 Flash) en entorno Linux (Ubuntu).
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
5. **Generación de suite de pruebas unitarias exhaustiva:**
   - *Prompt:* "Genera una suite de tests con TransactionCase para verificar el ciclo de vida completo de payment.request, validaciones de monto positivo, bloqueo de edición, prevención de aprobación no autorizada y reglas de registro".
   - *Resultado:* Suite con 8 tests automatizados cubriendo el 100% de los requerimientos del Tramo A.

## Lo que la IA hizo mal
- En un borrador inicial sugirió bloquear el método `write()` genéricamente para cualquier campo cuando `state != 'draft'`. Esto habría provocado errores en cascada al momento de actualizar el estado (`state = 'approved'`), registrar el seguimiento en el chatter o asignar campos del sistema.
- *Cómo se corrigió:* Se definió un conjunto específico de campos sensibles (`restricted_fields`: `partner_id`, `applicant_id`, `amount`, `currency_id`, `date`, `concept`, `company_id`) y se eximió a superusuario (`self.env.su`).

## Lo que escribiste tú sin IA
- Redacción detallada de la sección «Supuestos y preguntas al cliente» para Carolina Méndez en el `README.md`, analizando la realidad operativa de empresas venezolanas (tasas BCV vs fecha de pago, manejo de órdenes de pago directas vs facturas preexistentes en Odoo).
- Definición de la jerarquía de herencia de grupos de seguridad (`group_payment_request_user` -> `group_payment_request_approver` -> `group_payment_request_manager`) para simplificar la asignación de permisos de usuarios en el ERP.

