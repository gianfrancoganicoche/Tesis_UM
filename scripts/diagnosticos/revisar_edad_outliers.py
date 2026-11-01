"""
Script ad-hoc: revisar_edad_outliers.py

Investiga las filas con edad fuera del rango esperado [14, 42] en
dataset_modelable.
"""
import sys
from pathlib import Path

_RAIZ_SCRIPTS = Path(__file__).resolve().parents[1]  # scripts/, tras la reorganizacion en subcarpetas (22/09)
for _carpeta in ("config", "dataset", "eda", "diagnosticos"):
    sys.path.insert(0, str(_RAIZ_SCRIPTS / _carpeta))
import e01_analisis_exploratorio as e01


def main():
    dataset = e01.cargar_dataset_modelable()
    outliers = dataset[(dataset["edad"] < 14) | (dataset["edad"] > 42)].copy()
    outliers = outliers.sort_values("edad", ascending=False)

    columnas = [c for c in [
        "player_id", "season", "edad", "log_valor_mercado",
        "valor_mercado_eur", "club_id", "partidos_jugados",
    ] if c in outliers.columns]

    print(f"Filas con edad fuera de [14, 42]: {len(outliers)}")
    print(outliers[columnas].to_string(index=False))

    return outliers


if __name__ == "__main__":
    outliers_edad = main()