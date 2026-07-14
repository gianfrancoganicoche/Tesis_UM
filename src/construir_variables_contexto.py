"""
Construccion de variables de contexto para el panel de la tesis.

Fuente: davidcariboo/player-scores (Kaggle).
Ver docs/inventario_variables_contexto.md para el mapeo completo de factores
a tablas/campos, y que queda pendiente de construir.

Este script se va extendiendo sesion a sesion con una funcion por variable.
Cada funcion recibe DataFrames ya cargados (no rutas), para poder testearlas
y componerlas sin recargar los CSV cada vez.
"""

import re

import pandas as pd
import kagglehub

ANIO_MIN_COBERTURA = 2010  # piso de player_valuations.csv, usado en src/panel_pipeline.py
ANIO_MIN_COBERTURA_GAMES = 2012  # piso especifico de games.csv/club_games.csv --
# NO es el mismo que player_valuations.csv. Confirmado en sesion: season
# en games.csv tiene solo 31-64 partidos/anio en 2005-2011 (ruido de carga
# historica dispersa), y recien se vuelve densa y consecutiva desde 2012
# (~5.700-6.000 partidos/anio). Usar ANIO_MIN_COBERTURA (2010) para esta
# tabla habria incluido temporadas con cobertura casi vacia sin que ningun
# chequeo lo hiciera evidente.


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


def cargar_tablas():
    """Descarga (o reutiliza cache local) y carga todas las tablas de player-scores."""
    path = kagglehub.dataset_download("davidcariboo/player-scores")
    tablas = {
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
    return tablas


# ---------------------------------------------------------------------------
# Variable 1 - Objetivos deportivos (posicion en tabla, resultado, puntos)
# Estado: CONSTRUIDA Y VALIDADA.
# 3.906 filas club-temporada. partidos_jugados: mediana 34, IQR 30-38,
# consistente con formato de liga europea estandar. 94 casos con <15
# partidos, 93 de ellos en 2024 (48) y 2025 (45) -- temporadas en curso o
# recien cerradas al momento del snapshot del dataset, esperable. 1 unico
# outlier real en 2013, despreciable.
# ---------------------------------------------------------------------------

def construir_objetivos_deportivos(games, club_games, tipo_liga_domestica="domestic_league",
                                    anio_min=ANIO_MIN_COBERTURA_GAMES):
    """
    Agrega objetivos deportivos por club-temporada: posicion final en tabla,
    % de victorias, diferencia de gol promedio -- solo sobre partidos de liga
    domestica (own_position solo esta poblado ahi: 99.88% de cobertura en
    domestic_league vs. ~0% en domestic_cup/international_cup/national_team_competition,
    verificado en sesion). Filtra por ANIO_MIN_COBERTURA_GAMES (2012), no
    ANIO_MIN_COBERTURA (2010) -- ver nota junto a la constante.
    """
    partidos = club_games.merge(
        games[["game_id", "season", "competition_type", "date"]],
        on="game_id"
    )
    partidos = partidos[partidos["season"] >= anio_min]
    partidos_liga = partidos[partidos["competition_type"] == tipo_liga_domestica].copy()

    # is_win es int64 (1/0), no bool -- forzar comparacion explicita.
    # Usar .loc con la Serie de enteros directamente causa un KeyError
    # confuso porque pandas la interpreta como lista de indices, no mascara.
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
# Problema de origen: ni clubs.csv (snapshot del club actual, confirmado con
# club_id sin duplicados y last_season disperso 2012-2025) ni el campo
# current_club_id de player_valuations.csv (tambien snapshot -- confirmado
# con Haaland: club_id=281 constante en sus 26 valuaciones entre 2016 y
# 2025, pese a haber jugado en 4 clubes distintos) sirven para saber en que
# club estaba un jugador en el momento de una valuacion HISTORICA.
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
#   0-16 anios: 9.0%  (SIN mejora respecto a usar solo appearances.csv --
#                       ninguna de las dos fuentes cubre bien esta franja,
#                       son valuaciones especulativas pre-debut y pre-
#                       transferencia formal)
#   16-18:      36.0%
#   18-20:      47.8%
#   20-23:      53.5%
#   23+:        58.3%
#
# LIMITACION A DOCUMENTAR EN LA TESIS: el contexto de club no es
# reconstruible con confianza para una porcion sustancial de las
# valuaciones mas tempranas de la poblacion de interes (sub-23), en
# particular por debajo de los 16-17 anios. No es un bug de la
# implementacion -- es un vacio real de las fuentes de datos disponibles
# para el segmento de "promesa juvenil valuada antes de cualquier evento
# publico registrable". Cualquier variable derivada de club historico
# (calidad de plantel, companieros, objetivos deportivos del club en el
# momento T) hereda esta limitacion para esas observaciones.
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
# Estado: CONSTRUIDA sobre club_id_final (reconstruido), NO sobre
# current_club_id de player_valuations.csv (confirmado como snapshot) ni
# sobre clubs.csv (confirmado como snapshot).
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
# Estado: CONSTRUIDA Y VALIDADA.
# 3.304 filas club-temporada. fase_maxima_alcanzada sin ningun NaN (2080
# en fase 1, decreciendo hasta 83 en fase 6/Final -- distribucion esperada,
# el aparente "salto" entre semis (66) y final (83) es semantica correcta
# de tomar el maximo por club-temporada, no un error: un finalista tambien
# jugo semis pero queda clasificado en fase 6, no 5, asi que fase 5 solo
# cuenta a los perdedores de semifinal).
#
# HALLAZGO IMPORTANTE: NO filtrar por competition_type == 'international_cup'.
# Confirmado en sesion que Europa League y Conference League (competition_id
# EL, ELQ, UCOL, ECLQ) estan categorizadas bajo competition_type='other',
# NO 'international_cup' (que solo cubre Champions League + clasificacion +
# Supercopa). Filtrar por competition_type habria subestimado sistematicamente
# la participacion europea de clubes que juegan EL/Conference en vez de CL --
# sesgo correlacionado con el nivel del club, dificil de detectar despues.
# Se filtra por competition_id explicito en su lugar.
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
    Europa) por club-temporada. Ver nota de HALLAZGO IMPORTANTE arriba sobre
    por que se filtra por competition_id y no por competition_type.
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
# Estado: CONSTRUIDA Y VALIDADA.
# 3.906 filas club-temporada (mismo shape que objetivos_deportivos, filtro
# de liga domestica consistente entre variables). own_manager_name con
# cobertura casi completa (0.95% NaN) y nombres limpios, sin variantes de
# escritura -- verificado con historial completo del Real Madrid
# (Mourinho/Ancelotti/Benitez/Zidane/Lopetegui/Solari/Xabi Alonso/Arbeloa,
# todos distintos y correctos) y con el caso extremo de 7 entrenadores en
# una temporada (Denizlispor 2020, temporada de descenso -- 7 nombres
# genuinamente distintos, incluye un interino que vuelve dos veces
# separado en el tiempo; confirmado como caso real, no ruido de texto).
# entrenadores_distintos: mayoria 1-2 (2159 + 948 de 3906), cola decreciente
# hasta 7. hubo_cambio_entrenador=True en 44.7% de las temporadas.
#
# SIMPLIFICACION CONOCIDA: no distingue cambio de proyecto de fondo vs.
# interinato de corto plazo tras un despido -- ambos cuentan igual como
# "cambio de entrenador". Documentado, no resuelto en esta iteracion.
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
# Estado: CONSTRUIDA, CON ADVERTENCIA DE CONFIABILIDAD DOCUMENTADA.
# 3.668 filas club-temporada. hosting confirmado limpio (solo "Home"/"Away",
# sin variantes) y usado para elegir correctamente entre home_club_formation
# y away_club_formation segun corresponda a cada club en cada partido.
# Cobertura ~91% (9% de partidos sin formacion registrada en ninguno de los
# dos equipos). formacion_base (regex sobre el patron numerico, ej. "4-3-3"
# extraido de "4-3-3 Attacking") valida: value_counts muestra exactamente
# las 16 estructuras esperables, sin fragmentos rotos.
#
# ADVERTENCIA DE CONFIABILIDAD: estructuras_base_distintas tiene mediana 5
# (¡hasta 13!) por club-temporada -- verificado con un caso real (club_id
# 788, season 2025, 13 estructuras distintas en 30 partidos) que confirma
# que el dato varia genuinamente partido a partido, NO es un error de
# extraccion. Pero a diferencia de own_manager_name (hecho administrativo
# verificable), la formacion es una interpretacion editorial de quien narra
# cada partido -- variabilidad tan alta es mas consistente con una mezcla
# de variabilidad tactica real + ruido/inconsistencia de anotacion entre
# fuentes, que con un club excepcionalmente cambiante. No hay forma de
# separar ambos componentes con los datos disponibles.
#
# USO RECOMENDADO: tratar estructuras_base_distintas como la senal principal
# en si misma (alto = sistema inestable o mal documentado, cualquiera de
# las dos lecturas es contexto legitimo), y formacion_predominante /
# formacion_base_predominante como dato descriptivo secundario, no como
# variable de alta confianza.
#
# VALIDACION CUALITATIVA (sesion): se chequeo el ranking de club-temporada
# mas estables y menos estables (filtrando a >=30 partidos para evitar
# sesgo de muestra chica). Extremo estable: Inter Milan 3-5-2 en 3
# temporadas (coincide con la identidad tactica real de Inzaghi), Barcelona
# 4-3-3 2013-14 (tiki-taka), Athletic Bilbao 4-2-3-1 -- todos casos
# reconocibles, buena senal de que la variable capta algo real. Extremo
# inestable: Brighton 2019 (12 estructuras, coincide con la reputacion real
# de Graham Potter como tecnico tacticamente muy cambiante), PSG 2022
# (crisis de proyecto conocida), varios clubes en pelea de descenso esa
# temporada (Genoa 2018, Elche 2022, Werder Bremen 2020) -- tambien
# reconocibles. PERO: el extremo inestable tambien incluye clubes de ligas
# de menor cobertura (Beerschot/Belgica, Napredak Krusevac/Serbia, NAC
# Breda) donde no se puede descartar que parte de la variacion sea
# inconsistencia de anotacion entre fuentes, no variacion tactica real --
# consistente con el hallazgo ya documentado de cobertura desigual entre
# ligas. La variable es mas confiable para clubes de ligas top que de
# ligas secundarias.
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
# Estado: CONSTRUIDA Y VALIDADA.
# 14.964 filas club-temporada-posicion. Cobertura de mapeo de posicion
# 100% (ninguna posicion quedo sin mapear al correr sobre datos reales --
# el diccionario manual definido a partir del reconocimiento inicial
# resulto exhaustivo, no hizo falta la red de seguridad de fuzzy matching).
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
# que un modelo para este problema especifico. Se uso en cambio
# difflib.get_close_matches como red de seguridad liviana (sugerencia de
# categoria mas parecida si aparece una etiqueta no contemplada), sin
# necesidad de entrenar nada. Fuzzy matching / tecnicas de NLP mas
# sofisticadas quedan reservadas para un caso de uso real futuro: cruzar
# jugadores por NOMBRE entre player-scores y una fuente externa sin ID
# comun (ej. si se retoma hubertsidorowicz u otro dataset), donde si hace
# falta resolver que "Kylian Mbappe" y "K. Mbappe" son la misma persona.
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
        games[["game_id", "competition_type"]], on="game_id"
    )
    lineups = lineups[lineups["competition_type"] == "domestic_league"].copy()
    lineups["date"] = pd.to_datetime(lineups["date"])
    lineups["season"] = derivar_season_desde_fecha(lineups["date"])
    lineups = lineups[lineups["season"] >= anio_min]
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
# Variable 7 - Reputacion de club vendedor
# Estado: CONSTRUIDA, CON COBERTURA BAJA CONFIRMADA Y DECISION PENDIENTE.
#
# Requiere primero un mapeo club->liga POR TEMPORADA (no clubs.csv,
# snapshot) y un score de prestigio de liga calculado empiricamente desde
# los datos (mediana de market_value_in_eur de transferencias entrantes
# sub-23, NO transfer_fee -- confirmado en sesion que transfer_fee tiene
# solo 7.4% de cobertura con valor > 0 contra 61% de market_value_in_eur).
#
# DOS SESGOS ENCONTRADOS Y CORREGIDOS EN SESION, documentados porque el
# patron es reutilizable en cualquier variable con ventana movil + filtro
# de confiabilidad:
#   1) Colision de nombres: "Bundesliga" es tanto Alemania (L1) como
#      Austria (A1) en competitions.csv -- desambiguar SIEMPRE por
#      country_name, no solo por name.
#   2) El piso minimo de observaciones debe aplicarse sobre la cantidad de
#      observaciones que REALMENTE entran al calculo final (ventas_con_score),
#      NO sobre el total de eventos previos a cualquier filtro
#      (ventas_sub23_totales). Confirmado con caso real: Dinamo Zagreb
#      season 2018 tenia 8 ventas totales (pasaba un piso ingenuo de
#      "totales >= 3") pero solo 1 con score de liga disponible -- el
#      promedio quedaba armado sobre una sola observacion disfrazada de
#      estadistica confiable. Aplicar el piso sobre el subconjunto
#      efectivamente usado, no sobre el universo previo al filtro.
#
# RESULTADO: score de prestigio de liga con piso de 30 transferencias
# (confiable: GB1, ES1, FR1, L1-Alemania, IT1, BE1, NL1, PO1, RU1, GR
# Super League, Escocia, Dinamarca, Ucrania, Turquia -- A1-Austria, BRA1,
# Suiza, Japon, Croacia, Noruega quedan con NaN por muestra insuficiente).
# reputacion_vendedor final: solo 4.2% del panel club-temporada queda con
# valor no nulo (piso de 3 ventas CON score en la ventana de 5 anios).
# Top resultante tiene sentido futbolistico (Reading, Wigan, Fulham, Aston
# Villa -- perfil real de clubes ingleses de nivel medio conocidos por
# desarrollar y vender cantera), pero la cobertura es baja.
#
# DECISION PENDIENTE (proxima sesion): mantener como variable de cobertura
# limitada / señal rara (ej. flag binario de "club vendedor reconocido" en
# vez de score continuo), o relajar el piso de score de liga (hoy 30) para
# ampliar cobertura a costa de precision del score por liga. No resuelto
# en esta iteracion -- es decision de diseño, no bug.
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

    NOTA (sesion): min_transferencias se bajo de 30 a 10 a pedido, pero
    esto NO cambio ni el ranking de ligas con score ni la cobertura final
    de reputacion_vendedor (ambos identicos con 30 y con 10). Confirmado:
    ninguna liga excluida tiene entre 10 y 29 transferencias -- todas las
    que quedan fuera tienen de 1 a 7 (Austria, Brasil, Suiza, Japon,
    Croacia, Noruega, Rumania, Suecia, Serbia). El cuello de botella de
    cobertura no es el umbral elegido, es un limite duro de la fuente de
    datos para ligas fuera de las ~14 principales -- bajar el piso mas
    (a 5 o 2) probablemente tampoco cambiaria nada, seguirian siendo
    muestras de 1-4 observaciones. La cobertura baja de reputacion_vendedor
    (4.2%) es una limitacion estructural de la fuente, no un parametro
    ajustable.
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
    ventas_con_score (ver nota de sesgo #2 arriba), no sobre el total de
    ventas.
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

    A diferencia de reputacion_vendedor (score continuo, requiere >=3
    ventas con score para promediar de forma confiable, cobertura final
    4.2%), el flag no necesita promediar nada -- una sola venta
    documentada a una liga top ya es evidencia valida de que el evento
    ocurrio, no una estimacion que dependa de mas casos para
    estabilizarse. Esto da mucha mas cobertura, a costa de perder
    granularidad (no distingue "vendio una vez" de "vende
    sistematicamente" -- para eso sigue estando ventas_a_liga_top como
    conteo, y reputacion_vendedor como score cuando esta disponible).

    BUG CORREGIDO EN SESION: la primera version de esta funcion solo
    generaba filas para club-temporadas con >=1 venta, y calculaba la
    tasa de True SOLO sobre esas filas -- daba 100% por construccion
    (tautologico: "de los casos que ya filtre para tener >=1 venta,
    cuantos tienen >=1 venta"). La correccion requiere hacer left join
    contra el universo COMPLETO de club-temporadas (ej. objetivos_deportivos)
    y tratar la ausencia de filas como False explicito, no como NaN --
    recien ahi la tasa de True es interpretable (confirmado: 46.8% sobre
    el universo completo, distribucion balanceada y util para un modelo).
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
# Estado: CONSTRUIDA Y VALIDADA. Ultima de las 8 variables planificadas.
# Reutiliza reconstruir_club_historico (mismo mecanismo ya validado para
# calidad_plantel) -- no requirio resolver nada nuevo en terminos de datos,
# solo el ajuste leave-one-out.
#
# Solo 2.97% de los casos quedan sin companieros calculables (jugador unico
# valuado en su club esa temporada) -- cobertura mejor de lo esperado dado
# el 44.4% de NaN en la reconstruccion de club historico base.
#
# Validado con Haaland: trayectoria de companieros_valor_promedio coherente
# con su historial real (Salzburg ~13-17M -> Dortmund ~57-67M -> Man City
# ~86-118M, saltos que coinciden con el nivel real de cada plantel). Un
# valor puntual mas bajo en la ultima fila (61M, dic 2025) coincide con una
# caida de companieros_distintos (22 vs 28-29 en filas previas) -- ruido de
# cobertura puntual del snapshot de esa fecha, no un error de la formula.
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
