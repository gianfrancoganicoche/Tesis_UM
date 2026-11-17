"""
d10_construir_companieros_previo.py

Variable `companieros_valor_previo`: version SIN FUGA de `companieros_valor_promedio`.

PROBLEMA QUE RESUELVE (comentario del tutor, 16/11/2026): `companieros_valor_promedio`
(d02) se calcula como (valor total del plantel - valor del propio jugador) / (n - 1) en la
MISMA temporada. Aunque el propio jugador se excluya, el valor del plantel y el del jugador
se mueven juntos (clubes caros valuan caro a todos), y el efecto entre jugadores sale muy
alto (0,82 contra 0,22 dentro). Un boosting lo aprovecha y parece mejorar 32 %.

DEFINICION: para el jugador i en el club c y la temporada s, el promedio del valor de mercado
de los jugadores del plantel de c en la temporada ANTERIOR (s-1), sin contar a i si estaba
en ese plantel. Cada jugador cuenta una sola vez por club-temporada (su ultima valuacion de
la temporada, misma regla del panel). El valor propio de la temporada s no entra en ningun
paso, ni el propio valor de s-1.

LIMITES: se pierde la primera temporada del panel y los club-temporada cuyo plantel de s-1
no tiene valuaciones. El plantel solo incluye jugadores con valuacion en player_valuations
(cobertura parcial), igual que la variable original.

SALIDA: data/processed/companieros_previo_<fecha>.csv
  player_id, season, companieros_valor_previo, companieros_previo_n

USO: uv run scripts/dataset/d10_construir_companieros_previo.py
"""
import sys
from pathlib import Path

import pandas as pd

_RAIZ_SCRIPTS = Path(__file__).resolve().parents[1]
for _carpeta in ("config", "dataset"):
    sys.path.insert(0, str(_RAIZ_SCRIPTS / _carpeta))

import config
import d02_construir_variables_contexto as ctx


def ultima_valuacion_por_temporada(tablas):
    """Una fila por (player_id, season): ultima valuacion de la temporada y su club."""
    rec = ctx.reconstruir_club_historico(tablas["player_valuations"], tablas["transfers"], tablas["appearances"])
    rec["date"] = pd.to_datetime(rec["date"])
    rec["season"] = ctx.derivar_season_desde_fecha(rec["date"])
    rec = rec[rec["season"] >= config.ANIO_MIN_COBERTURA]
    rec = rec.dropna(subset=["club_id_final", "market_value_in_eur"])
    rec = rec.sort_values("date").drop_duplicates(subset=["player_id", "season"], keep="last")
    return rec[["player_id", "season", "club_id_final", "market_value_in_eur"]].reset_index(drop=True)


def construir_companieros_previo(ult):
    """ult: salida de ultima_valuacion_por_temporada. Devuelve el panel (player_id, season)."""
    plantel = ult.groupby(["club_id_final", "season"]).agg(
        total_prev=("market_value_in_eur", "sum"), n_prev=("player_id", "nunique")
    ).reset_index()
    plantel["season"] = plantel["season"] + 1  # el plantel de s-1 se asigna a la temporada s

    out = ult[["player_id", "season", "club_id_final"]].merge(plantel, on=["club_id_final", "season"], how="left")

    # Si el propio jugador estaba en ese plantel en s-1, se descuenta (leave-one-out).
    propio = ult.rename(columns={"market_value_in_eur": "propio_prev"})[
        ["player_id", "season", "club_id_final", "propio_prev"]
    ].copy()
    propio["season"] = propio["season"] + 1
    out = out.merge(propio, on=["player_id", "season", "club_id_final"], how="left")

    esta = out["propio_prev"].notna()
    out["companieros_previo_n"] = out["n_prev"] - esta.astype(int)
    out["companieros_valor_previo"] = (out["total_prev"] - out["propio_prev"].fillna(0.0)) / out["companieros_previo_n"]
    out.loc[~(out["companieros_previo_n"] >= 1), "companieros_valor_previo"] = float("nan")
    return out[["player_id", "season", "companieros_valor_previo", "companieros_previo_n"]]


def main():
    tablas = ctx.cargar_tablas()
    ult = ultima_valuacion_por_temporada(tablas)
    print(f"Jugador-temporada con valuacion y club: {len(ult)}")
    res = construir_companieros_previo(ult)
    validos = res["companieros_valor_previo"].notna()
    print(f"Con companieros_valor_previo: {int(validos.sum())} de {len(res)} ({validos.mean():.1%})")
    print("\nCompaneros contados (n) entre los validos:")
    print(res.loc[validos, "companieros_previo_n"].describe().round(1).to_string())
    print("\nCobertura por temporada:")
    print(res.groupby("season")["companieros_valor_previo"].apply(lambda s: s.notna().mean()).round(3).to_string())
    ruta = config.RUTA_DATOS_PROCESSED / f"companieros_previo_{pd.Timestamp.today().date()}.csv"
    res.to_csv(ruta, index=False)
    print(f"\nGuardado: {ruta}")


if __name__ == "__main__":
    main()
