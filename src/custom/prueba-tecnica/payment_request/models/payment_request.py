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
    approver_id = fields.Many2one(
        "res.users",
        string="Aprobador asignado",
        readonly=True,
        copy=False,
        tracking=True,
    )
    approved_by_id = fields.Many2one(
        "res.users",
        string="Aprobado por",
        readonly=True,
        copy=False,
    )
    approved_date = fields.Datetime(
        string="Fecha de aprobación",
        readonly=True,
        copy=False,
    )
    payment_id = fields.Many2one(
        "account.payment",
        string="Pago",
        readonly=True,
        copy=False,
        tracking=True,
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
            if not self.env.su and {"approver_id", "approved_by_id", "approved_date", "payment_id"} & vals.keys():
                raise AccessError(_("El aprobador y los datos de aprobación y de pago se asignan automáticamente."))
        return super().create(vals_list)

    def write(self, vals):
        if not self.env.su:
            # 1. State and sequence only change through the action_* methods,
            # which write via super(). The context is client-controlled over
            # RPC, so it must never unlock these fields.
            if "state" in vals:
                raise AccessError(_("El estado de la solicitud no puede modificarse directamente."))

            # 2. Protección contra manipulación manual de la secuencia
            if "name" in vals:
                raise AccessError(_("La secuencia es automática y no puede ser modificada manualmente."))

            # 3. The approver is assigned on submit, the approval data on approve and
            # the payment on pay; nobody may choose or forge them directly.
            if {"approver_id", "approved_by_id", "approved_date", "payment_id"} & vals.keys():
                raise AccessError(_("El aprobador y los datos de aprobación y de pago se asignan automáticamente."))

            # 4. Bloqueo de campos de negocio una vez enviada
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

    def _get_approval_level(self, levels):
        """Return the level with the highest minimum amount not above the request
        amount, comparing in the company currency. ``levels`` is sorted by
        ``min_amount`` descending."""
        self.ensure_one()
        amount = self.currency_id._convert(self.amount, self.company_id.currency_id, self.company_id, self.date)
        return next((level for level in levels if level.min_amount <= amount), levels.browse())

    def action_submit(self):
        levels = self.env["payment.approval.level"].search([])
        for req in self:
            if req.state != "draft":
                raise UserError(_("Solo se pueden enviar solicitudes en estado Borrador."))
            if req.amount <= 0.0:
                raise ValidationError(_("El monto de la solicitud debe ser estrictamente mayor a cero."))
            level = req._get_approval_level(levels)
            if not level:
                raise UserError(_("No hay un nivel de aprobación configurado para este monto. Contacte a Tesorería."))
            seq_name = req.name
            if seq_name == "/":
                seq_name = self.env["ir.sequence"].next_by_code("payment.request") or "/"
            super(PaymentRequest, req).write({
                "name": seq_name,
                "state": "submitted",
                "approver_id": level.approver_id.id,
            })
            req.activity_schedule(
                "mail.mail_activity_data_todo",
                user_id=level.approver_id.id,
                summary=_("Aprobar la solicitud de pago %s", seq_name),
            )

    def action_approve(self):
        for req in self:
            if req.state != "submitted":
                raise UserError(_("Solo se pueden aprobar solicitudes en estado Enviada."))
            if req.approver_id != self.env.user:
                raise AccessError(_("Solo el aprobador asignado a esta solicitud puede aprobarla."))
            super(PaymentRequest, req).write({
                "state": "approved",
                "approved_by_id": self.env.user.id,
                "approved_date": fields.Datetime.now(),
            })
            req.activity_feedback(["mail.mail_activity_data_todo"])

    def action_reject(self, reason=None):
        """Reject with a mandatory reason, posted in the chatter so the applicant
        (a follower since creating the request) is notified of it. Called from the
        reject wizard; the reason is also enforced here so RPC cannot skip it."""
        for req in self:
            if req.state != "submitted":
                raise UserError(_("Solo se pueden rechazar solicitudes en estado Enviada."))
            if req.approver_id != self.env.user:
                raise AccessError(_("Solo el aprobador asignado a esta solicitud puede rechazarla."))
            if not (reason or "").strip():
                raise UserError(_("Debe indicar el motivo del rechazo."))
            super(PaymentRequest, req).write({"state": "rejected"})
            req.message_post(
                body=_("Solicitud rechazada. Motivo: %s", reason.strip()),
                subtype_xmlid="mail.mt_comment",
            )
            req.activity_feedback(["mail.mail_activity_data_todo"])

    def action_pay(self, journal):
        """Create and post the vendor payment of an approved request and link it.
        Called from the pay wizard; the checks are here so RPC cannot skip them."""
        self.ensure_one()
        if not self.env.user.has_group("payment_request.group_payment_request_manager"):
            raise AccessError(_("Solo Tesorería puede pagar solicitudes."))
        if self.payment_id or self.state != "approved":
            raise UserError(_("Solo se pueden pagar solicitudes aprobadas que todavía no tengan pago."))
        payment = self.env["account.payment"].create({
            "payment_type": "outbound",
            "partner_type": "supplier",
            "partner_id": self.partner_id.id,
            "amount": self.amount,
            "currency_id": self.currency_id.id,
            "journal_id": journal.id,
            "memo": self.name,
        })
        payment.action_post()
        super(PaymentRequest, self).write({"state": "paid", "payment_id": payment.id})

    def action_reset_to_draft(self):
        for req in self:
            if req.state != "rejected":
                raise UserError(_("Solo se pueden restablecer a borrador solicitudes rechazadas."))
            super(PaymentRequest, req).write({"state": "draft"})

