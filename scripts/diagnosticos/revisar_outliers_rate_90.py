"""
Diagnostico puntual (21/09/2026): confirmar el mecanismo detras del maximo
de exactamente 90 en las cuatro variables "por 90 minutos" sin piso de
confiabilidad (goles_90, asistencias_90, contribucion_gol_90, tarjetas_90) --
la hipotesis es "pocos minutos jugados + un evento = tasa extrapolada a 90".
No es parte del pipeline (no depende de nada de d0X salvo config) -- consulta
ad-hoc, sin prefijo, igual que revisar_edad_outliers.py.
"""

import sys
from pathlib import Path

import pandas as pd

_RAIZ_SCRIPTS = Path(__file__).resolve().parents[1]  # scripts/, tras la reorganizacion en subcarpetas (22/09)
for _carpeta in ("config", "dataset", "eda", "diagnosticos"):
    sys.path.insert(0, str(_RAIZ_SCRIPTS / _carpeta))

import config

COLUMNAS_90 = ["goles_90", "asistencias_90", "contribucion_gol_90", "tarjetas_90"]

candidatos = sorted(config.RUTA_DATOS_PROCESSED.glob("dataset_modelable_*.csv"))
if not candidatos:
    raise FileNotFoundError(
        "No se encontro ningun dataset_modelable_*.csv en data/processed -- "
        "correr primero d06_extraer_panel_predictores.py."
    )
ruta_dataset = candidatos[-1]
print(f"Usando: {ruta_dataset.name}")

dataset = pd.read_csv(ruta_dataset)

# Umbral 89 (no exactamente 90) por si hay imprecision de float en la division.
mascara = (dataset[COLUMNAS_90] >= 89).any(axis=1)
casos = dataset.loc[mascara].copy()
print(f"\n{len(casos)} de {len(dataset)} filas ({len(casos) / len(dataset):.4%}) "
      f"tienen alguna variable '_90' >= 89.")

players = pd.read_csv(
    config.RUTA_DATOS_CONGELADOS / "players.csv",
    usecols=["player_id", "name"],
)
casos = casos.merge(players, on="player_id", how="left")

columnas_diagnostico = [
    "name", "player_id", "season", "minutos_totales", "partidos_jugados",
    "minutos_confiables", "goles_totales", "asistencias_totales",
    "tarjetas_amarillas", "tarjetas_rojas",
] + COLUMNAS_90

print("\nCasos ordenados por minutos_totales (deberian ser todos muy bajos, si la hipotesis es correcta):")
print(casos[columnas_diagnostico].sort_values("minutos_totales").to_string(index=False))

print(f"\nminutos_confiables=False en estos casos: {(~casos['minutos_confiables']).mean():.2%} "
      "(deberia ser cerca de 100% si el problema es realmente 'pocos minutos, sin piso de confiabilidad').")
print("minutos_totales -- describe de estos casos:")
print(casos["minutos_totales"].describe())