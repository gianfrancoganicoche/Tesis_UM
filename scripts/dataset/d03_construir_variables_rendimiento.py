"""
Construccion de variables de rendimiento individual para el panel de la tesis.

Complementa src/construir_variables_contexto.py -- separado deliberadamente porque
son conceptualmente distintas (rendimiento individual del jugador vs. entorno en el
que juega). Fuente: davidcariboo/player-scores (Kaggle).

"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_RAIZ_SCRIPTS = Path(__file__).resolve().parents[1]  # scripts/, tras la reorganizacion en subcarpetas (22/09)
for _carpeta in ("config", "dataset", "eda", "diagnosticos"):
    sys.path.insert(0, str(_RAIZ_SCRIPTS / _carpeta))

from config import ANIO_MIN_COBERTURA_GAMES

MINUTOS_MIN_CONFIABLE = 90  # 1 partido completo 

PARTIDOS_MIN_CONFIABLE = 5  # partidos titular 

# ---------------------------------------------------------------------------
# Variable A - Rendimiento basico por jugador-temporada
# ---------------------------------------------------------------------------

def construir_rendimiento_basico(appearances, games, anio_min=ANIO_MIN_COBERTURA_GAMES):
    """
    Goles/90, asistencias/90, contribucion de gol/90, tarjetas/90 y minutos
    totales, por jugador-temporada. 

    IMPORTANTE: estandarizar (z-score) estas variables por posicion-temporada
    antes de usarlas en la descomposicion -- goles_90 no es comparable entre
    posiciones sin esa correccion.

    FLAG DE CONFIABILIDAD: minutos_confiables marca jugador-temporadas con
    menos de MINUTOS_MIN_CONFIABLE minutos -- por debajo de ese piso, los
    ratios por-90 estan dominados por ruido de muestra chica. El shrinkage
    aplicado mas adelante en el modelo complementa esto para el resto del
    gradiente de confianza -- este flag solo filtra los casos mas extremos.
    """
    ap = appearances.merge(
        games[["game_id", "season", "competition_type"]], on="game_id"
    )
    ap = ap[(ap["season"] >= anio_min) & (ap["competition_type"] == "domestic_league")]

    agregado = ap.groupby(["player_id", "season"]).agg(
        goles_totales=("goals", "sum"),
        asistencias_totales=("assists", "sum"),
        tarjetas_amarillas=("yellow_cards", "sum"),
        tarjetas_rojas=("red_cards", "sum"),
        minutos_totales=("minutes_played", "sum"),
        partidos_jugados=("appearance_id", "count"),
    ).reset_index()

    # Por 90 minutos, no por partido -- evita distorsionar a jugadores que
    # entran de suplentes con pocos minutos por partido
    minutos_90 = agregado["minutos_totales"] / 90
    agregado["goles_90"] = agregado["goles_totales"] / minutos_90
    agregado["asistencias_90"] = agregado["asistencias_totales"] / minutos_90
    agregado["contribucion_gol_90"] = agregado["goles_90"] + agregado["asistencias_90"]
    agregado["tarjetas_90"] = (
        (agregado["tarjetas_amarillas"] + agregado["tarjetas_rojas"]) / minutos_90
    )

    # Division por cero -> NaN explicito, no inf
    cols_90 = ["goles_90", "asistencias_90", "contribucion_gol_90", "tarjetas_90"]
    agregado[cols_90] = agregado[cols_90].replace([np.inf, -np.inf], np.nan)

    agregado["minutos_confiables"] = agregado["minutos_totales"] >= MINUTOS_MIN_CONFIABLE

    return agregado


def construir_pct_minutos_disponibles(appearances, club_games, games, anio_min=ANIO_MIN_COBERTURA_GAMES):
    """
    Minutos jugados por el jugador / minutos totales posibles del equipo esa
    temporada (partidos jugados por el club x 90). Proxy de confianza del
    cuerpo tecnico.

    MULTIPLES CLUBES POR TEMPORADA: un jugador transferido a mitad de temporada
    genera una fila por club en el groupby interno. Se resuelve quedandose con
    el club donde jugo mas minutos esa temporada. Se agrega el flag
    tuvo_multiples_clubes_temporada para no perder esa informacion -- una
    transferencia a mitad de temporada probablemente tenga su propio efecto
    sobre el desarrollo/valor del jugador.
    """
    ap = appearances.merge(
        games[["game_id", "season", "competition_type", "competition_id"]], on="game_id"
    )
    ap = ap[(ap["season"] >= anio_min) & (ap["competition_type"] == "domestic_league")]

    minutos_jugador = ap.groupby(["player_id", "player_club_id", "season"]).agg(
        minutos_jugador=("minutes_played", "sum")
    ).reset_index()

    partidos_club = club_games.merge(
        games[["game_id", "season", "competition_type"]], on="game_id"
    )
    partidos_club = partidos_club[
        (partidos_club["season"] >= anio_min) & (partidos_club["competition_type"] == "domestic_league")
    ]
    minutos_posibles_club = partidos_club.groupby(["club_id", "season"]).agg(
        partidos_club=("game_id", "count")
    ).reset_index()
    minutos_posibles_club["minutos_posibles"] = minutos_posibles_club["partidos_club"] * 90

    resultado = minutos_jugador.merge(
        minutos_posibles_club,
        left_on=["player_club_id", "season"], right_on=["club_id", "season"], how="left"
    )
    resultado["pct_minutos_disponibles"] = (
        resultado["minutos_jugador"] / resultado["minutos_posibles"]
    )
    resultado["pct_minutos_disponibles"] = resultado["pct_minutos_disponibles"].replace(
        [np.inf, -np.inf], np.nan
    )

    n_clubes = resultado.groupby(["player_id", "season"])["player_club_id"].transform("nunique")
    resultado["tuvo_multiples_clubes_temporada"] = n_clubes > 1

    resultado = resultado.sort_values("minutos_jugador", ascending=False).drop_duplicates(
        subset=["player_id", "season"], keep="first"
    ).sort_values(["player_id", "season"]).reset_index(drop=True)

    return resultado[["player_id", "season", "pct_minutos_disponibles", "tuvo_multiples_clubes_temporada"]]


# ---------------------------------------------------------------------------
# Variable B - Goles recibidos como titular (proxy defensivo, especialmente
# arqueros)
# ---------------------------------------------------------------------------

def construir_goles_recibidos_titular(game_lineups, club_games, games, anio_min=ANIO_MIN_COBERTURA_GAMES):
    """
    Goles recibidos como titular, por jugador-temporada.
    """
    lineups = game_lineups.merge(
        games[["game_id", "season", "competition_type"]], on="game_id"
    )
    lineups = lineups[
        (lineups["season"] >= anio_min) &
        (lineups["competition_type"] == "domestic_league") &
        (lineups["type"] == "starting_lineup")
    ]

    resultado = lineups.merge(
        club_games[["game_id", "club_id", "opponent_goals"]],
        on=["game_id", "club_id"]
    )

    agregado = resultado.groupby(["player_id", "season"]).agg(
        goles_recibidos_titular=("opponent_goals", "sum"),
        partidos_titular=("game_id", "count"),
    ).reset_index()
    agregado["goles_recibidos_90"] = agregado["goles_recibidos_titular"] / agregado["partidos_titular"]
    agregado["partidos_confiables"] = agregado["partidos_titular"] >= PARTIDOS_MIN_CONFIABLE

    return agregado


# ---------------------------------------------------------------------------
# Variable C - Goles recibidos ajustado por fuerza ofensiva del rival
# ---------------------------------------------------------------------------

def construir_goles_recibidos_ajustado_rival(game_lineups, club_games, games,
                                              anio_min=ANIO_MIN_COBERTURA_GAMES):
    """
    Goles recibidos como titular, ponderados por la fuerza ofensiva del rival
    en cada partido (goles promedio marcados por ESE rival esa temporada,
    calculado sobre el resto de sus partidos, leave-one-out).

    LEAVE-ONE-OUT: la fuerza ofensiva del rival para el partido X se calcula
    excluyendo el propio partido X del promedio del rival. Sin esto, un rival
    con pocos partidos "se perdona a si mismo" cada vez que hace una goleada.
    """
    partidos = club_games.merge(
        games[["game_id", "season", "competition_type"]], on="game_id"
    )
    partidos = partidos[
        (partidos["season"] >= anio_min) & (partidos["competition_type"] == "domestic_league")
    ]

    fuerza_ofensiva_total = partidos.groupby(["club_id", "season"]).agg(
        goles_marcados_total=("own_goals", "sum"),
        partidos_totales=("game_id", "count"),
    ).reset_index()

    lineups = game_lineups.merge(
        games[["game_id", "season", "competition_type"]], on="game_id"
    )
    lineups = lineups[
        (lineups["season"] >= anio_min) &
        (lineups["competition_type"] == "domestic_league") &
        (lineups["type"] == "starting_lineup")
    ]

    resultado = lineups.merge(
        club_games[["game_id", "club_id", "opponent_id", "opponent_goals"]],
        on=["game_id", "club_id"]
    )

    resultado = resultado.merge(
        fuerza_ofensiva_total.rename(columns={"club_id": "opponent_id"}),
        on=["opponent_id", "season"], how="left"
    )

    goles_rival_este_partido = partidos[["game_id", "club_id", "own_goals"]].rename(
        columns={"club_id": "opponent_id", "own_goals": "goles_rival_este_partido"}
    )
    resultado = resultado.merge(goles_rival_este_partido, on=["game_id", "opponent_id"], how="left")

    denom_partidos = (resultado["partidos_totales"] - 1).clip(lower=1)
    resultado["fuerza_rival_loo"] = (
        (resultado["goles_marcados_total"] - resultado["goles_rival_este_partido"]) / denom_partidos
    )
    resultado["fuerza_rival_loo"] = resultado["fuerza_rival_loo"].clip(lower=0.3)

    resultado["goles_recibidos_ajustados"] = resultado["opponent_goals"] / resultado["fuerza_rival_loo"]

    agregado = resultado.groupby(["player_id", "season"]).agg(
        goles_recibidos_ajustados_total=("goles_recibidos_ajustados", "sum"),
        partidos_titular=("game_id", "count"),
    ).reset_index()
    agregado["goles_recibidos_ajustados_90"] = (
        agregado["goles_recibidos_ajustados_total"] / agregado["partidos_titular"]
    )
    agregado["partidos_confiables"] = agregado["partidos_titular"] >= PARTIDOS_MIN_CONFIABLE

    return agregado


# ---------------------------------------------------------------------------
# Variable D - Diferencial de resultado con/sin el jugador (plus-minus)
# ---------------------------------------------------------------------------

def construir_diferencial_con_sin_jugador(game_lineups, club_games, games,
                                           anio_min=ANIO_MIN_COBERTURA_GAMES,
                                           min_partidos_grupo=5):
    """
    % de victorias del equipo en partidos donde el jugador fue titular vs.
    partidos donde no participo, misma temporada. Piso de min_partidos_grupo
    en AMBOS grupos (con/sin) antes de confiar en el diferencial.

    DECISION DE DISEnO (dejar explicita, no obvia del codigo): el grupo "sin"
    incluye tanto partidos donde el jugador no fue convocado como partidos
    donde entro desde el banco -- solo se filtra por titularidad
    (type == "starting_lineup"), no por participacion. Esto mide el efecto de
    SER TITULAR, no el efecto de participar en el partido.
    """
    partidos_club = club_games.merge(
        games[["game_id", "season", "competition_type"]], on="game_id"
    )
    partidos_club = partidos_club[
        (partidos_club["season"] >= anio_min) & (partidos_club["competition_type"] == "domestic_league")
    ][["game_id", "club_id", "season", "is_win"]]

    titular = game_lineups[game_lineups["type"] == "starting_lineup"][
        ["game_id", "player_id", "club_id"]
    ].drop_duplicates()

    # Universo: jugadores que fueron titulares, con la season REAL de ese
    # partido (join por game_id+club_id, no por club_id solo -- cruzar solo
    # por club_id multiplica cada jugador contra TODAS las temporadas del
    # club y explota la memoria a escala completa)
    titular_con_season = titular.merge(
        partidos_club[["game_id", "club_id", "season"]], on=["game_id", "club_id"]
    )
    jugadores_club_temporada = titular_con_season[
        ["player_id", "club_id", "season"]
    ].drop_duplicates()

    # Producto cartesiano acotado: cada jugador-club-temporada x cada partido de ESA club-temporada
    cruce = jugadores_club_temporada.merge(
        partidos_club[["game_id", "club_id", "season", "is_win"]], on=["club_id", "season"]
    )

    titular_marca = titular.assign(con=True)
    cruce = cruce.merge(
        titular_marca[["game_id", "player_id", "club_id", "con"]],
        on=["game_id", "player_id", "club_id"], how="left"
    )
    cruce["con"] = cruce["con"].fillna(False)

    agregado = cruce.groupby(["player_id", "club_id", "season", "con"]).agg(
        victorias=("is_win", "sum"),
        partidos=("game_id", "count"),
    ).reset_index()
    agregado["pct_victorias"] = agregado["victorias"] / agregado["partidos"]

    pivot = agregado.pivot_table(
        index=["player_id", "club_id", "season"], columns="con",
        values=["pct_victorias", "partidos"]
    )
    pivot.columns = [f"{a}_{'con' if b else 'sin'}" for a, b in pivot.columns]
    pivot = pivot.reset_index()

    pivot = pivot.dropna(subset=["pct_victorias_con", "pct_victorias_sin"])
    pivot = pivot[
        (pivot["partidos_con"] >= min_partidos_grupo) & (pivot["partidos_sin"] >= min_partidos_grupo)
    ]
    pivot["diferencial_con_sin"] = pivot["pct_victorias_con"] - pivot["pct_victorias_sin"]

    cols = ["player_id", "club_id", "season", "pct_victorias_con", "pct_victorias_sin",
            "diferencial_con_sin", "partidos_con", "partidos_sin"]
    return pivot[cols].reset_index(drop=True)


# ---------------------------------------------------------------------------
# Variable E - Participacion relativa en la produccion ofensiva del equipo
# ---------------------------------------------------------------------------

def construir_participacion_produccion_ofensiva(appearances, club_games, games,
                                                  anio_min=ANIO_MIN_COBERTURA_GAMES):
    """
    (goles + asistencias del jugador) / goles totales del equipo esa
    temporada. Normaliza produccion individual por el contexto ofensivo del
    propio equipo -- complementa a goles_90, no lo reemplaza.

    MULTIPLES CLUBES POR TEMPORADA: Se resuelve igual que minutos disponible, quedarse 
    con el club de mayor produccion (goles_asist_jugador), agregando el mismo flag
    tuvo_multiples_clubes_temporada.

    NOTA CONCEPTUAL (no es bug): el numerador suma goles+asistencias del
    jugador pero el denominador es solo goles totales del equipo -- un gol
    con asistencia cuenta doble entre goleador y asistidor, asi que la suma de
    participacion_produccion de todos los jugadores de un equipo-temporada
    puede superar 1.0.
    """
    ap = appearances.merge(
        games[["game_id", "season", "competition_type"]], on="game_id"
    )
    ap = ap[(ap["season"] >= anio_min) & (ap["competition_type"] == "domestic_league")]

    produccion_jugador = ap.groupby(["player_id", "player_club_id", "season"]).agg(
        goles=("goals", "sum"),
        asistencias=("assists", "sum"),
    ).reset_index()
    produccion_jugador["goles_asist_jugador"] = (
        produccion_jugador["goles"] + produccion_jugador["asistencias"]
    )

    partidos_club = club_games.merge(
        games[["game_id", "season", "competition_type"]], on="game_id"
    )
    partidos_club = partidos_club[
        (partidos_club["season"] >= anio_min) & (partidos_club["competition_type"] == "domestic_league")
    ]
    goles_equipo = partidos_club.groupby(["club_id", "season"]).agg(
        goles_equipo_total=("own_goals", "sum")
    ).reset_index()

    resultado = produccion_jugador.merge(
        goles_equipo, left_on=["player_club_id", "season"], right_on=["club_id", "season"], how="left"
    )
    resultado["participacion_produccion"] = (
        resultado["goles_asist_jugador"] / resultado["goles_equipo_total"].clip(lower=1)
    )

    # Flag: cuantos clubes distintos tuvo el jugador esa temporada
    n_clubes = resultado.groupby(["player_id", "season"])["player_club_id"].transform("nunique")
    resultado["tuvo_multiples_clubes_temporada"] = n_clubes > 1

    # Quedarse con el club de mayor produccion (goles+asistencias) por jugador-temporada
    resultado = resultado.sort_values("goles_asist_jugador", ascending=False).drop_duplicates(
        subset=["player_id", "season"], keep="first"
    ).sort_values(["player_id", "season"]).reset_index(drop=True)

    return resultado[["player_id", "season", "participacion_produccion", "tuvo_multiples_clubes_temporada"]]


# ---------------------------------------------------------------------------
# Variable F - Edad de debut profesional
# ---------------------------------------------------------------------------

def construir_edad_debut(appearances, players, anio_min=ANIO_MIN_COBERTURA_GAMES):
    """
    Edad en la primera aparicion registrada en appearances.csv. Proxy de
    precocidad -- conecta con la curva de edad como "velocidad de arranque"
    de la carrera.
    """
    ap = appearances.copy()
    ap["date"] = pd.to_datetime(ap["date"])
    primera_aparicion = ap.groupby("player_id")["date"].min().reset_index()
    primera_aparicion = primera_aparicion.rename(columns={"date": "fecha_debut"})

    resultado = primera_aparicion.merge(
        players[["player_id", "date_of_birth"]], on="player_id", how="left"
    )
    resultado["date_of_birth"] = pd.to_datetime(resultado["date_of_birth"])
    resultado["edad_debut"] = (
        (resultado["fecha_debut"] - resultado["date_of_birth"]).dt.days / 365.25
    )

    resultado["debut_confiable"] = resultado["fecha_debut"].dt.year > anio_min

    return resultado[["player_id", "edad_debut", "debut_confiable"]]


# ---------------------------------------------------------------------------
# Merge final - unifica las 6 variables en un panel (player_id, season)
# ---------------------------------------------------------------------------

def construir_panel_rendimiento(appearances, players, games, club_games, game_lineups,
                                 anio_min=ANIO_MIN_COBERTURA_GAMES):
    """
    Corre las 6 funciones de variables de rendimiento y las une en un unico
    panel a nivel (player_id, season).

    DECISIONES DE MERGE (dejar explicitas, no default accidental):

    1. Variable D (diferencial_con_sin_jugador) es la unica que sale con
       club_id en la clave -- las demas ya estan a nivel (player_id, season).
       Un jugador con multiples clubes en la misma temporada (~6.2% de los
       casos, ver Variable B) generaria filas duplicadas en un merge directo.
       Se resuelve con el mismo criterio ya usado en Variable B: quedarse con
       el club_id de mayor partidos_con (donde jugo mas como titular).

    2. goles_recibidos_titular y goles_recibidos_ajustado_rival comparten el
       nombre de columna partidos_confiables -- se renombran antes de
       mergear para evitar sufijos automaticos ambiguos (_x/_y).

    3. edad_debut no tiene season en su clave (es un dato de carrera, no de
       temporada) -- se mergea solo por player_id, lo que la repite
       identica en todas las filas-temporada de ese jugador. Es el
       comportamiento esperado: la edad de debut no cambia entre temporadas.

    Todas las uniones son LEFT JOIN sobre la base de rendimiento_basico (la
    variable con mayor cobertura esperada) -- un jugador-temporada puede
    quedar con NaN en alguna variable si no aplica (ej. nunca fue titular =
    NaN en goles_recibidos; nunca marco un gol de equipo = 0 en
    participacion_produccion, no NaN, por el clip ya aplicado).
    """
    rendimiento_basico = construir_rendimiento_basico(appearances, games, anio_min)
    pct_minutos = construir_pct_minutos_disponibles(appearances, club_games, games, anio_min)
    goles_recibidos = construir_goles_recibidos_titular(game_lineups, club_games, games, anio_min)
    goles_ajustados = construir_goles_recibidos_ajustado_rival(game_lineups, club_games, games, anio_min)
    diferencial = construir_diferencial_con_sin_jugador(game_lineups, club_games, games, anio_min)
    participacion = construir_participacion_produccion_ofensiva(appearances, club_games, games, anio_min)
    edad_debut = construir_edad_debut(appearances, players, anio_min)

    # Renombrar partidos_confiables antes del merge para evitar choque de nombres
    goles_recibidos = goles_recibidos.rename(columns={"partidos_confiables": "partidos_confiables_goles"})
    goles_ajustados = goles_ajustados.rename(columns={"partidos_confiables": "partidos_confiables_goles_ajustados"})
    participacion = participacion.rename(
        columns={"tuvo_multiples_clubes_temporada": "tuvo_multiples_clubes_temporada_participacion"}
    )

    # Resolver duplicados de Variable D: quedarse con el club_id de mas partidos_con
    diferencial = diferencial.sort_values("partidos_con", ascending=False).drop_duplicates(
        subset=["player_id", "season"], keep="first"
    )
    diferencial = diferencial.drop(columns=["club_id"])

    panel = rendimiento_basico.merge(pct_minutos, on=["player_id", "season"], how="left")
    panel = panel.merge(goles_recibidos, on=["player_id", "season"], how="left")
    panel = panel.merge(
        goles_ajustados[["player_id", "season", "goles_recibidos_ajustados_90", "partidos_confiables_goles_ajustados"]],
        on=["player_id", "season"], how="left"
    )
    panel = panel.merge(diferencial, on=["player_id", "season"], how="left")
    panel = panel.merge(participacion, on=["player_id", "season"], how="left")
    panel = panel.merge(edad_debut, on="player_id", how="left")

    return panel


# ---------------------------------------------------------------------------
# Crosswalk (player_id, season) -> club_id
# Necesario porque 6 de las 8 variables de contexto viven a nivel
# (club_id, season) -- propiedades del entorno, no del jugador -- mientras
# que el panel de rendimiento es (player_id, season) sin club_id retenido
# (se calculo internamente en pct_minutos_disponibles pero se descarto en el
# return final). Sin este puente no hay forma de pegar contexto de club
# contra el panel de jugador.
# ---------------------------------------------------------------------------

def construir_crosswalk_jugador_club_temporada(appearances, games, anio_min=ANIO_MIN_COBERTURA_GAMES):
    """
    Club "principal" de cada jugador en cada temporada: el que le dio mas
    minutos jugados (mismo criterio que ya se aplico en
    construir_pct_minutos_disponibles para resolver el caso de multiples
    clubes en la misma temporada). Un jugador transferido a mitad de
    temporada queda asignado al club donde jugo mas, no a ambos.
    """
    ap = appearances.merge(
        games[["game_id", "season", "competition_type"]], on="game_id"
    )
    ap = ap[(ap["season"] >= anio_min) & (ap["competition_type"] == "domestic_league")]

    minutos_por_club = ap.groupby(["player_id", "player_club_id", "season"]).agg(
        minutos_jugador=("minutes_played", "sum")
    ).reset_index()

    n_clubes = minutos_por_club.groupby(["player_id", "season"])["player_club_id"].transform("nunique")
    minutos_por_club["tuvo_multiples_clubes_temporada"] = n_clubes > 1

    crosswalk = minutos_por_club.sort_values("minutos_jugador", ascending=False).drop_duplicates(
        subset=["player_id", "season"], keep="first"
    ).sort_values(["player_id", "season"]).reset_index(drop=True)

    return crosswalk.rename(columns={"player_club_id": "club_id"})[
        ["player_id", "season", "club_id", "tuvo_multiples_clubes_temporada"]
    ]


if __name__ == "__main__":
    # Import local (no a nivel de modulo): este archivo, usado como libreria,
    # no necesita construir_variables_contexto para nada -- solo el bloque de
    # diagnostico de aca abajo, para poder correr este script suelto y
    # validarlo igual que construir_variables_contexto.py.
    from d02_construir_variables_contexto import cargar_tablas

    tablas = cargar_tablas()

    rendimiento_basico = construir_rendimiento_basico(tablas["appearances"], tablas["games"])
    print("rendimiento_basico:", rendimiento_basico.shape)
    print("minutos_confiables (media):", rendimiento_basico["minutos_confiables"].mean())
    print(rendimiento_basico["goles_90"].describe())

    pct_minutos = construir_pct_minutos_disponibles(
        tablas["appearances"], tablas["club_games"], tablas["games"]
    )
    print("\npct_minutos_disponibles:", pct_minutos.shape)
    # Validacion documentada: ~6.2% de jugador-temporadas con multiples clubes
    print("tuvo_multiples_clubes_temporada (media):", pct_minutos["tuvo_multiples_clubes_temporada"].mean())

    goles_recibidos = construir_goles_recibidos_titular(
        tablas["game_lineups"], tablas["club_games"], tablas["games"]
    )
    print("\ngoles_recibidos_titular:", goles_recibidos.shape)
    print("partidos_confiables (media):", goles_recibidos["partidos_confiables"].mean())
    print(goles_recibidos["goles_recibidos_90"].describe())

    goles_ajustados = construir_goles_recibidos_ajustado_rival(
        tablas["game_lineups"], tablas["club_games"], tablas["games"]
    )
    print("\ngoles_recibidos_ajustado_rival:", goles_ajustados.shape)
    print("partidos_confiables (media):", goles_ajustados["partidos_confiables"].mean())

    comparacion = goles_recibidos.merge(
        goles_ajustados[["player_id", "season", "goles_recibidos_ajustados_90"]],
        on=["player_id", "season"]
    )
    comparacion_confiable = comparacion[comparacion["partidos_confiables"]]
    correlacion = comparacion_confiable["goles_recibidos_90"].corr(
        comparacion_confiable["goles_recibidos_ajustados_90"]
    )
    print("Correlacion goles_recibidos_90 vs ajustados_90 (partidos_confiables):", correlacion)

    diferencial = construir_diferencial_con_sin_jugador(
        tablas["game_lineups"], tablas["club_games"], tablas["games"]
    )
    print("\ndiferencial_con_sin_jugador:", diferencial.shape)
    print(diferencial["diferencial_con_sin"].describe())

    participacion = construir_participacion_produccion_ofensiva(
        tablas["appearances"], tablas["club_games"], tablas["games"]
    )
    print("\nparticipacion_produccion_ofensiva:", participacion.shape)
    print("tuvo_multiples_clubes_temporada_participacion (media):",
          participacion["tuvo_multiples_clubes_temporada"].mean())
    print(participacion["participacion_produccion"].describe())

    edad_debut = construir_edad_debut(tablas["appearances"], tablas["players"])
    print("\nedad_debut:", edad_debut.shape)
    # Validacion documentada: mediana ~25.4 en grupo no confiable vs ~21.6 en confiable
    print(edad_debut.groupby("debut_confiable")["edad_debut"].median())

    panel = construir_panel_rendimiento(
        tablas["appearances"], tablas["players"], tablas["games"],
        tablas["club_games"], tablas["game_lineups"]
    )
    print("\npanel_rendimiento:", panel.shape)

    crosswalk = construir_crosswalk_jugador_club_temporada(tablas["appearances"], tablas["games"])
    print("\ncrosswalk_jugador_club_temporada:", crosswalk.shape)
    print("tuvo_multiples_clubes_temporada (media):", crosswalk["tuvo_multiples_clubes_temporada"].mean())