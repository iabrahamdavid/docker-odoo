from datetime import datetime
from odoo import http
from odoo.http import request


class ShopProductApiController(http.Controller):

    @http.route(
        "/api/v1/products",
        type="http",
        auth="user",
        methods=["GET"],
        csrf=False,
    )
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

