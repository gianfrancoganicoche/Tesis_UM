"""
m03 (01/11/2026): contraste de H1 con validacion cruzada AGRUPADA POR JUGADOR.

H1: el contexto de equipo y liga explica valor de mercado de los sub-23 mas alla de
la curva de edad (y del resto de las covariables). Se contrasta comparando, con las
mismas filas y los mismos pliegues, el modelo completo de m02 contra el mismo
modelo SIN el bloque de contexto (4 variables):

    delta_ELPD = ELPD(completo) - ELPD(sin contexto)      (> 0 favorece al contexto)

POR QUE NO LOO POR FILA: muchos jugadores tienen una sola fila, y sacarla cambia
mucho alfa_i (Pareto-k alto, ver m02). Aca se deja afuera JUGADORES enteros: se
reparten en K pliegues, se ajusta con K-1 y se evalua sobre los jugadores
retenidos. Es la pregunta que importa: predecir el valor de un jugador NUEVO.

DENSIDAD PREDICTIVA DE UN JUGADOR NUEVO: su efecto alfa_i no se conoce, asi que
se integra. Para un jugador con n filas, el vector de log-valores es normal
multivariado con media mu_fija (todo el predictor menos alfa_i), varianza
sigma_eps^2 en la diagonal y sigma_alfa^2 fuera de ella (simetria compuesta).
Se promedia la densidad sobre los draws posteriores (log-media-exp). La unidad
de evaluacion es el JUGADOR, no la fila.

SE DE LA DIFERENCIA: sqrt(J) * desvio de las diferencias por jugador (J =
jugadores). Regla: |delta| > 2*SE se considera diferencia clara.

OTROS BLOQUES: `--quitar ctx rend atr` compara tambien contra el modelo sin ese
bloque (cada uno cuesta K ajustes mas).

NOTAS: (1) la estandarizacion de covariables se hizo con toda la muestra
(preparar_datos de m02); es un detalle menor: no usa y. (2) Solo
verosimilitud normal. (3) Para sacar un bloque se reemplaza por una columna de
ceros; su coeficiente queda en el prior y no afecta la prediccion.

SALIDAS:
    reports/m03_contraste_h1/<etiqueta>_elpd_por_jugador.csv
    reports/m03_contraste_h1/<etiqueta>_comparacion.csv
    reports/m03_contraste_h1/<etiqueta>_convergencia_pliegues.csv

USO:
    uv run scripts/modelado/m03_contraste_h1.py --rapido             # prueba de humo
    uv run scripts/modelado/m03_contraste_h1.py                      # K=5, 1000/1000, 4 cadenas
    uv run scripts/modelado/m03_contraste_h1.py --temporada rw --etiqueta h1_rw

Requiere: uv add pymc nutpie arviz
"""

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.special import logsumexp

_RAIZ_SCRIPTS = Path(__file__).resolve().parents[1]  # scripts/
for _carpeta in ("config", "dataset", "eda", "diagnosticos", "modelado"):
    sys.path.insert(0, str(_RAIZ_SCRIPTS / _carpeta))

BLOQUES = {"ctx": "X_ctx", "rend": "X_rend", "atr": "X_atr"}
SEMILLA_PLIEGUES = 2026


# ---------------------------------------------------------------------------
# Piezas puras (se prueban con datos sinteticos, sin PyMC)
# ---------------------------------------------------------------------------

def asignar_pliegues(jug_idx, k, semilla=SEMILLA_PLIEGUES):
    """Pliegue (0..k-1) de cada FILA; todas las filas de un jugador van al mismo pliegue."""
    jugadores = np.unique(jug_idx)
    orden = np.random.default_rng(semilla).permutation(jugadores)
    pliegue_de = {int(j): i % k for i, j in enumerate(orden)}
    return np.array([pliegue_de[int(j)] for j in jug_idx])


def subconjunto(d, meta, mascara):
    """Recorta las filas del diccionario del modelo y reindexa los jugadores a 0..J-1."""
    uniq, nuevo = np.unique(d["jug_idx"][mascara], return_inverse=True)
    sub = {k: v[mascara] for k, v in d.items() if k != "df"}
    sub["jug_idx"] = nuevo
    return sub, {**meta, "n_jugadores": int(len(uniq))}


def quitar_bloque(d, bloque):
    """Reemplaza un bloque de covariables por una columna de ceros (queda sin efecto)."""
    clave = BLOQUES[bloque]
    out = dict(d)
    out[clave] = np.zeros((len(d["y"]), 1))
    return out


def logp_jugadores(y, mu_fija, jug_idx, sigma_alfa, sigma_eps):
    """
    Log-densidad de cada jugador (vector de sus filas) bajo normal multivariada de
    simetria compuesta: media mu_fija, Cov = s_e^2 I + s_a^2 11'.
    `y`, `mu_fija`: (filas,). `jug_idx`: 0..J-1. Devuelve (J,).
    """
    J = int(jug_idx.max()) + 1
    n = np.bincount(jug_idx, minlength=J).astype(float)
    r = y - mu_fija
    sr = np.bincount(jug_idx, weights=r, minlength=J)
    sr2 = np.bincount(jug_idx, weights=r * r, minlength=J)
    se2, sa2 = sigma_eps ** 2, sigma_alfa ** 2
    denom = se2 + n * sa2
    logdet = (n - 1) * np.log(se2) + np.log(denom)
    cuad = (sr2 - sa2 / denom * sr ** 2) / se2
    return -0.5 * (n * np.log(2 * np.pi) + logdet + cuad)


def elpd_jugadores(y, mu_por_draw, jug_idx, sigma_alfa, sigma_eps):
    """
    ELPD por jugador. `mu_por_draw`: (S, filas); `sigma_*`: (S,).
    Promedia la densidad sobre los draws (log-media-exp).
    """
    S = mu_por_draw.shape[0]
    L = np.vstack([logp_jugadores(y, mu_por_draw[s], jug_idx, sigma_alfa[s], sigma_eps[s]) for s in range(S)])
    return logsumexp(L, axis=0) - np.log(S)


def comparar(elpd_a, elpd_b):
    """delta = a - b por jugador; devuelve total, SE y la regla de 2 SE."""
    dif = np.asarray(elpd_a) - np.asarray(elpd_b)
    J = len(dif)
    total = float(dif.sum())
    se = float(np.sqrt(J) * dif.std(ddof=1))
    return {"delta_elpd": total, "se": se, "delta_sobre_se": total / se if se > 0 else np.nan,
            "jugadores": J, "diferencia_clara": bool(abs(total) > 2 * se)}


# ---------------------------------------------------------------------------
# Ajuste por pliegue
# ---------------------------------------------------------------------------

def extraer_draws(idata, usar_temporada, n_max):
    """Draws posteriores (submuestreados) con el draw en el primer eje."""
    post = idata.posterior
    nombres = ["intercepto", "nivel_pos", "b_edad", "dev_edad", "b_ctx", "b_rend", "b_atr", "sigma_alfa", "sigma_eps"]
    if usar_temporada:
        nombres.append("gamma")
    salida = {}
    for nombre in nombres:
        salida[nombre] = post[nombre].stack(s=("chain", "draw")).transpose("s", ...).to_numpy()
    S = salida["intercepto"].shape[0]
    idx = np.linspace(0, S - 1, min(n_max, S)).astype(int)
    return {k: v[idx] for k, v in salida.items()}


def mu_fijo_por_draw(draws, d_te, grado_edad, usar_temporada):
    """Predictor sin alfa_i para cada draw: (S, filas del pliegue)."""
    import m02_modelo_base as m02

    P_edad = m02.potencias_edad(d_te["edad"], grado_edad)
    d_sin_jug = {**d_te, "jug_idx": np.zeros(len(d_te["y"]), dtype=int)}
    S = draws["intercepto"].shape[0]
    mu = np.empty((S, len(d_te["y"])))
    for s in range(S):
        p = {k: draws[k][s] for k in ("intercepto", "nivel_pos", "b_edad", "dev_edad", "b_ctx", "b_rend", "b_atr")}
        p["alfa"] = np.zeros(1)
        if usar_temporada:
            p["gamma"] = draws["gamma"][s]
        mu[s] = m02.predictor_lineal(p, d_sin_jug, P_edad, usar_temporada)
    return mu


def ajustar_y_evaluar(d_tr, meta_tr, d_te, args, etiqueta_modelo, pliegue):
    import arviz as az
    import pymc as pm
    import m02_modelo_base as m02

    modelo, _, usar_temporada = m02.construir_modelo(d_tr, meta_tr, args.grado_edad, args.temporada, "normal")
    tune, draws, chains = (500, 500, 2) if args.rapido else (1000, 1000, 4)
    tune, draws, chains = args.tune or tune, args.draws or draws, args.cadenas or chains
    kw = {"nuts_sampler": "nutpie"} if args.muestreador == "nutpie" else {}
    with modelo:
        idata = pm.sample(draws=draws, tune=tune, chains=chains, target_accept=args.objetivo_aceptacion,
                          random_seed=m02.SEMILLA + pliegue, progressbar=False, **kw)
    sin_alfa = [v for v in idata.posterior.data_vars if not v.startswith("alfa") and not v.endswith("_raw")]
    resumen = m02.resumen_compatible(az, idata, sin_alfa)
    c_rhat = m02.columna(resumen, "r_hat", "rhat")
    c_ess = m02.columna(resumen, "ess_bulk")
    conv = {"pliegue": pliegue, "modelo": etiqueta_modelo,
            "rhat_max": float(resumen[c_rhat].max()) if c_rhat else np.nan,
            "ess_bulk_min": float(resumen[c_ess].min()) if c_ess else np.nan,
            "divergencias": int(idata.sample_stats["diverging"].sum())}
    dr = extraer_draws(idata, usar_temporada, args.draws_evaluacion)
    mu = mu_fijo_por_draw(dr, d_te, args.grado_edad, usar_temporada)
    elpd = elpd_jugadores(d_te["y"], mu, d_te["jug_idx"], dr["sigma_alfa"], dr["sigma_eps"])
    return elpd, conv


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(description="m03: contraste de H1 con validacion cruzada agrupada por jugador.")
    parser.add_argument("--rapido", action="store_true", help="500/500, 2 cadenas, K=3 (prueba de humo).")
    parser.add_argument("--k", type=int, default=None, help="Pliegues (por defecto 5; 3 con --rapido).")
    parser.add_argument("--quitar", nargs="+", choices=list(BLOQUES), default=["ctx"],
                        help="Bloques a sacar, uno por modelo de comparacion (por defecto: ctx = contexto, el de H1).")
    parser.add_argument("--temporada", choices=["ninguno", "rw"], default="ninguno")
    parser.add_argument("--grado-edad", type=int, default=2)
    parser.add_argument("--etiqueta", default=None)
    parser.add_argument("--objetivo-aceptacion", type=float, default=0.95)
    parser.add_argument("--draws", type=int, default=None)
    parser.add_argument("--tune", type=int, default=None)
    parser.add_argument("--cadenas", type=int, default=None)
    parser.add_argument("--draws-evaluacion", type=int, default=400, help="Draws usados para evaluar cada pliegue.")
    parser.add_argument("--muestreador", choices=["pymc", "nutpie"], default="nutpie")
    args, _ = parser.parse_known_args(argv)

    import config
    import e08_poblacion_por_capa as e08
    import m02_modelo_base as m02

    k = args.k or (3 if args.rapido else 5)
    etiqueta = args.etiqueta or f"h1_{args.temporada}_k{k}"
    ruta_reports = config.ruta_reports_script(Path(__file__).stem)

    d, meta = m02.preparar_datos(e08.cargar_dataset_modelado())
    pliegue_fila = asignar_pliegues(d["jug_idx"], k)
    modelos = {"completo": d, **{f"sin_{b}": quitar_bloque(d, b) for b in args.quitar}}
    print(f"\nContraste H1: {k} pliegues por jugador, modelos = {list(modelos)}, temporada = {args.temporada}")

    elpd = {nombre: np.full(meta["n_jugadores"], np.nan) for nombre in modelos}
    convergencia = []
    for f in range(k):
        te = pliegue_fila == f
        jugadores_te = np.unique(d["jug_idx"][te])
        print(f"\nPliegue {f + 1}/{k}: {te.sum()} filas / {len(jugadores_te)} jugadores de prueba")
        for nombre, dm in modelos.items():
            t0 = time.time()
            d_tr, meta_tr = subconjunto(dm, meta, ~te)
            d_te, _ = subconjunto(dm, meta, te)
            e, conv = ajustar_y_evaluar(d_tr, meta_tr, d_te, args, nombre, f)
            elpd[nombre][jugadores_te] = e  # subconjunto reindexa con np.unique: mismo orden que jugadores_te
            convergencia.append(conv)
            aviso = "" if conv["rhat_max"] <= 1.01 and conv["divergencias"] == 0 else "  <-- revisar convergencia"
            print(f"  {nombre:<12s} {time.time() - t0:5.0f}s  R-hat {conv['rhat_max']:.3f}  "
                  f"ESS min {conv['ess_bulk_min']:.0f}  div {conv['divergencias']}{aviso}")

    por_jugador = pd.DataFrame({"jug_idx": np.arange(meta["n_jugadores"]), **elpd})
    por_jugador["player_id"] = np.unique(d["df"]["player_id"].to_numpy())
    por_jugador.to_csv(ruta_reports / f"{etiqueta}_elpd_por_jugador.csv", index=False)
    pd.DataFrame(convergencia).to_csv(ruta_reports / f"{etiqueta}_convergencia_pliegues.csv", index=False)

    filas = []
    for nombre in modelos:
        if nombre == "completo":
            continue
        r = comparar(elpd["completo"], elpd[nombre])
        filas.append({"completo_menos": nombre, **r,
                      "elpd_completo": float(np.nansum(elpd["completo"])), "elpd_otro": float(np.nansum(elpd[nombre]))})
    comp = pd.DataFrame(filas)
    comp.to_csv(ruta_reports / f"{etiqueta}_comparacion.csv", index=False)

    print("\nResultado (delta_ELPD = completo - sin el bloque; > 0 favorece al bloque):")
    with pd.option_context("display.width", 200, "display.float_format", "{:,.2f}".format):
        print(comp.to_string(index=False))
    h1 = comp[comp["completo_menos"] == "sin_ctx"]
    if len(h1):
        r = h1.iloc[0]
        if r["diferencia_clara"] and r["delta_elpd"] > 0:
            print("\nH1: el contexto mejora la prediccion de jugadores nuevos (|delta| > 2 SE).")
        elif r["diferencia_clara"]:
            print("\nH1: el modelo SIN contexto predice mejor (|delta| > 2 SE): revisar.")
        else:
            print("\nH1: sin diferencia clara (|delta| <= 2 SE) entre con y sin contexto.")
    print(f"\nListo. Tablas en {ruta_reports}.")


if __name__ == "__main__":
    main()
