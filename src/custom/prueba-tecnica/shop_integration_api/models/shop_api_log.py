from odoo import api, fields, models


class ShopApiLog(models.Model):
    _name = "shop.api.log"
    _description = "Shop API Request Log"
    _order = "request_date desc, id desc"

    name = fields.Char(
        string="Resumen",
        compute="_compute_name",
        store=True,
    )
    endpoint = fields.Char(
        string="Endpoint",
        required=True,
        index=True,
    )
    method = fields.Char(
        string="Método",
        required=True,
    )
    user_id = fields.Many2one(
        "res.users",
        string="Usuario",
        ondelete="set null",
        index=True,
    )
    status_code = fields.Integer(
        string="Código HTTP",
        required=True,
        index=True,
    )
    duration = fields.Float(
        string="Duración (segundos)",
        digits=(6, 4),
    )
    remote_addr = fields.Char(
        string="IP Cliente",
    )
    request_date = fields.Datetime(
        string="Fecha y Hora",
        default=fields.Datetime.now,
        required=True,
        index=True,
    )

    @api.depends("method", "endpoint", "status_code")
    def _compute_name(self):
        for record in self:
            record.name = f"{record.method or ''} {record.endpoint or ''} - {record.status_code or ''}"

    @classmethod
    def log_call(cls, env, endpoint, method, status_code, duration, user_id=None, remote_addr=None):
        """Registra la llamada en una transacción independiente para preservarla ante rollbacks."""
        # sudo() is required: rejected calls (401) run as the public user, which has no
        # create access on shop.api.log, and every call must be logged. It is limited to
        # create() on this model; the stored values never include the API key.
        try:
            with env.registry.cursor() as cr:
                isolated_env = env(cr=cr)
                isolated_env["shop.api.log"].sudo().create({
                    "endpoint": endpoint,
                    "method": method,
                    "status_code": status_code,
                    "duration": duration,
                    "user_id": user_id,
                    "remote_addr": remote_addr,
                    "request_date": fields.Datetime.now(),
                })
        except Exception:
            # Fallback en caso de que falle la apertura de un cursor nuevo
            env["shop.api.log"].sudo().create({
                "endpoint": endpoint,
                "method": method,
                "status_code": status_code,
                "duration": duration,
                "user_id": user_id,
                "remote_addr": remote_addr,
                "request_date": fields.Datetime.now(),
            })

