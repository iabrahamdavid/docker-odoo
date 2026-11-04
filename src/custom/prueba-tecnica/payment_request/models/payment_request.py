from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError


class PaymentRequest(models.Model):
    _name = "payment.request"
    _description = "Solicitud de Pago"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "id desc"

    name = fields.Char(
        string="Secuencia",
        required=True,
        copy=False,
        readonly=True,
        default="/",
        tracking=True,
    )
    partner_id = fields.Many2one(
        "res.partner",
        string="Proveedor",
        required=True,
        tracking=True,
    )
    applicant_id = fields.Many2one(
        "res.users",
        string="Solicitante",
        required=True,
        default=lambda self: self.env.user,
        tracking=True,
    )
    amount = fields.Monetary(
        string="Monto",
        required=True,
        currency_field="currency_id",
        tracking=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        string="Moneda",
        required=True,
        default=lambda self: self.env.company.currency_id,
    )
    date = fields.Date(
        string="Fecha",
        required=True,
        default=fields.Date.context_today,
    )
    concept = fields.Text(
        string="Concepto",
        required=True,
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Borrador"),
            ("submitted", "Enviada"),
            ("approved", "Aprobada"),
            ("paid", "Pagada"),
            ("rejected", "Rechazada"),
        ],
        string="Estado",
        default="draft",
        required=True,
        copy=False,
        tracking=True,
    )
    company_id = fields.Many2one(
        "res.company",
        string="Compañía",
        required=True,
        default=lambda self: self.env.company,
    )

    def _compute_display_name(self):
        for req in self:
            partner_name = req.partner_id.name if req.partner_id else ""
            req.display_name = f"{req.name} - {partner_name}" if partner_name else req.name

    @api.constrains("amount")
    def _check_amount(self):
        for req in self:
            if req.amount <= 0.0:
                raise ValidationError(_("El monto de la solicitud debe ser estrictamente mayor a cero."))

    def write(self, vals):
        if not self.env.su:
            restricted_fields = {
                "partner_id",
                "applicant_id",
                "amount",
                "currency_id",
                "date",
                "concept",
                "company_id",
            }
            if any(field in vals for field in restricted_fields):
                for req in self:
                    if req.state != "draft":
                        raise UserError(_("No puede modificar una solicitud que ya ha sido enviada o procesada."))
        return super().write(vals)

    def unlink(self):
        for req in self:
            if req.state not in ("draft", "rejected"):
                raise UserError(_("Solo se pueden eliminar solicitudes en estado borrador o rechazada."))
        return super().unlink()

    def action_submit(self):
        for req in self:
            if req.state != "draft":
                raise UserError(_("Solo se pueden enviar solicitudes en estado Borrador."))
            if req.amount <= 0.0:
                raise ValidationError(_("El monto de la solicitud debe ser estrictamente mayor a cero."))
            if req.name == "/":
                req.name = self.env["ir.sequence"].next_by_code("payment.request") or "/"
            req.state = "submitted"

    def action_approve(self):
        if not self.env.user.has_group("payment_request.group_payment_request_approver"):
            raise AccessError(_("Solo los usuarios autorizados como Aprobadores pueden aprobar solicitudes de pago."))
        for req in self:
            if req.state != "submitted":
                raise UserError(_("Solo se pueden aprobar solicitudes en estado Enviada."))
            req.state = "approved"

    def action_reject(self):
        if not self.env.user.has_group("payment_request.group_payment_request_approver"):
            raise AccessError(_("Solo los usuarios autorizados como Aprobadores pueden rechazar solicitudes de pago."))
        for req in self:
            if req.state != "submitted":
                raise UserError(_("Solo se pueden rechazar solicitudes en estado Enviada."))
            req.state = "rejected"

    def action_reset_to_draft(self):
        for req in self:
            if req.state != "rejected":
                raise UserError(_("Solo se pueden restablecer a borrador solicitudes rechazadas."))
            req.state = "draft"

