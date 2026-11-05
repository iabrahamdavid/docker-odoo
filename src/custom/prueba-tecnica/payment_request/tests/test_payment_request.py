from odoo import fields
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import Form
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
            "email": "applicant_1@example.com",
            "groups_id": [(6, 0, [cls.group_user.id])],
        })

        cls.user_applicant_2 = cls.env["res.users"].create({
            "name": "Solicitante Dos",
            "login": "applicant_2",
            "email": "applicant_2@example.com",
            "groups_id": [(6, 0, [cls.group_user.id])],
        })

        cls.user_approver = cls.env["res.users"].create({
            "name": "Gerente Aprobador",
            "login": "approver_1",
            "email": "approver_1@example.com",
            "groups_id": [(6, 0, [cls.group_approver.id])],
        })

        # Un nivel desde 0 para que toda solicitud tenga aprobador asignado al enviarse
        cls.env["payment.approval.level"].create({"min_amount": 0.0, "approver_id": cls.user_approver.id})

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

        # Intento de aprobación por solicitante llamando al método debe lanzar AccessError
        with self.assertRaises(AccessError):
            req.with_user(self.user_applicant_1).action_approve()

        # Intento de rechazo por solicitante llamando al método debe lanzar AccessError
        with self.assertRaises(AccessError):
            req.with_user(self.user_applicant_1).action_reject()

        # Intento de bypass mediante write directo de state debe lanzar AccessError
        with self.assertRaises(AccessError):
            req.with_user(self.user_applicant_1).write({"state": "approved"})

        with self.assertRaises(AccessError):
            req.with_user(self.user_applicant_1).write({"state": "paid"})

        # Intento de creación directa en estado aprobado debe lanzar AccessError
        with self.assertRaises(AccessError):
            self.env["payment.request"].with_user(self.user_applicant_1).create({
                "partner_id": self.partner_a.id,
                "amount": 100.0,
                "concept": "Intento de autoaprobación en create",
                "state": "approved",
            })

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
        req_2.with_user(self.user_approver).action_reject("Falta la factura del proveedor")
        self.assertEqual(req_2.state, "rejected")

    def test_06_reset_to_draft(self):
        """Verifica que una solicitud rechazada pueda ser restablecida a borrador para corrección."""
        req = self._create_request(user=self.user_applicant_1)
        req.action_submit()
        req.with_user(self.user_approver).action_reject("Monto incorrecto")
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

    def test_09_context_cannot_bypass_workflow(self):
        """Un solicitante no puede reabrir ni renumerar una solicitud enviada
        inyectando claves de contexto por RPC."""
        req = self._create_request(user=self.user_applicant_1, amount=300.0)
        req.action_submit()
        number = req.name
        forged = req.with_user(self.user_applicant_1).with_context(
            allow_state_transition=True, system_sequence=True,
        )

        with self.assertRaises(AccessError):
            forged.write({"state": "draft"})
        with self.assertRaises(AccessError):
            forged.write({"name": "SP/0000/9999"})

        self.assertEqual(req.state, "submitted")
        self.assertEqual(req.name, number)

    # ------------------------------------------------------------------
    # Tramo B: niveles de aprobación y aprobador asignado
    # ------------------------------------------------------------------

    def _create_management_level(self):
        """Segundo nivel: desde 10.000 aprueba gerencia (otro usuario aprobador)."""
        manager = self.env["res.users"].create({
            "name": "Gerencia General",
            "login": "approver_2",
            "email": "approver_2@example.com",
            "groups_id": [(6, 0, [self.group_approver.id])],
        })
        self.env["payment.approval.level"].create({"min_amount": 10000.0, "approver_id": manager.id})
        return manager

    def test_10_approver_assigned_by_amount(self):
        """Al enviar se asigna el nivel con mayor monto mínimo que no supere el monto."""
        manager = self._create_management_level()
        for amount, expected in ((500.0, self.user_approver), (10000.0, manager), (15000.0, manager)):
            req = self._create_request(user=self.user_applicant_1, amount=amount)
            req.action_submit()
            self.assertEqual(req.approver_id, expected, f"monto {amount}")

    def test_11_submit_creates_activity_for_assigned_approver(self):
        """El envío, hecho por el solicitante, crea una actividad para el aprobador asignado."""
        req = self._create_request(user=self.user_applicant_1)
        req.action_submit()
        self.assertEqual(req.activity_ids.user_id, self.user_approver)
        self.assertEqual(req.activity_ids.activity_type_id, self.env.ref("mail.mail_activity_data_todo"))

    def test_12_submit_without_applicable_level_fails(self):
        """Sin un nivel que cubra el monto, la solicitud no se puede enviar."""
        self.env["payment.approval.level"].search([]).unlink()
        req = self._create_request(user=self.user_applicant_1)
        with self.assertRaises(UserError):
            req.action_submit()
        self.assertEqual(req.state, "draft")

    def test_13_only_assigned_approver_can_approve(self):
        """Otro aprobador no puede aprobar; el asignado sí, y quedan quién y cuándo."""
        manager = self._create_management_level()
        req = self._create_request(user=self.user_applicant_1, amount=500.0)
        req.action_submit()
        self.assertEqual(req.approver_id, self.user_approver)

        with self.assertRaises(AccessError):
            req.with_user(manager).action_approve()
        self.assertEqual(req.state, "submitted")

        req.with_user(self.user_approver).action_approve()
        self.assertEqual(req.state, "approved")
        self.assertEqual(req.approved_by_id, self.user_approver)
        self.assertTrue(req.approved_date)
        self.assertFalse(req.activity_ids, "la actividad de aprobación se cierra al aprobar")

    def test_14_approval_fields_cannot_be_forged(self):
        """El solicitante no puede elegir su aprobador ni falsear los datos de aprobación."""
        req = self._create_request(user=self.user_applicant_1)
        as_applicant = req.with_user(self.user_applicant_1)
        with self.assertRaises(AccessError):
            as_applicant.write({"approver_id": self.user_applicant_1.id})
        with self.assertRaises(AccessError):
            as_applicant.write({"approved_by_id": self.user_approver.id})
        with self.assertRaises(AccessError):
            self._create_request(user=self.user_applicant_1, approver_id=self.user_applicant_1.id)

    # ------------------------------------------------------------------
    # Tramo B: rechazo con motivo
    # ------------------------------------------------------------------

    def test_15_reject_wizard_requires_reason_and_posts_it(self):
        """El wizard exige el motivo y lo publica en el chatter, notificando al solicitante."""
        req = self._create_request(user=self.user_applicant_1)
        req.action_submit()
        wizard_env = self.env(user=self.user_approver, context={"default_request_id": req.id})

        form = Form(wizard_env["payment.request.reject.wizard"])
        with self.assertRaises(AssertionError):
            form.save()  # el motivo es obligatorio

        form.reason = "Falta la factura del proveedor"
        form.save().action_confirm()

        self.assertEqual(req.state, "rejected")
        message = req.message_ids.filtered(lambda m: "Falta la factura del proveedor" in (m.body or ""))
        self.assertTrue(message, "el motivo queda en el chatter")
        self.assertIn(self.user_applicant_1.partner_id, message.notified_partner_ids)
        self.assertFalse(req.activity_ids, "la actividad de aprobación se cierra al rechazar")

    def test_16_reject_without_reason_or_by_other_approver_fails(self):
        """Sin el wizard tampoco se puede rechazar sin motivo, ni puede hacerlo otro aprobador."""
        manager = self._create_management_level()
        req = self._create_request(user=self.user_applicant_1, amount=500.0)
        req.action_submit()
        as_assigned = req.with_user(self.user_approver)

        for reason in (None, "", "   "):
            with self.assertRaises(UserError):
                as_assigned.action_reject(reason)
        with self.assertRaises(AccessError):
            req.with_user(manager).action_reject("Motivo de otro aprobador")
        self.assertEqual(req.state, "submitted")
