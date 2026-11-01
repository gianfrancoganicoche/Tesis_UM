"""
revisar_funnel_cobertura_appearances.py -- funnel completo, paso a paso, de
como appearances.csv se reduce hasta las filas de domestic_league europeas
(ver revisar_cobertura_appearances.py). Ademas, prueba DIRECTAMENTE la
hipotesis de Gianfranco (25/09): que las ligas no europeas no aparezcan por
un problema de NaN en el filtro (season/competition_type tras el merge con
games.csv), y no porque realmente carezcan de apariciones en el archivo.

La prueba clave (antes de aplicar ningun filtro): se busca en TODO
appearances.csv, usando su columna competition_id NATIVA, cualquier fila
que pertenezca a una de las ligas domesticas no europeas reales (segun
competitions.csv). Si esto ya da 0, las ligas no europeas no tienen
NINGUNA fila en appearances.csv bajo ningun filtro -- descarta de raiz la
hipotesis del NaN. Si da >0, el funnel de los pasos siguientes muestra
exactamente en que escalon se pierden.
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

    n0 = len(appearances)
    print(f"Paso 0 -- appearances.csv crudo: {n0} filas")

    # ---- universo real de ligas domesticas NO europeas (competitions.csv) ----
    ligas_no_europeas = competitions[
        (competitions["type"] == "domestic_league") & (competitions["confederation"] != "europa")
    ]["competition_id"].tolist()
    print(f"\nLigas domesticas NO europeas segun competitions.csv ({len(ligas_no_europeas)}): {ligas_no_europeas}")

    # ---- LA PRUEBA CLAVE: sin aplicar NINGUN filtro todavia ----
    filas_no_europeas_sin_filtrar = appearances[appearances["competition_id"].isin(ligas_no_europeas)]
    print(
        f"\n=== PRUEBA CLAVE: filas en appearances.csv cuyo competition_id NATIVO ya es "
        f"una liga no europea, SIN aplicar ningun filtro de season/competition_type: "
        f"{len(filas_no_europeas_sin_filtrar)} ==="
    )
    if len(filas_no_europeas_sin_filtrar) > 0:
        print(filas_no_europeas_sin_filtrar["competition_id"].value_counts())
    print(
        "-> Si esto da 0: las ligas no europeas no tienen NINGUNA fila en "
        "appearances.csv, bajo ningun filtro -- se descarta la hipotesis del NaN, "
        "es una ausencia real y total de cobertura, no un problema del filtro.\n"
        "-> Si da >0: los pasos siguientes muestran en que escalon se pierden esas filas."
    )

    # ---- Paso 1: merge con games (season, competition_type) ----
    cruce = appearances.merge(games[["game_id", "season", "competition_type"]], on="game_id", how="left")
    n1_nan_season = cruce["season"].isna().sum()
    n1_nan_tipo = cruce["competition_type"].isna().sum()
    print(f"\nPaso 1 -- merge con games: NaN en season={n1_nan_season}, NaN en competition_type={n1_nan_tipo}")

    sin_tipo = cruce[cruce["competition_type"].isna()]
    sin_tipo_no_europeas = sin_tipo[sin_tipo["competition_id"].isin(ligas_no_europeas)]
    print(
        f"De esas {n1_nan_tipo} filas sin competition_type (game_id no matcheo en games.csv), "
        f"{len(sin_tipo_no_europeas)} tienen competition_id nativo de liga NO europea."
    )
    if len(sin_tipo_no_europeas) > 0:
        print(sin_tipo_no_europeas["competition_id"].value_counts())

    # ---- Paso 2: filtro season >= anio_min ----
    paso2 = cruce[cruce["season"] >= config.ANIO_MIN_COBERTURA_GAMES]
    print(f"\nPaso 2 -- filtro season>={config.ANIO_MIN_COBERTURA_GAMES}: quedan {len(paso2)} de {len(cruce)}")
    excluidas_por_season = cruce[~(cruce["season"] >= config.ANIO_MIN_COBERTURA_GAMES)]
    excluidas_por_season_no_europeas = excluidas_por_season[
        excluidas_por_season["competition_id"].isin(ligas_no_europeas)
    ]
    print(
        f"De las {len(excluidas_por_season)} excluidas aca (season<{config.ANIO_MIN_COBERTURA_GAMES} o NaN), "
        f"{len(excluidas_por_season_no_europeas)} son de liga NO europea."
    )

    # ---- Paso 3: filtro competition_type == domestic_league ----
    paso3 = paso2[paso2["competition_type"] == "domestic_league"]
    print(f"\nPaso 3 -- filtro competition_type=='domestic_league': quedan {len(paso3)} de {len(paso2)}")
    excluidas_por_tipo = paso2[paso2["competition_type"] != "domestic_league"]
    print("Distribucion de competition_type entre las excluidas aca (incluye NaN):")
    print(excluidas_por_tipo["competition_type"].value_counts(dropna=False))
    excluidas_por_tipo_no_europeas = excluidas_por_tipo[
        excluidas_por_tipo["competition_id"].isin(ligas_no_europeas)
    ]
    print(
        f"De esas, {len(excluidas_por_tipo_no_europeas)} tienen competition_id nativo de liga NO europea "
        f"(es decir: SI tendrian apariciones reales, pero con un competition_type distinto a 'domestic_league')."
    )
    if len(excluidas_por_tipo_no_europeas) > 0:
        print(excluidas_por_tipo_no_europeas.groupby(["competition_id", "competition_type"], dropna=False).size())

    # ---- Paso 4: confederation de lo que sobrevive los 3 filtros ----
    con_confed = paso3.merge(competitions[["competition_id", "confederation"]], on="competition_id", how="left")
    print("\nPaso 4 -- confederation de lo que sobrevive los 3 filtros:")
    print(con_confed["confederation"].value_counts(dropna=False))

    print("\n=== RESUMEN DEL FUNNEL ===")
    print(f"Paso 0 (crudo):                                        {n0}")
    print(f"Paso 1 (post-merge con games, sin filtrar todavia):    {len(cruce)}  (NaN season={n1_nan_season}, NaN tipo={n1_nan_tipo})")
    print(f"Paso 2 (season>={config.ANIO_MIN_COBERTURA_GAMES}):                             {len(paso2)}")
    print(f"Paso 3 (+ competition_type=='domestic_league'):        {len(paso3)}")


if __name__ == "__main__":
    main()