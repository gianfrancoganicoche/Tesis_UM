"""
Construccion de variables de rendimiento individual para el panel de la tesis.

Complementa src/construir_variables_contexto.py -- separado deliberadamente porque
son conceptualmente distintas (rendimiento individual del jugador vs. entorno en el
que juega). Fuente: davidcariboo/player-scores (Kaggle).

Estado de validacion (sesion de correccion/validacion completa, previo a tutoria
del 22/07 -- todas las funciones corridas y validadas contra datos reales):

- Variable A (rendimiento_basico): VALIDADA. Flag minutos_confiables agregado
  (piso empirico de 90 minutos -- el std de goles_90 cae 73% entre 0 y 90
  minutos, despues decae suave sin codo marcado).

- Variable B (pct_minutos_disponibles): VALIDADA. Fix de duplicados por
  multiples clubes en la misma temporada (se toma el club de mas minutos, se
  agrega flag tuvo_multiples_clubes_temporada para no perder esa senal -- 6.2%
  de jugador-temporadas tienen multiples clubes).

- Variable B-goles / C (goles_recibidos_titular / goles_recibidos_ajustado_rival):
  VALIDADAS. Flag partidos_confiables agregado (piso empirico de 5 partidos
  titular -- casos de 1 solo partido titular generaban ratios absurdos, ej.
  goleada 0-10 = 10 goles/90). Ajuste por fuerza del rival corregido a
  leave-one-out. Correlacion simple vs. ajustada = 0.896 (validado, en rango
  esperado 0.7-0.9).

- Variable D (diferencial_con_sin_jugador): VALIDADA Y VECTORIZADA. La version
  original con loop (por club-temporada x jugador) tardaba ~9 min por
  temporada (~2+ horas para el dataset completo) -- inviable para iterar.
  ADEMAS se encontro un bug real en la logica original: al construir los
  partidos "con" de un jugador, filtraba por game_id sin filtrar tambien por
  club_id -- esto inflaba el conteo cuando un jugador jugo para dos clubes que
  se enfrentaron entre si en la misma temporada (caso real encontrado: jugador
  369267, temporada 2020, contado con 5 partidos "con" para el club 28643
  cuando el valor correcto era 4 -- uno de los partidos fue jugado para el
  club 475, rival de 28643 ese dia). La version vectorizada corrige esto por
  construccion (requiere club_id explicito en cada join) y corre en 2.4
  segundos sobre el dataset completo (vs. ~2+ horas proyectadas de la version
  original). Validada contra un caso sintetico controlado (match exacto) y
  contra el caso real encontrado.

- Variable E (participacion_produccion_ofensiva): VALIDADA. Fix del groupby
  fragil aplicado (doble groupby + suma por .values, que asumia mismo orden
  de grupos entre dos llamadas separadas, reemplazado por un unico groupby con
  dos agregaciones). NOTA CONCEPTUAL: el numerador suma goles+asistencias del
  jugador pero el denominador es solo goles totales del equipo -- un gol con
  asistencia cuenta doble entre goleador y asistidor, asi que la suma de
  participacion_produccion de todos los jugadores de un equipo-temporada puede
  superar 1.0. No es un bug, pero documentar si se agrega a nivel equipo.

- Variable F (edad_debut): VALIDADA. Flag debut_confiable agregado y
  confirmado empiricamente (mediana edad_debut 25.4 en grupo no confiable vs
  21.6 en confiable). LIMITACION ADICIONAL no cubierta por el flag: incluso en
  el grupo confiable la mediana sigue alta respecto a lo esperado (17-19) --
  sospecha de un segundo mecanismo de sesgo por falta de cobertura de segundas
  divisiones (jugadores que debutan en una segunda division no cubierta por el
  dataset y solo aparecen en appearances.csv al llegar a un club de primera).
  Documentar como limitacion aparte, no resuelta por debut_confiable.
"""

import numpy as np
import pandas as pd

ANIO_MIN_COBERTURA = 2010
ANIO_MIN_COBERTURA_GAMES = 2012

MINUTOS_MIN_CONFIABLE = 90  # 1 partido completo -- justificado empiricamente:
# el std de goles_90 cae 73% entre 0 y 90 minutos (0.67 -> 0.18), y de ahi en
# adelante la caida es suave sin un codo claro (ver bitacora, validacion Variable A)

PARTIDOS_MIN_CONFIABLE = 5  # partidos titular -- justificado empiricamente:
# el std de goles_recibidos_90 cae 31% entre 1 y 5 partidos (0.67 -> 0.46),
# despues decae gradualmente sin codo marcado (ver bitacora, validacion Variable B)


# ---------------------------------------------------------------------------
# Variable A - Rendimiento basico por jugador-temporada
# Estado: VALIDADA.
# ---------------------------------------------------------------------------

def construir_rendimiento_basico(appearances, games, anio_min=ANIO_MIN_COBERTURA_GAMES):
    """
    Goles/90, asistencias/90, contribucion de gol/90, tarjetas/90 y minutos
    totales, por jugador-temporada. Base de la definicion de rendimiento
    (seccion 3.2 de hipotesis_y_diseno_v2.md).

    IMPORTANTE: estandarizar (z-score) estas variables por posicion-temporada
    antes de usarlas en la descomposicion -- goles_90 no es comparable entre
    posiciones sin esa correccion (ver seccion 3.2).

    NOTA: si minutos_totales == 0 para algun jugador-temporada, las metricas
    por 90 quedan en NaN en vez de inf -- inf rompe silenciosamente downstream
    (promedios, modelos) sin lanzar error.

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
# Estado: VALIDADA.
# ---------------------------------------------------------------------------

def construir_goles_recibidos_titular(game_lineups, club_games, games, anio_min=ANIO_MIN_COBERTURA_GAMES):
    """
    Goles recibidos como titular, por jugador-temporada.

    FLAG DE CONFIABILIDAD: partidos_confiables marca jugador-temporadas con
    menos de PARTIDOS_MIN_CONFIABLE partidos como titular -- por debajo de ese
    piso, goles_recibidos_90 puede estar dominado por un unico resultado
    extremo (ej. una goleada 0-10 en un solo partido titular).
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
# Estado: VALIDADA.
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

    VALIDACION: correlacion con la version sin ajustar (goles_recibidos_90) =
    0.896 sobre casos con partidos_confiables -- en rango esperado (0.7-0.9),
    confirma que el ajuste aporta informacion real sin ser redundante.
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
# Estado: VALIDADA Y VECTORIZADA.
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

    VECTORIZADA (reemplaza la version original con loop -- ver nota completa
    en el docstring del modulo): el loop original ademas tenia un bug real,
    no filtraba por club_id al construir los partidos "con" de un jugador, lo
    que inflaba el conteo cuando el jugador jugo para dos clubes que se
    enfrentaron entre si en la misma temporada. Esta version lo corrige por
    construccion (requiere club_id explicito en cada join) ademas de correr
    en segundos en vez de horas.
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

    # Marcar si el jugador fue titular en ESE partido especifico Y para ESE club
    # (el join incluye club_id explicito -- esto es lo que corrige el bug de
    # atribucion de club que tenia la version original)
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
# Estado: VALIDADA.
# ---------------------------------------------------------------------------

def construir_participacion_produccion_ofensiva(appearances, club_games, games,
                                                  anio_min=ANIO_MIN_COBERTURA_GAMES):
    """
    (goles + asistencias del jugador) / goles totales del equipo esa
    temporada. Normaliza produccion individual por el contexto ofensivo del
    propio equipo -- complementa a goles_90, no lo reemplaza.

    NOTA: reemplaza el patron anterior de doble groupby + suma por .values
    (fragil, asumia mismo orden de grupos entre dos llamadas separadas) por
    un unico groupby con dos agregaciones -- garantiza alineacion correcta
    por construccion, no por supuesto de orden.

    MULTIPLES CLUBES POR TEMPORADA: mismo bug que se encontro originalmente
    en construir_pct_minutos_disponibles -- el groupby interno es por
    (player_id, player_club_id, season), pero devolver solo (player_id,
    season) sin resolver el duplicado genera filas repetidas para jugadores
    con multiples clubes en la misma temporada (detectado en la corrida del
    panel final: 5685 duplicados, mismo conteo exacto que el bug original de
    Variable B). Se resuelve igual: quedarse con el club de mayor
    produccion (goles_asist_jugador), agregando el mismo flag
    tuvo_multiples_clubes_temporada.

    NOTA CONCEPTUAL (no es bug): el numerador suma goles+asistencias del
    jugador pero el denominador es solo goles totales del equipo -- un gol
    con asistencia cuenta doble entre goleador y asistidor, asi que la suma de
    participacion_produccion de todos los jugadores de un equipo-temporada
    puede superar 1.0. Documentar si se agrega a nivel equipo mas adelante.
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
# Estado: VALIDADA.
# ---------------------------------------------------------------------------

def construir_edad_debut(appearances, players, anio_min=ANIO_MIN_COBERTURA_GAMES):
    """
    Edad en la primera aparicion registrada en appearances.csv. Proxy de
    precocidad -- conecta con la curva de edad como "velocidad de arranque"
    de la carrera.

    FLAG DE CONFIABILIDAD: appearances.csv depende de games.csv, que solo es
    confiable desde anio_min (2012). Un jugador con carrera anterior a 2012
    puede tener su debut real "perdido". debut_confiable = False marca los
    casos donde la fecha de debut calculada cae en o antes del piso de
    cobertura. No se descartan estos casos aca; la decision de excluirlos
    queda para la etapa de modelado.

    LIMITACION ADICIONAL (no cubierta por el flag, confirmada empiricamente):
    mediana edad_debut = 25.4 en grupo no confiable vs 21.6 en confiable.
    Incluso en el grupo confiable, 21.6 sigue alto respecto a lo esperado
    (17-19) -- sospecha de un segundo mecanismo de sesgo por falta de
    cobertura de segundas divisiones, no resuelto por este flag.
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
    # participacion tambien tiene su propio flag de multiples clubes (mismo
    # patron que pct_minutos) -- renombrar para no chocar con el de pct_minutos
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
