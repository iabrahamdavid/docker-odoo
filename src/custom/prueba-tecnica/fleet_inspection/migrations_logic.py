"""Logic of the vehicle type migration (selection -> many2one).

Kept in an importable module so the scripts in ``migrations/`` can call it
and the tests can exercise it (folders named after a version are not
importable).
"""
import logging

from odoo.tools.sql import column_exists, rename_column

_logger = logging.getLogger(__name__)

TABLE = "fleet_inspection"
OLD_COLUMN = "vehicle_type"
LEGACY_COLUMN = "vehicle_type_legacy"


def rename_legacy_column(cr):
    """Keep the old selection values under a column the ORM will not touch."""
    if column_exists(cr, TABLE, OLD_COLUMN) and not column_exists(cr, TABLE, LEGACY_COLUMN):
        rename_column(cr, TABLE, OLD_COLUMN, LEGACY_COLUMN)


def map_legacy_vehicle_types(cr):
    """Fill vehicle_type_id from the legacy selection value, matching by code.

    Inspections with an unknown or empty legacy value get the "other" type and
    are reported in the log, so none is left without a type.
    """
    if not column_exists(cr, TABLE, LEGACY_COLUMN):
        return
    cr.execute(
        """
        UPDATE fleet_inspection fi
           SET vehicle_type_id = vt.id
          FROM fleet_inspection_vehicle_type vt
         WHERE vt.code = fi.vehicle_type_legacy
           AND fi.vehicle_type_id IS NULL
        """
    )
    cr.execute("SELECT id FROM fleet_inspection WHERE vehicle_type_id IS NULL ORDER BY id")
    unmapped_ids = [row[0] for row in cr.fetchall()]
    if not unmapped_ids:
        return
    _logger.warning(
        "%s inspecciones sin tipo de vehículo reconocible se asignan a 'other': %s",
        len(unmapped_ids),
        unmapped_ids,
    )
    cr.execute(
        """
        UPDATE fleet_inspection
           SET vehicle_type_id = (SELECT id FROM fleet_inspection_vehicle_type WHERE code = 'other')
         WHERE id = ANY(%s)
        """,
        [unmapped_ids],
    )
