"""
Analisis exploratorio (e0X, 23/09/2026): VIF (Variance Inflation Factor) de la
especificacion final del bloque de contexto de club/liga, ya resuelta cluster
por cluster (ver learnings-and-pitfalls.md): pca_exito_deportivo (cluster 1,
PC1 de d07_construir_pca_exito_deportivo.py) + companieros_valor_promedio
(cluster 2) + formaciones_distintas (cluster 4a) + fase_maxima_alcanzada
(cluster 4b). Chequeo conjunto de colinealidad -- las correlaciones de a
pares (e02) ya estan resueltas por cluster, pero la colinealidad puede
aparecer entre variables de CLUSTERS DISTINTOS que ninguna vista de a pares
detecta.

Ademas (motivado por la corrida de revisar_endogeneidad_pct_victorias.py,
23/09: pct_victorias_con/sin correlacionan 0.83/0.85 con pca_exito_deportivo)
esta corrida agrega una SEGUNDA version que mete pct_victorias_con/sin en el
mismo bloque, para cuantificar en numeros concretos cuanto se dispara el VIF
de pca_exito_deportivo -- y de las propias con/sin -- si se las incluyera
igual, en vez de quedarse solo con el argumento de la correlacion pairwise.

Metodo: VIF_j = elemento diagonal j de la INVERSA de la matriz de correlacion
de las variables candidatas (estandarizadas) -- equivalente a regresionar
cada variable contra el resto y tomar 1/(1-R^2), pero mas simple de calcular.
Requiere una MUESTRA UNICA sin NaN en ninguna columna del bloque (listwise
deletion) -- a diferencia de pandas.DataFrame.corr(), que por default usa
pares completos DISTINTOS para cada par de columnas (pairwise), lo cual no es
valido para este metodo: la inversion de matriz necesita una matriz de
correlacion calculada sobre una sola muestra consistente.

Umbrales de referencia (los mas citados en la literatura de econometria,
ninguno es una regla absoluta): VIF > 5 amerita atencion, VIF > 10 se suele
considerar colinealidad seria.

PARTE 3 genera un grafico de barras (VIF antes/despues de agregar con/sin,
por variable) en reports/figuras/e04_vif_contexto/, con el estilo compartido
del repo -- pensado para ilustrar visualmente el salto de colinealidad, no
solo como tabla de numeros.

No escribe nada en el pipeline -- es puramente diagnostico.
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

_RAIZ_SCRIPTS = Path(__file__).resolve().parents[1]  # scripts/
for _carpeta in ("config", "dataset", "eda", "diagnosticos"):
    sys.path.insert(0, str(_RAIZ_SCRIPTS / _carpeta))

import config
import e01_analisis_exploratorio as e01
import estilo_graficos as estilo

COLUMNAS_CONTEXTO_FINAL = [
    "pca_exito_deportivo",
    "companieros_valor_promedio",
    "formaciones_distintas",
    "fase_maxima_alcanzada",
]
COLUMNAS_CANDIDATAS_EXTRA = ["pct_victorias_con", "pct_victorias_sin"]

UMBRAL_ATENCION = 5
UMBRAL_SERIO = 10


def calcular_vif(dataset, columnas):
    """
    Devuelve (serie_vif, n_filas_usadas). serie_vif tiene un VIF por columna,
    calculado sobre las filas donde TODAS las columnas de `columnas` tienen
    dato (listwise deletion, ver nota del modulo sobre por que no alcanza con
    el .corr() pairwise por default de pandas).
    """
    datos = dataset[columnas].dropna()
    matriz_corr = datos[columnas].corr()
    inversa = np.linalg.inv(matriz_corr.values)
    vif = pd.Series(np.diag(inversa), index=columnas)
    return vif, len(datos)


def imprimir_vif(titulo, vif, n_filas):
    print(f"\n{titulo} (n={n_filas} filas completas)")
    for col, v in vif.sort_values(ascending=False).items():
        marca = ""
        if v > UMBRAL_SERIO:
            marca = f"  <-- > {UMBRAL_SERIO} (colinealidad seria)"
        elif v > UMBRAL_ATENCION:
            marca = f"  <-- > {UMBRAL_ATENCION} (amerita atencion)"
        print(f"  {col}: VIF={v:.3f}{marca}")


def main():
    dataset = e01.cargar_dataset_modelable()
    print(f"Dataset: {dataset.shape[0]} filas, {dataset.shape[1]} columnas.")

    todas = COLUMNAS_CONTEXTO_FINAL + COLUMNAS_CANDIDATAS_EXTRA
    faltantes = [c for c in todas if c not in dataset.columns]
    if faltantes:
        raise KeyError(f"No estan en el dataset: {faltantes}.")

    vif_final, n_final = calcular_vif(dataset, COLUMNAS_CONTEXTO_FINAL)
    imprimir_vif("VIF -- especificacion final de contexto (4 variables)", vif_final, n_final)

    vif_extendido, n_extendido = calcular_vif(dataset, COLUMNAS_CONTEXTO_FINAL + COLUMNAS_CANDIDATAS_EXTRA)
    imprimir_vif(
        "VIF -- especificacion final + pct_victorias_con/sin (6 variables, "
        "para cuantificar el costo de incluirlas)",
        vif_extendido, n_extendido
    )

    print(f"\npca_exito_deportivo -- VIF sin con/sin: {vif_final['pca_exito_deportivo']:.3f}  "
          f"vs. con con/sin incluidas: {vif_extendido['pca_exito_deportivo']:.3f}")

    # -------------------------------------------------------------------
    # PARTE 3 -- grafico de barras: VIF antes/despues de agregar con/sin,
    # para mostrar visualmente el salto (guardado en reports/figuras/, mismo
    # estilo compartido del repo que el resto de los graficos de e0X)
    # -------------------------------------------------------------------
    ruta_figuras = config.ruta_figuras_script(Path(__file__).stem)
    estilo.aplicar_estilo()

    variables_orden = vif_extendido.sort_values(ascending=False).index.tolist()
    valores_extendido = [vif_extendido[v] for v in variables_orden]
    valores_final = [vif_final[v] if v in vif_final.index else np.nan for v in variables_orden]

    fig, ax = plt.subplots(figsize=(7.5, 4.5))
    y = np.arange(len(variables_orden))
    alto_barra = 0.35

    ax.barh(y + alto_barra / 2, valores_final, height=alto_barra, color=estilo.COLOR_NEUTRO,
            label="Especificacion final (4 variables)")
    ax.barh(y - alto_barra / 2, valores_extendido, height=alto_barra, color=estilo.COLOR_PRINCIPAL,
            label="+ pct_victorias_con/sin (6 variables)")

    ax.axvline(UMBRAL_ATENCION, color=estilo.COLOR_SECUNDARIO, linestyle="--", linewidth=1.2)
    ax.axvline(UMBRAL_SERIO, color="#b3261e", linestyle="--", linewidth=1.2)
    # Etiquetas de umbral arriba del todo -- con invert_yaxis() mas abajo, el
    # y NEGATIVO (por delante de la primera fila, indice 0) es lo que queda
    # visualmente arriba, no y_max (eso quedaria abajo, superpuesto con la
    # leyenda -- primer intento, corregido tras revisarlo con datos sinteticos).
    y_arriba = -0.9
    ax.text(UMBRAL_ATENCION, y_arriba, f" VIF={UMBRAL_ATENCION}\n (atencion)",
            fontsize=7.5, ha="left", va="top", color="#555555")
    ax.text(UMBRAL_SERIO, y_arriba, f" VIF={UMBRAL_SERIO}\n (serio)",
            fontsize=7.5, ha="left", va="top", color="#b3261e")

    ax.set_yticks(y)
    ax.set_yticklabels(variables_orden)
    ax.set_ylim(len(variables_orden) - 0.5, y_arriba - 0.3)  # deja lugar arriba para las etiquetas de umbral
    ax.set_xlabel("VIF")
    ax.set_title("VIF de contexto: efecto de incluir pct_victorias_con/sin")
    ax.legend(frameon=False, loc="lower right", fontsize=8)
    fig.tight_layout()
    ruta_grafico = ruta_figuras / "vif_comparacion.png"
    fig.savefig(ruta_grafico, dpi=150)
    plt.close(fig)
    print(f"\nGuardado: {ruta_grafico}")

    return vif_final, vif_extendido


if __name__ == "__main__":
    vif_contexto_final, vif_contexto_extendido = main()