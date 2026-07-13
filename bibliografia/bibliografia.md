# Bibliografía y fuentes de referencia

Listado centralizado de papers, artículos y fuentes usadas en la tesis, organizados por tema.
Actualizar este archivo cada vez que aparezca una fuente nueva relevante.

## Confiabilidad del valor de mercado de Transfermarkt

- Herm, S., Callsen-Bracker, H.-M., & Kreis, H. (2014). *When the crowd evaluates soccer
  players' market values: Accuracy and evaluation attributes of an online community.*
  Sport Management Review, 17(4), 484-492.
  Paywall (ScienceDirect). Metadata/abstract libre:
  https://www.semanticscholar.org/paper/When-the-crowd-evaluates-soccer-players%E2%80%99-market-and-Herm-Callsen-Bracker/b0b721775c7a1428661248ebd35fd066949a67cf

- Müller, O., Simons, A., & Weinmann, M. (2017). *Beyond crowd judgments: Data-driven
  estimation of market value in association football.* European Journal of Operational
  Research, 263(2), 611-624.
  PDF abierto: https://repub.eur.nl/pub/120757/Repub_120757_O-A.pdf

- Coates, D., & Parshakov, P. (2021/2022). *The Wisdom of Crowds and Transfer Market Values.*
  Working paper, National Research University Higher School of Economics.
  PDF abierto: https://hcapps.holycross.edu/hcs/RePEc/fek/Session08.2-Coates.pdf

- Peeters, T. (2018). *Testing the Wisdom of Crowds in the field: Transfermarkt valuations
  and international soccer results.* Working paper. (Sin acceso abierto verificado)

- Prockl, F., & Frick, B. (2018). *Information Precision in Online Communities: Player
  Valuations on www.Transfermarkt.de.* (Sin acceso abierto verificado)

- Franceschi, M., et al. (2025). *The debate behind the numbers: analyzing discussions
  about crowdsourced football player market valuations.* Managing Sport and Leisure.
  https://www.tandfonline.com/doi/full/10.1080/23750472.2025.2557905

- Transfermarkt (2021). *Transfermarkt Market Value explained - How is it determined?*
  (Documentación oficial de la plataforma sobre su propia metodología de valuación)

## Shocks de mercado / efecto de grandes torneos

- Franck, E., & Nüesch, S. (2012). *Talent and/or Popularity: What Does It Take to Be a
  Superstar?* Economic Inquiry, 50(1), 202-216.
  PDF abierto (SSRN): https://papers.ssrn.com/sol3/Delivery.cfm/SSRN_ID1710049_code943737.pdf?abstractid=1503346

- Havran, Z., Claro, D., & Nessel, K. (2026). *Talent, Capital, and the FIFA World Cup:
  How Participation Affects Football Players' Market Value.* Social Science Quarterly,
  107(1), e70125.
  https://onlinelibrary.wiley.com/doi/10.1111/ssqu.70125

## Identificación de talento (Talent Identification, TI)

- Reeves, M. J., Roberts, S. J., McRobert, A. P., & Littlewood, M. A. (2018). *Factors
  affecting the identification of talented junior-elite footballers: a case study.*
  Soccer & Society, 19(8), 1106-1121.
  Número especial completo: https://idrottsforum.org/soccer-society-volume-19-2018-issue-8-talent-identification-and-talent-development-in-junior-elite-football-in-the-uk-a-messy-affair/

- Reeves, M. J., McRobert, A., Lewis, C., & Roberts, S. (2019). *A case study of verbal
  reports for Talent Identification purposes in soccer: A Messi affair!* PLoS ONE,
  14(11), e0221151.

## Modelos de negocio de clubes (Ajax / AZ Alkmaar) — literatura gris

- Training Ground Guru (2025). *Daan Uitermark: How AZ Alkmaar are using data as their
  "compass".* https://trainingground.guru/daan-uitermark-how-az-alkmaar-are-using-data-as-their-compass/

- Stats Perform (2019). *AZ Alkmaar - Combining Data and Technology to Evolve Recruitment
  Processes.* https://www.statsperform.com/resource/az-alkmaar-combining-data-and-technology-to-evolve-recruitment-processes/

> Nota: no se identificó literatura académica peer-reviewed que documente en profundidad
> los modelos de datos internos de clubes específicos (Ajax, AZ). Ver
> `docs/justificacion_variable_dependiente.docx`, sección 7, para la discusión de este
> vacío como motivación adicional de la tesis.

## Núcleo metodológico (fixed effects / plus-minus / modelos predictivos)

- *Transfer Portal.* arXiv:2201.11533. https://arxiv.org/abs/2201.11533
- *Plus-Minus Soccer.* arXiv:1706.04943. https://arxiv.org/abs/1706.04943
- *Large Event Models.* arXiv:2402.06815. https://arxiv.org/abs/2402.06815

## Estabilidad temporal de métricas de rendimiento (persistencia de habilidad)

- Sidorowicz, H. (2026). *Year-to-Year Metric Stability in Elite Football: A Positional
  Analysis Across the Big Five European Leagues.* SportRxiv (preprint).
  https://sportrxiv.org/index.php/server/preprint/view/954
  Panel de 8.207 pares jugador-temporada (2017/18-2024/25, 2.866 jugadores únicos, 5
  grandes ligas). Mide correlación de Pearson e ICC año a año para 24 combinaciones
  posición-métrica. Hallazgo clave para esta tesis: **los jugadores sub-23 son
  sistemáticamente menos estables año a año que los veteranos en 18 de 24
  combinaciones testeadas (p < 0.05)** — evidencia académica directa a favor de tratar
  la persistencia de habilidad relativa (α_i) como hipótesis testeable y no como
  supuesto ciego en el enfoque de descomposición/recomposición (ver
  `docs/hipotesis_y_diseno_v2.md`, sección 3.1). También reporta que el % de pases
  completados es la métrica más estable en general (r = 0.824) y que todas las
  combinaciones se degradan a horizonte de dos años — relevante para la discusión de
  drift temporal y elección de horizonte de predicción.

## Fuente de datos

- Dataset: `davidcariboo/player-scores` (Kaggle) — https://www.kaggle.com/datasets/davidcariboo/player-scores
- Repositorio del dataset (dbt, esquema, actualización semanal):
  https://github.com/dcaribou/transfermarkt-datasets
