"""
nl04 (13/11/2026): extensiones NO LINEALES dentro del modelo bayesiano, evaluadas por delta ELPD.

Sale de lo que mostro nl03 (boosting sin contexto): la ventaja del boosting viene sobre todo de
curvas por variable (56 %), algo de posicion x variable (12 puntos) y un tercio de interacciones
mas complejas. Aca se prueba, DENTRO del modelo bayesiano jerarquico (mismo m02, mismos pliegues
por jugador que m03/nl01), si agregar esas piezas mejora la prediccion de jugadores nuevos:

    delta_ELPD = ELPD(con extension) - ELPD(base)        (> 0 favorece a la extension)

PAQUETES (cada uno se agrega solo al modelo base; "todo" los agrega juntos):
  min_x_rend        pocos_minutos x cada variable continua de rendimiento (6 columnas). Hipotesis:
                    con pocos minutos el rendimiento por 90' es ruido y su efecto es distinto.
  spline_debut      spline lineal por tramos en z_edad_debut (nudos en los cuartiles de los valores
                    observados). El termino lineal ya esta en el modelo; se agregan los cambios de pendiente.
  spline_goles_rec  idem para z_goles_recibidos_ajustados_90.
  edad_cola         cambios de pendiente de la edad a los 21 y 22 anos (la curva de edad es cuadratica
                    por posicion; nl03 mostro un tramo mas empinado a los 21-22).

COMO SE IMPLEMENTA: las columnas nuevas se agregan al bloque `X_atr` del modelo (su coeficiente tiene
prior N(0, 0.5), igual que el resto). Cada columna se divide por su desvio (calculado en toda la
muestra, sin usar y), asi el prior es comparable entre columnas. NO SE TOCA m02 NI m03. Con
`--mundlak` las columnas nuevas no tienen promedio por jugador (los promedios Mundlak son los de siempre).

VALORES IMPUTADOS: z_edad_debut y z_goles_recibidos_ajustados_90 se rellenan con 0 cuando faltan
(hay un indicador `falta_*`). Las columnas de spline se multiplican por (1 - falta): una fila imputada
no aporta curvatura, solo su indicador. Para z_participacion_produccion no hay indicador de faltante, asi que NO se
le pone spline; el script imprime cuantas filas tienen exactamente 0 en cada variable (y cuantas son
pocos_minutos) para decidir si ese 0 mezcla imputados con observados.

LECTURA: |delta| > 2 SE = diferencia clara (misma regla que m03). Un delta chico o dentro de 2 SE
significa que esa curva/interaccion NO mejora la prediccion de jugadores nuevos: el lineal alcanza.
Ojo: cada paquete cuesta K ajustes del modelo; con 4 paquetes + todo + base son 6 modelos x K pliegues.

SALIDAS:
    reports/nl04_extensiones_bayesianas/<etiqueta>_elpd_por_jugador.csv
    reports/nl04_extensiones_bayesianas/<etiqueta>_comparacion.csv
    reports/nl04_extensiones_bayesianas/<etiqueta>_convergencia_pliegues.csv
    reports/nl04_extensiones_bayesianas/<etiqueta>_columnas_extension.csv   (que columnas tiene cada paquete)

USO:
    uv run scripts/modelo_no_lineal/nl04_extensiones_bayesianas.py --rapido --etiqueta humo_ext
    uv run scripts/modelo_no_lineal/nl04_extensiones_bayesianas.py --temporada rw --mundlak \
        --objetivo-aceptacion 0.97 --tune 2000 --draws 2000 --etiqueta ext_rw_mun

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

import m03_contraste_h1 as m03  # noqa: E402

PAQUETES = ["min_x_rend", "spline_debut", "spline_goles_rec", "edad_cola"]
Z_CONTINUAS = ["z_goles_90", "z_asistencias_90", "z_participacion_produccion",
               "z_goles_recibidos_ajustados_90", "z_edad_debut", "z_amarillas_90"]
CUANTILES_NUDOS = (0.25, 0.50, 0.75)
NUDOS_EDAD = (21.0, 22.0)


# ---------------------------------------------------------------------------
# Piezas puras (se prueban con datos sinteticos, sin PyMC)
# ---------------------------------------------------------------------------

def bisagras(x, nudos):
    """Spline lineal por tramos: una columna max(0, x - nudo) por nudo."""
    x = np.asarray(x, dtype=float)
    return np.column_stack([np.maximum(0.0, x - k) for k in nudos])


def _col(d, meta, nombre):
    return d["X_rend"][:, meta["cols_rend"].index(nombre)]


def _spline_con_faltantes(d, meta, variable):
    """Bisagras de una variable rellenada con 0 cuando falta; las filas imputadas no aportan curvatura."""
    x = _col(d, meta, variable)
    falta = _col(d, meta, f"falta_{variable}") > 0.5
    obs = ~falta
    if obs.sum() < 50:
        raise ValueError(f"{variable}: muy pocas filas observadas ({int(obs.sum())}) para un spline.")
    nudos = np.unique(np.quantile(x[obs], CUANTILES_NUDOS))
    X = bisagras(x, nudos) * obs[:, None]
    nombres = [f"{variable}_sobre_{k:.2f}" for k in nudos]
    return X, nombres


def columnas_paquete(d, meta, paquete):
    """(matriz, nombres) de un paquete, sin escalar."""
    if paquete == "min_x_rend":
        pocos = _col(d, meta, "pocos_minutos")
        presentes = [v for v in Z_CONTINUAS if v in meta["cols_rend"]]
        X = np.column_stack([pocos * _col(d, meta, v) for v in presentes])
        return X, [f"pocos_x_{v}" for v in presentes]
    if paquete == "spline_debut":
        return _spline_con_faltantes(d, meta, "z_edad_debut")
    if paquete == "spline_goles_rec":
        return _spline_con_faltantes(d, meta, "z_goles_recibidos_ajustados_90")
    if paquete == "edad_cola":
        return bisagras(d["edad"], NUDOS_EDAD), [f"edad_sobre_{k:g}" for k in NUDOS_EDAD]
    raise ValueError(f"Paquete desconocido: {paquete}. Opciones: {PAQUETES}")


def construir_extensiones(d, meta, paquetes):
    """
    Devuelve (X_ext, nombres): columnas de todos los paquetes pedidos, cada una dividida por su
    desvio (toda la muestra). Columnas sin variacion se descartan.
    """
    mats, nombres = [], []
    for p in paquetes:
        X, n = columnas_paquete(d, meta, p)
        for j, nom in enumerate(n):
            s = X[:, j].std()
            if s < 1e-9:
                print(f"AVISO: la columna {nom} no varia; se descarta.")
                continue
            mats.append(X[:, j] / s)
            nombres.append(f"{p}:{nom}")
    if not mats:
        raise ValueError("Ningun paquete aporto columnas.")
    return np.column_stack(mats), nombres


def con_extension(d, X_ext):
    """Copia de `d` con las columnas nuevas agregadas al bloque de atributos."""
    out = dict(d)
    out["X_atr"] = np.hstack([d["X_atr"], X_ext])
    return out


def diagnostico_ceros(d, meta):
    """Filas con valor exactamente 0 en cada variable de rendimiento, y cuantas son pocos_minutos."""
    pocos = _col(d, meta, "pocos_minutos") > 0.5
    filas = []
    for v in Z_CONTINUAS:
        if v not in meta["cols_rend"]:
            continue
        x = _col(d, meta, v)
        cero = x == 0.0
        nombre_falta = f"falta_{v}"
        falta = _col(d, meta, nombre_falta) > 0.5 if nombre_falta in meta["cols_rend"] else None
        filas.append({
            "variable": v,
            "pct_cero_exacto": float(cero.mean()),
            "pct_de_los_ceros_en_pocos_minutos": float(pocos[cero].mean()) if cero.any() else np.nan,
            "pct_imputado_(falta)": float(falta.mean()) if falta is not None else np.nan,
            "pct_cero_sin_indicador": float((cero & ~falta).mean()) if falta is not None else float(cero.mean()),
        })
    return pd.DataFrame(filas)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(description="nl04: extensiones no lineales del modelo bayesiano, delta ELPD.")
    parser.add_argument("--rapido", action="store_true", help="500/500, 2 cadenas, K=3 (prueba de humo).")
    parser.add_argument("--k", type=int, default=None, help="Pliegues (por defecto 5; 3 con --rapido).")
    parser.add_argument("--paquetes", nargs="+", choices=PAQUETES, default=PAQUETES)
    parser.add_argument("--sin-todo", action="store_true", dest="sin_todo", help="No ajustar el modelo con todos los paquetes juntos.")
    parser.add_argument("--temporada", choices=["ninguno", "rw"], default="rw")
    parser.add_argument("--grado-edad", type=int, default=2)
    parser.add_argument("--mundlak", action="store_true")
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

    import config
    import e08_poblacion_por_capa as e08
    import m02_modelo_base as m02

    k = args.k or (3 if args.rapido else 5)
    etiqueta = args.etiqueta or f"ext_{args.temporada}_k{k}" + ("_mun" if args.mundlak else "")
    ruta_reports = config.ruta_reports_script(Path(__file__).stem)

    d, meta = m02.preparar_datos(e08.cargar_dataset_modelado())
    ids_jugadores = np.unique(d["df"]["player_id"].to_numpy())
    pliegue_fila = m03.asignar_pliegues(d["jug_idx"], k)

    print("\nFilas con valor exactamente 0 (rendimiento):")
    diag = diagnostico_ceros(d, meta)
    with pd.option_context("display.width", 200, "display.float_format", "{:.3f}".format):
        print(diag.to_string(index=False))
    diag.to_csv(ruta_reports / f"{etiqueta}_diagnostico_ceros.csv", index=False)

    modelos = {"base": d}
    columnas = []
    for p in args.paquetes:
        X_ext, nombres = construir_extensiones(d, meta, [p])
        modelos[p] = con_extension(d, X_ext)
        columnas += [{"paquete": p, "columna": n} for n in nombres]
    if len(args.paquetes) > 1 and not args.sin_todo:
        X_ext, nombres = construir_extensiones(d, meta, args.paquetes)
        modelos["todo"] = con_extension(d, X_ext)
    pd.DataFrame(columnas).to_csv(ruta_reports / f"{etiqueta}_columnas_extension.csv", index=False)
    print(f"\nnl04: {k} pliegues por jugador, modelos = {list(modelos)}, temporada = {args.temporada}, mundlak = {args.mundlak}")
    for c in columnas:
        print(f"  {c['paquete']:<18s} {c['columna']}")

    elpd = {nombre: np.full(meta["n_jugadores"], np.nan) for nombre in modelos}
    convergencia = []
    for f in range(k):
        te = pliegue_fila == f
        jugadores_te = np.unique(d["jug_idx"][te])
        print(f"\nPliegue {f + 1}/{k}: {te.sum()} filas / {len(jugadores_te)} jugadores de prueba")
        for nombre, dm in modelos.items():
            t0 = time.time()
            d_tr, meta_tr = m03.subconjunto(dm, meta, ~te)
            d_te, _ = m03.subconjunto(dm, meta, te)
            e, conv = m03.ajustar_y_evaluar(d_tr, meta_tr, d_te, args, nombre, f)
            elpd[nombre][jugadores_te] = e
            convergencia.append(conv)
            aviso = "" if conv["rhat_max"] <= 1.01 and conv["divergencias"] == 0 else "  <-- revisar convergencia"
            print(f"  {nombre:<18s} {time.time() - t0:5.0f}s  R-hat {conv['rhat_max']:.3f}  "
                  f"ESS min {conv['ess_bulk_min']:.0f}  div {conv['divergencias']}{aviso}")

    por_jugador = pd.DataFrame({"jug_idx": np.arange(meta["n_jugadores"]), **elpd})
    por_jugador["player_id"] = ids_jugadores
    por_jugador.to_csv(ruta_reports / f"{etiqueta}_elpd_por_jugador.csv", index=False)
    pd.DataFrame(convergencia).to_csv(ruta_reports / f"{etiqueta}_convergencia_pliegues.csv", index=False)

    filas = []
    for nombre in modelos:
        if nombre == "base":
            continue
        r = m03.comparar(elpd[nombre], elpd["base"])
        filas.append({"extension": nombre, **r, "elpd_extension": float(np.nansum(elpd[nombre])),
                      "elpd_base": float(np.nansum(elpd["base"]))})
    comp = pd.DataFrame(filas)
    comp.to_csv(ruta_reports / f"{etiqueta}_comparacion.csv", index=False)

    print("\nResultado (delta_ELPD = extension - base; > 0 favorece a la extension):")
    with pd.option_context("display.width", 200, "display.float_format", "{:,.2f}".format):
        print(comp.to_string(index=False))
    for _, r in comp.iterrows():
        if r["diferencia_clara"] and r["delta_elpd"] > 0:
            veredicto = "MEJORA la prediccion de jugadores nuevos"
        elif r["diferencia_clara"]:
            veredicto = "EMPEORA la prediccion (|delta| > 2 SE)"
        else:
            veredicto = "sin diferencia clara (el lineal alcanza)"
        print(f"  {r['extension']:<18s} {r['delta_elpd']:>9,.1f} ({r['delta_sobre_se']:>5.1f} SE): {veredicto}")
    print(f"\nListo. Tablas en {ruta_reports}.")


if __name__ == "__main__":
    main()
