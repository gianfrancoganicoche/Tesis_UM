"""
Merge final del panel de predictores: rendimiento individual (player_id,
season) + contexto de club (club_id, season), unidos via el crosswalk
jugador->club por temporada.

ALCANCE DE ESTE MERGE (sesion previa a tutoria 22/07):
- Incluye: las 6 variables de rendimiento (construir_variables_rendimiento.py)
  + 5 de las 8 variables de contexto que viven a nivel (club_id, season):
  objetivos_deportivos, calidad_plantel, competencias_internacionales,
  continuidad_tecnica, sistema_tactico, reputacion_vendedor + flag_vendedor.

- QUEDAN FUERA, documentado como pendiente explicito:
  1) competencia_interna_puesto: vive a nivel (club_id, season,
     posicion_amplia) -- una dimension extra que ninguna otra variable tiene.
     Pegarla requeriria la posicion de cada jugador por temporada, que no
     esta calculada en ningun panel todavia. No resuelto en esta sesion.
  2) companieros_plantel: vive a nivel (player_id, date_valuacion), no
     (player_id, season) -- atada a la fecha de cada valuacion de mercado,
     no a la temporada. Requiere una decision de diseño sobre como pasar de
     granularidad de valuacion a granularidad de temporada (ultima valuacion
     del año? promedio?) que no se tomo en esta sesion.
  3) La variable dependiente (crecimiento de valor de mercado bajo el diseño
     de trayectoria completa / Alternativa 3) -- el codigo que la construye
     bajo el diseño nuevo no existe todavia. El panel resultante de este
     script es un panel de PREDICTORES, no el dataset final modelable.
"""

import pandas as pd

import construir_variables_rendimiento as rend
import construir_variables_contexto as ctx


def construir_panel_predictores(tablas, anio_min=rend.ANIO_MIN_COBERTURA_GAMES):
    """
    tablas: dict con las tablas ya cargadas (mismo formato que devuelve
    construir_variables_contexto.cargar_tablas()) -- players, clubs,
    competitions, games, club_games, game_lineups, appearances, transfers,
    player_valuations.

    Devuelve un panel (player_id, season) con rendimiento individual +
    contexto de club. Ver docstring del modulo para lo que queda fuera.
    """
    # --- Rendimiento (ya validado en sesion previa) ---
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
    # pero calculado independiente -- se documenta la redundancia, no se
    # elimina, para poder comparar ambos calculos como chequeo de consistencia)
    crosswalk_para_merge = crosswalk.rename(
        columns={"tuvo_multiples_clubes_temporada": "tuvo_multiples_clubes_temporada_crosswalk"}
    )

    panel = panel_rendimiento.merge(crosswalk_para_merge, on=["player_id", "season"], how="left")

    # --- Contexto de club (5 de las 8 variables, todas a nivel club_id+season) ---
    objetivos_deportivos = ctx.construir_objetivos_deportivos(
        tablas["games"], tablas["club_games"], anio_min=anio_min
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

    return panel


if __name__ == "__main__":
    tablas = ctx.cargar_tablas()
    panel = construir_panel_predictores(tablas)
    print("panel_predictores:", panel.shape)
    print("duplicados (player_id, season):", panel.duplicated(subset=["player_id", "season"]).sum())
    print(panel.head())
