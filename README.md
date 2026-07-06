# Tesis: Predicción del desarrollo de jóvenes futbolistas vía crecimiento de valor de mercado

Repositorio de trabajo para la tesis de la Maestría en Ciencia de Datos (Universidad de Montevideo).

## Pregunta de investigación

¿Es posible aislar la contribución individual de un jugador joven al crecimiento de su valor
de mercado, separándola de los efectos de equipo, liga y shocks mediáticos, y usar esa
estimación para predecir su desarrollo futuro?

## Estructura del repositorio

```
.
├── bibliografia/
│   └── bibliografia.md                    # papers y fuentes de referencia, con links
├── data/
│   ├── raw/                                # datos crudos descargados (no versionados, ver .gitignore)
│   └── processed/                          # paneles ya construidos (panel_final.csv, etc.)
├── docs/
│   ├── tema_tesis.md
│   ├── justificacion_variable_dependiente.md
│   └── bitacora/
│       ├── 2026-06-29_entrada-01-tema-y-fuentes.md
│       ├── 2026-07-05_entrada-02-teoria.md
│       └── 2026-07-05_entrada-03-datos.md
├── notebooks/                              # exploración interactiva (Jupyter)
├── src/                                    # código reutilizable del pipeline
│   └── panel_pipeline.py
└── requirements.txt
```

Convención de nombres de bitácora: `AAAA-MM-DD_entrada-NN-tema-breve.md`, una por sesión,
en orden cronológico visible directamente en el nombre de archivo.

## Metodología (resumen)

1. **Fuente de datos**: [`davidcariboo/player-scores`](https://www.kaggle.com/datasets/davidcariboo/player-scores) (Kaggle),
   dump curado de Transfermarkt, actualizado semanalmente. No depende de Opta (ver limitaciones
   en `docs/tema_tesis.md`, sección 4, sobre el corte de licencia que afectó a FBref).
2. **Construcción del panel**: pares T → T+3 por jugador, apilados en todo el período histórico
   disponible (2010 en adelante, por densidad de cobertura).
3. **Población**: jugadores sub-23 (edad ≤ 20 en T), ligas europeas.
4. **Variable dependiente**: `crecimiento_log = log(valor_T+3) - log(valor_T)`.
5. **Modelo**: efectos fijos de liga/año/posición (fase actual) → modelo jerárquico con
   shrinkage para estimar α_i individual (próxima fase) → modelo predictivo (XGBoost/Random Forest).

## Estado actual

- [x] Definición del tema y alcance (`docs/tema_tesis.md`)
- [x] Justificación de la variable dependiente (`docs/justificacion_variable_dependiente.md`)
- [x] Pipeline de construcción del panel T→T+3 (`src/panel_pipeline.py`)
- [x] Primer modelo de efectos fijos (liga + año + posición) — R² Within ≈ -0.02,
      confirma insuficiente variación intra-jugador para efectos fijos estándar
- [ ] Modelo de efectos mixtos / shrinkage para α_i individual (siguiente paso)
- [ ] Análisis de robustez (horizontes T+1 a T+4, exclusión de shocks de torneos)
- [ ] Definir features de rendimiento sin Opta/FBref (Etapa 2, KPIs por posición)
- [ ] Modelo predictivo (XGBoost/Random Forest)

## Cómo correr el pipeline

```bash
pip install -r requirements.txt
python src/panel_pipeline.py
```

## Bitácora y documentos de tesis

Toda la documentación de la tesis vive en `docs/` en formato Markdown (migrada desde Word
para facilitar lectura y versionado directo en GitHub). La bitácora cronológica está en
`docs/bitacora/`, una entrada por sesión de trabajo.
