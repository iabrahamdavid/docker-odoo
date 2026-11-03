import json
from datetime import datetime
from odoo import http
from odoo.http import request
from .auth import api_endpoint


class ShopApiController(http.Controller):

    @http.route(
        "/api/v1/products",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
    )
    @api_endpoint(require_auth=True)
    def get_products(self, **kwargs):
        """Devuelve el catálogo de productos activos para la venta con stock y filtros."""
        domain = [
            ("active", "=", True),
            ("sale_ok", "=", True),
        ]

        # 1. Filtro por categoría (category_id)
        category_id = kwargs.get("category_id")
        if category_id:
            try:
                cat_id = int(category_id)
                domain.append(("categ_id", "child_of", cat_id))
            except ValueError:
                return request.make_json_response(
                    {
                        "error": {
                            "code": "INVALID_CATEGORY_ID",
                            "field": "category_id",
                            "message": "El identificador de categoría debe ser un número entero válido.",
                        }
                    },
                    status=400,
                )

        # 2. Filtro «solo con stock» (in_stock)
        in_stock_raw = kwargs.get("in_stock")
        if in_stock_raw is not None:
            in_stock = str(in_stock_raw).strip().lower() in ("true", "1", "yes")
            if in_stock:
                domain.append(("qty_available", ">", 0))

        # 3. Filtro «modificados desde» (updated_since)
        updated_since_raw = kwargs.get("updated_since")
        if updated_since_raw:
            try:
                # Soporta ISO 8601 (YYYY-MM-DD o YYYY-MM-DDTHH:MM:SS)
                parsed_date = datetime.fromisoformat(updated_since_raw.strip())
                domain.append(("write_date", ">=", parsed_date))
            except (ValueError, TypeError):
                return request.make_json_response(
                    {
                        "error": {
                            "code": "INVALID_DATE_FORMAT",
                            "field": "updated_since",
                            "message": "Formato de fecha inválido. Utilice formato ISO 8601 (ej. YYYY-MM-DD o YYYY-MM-DDTHH:MM:SS).",
                        }
                    },
                    status=400,
                )

        # Buscar productos según dominio
        products = request.env["product.product"].search(domain, order="id asc")

        products_data = [
            {
                "id": product.id,
                "default_code": product.default_code or "",
                "name": product.name,
                "list_price": product.list_price,
                "qty_available": product.qty_available,
            }
            for product in products
        ]

        return request.make_json_response(products_data, status=200)

    @http.route(
        "/api/v1/orders",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
    )
    @api_endpoint(require_auth=True)
    def create_order(self, **kwargs):
        """Crea un pedido de venta (sale.order) en estado draft desde un payload JSON."""
        data = None
        # Intento 1: get_json nativo de Werkzeug
        try:
            data = request.httprequest.get_json(silent=True)
        except Exception:
            pass

        # Intento 2: lectura manual de stream / data
        if data is None:
            try:
                raw_bytes = request.httprequest.get_data() or request.httprequest.data
                raw_text = raw_bytes.decode("utf-8").strip() if raw_bytes else ""
                if raw_text:
                    try:
                        data = json.loads(raw_text)
                    except Exception:
                        if '\\"' in raw_text:
                            data = json.loads(raw_text.replace('\\"', '"'))
                        else:
                            raise
            except Exception:
                pass

        if not data:
            return request.make_json_response(
                {
                    "error": {
                        "code": "INVALID_JSON",
                        "message": "El cuerpo de la petición debe ser un JSON válido.",
                    }
                },
                status=400,
            )

        if not isinstance(data, dict):
            return request.make_json_response(
                {
                    "error": {
                        "code": "INVALID_PAYLOAD",
                        "message": "El payload debe ser un objeto JSON.",
                    }
                },
                status=400,
            )

        # 1. Validación de cliente (customer_rif)
        customer_rif = data.get("customer_rif")
        if not customer_rif or not str(customer_rif).strip():
            return request.make_json_response(
                {
                    "error": {
                        "code": "CUSTOMER_NOT_FOUND",
                        "field": "customer_rif",
                        "message": "El campo customer_rif es requerido.",
                    }
                },
                status=422,
            )

        partner = request.env["res.partner"].search(
            [("vat", "=", str(customer_rif).strip())], limit=1
        )
        if not partner:
            return request.make_json_response(
                {
                    "error": {
                        "code": "CUSTOMER_NOT_FOUND",
                        "field": "customer_rif",
                        "message": f"No existe un cliente con el RIF {customer_rif}",
                    }
                },
                status=422,
            )

        # 2. Validación de referencia externa (client_order_ref)
        client_order_ref = data.get("client_order_ref")
        if not client_order_ref or not str(client_order_ref).strip():
            return request.make_json_response(
                {
                    "error": {
                        "code": "MISSING_FIELD",
                        "field": "client_order_ref",
                        "message": "El campo client_order_ref es requerido.",
                    }
                },
                status=422,
            )

        # 3. Validación de líneas (lines)
        lines = data.get("lines")
        if not lines or not isinstance(lines, list) or len(lines) == 0:
            return request.make_json_response(
                {
                    "error": {
                        "code": "EMPTY_LINES",
                        "field": "lines",
                        "message": "El pedido debe contener al menos una línea de producto.",
                    }
                },
                status=422,
            )

        # 4. Validación de cada línea
        validated_items = []
        for idx, line in enumerate(lines):
            if not isinstance(line, dict):
                return request.make_json_response(
                    {
                        "error": {
                            "code": "INVALID_LINE",
                            "field": f"lines[{idx}]",
                            "message": "Cada línea debe ser un objeto con default_code y quantity.",
                        }
                    },
                    status=422,
                )

            code = line.get("default_code")
            if not code or not str(code).strip():
                return request.make_json_response(
                    {
                        "error": {
                            "code": "PRODUCT_NOT_FOUND",
                            "field": f"lines[{idx}].default_code",
                            "message": "No existe un producto con el código especificado.",
                        }
                    },
                    status=422,
                )

            product = request.env["product.product"].search(
                [("default_code", "=", str(code).strip())], limit=1
            )
            if not product:
                return request.make_json_response(
                    {
                        "error": {
                            "code": "PRODUCT_NOT_FOUND",
                            "field": f"lines[{idx}].default_code",
                            "message": f"No existe un producto con el código {code}",
                        }
                    },
                    status=422,
                )

            raw_qty = line.get("quantity")
            try:
                quantity = float(raw_qty) if raw_qty is not None else 0.0
            except (ValueError, TypeError):
                quantity = 0.0

            if quantity <= 0:
                return request.make_json_response(
                    {
                        "error": {
                            "code": "INVALID_QUANTITY",
                            "field": f"lines[{idx}].quantity",
                            "message": "La cantidad del producto debe ser mayor a cero.",
                        }
                    },
                    status=422,
                )

            validated_items.append({"product": product, "quantity": quantity})

        # 5. Creación de sale.order en estado draft (Cotización)
        order_lines = [
            (
                0,
                0,
                {
                    "product_id": item["product"].id,
                    "product_uom_qty": item["quantity"],
                },
            )
            for item in validated_items
        ]

        order = request.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "client_order_ref": str(client_order_ref).strip(),
                "order_line": order_lines,
            }
        )

        return request.make_json_response(
            {
                "id": order.id,
                "name": order.name,
                "client_order_ref": order.client_order_ref,
                "amount_total": round(order.amount_total, 2),
                "state": order.state,
            },
            status=201,
        )

