# AI_LOG — shop_integration_api

## Herramientas
- Antigravity / Gemini (Asistente de codificación y arquitectura)

## Prompts clave (3 a 5)
1. *Diseño del controlador de productos Tramo A:*
   - **Pedido:** "Diseñar un controlador REST en Odoo 18 para el endpoint GET /api/v1/products con autenticación, filtros por categoría, stock disponible y fecha de modificación, garantizando que errores de formato en fecha retornen HTTP 400 y nunca 500."
   - **Resultado:** Devolvió un controlador con `type='http'` y uso de `request.make_json_response()`. Se adoptó la estructura asegurando que el dominio base siempre filtre por `active=True` y `sale_ok=True`.
2. *Autenticación Bearer nativa con API Keys (Tramo B):*
   - **Pedido:** "Implementar un middleware/decorador que extraiga el token Bearer de la cabecera Authorization y lo valide contra res.users.apikeys._check_credentials(scope='rpc', key=token), actualizando el entorno con request.update_env(user=uid)."
   - **Resultado:** Creó el decorador `@api_endpoint` en `controllers/auth.py` manejando el fallback a sesión activa y devolviendo respuestas 401 estructuradas en JSON.
3. *Persistencia de logs en transacciones aisladas:*
   - **Pedido:** "Garantizar que shop.api.log registre el código de estado, duración y usuario incluso si la petición falla o la transacción principal del endpoint se revierte con rollback."
   - **Resultado:** Implementó el método `log_call` utilizando un cursor independiente (`with env.registry.cursor() as cr:`) para confirmar el log en base de datos de manera atómica e inmune a fallos externos.
4. *Validación de negocio y creación de pedidos POST /api/v1/orders:*
   - **Pedido:** "Crear el endpoint POST /api/v1/orders con validaciones de cliente (RIF), líneas no vacías, existencia de productos y cantidad mayor a cero con respuestas 422 Unprocessable Entity indicando el campo exacto (ej. lines[i].default_code)."
   - **Resultado:** Implementó la lógica completa en `controllers/main.py`, generando pedidos en `sale.order` en estado `draft` y devolviendo HTTP 201 Created.

## Lo que la IA hizo mal
- **Compatibilidad de productos en Odoo 18:** La IA intentó crear productos almacenables usando `type='product'` o un fallback `type='consu'`. En Odoo 18, el modelo de datos de stock cambió: los productos almacenables exigen explícitamente `is_storable = True`. Esto provocó un fallo al asignar stock: `ValidationError: Quants cannot be created for consumables or services`.
  - *Cómo se detectó:* Al correr `./odoo test prueba-tecnica shop_integration_api`, la prueba falló de inmediato en el setup. Se inspeccionó el método `StockQuant.check_product_id` en Odoo 18 y se corrigió fijando `is_storable=True`.
- **Diferencia entre `name` y `display_name`:** La IA sugirió mapear `"name": product.display_name or product.name`. En Odoo, `display_name` concatena la referencia interna (`[TECH-001] Ratón Óptico`).
  - *Cómo se detectó:* El test unitario `test_01_get_products_base` falló al comparar el nombre esperado (`Ratón Óptico`) contra `[TECH-001] Ratón Óptico`. Se corrigió para extraer directamente `product.name`.
- **Comportamiento de `auth='user'` con tokens HTTP:** La IA propuso inicialmente usar `auth='user'` en la ruta del endpoint para tokens Bearer. En Odoo, `auth='user'` intercepta la petición a nivel de framework y devuelve una redirección HTTP 303 a `/web/login` si no hay cookie de sesión web.
  - *Cómo se detectó:* Al realizar llamadas con `curl` enviando cabecera Bearer, Odoo devolvía el HTML de redirección a login en lugar del JSON. Se cambió la ruta a `auth='public'` y se delegó la autenticación completa al decorador `@api_endpoint`.
- **Tipo de dato en expiración de API Keys:** Al generar claves con `_generate()` en las pruebas, la IA pasó un objeto `fields.Date.today()`. Odoo 18 exige estrictamente un `datetime.datetime`, provocando un `TypeError: can't compare datetime.datetime to datetime.date`. Se corrigió usando `datetime.now() + timedelta(...)`.

## Lo que escribiste tú sin IA
- Definición de los supuestos de negocio sobre el catálogo: exponer el modelo `product.product` en lugar de `product.template` para tener disponibilidad de inventario real inmediata por variante.
- La decisión arquitectónica de crear los pedidos de venta en estado `draft` (Cotización) para permitir revisión comercial y no comprometer inventario de forma irreversible.
- El esquema de transacciones aisladas con nuevo cursor para evitar la pérdida de trazabilidad ante fallos HTTP 4xx/5xx en `shop.api.log`.
