# Tesis — Trayectoria de valor de mercado de futbolistas jóvenes

Tesis de la Maestría en Data Science (Universidad de Montevideo). Autor: Gianfranco Ganicoche. Tutor: Alan Silberman.

## Descripción

El proyecto busca separar la **calidad individual** de un jugador joven del **efecto de su contexto** (club y liga) al explicar la evolución de su valor de mercado en Transfermarkt.

- **Variable dependiente:** `log_valor_mercado` (valor de mercado en euros, en logaritmo), a nivel jugador-temporada.
- **Metodología (Alternativa 3):** modelo bayesiano jerárquico, inspirado en Dinsdale & Gallagher (2022) y Säfvenberg et al. (2024). El valor se descompone en:
  - nivel por posición + curva de edad (polinomio de grado 2, con desvíos por posición),
  - variables de contexto de club/liga,
  - variables de rendimiento individual y atributos del jugador,
  - un efecto aleatorio por jugador (α_i) con contracción (*shrinkage*).
  - Extensión opcional: efecto temporal γ_t como paseo aleatorio.
- **Hipótesis central (H1):** el contexto de equipo y liga explica varianza significativa del valor de los sub-23 más allá de la curva de edad. Se contrasta comparando modelos con y sin contexto (LOO / ΔELPD, agrupado por jugador).
- **Variante autorregresiva (m05, prevista):** agrega `log_valor_previo` (último valor registrado antes de la temporada) y `rezago_previo` (antigüedad de esa valuación). No forma parte del modelo base.

**Datos:** dataset público de Kaggle `davidcariboo/player-scores` (Transfermarkt). El snapshot se congela localmente con `d01`; el resto del pipeline lee solo de esa copia.

## Estado del proyecto

Última actualización: 2026-10-31. Entrega: 1 de diciembre. Defensa: 8 de diciembre.

| Bloque | Estado |
|---|---|
| Pipeline de datos (`d01`–`d09`) | Terminado |
| Análisis exploratorio (`e01`–`e08`) | Terminado |
| Dataset de modelado (`m01`) | Terminado; reconstrucción con las decisiones nuevas en curso |
| Modelo base (`m02`) | Escrito, todavía **no ejecutado** |
| Modelos siguientes (`m03`–`m06`) | Pendientes |
| Redacción | Pendiente |

**En curso.** Hay decisiones de modelado pendientes de validación con el tutor (tutoría del 2026-11-02). Están documentadas en `entregables/2026-10-18_decisiones_antes_de_modelar.docx`:

1. Construcción de `log_valor_previo` (variante C).
2. Tratamiento de faltantes de rendimiento (se completan con 0 más un indicador `pocos_minutos`).
3. `reputacion_vendedor` solo para 2017–2025.
4. Valuaciones faltantes de 2024: es un hueco de la fuente, no se imputa; se corre como análisis de sensibilidad.

El dataset se reconstruyó con las decisiones propuestas (`amarillas_90` y `tuvo_roja` en lugar de `tarjetas_90`) para poder correr `m02` como si ya estuvieran validadas. Si el tutor cambia alguna, se reconstruye.

**Próximos pasos:** corrida completa de `m02`, revisión de residuos (2021 y 2024), LOO agrupado por jugador y luego `m03`–`m06`.

## Estructura del repositorio

```
scripts/
  config/        rutas, constantes y estilo de gráficos
  dataset/       d01–d09: pipeline de construcción de datos
  eda/           e01–e08: análisis exploratorio (no modifica datos)
  modelado/      m01–m0X: dataset de modelado y modelos
  diagnosticos/  consultas puntuales de auditoría
  entorno/       scripts de setup (PowerShell)
entregables/     documentos para el tutor
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

## Cómo reproducir

Requiere Python ≥ 3.14 y [uv](https://docs.astral.sh/uv/).

```powershell
uv sync

# 1. Snapshot local de los datos (única vez; usa kagglehub y requiere credenciales de Kaggle)
uv run scripts/dataset/d01_guardar_copia_local_datos.py

# 2. Panel y dataset modelable (orquesta d02–d05, d07–d09)
uv run scripts/dataset/d06_extraer_panel_predictores.py
#    Para reajustar los parámetros del z-score (solo de forma explícita):
#    uv run scripts/dataset/d06_extraer_panel_predictores.py --forzar-reajuste-zscore

# 3. Dataset de modelado y modelo base
uv run scripts/modelado/m01_construir_dataset_modelado.py
uv run scripts/modelado/m02_modelo_base.py --rapido
```

Notas:

- Ejecutar los scripts como archivo (`uv run ...` o `%run`), no pegando el contenido en la consola: usan `__file__` para resolver imports.
- Los loaders toman el archivo más reciente por orden alfabético del nombre.
- Los parámetros del z-score se guardan en `data/processed/parametros_*.json` (versionados); no se reajustan salvo pedido explícito.

## Datos

`data/raw/` y `data/processed/` no se suben al repositorio (por tamaño y por licencia del dataset). Se regeneran con los pasos de arriba. Se versiona solo `data/processed/parametros_*.json`.

## Documentos

En `entregables/` están los informes de cada etapa:

- EDA 1–6 (univariado y bivariado, reducción de variables, PCA de éxito deportivo, exclusión de `pct_victorias`, variables de rendimiento, auditoría de variables clave).
- Inventario de variables (`.docx` y `.xlsx`).
- `2026-10-18_decisiones_antes_de_modelar.docx`: contexto y decisiones a validar con el tutor.
