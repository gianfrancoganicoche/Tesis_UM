"""
revisar_fuentes_seleccion_nacional.py -- ad-hoc (25/09)

Motivo: Gianfranco planteo una alternativa mas simple a la variable de
"rendimiento en seleccion nacional" que ya se habia descartado por falta de
cobertura (ver revisar_national_team_competition.py, 22/09): en vez de medir
como le fue jugando, un flag binario mas modesto, "fue convocado/citado a
seleccion en este periodo". La pregunta correcta antes de proponer una
resolucion es empirica, no una suposicion.

Lo que YA esta confirmado (revisar_national_team_competition.py, corrido
sobre datos reales el 22/09): `games.csv` tiene 742 partidos con
competition_type == "national_team_competition" (Mundial=FIWC 392,
Eurocopa=EURO 215, Copa Africana=AFCN 52, eliminatorias africanas=AFAC 51,
Copa America=COPA 32), distribuidos en un rango amplio de seasons. Pero
`appearances.csv` (la unica tabla revisada hasta ahora que vincula player_id
a un game_id especifico) SOLO tiene filas para season == 2025 -- 0 filas
para 2005-2024, aunque esos partidos esten listados en games.csv. Un flag
construido desde appearances.csv de la misma manera heredaria exactamente
esa limitacion (un solo season, no sirve como variable de panel).

Lo que este script agrega (no investigado en la corrida del 22/09): hay
otras dos tablas en el dataset que tambien vinculan player_id a un game_id
especifico -- game_lineups.csv (planteles/citaciones por partido, ya usado
en d02 para posicion_amplia) y game_events.csv (eventos puntuales por
partido). Ninguna de las dos fue revisada todavia para partidos de
seleccion nacional. Si CUALQUIERA de ellas tiene cobertura real de mas de
un season (no solo 2025), el flag "fue convocado" si seria viable -- aunque
sea con una fuente distinta a appearances.csv. Este script no asume la
respuesta, la mide.

Que hace:
1. Lista los archivos .csv que existen REALMENTE en la carpeta de datos
   congelada (config.RUTA_DATOS_CONGELADOS).
2. Confirma, en games.csv, la cantidad de partidos con competition_type ==
   "national_team_competition" y su rango de seasons (deberia reproducir el
   742/0.83% ya documentado, como chequeo de que se esta mirando la misma
   version de datos).
3. Para cada tabla candidata a vincular player_id <-> game_id que exista
   (appearances.csv, game_lineups.csv, game_events.csv), cruza contra esos
   game_id y reporta que seasons sobreviven y cuantas filas/jugadores
   distintos hay por season.
4. Conclusion explicita: si alguna tabla tiene cobertura de mas de un
   season para estos partidos, el flag "fue convocado" es viable desde esa
   fuente. Si ninguna la tiene, el flag hereda la misma limitacion de un
   unico season que ya se confirmo para appearances.csv.

Nota sobre `season`: convencion de anio de arranque de temporada (ver
README_convencion_scripts.md) -- no hace falta convertir nada aca, solo se
compara la CANTIDAD de seasons distintos que aparecen, no fechas puntuales.
"""
import sys
from pathlib import Path

import pandas as pd

_RAIZ_SCRIPTS = Path(__file__).resolve().parents[1]
for _carpeta in ("config", "dataset", "eda", "diagnosticos"):
    sys.path.insert(0, str(_RAIZ_SCRIPTS / _carpeta))

import config

# tablas que, en principio, podrian vincular player_id a un game_id
# especifico. appearances.csv ya fue revisada (22/09); game_lineups.csv y
# game_events.csv son las candidatas nuevas de este script. Si en el futuro
# aparece alguna tabla nueva en el repo de datos que tambien lo haga,
# agregarla aca.
TABLAS_CANDIDATAS = ["appearances.csv", "game_lineups.csv", "game_events.csv"]

VALOR_COMPETITION_TYPE_SELECCION = "national_team_competition"


def listar_csvs_disponibles(ruta_carpeta):
    encontrados = sorted(p.name for p in ruta_carpeta.glob("*.csv"))
    print(f"=== archivos .csv encontrados en {ruta_carpeta} ===")
    if not encontrados:
        print("(ninguno -- revisar que config.RUTA_DATOS_CONGELADOS apunte a la carpeta correcta)")
    else:
        for nombre in encontrados:
            print(f"  - {nombre}")
    return encontrados


def identificar_partidos_seleccion(games):
    """Usa el filtro YA CONFIRMADO el 22/09 (revisar_national_team_competition.py):
    games.csv trae su propio competition_type == 'national_team_competition'.
    No depende de competitions.csv ni de su columna 'confederation' -- esa
    columna no alcanza para este chequeo (Copa America/Copa Africana caen
    en confederaciones 'amerika'/'afrika', no 'fifa'; el filtro correcto y
    ya validado es este)."""
    if "competition_type" not in games.columns:
        print(f"\nADVERTENCIA: games.csv no tiene columna 'competition_type' -- columnas reales: {list(games.columns)}. Ajustar el filtro.")
        return None
    nt = games[games["competition_type"] == VALOR_COMPETITION_TYPE_SELECCION].copy()
    print(f"\n=== partidos con competition_type == '{VALOR_COMPETITION_TYPE_SELECCION}' en games.csv: {len(nt)} de {len(games)} ({len(nt) / len(games):.2%}) ===")
    if len(nt) == 0:
        print("(0 partidos -- revisar si el valor de competition_type cambio en esta version de los datos)")
        return None
    print(f"Rango de season: {nt['season'].min()}-{nt['season'].max()}")
    if "competition_id" in nt.columns:
        print("competition_id mas frecuentes:")
        print(nt["competition_id"].value_counts().to_string())
    return set(nt["game_id"])


def revisar_cobertura_por_tabla(nombre_archivo, ruta_carpeta, games, game_ids_seleccion):
    ruta = ruta_carpeta / nombre_archivo
    if not ruta.exists():
        print(f"\n--- {nombre_archivo}: no existe en la carpeta de datos, se omite ---")
        return None
    tabla = pd.read_csv(ruta)
    if "game_id" not in tabla.columns or "player_id" not in tabla.columns:
        print(f"\n--- {nombre_archivo}: no tiene 'game_id' y/o 'player_id' -- columnas reales: {list(tabla.columns)}. No sirve para este chequeo. ---")
        return None

    cruce = tabla[tabla["game_id"].isin(game_ids_seleccion)].merge(
        games[["game_id", "season"]], on="game_id", how="left"
    )

    print(f"\n--- {nombre_archivo}: filas totales={len(tabla)}, filas de partidos de seleccion={len(cruce)} ---")
    if len(cruce) == 0:
        print("   (0 filas de seleccion nacional en esta tabla)")
        return set()

    resumen = cruce.groupby("season").agg(
        filas=("player_id", "count"), jugadores_distintos=("player_id", "nunique")
    ).reset_index()
    print(resumen.to_string(index=False))
    seasons_presentes = set(cruce["season"].dropna().unique())
    print(f"   -> seasons distintos con datos de seleccion: {sorted(seasons_presentes)}")
    return seasons_presentes


def main():
    ruta_carpeta = config.RUTA_DATOS_CONGELADOS
    listar_csvs_disponibles(ruta_carpeta)

    ruta_games = ruta_carpeta / "games.csv"
    if not ruta_games.exists():
        print("\nADVERTENCIA: no existe games.csv -- no se puede cruzar ninguna tabla por game_id. Se corta aca.")
        return
    games = pd.read_csv(ruta_games)
    if "season" not in games.columns:
        print(f"\nADVERTENCIA: games.csv no tiene columna 'season' -- columnas reales: {list(games.columns)}. Ajustar el script.")
        return

    game_ids_seleccion = identificar_partidos_seleccion(games)
    if not game_ids_seleccion:
        print("\nNo se identificaron partidos de seleccion nacional -- no se puede seguir con el chequeo de cobertura.")
        return

    seasons_por_tabla = {}
    for nombre_archivo in TABLAS_CANDIDATAS:
        seasons = revisar_cobertura_por_tabla(nombre_archivo, ruta_carpeta, games, game_ids_seleccion)
        if seasons is not None:
            seasons_por_tabla[nombre_archivo] = seasons

    print("\n=== CONCLUSION ===")
    if not seasons_por_tabla:
        print("Ninguna de las tablas candidatas (appearances.csv, game_lineups.csv, game_events.csv) existe o vincula player_id<->game_id en estos datos.")
        return

    tablas_con_multiples_seasons = {
        nombre: seasons for nombre, seasons in seasons_por_tabla.items() if len(seasons) > 1
    }
    if tablas_con_multiples_seasons:
        print("Hay al menos una tabla con cobertura de MAS de un season para partidos de seleccion nacional:")
        for nombre, seasons in tablas_con_multiples_seasons.items():
            print(f"  - {nombre}: seasons {sorted(seasons)}")
        print(
            "-> El flag 'fue convocado a seleccion' SI seria viable como variable de panel "
            "(con cobertura multi-temporada real), construido desde la tabla con mejor cobertura listada arriba. "
            "Falta confirmar el detalle de que representa cada fila en esa tabla (titular, suplente, convocado sin jugar) "
            "antes de definir el criterio exacto del flag."
        )
    else:
        print("NINGUNA tabla candidata tiene cobertura de mas de un season para partidos de seleccion nacional.")
        print(
            "-> El flag 'fue convocado a seleccion', si se construye desde estas tablas, hereda la misma limitacion "
            "de un unico season que ya se confirmo para appearances.csv (revisar_national_team_competition.py, 22/09) "
            "-- no aporta como variable de panel (no varia en el tiempo para la gran mayoria de jugador-temporadas)."
        )


if __name__ == "__main__":
    main()