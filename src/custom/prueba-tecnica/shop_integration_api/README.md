# Shop Integration API (`shop_integration_api`)

Módulo de integración REST para conectar una tienda en línea externa con Odoo.

---

## 1. Tramos Completados

- [x] **Tramo A:** Endpoint `GET /api/v1/products` con autenticación `auth='user'`.
  - Filtros opcionales: `category_id`, `in_stock`, `updated_since`.
  - Validación de tipos y formato de fecha (error `400 Bad Request` en JSON ante fechas o IDs inválidos, **nunca error 500**).
  - Serialización con `id`, `default_code`, `name`, `list_price` y `qty_available`.
  - Filtrado estricto: solo productos activos (`active=True`) y disponibles para venta (`sale_ok=True`).
  - Pruebas automatizadas de integración HTTP con `HttpCase`.
- [ ] **Tramo B:** Autenticación con API keys nativas (`res.users.apikeys`, Bearer), `POST /api/v1/orders` y log de llamadas.
- [ ] **Tramo C:** Paginación con metadatos, idempotencia (`Idempotency-Key`), optimización de stock y webhook de entrega.

---

## 2. Cómo Probarlo

### A. Pruebas Automatizadas
Ejecutar la suite de pruebas unitarias y de integración desde la raíz del proyecto:

```powershell
$env:PYTHONUTF8=1; python odoo test prueba-tecnica shop_integration_api
```

### B. Pruebas Manuales (cURL / HTTP Client)
Iniciar sesión en Odoo (ej. `http://localhost:8069`) para obtener una cookie de sesión (`session_id`) y ejecutar:

```bash
# 1. Catálogo completo de productos vendibles y activos
curl -X GET "http://localhost:8069/api/v1/products" \
  --cookie "session_id=<TU_SESSION_ID>"

# 2. Filtro combinado: Categoría específica y solo con stock disponible
curl -X GET "http://localhost:8069/api/v1/products?category_id=1&in_stock=true" \
  --cookie "session_id=<TU_SESSION_ID>"

# 3. Filtro por fecha de modificación (ISO 8601)
curl -X GET "http://localhost:8069/api/v1/products?updated_since=2026-10-01T00:00:00" \
  --cookie "session_id=<TU_SESSION_ID>"

# 4. Caso de error controlado: Fecha inválida (devuelve HTTP 400 en JSON, no 500)
curl -X GET "http://localhost:8069/api/v1/products?updated_since=fecha-invalida" \
  --cookie "session_id=<TU_SESSION_ID>"
```

---

## 3. Supuestos y Decisiones de Diseño

1. **Modelo `product.product` vs `product.template`:**
   Se expone el modelo `product.product` (variantes vendibles) debido a que es en este nivel donde Odoo gestiona el stock disponible en tiempo real (`qty_available`) y la referencia interna única (`default_code`).
2. **Uso de `child_of` en categorías:**
   Al filtrar por `category_id`, se utiliza el operador `child_of` para que la tienda externa pueda consultar una categoría padre y recibir también los productos de sus subcategorías.
3. **Manejo de Respuestas HTTP en Odoo:**
   Se utiliza `type='http'` con `request.make_json_response()` en lugar de `type='json'`. Esto garantiza que la respuesta sea un JSON REST estándar con códigos de estado HTTP nativos (200, 400), evitando la sobrecarga del protocolo JSON-RPC de Odoo.

---

## 4. Limitaciones Conocidas

- En este Tramo A, la autenticación depende de una sesión activa de Odoo (`auth='user'`). La autenticación desatendida mediante tokens/API Keys Bearer para sistemas externos será implementada en el Tramo B.

