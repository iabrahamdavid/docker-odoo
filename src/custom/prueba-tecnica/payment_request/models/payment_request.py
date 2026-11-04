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

    @api.model_create_multi
    def create(self, vals_list):
        is_approver = self.env.user.has_group("payment_request.group_payment_request_approver")
        for vals in vals_list:
            if not self.env.su and not is_approver:
                if vals.get("state") and vals["state"] != "draft":
                    raise AccessError(_("No tiene autorización para crear solicitudes en un estado diferente a borrador."))
                if vals.get("name") and vals["name"] != "/":
                    raise AccessError(_("La secuencia de la solicitud es automática y no puede ser manipulada manualmente."))
        return super().create(vals_list)

    def write(self, vals):
        if not self.env.su:
            is_approver = self.env.user.has_group("payment_request.group_payment_request_approver")

            # 1. Protección contra manipulación directa de estado
            if "state" in vals:
                if not self.env.context.get("allow_state_transition") and not is_approver:
                    raise AccessError(_("El estado de la solicitud no puede modificarse directamente."))
                if vals["state"] in ("approved", "paid") and not is_approver:
                    raise AccessError(_("Solo los usuarios autorizados como Aprobadores pueden aprobar o procesar solicitudes."))

            # 2. Protección contra manipulación manual de la secuencia
            if "name" in vals and not self.env.context.get("system_sequence") and not is_approver:
                raise AccessError(_("La secuencia es automática y no puede ser modificada manualmente."))

            # 3. Bloqueo de campos de negocio una vez enviada
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
            seq_name = req.name
            if seq_name == "/":
                seq_name = self.env["ir.sequence"].next_by_code("payment.request") or "/"
            req.with_context(allow_state_transition=True, system_sequence=True).write({
                "name": seq_name,
                "state": "submitted",
            })

    def action_approve(self):
        if not self.env.user.has_group("payment_request.group_payment_request_approver"):
            raise AccessError(_("Solo los usuarios autorizados como Aprobadores pueden aprobar solicitudes de pago."))
        for req in self:
            if req.state != "submitted":
                raise UserError(_("Solo se pueden aprobar solicitudes en estado Enviada."))
            req.with_context(allow_state_transition=True).write({"state": "approved"})

    def action_reject(self):
        if not self.env.user.has_group("payment_request.group_payment_request_approver"):
            raise AccessError(_("Solo los usuarios autorizados como Aprobadores pueden rechazar solicitudes de pago."))
        for req in self:
            if req.state != "submitted":
                raise UserError(_("Solo se pueden rechazar solicitudes en estado Enviada."))
            req.with_context(allow_state_transition=True).write({"state": "rejected"})

    def action_reset_to_draft(self):
        for req in self:
            if req.state != "rejected":
                raise UserError(_("Solo se pueden restablecer a borrador solicitudes rechazadas."))
            req.with_context(allow_state_transition=True).write({"state": "draft"})

