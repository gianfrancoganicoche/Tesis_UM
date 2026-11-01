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


def construir_variable_dependiente(player_valuations, players):
    """Punto de entrada: valor de mercado + edad, a nivel (player_id, season)."""
    valor_mercado = construir_valor_mercado_por_temporada(player_valuations)
    return agregar_edad(players, valor_mercado)