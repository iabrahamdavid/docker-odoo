# Inspecciones de vehículos (`fleet_inspection`)

Módulo migrado para **Odoo 18.0** como parte del **Ejercicio 2 — Migración** de la prueba técnica de Binaural.

---

## 1. Tramos Completados
- [x] **Tramo A: Migración completa a Odoo 18.0:**
  - Manifiesto, modelos, vistas, acciones, cron, seguridad, datos y pruebas unitarias actualizados a Odoo 18.
  - Cero advertencias de obsolescencia durante la instalación.
  - 9 pruebas automatizadas ejecutadas y pasando con 93% de cobertura sobre base limpia.
- [x] **Tramo B: Tipo de vehículo como catálogo:**
  - Nuevo modelo `fleet.inspection.vehicle.type` (Many2one `vehicle_type_id` en la inspección) con los tipos Moto, Carro, Camión y Otro.
  - Script en `migrations/18.0.1.1.0/` que, al actualizar con `-u`, asigna a cada inspección existente su tipo correcto, incluido «Otro».
  - Probado en el escenario real (Tramo A instalado → datos → versión `18.0.1.1.0` → `-u`) y con 3 pruebas de la lógica de migración (12 pruebas en total, 94% de cobertura).
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

## 3. Tramo B: tipo de vehículo como catálogo

| Qué | Decisión | Por qué |
|---|---|---|
| Modelo nuevo | `fleet.inspection.vehicle.type` con `name`, `code` (único) y `active`. Datos iniciales con `noupdate="1"`. | El enunciado pide un catálogo. `noupdate` evita que un `-u` pise los nombres que el cliente cambie. |
| ¿Usar lo que trae Odoo? | No se usa `fleet.vehicle.model.vehicle_type`. | Es un `Selection` con solo `car` y `bike`: no tiene camión ni otro y no es un catálogo. |
| Campo en la inspección | `vehicle_type_id` (Many2one, obligatorio, con seguimiento en el chatter, `ondelete="restrict"`, por defecto «Carro»). | Mantener el nombre `vehicle_type` con otro tipo hace que el ORM aparte la columna vieja con un nombre automático. `restrict` impide borrar un tipo en uso; «Carro» era el valor por defecto del Tramo A. |
| `pre-migrate` | Renombra la columna `vehicle_type` a `vehicle_type_legacy`. | Odoo borra la columna de un campo eliminado al actualizar; renombrarla conserva el valor original para mapearlo y verificarlo después. |
| `post-migrate` | Un único `UPDATE` que cruza `vehicle_type_legacy` con `code` del catálogo. | Se mapea por el código técnico, no por el nombre visible, que el cliente puede renombrar. |
| Lógica separada | `migrations_logic.py`; los scripts de `migrations/` solo la llaman. | Las carpetas con puntos en el nombre no se pueden importar desde las pruebas. |
| Historial del chatter | No se hizo nada especial. | Odoo 18 guarda la descripción del campo eliminado en `field_info`: los cambios antiguos («Camión → Otro») se siguen viendo. |

### Resultado del escenario real
Base `fleet_migracion` con el módulo del Tramo A (`18.0.1.0.0`, commit `847c7b9`) y 14 inspecciones, luego actualización a `18.0.1.1.0` con `-u`:

| Tipo | Antes (`vehicle_type`) | Después (`vehicle_type_id`) |
|---|---|---|
| car / Carro | 5 | 5 |
| motorcycle / Moto | 3 | 3 |
| other / Otro | 5 | 5 |
| truck / Camión | 1 | 1 |

- Inspecciones sin tipo: **0**. Inspecciones con un tipo distinto a su valor original: **0**.
- `vehicle_type_id` queda con `NOT NULL` en la base de datos. El log del `-u` no muestra advertencias ni errores.
- El cambio «Camión → Otro» registrado antes de migrar sigue visible en el chatter.

---

## 4. Cómo Probarlo

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

### Migración del tipo de vehículo (Tramo B)
Las pruebas de `tests/test_vehicle_type_migration.py` simulan una base del Tramo A dentro de la transacción y comprueban que cada valor antiguo acaba en su tipo, que «Otro» se conserva y que ninguna inspección queda sin tipo.

Para repetir el escenario real (los scripts de `migrations/` no se ejecutan en una instalación nueva, solo al actualizar):
1. Instalar el módulo del Tramo A (commit `847c7b9`, versión `18.0.1.0.0`) en una base nueva y crear inspecciones de cada tipo.
2. Pasar al código actual (versión `18.0.1.1.0`) y actualizar: `./odoo update prueba-tecnica -d <base> -m fleet_inspection`.
3. Verificar con `./odoo psql prueba-tecnica -d <base>`:
   ```sql
   SELECT vt.code, count(*) FROM fleet_inspection fi
     JOIN fleet_inspection_vehicle_type vt ON vt.id = fi.vehicle_type_id GROUP BY 1;
   SELECT count(*) FROM fleet_inspection WHERE vehicle_type_id IS NULL;            -- 0
   SELECT count(*) FROM fleet_inspection fi
     JOIN fleet_inspection_vehicle_type vt ON vt.id = fi.vehicle_type_id
    WHERE vt.code IS DISTINCT FROM fi.vehicle_type_legacy;                        -- 0
   ```

---

## 5. Supuestos y Limitaciones Conocidas
- **Tipo de vehículo (Tramo A):** Se mantuvo como campo `Selection` (`motorcycle`, `car`, `truck`, `other`) tal como venía en Odoo 16. En el Tramo B pasó a catálogo.
- **Valores desconocidos (Tramo B):** Si una inspección tuviera un valor antiguo vacío o que no está en el catálogo, se le asigna «Otro» y se deja un aviso en el log con cuántas y cuáles. Con el Tramo A no debería ocurrir, porque el campo era obligatorio.
- **Columna antigua (Tramo B):** `vehicle_type_legacy` no se borra: sirve para verificar la migración y para revertirla. Su eliminación queda para cuando el plan de migración (Tramo C) lo decida.
- **Pendiente para el Tramo C:** No se ha demostrado que el script pueda ejecutarse dos veces sin dañar nada, ni que procese 10.000 inspecciones por lotes; tampoco existe `MIGRATION_PLAN.md`.
- **Acción planificada:** El cron mantiene la frecuencia diaria para alertar inspecciones en curso de más de 7 días, adaptado a la firma moderna de `ir.cron` en Odoo 18.
