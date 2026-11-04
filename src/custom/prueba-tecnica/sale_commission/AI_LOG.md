# AI_LOG — sale_commission

## Herramientas
- Antigravity AI Assistant (Gemini 3.8 Flash) en entorno Linux (Ubuntu).

## Prompts clave (3 a 5)
1. **Auditoría de historial Git y diagnóstico de regresión:**
   - *Prompt:* "Analiza el historial de commits de sale_commission e identifica qué cambio introdujo el error de confirmación reportado en el ticket T-200."
   - *Resultado:* Se identificó el commit `3f4d73f` que agregó el modelo `sale.commission.rule` omitiendo permisos de lectura para vendedores en `ir.model.access.csv`.
2. **Diseño de caso de prueba de regresión (Red Test):**
   - *Prompt:* "Diseña un método de prueba en test_sale_commission.py que ejecute la creación y confirmación de un pedido explícitamente como usuario vendedor (group_sale_salesman) para forzar la reproducción del AccessError antes del arreglo."
   - *Resultado:* Se generó `test_salesman_can_confirm_order_with_category_commission` utilizando `.with_user(self.salesman)`, provocando la falla esperada con `AccessError`.
3. **Determinación de la solución mínima (Principio de Menor Privilegio):**
   - *Prompt:* "Define el cambio mínimo para solucionar el ticket T-200 sin usar sudo() y sin elevar privilegios innecesarios al vendedor."
   - *Resultado:* Se definió agregar la línea de permisos de solo lectura (`1,0,0,0`) para `sales_team.group_sale_salesman` sobre `model_sale_commission_rule` en `ir.model.access.csv`.
4. **Estructura y redacción formal de post-mortem:**
   - *Prompt:* "Genera la documentación de INCIDENT.md cubriendo resumen, pasos de reproducción funcional y técnica, causa raíz, solución mínima y verificación verde."
   - *Resultado:* Se redactó el documento técnico formal del incidente cumpliendo todas las directrices de entrega de Binaural.

## Lo que la IA hizo mal
- **Tendencia inicial a sugerir `sudo()` en `_get_commission_percent()`:** En un primer análisis, modelos de IA suelen proponer resolver errores de lectura aplicando `rules = self.env["sale.commission.rule"].sudo().search(...)`. Si bien eso elimina el error en runtime, viola el principio de menor privilegio y la regla estricta del ejercicio ("sin usar sudo() sin justificar"), además de no corregir la deficiencia estructural en la capa de seguridad (`ir.model.access.csv`).
  - *Cómo se detectó:* Revisión manual contra los criterios de evaluación del Tramo A y las restricciones de `CONTEXT.md` §2.3.
- **Sutileza de permisos en `tests`:** Inicialmente no se había advertido que los tests previos pasaban en verde porque corrían bajo `self.env.user` (Admin) en lugar del usuario vendedor creado en el setup (`cls.salesman`). Se verificó la necesidad de usar `.with_user(self.salesman)` tanto en la creación como en el `action_confirm()`.

## Lo que escribiste tú sin IA
- Decisión de no refactorizar la llamada `return self.env.user.commission_percent` en `sale_order_line.py`, respetando la consigna estricta de producción de no reescribir código no directamente relacionado con la causa raíz del bloqueo.
- Verificación en base de datos PostgreSQL limpia mediante el CLI oficial de Docker (`./odoo test prueba-tecnica sale_commission`) comprobando el paso de rojo (1 error) a verde (0 errores, 5/5 OK).
