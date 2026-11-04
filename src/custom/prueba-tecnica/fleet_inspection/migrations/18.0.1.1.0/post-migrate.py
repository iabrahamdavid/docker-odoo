from odoo.addons.fleet_inspection.migrations_logic import map_legacy_vehicle_types


def migrate(cr, version):
    map_legacy_vehicle_types(cr)
