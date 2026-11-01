"""
Pipeline (d0X, 22/09/2026): componente PCA del cluster 1 de multicolinealidad
("exito deportivo del club", ver e02_correlaciones_predictores.py) como
predictor de contexto para el panel. Cierra el analisis exploratorio de
e03_pca_exito_deportivo.py -- ese script ya recorrio y justifico la decision
(PARTE 1: 8 variables originales, descarte de pct_victorias_con/sin por
mediador/endogeneidad; PARTE 2: PCA final sobre las 6 variables
club-temporada restantes, 90.61% de varianza en PC1, criterio de Kaiser
confirmado). Este script fija esa decision como parte del pipeline.

Las 6 variables (COLUMNAS_CLUSTER_EXITO) se construyen en
d02_construir_variables_contexto.construir_objetivos_deportivos() y llegan
al panel de predictores via d04_construir_panel_predictores() -- este script
no las calcula, solo las combina en la componente.

DECISION DE DISEÑO (por que hay que "ajustar" y "guardar", no solo "correr
el PCA cada vez"): un PCA refiteado en cada corrida del pipeline dependeria
de que filas esten presentes en ESE momento (que cambian: el panel crece,
Kaggle actualiza el snapshot, etc.), asi que la definicion misma de que es
"exito deportivo" (los pesos de la combinacion lineal) podria correrse un
poco de una corrida a otra sin que nadie lo note -- rompe reproducibilidad y
comparabilidad entre corridas. La alternativa (la que se implementa aca):
ajustar los parametros (media/desvio de StandardScaler + vector de loadings
de PCA) UNA vez, guardarlos en un .json versionado en git, y de ahi en
adelante SOLO aplicar esa transformacion lineal fija a cada fila nueva --
sin volver a ajustar nada. Reajustar deliberadamente (por ejemplo, al migrar
de v679 a una version de datos mas nueva) es una decision explicita, no un
efecto secundario de correr el pipeline: se hace llamando a main(forzar_reajuste=True).

Convencion de firma de las 2 funciones reusables (import directo desde
d06_extraer_panel_predictores.py, sin ejecutar este __main__):
  - ajustar_parametros(dataset) -> dict de parametros (no toca disco)
  - aplicar_pca_exito_deportivo(dataset, parametros) -> DataFrame
    [player_id, season, pca_exito_deportivo]
  - guardar_parametros(parametros) / cargar_parametros() -> IO del .json

SALIDA (parametros, no datos): data/processed/parametros_pca_exito_deportivo.json
-- SI hay que versionar este archivo en git (a diferencia de los
dataset_modelable_*.csv con fecha, que son productos regenerables): es lo
que fija la definicion de la componente entre corridas y entre maquinas.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

_RAIZ_SCRIPTS = Path(__file__).resolve().parents[1]  # scripts/, tras la reorganizacion en subcarpetas (22/09)
for _carpeta in ("config", "dataset", "eda", "diagnosticos"):
    sys.path.insert(0, str(_RAIZ_SCRIPTS / _carpeta))

import config

# Mismas 6 variables y misma inversion de signo que PARTE 2 de
# e03_pca_exito_deportivo.py (posicion_final/posicion_promedio son "mas bajo
# = mejor" en la tabla de posiciones -- se invierten para que las 6 apunten
# a "exito", no a "fracaso").
COLUMNAS_CLUSTER_EXITO = [
    "pct_victorias", "puntos_por_partido", "puntos_totales",
    "diferencia_gol_promedio", "posicion_final", "posicion_promedio",
]
COLUMNAS_A_INVERTIR = ["posicion_final", "posicion_promedio"]

RUTA_PARAMETROS = config.RUTA_DATOS_PROCESSED / "parametros_pca_exito_deportivo.json"


def ajustar_parametros(dataset):
    """
    Ajusta StandardScaler + PCA(n_components=1) sobre las filas con las 6
    columnas completas -- mismo procedimiento exacto que PARTE 2 de
    e03_pca_exito_deportivo.py. Devuelve un dict serializable a JSON, no
    escribe nada a disco (eso lo hace guardar_parametros por separado, para
    poder inspeccionar el resultado antes de persistirlo si hace falta).
    """
    faltantes = [c for c in COLUMNAS_CLUSTER_EXITO if c not in dataset.columns]
    if faltantes:
        raise KeyError(
            f"No estan en el dataset: {faltantes}. Se esperaban las 6 variables "
            "de d02_construir_variables_contexto.construir_objetivos_deportivos()."
        )

    mascara_completa = dataset[COLUMNAS_CLUSTER_EXITO].notna().all(axis=1)
    datos = dataset.loc[mascara_completa, COLUMNAS_CLUSTER_EXITO].copy()
    for col in COLUMNAS_A_INVERTIR:
        datos[col] = -datos[col]

    escalador = StandardScaler()
    datos_std = escalador.fit_transform(datos)

    pca = PCA(n_components=1)
    pca.fit(datos_std)
    componente = pca.components_[0].copy()

    # Convencion de signo fija: se fuerza a que el promedio de los loadings
    # sea positivo, para que "mas alto en la componente" siempre se lea como
    # "mas exito", nunca al reves -- PCA no fija el signo por si solo (es
    # arbitrario cual de las dos direcciones opuestas devuelve sklearn), asi
    # que sin esto la interpretacion podria invertirse silenciosamente si
    # algun dia se reajustan los parametros con datos distintos.
    if componente.mean() < 0:
        componente = -componente

    return {
        "columnas": COLUMNAS_CLUSTER_EXITO,
        "columnas_a_invertir": COLUMNAS_A_INVERTIR,
        "media": escalador.mean_.tolist(),
        "desvio": escalador.scale_.tolist(),
        "componente": componente.tolist(),
        "var_explicada": float(pca.explained_variance_ratio_[0]),
        "n_filas_ajuste": int(mascara_completa.sum()),
        "fecha_ajuste": pd.Timestamp.now().strftime("%Y-%m-%d"),
    }


def guardar_parametros(parametros, ruta=RUTA_PARAMETROS):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(parametros, f, indent=2, ensure_ascii=False)


def cargar_parametros(ruta=RUTA_PARAMETROS):
    if not ruta.exists():
        raise FileNotFoundError(
            f"No existe {ruta} todavia -- correr ajustar_parametros() + "
            "guardar_parametros() una primera vez (main() de este script lo "
            "hace automaticamente si el archivo no esta)."
        )
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def aplicar_pca_exito_deportivo(dataset, parametros):
    """
    Aplica la transformacion lineal FIJA (parametros ya ajustados, no un
    refit) a cada fila de dataset: (x - media) / desvio, proyectado sobre el
    vector de loadings de PC1. No usa sklearn -- es exactamente lo mismo que
    hace StandardScaler + PCA.transform() por dentro, escrito explicito para
    no depender de reconstruir los objetos sklearn a partir del JSON.

    Devuelve player_id/season + pca_exito_deportivo; NaN en las filas que no
    tengan las 6 columnas completas (deberia ser ~0% del panel, ver
    e03_pca_exito_deportivo.py, pero no se asume).
    """
    columnas = parametros["columnas"]
    media = np.array(parametros["media"])
    desvio = np.array(parametros["desvio"])
    componente = np.array(parametros["componente"])

    faltantes = [c for c in columnas if c not in dataset.columns]
    if faltantes:
        raise KeyError(f"No estan en el dataset: {faltantes}.")

    datos = dataset[columnas].copy()
    for col in parametros["columnas_a_invertir"]:
        datos[col] = -datos[col]

    mascara_completa = datos.notna().all(axis=1)
    datos_std = (datos.values - media) / desvio
    scores = datos_std @ componente

    resultado = dataset[["player_id", "season"]].copy()
    resultado["pca_exito_deportivo"] = np.where(mascara_completa, scores, np.nan)
    return resultado


def construir_pca_exito_deportivo(dataset, forzar_reajuste=False):
    """
    Punto de entrada pensado para que lo importe d06_extraer_panel_predictores.py:
    usa los parametros ya guardados si existen (caso normal, todas las
    corridas del pipeline despues de la primera), o los ajusta y guarda por
    primera vez si todavia no hay archivo -- forzar_reajuste=True fuerza un
    reajuste deliberado aunque ya exista (ver nota de diseño al principio del
    modulo sobre por que esto tiene que ser explicito).
    """
    if RUTA_PARAMETROS.exists() and not forzar_reajuste:
        parametros = cargar_parametros()
        print(f"PCA exito deportivo: usando parametros ya ajustados ({RUTA_PARAMETROS.name}, "
              f"ajustados el {parametros['fecha_ajuste']} sobre {parametros['n_filas_ajuste']} filas).")
    else:
        motivo = "forzado" if (RUTA_PARAMETROS.exists() and forzar_reajuste) else "primera vez"
        parametros = ajustar_parametros(dataset)
        guardar_parametros(parametros)
        print(f"PCA exito deportivo: parametros ajustados ({motivo}) y guardados en {RUTA_PARAMETROS}.")

    resultado = aplicar_pca_exito_deportivo(dataset, parametros)
    return resultado, parametros


def main(forzar_reajuste=False):
    candidatos = sorted(config.RUTA_DATOS_PROCESSED.glob("dataset_modelable_*.csv"))
    if not candidatos:
        raise FileNotFoundError(
            "No se encontro ningun dataset_modelable_*.csv en data/processed -- "
            "correr primero d06_extraer_panel_predictores.py."
        )
    ruta_dataset = candidatos[-1]
    print(f"Usando: {ruta_dataset.name}")
    dataset = pd.read_csv(ruta_dataset)

    resultado, parametros = construir_pca_exito_deportivo(dataset, forzar_reajuste=forzar_reajuste)

    print("\nVector de loadings (PC1, columnas ya invertidas donde corresponde):")
    for col, peso in zip(parametros["columnas"], parametros["componente"]):
        print(f"  {col}: {peso:.3f}")
    print(f"Varianza explicada por PC1: {parametros['var_explicada']:.2%}")
    print(f"\nCobertura de pca_exito_deportivo: {resultado['pca_exito_deportivo'].notna().mean():.4f}")

    # Chequeo informativo (no assert -- una pequeña diferencia frente a lo
    # documentado en e03/learnings-and-pitfalls es esperable si el snapshot
    # de datos cambio; una diferencia GRANDE si mereceria mirarse) contra
    # log_valor_mercado, si esta columna esta disponible en lo que se cargo.
    if "log_valor_mercado" in dataset.columns:
        comparacion = dataset[["player_id", "season", "log_valor_mercado"]].merge(
            resultado, on=["player_id", "season"], how="inner"
        )
        r = comparacion["pca_exito_deportivo"].corr(comparacion["log_valor_mercado"])
        print(f"Correlacion (Pearson) con log_valor_mercado: {r:.3f} "
              "(referencia documentada en la nota metodologica: 0.393 sobre el panel completo).")

    return resultado, parametros


if __name__ == "__main__":
    resultado_pca_exito_deportivo, parametros_pca_exito_deportivo = main()