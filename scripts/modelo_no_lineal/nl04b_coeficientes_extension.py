"""
nl04b (13/11/2026): COEFICIENTES de la extension de nl04, ajustando con TODOS los datos.

nl04 mostro que agregar `pocos_minutos x rendimiento` mejora la prediccion de jugadores nuevos
(+591 ELPD, 16 SE). Aca se ajusta UNA vez el modelo con todas las filas y se responde la pregunta
que importa para interpretarlo: ¿cual es el efecto de cada variable de rendimiento en jugadores
con muchos minutos y en jugadores con pocos?

    pendiente_normal  = b_rend[v]                     (>= 450 minutos)
    pendiente_pocos   = b_rend[v] + b_inter[v]        (< 450 minutos, con estadistica observada)
    diferencia        = b_inter[v]

Todo en la escala original de la variable (se deshace la division por el desvio de nl04), con
media, desvio y intervalo del 94 % de la posterior. `razon` = pendiente_pocos / pendiente_normal
solo se informa cuando la pendiente normal es claramente distinta de 0 (|media| > 2 desvios);
si no, es inestable.

Con `--mundlak`, b_rend es el efecto DENTRO del jugador (igual que en m02/m03) y la interaccion
modifica ese mismo efecto en las filas con pocos minutos.

Las filas con estadistica imputada (0) no aportan a la interaccion: pocos_x_z vale 0 ahi. La
interaccion se activa solo en las filas con pocos minutos Y estadistica observada.

SALIDAS:
    reports/nl04b_coeficientes_extension/<etiqueta>_pendientes.csv
    reports/nl04b_coeficientes_extension/<etiqueta>_resumen_ajuste.csv

USO:
    uv run scripts/modelo_no_lineal/nl04b_coeficientes_extension.py --temporada rw --mundlak --objetivo-aceptacion 0.97 --tune 2000 --draws 2000 --etiqueta coef_rw_mun

Requiere: uv add pymc nutpie arviz
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_RAIZ_SCRIPTS = Path(__file__).resolve().parents[1]  # scripts/
for _carpeta in ("config", "dataset", "eda", "diagnosticos", "modelado", "modelo_no_lineal"):
    sys.path.insert(0, str(_RAIZ_SCRIPTS / _carpeta))

import nl04_extensiones_bayesianas as nl04  # noqa: E402


# ---------------------------------------------------------------------------
# Piezas puras (se prueban con datos sinteticos, sin PyMC)
# ---------------------------------------------------------------------------

def escalas_columnas(d, meta, paquetes):
    """Desvio de cada columna de extension (el mismo que usa construir_extensiones). {nombre: desvio}."""
    esc = {}
    for p in paquetes:
        X, nombres = nl04.columnas_paquete(d, meta, p)
        for j, n in enumerate(nombres):
            s = X[:, j].std()
            if s >= 1e-9:
                esc[f"{p}:{n}"] = float(s)
    return esc


def resumir(x):
    """Media, desvio e intervalo del 94 % de un vector de draws."""
    x = np.asarray(x, dtype=float)
    lo, hi = np.percentile(x, [3, 97])
    return {"media": float(x.mean()), "desvio": float(x.std(ddof=1)), "p3": float(lo), "p97": float(hi)}


def pendientes_por_variable(b_rend, b_atr, meta, nombres_ext, escalas):
    """
    `b_rend`: (S, n_rend); `b_atr`: (S, n_atr_original + n_ext). `nombres_ext`: nombres de las columnas
    de extension en el orden en que se agregaron a X_atr. Devuelve una fila por variable con interaccion.
    """
    n_orig = b_atr.shape[1] - len(nombres_ext)
    filas = []
    for j, nom in enumerate(nombres_ext):
        paquete, col = nom.split(":", 1)
        if paquete != "min_x_rend":
            continue
        variable = col.replace("pocos_x_", "", 1)
        if variable not in meta["cols_rend"]:
            continue
        inter = b_atr[:, n_orig + j] / escalas[nom]
        normal = b_rend[:, meta["cols_rend"].index(variable)]
        pocos = normal + inter
        r_n, r_p, r_i = resumir(normal), resumir(pocos), resumir(inter)
        razon = np.nan
        if abs(r_n["media"]) > 2 * r_n["desvio"]:
            razon = float(r_p["media"] / r_n["media"])
        filas.append({
            "variable": variable,
            "pendiente_normal": r_n["media"], "normal_p3": r_n["p3"], "normal_p97": r_n["p97"],
            "pendiente_pocos": r_p["media"], "pocos_p3": r_p["p3"], "pocos_p97": r_p["p97"],
            "diferencia": r_i["media"], "dif_p3": r_i["p3"], "dif_p97": r_i["p97"],
            "dif_distinta_de_0": bool(r_i["p3"] > 0 or r_i["p97"] < 0),
            "razon_pocos_sobre_normal": razon,
        })
    return pd.DataFrame(filas)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(description="nl04b: coeficientes de la extension pocos_minutos x rendimiento.")
    parser.add_argument("--paquetes", nargs="+", choices=nl04.PAQUETES, default=["min_x_rend"])
    parser.add_argument("--temporada", choices=["ninguno", "rw"], default="rw")
    parser.add_argument("--grado-edad", type=int, default=2)
    parser.add_argument("--mundlak", action="store_true")
    parser.add_argument("--etiqueta", default=None)
    parser.add_argument("--objetivo-aceptacion", type=float, default=0.95)
    parser.add_argument("--draws", type=int, default=1000)
    parser.add_argument("--tune", type=int, default=1000)
    parser.add_argument("--cadenas", type=int, default=4)
    parser.add_argument("--muestreador", choices=["pymc", "nutpie"], default="nutpie")
    args, desconocidos = parser.parse_known_args(argv)
    if desconocidos:
        raise SystemExit(f"Opciones no reconocidas: {desconocidos}. Revisar que el script este actualizado (ver --help).")
    if "min_x_rend" not in args.paquetes:
        raise SystemExit("nl04b interpreta las interacciones de min_x_rend: incluirlo en --paquetes.")

    import arviz as az
    import config
    import e08_poblacion_por_capa as e08
    import m02_modelo_base as m02
    import pymc as pm

    etiqueta = args.etiqueta or f"coef_{args.temporada}" + ("_mun" if args.mundlak else "")
    ruta_reports = config.ruta_reports_script(Path(__file__).stem)

    d, meta = m02.preparar_datos(e08.cargar_dataset_modelado())
    X_ext, nombres_ext = nl04.construir_extensiones(d, meta, args.paquetes)
    escalas = escalas_columnas(d, meta, args.paquetes)
    dm = nl04.con_extension(d, X_ext)

    modelo, _, _ = m02.construir_modelo(dm, meta, args.grado_edad, args.temporada, "normal", mundlak=args.mundlak)
    kw = {"nuts_sampler": "nutpie"} if args.muestreador == "nutpie" else {}
    print(f"\nAjuste con todas las filas ({len(dm['y'])} filas, {meta['n_jugadores']} jugadores), paquetes = {args.paquetes}")
    with modelo:
        idata = pm.sample(draws=args.draws, tune=args.tune, chains=args.cadenas, target_accept=args.objetivo_aceptacion,
                          random_seed=m02.SEMILLA, progressbar=False, **kw)

    sin_alfa = [v for v in idata.posterior.data_vars if not v.startswith("alfa") and not v.endswith("_raw")]
    resumen = m02.resumen_compatible(az, idata, sin_alfa)
    c_rhat, c_ess = m02.columna(resumen, "r_hat", "rhat"), m02.columna(resumen, "ess_bulk")
    conv = {"rhat_max": float(resumen[c_rhat].max()), "ess_bulk_min": float(resumen[c_ess].min()),
            "divergencias": int(idata.sample_stats["diverging"].sum())}
    pd.DataFrame([conv]).to_csv(ruta_reports / f"{etiqueta}_resumen_ajuste.csv", index=False)
    print(f"Convergencia: R-hat max {conv['rhat_max']:.3f}, ESS min {conv['ess_bulk_min']:.0f}, divergencias {conv['divergencias']}")

    post = idata.posterior
    b_rend = post["b_rend"].stack(s=("chain", "draw")).transpose("s", ...).to_numpy()
    b_atr = post["b_atr"].stack(s=("chain", "draw")).transpose("s", ...).to_numpy()
    tabla = pendientes_por_variable(b_rend, b_atr, meta, nombres_ext, escalas)
    tabla.to_csv(ruta_reports / f"{etiqueta}_pendientes.csv", index=False)

    print("\nPendiente de cada variable de rendimiento (escala original; intervalo 94 %):")
    with pd.option_context("display.width", 220, "display.float_format", "{:.3f}".format):
        print(tabla[["variable", "pendiente_normal", "normal_p3", "normal_p97", "pendiente_pocos", "pocos_p3", "pocos_p97",
                     "diferencia", "dif_distinta_de_0", "razon_pocos_sobre_normal"]].to_string(index=False))
    print("\nLectura: 'normal' = 450 minutos o mas; 'pocos' = menos de 450 con estadistica observada. "
          "La razon solo se informa si la pendiente normal es claramente distinta de 0.")
    print(f"\nListo. Tablas en {ruta_reports}.")


if __name__ == "__main__":
    main()
