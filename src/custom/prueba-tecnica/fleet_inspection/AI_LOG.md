# AI_LOG — fleet_inspection

## Herramientas
- Antigravity AI Assistant (Gemini 3.8 Flash) en entorno Linux (Ubuntu).

## Prompts clave (3 a 5)
1. **Auditoría de obsolescencias de Odoo 16 a Odoo 18:**
   - *Prompt:* "Analiza el módulo fleet_inspection en Odoo 16 e identifica todas las incompatibilidades con Odoo 18 en manifiesto, vistas, modelos, cron y seguridad".
   - *Resultado:* Se detectó el uso de `attrs`, `states`, `tree`, `numbercall` en `ir.cron`, y `name_get` en Python.
2. **Modernización de vistas XML y etiquetas canónicas:**
   - *Prompt:* "Convierte las vistas XML reemplazando attrs y states por invisible y readonly nativos, y adopta list y chatter".
   - *Resultado:* Se refactorizó `fleet_inspection_views.xml` e `fleet_inspection_item_views.xml` eliminando completamente la sintaxis previa.
3. **Optimización del modelo con `@api.model_create_multi`:**
   - *Prompt:* "Adapta el método create de fleet.inspection para soportar creación masiva vals_list evitando consultas N+1 en checklist items".
   - *Resultado:* Se cacheó la búsqueda de items para todo el batch antes del super().create().
4. **Depuración de error en carga de datos cron:**
   - *Prompt:* "Identifica el fallo de ParseError en data/ir_cron_data.xml durante la instalación en base limpia".
   - *Resultado:* Se descubrió que además de `numbercall`, Odoo 18 eliminó el campo `doall` del modelo `ir.cron`.

## Lo que la IA hizo mal
- Inicialmente solo sugirió remover `numbercall` de `data/ir_cron_data.xml`, pasando por alto que `doall` también fue eliminado en Odoo 18. Al ejecutar `./odoo test` en una base virgen, Odoo arrojó `ValueError: Invalid field 'doall' on model 'ir.cron'`.
- *Cómo se detectó:* Mediante la ejecución real del test en base limpia con `./odoo test`, analizando el traceback exacto en los logs del contenedor Docker.

## Lo que escribiste tú sin IA
- Verificación manual de las dependencias externas (`fleet` y `mail`) en el entorno Docker para corroborar que los grupos de usuario no sufrieron renombrado de XML IDs en Odoo 18.
- La estrategia de compatibilidad dual en `name_get()` llamando internamente a `_compute_display_name()` para asegurar que tanto la API nueva de Odoo 18 como posibles llamadas legadas o tests mantuvieran total estabilidad.

---

# Tramo B — tipo de vehículo como catálogo

## Herramientas
- Claude Code (Claude Opus 5.5) en VS Code sobre Linux, con acceso al repositorio y a los contenedores Docker de la instancia `prueba-tecnica`.

## Prompts clave (3 a 5)
1. **Arranque con un plan escrito:**
   - *Prompt:* "Revisa `PLAN_EJ2_TRAMO_B.md` para proceder".
   - *Resultado:* Contrastó el plan con el estado real del repositorio (rama, versión del manifiesto, las 6 referencias a `vehicle_type`) e implementó el catálogo, el campo Many2one, los scripts `pre`/`post` y las pruebas, pidiendo confirmación antes de cada commit.
2. **Escenario real del enunciado:**
   - *Pedido:* instalar el Tramo A, crear datos, subir la versión y actualizar con `-u`.
   - *Resultado:* Instaló el Tramo A desde el commit `847c7b9` en una base aparte, creó 14 inspecciones y comparó los conteos por tipo antes y después con SQL.
3. **Revisión de lo hecho:**
   - *Prompt:* "Puedes verificar si lo que llevamos está bien y mostrármelo en tablas".
   - *Resultado:* Tablas de criterios del enunciado frente a evidencia; detectó y corrigió dos detalles de estilo (línea en blanco antes de la clase y una línea de 158 caracteres en las pruebas).

## Lo que la IA hizo mal
- **Datos de prueba que no probaban el chatter:** cambió el tipo de una inspección dos veces (Camión y de vuelta a Otro) en la misma transacción, así que Odoo no registró ningún cambio y la comprobación del historial no probaba nada.
  - *Cómo se detectó:* la consulta a `mail_tracking_value` volvió vacía. Se repitió el escenario con un cambio real y confirmado.
- **Shell de Odoo con el código equivocado:** al crear datos del Tramo A, `odoo shell` cargó el código nuevo porque la variable `ODOO_RC` del contenedor se lee antes que `--addons-path`.
  - *Cómo se detectó:* error `Invalid field 'vehicle_type' on model 'fleet.inspection'`; se resolvió apuntando `ODOO_RC` a una configuración temporal.
- **Mensajes de commit fuera del estilo del repositorio:** propuso asuntos con tildes y una redacción distinta a la del historial.
  - *Cómo se detectó:* lo señalé yo al revisarlos; se reescribieron siguiendo `git log`.

## Lo que escribiste tú sin IA
- Las decisiones de alcance: no añadir pruebas que el enunciado no pide (por ejemplo, la de borrar un tipo en uso) y hacer un commit por paso en lugar de uno al final.
- La revisión y el estilo de los mensajes de commit.
