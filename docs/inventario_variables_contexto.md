# Inventario de variables de contexto

*Consolida el punto 3 de la devolución de Alan más los factores adicionales identificados en sesión. Actualizado con el esquema real de `player-scores` (verificado en sesión).*

## Leyenda de estado
- ✅ **Disponible directo** — el campo existe, solo hay que incorporarlo.
- 🔨 **Construible** — se arma con una agregación/cruce sobre tablas existentes.
- ⚠️ **Ojo con la temporalidad** — el campo existe pero puede ser un snapshot actual, no histórico por temporada — requiere verificación adicional antes de usarlo tal cual.
- ❌ **No disponible** — no está en `player-scores`.
- 🔁 **Ya cubierto en otra parte** — no duplicar.
- ⏸ **Pendiente, otra sesión** — va con la validez entre ligas concentradas.

## Tabla de factores (actualizada con esquema real)

| # | Factor | Estado | Campo(s) fuente confirmados |
|---|---|---|---|
| 1 | Liga (nivel/tipo) | ✅ | `competitions.csv`: `type`, `sub_type`, `confederation` |
| 2 | Equipo (identidad, efecto club-temporada) | ✅ | `clubs.csv` / `player_valuations.csv`: `club_id` |
| 3 | Calidad del plantel (valor, edad, extranjeros) | ✅ **CONSTRUIDA** | `clubs.csv`: `total_market_value`, `average_age`, `foreigners_number`, `foreigners_percentage`, `national_team_players`, `squad_size` — **pero `clubs.csv` tiene `last_season`, sugiere snapshot actual, no panel histórico.** Para calidad de plantel *por temporada pasada*, construir agregando `player_valuations.csv` por `club_id` + año, no usar los campos de `clubs.csv` directamente. |
| 4 | Compañeros de plantel | ✅ **CONSTRUIDA** (leave-one-out, validada con Haaland) | `game_lineups.csv` (`club_id`, `player_id`, `date`) + `player_valuations.csv` cruzado por fecha más cercana |
| 5 | Participación en competencias internacionales de club | ✅ **CONSTRUIDA** | `games.csv`: `competition_type` (categoriza el tipo de partido directamente) + `competition_id` → `competitions.csv` |
| 6 | Objetivos deportivos (posición, resultado) | ✅ **CONSTRUIDA** | `club_games.csv`: `own_position`, `opponent_position`, `is_win`, `own_goals`/`opponent_goals` — agregación directa por club-temporada |
| 7 | Fortaleza de rivales | ⏸ **Reformulado** — ya no es fase 2 separada, pasa a ser interacción liga×contexto dentro del test de H1 (ver `hipotesis_y_diseno_v2.md`, sección 4) | `club_games.csv`: `opponent_id`, `opponent_position` — base lista, tratamiento completo en sesión de ligas |
| 8 | Participación en selección | 🔁 | Ya tratado en `justificacion_variable_dependiente.md` — campos disponibles si hace falta retomarlo: `players.csv`: `international_caps`, `international_goals`, `current_national_team_id` |
| 9 | Entrenador (identidad, continuidad) | ✅ **CONSTRUIDA** (antes ❌) | `games.csv`: `home_club_manager_name` / `away_club_manager_name` (por partido, histórico); `club_games.csv`: `own_manager_name`. Permite construir "cambios de entrenador en la temporada" sin depender del snapshot de `clubs.csv: coach_name` |
| 10 | Sistema táctico | ✅ **CONSTRUIDA, con advertencia de confiabilidad** (antes ❌) | `games.csv`: `home_club_formation` / `away_club_formation` (ej. "4-3-3") — disponible por partido, se puede agregar a formación predominante por club-temporada |
| 11 | Reputación de club vendedor | ✅ **CONSTRUIDA** (score continuo 4.2% cobertura + flag binario 46.8% cobertura) | `transfers.csv`: `from_club_id`, `to_club_id`, `transfer_fee`, `transfer_date` |
| 12 | Competencia interna por el puesto | ✅ **CONSTRUIDA** | `game_lineups.csv`: `position` (por alineación/partido, no solo la posición "principal" estática de `players.csv`) |
| 13 | Situación contractual | ✅ **(antes ⚠️, ya confirmado)** | `players.csv`: `contract_expiration_date` — directo, sin construir nada |
| 14 | Pertenencia a grupo multi-club | ❌ | No está en el dataset, requiere mapeo externo manual |
| 15 | Continuidad del cuerpo técnico | 🔨 **(antes ❌)** | Misma fuente que #9 — cambios de `manager_name` a lo largo de la temporada |

## Hallazgo importante fuera de la lista original

`game_lineups.csv` tiene `position` **a nivel de partido**, no solo la posición "principal" fija de `players.csv`. Esto resuelve directamente el chequeo pendiente del punto 5 de la devolución de Alan (cambios de posición entre T y T+3, ver `hipotesis_y_diseno_v2.md`) — ya no hace falta inferirlo indirectamente, se puede medir cuántas veces un jugador jugó en una posición distinta a su posición "principal" declarada, partido a partido.

## Estado final (cierre, 13/07/2026)

**8 de 8 variables de contexto construidas y validadas** en `src/construir_variables_contexto.py`: objetivos deportivos, calidad de plantel, competencias internacionales, continuidad técnica, sistema táctico, competencia interna por puesto, reputación de club vendedor (score + flag), compañeros de plantel. Cada una con reconocimiento de datos previo, validación cualitativa contra casos futbolísticos conocidos, y documentación in-code de cada decisión y bug encontrado.

**Variables de rendimiento individual** (distintas conceptualmente — entorno vs. rendimiento propio del jugador): 6 candidatas planificadas en `src/construir_variables_rendimiento.py`, **ninguna corrida ni validada todavía**. Ver `docs/diccionario_variables.md` para el listado completo y unificado de variables de contexto + rendimiento + atributos, con estado de cada una.

- **No disponible, sin resolver (1):** pertenencia a grupo multi-club.
- **Reformulado (1):** fortaleza de rivales — ya no es fase 2 separada, pasa a ser interacción liga×contexto dentro del test de H1 (`hipotesis_y_diseno_v2.md`, sección 4).
- **Ya cubierto en otra parte (1):** participación en selección (`justificacion_variable_dependiente.md`).

De los 15 factores originales de este inventario, terminan **13 resueltos o reformulados**, solo **1 fuera de alcance real** (grupo multi-club).

## Próximo paso

Correr, validar y depurar `src/construir_variables_rendimiento.py` con el mismo patrón usado para el script de contexto (reconocimiento → construcción → validación cualitativa → piso de confiabilidad donde corresponda) — es plan, no trabajo terminado.

¿Arrancamos con el código de la primera variable (objetivos deportivos, la más simple y directa), o preferís que te arme el esqueleto completo de las 10 funciones antes de empezar a correr nada?
