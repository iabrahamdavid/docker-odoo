# AI_LOG — shop_integration_api

## Herramientas
- Antigravity / Gemini 3.8 Flash (Asistente de codificación y arquitectura)

## Prompts clave (3 a 5)
1. *Diseño del controlador de productos Tramo A:*
   - **Pedido:** "Diseñar un controlador REST en Odoo 18 para el endpoint GET /api/v1/products con autenticación 'user', filtros por categoría, stock disponible y fecha de modificación, garantizando que errores de formato en fecha retornen HTTP 400 y nunca 500."
   - **Resultado:** Devolvió un controlador con `type='http'` y uso de `request.make_json_response()`. Se adoptó la estructura asegurando que el dominio base siempre filtre por `active=True` y `sale_ok=True`.
2. *Validación robusta de parámetros en el endpoint:*
   - **Pedido:** "Asegurar que los parámetros query string como category_id e in_stock se casteen con seguridad y soporte para valores booleanos textuales ('true', '1')."
   - **Resultado:** Implementó el parseo defensivo de `in_stock` y `category_id` devolviendo errores en formato JSON estándar en caso de fallo.
3. *Suite de pruebas HTTP con HttpCase:*
   - **Pedido:** "Escribir pruebas automatizadas con HttpCase que simulen la sesión web del usuario y validen filtros individuales, filtros combinados y los casos de error 400."
   - **Resultado:** Creó la clase `TestShopProductApi` con fixtures de productos, categorías y cantidades en stock para validar el comportamiento real contra el servidor HTTP de Odoo.

## Lo que la IA hizo mal
- **Compatibilidad de productos en Odoo 18:** La IA intentó crear productos almacenables usando `type='product'` o un fallback `type='consu'`. En Odoo 18, el modelo de datos de stock cambió: los productos almacenables exigen explícitamente `is_storable = True`. Esto provocó un fallo al asignar stock: `ValidationError: Quants cannot be created for consumables or services`.
  - *Cómo se detectó:* Al correr `./odoo test prueba-tecnica shop_integration_api`, la prueba falló de inmediato en el setup. Se inspeccionó el método `StockQuant.check_product_id` en Odoo 18 y se corrigió fijando `is_storable=True`.
- **Diferencia entre `name` y `display_name`:** La IA sugirió mapear `"name": product.display_name or product.name`. En Odoo, `display_name` concatena la referencia interna (`[TECH-001] Ratón Óptico`).
  - *Cómo se detectó:* El test unitario `test_01_get_products_base` falló al comparar el nombre esperado (`Ratón Óptico`) contra `[TECH-001] Ratón Óptico`. Se corrigió para extraer directamente `product.name`.
- **Permisos de lectura sobre `stock.move`:** El usuario de prueba inicial solo tenía el grupo `base.group_user`, lo que causaba un HTTP 403 al evaluar el stock computado `qty_available`. Se agregaron los grupos requeridos `sales_team.group_sale_salesman` y `stock.group_stock_user`.

## Lo que escribiste tú sin IA
- Definición de los supuestos de negocio sobre el catálogo: exponer el modelo `product.product` en lugar de `product.template` para tener disponibilidad de inventario real inmediata por variante.
- La estrategia de validación de fechas mediante `datetime.fromisoformat()` capturando `ValueError` para responder con un código de error de negocio semántico.
