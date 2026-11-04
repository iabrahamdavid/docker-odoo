from odoo import fields, models


class FleetInspectionVehicleType(models.Model):
    _name = "fleet.inspection.vehicle.type"
    _description = "Tipo de vehículo de inspección"
    _order = "name"

    name = fields.Char(string="Nombre", required=True, translate=True)
    code = fields.Char(
        string="Código",
        required=True,
        help="Clave técnica estable; se usa para migrar el antiguo campo de selección.",
    )
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ("code_unique", "unique(code)", "El código del tipo de vehículo debe ser único."),
    ]
