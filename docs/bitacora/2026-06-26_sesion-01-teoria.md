# Bitácora — Sesión 1: Tutoría inicial y justificación teórica

**Fecha:** 05/07/2026
**Contexto:** Primera reunión de tutoría de tesis.

## Preguntas planteadas por el tutor

1. ¿Qué consideramos "desarrollo" en un futbolista? ¿Alcanza con medir su valor de mercado?
2. ¿Es confiable el valor de mercado publicado en Transfermarkt?

## Trabajo realizado

### 1. Marco conceptual de "desarrollo"
Se definieron cuatro dimensiones no intercambiables: técnico-táctico, rendimiento en cancha,
trayectoria de carrera, y reconocimiento de mercado. Se reconoció explícitamente que valor
de mercado ≠ desarrollo técnico puro, y se justificó su elección como proxy por relevancia
aplicada al caso de uso de la tesis (scouting y decisiones de inversión de clubes), no por
equivalencia conceptual.

### 2. Confiabilidad de Transfermarkt
Se relevó evidencia académica que valida los valores de Transfermarkt como proxy de precios
reales de mercado (Herm, Callsen-Bracker & Kreis, 2014; Müller, Simons & Weinmann, 2017;
Prockl & Frick, 2018), reconociendo también los sesgos sistemáticos documentados
(Coates & Parshakov, 2021/2022). Ver `docs/bibliografia.md` para el listado completo con links.

### 3. Caso Lamine Yamal (valoración sin transferencia)
Se investigó y documentó la metodología de Transfermarkt para valuar jugadores sin
transacción real: el valor representa una estimación de "reposición hipotética" en un
mercado abierto, actualizada por rendimiento, edad/potencial, nivel de liga, reputación,
marketing y contrato — no una predicción de precio de transferencia.

### 4. Modelos de negocio de clubes (Ajax / AZ Alkmaar)
Se buscó bibliografía específica sobre los modelos de datos/scouting de estos clubes.
Hallazgo: existe literatura académica sólida sobre identificación de talento en general
(Reeves et al., 2018 y 2019, Soccer & Society / PLoS ONE), pero **no existe literatura
académica peer-reviewed** que documente en profundidad los modelos de negocio o de datos
internos de clubes específicos. Lo disponible es literatura gris (entrevistas a Daan
Uitermark y Koen Veenstra de AZ Alkmaar). Este vacío se documentó como motivación adicional
de la tesis (originalidad/relevancia).

### 5. Shocks de corto plazo en el valor de mercado
Se discutió el efecto de eventos de alta visibilidad (Mundial 2026, en curso) sobre el
valor de mercado, con respaldo de Franck & Nüesch (2012) sobre el efecto de popularidad, y
del paper específico de Havran, Claro & Nessel (2026) sobre el impacto de la participación
mundialista en el valor de jugadores de las cinco grandes ligas. Se definieron estrategias
metodológicas a futuro: estimadores robustos, control explícito por participación en
torneos, análisis de persistencia vs. reversión, y análisis de robustez excluyendo
temporadas de grandes torneos.

## Documento generado

`docs/justificacion_variable_dependiente.docx` — 10 secciones: planteo del problema, marco
de "desarrollo", justificación del proxy, limitaciones reconocidas, confiabilidad empírica
de Transfermarkt, caso Lamine Yamal, motivación adicional (vacío de literatura), shocks de
torneos, síntesis para la tutoría, y referencias completas.

## Próximos pasos

- Llevar este documento a la próxima instancia de tutoría.
- Arrancar la etapa de construcción de datos (panel T→T+3).
