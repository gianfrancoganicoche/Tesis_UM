# Bitácora — Entrada 4: Variables de rendimiento y primer panel de predictores

**Fecha:** 20/07/2026
**Contexto:** Sesión de construcción y validación previa a la tutoría del 22/07.

## Resumen

Se corrieron y validaron contra datos reales las 6 funciones de variables de
rendimiento que habían quedado planteadas pero sin ejecutar. En el proceso se
encontraron y corrigieron 5 bugs reales (no solo ajustes de umbral), y se
descubrió un problema estructural de granularidad entre el panel de
rendimiento y las variables de contexto que obligó a construir una pieza
nueva (crosswalk jugador-club-temporada) antes de poder mergear ambos
paneles. Se cierra la sesión con un panel de predictores unificado
`(player_id, season)`, 90.408 filas, sin duplicados, guardado en
`data/processed/panel_predictores_2026-07-20.parquet`.

## Variables de rendimiento — bugs encontrados y corregidos

### Variable A (rendimiento básico)
- División por cero en minutos → `inf` en vez de `NaN`. Corregido con
  `.replace([np.inf, -np.inf], np.nan)`.
- Ratios por-90 con muestra chica (ej. 1 minuto jugado + 1 gol = `goles_90 =
  90`) distorsionaban la varianza. Piso empírico definido en **90 minutos**
  (1 partido completo): el std de `goles_90` cae 73% entre 0 y 90 minutos, y
  de ahí en más la caída es gradual sin codo marcado. Flag agregado:
  `minutos_confiables`.

### Variable B (% minutos disponibles)
- Bug de diseño: un jugador transferido a mitad de temporada generaba filas
  duplicadas por `(player_id, season)` — el `groupby` interno incluía
  `club_id` pero el `return` final lo descartaba. Afectaba 5.685
  jugador-temporadas (6.2% del panel). Resuelto quedándose con el club de
  más minutos jugados esa temporada, con flag
  `tuvo_multiples_clubes_temporada` para no perder la señal de que hubo
  transferencia.
- **El mismo bug exacto reapareció después en Variable E**
  (`participacion_produccion_ofensiva`) — mismo patrón de groupby con
  `player_club_id` interno sin resolver antes del return. Se detectó recién
  al validar el panel completo (duplicados = 5.685, número idéntico al de
  Variable B, lo que delató la causa). Corregido con el mismo criterio.

### Variable B/C (goles recibidos, simple y ajustado por rival)
- Ratios por-90 sobre 1 solo partido titular generaban valores absurdos (ej.
  una goleada 0-10 en un único partido = 10 goles recibidos/90). Piso
  empírico definido en **5 partidos titular**: el std cae 31% entre 1 y 5
  partidos, después decae gradual sin codo marcado. Flag agregado:
  `partidos_confiables`.
- El ajuste por fuerza ofensiva del rival no era leave-one-out (el propio
  partido inflaba el promedio del rival, "perdonándose a sí mismo" en
  goleadas). Corregido con leave-one-out explícito.
- Validación: correlación entre versión simple y ajustada = 0.896 (esperado
  0.7-0.9) — confirma que el ajuste aporta información real sin ser
  redundante.

### Variable D (diferencial con/sin jugador, plus-minus)
- **Performance inviable**: la versión original (loop anidado por
  club-temporada × jugador) tardó 9 minutos para una sola temporada (2020) —
  proyectado a 2+ horas para el dataset completo. Se reescribió vectorizada,
  validada primero contra un caso sintético controlado (match exacto) y
  después contra datos reales.
- **Bug real encontrado al validar la vectorización** (no solo un problema
  de velocidad): la versión original filtraba los partidos "con" de un
  jugador solo por `game_id`, sin filtrar también por `club_id`. Esto
  inflaba el conteo cuando un jugador jugó para dos clubes que se
  enfrentaron entre sí en la misma temporada (caso real encontrado: jugador
  369267, temporada 2020, contado con 5 partidos "con" para el club 28643
  cuando el valor correcto era 4 — uno de esos partidos lo jugó para el
  club rival, 475). La versión vectorizada corrige esto por construcción.
- Resultado: 2.4 segundos sobre el dataset completo (vs. ~2+ horas
  proyectadas), 62.445 filas, sin casos degenerados (máximo |diferencial|
  = 0.88, dentro de lo esperable con el piso de 5 partidos por grupo).

### Variable E (participación en producción ofensiva)
- Bug de groupby frágil: doble `groupby` + suma por `.values`, que asumía
  mismo orden de grupos entre dos llamadas separadas a `groupby` sin
  garantía real de ese orden. Reemplazado por un único `groupby` con dos
  agregaciones en la misma llamada.
- Bug de duplicados por multi-club (ver nota en Variable B arriba).
- Nota conceptual documentada (no bug): el numerador suma goles+asistencias
  del jugador pero el denominador es solo goles totales del equipo — un gol
  con asistencia cuenta doble entre goleador y asistidor, la suma de
  `participacion_produccion` de un plantel completo puede superar 1.0.

### Variable F (edad de debut)
- Flag `debut_confiable` agregado (post-2012, por el piso de cobertura de
  `games.csv`) y **confirmado empíricamente**: mediana `edad_debut` = 25.4
  en el grupo no confiable vs. 21.6 en el confiable.
- **Limitación adicional detectada, no resuelta por el flag**: incluso en el
  grupo confiable, la mediana (21.6) sigue por encima de lo esperable para
  debut real (17-19). Hipótesis: un segundo mecanismo de sesgo por falta de
  cobertura de segundas divisiones — jugadores que debutan ahí y solo entran
  al dataset al llegar a un club de primera. Documentado como limitación
  aparte, pendiente de evaluar cuánto aporta la variable en el modelo antes
  de decidir cómo tratarla.

## Hallazgo estructural: granularidad de las variables de contexto

Al revisar el archivo completo de `construir_variables_contexto.py` (8
variables ya construidas en sesiones previas) se encontró que **no todas
comparten granularidad**:

- 6 de las 8 viven a nivel `(club_id, season)`: objetivos deportivos,
  calidad de plantel, competencias internacionales, continuidad técnica,
  sistema táctico, reputación de club vendedor (+ su flag). Tiene sentido
  conceptual (son propiedades del entorno), pero no se pueden mergear
  directo contra el panel de rendimiento, que es `(player_id, season)` sin
  `club_id` retenido.
- 1 (competencia interna por puesto) vive a nivel `(club_id, season,
  posición_amplia)` — una dimensión extra que ninguna otra tiene.
- 1 (compañeros de plantel) vive a nivel `(player_id, date_valuación)` — atada
  a la fecha de cada valuación de mercado, no a la temporada.

Para resolver el primer grupo (el más grande y directo), se construyó
`construir_crosswalk_jugador_club_temporada()`: mapea cada `(player_id,
season)` al club donde el jugador tuvo más minutos esa temporada (mismo
criterio ya usado en Variable B). Con ese puente se armó
`construir_panel_predictores()` en un archivo nuevo
(`src/construir_panel_predictores.py`), que une rendimiento + las 5
variables de contexto de club-temporada más directas.

## Resultado: panel de predictores

- **90.408 filas, 59 columnas, `(player_id, season)`, sin duplicados**
  (verificado).
- Cobertura de las variables de contexto pegadas: alta para objetivos
  deportivos, continuidad técnica y calidad de plantel (0% NaN); moderada
  para sistema táctico (7% NaN, consistente con lo ya documentado);
  baja para reputación de vendedor (86.7% NaN a nivel jugador — coherente
  con el 4.2% de cobertura ya conocido a nivel club, algo mejor acá porque
  los clubes grandes concentran más jugador-temporadas).
- **Corrección aplicada**: `partidos_europeos`, `fase_maxima_alcanzada`,
  `competencias_distintas` y `jugo_fase_grupos_o_mas` tenían NaN para
  club-temporadas que simplemente no jugaron competencia europea ese año —
  no es dato faltante, es un cero real. Se rellenaron explícitamente
  (0 / False) para no confundir "no aplica" con "no disponible", a
  diferencia de `reputacion_vendedor`, donde el NaN sí es genuina falta de
  información por baja cobertura de score de liga.
- Guardado en `data/processed/panel_predictores_2026-07-20.parquet` (o
  `.csv` si el entorno no tenía `pyarrow` disponible al momento de guardar).

**Nota operativa:** durante la sesión el kernel de Positron pasó, sin acción
deliberada, de un entorno Python 3.11 (instalación directa) a un entorno
gestionado por `uv` con Python 3.14.6 (`uv: Tesis_UM`). Esto causó varios
`ModuleNotFoundError`/`ImportError` intermedios (incluyendo un
`ArrowKeyError` al instalar `pyarrow` a mitad de sesión activa, resuelto con
un reinicio de kernel limpio). Vale la pena confirmar antes de la próxima
sesión cuál es el entorno "canónico" del proyecto para evitar reconstruir
instalaciones de librerías cada vez que cambia el entorno activo.

## Queda pendiente (explícito, no resuelto en esta sesión)

1. **`competencia_interna_puesto`**: requiere la posición de cada jugador
   por temporada para poder pegarse (dimensión extra que hoy nadie más
   tiene). No calculado.
2. **`companieros_plantel`**: vive a nivel fecha-de-valuación, no temporada.
   Requiere decidir el criterio de agregación a `season` (¿última valuación
   del año? ¿promedio?) antes de poder incorporarla.
3. **Variable dependiente bajo Alternativa 3**: el panel de hoy es un panel
   de **predictores**, no el dataset modelable completo. El código que
   reconstruye el crecimiento de valor de mercado bajo el diseño de
   trayectoria completa (a diferencia del `crecimiento_log` T→T+3 del
   diseño viejo) todavía no existe. Es la pieza más importante que falta
   antes de poder correr cualquier modelo bajo el diseño nuevo.
4. Evaluar, una vez que haya modelo corriendo, cuánto aporta realmente
   `edad_debut` dado el sesgo estructural documentado — decidir si se
   excluye, se usa solo el subconjunto confiable, o se mantiene con el
   flag como control.

## Próximos pasos

- Definir y construir la variable dependiente bajo Alternativa 3 (prioridad
  más alta, bloquea cualquier modelado).
- Resolver companieros_plantel (agregación a season) y competencia interna
  por puesto (necesita posición por jugador-temporada) para completar las
  8 variables de contexto originalmente planeadas.
- Con el panel de predictores ya sólido, este es buen momento para llevar a
  Alan una pregunta concreta: ¿conviene cerrar primero la variable
  dependiente antes de seguir sumando predictores, o hay alguna prioridad
  distinta desde su perspectiva?
