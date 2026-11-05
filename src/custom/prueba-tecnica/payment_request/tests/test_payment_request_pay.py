from odoo.exceptions import AccessError, UserError
from odoo.tests import Form, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestPaymentRequestPay(AccountTestInvoicingCommon):
    """Tramo B: pago de la solicitud con account.payment de proveedor."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        group = lambda xmlid: cls.env.ref(f"payment_request.{xmlid}")
        cls.applicant = cls._create_user("applicant", group("group_payment_request_user"))
        cls.approver = cls._create_user("approver", group("group_payment_request_approver"))
        cls.treasury = cls._create_user("treasury", group("group_payment_request_manager"))
        # Los niveles los configura Tesorería (el usuario de AccountTestInvoicingCommon no puede)
        cls.env["payment.approval.level"].with_user(cls.treasury).create(
            {"min_amount": 0.0, "approver_id": cls.approver.id}
        )
        cls.vendor = cls.env["res.partner"].create({"name": "Proveedor de Pago C.A."})
        cls.bank_journal = cls.company_data["default_journal_bank"]

    @classmethod
    def _create_user(cls, login, group):
        return cls.env["res.users"].create({
            "name": login.capitalize(),
            "login": f"pr_{login}",
            "email": f"pr_{login}@example.com",
            "groups_id": [(6, 0, [group.id])],
        })

    def _approved_request(self, amount=350.0):
        req = self.env["payment.request"].with_user(self.applicant).create({
            "partner_id": self.vendor.id,
            "amount": amount,
            "currency_id": self.env.company.currency_id.id,
            "concept": "Pago a proveedor",
        })
        req.action_submit()
        req.with_user(self.approver).action_approve()
        return req

    def _pay_with_wizard(self, req, user):
        form = Form(self.env(user=user, context={"default_request_id": req.id})["payment.request.pay.wizard"])
        form.journal_id = self.bank_journal
        form.save().action_confirm()

    def test_01_pay_creates_posted_vendor_payment_linked(self):
        """Tesorería paga con el wizard: pago de proveedor publicado y vinculado a la solicitud."""
        req = self._approved_request()
        self._pay_with_wizard(req, self.treasury)

        payment = req.payment_id
        self.assertEqual(req.state, "paid")
        self.assertTrue(payment)
        self.assertEqual(payment.payment_type, "outbound")
        self.assertEqual(payment.partner_type, "supplier")
        self.assertEqual(payment.partner_id, self.vendor)
        self.assertEqual(payment.amount, req.amount)
        self.assertEqual(payment.currency_id, req.currency_id)
        self.assertEqual(payment.journal_id, self.bank_journal)
        self.assertEqual(payment.memo, req.name)
        self.assertNotEqual(payment.state, "draft", "el pago queda publicado en contabilidad")
        self.assertTrue(payment.move_id)

    def test_02_request_cannot_be_paid_twice(self):
        """Una solicitud pagada no se puede volver a pagar: sigue habiendo un único pago."""
        req = self._approved_request()
        self._pay_with_wizard(req, self.treasury)
        first_payment = req.payment_id

        with self.assertRaises(UserError):
            self._pay_with_wizard(req, self.treasury)
        with self.assertRaises(UserError):
            req.with_user(self.treasury).action_pay(self.bank_journal)

        self.assertEqual(req.payment_id, first_payment)
        self.assertEqual(self.env["account.payment"].search_count([("memo", "=", req.name)]), 1)

    def test_03_only_treasury_pays_only_approved_requests(self):
        """Un aprobador no puede pagar, y no se puede pagar una solicitud sin aprobar."""
        req = self._approved_request()
        with self.assertRaises(AccessError):
            req.with_user(self.approver).action_pay(self.bank_journal)

        submitted = self.env["payment.request"].with_user(self.applicant).create({
            "partner_id": self.vendor.id, "amount": 80.0, "concept": "Sin aprobar",
        })
        submitted.action_submit()
        with self.assertRaises(UserError):
            submitted.with_user(self.treasury).action_pay(self.bank_journal)
        self.assertFalse(submitted.payment_id)

    def test_04_applicant_sees_payment_on_paid_request(self):
        """El solicitante, sin permisos contables, ve el pago desde su solicitud."""
        req = self._approved_request()
        self._pay_with_wizard(req, self.treasury)

        self.assertFalse(self.applicant.has_group("account.group_account_invoice"))
        data = req.with_user(self.applicant).web_read({
            "state": {},
            "payment_id": {"fields": {"display_name": {}}},
        })[0]
        self.assertEqual(data["state"], "paid")
        self.assertEqual(data["payment_id"]["id"], req.payment_id.id)
