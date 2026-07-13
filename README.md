# Tesis de Maestría — Predicción de desarrollo de jugadores jóvenes de fútbol

**Aislando el rendimiento individual del contexto de equipo y liga**

*Gianfranco Ganicoche — Maestría en Ciencia de Datos, Universidad de Montevideo*

## Tema

¿Es posible aislar la contribución individual de un jugador joven al crecimiento de su
valor de mercado, separándola de los efectos de equipo, liga y contexto, y usar esa
estimación para predecir su desarrollo futuro?

El scouting tradicional evalúa el rendimiento observado de un jugador, pero no puede
separar sistemáticamente cuánto de ese rendimiento es mérito individual y cuánto es
producto del contexto: la calidad del equipo, la liga, el sistema táctico. Esta tesis
construye un modelo que busca aislar esa contribución individual y usarla para predecir
el desarrollo de jugadores sub-23, con la mira puesta en el modelo de negocio de clubes
como Ajax o AZ Alkmaar: identificar talento joven subvalorado antes que el resto del
mercado.

**Estado actual (julio 2026):** el diseño original (comparación A/B de modelos con y sin
ajuste por contexto) se reformuló tras un chequeo empírico que mostró ganancias sustanciales
al pasar de pares fijos T→T+3 a trayectorias completas de carrera. El diseño vigente
combina una curva de desarrollo por edad con un enfoque de descomposición/recomposición
de la habilidad individual (inspirado en *Transfer Portal*, Dinsdale & Gallagher 2022).
Ver `docs/hipotesis_y_diseno_v2.md` para el detalle completo y las alternativas en
evaluación con el tutor.

**Tutor:** Alan Silberman.

## Variable dependiente

Crecimiento del valor de mercado en Transfermarkt para jugadores sub-23, usando el panel
histórico completo de valuaciones (no un único corte T→T+3 fijo). Justificación completa,
incluyendo limitaciones reconocidas y evidencia de confiabilidad de Transfermarkt como
fuente, en `docs/justificacion_variable_dependiente.md`.

## Fuente de datos

[`davidcariboo/player-scores`](https://www.kaggle.com/datasets/davidcariboo/player-scores)
(Kaggle) — valor de mercado histórico, apariciones, transferencias, alineaciones y datos
de competiciones para ligas europeas. No depende de licencias Opta/FBref (ver nota sobre
el corte de licencia de enero 2026 en `docs/tema_tesis.md`, sección 2).

Se evaluaron fuentes alternativas (Understat, StatsBomb Open Data,
`hubertsidorowicz/football-players-stats`) para complementar con métricas avanzadas de
rendimiento (xG, xA); ninguna ofrece la amplitud de ligas necesaria — todas cubren solo
las 5-6 grandes ligas europeas, mientras que buena parte de la muestra sub-23 de interés
está en ligas secundarias. `player-scores` sigue siendo la única fuente con la amplitud
requerida.

## Estructura del repositorio

```
├── docs/
│   ├── tema_tesis.md                          # Punteo general, actualizado
│   ├── justificacion_variable_dependiente.md  # Justificación formal de la VD
│   ├── hipotesis_y_diseno_v2.md                # Diseño vigente, con alternativas
│   ├── inventario_variables_contexto.md        # Mapeo de factores de contexto a datos
│   └── bitacora/                               # Registro cronológico de sesiones
│       └── AAAA-MM-DD_[descripción].md
├── src/
│   ├── panel_pipeline.py                       # Pipeline del panel T→T+3 (diseño v1)
│   └── construir_variables_contexto.py         # Variables de contexto (liga, equipo,
│                                                #   entrenador, táctica, etc.)
├── bibliografia/
│   └── bibliografia.md                         # Papers y fuentes, por tema
├── data/
│   ├── raw/
│   └── processed/
└── notebooks/
```

## Estado de las variables de contexto

Construidas y validadas en `src/construir_variables_contexto.py` (7 de 8 planificadas):

| Variable | Estado |
|---|---|
| Objetivos deportivos (posición, puntos) | ✅ |
| Calidad de plantel por temporada | ✅ |
| Competencias internacionales de club | ✅ |
| Continuidad técnica (entrenador) | ✅ |
| Sistema táctico (formación) | ✅ (confiabilidad advertida — ver docstring) |
| Competencia interna por puesto | ✅ |
| Reputación de club vendedor | ✅ (score continuo de baja cobertura + flag binario complementario) |
| Compañeros de plantel | ⏳ pendiente |

Cada función incluye, en comentarios, el razonamiento de construcción, los problemas de
calidad de datos encontrados (ej. `clubs.csv` es un snapshot y no un panel histórico,
`current_club_id` de `player_valuations.csv` tampoco es histórico, huecos sistemáticos
en `transfers.csv`) y la validación aplicada antes de dar cada variable por confiable.

## Metodología (resumen, ver `docs/hipotesis_y_diseno_v2.md` para el detalle)

1. Panel de trayectorias completas de carrera (no pares T→T+3 fijos), sub-23.
2. Curva de desarrollo por edad, estimada sobre carrera completa (no truncada a sub-23),
   con posible interacción por posición testeada formalmente.
3. Modelo de efectos mixtos/shrinkage para aislar la habilidad individual (α_i) del
   efecto de contexto (liga, equipo, y las variables de `construir_variables_contexto.py`).
4. Recomposición para predicción a futuro: persistencia de α_i tratada como hipótesis
   testeable contra datos históricos; contexto futuro (club/liga) como escenario
   explícito, no supuesto oculto.

## Limitaciones reconocidas (alcance de esta tesis, no fallas de diseño)

- Cobertura geográfica: solo ligas europeas, por disponibilidad de datos. Extensión a
  Sudamérica queda como trabajo futuro.
- El valor de mercado captura percepción y exposición mediática, no solo rendimiento —
  es la mejor proxy disponible, no una medida perfecta de desarrollo futbolístico.
- Reconstrucción de club histórico de jugador tiene cobertura parcial (~56%), fuertemente
  correlacionada con edad — más débil justo en las valuaciones más tempranas de la
  población de interés.
- Dependencia de una única fuente de datos con amplitud suficiente (`player-scores`),
  documentada como riesgo estructural.

## Bibliografía

Ver `bibliografia/bibliografia.md`, organizada por tema: confiabilidad de Transfermarkt,
shocks de mercado, identificación de talento, modelos de negocio de clubes de desarrollo,
núcleo metodológico (fixed effects / plus-minus / modelos predictivos), y estabilidad
temporal de métricas de rendimiento.
