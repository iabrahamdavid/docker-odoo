import time
from functools import wraps
from odoo.http import request


def api_endpoint(require_auth=True):
    """Decorador para endpoints REST:
    - Valida autenticación Bearer con res.users.apikeys (o sesión activa como fallback).
    - Mide la duración exacta de la petición.
    - Registra cada llamada (exitosa o con error 401, 400, 422) en shop.api.log.
    - Garantiza que NUNCA se guarde el token ni la clave en logs.
    """

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            endpoint = request.httprequest.path
            method = request.httprequest.method
            remote_addr = request.httprequest.remote_addr or "n/a"
            user_id = None
            status_code = 500

            try:
                if require_auth:
                    auth_header = request.httprequest.headers.get("Authorization", "")
                    
                    # Caso A: Cabecera Authorization presente (Autenticación Bearer - Tramo B)
                    if auth_header:
                        if not auth_header.startswith("Bearer "):
                            status_code = 401
                            return request.make_json_response(
                                {
                                    "error": {
                                        "code": "UNAUTHORIZED",
                                        "message": "Token de autenticación faltante o inválido.",
                                    }
                                },
                                status=401,
                            )

                        token = auth_header[7:].strip()
                        if not token:
                            status_code = 401
                            return request.make_json_response(
                                {
                                    "error": {
                                        "code": "UNAUTHORIZED",
                                        "message": "Token de autenticación faltante o inválido.",
                                    }
                                },
                                status=401,
                            )

                        uid = request.env["res.users.apikeys"].sudo()._check_credentials(
                            scope="rpc", key=token
                        )
                        if not uid:
                            status_code = 401
                            return request.make_json_response(
                                {
                                    "error": {
                                        "code": "UNAUTHORIZED",
                                        "message": "Token de autenticación faltante o inválido.",
                                    }
                                },
                                status=401,
                            )

                        user_id = uid
                        request.update_env(user=uid)

                    # Caso B: Sin cabecera Authorization pero con sesión activa en navegador (Tramo A)
                    elif request.session.uid:
                        public_user = request.env.ref("base.public_user", raise_if_not_found=False)
                        public_uid = public_user.id if public_user else None
                        if request.session.uid != public_uid:
                            user_id = request.session.uid
                        else:
                            status_code = 401
                            return request.make_json_response(
                                {
                                    "error": {
                                        "code": "UNAUTHORIZED",
                                        "message": "Token de autenticación faltante o inválido.",
                                    }
                                },
                                status=401,
                            )

                    # Caso C: Sin cabecera ni sesión
                    else:
                        status_code = 401
                        return request.make_json_response(
                            {
                                "error": {
                                    "code": "UNAUTHORIZED",
                                    "message": "Token de autenticación faltante o inválido.",
                                }
                            },
                            status=401,
                        )

                # Ejecutar el controlador
                response = fn(*args, **kwargs)
                if hasattr(response, "status_code"):
                    status_code = response.status_code
                else:
                    status_code = 200
                return response

            except Exception:
                status_code = 500
                raise

            finally:
                duration = time.time() - start_time
                try:
                    request.env["shop.api.log"].log_call(
                        env=request.env,
                        endpoint=endpoint,
                        method=method,
                        status_code=status_code,
                        duration=duration,
                        user_id=user_id,
                        remote_addr=remote_addr,
                    )
                except Exception:
                    pass

        return wrapper

    return decorator
