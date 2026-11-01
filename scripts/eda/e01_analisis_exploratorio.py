"""
Analisis exploratorio de datos (EDA) univariado y bivariado sobre el
dataset_modelable, contra la variable dependiente (log_valor_mercado).

No es parte del pipeline de construccion de datos (d0X) -- lee el
dataset_modelable ya guardado por d06_extraer_panel_predictores.py y
produce diagnostico, no datos nuevos. Por eso el prefijo es "e"
(exploratorio), no "d".

ALCANCE: recorre programaticamente TODAS las columnas predictoras del
dataset (no una lista curada a mano), clasificandolas en numericas /
booleanas / categoricas por su contenido real, no por su nombre. Esto
significa que si mas adelante se suman columnas nuevas al panel de
predictores, este script las va a incluir automaticamente sin tener que
tocarlo -- a cambio, no hay curaduria de "estas son las variables
importantes", eso queda para el analisis posterior.

QUEDAN EXCLUIDAS del analisis columna-por-columna (ver COLUMNAS_EXCLUIR):
identificadores (player_id, club_id), el indice de panel (season) y la
fecha de valuacion -- no son predictores, son claves. La variable
dependiente (valor_mercado_eur, log_valor_mercado) y edad se tratan aparte,
con su propio bloque, porque son el centro del analisis (la curva
edad-valor es la relacion central del diseño de trayectoria completa /
Alternativa 3), no una columna mas del loop generico.

SALIDAS (22/09: movidas a una subcarpeta propia de este script, via
config.ruta_reports_script()/ruta_figuras_script(), para no mezclarse con
las de otros scripts de EDA -- ver esas funciones en config.py):
- reports/e01_analisis_exploratorio/resumen_univariado.csv -- una fila por
  columna predictora, con su tipo, cobertura y estadisticos basicos.
- reports/e01_analisis_exploratorio/bivariado_correlaciones_numericas.csv --
  correlacion (Pearson y Spearman) de cada predictor numerico contra
  log_valor_mercado, ordenada por |Pearson| descendente.
- reports/figuras/e01_analisis_exploratorio/*.png -- un histograma/barras
  por columna (salvo categoricas de alta cardinalidad, que se omiten del
  grafico pero quedan en la tabla resumen), mas la curva edad-vs-DV y el
  heatmap de correlaciones entre predictores numericos.
"""

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # sin GUI -- este script solo guarda figuras, no las muestra
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

_RAIZ_SCRIPTS = Path(__file__).resolve().parents[1]  # scripts/, tras la reorganizacion en subcarpetas (22/09)
for _carpeta in ("config", "dataset", "eda", "diagnosticos"):
    sys.path.insert(0, str(_RAIZ_SCRIPTS / _carpeta))

import config
import estilo_graficos as estilo

DV = "log_valor_mercado"
COLUMNAS_EXCLUIR = ["player_id", "season", "club_id", "fecha_ultima_valuacion_temporada"]
COLUMNAS_DV = ["valor_mercado_eur", "log_valor_mercado"]
COLUMNA_EDAD = "edad"
CARDINALIDAD_MAX_GRAFICO = 30  # categoricas con mas categorias que esto no se grafican (ilegible), solo tabla

# Columnas "por 90"/"por partido" que YA tienen un flag de confiabilidad en el
# panel (d03_construir_variables_rendimiento.py) -- ese script deja el valor
# crudo sin anular a proposito (docstring: "el shrinkage aplicado mas adelante
# en el modelo complementa esto"), asi que el panel guardado no cambia. Pero
# para EDA univariado/bivariado el piso hay que aplicarlo aca: sin esto,
# jugador-temporadas con muestra minima (ej. 1 minuto jugado) generan ratios
# sin sentido (goles_90=90) que contaminan medias/std/asimetria/correlacion.
# Confirmado empiricamente el 21/09 con revisar_outliers_rate_90.py: los 14
# casos con alguna '_90' >= 89 tienen TODOS minutos_totales=1 y
# minutos_confiables=False.
COLUMNAS_CON_PISO_CONFIABILIDAD = {
    "goles_90": "minutos_confiables",
    "asistencias_90": "minutos_confiables",
    "contribucion_gol_90": "minutos_confiables",
    "tarjetas_90": "minutos_confiables",
    "goles_recibidos_90": "partidos_confiables_goles",
    "goles_recibidos_ajustados_90": "partidos_confiables_goles_ajustados",
}


def serie_efectiva(dataset, col):
    """
    Devuelve la serie de una columna, enmascarada por su piso de
    confiabilidad si tiene uno (COLUMNAS_CON_PISO_CONFIABILIDAD) -- unico
    punto de esta logica, para que histograma, resumen univariado y
    correlacion bivariada usen siempre la misma version de cada columna.
    .fillna(False) en el flag: si el flag mismo es NaN (la variable de base
    no se pudo calcular), se trata como no confiable, no como "confiable por
    default".
    """
    flag = COLUMNAS_CON_PISO_CONFIABILIDAD.get(col)
    if flag is None:
        return dataset[col]
    return dataset[col].where(dataset[flag].fillna(False))


def guardar_csv_legible(df, ruta, decimales=4):
    """
    Guarda un CSV pensado para abrir A MANO en Excel -- no para que otro
    script lo vuelva a leer con pandas (esos, como dataset_modelable_*.csv,
    se guardan con el separador por defecto de pandas y no se tocan aca).

    Separador ';' y coma decimal: Excel en espanol (configuracion regional
    Uruguay/Argentina) espera eso por defecto. Un CSV con ',' como
    separador de columna Y de decimal a la vez (el default de
    pandas.to_csv) es ambiguo para Excel en esa configuracion -- interpreta
    cada ',' como el separador decimal de un numero, y las columnas quedan
    corridas. Tambien redondea las columnas numericas: sin esto, un float
    de pandas sale con hasta 16 decimales, que no aportan nada en una tabla
    pensada para mirar a ojo.

    Para volver a leer este archivo con pandas mas adelante:
    pd.read_csv(ruta, sep=";", decimal=",")
    """
    df_redondeado = df.copy()
    columnas_numericas = df_redondeado.select_dtypes(include="number").columns
    df_redondeado[columnas_numericas] = df_redondeado[columnas_numericas].round(decimales)
    df_redondeado.to_csv(ruta, index=False, sep=";", decimal=",")


def cargar_dataset_modelable():
    """Toma el dataset_modelable mas reciente guardado en data/processed."""
    candidatos = sorted(config.RUTA_DATOS_PROCESSED.glob("dataset_modelable_*.csv"))
    if not candidatos:
        raise FileNotFoundError(
            "No se encontro ningun dataset_modelable_*.csv en data/processed -- "
            "correr primero d06_extraer_panel_predictores.py."
        )
    ruta = candidatos[-1]
    print(f"Usando: {ruta.name}")
    return pd.read_csv(ruta)


def clasificar_columna(serie):
    """
    Clasifica una columna en 'booleana', 'numerica' o 'categorica' segun su
    CONTENIDO real, no su dtype declarado -- porque una columna booleana con
    NaN (ej. un left join sin match) suele quedar como dtype object con
    valores True/False/NaN, no como dtype bool puro. Por eso el chequeo de
    "es booleana" va antes que el de "es numerica": bool es tecnicamente un
    subtipo numerico en pandas, y si no se chequea primero, una columna
    booleana con NaN podria clasificarse mal.
    """
    if serie.dtype == bool:
        return "booleana"
    valores_no_nulos = set(serie.dropna().unique().tolist())
    if valores_no_nulos and valores_no_nulos <= {True, False}:
        return "booleana"
    if pd.api.types.is_numeric_dtype(serie):
        return "numerica"
    return "categorica"


def tasa_true(serie):
    """Proporcion de True sobre los valores no nulos, sea cual sea el dtype real."""
    return serie.map({True: 1.0, False: 0.0}).mean()


# ---------------------------------------------------------------------------
# Univariado
# ---------------------------------------------------------------------------

def resumen_univariado_numerico(dataset, columnas):
    filas = []
    for col in columnas:
        s = serie_efectiva(dataset, col)
        filas.append({
            "columna": col, "tipo": "numerica",
            "piso_confiabilidad": COLUMNAS_CON_PISO_CONFIABILIDAD.get(col, ""),
            "n_no_nulos": s.notna().sum(), "pct_nulos": s.isna().mean(),
            "media": s.mean(), "mediana": s.median(), "std": s.std(),
            "min": s.min(), "max": s.max(), "asimetria": s.skew(),
        })
    return pd.DataFrame(filas)


def resumen_univariado_booleano(dataset, columnas):
    filas = []
    for col in columnas:
        s = dataset[col]
        filas.append({
            "columna": col, "tipo": "booleana",
            "n_no_nulos": s.notna().sum(), "pct_nulos": s.isna().mean(),
            "tasa_true": tasa_true(s),
        })
    return pd.DataFrame(filas)


def resumen_univariado_categorico(dataset, columnas):
    filas = []
    for col in columnas:
        s = dataset[col]
        conteo = s.value_counts(dropna=True, normalize=True)
        filas.append({
            "columna": col, "tipo": "categorica",
            "n_no_nulos": s.notna().sum(), "pct_nulos": s.isna().mean(),
            "n_unicos": s.nunique(dropna=True),
            "moda": conteo.index[0] if len(conteo) else None,
            "pct_moda": conteo.iloc[0] if len(conteo) else None,
        })
    return pd.DataFrame(filas)


def elegir_bins(datos, max_bins=40):
    """
    Bordes de bins para un histograma, evitando el patron de "peine" (bins
    vacios intercalados con bins llenos) que aparece cuando una columna solo
    toma valores enteros (partidos_con, puntos_totales, titularidades_puesto_club,
    competidores_*, etc.) y se la grafica con un numero de bins fijo (bins=40)
    que no es multiplo limpio de 1: el ancho de bin resultante (ej. 0.75) hace
    que algunos bins caigan justo sobre un entero alcanzable y otros caigan en
    el hueco entre dos enteros, donde no puede haber ningun dato por
    construccion -- no es un problema de los datos, es un desajuste entre el
    binning y la granularidad real de la variable.

    Si la columna es de enteros (dentro de tolerancia de punto flotante), se
    devuelve un array de bordes alineados a esa granularidad: separados por un
    "paso" entero elegido para no superar max_bins, empezando en
    minimo - 0.5 -- con paso entero y arranque en un semientero, cada bin
    cubre un rango cerrado de enteros consecutivos sin dejar huecos posibles
    entre bins, sea cual sea el paso.

    Si la columna NO es de enteros (razones/promedios como pct_victorias_con,
    puntos_por_partido, posicion_promedio), se devuelve max_bins sin cambios:
    la acumulacion en valores "redondos" de esas variables (ej. 0.5 en una
    razon victorias/partidos) es una caracteristica real del dato, no un
    artefacto de graficado, y no corresponde corregirla aca.
    """
    valores_unicos = datos.unique()
    if len(valores_unicos) == 0:
        return max_bins
    es_entero = np.allclose(valores_unicos, np.round(valores_unicos))
    if not es_entero:
        return max_bins

    minimo, maximo = datos.min(), datos.max()
    rango = maximo - minimo
    if rango <= 0:
        return max_bins

    paso = max(1, int(np.ceil((rango + 1) / max_bins)))
    return np.arange(minimo - 0.5, maximo + paso + 0.5, paso)


def graficar_histograma(serie, titulo, ruta_png):
    datos = serie.dropna()
    if datos.empty:
        return
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.hist(datos, bins=elegir_bins(datos), color=estilo.COLOR_PRINCIPAL, edgecolor="white")
    ax.set_title(titulo)
    ax.set_xlabel(titulo)
    ax.set_ylabel("frecuencia")
    fig.tight_layout()
    fig.savefig(ruta_png, dpi=120)
    plt.close(fig)


def graficar_barras_booleana(serie, titulo, ruta_png):
    # Orden y color FIJOS (True/False/NaN), no por frecuencia -- la identidad
    # (True siempre azul, False siempre naranja, faltante siempre gris) tiene
    # que ser la misma en todos los graficos del script, no reasignarse segun
    # cual sea mas frecuente en cada columna en particular.
    #
    # fillna("NaN") ANTES de value_counts, no despues: si el NaN llega vivo
    # (float) hasta el reindex de mas abajo, no matchea la clave de texto
    # "NaN" y esa proporcion se pierde en silencio -- mismo tipo de bug que
    # ya habiamos pisado antes con el grafico de barras booleano.
    etiquetas = serie.map({True: "True", False: "False"}).fillna("NaN")
    orden = ["True", "False", "NaN"]
    colores = [estilo.COLOR_PRINCIPAL, estilo.COLOR_SECUNDARIO, estilo.COLOR_NEUTRO]

    conteo = etiquetas.value_counts(dropna=False, normalize=True).reindex(orden, fill_value=0.0)

    fig, ax = plt.subplots(figsize=(4, 4))
    ax.bar(orden, conteo.values, color=colores)
    ax.set_title(titulo)
    ax.set_ylabel("proporcion")
    fig.tight_layout()
    fig.savefig(ruta_png, dpi=120)
    plt.close(fig)


def graficar_barras_categorica(serie, titulo, ruta_png, top_n=15):
    conteo = serie.value_counts(dropna=True, normalize=True).head(top_n)
    if conteo.empty:
        return
    fig, ax = plt.subplots(figsize=(7, max(3, 0.3 * len(conteo))))
    etiquetas = [str(x) for x in conteo.index][::-1]
    ax.barh(etiquetas, conteo.values[::-1], color=estilo.COLOR_PRINCIPAL)
    ax.set_title(titulo)
    ax.set_xlabel("proporcion")
    fig.tight_layout()
    fig.savefig(ruta_png, dpi=120)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Bivariado (contra DV)
# ---------------------------------------------------------------------------

def calcular_correlaciones_numericas(dataset, columnas, dv, n_min=30):
    filas = []
    for col in columnas:
        sub = pd.DataFrame({col: serie_efectiva(dataset, col), dv: dataset[dv]}).dropna()
        if len(sub) < n_min:
            pearson = spearman = None
        else:
            pearson = sub[col].corr(sub[dv], method="pearson")
            spearman = sub[col].corr(sub[dv], method="spearman")
        filas.append({
            "columna": col, "n_obs": len(sub), "pearson": pearson, "spearman": spearman,
            "piso_confiabilidad": COLUMNAS_CON_PISO_CONFIABILIDAD.get(col, ""),
        })
    tabla = pd.DataFrame(filas)
    tabla["_abs_pearson"] = tabla["pearson"].abs()
    tabla = tabla.sort_values("_abs_pearson", ascending=False).drop(columns="_abs_pearson")
    return tabla.reset_index(drop=True)


def tabla_bivariado_grupos(dataset, columna, dv):
    return (
        dataset.groupby(columna, dropna=False)[dv]
        .agg(media="mean", mediana="median", n="count")
        .reset_index()
        .sort_values("media", ascending=False)
    )


def graficar_curva_edad(dataset, dv, ruta_png):
    sub = dataset[[COLUMNA_EDAD, dv]].dropna()
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.hexbin(sub[COLUMNA_EDAD], sub[dv], gridsize=40, cmap=estilo.CMAP_SECUENCIAL, mincnt=1)

    sub = sub.copy()
    sub["edad_entera"] = sub[COLUMNA_EDAD].round().astype(int)
    mediana_por_edad = sub.groupby("edad_entera")[dv].median()
    ax.plot(mediana_por_edad.index, mediana_por_edad.values, color=estilo.COLOR_SECUNDARIO,
            linewidth=2, label="mediana por edad")

    ax.set_xlabel("edad")
    ax.set_ylabel(dv)
    ax.set_title(f"{dv} vs edad")
    ax.legend()
    fig.tight_layout()
    fig.savefig(ruta_png, dpi=120)
    plt.close(fig)


def graficar_heatmap_correlaciones(dataset, columnas, ruta_png):
    # Mismo enmascarado que la tabla de correlaciones y el resumen univariado
    # -- si no se aplica aca tambien, el heatmap queda inconsistente con el
    # resto del EDA para las columnas con piso de confiabilidad.
    marco = pd.DataFrame({col: serie_efectiva(dataset, col) for col in columnas})
    corr = marco.corr(method="pearson")
    n = len(columnas)
    fig, ax = plt.subplots(figsize=(max(6, 0.3 * n), max(6, 0.3 * n)))
    im = ax.imshow(corr.values, cmap=estilo.CMAP_DIVERGENTE, vmin=-1, vmax=1)
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(columnas, rotation=90, fontsize=6)
    ax.set_yticklabels(columnas, fontsize=6)
    fig.colorbar(im, ax=ax, shrink=0.7)
    ax.set_title("Correlacion (Pearson) entre predictores numericos y la DV")
    fig.tight_layout()
    fig.savefig(ruta_png, dpi=150)
    plt.close(fig)


def main():
    estilo.aplicar_estilo()

    dataset = cargar_dataset_modelable()
    print(f"Dataset: {dataset.shape[0]} filas, {dataset.shape[1]} columnas.")

    # Subcarpeta propia para este script (reports/e01_analisis_exploratorio/ y
    # reports/figuras/e01_analisis_exploratorio/) -- evita que sus tablas y
    # figuras se mezclen con las de otros scripts de EDA.
    ruta_reports = config.ruta_reports_script(Path(__file__).stem)
    ruta_figuras = config.ruta_figuras_script(Path(__file__).stem)

    # --- Clasificacion de columnas ---
    columnas_predictoras = [
        c for c in dataset.columns
        if c not in COLUMNAS_EXCLUIR + COLUMNAS_DV + [COLUMNA_EDAD]
    ]

    numericas, booleanas, categoricas = [], [], []
    for col in columnas_predictoras:
        tipo = clasificar_columna(dataset[col])
        {"numerica": numericas, "booleana": booleanas, "categorica": categoricas}[tipo].append(col)

    print(f"\nPredictoras: {len(columnas_predictoras)} totales "
          f"({len(numericas)} numericas, {len(booleanas)} booleanas, {len(categoricas)} categoricas).")

    # === UNIVARIADO ===
    print("\n=== Univariado: variable dependiente y edad ===")
    for col in COLUMNAS_DV + [COLUMNA_EDAD]:
        print(f"\n{col}:")
        print(dataset[col].describe())
        graficar_histograma(dataset[col], col, ruta_figuras / f"univariado_{col}.png")

    print("\nColumnas con piso de confiabilidad aplicado en este EDA (el dataset guardado no cambia):")
    for col, flag in COLUMNAS_CON_PISO_CONFIABILIDAD.items():
        if col in dataset.columns:
            con_valor = dataset[col].notna()
            excluidos = (con_valor & ~dataset[flag].fillna(False)).sum()
            print(f"  {col}: {excluidos} de {con_valor.sum()} filas con valor excluidas por {flag}=False")

    for col in numericas:
        graficar_histograma(serie_efectiva(dataset, col), col, ruta_figuras / f"univariado_{col}.png")
    for col in booleanas:
        graficar_barras_booleana(dataset[col], col, ruta_figuras / f"univariado_{col}.png")
    for col in categoricas:
        n_unicos = dataset[col].nunique(dropna=True)
        if n_unicos <= CARDINALIDAD_MAX_GRAFICO:
            graficar_barras_categorica(dataset[col], col, ruta_figuras / f"univariado_{col}.png")
        else:
            print(f"'{col}': {n_unicos} categorias distintas -- se omite el grafico "
                  "(alta cardinalidad), queda en la tabla resumen.")

    resumen_univariado = pd.concat([
        resumen_univariado_numerico(dataset, numericas),
        resumen_univariado_booleano(dataset, booleanas),
        resumen_univariado_categorico(dataset, categoricas),
    ], ignore_index=True)

    ruta_resumen = ruta_reports / "resumen_univariado.csv"
    guardar_csv_legible(resumen_univariado, ruta_resumen)
    print(f"\nResumen univariado guardado en: {ruta_resumen}")
    print("\nColumnas con mayor % de nulos:")
    print(resumen_univariado.sort_values("pct_nulos", ascending=False).head(15).to_string(index=False))

    # === BIVARIADO (contra DV) ===
    print(f"\n=== Bivariado contra {DV} ===")

    graficar_curva_edad(dataset, DV, ruta_figuras / "bivariado_edad_vs_dv.png")
    print(f"Curva edad-vs-{DV} guardada (bivariado_edad_vs_dv.png).")

    tabla_corr = calcular_correlaciones_numericas(dataset, numericas, DV)
    ruta_corr = ruta_reports / "bivariado_correlaciones_numericas.csv"
    guardar_csv_legible(tabla_corr, ruta_corr)
    print(f"\nTop 15 predictores numericos por |correlacion de Pearson| con {DV}:")
    print(tabla_corr.head(15).to_string(index=False))

    graficar_heatmap_correlaciones(dataset, [DV] + numericas, ruta_figuras / "bivariado_heatmap_correlaciones.png")

    print(f"\n--- Booleanas vs {DV} ---")
    for col in booleanas:
        print(f"\n{col}:")
        print(tabla_bivariado_grupos(dataset, col, DV).to_string(index=False))

    print(f"\n--- Categoricas vs {DV} (solo cardinalidad <= {CARDINALIDAD_MAX_GRAFICO}) ---")
    for col in categoricas:
        n_unicos = dataset[col].nunique(dropna=True)
        if n_unicos <= CARDINALIDAD_MAX_GRAFICO:
            print(f"\n{col}:")
            print(tabla_bivariado_grupos(dataset, col, DV).to_string(index=False))
        else:
            print(f"\n{col}: se omite (alta cardinalidad, {n_unicos} categorias).")

    print(f"\nFiguras guardadas en: {ruta_figuras}")

    return dataset, resumen_univariado, tabla_corr


if __name__ == "__main__":
    dataset, resumen_univariado, tabla_correlaciones_numericas = main()