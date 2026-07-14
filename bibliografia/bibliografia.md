# Bibliografía y fuentes de referencia

Listado centralizado de papers, artículos y fuentes usadas en la tesis, organizados por
tema. Actualizar este archivo cada vez que aparezca una fuente nueva relevante.

*Reorganizado en sesión (13/07/2026) para reflejar la Alternativa 3 (descomposición/
recomposición con curva de edad) como enfoque de trabajo. La sección "Núcleo
metodológico" agrupa lo que sostiene directamente el diseño actual; el resto son fuentes
que siguen siendo válidas para otras secciones de la tesis (justificación de la VD,
motivación, limitaciones) pero no son insumo directo del método.*

## Núcleo metodológico para la Alternativa 3

### Descomposición/recomposición y shrinkage

- *Transfer Portal: Accurately Forecasting the Impact of a Player Transfer in Soccer.*
  Dinsdale & Gallagher (2022). arXiv:2201.11533. https://arxiv.org/abs/2201.11533
  Template directo del enfoque de descomposición (aislar habilidad individual del
  contexto de equipo/liga) y recomposición (proyectar a un contexto distinto).

- *Plus-Minus Player Ratings for Soccer.* Kharrat, McHale & Peña (2020) /
  arXiv:1706.04943. https://arxiv.org/abs/1706.04943
  Base para el mecanismo de shrinkage (estilo RAPM) usado para estimar α_i con
  confianza proporcional al volumen de datos disponible por jugador.

- Sidorowicz, H. (2026). *Year-to-Year Metric Stability in Elite Football: A Positional
  Analysis Across the Big Five European Leagues.* SportRxiv (preprint).
  https://sportrxiv.org/index.php/server/preprint/view/954
  Evidencia de que los jugadores sub-23 son sistemáticamente menos estables año a año
  que los veteranos (18 de 24 combinaciones posición-métrica) — sostiene tratar la
  persistencia de α_i como hipótesis testeable, no como supuesto.

### Curva de edad / peak age (agregado en sesión — vacío que no estaba cubierto)

- Dendir, S. (2016). *When do soccer players peak? A note.* Journal of Sports Analytics,
  2(2), 89-105. https://doi.org/10.3233/JSA-160021
  Modelo de efectos fijos por jugador (controla sesgo de selección) sobre ratings de
  WhoScored.com, 4 grandes ligas. Pico general 25-27 años; delanteros ~25, defensores
  ~27. Referencia central para justificar la forma esperada de la curva y la
  interacción edad×posición (H2).

- Kalén, A., Rey, E., Sal de Rellán-Guerra, A., & Lago-Peñas, C. (2019). *Are Soccer
  Players Older Now Than Before? Aging Trends and Market Value in the Last Three
  Decades of the UEFA Champions League.* Frontiers in Psychology, 10:76.
  https://doi.org/10.3389/fpsyg.2019.00076
  Curva de valor de mercado (no solo rendimiento físico) con forma de U invertida,
  pico en 26-30 años; arqueros y centrales pican más tarde (hasta ~31) que delanteros
  — evidencia directa sobre la variable dependiente de esta tesis, no solo sobre
  rendimiento deportivo.

- Säfvenberg, R., Nordgaard, A., Lidmark Eriksson, O., Carlsson, N., & Lambrix, P.
  (2024). *Age of Peak Performance among Soccer Players in Sweden.* Proceedings of the
  First International Sports Analytics Conference and Exhibition (ISACE 2024).
  https://www.ida.liu.se/~patla00/publications/ISACE24-preprint.pdf
  **Precedente metodológico más cercano al diseño de esta tesis**: modelo jerárquico
  bayesiano con intercepto y pendiente a nivel jugador sobre una curva de edad (spline
  de placa delgada), con shrinkage explícito para jugadores con pocas temporadas — es
  esencialmente la misma arquitectura estadística que se planea usar acá, aplicada a
  una liga de menor nivel. Además discute explícitamente el sesgo de que los mejores
  jugadores de ligas menores se venden antes de alcanzar su pico, dato relevante para
  el punto 4 de Alan (validez entre ligas concentradas) todavía pendiente.

## Confiabilidad del valor de mercado de Transfermarkt

*(Sigue siendo relevante independientemente de la alternativa — sostiene la variable
dependiente, no el método de descomposición.)*

- Herm, S., Callsen-Bracker, H.-M., & Kreis, H. (2014). *When the crowd evaluates soccer
  players' market values: Accuracy and evaluation attributes of an online community.*
  Sport Management Review, 17(4), 484-492.
  https://www.semanticscholar.org/paper/When-the-crowd-evaluates-soccer-players%E2%80%99-market-and-Herm-Callsen-Bracker/b0b721775c7a1428661248ebd35fd066949a67cf

- Müller, O., Simons, A., & Weinmann, M. (2017). *Beyond crowd judgments: Data-driven
  estimation of market value in association football.* European Journal of Operational
  Research, 263(2), 611-624. https://repub.eur.nl/pub/120757/Repub_120757_O-A.pdf

- Coates, D., & Parshakov, P. (2021/2022). *The Wisdom of Crowds and Transfer Market
  Values.* Working paper, National Research University Higher School of Economics.
  https://hcapps.holycross.edu/hcs/RePEc/fek/Session08.2-Coates.pdf

- Peeters, T. (2018). *Testing the Wisdom of Crowds in the field: Transfermarkt
  valuations and international soccer results.* Working paper.

- Prockl, F., & Frick, B. (2018). *Information Precision in Online Communities: Player
  Valuations on www.Transfermarkt.de.*

- Franceschi, M., et al. (2025). *The debate behind the numbers: analyzing discussions
  about crowdsourced football player market valuations.* Managing Sport and Leisure.
  https://www.tandfonline.com/doi/full/10.1080/23750472.2025.2557905

- Transfermarkt (2021). *Transfermarkt Market Value explained - How is it determined?*

## Shocks de mercado / efecto de grandes torneos

*(Relevante para la sección de limitaciones/robustez de la VD, no para el método
central.)*

- Franck, E., & Nüesch, S. (2012). *Talent and/or Popularity: What Does It Take to Be a
  Superstar?* Economic Inquiry, 50(1), 202-216.
  https://papers.ssrn.com/sol3/Delivery.cfm/SSRN_ID1710049_code943737.pdf?abstractid=1503346

- Havran, Z., Claro, D., & Nessel, K. (2026). *Talent, Capital, and the FIFA World Cup:
  How Participation Affects Football Players' Market Value.* Social Science Quarterly,
  107(1), e70125. https://onlinelibrary.wiley.com/doi/10.1111/ssqu.70125

## Secundaria — motivación y contexto (no núcleo metodológico actual)

*(Se conservan porque justifican la relevancia/originalidad de la tesis o cubren
aspectos que quedaron fuera del foco metodológico actual — no descartadas, pero no
son insumo directo de la Alternativa 3.)*

### Identificación de talento (Talent Identification, TI)

- Reeves, M. J., Roberts, S. J., McRobert, A. P., & Littlewood, M. A. (2018). *Factors
  affecting the identification of talented junior-elite footballers: a case study.*
  Soccer & Society, 19(8), 1106-1121.

- Reeves, M. J., McRobert, A., Lewis, C., & Roberts, S. (2019). *A case study of verbal
  reports for Talent Identification purposes in soccer: A Messi affair!* PLoS ONE,
  14(11), e0221151.

### Modelos de negocio de clubes (Ajax / AZ Alkmaar) — literatura gris

- Training Ground Guru (2025). *Daan Uitermark: How AZ Alkmaar are using data as their
  "compass".* https://trainingground.guru/daan-uitermark-how-az-alkmaar-are-using-data-as-their-compass/

- Stats Perform (2019). *AZ Alkmaar - Combining Data and Technology to Evolve
  Recruitment Processes.*
  https://www.statsperform.com/resource/az-alkmaar-combining-data-and-technology-to-evolve-recruitment-processes/

> No se identificó literatura académica peer-reviewed sobre los modelos de datos
> internos de clubes específicos (Ajax, AZ). Ver `docs/justificacion_variable_dependiente.md`,
> sección 7.

### Modelado predictivo de eventos (deprioritizado para el diseño actual)

- *Estimating Player Performance in Different Contexts Using Finetuned Large Events
  Models.* Mendes-Neves et al. (2024). arXiv:2402.06815.
  https://arxiv.org/abs/2402.06815
  Relevante para una eventual etapa predictiva basada en eventos de partido; no es
  insumo directo de la Alternativa 3, que trabaja sobre agregados de temporada, no
  sobre eventos. Se conserva para revisar si se retoma en una etapa posterior.

## Fuente de datos

- Dataset: `davidcariboo/player-scores` (Kaggle) —
  https://www.kaggle.com/datasets/davidcariboo/player-scores
- Repositorio del dataset (dbt, esquema, actualización semanal):
  https://github.com/dcaribou/transfermarkt-datasets
