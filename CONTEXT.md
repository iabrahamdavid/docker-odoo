# CONTEXT.md — Especificaciones del Entorno y Reglas del Proyecto

Este documento establece la **fuente única de verdad** para el desarrollo, las directrices técnicas y el comportamiento asistido por IA en esta prueba técnica para **Binaural**.

---

## 1. Información del Entorno y Versión

- **Versión de Odoo Objetivo:** `18.0` (Community Edition).
- **Contenedor Principal:** `dockerodoo-odoo-prueba-tecnica-1` (instancia `prueba-tecnica` en `instances.json`).
- **Base de Datos:** PostgreSQL 17 (`dockerodoo-db-v18-1`), accesible internamente en la red Docker y externamente en `localhost:5433` (con `expose_host_port: true`).
- **Ruta de Addons Activa:** `src/custom/prueba-tecnica/`.
- **Ejecutor de Comandos:** CLI oficial `odoo` (Python 3.12).

---

## 2. Restricciones Técnicas Absolutas (Odoo 17 y 18+)

1. **Sintaxis Moderna Obligatoria:**
   - Prohibido terminantemente el uso de atributos obsoletos como `attrs="..."` y `states="..."` en vistas XML. Se debe usar la sintaxis nativa: `invisible="..."`, `readonly="..."`, `required="..."`.
   - Vistas de lista en Odoo 18: Se acepta `<tree>` y `<list>`.
   - Vistas y acciones: No utilizar `numbercall` en `ir.cron` (obsoleto a partir de Odoo 18).
2. **Convención de Idiomas:**
   - **Código Técnico:** Nombres de modelos (`payment.request`), campos (`amount`, `partner_id`), nombres de métodos, variables y docstrings técnicos en **inglés**.
   - **Interfaz y Documentación:** Etiquetas visibles al usuario (`string="..."`, mensajes de error, tooltips) y documentación (`README.md`, `INCIDENT.md`, etc.) en **español**.
3. **Seguridad y Control de Acceso:**
   - Todo modelo nuevo debe contar con su correspondiente archivo de permisos `security/ir.model.access.csv`.
   - **Regla sobre `sudo()`:** Queda estrictamente prohibido el uso indiscriminado de `sudo()` para enmascarar fallos de permisos. Si un caso de negocio requiere elevar privilegios, debe quedar formalmente justificado en el código y en el `README.md`.
   - Ninguna clave privada, token o contraseña real debe ser almacenada en el repositorio ni registrada en archivos de log.
4. **Optimización de Consultas (No N+1):**
   - Prohibido invocar `.search()` dentro de bucles `for`. Usar `search_read`, prefetching automático o cálculos agrupados con `read_group` / SQL directo cuando la volumetría lo amerite.

---

## 3. Convenciones de Git y Entregables

- **Prefijos de Commit Obligatorios:**
  - `[FEAT]` Nueva funcionalidad.
  - `[FIX]` Corrección de errores o bugs.
  - `[MIG]` Migración de versiones o transformaciones de esquema/datos.
  - `[TEST]` Creación o ajuste de pruebas unitarias/integración.
  - `[DOC]` Documentación, análisis o bitácoras.
- **Nomenclatura y Trazabilidad por Ejercicio y Tramo:**
  Para facilitar la auditoría técnica y revisión de la entrega, cada commit identifica formalmente al final de su mensaje el ejercicio y tramo al que corresponde:
  - Formato: [PREFIJO] <módulo>: <descripción> (<ejercicio>.<tramo>)
  - Ejemplos: (1.A) = Ejercicio 1, Tramo A; (1.B) = Ejercicio 1, Tramo B; (2.A) = Ejercicio 2, Tramo A, etc.
- **Granularidad de Commits:** Commits atómicos y descriptivos ([FEAT], [TEST], [DOC]). No se aceptan megacommit finales.
- **Flujo de Ramas:**
  - Rama base: `master-multi-prueba-tecnica`.
  - **Ejercicio 3 (Exigencia formal):** Debe desarrollarse en la rama aislada `hotfix/T-200` y subirse a GitHub para abrir el correspondiente Pull Request hacia la rama base.

---

## 4. Estructura de Módulos Requerida

Todos los módulos deben residir en `src/custom/prueba-tecnica/`:

| Ejercicio | Directorio del Módulo | Tipo | Requisitos Especiales |
|---|---|---|---|
| **1. Integración API** | `shop_integration_api` | Nuevo | `README.md`, `AI_LOG.md`, `openapi.yaml` (Tramo C) |
| **2. Migración** | `fleet_inspection` | Migrado de 16 | `README.md` (con tabla de cambios), `AI_LOG.md`, `MIGRATION_PLAN.md` (Tramo C) |
| **3. Ticket Urgente** | `sale_commission` | Hotfix | Rama `hotfix/T-200`, `README.md`, `AI_LOG.md`, `INCIDENT.md` |
| **4. Solicitud de Pagos** | `payment_request` | Nuevo | `README.md` (con sección Supuestos y preguntas), `AI_LOG.md`, `ARCHITECTURE.md` |

---

## 5. Protocolo de Pruebas Automatizadas

Todo módulo debe verificarse en el entorno Docker mediante el comando oficial del repositorio:

```powershell
$env:PYTHONUTF8=1; python odoo test prueba-tecnica <nombre_modulo>
```

Y para la verificación final conjunta de todos los módulos sobre base limpia:
```powershell
$env:PYTHONUTF8=1; python odoo test -d prueba_limpia -m shop_integration_api,fleet_inspection,sale_commission,payment_request
```

