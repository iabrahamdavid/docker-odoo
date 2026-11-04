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
En el commit `3f4d73f`, el helper `_create_order()` de `tests/test_sale_commission.py` dejó de usar `.with_user(user)`: desde entonces todos los pedidos de prueba se crean y se confirman como administrador, que no pasa por las listas de control de acceso. La línea `cls.env.user.commission_percent = 5.0` se añadió en el mismo commit para que las pruebas existentes siguieran pasando ya como administrador; es una consecuencia del cambio, no la causa. Por eso las pruebas quedaron en verde aunque un vendedor no pudiera confirmar. El análisis completo está en la sección 7.

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

---

# Tramo B — Contención y comunicación

## 6. Contención en los primeros 15 minutos

### Medida
Antes de tener la corrección desplegada, un administrador crea desde la interfaz **un permiso de solo lectura** sobre las reglas de comisión para el grupo de vendedores:

- Ruta: *Ajustes → Técnico → Seguridad → Derechos de acceso → Nuevo*.
- Nombre: `TEMP T-200 contencion`.
- Modelo: *Comisión por categoría de producto* (`sale.commission.rule`).
- Grupo: *Ventas / Usuario: solo documentos propios* (`sales_team.group_sale_salesman`).
- Permisos: solo **Leer**. Escribir, Crear y Eliminar quedan sin marcar.

Toma unos 2 minutos, no requiere desplegar código ni reiniciar el servidor y tiene el mismo efecto que la corrección definitiva (sección 4).

### Por qué es reversible
Basta con borrar o archivar el registro `TEMP T-200 contencion` para volver exactamente al estado anterior. No toca datos de pedidos ni el código del módulo.

### Riesgos
- Los vendedores pueden **leer** los porcentajes de comisión por categoría. Es el mismo acceso que dará la corrección definitiva, pero conviene que el cliente lo sepa.
- Es un cambio manual fuera del código. Si no se borra después de desplegar la corrección, quedan dos permisos equivalentes: no causa errores, pero confunde a quien audite los permisos. Por eso su borrado es un paso explícito del despliegue (sección 8).
- Lo debe hacer un usuario administrador, dejando constancia de quién lo hizo y a qué hora.

### Alternativas descartadas
| Alternativa | Motivo |
|---|---|
| Dar a los vendedores el grupo del gerente | Reparte permisos de más: podrían editar porcentajes y ver lo de otros vendedores. |
| Volver a la versión 1.0.0 del módulo | Obliga a desinstalar o retroceder el esquema y se pierden las reglas por categoría; no cabe en 15 minutos ni se revierte con facilidad. |
| Que el gerente siga confirmando los pedidos | No aguanta el volumen del sábado y deja pedidos confirmados con el usuario equivocado. |
| Añadir `sudo()` en el código | Exige desplegar código, que es justo lo que no se puede hacer en 15 minutos, y oculta el problema de permisos. |

### Prueba realizada
Se probó en una base de datos aparte (`t200_contencion`) con el código de la rama base, que todavía tiene el error. Se usó un usuario vendedor que no pertenece al grupo del gerente y una categoría con regla del 8 %. El permiso se creó y se borró con `odoo shell`, que equivale a hacerlo desde la interfaz. Resultados reales:

| Paso | Acción | Resultado |
|---|---|---|
| 1 | El vendedor confirma `S00001` sin contención | `AccessError: You are not allowed to access 'Comisión por categoría de producto' (sale.commission.rule) records.` |
| 2 | Se crea el permiso `TEMP T-200 contencion` (solo lectura) | Creado |
| 3 | El vendedor confirma `S00002` | Confirmado (estado `sale`), comisión de la línea: 8,0 % |
| 3b | El vendedor intenta cambiar el porcentaje de la categoría | `AccessError`: sigue sin poder editarlo |
| 4 | Se borra el permiso temporal | Quedan 0 permisos con ese nombre |
| 5 | El vendedor confirma `S00003` | `AccessError` de nuevo: la medida se revierte por completo |

---

## 7. Commit que introdujo el error y por qué pasó la revisión

### Identificación
Historial del módulo (`git log --oneline -- src/custom/prueba-tecnica/sale_commission`):

| Commit | Descripción | Estado |
|---|---|---|
| `ad51040` | [ADD] versión 1.0.0: comisión por línea y análisis mensual | Funciona |
| **`3f4d73f`** | **[FEAT] versión 1.1.0: porcentaje de comisión por categoría de producto** | **Falla** |
| `87ac54d` | [DOC] README con la configuración por categoría | Solo documentación |

`3f4d73f` es el primer commit en el que aparece `sale.commission.rule` y en el que la confirmación del pedido empieza a consultarlo. Así lo muestra `git show 3f4d73f -- security/ tests/`:

```diff
 # security/ir.model.access.csv
 id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink
+access_sale_commission_rule_manager,sale.commission.rule.manager,model_sale_commission_rule,sales_team.group_sale_manager,1,1,1,1
 access_sale_commission_report_salesman,sale.commission.report.salesman,model_sale_commission_report,sales_team.group_sale_salesman,1,0,0,0
```

```diff
 # tests/test_sale_commission.py
         cls.salesman.commission_percent = 5.0
+        cls.env.user.commission_percent = 5.0
 ...
     def _create_order(self, user, qty=2):
-        return self.env["sale.order"].with_user(user).create({
+        return self.env["sale.order"].create({
```

Con un historial más largo se confirmaría con `git bisect` entre la última versión buena y la primera mala. El criterio sería la prueba de regresión del Tramo A, que hay que copiar en cada commit evaluado porque no existe en esos commits:

```bash
git bisect start 3f4d73f ad51040   # malo, bueno
git bisect run <script que copia la prueba de regresión y corre ./odoo test prueba-tecnica sale_commission>
git bisect reset
```

No se ejecutó: `3f4d73f` es el único commit de código entre la versión que funciona (`ad51040`) y la que falla, así que `git log` y el diff bastan para identificarlo.

### Por qué pasó la revisión
1. **Las pruebas dejaron de ejecutarse como vendedor.** Al quitar `.with_user(user)` de `_create_order()`, todos los pedidos de prueba se crean y confirman como administrador, que no pasa por las listas de control de acceso. La línea `cls.env.user.commission_percent = 5.0` se añadió para que las pruebas siguieran dando el resultado esperado ya como administrador: es una consecuencia, no la causa.
2. **Lo que falta no aparece en el diff.** En `ir.model.access.csv` solo se añade una línea, la del gerente, que es correcta. La línea ausente, la del vendedor, no se ve en la revisión.
3. **El mensaje del commit orienta hacia el gerente.** Dice «configurable desde la categoría por el gerente de ventas», lo que lleva a pensar solo en ese rol. Sin embargo, `_get_commission_percent()` se ejecuta al confirmar el pedido, es decir, con el usuario vendedor.
4. **Nadie confirmó un pedido con un vendedor antes de desplegar.** Las pruebas estaban en verde y no hubo una prueba manual con ese rol.
