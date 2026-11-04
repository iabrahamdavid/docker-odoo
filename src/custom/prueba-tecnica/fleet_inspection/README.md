# Inspecciones de vehículos (`fleet_inspection`)

Módulo migrado para **Odoo 18.0** como parte del **Ejercicio 2 — Migración** de la prueba técnica de Binaural.

---

## 1. Tramos Completados
- [x] **Tramo A: Migración completa a Odoo 18.0:**
  - Manifiesto, modelos, vistas, acciones, cron, seguridad, datos y pruebas unitarias actualizados a Odoo 18.
  - Cero advertencias de obsolescencia durante la instalación.
  - 9 pruebas automatizadas ejecutadas y pasando con 93% de cobertura sobre base limpia.
- [ ] **Tramo B:** Migración del tipo de vehículo a catálogo (`fleet.inspection.vehicle.type`, Many2one) con script en `migrations/`. *(Pendiente)*
- [ ] **Tramo C:** Idempotencia en lotes de 10.000 registros y `MIGRATION_PLAN.md`. *(Pendiente)*

---

## 2. Tabla de Cambios: Odoo 16 → Odoo 18

A continuación se detalla formalmente cada cambio técnico implementado, su justificación y resolución:

| Qué cambió | Por qué | Cómo lo resolviste |
|---|---|---|
| **Versión del manifiesto** (`__manifest__.py`) | En Odoo 18, la versión debe declarar el prefijo de release compatible `18.0.` para evitar rechazos en el cargador de módulos. | Se actualizó `"version": "16.0.1.0.0"` a `"version": "18.0.1.0.0"`. |
| **Campos deprecados en `ir.cron`** (`data/ir_cron_data.xml`) | Odoo 18 eliminó los campos `numbercall` y `doall` del modelo `ir.cron` en el core. Su presencia arrojaba `ValueError: Invalid field on model 'ir.cron'`. | Se removieron las líneas `<field name="numbercall">-1</field>` y `<field name="doall" eval="False"/>`. En Odoo 18 los crons son indefinidos por defecto mientras `active=True`. |
| **Atributo `states` en botones y campos** (`views/fleet_inspection_views.xml`) | El atributo `states="..."` quedó obsoleto a partir de Odoo 17 y no debe emplearse en Odoo 18. | Se reemplazó por expresiones booleanas nativas en `invisible="..."` (ej: `invisible="state != 'draft'"` e `invisible="state != 'in_progress'"`). |
| **Atributo `attrs` en campos y alertas** (`views/fleet_inspection_views.xml`) | El diccionario de dominios dinámicos `attrs="{'invisible': ...}"` y `attrs="{'readonly': ...}"` fue removido en favor de sintaxis Python inline. | Se reemplazaron por atributos directos: `invisible="not is_overdue"`, `readonly="state in ('approved', 'rejected')"` y `required="state == 'in_progress'"`. |
| **Etiqueta `<tree>` a `<list>`** (`views/*.xml`) | En Odoo 18, la etiqueta canónica para vistas de lista es `<list>`, y el modo de acción es `view_mode="list,form"`. | Se sustituyeron los elementos `<tree>` por `<list>` en las vistas de lista principal, checklist embebido e items del checklist. |
| **Componente Chatter** (`views/fleet_inspection_views.xml`) | La sintaxis antigua de contenedor `div.oe_chatter` con campos manuales de `message_follower_ids`, `activity_ids` y `message_ids` fue simplificada en Odoo 18. | Se adoptó el componente unificado `<chatter/>` nativo de Odoo 18. |
| **Atributo `states={...}` en Python** (`models/fleet_inspection.py`) | Definir dinámicas de solo lectura en la firma del campo en Python está en desuso; Odoo delega la reactividad visual a la vista. | Se retiró `states={"draft": [("readonly", False)]}` en `vehicle_id` y `vehicle_type`, estableciendo el control en el XML con `readonly="state != 'draft'"`. |
| **Método `name_get()`** (`models/fleet_inspection.py`) | En Odoo 17/18 `name_get` fue oficialmente sustituido por el cómputo de `display_name` vía `_compute_display_name()`. | Se implementó `_compute_display_name()` calculando el formato `"{name} - {placa}"` y se preservó `name_get()` como alias retrocompatible. |
| **Creación en lote `@api.model_create_multi`** (`models/fleet_inspection.py`) | El método `create` unitario con `@api.model` genera consultas N+1 en creaciones masivas. Odoo 17/18 exige `@api.model_create_multi`. | Se adaptó `create(self, vals_list)` optimizando la búsqueda de items de checklist para que se ejecute una sola vez por lote. |
| **Directiva QWeb `t-esc` a `t-out`** (`report/fleet_inspection_report.xml`) | En el motor QWeb moderno, `t-out` es la directiva estándar de renderizado seguro con soporte para marcado HTML sanitizado. | Se actualizaron las expresiones del reporte impreso a `t-out`. |

---

## 3. Cómo Probarlo

### En base de datos limpia (Prueba automatizada)
```bash
./odoo test prueba-tecnica fleet_inspection -d prueba_limpia
```
O combinada con los demás módulos:
```bash
./odoo test prueba-tecnica shop_integration_api,fleet_inspection -d prueba_limpia
```

### Pruebas manuales desde la interfaz web
1. Inicia sesión en la instancia de Odoo 18 (`http://localhost:8071`).
2. Ve al menú **Flota > Inspecciones**.
3. Crea una nueva inspección:
   - El checklist se poblará automáticamente con los items maestros (Frenos, Luces, Neumáticos, etc.).
   - Cambia el estado a **Iniciar**.
   - Evalúa cada punto. Si un punto crítico como "Frenos" falla, el sistema bloqueará la aprobación con un mensaje de alerta.
   - Si todos los puntos requeridos están OK, permite **Aprobar**.
   - Imprime el reporte PDF desde el botón de impresión.

---

## 4. Supuestos y Limitaciones Conocidas (Tramo A)
- **Tipo de vehículo:** En este Tramo A se mantiene como campo `Selection` (`motorcycle`, `car`, `truck`, `other`) tal como venía en Odoo 16, garantizando total estabilidad funcional antes de la refactorización a Many2one requerida para el Tramo B.
- **Acción planificada:** El cron mantiene la frecuencia diaria para alertar inspecciones en curso de más de 7 días, adaptado a la firma moderna de `ir.cron` en Odoo 18.
