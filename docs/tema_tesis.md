# Tesis de Maestría — Punteo actualizado

**Predicción de desarrollo de jugadores jóvenes de fútbol**
Aislando el rendimiento individual del contexto de equipo y liga
*Gianfranco Ganicoche*

> **Pregunta de investigación central**
> ¿Es posible aislar la contribución individual de un jugador joven al crecimiento de su valor de mercado, separándola de los efectos de equipo, liga y shocks mediáticos, y usar esa estimación para predecir su desarrollo futuro?

## 1. El tema

El scouting tradicional evalúa el rendimiento actual de un jugador, pero no puede separar cuánto de ese rendimiento es mérito individual y cuánto es producto del contexto: el equipo que lo rodea, el sistema táctico, la calidad de la liga. Esta tesis propone construir un modelo que aísle esa contribución individual y la use para predecir el desarrollo futuro de jugadores jóvenes.

El modelo de negocio de referencia son los clubes holandeses (Ajax, AZ Alkmaar, Feyenoord) que identifican talento joven subvalorado, lo desarrollan, y lo venden a un múltiplo de su precio de compra. Su ventaja competitiva es identificar potencial antes que los demás. Esta tesis busca sistematizar ese proceso con datos.

> **Variable dependiente**
> Crecimiento logarítmico del valor de mercado en Transfermarkt entre T y T+3 para jugadores sub-23 (edad ≤ 20 en T). Se apilan todas las transiciones T→T+3 disponibles en el panel histórico (2010 en adelante, por densidad de cobertura), no un único período calendario. Es una métrica estándar, verificable, y alineada con el modelo de negocio real de los clubes que hacen scouting de desarrollo. Justificación completa en `docs/justificacion_variable_dependiente.md`.

## 2. Por qué este tema tiene sentido

### La ventaja sobre el scout humano es real

Un scout humano no puede aislar sistemáticamente el efecto del equipo en el rendimiento de un jugador. Ve a un delantero del City marcar 20 goles y no puede cuantificar cuántos de esos goles son producto de jugar con compañeros de élite. Un modelo sí puede hacerlo, y aplicarlo consistentemente a miles de jugadores en paralelo.

### El problema de datos — actualizado

El planteo original asumía FBref como fuente de métricas avanzadas de rendimiento (xG, npxG, progressive passes, pressures) para más de 30 ligas europeas. Esto cambió: el 20 de enero de 2026, Stats Perform (Opta) terminó el acuerdo de datos con FBref y exigió eliminar las estadísticas avanzadas del sitio (motivo aparente: Opta pasó a ser distribuidor exclusivo de datos de apuestas para el Mundial 2026). Esto se documenta como riesgo estructural de dependencia de terceros (ver sección 4).

La fuente de datos principal pasó a ser el dataset [`davidcariboo/player-scores`](https://www.kaggle.com/datasets/davidcariboo/player-scores) (Kaggle), que no depende de Opta: incluye valor de mercado histórico, apariciones (goles, asistencias, minutos), transferencias, y datos de competiciones — pero no métricas avanzadas de eventos (xG, progressive passes, pressures). Esto implica que, al menos en esta etapa, el ajuste por contexto se está aplicando directamente sobre el crecimiento de valor de mercado, y la Etapa 2 (KPIs avanzados por posición) queda condicionada a qué métricas básicas alcancen a construirse desde `appearances.csv`, o a evaluar fuentes alternativas no afectadas por el corte de Opta (ver `bibliografia/bibliografia.md` para alternativas identificadas: Understat, StatsBomb Open Data, datasets de Kaggle pre-corte).

### La variable dependiente es verificable

Se toman jugadores sub-23 en un momento T cualquiera del panel histórico, se registra su valor de mercado, y se verifica su valor tres años después (T+3). El panel apila todas las transiciones válidas de todos los jugadores y todos los años disponibles (no un único par de años fijo), lo que permite validar el modelo con historia real y con un volumen de muestra considerablemente mayor al de un corte transversal único.

### El aporte para un club es explicable en una oración

"Este modelo te dice cuánto del crecimiento de valor que ves en un jugador joven es él, independientemente del equipo y la liga donde juega, y qué probabilidad tiene de seguir creciendo en los próximos años."

## 3. Metodología (actualizada)

### Etapa 0 (nueva) — Robustez del horizonte temporal

Surgió en la primera tutoría: en vez de fijar arbitrariamente T+3, se tratará el horizonte como pregunta empírica en la etapa predictiva (probar T+1, T+2, T+3, T+4 y comparar poder predictivo), manteniendo un horizonte fijo únicamente en la etapa de efectos fijos/mixtos por motivos de identificación limpia. Se sumará también un control explícito por participación en grandes torneos internacionales (Mundial, Eurocopa, Copa América) para separar shocks mediáticos de corto plazo del desarrollo real.

### Etapa 1 — Ajuste por contexto (en curso)

Se construyó un panel T→T+3 de jugadores sub-23 (30.615 observaciones, 16.428 jugadores únicos, ligas europeas) y se corrió un primer modelo de efectos fijos de liga, año y posición sobre el crecimiento logarítmico de valor de mercado. Resultado: R² Within ≈ -0.02, lo que confirma que la mayoría de los jugadores tiene 1 a 2 ventanas observadas — insuficiente variación intra-jugador para identificar un efecto fijo individual (α_i) de forma confiable con efectos fijos estándar.

Próximo paso: migrar a un modelo de efectos mixtos/jerárquico con shrinkage (lógica análoga a RAPM de básquet), que "encoge" la estimación de cada jugador hacia el promedio de su liga/posición en proporción inversa a la cantidad de observaciones disponibles, en vez de tratar a cada jugador como si tuviera suficiente historia propia para estimarse de forma independiente.

### Etapa 2 — KPIs diferenciados por posición (pendiente, redefinida)

El planteo original preveía métricas avanzadas de eventos (xG/90, progressive passes, pressures) ajustadas por contexto, diferenciadas por posición. Dado el corte de acceso a Opta/FBref, esta etapa queda condicionada a: (a) construir features desde métricas básicas disponibles en Transfermarkt (goles, asistencias, minutos jugados vía `appearances.csv`), o (b) evaluar fuentes alternativas de métricas avanzadas no afectadas por el corte.

### Etapa 3 — Modelo predictivo de desarrollo

Sin cambios de fondo respecto al planteo original: con las métricas ajustadas por contexto (o, en su defecto, las estimaciones de α_i de la Etapa 1), predecir el crecimiento de valor de mercado a futuro. Se compararán regresión regularizada como baseline, Random Forest y XGBoost. El output es un ranking de jugadores con mayor potencial de desarrollo subvalorado por el mercado actual.

## 4. Limitaciones

> **Limitaciones conocidas**
> - El valor de mercado captura percepción y exposición mediática, no solo rendimiento — es la mejor proxy disponible pero no es perfecta.
> - Casos de "descubrimiento" (jugadores que pasan del piso de valuación de Transfermarkt, ~25-50k€, a decenas de millones en la misma ventana) conflacionan desarrollo incremental con el evento de ser "encontrado" por el mercado — dominan desproporcionadamente la cola derecha de la distribución de crecimiento.
> - Shocks de corto plazo por grandes torneos internacionales introducen varianza no atribuible a desarrollo individual sostenido.
> - Cobertura desigual entre ligas: Italia y Turquía concentran notablemente más jugadores sub-23 valuados que España o Inglaterra — patrón real de amplitud de cobertura, no artefacto de frecuencia de actualización (verificado), pero afecta el balance de la muestra por liga.
> - Dependencia de terceros para datos: el corte de licencia Opta que afectó a FBref desde enero de 2026 es evidencia directa de este riesgo estructural, y motivó el pivot de fuente de datos de esta tesis.
> - Pseudo-replicación: la mayoría de los jugadores aporta 1-2 ventanas correlacionadas al panel — requiere clustering de errores estándar por jugador en toda estimación, y es la razón principal para migrar a modelos de shrinkage en vez de efectos fijos puros.
> - Sesgo de selección: solo se observa el desarrollo de jugadores que siguieron jugando y manteniendo valoración activa — los que desaparecieron del radar no están en el dataset.
> - Sin datos de tracking ni métricas avanzadas de eventos tras el corte de Opta/FBref — el modelo depende de métricas básicas y de la variable de mercado directamente, no de posicionales.

### Lo que el modelo no puede predecir

- Lesiones graves que interrumpan el desarrollo
- Cambios tácticos drásticos en el equipo del jugador
- Factores extradeportivos (motivación, adaptación cultural en una transferencia)
- Desarrollo de jugadores en ligas sin cobertura de datos (Latinoamérica, África, Asia)

## 5. Perspectivas a futuro

### Extensión geográfica — el objetivo real

La limitación más importante de esta tesis es que vive en Europa por disponibilidad de datos. La metodología es transferible a cualquier liga del mundo una vez que existan datos de valor de mercado y eventos accesibles. La extensión natural es Sudamérica, especialmente Uruguay y Argentina, mercados que exportan talento constantemente pero donde el scouting sistematizado con datos casi no existe.

### Incorporar curva de desarrollo por edad

Un jugador de 18 años y uno de 22 tienen trayectorias de desarrollo esperadas muy distintas. Incorporar modelos de curva de desarrollo (peak age por posición, degradación esperada post-peak) agregaría precisión al modelo predictivo.

### Clustering de perfiles dentro de una posición

En lugar de asumir que todos los mediocampistas son iguales, aplicar clustering para identificar arquetipos dentro de cada posición y modelar el desarrollo por arquetipo.

### Aplicación como herramienta de scouting

El output final del modelo puede empaquetarse como una herramienta concreta: dado un perfil buscado (posición, rango de edad, métricas mínimas), el sistema devuelve un ranking de jugadores con mayor potencial de desarrollo subvalorado por el mercado. Ese es el producto que un director deportivo usaría en la práctica.

## 6. Pasos a seguir (actualizado)

### Completado

- Papers centrales entendidos, bibliografía ampliada con literatura de confiabilidad de Transfermarkt, shocks de torneos, e identificación de talento (ver `bibliografia/bibliografia.md`)
- Justificación formal de la variable dependiente, con limitaciones reconocidas (`docs/justificacion_variable_dependiente.md`)
- Pipeline de datos construido y documentado sobre `davidcariboo/player-scores` (`src/panel_pipeline.py`), con diagnóstico completo de cobertura temporal, densidad por liga, y calidad de datos
- Panel T→T+3 sub-23 construido (30.615 observaciones, 16.428 jugadores únicos)
- Primer modelo de efectos fijos (liga + año + posición) corrido e interpretado
- Repositorio de trabajo creado en GitHub para versionar código, documentos y bitácora

### Inmediatos

- Migrar a modelo de efectos mixtos/shrinkage para estimar α_i individual
- Análisis de robustez de horizonte temporal (T+1 a T+4)
- Definir features de rendimiento disponibles sin Opta/FBref (goles, asistencias, minutos) para la Etapa 2
- Evaluar si existen fuentes alternativas de métricas avanzadas no afectadas por el corte de licencia

### Preguntas abiertas

- ¿El horizonte T+3 debe mantenerse fijo también en la etapa predictiva, o directamente optimizarse desde el inicio junto con los demás hiperparámetros?
- ¿Modelos separados por posición o un modelo único con posición como feature?
- ¿El sesgo de selección (solo se observa a jugadores que siguieron jugando) requiere corrección formal o es suficiente nombrarlo?
- ¿Conviene tratar los casos de "descubrimiento" (piso de valuación) como una submuestra aparte en vez de mezclarlos con el desarrollo incremental?
- ¿Existe alguna fuente de datos alternativa, no afectada por el corte de Opta, para ligas en desarrollo (Latinoamérica)?

---
*Tesis de Maestría — Punteo actualizado*
