{
    "name": "Solicitudes de Pago",
    "version": "18.0.1.1.0",
    "category": "Accounting/Payment",
    "summary": "Gestión de solicitudes de pago a proveedores con flujo de aprobación",
    "author": "Binaural / Abraham David",
    "license": "LGPL-3",
    "depends": [
        "base",
        "mail",
    ],
    "data": [
        "security/payment_request_security.xml",
        "security/ir.model.access.csv",
        "data/ir_sequence_data.xml",
        "views/payment_approval_level_views.xml",
        "wizard/payment_request_reject_wizard_views.xml",
        "views/payment_request_views.xml",
        "views/payment_request_menus.xml",
    ],
    "installable": True,
    "application": True,
}

