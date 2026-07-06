# Bitácora — Entrada 3: Construcción del panel de datos y primer modelo

**Fecha:** 05/07/2026

## Resolución de entorno de trabajo

Positron fallaba al iniciar sesiones de Python/R con el error "The supervisor process
exited unexpectedly during startup" (Kallichore). Se descartaron como causa el antivirus
y el bloqueo de Windows SmartScreen. Causa real identificada corriendo `kcserver.exe` a
mano en `cmd.exe`: faltaba el **Microsoft Visual C++ Redistributable**
(`VCRUNTIME140.dll` no encontrada). Solución: instalar
[`vc_redist.x64.exe`](https://aka.ms/vs/17/release/vc_redist.x64.exe) desde Microsoft.
Positron quedó funcional.

## Fuente de datos

Se confirmó `davidcariboo/player-scores` (Kaggle) como fuente principal, descargable vía
`kagglehub`. Tablas clave: `players.csv`, `player_valuations.csv`, `clubs.csv`,
`competitions.csv`. Primer ejemplo de exploración: la serie de valor de mercado de
Erling Haaland (player_id 418560), que ilustra perfectamente el problema de
identificación que motiva la tesis (cada salto de valor viene acompañado de un salto de
liga: NO1 → A1 → L1 → GB1).

## Diagnóstico de cobertura temporal

- Rango de datos: 2000-01-20 a 2026-06-12, pero 2000-2001 son registros aislados (ruido,
  descartados).
- Casi todas las ligas top comparten fecha mínima idéntica (2004-10-04) — huella de una
  carga histórica retroactiva (backfill), no de cobertura orgánica.
- Densidad confiable recién se estabiliza desde **~2010** en adelante (2.300 registros en
  2004 → 13.800 en 2010 → 59.500 en 2022). Se fijó `ANIO_MIN_COBERTURA = 2010` para el
  panel.
- Promedio de ~15.8 valuaciones por jugador a lo largo de su carrera — frecuencia
  suficiente para construir pares T→T+3 sin perder muestra por granularidad.

## Construcción del panel T→T+3

- Función `construir_pares`: para cada valuación de un jugador, busca la valuación más
  cercana a T+3 dentro de una tolerancia de 120 días.
- **Thinning**: se redujo a una ventana por jugador-año (`groupby(["player_id",
  "anio_T"]).first()`) para bajar la pseudo-replicación de ventanas semestrales
  altamente solapadas.
- **Filtro sub-23**: edad ≤ 20 en T (para que el jugador siga siendo joven en T+3).
  Distribución de edad razonable (mediana 18.9, sin bulto artificial en el extremo
  joven — los 41 casos <16 años son ruido despreciable, 0.13% de la muestra).
- Panel final: **30.615 observaciones, 16.428 jugadores únicos** (tras limpiar
  `position == "Missing"`).

## Hallazgos de calidad de datos

- **Cobertura por liga desigual**: Italia (IT1) y Turquía (TR1) concentran muchos más
  jugadores sub-23 valuados que España o Inglaterra. Se verificó que **no** es un
  artefacto de frecuencia de actualización (densidad de valuaciones por jugador similar
  entre ligas, ~11-13) — es amplitud real de cobertura (más jugadores jóvenes distintos
  entran al radar en esas ligas).
- **Liga faltante (`liga_T` con NaN)**: 31% de NaN inicial. Se correlaciona con
  `valor_T` bajo, no con edad. Se resolvió con forward/backward fill por jugador sobre
  el historial completo de valuaciones, bajando el NaN a 3.6% irreductible (jugadores
  sin ninguna liga asignada en ningún punto de su historial) — esas filas se dropearon
  para el panel principal.
- **Casos de "descubrimiento"** (crecimiento_log > 4): identificados con nombre y
  apellido — Mbappé, João Félix, Rúben Dias, Kai Havertz, De Ligt, Chiesa, Zaniolo,
  Caicedo, Fermín López, Javi Guerra, entre otros. Todos arrancan en el piso de
  valuación de Transfermarkt (25-100k€) y explotan a 20-200M€ en la misma ventana. Se
  documentó como fenómeno distinto de "desarrollo incremental" (ver
  `docs/justificacion_variable_dependiente.md`, sección 6).

## Variable dependiente

`crecimiento_log = log(valor_T3) - log(valor_T)`. Distribución razonable: mediana 1.25,
IQR [0.41, 2.20], sin ceros ni nulos en la muestra final. Se creó también un flag
`valor_T_piso` para identificar los casos de descubrimiento en análisis futuros.

## Primer modelo de efectos fijos (v1)

`crecimiento_log ~ liga_T + año_T + posición`, vía `linearmodels.PanelOLS`, errores
clusterizados por jugador.

- **R² Within ≈ -0.02**: confirma que la mayoría de los jugadores tiene 1-2 ventanas
  observadas — insuficiente variación intra-jugador para efectos fijos individuales
  confiables. Este es el hallazgo metodológico central de la sesión: justifica migrar a
  un modelo de efectos mixtos/shrinkage (tipo RAPM) en la próxima etapa.
- **Liga**: Argentina, Brasil, Francia y Suiza (código `C1`) con mayor crecimiento
  relativo; Italia, Ucrania, Turquía, Grecia, Escocia y Rusia con menor crecimiento —
  todas altamente significativas.
- **Año**: patrón en forma de "U" (2011-2020 negativo respecto a 2010, recuperación
  desde 2021) — posible artefacto de cobertura creciente en años tempranos, a
  investigar antes de interpretar como tendencia de mercado real.
- **Posición**: defensores y mediocampistas crecen algo más que delanteros (base);
  arqueros notablemente menos (-0.27) — consistente con la intuición futbolística.

## Organización de código y repositorio

- Pipeline completo organizado en `src/panel_pipeline.py` (10 funciones, parámetros
  centralizados como constantes).
- Repositorio de GitHub creado: `github.com/gianfrancoganicoche/Tesis_UM`, con
  estructura `src/`, `docs/`, `docs/bitacora/`, `bibliografia/`, `data/raw/`,
  `data/processed/`, `notebooks/`.
- Documentación actualizada: `tema_tesis.md` reescrito para reflejar el pivot de fuente
  de datos y el estado real de la metodología; toda la documentación migrada de `.docx`
  a `.md` para facilitar lectura y versionado en GitHub.

## Próximos pasos

- Modelo de efectos mixtos/shrinkage para estimar α_i individual.
- Análisis de robustez de horizonte temporal (T+1 a T+4).
- Investigar el patrón en "U" del efecto año (¿artefacto de cobertura o tendencia real?).
- Definir features de rendimiento básico (goles, asistencias, minutos) desde
  `appearances.csv` para la Etapa 2.
