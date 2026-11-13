# Tesis — Trayectoria de valor de mercado de futbolistas jóvenes

Tesis de la Maestría en Data Science (Universidad de Montevideo). Autor: Gianfranco Ganicoche. Tutor: Alan Silberman.

## Descripción

El proyecto busca separar la **calidad individual** de un jugador joven del **efecto de su contexto** (club y liga) al explicar la evolución de su valor de mercado en Transfermarkt.

- **Variable dependiente:** `log_valor_mercado` (valor de mercado en euros, en logaritmo), a nivel jugador-temporada.
- **Metodología:** modelo bayesiano jerárquico, inspirado en Dinsdale & Gallagher (2022) y Säfvenberg et al. (2024). El valor se descompone en:
  - nivel por posición + curva de edad (polinomio de grado 2, con desvíos por posición),
  - variables de contexto de club/liga,
  - variables de rendimiento individual y atributos del jugador,
  - un efecto aleatorio por jugador (α_i) con contracción (*shrinkage*).
  - Efecto temporal γ_t como paseo aleatorio (`--temporada rw`).
  - Chequeo de Mundlak (`--mundlak`): promedios por jugador de las covariables que varían en el tiempo, para separar el efecto dentro del efecto entre jugadores.
- **Hipótesis central (H1):** el contexto de equipo y liga explica varianza significativa del valor de los sub-23 más allá de la curva de edad. Se contrasta comparando modelos con y sin contexto (LOO / ΔELPD, agrupado por jugador).
- **Variante autorregresiva:** agrega `log_valor_previo` (último valor registrado antes de la temporada) y `rezago_previo` (antigüedad de esa valuación). No forma parte del modelo base.

**Datos:** dataset público de Kaggle `davidcariboo/player-scores` (Transfermarkt). El snapshot se congela localmente con `d01`; el resto del pipeline lee solo de esa copia.

## Estado del proyecto

Última actualización: 2026-11-13.

| Bloque | Estado |
|---|---|
| Pipeline de datos (`d01`–`d09`) | Terminado |
| Análisis exploratorio (`e01`–`e08`) | Terminado |
| Dataset de modelado (`m01`) | Terminado |
| Modelo base (`m02`) | Terminado: con y sin efecto de temporada, y con chequeo de Mundlak (`--mundlak`). El ESS mínimo (~230) corresponde al desvío entre posiciones y no afecta a los coeficientes interpretados |
| Contraste de H1 (`m03`) | Hecho: ΔELPD +2.081 (26 SE) sin Mundlak. Con Mundlak: +2.896 (36 SE) sacando todo el contexto y +556 (14 SE) sacando solo el efecto dentro del jugador. Falta la robustez temporal |
| Chequeo de Mundlak | Hecho: el efecto individual no es independiente del contexto; el efecto de los compañeros dentro del jugador (0,22) es la mitad del efecto sin Mundlak (0,42) |
| Modelos no lineales (`nl01`–`nl02`) | Código listo; falta correrlo. Pregunta del tutor: ¿un modelo no lineal predice jugadores nuevos mejor que el lineal? |
| Modelos siguientes (`m04`–`m06`) | Pendientes |
| Redacción | Pendiente |

**Próximos pasos:** contraste con Mundlak sin 2019–2020 y sin 2024 (`--excluir-temporadas`), sensibilidad al prior del efecto de temporada y a la verosimilitud t, referente no lineal (gradient boosting con los mismos pliegues por jugador, documento aparte), y luego porteros (`m04`), autorregresivo (`m05`) y reputación del vendedor (`m06`). El cronograma se reestima para la entrega de marzo de 2027.

## Estructura del repositorio

```
scripts/
  config/        rutas, constantes y estilo de gráficos
  dataset/       d01–d09: pipeline de construcción de datos
  eda/           e01–e08: análisis exploratorio (no modifica datos)
  modelado/      m01–m0X: dataset de modelado y modelos
  modelo_no_lineal/  nl01–nl0X: revisión de no linealidad (referente de boosting, splines); ver su README
  diagnosticos/  consultas puntuales de auditoría
  entorno/       scripts de setup (PowerShell)
entregables/     documentos para el tutor, por etapa (dataset, eda, diagnosticos, modelado, modelo_no_lineal)
reports/         tablas y figuras generadas
outputs/         resultados de modelos
assets/          fuentes tipográficas
data/            local, no se versiona (ver abajo)
```

### Convención de nombres

| Prefijo | Rol |
|---|---|
| `d0X` | Datos: construcción del dataset, se ejecutan en orden |
| `e0X` | Exploratorio: diagnóstico sobre datos ya construidos |
| `m0X` | Modelos |
| `nl0X` | Modelos no lineales (módulo aparte, `scripts/modelo_no_lineal/`) |

Los scripts de `diagnosticos/` son consultas ad hoc y no forman parte del flujo regular.

## Documentos

En `entregables/` están los informes de cada etapa, ordenados en subcarpetas como `scripts/`:

- EDA 1–6 (univariado y bivariado, reducción de variables, PCA de éxito deportivo, exclusión de `pct_victorias`, variables de rendimiento, auditoría de variables clave).
- Inventario de variables (`.docx` y `.xlsx`).
