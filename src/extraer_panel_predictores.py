"""
Script de extraccion: descarga/carga el dataset davidcariboo/player-scores,
corre el pipeline completo (variables de contexto + rendimiento + panel de
predictores) y guarda el resultado en data/processed/.

Uso: correr desde la raiz del repo (Tesis_UM/), con src/ en el path.
"""

import os
import sys

sys.path.append("src")

import kagglehub
import pandas as pd

from construir_panel_predictores import construir_panel_predictores
import construir_variables_contexto as ctx


def cargar_tablas():
    """
    Descarga (o reutiliza cache local) el dataset via kagglehub -- no
    hardcodea la ruta de version, para que el script siga funcionando si
    kagglehub actualiza la version cacheada localmente (ej. v671 -> v673,
    ya visto en esta sesion). Si en algun momento se necesita fijar una
    version exacta para reproducibilidad, agregar el parametro correspondiente
    aca, documentando por que.
    """
    path = kagglehub.dataset_download("davidcariboo/player-scores")
    print(f"Dataset en: {path}")

    return {
        "players": pd.read_csv(f"{path}/players.csv"),
        "clubs": pd.read_csv(f"{path}/clubs.csv"),
        "competitions": pd.read_csv(f"{path}/competitions.csv"),
        "games": pd.read_csv(f"{path}/games.csv"),
        "club_games": pd.read_csv(f"{path}/club_games.csv"),
        "game_lineups": pd.read_csv(f"{path}/game_lineups.csv"),
        "appearances": pd.read_csv(f"{path}/appearances.csv"),
        "transfers": pd.read_csv(f"{path}/transfers.csv"),
        "player_valuations": pd.read_csv(f"{path}/player_valuations.csv"),
    }


def main():
    tablas = cargar_tablas()

    panel = construir_panel_predictores(tablas)

    # NaN de competencias europeas = "no jugo europeo esa temporada", no dato
    # faltante -- rellenar explicito (ver bitacora entrada 4, 20/07/2026)
    cols_europeas_a_cero = ["partidos_europeos", "fase_maxima_alcanzada", "competencias_distintas"]
    panel[cols_europeas_a_cero] = panel[cols_europeas_a_cero].fillna(0)
    panel["jugo_fase_grupos_o_mas"] = panel["jugo_fase_grupos_o_mas"].fillna(False)

    # Chequeo de sanidad antes de guardar -- no guardar silenciosamente un
    # panel con duplicados de clave
    n_duplicados = panel.duplicated(subset=["player_id", "season"]).sum()
    if n_duplicados > 0:
        raise ValueError(
            f"El panel tiene {n_duplicados} filas duplicadas en (player_id, season). "
            "No se guarda hasta resolver la causa."
        )
    print(f"Panel de predictores: {panel.shape[0]} filas, {panel.shape[1]} columnas. Sin duplicados.")

    os.makedirs("data/processed", exist_ok=True)
    fecha = pd.Timestamp.now().strftime("%Y-%m-%d")

    try:
        ruta_parquet = f"data/processed/panel_predictores_{fecha}.parquet"
        panel.to_parquet(ruta_parquet, index=False)
        print(f"Guardado: {ruta_parquet}")
    except ImportError:
        print("pyarrow/fastparquet no disponibles -- guardando solo CSV.")

    ruta_csv = f"data/processed/panel_predictores_{fecha}.csv"
    panel.to_csv(ruta_csv, index=False)
    print(f"Guardado: {ruta_csv}")

    return panel


if __name__ == "__main__":
    panel_predictores = main()
