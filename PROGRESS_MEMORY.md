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
| **2. Migración** | `fleet_inspection` | ⏳ Pendiente | ⏳ Pendiente | ⏳ Pendiente | Mover de `prueba-tecnica-odoo16/`, tabla cambios, `MIGRATION_PLAN.md` |
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

---

## 4. Tarea Actual en Ejecución
- **Módulo:** `shop_integration_api` (Ejercicio 1)
- **Objetivo:** Tramo B culminado con éxito. Próximo paso: Tramo C (Paginación, idempotencia con `Idempotency-Key`, optimización de stock y webhook) o commits atómicos de cierre.
