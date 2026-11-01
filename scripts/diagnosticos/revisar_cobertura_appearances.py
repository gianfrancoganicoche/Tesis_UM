"""
revisar_cobertura_appearances.py -- ad-hoc: confirma (o descarta) la hipotesis
de que appearances.csv en si mismo tiene cobertura real casi exclusivamente
europea para domestic_league, INDEPENDIENTEMENTE de
construir_crosswalk_jugador_club_temporada (d03) y de
construir_mapa_club_liga_por_temporada (d02).

Va directo a la fuente: appearances.csv + games.csv + competitions.csv, sin
pasar por club_games ni por el mapa club_id->season->competition_id (ese mapa
ya se descarto como sospechoso con revisar_mapa_liga.py y
revisar_mapa_liga_paso_a_paso.py: el mapa SI tiene diversidad real).

Ojo: appearances.csv trae competition_id de forma mas directa que el mapa de
d02 -- via su propio game_id -> games.csv -> competition_id, fila por fila,
sin necesitar agregar por moda. Por eso este chequeo es mas fuerte que
mirar solo el mapa club-liga.
"""
import sys
from pathlib import Path

_RAIZ_SCRIPTS = Path(__file__).resolve().parents[1]
for _carpeta in ("config", "dataset", "eda", "diagnosticos"):
    sys.path.insert(0, str(_RAIZ_SCRIPTS / _carpeta))

import config
import d02_construir_variables_contexto as ctx


def main():
    tablas = ctx.cargar_tablas()
    appearances = tablas["appearances"]
    games = tablas["games"]
    competitions = tablas["competitions"]

    print("=== appearances.csv: shape crudo ===")
    print(appearances.shape)
    print("columnas:", list(appearances.columns))
    print("player_club_id unicos en TODO appearances.csv (sin filtrar):", appearances["player_club_id"].nunique())

    # NOTA (25/09, corregido tras el primer intento real): appearances.csv YA
    # trae su propia columna "competition_id" nativa -- no hace falta (y de
    # hecho colisiona, pandas la resuelve como _x/_y) traerla de nuevo desde
    # games.csv. De games.csv solo se necesitan "season" y "competition_type",
    # que appearances.csv no tiene.
    if "competition_id" not in appearances.columns:
        raise KeyError(
            "Se esperaba que appearances.csv trajera su propia columna "
            "'competition_id' nativa (asi salio en la corrida real del "
            "25/09). Si esto cambio, avisar antes de seguir -- no asumir."
        )

    print("\n=== Paso 1: appearances + games[[game_id, season, competition_type]] ===")
    cruce = appearances.merge(
        games[["game_id", "season", "competition_type"]],
        on="game_id", how="left",
    )
    print("shape post-merge:", cruce.shape, "(deberia seguir siendo", appearances.shape[0], "filas y",
          appearances.shape[1] + 2, "columnas)")
    print("NaN en season tras el merge con games:", cruce["season"].isna().sum())
    print("NaN en competition_type tras el merge con games:", cruce["competition_type"].isna().sum())
    print("NaN en competition_id (nativo de appearances.csv, no vino del merge):", cruce["competition_id"].isna().sum())

    print(f"\n=== Paso 2: filtro domestic_league, season >= {config.ANIO_MIN_COBERTURA_GAMES} ===")
    domesticas = cruce[
        (cruce["season"] >= config.ANIO_MIN_COBERTURA_GAMES)
        & (cruce["competition_type"] == "domestic_league")
    ]
    print(f"filas resultantes: {len(domesticas)} de {len(cruce)}")
    print("competition_id distintos:", domesticas["competition_id"].nunique())
    print(domesticas["competition_id"].value_counts())
    print("player_club_id distintos (con >=1 aparicion real en domestic_league):", domesticas["player_club_id"].nunique())

    print("\n=== Paso 3: confederation a nivel de FILA de appearances (no de jugador-temporada) ===")
    con_confed = domesticas.merge(
        competitions[["competition_id", "confederation"]], on="competition_id", how="left"
    )
    print(con_confed["confederation"].value_counts(dropna=False))
    print(
        "\n-> Si esto ya sale ~100% 'europa' ACA, con cero pasos de agregacion "
        "de por medio, confirma que appearances.csv en si mismo carece de "
        "cobertura real para ligas domesticas no europeas (no es un artefacto "
        "de construir_crosswalk_jugador_club_temporada ni del mapa club-liga)."
    )

    print("\n=== Paso 4 (contraste): universo de ligas domesticas segun competitions.csv ===")
    domesticas_universo = competitions[competitions["type"] == "domestic_league"]
    print(f"ligas domesticas en competitions.csv: {len(domesticas_universo)}")
    print(domesticas_universo["confederation"].value_counts())
    print(
        "\n-> Comparar esto con el Paso 3: si aca hay diversidad real (europa + "
        "americas + asien, con volumenes de partidos > 0 segun club_games/games) "
        "pero el Paso 3 sale monolitico, la diversidad del CALENDARIO no se "
        "traduce en cobertura real de EVENTOS (appearances.csv)."
    )


if __name__ == "__main__":
    main()