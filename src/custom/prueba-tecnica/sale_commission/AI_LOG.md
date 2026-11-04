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

---

# Tramo B — Contención y comunicación

## Herramientas
- Claude Code (Claude Opus 5.5) en VS Code sobre Linux, con acceso al repositorio y a los contenedores Docker de la instancia `prueba-tecnica`.

## Prompts clave (3 a 5)
1. **Arranque con un plan escrito:**
   - *Prompt:* "Vamos a hacer el Tramo B del ejercicio 3… lee el plan, el enunciado y el INCIDENT.md de la rama hotfix/T-200. Solo lo que pide el enunciado."
   - *Resultado:* Contrastó el plan con el estado real de las ramas y propuso cada operación de git antes de hacerla.
2. **Probar la contención de verdad:**
   - *Prompt:* "La contención se prueba de verdad (falla → permiso temporal → confirma → se borra → vuelve a fallar) y en el INCIDENT van los resultados reales."
   - *Resultado:* Instaló el módulo de la rama base (con el error) en una base de datos aparte y ejecutó un guion con `odoo shell` que hizo los cinco pasos. Los resultados están en la tabla de la sección 6 del `INCIDENT.md`.
3. **Cuándo hace falta actualizar el módulo:**
   - *Prompt:* "¿Antes de probar no debería hacer un update? ¿Cuándo se usa el update?"
   - *Resultado:* Explicó la diferencia entre instalar (`-i`) y actualizar (`-u`). Al revisarlo se vio que la corrección no cambia la versión del módulo (`1.1.0`), por eso el paso de despliegue nombra `sale_commission` de forma explícita.
4. **Qué significa «antes de tener la corrección»:**
   - *Prompt:* "Dice 'antes de tener la corrección', ¿qué entiendes tú por ello?"
   - *Resultado:* Se reescribió la justificación de la contención para que parta del texto del error que ven los vendedores, que es lo único disponible a las 5:40 p.m., y no de la corrección ya analizada.

## Lo que la IA hizo mal
- **Contención justificada con la corrección:** escribió que la medida «tiene el mismo efecto que la corrección definitiva», lo que supone tener ya la corrección.
  - *Cómo se detectó:* lo cuestioné yo al releer «antes de tener la corrección» del enunciado.
- **Mensaje al cliente con trabajo del Tramo C:** incluyó una línea sobre revisar los pedidos que confirmó el gerente.
  - *Cómo se detectó:* lo señalé yo al revisar el mensaje; se quitó.
- **Datos incorrectos sobre `git bisect`:** el primer borrador decía que había dos commits de código entre la versión buena y la mala (hay uno) y proponía correr una prueba que no existe en esos commits.
  - *Cómo se detectó:* la propia IA lo corrigió al releer el texto contra `git log` antes de mostrarlo.
- **Plan con un dato incompleto:** el plan daba por hecho que el README del módulo no tenía tramos ni limitaciones, pero en la rama base ya los tenía; editarlo en `hotfix/T-200` habría causado un conflicto al integrar el PR.
  - *Cómo se detectó:* comparando el archivo en las dos ramas antes de editarlo.

## Lo que escribiste tú sin IA
- Las decisiones de alcance: no ejecutar `git bisect`, no cambiar el estado de la cabecera del incidente y actualizar el README y la memoria de progreso solo en la rama base.
- La revisión del mensaje al cliente y del estilo de los mensajes de commit.
