"""
nl03 (13/11/2026): DONDE y POR QUE el modelo no lineal predice mejor que el lineal.

Parte de las predicciones de nl01 (lineal) y nl02 (boosting). Cuatro piezas:

 1. ERROR POR SEGMENTO: posicion, edad, minutos (pocos_minutos), temporada. Muestra en que tipo de
    jugador el boosting le gana al lineal (RMSE de cada uno y diferencia de error cuadratico
    medio por jugador con su SE).
 2. VARIANTES DEL BOOSTING: separa NO LINEALIDAD de INTERACCIONES, con los mismos hiperparametros:
      completo              cualquier interaccion entre variables;
      aditivo               sin interacciones (cada variable aporta una curva propia: es un GAM);
      posicion_x_variable   cada variable puede interactuar solo con la posicion.
    Si el aditivo ya recupera casi toda la mejora, el lineal pierde curvas. Si hace falta
    posicion_x_variable, pierde efectos distintos por posicion (por ejemplo goles en delanteros).
    Si solo el completo mejora, hay interacciones mas complejas.
 3. IMPORTANCIA POR PERMUTACION en los jugadores retenidos (aumento del error cuadratico medio al
    mezclar una variable o un bloque de variables).
 4. DEPENDENCIA PARCIAL por posicion de las variables mas importantes: cuanto cambia el valor
    predicho al mover una variable de su percentil 10 al 90, para cada posicion.

Usa los mismos pliegues y las mismas variables que nl02: pasar los mismos --excluir-variables y
--medias-jugador. Verifica que reproduce las predicciones del boosting de nl02 (si no coinciden,
aborta: los flags no son los mismos).

USO:
    uv run scripts/modelo_no_lineal/nl03_diagnostico_no_lineal.py --etiqueta lineal_rw_sin_ctx --excluir-variables ctx
    uv run scripts/modelo_no_lineal/nl03_diagnostico_no_lineal.py --etiqueta humo_sin_comp --excluir-variables companieros_valor_promedio

Lee reports/nl01_predicciones_lineal/<etiqueta>_predicciones.csv y reports/nl02_referente_boosting/<etiqueta>_{predicciones,hiperparametros}.csv.
SALIDAS: reports/nl03_diagnostico_no_lineal/<etiqueta>_{segmentos,variantes,importancia,dependencia_parcial,efecto_por_posicion}.csv
         reports/figuras/nl03_diagnostico_no_lineal/<etiqueta>_{importancia,dependencia_parcial}.png
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_RAIZ_SCRIPTS = Path(__file__).resolve().parents[1]  # scripts/
for _carpeta in ("config", "dataset", "eda", "diagnosticos", "modelado", "modelo_no_lineal"):
    sys.path.insert(0, str(_RAIZ_SCRIPTS / _carpeta))

import nl02_referente_boosting as nl02  # noqa: E402

BLOQUES_IMPORTANCIA = {
    "edad_posicion_temporada": lambda c: c in ("edad", "posicion", "anio"),
    "rendimiento": lambda c: c.startswith("rend_"),
    "atributos": lambda c: c.startswith("atr_"),
    "contexto": lambda c: c.startswith("ctx_") or c.startswith("mun_ctx_"),
    "promedios_jugador": lambda c: c.startswith("mun_"),
}


# ---------------------------------------------------------------------------
# Piezas puras (se prueban con datos sinteticos)
# ---------------------------------------------------------------------------

def etiquetas_segmentos(d, meta, X):
    """Etiqueta de segmento por fila para cada criterio disponible."""
    seg = {"posicion": pd.Series(np.asarray(meta["posiciones"])[d["pos_idx"]])}
    edad = np.floor(d["edad"]).astype(int)
    seg["edad"] = pd.Series(np.where(edad <= 17, "17 o menos", np.where(edad >= 22, "22 o mas", edad.astype(str))))
    if "rend_pocos_minutos" in X.columns:
        seg["minutos"] = pd.Series(np.where(X["rend_pocos_minutos"].to_numpy() > 0.5, "menos de 450 min", "450 min o mas"))
    seg["temporada"] = pd.Series(X["anio"].astype(int).astype(str).to_numpy())
    return seg


def tabla_segmentos(y, pred_lin, pred_nl, jug_idx, etiquetas):
    filas = []
    for criterio, serie in etiquetas.items():
        valores = serie.to_numpy()
        for valor in sorted(pd.unique(valores)):
            m = valores == valor
            if m.sum() < 30 or len(np.unique(jug_idx[m])) < 10:
                continue
            _, j = np.unique(jug_idx[m], return_inverse=True)
            comp = nl02.comparar_error(y[m], pred_lin[m], pred_nl[m], j)
            rl, rn = nl02.metricas(y[m], pred_lin[m])["rmse"], nl02.metricas(y[m], pred_nl[m])["rmse"]
            filas.append({"criterio": criterio, "segmento": valor, "filas": int(m.sum()), "jugadores": comp["jugadores"],
                          "rmse_lineal": rl, "rmse_boosting": rn, "mejora_rmse_pct": 100 * (rl - rn) / rl,
                          "delta_ecm": comp["delta_ecm"], "se": comp["se"], "delta_sobre_se": comp["delta_sobre_se"]})
    return pd.DataFrame(filas)


def restricciones_interaccion(columnas, variante):
    """`interaction_cst` de HistGradientBoostingRegressor para cada variante (None = sin restriccion)."""
    n = len(columnas)
    if variante == "completo":
        return None
    if variante == "aditivo":
        return [[i] for i in range(n)]
    if variante == "posicion_x_variable":
        p = columnas.index("posicion")
        return [[p]] + [[p, j] for j in range(n) if j != p]
    raise ValueError(variante)


def ajustar_pliegues(X, y, pliegue_fila, params_por_pliegue, variante="completo", semilla=2026):
    """Boosting fuera de muestra con hiperparametros dados por pliegue. Devuelve (pred, {pliegue: modelo})."""
    from sklearn.ensemble import HistGradientBoostingRegressor

    columnas = list(X.columns)
    # La variante completa trata la posicion como categorica (igual que nl02). Con restricciones de interaccion
    # scikit-learn rinde mal con variables categoricas (probado: RMSE 1.13 contra 1.01 con la posicion como
    # codigo numerico), asi que las variantes restringidas usan la posicion como codigo 0..3.
    categorica = [c == "posicion" for c in columnas] if variante == "completo" else None
    cst = restricciones_interaccion(columnas, variante)
    pred, modelos = np.full(len(y), np.nan), {}
    for f in np.unique(pliegue_fila):
        te = pliegue_fila == f
        m = HistGradientBoostingRegressor(categorical_features=categorica, interaction_cst=cst, early_stopping=False,
                                          random_state=semilla, **params_por_pliegue[int(f)])
        m.fit(X[~te], y[~te])
        pred[te] = m.predict(X[te])
        modelos[int(f)] = m
    return pred, modelos


def importancia_permutacion(X, y, pliegue_fila, modelos, repeticiones=5, semilla=2026):
    """Aumento del error cuadratico medio (en % del error base) al mezclar cada variable y cada bloque."""
    rng = np.random.default_rng(semilla)
    columnas = list(X.columns)
    grupos = {c: [c] for c in columnas}
    for nombre, regla in BLOQUES_IMPORTANCIA.items():
        cols = [c for c in columnas if regla(c)]
        if cols:
            grupos[f"[bloque] {nombre}"] = cols
    filas = []
    for f, modelo in modelos.items():
        te = pliegue_fila == f
        Xt, yt = X[te].reset_index(drop=True), y[te]
        base = float(((yt - modelo.predict(Xt)) ** 2).mean())
        for nombre, cols in grupos.items():
            aumentos = []
            for _ in range(repeticiones):
                Xp = Xt.copy()
                orden = rng.permutation(len(Xt))
                Xp[cols] = Xt[cols].to_numpy()[orden]
                aumentos.append(float(((yt - modelo.predict(Xp)) ** 2).mean()) - base)
            filas.append({"pliegue": f, "variable": nombre, "aumento_ecm": np.mean(aumentos), "ecm_base": base, "filas": int(te.sum())})
    df = pd.DataFrame(filas)
    resumen = df.groupby("variable").apply(
        lambda g: pd.Series({"aumento_ecm": np.average(g["aumento_ecm"], weights=g["filas"]),
                             "aumento_pct": 100 * np.average(g["aumento_ecm"], weights=g["filas"]) / np.average(g["ecm_base"], weights=g["filas"])}),
        include_groups=False).reset_index()
    return resumen.sort_values("aumento_ecm", ascending=False).reset_index(drop=True)


def dependencia_parcial(X, pliegue_fila, modelos, variables, posiciones_fila, nombres_posicion, n_grilla=9):
    """
    Dependencia parcial promediada en los pliegues: valor predicho medio al fijar una variable en cada punto de
    una grilla de percentiles 5-95, para todas las filas ("todas") y para cada posicion por separado.
    """
    filas = []
    for var in variables:
        grilla = np.unique(np.percentile(X[var], np.linspace(5, 95, n_grilla)))
        for etiqueta, mascara_pos in [("todas", np.ones(len(X), bool))] + [(n, posiciones_fila == n) for n in nombres_posicion]:
            for g in grilla:
                vals = []
                for f, modelo in modelos.items():
                    m = (pliegue_fila == f) & mascara_pos
                    if m.sum() < 20:
                        continue
                    Xg = X[m].copy()
                    Xg[var] = g
                    vals.append((modelo.predict(Xg).mean(), m.sum()))
                if vals:
                    filas.append({"variable": var, "posicion": etiqueta, "valor": float(g),
                                  "pd": float(np.average([v for v, _ in vals], weights=[w for _, w in vals]))})
    return pd.DataFrame(filas)


def efecto_p10_p90(pd_tabla, X, variables, posiciones_fila):
    """Cambio del valor predicho (log) al pasar la variable del percentil 10 al 90, por posicion."""
    filas = []
    for var in variables:
        for pos, g in pd_tabla[pd_tabla["variable"] == var].groupby("posicion"):
            g = g.sort_values("valor")
            if len(g) < 3:
                continue
            m = np.ones(len(X), bool) if pos == "todas" else posiciones_fila == pos
            p10, p90 = np.percentile(X.loc[m, var], [10, 90])
            filas.append({"variable": var, "posicion": pos, "p10": p10, "p90": p90,
                          "efecto_p10_a_p90": float(np.interp(p90, g["valor"], g["pd"]) - np.interp(p10, g["valor"], g["pd"]))})
    return pd.DataFrame(filas)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(description="nl03: diagnostico de donde y por que el boosting mejora al lineal.")
    parser.add_argument("--etiqueta", required=True, help="Etiqueta de nl01/nl02.")
    parser.add_argument("--excluir-variables", nargs="+", default=[], dest="excluir_variables")
    parser.add_argument("--medias-jugador", action="store_true", dest="medias_jugador")
    parser.add_argument("--variables-pdp", type=int, default=6, dest="variables_pdp", help="Cuantas variables (las mas importantes) graficar.")
    args, desconocidos = parser.parse_known_args(argv)
    if desconocidos:
        raise SystemExit(f"Opciones no reconocidas: {desconocidos}. Revisar que el script este actualizado (ver --help).")

    import config
    import e08_poblacion_por_capa as e08
    import m02_modelo_base as m02

    ruta_nl02 = config.ruta_reports_script("nl02_referente_boosting")
    arch_pred, arch_hip = ruta_nl02 / f"{args.etiqueta}_predicciones.csv", ruta_nl02 / f"{args.etiqueta}_hiperparametros.csv"
    for a in (arch_pred, arch_hip):
        if not a.exists():
            raise SystemExit(f"No existe {a}: correr primero nl01 y nl02 con --etiqueta {args.etiqueta}.")
    ruta_reports = config.ruta_reports_script(Path(__file__).stem)
    ruta_fig = config.ruta_figuras_script(Path(__file__).stem)

    d, meta = m02.preparar_datos(e08.cargar_dataset_modelado(), verbose=False)
    pred = pd.read_csv(arch_pred)
    y = d["y"] + meta["media_y"]
    if len(pred) != len(y) or not np.allclose(pred["y_log"].to_numpy(), y):
        raise SystemExit("Las filas de nl02 no coinciden con el dataset actual. Volver a correr nl01 y nl02.")
    pliegue_fila, pred_lin, pred_nl = pred["pliegue"].to_numpy(), pred["mu_lineal"].to_numpy(), pred["mu_boosting"].to_numpy()

    X = nl02.construir_features(d, meta, args.medias_jugador, args.excluir_variables)
    hip = pd.read_csv(arch_hip)
    enteros = {"max_iter", "max_leaf_nodes", "min_samples_leaf"}
    params = {int(r["pliegue"]): {k: (int(r[k]) if k in enteros else float(r[k])) for k in hip.columns if k not in ("pliegue", "rmse_interno")}
              for _, r in hip.iterrows()}

    print(f"Variables: {X.shape[1]}. Reajustando el boosting de nl02 para verificar...")
    pred_comp, modelos = ajustar_pliegues(X, y, pliegue_fila, params, "completo")
    if not np.allclose(pred_comp, pred_nl, atol=1e-5):
        raise SystemExit(f"No reproduzco las predicciones de nl02 (dif. maxima {np.abs(pred_comp - pred_nl).max():.2e}): "
                         "los flags --excluir-variables / --medias-jugador deben ser los mismos que en nl02.")

    # 1. segmentos
    seg = tabla_segmentos(y, pred_lin, pred_nl, d["jug_idx"], etiquetas_segmentos(d, meta, X))
    seg.to_csv(ruta_reports / f"{args.etiqueta}_segmentos.csv", index=False)

    # 2. variantes
    resultados = {"lineal_bayesiano": pred_lin, "completo": pred_comp}
    for v in ("aditivo", "posicion_x_variable"):
        resultados[v], _ = ajustar_pliegues(X, y, pliegue_fila, params, v)
    m_lin = nl02.metricas(y, pred_lin)["rmse"]
    m_comp = nl02.metricas(y, pred_comp)["rmse"]
    filas = []
    for nombre, p in resultados.items():
        met = nl02.metricas(y, p)
        comp = nl02.comparar_error(y, pred_lin, p, d["jug_idx"]) if nombre != "lineal_bayesiano" else {}
        filas.append({"variante": nombre, **met, "mejora_vs_lineal_pct": 100 * (m_lin - met["rmse"]) / m_lin,
                      "parte_de_la_mejora_del_completo_pct": 100 * (m_lin - met["rmse"]) / (m_lin - m_comp) if m_lin > m_comp else np.nan,
                      "delta_ecm_vs_lineal": comp.get("delta_ecm", np.nan), "se": comp.get("se", np.nan)})
    var_tabla = pd.DataFrame(filas)
    var_tabla.to_csv(ruta_reports / f"{args.etiqueta}_variantes.csv", index=False)

    # 3. importancia
    imp = importancia_permutacion(X, y, pliegue_fila, modelos)
    imp.to_csv(ruta_reports / f"{args.etiqueta}_importancia.csv", index=False)

    # 4. dependencia parcial por posicion
    posiciones_fila = np.asarray(meta["posiciones"])[d["pos_idx"]]
    candidatas = [v for v in imp["variable"] if not v.startswith("[bloque]") and v not in ("posicion",)]
    top = candidatas[: args.variables_pdp]
    dp = dependencia_parcial(X, pliegue_fila, modelos, top, posiciones_fila, list(meta["posiciones"]))
    dp.to_csv(ruta_reports / f"{args.etiqueta}_dependencia_parcial.csv", index=False)
    efecto = efecto_p10_p90(dp, X, top, posiciones_fila)
    efecto.to_csv(ruta_reports / f"{args.etiqueta}_efecto_por_posicion.csv", index=False)

    # figuras
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        try:
            import estilo_graficos as estilo
            estilo.aplicar_estilo()
        except Exception:
            pass
        sel = imp.head(15).iloc[::-1]
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.barh(sel["variable"], sel["aumento_pct"])
        ax.set_xlabel("Aumento del error cuadratico medio al mezclar la variable (%)")
        fig.tight_layout()
        fig.savefig(ruta_fig / f"{args.etiqueta}_importancia.png", dpi=150)
        plt.close(fig)
        n = len(top)
        cols = 3
        fig, axes = plt.subplots(int(np.ceil(n / cols)), cols, figsize=(12, 3.6 * int(np.ceil(n / cols))), squeeze=False)
        for ax, var in zip(axes.ravel(), top):
            for pos, g in dp[dp["variable"] == var].groupby("posicion"):
                g = g.sort_values("valor")
                ax.plot(g["valor"], g["pd"], lw=2.5 if pos == "todas" else 1.4, color="black" if pos == "todas" else None, label=pos)
            ax.set_title(var, fontsize=9)
        axes.ravel()[0].legend(fontsize=7)
        for ax in axes.ravel()[n:]:
            ax.axis("off")
        fig.supylabel("Log del valor predicho")
        fig.tight_layout()
        fig.savefig(ruta_fig / f"{args.etiqueta}_dependencia_parcial.png", dpi=150)
        plt.close(fig)
    except Exception as e:  # las figuras son un extra
        print(f"AVISO: no se pudieron generar las figuras ({e!r}).")

    with pd.option_context("display.width", 220, "display.float_format", "{:,.3f}".format, "display.max_columns", 20):
        print("\n=== Variantes (jugadores nuevos, escala del log del valor) ===")
        print(var_tabla[["variante", "rmse", "mae", "r2", "mejora_vs_lineal_pct", "parte_de_la_mejora_del_completo_pct", "delta_ecm_vs_lineal", "se"]].to_string(index=False))
        print("\n=== Error por segmento (mejora del boosting sobre el lineal) ===")
        print(seg[["criterio", "segmento", "filas", "jugadores", "rmse_lineal", "rmse_boosting", "mejora_rmse_pct", "delta_sobre_se"]].to_string(index=False))
        print("\n=== Importancia por permutacion (top 15) ===")
        print(imp.head(15).to_string(index=False))
        print("\n=== Efecto de pasar del percentil 10 al 90, por posicion (log del valor predicho) ===")
        print(efecto.pivot(index="variable", columns="posicion", values="efecto_p10_a_p90").to_string())
    print(f"\nListo. Tablas en {ruta_reports}, figuras en {ruta_fig}.")


if __name__ == "__main__":
    main()
