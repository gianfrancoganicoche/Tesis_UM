# Justificación de la Variable Dependiente

*Crecimiento del valor de mercado (Transfermarkt) como proxy de desarrollo del jugador*

## 1. Planteo del problema

La tutoría planteó dos preguntas que cuestionan directamente la validez de constructo de la variable dependiente de esta tesis: (i) ¿qué entendemos por "desarrollo" de un futbolista?, y (ii) ¿alcanza con medir su valor de mercado para capturarlo? A esto se suma una tercera pregunta derivada: ¿es confiable el valor de mercado publicado por Transfermarkt como fuente de datos? Este documento responde a las tres, reconociendo explícitamente las limitaciones conceptuales antes de justificar la elección metodológica.

## 2. ¿Qué es "desarrollo" en un futbolista?

"Desarrollo" es un concepto multidimensional que admite al menos cuatro operacionalizaciones distintas, no necesariamente convergentes:

- **Técnico-táctico**: mejora en habilidades específicas (pase, definición, lectura de juego, toma de decisiones).
- **Rendimiento en cancha**: métricas de performance ajustadas por contexto (minutos, producción ofensiva/defensiva, aporte relativo al equipo).
- **Trayectoria de carrera**: progresión en minutos, nivel de competición, convocatorias a selecciones juveniles/mayores, salto a ligas top.
- **Reconocimiento de mercado**: valor estimado por el mercado de transferencias (Transfermarkt), que agrega expectativas sobre habilidad, rendimiento, visibilidad y potencial futuro.

Estas dimensiones están correlacionadas pero no son intercambiables. Un jugador puede mejorar técnicamente sin que esto se refleje de inmediato en su valor de mercado (falta de oportunidades, liga de baja visibilidad, ausencia de eventos mediáticos que "activen" la revalorización), o puede subir de valor por factores que exceden el desarrollo puro (un gol viral, un buen Mundial juvenil, un rumor de fichaje). Reconocer esta brecha es un punto de partida necesario, no una debilidad a esconder.

## 3. ¿Por qué elegir el valor de mercado como proxy?

La justificación no es conceptual ("valor de mercado = desarrollo"), sino aplicada. Esta tesis no busca medir el desarrollo técnico en abstracto, sino modelar el desarrollo desde la óptica de un club que debe decidir en qué jugadores jóvenes invertir — el caso de uso que motiva el trabajo (modelo de scouting tipo Ajax/AZ Alkmaar). Para esa decisión, lo relevante no es únicamente la habilidad "real" del jugador, sino cómo el mercado la va a reconocer y remunerar, porque de eso depende el retorno de la inversión en el desarrollo del jugador.

Adicionalmente, el valor de mercado presenta tres ventajas prácticas decisivas frente a las otras dimensiones:

- Es observable y está disponible de forma sistemática, histórica y comparable entre ligas — a diferencia de métricas técnicas avanzadas, que dejaron de estar disponibles públicamente tras el corte de licencia Opta/FBref (documentado en la bitácora).
- Es verificable externamente: no depende de un juicio subjetivo del investigador, sino de un mecanismo de mercado agregado y auditable en el tiempo.
- Tiene relevancia directa para el caso de uso aplicado: es la métrica que efectivamente usan clubes, agentes y medios para tomar decisiones de inversión y negociación.

> "El valor de mercado es un proxy imperfecto pero empíricamente validado del desarrollo percibido por el mercado, que combina habilidad, rendimiento, visibilidad y potencial futuro esperado. Se elige sobre alternativas técnicas por ser la única variable observable, comparable entre ligas y contextos, y con relevancia directa para el caso de uso aplicado (scouting y toma de decisiones de inversión en clubes)."

## 4. Limitaciones reconocidas

- No captura desarrollo técnico que aún no fue "visto" ni reconocido por el mercado (riesgo de subestimar jugadores de ligas poco seguidas — relevante para la limitación de alcance geográfico ya documentada).
- Puede reflejar efectos de visibilidad mediática y marketing independientes de la mejora futbolística real.
- Es sensible a factores contractuales y situacionales (duración de contrato, cláusulas de rescisión) que no son "desarrollo" en ningún sentido.
- Un estudio (Coates & Parshakov) encuentra sesgos sistemáticos: los valores de Transfermarkt no son predictores perfectamente insesgados de los precios reales de mercado.

Estas limitaciones se documentan explícitamente en la tesis como parte del alcance del trabajo, siguiendo el mismo criterio ya aplicado a la limitación geográfica (Latinoamérica): son fronteras de alcance, no fallas de diseño.

## 5. Confiabilidad empírica de Transfermarkt: evidencia académica

Existe una línea de investigación específica dedicada a validar los valores de Transfermarkt como proxy de precios reales de mercado. Los hallazgos centrales:

- **Herm, Callsen-Bracker & Kreis (2014)** — el trabajo fundacional — muestran que las estimaciones de la comunidad de Transfermarkt son excelentes predictoras de las tarifas de transferencia reales, usando un modelo de "principio del juez" (judge principle) donde miembros experimentados de la comunidad agregan y actualizan valoraciones.
- **Müller, Simons & Weinmann (2017)** confirman que estos valores han sido la base de numerosos estudios del mercado de transferencias y que su precisión es notable pese a los desafíos típicos del crowdsourcing (influencia social, manipulación, falta de experiencia de algunos usuarios).
- **Coates & Parshakov (2021/2022)** aportan la contracara necesaria: si bien los valores predicen razonablemente bien las tarifas reales, existen sesgos sistemáticos asociados a ciertos factores observables, por lo que no deben tratarse como una medida sin ruido ni sesgo.
- **Prockl & Frick (2018)** muestran que los valores también son buenos indicadores de salarios actuales y futuros de los jugadores, ampliando la validez del proxy más allá de las transferencias.
- Trabajos posteriores (**Peeters, 2018**; **Campa, 2022**; **Franceschi et al., 2023/2025**) reafirman que Transfermarkt es una fuente ampliamente citada y utilizada en investigación académica de economía del deporte, a la vez que llaman a seguir profundizando la validación de estos modelos crowdsourced a medida que evolucionan.

En síntesis: la literatura no sostiene que Transfermarkt sea una medida perfecta, sino que es la mejor aproximación pública, sistemática y validada empíricamente disponible para estudios de esta naturaleza — lo cual es exactamente el estándar que esta tesis necesita.

## 6. Caso especial: valoración sin transferencia (ej. Lamine Yamal)

Un caso que ilustra bien el mecanismo es el de jugadores con valores de mercado muy altos sin haber sido nunca transferidos (ej. Lamine Yamal, valorado en el entorno de 200 M€ sin transferencia registrada). Esto no es una inconsistencia del sistema: Transfermarkt define explícitamente el valor de mercado no como una predicción de precio de transferencia, sino como una estimación del valor que tendría el jugador si estuviera en un mercado abierto en este momento — es decir, un valor de reposición hipotético, no un precio observado.

El valor se actualiza en base a un conjunto de factores explícitos (no un algoritmo cerrado, sino un proceso de la comunidad y editores especializados): rendimiento en el club y la selección, edad y potencial de desarrollo futuro, nivel deportivo y financiero de la liga, reputación y prestigio, valor de marketing, duración de contrato, y nivel de interés de otros clubes, entre otros. Para un jugador muy joven con proyección alta y desempeño ya validado a nivel de élite, estos factores pueden generar una valoración muy alta incluso sin ninguna transacción de por medio — el valor no está "probado" por una venta, pero sí está sustentado en un conjunto de señales observables y en el consenso de una comunidad experta que actualiza esas valoraciones periódicamente (dos veces por temporada como mínimo, con ajustes intermedios para casos de alta variabilidad como jugadores jóvenes en ascenso).

Para la tesis, este caso es un buen ejemplo a incluir en la sección de limitaciones/discusión: refuerza que el valor de mercado captura "desarrollo esperado y reconocido", no únicamente desarrollo confirmado por una transacción, lo cual es coherente con el uso que se le da en este trabajo (predecir crecimiento de valor esperado, no replicar transferencias).

## 7. Motivación adicional: el vacío de evidencia sistemática sobre los modelos de negocio de los clubes

Un hallazgo relevante durante la revisión de antecedentes es que la inspiración de negocio de esta tesis — el modelo de clubes como Ajax y AZ Alkmaar, que crecen económicamente comprando/formando jugadores jóvenes y revendiéndolos con plusvalía — está pobremente documentada desde una perspectiva académica y cuantitativa. La literatura se divide en dos bloques de calidad muy distinta:

- Un bloque académico sólido sobre identificación de talento (Talent Identification, TI) — Reeves, Roberts, McRobert & Littlewood (2018, Soccer & Society) y trabajos relacionados — pero centrado en los procesos sociológicos y de juicio experto de los scouts, no en el modelado cuantitativo del desarrollo de valor del jugador ni en el modelo de negocio subyacente.
- Un bloque de literatura gris (entrevistas periodísticas, presentaciones corporativas, contenido de proveedores de datos como Stats Perform) con información valiosa pero anecdótica sobre casos puntuales (AZ Alkmaar, declaraciones de Daan Uitermark y Koen Veenstra), sin metodología reproducible ni validación estadística pública.

No se identificó, en cambio, literatura académica que modele de forma sistemática y cuantitativa cómo se genera la plusvalía en el desarrollo de jugadores jóvenes, ni que aísle la contribución individual del jugador de los efectos de equipo y liga con fines de estimar el retorno económico de la inversión en captación y formación temprana. Este vacío es, en sí mismo, una motivación adicional para esta tesis: no se trata solo de aplicar técnicas econométricas y de machine learning a un problema ya resuelto en la literatura, sino de aportar evidencia sistemática y reproducible en un área donde el conocimiento existente es, en su mayoría, tácito, anecdótico o propietario de los propios clubes (que no publican sus metodologías internas por razones competitivas obvias). Esto conecta directamente con la relevancia práctica del trabajo: si los propios clubes no divulgan cómo modelan esta decisión, un enfoque académico y abierto tiene valor añadido tanto para la comunidad de investigación como para clubes con recursos limitados que no pueden desarrollar internamente estas capacidades (el mismo problema que describe AZ Alkmaar respecto de sus competidores con mayor presupuesto).

## 8. Datos atípicos y shocks: el efecto de grandes torneos sobre el valor de mercado

Un fenómeno adicional a considerar es el de los shocks de corto plazo sobre el valor de mercado generados por eventos puntuales de alta visibilidad — un Mundial, una Eurocopa, un gol o una actuación viral — que pueden elevar o desplomar el valor de un jugador de forma abrupta, sin que medie necesariamente un cambio real y sostenido en su nivel técnico. El Mundial 2026, en curso al momento de escribir este documento, ofrece ejemplos concretos: Lamine Yamal y Erling Haaland lideran la valoración del torneo con 200 M€ cada uno, cifras que ya reflejan en buena medida expectativa mediática y de rendimiento futuro más que una transacción o consolidación de largo plazo.

La literatura respalda que este no es solo un efecto anecdótico. Franck y Nüesch muestran que señales de popularidad —incluyendo exposición mediática y atención del público— inflan sistemáticamente las valoraciones de mercado por encima de lo explicado por la contribución real en el campo de juego. Esto es consistente con los hallazgos de Coates & Parshakov sobre sesgos sistemáticos en los valores de Transfermarkt como predictores de precios reales: los grandes eventos mediáticos son candidatos naturales a explicar parte de ese sesgo.

Un estudio reciente de **Havran, Claro & Nessel (2026)**, publicado en Social Science Quarterly, analiza específicamente este fenómeno: usando datos de 675 jugadores y modelos lineales jerárquicos, examina cómo la participación en los Mundiales 2018 y 2022 afectó el valor de mercado de futbolistas de las cinco grandes ligas europeas. El hallazgo central matiza la intuición simple: la participación en el Mundial no incrementa automáticamente el valor de mercado; los cambios están impulsados principalmente por el rendimiento individual antes que por el éxito colectivo del equipo, y el efecto es más pronunciado en jugadores emergentes (más jóvenes y de menor valor inicial) y en aquellos de ligas con mayor exposición en redes sociales (Premier League, La Liga). Este resultado es especialmente relevante para esta tesis, dado que su población de interés (jugadores sub-23) coincide en gran medida con el segmento donde el estudio encuentra los efectos más significativos.

### 8.1 Por qué esto es relevante para la metodología de esta tesis

La variable dependiente de esta tesis (crecimiento de valor de mercado entre T y T+3) puede verse afectada por estos shocks de forma que no corresponde a ninguno de los componentes que el modelo de efectos fijos busca aislar: no es habilidad individual sostenida (α_i), no es efecto de equipo (γ_j), ni efecto de liga. Es una fuente de varianza adicional —evento mediático de corto plazo— que conviene reconocer y, en la medida de lo posible, tratar explícitamente en vez de dejar que contamine silenciosamente la estimación.

### 8.2 Estrategias metodológicas a considerar

- **Estimadores robustos a outliers**: regresión robusta (tipo Huber) o winsorizing de los percentiles extremos de crecimiento de valor, para evitar que un número reducido de casos extremos distorsione la estimación general de α_i.
- **Modelado explícito del shock**: incorporar una variable de control por participación y rendimiento en grandes torneos internacionales (Mundial, Eurocopa, Copa América, Juegos Olímpicos) durante la ventana de observación, en lugar de tratarlo únicamente como ruido a eliminar.
- **Análisis de persistencia vs. reversión**: dado que Transfermarkt actualiza los valores como mínimo dos veces por temporada, con ajustes intermedios para casos de alta variabilidad, es posible contrastar si una revalorización post-torneo se sostiene en la actualización siguiente (más consistente con una revalorización real) o se revierte (más consistente con sobrerreacción de corto plazo).
- **Análisis de robustez**: re-estimar el modelo excluyendo o marcando explícitamente las temporadas con grandes torneos, y reportar si las estimaciones de α_i se mantienen estables. Estabilidad ante esta exclusión sería evidencia a favor de la robustez del método; cambios significativos serían, en sí mismos, un hallazgo relevante para discutir.

Este análisis se documentará como una limitación reconocida junto con un análisis de robustez concreto, siguiendo el mismo criterio aplicado a las demás limitaciones de esta tesis (alcance geográfico, valor de mercado como proxy imperfecto de desarrollo): no invalida el enfoque, pero es una fuente de varianza conocida que debe nombrarse y, en lo posible, controlarse explícitamente.

## 9. Síntesis para la tutoría

La postura a sostener frente al tutor puede resumirse en cinco pasos:

1. Se reconoce que valor de mercado ≠ desarrollo técnico puro; son conceptos relacionados pero distintos.
2. Se justifica la elección por su relevancia aplicada al caso de uso de la tesis (scouting y decisiones de inversión) y por ser la única variable observable, comparable y sistemática disponible.
3. Se respalda con evidencia empírica de que Transfermarkt correlaciona fuertemente con precios reales de mercado y salarios, reconociendo a la vez los sesgos documentados en la literatura.
4. Se señala que el vacío de literatura académica y sistemática sobre cómo los clubes modelan y capturan la plusvalía del desarrollo de jóvenes talentos (más allá de casos anecdóticos) refuerza la relevancia y originalidad de esta tesis.
5. Se reconoce que eventos de alta visibilidad (grandes torneos, actuaciones virales) generan shocks de corto plazo sobre el valor de mercado no atribuibles a desarrollo real, y se propone un plan concreto de robustez (control explícito y/o estimadores robustos) para tratarlos.

## 10. Referencias

- Coates, D., & Parshakov, P. (2021/2022). *The Wisdom of Crowds and Transfer Market Values.* Working paper, National Research University Higher School of Economics.
- Herm, S., Callsen-Bracker, H.-M., & Kreis, H. (2014). *When the crowd evaluates soccer players' market values: Accuracy and evaluation attributes of an online community.* Sport Management Review, 17(4), 484-492.
- Müller, O., Simons, A., & Weinmann, M. (2017). *Beyond crowd judgments: Data-driven estimation of market value in association football.* European Journal of Operational Research, 263(2), 611-624.
- Peeters, T. (2018). *Testing the Wisdom of Crowds in the field: Transfermarkt valuations and international soccer results.* Working paper.
- Prockl, F., & Frick, B. (2018). *Information Precision in Online Communities: Player Valuations on www.Transfermarkt.de.*
- Franceschi, M., et al. (2023/2025). *The debate behind the numbers: analyzing discussions about crowdsourced football player market valuations.* Managing Sport and Leisure.
- Transfermarkt (2021). *Transfermarkt Market Value explained - How is it determined?*
- Reeves, M. J., Roberts, S. J., McRobert, A. P., & Littlewood, M. A. (2018). *Factors affecting the identification of talented junior-elite footballers: a case study.* Soccer & Society, 19(8), 1106-1121.
- Reeves, M. J., McRobert, A., Lewis, C., & Roberts, S. (2019). *A case study of verbal reports for Talent Identification purposes in soccer: A Messi affair!* PLoS ONE, 14(11), e0221151.
- Training Ground Guru (2025). *Daan Uitermark: How AZ Alkmaar are using data as their "compass".*
- Stats Perform (2019). *AZ Alkmaar - Combining Data and Technology to Evolve Recruitment Processes.*
- Franck, E., & Nüesch, S. (2012). *Talent and/or Popularity: What Does It Take to Be a Superstar?* Economic Inquiry, 50(1), 202-216.
- Havran, Z., Claro, D., & Nessel, K. (2026). *Talent, Capital, and the FIFA World Cup: How Participation Affects Football Players' Market Value.* Social Science Quarterly, 107(1), e70125.

> Ver `bibliografia/bibliografia.md` para el listado completo con links directos a cada fuente.
