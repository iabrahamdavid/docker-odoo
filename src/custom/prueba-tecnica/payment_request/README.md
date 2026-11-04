# Solicitudes de Pago (`payment_request`)

Módulo desarrollado para la **Prueba Técnica de Desarrollador Odoo** en **Binaural**.
Gestiona el flujo completo de solicitudes de pago a proveedores con control de aprobaciones, trazabilidad en chatter y aislamiento de seguridad por roles.

---

## 1. Contexto de Negocio

A partir del requerimiento remitido por **Carolina Méndez** (Gerente de Administración de Distribuidora Andina C.A.):
> *"Hoy las solicitudes de pago a proveedores llegan por WhatsApp y nadie sabe cuáles se aprobaron. Necesitamos que en Odoo cualquier empleado pueda pedir un pago indicando el proveedor, el monto y el concepto, y que una vez enviada la solicitud ya no la pueda cambiar.*  
> *Los pagos normales los aprueba el jefe del área, pero los grandes los tiene que aprobar gerencia. Si se rechaza, el empleado tiene que saber por qué.*  
> *Cuando tesorería pague, que quede registrado en contabilidad y que podamos imprimir la solicitud para la carpeta del proveedor. Ah, y muchos proveedores nos facturan en dólares pero les pagamos en bolívares."*

---

## 2. Supuestos y Preguntas al Cliente (Obligatorio)

Como consultores funcionales y técnicos de Odoo, se identificaron ambigüedades en el requerimiento inicial. Para avanzar de manera sólida en el desarrollo sin bloquear la entrega, se establecieron los siguientes supuestos y preguntas de clarificación:

### Preguntas para Carolina Méndez:
1. **Umbral de Aprobación Gerencial:** ¿A partir de qué monto exacto una solicitud deja de ser un «pago normal» y pasa a ser un «pago grande» que requiere la aprobación exclusiva de gerencia? ¿Este umbral se calcula en USD o en moneda local (VES)?
2. **Jerarquía Organizacional:** ¿Cómo está modelado el «jefe del área» del solicitante en Odoo? ¿Se utilizará la relación de responsable en el departamento (`hr.department.manager_id`), el responsable directo del empleado (`hr.employee.parent_id`), o una asignación manual por usuario?
3. **Flujo de Rechazo:** Si una solicitud es rechazada, ¿el empleado debe tener la posibilidad de corregir las observaciones y reenviar la misma solicitud (volviendo a borrador), o la política interna exige archivarla e iniciar una solicitud desde cero?
4. **Vínculo Contable de Tesorería:** Al registrar el pago en contabilidad, ¿se debe conciliar contra una factura de proveedor (`account.move`) preexistente registrada en el sistema, o se trata de pagos anticipados / gastos directos mediante `account.payment`?
5. **Conversión Cambiaria (USD a VES):** Para proveedores que facturan en USD pero cobran en VES, ¿qué tasa de cambio oficial debe tomarse? ¿La tasa de cambio del Banco Central (BCV) correspondiente a la fecha de la solicitud, o la tasa efectiva del día en que Tesorería ejecuta el pago?

### Supuestos asumidos para la solución técnica:
1. **Identidad del Solicitante:** Se asume que cualquier usuario activo del sistema con rol de empleado puede generar solicitudes de pago, asignándose automáticamente `env.user` como solicitante por defecto.
2. **Alcance del Tramo A:** En este tramo base, la aprobación queda habilitada para los miembros del grupo de seguridad **Aprobador** (`group_payment_request_approver`), dejando la parametrización de rangos de montos y matrices dinámicas de aprobación lista para su conexión en el Tramo B (`payment.approval.level`).
3. **Inmutabilidad Estricta:** La solicitud enviada queda blindada frente a modificaciones tanto en la interfaz de usuario (`readonly="state != 'draft'"`) como en la capa ORM (`write()`), impidiendo alteraciones fraudulentas de montos o proveedores tras su envío.
4. **Ciclo de Corrección:** Se permite al usuario restablecer una solicitud a borrador únicamente si fue rechazada (`action_reset_to_draft()`), permitiendo corregir errores señalados por los aprobadores sin perder el histórico.

---

## 3. Estado de Tramos del Módulo

| Tramo | Descripción | Estado | Cobertura / Entregables |
|---|---|:---:|---|
| **Tramo A** | **Modelo Base, Seguridad y Vistas:**<br>Modelo `payment.request` con `mail.thread` y `mail.activity.mixin`, secuencia `SP/YYYY/NNNN`, estados (`draft`, `submitted`, `approved`, `paid`, `rejected`), inmutabilidad ORM en `write()`, reglas de borrado en `unlink()`, 3 grupos de seguridad con herencia, reglas de registro de aislamiento (`ir.rule`), vistas `<list>`, `<form>` con `<chatter/>` y `<search>`. | ✅ **Completado** | 8 tests unitarios (cobertura > 85%), `README.md`, `AI_LOG.md`. |
| **Tramo B** | **Niveles de Aprobación, Wizards y PDF:**<br>Modelo `payment.approval.level`, actividades automáticas por monto, wizard de motivo de rechazo en chatter, wizard de pago con `account.payment` y reporte QWeb PDF. | ⏳ Planificado | A desarrollar según roadmap. |
| **Tramo C** | **Multi-Moneda USD/VES y Concurrencia:**<br>Cálculo de tasa a la fecha de pago, soporte multi-compañía estricto, control de concurrencia con bloqueo en base de datos (`SELECT FOR UPDATE`), `ARCHITECTURE.md`. | ⏳ Planificado | A desarrollar según roadmap. |

---

## 4. Estructura de Seguridad y Roles

El módulo implementa tres niveles de acceso jerárquicos:

1. **Solicitante (`group_payment_request_user`):**
   * Empleado base (`base.group_user`).
   * Puede crear, editar (solo en borrador) y consultar **únicamente sus propias solicitudes**.
   * Regla de registro: `[('applicant_id', '=', user.id)]`.
   * Prohibido aprobar o rechazar solicitudes (restringido tanto en vistas como a nivel de métodos ORM con `AccessError`).
2. **Aprobador (`group_payment_request_approver`):**
   * Jefes de área y gerencia. Hereda permisos de Solicitante.
   * Visualiza todas las solicitudes de la compañía (`[(1, '=', 1)]`).
   * Autorizado para ejecutar las acciones `action_approve()` y `action_reject()`.
3. **Tesorería / Responsable (`group_payment_request_manager`):**
   * Encargados de la dispersión de fondos y administración del módulo.
   * Acceso total de gestión y configuración.

---

## 5. Instrucciones de Ejecución de Pruebas

Para ejecutar la suite completa de pruebas unitarias sobre este módulo en el contenedor Docker:

```bash
./odoo test prueba-tecnica payment_request
```

O en entornos Windows PowerShell:
```powershell
$env:PYTHONUTF8=1; python odoo test prueba-tecnica payment_request
```

---

## 6. Limitaciones Conocidas (Tramo A)

1. **Niveles de aprobación por monto:** En el Tramo A, la aprobación queda habilitada para cualquier usuario perteneciente al grupo `group_payment_request_approver`. La matriz dinámica de aprobación según el monto y la asignación automática de actividades (`payment.approval.level`) pertenecen al Tramo B.
2. **Transición a Pagada:** En este tramo no existe un botón manual para forzar el estado `paid`; dicho estado se alcanzará en el Tramo B mediante el wizard de pago contable vinculado a `account.payment`.
3. **Blindaje de inmutabilidad en ORM:** Para evitar vulnerabilidades de omisión de controles, los métodos `write()` y `create()` impiden que usuarios sin rol de aprobador modifiquen directamente el estado (`state`) o alteren la secuencia (`name`), exigiendo que el avance de estados ocurra únicamente mediante los botones y métodos del flujo oficial. En `write()` esta restricción aplica a todo usuario y no depende del contexto: el contexto lo controla el cliente en cada llamada RPC, así que inyectar claves en él no permite reabrir ni renumerar una solicitud enviada (prueba `test_09`).

