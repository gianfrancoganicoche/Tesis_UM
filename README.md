# Tesis: Predicción del desarrollo de jóvenes futbolistas vía crecimiento de valor de mercado

Repositorio de trabajo para la tesis de la Maestría en Data Science (Universidad de Montevideo).

## Pregunta de investigación

¿Es posible predecir la trayectoria de desarrollo de jóvenes futbolistas (sub-23, ligas europeas),
aislando la contribución individual del jugador de los efectos de equipo y liga, usando el
crecimiento del valor de mercado de Transfermarkt (ventana T → T+3) como variable dependiente?

## Estructura del repositorio

```
.
├── data/
│   ├── raw/            # datos crudos descargados (no versionados, ver .gitignore)
│   └── processed/      # paneles ya construidos (panel_final.csv, etc.)
├── docs/               # documentos de la tesis (justificación, bitácora, tema)
├── notebooks/          # exploración interactiva (Jupyter)
├── src/                # código reutilizable del pipeline
│   └── panel_pipeline.py
└── requirements.txt
```

## Metodología (resumen)

1. **Fuente de datos**: [`davidcariboo/player-scores`](https://www.kaggle.com/datasets/davidcariboo/player-scores) (Kaggle),
   dump curado de Transfermarkt, actualizado semanalmente.
2. **Construcción del panel**: pares T → T+3 por jugador, apilados en todo el período histórico
   disponible (2010 en adelante, por densidad de cobertura).
3. **Población**: jugadores sub-23 (edad ≤ 20 en T), ligas europeas.
4. **Variable dependiente**: `crecimiento_log = log(valor_T+3) - log(valor_T)`.
5. **Modelo**: efectos fijos de liga/año/posición (fase actual) → modelo jerárquico con
   shrinkage para estimar α_i individual (próxima fase) → modelo predictivo (XGBoost/Random Forest).

## Estado actual

- [x] Definición del tema y alcance (ver `docs/tema_tesis.docx`)
- [x] Justificación de la variable dependiente (ver `docs/justificacion_variable_dependiente.docx`)
- [x] Pipeline de construcción del panel T→T+3 (`src/panel_pipeline.py`)
- [x] Primer modelo de efectos fijos (liga + año + posición)
- [ ] Modelo de efectos mixtos / shrinkage para α_i individual
- [ ] Análisis de robustez (horizontes T+1 a T+4, exclusión de shocks de torneos)
- [ ] Modelo predictivo (XGBoost/Random Forest)

## Cómo correr el pipeline

```bash
pip install -r requirements.txt
python src/panel_pipeline.py
```

## Bitácora y documentos de tesis

Los documentos formales de la tesis (bitácora, tema, justificaciones) viven en `docs/` como
archivos de Word, para mantener compatibilidad con el flujo de trabajo con el tutor.
