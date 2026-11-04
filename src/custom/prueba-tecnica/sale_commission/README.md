# Comisiones de vendedores (`sale_commission`)

Calcula la comisión del vendedor en cada línea de pedido de venta y ofrece un análisis mensual por vendedor.

---

## 1. Tramos y Estado de Avance

- [x] **Tramo A — Ticket urgente T-200:** Corrección de `AccessError` al confirmar pedidos por usuarios con rol de vendedor (`sales_team.group_sale_salesman`). Resuelto en la rama aislada `hotfix/T-200` y documentado en [`INCIDENT.md`](./INCIDENT.md).
- [x] **Tramo B — Contención y comunicación:** Contención de 15 minutos con permiso temporal de solo lectura (probada y reversible), commit causante `3f4d73f` y por qué pasó la revisión, pasos de despliegue y verificación, y mensaje al cliente. Documentado en [`INCIDENT.md`](./INCIDENT.md), secciones 6 a 9.
- [ ] **Tramo C — Impacto en datos y prevención:** Script de auditoría de comisiones calculadas por terceros y propuestas de prevención en CI. *(Pendiente)*

---

## 2. Configuración y Funcionamiento

- **Porcentaje del vendedor:** Ajustes › Usuarios › pestaña *Comisiones* (solo gerentes de ventas).
- **Porcentaje por categoría (desde la 1.1):** Inventario/Ventas › Configuración › Categorías de producto, campo *Comisión (%)*. Si la categoría (o una categoría padre) tiene porcentaje, reemplaza al del vendedor.
- **Cálculo de comisión:** Al confirmar el pedido se fija el porcentaje en cada línea y se calcula la comisión sobre el subtotal sin impuestos.
- **Reportes:** Ventas › Reportes › *Comisiones*: tabla dinámica y gráfico por vendedor y mes. Cada vendedor ve solo lo suyo.

---

## 3. Pruebas Automatizadas

Para ejecutar la suite de pruebas unitarias del módulo:

```bash
./odoo test prueba-tecnica sale_commission
```

En la rama `hotfix/T-200`, la suite incluye el test de regresión `test_salesman_can_confirm_order_with_category_commission` que reproduce el fallo antes del cambio y verifica la solución posterior (5 tests pasando al 100%, 83% de cobertura).

La prueba de la contención del Tramo B (pasos y resultados reales) está en [`INCIDENT.md`](./INCIDENT.md), sección 6.

---

## 4. Supuestos y Limitaciones Conocidas (Tramos A y B)

1. **Principio de menor privilegio:** La corrección del ticket T-200 se limitó estrictamente a conceder permiso de lectura (`perm_read = 1, perm_write = 0, perm_create = 0, perm_unlink = 0`) sobre el modelo `sale.commission.rule` al grupo de vendedores, sin elevar privilegios innecesariamente ni recurrir a `sudo()`.
2. **Determinación del usuario en comisiones:** En `sale_order_line.py`, el método `_get_commission_percent` retorna `self.env.user.commission_percent` como fallback si no hay regla de categoría. Por regla de producción (cambio mínimo para corregir la causa raíz sin alterar comportamiento previo), este diseño se conservó intacto en el Tramo A.
3. **Contención manual (Tramo B):** el permiso temporal `TEMP T-200 contencion` se crea a mano, fuera del código del módulo, y la actualización del módulo no lo borra. Hay que borrarlo después de desplegar la corrección (paso 6 de la sección 8 del `INCIDENT.md`). Se probó en una base de datos de prueba con el código que tiene el error, no en la producción del cliente.
