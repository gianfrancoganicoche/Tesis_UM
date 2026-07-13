# Inventario de variables de contexto

*Consolida el punto 3 de la devolución de Alan más los factores adicionales identificados en sesión. Sirve de checklist para la construcción de features en `src/panel_pipeline.py`.*

## Leyenda de estado
- ✅ **Disponible directo** — el campo existe en el dataset, solo hay que incorporarlo.
- 🔨 **Construible** — no existe como campo directo, pero se arma con una agregación sobre tablas existentes.
- ⚠️ **Verificar** — puede existir, no confirmado; requiere chequeo de esquema antes de decidir.
- ❌ **No disponible** — no está en `player-scores`; queda como limitación reconocida o trabajo futuro.
- 🔁 **Ya cubierto en otra parte** — no duplicar, referenciar la sección existente.
- ⏸ **Pendiente, otra sesión** — se resuelve junto con la validez entre ligas concentradas.

## Tabla de factores

| # | Factor | Origen | Estado | Tabla(s) / campo(s) fuente |
|---|---|---|---|---|
| 1 | Liga (nivel/tipo de competencia) | Alan | ✅ | `competitions.csv` |
| 2 | Equipo (identidad, efecto club-temporada) | Alan | ✅ | `clubs.csv` — `club_id` |
| 3 | Calidad del plantel (valor total, edad promedio) | Alan | 🔨 | Agregación de `player_valuations.csv` por `club_id` + temporada |
| 4 | Compañeros de plantel (valor promedio, experiencia internacional) | Alan | 🔨 | `game_lineups.csv` + `player_valuations.csv` |
| 5 | Participación en competencias internacionales de club | Alan | 🔨 | `competitions.csv` + `games.csv` (flags de Champions/Europa/Conference) |
| 6 | Objetivos deportivos (posición en tabla, puntos, diferencia de gol) | Alan | 🔨 | `games.csv` + `club_games.csv` |
| 7 | Fortaleza de rivales / calendario ponderado | Alan | ⏸ | `games.csv` (club rival) + valor de plantel rival — va con la sesión de ligas concentradas |
| 8 | Participación en selección / torneos internacionales | Alan | 🔁 | Ya tratado en `justificacion_variable_dependiente.md`, sección 8 (shocks de torneos) |
| 9 | Entrenador | Alan | ❌ | No está en el dataset |
| 10 | Sistema táctico | Alan | ❌ | No está en el dataset |
| 11 | Reputación de club como "vendedor" de jóvenes | Sesión | 🔨 | `transfers.csv` — % de sub-23 transferidos a ligas top en los últimos N años, por club |
| 12 | Competencia interna por el puesto (profundidad de plantel en esa posición) | Sesión | 🔨 | `game_lineups.csv` + `position` |
| 13 | Situación contractual (años restantes de contrato) | Sesión | ⚠️ | `players.csv` — chequear si existe `contract_expiration_date` o similar |
| 14 | Pertenencia a grupo multi-club (City Group, Red Bull, etc.) | Sesión | ❌ | Requiere mapeo externo manual club→grupo, no está en el dataset |
| 15 | Continuidad del cuerpo técnico (cambios de entrenador en la temporada) | Sesión | ❌ | No está en el dataset |

## Resumen por estado

- **Disponibles directos (2):** liga, equipo — ya usados en el modelo de efectos fijos actual.
- **Construibles esta iteración (6):** calidad del plantel, compañeros, competencias internacionales, objetivos deportivos, reputación de club vendedor, competencia interna por puesto.
- **A verificar (1):** situación contractual — primer paso antes de construir nada.
- **No disponibles (3):** entrenador, sistema táctico, pertenencia a grupo multi-club, continuidad técnica — quedan documentados como limitación reconocida, con la salvedad de que el efecto de club-temporada (factor #2) los absorbe de forma indirecta y no explicada (ver `hipotesis_y_diseno_v2.md`, discusión de la estructura de dos capas).
- **Pendiente para la sesión de ligas (1):** fortaleza de rivales.
- **Ya cubierto en otra parte (1):** participación en selección.

## Paso 0 — Verificar esquema real antes de construir nada

Antes de escribir cualquier función de feature engineering, correr esto para confirmar qué columnas existen realmente (los nombres de campo pueden diferir de lo asumido, y el punto 13 depende enteramente de este chequeo):

```python
import pandas as pd
import kagglehub

path = kagglehub.dataset_download("davidcariboo/player-scores")

tablas = [
    "players", "clubs", "competitions", "games",
    "club_games", "game_lineups", "appearances", "transfers",
    "player_valuations",
]

for nombre in tablas:
    try:
        df = pd.read_csv(f"{path}/{nombre}.csv", nrows=5)
        print(f"\n=== {nombre}.csv ===")
        print(list(df.columns))
    except FileNotFoundError:
        print(f"\n=== {nombre}.csv NO EXISTE ===")
```

Prestar especial atención a:
- `players.csv` → ¿existe algún campo de vencimiento/duración de contrato? (resuelve el punto 13)
- `games.csv` / `club_games.csv` → nombres exactos de campos de competencia (para identificar Champions/Europa/Conference, punto 5) y de resultado (para puntos/posición en tabla, punto 6)
- `game_lineups.csv` → si tiene `position` a nivel de alineación (no solo la posición "principal" de `players.csv`) — sería una vía directa para el chequeo de cambio de posición que quedó pendiente del punto 5 de Alan

## Paso 1 — Orden sugerido de construcción (de más simple a más compleja)

1. **Objetivos deportivos** (#6) — es agregación directa de resultados de partidos, no requiere cruces complejos.
2. **Calidad del plantel** (#3) — agregación de valuaciones por club-temporada, ya tenés la lógica de agregación de valores en el pipeline actual.
3. **Participación en competencias internacionales** (#5) — depende de cómo esté codificado el tipo de competencia en `competitions.csv`/`games.csv`, a confirmar en el Paso 0.
4. **Competencia interna por el puesto** (#12) — requiere cruzar alineaciones con posición amplia, similar a lo que ya usamos para la densidad edad×posición.
5. **Compañeros de plantel** (#4) — más laboriosa, requiere alinear jugador-temporada con el resto de la plantilla que compartió cancha.
6. **Reputación de club vendedor** (#11) — la más laboriosa, requiere una ventana móvil de N años sobre `transfers.csv` por club.

¿Empezamos corriendo el Paso 0 para confirmar el esquema real, o preferís que ya te arme el esqueleto de función para la primera variable (objetivos deportivos) asumiendo los nombres de campo típicos de este dataset, y lo ajustamos si el esquema difiere?
