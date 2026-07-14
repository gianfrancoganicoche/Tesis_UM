# Tesis de Maestría — Punteo actualizado

**Predicción de desarrollo de jugadores jóvenes de fútbol**
Aislando el rendimiento individual del contexto de equipo y liga
*Gianfranco Ganicoche*

> **Pregunta de investigación central**
> ¿Es posible aislar la contribución individual de un jugador joven al crecimiento de su valor de mercado, separándola de los efectos de equipo, liga y shocks mediáticos, y usar esa estimación para predecir su desarrollo futuro?

> **Hipótesis central, formalizada (13/07/2026)**
> H1: El contexto de equipo y liga explica una porción estadísticamente significativa de la varianza en el valor de mercado de jugadores sub-23, más allá de lo que explica la curva de desarrollo por edad. Testeada con test de razón de verosimilitud entre un modelo restringido (solo curva de edad + efecto individual) y el modelo completo (+ efectos de contexto). H2: el efecto del contexto varía según la posición del jugador (interacción edad×posición). Ver `docs/hipotesis_y_diseno_v2.md` para el detalle completo, incluidas dos alternativas de diseño consideradas y no adoptadas.

## 1. El tema

El scouting tradicional evalúa el rendimiento actual de un jugador, pero no puede separar cuánto de ese rendimiento es mérito individual y cuánto es producto del contexto: el equipo que lo rodea, el sistema táctico, la calidad de la liga. Esta tesis propone construir un modelo que aísle esa contribución individual y la use para predecir el desarrollo futuro de jugadores jóvenes.

El modelo de negocio de referencia son los clubes holandeses (Ajax, AZ Alkmaar, Feyenoord) que identifican talento joven subvalorado, lo desarrollan, y lo venden a un múltiplo de su precio de compra. Su ventaja competitiva es identificar potencial antes que los demás. Esta tesis busca sistematizar ese proceso con datos.

> **Variable dependiente — redefinida (13/07/2026)**
> Valor de mercado en Transfermarkt de jugadores sub-23, descompuesto como `valor = curva_edad(edad, posición) + contexto + rendimiento + α_i + ε`, sobre trayectorias completas de carrera (no un corte fijo T→T+3). α_i es la habilidad individual aislada, portable entre contextos — el objetivo aplicado central de la tesis. Unidad de análisis: jugador-temporada (última valuación registrada dentro de cada temporada). Justificación conceptual completa en `docs/justificacion_variable_dependiente.md`; diseño formal del modelo en `docs/hipotesis_y_diseno_v2.md`.
>
> *(Nota histórica: el diseño original usaba crecimiento logarítmico T→T+3 como variable dependiente. Se abandonó tras confirmar empíricamente que el panel de pares fijos daba solo 1.86 ventanas/jugador —insuficiente para identificar efectos individuales— contra 6.43 ventanas/jugador con trayectorias completas. Ver sección 3 y bitácora del 12-13/07/2026 para el detalle de la reformulación.)*

## 2. Por qué este tema tiene sentido

### La ventaja sobre el scout humano es real

Un scout humano no puede aislar sistemáticamente el efecto del equipo en el rendimiento de un jugador. Ve a un delantero del City marcar 20 goles y no puede cuantificar cuántos de esos goles son producto de jugar con compañeros de élite. Un modelo sí puede hacerlo, y aplicarlo consistentemente a miles de jugadores en paralelo.

### El problema de datos

El planteo original asumía FBref como fuente de métricas avanzadas de rendimiento (xG, npxG, progressive passes, pressures) para más de 30 ligas europeas. Esto cambió: el 20 de enero de 2026, Stats Perform (Opta) terminó el acuerdo de datos con FBref y exigió eliminar las estadísticas avanzadas del sitio. Se documenta como riesgo estructural de dependencia de terceros (ver sección 4).

La fuente de datos principal es el dataset [`davidcariboo/player-scores`](https://www.kaggle.com/datasets/davidcariboo/player-scores) (Kaggle), que no depende de Opta: incluye valor de mercado histórico, apariciones (goles, asistencias, minutos), transferencias, alineaciones por partido, y datos de competiciones — pero no métricas avanzadas de eventos (xG, progressive passes, pressures). Se evaluaron fuentes alternativas (Understat, StatsBomb Open Data, `hubertsidorowicz/football-players-stats`) — ninguna ofrece la amplitud de ligas necesaria, todas cubren solo las 5-6 grandes ligas europeas. `player-scores` sigue siendo la única fuente con la amplitud requerida para la población completa de la tesis (ver sección 3, población de estudio).

### El aporte para un club es explicable en una oración

"Este modelo te dice cuánto vale este jugador independientemente de dónde juega y de cuán desarrollado está por edad — y permite simular cuánto valdría en otro contexto (otro club, otra liga)."

## 3. Metodología (reformulada 13/07/2026 — reemplaza por completo la versión anterior)

Detalle técnico completo en `docs/hipotesis_y_diseno_v2.md`. Resumen operativo:

### 3.1 Por qué se abandonó el diseño de pares fijos T→T+3

Se consideraron tres alternativas de diseño (comparación A/B clásica, feature importance/SHAP, descomposición/recomposición con curva de edad — la adoptada). Las tres comparten el mismo punto de partida (trayectorias completas de carrera, no pares fijos), pero difieren en si necesitan buscar un horizonte de predicción óptimo como paso previo. La adoptada no lo necesita: predice el nivel de valor/habilidad en cualquier edad, no el crecimiento entre dos puntos — el horizonte deja de ser un parámetro de diseño y pasa a ser una consulta libre sobre la curva de edad ya ajustada.

### 3.2 Curva de desarrollo por edad

Estimada sobre la **carrera completa** de todos los jugadores del dataset (no truncada a sub-23 — truncar impide ver el pico y el declive reales). Confirmado empíricamente: forma de U invertida, sube sostenido desde los 16, meseta de pico entre 26-28 años, declive sostenido hasta ~40. Sostenida por literatura específica agregada en sesión: Dendir (2016), Kalén et al. (2019), Säfvenberg et al. (2024) — este último es el precedente metodológico más cercano (modelo jerárquico bayesiano con shrinkage por jugador sobre spline de edad).

### 3.3 Población de estudio (tres capas)

1. **Estimación de la curva de edad:** carrera completa, todas las edades, sin restricción de liga.
2. **Población de interés (a quién sirve el modelo):** sub-23.
3. **Población del test de hipótesis (H1/H2):** sub-23, ligas de primera división europea — definidas por estructura de campeonato (`competitions.csv`: `confederation == "europa"`, `type == "domestic_league"`, `sub_type == "first_tier"`), no por criterio editorial de "ligas top". Confirmado: **23 ligas, 23 países**. La heterogeneidad entre estas ligas se testea como interacción liga×contexto dentro del mismo modelo, no como fase separada.

**Hallazgo de cobertura:** el dataset no tiene segundas divisiones europeas como entidades propias — afecta el contexto reconstruible para jugadores con tramos de carrera en categorías inferiores (ver sección 4).

### 3.4 Variables de contexto — 8/8 construidas y validadas

`src/construir_variables_contexto.py`: objetivos deportivos, calidad de plantel, competencias internacionales, continuidad técnica, sistema táctico (con advertencia de confiabilidad), competencia interna por puesto, reputación de club vendedor (score continuo + flag binario), compañeros de plantel. Cada una con reconocimiento de datos, construcción, y validación cualitativa contra casos futbolísticos conocidos documentados in-code. Detalle en `docs/inventario_variables_contexto.md`.

### 3.5 Variables de rendimiento individual — 6 planificadas, sin correr

`src/construir_variables_rendimiento.py`: goles/90, asistencias/90, % minutos disponibles, goles recibidos como titular (y ajustados por fuerza del rival), diferencial de resultado con/sin el jugador (estilo *Plus-Minus Soccer*), participación en producción ofensiva del equipo, edad de debut. Necesarias para que α_i no funcione como caja negra (mezclando producción observable con señal genuina de scouting).

### 3.6 Atributos adicionales del jugador

Auditoría sistemática de campos no usados en `players.csv`: condición comunitario/extracomunitario (construida, 41.6% de la base), pie hábil y altura (planificadas, con respaldo de literatura de prima de mercado). Nombre de agente descartado explícitamente por riesgo de sesgo subjetivo no defendible.

### 3.7 Estimación y test de hipótesis

Modelo de efectos mixtos/jerárquico con shrinkage (lógica RAPM) sobre los residuos de la curva de edad, con restricción temporal (solo historial previo al punto de estimación, para evitar fuga de información hacia el futuro al usar α_i como feature predictiva). H1 y H2 testeadas con test de razón de verosimilitud entre modelos anidados — no con comparación de RMSE entre dos modelos de machine learning.

### 3.8 Recomposición para predicción a futuro

La persistencia de α_i entre T y T+n se trata como **hipótesis testeable contra datos históricos** (proyección ingenua vs. valor real observado), no como supuesto ciego. El contexto futuro (club/liga) se trata como **escenario explícito** que provee el usuario del modelo (simulador de "¿cuánto valdría si lo transferimos a X?"), no como supuesto oculto.

## 4. Limitaciones

> **Limitaciones conocidas**
> - El valor de mercado captura percepción y exposición mediática, no solo rendimiento — es la mejor proxy disponible pero no es perfecta.
> - Casos de "descubrimiento" (jugadores que pasan del piso de valuación de Transfermarkt a decenas de millones en poco tiempo) conflacionan desarrollo incremental con el evento de ser "encontrado" por el mercado.
> - Shocks de corto plazo por grandes torneos internacionales introducen varianza no atribuible a desarrollo individual sostenido (ver `justificacion_variable_dependiente.md`).
> - Cobertura desigual entre ligas: Italia y Turquía concentran notablemente más jugadores sub-23 valuados que España o Inglaterra.
> - **El dataset no tiene cobertura de segundas divisiones europeas como entidades propias** (confirmado 13/07/2026: cero coincidencias en `competitions.csv`, clubes como Derby County sin fila en `clubs.csv`). Afecta el contexto reconstruible para jugadores con tramos de carrera en categorías inferiores, y subestima sistemáticamente las ventas hacia ligas inferiores en `reputacion_vendedor`.
> - **Condición comunitario/extracomunitario medida de forma imperfecta**: `country_of_citizenship` registra una única ciudadanía, no captura doble ciudadanía por ascendencia (común en jugadores sudamericanos/africanos con pasaporte europeo heredado) — subestima la proporción real de jugadores con circulación libre en la UE/EEE.
> - Dependencia de terceros para datos: el corte de licencia Opta (enero 2026) es evidencia directa de este riesgo estructural.
> - Reconstrucción de club histórico de jugador (necesaria porque ni `clubs.csv` ni `current_club_id` de `player_valuations.csv` son históricos, solo snapshot) tiene cobertura del 55.6%, fuertemente correlacionada con edad — más débil justo en las valuaciones más tempranas de la población de interés.
> - Sesgo de selección: solo se observa el desarrollo de jugadores que siguieron jugando y manteniendo valoración activa.
> - Sin datos de tracking ni métricas avanzadas de eventos (xG, progressive passes) tras el corte de Opta/FBref para el grueso del panel — parcialmente mitigable solo para la población de primera división europea vía cruce con Understat (fuzzy matching por nombre, no implementado todavía).

### Lo que el modelo no puede predecir

- Lesiones graves que interrumpan el desarrollo
- Cambios tácticos drásticos en el equipo del jugador
- Factores extradeportivos (motivación, adaptación cultural en una transferencia)
- Desarrollo de jugadores en ligas sin cobertura de datos (Latinoamérica, África, Asia, segundas divisiones europeas)

## 5. Perspectivas a futuro

### Extensión geográfica

La limitación más importante de esta tesis es que vive en Europa por disponibilidad de datos. La extensión natural es Sudamérica, especialmente Uruguay y Argentina.

### Clustering de perfiles dentro de una posición

Aplicar clustering para identificar arquetipos dentro de cada posición y modelar el desarrollo por arquetipo, en vez de asumir homogeneidad dentro de las 4 categorías amplias usadas actualmente.

### Desagregación de `sub_position`

La granularidad posicional se sacrificó por densidad de datos edad×posición (ver `hipotesis_y_diseno_v2.md`, sección 3.3). Si el volumen final del modelo lo permite, desagregar más allá de arquero/defensor/mediocampista/delantero.

### Aplicación como herramienta de scouting

El output final se empaqueta como simulador: dado un jugador y un contexto hipotético (club/liga de destino), el modelo devuelve una proyección de valor futuro — el producto que un director deportivo usaría en la práctica.

## 6. Pasos a seguir (actualizado 13/07/2026)

### Completado

- Justificación formal de la variable dependiente (`docs/justificacion_variable_dependiente.md`)
- Diseño formal reformulado, con tres alternativas evaluadas y una adoptada (`docs/hipotesis_y_diseno_v2.md`)
- 8 de 8 variables de contexto construidas y validadas (`src/construir_variables_contexto.py`)
- 6 variables de rendimiento individual planificadas, sin correr (`src/construir_variables_rendimiento.py`)
- Población de estudio definida en tres capas, con hallazgo de cobertura de segundas divisiones documentado
- Condición comunitario/extracomunitario construida y validada
- Bibliografía reorganizada por tema, con literatura específica de curva de edad agregada (`docs/bibliografia.md`)
- Diccionario unificado de ~19 variables candidatas (`docs/diccionario_variables.md`)
- Modelo relacional del dataset documentado (`docs/modelo_relacional.pdf`)
- Documento de discusión para la próxima tutoría con Alan (`docs/discusion_enfoque_tesis_proxima_tutoria.md`)

### Inmediatos

- Validar el enfoque reformulado con Alan (tutoría pendiente)
- Correr, validar y depurar `src/construir_variables_rendimiento.py` (mismo patrón de reconocimiento → construcción → validación cualitativa ya usado en variables de contexto)
- Implementar el modelo de efectos mixtos con shrinkage sobre los residuos de la curva de edad
- Implementar el test de razón de verosimilitud para H1/H2

### Pendiente, sin abordar en profundidad

- Punto 7 de la devolución de Alan: calidad de datos consolidada por país/año
- Punto 8 de la devolución de Alan: survivorship bias
- Evaluar cruce con Understat (fuzzy matching por nombre) para xG/xGA en la población de primera división europea

### Preguntas abiertas

- ¿Modelos separados por posición o un modelo único con posición como feature/interacción?
- ¿El sesgo de selección requiere corrección formal o es suficiente nombrarlo?
- ¿Conviene tratar los casos de "descubrimiento" como una submuestra aparte?
- ¿Cómo se pondera la extensión de robustez de las variables frágiles (sistema táctico, reputación de vendedor) frente al modelo base de variables robustas?

---
*Tesis de Maestría — Punteo actualizado — 13/07/2026*
