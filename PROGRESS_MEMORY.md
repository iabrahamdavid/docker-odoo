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
| **1. API Tienda** | `shop_integration_api` | ✅ Completado | ✅ Completado (15/15 tests, 77% cov) | ⏳ Pendiente | `README.md`, `AI_LOG.md` |
| **2. Migración** | `fleet_inspection` | ✅ Completado (9/9 tests, 93% cov) | ⏳ Pendiente | ⏳ Pendiente | Tabla cambios, `README.md`, `AI_LOG.md` |
| **3. Ticket Urgente** | `sale_commission` | ⏳ Pendiente | ⏳ Pendiente | ⏳ Pendiente | Rama `hotfix/T-200`, `INCIDENT.md`, PR |
| **4. Solicitudes Pago** | `payment_request` | ⏳ Pendiente | ⏳ Pendiente | ⏳ Pendiente | Supuestos Carolina, `ARCHITECTURE.md` |

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

---

## 4. Tarea Actual en Ejecución
- **Módulo:** `sale_commission` (Ejercicio 3)
- **Objetivo:** Tramo A — Ticket urgente T-200. Creación de rama `hotfix/T-200`, reproducción de fallo con vendedor, test que falle y corrección mínima.
