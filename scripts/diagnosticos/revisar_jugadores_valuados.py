"""
Script ad-hoc: revisar_jugadores_valuados.py

Investiga la correlacion negativa de jugadores_valuados con
log_valor_mercado (-0.20 en el EDA de e01).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_RAIZ_SCRIPTS = Path(__file__).resolve().parents[1]  # scripts/, tras la reorganizacion en subcarpetas (22/09)
for _carpeta in ("config", "dataset", "eda", "diagnosticos"):
    sys.path.insert(0, str(_RAIZ_SCRIPTS / _carpeta))
import e01_analisis_exploratorio as e01


def main():
    dataset = e01.cargar_dataset_modelable()

    columnas = [
        "jugadores_valuados", "valor_promedio_plantel", "valor_total_plantel",
        "companieros_distintos", "log_valor_mercado",
    ]
    presentes = [c for c in columnas if c in dataset.columns]
    correlaciones = dataset[presentes].corr(method="pearson")

    print("=== Correlacion (Pearson) de jugadores_valuados con otras variables ===")
    print(correlaciones["jugadores_valuados"].sort_values(ascending=False))

    print("\n=== log_valor_mercado promedio por bin de jugadores_valuados ===")
    bins = pd.qcut(dataset["jugadores_valuados"], q=5, duplicates="drop")
    resumen = dataset.groupby(bins, observed=True).agg(
        n=("jugadores_valuados", "size"),
        jugadores_valuados_promedio=("jugadores_valuados", "mean"),
        valor_promedio_plantel_promedio=("valor_promedio_plantel", "mean"),
        log_valor_mercado_promedio=("log_valor_mercado", "mean"),
    )
    print(resumen.to_string())

    print("\n=== Correlacion parcial: jugadores_valuados vs log_valor_mercado, "
          "controlando valor_promedio_plantel ===")
    validos = dataset.dropna(subset=["jugadores_valuados", "valor_promedio_plantel", "log_valor_mercado"])
    x = validos["valor_promedio_plantel"].to_numpy()

    def residuo(y):
        pendiente, ordenada = np.polyfit(x, y.to_numpy(), 1)
        return y.to_numpy() - (pendiente * x + ordenada)

    resid_jugadores = residuo(validos["jugadores_valuados"])
    resid_dv = residuo(validos["log_valor_mercado"])
    parcial = np.corrcoef(resid_jugadores, resid_dv)[0, 1]
    print(f"Correlacion parcial (controlando valor_promedio_plantel): {parcial:.3f}")

    return correlaciones, resumen


if __name__ == "__main__":
    correlaciones_jugadores_valuados, resumen_jugadores_valuados = main()