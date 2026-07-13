# Bitácora — Entrada: Devolución de Alan, reformulación de diseño, y construcción de variables de contexto

**Fecha:** 12/07/2026
**Contexto:** Sesión larga, dividida en varios bloques. Primer procesamiento formal de la devolución escrita de Alan Silberman al punteo inicial (`Ganicoche_RespuestaAPunteoInicial.docx`).

## Bloque 1 — Procesamiento de la devolución de Alan y reformulación de hipótesis

La devolución de Alan plantea 9 puntos organizados por prioridad. Estado de resolución tras esta sesión:

| Punto | Estado |
|---|---|
| 1. Pregunta e hipótesis | Reformulado en profundidad (ver abajo) |
| 2. Definición conceptual | Ya resuelto en sesión anterior (`justificacion_variable_dependiente.md`) |
| 3. Componentes del contexto | Inventariado y mayormente construido (ver Bloque 2) |
| 4. Validez entre ligas concentradas | Pendiente — sesión futura, junto con calidad de datos |
| 5. Posiciones no fijas | Decisión documentada en v1; con `game_lineups.csv` ahora hay vía directa de medición pendiente de explotar |
| 6. Ventana temporal y drift | Resuelto conceptualmente (ver reformulación) |
| 7. Calidad de datos | Parcial, se descubrieron varios problemas de calidad concretos (ver Bloque 2) |
| 8. Sesgos estadísticos | Parcial |
| 9. Scouting vs. predicción | Ya resuelto en sesión anterior |

### La reformulación de fondo

Se discutió en profundidad el diseño original de comparación A/B (features crudas vs. ajustadas por contexto, prediciendo `crecimiento_log` en ventana fija T→T+3) y se identificaron tres problemas: (1) con modelos flexibles, "más variables" casi siempre gana en RMSE/MAE de forma poco informativa; (2) la ventana fija T→T+3 es arbitraria y da solo 1.86 ventanas/jugador; (3) la edad no estaba tratada como variable central pese a ser probablemente el factor más determinante en la población sub-23.

**Chequeo empírico decisivo:** pasar de pares fijos T→T+3 a trayectorias completas de carrera da **5.33x más observaciones** (163.150 vs. 30.615) y **6.43 ventanas/jugador** (vs. 1.86). La curva de valor por edad, estimada sobre carrera completa (no solo sub-23, porque truncar en 23 nunca deja ver el pico ni el declive), muestra la forma esperada: sube sostenido desde los 16, meseta de pico entre 26-28 años, declive sostenido hasta ~40. Evidencia preliminar de heterogeneidad por posición (arqueros mantienen densidad de datos mucho más tarde que jugadores de campo).

**Diseño resultante (documentado en `docs/hipotesis_y_diseno_v2.md`):** tres alternativas presentadas — (1) comparación A/B clásica, (2) feature importance/SHAP sobre modelo único, (3) descomposición/recomposición estilo *Transfer Portal* (Dinsdale & Gallagher 2022) con curva de edad, recomendada por la evidencia empírica. La alternativa 3 no descarta el testeo de hipótesis: se conserva como test formal de interacción edad×posición (modelo restringido vs. con interacción, AIC/BIC).

**Matiz importante agregado (sección 3.1 del documento):** la recomposición a futuro requiere asumir persistencia de habilidad relativa (α_i) y contexto futuro. Se resolvió tratando la persistencia de α_i como **hipótesis testeable contra datos históricos** (proyección ingenua vs. valor real observado), no como supuesto ciego; y el contexto futuro (club/liga) como **escenario explícito** que provee el usuario del modelo, no como supuesto oculto.

**Referencia bibliográfica agregada:** Sidorowicz (2026), *Year-to-Year Metric Stability in Elite Football*, encuentra que jugadores sub-23 son sistemáticamente menos estables año a año que veteranos — evidencia académica directa a favor del tratamiento de α_i como hipótesis testeable. Agregado a `bibliografia.md`.

**Fuentes de datos alternativas evaluadas y descartadas:** Understat (solo 6 grandes ligas), StatsBomb Open Data (cobertura muy acotada, competiciones puntuales), `hubertsidorowicz/football-players-stats` (también limitado a Big 5). Ninguna resuelve el problema de amplitud que sí tiene `davidcariboo/player-scores`. Confirmado: no hay mejor alternativa gratuita de amplitud disponible.

## Bloque 2 — Inventario y construcción de variables de contexto

Se armó `docs/inventario_variables_contexto.md` con los 15 factores de contexto (9 de la devolución de Alan + 6 identificados en sesión: reputación de club vendedor, competencia interna por puesto, situación contractual, pertenencia a grupo multi-club, continuidad técnica). Tras verificar el esquema real de `player-scores`, se confirmó que 12 de los 15 son construibles o directos (solo pertenencia a grupo multi-club queda fuera de alcance).

Se construyó `src/construir_variables_contexto.py` con 7 de las 8 variables planificadas, cada una con reconocimiento de datos previo, validación posterior (incluyendo validación cualitativa contra casos futbolísticos conocidos), y documentación in-code de cada decisión:

1. **Objetivos deportivos** (posición en tabla, puntos, diferencia de gol) — desde `club_games.csv`, filtrado a `competition_type == "domestic_league"`.
2. **Calidad de plantel por temporada** — requirió resolver primero la reconstrucción de club histórico por jugador (ver hallazgo de datos abajo).
3. **Competencias internacionales de club** — hallazgo importante: Europa League y Conference League están mal categorizadas bajo `competition_type == "other"` en vez de `"international_cup"`; hay que filtrar por `competition_id` explícito.
4. **Continuidad técnica (entrenador)** — validada con caso real (Denizlispor 2020, 7 entrenadores distintos en una temporada de descenso, incluyendo un interino que vuelve).
5. **Sistema táctico (formación)** — validada cualitativamente en ambos extremos: estable (Inter Milan 3-5-2 bajo Inzaghi, Barcelona 4-3-3 tiki-taka, Athletic Bilbao) e inestable (Brighton bajo Graham Potter, conocido por flexibilidad táctica real; PSG en crisis de proyecto). Documentada advertencia de confiabilidad: el dato de formación es interpretación editorial, no hecho verificable como el entrenador.
6. **Competencia interna por puesto** — desde `game_lineups.csv`, solo alineaciones titulares. Se evaluó y descartó usar ML/NLP para el mapeo de posiciones (vocabulario cerrado, un diccionario manual es más preciso y auditable); se usó `difflib.get_close_matches` como red de seguridad liviana en caso de categorías no contempladas.
7. **Reputación de club vendedor** — la más compleja. Requirió construir un score de prestigio de liga desde cero (mediana de `market_value_in_eur` de transferencias entrantes sub-23 por liga, con piso de confiabilidad). Cobertura final baja (4.2% con el score continuo) llevó a construir una segunda versión como flag binario (`club_vendedor_reconocido`), con cobertura mucho mayor (46.8%) al no requerir promediar múltiples observaciones.

**Pendiente:** compañeros de plantel (la variable más laboriosa, cruce de alineaciones con valuaciones por fecha) — queda para la próxima sesión.

### Hallazgos de calidad de datos (relevantes para la sección de limitaciones de la tesis)

- **`clubs.csv` es un snapshot, no un panel histórico** (una fila por club, con el dato más reciente disponible) — confirmado con `club_id` sin duplicados y `last_season` disperso entre 2012-2025. No sirve para reconstruir contexto histórico de club.
- **`current_club_id` en `player_valuations.csv` también es snapshot**, no histórico — confirmado con el caso Haaland (club_id=281, Manchester City, constante en sus 26 valuaciones desde 2016, pese a haber jugado en 4 clubes reales distintos).
- **`transfers.csv` tiene huecos sistemáticos**: 87.8% de los jugadores valuados no tienen ningún registro; de los que sí tienen partidos jugados en `appearances.csv`, el 54.4% jugó en múltiples clubes sin que quedara registrado en `transfers.csv` (caso Haaland: 0 filas en `transfers.csv` pese a su historial real de transferencias).
- **Solución de reconstrucción de club histórico:** combinar `transfers.csv` (prioridad, cuando existe) con `appearances.csv` (respaldo). Cobertura final combinada: 55.6% (44.4% de NaN), fuertemente correlacionado con edad — 9% de cobertura en 0-16 años, subiendo a 58% en 23+. Limitación real y documentada, no aleatoria: valuaciones muy tempranas (pre-debut, pre-transferencia formal) quedan sin club reconstruible.
- **`games.csv` tiene su propio piso de cobertura, distinto al de `player_valuations.csv`**: denso y consecutivo recién desde 2012 (no 2010). Se agregó `ANIO_MIN_COBERTURA_GAMES = 2012` como constante separada.
- **Convención de `season` en `games.csv`** es año de inicio de temporada, no año calendario — se agregó `derivar_season_desde_fecha()` para alinear con `player_valuations.csv` y evitar desalineamientos silenciosos entre variables al cruzarlas.
- **`is_win` en `club_games.csv` es `int64` (1/0), no booleano** — usarlo directamente en `.loc[]` como si fuera máscara booleana produce un `KeyError` confuso (pandas lo interpreta como lista de índices a buscar, no como filtro).
- **Bundesliga alemana y austríaca comparten el mismo `name`** en `competitions.csv` ("bundesliga") — hay que desambiguar siempre por `country_name`.
- **Lección metodológica general (se repitió dos veces en la sesión):** un piso de confiabilidad por muestra chica debe aplicarse sobre la cantidad de observaciones que efectivamente entran al cálculo final, no sobre el universo de eventos previo a cualquier filtro. Se encontró explícitamente con `reputacion_vendedor` (Dinamo Zagreb 2018: 8 ventas totales pasaban un piso ingenuo, pero solo 1 tenía score de liga disponible).
- **Un flag binario de "¿ocurrió alguna vez?" no tiene el mismo problema de muestra chica que un score continuo/promedio** — no necesita varias observaciones para ser confiable, porque no está estimando una media. Se aplicó para resolver la baja cobertura de `reputacion_vendedor`.

## Archivos creados o actualizados en esta sesión

- `docs/hipotesis_y_diseno_v2.md` (nuevo, reemplaza conceptualmente a v1)
- `docs/inventario_variables_contexto.md` (nuevo)
- `docs/bibliografia.md` (actualizado, nueva sección de estabilidad temporal de métricas)
- `src/construir_variables_contexto.py` (nuevo, 7 de 8 variables de contexto construidas y validadas)

## Próximos pasos

- Terminar la última variable de contexto pendiente: compañeros de plantel.
- Decidir con Alan cuál de las 3 alternativas de diseño seguir (llevar `hipotesis_y_diseno_v2.md` a la próxima tutoría).
- Retomar el punto 4 de la devolución de Alan (validez entre ligas concentradas / fortaleza de rivales) en sesión dedicada, junto con calidad de datos por país/año (punto 7).
- Pendiente de larga data: survivorship bias (punto 8), todavía sin abordar en profundidad.
