"""
Construccion de variables de rendimiento individual para el panel de la tesis.

Complementa src/construir_variables_contexto.py -- separado deliberadamente porque
son conceptualmente distintas (rendimiento individual del jugador vs. entorno en el
que juega). Fuente: davidcariboo/player-scores (Kaggle).

Ninguna funcion de este script fue corrida ni validada contra datos reales todavia --
a diferencia de construir_variables_contexto.py, esto es el plan de la sesion,
pendiente de reconocimiento y validacion antes de confiar en los resultados. Aplicar
el mismo patron de: reconocimiento -> construccion -> validacion con casos conocidos
-> piso de confiabilidad donde corresponda, ya usado para las variables de contexto.
"""

import pandas as pd

ANIO_MIN_COBERTURA = 2010
ANIO_MIN_COBERTURA_GAMES = 2012


# ---------------------------------------------------------------------------
# Variable A - Rendimiento basico por jugador-temporada
# Estado: PENDIENTE DE VALIDAR. Cobertura de goals/assists/minutes_played en
# appearances.csv confirmada sin NaN en sesion.
# ---------------------------------------------------------------------------

def construir_rendimiento_basico(appearances, games, anio_min=ANIO_MIN_COBERTURA_GAMES):
    """
    Goles/90, asistencias/90, contribucion de gol/90, tarjetas/90 y minutos
    totales, por jugador-temporada. Base de la definicion de rendimiento
    (seccion 3.2 de hipotesis_y_diseno_v2.md).

    IMPORTANTE: estandarizar (z-score) estas variables por posicion-temporada
    antes de usarlas en la descomposicion -- goles_90 no es comparable entre
    posiciones sin esa correccion (ver seccion 3.2).
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
    agregado["goles_90"] = agregado["goles_totales"] / (agregado["minutos_totales"] / 90)
    agregado["asistencias_90"] = agregado["asistencias_totales"] / (agregado["minutos_totales"] / 90)
    agregado["contribucion_gol_90"] = agregado["goles_90"] + agregado["asistencias_90"]
    agregado["tarjetas_90"] = (
        (agregado["tarjetas_amarillas"] + agregado["tarjetas_rojas"]) / (agregado["minutos_totales"] / 90)
    )

    return agregado


def construir_pct_minutos_disponibles(appearances, club_games, games, anio_min=ANIO_MIN_COBERTURA_GAMES):
    """
    Minutos jugados por el jugador / minutos totales posibles del equipo esa
    temporada (partidos jugados por el club x 90). Proxy de confianza del
    cuerpo tecnico -- reutiliza la misma logica que construir_objetivos_deportivos
    en construir_variables_contexto.py para partidos jugados por club.
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
    resultado["pct_minutos_disponibles"] = resultado["minutos_jugador"] / resultado["minutos_posibles"]

    return resultado[["player_id", "season", "pct_minutos_disponibles"]]


# ---------------------------------------------------------------------------
# Variable B - Goles recibidos como titular (proxy defensivo, especialmente
# arqueros)
# Estado: PENDIENTE DE VALIDAR. Ver discusion de sesion: mezcla calidad
# individual con calidad de equipo -- el termino de contexto (calidad de
# plantel, companieros) esta pensado para absorber esa mezcla.
# ---------------------------------------------------------------------------

def construir_goles_recibidos_titular(game_lineups, club_games, games, anio_min=ANIO_MIN_COBERTURA_GAMES):
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

    return agregado


# ---------------------------------------------------------------------------
# Variable C - Goles recibidos ajustado por fuerza ofensiva del rival
# Estado: PENDIENTE DE VALIDAR. Adelanta parte del punto 4 de Alan (fortaleza
# de rivales) sin esperar a la sesion dedicada a ligas concentradas.
# ---------------------------------------------------------------------------

def construir_goles_recibidos_ajustado_rival(game_lineups, club_games, games,
                                              anio_min=ANIO_MIN_COBERTURA_GAMES):
    """
    Goles recibidos como titular, ponderados por la fuerza ofensiva del rival
    en cada partido (goles promedio marcados por ESE rival esa temporada,
    calculado sobre el resto de sus partidos). Un gol recibido contra un
    ataque fuerte pesa menos que uno recibido contra un ataque debil.
    """
    partidos = club_games.merge(
        games[["game_id", "season", "competition_type"]], on="game_id"
    )
    partidos = partidos[
        (partidos["season"] >= anio_min) & (partidos["competition_type"] == "domestic_league")
    ]

    # Fuerza ofensiva de cada club por temporada: promedio de goles propios marcados
    fuerza_ofensiva = partidos.groupby(["club_id", "season"]).agg(
        goles_marcados_promedio=("own_goals", "mean")
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
        fuerza_ofensiva.rename(columns={"club_id": "opponent_id", "goles_marcados_promedio": "fuerza_rival"}),
        on=["opponent_id", "season"], how="left"
    )

    # Ponderacion: gol recibido / fuerza ofensiva promedio del rival (evita
    # dividir por cero con un piso minimo)
    resultado["fuerza_rival"] = resultado["fuerza_rival"].clip(lower=0.3)
    resultado["goles_recibidos_ajustados"] = resultado["opponent_goals"] / resultado["fuerza_rival"]

    agregado = resultado.groupby(["player_id", "season"]).agg(
        goles_recibidos_ajustados_total=("goles_recibidos_ajustados", "sum"),
        partidos_titular=("game_id", "count"),
    ).reset_index()
    agregado["goles_recibidos_ajustados_90"] = (
        agregado["goles_recibidos_ajustados_total"] / agregado["partidos_titular"]
    )

    return agregado


# ---------------------------------------------------------------------------
# Variable D - Diferencial de resultado con/sin el jugador (plus-minus)
# Estado: PENDIENTE DE VALIDAR. Mas fiel al paper Plus-Minus Soccer
# (Kharrat/McHale/Pena) que el proxy de goles recibidos -- sirve para las
# cuatro posiciones, no solo defensivas.
# ---------------------------------------------------------------------------

def construir_diferencial_con_sin_jugador(game_lineups, club_games, games,
                                           anio_min=ANIO_MIN_COBERTURA_GAMES,
                                           min_partidos_grupo=5):
    """
    % de victorias del equipo en partidos donde el jugador fue titular vs.
    partidos donde no participo, misma temporada. Piso de min_partidos_grupo
    en AMBOS grupos (con/sin) antes de confiar en el diferencial -- mismo
    principio de piso de confiabilidad aplicado en toda la sesion (aplicar
    sobre las observaciones que efectivamente entran al calculo).

    Nota de rendimiento: esta funcion itera por club-temporada y por jugador
    dentro de cada club -- con el volumen completo del dataset puede ser
    lenta. Si tarda demasiado, reescribir vectorizado antes de descartarla.
    """
    partidos_club = club_games.merge(
        games[["game_id", "season", "competition_type"]], on="game_id"
    )
    partidos_club = partidos_club[
        (partidos_club["season"] >= anio_min) & (partidos_club["competition_type"] == "domestic_league")
    ]

    titular = game_lineups[game_lineups["type"] == "starting_lineup"][["game_id", "player_id", "club_id"]]

    resultado = []
    for (club_id, season), partidos in partidos_club.groupby(["club_id", "season"]):
        jugadores_club = titular[titular["club_id"] == club_id]["player_id"].unique()
        for player_id in jugadores_club:
            juegos_titular = titular[
                (titular["player_id"] == player_id) & (titular["game_id"].isin(partidos["game_id"]))
            ]["game_id"]
            con = partidos[partidos["game_id"].isin(juegos_titular)]
            sin = partidos[~partidos["game_id"].isin(juegos_titular)]
            if len(con) >= min_partidos_grupo and len(sin) >= min_partidos_grupo:
                resultado.append({
                    "player_id": player_id, "club_id": club_id, "season": season,
                    "pct_victorias_con": (con["is_win"] == 1).mean(),
                    "pct_victorias_sin": (sin["is_win"] == 1).mean(),
                    "diferencial_con_sin": (con["is_win"] == 1).mean() - (sin["is_win"] == 1).mean(),
                    "partidos_con": len(con), "partidos_sin": len(sin),
                })
    return pd.DataFrame(resultado)


# ---------------------------------------------------------------------------
# Variable E - Participacion relativa en la produccion ofensiva del equipo
# Estado: PENDIENTE DE VALIDAR.
# ---------------------------------------------------------------------------

def construir_participacion_produccion_ofensiva(appearances, club_games, games,
                                                  anio_min=ANIO_MIN_COBERTURA_GAMES):
    """
    (goles + asistencias del jugador) / goles totales del equipo esa
    temporada. Normaliza produccion individual por el contexto ofensivo del
    propio equipo -- complementa a goles_90, no lo reemplaza.
    """
    ap = appearances.merge(
        games[["game_id", "season", "competition_type"]], on="game_id"
    )
    ap = ap[(ap["season"] >= anio_min) & (ap["competition_type"] == "domestic_league")]

    produccion_jugador = ap.groupby(["player_id", "player_club_id", "season"]).agg(
        goles_asist_jugador=("goals", "sum")
    ).reset_index()
    produccion_jugador["goles_asist_jugador"] += ap.groupby(
        ["player_id", "player_club_id", "season"]
    )["assists"].sum().values

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

    return resultado[["player_id", "season", "participacion_produccion"]]


# ---------------------------------------------------------------------------
# Variable F - Edad de debut profesional
# Estado: PENDIENTE DE VALIDAR. La mas simple de las seis.
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

    return resultado[["player_id", "edad_debut"]]
