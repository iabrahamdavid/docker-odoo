# Shop Integration API (`shop_integration_api`)

Módulo de integración REST para conectar una tienda en línea externa con Odoo.

---

## 1. Tramos Completados

- [x] **Tramo A:** Endpoint `GET /api/v1/products` con autenticación y filtros.
  - Filtros opcionales: `category_id`, `in_stock`, `updated_since`.
  - Validación de tipos y formato de fecha (error `400 Bad Request` en JSON ante fechas o IDs inválidos, **nunca error 500**).
  - Serialización con `id`, `default_code`, `name`, `list_price` y `qty_available`.
  - Filtrado estricto: solo productos activos (`active=True`) y disponibles para venta (`sale_ok=True`).
  - Pruebas automatizadas de integración HTTP con `HttpCase`.
- [x] **Tramo B:** Autenticación con API keys nativas (`res.users.apikeys`, Bearer), `POST /api/v1/orders` y log de llamadas.
  - Modelo de auditoría `shop.api.log` con medición de duración y transacción aislada (`cr` independiente).
  - Middleware `@api_endpoint(require_auth=True)` con cabecera `Authorization: Bearer <token>`.
  - Manejo de respuestas 401 JSON si el token falta o es inválido.
  - Endpoint `POST /api/v1/orders` con validación de negocio y códigos HTTP 422 (`CUSTOMER_NOT_FOUND`, `PRODUCT_NOT_FOUND`, `INVALID_QUANTITY`, `EMPTY_LINES`).
  - Creación de pedidos en `sale.order` con estado `draft` (Cotización) y respuesta HTTP 201 Created.
  - 15 tests automatizados pasando en verde (100% de éxito, 77% de cobertura total).
- [ ] **Tramo C:** Paginación con metadatos, idempotencia (`Idempotency-Key`), optimización de stock y webhook de entrega.

---

## 2. Cómo Probarlo

### A. Pruebas Automatizadas
Ejecutar la suite completa de pruebas unitarias y de integración desde la raíz del proyecto:

```powershell
$env:PYTHONUTF8=1; python odoo test prueba-tecnica shop_integration_api
```

### B. Pruebas Manuales (cURL / HTTP Client)

#### 1. Autenticación Bearer y Catálogo de Productos (`GET /api/v1/products`)
```bash
# Token válido: Retorna HTTP 200 con el listado JSON
curl -i -H "Authorization: Bearer <TU_API_KEY>" http://localhost:8069/api/v1/products

# Token inválido: Retorna HTTP 401 UNAUTHORIZED en JSON
curl -i -H "Authorization: Bearer token_falso" http://localhost:8069/api/v1/products
```

#### 2. Creación de Pedidos (`POST /api/v1/orders`)
```bash
# Caso Exitoso (HTTP 201 Created):
curl -i -X POST \
  -H "Authorization: Bearer <TU_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"customer_rif": "J-12345678-9", "client_order_ref": "ORD-001", "lines": [{"default_code": "PROD-001", "quantity": 2}]}' \
  http://localhost:8069/api/v1/orders

# Validaciones de Negocio (HTTP 422 Unprocessable Entity):
# - Cliente inexistente: error "CUSTOMER_NOT_FOUND" en campo "customer_rif"
# - Producto inexistente: error "PRODUCT_NOT_FOUND" en campo "lines[i].default_code"
# - Cantidad inválida (<=0): error "INVALID_QUANTITY" en campo "lines[i].quantity"
```

#### 3. Auditoría y Logs (`shop.api.log`)
Cada llamada a los endpoints de la API (exitosa o con error 401, 400, 422) se registra automáticamente en la tabla `shop.api.log` con:
- `name`: Resumen de la llamada (ej. `GET /api/v1/products - 200`).
- `endpoint`: Ruta solicitada.
- `method`: Método HTTP (`GET`, `POST`).
- `status_code`: Código HTTP resultante.
- `duration`: Tiempo de respuesta en segundos medido por el middleware.
- `user_id`: ID del usuario autenticado (o `NULL` si falló la autenticación).
- `remote_addr`: Dirección IP del cliente.
- `request_date`: Marca temporal de la petición.
- **Seguridad:** En ningún caso se almacena el token o API Key en logs ni en texto plano.

---

## 3. Supuestos y Decisiones de Diseño

1. **Modelo `product.product` vs `product.template`:**
   Se expone el modelo `product.product` (variantes vendibles) debido a que es en este nivel donde Odoo gestiona el stock disponible en tiempo real (`qty_available`) y la referencia interna única (`default_code`).
2. **Uso de `child_of` en categorías:**
   Al filtrar por `category_id`, se utiliza el operador `child_of` para que la tienda externa pueda consultar una categoría padre y recibir también los productos de sus subcategorías.
3. **Manejo de Respuestas HTTP en Odoo:**
   Se utiliza `type='http'` con `request.make_json_response()` en lugar de `type='json'`. Esto garantiza que la respuesta sea un JSON REST estándar con códigos de estado HTTP nativos (200, 201, 400, 401, 422), evitando la sobrecarga del protocolo JSON-RPC de Odoo.
4. **Estado Inicial de Pedidos en `draft` (Cotización):**
   Al recibir una compra vía `POST /api/v1/orders`, el pedido se crea deliberadamente en estado `draft` (Cotización) en `sale.order`. Esto permite validación comercial/financiera por parte del equipo interno y previene bloqueos irreversibles o consumos accidentales de inventario antes de confirmar la transacción.
5. **Persistencia Aislada de Logs (`cr` independiente):**
   Para garantizar la trazabilidad de seguridad y técnica ante cualquier excepción o rollback en la transacción del endpoint, el registro en `shop.api.log` se realiza abriendo un cursor de base de datos independiente (`env.registry.cursor()`), asegurando que el log se confirme (commit) en PostgreSQL sin importar el resultado de la transacción principal.
6. **Autenticación con `auth='public'` y decorador `@api_endpoint`:**
   En Odoo, declarar `auth='user'` a nivel de `@http.route` fuerza una redirección HTTP 303 hacia `/web/login` en caso de no existir una cookie de sesión activa de navegador. Para soportar clientes API REST desacoplados que envían cabeceras `Authorization: Bearer <token>` (Tramo B) o sesiones existentes (Tramo A), la ruta se definió con `auth='public'` y la autenticación se delega por completo al decorador `@api_endpoint`.

---

## 4. Limitaciones Conocidas (Tramo A y B)

1. **Paginación:** En el Tramo A y B el catálogo de productos devuelve todos los registros coincidentes sin paginar. La paginación estructurada con metadatos (`total`, `page`, `next`) corresponde al alcance del Tramo C.
2. **Idempotencia de pedidos:** La prevención de pedidos duplicados ante reintentos de red mediante cabecera `Idempotency-Key` está planificada para el Tramo C.
3. **Visibilidad de logs:** El modelo `shop.api.log` no cuenta con menú ni vista en la interfaz de usuario en estos tramos; su consulta se realiza a través de base de datos o en modo técnico.
