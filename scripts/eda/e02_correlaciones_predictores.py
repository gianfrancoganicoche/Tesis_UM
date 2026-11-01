"""
Segundo script de EDA (21/09/2026): correlacion cruzada entre TODOS los
predictores numericos entre si -- no contra la variable dependiente, eso ya
esta en e01_analisis_exploratorio.py (bivariado_correlaciones_numericas.csv).

Motivacion: el heatmap de e01 (bivariado_heatmap_correlaciones.png) deja ver
a ojo varios clusters de multicolinealidad (exito deportivo del club, valor
patrimonial del club, volumen de minutos jugados), pero un heatmap de ~50x50
variables no permite leer con precision CUALES pares estan mas
correlacionados entre si, ni ordenarlos. Este script calcula la matriz
completa de correlacion (Pearson y Spearman) entre pares de predictores
numericos, la aplana a una tabla de pares unicos (sin diagonal, sin
duplicar A-B/B-A), y la filtra a los pares con |Pearson| >=
UMBRAL_CORRELACION_ALTA -- una lista concreta y priorizada de candidatos a
redundancia, para tener en cuenta antes de definir la especificacion final
del modelo (que variables de contexto club/liga entran, cuales se dejan
afuera o se combinan).

Reutiliza de e01_analisis_exploratorio.py (import directo, no duplicacion):
cargar_dataset_modelable, clasificar_columna, serie_efectiva (con su mismo
piso de confiabilidad para las columnas '_90'), COLUMNAS_EXCLUIR,
COLUMNAS_DV, COLUMNA_EDAD, guardar_csv_legible. Mismo patron que ya usan los
scripts d0X entre si (import de modulo hermano via sys.path, sin ejecutar su
bloque __main__).

SALIDA: reports/e02_correlaciones_predictores/pares_correlacionados_predictores.csv
(22/09: movida a una subcarpeta propia de este script -- ver
config.ruta_reports_script() en config.py -- para no mezclarse con las
salidas de otros scripts de EDA).
"""

import sys
from pathlib import Path

import pandas as pd

_RAIZ_SCRIPTS = Path(__file__).resolve().parents[1]  # scripts/, tras la reorganizacion en subcarpetas (22/09)
for _carpeta in ("config", "dataset", "eda", "diagnosticos"):
    sys.path.insert(0, str(_RAIZ_SCRIPTS / _carpeta))

import config
import e01_analisis_exploratorio as e01

UMBRAL_CORRELACION_ALTA = 0.7


def calcular_matriz_correlaciones(dataset, columnas, metodo):
    """
    Arma un DataFrame con la version enmascarada (serie_efectiva) de cada
    columna y calcula su matriz de correlacion cuadrada. pandas.DataFrame.corr
    usa pairwise-complete-observations por default: si dos columnas tienen
    piso de confiabilidad distinto (o nulos en filas distintas), cada par se
    calcula sobre las filas donde AMBAS tienen dato, no sobre la interseccion
    global -- mismo comportamiento que ya usa graficar_heatmap_correlaciones
    en e01, para que ambas salidas sean consistentes entre si.
    """
    marco = pd.DataFrame({col: e01.serie_efectiva(dataset, col) for col in columnas})
    return marco.corr(method=metodo)


def aplanar_pares(matriz_pearson, matriz_spearman):
    """
    Convierte dos matrices cuadradas (mismas columnas, mismo orden) en una
    tabla de pares unicos columna_a/columna_b -- solo el triangulo superior
    (sin la diagonal), para no duplicar A-B y B-A ni incluir la correlacion
    de una columna consigo misma.
    """
    columnas = matriz_pearson.columns
    filas = []
    for i, col_a in enumerate(columnas):
        for col_b in columnas[i + 1:]:
            filas.append({
                "columna_a": col_a,
                "columna_b": col_b,
                "pearson": matriz_pearson.loc[col_a, col_b],
                "spearman": matriz_spearman.loc[col_a, col_b],
            })
    return pd.DataFrame(filas)


def main():
    dataset = e01.cargar_dataset_modelable()
    print(f"Dataset: {dataset.shape[0]} filas, {dataset.shape[1]} columnas.")

    ruta_reports = config.ruta_reports_script(Path(__file__).stem)

    columnas_predictoras = [
        c for c in dataset.columns
        if c not in e01.COLUMNAS_EXCLUIR + e01.COLUMNAS_DV + [e01.COLUMNA_EDAD]
    ]
    numericas = [c for c in columnas_predictoras if e01.clasificar_columna(dataset[c]) == "numerica"]
    print(f"Predictores numericos considerados: {len(numericas)}.")

    matriz_pearson = calcular_matriz_correlaciones(dataset, numericas, "pearson")
    matriz_spearman = calcular_matriz_correlaciones(dataset, numericas, "spearman")

    tabla_pares = aplanar_pares(matriz_pearson, matriz_spearman)
    tabla_pares["_abs_pearson"] = tabla_pares["pearson"].abs()
    tabla_pares = tabla_pares.sort_values("_abs_pearson", ascending=False).drop(columns="_abs_pearson")

    n_pares_totales = len(tabla_pares)
    tabla_pares_altos = tabla_pares[tabla_pares["pearson"].abs() >= UMBRAL_CORRELACION_ALTA].reset_index(drop=True)

    ruta_salida = ruta_reports / "pares_correlacionados_predictores.csv"
    e01.guardar_csv_legible(tabla_pares_altos, ruta_salida)

    print(f"\n{len(tabla_pares_altos)} pares con |Pearson| >= {UMBRAL_CORRELACION_ALTA} "
          f"(de {n_pares_totales} pares posibles entre {len(numericas)} predictores numericos).")
    print(f"Guardado en: {ruta_salida}")
    print("\nTodos los pares por encima del umbral, ordenados por |Pearson| descendente:")
    print(tabla_pares_altos.to_string(index=False))

    return tabla_pares, tabla_pares_altos


if __name__ == "__main__":
    tabla_pares_predictores, tabla_pares_predictores_altos = main()