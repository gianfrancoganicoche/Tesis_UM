"""
Diagnostico puntual (22/09/2026): explorar el valor de competition_type ==
"national_team_competition" en games.csv, presente en el dataset crudo pero
todavia no usado por ningun script del pipeline (construir_variables_contexto.py
y construir_variables_rendimiento.py filtran todo explicitamente a
domestic_league). Objetivo: confirmar que efectivamente son partidos de
selecciones nacionales, ver si se puede distinguir Mundial/Eurocopa/Copa
America de eliminatorias/amistosos, y medir cobertura a nivel jugador-temporada
-- insumo para decidir si vale la pena construir una variable de participacion
en selecciones. No es parte del pipeline -- consulta ad-hoc, sin prefijo,
mismo patron que los revisar_*.py anteriores.
"""

import sys
from pathlib import Path

import pandas as pd

_RAIZ_SCRIPTS = Path(__file__).resolve().parents[1]  # scripts/, tras la reorganizacion en subcarpetas (22/09)
for _carpeta in ("config", "dataset", "eda", "diagnosticos"):
    sys.path.insert(0, str(_RAIZ_SCRIPTS / _carpeta))

import config

RUTA = config.RUTA_DATOS_CONGELADOS

# ---------------------------------------------------------------------------
# 1) games.csv: cuantos partidos son de seleccion, en que rango de temporadas
# ---------------------------------------------------------------------------
games = pd.read_csv(f"{RUTA}/games.csv")
print(f"Columnas de games.csv: {list(games.columns)}\n")

nt = games[games["competition_type"] == "national_team_competition"].copy()
print(f"{len(nt)} de {len(games)} filas de games.csv "
      f"({len(nt) / len(games):.2%}) son competition_type == 'national_team_competition'.")
print(f"Rango de season en esas filas: {nt['season'].min()} - {nt['season'].max()}")
if "date" in nt.columns:
    fechas = pd.to_datetime(nt["date"], errors="coerce")
    print(f"Rango de fechas: {fechas.min()} - {fechas.max()}")

# ---------------------------------------------------------------------------
# 2) Que competiciones son exactamente -- Mundial/Eurocopa/Copa America
#    vs. eliminatorias/amistosos. Cruce con competitions.csv.
# ---------------------------------------------------------------------------
print("\ncompetition_id mas frecuentes dentro de national_team_competition:")
print(nt["competition_id"].value_counts().head(30))

competitions = pd.read_csv(f"{RUTA}/competitions.csv")
print(f"\nColumnas de competitions.csv: {list(competitions.columns)}")

nt_comp = nt.merge(competitions, on="competition_id", how="left", suffixes=("", "_comp"))
columnas_nombre = [c for c in ["name", "country_name", "sub_type", "type"] if c in nt_comp.columns]
print(f"\nConteo de partidos por {columnas_nombre} (top 30):")
print(nt_comp.groupby(columnas_nombre).size().sort_values(ascending=False).head(30))

if "round" in nt.columns:
    print("\nValores de 'round' mas frecuentes (para ver si distingue fase de grupos/amistoso/eliminatoria):")
    print(nt["round"].value_counts().head(30))

# ---------------------------------------------------------------------------
# 3) appearances.csv: cobertura a nivel jugador-partido dentro de esta categoria
# ---------------------------------------------------------------------------
appearances = pd.read_csv(f"{RUTA}/appearances.csv")
print(f"\nColumnas de appearances.csv: {list(appearances.columns)}")

ap = appearances.merge(
    games[["game_id", "season", "competition_type"]], on="game_id", how="left"
)
ap_nt = ap[ap["competition_type"] == "national_team_competition"].copy()
print(f"\n{len(ap_nt)} filas de appearances.csv corresponden a partidos de seleccion "
      f"({ap_nt['player_id'].nunique()} jugadores distintos, "
      f"temporadas {ap_nt['season'].min()}-{ap_nt['season'].max()}).")

agregado_jugador_season = ap_nt.groupby(["player_id", "season"]).agg(
    partidos_seleccion=("appearance_id", "count"),
    minutos_seleccion=("minutes_played", "sum"),
    goles_seleccion=("goals", "sum"),
    asistencias_seleccion=("assists", "sum"),
).reset_index()

print(f"\n{len(agregado_jugador_season)} filas jugador-temporada con al menos 1 partido de seleccion.")
print("\nDescribe de partidos_seleccion / minutos_seleccion por jugador-temporada:")
print(agregado_jugador_season[["partidos_seleccion", "minutos_seleccion"]].describe())

# ---------------------------------------------------------------------------
# 4) Cruce contra el dataset_modelable: que fraccion de la poblacion sub-23
#    ya modelada tiene alguna aparicion de seleccion esa misma temporada
# ---------------------------------------------------------------------------
candidatos = sorted(config.RUTA_DATOS_PROCESSED.glob("dataset_modelable_*.csv"))
if not candidatos:
    print("\n(No se encontro dataset_modelable_*.csv en data/processed -- se omite el cruce final.)")
else:
    ruta_dataset = candidatos[-1]
    print(f"\nUsando para el cruce: {ruta_dataset.name}")
    dataset = pd.read_csv(ruta_dataset, usecols=["player_id", "season", "edad", "valor_mercado_eur"])

    cruce = dataset.merge(agregado_jugador_season, on=["player_id", "season"], how="left")
    cruce["tuvo_partido_seleccion"] = cruce["partidos_seleccion"].notna()

    print(f"\n{cruce['tuvo_partido_seleccion'].mean():.2%} de las {len(cruce)} filas del dataset_modelable "
          "tienen al menos un partido de seleccion registrado esa temporada.")

    players = pd.read_csv(f"{RUTA}/players.csv", usecols=["player_id", "name"])
    top_casos = cruce[cruce["tuvo_partido_seleccion"]].merge(players, on="player_id", how="left")
    top_casos = top_casos.sort_values("partidos_seleccion", ascending=False).head(20)
    print("\nTop 20 jugador-temporada del dataset_modelable con mas partidos_seleccion:")
    print(top_casos[["name", "player_id", "season", "edad", "valor_mercado_eur",
                      "partidos_seleccion", "minutos_seleccion", "goles_seleccion"]].to_string(index=False))