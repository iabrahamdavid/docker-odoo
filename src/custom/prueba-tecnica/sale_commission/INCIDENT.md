# INCIDENT.md — Reporte Técnico de Incidencia en Producción

- **Ticket:** T-200 · Crítica · ¡No podemos vender!
- **Módulo afectado:** `sale_commission`
- **Fecha del incidente:** Viernes, 17:40 hrs (desplegado a las 12:00 m.)
- **Cliente:** Comercial Los Andes C.A.
- **Severidad:** Crítica (Bloqueante de ventas)
- **Estado:** ✅ Resuelto y verificado

---

## 1. Resumen Ejecutivo del Incidente
Tras el despliegue a las 12:00 m. de la actualización del módulo `sale_commission` (versión 1.1.0, commit `3f4d73f`), ningún usuario con rol de vendedor (`sales_team.group_sale_salesman`) podía confirmar pedidos de venta desde la interfaz web, recibiendo una ventana modal roja con error de acceso (`AccessError`). La confirmación únicamente funcionaba con el usuario del gerente de ventas (`sales_team.group_sale_manager`), quien tuvo que confirmar manualmente los pedidos durante la tarde.

---

## 2. Cómo se Reproduce el Error

### Reproducción Funcional (Interfaz Web)
1. Iniciar sesión con un usuario perteneciente al grupo **Ventas / Mostrar solo documentos propios** (`sales_team.group_sale_salesman`).
2. Crear un presupuesto de venta (`sale.order`) agregando una línea de producto cuya categoría cuente con regla de comisión o esté sujeta al cálculo.
3. Hacer clic en el botón **Confirmar** (`action_confirm`).
4. **Resultado observado:** Odoo bloquea la acción y arroja una excepción en pantalla:
   ```text
   odoo.exceptions.AccessError: You are not allowed to access 'Comisión por categoría de producto' (sale.commission.rule) records.
   This operation is allowed for the following groups:
       - Sales/Administrator
   ```

### Reproducción Automatizada (Test de Regresión)
Se incorporó el caso de prueba `test_salesman_can_confirm_order_with_category_commission` en `tests/test_sale_commission.py`:
```python
def test_salesman_can_confirm_order_with_category_commission(self):
    self.category.commission_percent = 8.0
    order = self.env["sale.order"].with_user(self.salesman).create({
        "partner_id": self.partner.id,
        "user_id": self.salesman.id,
        "order_line": [(0, 0, {"product_id": self.product.id, "product_uom_qty": 2})],
    })
    order.with_user(self.salesman).action_confirm()
    self.assertEqual(order.state, "sale")
    self.assertEqual(order.order_line.commission_percent, 8.0)
```
Al correr `./odoo test prueba-tecnica sale_commission`, la prueba falla con `AccessError` antes del parche.

---

## 3. Diagnóstico Técnico y Causa Raíz

### Auditoría del Despliegue
Al revisar el historial con `git log -p 3f4d73f`, se identificó el commit responsable:
- **Commit:** `3f4d73fb2810f1fd650ce1de24557cb9b49624b3`
- **Título:** `[FEAT] sale_commission: porcentaje de comisión por categoría de producto`

### Mecanismo de Falla
1. El commit introdujo el nuevo modelo `sale.commission.rule` para gestionar porcentajes por categoría.
2. Al confirmar un pedido en `sale_order.py`, se invoca `line._get_commission_percent()` en `sale_order_line.py`:
   ```python
   rules = self.env["sale.commission.rule"].search([
       ("categ_id", "parent_of", self.product_id.categ_id.id),
       ("company_id", "in", [False, self.company_id.id]),
   ])
   ```
3. En el archivo de listas de control de acceso (`security/ir.model.access.csv`), el autor original solo definió permisos para el gerente:
   ```csv
   access_sale_commission_rule_manager,sale.commission.rule.manager,model_sale_commission_rule,sales_team.group_sale_manager,1,1,1,1
   ```
   Omitió por completo otorgar permisos de lectura al grupo de vendedores (`sales_team.group_sale_salesman`).
4. Al ejecutarse `search()` en el contexto del vendedor (`self.env.user`), el ORM de Odoo valida la lista de control de acceso sobre `sale.commission.rule`. Al no existir entrada, lanza `AccessError`.

### ¿Por qué no se detectó en CI antes de desplegar?
En el commit `3f4d73f`, el desarrollador modificó el helper `_create_order()` en `tests/test_sale_commission.py` y fijó `cls.env.user.commission_percent = 5.0`. Los tests invocaban `order.action_confirm()` utilizando `self.env.user` (Superusuario / Admin), el cual elude las comprobaciones de ACL (`ir.model.access.csv`). En consecuencia, el pipeline de CI marcó verde a pesar de existir una vulnerabilidad funcional crítica para usuarios restringidos.

---

## 4. Corrección Quirúrgica Aplicada (Principio de Menor Privilegio)

Siguiendo las restricciones estrictas de producción:
- **No reescribir el módulo.**
- **No repartir permisos excesivos** (no otorgar `group_sale_manager` al vendedor).
- **No usar `sudo()`** innecesario que rompa el aislamiento de seguridad.

Se aplicó la corrección mínima y suficiente en `security/ir.model.access.csv` agregando una regla de **solo lectura** (`perm_read = 1, perm_write = 0, perm_create = 0, perm_unlink = 0`) para los vendedores:

```csv
access_sale_commission_rule_salesman,sale.commission.rule.salesman,model_sale_commission_rule,sales_team.group_sale_salesman,1,0,0,0
```

Con esto:
1. El vendedor puede leer las reglas durante la confirmación del pedido y el cálculo de comisiones.
2. El vendedor **no** puede crear, modificar ni eliminar reglas de comisión ni porcentajes.
3. El gerente conserva su acceso total (`1,1,1,1`).

---

## 5. Verificación y Resultados de Pruebas

Tras aplicar la línea en `ir.model.access.csv`, se ejecutó nuevamente la suite de pruebas automatizadas sobre base de datos limpia:

```bash
./odoo test prueba-tecnica sale_commission
```

**Resultado:**
- **Tests ejecutados:** 5 (100% de éxito, 0 errores, 0 fallos).
- **Cobertura de código:** 83%.
- **Resultado del test de regresión:** El vendedor confirma pedidos correctamente con las comisiones por categoría aplicadas, y el gerente sigue operando sin alteraciones.
