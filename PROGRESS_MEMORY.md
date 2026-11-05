# PROGRESS_MEMORY.md — Memoria Viva del Proyecto

Este archivo mantiene el estado continuo del desarrollo. Si la ventana de contexto se compacta o se reinicia la sesión, este documento contiene el estado exacto, decisiones tomadas y próximos pasos inmediatos.

---

## 1. Estado General del Proyecto
- **Versión de Odoo:** `18.0` (instancia `prueba-tecnica`)
- **Base de Datos:** PostgreSQL 17 (`v18`, puerto 5433 expuesto para inspección)
- **Repo Remoto:** `https://github.com/iabrahamdavid/binaural-testing.git` (rama `master-multi-prueba-tecnica`)
- **Comando de prueba:** `$env:PYTHONUTF8=1; python odoo test prueba-tecnica <modulo>`

---

## 2. Mapa de Progreso por Ejercicio

| Ejercicio | Módulo | Tramo A | Tramo B | Tramo C | Notas / Entregables |
|---|---|:---:|:---:|:---:|---|
| **1. API Tienda** | `shop_integration_api` | ✅ Completado | ✅ Completado (16/16 tests, 77% cov) | ⏳ Pendiente | `README.md`, `AI_LOG.md` |
| **2. Migración** | `fleet_inspection` | ✅ Completado (9/9 tests, 93% cov) | ✅ Completado (12/12 tests, 94% cov) | ⏳ Pendiente | Tabla cambios, `migrations/`, `README.md`, `AI_LOG.md` |
| **3. Ticket Urgente** | `sale_commission` | ✅ Completado (5/5 tests, 83% cov) | ✅ Completado (solo documentación) | ⏳ Pendiente | Rama `hotfix/T-200`, `INCIDENT.md`, `AI_LOG.md`, PR |
| **4. Solicitudes Pago** | `payment_request` | ✅ Completado (9/9 tests) | ✅ Completado (21/21 tests, 94% cov) | ⏳ Pendiente | Supuestos Carolina, `README.md`, `AI_LOG.md` |

---

## 3. Bitácora de Acciones Completadas

- [x] Configuración de Git en Windows (`core.autocrlf false`) y subida limpia del repositorio a GitHub.
- [x] Corrección de compatibilidad en Windows para `odoo_cli/core/actions/testing.py` (`sys.executable`) y `.resources/generators/compose_generator.py` (`encoding='utf-8'`).
- [x] Publicación de puerto PostgreSQL 5433 en `instances.json` y verificación de conexión externa con pgAdmin 4.
- [x] Configuración de `.vscode/settings.json` para silenciar advertencias de importaciones de Odoo en el host Windows.
- [x] Declaración formal de versión Odoo 18.0 en `readme.md` principal.
- [x] **Tramo A `shop_integration_api`:** Endpoint `GET /api/v1/products` con filtros, HTTP 400 y tests `HttpCase`.
- [x] **Tramo B `shop_integration_api`:**
  - Modelo `shop.api.log` con seguridad `ir.model.access.csv`.
  - Autenticación Bearer nativa con API Keys (`res.users.apikeys`).
  - Endpoint `POST /api/v1/orders` con validación 422 (`CUSTOMER_NOT_FOUND`, `PRODUCT_NOT_FOUND`, `INVALID_QUANTITY`, `EMPTY_LINES`) y 201 Created.
  - Middleware de medición y registro en transacción aislada (`env.registry.cursor()`).
  - 15 tests automatizados pasando en verde (100% éxito, 0 errores, 0 fallos).
  - Documentación actualizada en `README.md` y `AI_LOG.md`.

- [x] **Tramo A `fleet_inspection` (Ejercicio 2):**
  - Reubicación a `src/custom/prueba-tecnica/fleet_inspection`.
  - Migración a Odoo 18: manifiesto (`18.0.1.0.0`), modelos (`_compute_display_name`, `@api.model_create_multi`, eliminación de `states={...}`).
  - Modernización de vistas XML: adopción de `<list>`, `<chatter/>`, atributos nativos `invisible` y `readonly`.
  - Corrección en datos de cron: eliminación de campos removidos en Odoo 18 (`numbercall` y `doall`).
  - 9 tests automatizados pasando en verde (100% éxito, 0 fallos, 0 errores, 93% cobertura).
  - Documentación obligatoria con tabla formal de cambios en `README.md` y bitácora en `AI_LOG.md`.
  - 3 commits atómicos con prefijos `[MIG]`, `[TEST]`, `[DOC]`.

- [x] **Tramo B `fleet_inspection` (Ejercicio 2):**
  - Catálogo `fleet.inspection.vehicle.type` (Moto, Carro, Camión, Otro) con permisos y menú en Configuración de Flota.
  - Campo `vehicle_type` (Selection) reemplazado por `vehicle_type_id` (Many2one); manifiesto `18.0.1.1.0`.
  - Scripts `migrations/18.0.1.1.0/pre-migrate.py` (conserva la columna como `vehicle_type_legacy`) y `post-migrate.py` (mapeo por `code`; valores desconocidos a «Otro» con aviso).
  - Escenario real Tramo A → datos → `-u`: 14 inspecciones, mismos conteos por tipo antes y después, 0 sin tipo, 0 con tipo equivocado, «Otro» conservado.
  - 12 tests en verde (3 nuevos de la lógica de migración), 94% de cobertura.
  - 4 commits atómicos con prefijos `[FEAT]`, `[MIG]`, `[TEST]`, `[DOC]`.

- [x] **Tramo A `sale_commission` (Ejercicio 3 — Ticket T-200):**
  - Rama `hotfix/T-200` creada a partir de `master-multi-prueba-tecnica`.
  - Reproducción formal del fallo con test unitario ejecutado bajo usuario vendedor (`test_salesman_can_confirm_order_with_category_commission`), confirmando `AccessError` en la fase roja.
  - Corrección mínima bajo principio de menor privilegio en `security/ir.model.access.csv`: permiso exclusivo de lectura (`1,0,0,0`) al grupo `sales_team.group_sale_salesman` sobre `sale.commission.rule`.
  - Fase verde superada con 5/5 tests en éxito y 83% de cobertura.
  - Creación de documentación del incidente en `INCIDENT.md` y bitácora en `AI_LOG.md`.

- [x] **Tramo A `payment_request` (Ejercicio 4):**
  - Creación del módulo base `payment_request` con dependencias `base` y `mail`.
  - Modelo `payment.request` con `mail.thread` y `mail.activity.mixin`, secuencia automática `SP/%(year)s/0001` al enviar.
  - Validación de monto estrictamente positivo (`amount > 0`).
  - Inmutabilidad estricta tras envío en `write()` y reglas de borrado seguro en `unlink()`.
  - Seguridad jerárquica: `Solicitante` (`group_payment_request_user`), `Aprobador` (`group_payment_request_approver`) y `Tesorería` (`group_payment_request_manager`).
  - Reglas de registro con aislamiento de visibilidad (`ir.rule`) para que solicitantes solo vean sus solicitudes y aprobadores vean todas.
  - Restricción de método en `action_approve()` y `action_reject()` con `AccessError` para no aprobadores.
  - Vistas modernas Odoo 18: `<list>` decorada, `<form>` con `<chatter/>` y `<search>` con filtros por estado y agrupaciones.
  - Suite de 8 pruebas unitarias automatizadas (`test_payment_request.py`).
  - Blindaje contra auto-aprobación en `write()` y `create()` ante manipulaciones directas de `state` y `name`.
  - Documentación obligatoria en `README.md` con sección de «Supuestos y preguntas al cliente» (Carolina Méndez), limitaciones conocidas y bitácora transparente `AI_LOG.md`.

- [x] **Tramo B `sale_commission` (Ejercicio 3 — Ticket T-200, en la rama `hotfix/T-200`, PR abierto):**
  - Contención de 15 minutos probada: permiso temporal de solo lectura `TEMP T-200 contencion` (falla → permiso → confirma → se borra → vuelve a fallar).
  - Commit causante `3f4d73f` y por qué pasó la revisión (las pruebas dejaron de ejecutarse como vendedor).
  - Pasos de despliegue (`-u sale_commission`, borrar el permiso temporal) y verificación, y mensaje al cliente en `INCIDENT.md`.
  - El PR solo contiene archivos del T-200; este archivo se lleva en la rama base.

- [x] **Revisión previa a la entrega (`shop_integration_api`, 1.B):**
  - Quitado el `sudo()` innecesario al validar la API key; justificado el del registro de llamadas (medido: sin él, las llamadas con 401 no quedan en el log).
  - Prueba nueva de que las llamadas fallidas quedan en el log sin la clave (16 tests).

- [x] **Tramo B `payment_request` (Ejercicio 4):**
  - Modelo `payment.approval.level` (monto mínimo y aprobador); al enviar se asigna el aprobador por monto y se le crea una actividad.
  - Solo el aprobador asignado aprueba o rechaza; quedan quién aprobó y cuándo.
  - Wizard de rechazo con motivo obligatorio publicado en el chatter (notifica al solicitante).
  - Wizard de pago con diario: crea y publica el `account.payment` de proveedor vinculado; no se puede pagar dos veces. Depende de `account`; Tesorería incluye Facturación.
  - Reporte QWeb PDF con quién aprobó y cuándo.
  - 21 tests en verde (12 nuevos), 94% de cobertura; cada prueba nueva falla al quitar la regla que cubre.

---

## 4. Tarea Actual en Ejecución
- **Módulos:** `shop_integration_api`, `fleet_inspection`, `sale_commission`, `payment_request`
- **Objetivo:** Tramos A y B de los 4 ejercicios completados (el ejercicio 3 en el PR de `hotfix/T-200`); quedan los Tramos C.
- **Último avance:** Ejercicio 4 Tramo B completado. Batería oficial sobre `prueba_limpia` (2026-11-05): 53/53 tests en verde, 4/4 módulos instalados, 87% de cobertura global, 0 avisos de obsolescencia. Siguiente: Tramos C.
