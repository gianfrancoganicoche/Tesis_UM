"""
revisar_mapa_liga_paso_a_paso.py -- ad-hoc: reproduce el cruce de m01
(construir_columnas_liga) paso a paso, imprimiendo dtypes y diversidad en
cada etapa, para encontrar en que punto exacto se pierde la variedad real
de ligas (el mapa club-liga SI tiene diversidad -- confirmado con
revisar_mapa_liga.py -- asi que el problema esta en como m01 lo usa).
"""
import sys
from pathlib import Path

import pandas as pd

_RAIZ_SCRIPTS = Path(__file__).resolve().parents[1]
for _carpeta in ("config", "dataset", "eda", "diagnosticos"):
    sys.path.insert(0, str(_RAIZ_SCRIPTS / _carpeta))

import config
import d02_construir_variables_contexto as ctx


def main():
    candidatos = sorted(config.RUTA_DATOS_PROCESSED.glob("panel_predictores_*.csv"))
    ruta_panel = candidatos[-1]
    print(f"Usando panel: {ruta_panel.name}")
    panel = pd.read_csv(ruta_panel, usecols=["player_id", "season", "club_id"])

    print("\n=== Paso 0: club_por_jugador (panel_predictores) ===")
    print("shape:", panel.shape)
    print("dtypes:\n", panel.dtypes)
    print("club_id unicos:", panel["club_id"].nunique())
    print("NaN en club_id:", panel["club_id"].isna().sum())
    print(panel["club_id"].value_counts().head(10))

    tablas = ctx.cargar_tablas()
    mapa_club_liga = ctx.construir_mapa_club_liga_por_temporada(tablas["games"], tablas["club_games"])

    print("\n=== mapa_club_liga (de d02) ===")
    print("shape:", mapa_club_liga.shape)
    print("dtypes:\n", mapa_club_liga.dtypes)
    print("club_id unicos:", mapa_club_liga["club_id"].nunique())

    print("\n=== Paso 1: merge panel + mapa_club_liga on [club_id, season] ===")
    paso1 = panel.merge(mapa_club_liga, on=["club_id", "season"], how="left")
    print("shape post-merge:", paso1.shape, "(deberia seguir siendo", panel.shape[0], "filas)")
    print("NaN en competition_id post-merge:", paso1["competition_id"].isna().sum())
    print("competition_id distintos post-merge:", paso1["competition_id"].nunique())
    print(paso1["competition_id"].value_counts(dropna=False).head(15))

    print("\n=== Paso 2: merge paso1 + competitions[[competition_id, confederation, type, sub_type]] ===")
    competitions = tablas["competitions"]
    print("competition_id duplicados en competitions.csv:", competitions["competition_id"].duplicated().sum())
    paso2 = paso1.merge(
        competitions[["competition_id", "confederation", "type", "sub_type"]],
        on="competition_id", how="left",
    )
    print("shape post-merge:", paso2.shape, "(deberia seguir siendo", panel.shape[0], "filas)")
    print("confederation value_counts (dropna=False):")
    print(paso2["confederation"].value_counts(dropna=False))


if __name__ == "__main__":
    main()