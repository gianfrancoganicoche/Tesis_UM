"""
Modelo base (m02, 10/10/2026): primer ajuste de la Alternativa 3 en PyMC, ANTES
de cualquier chequeo de Alan. Es la referencia contra la que se comparan los
puntos 8 (efecto temporal), 3 (porteros), 9 (autorregresivo) y 1 (vendedor).

    log_valor_it = intercepto + nivel_posicion[pos_i]
                 + curva_edad(edad_it; pos_i)            (polinomio, ver abajo)
                 + contexto_it + rendimiento_it + atributos_i
                 + alfa_i                                 (efecto de jugador)
                 + [gamma_t]                              (efecto temporada, opcional)
                 + eps_it

POBLACION: capa 3 (es_poblacion_h1: sub-23 en primera division europea), sin las
filas sin posicion (la interaccion edad x posicion las necesita; 6.9% de la capa).
Decisiones tomadas con Gianfranco el 10/10 (ver plan del proyecto):

  * FALTANTES DE RENDIMIENTO: se mantienen todas las filas. Las 6 variables z se
    rellenan con 0 (el promedio del z-score) donde faltan, y se agrega el
    indicador `pocos_minutos` (minutos_totales < 450), porque el faltante es una
    funcion de los minutos (que si se observan). Ademas, `z_edad_debut` y
    `z_goles_recibidos_ajustados_90` tienen otro mecanismo de faltante (no es
    solo el piso de minutos), asi que cada una lleva su propio indicador
    `falta_<variable>`.
  * Faltantes en contexto, altura, pie_habil y es_comunitario (<= ~7% cada uno):
    se descartan esas filas y se informa cuantas (la cascada de filas se imprime).
  * Efecto temporada: por defecto NINGUNO (B0 del plan). `--temporada rw` lo
    agrega como random walk con prior suave (B1), para reusar este script en m03.
  * Verosimilitud normal por defecto; `--verosimilitud t` usa Student-t (A4).

CURVA DE EDAD: polinomio de grado `--grado-edad` (por defecto 2) en
x = (edad - 20) / 2, con coeficientes comunes + desvios por posicion (jerarquicos,
encogidos hacia 0). Los desvios por posicion son la parte de H2. La edad de la
capa 3 va de ~15 a 23 anios, un rango corto donde un polinomio de grado 2 alcanza;
si los residuos por edad piden mas flexibilidad se sube el grado o se pasa a splines.

PRIORS (todas las covariables estandarizadas con la muestra del modelo; y en
log-euros, centrado en su media):
    intercepto ~ Normal(media_y, 2)      coeficientes ~ Normal(0, 0.5)
    sigma_alfa, sigma_eps ~ HalfNormal(1)    desvios por posicion ~ HalfNormal(0.5)

SALIDAS:
    outputs/modelado/m02_modelo_base/<etiqueta>.nc            traza (con log-verosimilitud para LOO)
    outputs/modelado/m02_modelo_base/<etiqueta>_escalas.json  medias y desvios para des-estandarizar
    reports/m02_modelo_base/<etiqueta>_resumen_parametros.csv, _residuos_por_temporada.csv,
        _residuos_por_posicion.csv, _autocorrelacion_residual.csv, _diagnosticos.csv
    reports/figuras/m02_modelo_base/<etiqueta>_curva_edad.png, _residuos_temporada.png, _ppc.png

USO:
    uv run scripts/modelado/m02_modelo_base.py --rapido          # 500/500, 2 cadenas: prueba de humo
    uv run scripts/modelado/m02_modelo_base.py                   # 1000/1000, 4 cadenas
    uv run scripts/modelado/m02_modelo_base.py --temporada rw --etiqueta b1_rw

Requiere: uv add pymc arviz
"""

import argparse
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

_RAIZ_SCRIPTS = Path(__file__).resolve().parents[1]  # scripts/
for _carpeta in ("config", "dataset", "eda", "diagnosticos"):
    sys.path.insert(0, str(_RAIZ_SCRIPTS / _carpeta))

import config
import estilo_graficos as estilo

COL_JUGADOR = "player_id"
COL_TEMPORADA = "season"
COL_EDAD = "edad"
COL_POSICION = "posicion_amplia_predominante"
COL_DV = "log_valor_mercado"
COL_MINUTOS = "minutos_totales"
FLAG_POBLACION = "es_poblacion_h1"

UMBRAL_POCOS_MINUTOS = 450
EDAD_CENTRO, EDAD_ESCALA = 20.0, 2.0

CONTEXTO = ["pca_exito_deportivo", "companieros_valor_promedio", "formaciones_distintas", "fase_maxima_alcanzada"]
RENDIMIENTO_Z = [
    "z_goles_90", "z_asistencias_90", "z_participacion_produccion",
    "z_goles_recibidos_ajustados_90", "z_edad_debut", "z_amarillas_90",
]
# Tarjeta roja (31/10/2026): dummy 0/1 (>=1 roja en la temporada), entra sin estandarizar.
REND_BINARIAS = ["tuvo_roja"]
CON_INDICADOR_PROPIO = ["z_edad_debut", "z_goles_recibidos_ajustados_90"]
ATRIBUTOS_NUM = ["z_altura_cm", "es_comunitario"]
PIE = "pie_habil"

SEMILLA = 2026


# ---------------------------------------------------------------------------
# Preparacion de datos (pura: se prueba con datos sinteticos)
# ---------------------------------------------------------------------------

def a_binaria(serie):
    """es_comunitario llega con tipos mezclados (bool / texto / numero): se pasa a 0/1/NaN."""
    mapa = {"true": 1.0, "false": 0.0, "1": 1.0, "0": 0.0, "1.0": 1.0, "0.0": 0.0}
    return serie.astype(str).str.strip().str.lower().map(mapa)


def estandarizar(serie, media=None, desvio=None):
    media = serie.mean() if media is None else media
    desvio = serie.std(ddof=0) if desvio is None else desvio
    desvio = desvio if desvio and desvio > 0 else 1.0
    return (serie - media) / desvio, float(media), float(desvio)


def preparar_datos(dataset, verbose=True):
    """
    Devuelve (d, meta): `d` es un diccionario de arrays listos para el modelo y
    `meta` los nombres/escalas. Imprime la cascada de filas.
    """
    cascada = []

    def paso(nombre, df):
        cascada.append((nombre, len(df), df[COL_JUGADOR].nunique()))

    df = dataset.copy()
    paso("dataset completo", df)
    df = df[df[FLAG_POBLACION].fillna(False).astype(bool)]
    paso("capa 3 (sub-23, primera division europea)", df)
    df = df[df[COL_POSICION].notna()]
    paso("sin las filas sin posicion", df)
    df = df[df[COL_DV].notna() & df[COL_EDAD].notna()]
    paso("con DV y edad", df)

    df = df.copy()
    df["es_comunitario"] = a_binaria(df["es_comunitario"])
    obligatorias = CONTEXTO + ["z_altura_cm", "es_comunitario", PIE]
    df = df.dropna(subset=obligatorias)
    paso("sin faltantes en contexto/altura/pie/comunitario", df)
    df = df.reset_index(drop=True)

    # --- Rendimiento: indicadores ANTES de rellenar -----------------------
    if COL_MINUTOS in df.columns:
        sin_minutos = df[COL_MINUTOS].isna().sum()
        if sin_minutos:
            print(f"AVISO: {sin_minutos} filas sin {COL_MINUTOS}: se tratan como NO pocos_minutos.")
        pocos = (df[COL_MINUTOS] < UMBRAL_POCOS_MINUTOS).astype(float)
    else:
        raise KeyError(f"Falta {COL_MINUTOS}: e08.cargar_dataset_modelado() lo trae de dataset_modelable.")
    indicadores = {"pocos_minutos": pocos}
    for v in CON_INDICADOR_PROPIO:
        indicadores[f"falta_{v}"] = df[v].isna().astype(float)
    rend = pd.concat([df[RENDIMIENTO_Z].fillna(0.0), df[REND_BINARIAS].astype(float).fillna(0.0)], axis=1)

    # --- Estandarizacion (contexto, altura) -------------------------------
    escalas = {}
    ctx = {}
    for c in CONTEXTO:
        ctx[c], m, s = estandarizar(df[c])
        escalas[c] = {"media": m, "desvio": s}
    atr = {}
    atr["z_altura_cm"], m, s = estandarizar(df["z_altura_cm"])
    escalas["z_altura_cm"] = {"media": m, "desvio": s}
    atr["es_comunitario"] = df["es_comunitario"].astype(float)

    pie_dummies = pd.get_dummies(df[PIE].astype(str), prefix="pie").astype(float)
    referencia = pie_dummies.sum().idxmax()
    pie_dummies = pie_dummies.drop(columns=[referencia])
    for c in pie_dummies.columns:
        atr[c] = pie_dummies[c]

    X_ctx = pd.DataFrame(ctx)
    X_rend = pd.concat([rend.reset_index(drop=True), pd.DataFrame(indicadores)], axis=1)
    X_atr = pd.DataFrame(atr)

    # --- Indices -----------------------------------------------------------
    posiciones = sorted(df[COL_POSICION].unique())
    jugadores, jug_idx = np.unique(df[COL_JUGADOR].to_numpy(), return_inverse=True)
    temporadas = np.sort(df[COL_TEMPORADA].unique())
    temp_idx = np.searchsorted(temporadas, df[COL_TEMPORADA].to_numpy())
    pos_idx = np.searchsorted(posiciones, df[COL_POSICION].to_numpy())

    y = df[COL_DV].to_numpy(dtype=float)
    media_y = float(y.mean())

    d = {
        "df": df,
        "y": y - media_y,
        "edad": df[COL_EDAD].to_numpy(dtype=float),
        "X_ctx": X_ctx.to_numpy(dtype=float),
        "X_rend": X_rend.to_numpy(dtype=float),
        "X_atr": X_atr.to_numpy(dtype=float),
        "pos_idx": pos_idx,
        "jug_idx": jug_idx,
        "temp_idx": temp_idx,
    }
    meta = {
        "media_y": media_y,
        "posiciones": [str(p) for p in posiciones],
        "temporadas": [int(t) for t in temporadas],
        "n_jugadores": int(len(jugadores)),
        "cols_ctx": list(X_ctx.columns),
        "cols_rend": list(X_rend.columns),
        "cols_atr": list(X_atr.columns),
        "pie_referencia": str(referencia),
        "escalas": escalas,
        "cascada": [{"paso": n, "filas": f, "jugadores": j} for n, f, j in cascada],
    }
    if verbose:
        print("\nCascada de filas:")
        for n, f, j in cascada:
            print(f"  {n:<55s} {f:>7d} filas  {j:>6d} jugadores")
        print(f"  pocos_minutos (<{UMBRAL_POCOS_MINUTOS}): {pocos.mean():.1%} de las filas del modelo")
        print(f"  pie_habil: referencia = {referencia}")
    return d, meta


# ---------------------------------------------------------------------------
# Modelo
# ---------------------------------------------------------------------------

def potencias_edad(edad, grado):
    x = (np.asarray(edad, dtype=float) - EDAD_CENTRO) / EDAD_ESCALA
    return np.column_stack([x ** k for k in range(1, grado + 1)])


def predictor_lineal(p, d, P_edad, usar_temporada):
    """
    Media del modelo. Escrita una sola vez para que sirva tanto con tensores de
    PyMC (construccion del modelo) como con arrays de numpy (residuos con las
    medias posteriores; el modelo es lineal en los parametros, asi que la media
    posterior del predictor es el predictor evaluado en las medias).
    """
    mu = p["intercepto"] + p["nivel_pos"][d["pos_idx"]]
    curva = (P_edad * (p["b_edad"][None, :] + p["dev_edad"][d["pos_idx"], :])).sum(axis=1)
    mu = mu + curva
    mu = mu + d["X_ctx"] @ p["b_ctx"] + d["X_rend"] @ p["b_rend"] + d["X_atr"] @ p["b_atr"]
    mu = mu + p["alfa"][d["jug_idx"]]
    if usar_temporada:
        mu = mu + p["gamma"][d["temp_idx"]]
    return mu


def construir_modelo(d, meta, grado_edad, temporada, verosimilitud):
    import pymc as pm

    n_pos = len(meta["posiciones"])
    n_jug = meta["n_jugadores"]
    n_temp = len(meta["temporadas"])
    P_edad = potencias_edad(d["edad"], grado_edad)
    usar_temporada = temporada == "rw"

    with pm.Model() as modelo:
        intercepto = pm.Normal("intercepto", 0.0, 2.0)
        sigma_nivel = pm.HalfNormal("sigma_nivel_pos", 0.5)
        nivel_raw = pm.Normal("nivel_pos_raw", 0.0, 1.0, shape=n_pos)
        nivel_pos = pm.Deterministic("nivel_pos", sigma_nivel * nivel_raw)

        b_edad = pm.Normal("b_edad", 0.0, 0.5, shape=grado_edad)
        sigma_dev = pm.HalfNormal("sigma_dev_edad", 0.5, shape=grado_edad)
        dev_raw = pm.Normal("dev_edad_raw", 0.0, 1.0, shape=(n_pos, grado_edad))
        dev_edad = pm.Deterministic("dev_edad", dev_raw * sigma_dev[None, :])

        b_ctx = pm.Normal("b_ctx", 0.0, 0.5, shape=d["X_ctx"].shape[1])
        b_rend = pm.Normal("b_rend", 0.0, 0.5, shape=d["X_rend"].shape[1])
        b_atr = pm.Normal("b_atr", 0.0, 0.5, shape=d["X_atr"].shape[1])

        sigma_alfa = pm.HalfNormal("sigma_alfa", 1.0)
        alfa_raw = pm.Normal("alfa_raw", 0.0, 1.0, shape=n_jug)
        alfa = pm.Deterministic("alfa", sigma_alfa * alfa_raw)

        params = {
            "intercepto": intercepto, "nivel_pos": nivel_pos, "b_edad": b_edad, "dev_edad": dev_edad,
            "b_ctx": b_ctx, "b_rend": b_rend, "b_atr": b_atr, "alfa": alfa,
        }
        if usar_temporada:
            sigma_rw = pm.HalfNormal("sigma_rw", 0.1)
            pasos = pm.Normal("pasos_rw", 0.0, 1.0, shape=n_temp - 1)
            camino = pm.math.concatenate([pm.math.zeros(1), pm.math.cumsum(sigma_rw * pasos)])
            gamma = pm.Deterministic("gamma", camino - camino.mean())
            params["gamma"] = gamma

        mu = predictor_lineal(params, d, P_edad, usar_temporada)
        sigma_eps = pm.HalfNormal("sigma_eps", 1.0)
        if verosimilitud == "t":
            nu = pm.Gamma("nu", alpha=2.0, beta=0.1)
            pm.StudentT("y", nu=nu, mu=mu, sigma=sigma_eps, observed=d["y"])
        else:
            pm.Normal("y", mu=mu, sigma=sigma_eps, observed=d["y"])
    return modelo, P_edad, usar_temporada


def medias_posteriores(idata, usar_temporada):
    post = idata.posterior
    def m(nombre):
        return post[nombre].mean(dim=("chain", "draw")).to_numpy()
    p = {k: m(k) for k in ("intercepto", "nivel_pos", "b_edad", "dev_edad", "b_ctx", "b_rend", "b_atr", "alfa")}
    if usar_temporada:
        p["gamma"] = m("gamma")
    return p


# ---------------------------------------------------------------------------
# Diagnosticos
# ---------------------------------------------------------------------------

def prueba_wooldridge(df_u, col_u="u"):
    """
    Prueba de correlacion serial para paneles con efecto de jugador (Wooldridge, 2002).
    `col_u` es el residuo SIN restar alfa_i (u = alfa_i + eps_it). Se regresa
    (u_t - u_{t-1}) sobre (u_{t-1} - u_{t-2}) sin constante, con temporadas
    consecutivas: alfa_i se cancela en las diferencias. Si eps es i.i.d. la
    pendiente es -0.5; mas cerca de 0 o positiva indica autocorrelacion positiva
    (rho implicado ~ 1 + 2*pendiente, en un AR(1) estacionario). Error estandar
    agrupado por jugador.

    NO se usa la correlacion simple del residuo con alfa_i restado: con pocas
    filas por jugador ese residuo queda negativamente correlacionado por
    construccion (alfa_i absorbe el promedio del jugador), aunque no haya
    dependencia temporal.
    """
    d = df_u[[COL_JUGADOR, COL_TEMPORADA, col_u]]
    clave = [COL_JUGADOR, COL_TEMPORADA]
    u1 = d.assign(**{COL_TEMPORADA: d[COL_TEMPORADA] + 1}).rename(columns={col_u: "u1"})
    u2 = d.assign(**{COL_TEMPORADA: d[COL_TEMPORADA] + 2}).rename(columns={col_u: "u2"})
    t = d.merge(u1, on=clave).merge(u2, on=clave)
    vacio = {"tripletas": int(len(t)), "jugadores": int(t[COL_JUGADOR].nunique()),
             "pendiente": np.nan, "se_agrupado": np.nan, "z_contra_menos_0.5": np.nan, "rho_implicado": np.nan}
    if len(t) < 30:
        return vacio
    dy = (t[col_u] - t["u1"]).to_numpy()
    dx = (t["u1"] - t["u2"]).to_numpy()
    beta = float((dx * dy).sum() / (dx ** 2).sum())
    e = dy - beta * dx
    por_jugador = pd.Series(dx * e).groupby(t[COL_JUGADOR].to_numpy()).sum()
    se = float(np.sqrt((por_jugador ** 2).sum()) / (dx ** 2).sum())
    return {**vacio, "pendiente": beta, "se_agrupado": se,
            "z_contra_menos_0.5": (beta + 0.5) / se, "rho_implicado": 1 + 2 * beta}


def resumen_residuos(df_res, por):
    g = df_res.groupby(por)["residuo"]
    return pd.DataFrame({
        "filas": g.size(), "residuo_medio": g.mean(), "residuo_sd": g.std(),
        "residuo_p05": g.quantile(0.05), "residuo_p95": g.quantile(0.95),
    }).reset_index()


def resumen_compatible(az, idata, var_names):
    """az.summary con intervalo de 94% en arviz 0.x (hdi_prob) y 1.x (ci_prob)."""
    for kw in ("hdi_prob", "ci_prob"):
        try:
            return az.summary(idata, var_names=var_names, **{kw: 0.94})
        except TypeError:
            continue
    return az.summary(idata, var_names=var_names)


def columna(resumen, *candidatas):
    """Primera columna existente (los nombres cambian entre versiones de arviz)."""
    for c in candidatas:
        if c in resumen.columns:
            return c
    return None


def curva_edad_posterior(idata, meta, grado_edad, grilla):
    """Curva de edad (sin intercepto de nivel) por posicion: media y HDI 94% sobre la grilla."""
    post = idata.posterior
    b = post["b_edad"].stack(s=("chain", "draw")).transpose("s", "b_edad_dim_0").to_numpy()
    dev = post["dev_edad"].stack(s=("chain", "draw")).transpose("s", "dev_edad_dim_0", "dev_edad_dim_1").to_numpy()
    niv = post["nivel_pos"].stack(s=("chain", "draw")).transpose("s", "nivel_pos_dim_0").to_numpy()
    P = potencias_edad(grilla, grado_edad)
    salida = {}
    for k, pos in enumerate(meta["posiciones"]):
        coef = b + dev[:, k, :]                  # (s, grado)
        curva = coef @ P.T + niv[:, [k]]         # (s, grilla)
        salida[pos] = (curva.mean(axis=0), np.percentile(curva, 3, axis=0), np.percentile(curva, 97, axis=0))
    return salida


def graficar_curva_edad(curvas, grilla, ruta):
    fig, ax = plt.subplots(figsize=(8, 5))
    colores = [estilo.COLOR_PRINCIPAL, estilo.COLOR_SECUNDARIO, "#0b0b0b", estilo.COLOR_NEUTRO]
    for (pos, (m, lo, hi)), c in zip(curvas.items(), colores * 2):
        ax.plot(grilla, m, label=pos, color=c)
        ax.fill_between(grilla, lo, hi, color=c, alpha=0.15)
    ax.set_xlabel("Edad")
    ax.set_ylabel("Efecto en log(valor) (nivel + curva)")
    ax.set_title("Curva de edad por posicion (media y HDI 94%)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(ruta, dpi=150)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(description="m02: modelo base jerarquico (PyMC).")
    parser.add_argument("--rapido", action="store_true", help="500 tune / 500 draws / 2 cadenas (prueba de humo).")
    parser.add_argument("--temporada", choices=["ninguno", "rw"], default="ninguno")
    parser.add_argument("--verosimilitud", choices=["normal", "t"], default="normal")
    parser.add_argument("--grado-edad", type=int, default=2)
    parser.add_argument("--etiqueta", default=None, help="Nombre de la corrida (por defecto segun las opciones).")
    parser.add_argument("--objetivo-aceptacion", type=float, default=0.9)
    args, _ = parser.parse_known_args(argv)

    import arviz as az
    import pymc as pm
    import e08_poblacion_por_capa as e08

    estilo.aplicar_estilo()
    etiqueta = args.etiqueta or f"base_{args.temporada}_{args.verosimilitud}_g{args.grado_edad}"
    ruta_reports = config.ruta_reports_script(Path(__file__).stem)
    ruta_figuras = config.ruta_figuras_script(Path(__file__).stem)
    ruta_traza = config.REPO_ROOT / "outputs" / "modelado" / Path(__file__).stem
    ruta_traza.mkdir(parents=True, exist_ok=True)

    dataset = e08.cargar_dataset_modelado()
    d, meta = preparar_datos(dataset)
    modelo, P_edad, usar_temporada = construir_modelo(d, meta, args.grado_edad, args.temporada, args.verosimilitud)

    tune, draws, chains = (500, 500, 2) if args.rapido else (1000, 1000, 4)
    print(f"\nMuestreo ({etiqueta}): {chains} cadenas x ({tune} tune + {draws} draws)...")
    with modelo:
        idata = pm.sample(
            draws=draws, tune=tune, chains=chains, target_accept=args.objetivo_aceptacion,
            random_seed=SEMILLA,
        )
        try:
            idata = pm.compute_log_likelihood(idata, model=modelo, progressbar=False)
        except Exception as exc:  # sin log-verosimilitud no hay LOO, pero el resto sigue
            print(f"AVISO: no se pudo calcular la log-verosimilitud ({type(exc).__name__}: {exc}).")

    # --- Convergencia -------------------------------------------------------
    sin_alfa = [v for v in idata.posterior.data_vars if not v.startswith("alfa") and not v.endswith("_raw")]
    resumen = resumen_compatible(az, idata, sin_alfa)
    resumen.to_csv(ruta_reports / f"{etiqueta}_resumen_parametros.csv")
    divergencias = int(idata.sample_stats["diverging"].sum())
    c_rhat = columna(resumen, "r_hat", "rhat")
    c_ess = columna(resumen, "ess_bulk")
    rhat_max = float(resumen[c_rhat].max()) if c_rhat else float("nan")
    ess_min = float(resumen[c_ess].min()) if c_ess else float("nan")
    print(f"\nConvergencia: R-hat max = {rhat_max:.3f}, ESS bulk min = {ess_min:.0f}, divergencias = {divergencias}")
    if rhat_max > 1.01 or divergencias > 0 or ess_min < 400:
        print("  ATENCION: la corrida no cumple los umbrales (R-hat <= 1.01, ESS >= 400, 0 divergencias). "
              "No interpretar los coeficientes sin revisar.")
    with pd.option_context("display.width", 200, "display.float_format", "{:,.3f}".format):
        print(resumen.to_string())

    # --- Ajuste: LOO ----------------------------------------------------------
    diag = {"etiqueta": etiqueta, "filas": len(d["y"]), "jugadores": meta["n_jugadores"],
            "rhat_max": rhat_max, "ess_bulk_min": ess_min, "divergencias": divergencias}
    try:
        loo = az.loo(idata)
        diag["elpd_loo"] = float(loo.elpd)
        diag["se_elpd_loo"] = float(loo.se)
        diag["p_loo"] = float(loo.p)
        pareto = np.asarray(loo.pareto_k)
        diag["pareto_k_gt_0.7"] = int((pareto > 0.7).sum())
        print(f"\nLOO: elpd = {diag['elpd_loo']:.1f} (SE {diag['se_elpd_loo']:.1f}), p_loo = {diag['p_loo']:.0f}, "
              f"Pareto-k > 0.7 en {diag['pareto_k_gt_0.7']} filas ({diag['pareto_k_gt_0.7'] / len(pareto):.1%})")
        if diag["pareto_k_gt_0.7"] / len(pareto) > 0.05:
            print("  NOTA: muchas filas con Pareto-k alto. Es esperable con muchos jugadores de una sola fila "
                  "(sacar la fila cambia mucho alfa_i): el LOO por fila no es confiable para comparar modelos. "
                  "Usar validacion cruzada agrupada por jugador (K-fold por player_id).")
    except Exception as exc:  # LOO depende de la version de arviz: no debe tirar abajo la corrida
        print(f"\nAVISO: no se pudo calcular LOO ({type(exc).__name__}: {exc}).")

    # --- Residuos ---------------------------------------------------------------
    p_medias = medias_posteriores(idata, usar_temporada)
    mu_hat = predictor_lineal(p_medias, d, P_edad, usar_temporada)
    df_res = d["df"][[COL_JUGADOR, COL_TEMPORADA, COL_POSICION, COL_EDAD]].copy()
    df_res["residuo"] = d["y"] - mu_hat
    por_temp = resumen_residuos(df_res, COL_TEMPORADA)
    por_pos = resumen_residuos(df_res, COL_POSICION)
    por_temp.to_csv(ruta_reports / f"{etiqueta}_residuos_por_temporada.csv", index=False)
    por_pos.to_csv(ruta_reports / f"{etiqueta}_residuos_por_posicion.csv", index=False)
    df_res["u"] = d["y"] - (mu_hat - p_medias["alfa"][d["jug_idx"]])  # residuo + alfa_i
    ac = prueba_wooldridge(df_res)
    pd.DataFrame([ac]).to_csv(ruta_reports / f"{etiqueta}_autocorrelacion_residual.csv", index=False)
    diag["residuo_sd"] = float(df_res["residuo"].std())
    diag.update({f"wooldridge_{k}": v for k, v in ac.items()})
    pd.DataFrame([diag]).to_csv(ruta_reports / f"{etiqueta}_diagnosticos.csv", index=False)

    print("\nResiduos por temporada (media, sd):")
    with pd.option_context("display.width", 200, "display.float_format", "{:,.3f}".format):
        print(por_temp[[COL_TEMPORADA, "filas", "residuo_medio", "residuo_sd"]].to_string(index=False))
        print("\nResiduos por posicion:")
        print(por_pos[[COL_POSICION, "filas", "residuo_medio", "residuo_sd"]].to_string(index=False))
    print(f"\nPrueba de correlacion serial de Wooldridge (punto 9, paso 1): {ac['tripletas']} tripletas de "
          f"temporadas consecutivas, {ac['jugadores']} jugadores.")
    if not np.isnan(ac["pendiente"]):
        print(f"  pendiente = {ac['pendiente']:.3f} (SE {ac['se_agrupado']:.3f}); sin autocorrelacion deberia ser -0.5 "
              f"(z contra -0.5 = {ac['z_contra_menos_0.5']:.1f}); rho implicado ~ {ac['rho_implicado']:.2f}.")
    else:
        print("  muy pocas tripletas para estimarla en esta capa: correrla sobre la capa 1 (m05).")

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.axhline(0, color=estilo.COLOR_NEUTRO)
    ax.errorbar(por_temp[COL_TEMPORADA], por_temp["residuo_medio"],
                yerr=por_temp["residuo_sd"] / np.sqrt(por_temp["filas"]) * 1.96,
                fmt="o-", color=estilo.COLOR_PRINCIPAL)
    ax.set_xlabel("Temporada")
    ax.set_ylabel("Residuo medio (IC 95% aprox.)")
    ax.set_title("Residuo medio por temporada")
    fig.tight_layout()
    fig.savefig(ruta_figuras / f"{etiqueta}_residuos_temporada.png", dpi=150)
    plt.close(fig)

    # --- Curva de edad -------------------------------------------------------------
    grilla = np.linspace(max(15.0, np.floor(d["edad"].min())), min(23.0, np.ceil(d["edad"].max())), 60)
    curvas = curva_edad_posterior(idata, meta, args.grado_edad, grilla)
    graficar_curva_edad(curvas, grilla, ruta_figuras / f"{etiqueta}_curva_edad.png")

    # --- Posterior predictive (submuestreado para no llenar la memoria) -------------
    sub = idata.posterior.isel(draw=slice(0, None, max(1, draws // 100)))
    with modelo:
        ppc = pm.sample_posterior_predictive(sub, var_names=["y"], random_seed=SEMILLA, progressbar=False)
    sim = ppc.posterior_predictive["y"].stack(s=("chain", "draw")).to_numpy()  # (filas, s)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    bins = np.linspace(d["y"].min() - 1, d["y"].max() + 1, 60)
    for j in range(min(sim.shape[1], 40)):
        ax.hist(sim[:, j], bins=bins, histtype="step", color=estilo.COLOR_NEUTRO, alpha=0.6)
    ax.hist(d["y"], bins=bins, histtype="step", color=estilo.COLOR_SECUNDARIO, linewidth=2, label="observado")
    ax.set_xlabel("log(valor) centrado")
    ax.set_title("Posterior predictive check (gris = simulaciones)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(ruta_figuras / f"{etiqueta}_ppc.png", dpi=150)
    plt.close(fig)

    # --- Guardado --------------------------------------------------------------------
    try:
        idata.to_netcdf(ruta_traza / f"{etiqueta}.nc")
    except Exception as exc:
        import pickle
        print(f"AVISO: no se pudo guardar .nc ({type(exc).__name__}); falta quiza `uv add h5netcdf`. Se guarda en pickle.")
        with open(ruta_traza / f"{etiqueta}.pkl", "wb") as f:
            pickle.dump(idata, f)
    with open(ruta_traza / f"{etiqueta}_escalas.json", "w", encoding="utf-8") as f:
        json.dump({k: v for k, v in meta.items()}, f, ensure_ascii=False, indent=2)

    print(f"\nListo. Tablas en {ruta_reports}, figuras en {ruta_figuras}, traza en {ruta_traza}.")
    return idata


if __name__ == "__main__":
    main()