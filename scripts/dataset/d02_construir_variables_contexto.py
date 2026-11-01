"""
Construccion de variables de contexto para el panel de la tesis.

Fuente: davidcariboo/player-scores (Kaggle).

"""

import re
import sys
from pathlib import Path

import pandas as pd

_RAIZ_SCRIPTS = Path(__file__).resolve().parents[1]  # scripts/, tras la reorganizacion en subcarpetas (22/09)
for _carpeta in ("config", "dataset", "eda", "diagnosticos"):
    sys.path.insert(0, str(_RAIZ_SCRIPTS / _carpeta))

from config import ANIO_MIN_COBERTURA, ANIO_MIN_COBERTURA_GAMES, RUTA_DATOS_CONGELADOS

# season en games.csv tiene solo 31-64 partidos/anio en 2005-2011 
# (ruido de carga historica dispersa), y recien se vuelve densa y 
# consecutiva desde 2012 (~5.700-6.000 partidos/anio).
# Usar ANIO_MIN_COBERTURA (2010) para esta tabla habria incluido temporadas
# con cobertura casi vacia sin que ningun chequeo lo hiciera evidente.


def derivar_season_desde_fecha(date_series, mes_corte=7):
    """
    Deriva el anio de inicio de temporada desde una fecha, replicando la
    convencion de 'season' en games.csv. Confirmado empiricamente en sesion:
    season=2015 en games.csv cubre fechas entre 2015-06-30 y 2016-07-10 --
    o sea, season = anio en que arranca la temporada (jun/jul), no el anio
    calendario de cada fecha individual. Sin esto, una valuacion de enero
    2016 se agregaria bajo season=2016 en un lado y season=2015 en el otro
    al cruzar con datos de games.csv, desalineando el panel en silencio.
    """
    return date_series.dt.year - (date_series.dt.month < mes_corte).astype(int)


def cargar_tablas(ruta=RUTA_DATOS_CONGELADOS):
    """
    Carga todas las tablas de player-scores desde el snapshot local
    congelado en `ruta` (por defecto RUTA_DATOS_CONGELADOS).

    Para actualizar deliberadamente a una version mas nueva del dataset:
    correr scripts/01_guardar_copia_local_datos.py (unico script que debe
    seguir usando kagglehub.dataset_download() -- ese es justamente su rol)
    para generar un nuevo data/raw/<fecha>_vNNN/, re-validar todo lo que
    dependa de datos crudos, y recien despues actualizar RUTA_DATOS_CONGELADOS
    en config.py.
    """
    tablas = {
        "players": pd.read_csv(f"{ruta}/players.csv"),
        "clubs": pd.read_csv(f"{ruta}/clubs.csv"),
        "competitions": pd.read_csv(f"{ruta}/competitions.csv"),
        "games": pd.read_csv(f"{ruta}/games.csv"),
        "club_games": pd.read_csv(f"{ruta}/club_games.csv"),
        "game_lineups": pd.read_csv(f"{ruta}/game_lineups.csv", dtype={"number": "object"}),
        "appearances": pd.read_csv(f"{ruta}/appearances.csv"),
        "transfers": pd.read_csv(f"{ruta}/transfers.csv"),
        "player_valuations": pd.read_csv(f"{ruta}/player_valuations.csv"),
    }
    return tablas


# ---------------------------------------------------------------------------
# Variable 1 - Objetivos deportivos (posicion en tabla, resultado, puntos)
# ---------------------------------------------------------------------------

def construir_objetivos_deportivos(games, club_games, tipo_liga_domestica="domestic_league",
                                    anio_min=ANIO_MIN_COBERTURA_GAMES):
    """
    Agrega objetivos deportivos por club-temporada: posicion final en tabla,
    % de victorias, diferencia de gol promedio -- solo sobre partidos de liga
    domestica (own_position solo esta poblado ahi: 99.88% de cobertura en
    domestic_league vs. ~0% en domestic_cup/international_cup/national_team_competition,
    verificado en sesion). Filtra por ANIO_MIN_COBERTURA_GAMES (2012)
    """
    partidos = club_games.merge(
        games[["game_id", "season", "competition_type", "date"]],
        on="game_id"
    )
    partidos = partidos[partidos["season"] >= anio_min]
    partidos_liga = partidos[partidos["competition_type"] == tipo_liga_domestica].copy()

    es_victoria = partidos_liga["is_win"] == 1
    es_empate = partidos_liga["own_goals"] == partidos_liga["opponent_goals"]

    partidos_liga["puntos"] = 0
    partidos_liga.loc[es_victoria, "puntos"] = 3
    partidos_liga.loc[es_empate, "puntos"] = 1
    partidos_liga["diferencia_gol"] = partidos_liga["own_goals"] - partidos_liga["opponent_goals"]

    partidos_liga = partidos_liga.sort_values("date")

    agregado = partidos_liga.groupby(["club_id", "season"]).agg(
        posicion_final=("own_position", "last"),
        posicion_promedio=("own_position", "mean"),
        pct_victorias=("is_win", lambda x: (x == 1).mean()),
        diferencia_gol_promedio=("diferencia_gol", "mean"),
        puntos_totales=("puntos", "sum"),
        partidos_jugados=("game_id", "count"),
    ).reset_index()

    agregado["puntos_por_partido"] = agregado["puntos_totales"] / agregado["partidos_jugados"]

    return agregado


# ---------------------------------------------------------------------------
# Reconstruccion de club historico por fecha de valuacion
# Estado: CONSTRUIDA Y VALIDADA, CON LIMITACION DOCUMENTADA.
#
# Problema de origen: ni clubs.csv  ni el campo current_club_id de 
# player_valuations.csv sirven para saber en que club estaba un 
# jugador en el momento de una valuacion HISTORICA.
#
# Solucion: combinar dos fuentes, en orden de prioridad:
#   1) transfers.csv -- preciso cuando existe (fecha real de transferencia),
#      pero con huecos sistematicos: 87.8% de los jugadores valuados no
#      tienen NINGUN registro en transfers.csv, y de los que si tienen
#      partidos jugados en appearances.csv, el 54.4% jugo en MULTIPLES
#      clubes sin que quedara registrado en transfers.csv (caso Haaland:
#      0 filas en transfers.csv pese a 4 clubes reales conocidos). No es
#      un problema marginal, es estructural de la fuente.
#   2) appearances.csv como respaldo (club del partido mas cercano en fecha,
#      tolerancia 365 dias) para lo que transfers.csv no cubre.
#
# Resultado final combinado: 44.4% de NaN global. Por tramo de edad:
#   0-16 anios: 9.0%
#   16-18:      36.0%
#   18-20:      47.8%
#   20-23:      53.5%
#   23+:        58.3%
#
# ---------------------------------------------------------------------------

def reconstruir_club_historico_appearances(player_valuations, appearances):
    """Respaldo: club del partido mas cercano en fecha (tolerancia 365 dias)."""
    pv = player_valuations.copy()
    pv["date"] = pd.to_datetime(pv["date"])
    pv = pv.sort_values("date").reset_index(drop=True)

    ap = appearances[["player_id", "date", "player_club_id"]].copy()
    ap["date"] = pd.to_datetime(ap["date"])
    ap = ap.dropna(subset=["player_club_id"]).sort_values("date").reset_index(drop=True)

    resultado = pd.merge_asof(
        pv, ap, on="date", by="player_id",
        direction="nearest", tolerance=pd.Timedelta("365days"),
    )
    return resultado.rename(columns={"player_club_id": "club_id_historico"})


def reconstruir_club_historico_transfers(player_valuations, transfers):
    """Prioridad 1: club vigente segun la ultima transferencia anterior a la fecha."""
    tr = transfers.copy()
    tr["transfer_date"] = pd.to_datetime(tr["transfer_date"])
    tr["player_id"] = tr["player_id"].astype("int64")
    tr = tr.sort_values(["player_id", "transfer_date"])
    tr = tr.rename(columns={"to_club_id": "club_id_desde_transferencia"})

    pv = player_valuations.copy()
    pv["date"] = pd.to_datetime(pv["date"])
    pv["player_id"] = pv["player_id"].astype("int64")
    pv = pv.sort_values("date").reset_index(drop=True)

    tr_merge = tr[["player_id", "transfer_date", "club_id_desde_transferencia"]].sort_values("transfer_date")

    resultado = pd.merge_asof(
        pv, tr_merge, left_on="date", right_on="transfer_date",
        by="player_id", direction="backward",
    )
    return resultado


def reconstruir_club_historico(player_valuations, transfers, appearances):
    """
    Combina transfers.csv (prioridad) + appearances.csv (respaldo) para
    reconstruir el club de cada jugador en el momento de cada valuacion.
    Ver nota de limitacion arriba antes de usar esto para filtrar o excluir
    observaciones -- el NaN resultante esta correlacionado con edad joven,
    no es aleatorio.
    """
    via_transfers = reconstruir_club_historico_transfers(player_valuations, transfers)
    via_transfers = via_transfers.rename(columns={"club_id_desde_transferencia": "club_id_final"})

    via_appearances = reconstruir_club_historico_appearances(player_valuations, appearances)

    combinado = via_transfers.copy()
    faltantes = combinado["club_id_final"].isna()
    combinado.loc[faltantes, "club_id_final"] = via_appearances.loc[faltantes, "club_id_historico"].values

    return combinado


def diagnostico_haaland(club_historico_reconstruido):
    """Verificacion de sanidad rapida sobre cualquier reconstruccion de club."""
    cols = [c for c in club_historico_reconstruido.columns if "club_id" in c or c in ("date", "market_value_in_eur")]
    return (
        club_historico_reconstruido[club_historico_reconstruido["player_id"] == 418560][cols]
        .sort_values("date")
    )


# ---------------------------------------------------------------------------
# Variable 2 - Calidad del plantel por temporada
# Hereda la limitacion de cobertura de reconstruir_club_historico -- las
# filas sin club reconstruible se excluyen del agregado (no se imputan).
# ---------------------------------------------------------------------------

def construir_calidad_plantel(player_valuations, transfers, appearances, anio_min=ANIO_MIN_COBERTURA):
    """
    Agrega calidad de plantel por club-anio: valor total, valor promedio,
    cantidad de jugadores valuados. Usa el club HISTORICO reconstruido
    (transfers.csv + appearances.csv combinados), no current_club_id.

    'season' se deriva con la misma convencion que games.csv (anio de
    inicio de temporada, ver derivar_season_desde_fecha), NO con el anio
    calendario crudo de la fecha -- de lo contrario una valuacion de enero
    queda mal alineada al cruzar esta tabla con objetivos_deportivos u otras
    variables derivadas de games.csv.
    """
    reconstruido = reconstruir_club_historico(player_valuations, transfers, appearances)
    reconstruido["anio"] = derivar_season_desde_fecha(reconstruido["date"])
    reconstruido = reconstruido[reconstruido["anio"] >= anio_min]
    reconstruido = reconstruido.dropna(subset=["club_id_final"])

    agregado = reconstruido.groupby(["club_id_final", "anio"]).agg(
        valor_total_plantel=("market_value_in_eur", "sum"),
        valor_promedio_plantel=("market_value_in_eur", "mean"),
        jugadores_valuados=("player_id", "nunique"),
    ).reset_index()

    agregado = agregado.rename(columns={"club_id_final": "club_id", "anio": "season"})
    return agregado


# ---------------------------------------------------------------------------
# Variable 3 - Participacion en competencias internacionales de club
# Fase_maxima_alcanzada sin ningun NaN (2080 en fase 1, decreciendo hasta 
# 83 en fase 6/Final -- distribucion esperada, el aparente "salto" entre 
# semis (66) y final (83) es semantica correcta de tomar el maximo por 
# club-temporada, no un error: un finalista tambien jugo semis pero queda 
# clasificado en fase 6, no 5, asi que fase 5 solo cuenta a los perdedores 
# de semifinal).
# ---------------------------------------------------------------------------

def clasificar_fase(round_texto):
    """
    Clasifica una fase de competencia europea en una escala ordinal gruesa.
    Deliberadamente NO distingue el orden fino entre fases de clasificacion
    (First/Second/3rd/4th round, Qualifying Round, intermediate stage) porque
    ese orden depende del formato especifico de cada competencia y temporada
    -- una precision que los datos no sostienen con confianza. Se agrupan
    todas como fase_ordinal=1 ('no llego a fase de grupos').
    """
    if pd.isna(round_texto):
        return None

    t = round_texto.lower().strip()
    t = re.sub(r"\s*(1st|2nd)\s*leg\s*$", "", t)

    if t == "final":
        return 6
    if "semi-final" in t or "semifinal" in t:
        return 5
    if "quarter-final" in t or "quarterfinal" in t:
        return 4
    if "round of 16" in t or "last 16" in t:
        return 3
    if "group" in t:
        return 2
    return 1


def construir_competencias_internacionales(games, club_games, anio_min=ANIO_MIN_COBERTURA_GAMES):
    """
    Participacion en competencias internacionales de club (Champions League,
    Europa League, Conference League + fases clasificatorias, Supercopa de
    Europa) por club-temporada.
    """
    ids_europeos = ["CL", "CLQ", "EL", "ELQ", "UCOL", "ECLQ", "USC"]

    partidos = club_games.merge(
        games[["game_id", "season", "competition_id", "round", "date"]],
        on="game_id"
    )
    partidos = partidos[partidos["season"] >= anio_min]
    intl = partidos[partidos["competition_id"].isin(ids_europeos)].copy()

    intl["fase_ordinal"] = intl["round"].apply(clasificar_fase)
    intl["llego_fase_grupos"] = intl["fase_ordinal"] >= 2

    agregado = intl.groupby(["club_id", "season"]).agg(
        partidos_europeos=("game_id", "count"),
        fase_maxima_alcanzada=("fase_ordinal", "max"),
        jugo_fase_grupos_o_mas=("llego_fase_grupos", "any"),
        competencias_distintas=("competition_id", "nunique"),
    ).reset_index()

    return agregado


# ---------------------------------------------------------------------------
# Variable 4 - Continuidad del cuerpo tecnico (entrenador)
# own_manager_name con cobertura casi completa (0.95% NaN) y nombres limpios, 
# sin variantes de escritura -- verificado con historial completo del Real Madrid
# (Mourinho/Ancelotti/Benitez/Zidane/Lopetegui/Solari/Xabi Alonso/Arbeloa,
# todos distintos y correctos) y con el caso extremo de 7 entrenadores en
# una temporada (Denizlispor 2020, temporada de descenso -- 7 nombres
# genuinamente distintos, incluye un interino que vuelve dos veces
# separado en el tiempo; confirmado como caso real, no ruido de texto).
# entrenadores_distintos: mayoria 1-2 (2159 + 948 de 3906), cola decreciente
# hasta 7. hubo_cambio_entrenador=True en 44.7% de las temporadas.
# ---------------------------------------------------------------------------

def construir_continuidad_tecnica(games, club_games, anio_min=ANIO_MIN_COBERTURA_GAMES):
    """
    Continuidad del cuerpo tecnico por club-temporada: cantidad de
    entrenadores distintos, si hubo cambio de entrenador dentro de la
    temporada, y quien fue el entrenador que dirigio mas partidos (el
    "titular" de la temporada, en caso de haber mas de uno).
    """
    partidos = club_games.merge(
        games[["game_id", "season", "competition_type", "date"]],
        on="game_id"
    )
    partidos = partidos[partidos["season"] >= anio_min]
    partidos = partidos[partidos["competition_type"] == "domestic_league"].copy()
    partidos = partidos.dropna(subset=["own_manager_name"])
    partidos = partidos.sort_values("date")

    agregado = partidos.groupby(["club_id", "season"]).agg(
        entrenadores_distintos=("own_manager_name", "nunique"),
        partidos_con_entrenador=("game_id", "count"),
    ).reset_index()

    agregado["hubo_cambio_entrenador"] = agregado["entrenadores_distintos"] > 1

    entrenador_titular = (
        partidos.groupby(["club_id", "season", "own_manager_name"])
        .size()
        .reset_index(name="partidos_dirigidos")
        .sort_values("partidos_dirigidos", ascending=False)
        .drop_duplicates(subset=["club_id", "season"])
        [["club_id", "season", "own_manager_name"]]
        .rename(columns={"own_manager_name": "entrenador_titular"})
    )

    agregado = agregado.merge(entrenador_titular, on=["club_id", "season"], how="left")

    return agregado


# ---------------------------------------------------------------------------
# Variable 5 - Sistema tactico (formacion)
# Cobertura ~91% (9% de partidos sin formacion registrada en ninguno de los
# dos equipos). formacion_base (regex sobre el patron numerico, ej. "4-3-3"
# extraido de "4-3-3 Attacking") valida: value_counts muestra exactamente
# las 16 estructuras esperables, sin fragmentos rotos.
#
# ADVERTENCIA DE CONFIABILIDAD: la formacion es una interpretacion editorial 
# de quien narra cada partido -- variabilidad tan alta es mas consistente 
# con una mezcla de variabilidad tactica real + ruido/inconsistencia de 
# anotacion entre fuentes, que con un club excepcionalmente cambiante. No hay 
# forma de separar ambos componentes con los datos disponibles.
#
# USO RECOMENDADO: tratar estructuras_base_distintas como la senal principal
# en si misma (alto = sistema inestable o mal documentado, cualquiera de
# las dos lecturas es contexto legitimo), y formacion_predominante /
# formacion_base_predominante como dato descriptivo secundario, no como
# variable de alta confianza.
# ---------------------------------------------------------------------------

def construir_sistema_tactico(games, club_games, anio_min=ANIO_MIN_COBERTURA_GAMES):
    """
    Formacion tactica predominante por club-temporada, en dos niveles de
    granularidad: formacion exacta (ej. "4-3-3 Attacking") y estructura
    base (ej. "4-3-3", agrupando variantes descriptivas del mismo esqueleto
    numerico). Usa hosting (Home/Away) para elegir entre home_club_formation
    y away_club_formation segun corresponda a cada club en cada partido.
    Ver advertencia de confiabilidad arriba antes de usar como feature de
    alta confianza.
    """
    partidos = club_games.merge(
        games[["game_id", "season", "competition_type", "date",
               "home_club_formation", "away_club_formation"]],
        on="game_id"
    )
    partidos = partidos[partidos["season"] >= anio_min]
    partidos = partidos[partidos["competition_type"] == "domestic_league"].copy()

    partidos["formacion"] = partidos["home_club_formation"].where(
        partidos["hosting"] == "Home", partidos["away_club_formation"]
    )
    partidos = partidos.dropna(subset=["formacion"])

    partidos["formacion_base"] = partidos["formacion"].str.extract(r"^([\d-]+)")

    agregado = partidos.groupby(["club_id", "season"]).agg(
        formacion_predominante=("formacion", lambda x: x.mode().iloc[0] if not x.mode().empty else None),
        formacion_base_predominante=("formacion_base", lambda x: x.mode().iloc[0] if not x.mode().empty else None),
        formaciones_distintas=("formacion", "nunique"),
        estructuras_base_distintas=("formacion_base", "nunique"),
        partidos_con_formacion=("game_id", "count"),
    ).reset_index()

    return agregado


# ---------------------------------------------------------------------------
# Variable 6 - Competencia interna por el puesto (profundidad de plantel)
# Patron por posicion coherente con la realidad futbolistica: arquero con
# mediana 2 jugadores distintos por temporada (tipico -- 2-3 arqueros con
# minutos reales), mediocampista con la mediana mas alta (11), seguido de
# defensor (10) y delantero (9) -- consistente con mayor rotacion en el
# mediocampo.
#
# DECISION DE DISENO: usa solo type == 'starting_lineup', no 'substitutes'.
# "Competencia por el puesto" mide quien efectivamente GANA el lugar en la
# cancha, no quien esta disponible en el banco sin jugar.
#
# NOTA METODOLOGICA (no ML): se evaluo usar un modelo entrenado para
# clasificar el texto de position en categorias amplias, mas alla del
# diccionario manual. Se descarto: el vocabulario de posiciones es cerrado
# y conocido (~15-20 etiquetas totales, todas vistas en el reconocimiento
# inicial), un mapeo determinista es mas preciso, transparente y auditable
# que un modelo para este problema especifico.
# ---------------------------------------------------------------------------

MAPA_POSICION_AMPLIA = {
    "centre-back": "defensor", "left-back": "defensor", "right-back": "defensor",
    "defender": "defensor", "sweeper": "defensor",
    "goalkeeper": "arquero",
    "central midfield": "mediocampista", "defensive midfield": "mediocampista",
    "attacking midfield": "mediocampista", "left midfield": "mediocampista",
    "right midfield": "mediocampista", "midfield": "mediocampista",
    "centre-forward": "delantero", "left winger": "delantero",
    "right winger": "delantero", "second striker": "delantero", "attack": "delantero",
}

def construir_competencia_interna_puesto(game_lineups, games, anio_min=ANIO_MIN_COBERTURA_GAMES):
    """
    Profundidad de plantel por posicion amplia: cuantos jugadores distintos
    ganaron un lugar en el once TITULAR (no suplentes) en cada posicion
    amplia, por club-temporada.
    """
    from difflib import get_close_matches

    lineups = game_lineups.merge(
        games[["game_id", "season", "competition_type"]], on="game_id"
    )
    lineups = lineups[
        (lineups["season"] >= anio_min) & (lineups["competition_type"] == "domestic_league")
    ].copy()
    lineups = lineups[lineups["type"] == "starting_lineup"].copy()

    lineups["posicion_amplia"] = lineups["position"].str.lower().str.strip().map(MAPA_POSICION_AMPLIA)

    sin_mapear = lineups[lineups["posicion_amplia"].isna()]["position"].dropna().unique()
    if len(sin_mapear) > 0:
        print("ADVERTENCIA -- posiciones sin mapear, sugerencia por similitud de texto:")
        for pos in sin_mapear:
            sugerencia = get_close_matches(pos.lower(), MAPA_POSICION_AMPLIA.keys(), n=1)
            print(f"  '{pos}' -> ¿'{sugerencia[0]}'?" if sugerencia else f"  '{pos}' -> sin sugerencia clara, revisar a mano")

    lineups = lineups.dropna(subset=["posicion_amplia"])

    agregado = lineups.groupby(["club_id", "season", "posicion_amplia"]).agg(
        jugadores_distintos=("player_id", "nunique"),
        titularidades_totales=("game_lineups_id", "count"),
    ).reset_index()

    return agregado


# ---------------------------------------------------------------------------
# Posicion amplia predominante por jugador-temporada
#
# Necesaria para dos usos distintos: (1) estandarizar (z-score) las
# variables de rendimiento por posicion-temporada, tal como exige la
# seccion 3.2 de hipotesis_y_diseno_v2.md ("ninguna de estas variables es
# comparable cruda entre posiciones"); (2) mergear competencia_interna_puesto
# (vive a nivel club-temporada-posicion) contra el panel de jugadores --
# tarea separada, todavia pendiente.
# ---------------------------------------------------------------------------

# NOTA (25/09, ver auditar_variables_clave.py y config.ANIO_MIN_COBERTURA_LINEUPS):
# aunque este filtro usa anio_min=ANIO_MIN_COBERTURA_GAMES (2012), en la practica
# ninguna fila de season=2012 sobrevive el merge de todas formas -- game_lineups.csv
# no tiene NINGUNA fila para partidos de liga domestica de esa temporada. El piso real
# y mas estricto para esta tabla puntual es 2013.
def construir_posicion_amplia_jugador_temporada(game_lineups, games, anio_min=ANIO_MIN_COBERTURA_GAMES):
    """
    Posicion amplia predominante de cada jugador en cada temporada: la
    posicion en la que jugo mas partidos ese año, entre las 4 categorias de
    MAPA_POSICION_AMPLIA (arquero/defensor/mediocampista/delantero).

    A diferencia de construir_competencia_interna_puesto (que solo mira
    titularidades, porque mide "quien gana el puesto"), aca se usan TODAS
    las apariciones de game_lineups (titular + suplente) -- lo que se busca
    es la posicion real del jugador, no si gano el lugar en el equipo. Un
    jugador que entra siempre desde el banco en la misma posicion sigue
    jugando ahi, y descartar esas filas subestimaria su volumen real de
    apariciones en esa posicion.

    DESEMPATE: si un jugador tuvo la misma cantidad de apariciones en dos o
    mas posiciones amplias en la misma temporada (poco frecuente pero
    posible con pocos partidos), se queda con la primera en orden
    alfabetico -- desempate arbitrario pero determinista (ordenamiento
    estable en dos pasos), no depende del orden de filas de entrada.

    Devuelve tambien apariciones_totales y posiciones_distintas -- utiles
    como flag de versatilidad/confiabilidad: un jugador con
    posiciones_distintas alto tiene una "posicion predominante" menos
    representativa de su rol real que uno que jugo siempre en la misma.
    """
    lineups = game_lineups.merge(
        games[["game_id", "season", "competition_type"]], on="game_id"
    )
    lineups = lineups[
        (lineups["season"] >= anio_min) & (lineups["competition_type"] == "domestic_league")
    ].copy()

    lineups["posicion_amplia"] = lineups["position"].str.lower().str.strip().map(MAPA_POSICION_AMPLIA)
    lineups = lineups.dropna(subset=["posicion_amplia"])

    conteo = lineups.groupby(["player_id", "season", "posicion_amplia"]).agg(
        apariciones=("game_lineups_id", "count")
    ).reset_index()

    conteo_total = conteo.groupby(["player_id", "season"]).agg(
        apariciones_totales=("apariciones", "sum"),
        posiciones_distintas=("posicion_amplia", "nunique"),
    ).reset_index()

    conteo = conteo.sort_values("posicion_amplia", kind="mergesort")
    predominante = conteo.sort_values("apariciones", ascending=False, kind="mergesort").drop_duplicates(
        subset=["player_id", "season"], keep="first"
    )
    predominante = predominante.rename(columns={
        "posicion_amplia": "posicion_amplia_predominante",
        "apariciones": "apariciones_en_posicion_predominante",
    })

    resultado = predominante.merge(conteo_total, on=["player_id", "season"])

    return resultado[[
        "player_id", "season", "posicion_amplia_predominante",
        "apariciones_en_posicion_predominante", "apariciones_totales", "posiciones_distintas"
    ]].sort_values(["player_id", "season"]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Variable 7 - Reputacion de club vendedor
#
# reputacion_vendedor final: solo 4.2% del panel club-temporada queda con
# valor no nulo (piso de 3 ventas CON score en la ventana de 5 anios).
# Top resultante tiene sentido futbolistico (Reading, Wigan, Fulham, Aston
# Villa -- perfil real de clubes ingleses de nivel medio conocidos por
# desarrollar y vender cantera), pero la cobertura es baja.
# ---------------------------------------------------------------------------

def construir_mapa_club_liga_por_temporada(games, club_games, anio_min=ANIO_MIN_COBERTURA_GAMES):
    """
    Liga domestica de cada club en cada temporada, derivada de partidos
    reales jugados (no de clubs.csv, que es snapshot). Reutilizable para
    cualquier variable que necesite "en que liga jugaba este club en el
    año X".
    """
    partidos = club_games.merge(
        games[["game_id", "season", "competition_type", "competition_id"]],
        on="game_id"
    )
    partidos = partidos[
        (partidos["season"] >= anio_min) & (partidos["competition_type"] == "domestic_league")
    ]
    mapa = partidos.groupby(["club_id", "season"])["competition_id"].agg(
        lambda x: x.mode().iloc[0] if not x.mode().empty else None
    ).reset_index()
    return mapa


def construir_score_prestigio_liga(transfers, players, mapa_club_liga, competitions,
                                    edad_max=23, min_transferencias=10):
    """
    Score de prestigio de liga: mediana del market_value_in_eur de
    transferencias entrantes de jugadores sub-23, por liga de destino.
    Ligas con menos de min_transferencias observaciones quedan con score
    NaN (no se inventa una estimacion sobre muestra insuficiente).

    """
    tr = transfers.copy()
    tr["transfer_date"] = pd.to_datetime(tr["transfer_date"])
    tr["season"] = derivar_season_desde_fecha(tr["transfer_date"])
    tr = tr.merge(players[["player_id", "date_of_birth"]], on="player_id", how="left")
    tr["date_of_birth"] = pd.to_datetime(tr["date_of_birth"])
    tr["edad"] = (tr["transfer_date"] - tr["date_of_birth"]).dt.days / 365.25
    tr = tr[tr["edad"] <= edad_max]
    tr = tr[tr["market_value_in_eur"] > 0]

    mapa_destino = mapa_club_liga.rename(columns={"club_id": "to_club_id", "competition_id": "liga_destino"})
    tr = tr.merge(mapa_destino, on=["to_club_id", "season"], how="left")

    score = (
        tr.dropna(subset=["liga_destino"])
        .groupby("liga_destino")["market_value_in_eur"]
        .agg(score_prestigio_liga="median", transferencias_consideradas="count")
        .reset_index()
    )
    score.loc[score["transferencias_consideradas"] < min_transferencias, "score_prestigio_liga"] = None

    # Desambiguar nombres duplicados (ej. "bundesliga" alemana vs austriaca)
    score = score.merge(
        competitions[["competition_id", "name", "country_name"]],
        left_on="liga_destino", right_on="competition_id", how="left"
    )
    return score


def construir_reputacion_club_vendedor(transfers, players, mapa_club_liga, score_prestigio_liga,
                                        anio_min=ANIO_MIN_COBERTURA, ventana_anios=5, edad_max=23,
                                        min_ventas_con_score=3):
    """
    Reputacion de club vendedor por club-temporada: score de prestigio
    promedio de las ligas de destino de las transferencias SALIENTES de
    jugadores sub-23 del club, en una ventana movil de los N años
    ESTRICTAMENTE anteriores a T. Piso de confiabilidad aplicado sobre
    ventas_con_score, no sobre el total de ventas.
    """
    tr = transfers.copy()
    tr["transfer_date"] = pd.to_datetime(tr["transfer_date"])
    tr["season"] = derivar_season_desde_fecha(tr["transfer_date"])
    tr = tr.merge(players[["player_id", "date_of_birth"]], on="player_id", how="left")
    tr["date_of_birth"] = pd.to_datetime(tr["date_of_birth"])
    tr["edad"] = (tr["transfer_date"] - tr["date_of_birth"]).dt.days / 365.25
    tr = tr[tr["edad"] <= edad_max]

    mapa_destino = mapa_club_liga.rename(columns={"club_id": "to_club_id", "competition_id": "liga_destino"})
    tr = tr.merge(mapa_destino, on=["to_club_id", "season"], how="left")

    scores = score_prestigio_liga[["liga_destino", "score_prestigio_liga"]].dropna()
    tr = tr.merge(scores, on="liga_destino", how="left")

    resultado = []
    temporadas = range(anio_min, tr["season"].max() + 1)
    for club_id, grupo in tr.groupby("from_club_id"):
        for season in temporadas:
            ventana = grupo[
                (grupo["season"] < season) & (grupo["season"] >= season - ventana_anios)
            ]
            total_ventas = len(ventana)
            if total_ventas == 0:
                continue

            con_score = ventana.dropna(subset=["score_prestigio_liga"])
            reputacion = (
                con_score["score_prestigio_liga"].mean()
                if len(con_score) >= min_ventas_con_score else None
            )

            resultado.append({
                "club_id": club_id,
                "season": season,
                "reputacion_vendedor": reputacion,
                "ventas_sub23_totales": total_ventas,
                "ventas_con_score": len(con_score),
                "cobertura_score": len(con_score) / total_ventas,
            })

    return pd.DataFrame(resultado)


def construir_flag_club_vendedor(transfers, players, mapa_club_liga, score_prestigio_liga,
                                  universo_club_temporada, anio_min=ANIO_MIN_COBERTURA,
                                  ventana_anios=5, edad_max=23, min_ventas_para_flag=1):
    """
    Flag de club vendedor reconocido: True si el club vendio al menos
    min_ventas_para_flag jugadores sub-23 a una liga CON score de
    prestigio disponible, en la ventana movil de N años anteriores a T.

    A diferencia de reputacion_vendedor, el flag no necesita promediar nada 
    -- una sola venta documentada a una liga top ya es evidencia valida de 
    que el evento ocurrio. Esto da mucha mas cobertura, a costa de perder
    granularidad (no distingue "vendio una vez" de "vende
    sistematicamente" -- para eso sigue estando ventas_a_liga_top como
    conteo, y reputacion_vendedor como score cuando esta disponible).

    """
    tr = transfers.copy()
    tr["transfer_date"] = pd.to_datetime(tr["transfer_date"])
    tr["season"] = derivar_season_desde_fecha(tr["transfer_date"])
    tr = tr.merge(players[["player_id", "date_of_birth"]], on="player_id", how="left")
    tr["date_of_birth"] = pd.to_datetime(tr["date_of_birth"])
    tr["edad"] = (tr["transfer_date"] - tr["date_of_birth"]).dt.days / 365.25
    tr = tr[tr["edad"] <= edad_max]

    mapa_destino = mapa_club_liga.rename(columns={"club_id": "to_club_id", "competition_id": "liga_destino"})
    tr = tr.merge(mapa_destino, on=["to_club_id", "season"], how="left")

    scores = score_prestigio_liga[["liga_destino", "score_prestigio_liga"]].dropna()
    tr = tr.merge(scores, on="liga_destino", how="left")
    tr = tr.dropna(subset=["score_prestigio_liga"])

    parcial = []
    temporadas = range(anio_min, tr["season"].max() + 1)
    for club_id, grupo in tr.groupby("from_club_id"):
        for season in temporadas:
            ventana = grupo[
                (grupo["season"] < season) & (grupo["season"] >= season - ventana_anios)
            ]
            if len(ventana) == 0:
                continue
            parcial.append({
                "club_id": club_id,
                "season": season,
                "club_vendedor_reconocido": len(ventana) >= min_ventas_para_flag,
                "ventas_a_liga_top": len(ventana),
            })

    parcial_df = pd.DataFrame(parcial)

    completo = universo_club_temporada[["club_id", "season"]].drop_duplicates().merge(
        parcial_df, on=["club_id", "season"], how="left"
    )
    completo["club_vendedor_reconocido"] = completo["club_vendedor_reconocido"].fillna(False)
    completo["ventas_a_liga_top"] = completo["ventas_a_liga_top"].fillna(0)

    return completo


# ---------------------------------------------------------------------------
# Variable 8 - Companieros de plantel (valor promedio, leave-one-out)
# ---------------------------------------------------------------------------

def construir_companieros_plantel(player_valuations, transfers, appearances,
                                   anio_min=ANIO_MIN_COBERTURA):
    """
    Valor promedio de los companeros de plantel de cada jugador, en el
    momento de cada valuacion -- leave-one-out sobre calidad_plantel
    (excluye al propio jugador del promedio, para no inflar la medida de
    contexto con el valor del jugador mismo).
    """
    reconstruido = reconstruir_club_historico(player_valuations, transfers, appearances)
    reconstruido["anio"] = derivar_season_desde_fecha(reconstruido["date"])
    reconstruido = reconstruido[reconstruido["anio"] >= anio_min]
    reconstruido = reconstruido.dropna(subset=["club_id_final"])

    agregado_plantel = reconstruido.groupby(["club_id_final", "anio"]).agg(
        valor_total_plantel=("market_value_in_eur", "sum"),
        jugadores_plantel=("player_id", "nunique"),
    ).reset_index()

    resultado = reconstruido.merge(agregado_plantel, on=["club_id_final", "anio"])

    resultado["valor_companieros_total"] = resultado["valor_total_plantel"] - resultado["market_value_in_eur"]
    resultado["companieros_distintos"] = resultado["jugadores_plantel"] - 1

    sin_companieros = resultado["companieros_distintos"] == 0
    resultado["companieros_valor_promedio"] = None
    resultado.loc[~sin_companieros, "companieros_valor_promedio"] = (
        resultado.loc[~sin_companieros, "valor_companieros_total"] /
        resultado.loc[~sin_companieros, "companieros_distintos"]
    )

    return resultado[[
        "player_id", "date", "club_id_final", "anio",
        "companieros_valor_promedio", "companieros_distintos"
    ]]


if __name__ == "__main__":
    tablas = cargar_tablas()

    objetivos_deportivos = construir_objetivos_deportivos(
        tablas["games"], tablas["club_games"]
    )
    print("objetivos_deportivos:", objetivos_deportivos.shape)

    club_historico = reconstruir_club_historico(
        tablas["player_valuations"], tablas["transfers"], tablas["appearances"]
    )
    print("\n=== Diagnostico Haaland (club historico reconstruido) ===")
    print(diagnostico_haaland(club_historico))
    print("\nNaN global en club_id_final:", club_historico["club_id_final"].isna().mean())

    calidad_plantel = construir_calidad_plantel(
        tablas["player_valuations"], tablas["transfers"], tablas["appearances"]
    )
    print("\ncalidad_plantel:", calidad_plantel.shape)
    print(calidad_plantel.head(10))
    print(calidad_plantel["jugadores_valuados"].describe())

    competencias_intl = construir_competencias_internacionales(
        tablas["games"], tablas["club_games"]
    )
    print("\ncompetencias_internacionales:", competencias_intl.shape)
    print(competencias_intl["fase_maxima_alcanzada"].value_counts().sort_index())
    print(competencias_intl.head(10))

    continuidad_tecnica = construir_continuidad_tecnica(
        tablas["games"], tablas["club_games"]
    )
    print("\ncontinuidad_tecnica:", continuidad_tecnica.shape)
    print(continuidad_tecnica["entrenadores_distintos"].value_counts().sort_index())
    print("hubo_cambio_entrenador (media):", continuidad_tecnica["hubo_cambio_entrenador"].mean())

    sistema_tactico = construir_sistema_tactico(
        tablas["games"], tablas["club_games"]
    )
    print("\nsistema_tactico:", sistema_tactico.shape)
    print(sistema_tactico["formacion_base_predominante"].value_counts())
    print(sistema_tactico["estructuras_base_distintas"].describe())

    competencia_puesto = construir_competencia_interna_puesto(
        tablas["game_lineups"], tablas["games"]
    )
    print("\ncompetencia_interna_puesto:", competencia_puesto.shape)
    print(competencia_puesto.groupby("posicion_amplia")["jugadores_distintos"].describe())

    posicion_jugador = construir_posicion_amplia_jugador_temporada(
        tablas["game_lineups"], tablas["games"]
    )
    print("\nposicion_amplia_jugador_temporada:", posicion_jugador.shape)
    print(posicion_jugador["posicion_amplia_predominante"].value_counts())
    print("posiciones_distintas > 1 (jugadores versatiles):",
          (posicion_jugador["posiciones_distintas"] > 1).mean())

    mapa_club_liga = construir_mapa_club_liga_por_temporada(tablas["games"], tablas["club_games"])
    score_prestigio = construir_score_prestigio_liga(
        tablas["transfers"], tablas["players"], mapa_club_liga, tablas["competitions"]
    )
    reputacion_vendedor = construir_reputacion_club_vendedor(
        tablas["transfers"], tablas["players"], mapa_club_liga, score_prestigio
    )
    print("\nreputacion_vendedor:", reputacion_vendedor.shape)
    print("cobertura (fraccion con valor no nulo):", reputacion_vendedor["reputacion_vendedor"].notna().mean())

    flag_vendedor = construir_flag_club_vendedor(
        tablas["transfers"], tablas["players"], mapa_club_liga, score_prestigio,
        universo_club_temporada=objetivos_deportivos
    )
    print("\nflag_club_vendedor:", flag_vendedor.shape)
    print("tasa de club_vendedor_reconocido=True:", flag_vendedor["club_vendedor_reconocido"].mean())

    companieros = construir_companieros_plantel(
        tablas["player_valuations"], tablas["transfers"], tablas["appearances"]
    )
    print("\ncompanieros_plantel:", companieros.shape)
    print("fraccion sin companieros calculables:", (companieros["companieros_distintos"] == 0).mean())