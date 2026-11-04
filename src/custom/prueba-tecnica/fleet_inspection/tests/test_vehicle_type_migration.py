from odoo.tests.common import TransactionCase, tagged
from odoo.tools.sql import column_exists

from odoo.addons.fleet_inspection.migrations_logic import (
    map_legacy_vehicle_types,
    rename_legacy_column,
)


@tagged("post_install", "-at_install")
class TestVehicleTypeMigration(TransactionCase):
    """Simulates a Tramo A database (selection values) inside the test transaction.

    PostgreSQL DDL is transactional, so the schema changes are rolled back
    when the test ends.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        brand = cls.env["fleet.vehicle.model.brand"].create({"name": "Marca de prueba"})
        model = cls.env["fleet.vehicle.model"].create({"name": "Modelo de prueba", "brand_id": brand.id})
        vehicle = cls.env["fleet.vehicle"].create({"model_id": model.id, "license_plate": "MIG001"})
        # legacy selection value -> expected catalog record
        cls.cases = [
            ("motorcycle", "fleet_inspection.vehicle_type_motorcycle"),
            ("car", "fleet_inspection.vehicle_type_car"),
            ("truck", "fleet_inspection.vehicle_type_truck"),
            ("other", "fleet_inspection.vehicle_type_other"),
            ("other", "fleet_inspection.vehicle_type_other"),
        ]
        cls.inspections = cls.env["fleet.inspection"].create([{"vehicle_id": vehicle.id} for _case in cls.cases])

    def _simulate_tramo_a(self, legacy_values):
        """Leave the inspections as right after the pre-migrate: no type, legacy value kept."""
        self.env.flush_all()
        cr = self.env.cr
        cr.execute("ALTER TABLE fleet_inspection ADD COLUMN vehicle_type_legacy varchar")
        cr.execute("ALTER TABLE fleet_inspection ALTER COLUMN vehicle_type_id DROP NOT NULL")
        for inspection, legacy in zip(self.inspections, legacy_values):
            cr.execute(
                "UPDATE fleet_inspection SET vehicle_type_id = NULL, vehicle_type_legacy = %s WHERE id = %s",
                [legacy, inspection.id],
            )

    def test_map_legacy_vehicle_types(self):
        self._simulate_tramo_a([legacy for legacy, _xmlid in self.cases])

        map_legacy_vehicle_types(self.env.cr)
        self.env["fleet.inspection"].invalidate_model()

        for inspection, (legacy, xmlid) in zip(self.inspections, self.cases):
            self.assertEqual(inspection.vehicle_type_id, self.env.ref(xmlid), legacy)
        other = self.env.ref("fleet_inspection.vehicle_type_other")
        self.assertEqual(
            self.inspections.filtered(lambda i: i.vehicle_type_id == other),
            self.inspections[3:],
            "El valor 'other' debe conservarse",
        )
        self.assertFalse(self.inspections.filtered(lambda i: not i.vehicle_type_id))

    def test_unknown_or_empty_legacy_value_falls_back_to_other(self):
        self._simulate_tramo_a(["car", "van", None, "truck", "other"])

        with self.assertLogs("odoo.addons.fleet_inspection.migrations_logic", level="WARNING"):
            map_legacy_vehicle_types(self.env.cr)
        self.env["fleet.inspection"].invalidate_model()

        other = self.env.ref("fleet_inspection.vehicle_type_other")
        self.assertEqual(self.inspections[1].vehicle_type_id, other)
        self.assertEqual(self.inspections[2].vehicle_type_id, other)
        self.assertEqual(self.inspections[0].vehicle_type_id, self.env.ref("fleet_inspection.vehicle_type_car"))
        self.assertFalse(self.inspections.filtered(lambda i: not i.vehicle_type_id))

    def test_rename_legacy_column(self):
        cr = self.env.cr
        cr.execute("ALTER TABLE fleet_inspection ADD COLUMN vehicle_type varchar")
        cr.execute("UPDATE fleet_inspection SET vehicle_type = 'truck' WHERE id = %s", [self.inspections[0].id])

        rename_legacy_column(cr)

        self.assertFalse(column_exists(cr, "fleet_inspection", "vehicle_type"))
        cr.execute("SELECT vehicle_type_legacy FROM fleet_inspection WHERE id = %s", [self.inspections[0].id])
        self.assertEqual(cr.fetchone()[0], "truck")
        # Without the old column (fresh install) it must do nothing.
        rename_legacy_column(cr)
        self.assertTrue(column_exists(cr, "fleet_inspection", "vehicle_type_legacy"))
