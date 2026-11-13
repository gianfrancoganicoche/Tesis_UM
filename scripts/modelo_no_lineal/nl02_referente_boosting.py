"""
nl02 (13/11/2026): referente NO LINEAL -- gradient boosting -- contra el modelo lineal bayesiano,
sobre las mismas filas y los mismos pliegues por jugador.

PREGUNTA (tutor): el valor de un jugador es comportamiento humano y quiza no sea lineal.
Un modelo mucho mas flexible, ¿predice jugadores NUEVOS bastante mejor que el lineal?
Si no lo hace, la forma lineal no es una limitacion relevante para predecir. Si lo hace,
se mira donde (nl03) y se lleva esa flexibilidad al modelo bayesiano (splines, interacciones).

ATENCION -- FUGA DE LA VARIABLE DEPENDIENTE (hallazgo del 13/11/2026): companieros_valor_promedio es el promedio
de los valores de los companeros SIN el propio jugador (leave-one-out): (T - v_i)/(N-1), con T el valor total
del plantel y N sus jugadores. Dentro de un club-temporada, T y N son los mismos para todos, asi que la variable
queda ligada de forma mecanica al valor propio v_i. Un modelo lineal casi no puede usarlo, pero uno flexible puede
reconocer el club-temporada con las otras variables de contexto (iguales para todo el plantel), aprender T de los
companeros que estan en entrenamiento y despejar v_i. Por eso este script tiene --excluir-variables: la
comparacion que importa para la pregunta de no linealidad es la que NO usa esa variable (y, como segundo control,
la que no usa ningun contexto).

COMO SE HACE JUSTO:
  * mismas filas (m02.preparar_datos) y mismos pliegues (m03.asignar_pliegues, semilla 2026):
    todas las filas de un jugador van al mismo pliegue;
  * el boosting NO ve alfa_i ni al jugador: igual que el lineal, predice un jugador nuevo;
  * mismas variables: edad, posicion (categorica), temporada (anio, numerica), contexto,
    rendimiento y atributos. Con --medias-jugador se agregan los promedios por jugador
    (equivalente al Mundlak del lineal; usar solo si nl01 se corrio con --mundlak);
  * los hiperparametros se eligen SOLO con los datos de entrenamiento de cada pliegue
    (validacion cruzada interna agrupada por jugador), nunca con el pliegue de prueba.

QUE SE REPORTA: RMSE, MAE y R2 de ambos modelos en jugadores nuevos, y la diferencia de error
cuadratico medio por jugador (con su error estandar y la regla de 2 SE). Referencia: el lineal
no puede bajar de sqrt(sigma_alfa^2 + sigma_eps^2) ~ 1.0 en RMSE, porque alfa_i de un jugador
nuevo no se conoce; una mejora grande del boosting seria una mejora sobre esa base.

USO:
    uv run scripts/modelo_no_lineal/nl02_referente_boosting.py --etiqueta lineal_rw
    uv run scripts/modelo_no_lineal/nl02_referente_boosting.py --etiqueta lineal_rw --rapido

Lee reports/nl01_predicciones_lineal/<etiqueta>_predicciones.csv.
SALIDAS (reports/nl02_referente_boosting/):
    <etiqueta>_predicciones.csv, <etiqueta>_metricas.csv, <etiqueta>_comparacion.csv, <etiqueta>_hiperparametros.csv

Requiere: scikit-learn (ya esta en pyproject.toml)
"""

import argparse
import itertools
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_RAIZ_SCRIPTS = Path(__file__).resolve().parents[1]  # scripts/
for _carpeta in ("config", "dataset", "eda", "diagnosticos", "modelado", "modelo_no_lineal"):
    sys.path.insert(0, str(_RAIZ_SCRIPTS / _carpeta))

GRILLA = {
    "learning_rate": [0.05],
    "max_iter": [150, 400],
    "max_leaf_nodes": [8, 31],
    "min_samples_leaf": [50, 200],
    "l2_regularization": [0.0, 1.0],
}
GRILLA_RAPIDA = {"learning_rate": [0.1], "max_iter": [100], "max_leaf_nodes": [8, 31], "min_samples_leaf": [100]}


# ---------------------------------------------------------------------------
# Piezas puras (se prueban con datos sinteticos, sin PyMC)
# ---------------------------------------------------------------------------

def columnas_a_excluir(columnas, excluir):
    """
    Nombres de columnas a sacar. Cada elemento de `excluir` puede ser un bloque (ctx, rend, atr: saca
    todas sus columnas y sus promedios por jugador) o el nombre de una variable (ej. companieros_valor_promedio).
    """
    fuera = set()
    for token in excluir:
        for c in columnas:
            sin_mun = c[4:] if c.startswith("mun_") else c
            if token in ("ctx", "rend", "atr"):
                if sin_mun.startswith(token + "_"):
                    fuera.add(c)
            elif sin_mun.split("_", 1)[-1] == token:
                fuera.add(c)
    desconocidos = [t for t in excluir if not any(
        (t in ("ctx", "rend", "atr") and (c[4:] if c.startswith("mun_") else c).startswith(t + "_"))
        or (c[4:] if c.startswith("mun_") else c).split("_", 1)[-1] == t for c in columnas)]
    if desconocidos:
        raise ValueError(f"No es un bloque ni una variable del boosting: {desconocidos}")
    return sorted(fuera)


def construir_features(d, meta, medias_jugador=False, excluir=()):
    """DataFrame de variables para el boosting (mismas filas y orden que `d`)."""
    X = pd.DataFrame({"edad": d["edad"]})
    X["posicion"] = d["pos_idx"].astype(int)
    X["anio"] = np.asarray(meta["temporadas"])[d["temp_idx"]].astype(float)
    bloques = [("ctx", "X_ctx", "cols_ctx"), ("rend", "X_rend", "cols_rend"), ("atr", "X_atr", "cols_atr")]
    for pref, clave, cols in bloques:
        for j, nombre in enumerate(meta[cols]):
            X[f"{pref}_{nombre}"] = d[clave][:, j]
    if medias_jugador:
        base = X[[c for c in X.columns if c.startswith(("ctx_", "rend_"))]]
        medias = base.groupby(d["jug_idx"]).transform("mean")
        medias.columns = [f"mun_{c}" for c in medias.columns]
        X = pd.concat([X, medias], axis=1)
    if excluir:
        X = X.drop(columns=columnas_a_excluir(list(X.columns), excluir))
    return X


def combinaciones(grilla):
    claves = list(grilla)
    return [dict(zip(claves, valores)) for valores in itertools.product(*(grilla[c] for c in claves))]


def elegir_hiperparametros(X, y, grupos, grilla, k_interno=3, semilla=2026):
    """Mejor combinacion por RMSE con CV interna agrupada por jugador, SOLO con datos de entrenamiento."""
    from sklearn.ensemble import HistGradientBoostingRegressor
    from sklearn.model_selection import GroupKFold

    categorica = [c == "posicion" for c in X.columns]
    mejor, mejor_rmse = None, np.inf
    for params in combinaciones(grilla):
        errores = []
        for tr, va in GroupKFold(n_splits=k_interno).split(X, y, grupos):
            m = HistGradientBoostingRegressor(categorical_features=categorica, early_stopping=False,
                                              random_state=semilla, **params)
            m.fit(X.iloc[tr], y[tr])
            errores.append(((y[va] - m.predict(X.iloc[va])) ** 2).mean())
        rmse = float(np.sqrt(np.mean(errores)))
        if rmse < mejor_rmse:
            mejor, mejor_rmse = params, rmse
    return mejor, mejor_rmse


def predecir_por_pliegue(X, y, jug_idx, pliegue_fila, grilla, semilla=2026):
    """Boosting fuera de muestra: ajusta con los demas pliegues y predice el pliegue retenido."""
    from sklearn.ensemble import HistGradientBoostingRegressor

    categorica = [c == "posicion" for c in X.columns]
    pred = np.full(len(y), np.nan)
    filas = []
    for f in np.unique(pliegue_fila):
        te = pliegue_fila == f
        tr = ~te
        params, rmse_interno = elegir_hiperparametros(X[tr].reset_index(drop=True), y[tr], jug_idx[tr], grilla, semilla=semilla)
        m = HistGradientBoostingRegressor(categorical_features=categorica, early_stopping=False,
                                          random_state=semilla, **params)
        m.fit(X[tr], y[tr])
        pred[te] = m.predict(X[te])
        filas.append({"pliegue": int(f), "rmse_interno": rmse_interno, **params})
    return pred, pd.DataFrame(filas)


def metricas(y, pred):
    e = y - pred
    return {"rmse": float(np.sqrt((e ** 2).mean())), "mae": float(np.abs(e).mean()),
            "r2": float(1 - (e ** 2).sum() / ((y - y.mean()) ** 2).sum())}


def comparar_error(y, pred_a, pred_b, jug_idx):
    """
    Compara dos modelos con el error cuadratico medio POR JUGADOR (la unidad es el jugador, no la
    fila). delta = ECM(a) - ECM(b) promedio entre jugadores: > 0 favorece a b. SE = sd / sqrt(J).
    """
    J = int(jug_idx.max()) + 1
    n = np.bincount(jug_idx, minlength=J).astype(float)
    ecm_a = np.bincount(jug_idx, weights=(y - pred_a) ** 2, minlength=J) / n
    ecm_b = np.bincount(jug_idx, weights=(y - pred_b) ** 2, minlength=J) / n
    dif = ecm_a - ecm_b
    delta, se = float(dif.mean()), float(dif.std(ddof=1) / np.sqrt(J))
    return {"delta_ecm": delta, "se": se, "delta_sobre_se": delta / se if se > 0 else np.nan, "jugadores": J,
            "pct_jugadores_mejora_b": float((dif > 0).mean()), "diferencia_clara": bool(abs(delta) > 2 * se)}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(description="nl02: referente de gradient boosting contra el modelo lineal.")
    parser.add_argument("--etiqueta", required=True, help="Etiqueta de nl01 (lee sus predicciones).")
    parser.add_argument("--medias-jugador", action="store_true", dest="medias_jugador",
                        help="Agrega promedios por jugador (usar solo si nl01 se corrio con --mundlak).")
    parser.add_argument("--excluir-variables", nargs="+", default=[], dest="excluir_variables",
                        help="Variables (o bloques ctx/rend/atr) que el boosting NO usa. Para el control de fuga: "
                             "companieros_valor_promedio, o ctx. Correr nl01 con las mismas exclusiones (--quitar-variable / --quitar-contexto).")
    parser.add_argument("--rapido", action="store_true", help="Grilla minima (prueba de humo).")
    args, desconocidos = parser.parse_known_args(argv)
    if desconocidos:
        raise SystemExit(f"Opciones no reconocidas: {desconocidos}. Revisar que el script este actualizado (ver --help).")

    import config
    import e08_poblacion_por_capa as e08
    import m02_modelo_base as m02

    ruta_nl01 = config.ruta_reports_script("nl01_predicciones_lineal") / f"{args.etiqueta}_predicciones.csv"
    if not ruta_nl01.exists():
        raise SystemExit(f"No existe {ruta_nl01}: correr primero nl01 con --etiqueta {args.etiqueta}.")
    ruta_reports = config.ruta_reports_script(Path(__file__).stem)

    d, meta = m02.preparar_datos(e08.cargar_dataset_modelado(), verbose=False)
    lin = pd.read_csv(ruta_nl01)
    df = d["df"].reset_index(drop=True)
    y = d["y"] + meta["media_y"]
    if len(lin) != len(y) or not np.allclose(lin["y_log"].to_numpy(), y) or not (lin["player_id"].to_numpy() == df["player_id"].to_numpy()).all():
        raise SystemExit("Las filas de nl01 no coinciden con el dataset actual (¿cambio el dataset o los filtros?). Volver a correr nl01.")
    pliegue_fila = lin["pliegue"].to_numpy()

    X = construir_features(d, meta, args.medias_jugador, args.excluir_variables)
    if args.excluir_variables:
        print(f"Variables excluidas del boosting: {args.excluir_variables}")
    print(f"Variables del boosting: {X.shape[1]} ({', '.join(X.columns[:6])}, ...)")
    grilla = GRILLA_RAPIDA if args.rapido else GRILLA
    print(f"Grilla: {len(combinaciones(grilla))} combinaciones x CV interna de 3 pliegues, por cada uno de {len(np.unique(pliegue_fila))} pliegues.")
    pred_nl, hiper = predecir_por_pliegue(X, y, d["jug_idx"], pliegue_fila, grilla)

    pred_lin = lin["mu_lineal"].to_numpy()
    filas = []
    for nombre, p in (("lineal_bayesiano", pred_lin), ("boosting", pred_nl)):
        filas.append({"modelo": nombre, "pliegue": "todos", **metricas(y, p)})
        for f in np.unique(pliegue_fila):
            m = pliegue_fila == f
            filas.append({"modelo": nombre, "pliegue": int(f), **metricas(y[m], p[m])})
    tabla_met = pd.DataFrame(filas)
    comp = comparar_error(y, pred_lin, pred_nl, d["jug_idx"])
    rm_lin, rm_nl = tabla_met.query("modelo == 'lineal_bayesiano' and pliegue == 'todos'")["rmse"].iloc[0], tabla_met.query("modelo == 'boosting' and pliegue == 'todos'")["rmse"].iloc[0]
    comp["rmse_lineal"], comp["rmse_boosting"], comp["mejora_rmse_pct"] = rm_lin, rm_nl, 100 * (rm_lin - rm_nl) / rm_lin

    pd.DataFrame({"fila": lin["fila"], "player_id": lin["player_id"], "season": lin["season"], "pliegue": pliegue_fila,
                  "y_log": y, "mu_lineal": pred_lin, "mu_boosting": pred_nl}).to_csv(ruta_reports / f"{args.etiqueta}_predicciones.csv", index=False)
    tabla_met.to_csv(ruta_reports / f"{args.etiqueta}_metricas.csv", index=False)
    pd.DataFrame([comp]).to_csv(ruta_reports / f"{args.etiqueta}_comparacion.csv", index=False)
    hiper.to_csv(ruta_reports / f"{args.etiqueta}_hiperparametros.csv", index=False)

    print("\nJugadores nuevos, todos los pliegues (escala del log del valor):")
    with pd.option_context("display.width", 200, "display.float_format", "{:,.3f}".format):
        print(tabla_met[tabla_met["pliegue"] == "todos"].to_string(index=False))
        print("\nPor pliegue (RMSE):")
        print(tabla_met[tabla_met["pliegue"] != "todos"].pivot(index="pliegue", columns="modelo", values="rmse").to_string())
    print(f"\nDiferencia de error cuadratico medio por jugador (lineal - boosting): {comp['delta_ecm']:+.4f} (SE {comp['se']:.4f}, "
          f"{comp['delta_sobre_se']:.1f} SE); el boosting mejora al {100 * comp['pct_jugadores_mejora_b']:.0f}% de los jugadores; "
          f"RMSE {rm_lin:.3f} -> {rm_nl:.3f} ({comp['mejora_rmse_pct']:+.1f}%).")
    print("Diferencia clara (|delta| > 2 SE)." if comp["diferencia_clara"] else "Diferencia NO clara (|delta| <= 2 SE).")
    print(f"\nListo. Tablas en {ruta_reports}.")


if __name__ == "__main__":
    main()
