from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPaymentRequest(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.partner_a = cls.env["res.partner"].create({"name": "Proveedor Central C.A."})
        cls.partner_b = cls.env["res.partner"].create({"name": "Distribuciones Los Andes"})

        # Grupos de seguridad
        cls.group_user = cls.env.ref("payment_request.group_payment_request_user")
        cls.group_approver = cls.env.ref("payment_request.group_payment_request_approver")

        # Usuarios de prueba
        cls.user_applicant_1 = cls.env["res.users"].create({
            "name": "Solicitante Uno",
            "login": "applicant_1",
            "groups_id": [(6, 0, [cls.group_user.id])],
        })

        cls.user_applicant_2 = cls.env["res.users"].create({
            "name": "Solicitante Dos",
            "login": "applicant_2",
            "groups_id": [(6, 0, [cls.group_user.id])],
        })

        cls.user_approver = cls.env["res.users"].create({
            "name": "Gerente Aprobador",
            "login": "approver_1",
            "groups_id": [(6, 0, [cls.group_approver.id])],
        })

    def _create_request(self, user=None, **kwargs):
        env = self.env(user=user) if user else self.env
        values = {
            "partner_id": self.partner_a.id,
            "amount": 250.0,
            "concept": "Pago de servicios profesionales de consultoría",
        }
        values.update(kwargs)
        return env["payment.request"].create(values)

    def test_01_create_defaults_and_sequence_on_submit(self):
        """Verifica valores por defecto en borrador y asignación de secuencia al enviar."""
        req = self._create_request(user=self.user_applicant_1)
        self.assertEqual(req.state, "draft")
        self.assertEqual(req.name, "/")
        self.assertEqual(req.applicant_id, self.user_applicant_1)

        req.action_submit()
        self.assertEqual(req.state, "submitted")
        self.assertTrue(req.name.startswith("SP/"))
        self.assertNotEqual(req.name, "/")
        self.assertIn(self.partner_a.name, req.display_name)

    def test_02_negative_or_zero_amount_forbidden(self):
        """Verifica que montos <= 0 sean rechazados por constraint."""
        with self.assertRaises(ValidationError):
            self._create_request(amount=0.0)

        with self.assertRaises(ValidationError):
            self._create_request(amount=-150.0)

        req = self._create_request(amount=100.0)
        with self.assertRaises(ValidationError):
            req.write({"amount": 0.0})

    def test_03_submitted_request_cannot_be_edited(self):
        """Verifica que una solicitud enviada no pueda ser modificada."""
        req = self._create_request(user=self.user_applicant_1, amount=300.0)
        req.write({"concept": "Concepto corregido en borrador"})
        self.assertEqual(req.concept, "Concepto corregido en borrador")

        req.action_submit()
        self.assertEqual(req.state, "submitted")

        with self.assertRaises(UserError):
            req.with_user(self.user_applicant_1).write({"amount": 500.0})

        with self.assertRaises(UserError):
            req.with_user(self.user_applicant_1).write({"concept": "Intento de cambio fraudulento"})

        with self.assertRaises(UserError):
            req.with_user(self.user_applicant_1).write({"partner_id": self.partner_b.id})

    def test_04_applicant_cannot_approve_or_reject(self):
        """Verifica que el solicitante no pueda aprobar ni rechazar (ni UI ni ORM)."""
        req = self._create_request(user=self.user_applicant_1)
        req.action_submit()

        # Intento de aprobación por solicitante debe lanzar AccessError
        with self.assertRaises(AccessError):
            req.with_user(self.user_applicant_1).action_approve()

        # Intento de rechazo por solicitante debe lanzar AccessError
        with self.assertRaises(AccessError):
            req.with_user(self.user_applicant_1).action_reject()

    def test_05_approver_can_approve_and_reject(self):
        """Verifica que un usuario aprobador pueda aprobar y rechazar solicitudes enviadas."""
        req = self._create_request(user=self.user_applicant_1)

        # No se puede aprobar en borrador
        with self.assertRaises(UserError):
            req.with_user(self.user_approver).action_approve()

        req.action_submit()
        self.assertEqual(req.state, "submitted")

        # Aprobación exitosa
        req.with_user(self.user_approver).action_approve()
        self.assertEqual(req.state, "approved")

        # Flujo de rechazo en otra solicitud
        req_2 = self._create_request(user=self.user_applicant_1)
        req_2.action_submit()
        req_2.with_user(self.user_approver).action_reject()
        self.assertEqual(req_2.state, "rejected")

    def test_06_reset_to_draft(self):
        """Verifica que una solicitud rechazada pueda ser restablecida a borrador para corrección."""
        req = self._create_request(user=self.user_applicant_1)
        req.action_submit()
        req.with_user(self.user_approver).action_reject()
        self.assertEqual(req.state, "rejected")

        # Restablecer a borrador
        req.action_reset_to_draft()
        self.assertEqual(req.state, "draft")

        # Modificación permitida nuevamente en borrador
        req.write({"amount": 450.0})
        self.assertEqual(req.amount, 450.0)

    def test_07_record_rules_applicant_isolation(self):
        """Verifica que cada solicitante solo vea sus propias solicitudes y el aprobador todas."""
        req_1 = self._create_request(user=self.user_applicant_1, concept="Solicitud de User 1")
        req_2 = self._create_request(user=self.user_applicant_2, concept="Solicitud de User 2")

        # Búsqueda como solicitante 1
        reqs_user_1 = self.env["payment.request"].with_user(self.user_applicant_1).search([])
        self.assertIn(req_1, reqs_user_1)
        self.assertNotIn(req_2, reqs_user_1)

        # Búsqueda como solicitante 2
        reqs_user_2 = self.env["payment.request"].with_user(self.user_applicant_2).search([])
        self.assertIn(req_2, reqs_user_2)
        self.assertNotIn(req_1, reqs_user_2)

        # Búsqueda como aprobador (debe ver ambas)
        reqs_approver = self.env["payment.request"].with_user(self.user_approver).search([])
        self.assertIn(req_1, reqs_approver)
        self.assertIn(req_2, reqs_approver)

    def test_08_unlink_restrictions(self):
        """Verifica las reglas de borrado: solo permitido en draft y rejected."""
        req = self._create_request(user=self.user_applicant_1)
        req_id = req.id
        req.unlink()
        self.assertFalse(self.env["payment.request"].browse(req_id).exists())

        req_submitted = self._create_request(user=self.user_applicant_1)
        req_submitted.action_submit()
        with self.assertRaises(UserError):
            req_submitted.unlink()

        req_approved = self._create_request(user=self.user_applicant_1)
        req_approved.action_submit()
        req_approved.with_user(self.user_approver).action_approve()
        with self.assertRaises(UserError):
            req_approved.unlink()

