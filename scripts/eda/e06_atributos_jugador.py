"""
Analisis exploratorio (e0X, 24/09/2026): primer vistazo a los 3 atributos de
jugador nuevos que agrega d08_construir_atributos_jugador.py -- altura_cm,
pie_habil, es_comunitario -- ANTES de estandarizar altura_cm por posicion en
d09. Mismo orden ya usado con rendimiento_it: mirar los datos crudos y
confirmar el spec antes de estandarizar, no al reves.

ALCANCE deliberadamente MAS CHICO que e01-e05: esos scripts mapeaban
multicolinealidad DENTRO de bloques grandes (8 variables de contexto, 8
candidatas de rendimiento) que competian entre si por el mismo rol en el
modelo. Estos 3 atributos no compiten entre si (un jugador tiene altura, pie
Y ciudadania a la vez, no hay que elegir uno) -- el chequeo que hace falta es
mas acotado:

    1. Univariado de cada uno (ya se vio parte de esto en los prints de
       d08/d06 sobre la corrida real, esto lo deja formalizado con
       tablas/graficos guardados en reports/, mismo patron que e01).
    2. Bivariado contra la DV (log_valor_mercado):
       - altura_cm: correlacion pooled Y desglosada por
         posicion_amplia_predominante -- decision de Gianfranco (24/09): el
         diccionario de variables ya señala que el efecto de altura es
         distinto para arqueros/centrales que para el resto de las
         posiciones; una correlacion pooled puede diluir o esconder ese
         efecto (mismo argumento ya usado para justificar mantener
         tarjetas_90 en e05 pese a su correlacion pooled debil).
       - pie_habil / es_comunitario: medias/mediana de la DV por grupo
         (reusa e01.tabla_bivariado_grupos tal cual), no correlacion --
         son categoricas, no numericas.
    3. VIF conjunto: suma altura_cm y es_comunitario (numerica y booleana,
       entran directo a una matriz de correlacion) a la especificacion
       final YA CERRADA de contexto (e04, 4 variables) + rendimiento (e05,
       6 variables) -- 12 variables en total -- para confirmar que no
       meten colinealidad nueva con lo que ya esta decidido. pie_habil
       QUEDA AFUERA del VIF a proposito: es categorica de 3 niveles
       (right/left/both), no una variable continua/binaria que entre
       directo a una matriz de correlacion -- mismo tratamiento que ya
       recibe posicion_amplia_predominante en el resto del pipeline
       (variable de agrupamiento/interaccion, no un regresor VIF-comprobable
       por si sola). Si mas adelante se decide meter dummies de pie_habil
       como regresores directos, ese chequeo se hace en ese momento, no aca.

Corre sobre el dataset_modelable MAS RECIENTE en data/processed/ (mismo
patron que el resto de e0X, via e01.cargar_dataset_modelable()) -- asume que
ya se volvio a correr d06_extraer_panel_predictores.py con el d08 actualizado
(altura_cm/pie_habil/es_comunitario); si no, faltan columnas y el script tira
KeyError explicito en vez de fallar en un punto arbitrario mas adelante.

SALIDAS (en reports/e06_atributos_jugador/, figuras en
reports/figuras/e06_atributos_jugador/):
    resumen_univariado.csv
    correlacion_altura_vs_dv_pooled.csv
    correlacion_altura_vs_dv_por_posicion.csv
    bivariado_pie_habil_vs_dv.csv
    bivariado_es_comunitario_vs_dv.csv
    vif_atributos_mas_especificacion_final.csv
    univariado_altura_cm.png / univariado_pie_habil.png / univariado_es_comunitario.png
    boxplot_altura_por_posicion.png / boxplot_dv_por_posicion.png
    boxplot_pie_habil_vs_dv.png / boxplot_es_comunitario_vs_dv.png

No decide nada por si solo -- junta la evidencia para el spec final de
atributos de jugador, mismo criterio ya usado en e02/e04/e05.
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
import e04_vif_contexto as e04
import e05_seleccion_rendimiento as e05
import estilo_graficos as estilo

VARIABLE_DEPENDIENTE = "log_valor_mercado"
COLUMNA_POSICION = "posicion_amplia_predominante"
ATRIBUTOS_NUEVOS = ["altura_cm", "pie_habil", "es_comunitario"]
N_MIN_CORRELACION = 30  # mismo piso que el resto de e0X


def resumen_univariado_atributos(dataset):
    filas = []
    s = dataset["altura_cm"]
    filas.append({
        "columna": "altura_cm", "tipo": "numerica",
        "n_no_nulos": s.notna().sum(), "pct_nulos": s.isna().mean(),
        "media": s.mean(), "mediana": s.median(), "std": s.std(),
        "min": s.min(), "max": s.max(),
    })
    for col in ["pie_habil", "es_comunitario"]:
        s = dataset[col]
        filas.append({
            "columna": col, "tipo": e01.clasificar_columna(s),
            "n_no_nulos": s.notna().sum(), "pct_nulos": s.isna().mean(),
        })
    return pd.DataFrame(filas)


def correlacion_altura_por_posicion(dataset, dv, n_min=N_MIN_CORRELACION):
    filas = []
    for posicion, grupo in dataset.groupby(COLUMNA_POSICION, dropna=False):
        sub = grupo[["altura_cm", dv]].dropna()
        n = len(sub)
        if n < n_min:
            pearson = spearman = np.nan
        else:
            pearson = sub["altura_cm"].corr(sub[dv], method="pearson")
            spearman = sub["altura_cm"].corr(sub[dv], method="spearman")
        filas.append({
            COLUMNA_POSICION: posicion, "n": n,
            "pearson_vs_dv": pearson, "spearman_vs_dv": spearman,
        })
    tabla = pd.DataFrame(filas)
    return tabla.sort_values("n", ascending=False).reset_index(drop=True)


def graficar_boxplot_por_grupo(dataset, columna, dv, ruta_png, top_n=10):
    """
    Boxplot de `dv` por categoria de `columna`. Categorias descubiertas en
    vivo (sin hardcodear nombres de posicion/pie -- no sabemos de antemano
    como estan escritas en el dataset real), ordenadas por frecuencia y
    acotadas a top_n para no saturar el grafico si `columna` tuviera muchos
    niveles (no deberia pasar con las columnas de este script, pero se deja
    el resguardo, mismo criterio que CARDINALIDAD_MAX_GRAFICO en e01).
    """
    conteo = dataset[columna].value_counts(dropna=False).head(top_n)
    grupos, etiquetas = [], []
    for valor in conteo.index:
        if pd.isna(valor):
            mascara = dataset[columna].isna()
            etiqueta = "NaN"
        else:
            mascara = dataset[columna] == valor
            etiqueta = str(valor)
        datos = dataset.loc[mascara, dv].dropna()
        if len(datos) == 0:
            continue
        grupos.append(datos.values)
        etiquetas.append(f"{etiqueta}\n(n={len(datos)})")

    if not grupos:
        print(f"AVISO: no hay datos para graficar el boxplot de {dv} por {columna}.")
        return

    fig, ax = plt.subplots(figsize=(max(5, 1.3 * len(grupos)), 5))
    caja = ax.boxplot(grupos, tick_labels=etiquetas, patch_artist=True, showfliers=False)
    for parche in caja["boxes"]:
        parche.set_facecolor(estilo.COLOR_PRINCIPAL)
        parche.set_alpha(0.6)
    ax.set_ylabel(dv)
    ax.set_title(f"{dv} por {columna}")
    fig.tight_layout()
    fig.savefig(ruta_png, dpi=120)
    plt.close(fig)


def main():
    estilo.aplicar_estilo()
    dataset = e01.cargar_dataset_modelable()
    print(f"Dataset: {dataset.shape[0]} filas, {dataset.shape[1]} columnas.")

    faltantes = [c for c in ATRIBUTOS_NUEVOS if c not in dataset.columns]
    if faltantes:
        raise KeyError(
            f"No estan en el dataset: {faltantes}. Correr d06_extraer_panel_predictores.py "
            "con el d08 actualizado (altura_cm/pie_habil/es_comunitario) antes de este script."
        )
    if COLUMNA_POSICION not in dataset.columns:
        raise KeyError(
            f"No esta la columna '{COLUMNA_POSICION}' -- necesaria para el desglose de "
            "altura_cm por posicion."
        )

    ruta_reports = config.ruta_reports_script(Path(__file__).stem)
    ruta_figuras = config.ruta_figuras_script(Path(__file__).stem)

    # --- 1. Univariado ---
    resumen = resumen_univariado_atributos(dataset)
    e01.guardar_csv_legible(resumen, ruta_reports / "resumen_univariado.csv")
    print("\nResumen univariado:")
    print(resumen.to_string(index=False))

    e01.graficar_histograma(dataset["altura_cm"], "altura_cm", ruta_figuras / "univariado_altura_cm.png")
    e01.graficar_barras_categorica(dataset["pie_habil"], "pie_habil", ruta_figuras / "univariado_pie_habil.png")
    e01.graficar_barras_booleana(dataset["es_comunitario"], "es_comunitario", ruta_figuras / "univariado_es_comunitario.png")

    # --- 2. Bivariado contra la DV ---
    sub_pooled = dataset[["altura_cm", VARIABLE_DEPENDIENTE]].dropna()
    n_pooled = len(sub_pooled)
    if n_pooled >= N_MIN_CORRELACION:
        pearson_pooled = sub_pooled["altura_cm"].corr(sub_pooled[VARIABLE_DEPENDIENTE], method="pearson")
        spearman_pooled = sub_pooled["altura_cm"].corr(sub_pooled[VARIABLE_DEPENDIENTE], method="spearman")
    else:
        pearson_pooled = spearman_pooled = np.nan
    corr_pooled = pd.DataFrame([{"n": n_pooled, "pearson_vs_dv": pearson_pooled, "spearman_vs_dv": spearman_pooled}])
    e01.guardar_csv_legible(corr_pooled, ruta_reports / "correlacion_altura_vs_dv_pooled.csv")
    print(f"\naltura_cm vs {VARIABLE_DEPENDIENTE} (pooled, n={n_pooled}):")
    print(corr_pooled.to_string(index=False))

    corr_por_posicion = correlacion_altura_por_posicion(dataset, VARIABLE_DEPENDIENTE)
    e01.guardar_csv_legible(corr_por_posicion, ruta_reports / "correlacion_altura_vs_dv_por_posicion.csv")
    print(f"\naltura_cm vs {VARIABLE_DEPENDIENTE}, desglosado por {COLUMNA_POSICION}:")
    print(corr_por_posicion.to_string(index=False))
    grupos_chicos = corr_por_posicion[corr_por_posicion["n"] < N_MIN_CORRELACION]
    if len(grupos_chicos) > 0:
        print(
            f"AVISO: {len(grupos_chicos)} grupo(s) de {COLUMNA_POSICION} con n < {N_MIN_CORRELACION} "
            "-- correlacion no calculada para esos, ver tabla (queda como NaN, no como 0)."
        )

    graficar_boxplot_por_grupo(dataset, COLUMNA_POSICION, "altura_cm", ruta_figuras / "boxplot_altura_por_posicion.png")
    graficar_boxplot_por_grupo(dataset, COLUMNA_POSICION, VARIABLE_DEPENDIENTE, ruta_figuras / "boxplot_dv_por_posicion.png")

    bivariado_pie = e01.tabla_bivariado_grupos(dataset, "pie_habil", VARIABLE_DEPENDIENTE)
    e01.guardar_csv_legible(bivariado_pie, ruta_reports / "bivariado_pie_habil_vs_dv.csv")
    print(f"\n{VARIABLE_DEPENDIENTE} por pie_habil:")
    print(bivariado_pie.to_string(index=False))
    graficar_boxplot_por_grupo(dataset, "pie_habil", VARIABLE_DEPENDIENTE, ruta_figuras / "boxplot_pie_habil_vs_dv.png")

    bivariado_comunitario = e01.tabla_bivariado_grupos(dataset, "es_comunitario", VARIABLE_DEPENDIENTE)
    e01.guardar_csv_legible(bivariado_comunitario, ruta_reports / "bivariado_es_comunitario_vs_dv.csv")
    print(f"\n{VARIABLE_DEPENDIENTE} por es_comunitario:")
    print(bivariado_comunitario.to_string(index=False))
    graficar_boxplot_por_grupo(dataset, "es_comunitario", VARIABLE_DEPENDIENTE, ruta_figuras / "boxplot_es_comunitario_vs_dv.png")

    # --- 3. VIF conjunto: altura_cm + es_comunitario contra la especificacion final ya cerrada ---
    tabla_vif = e05.construir_tabla_efectiva(dataset)[e05.ESPECIFICACION_FINAL_PROPUESTA].copy()
    for col in e04.COLUMNAS_CONTEXTO_FINAL:
        tabla_vif[col] = dataset[col]
    tabla_vif["altura_cm"] = dataset["altura_cm"]
    tabla_vif["es_comunitario"] = dataset["es_comunitario"].map({True: 1.0, False: 0.0})

    variables_vif = e04.COLUMNAS_CONTEXTO_FINAL + e05.ESPECIFICACION_FINAL_PROPUESTA + ["altura_cm", "es_comunitario"]
    n_completo = tabla_vif[variables_vif].dropna().shape[0]
    print(
        f"\nFilas con las {len(variables_vif)} variables simultaneamente no-nulas: "
        f"{n_completo} / {len(tabla_vif)} ({n_completo / len(tabla_vif):.1%})"
    )
    if n_completo / len(tabla_vif) < 0.5:
        print(
            "AVISO: el VIF conjunto cae sobre menos de la mitad del panel -- interpretar con "
            "cautela (mismo aviso que ya usa e05 para el bloque de rendimiento)."
        )

    vif, n_vif = e05.calcular_vif(tabla_vif, variables_vif)
    tabla_vif_resultado = vif.rename("vif").rename_axis("variable").reset_index()
    e01.guardar_csv_legible(tabla_vif_resultado, ruta_reports / "vif_atributos_mas_especificacion_final.csv")
    e05.imprimir_vif(
        f"VIF -- especificacion final de contexto+rendimiento (10 variables) + altura_cm + "
        f"es_comunitario ({len(variables_vif)} variables en total; pie_habil queda afuera, "
        "ver docstring del modulo)",
        vif, n_vif,
    )

    print(
        f"\nListo. Reportes en {ruta_reports}, figuras en {ruta_figuras}. Este script no descarta "
        "nada por si solo -- junta la evidencia para decidir el spec final de atributos de jugador "
        "antes de construir d09 (z-score)."
    )

    return resumen, corr_pooled, corr_por_posicion, bivariado_pie, bivariado_comunitario, vif


if __name__ == "__main__":
    (resumen_univariado, correlacion_altura_pooled, correlacion_altura_por_posicion_tabla,
     bivariado_pie_habil, bivariado_es_comunitario, vif_atributos) = main()