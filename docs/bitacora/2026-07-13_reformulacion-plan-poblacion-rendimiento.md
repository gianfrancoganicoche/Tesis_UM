# Bitácora — Entrada: Reformulación del plan de tesis, población de estudio, variables de rendimiento

**Fecha:** 13/07/2026
**Contexto:** Continuación de la sesión del 12/07 (devolución de Alan + construcción de variables de contexto). Esta entrada cubre el trabajo posterior: modelo relacional, historia narrativa de construcción, reformulación completa del enfoque analítico, y cierre de los puntos bloqueantes para la próxima tutoría.

## Bloque 1 — Modelo relacional y narrativa de construcción

Se armó un diagrama del modelo relacional de `player-scores` (9 tablas, exportado como `docs/modelo_relacional.pdf`). Se reconstruyó la historia completa de la construcción de las 8 variables de contexto en formato narrativo, útil como referencia rápida de por qué se tomó cada decisión (ver entrada del 12/07 para el detalle completo).

## Bloque 2 — Mapa de estado y mini documento para Alan (versión 1, superada)

Se armó un primer mapa de estado de los 9 puntos de la devolución de Alan y un mini documento para la tutoría, centrado en tres alternativas de diseño con H1a (top 5 ligas) / H1b (extensión). **Esta versión quedó superada en el Bloque 3** tras una corrección importante señalada por el tutorando.

## Bloque 3 — Reformulación de las tres alternativas (corrección clave)

Se detectó que la ganancia de trayectorias completas (5.33x más datos) ya no diferenciaba a la Alternativa 3 de las otras dos — Alan mismo, en su reformulación de H1/H2/H3, propone buscar el horizonte óptimo empíricamente sobre trayectorias completas, lo cual aplica igual a un diseño A/B clásico. Se re-derivó la diferencia real entre las tres alternativas: **la Alternativa 3 no tiene un paso de "elegir el mejor horizonte T"** — predice el nivel de valor/habilidad en cualquier edad, no el crecimiento entre dos puntos; el horizonte pasa a ser una consulta libre sobre la curva de edad ya ajustada, no un parámetro a buscar.

**Hallazgo importante:** se identificó que la Alternativa 3 sí ofrece un test de hipótesis clásico con p-valor (test de razón de verosimilitud entre modelo restringido y modelo con contexto, comparando varianza explicada) — más riguroso en sentido estadístico clásico que la comparación de RMSE de la Alternativa 1, que no tiene distribución nula bien definida. Esto resuelve la preocupación del tutorando de que la Alternativa 3 "no permitía testear hipótesis".

Se reformuló H1 como pregunta ancla testeable: *"El contexto de equipo y liga explica una porción estadísticamente significativa de la varianza en el valor de mercado de jugadores sub-23, más allá de lo que explica la curva de desarrollo por edad"* — testeada con razón de verosimilitud, H0: varianza del componente de contexto es cero.

## Bloque 4 — Corrección de la población del test (aporte clave del tutorando)

Se había propuesto inicialmente acotar el test ancla a las 5 grandes ligas "por densidad de datos". El tutorando cuestionó correctamente esta restricción: al auditar cuáles variables son realmente frágiles por liga, se encontró que **las variables robustas del modelo base de H1 (liga, equipo, objetivos deportivos, rendimiento básico) tienen cobertura completa en cualquier liga** — la restricción a top 5 no tenía justificación real para el test central, solo para variables específicas (sistema táctico, reputación de vendedor).

**Confirmado en sesión:** `reputacion_vendedor` tiene 17.3% de cobertura en ligas con score de prestigio disponible vs. 3.4% en el resto — la fragilidad de esta variable sí correlaciona con nivel de liga. `calidad_plantel`, en cambio, es frágil por la edad del jugador, no por la liga (9% cobertura en 0-16 años vs. 58% en 23+, parejo en cualquier liga).

**Rediseño de la población del test:** sin restricción a priori. H1 corre sobre **todas** las ligas de primera división europea, con la heterogeneidad entre ligas tratada como interacción liga×contexto dentro del mismo modelo (resuelve el punto 4 de la devolución de Alan sin necesitar una fase separada). Las variables frágiles se evalúan como extensión de robustez, no como recorte silencioso de la población general.

**Definición operacional de "primera división europea", verificada con código:** `competitions.csv` con `confederation == "europa"`, `type == "domestic_league"`, `sub_type == "first_tier"` → **23 ligas, 23 países** confirmados (no 53, que era el total de todas las entidades europeas incluyendo copas y competencias continentales).

**Hallazgo colateral importante:** el dataset no tiene cobertura de segundas divisiones europeas como entidades propias (0 coincidencias en `competitions.csv` con `sub_type == "second_tier"`, y Derby County —club de Championship inglesa— no tiene fila en `clubs.csv`). Esto explica retroactivamente un hallazgo sin resolver de la sesión anterior (varios `club_id` de destino sin nombre al construir `reputacion_vendedor`). Documentado como limitación estructural de la fuente, con dos consecuencias nombradas: contexto incompleto para jugadores que pasaron por clubes de segunda, y subestimación de ventas hacia ligas inferiores en `reputacion_vendedor`.

## Bloque 5 — Reordenamiento de prioridades para la tutoría

Se cruzó el texto completo de los puntos 1 y 2 de la devolución de Alan (releído completo, no solo lo ya resuelto) contra el estado real del proyecto. Aparecieron dos vacíos genuinos no detectados antes:

- **Condición comunitario/extracomunitario** — mencionada explícitamente por Alan, nunca abordada.
- **Definición formal de "rendimiento"** — nunca se formalizó qué variables de rendimiento individual entran al modelo, más allá de una mención genérica temprana.

Se estableció un orden de prioridad con dos puntos bloqueantes para la tutoría (rendimiento y población/comunitario) y el resto como no bloqueante.

## Bloque 6 — Definición formal de rendimiento individual

Se detectó un vacío conceptual en el diseño de la Alternativa 3: la especificación original (`valor = curva_edad + contexto + α_i`) no incluía ningún término de rendimiento, dejando a α_i funcionando como caja negra (mezcla producción observable con señal genuina de scouting). Se corrigió agregando rendimiento a la descomposición.

**Definición inicial** (goles/90, asistencias/90, minutos): el tutorando señaló correctamente que estas variables solo sirven bien para posiciones ofensivas. Se ampliaron a 6 variables candidatas (`src/construir_variables_rendimiento.py`, ninguna corrida todavía):
- Rendimiento básico: goles/90, asistencias/90, contribución de gol/90, tarjetas/90, % minutos disponibles.
- Proxy defensivo: goles recibidos como titular (especialmente arqueros).
- Goles recibidos ajustados por fuerza ofensiva del rival (adelanta parte del punto 4 de Alan).
- Diferencial con/sin el jugador (estilo *Plus-Minus Soccer*, sirve para las 4 posiciones).
- Participación relativa en la producción ofensiva del equipo.
- Edad de debut profesional.

Cobertura de `appearances.csv` (goals/assists/minutes_played/yellow_cards/red_cards) confirmada sin ningún NaN.

## Bloque 7 — Auditoría sistemática de atributos del jugador

Para resolver el punto de comunitario/extracomunitario y evitar el riesgo de "no me di cuenta" ante preguntas de un jurado, se auditaron todos los campos de `players.csv` no usados hasta el momento, con decisión explícita para cada uno:

- **`es_comunitario`** (ciudadanía UE/EEE+Suiza) — construida y validada. Cobertura 99.5%, 41.6% de la base clasificada como comunitaria. Limitación documentada: no captura doble ciudadanía por ascendencia.
- **`foot`, `height_in_cm`** — incorporadas como candidatas, con literatura de respaldo para altura/pie hábil.
- **`agent_name`** — descartada explícitamente (riesgo de sesgo subjetivo sin criterio objetivo).
- **`sub_position`** — pérdida de granularidad reconocida y justificada (densidad de datos edad×posición).

## Bloque 8 — Bibliografía: reset y tres papers nuevos sobre curva de edad

Se identificó que no había ninguna cita sosteniendo directamente la forma de la curva de edad —pieza central de la Alternativa 3. Se agregaron tres papers tras búsqueda:

- **Dendir (2016)**, *When do soccer players peak? A note* — modelo de efectos fijos por jugador, pico 25-27 años, forwards ~25, defensores ~27.
- **Kalén, Rey, Sal de Rellán-Guerra & Lago-Peñas (2019)** — curva de valor de mercado (no solo rendimiento físico), forma de U invertida, pico 26-30, arqueros/centrales pican más tarde.
- **Säfvenberg, Nordgaard, Lidmark Eriksson, Carlsson & Lambrix (2024)** — **precedente metodológico más cercano al diseño de la tesis**: modelo jerárquico bayesiano con intercepto/pendiente por jugador sobre spline de edad, con shrinkage — misma arquitectura estadística planeada acá, aplicada a una liga menor (Suecia). Discute explícitamente el sesgo de jugadores de ligas menores vendidos antes de alcanzar su pico — relevante para el punto de ligas concentradas.

`docs/bibliografia.md` reorganizado por tema: núcleo metodológico para la Alternativa 3 separado de literatura secundaria/motivacional (Large Event Models deprioritizado, talent identification y Ajax/AZ marcados como motivacionales, no metodológicos).

## Archivos creados o actualizados en esta sesión

- `docs/modelo_relacional.pdf` (nuevo)
- `docs/discusion_enfoque_tesis_proxima_tutoria.md` (reescrito, versión final centrada en el plan sobre la Alternativa 3)
- `docs/hipotesis_y_diseno_v2.md` (actualizado sustancialmente: alternativas reformuladas, sección 3.2 rendimiento, sección 3.3 atributos, sección 4 población en tres capas)
- `docs/bibliografia.md` (reorganizado por tema, 3 papers nuevos de curva de edad)
- `docs/inventario_variables_contexto.md` (actualizado a 8/8 variables construidas)
- `docs/diccionario_variables.md` (nuevo — diccionario unificado de ~19 variables candidatas)
- `src/construir_variables_rendimiento.py` (nuevo — 6 funciones planificadas, sin correr)

## Próximos pasos

- Llevar `docs/discusion_enfoque_tesis_proxima_tutoria.md` a la próxima tutoría con Alan — validar el plan sobre la Alternativa 3.
- Correr, validar y depurar `src/construir_variables_rendimiento.py` (mismo patrón que el script de contexto).
- Actualizar `docs/tema_tesis.md` para reflejar el estado real del proyecto (pendiente, no se llegó a hacer en esta sesión).
- Retomar punto 7 de Alan (calidad de datos por país/año) y punto 8 (survivorship bias), ambos todavía sin abordar en profundidad.
