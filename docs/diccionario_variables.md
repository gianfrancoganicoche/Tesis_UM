# Diccionario de variables — candidatas para el modelo

*Referencia unificada de todas las variables construidas o planificadas hasta el
13/07/2026: contexto (`src/construir_variables_contexto.py`), rendimiento
(`src/construir_variables_rendimiento.py`), y atributos del jugador
(`hipotesis_y_diseno_v2.md`, sección 3.3). Actualizar cada vez que se agregue,
valide, o descarte una variable.*

## Leyenda

- **Estado:** ✅ Construida y validada · 🔨 Planificada, sin correr · ⚠️ Construida con advertencia de confiabilidad · ⏸ Pendiente de decisión
- **Nivel:** unidad sobre la que está definida la variable (jugador-temporada, club-temporada, jugador-liga, etc.)
- **Cobertura:** dato de sesión cuando se verificó; "sin verificar" si es de `construir_variables_rendimiento.py`

---

## A. Curva de edad y variable dependiente (núcleo del modelo)

| Variable | Nivel | Descripción | Fuente | Estado |
|---|---|---|---|---|
| `edad` | jugador-temporada | Edad calculada desde `date_of_birth`, a la fecha de valuación | `players.csv` + `player_valuations.csv` | ✅ |
| `valor_mercado` (VD) | jugador-temporada | Última valuación registrada en la temporada (regla de resumen fijada en sesión) | `player_valuations.csv` | ✅ |
| `posicion_amplia` | jugador | 4 categorías: arquero, defensor, mediocampista, delantero | `players.csv`: `position`, normalizado | ✅ |

---

## B. Variables de contexto (`construir_variables_contexto.py` — 8/8 construidas y validadas)

| Variable | Nivel | Descripción | Estado | Notas clave |
|---|---|---|---|---|
| `posicion_final`, `posicion_promedio`, `pct_victorias`, `diferencia_gol_promedio`, `puntos_por_partido` | club-temporada | Objetivos deportivos: posición en tabla, resultado | ✅ | Filtro `competition_type == "domestic_league"`; 94 casos <15 partidos son casi todos temporadas en curso, no error |
| `valor_total_plantel`, `valor_promedio_plantel`, `jugadores_valuados` | club-temporada | Calidad de plantel | ✅ | Requiere club histórico reconstruido (ver sección E); NO usar `clubs.csv` (snapshot) |
| `partidos_europeos`, `fase_maxima_alcanzada`, `jugo_fase_grupos_o_mas`, `competencias_distintas` | club-temporada | Participación en competencias internacionales | ✅ | Filtrar por `competition_id` explícito (`CL`,`CLQ`,`EL`,`ELQ`,`UCOL`,`ECLQ`,`USC`), NO por `competition_type` (Europa League/Conference mal categorizadas como `"other"`) |
| `entrenadores_distintos`, `hubo_cambio_entrenador`, `entrenador_titular` | club-temporada | Continuidad técnica | ✅ | Validado con caso real (Denizlispor 2020, 7 entrenadores) |
| `formacion_predominante`, `formacion_base_predominante`, `estructuras_base_distintas` | club-temporada | Sistema táctico | ⚠️ | Dato de interpretación editorial, no hecho verificable — usar `estructuras_base_distintas` como señal principal, formación textual como descriptivo secundario |
| `jugadores_distintos`, `titularidades_totales` (por posición amplia) | club-temporada-posición | Competencia interna por el puesto | ✅ | Solo `starting_lineup`, no suplentes |
| `reputacion_vendedor` | club-temporada | Score continuo de prestigio de ligas de destino en ventas sub-23 (ventana móvil 5 años) | ✅ | Cobertura baja: 4.2% del panel. Piso aplicado sobre ventas CON score, no sobre total (lección de sesión) |
| `club_vendedor_reconocido`, `ventas_a_liga_top` | club-temporada | Flag binario de reputación de vendedor | ✅ | Cobertura 46.8% — usar en vez del score continuo cuando se necesite cobertura amplia |
| `companieros_valor_promedio`, `companieros_distintos` | jugador-temporada | Valor de compañeros de plantel (leave-one-out) | ✅ | Validado con Haaland (Salzburg→Dortmund→Man City, saltos coherentes) |

---

## C. Variables de rendimiento individual (`construir_variables_rendimiento.py` — 6 planificadas, sin correr)

| Variable | Nivel | Descripción | Estado | Posiciones donde mejor aplica |
|---|---|---|---|---|
| `goles_90`, `asistencias_90`, `contribucion_gol_90` | jugador-temporada | Producción ofensiva básica | 🔨 | Delanteros, mediocampistas |
| `tarjetas_90` | jugador-temporada | Disciplinaria | 🔨 | Todas (señal débil) |
| `pct_minutos_disponibles` | jugador-temporada | Minutos jugados / minutos posibles del equipo | 🔨 | Todas — proxy de confianza del cuerpo técnico |
| `goles_recibidos_90` (como titular) | jugador-temporada | Proxy defensivo | 🔨 | Arqueros (central), defensores (más ruidoso) |
| `goles_recibidos_ajustados_90` | jugador-temporada | Igual, ponderado por fuerza ofensiva del rival | 🔨 | Arqueros, defensores — adelanta parte del punto 4 de Alan |
| `diferencial_con_sin` | jugador-temporada | % victorias del equipo con el jugador titular vs. sin él | 🔨 | Todas las posiciones (estilo *Plus-Minus Soccer*) |
| `participacion_produccion` | jugador-temporada | (goles+asistencias del jugador) / goles totales del equipo | 🔨 | Delanteros, mediocampistas |
| `edad_debut` | jugador | Edad en la primera aparición registrada | 🔨 | Todas — proxy de precocidad |

**Extensión opcional, solo para H1a-equivalente (población de primera división europea):** xG/xGA vía cruce por nombre (fuzzy matching) con Understat — mejora señal ofensiva, no resuelve bien la defensiva. No aplica a ligas fuera de las top 6 cubiertas por esa fuente.

---

## D. Atributos adicionales del jugador (`hipotesis_y_diseno_v2.md`, sección 3.3)

| Variable | Nivel | Descripción | Estado | Notas |
|---|---|---|---|---|
| `es_comunitario` | jugador | Ciudadanía en país con libre circulación UE/EEE + Suiza | ✅ | Cobertura 99.5%. **Limitación:** no captura doble ciudadanía por ascendencia — subestima la proporción real |
| `foot` | jugador | Pie hábil | 🔨 | Prima de mercado documentada para zurdos en extremos/laterales |
| `height_in_cm` | jugador | Altura | 🔨 | Estandarizar por posición (mismo z-score que rendimiento). Relevante para arqueros, centrales, delanteros de área |

**Descartadas explícitamente (no por descuido):**
- `agent_name` — riesgo de sesgo subjetivo no defendible sin criterio objetivo de "reputación de agente".
- `sub_position` (granularidad fina) — sacrificada por densidad de datos edad×posición; posible desagregación futura.
- `international_caps`/`international_goals` — ya cubiertas en `justificacion_variable_dependiente.md` (shocks de torneos), no duplicar.

---

## E. Variables auxiliares (insumo de otras, no entran directo al modelo)

| Variable | Nivel | Descripción | Usada por |
|---|---|---|---|
| `club_id_final` (club histórico reconstruido) | jugador-fecha | Club real del jugador en cada valuación, combinando `transfers.csv` (prioridad) + `appearances.csv` (respaldo) | Calidad de plantel, compañeros de plantel |
| `score_prestigio_liga` | liga | Mediana de `market_value_in_eur` de transferencias entrantes sub-23 por liga, piso de 10 transferencias | Reputación de club vendedor |
| `mapa_club_liga` (club→liga por temporada) | club-temporada | Liga doméstica real de cada club, derivada de partidos jugados | Reputación de club vendedor, definición de población H1 |

**Limitación transversal de `club_id_final`:** 44.4% de NaN global, fuertemente correlacionado con edad (9% de cobertura en 0-16 años, 58% en 23+). Afecta a toda variable que dependa de él.

---

## F. Resumen de estandarización requerida antes del modelo

Ninguna variable de rendimiento (sección C) ni las estructurales de altura (sección D) son comparables cruda entre posiciones. **Regla fija:** estandarizar (z-score) dentro de grupo posición-temporada antes de entrar a la descomposición — no una definición de rendimiento distinta por posición, es preprocesamiento.

## G. Cuenta total de candidatas

- Contexto: 8 construidas (∼20 columnas derivadas en total, contando variantes).
- Rendimiento: 8 planificadas.
- Atributos: 1 construida + 2 planificadas.
- **Total: ~19 variables candidatas**, antes de cualquier reducción por importancia. Ver `hipotesis_y_diseno_v2.md`, sección 3.2, "Plan de reducción": no hay compromiso de usarlas todas — la selección final depende del análisis de importancia en la etapa predictiva.
