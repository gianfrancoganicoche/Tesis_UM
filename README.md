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
  - Extensión opcional: efecto temporal γ_t como paseo aleatorio.
- **Hipótesis central (H1):** el contexto de equipo y liga explica varianza significativa del valor de los sub-23 más allá de la curva de edad. Se contrasta comparando modelos con y sin contexto (LOO / ΔELPD, agrupado por jugador).
- **Variante autorregresiva:** agrega `log_valor_previo` (último valor registrado antes de la temporada) y `rezago_previo` (antigüedad de esa valuación). No forma parte del modelo base.

**Datos:** dataset público de Kaggle `davidcariboo/player-scores` (Transfermarkt). El snapshot se congela localmente con `d01`; el resto del pipeline lee solo de esa copia.

## Estado del proyecto

Última actualización: 2026-11-01.

| Bloque | Estado |
|---|---|
| Pipeline de datos (`d01`–`d09`) | Terminado |
| Análisis exploratorio (`e01`–`e08`) | Terminado |
| Dataset de modelado (`m01`) | Terminado |
| Modelo base (`m02`) | Terminado: corrida completa con convergencia aceptable, con y sin efecto de temporada |
| Contraste de H1 (`m03`) | Hecho: ΔELPD +2.081 (26 SE), el contexto mejora la predicción; falta descomponer y chequear Mundlak |
| Modelos siguientes (`m04`–`m06`) | Pendientes |
| Redacción | Pendiente |

**Próximos pasos:** chequeo de Mundlak (¿el contexto sobrevive a la correlación entre el efecto del jugador y el club?), sensibilidad al prior del efecto de temporada y a la verosimilitud t, contraste sin 2019–2020 y sin 2024, y luego porteros (`m04`), autorregresivo (`m05`) y reputación del vendedor (`m06`).

## Estructura del repositorio

```
scripts/
  config/        rutas, constantes y estilo de gráficos
  dataset/       d01–d09: pipeline de construcción de datos
  eda/           e01–e08: análisis exploratorio (no modifica datos)
  modelado/      m01–m0X: dataset de modelado y modelos
  diagnosticos/  consultas puntuales de auditoría
  entorno/       scripts de setup (PowerShell)
entregables/     documentos para el tutor, por etapa (dataset, eda, diagnosticos, modelado)
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

Los scripts de `diagnosticos/` son consultas ad hoc y no forman parte del flujo regular.

## Documentos

En `entregables/` están los informes de cada etapa, ordenados en subcarpetas como `scripts/`:

- EDA 1–6 (univariado y bivariado, reducción de variables, PCA de éxito deportivo, exclusión de `pct_victorias`, variables de rendimiento, auditoría de variables clave).
- Inventario de variables (`.docx` y `.xlsx`).
