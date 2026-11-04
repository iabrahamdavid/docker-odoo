from odoo.addons.fleet_inspection.migrations_logic import rename_legacy_column


def migrate(cr, version):
    rename_legacy_column(cr)
