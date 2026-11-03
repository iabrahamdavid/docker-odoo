import json
from datetime import datetime, timedelta
from odoo.tests.common import HttpCase, tagged


@tagged("post_install", "-at_install", "shop_api")
class TestShopOrderApi(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # 1. Usuario con permisos para crear pedidos y API Key
        cls.api_user = cls.env["res.users"].create({
            "name": "Shop Integration User",
            "login": "shop_user",
            "email": "shop_user@test.com",
            "groups_id": [
                (6, 0, [
                    cls.env.ref("base.group_user").id,
                    cls.env.ref("sales_team.group_sale_salesman").id,
                    cls.env.ref("stock.group_stock_user").id,
                ])
            ],
        })

        # Generar API Key nativa para api_user con fecha de expiración válida
        cls.valid_token = (
            cls.env["res.users.apikeys"]
            .sudo()
            .with_user(cls.api_user)
            ._generate(
                scope="rpc",
                name="Test Shop Key",
                expiration_date=datetime.now() + timedelta(days=30),
            )
        )

        # 2. Cliente con RIF
        cls.partner = cls.env["res.partner"].create({
            "name": "Inversiones Los Andes C.A.",
            "vat": "J-12345678-9",
        })

        # 3. Categoría y producto para pruebas
        cls.category = cls.env["product.category"].create({"name": "Ferretería"})
        cls.product = cls.env["product.product"].create({
            "name": "Martillo Tubular 16oz",
            "default_code": "TOOL-001",
            "list_price": 18.50,
            "sale_ok": True,
            "active": True,
            "categ_id": cls.category.id,
            "is_storable": True,
        })

    def _auth_headers(self, token=None):
        tok = token if token is not None else self.valid_token
        headers = {"Content-Type": "application/json"}
        if tok:
            headers["Authorization"] = f"Bearer {tok}"
        return headers

    def test_01_missing_bearer_token_returns_401(self):
        """Petición sin cabecera Authorization debe devolver 401 UNAUTHORIZED."""
        payload = json.dumps({
            "customer_rif": "J-12345678-9",
            "client_order_ref": "ORDER-001",
            "lines": [{"default_code": "TOOL-001", "quantity": 1}],
        })
        response = self.url_open(
            "/api/v1/orders",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertEqual(data.get("error", {}).get("code"), "UNAUTHORIZED")

    def test_02_invalid_bearer_token_returns_401(self):
        """Petición con token inexistente o expirado debe devolver 401 UNAUTHORIZED."""
        payload = json.dumps({
            "customer_rif": "J-12345678-9",
            "client_order_ref": "ORDER-002",
            "lines": [{"default_code": "TOOL-001", "quantity": 1}],
        })
        response = self.url_open(
            "/api/v1/orders",
            data=payload,
            headers=self._auth_headers(token="token_invalido_totalmente_falso"),
        )
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertEqual(data.get("error", {}).get("code"), "UNAUTHORIZED")

    def test_03_customer_not_found_returns_422(self):
        """Cliente que no existe por VAT debe responder HTTP 422 con código CUSTOMER_NOT_FOUND."""
        payload = json.dumps({
            "customer_rif": "J-99999999-9",
            "client_order_ref": "ORDER-003",
            "lines": [{"default_code": "TOOL-001", "quantity": 2}],
        })
        response = self.url_open(
            "/api/v1/orders",
            data=payload,
            headers=self._auth_headers(),
        )
        self.assertEqual(response.status_code, 422)
        data = response.json()
        self.assertEqual(data.get("error", {}).get("code"), "CUSTOMER_NOT_FOUND")
        self.assertEqual(data.get("error", {}).get("field"), "customer_rif")
        self.assertIn("J-99999999-9", data.get("error", {}).get("message"))

    def test_04_empty_lines_returns_422(self):
        """Pedido sin líneas de producto debe responder HTTP 422 con error en field lines."""
        payload = json.dumps({
            "customer_rif": "J-12345678-9",
            "client_order_ref": "ORDER-004",
            "lines": [],
        })
        response = self.url_open(
            "/api/v1/orders",
            data=payload,
            headers=self._auth_headers(),
        )
        self.assertEqual(response.status_code, 422)
        data = response.json()
        self.assertEqual(data.get("error", {}).get("code"), "EMPTY_LINES")
        self.assertEqual(data.get("error", {}).get("field"), "lines")

    def test_05_product_not_found_returns_422(self):
        """Línea con default_code inexistente debe devolver HTTP 422 indicando el índice exacto."""
        payload = json.dumps({
            "customer_rif": "J-12345678-9",
            "client_order_ref": "ORDER-005",
            "lines": [
                {"default_code": "TOOL-001", "quantity": 2},
                {"default_code": "NO-EXISTE-XYZ", "quantity": 1},
            ],
        })
        response = self.url_open(
            "/api/v1/orders",
            data=payload,
            headers=self._auth_headers(),
        )
        self.assertEqual(response.status_code, 422)
        data = response.json()
        self.assertEqual(data.get("error", {}).get("code"), "PRODUCT_NOT_FOUND")
        self.assertEqual(data.get("error", {}).get("field"), "lines[1].default_code")

    def test_06_invalid_quantity_returns_422(self):
        """Línea con quantity <= 0 debe responder HTTP 422 con código INVALID_QUANTITY."""
        payload = json.dumps({
            "customer_rif": "J-12345678-9",
            "client_order_ref": "ORDER-006",
            "lines": [{"default_code": "TOOL-001", "quantity": 0}],
        })
        response = self.url_open(
            "/api/v1/orders",
            data=payload,
            headers=self._auth_headers(),
        )
        self.assertEqual(response.status_code, 422)
        data = response.json()
        self.assertEqual(data.get("error", {}).get("code"), "INVALID_QUANTITY")
        self.assertEqual(data.get("error", {}).get("field"), "lines[0].quantity")

    def test_07_create_order_success_returns_201(self):
        """Creación exitosa de pedido devuelve HTTP 201 y crea registro sale.order en draft."""
        payload = json.dumps({
            "customer_rif": "J-12345678-9",
            "client_order_ref": "TIENDA-ORD-777",
            "lines": [{"default_code": "TOOL-001", "quantity": 3}],
        })
        response = self.url_open(
            "/api/v1/orders",
            data=payload,
            headers=self._auth_headers(),
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIn("id", data)
        self.assertEqual(data["client_order_ref"], "TIENDA-ORD-777")
        self.assertEqual(data["state"], "draft")
        self.assertGreater(data["amount_total"], 0)

        # Verificar directamente en base de datos
        order = self.env["sale.order"].browse(data["id"])
        self.assertTrue(order.exists())
        self.assertEqual(order.partner_id.id, self.partner.id)
        self.assertEqual(order.client_order_ref, "TIENDA-ORD-777")
        self.assertEqual(order.state, "draft")
        self.assertEqual(len(order.order_line), 1)
        self.assertEqual(order.order_line[0].product_id.id, self.product.id)
        self.assertEqual(order.order_line[0].product_uom_qty, 3.0)

    def test_08_middleware_logs_endpoint_call(self):
        """Verifica que el decorador registre la llamada en shop.api.log."""
        initial_log_count = self.env["shop.api.log"].search_count([("endpoint", "=", "/api/v1/orders")])
        payload = json.dumps({
            "customer_rif": "J-12345678-9",
            "client_order_ref": "TIENDA-ORD-LOG-01",
            "lines": [{"default_code": "TOOL-001", "quantity": 1}],
        })
        response = self.url_open(
            "/api/v1/orders",
            data=payload,
            headers=self._auth_headers(),
        )
        self.assertEqual(response.status_code, 201)

        # Comprobar que se generó un nuevo registro de log
        logs = self.env["shop.api.log"].search(
            [("endpoint", "=", "/api/v1/orders"), ("status_code", "=", 201)],
            order="id desc",
            limit=1,
        )
        self.assertTrue(logs)
        self.assertEqual(logs.method, "POST")
        self.assertEqual(logs.user_id.id, self.api_user.id)
        self.assertGreater(logs.duration, 0.0)

