from odoo import fields, models


class PaymentApprovalLevel(models.Model):
    _name = "payment.approval.level"
    _description = "Nivel de Aprobación de Solicitudes de Pago"
    _order = "min_amount desc"
    _rec_name = "approver_id"

    min_amount = fields.Monetary(
        string="Monto mínimo",
        required=True,
        currency_field="currency_id",
        help="Las solicitudes cuyo monto, en la moneda de la compañía, sea igual o mayor "
        "a este valor (y menor que el del siguiente nivel) las aprueba este aprobador.",
    )
    approver_id = fields.Many2one(
        "res.users",
        string="Aprobador",
        required=True,
        domain=lambda self: [("groups_id", "in", self.env.ref("payment_request.group_payment_request_approver").id)],
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Moneda",
        required=True,
        readonly=True,
        default=lambda self: self.env.company.currency_id,
    )
