"""
nl01 (13/11/2026): predicciones fuera de muestra del modelo LINEAL, por pliegue, para
poder compararlo con un modelo no lineal sobre las mismas filas y los mismos pliegues.

POR QUE EXISTE: m03 evalua con ELPD y no guarda las predicciones. Para comparar contra
un modelo que solo da predicciones puntuales (gradient boosting, nl02) hacen falta las
predicciones del modelo lineal de cada jugador retenido. No se toca m03: este script
reutiliza sus funciones (mismos pliegues: asignar_pliegues con semilla 2026, mismas
filas: m02.preparar_datos).

QUE SE PREDICE: el valor de un jugador NUEVO (los jugadores del pliegue no estan en el
ajuste). La prediccion es la parte fija del modelo (todo menos alfa_i, que es 0 en
promedio), promediada sobre los draws posteriores, en la escala original del log del
valor. Las dos fuentes de error que quedan son sigma_alfa y sigma_eps, que el modelo no
puede reducir con covariables.

SALIDAS (reports/nl01_predicciones_lineal/):
    <etiqueta>_predicciones.csv     fila, player_id, season, pliegue, y_log, mu_lineal
    <etiqueta>_elpd_por_jugador.csv ELPD por jugador (para comparar luego con splines bayesianos)
    <etiqueta>_convergencia_pliegues.csv

USO:
    uv run scripts/modelo_no_lineal/nl01_predicciones_lineal.py --rapido                 # prueba de humo
    uv run scripts/modelo_no_lineal/nl01_predicciones_lineal.py --temporada rw --objetivo-aceptacion 0.97 --tune 2000 --draws 2000 --etiqueta lineal_rw

CONTROLES DE FUGA (ver nl02): el lineal con las mismas variables que el boosting de comparacion, por ejemplo
    ... nl01_predicciones_lineal.py --temporada rw --quitar-variable companieros_valor_promedio --etiqueta lineal_rw_sin_comp
    ... nl01_predicciones_lineal.py --temporada rw --quitar-contexto --etiqueta lineal_rw_sin_ctx

Especificacion por defecto: la misma de H1 sin Mundlak (--temporada rw). Con --mundlak se
agregan los promedios por jugador (en ese caso nl02 debe correrse con --medias-jugador).

Requiere: uv add pymc nutpie arviz
"""

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

_RAIZ_SCRIPTS = Path(__file__).resolve().parents[1]  # scripts/
for _carpeta in ("config", "dataset", "eda", "diagnosticos", "modelado", "modelo_no_lineal"):
    sys.path.insert(0, str(_RAIZ_SCRIPTS / _carpeta))


def tabla_predicciones(d, meta, pliegue_fila, mu_lineal):
    """Predicciones por fila en escala original. `d["y"]` esta centrado: se le suma media_y."""
    df = d["df"].reset_index(drop=True)
    return pd.DataFrame({
        "fila": np.arange(len(d["y"])),
        "player_id": df["player_id"].to_numpy(),
        "season": df["season"].to_numpy(),
        "pliegue": pliegue_fila,
        "y_log": d["y"] + meta["media_y"],
        "mu_lineal": mu_lineal,
    })


def main(argv=None):
    parser = argparse.ArgumentParser(description="nl01: predicciones por pliegue del modelo lineal bayesiano.")
    parser.add_argument("--rapido", action="store_true", help="500/500, 2 cadenas, K=3 (prueba de humo).")
    parser.add_argument("--k", type=int, default=None, help="Pliegues (por defecto 5; 3 con --rapido).")
    parser.add_argument("--temporada", choices=["ninguno", "rw"], default="rw")
    parser.add_argument("--grado-edad", type=int, default=2)
    parser.add_argument("--mundlak", action="store_true", help="Agrega el promedio por jugador de contexto y rendimiento.")
    parser.add_argument("--quitar-variable", nargs="+", default=[], dest="quitar_variable",
                        help="Variables de contexto a sacar del modelo (ej. companieros_valor_promedio).")
    parser.add_argument("--quitar-contexto", action="store_true", dest="quitar_contexto",
                        help="Saca todo el bloque de contexto del modelo.")
    parser.add_argument("--etiqueta", default=None)
    parser.add_argument("--objetivo-aceptacion", type=float, default=0.95)
    parser.add_argument("--draws", type=int, default=None)
    parser.add_argument("--tune", type=int, default=None)
    parser.add_argument("--cadenas", type=int, default=None)
    parser.add_argument("--draws-evaluacion", type=int, default=400, help="Draws usados para evaluar cada pliegue.")
    parser.add_argument("--muestreador", choices=["pymc", "nutpie"], default="nutpie")
    args, desconocidos = parser.parse_known_args(argv)
    if desconocidos:
        raise SystemExit(f"Opciones no reconocidas: {desconocidos}. Revisar que el script este actualizado (ver --help).")

    import arviz as az
    import pymc as pm

    import config
    import e08_poblacion_por_capa as e08
    import m02_modelo_base as m02
    import m03_contraste_h1 as m03

    k = args.k or (3 if args.rapido else 5)
    sufijo = ("_sin_ctx" if args.quitar_contexto else "") + "".join(f"_sin_{v}" for v in args.quitar_variable)
    etiqueta = args.etiqueta or f"lineal_{args.temporada}_k{k}" + ("_mun" if args.mundlak else "") + sufijo
    ruta_reports = config.ruta_reports_script(Path(__file__).stem)

    d, meta = m02.preparar_datos(e08.cargar_dataset_modelado())
    if args.quitar_contexto:
        d = m03.quitar_bloque(d, "ctx", meta)
    for v in args.quitar_variable:
        d = m03.quitar_variable(d, meta, v)
    pliegue_fila = m03.asignar_pliegues(d["jug_idx"], k)
    mu_lineal = np.full(len(d["y"]), np.nan)
    elpd = np.full(meta["n_jugadores"], np.nan)
    convergencia = []
    tune, draws, chains = (500, 500, 2) if args.rapido else (1000, 1000, 4)
    tune, draws, chains = args.tune or tune, args.draws or draws, args.cadenas or chains
    kw = {"nuts_sampler": "nutpie"} if args.muestreador == "nutpie" else {}

    print(f"\nPredicciones del modelo lineal: {k} pliegues por jugador, temporada = {args.temporada}, mundlak = {args.mundlak}")
    for f in range(k):
        te = pliegue_fila == f
        jugadores_te = np.unique(d["jug_idx"][te])
        print(f"\nPliegue {f + 1}/{k}: {te.sum()} filas / {len(jugadores_te)} jugadores de prueba")
        t0 = time.time()
        d_tr, meta_tr = m03.subconjunto(d, meta, ~te)
        d_te, _ = m03.subconjunto(d, meta, te)
        modelo, _, usar_temporada = m02.construir_modelo(d_tr, meta_tr, args.grado_edad, args.temporada, "normal", mundlak=args.mundlak)
        with modelo:
            idata = pm.sample(draws=draws, tune=tune, chains=chains, target_accept=args.objetivo_aceptacion,
                              random_seed=m02.SEMILLA + f, progressbar=False, **kw)
        sin_alfa = [v for v in idata.posterior.data_vars if not v.startswith("alfa") and not v.endswith("_raw")]
        resumen = m02.resumen_compatible(az, idata, sin_alfa)
        c_rhat, c_ess = m02.columna(resumen, "r_hat", "rhat"), m02.columna(resumen, "ess_bulk")
        conv = {"pliegue": f, "rhat_max": float(resumen[c_rhat].max()) if c_rhat else np.nan,
                "ess_bulk_min": float(resumen[c_ess].min()) if c_ess else np.nan,
                "divergencias": int(idata.sample_stats["diverging"].sum())}
        convergencia.append(conv)
        dr = m03.extraer_draws(idata, usar_temporada, args.draws_evaluacion)
        mu = m03.mu_fijo_por_draw(dr, d_te, args.grado_edad, usar_temporada)  # (draws, filas del pliegue)
        mu_lineal[te] = mu.mean(axis=0) + meta["media_y"]
        elpd[jugadores_te] = m03.elpd_jugadores(d_te["y"], mu, d_te["jug_idx"], dr["sigma_alfa"], dr["sigma_eps"])
        aviso = "" if conv["rhat_max"] <= 1.01 and conv["divergencias"] == 0 else "  <-- revisar convergencia"
        print(f"  {time.time() - t0:5.0f}s  R-hat {conv['rhat_max']:.3f}  ESS min {conv['ess_bulk_min']:.0f}  div {conv['divergencias']}{aviso}")

    tabla = tabla_predicciones(d, meta, pliegue_fila, mu_lineal)
    tabla.to_csv(ruta_reports / f"{etiqueta}_predicciones.csv", index=False)
    pd.DataFrame({"jug_idx": np.arange(meta["n_jugadores"]), "elpd": elpd}).to_csv(
        ruta_reports / f"{etiqueta}_elpd_por_jugador.csv", index=False)
    pd.DataFrame(convergencia).to_csv(ruta_reports / f"{etiqueta}_convergencia_pliegues.csv", index=False)

    error = tabla["y_log"] - tabla["mu_lineal"]
    print(f"\nModelo lineal, jugadores nuevos: RMSE = {np.sqrt((error ** 2).mean()):.3f}, MAE = {error.abs().mean():.3f} (escala del log del valor)")
    print(f"ELPD total = {np.nansum(elpd):,.1f}")
    print(f"\nListo. Tablas en {ruta_reports}. Siguiente: nl02_referente_boosting.py --etiqueta {etiqueta}")


if __name__ == "__main__":
    main()
