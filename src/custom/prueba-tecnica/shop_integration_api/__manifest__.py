{
    "name": "Shop Integration API",
    "version": "18.0.1.0.0",
    "category": "Sales",
    "summary": "API REST para integración con tienda en línea externa",
    "description": """
Shop Integration API
====================
Módulo de integración REST que permite a una tienda en línea externa:
- Consultar el catálogo de productos con stock disponible y filtros avanzados.
- Crear pedidos de venta en Odoo (próximos tramos).
    """,
    "author": "Binaural / Abraham David",
    "depends": [
        "base",
        "sale_management",
        "stock",
    ],
    "data": [],
    "installable": True,
    "application": True,
    "license": "LGPL-3",
}

