# Hipótesis y diseño formal de la tesis (v2)

*Actualiza `docs/hipotesis_y_diseno.md` (v1). Responde al punto 1 de la devolución de Alan Silberman, incorporando los hallazgos de una sesión de exploración posterior que llevó a reformular el diseño analítico. La v1 no se descarta — su formalización de población e hipótesis clásicas sigue vigente como Alternativa 1 de este documento.*

## 1. Qué cambió respecto a v1 y por qué

La v1 asumía un diseño de comparación A/B: un modelo con features de rendimiento "crudas" contra un modelo con features "ajustadas por contexto", prediciendo `crecimiento_log` en una ventana fija T→T+3. Al explorar la implementación concreta de ese diseño surgieron tres problemas de fondo:

1. **Con modelos flexibles (Random Forest/XGBoost), un modelo con más variables casi siempre "gana"** en RMSE/MAE por construcción, sin que eso sea necesariamente un hallazgo informativo — la comparación A/B corre el riesgo de contestar una pregunta trivial.
2. **La ventana fija T→T+3 es arbitraria** (punto 6 de Alan) y además desperdicia datos: con ella, cada jugador aporta en promedio solo **1.86 ventanas** al panel, insuficiente para identificar efectos individuales con confianza (es la causa directa del R² Within ≈ -0.02 obtenido en el primer modelo de efectos fijos).
3. **La edad no estaba tratada como variable central**, cuando en la población sub-23 es probablemente el factor más determinante del valor de mercado — y tratarla como un control lineal más, en vez de como una curva de desarrollo esperada, contamina cualquier intento de aislar "calidad individual" real.

Un chequeo empírico sobre los datos crudos confirmó que un diseño alternativo, basado en trayectorias completas de carrera en vez de pares fijos, resuelve los tres problemas a la vez (ver sección 4). Esto no invalida la pregunta de investigación original — la reformula hacia una versión más rica y mejor identificada.

## 2. Pregunta de investigación (sin cambios en el fondo)

Se mantiene el objetivo general definido en v1: evaluar si la corrección por contexto de equipo y liga mejora la comprensión/predicción del desarrollo de valor de mercado de jugadores jóvenes, y si esa corrección aísla una señal de calidad individual útil para decisiones de scouting.

Lo que cambia es **cómo** se responde esa pregunta — no la pregunta en sí. A continuación se presentan tres alternativas de diseño analítico, de la más simple a la más ambiciosa, para decidir con Alan cuál (o qué combinación) seguir.

## 3. Tres alternativas de diseño

### Alternativa 1 — Comparación A/B con testeo de hipótesis clásico (diseño de v1)

**Enfoque:** dos modelos predictivos (features crudas vs. features ajustadas por contexto) prediciendo `crecimiento_log` en ventana fija T→T+3, comparados por RMSE/MAE/Spearman.

**Hipótesis:** H1 (el ajuste mejora la predicción), H2 (el efecto varía por posición), H3 (modelos corregidos superan a los no corregidos) — tal como se formularon en v1.

**Ventajas:**
- Es el diseño que Alan propuso explícitamente en su devolución — cero fricción de alineación con el tutor.
- Estructura de testeo de hipótesis clásica, fácil de defender en la instancia de tesis.
- Metodológicamente simple de implementar sobre el pipeline ya construido.

**Desventajas:**
- Riesgo real de responder una pregunta poco informativa (con un modelo suficientemente flexible, "más variables" probablemente gane, sin que eso mida lo que la tesis quiere medir).
- No resuelve la arbitrariedad de la ventana T+3 ni el problema de las 1.86 ventanas/jugador.
- No produce un output directamente utilizable como herramienta de scouting — es un resultado de significancia estadística, no un score por jugador.

### Alternativa 2 — Feature importance / ablation sobre un modelo único

**Enfoque:** un solo modelo con todas las variables de contexto y rendimiento disponibles (sin pre-ajustar nada a mano), evaluando importancia de variables vía SHAP y/o un estudio de ablación (agregar variables de a grupos y medir la mejora incremental en RMSE/Spearman).

**Hipótesis:** reformulación de H1/H3 hacia "¿qué variables de contexto aportan más valor predictivo incremental?" y de H2 hacia "¿varía esa importancia por posición?".

**Ventajas:**
- Evita la comparación trivial de la Alternativa 1 — mide magnitud real de cada variable, no solo si "ayuda o no".
- Con el universo de features realista (~15-25 variables construibles desde `davidcariboo/player-scores`, ver v1 sección 4 revisada), es un análisis acotado y defendible, no un ejercicio de "tirar variables a ver qué pega".
- Resultado interpretable y parcialmente accionable (qué mirar al scoutear).

**Desventajas:**
- No aísla una señal de calidad individual portable — no responde "cuánto vale este jugador independientemente de su contexto", que es el objetivo aplicado real.
- Importancia predictiva (SHAP) no es identificación causal — Alan, con formación de economista, puede considerarlo insuficiente para las hipótesis que él mismo propuso.
- Sigue arrastrando el problema de la ventana fija T+3, salvo que se combine con el cambio de la Alternativa 3.

### Alternativa 3 — Descomposición/recomposición con curva de edad sobre trayectorias completas (recomendada)

**Enfoque:** inspirado en la arquitectura de *Transfer Portal* (Dinsdale & Gallagher, 2022; ya en la bibliografía de la tesis). Se abandona el panel de pares fijos T→T+3 y se usa la trayectoria completa de valuaciones de cada jugador. El valor de mercado observado en cualquier punto de la carrera se descompone en:

`valor_it = curva_edad(edad_it, posición_i) + contexto_it (liga, equipo) + α_i (calidad individual) + ε_it`

`α_i` — la calidad individual aislada del contexto y de la edad — se estima con un modelo de efectos mixtos/shrinkage (continuidad directa de la Etapa 1 ya construida, pero re-especificada), y se usa como score portable: "cuánto vale este jugador independientemente de dónde juega y de qué tan desarrollado está por edad". La predicción a futuro se arma recomponiendo α_i (proyectado según su evolución esperable) con el contexto proyectado a la fecha de interés.

**Hipótesis:** requiere reformular H1-H3 hacia una versión de descomposición de varianza — ej. H1': "una parte sustancial de la varianza en valor de mercado observado es explicada por la curva de edad y el contexto, dejando un residuo (α_i) informativo sobre calidad individual"; H2 se mantiene, pero testeada como interacción edad×posición dentro de la curva, con evidencia preliminar ya a favor (ver sección 4).

**Ventajas (validadas empíricamente en esta sesión, ver sección 4):**
- Usa **5.33x más observaciones** que el panel de pares fijos (163.150 vs. 30.615), con 6.43 ventanas/jugador en vez de 1.86 — resuelve directamente el problema de identificación que produjo el R² Within negativo.
- Resuelve la arbitrariedad de T+3 (punto 6 de Alan): el horizonte de predicción deja de ser una decisión de diseño y pasa a ser una consulta sobre la curva ya ajustada.
- Produce un output directamente utilizable para scouting: un score α_i por jugador, portable entre contextos — es la traducción más directa de la aspiración profesional que motiva la tesis.
- Densidad de datos confirmada: la curva de edad estimada sobre carrera completa (sin el corte artificial en 23 años) muestra la forma esperada en la literatura (pico en 26-28 años, con densidad robusta en todo el rango hasta ~40 años), lo que valida que el enfoque es viable con los datos disponibles.

**Desventajas:**
- Es la alternativa más ambiciosa metodológicamente — requiere estimar la curva de edad (spline, no cuadrática simple, dado que el pico observado no es simétrico) antes de poder avanzar con la descomposición.
- La recomposición a futuro requiere una decisión explícita sobre qué asumir para el contexto en T+n (¿mismo club? ¿promedio de mercado? — ver v1 sección 5), que no tiene una respuesta trivial y probablemente amerite tratarse como escenario base + análisis de sensibilidad (simulación de transferencias).
- Es la que más se aleja del planteo original de Alan (comparación A/B con hipótesis clásicas), así que requiere una conversación explícita de realineación con él antes de comprometerse.

### 3.1 Aclaración necesaria sobre la Alternativa 3: la recomposición no es una suposición ciega

Un riesgo real de la Alternativa 3, señalado explícitamente en discusión con el tutorando: para recomponer un valor futuro hace falta asumir (a) que la habilidad relativa del jugador (α_i) se mantiene constante entre T y T+n, y (b) algún supuesto sobre el contexto futuro (club/liga). A primera vista esto parece reemplazar "testeo" por "suposición" sin más. Conviene precisar por qué no es así, y qué sí queda como supuesto genuino.

**Sobre la persistencia de α_i — es una hipótesis testeable, no un supuesto ciego.**
Con las trayectorias históricas ya disponibles, es posible construir una *proyección ingenua* — `curva_edad(edad, posición) + α_i(T)` — y contrastarla contra el valor real observado en T+n para todos los casos históricos donde ambos puntos ya existen. Esto convierte la persistencia de habilidad relativa en un benchmark medible (vía RMSE/MAE/Spearman, igual que el resto del diseño), no en un artículo de fe. Si la proyección ingenua predice mal, es en sí mismo un hallazgo relevante (evidencia de que la habilidad relativa de jugadores jóvenes es más volátil de lo asumible, lo cual es coherente con por qué el scouting de desarrollo temprano es valioso). El valor metodológico central de la tesis pasa a estar, en parte, en identificar sistemáticamente **quiénes se desvían de esta proyección ingenua y por qué** — usando la proyección como vara de comparación, no como resultado final.

Esto además habilita una vía de medición empírica del efecto de cambio de contexto que no estaba explícita antes: comparando, entre los casos históricos donde sí hubo una transferencia entre T y T+n, cuánto se desviaron de la proyección ingenua (calculada asumiendo continuidad de contexto) — eso le da contenido cuantitativo real a "cuánto vale un cambio de club", en vez de asumirlo.

**Sobre el contexto futuro (club/liga) — esto sí es un supuesto genuino, y se trata como tal.**
A diferencia de la habilidad, el club/liga futuro no es razonable proyectarlo como "el mismo" de forma silenciosa, porque las transferencias no son un evento raro ni aleatorio en esta población. La decisión de diseño adoptada es no ocultar este supuesto dentro del modelo, sino exponerlo como una **entrada explícita del usuario**: el modelo admite escenarios ("proyectar asumiendo que el jugador sigue en su club actual" vs. "proyectar asumiendo que se transfiere a un club/liga de contexto X"), calculados recomponiendo con distintos valores de contexto. Esto convierte una debilidad metodológica en una funcionalidad de simulación — más útil para un club real que una única predicción puntual.

## 4. Evidencia empírica que sostiene la Alternativa 3

Chequeos corridos sobre `davidcariboo/player-scores` (players.csv + player_valuations.csv, filtro de cobertura desde 2010):

**Ganancia de tamaño de muestra (trayectorias completas sub-23 vs. panel de pares fijos):**

| | Pares fijos T→T+3 (panel actual) | Trayectorias completas (sub-23) |
|---|---|---|
| Observaciones | 30.615 | 163.150 |
| Jugadores únicos | 16.428 | 25.372 |
| Obs/jugador | 1.86 | 6.43 |

**Densidad edad × posición (sub-23):** sólida desde los 17 años en las cuatro categorías amplias (Attack, Defender, Goalkeeper, Midfield); la edad 15-16 tiene volumen insuficiente y se recomienda excluirla del piso de la curva.

**Forma de la curva de valor por edad (carrera completa, sin corte en 23):**
- Sube de forma sostenida y acelerada de los 16 a los 24 años.
- Meseta de pico entre 26 y 28 años (~3.6-3.7M€ promedio).
- Declive sostenido desde los 29 hasta los ~40, donde la densidad ya es insuficiente para confiar en el promedio (menos de ~400 observaciones por edad desde los 41 años).
- **Hallazgo preliminar sobre H2:** la densidad de arqueros con datos cae de forma notablemente más lenta con la edad que la de jugadores de campo (a los 38 años, casi tantos arqueros como delanteros con datos, cuando a los 22 eran un tercio) — evidencia preliminar, no un test formal, a favor de que la curva de edad difiere por posición.

**Implicancia metodológica:** la curva de edad debe estimarse sobre la muestra de carrera completa (sin filtro de edad superior, salvo el descarte de la cola con muy baja densidad ~41+), y luego aplicarse como referencia fija sobre la población de interés (sub-23) para calcular las desviaciones α_i. Estimarla solo con datos sub-23 sesga la forma de la curva, porque nunca observa el pico ni el declive real.

## 5. Recomendación y próximos pasos

**Recomendación:** llevar las tres alternativas a Alan tal como están presentadas en este documento, con la Alternativa 3 como propuesta principal (por la evidencia empírica de la sección 4) sin descartar la Alternativa 1 — es posible, y probablemente deseable, conservar un testeo de hipótesis clásico *dentro* del diseño de la Alternativa 3 (ej. testear formalmente si la curva de edad difiere por posición, en vez de asumirlo, vía comparación de modelos anidados con test de razón de verosimilitud o AIC/BIC), en vez de tratarlas como mutuamente excluyentes.

**Preguntas concretas para la próxima tutoría:**
1. ¿La Alternativa 3 (descomposición/recomposición con curva de edad) es aceptable como reformulación del diseño, dada la evidencia de la sección 4, o prefiere mantener el diseño A/B original de la Alternativa 1?
2. Para la recomposición a futuro (predecir α_i + contexto proyectado en T+n): se propone tratar la persistencia de α_i como una hipótesis testeable contra datos históricos (proyección ingenua vs. valor real observado, ver sección 3.1), y el contexto futuro (club/liga) como un escenario explícito que provee el usuario, no como un supuesto oculto del modelo. ¿Le parece un tratamiento metodológicamente aceptable, o prefiere otro enfoque para esta parte?
3. ¿Está de acuerdo en conservar un componente de testeo de hipótesis clásico (interacción edad×posición) dentro del diseño de descomposición, como forma de no perder el rigor de hipótesis testeable que él propuso originalmente?

**Próximos pasos técnicos (una vez validado el enfoque con Alan):**
- Reconstruir el panel como trayectorias completas en vez de pares fijos T→T+3 (`src/panel_pipeline.py` requiere una función nueva, no una modificación menor).
- Estimar la curva de edad con spline sobre la muestra de carrera completa, con piso de observaciones mínimas por edad para descartar la cola ruidosa.
- Testear formalmente la interacción edad×posición (modelo restringido vs. modelo con interacción, comparación por AIC/BIC o test de razón de verosimilitud).
- Re-especificar el modelo de efectos mixtos de Etapa 1 sobre los residuos de la curva de edad (en vez de sobre `crecimiento_log` directo), con la restricción temporal de usar solo historial previo al punto de estimación para evitar fuga de información hacia atrás.
