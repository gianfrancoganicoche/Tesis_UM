"""
Merge final del panel de predictores: rendimiento individual (player_id,
season) + contexto de club (club_id, season), unidos via el crosswalk
jugador->club por temporada.

ALCANCE DE ESTE MERGE:
- Incluye: las 6 variables de rendimiento (d03_construir_variables_rendimiento.py)
  + 6 de las 8 variables de contexto que viven a nivel (club_id, season):
  objetivos_deportivos, calidad_plantel, competencias_internacionales,
  continuidad_tecnica, sistema_tactico, reputacion_vendedor + flag_vendedor
  -- mas companieros_plantel (nivel (player_id, season), ver nota abajo).

- companieros_plantel: vive originalmente a nivel (player_id,
  date_valuacion), no (player_id, season). Se resuelve aplicando la misma
  regla ya fijada ("para cada jugador-temporada, se usa la ultima valuacion
  registrada dentro de esa temporada") -- no es una decision de diseño
  nueva ni distinta para esta variable, es la regla general del panel
  aplicada aca. Ver construir_companieros_plantel_por_temporada() abajo.

"""

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import d02_construir_variables_contexto as ctx
import d03_construir_variables_rendimiento as rend


def construir_companieros_plantel_por_temporada(player_valuations, transfers, appearances,
                                                 anio_min=ctx.ANIO_MIN_COBERTURA):
    """
    Colapsa companieros_plantel de (player_id, fecha de valuacion) a
    (player_id, season), aplicando la regla ya fijada para todo el panel: para 
    cada jugador-temporada, se usa la ultima valuacion registrada dentro de esa
    temporada (no el promedio -- para no diluir shocks de fin de temporada
    que son informativos, ej. post-mundial). Es la misma regla que ya se
    aplica implicitamente al resto del panel via la granularidad de
    appearances.csv/games.csv; aca se aplica de forma explicita porque
    companieros_plantel es la unica variable que todavia vive a nivel de
    valuacion individual, no de temporada.
    """
    companieros = ctx.construir_companieros_plantel(player_valuations, transfers, appearances)
    companieros = companieros.dropna(subset=["companieros_valor_promedio"])
    companieros = companieros.rename(columns={"anio": "season"})
    companieros = companieros[companieros["season"] >= anio_min]

    companieros["date"] = pd.to_datetime(companieros["date"])
    ultima_por_temporada = (
        companieros.sort_values("date")
        .drop_duplicates(subset=["player_id", "season"], keep="last")
    )

    return ultima_por_temporada[
        ["player_id", "season", "companieros_valor_promedio", "companieros_distintos"]
    ]


def construir_panel_predictores(tablas, anio_min=rend.ANIO_MIN_COBERTURA_GAMES):
    """
    tablas: dict con las tablas ya cargadas (mismo formato que devuelve
    construir_variables_contexto.cargar_tablas()) -- players, clubs,
    competitions, games, club_games, game_lineups, appearances, transfers,
    player_valuations.

    Devuelve un panel (player_id, season) con rendimiento individual +
    contexto de club.
    """
    # --- Rendimiento ---
    panel_rendimiento = rend.construir_panel_rendimiento(
        tablas["appearances"], tablas["players"], tablas["games"],
        tablas["club_games"], tablas["game_lineups"], anio_min
    )

    # --- Crosswalk: que club tuvo cada jugador cada temporada ---
    crosswalk = rend.construir_crosswalk_jugador_club_temporada(
        tablas["appearances"], tablas["games"], anio_min
    )
    # Renombrar para no chocar con el flag de multiples clubes que ya trae
    # panel_rendimiento (viene de pct_minutos_disponibles, mismo concepto
    # pero calculado independiente
    crosswalk_para_merge = crosswalk.rename(
        columns={"tuvo_multiples_clubes_temporada": "tuvo_multiples_clubes_temporada_crosswalk"}
    )

    panel = panel_rendimiento.merge(crosswalk_para_merge, on=["player_id", "season"], how="left")

    # --- Contexto de club (5 de las 8 variables, todas a nivel club_id+season) ---
    objetivos_deportivos = ctx.construir_objetivos_deportivos(
        tablas["games"], tablas["club_games"], anio_min=anio_min
    )
    objetivos_deportivos = objetivos_deportivos.rename(
        columns={"partidos_jugados": "partidos_jugados_club"}
    )
    competencias_intl = ctx.construir_competencias_internacionales(
        tablas["games"], tablas["club_games"], anio_min=anio_min
    )
    continuidad_tecnica = ctx.construir_continuidad_tecnica(
        tablas["games"], tablas["club_games"], anio_min=anio_min
    )
    sistema_tactico = ctx.construir_sistema_tactico(
        tablas["games"], tablas["club_games"], anio_min=anio_min
    )
    calidad_plantel = ctx.construir_calidad_plantel(
        tablas["player_valuations"], tablas["transfers"], tablas["appearances"]
    )

    mapa_club_liga = ctx.construir_mapa_club_liga_por_temporada(tablas["games"], tablas["club_games"])
    score_prestigio = ctx.construir_score_prestigio_liga(
        tablas["transfers"], tablas["players"], mapa_club_liga, tablas["competitions"]
    )
    reputacion_vendedor = ctx.construir_reputacion_club_vendedor(
        tablas["transfers"], tablas["players"], mapa_club_liga, score_prestigio
    )
    flag_vendedor = ctx.construir_flag_club_vendedor(
        tablas["transfers"], tablas["players"], mapa_club_liga, score_prestigio,
        universo_club_temporada=objetivos_deportivos
    )

    # Cada merge de contexto es LEFT JOIN sobre club_id+season -- un jugador
    # cuyo club-temporada no tiene esa variable calculada (ej. reputacion_vendedor,
    # cobertura de solo 4.2%) queda con NaN, no se descarta la fila.
    panel = panel.merge(objetivos_deportivos, on=["club_id", "season"], how="left")
    panel = panel.merge(competencias_intl, on=["club_id", "season"], how="left")
    panel = panel.merge(continuidad_tecnica, on=["club_id", "season"], how="left")
    panel = panel.merge(sistema_tactico, on=["club_id", "season"], how="left")
    panel = panel.merge(calidad_plantel, on=["club_id", "season"], how="left")
    panel = panel.merge(
        reputacion_vendedor[["club_id", "season", "reputacion_vendedor", "ventas_sub23_totales"]],
        on=["club_id", "season"], how="left"
    )
    panel = panel.merge(
        flag_vendedor[["club_id", "season", "club_vendedor_reconocido", "ventas_a_liga_top"]],
        on=["club_id", "season"], how="left"
    )
    panel["tiene_score_vendedor"] = panel["reputacion_vendedor"].notna()

    # --- Companieros de plantel (7ma de las 8 variables de contexto) ---
    # Unica variable de contexto a nivel (player_id, season) en vez de
    # (club_id, season) -- se mergea por player_id+season, no por club_id.
    companieros = construir_companieros_plantel_por_temporada(
        tablas["player_valuations"], tablas["transfers"], tablas["appearances"]
    )
    panel = panel.merge(companieros, on=["player_id", "season"], how="left")

    # --- Competencia interna por el puesto (8va y ultima variable de contexto) ---
    # Vive a nivel (club_id, season, posicion_amplia) -- se trae a nivel
    # (player_id, season) via la posicion_amplia_predominante de cada jugador
    # esa temporada (T27). Un jugador versatil (25.8% de los casos) 
    # queda representado solo por su posicion predominante, no por las secundarias.
    posicion_jugador = ctx.construir_posicion_amplia_jugador_temporada(
        tablas["game_lineups"], tablas["games"], anio_min=anio_min
    )
    panel = panel.merge(posicion_jugador, on=["player_id", "season"], how="left")

    competencia_puesto = ctx.construir_competencia_interna_puesto(
        tablas["game_lineups"], tablas["games"], anio_min=anio_min
    ).rename(columns={
        "posicion_amplia": "posicion_amplia_predominante",
        "jugadores_distintos": "competidores_totales_puesto",
        "titularidades_totales": "titularidades_puesto_club",
    })
    panel = panel.merge(
        competencia_puesto,
        on=["club_id", "season", "posicion_amplia_predominante"],
        how="left"
    )

    # Leave-one-out: el propio jugador esta incluido en
    # competidores_totales_puesto por construccion -- restar 1 para medir la
    # competencia que ENFRENTA, no la competencia total incluyendose a si
    # mismo (mismo criterio que companieros_plantel).
    panel["competidores_mismo_puesto"] = panel["competidores_totales_puesto"] - 1

    return panel


if __name__ == "__main__":
    tablas = ctx.cargar_tablas()
    panel = construir_panel_predictores(tablas)
    print("panel_predictores:", panel.shape)
    print("duplicados (player_id, season):", panel.duplicated(subset=["player_id", "season"]).sum())
    print(panel.head())