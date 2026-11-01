"""
Construccion de la variable dependiente (valor de mercado / curva de edad)
bajo el diseño de trayectoria completa. 
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import d02_construir_variables_contexto as ctx


def construir_valor_mercado_por_temporada(player_valuations, anio_min=ctx.ANIO_MIN_COBERTURA):
    """
    Valor de mercado a nivel (player_id, season), aplicando la misma regla ya
    fijada para todo el panel: para cada jugador-temporada, se usa la ULTIMA 
    valuacion registrada dentro de esa temporada (no el promedio) -- mismo 
    criterio que companieros_plantel.
    """
    pv = player_valuations.copy()
    pv["date"] = pd.to_datetime(pv["date"])
    pv["season"] = ctx.derivar_season_desde_fecha(pv["date"])
    pv = pv[pv["season"] >= anio_min]

    ultima_por_temporada = (
        pv.sort_values("date")
        .drop_duplicates(subset=["player_id", "season"], keep="last")
    )

    resultado = ultima_por_temporada[["player_id", "season", "market_value_in_eur", "date"]].rename(
        columns={"market_value_in_eur": "valor_mercado_eur", "date": "fecha_ultima_valuacion_temporada"}
    )
    resultado["log_valor_mercado"] = np.log(resultado["valor_mercado_eur"])
    return resultado


def agregar_edad(players, valor_mercado_por_temporada):
    """
    Edad del jugador al momento de la ultima valuacion de esa temporada -- es
    el eje x de la curva de edad.
    """
    pl = players[["player_id", "date_of_birth"]].copy()
    pl["date_of_birth"] = pd.to_datetime(pl["date_of_birth"])

    resultado = valor_mercado_por_temporada.merge(pl, on="player_id", how="left")
    resultado["edad"] = (
        (resultado["fecha_ultima_valuacion_temporada"] - resultado["date_of_birth"]).dt.days / 365.25
    )
    return resultado.drop(columns=["date_of_birth"])


def construir_valor_previo(valor_mercado_por_temporada, claves_panel):
    """
    Variante C del "valor de antes" (decision 31/10/2026, ver nota para el tutor,
    decision 1): para cada fila (player_id, season) del panel, la ULTIMA valuacion
    estrictamente ANTERIOR a esa temporada, mirando todas las valuaciones por
    temporada del jugador -- con o sin fila en el panel, y hasta 2010
    (ANIO_MIN_COBERTURA), asi que cubre valuaciones de antes de que el jugador
    entrara al panel (caso "Haaland antes de llegar a una liga top") sin agregar
    filas nuevas.

    Devuelve [player_id, season, log_valor_previo, rezago_previo]:
      - log_valor_previo: log del valor de esa valuacion previa (NaN si el jugador
        no tiene ninguna anterior; ~24.5% de los ingresos reales al panel).
      - rezago_previo: temporadas entre esa valuacion y la fila (>=1; 1 = la
        temporada inmediata anterior). OJO: el valor puede estar desactualizado
        -- para jugadores cuya serie de valuaciones se corta en la fuente, el
        valor queda congelado en el ultimo registrado (rezago grande o creciente).
        rezago_previo es la variable que marca esa antiguedad.

    Misma regla de temporada que valor_mercado_por_temporada (ultima valuacion de
    cada temporada). Funcion pura; el resultado tiene una fila por clave del
    panel (se valida).
    """
    claves = claves_panel[["player_id", "season"]].drop_duplicates().sort_values("season").reset_index(drop=True)
    v = valor_mercado_por_temporada[["player_id", "season", "valor_mercado_eur"]].copy()
    v = v.drop_duplicates(["player_id", "season"]).rename(columns={"season": "_t_previa"})
    v["log_valor_previo"] = np.log(v["valor_mercado_eur"])
    v["_clave"] = v["_t_previa"]
    v = v.sort_values("_clave")

    claves["season"] = claves["season"].astype("int64")
    v["_clave"] = v["_clave"].astype("int64")
    m = pd.merge_asof(
        claves, v[["player_id", "_t_previa", "_clave", "log_valor_previo"]],
        left_on="season", right_on="_clave", by="player_id",
        direction="backward", allow_exact_matches=False,
    )
    m["rezago_previo"] = m["season"] - m["_t_previa"]
    resultado = m[["player_id", "season", "log_valor_previo", "rezago_previo"]]
    if resultado.duplicated(["player_id", "season"]).any():
        raise ValueError("construir_valor_previo devolvio claves duplicadas -- no deberia pasar.")
    return resultado


def construir_variable_dependiente(player_valuations, players):
    """Punto de entrada: valor de mercado + edad, a nivel (player_id, season)."""
    valor_mercado = construir_valor_mercado_por_temporada(player_valuations)
    return agregar_edad(players, valor_mercado)