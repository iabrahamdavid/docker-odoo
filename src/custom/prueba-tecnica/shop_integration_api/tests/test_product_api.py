from datetime import datetime, timedelta
from odoo.tests.common import HttpCase, tagged


@tagged("post_install", "-at_install", "shop_api")
class TestShopProductApi(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # 1. Usuario para autenticación de sesión (auth='user' con acceso de ventas)
        cls.api_user = cls.env["res.users"].create({
            "name": "API User",
            "login": "api_user",
            "email": "api_user@test.com",
            "groups_id": [
                (6, 0, [
                    cls.env.ref("base.group_user").id,
                    cls.env.ref("sales_team.group_sale_salesman").id,
                    cls.env.ref("stock.group_stock_user").id,
                ])
            ],
        })
        cls.api_user.password = "api_secret_123"

        # 2. Categorías de prueba
        cls.category_tech = cls.env["product.category"].create({"name": "Tecnología"})
        cls.category_home = cls.env["product.category"].create({"name": "Hogar"})

        # 3. Ubicación interna para stock
        cls.stock_location = cls.env.ref("stock.stock_location_stock")

        # 4. Productos
        # Producto 1: Tecnología, vendible, activo, con stock (almacenable en Odoo 18)
        cls.product_mouse = cls.env["product.product"].create({
            "name": "Ratón Óptico",
            "default_code": "TECH-001",
            "list_price": 25.50,
            "sale_ok": True,
            "active": True,
            "categ_id": cls.category_tech.id,
            "is_storable": True,
        })
        # Asignar stock al producto 1
        cls.env["stock.quant"]._update_available_quantity(
            cls.product_mouse, cls.stock_location, 15.0
        )

        # Producto 2: Hogar, vendible, activo, almacenable sin stock (0 disponible)
        cls.product_lamp = cls.env["product.product"].create({
            "name": "Lámpara de Mesa",
            "default_code": "HOME-001",
            "list_price": 45.00,
            "sale_ok": True,
            "active": True,
            "categ_id": cls.category_home.id,
            "is_storable": True,
        })

        # Producto 3: Inactivo (no debe aparecer)
        cls.product_inactive = cls.env["product.product"].create({
            "name": "Producto Descontinuado",
            "default_code": "DISC-001",
            "list_price": 5.00,
            "sale_ok": True,
            "active": False,
            "categ_id": cls.category_tech.id,
        })

        # Producto 4: No vendible (sale_ok=False, no debe aparecer)
        cls.product_internal = cls.env["product.product"].create({
            "name": "Materia Prima Interna",
            "default_code": "RAW-001",
            "list_price": 10.00,
            "sale_ok": False,
            "active": True,
            "categ_id": cls.category_tech.id,
        })

    def setUp(self):
        super().setUp()
        self.authenticate("api_user", "api_secret_123")

    def test_01_get_products_base(self):
        """Verifica que devuelve productos activos y vendibles, excluyendo inactivos y no vendibles."""
        res = self.url_open("/api/v1/products")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIsInstance(data, list)

        product_codes = [p["default_code"] for p in data]
        self.assertIn("TECH-001", product_codes)
        self.assertIn("HOME-001", product_codes)
        self.assertNotIn("DISC-001", product_codes)
        self.assertNotIn("RAW-001", product_codes)

        # Validar estructura del producto
        mouse = next(p for p in data if p["default_code"] == "TECH-001")
        self.assertEqual(mouse["name"], "Ratón Óptico")
        self.assertEqual(mouse["list_price"], 25.50)
        self.assertGreaterEqual(mouse["qty_available"], 15.0)

    def test_02_filter_category(self):
        """Verifica el filtro por categoría."""
        url = f"/api/v1/products?category_id={self.category_tech.id}"
        res = self.url_open(url)
        self.assertEqual(res.status_code, 200)
        data = res.json()

        codes = [p["default_code"] for p in data]
        self.assertIn("TECH-001", codes)
        self.assertNotIn("HOME-001", codes)

    def test_03_filter_in_stock(self):
        """Verifica el filtro «solo con stock»."""
        res = self.url_open("/api/v1/products?in_stock=true")
        self.assertEqual(res.status_code, 200)
        data = res.json()

        codes = [p["default_code"] for p in data]
        self.assertIn("TECH-001", codes)
        self.assertNotIn("HOME-001", codes)

    def test_04_filter_updated_since(self):
        """Verifica el filtro por fecha de modificación."""
        past_date = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
        res = self.url_open(f"/api/v1/products?updated_since={past_date}")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        codes = [p["default_code"] for p in data]
        self.assertIn("TECH-001", codes)

    def test_05_filters_combined(self):
        """Verifica el funcionamiento de filtros combinados (categoría + stock)."""
        # Categoría Tecnología + in_stock=true -> TECH-001
        url = f"/api/v1/products?category_id={self.category_tech.id}&in_stock=true"
        res = self.url_open(url)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        codes = [p["default_code"] for p in data]
        self.assertEqual(codes, ["TECH-001"])

        # Categoría Hogar + in_stock=true -> Vacío (Lámpara tiene 0 de stock)
        url_empty = f"/api/v1/products?category_id={self.category_home.id}&in_stock=true"
        res_empty = self.url_open(url_empty)
        self.assertEqual(res_empty.status_code, 200)
        self.assertEqual(res_empty.json(), [])

    def test_06_invalid_date_format_returns_400(self):
        """Una fecha mal formateada debe devolver error claro 400 en JSON, nunca error 500."""
        res = self.url_open("/api/v1/products?updated_since=fecha-invalida-123")
        self.assertEqual(res.status_code, 400)
        data = res.json()
        self.assertIn("error", data)
        self.assertEqual(data["error"]["code"], "INVALID_DATE_FORMAT")
        self.assertEqual(data["error"]["field"], "updated_since")

    def test_07_invalid_category_returns_400(self):
        """Un category_id no numérico debe devolver error 400."""
        res = self.url_open("/api/v1/products?category_id=no-es-numero")
        self.assertEqual(res.status_code, 400)
        data = res.json()
        self.assertIn("error", data)
        self.assertEqual(data["error"]["code"], "INVALID_CATEGORY_ID")

