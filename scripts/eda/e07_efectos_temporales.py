"""
Analisis exploratorio (e0X, 06/10/2026): diagnosticos previos a los cambios que
salieron de la tutoria con Alan. NO modifica datos ni decide nada -- junta la
evidencia para decidir (a) como tratar el tiempo en el modelo (inflacion del
mercado, pandemia), (b) si hace falta tocar el panel (valor previo, tarjetas) y
(c) que variantes de muestra correr como sensibilidad (con/sin porteros).

Cubre los chequeos que NO necesitan un modelo ajustado. Quedan para m01 (porque
son comparaciones de modelos): contribucion de la reputacion del club vendedor,
la sensibilidad con/sin porteros y sin pandemia a nivel modelo, y el
componente autorregresivo.

SECCIONES (cada una guarda su(s) tabla(s) en reports/e07_efectos_temporales/ y
su(s) figura(s) en reports/figuras/e07_efectos_temporales/):

  1. Serie del valor por temporada (global, y sin porteros).
       -> serie_valor_por_temporada.csv, serie_valor_por_temporada.png
  2. Serie por posicion -- incluye la pregunta del tutor: todos los porteros de
     todos los equipos en 2018 vs 2019 (grupo homogeneo: aisla inflacion de
     cambio de composicion). Generalizado a todas las posiciones.
       -> serie_valor_por_posicion.csv, serie_valor_por_posicion.png
  2b. Deriva anual (% por anio) por grupo -- el chequeo de Alan sobre porteros.
       -> deriva_anual_por_grupo.csv
  2c. COHORTE FIJA ALEATORIA (la lectura correcta del chequeo de Alan): se toma
     el MISMO grupo de jugadores, elegido al azar, y se sigue su valor de
     mercado a lo largo de una ventana de temporadas. Asi el recambio de
     plantel no puede explicar ningun movimiento. Se reporta la trayectoria
     acumulada (% respecto de la temporada inicial) de N_SORTEOS grupos
     aleatorios (mediana y banda 5-95), la del panel balanceado completo, y la
     de cada banda de edad al inicio de la ventana (un grupo fijo envejece: ver
     CAVEAT en la seccion).
       -> cohorte_aleatoria_trayectoria.csv, cohorte_aleatoria_resumen.csv,
          cohorte_aleatoria_<ventana>.png
  2d. DESCOMPOSICION "SE QUEDAN vs ENTRAN/SALEN" (sigue a 2c): el valor medio
     del panel, ajustado por edad, sube de una temporada a la siguiente por dos
     motivos: (a) los jugadores que estaban en ambas temporadas cambian de
     valor ("dentro"), (b) cambia quien esta en el panel ("recambio": entran
     jugadores y salen otros). Si el nivel sube pero el "dentro" no, la subida
     viene de la composicion y no de una reevaluacion general del mercado.
       -> recambio_por_temporada.csv, recambio_acumulado.png
  2e. HUECOS DE COBERTURA (sigue a 2d): dos tipos de hueco que explicarian las
     anomalias de 2021 y 2024-25. Tipo A: el jugador tiene fila en t-1 y t+1
     pero NO en t (fila ausente). Tipo B: tiene fila en t pero sin valuacion.
     Para cada tipo, compara a los jugadores que faltan con los que siguen
     presentes (valor, minutos y edad en t-1, % arqueros) y mide si el hueco se
     concentra en pocos clubes (columna club_id) o esta repartido. Si los que
     faltan valen mucho menos que los que quedan, el hueco infla la media.
       -> huecos_tasas_por_temporada.csv, huecos_perfil.csv, huecos_tasas.png
  2f. DISTRIBUCION DE MINUTOS POR TEMPORADA (sigue a 2e): cuantas filas hay por
     tramo de minutos jugados (<450, 450-900, 900-1800, >=1800, sin dato) y su
     valor medio. Si en 2021 faltan filas de pocos minutos (en numeros
     absolutos, no solo en %), eso explica por que la media sube ese anio.
       -> minutos_por_tramo_y_temporada.csv, minutos_por_tramo.png
  3. "Jugador promedio" por banda de edad y temporada.
       -> serie_valor_por_banda_edad.csv, serie_valor_por_banda_edad.png
  4. Crecimiento INTRA-jugador (log V_{t+1} - log V_t) por banda de edad y
     temporada. Es la lectura mas limpia de "inflacion" porque compara al
     mismo jugador consigo mismo un anio despues, asi que el recambio de
     plantel no entra.
       -> crecimiento_intrajugador_por_banda_y_temporada.csv, .png
  5. Pandemia: volumen de juego, valuaciones faltantes, media del valor y
     composicion del panel (filas, clubes, filas por club) por temporada, con
     2019 y 2020 marcadas. La composicion sirve para revisar 2021 (menos filas
     y mas minutos por fila que las temporadas vecinas en la primera corrida).
       -> pandemia_por_temporada.csv, pandemia_por_temporada.png
  6. Altura: por temporada, por cohorte de nacimiento (aprox.), por posicion y
     por banda de edad.
       -> altura_*.csv, altura_*.png
  7. "Dejar el valor de antes" (necesita las tablas crudas; se omite con
     --omitir-crudas): (a) valuaciones que existen en player_valuations pero no
     tienen fila en el panel, clasificadas segun donde caen respecto de la
     carrera del jugador en el panel; (b) filas del panel SIN valuacion en esa
     temporada, y cuan vieja es la ultima valuacion previa disponible.
       -> valor_previo_*.csv
     (c) PERFIL de las valuaciones ANTES DE ENTRAR al panel (lo que Alan pidio
     "dejar": p. ej. Haaland sin datos de rendimiento hasta llegar a una liga
     top): cuantas filas jugador-temporada serian, cuanto valen segun cuantas
     temporadas faltan para entrar y cuanto crece el valor hasta la primera
     temporada del panel (ojo: son solo jugadores que despues SI llegaron, o
     sea sesgo de supervivencia).
       -> valor_previo_pre_entrada_*.csv
     (d) VALOR PREVIO COMO VARIABLE (la alternativa a agregar filas): para cada
     fila del panel, la ultima valuacion anterior a esa temporada (de todas las
     valuaciones, tengan o no fila en el panel) y su rezago. Mide: cobertura
     (por rezago y en la primera temporada de cada jugador), poder predictivo
     (R2 de la edad sola vs edad + valor previo; es la fuerza del componente
     autorregresivo) y salto de ingreso (cambio de valor en la primera
     temporada del panel vs el de quien ya estaba, por banda de edad).
       -> valor_previo_variable_*.csv
  8. Tarjetas amarillas y rojas por separado (por 90, con el mismo piso de
     confiabilidad de minutos que tarjetas_90).
       -> tarjetas_*.csv, tarjetas_*.png
  9. Con y sin porteros (descriptivo): correlacion de la especificacion cerrada
     (4 contexto + 6 rendimiento) contra la DV en todos / sin porteros / solo
     porteros.
       -> porteros_correlaciones_spec_vs_dv.csv

ESTADISTICO PRINCIPAL = MEDIA de log(valor), NO la mediana (cambio 06/10, tras la
primera corrida real): las valuaciones de Transfermarkt caen en escalones
redondos (800k, 1M, 1.5M...), asi que la mediana queda clavada en un escalon
durante anios (1.000.000 EUR de 2012 a 2020) y no ve los movimientos del
mercado. Por la misma razon, en la seccion 4 la mediana de crecimiento da
exactamente 0 para casi todo un grupo: se usa la media de delta-log y se agrega
el % de jugadores cuyo valor no cambia de un anio al otro. La mediana y los
cuartiles siguen en los CSV como referencia.

CHEQUEO DE ALAN (secciones 2 y 2b): un grupo cuya calidad no deberia cambiar
(todos los porteros de todos los equipos) NO deberia mostrar un movimiento
grupal de 3-4% anual tipo inflacion; sus valores deberian mantenerse parejos.
La seccion 2b calcula la deriva anual (% por anio) de la media de log(valor) de
los porteros y de cada posicion, con y sin las temporadas de pandemia, y una
version ajustada por edad (para que un cambio en la edad media del grupo no
tape ni invente una deriva).

CAVEAT METODOLOGICO (relevante para m01, no solo para este script): edad,
temporada y efecto fijo de jugador no se pueden separar de forma no parametrica
(edad = temporada - anio de nacimiento, y el anio de nacimiento queda absorbido
por el efecto de jugador). Por eso la seccion 4 compara bandas de edad
ANCHAS dentro de cada temporada y asume que el perfil de envejecimiento es
estable entre temporadas. En el modelo, el efecto temporal necesita una
restriccion explicita (por ejemplo, curva de edad suave + efecto de temporada
con prior que lo ancle), no se identifica "gratis".

Corre sobre el dataset_modelable MAS RECIENTE en data/processed/ (via
e01.cargar_dataset_modelable()). Convencion de temporada: anio de inicio (la
temporada 2019 es la 2019/20, la que se corta en marzo de 2020).

Uso:
    uv run scripts/eda/e07_efectos_temporales.py
    uv run scripts/eda/e07_efectos_temporales.py --omitir-crudas   # sin la seccion 7
"""

import argparse
import re
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

DV = "log_valor_mercado"
COL_EUR = "valor_mercado_eur"
COL_JUGADOR = "player_id"
COL_TEMPORADA = "season"
COL_EDAD = "edad"
COL_POSICION = "posicion_amplia_predominante"
COL_ALTURA = "altura_cm"

COLUMNAS_REQUERIDAS = [COL_JUGADOR, COL_TEMPORADA, DV, COL_EUR, COL_EDAD, COL_POSICION]

N_MIN_CELDA = 30  # mismo piso que el resto de e0X: celdas con menos filas quedan en NaN
TEMPORADAS_PANDEMIA = (2019, 2020)  # anio de inicio: 2019/20 (corte en marzo) y 2020/21 (sin publico)
ANIOS_TUTOR = (2018, 2019)

# Bandas de edad (borde izquierdo incluido). Anchas a proposito -- ver CAVEAT en el docstring.
LIMITES_BANDA_EDAD = [0, 20, 23, 27, 31, 200]
ETIQUETAS_BANDA_EDAD = ["<20", "20-22", "23-26", "27-30", "31+"]

ALTURA_MIN, ALTURA_MAX = 140, 220  # mismo rango de plausibilidad que d08/d09
PATRON_PORTERO = r"arquer|portero|goalkeep|keeper"

# Seccion 2c (cohorte fija aleatoria, chequeo de Alan)
VENTANAS_COHORTE = [(2012, 2018), (2021, 2025)]  # antes de la pandemia / despues
N_COHORTE = 500          # tamanio de cada grupo aleatorio (si hay menos jugadores: la mitad del balanceado)
N_SORTEOS = 200          # cantidad de grupos aleatorios distintos por ventana
SEMILLA_COHORTE = 2026   # semilla fija: la corrida es reproducible

_COLORES_SERIES = [estilo.COLOR_PRINCIPAL, estilo.COLOR_SECUNDARIO, "#0b0b0b", estilo.COLOR_NEUTRO]
_MARCADORES = ["o", "s", "^", "D", "v"]


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------

def agregar_banda_edad(dataset):
    d = dataset.copy()
    d["banda_edad"] = pd.cut(
        d[COL_EDAD], bins=LIMITES_BANDA_EDAD, labels=ETIQUETAS_BANDA_EDAD, right=False
    )
    return d


def detectar_porteros(dataset):
    """
    Mascara booleana de porteros, descubriendo en vivo como se llama la
    categoria en `posicion_amplia_predominante` (no se hardcodea el nombre).
    Filas con posicion NaN quedan como NO portero. Falla con un mensaje util
    si ninguna categoria matchea, en vez de seguir con una mascara vacia.
    """
    valores = [v for v in dataset[COL_POSICION].dropna().unique()]
    etiquetas = [v for v in valores if re.search(PATRON_PORTERO, str(v), re.IGNORECASE)]
    if not etiquetas:
        raise ValueError(
            f"No se encontro ninguna categoria de portero en {COL_POSICION}. "
            f"Categorias presentes: {sorted(map(str, valores))}. Ajustar PATRON_PORTERO."
        )
    print(f"Porteros detectados como: {etiquetas} "
          f"({dataset[COL_POSICION].isin(etiquetas).mean():.1%} de las filas)")
    return dataset[COL_POSICION].isin(etiquetas)


def estadisticos_por_grupo(dataset, grupos, n_min=N_MIN_CELDA):
    """n, media/mediana de log DV y mediana/cuartiles del valor en euros, por grupo."""
    grupos = [grupos] if isinstance(grupos, str) else list(grupos)
    base = dataset.dropna(subset=[DV, COL_EUR])
    tabla = (
        base.groupby(grupos, observed=True)
        .agg(
            n=(DV, "size"),
            media_log=(DV, "mean"),
            edad_media=(COL_EDAD, "mean"),
            mediana_log=(DV, "median"),
            mediana_eur=(COL_EUR, "median"),
            p25_eur=(COL_EUR, lambda s: s.quantile(0.25)),
            p75_eur=(COL_EUR, lambda s: s.quantile(0.75)),
        )
        .reset_index()
    )
    columnas_stats = ["media_log", "edad_media", "mediana_log", "mediana_eur", "p25_eur", "p75_eur"]
    tabla.loc[tabla["n"] < n_min, columnas_stats] = np.nan
    return tabla


def agregar_variacion_interanual(tabla, grupo_extra=None):
    """
    Variacion % de la media geometrica del valor vs. la temporada anterior (exp
    de la diferencia de medias de log = cociente de medias geometricas). Solo se
    calcula entre temporadas consecutivas: un hueco en la serie deja NaN, no
    una variacion a cuenta de varios anios.
    """
    claves = ([grupo_extra] if isinstance(grupo_extra, str) else list(grupo_extra or []))
    t = tabla.sort_values(claves + [COL_TEMPORADA]).reset_index(drop=True)
    agrupado = t.groupby(claves, observed=True) if claves else t
    diff_log = agrupado["media_log"].diff()
    diff_temp = agrupado[COL_TEMPORADA].diff()
    t["var_media_geom_pct"] = np.where(diff_temp == 1, (np.exp(diff_log) - 1) * 100, np.nan)
    return t


def graficar_lineas(ancha, titulo, ylabel, ruta_png, sombrear_pandemia=True):
    """
    Lineas por serie (columnas de `ancha`, indice = temporada). Paleta de
    estilo_graficos (2 colores + negro + gris) con marcadores distintos y
    etiqueta directa al final de cada linea, para no depender solo del color.
    """
    ancha = ancha.dropna(how="all")
    if ancha.empty:
        print(f"AVISO: sin datos para graficar '{titulo}'.")
        return
    fig, ax = plt.subplots(figsize=(8, 4.6))
    for i, col in enumerate(ancha.columns):
        serie = ancha[col].dropna()
        if serie.empty:
            continue
        ax.plot(serie.index, serie.values, color=_COLORES_SERIES[i % len(_COLORES_SERIES)],
                marker=_MARCADORES[i % len(_MARCADORES)], lw=2, ms=4)
        ax.annotate(str(col), (serie.index[-1], serie.values[-1]), xytext=(5, 0),
                    textcoords="offset points", fontsize=8, va="center")
    if sombrear_pandemia:
        ax.axvspan(TEMPORADAS_PANDEMIA[0] - 0.5, TEMPORADAS_PANDEMIA[-1] + 0.5,
                   color=estilo.COLOR_NEUTRO, alpha=0.25, lw=0)
    ax.set_xticks(list(ancha.index))
    ax.tick_params(axis="x", labelrotation=45)
    ax.set_xlabel("temporada (anio de inicio)")
    ax.set_ylabel(ylabel)
    ax.set_title(titulo)
    ax.margins(x=0.1)
    fig.tight_layout()
    fig.savefig(ruta_png, dpi=120)
    plt.close(fig)


def spearman_sin_scipy(a, b):
    """
    Spearman = Pearson sobre los rangos (rangos promedio en empates, igual que
    scipy). Se usa en vez de Series.corr(method="spearman") porque pandas
    importa scipy.stats para eso, y en esta maquina Windows (control de
    aplicaciones) puede bloquear los DLL de scipy (06/10: _qhull/messagestream).
    """
    return a.rank().corr(b.rank())


def pivot_ancho(tabla, columnas, valores):
    return tabla.pivot_table(index=COL_TEMPORADA, columns=columnas, values=valores, observed=True)


# ---------------------------------------------------------------------------
# 1-3. Series del valor
# ---------------------------------------------------------------------------

def seccion_serie_global(dataset, es_portero, ruta_reports, ruta_figuras):
    total = agregar_variacion_interanual(estadisticos_por_grupo(dataset, COL_TEMPORADA))
    sin = estadisticos_por_grupo(dataset[~es_portero], COL_TEMPORADA)[[COL_TEMPORADA, "n", "media_log"]]
    sin = sin.rename(columns={"n": "n_sin_porteros", "media_log": "media_log_sin_porteros"})
    serie = total.merge(sin, on=COL_TEMPORADA, how="left")

    e01.guardar_csv_legible(serie, ruta_reports / "serie_valor_por_temporada.csv")
    print("\n[1] Valor por temporada (global):")
    print(serie.round(3).to_string(index=False))

    ancha = serie.set_index(COL_TEMPORADA)[["media_log", "media_log_sin_porteros"]]
    ancha.columns = ["todos", "sin porteros"]
    graficar_lineas(ancha, "Media de log(valor de mercado) por temporada", DV,
                    ruta_figuras / "serie_valor_por_temporada.png")
    return serie


def seccion_serie_por_posicion(dataset, es_portero, ruta_reports, ruta_figuras):
    tabla = agregar_variacion_interanual(
        estadisticos_por_grupo(dataset, [COL_POSICION, COL_TEMPORADA]), grupo_extra=COL_POSICION
    )
    e01.guardar_csv_legible(tabla, ruta_reports / "serie_valor_por_posicion.csv")

    ancha = pivot_ancho(tabla, COL_POSICION, "media_log")
    graficar_lineas(ancha, "Media de log(valor) por posicion y temporada", DV,
                    ruta_figuras / "serie_valor_por_posicion.png")

    # Pregunta literal del tutor: todos los porteros de todos los equipos, 2018 vs 2019.
    porteros = dataset[es_portero]
    t_por = estadisticos_por_grupo(porteros, COL_TEMPORADA).set_index(COL_TEMPORADA)
    a0, a1 = ANIOS_TUTOR
    print(f"\n[2] Porteros (todos los equipos), {a0} vs {a1}:")
    if a0 in t_por.index and a1 in t_por.index and t_por.loc[[a0, a1], "media_log"].notna().all():
        fila = t_por.loc[[a0, a1], ["n", "media_log", "edad_media", "mediana_log", "mediana_eur"]]
        print(fila.round(3).to_string())
        ratio = np.exp(t_por.loc[a1, "media_log"] - t_por.loc[a0, "media_log"])
        print(f"  Media geometrica del valor en {a1} / en {a0} = {ratio:.3f}  ({(ratio - 1) * 100:+.1f}%)")
    else:
        print(f"  AVISO: sin datos suficientes (n >= {N_MIN_CELDA}) para porteros en {a0} y/o {a1}.")
    print("\n  Serie completa de porteros:")
    print(t_por.round(3).reset_index().to_string(index=False))

    print("\n  Composicion: % de filas que son porteros, por temporada")
    comp = es_portero.groupby(dataset[COL_TEMPORADA]).mean()
    print((comp * 100).round(1).to_string())
    return tabla


def pendiente_anual_pct(serie_media_log, excluir=()):
    """
    Deriva anual (% por anio) de una serie de media de log(valor) por
    temporada, via regresion lineal sobre las medias por temporada. Devuelve
    (deriva_pct, error_estandar_pct, n_temporadas). Con menos de 4 temporadas
    no calcula nada (NaN).
    """
    s = serie_media_log.dropna()
    s = s[~s.index.isin(list(excluir))]
    if len(s) < 4:
        return np.nan, np.nan, len(s)
    coef, cov = np.polyfit(s.index.astype(float), s.values, 1, cov=True)
    return (np.exp(coef[0]) - 1) * 100, np.sqrt(cov[0, 0]) * 100, len(s)


def deriva_ajustada_por_edad_pct(df, excluir=()):
    """
    Deriva anual (% por anio) del log(valor) controlando por edad (cuadratica),
    por minimos cuadrados sobre filas jugador-temporada. No es un modelo con
    efecto de jugador: solo sirve para ver si un cambio en la edad media del
    grupo esta tapando o inventando la deriva.
    """
    d = df.dropna(subset=[DV, COL_EDAD, COL_TEMPORADA])
    d = d[~d[COL_TEMPORADA].isin(list(excluir))]
    if len(d) < N_MIN_CELDA:
        return np.nan
    edad = d[COL_EDAD].to_numpy(dtype=float)
    anio = d[COL_TEMPORADA].to_numpy(dtype=float)
    X = np.column_stack([np.ones(len(d)), anio - anio.min(), edad, edad ** 2])
    beta, *_ = np.linalg.lstsq(X, d[DV].to_numpy(dtype=float), rcond=None)
    return (np.exp(beta[1]) - 1) * 100


def seccion_deriva_anual(dataset, es_portero, ruta_reports):
    """
    2b. Chequeo de Alan: un grupo cuya calidad no cambia (los porteros) no
    deberia mostrar una deriva grupal de 3-4% anual. Se calcula para porteros,
    jugadores de campo y cada posicion, usando solo filas con posicion conocida
    (la posicion falta en 2012: piso de cobertura de game_lineups).
    """
    con_pos = dataset[dataset[COL_POSICION].notna()]
    grupos = {"porteros": con_pos[es_portero.loc[con_pos.index]],
              "jugadores_de_campo": con_pos[~es_portero.loc[con_pos.index]]}
    for pos in sorted(con_pos[COL_POSICION].unique(), key=str):
        grupos[f"posicion={pos}"] = con_pos[con_pos[COL_POSICION] == pos]

    ventanas = {"todas_las_temporadas": (), "sin_pandemia_2019_2020": TEMPORADAS_PANDEMIA}
    filas = []
    for nombre, df in grupos.items():
        medias = estadisticos_por_grupo(df, COL_TEMPORADA).set_index(COL_TEMPORADA)["media_log"]
        for ventana, excluir in ventanas.items():
            deriva, se, n_temp = pendiente_anual_pct(medias, excluir)
            filas.append({"grupo": nombre, "ventana": ventana, "n_temporadas": n_temp,
                          "deriva_anual_pct": deriva, "error_estandar_pct": se,
                          "deriva_anual_ajustada_edad_pct": deriva_ajustada_por_edad_pct(df, excluir)})
    tabla = pd.DataFrame(filas)
    e01.guardar_csv_legible(tabla, ruta_reports / "deriva_anual_por_grupo.csv")
    print("\n[2b] Deriva anual del valor por grupo (% por anio; chequeo de Alan: los porteros "
          "no deberian mostrar un movimiento grupal tipo inflacion de 3-4%):")
    print(tabla.round(2).to_string(index=False))
    return tabla


# ---------------------------------------------------------------------------
# 2c. Cohorte fija aleatoria
# ---------------------------------------------------------------------------

def matriz_cohorte_balanceada(dataset, t0, t1):
    """
    Panel BALANCEADO de la ventana [t0, t1]: jugadores con valuacion (DV no
    nula) en TODAS las temporadas de la ventana. Devuelve (matriz, ids, edad_t0)
    con matriz de forma (n_jugadores, n_temporadas) de log(valor), columnas en
    orden de temporada, y edad_t0 = edad en la temporada inicial (Serie por id).
    """
    temporadas = list(range(t0, t1 + 1))
    d = dataset[[COL_JUGADOR, COL_TEMPORADA, DV, COL_EDAD]].dropna(subset=[DV])
    d = d[d[COL_TEMPORADA].between(t0, t1)].drop_duplicates([COL_JUGADOR, COL_TEMPORADA])
    ancho = d.pivot(index=COL_JUGADOR, columns=COL_TEMPORADA, values=DV).reindex(columns=temporadas)
    ancho = ancho.dropna(how="any")
    edad_t0 = d[d[COL_TEMPORADA] == t0].set_index(COL_JUGADOR)[COL_EDAD].reindex(ancho.index)
    return ancho.to_numpy(dtype=float), ancho.index.to_numpy(), edad_t0


def trayectorias_sorteos(matriz, tamano, n_sorteos, semilla):
    """
    Para cada sorteo (muestra sin reemplazo de `tamano` filas), trayectoria de
    la media de log(valor) menos su valor en la temporada inicial. Devuelve un
    array (n_sorteos, n_temporadas); la primera columna es 0 por construccion.
    """
    rng = np.random.default_rng(semilla)
    n = matriz.shape[0]
    tamano = min(tamano, n)
    salida = np.empty((n_sorteos, matriz.shape[1]))
    for i in range(n_sorteos):
        idx = rng.choice(n, size=tamano, replace=False)
        medias = matriz[idx].mean(axis=0)
        salida[i] = medias - medias[0]
    return salida


def seccion_cohorte_aleatoria(dataset, ruta_reports, ruta_figuras):
    """
    2c. Chequeo de Alan, lectura correcta: el MISMO grupo de jugadores (al azar)
    seguido en el tiempo. Si el mercado "inflara" 3-4% anual de forma
    generalizada, la trayectoria de un grupo fijo subiria ~3-4% por anio; si los
    valores se mantienen parejos, queda plana.

    CAVEAT de envejecimiento: un grupo fijo envejece un anio por temporada, y
    la curva de edad no es plana (sube hasta ~26-27 y baja despues). Por eso se
    agregan las bandas de edad al inicio de la ventana: la de 23-26 (cerca del
    pico) es la lectura menos contaminada por envejecimiento -- si ahi hay
    deriva positiva, el envejecimiento la subestima, no la explica. Las bandas
    jovenes (<23) deberian subir y las de 31+ bajar aunque no hubiera inflacion.

    CAVEAT de supervivencia: el panel balanceado exige valuacion en todas las
    temporadas, o sea que se queda con jugadores que siguieron en las 14 ligas
    del panel; quien cayo de nivel y se fue queda afuera y eso sesga hacia
    arriba. La ventana corta pre-pandemia limita ese sesgo.
    """
    print("\n[2c] COHORTE FIJA ALEATORIA (mismo grupo de jugadores seguido en el tiempo)")
    filas_tray, filas_res = [], []
    for t0, t1 in VENTANAS_COHORTE:
        matriz, ids, edad_t0 = matriz_cohorte_balanceada(dataset, t0, t1)
        temporadas = list(range(t0, t1 + 1))
        etiqueta = f"{t0}-{t1}"
        n = matriz.shape[0]
        print(f"\n  Ventana {etiqueta}: {n} jugadores con valuacion en las {len(temporadas)} temporadas.")
        if n < 2 * N_MIN_CELDA:
            print("  AVISO: panel balanceado demasiado chico; se omite la ventana.")
            continue
        tamano = N_COHORTE if n >= 2 * N_COHORTE else n // 2
        tray = trayectorias_sorteos(matriz, tamano, N_SORTEOS, SEMILLA_COHORTE)
        acum = (np.exp(tray) - 1) * 100
        mediana = np.median(acum, axis=0)
        p05, p95 = np.percentile(acum, [5, 95], axis=0)
        medias_all = matriz.mean(axis=0)
        acum_all = (np.exp(medias_all - medias_all[0]) - 1) * 100
        deriva_all = pendiente_anual_pct(pd.Series(medias_all, index=temporadas))[0]

        # Una cohorte puntual (el primer sorteo con la misma semilla), para verla concreta.
        rng = np.random.default_rng(SEMILLA_COHORTE)
        idx0 = rng.choice(n, size=tamano, replace=False)
        m0 = matriz[idx0].mean(axis=0)
        acum_0 = (np.exp(m0 - m0[0]) - 1) * 100

        # Cambio entre pares consecutivos del grupo completo: % sin cambio y variacion media
        delta = np.diff(matriz, axis=1)
        pct_sin_cambio = (np.abs(delta) < 1e-9).mean(axis=0) * 100
        var_geom = (np.exp(delta.mean(axis=0)) - 1) * 100

        for j, t in enumerate(temporadas):
            filas_tray.append(dict(ventana=etiqueta, grupo=f"aleatorio (n={tamano}, mediana de {N_SORTEOS} sorteos)",
                                   temporada=t, n=tamano, acum_pct=mediana[j], acum_p05=p05[j], acum_p95=p95[j]))
            filas_tray.append(dict(ventana=etiqueta, grupo="panel balanceado completo", temporada=t, n=n,
                                   acum_pct=acum_all[j], acum_p05=np.nan, acum_p95=np.nan))
            filas_tray.append(dict(ventana=etiqueta, grupo="un sorteo concreto", temporada=t, n=tamano,
                                   acum_pct=acum_0[j], acum_p05=np.nan, acum_p95=np.nan))

        # Por banda de edad al inicio de la ventana
        bandas = pd.cut(edad_t0, bins=LIMITES_BANDA_EDAD, labels=ETIQUETAS_BANDA_EDAD, right=False)
        ancha_graf = pd.DataFrame({"aleatorio (mediana)": mediana, "balanceado completo": acum_all}, index=temporadas)
        resumen_bandas = []
        for banda in ETIQUETAS_BANDA_EDAD:
            mask = (bandas == banda).to_numpy()
            nb = int(mask.sum())
            if nb < N_MIN_CELDA:
                continue
            mb = matriz[mask].mean(axis=0)
            ab = (np.exp(mb - mb[0]) - 1) * 100
            deriva_b = pendiente_anual_pct(pd.Series(mb, index=temporadas))[0]
            ancha_graf[f"edad t0 {banda} (n={nb})"] = ab
            for j, t in enumerate(temporadas):
                filas_tray.append(dict(ventana=etiqueta, grupo=f"edad al inicio {banda}", temporada=t, n=nb,
                                       acum_pct=ab[j], acum_p05=np.nan, acum_p95=np.nan))
            resumen_bandas.append((banda, nb, ab[-1], deriva_b))

        filas_res.append(dict(ventana=etiqueta, grupo="panel balanceado completo", n=n,
                              acum_final_pct=acum_all[-1], deriva_anual_pct=deriva_all,
                              pct_sin_cambio_medio=pct_sin_cambio.mean()))
        filas_res.append(dict(ventana=etiqueta, grupo="aleatorio (mediana de sorteos)", n=tamano,
                              acum_final_pct=mediana[-1],
                              deriva_anual_pct=pendiente_anual_pct(
                                  pd.Series(np.median(tray, axis=0), index=temporadas))[0],
                              pct_sin_cambio_medio=np.nan))
        for banda, nb, final, deriva_b in resumen_bandas:
            filas_res.append(dict(ventana=etiqueta, grupo=f"edad al inicio {banda}", n=nb,
                                  acum_final_pct=final, deriva_anual_pct=deriva_b, pct_sin_cambio_medio=np.nan))

        print(f"  Trayectoria acumulada % (base = {t0}); sorteos aleatorios: mediana [p05, p95]:")
        tabla_print = pd.DataFrame({"mediana": mediana, "p05": p05, "p95": p95,
                                    "balanceado": acum_all, "un_sorteo": acum_0}, index=temporadas)
        print(tabla_print.round(1).to_string())
        print(f"  Deriva anual del panel balanceado completo: {deriva_all:+.2f}%/anio "
              f"(lo que Alan espera ~0 si no hay inflacion generalizada)")
        print(f"  Variacion media entre temporadas consecutivas (grupo completo): "
              f"{[f'{t}->{t + 1}: {v:+.1f}%' for t, v in zip(temporadas[:-1], var_geom)]}")
        print(f"  % de jugadores con valor IGUAL de un anio al siguiente: "
              f"{[f'{t}->{t + 1}: {v:.0f}%' for t, v in zip(temporadas[:-1], pct_sin_cambio)]}")
        print("  Por banda de edad al inicio (acumulado final %, deriva %/anio):")
        for banda, nb, final, deriva_b in resumen_bandas:
            print(f"    {banda:>6} (n={nb}): {final:+.1f}% acumulado, {deriva_b:+.2f}%/anio")

        # Figura: banda 5-95 de los sorteos + media del panel balanceado + bandas de edad
        fig, ax = plt.subplots(figsize=(8, 4.8))
        ax.fill_between(temporadas, p05, p95, color=estilo.COLOR_PRINCIPAL, alpha=0.2, lw=0,
                        label=f"{N_SORTEOS} grupos aleatorios (p05-p95)")
        ax.plot(temporadas, mediana, color=estilo.COLOR_PRINCIPAL, lw=2.4, marker="o", ms=4,
                label="grupo aleatorio (mediana)")
        ax.plot(temporadas, acum_all, color="#0b0b0b", lw=1.6, ls="--", label="panel balanceado completo")
        colores_bandas = [estilo.COLOR_SECUNDARIO, estilo.COLOR_NEUTRO, "#7a5195", "#2f9e6b", "#b3261e"]
        for k, col in enumerate([c for c in ancha_graf.columns if c.startswith("edad t0")]):
            ax.plot(temporadas, ancha_graf[col].values, color=colores_bandas[k % 5], lw=1.3,
                    marker=_MARCADORES[k % 5], ms=3, label=col)
        ax.axhline(0, color="#888888", lw=0.8)
        if t0 <= TEMPORADAS_PANDEMIA[-1] and t1 >= TEMPORADAS_PANDEMIA[0]:
            ax.axvspan(TEMPORADAS_PANDEMIA[0] - 0.5, TEMPORADAS_PANDEMIA[-1] + 0.5,
                       color=estilo.COLOR_NEUTRO, alpha=0.2, lw=0)
        ax.set_xticks(temporadas)
        ax.set_xlabel("temporada (anio de inicio)")
        ax.set_ylabel(f"% acumulado respecto de {t0}")
        ax.set_title(f"Mismo grupo de jugadores seguido en el tiempo ({etiqueta})")
        ax.legend(frameon=False, fontsize=7, loc="upper left")
        fig.tight_layout()
        fig.savefig(ruta_figuras / f"cohorte_aleatoria_{t0}_{t1}.png", dpi=120)
        plt.close(fig)

    if filas_tray:
        e01.guardar_csv_legible(pd.DataFrame(filas_tray), ruta_reports / "cohorte_aleatoria_trayectoria.csv")
        e01.guardar_csv_legible(pd.DataFrame(filas_res), ruta_reports / "cohorte_aleatoria_resumen.csv")


# ---------------------------------------------------------------------------
# 2d. Se quedan vs entran/salen
# ---------------------------------------------------------------------------

def descomposicion_recambio(df):
    """
    Descompone, por temporada t, el cambio de la media de r (log(valor) menos el
    efecto de la edad en anios enteros, estimado sobre todo el panel) respecto de
    t-1:

        delta_total = media_r(t) - media_r(t-1)            (todos los presentes)
        dentro      = media(r_t - r_{t-1}) de los que estan en AMBAS temporadas
        recambio    = delta_total - dentro                  (efecto de quien entra y sale)

    "Entra" = tiene valuacion en t y no en t-1; "sale" = la tiene en t-1 y no en
    t. Devuelve un DataFrame con una fila por temporada t (desde la 2da), con
    cambios en log. `df` necesita player_id, season, DV y edad.
    """
    d = df[[COL_JUGADOR, COL_TEMPORADA, DV, COL_EDAD]].dropna().drop_duplicates([COL_JUGADOR, COL_TEMPORADA]).copy()
    d["_edad_ent"] = np.floor(d[COL_EDAD]).clip(17, 38)
    d["r"] = d[DV] - d.groupby("_edad_ent")[DV].transform("mean")
    filas = []
    temporadas = sorted(d[COL_TEMPORADA].unique())
    for t in temporadas[1:]:
        if t - 1 not in temporadas:
            continue
        cur = d[d[COL_TEMPORADA] == t].set_index(COL_JUGADOR)
        prev = d[d[COL_TEMPORADA] == t - 1].set_index(COL_JUGADOR)
        quedan = cur.index.intersection(prev.index)
        entran = cur.index.difference(prev.index)
        salen = prev.index.difference(cur.index)
        if len(quedan) < N_MIN_CELDA:
            continue
        dentro = (cur.loc[quedan, "r"] - prev.loc[quedan, "r"]).mean()
        delta_total = cur["r"].mean() - prev["r"].mean()
        filas.append(dict(
            season=t, n_quedan=len(quedan), n_entran=len(entran), n_salen=len(salen),
            pct_entran=len(entran) / len(cur) * 100,
            r_quedan_t=cur.loc[quedan, "r"].mean(), r_quedan_t_1=prev.loc[quedan, "r"].mean(),
            r_entran=cur.loc[entran, "r"].mean() if len(entran) else np.nan,
            r_salen=prev.loc[salen, "r"].mean() if len(salen) else np.nan,
            edad_entran=cur.loc[entran, COL_EDAD].mean() if len(entran) else np.nan,
            edad_salen=prev.loc[salen, COL_EDAD].mean() if len(salen) else np.nan,
            delta_total=delta_total, dentro=dentro, recambio=delta_total - dentro,
        ))
    return pd.DataFrame(filas)


def seccion_recambio(dataset, ruta_reports, ruta_figuras):
    """
    2d. Si la media (ajustada por edad) sube ~3-4% por anio pero los jugadores
    que se quedan no suben, la subida es composicion. Imprime la tabla por
    temporada y los acumulados (todo el periodo y sin las transiciones de la
    pandemia, t = 2019 y 2020, que son la revaluacion masiva y el rebote).
    """
    print("\n[2d] DESCOMPOSICION: los que se quedan vs los que entran/salen (valor ajustado por edad)")
    tabla = descomposicion_recambio(dataset)
    if tabla.empty:
        print("  AVISO: sin datos suficientes.")
        return tabla
    salida = tabla.copy()
    for c in ("delta_total", "dentro", "recambio"):
        salida[c + "_pct"] = (np.exp(salida[c]) - 1) * 100
    e01.guardar_csv_legible(salida, ruta_reports / "recambio_por_temporada.csv")

    mostrar = salida[["season", "n_quedan", "n_entran", "n_salen", "pct_entran", "edad_entran", "edad_salen",
                      "r_entran", "r_salen", "delta_total_pct", "dentro_pct", "recambio"]].copy()
    mostrar["recambio_pct"] = (np.exp(mostrar.pop("recambio")) - 1) * 100
    print("  Por temporada t (cambios vs t-1, en %, valor ajustado por edad; r_* = media de log(valor) "
          "menos efecto edad, 0 = promedio del panel):")
    print(mostrar.round(2).to_string(index=False))

    sin_pandemia = tabla[~tabla[COL_TEMPORADA].isin(TEMPORADAS_PANDEMIA)]
    for etiqueta, sub in (("todas las transiciones", tabla), ("sin t=2019 y 2020", sin_pandemia)):
        n = len(sub)
        tot, dent, rec = sub["delta_total"].sum(), sub["dentro"].sum(), sub["recambio"].sum()
        print(f"  Acumulado ({etiqueta}, {n} transiciones): total {(np.exp(tot) - 1) * 100:+.1f}% "
              f"= dentro {(np.exp(dent) - 1) * 100:+.1f}% y recambio {(np.exp(rec) - 1) * 100:+.1f}% (se suman en log); "
              f"por anio: total {(np.exp(tot / n) - 1) * 100:+.2f}%, dentro {(np.exp(dent / n) - 1) * 100:+.2f}%, "
              f"recambio {(np.exp(rec / n) - 1) * 100:+.2f}%")

    acum = tabla.set_index(COL_TEMPORADA)[["delta_total", "dentro", "recambio"]].cumsum()
    acum = (np.exp(acum) - 1) * 100
    acum.columns = ["total", "dentro (se quedan)", "recambio (entran/salen)"]
    fig, ax = plt.subplots(figsize=(8, 4.6))
    estilos = [("total", "#0b0b0b", "o"), ("dentro (se quedan)", estilo.COLOR_PRINCIPAL, "s"),
               ("recambio (entran/salen)", estilo.COLOR_SECUNDARIO, "^")]
    for col, color, marcador in estilos:
        ax.plot(acum.index, acum[col], color=color, marker=marcador, lw=2, ms=4, label=col)
    ax.axhline(0, color="#888888", lw=0.8)
    ax.axvspan(TEMPORADAS_PANDEMIA[0] - 0.5, TEMPORADAS_PANDEMIA[-1] + 0.5, color=estilo.COLOR_NEUTRO, alpha=0.25, lw=0)
    ax.set_xticks(list(acum.index))
    ax.tick_params(axis="x", labelrotation=45)
    ax.set_xlabel("temporada (anio de inicio)")
    ax.set_ylabel("% acumulado desde la primera temporada")
    ax.set_title("Cambio acumulado del valor (ajustado por edad): se quedan vs recambio")
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(ruta_figuras / "recambio_acumulado.png", dpi=120)
    plt.close(fig)
    return tabla


# ---------------------------------------------------------------------------
# 2e. Huecos de cobertura
# ---------------------------------------------------------------------------

TEMPORADAS_FOCO_HUECOS = (2021, 2024, 2025)


def perfil_huecos(dataset, t):
    """
    Clasifica a los jugadores de la temporada t-1 (con valuacion en t-1):
      A) fila AUSENTE en t pero con fila en t+1 (hueco; requiere t+1 en el panel)
      B) fila presente en t pero SIN valuacion (DV nula)
      P) presentes en t con valuacion (referencia)
    Devuelve (resumen, tasas): `resumen` = una fila por grupo con n, valor/minutos/
    edad en t-1 y % arqueros; `tasas` = dict con tasa_A (sobre jugadores con
    valuacion en t-1 y fila en t+1) y tasa_B (sobre jugadores con valuacion en t-1
    y fila en t). Los grupos de referencia usan los mismos universos.
    """
    cols = [COL_JUGADOR, COL_TEMPORADA, DV, COL_EDAD, COL_POSICION]
    extra = [c for c in ("minutos_totales", "club_id") if c in dataset.columns]
    d = dataset[cols + extra].drop_duplicates([COL_JUGADOR, COL_TEMPORADA])

    def tomar(temp):
        return d[d[COL_TEMPORADA] == temp].set_index(COL_JUGADOR)

    prev, cur, nxt = tomar(t - 1), tomar(t), tomar(t + 1)
    prev_v = prev[prev[DV].notna()]
    ids_prev = prev_v.index
    en_cur = ids_prev.intersection(cur.index)
    cur_con_dv = cur.index[cur[DV].notna()]
    ids_B = en_cur.intersection(cur.index[cur[DV].isna()])
    ids_P = ids_prev.intersection(cur_con_dv)
    tasas = dict(season=t, tasa_B_pct=len(ids_B) / max(len(en_cur), 1) * 100, n_B=len(ids_B), n_base_B=len(en_cur))
    grupos = {"B: fila sin valuacion": ids_B, "referencia B: presentes con valuacion": ids_P}
    if len(nxt):
        ids_N = ids_prev.intersection(nxt.index)
        ids_A = ids_N.difference(cur.index)
        ids_PN = ids_N.intersection(cur_con_dv)
        tasas.update(tasa_A_pct=len(ids_A) / max(len(ids_N), 1) * 100, n_A=len(ids_A), n_base_A=len(ids_N))
        grupos["A: fila ausente (hueco)"] = ids_A
        grupos["referencia A: presentes con valuacion"] = ids_PN
    else:
        tasas.update(tasa_A_pct=np.nan, n_A=0, n_base_A=0)
    filas = []
    for nombre, ids in grupos.items():
        sub = prev_v.loc[ids]
        fila = dict(season=t, grupo=nombre, n=len(ids), valor_log_t_1=sub[DV].mean(),
                    edad_t_1=sub[COL_EDAD].mean(),
                    pct_arquero=np.nan)
        if COL_POSICION in sub.columns and sub[COL_POSICION].notna().any():
            fila["pct_arquero"] = sub[COL_POSICION].astype(str).str.contains(
                PATRON_PORTERO, case=False, regex=True).mean() * 100
        if "minutos_totales" in sub.columns:
            fila["minutos_t_1"] = sub["minutos_totales"].mean()
        if "club_id" in sub.columns and len(sub):
            fila["n_clubes"] = sub["club_id"].nunique()
        if len(ids) < N_MIN_CELDA:
            for c in ("valor_log_t_1", "edad_t_1", "pct_arquero", "minutos_t_1"):
                if c in fila:
                    fila[c] = np.nan
        filas.append(fila)
    return pd.DataFrame(filas), tasas


def concentracion_por_club(dataset, t):
    """
    Entre los jugadores con valuacion en t-1 y fila en t+1, fraccion de cada club
    (club en t-1) que NO tiene fila en t. Clubes con menos de 10 jugadores de ese
    universo se omiten. Devuelve dict con n_clubes, mediana, p90 y cuantos clubes
    pierden mas de la mitad. Si falta club_id devuelve None.
    """
    if "club_id" not in dataset.columns:
        return None
    d = dataset[[COL_JUGADOR, COL_TEMPORADA, DV, "club_id"]].drop_duplicates([COL_JUGADOR, COL_TEMPORADA])
    prev = d[(d[COL_TEMPORADA] == t - 1) & d[DV].notna()].set_index(COL_JUGADOR)
    ids_cur = set(d.loc[d[COL_TEMPORADA] == t, COL_JUGADOR])
    ids_nxt = set(d.loc[d[COL_TEMPORADA] == t + 1, COL_JUGADOR])
    prev = prev[prev.index.isin(ids_nxt)]
    if prev.empty:
        return None
    prev = prev.assign(ausente=~prev.index.isin(ids_cur))
    por_club = prev.groupby("club_id")["ausente"].agg(["size", "mean"])
    por_club = por_club[por_club["size"] >= 10]
    if por_club.empty:
        return None
    return dict(n_clubes=len(por_club), mediana=por_club["mean"].median() * 100,
                p90=por_club["mean"].quantile(0.9) * 100, clubes_mas_de_la_mitad=int((por_club["mean"] > 0.5).sum()))


def seccion_huecos(dataset, ruta_reports, ruta_figuras):
    print("\n[2e] HUECOS DE COBERTURA (quien falta en el panel, y cuanto valia en t-1)")
    temporadas = sorted(dataset[COL_TEMPORADA].dropna().unique())
    perfiles, tasas = [], []
    for t in temporadas[1:]:
        if t - 1 not in temporadas:
            continue
        perfil, tasa = perfil_huecos(dataset, t)
        perfiles.append(perfil)
        tasas.append(tasa)
    if not tasas:
        print("  AVISO: sin datos suficientes.")
        return None
    tasas = pd.DataFrame(tasas)
    perfiles = pd.concat(perfiles, ignore_index=True)
    e01.guardar_csv_legible(tasas, ruta_reports / "huecos_tasas_por_temporada.csv")
    e01.guardar_csv_legible(perfiles, ruta_reports / "huecos_perfil.csv")

    print("  Tasa A = % de jugadores con valuacion en t-1 y fila en t+1 que NO tienen fila en t (hueco).")
    print("  Tasa B = % de jugadores con valuacion en t-1 y fila en t cuya fila en t no tiene valuacion.")
    print(tasas[["season", "tasa_A_pct", "n_A", "tasa_B_pct", "n_B"]].round(2).to_string(index=False))

    for t in TEMPORADAS_FOCO_HUECOS:
        sub = perfiles[perfiles["season"] == t]
        if sub.empty:
            continue
        print(f"\n  Perfil en t = {t} (valores medidos en t-1 = {t - 1}):")
        mostrar = [c for c in ("grupo", "n", "valor_log_t_1", "minutos_t_1", "edad_t_1", "pct_arquero", "n_clubes") if c in sub.columns]
        print(sub[mostrar].round(2).to_string(index=False))
        conc = concentracion_por_club(dataset, t)
        if conc is not None:
            print(f"  Concentracion del hueco A por club (clubes con >=10 jugadores en el universo): "
                  f"{conc['n_clubes']} clubes, mediana {conc['mediana']:.0f}% ausente, p90 {conc['p90']:.0f}%, "
                  f"{conc['clubes_mas_de_la_mitad']} clubes pierden mas de la mitad")

    fig, ax = plt.subplots(figsize=(8, 4.4))
    ax.plot(tasas["season"], tasas["tasa_A_pct"], color=estilo.COLOR_PRINCIPAL, marker="o", lw=2, ms=4,
            label="A: fila ausente en t (tenia t-1 y t+1)")
    ax.plot(tasas["season"], tasas["tasa_B_pct"], color=estilo.COLOR_SECUNDARIO, marker="s", lw=2, ms=4,
            label="B: fila presente sin valuacion")
    ax.axvspan(TEMPORADAS_PANDEMIA[0] - 0.5, TEMPORADAS_PANDEMIA[-1] + 0.5, color=estilo.COLOR_NEUTRO, alpha=0.25, lw=0)
    ax.set_xticks(list(tasas["season"]))
    ax.tick_params(axis="x", labelrotation=45)
    ax.set_xlabel("temporada t (anio de inicio)")
    ax.set_ylabel("% de jugadores")
    ax.set_title("Huecos de cobertura por temporada")
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(ruta_figuras / "huecos_tasas.png", dpi=120)
    plt.close(fig)
    return tasas, perfiles


# ---------------------------------------------------------------------------
# 2f. Distribucion de minutos
# ---------------------------------------------------------------------------

LIMITES_TRAMO_MINUTOS = [0, 450, 900, 1800, np.inf]
ETIQUETAS_TRAMO_MINUTOS = ["<450", "450-900", "900-1800", ">=1800"]


def tramos_minutos(dataset):
    """Serie categorica del tramo de minutos_totales; 'sin dato' si es NaN."""
    tramo = pd.cut(dataset["minutos_totales"], bins=LIMITES_TRAMO_MINUTOS,
                   labels=ETIQUETAS_TRAMO_MINUTOS, right=False).astype(object)
    return tramo.where(dataset["minutos_totales"].notna(), "sin dato")


def seccion_minutos(dataset, ruta_reports, ruta_figuras):
    print("\n[2f] DISTRIBUCION DE MINUTOS POR TEMPORADA (filas por tramo de minutos_totales)")
    if "minutos_totales" not in dataset.columns:
        print("  AVISO: falta la columna 'minutos_totales'; se omite.")
        return None
    d = dataset[[COL_TEMPORADA, DV, "minutos_totales"]].copy()
    d["tramo"] = tramos_minutos(d)
    orden = ETIQUETAS_TRAMO_MINUTOS + ["sin dato"]
    conteo = d.pivot_table(index=COL_TEMPORADA, columns="tramo", values="minutos_totales",
                           aggfunc="size", fill_value=0).reindex(columns=orden, fill_value=0)
    pct = conteo.div(conteo.sum(axis=1), axis=0) * 100
    valor = d.pivot_table(index=COL_TEMPORADA, columns="tramo", values=DV, aggfunc="mean").reindex(columns=orden)
    valor_n = d.dropna(subset=[DV]).pivot_table(index=COL_TEMPORADA, columns="tramo", values=DV,
                                                aggfunc="size", fill_value=0).reindex(columns=orden, fill_value=0)
    valor = valor.where(valor_n >= N_MIN_CELDA)

    salida = pd.concat({"n_filas": conteo, "pct_filas": pct, "media_log_valor": valor}, axis=1)
    salida.columns = [f"{a}__{b}" for a, b in salida.columns]
    e01.guardar_csv_legible(salida.reset_index(), ruta_reports / "minutos_por_tramo_y_temporada.csv")

    print("  Filas por tramo de minutos (cuenta absoluta):")
    print(conteo.to_string())
    print("\n  % de filas por tramo:")
    print(pct.round(1).to_string())
    print("\n  Media de log(valor) por tramo (celdas con menos de 30 filas valuadas = NaN):")
    print(valor.round(2).to_string())

    if 2021 in conteo.index and 2020 in conteo.index and 2022 in conteo.index:
        vecinos = (conteo.loc[2020] + conteo.loc[2022]) / 2
        dif = (conteo.loc[2021] - vecinos)
        print("\n  2021 contra el promedio de 2020 y 2022 (filas de mas o de menos por tramo): "
              + ", ".join(f"{k}: {v:+.0f}" for k, v in dif.items()))

    fig, ax = plt.subplots(figsize=(8, 4.6))
    colores = [estilo.COLOR_PRINCIPAL, estilo.COLOR_SECUNDARIO, "#0b0b0b", estilo.COLOR_NEUTRO]
    for i, tramo in enumerate(ETIQUETAS_TRAMO_MINUTOS):
        ax.plot(conteo.index, conteo[tramo], color=colores[i], marker=_MARCADORES[i], lw=2, ms=4, label=tramo)
    ax.axvspan(TEMPORADAS_PANDEMIA[0] - 0.5, TEMPORADAS_PANDEMIA[-1] + 0.5, color=estilo.COLOR_NEUTRO, alpha=0.25, lw=0)
    ax.set_xticks(list(conteo.index))
    ax.tick_params(axis="x", labelrotation=45)
    ax.set_xlabel("temporada (anio de inicio)")
    ax.set_ylabel("cantidad de filas")
    ax.set_title("Filas por tramo de minutos jugados")
    ax.legend(frameon=False, fontsize=8, title="minutos_totales")
    fig.tight_layout()
    fig.savefig(ruta_figuras / "minutos_por_tramo.png", dpi=120)
    plt.close(fig)
    return conteo


def seccion_serie_por_banda_edad(dataset, ruta_reports, ruta_figuras):
    d = agregar_banda_edad(dataset)
    tabla = agregar_variacion_interanual(
        estadisticos_por_grupo(d, ["banda_edad", COL_TEMPORADA]), grupo_extra="banda_edad"
    )
    e01.guardar_csv_legible(tabla, ruta_reports / "serie_valor_por_banda_edad.csv")
    ancha = pivot_ancho(tabla, "banda_edad", "media_log")
    ancha.columns = [str(c) for c in ancha.columns]
    ancha = ancha[[c for c in ETIQUETAS_BANDA_EDAD if c in ancha.columns]]
    graficar_lineas(ancha, "Media de log(valor) por banda de edad y temporada", DV,
                    ruta_figuras / "serie_valor_por_banda_edad.png")
    print("\n[3] Media de log(valor) por banda de edad x temporada:")
    print(ancha.round(2).to_string())
    return tabla


# ---------------------------------------------------------------------------
# 4. Crecimiento intra-jugador
# ---------------------------------------------------------------------------

def seccion_crecimiento_intrajugador(dataset, ruta_reports, ruta_figuras):
    d = agregar_banda_edad(dataset)[[COL_JUGADOR, COL_TEMPORADA, DV, "banda_edad"]].dropna(
        subset=[DV, "banda_edad"]
    )
    siguiente = d[[COL_JUGADOR, COL_TEMPORADA, DV]].copy()
    siguiente[COL_TEMPORADA] = siguiente[COL_TEMPORADA] - 1
    siguiente = siguiente.rename(columns={DV: "dv_siguiente"})
    pares = d.merge(siguiente, on=[COL_JUGADOR, COL_TEMPORADA], how="inner")
    pares["delta_log"] = pares["dv_siguiente"] - pares[DV]
    print(f"\n[4] Pares jugador-(t, t+1) consecutivos con valuacion en ambos: {len(pares)}")

    pares["sin_cambio"] = pares["delta_log"].abs() < 1e-9
    pares["sube"] = pares["delta_log"] > 1e-9
    pares["baja"] = pares["delta_log"] < -1e-9

    def resumir(agrupado):
        t = agrupado.agg(
            n=("delta_log", "size"), media_delta_log=("delta_log", "mean"),
            mediana_delta_log=("delta_log", "median"),
            pct_sin_cambio=("sin_cambio", "mean"), pct_sube=("sube", "mean"), pct_baja=("baja", "mean"),
        ).reset_index()
        columnas = ["media_delta_log", "mediana_delta_log", "pct_sin_cambio", "pct_sube", "pct_baja"]
        t.loc[t["n"] < N_MIN_CELDA, columnas] = np.nan
        return t

    tabla = resumir(pares.groupby(["banda_edad", COL_TEMPORADA], observed=True))
    todas = resumir(pares.groupby(COL_TEMPORADA))
    todas.insert(0, "banda_edad", "todas")
    tabla = pd.concat([tabla, todas], ignore_index=True)
    tabla["crecimiento_medio_pct"] = (np.exp(tabla["media_delta_log"]) - 1) * 100
    for c in ("pct_sin_cambio", "pct_sube", "pct_baja"):
        tabla[c] = tabla[c] * 100
    e01.guardar_csv_legible(tabla, ruta_reports / "crecimiento_intrajugador_por_banda_y_temporada.csv")

    orden = [c for c in ETIQUETAS_BANDA_EDAD + ["todas"]]
    ancha = tabla.pivot_table(index=COL_TEMPORADA, columns="banda_edad", values="crecimiento_medio_pct", observed=True)
    ancha.columns = [str(c) for c in ancha.columns]
    ancha = ancha[[c for c in orden if c in ancha.columns]]
    print("  Crecimiento MEDIO % (t -> t+1, media geometrica), por banda de edad en t; fila = temporada t:")
    print(ancha.round(1).to_string())
    sin_cambio = tabla.pivot_table(index=COL_TEMPORADA, columns="banda_edad", values="pct_sin_cambio", observed=True)
    sin_cambio.columns = [str(c) for c in sin_cambio.columns]
    sin_cambio = sin_cambio[[c for c in orden if c in sin_cambio.columns]]
    print("\n  % de jugadores cuyo valor NO cambia de t a t+1 (evidencia de persistencia / escalones):")
    print(sin_cambio.round(1).to_string())
    graficar_lineas(ancha, "Crecimiento intra-jugador medio (%, t a t+1)", "% de cambio en el valor",
                    ruta_figuras / "crecimiento_intrajugador_por_banda_y_temporada.png")
    return tabla


# ---------------------------------------------------------------------------
# 5. Pandemia
# ---------------------------------------------------------------------------

def seccion_pandemia(dataset, serie_global, ruta_reports, ruta_figuras):
    agregados = {"n_filas": (COL_JUGADOR, "size"), "pct_sin_valuacion": (DV, lambda s: s.isna().mean())}
    for col, nombre in (("minutos_totales", "minutos_medios"), ("partidos_jugados", "partidos_medios")):
        if col in dataset.columns:
            agregados[nombre] = (col, "mean")
        else:
            print(f"AVISO: falta la columna '{col}' -- no se calcula '{nombre}'.")
    if "club_id" in dataset.columns:
        agregados["n_clubes"] = ("club_id", "nunique")
    if "minutos_confiables" in dataset.columns:
        agregados["pct_minutos_confiables"] = ("minutos_confiables", lambda x: x.fillna(False).astype(bool).mean())
    tabla = dataset.groupby(COL_TEMPORADA).agg(**agregados).reset_index()
    if "n_clubes" in tabla.columns:
        tabla["filas_por_club"] = tabla["n_filas"] / tabla["n_clubes"]
    tabla = tabla.merge(serie_global[[COL_TEMPORADA, "media_log", "var_media_geom_pct"]],
                        on=COL_TEMPORADA, how="left")
    tabla["temporada_pandemia"] = tabla[COL_TEMPORADA].isin(TEMPORADAS_PANDEMIA)
    e01.guardar_csv_legible(tabla, ruta_reports / "pandemia_por_temporada.csv")
    print(f"\n[5] Pandemia (temporadas marcadas: {TEMPORADAS_PANDEMIA}, anio de inicio):")
    print(tabla.round(3).to_string(index=False))

    paneles = [c for c in ("minutos_medios", "pct_sin_valuacion", "var_media_geom_pct") if c in tabla.columns]
    fig, ejes = plt.subplots(len(paneles), 1, figsize=(8, 2.6 * len(paneles)), sharex=True, squeeze=False)
    for ax, col in zip(ejes[:, 0], paneles):
        ax.plot(tabla[COL_TEMPORADA], tabla[col], color=estilo.COLOR_PRINCIPAL, marker="o", lw=2, ms=4)
        ax.axvspan(TEMPORADAS_PANDEMIA[0] - 0.5, TEMPORADAS_PANDEMIA[-1] + 0.5,
                   color=estilo.COLOR_NEUTRO, alpha=0.25, lw=0)
        ax.set_ylabel(col)
    ejes[-1, 0].set_xticks(list(tabla[COL_TEMPORADA]))
    ejes[-1, 0].tick_params(axis="x", labelrotation=45)
    ejes[-1, 0].set_xlabel("temporada (anio de inicio)")
    fig.suptitle("Indicadores por temporada (franja gris = pandemia)")
    fig.tight_layout()
    fig.savefig(ruta_figuras / "pandemia_por_temporada.png", dpi=120)
    plt.close(fig)
    return tabla


# ---------------------------------------------------------------------------
# 6. Altura
# ---------------------------------------------------------------------------

def seccion_altura(dataset, ruta_reports, ruta_figuras):
    if COL_ALTURA not in dataset.columns:
        print(f"\n[6] AVISO: no esta '{COL_ALTURA}' en el dataset -- seccion de altura omitida.")
        return None
    plausible = dataset[COL_ALTURA].between(ALTURA_MIN, ALTURA_MAX)
    n_implausible = int((dataset[COL_ALTURA].notna() & ~plausible).sum())
    d = agregar_banda_edad(dataset[plausible])
    print(f"\n[6] Altura: {len(d)} filas con altura plausible [{ALTURA_MIN},{ALTURA_MAX}] cm "
          f"({n_implausible} fuera de rango excluidas). Recordar: altura_cm es una foto actual de "
          "players.csv, no varia en el tiempo para un mismo jugador.")

    por_temporada = d.groupby(COL_TEMPORADA)[COL_ALTURA].agg(n="size", media="mean", mediana="median", std="std").reset_index()
    e01.guardar_csv_legible(por_temporada, ruta_reports / "altura_por_temporada.csv")
    print("\n  Altura por temporada (filas jugador-temporada):")
    print(por_temporada.round(2).to_string(index=False))

    # Nivel jugador (una fila por jugador) para no ponderar por cuantas temporadas aparece.
    jugadores = d.sort_values(COL_TEMPORADA).drop_duplicates(COL_JUGADOR).dropna(subset=[COL_EDAD]).copy()
    jugadores["anio_nacimiento_aprox"] = (jugadores[COL_TEMPORADA] + 0.5 - jugadores[COL_EDAD]).round()
    jugadores["cohorte_quinquenio"] = (jugadores["anio_nacimiento_aprox"] // 5 * 5).astype(int)
    por_cohorte = jugadores.groupby("cohorte_quinquenio")[COL_ALTURA].agg(n="size", media="mean", std="std").reset_index()
    por_cohorte.loc[por_cohorte["n"] < N_MIN_CELDA, ["media", "std"]] = np.nan
    e01.guardar_csv_legible(por_cohorte, ruta_reports / "altura_por_cohorte_nacimiento.csv")
    print("\n  Altura por cohorte de nacimiento (aprox., 1 fila por jugador):")
    print(por_cohorte.round(2).to_string(index=False))

    por_pos = d.groupby([COL_POSICION, COL_TEMPORADA])[COL_ALTURA].agg(n="size", media="mean").reset_index()
    por_pos.loc[por_pos["n"] < N_MIN_CELDA, "media"] = np.nan
    e01.guardar_csv_legible(por_pos, ruta_reports / "altura_por_posicion_y_temporada.csv")
    graficar_lineas(por_pos.pivot_table(index=COL_TEMPORADA, columns=COL_POSICION, values="media"),
                    "Altura media por posicion y temporada", COL_ALTURA,
                    ruta_figuras / "altura_por_posicion_y_temporada.png", sombrear_pandemia=False)

    por_banda = d.groupby(["banda_edad", COL_TEMPORADA], observed=True)[COL_ALTURA].agg(n="size", media="mean").reset_index()
    por_banda.loc[por_banda["n"] < N_MIN_CELDA, "media"] = np.nan
    e01.guardar_csv_legible(por_banda, ruta_reports / "altura_por_banda_edad_y_temporada.csv")
    ancha = por_banda.pivot_table(index=COL_TEMPORADA, columns="banda_edad", values="media", observed=True)
    ancha.columns = [str(c) for c in ancha.columns]
    ancha = ancha[[c for c in ETIQUETAS_BANDA_EDAD if c in ancha.columns]]
    print("\n  Altura media por banda de edad x temporada (jovenes que hoy siguen creciendo "
          "podrian mostrar una altura menor en las ultimas temporadas):")
    print(ancha.round(1).to_string())
    graficar_lineas(ancha, "Altura media por banda de edad y temporada", COL_ALTURA,
                    ruta_figuras / "altura_por_banda_edad_y_temporada.png", sombrear_pandemia=False)
    return por_temporada


# ---------------------------------------------------------------------------
# 7. "Dejar el valor de antes" (necesita tablas crudas)
# ---------------------------------------------------------------------------

def clasificar_valuaciones_sin_panel(valuaciones, panel):
    """
    Para cada valuacion (player_id, season) que NO tiene fila en el panel, dice
    donde cae respecto de la carrera del jugador en el panel: antes de su
    primera temporada, en un hueco entre temporadas, despues de la ultima, o si
    el jugador nunca aparece. Funcion pura (sin lectura de archivos) para poder
    probarla.
    """
    panel = panel[[COL_JUGADOR, COL_TEMPORADA]].drop_duplicates().copy()
    panel["_en_panel"] = True
    span = panel.groupby(COL_JUGADOR)[COL_TEMPORADA].agg(primera="min", ultima="max").reset_index()

    v = valuaciones[[COL_JUGADOR, COL_TEMPORADA]].drop_duplicates().merge(panel, on=[COL_JUGADOR, COL_TEMPORADA], how="left")
    v = v[v["_en_panel"].isna()].drop(columns="_en_panel").merge(span, on=COL_JUGADOR, how="left")
    v["categoria"] = np.select(
        [v["primera"].isna(), v[COL_TEMPORADA] < v["primera"], v[COL_TEMPORADA] > v["ultima"]],
        ["jugador_nunca_en_panel", "antes_de_entrar_al_panel", "despues_de_salir_del_panel"],
        default="hueco_entre_temporadas_del_panel",
    )
    return v


def rezago_ultima_valuacion_previa(filas_sin_dv, valuaciones):
    """
    Para filas del panel sin valuacion en su temporada: cuantas temporadas atras
    esta la ultima valuacion previa del mismo jugador (NaN si no tiene
    ninguna). Funcion pura.
    """
    izq = filas_sin_dv[[COL_JUGADOR, COL_TEMPORADA]].drop_duplicates().sort_values(COL_TEMPORADA)
    der = (valuaciones[[COL_JUGADOR, COL_TEMPORADA]].drop_duplicates()
           .rename(columns={COL_TEMPORADA: "temporada_valuacion_previa"})
           .assign(_clave=lambda x: x["temporada_valuacion_previa"])
           .sort_values("_clave"))
    res = pd.merge_asof(izq, der, left_on=COL_TEMPORADA, right_on="_clave", by=COL_JUGADOR,
                        direction="backward", allow_exact_matches=False)
    res["rezago_temporadas"] = res[COL_TEMPORADA] - res["temporada_valuacion_previa"]
    return res.drop(columns="_clave")


def perfil_pre_entrada(vals, dataset, col_valor):
    """
    Perfil de las valuaciones (player_id, season) de jugadores que despues
    entran al panel pero que son ANTERIORES a su primera temporada en el panel.
    `vals` necesita player_id, season y la columna `col_valor` con el valor de
    la temporada (en euros o en log; se pasa a log si es euros). Devuelve
    (por_k, por_temporada, n_total, n_jugadores):
      por_k: por cantidad de temporadas hasta entrar (1, 2, 3, 4+): n filas, n
        jugadores, media de log(valor), edad aprox. (edad en la 1ra temporada del
        panel menos k) y crecimiento medio de log(valor) hasta la 1ra temporada
        del panel con valuacion.
      por_temporada: filas pre-entrada por temporada y como % de las filas del panel.
    Funcion pura.
    """
    sin_panel = clasificar_valuaciones_sin_panel(vals, dataset)
    pre = sin_panel[sin_panel["categoria"] == "antes_de_entrar_al_panel"].copy()
    v = vals[[COL_JUGADOR, COL_TEMPORADA, col_valor]].drop_duplicates([COL_JUGADOR, COL_TEMPORADA])
    pre = pre.merge(v, on=[COL_JUGADOR, COL_TEMPORADA], how="left")
    pre["log_valor"] = np.log(pre[col_valor]) if col_valor == COL_EUR else pre[col_valor]
    primero = (dataset.dropna(subset=[DV]).sort_values(COL_TEMPORADA)
               .drop_duplicates(COL_JUGADOR)[[COL_JUGADOR, COL_TEMPORADA, DV, COL_EDAD]]
               .rename(columns={COL_TEMPORADA: "t_primera_dv", DV: "dv_primera", COL_EDAD: "edad_primera"}))
    pre = pre.merge(primero, on=COL_JUGADOR, how="inner")
    pre["k"] = pre["t_primera_dv"] - pre[COL_TEMPORADA]
    pre = pre[pre["k"] >= 1].copy()
    pre["edad_aprox"] = pre["edad_primera"] - pre["k"]
    pre["crec_hasta_entrar"] = pre["dv_primera"] - pre["log_valor"]
    pre["k_tramo"] = pd.cut(pre["k"], bins=[0, 1, 2, 3, np.inf], labels=["1", "2", "3", "4+"], right=True)
    por_k = pre.groupby("k_tramo", observed=True).agg(
        n_filas=(COL_JUGADOR, "size"), n_jugadores=(COL_JUGADOR, "nunique"),
        media_log_valor=("log_valor", "mean"), edad_aprox=("edad_aprox", "mean"),
        crec_log_hasta_entrar=("crec_hasta_entrar", "mean"),
    ).reset_index()
    por_k["crec_pct_hasta_entrar"] = (np.exp(por_k["crec_log_hasta_entrar"]) - 1) * 100
    n_panel = dataset.groupby(COL_TEMPORADA).size().rename("n_filas_panel")
    por_temp = pre.groupby(COL_TEMPORADA).size().rename("n_filas_pre_entrada").to_frame().join(n_panel, how="left")
    por_temp["pct_sobre_panel"] = por_temp["n_filas_pre_entrada"] / por_temp["n_filas_panel"] * 100
    return por_k, por_temp.reset_index(), len(pre), pre[COL_JUGADOR].nunique()


def construir_valor_previo(dataset, vals, col_valor):
    """
    Para cada fila (player_id, season) del panel, la ULTIMA valuacion estrictamente
    anterior a esa temporada, mirando todas las valuaciones `vals` (con o sin fila
    en el panel). Devuelve el dataset con dos columnas nuevas: log_valor_previo y
    rezago_previo (temporadas entre ambas). NaN si el jugador no tiene valuacion
    previa. Funcion pura.
    """
    izq = dataset[[COL_JUGADOR, COL_TEMPORADA]].drop_duplicates().sort_values(COL_TEMPORADA)
    v = vals[[COL_JUGADOR, COL_TEMPORADA, col_valor]].drop_duplicates([COL_JUGADOR, COL_TEMPORADA])
    v = v.rename(columns={COL_TEMPORADA: "_t_previa", col_valor: "_valor_previo"})
    v["log_valor_previo"] = np.log(v["_valor_previo"]) if col_valor == COL_EUR else v["_valor_previo"]
    v["_clave"] = v["_t_previa"]
    v = v.sort_values("_clave")
    m = pd.merge_asof(izq, v[[COL_JUGADOR, "_t_previa", "_clave", "log_valor_previo"]],
                      left_on=COL_TEMPORADA, right_on="_clave", by=COL_JUGADOR,
                      direction="backward", allow_exact_matches=False)
    m["rezago_previo"] = m[COL_TEMPORADA] - m["_t_previa"]
    return dataset.merge(m[[COL_JUGADOR, COL_TEMPORADA, "log_valor_previo", "rezago_previo"]],
                         on=[COL_JUGADOR, COL_TEMPORADA], how="left")


def r2_mco(y, X):
    """R2 y coeficientes de MCO (con constante ya incluida en X)."""
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    return 1 - resid.var() / y.var(), beta


def seccion_valor_previo_variable(dataset, vals, col_valor, ruta_reports):
    """
    7d. Evalua la alternativa "valor previo como variable" (ver docstring del modulo).
    """
    print("\n[7d] VALOR PREVIO COMO VARIABLE (ultima valuacion anterior a la temporada)")
    d = construir_valor_previo(dataset, vals, col_valor)
    d = d.dropna(subset=[DV]).copy()
    # Borde izquierdo: en la primera temporada del panel TODOS los jugadores tienen "su primera fila"
    # solo porque el panel empieza ahi, no porque hayan ingresado. Un ingreso real es una primera
    # fila posterior a esa temporada.
    borde = int(dataset[COL_TEMPORADA].min())
    primera = d.groupby(COL_JUGADOR)[COL_TEMPORADA].transform("min")
    d["es_primera_fila"] = (d[COL_TEMPORADA] == primera) & (d[COL_TEMPORADA] > borde)
    d["grupo_fila"] = np.where(
        d[COL_TEMPORADA] == borde, f"temporada inicial del panel ({borde}; borde, no es un ingreso)",
        np.where(d["es_primera_fila"], "primera fila (ingreso real)", "otras filas"))
    d["tramo_rezago"] = pd.cut(d["rezago_previo"], bins=[0, 1, 2, 3, np.inf], labels=["1", "2", "3", "4+"],
                               right=True).astype(object).fillna("sin_valuacion_previa")

    # a) Cobertura
    cob = d.groupby(["grupo_fila", "tramo_rezago"]).size().unstack(fill_value=0)
    cob = cob.reindex(columns=["1", "2", "3", "4+", "sin_valuacion_previa"], fill_value=0)
    cob["total"] = cob.sum(axis=1)
    cob_pct = cob.drop(columns="total").div(cob["total"], axis=0) * 100
    cob_pct.index = cob.index
    e01.guardar_csv_legible(pd.concat({"n": cob, "pct": cob_pct}, axis=1).reset_index(), ruta_reports / "valor_previo_variable_cobertura.csv")
    print("  a) Cobertura: filas del panel con DV segun el rezago de su valor previo (n):")
    print(cob.to_string())
    print("\n     En % de cada fila:")
    print(cob_pct.round(1).to_string())
    n_prim = int(d["es_primera_fila"].sum())
    n_prim_con = int((d["es_primera_fila"] & d["rezago_previo"].notna()).sum())
    print(f"     Ingresos reales con valor previo: {n_prim_con} de {n_prim} ({n_prim_con / max(n_prim, 1):.1%}) "
          "-- esa es la informacion NUEVA que aporta la variable.")
    por_ent = d[d["es_primera_fila"]].groupby(COL_TEMPORADA).agg(
        n_ingresos=(COL_JUGADOR, "size"), pct_con_valor_previo=("rezago_previo", lambda x: x.notna().mean() * 100)).reset_index()
    e01.guardar_csv_legible(por_ent, ruta_reports / "valor_previo_variable_cobertura_por_temporada_de_ingreso.csv")
    print("     Ingresos por temporada de ingreso y % con valor previo:")
    print(por_ent.round(1).to_string(index=False))

    # b) Poder predictivo (filas con rezago 1, para que sea el valor del ano anterior)
    r1 = d[d["rezago_previo"] == 1].dropna(subset=[COL_EDAD]).copy()
    filas = []
    if len(r1) > 100:
        y = r1[DV].to_numpy(dtype=float)
        edad = r1[COL_EDAD].to_numpy(dtype=float)
        X0 = np.column_stack([np.ones(len(r1)), edad, edad ** 2])
        X1 = np.column_stack([X0, r1["log_valor_previo"].to_numpy(dtype=float)])
        r2_0, _ = r2_mco(y, X0)
        r2_1, beta1 = r2_mco(y, X1)
        # Mismo ajuste sobre cambios: delta = DV - valor previo, explicado por la edad
        delta = y - r1["log_valor_previo"].to_numpy(dtype=float)
        r2_d, _ = r2_mco(delta, X0)
        filas.append(dict(muestra="filas con valor previo de 1 temporada atras", n=len(r1), r2_solo_edad=r2_0,
                          r2_edad_y_valor_previo=r2_1, coef_valor_previo=beta1[3], r2_edad_sobre_el_cambio=r2_d))
        print(f"\n  b) Poder predictivo (n={len(r1)}, valor previo de la temporada anterior):")
        print(f"     R2 de log(valor) con solo la edad (cuadratica): {r2_0:.3f}")
        print(f"     R2 agregando el valor previo: {r2_1:.3f}  (coeficiente del valor previo: {beta1[3]:.3f})")
        print(f"     R2 de la edad sobre el CAMBIO log(valor) - log(valor previo): {r2_d:.3f}")
        ent = r1[r1["es_primera_fila"]]
        if len(ent) > 100:
            ye = ent[DV].to_numpy(dtype=float)
            ae = ent[COL_EDAD].to_numpy(dtype=float)
            X0e = np.column_stack([np.ones(len(ent)), ae, ae ** 2])
            X1e = np.column_stack([X0e, ent["log_valor_previo"].to_numpy(dtype=float)])
            r2_0e, _ = r2_mco(ye, X0e)
            r2_1e, b1e = r2_mco(ye, X1e)
            filas.append(dict(muestra="solo primeras filas (con valor previo de 1 temporada atras)", n=len(ent),
                              r2_solo_edad=r2_0e, r2_edad_y_valor_previo=r2_1e, coef_valor_previo=b1e[3],
                              r2_edad_sobre_el_cambio=np.nan))
            print(f"     Solo primeras filas (n={len(ent)}): R2 solo edad {r2_0e:.3f} -> con valor previo {r2_1e:.3f} "
                  f"(coef {b1e[3]:.3f})")
        e01.guardar_csv_legible(pd.DataFrame(filas), ruta_reports / "valor_previo_variable_poder_predictivo.csv")

    # c) Salto de ingreso: cambio de valor de la primera fila vs el de quien ya estaba, misma banda de edad
    r1 = agregar_banda_edad(r1)
    r1["delta_log"] = r1[DV] - r1["log_valor_previo"]
    def resumen(g):
        return pd.Series(dict(n=len(g), media_delta_log=g["delta_log"].mean(), mediana_delta_log=g["delta_log"].median(),
                              p25=g["delta_log"].quantile(.25), p75=g["delta_log"].quantile(.75)))
    filas_c = []
    for banda in ETIQUETAS_BANDA_EDAD:
        for flag, nombre in ((True, "primera fila (ingreso)"), (False, "ya estaba en el panel")):
            g = r1[(r1["banda_edad"] == banda) & (r1["es_primera_fila"] == flag)]
            if len(g) >= N_MIN_CELDA:
                fila = resumen(g).to_dict()
                fila.update(banda_edad=banda, grupo=nombre)
                filas_c.append(fila)
    if filas_c:
        tc = pd.DataFrame(filas_c)
        tc["crecimiento_medio_pct"] = (np.exp(tc["media_delta_log"]) - 1) * 100
        e01.guardar_csv_legible(tc, ruta_reports / "valor_previo_variable_salto_de_ingreso.csv")
        ancho = tc.pivot(index="banda_edad", columns="grupo", values="crecimiento_medio_pct").reindex(ETIQUETAS_BANDA_EDAD)
        nn = tc.pivot(index="banda_edad", columns="grupo", values="n").reindex(ETIQUETAS_BANDA_EDAD)
        if {"primera fila (ingreso)", "ya estaba en el panel"} <= set(ancho.columns):
            ancho["diferencia_puntos"] = ancho["primera fila (ingreso)"] - ancho["ya estaba en el panel"]
        print("\n  c) Salto de ingreso: crecimiento medio % del valor respecto del de la temporada anterior, por banda de edad:")
        print(ancho.round(1).to_string())
        print("     n por celda:")
        print(nn.to_string())
        print("     (Descriptivo, con sesgo de seleccion: solo jugadores que despues llegaron al panel.)")
    return d


def seccion_valor_previo(dataset, tablas, ruta_reports):
    import d05_construir_variable_dependiente as d05

    vals = d05.construir_valor_mercado_por_temporada(tablas["player_valuations"])
    vals_panel_rango = vals[vals[COL_TEMPORADA] >= config.ANIO_MIN_COBERTURA_GAMES]

    sin_panel = clasificar_valuaciones_sin_panel(vals_panel_rango, dataset)
    total_val = len(vals_panel_rango[[COL_JUGADOR, COL_TEMPORADA]].drop_duplicates())
    resumen = sin_panel.groupby("categoria").agg(
        n_valuaciones=(COL_JUGADOR, "size"), n_jugadores=(COL_JUGADOR, "nunique")
    ).reset_index()
    resumen["pct_de_valuaciones_totales"] = resumen["n_valuaciones"] / total_val * 100
    e01.guardar_csv_legible(resumen, ruta_reports / "valor_previo_valuaciones_sin_fila_en_panel.csv")
    print(f"\n[7a] Valuaciones (season >= {config.ANIO_MIN_COBERTURA_GAMES}) SIN fila en el panel: "
          f"{len(sin_panel)} de {total_val} ({len(sin_panel) / total_val:.1%})")
    print(resumen.round(2).to_string(index=False))
    print("  'hueco_entre_temporadas_del_panel' es el caso donde arrastrar el valor tendria sentido sin "
          "inventar nada nuevo; 'antes_de_entrar_al_panel' suele ser desarrollo en ligas sin cobertura de eventos.")
    por_temp = sin_panel.pivot_table(index=COL_TEMPORADA, columns="categoria", values=COL_JUGADOR, aggfunc="size", fill_value=0)
    e01.guardar_csv_legible(por_temp.reset_index(), ruta_reports / "valor_previo_valuaciones_sin_panel_por_temporada.csv")

    col_valor = COL_EUR if COL_EUR in vals_panel_rango.columns else (DV if DV in vals_panel_rango.columns else None)
    if col_valor is None:
        print("\n[7c] AVISO: no encuentro la columna de valor en las valuaciones por temporada; se omite.")
    else:
        por_k, por_temp, n_pre, n_jug_pre = perfil_pre_entrada(vals_panel_rango, dataset, col_valor)
        e01.guardar_csv_legible(por_k, ruta_reports / "valor_previo_pre_entrada_por_temporadas_hasta_entrar.csv")
        e01.guardar_csv_legible(por_temp, ruta_reports / "valor_previo_pre_entrada_por_temporada.csv")
        print(f"\n[7c] Filas ANTES de entrar al panel (jugador-temporada con valuacion, jugador que despues entra): "
              f"{n_pre} filas de {n_jug_pre} jugadores = {n_pre / len(dataset):.1%} de las {len(dataset)} filas del panel.")
        print("  Por temporadas que faltan para entrar (k); crec = crecimiento medio del valor hasta la 1ra temporada del panel:")
        print(por_k.round(2).to_string(index=False))
        print("\n  Filas pre-entrada por temporada y % sobre las filas del panel de esa temporada:")
        print(por_temp.round(1).to_string(index=False))
        print("  OJO: solo estan los jugadores que despues SI llegaron al panel (sesgo de supervivencia): "
              "su valor previo crece mas que el de un joven promedio de esas ligas.")

    if col_valor is not None:
        seccion_valor_previo_variable(dataset, vals, col_valor, ruta_reports)

    filas_sin_dv = dataset[dataset[DV].isna()]
    rez = rezago_ultima_valuacion_previa(filas_sin_dv, vals)
    etiquetas = pd.cut(rez["rezago_temporadas"], bins=[0, 1, 2, 3, np.inf], labels=["1", "2", "3", "4+"], right=True)
    dist = etiquetas.astype(object).fillna("sin_valuacion_previa").value_counts().rename_axis("rezago_temporadas").reset_index(name="n_filas")
    dist["pct"] = dist["n_filas"] / len(rez) * 100
    e01.guardar_csv_legible(dist, ruta_reports / "valor_previo_filas_panel_sin_valuacion.csv")
    print(f"\n[7b] Filas del panel SIN valuacion en su temporada: {len(filas_sin_dv)} "
          f"({len(filas_sin_dv) / len(dataset):.1%} del panel). Antiguedad de la ultima valuacion previa:")
    print(dist.round(2).to_string(index=False))
    return resumen, dist


# ---------------------------------------------------------------------------
# 8. Tarjetas
# ---------------------------------------------------------------------------

def seccion_tarjetas(dataset, ruta_reports, ruta_figuras):
    requeridas = ["tarjetas_amarillas", "tarjetas_rojas", "minutos_totales", "minutos_confiables"]
    faltan = [c for c in requeridas if c not in dataset.columns]
    if faltan:
        cand = [c for c in dataset.columns if "tarjeta" in c]
        print(f"\n[8] AVISO: faltan {faltan} -- seccion de tarjetas omitida. Columnas con 'tarjeta': {cand}")
        return None

    confiable = dataset["minutos_confiables"].fillna(False).astype(bool)
    min90 = (dataset["minutos_totales"] / 90).replace(0, np.nan)
    d = dataset.copy()
    d["amarillas_90"] = (d["tarjetas_amarillas"] / min90).where(confiable)
    d["rojas_90"] = (d["tarjetas_rojas"] / min90).where(confiable)
    d["tarjetas_90_efectiva"] = e01.serie_efectiva(d, "tarjetas_90") if "tarjetas_90" in d.columns else np.nan

    filas = []
    for col in ("amarillas_90", "rojas_90", "tarjetas_90_efectiva"):
        s = d[col].dropna()
        if s.empty:
            continue
        filas.append({"variable": col, "n_no_nulos": len(s), "pct_cero": (s == 0).mean(),
                      "media": s.mean(), "mediana": s.median(), "p95": s.quantile(0.95),
                      "p99": s.quantile(0.99), "max": s.max()})
    univ = pd.DataFrame(filas)
    e01.guardar_csv_legible(univ, ruta_reports / "tarjetas_univariado.csv")
    print("\n[8] Tarjetas por 90 (solo filas con minutos confiables):")
    print(univ.round(4).to_string(index=False))

    # Que tan rara es la roja: % de jugador-temporadas confiables con al menos una.
    con_roja = (d["tarjetas_rojas"] > 0)[confiable]
    print(f"  Filas confiables con >=1 roja: {con_roja.mean():.2%} ({int(con_roja.sum())} de {len(con_roja)})")
    print(f"  Filas confiables con >=1 amarilla: {(d['tarjetas_amarillas'] > 0)[confiable].mean():.2%}")

    if "tarjetas_90" in d.columns:
        suma = (d["amarillas_90"] + d["rojas_90"])
        diff = (suma - d["tarjetas_90_efectiva"]).abs().max()
        print(f"  Chequeo: max |(amarillas_90 + rojas_90) - tarjetas_90| = {diff:.2e} (debe ser ~0)")

    filas_corr = []
    for etiqueta, mascara in [("todas", pd.Series(True, index=d.index))] + [
        (str(p), d[COL_POSICION] == p) for p in sorted(d[COL_POSICION].dropna().unique(), key=str)
    ]:
        sub = d[mascara]
        for col in ("amarillas_90", "rojas_90", "tarjetas_90_efectiva"):
            pareja = sub[[col, DV]].dropna()
            n = len(pareja)
            pearson = pareja[col].corr(pareja[DV], method="pearson") if n >= N_MIN_CELDA else np.nan
            spearman = spearman_sin_scipy(pareja[col], pareja[DV]) if n >= N_MIN_CELDA else np.nan
            filas_corr.append({"posicion": etiqueta, "variable": col, "n": n,
                               "pearson_vs_dv": pearson, "spearman_vs_dv": spearman})
    corr = pd.DataFrame(filas_corr)
    e01.guardar_csv_legible(corr, ruta_reports / "tarjetas_correlaciones_vs_dv.csv")
    print("\n  Correlacion con la DV, total y por posicion:")
    print(corr.round(3).to_string(index=False))
    entre = d[["amarillas_90", "rojas_90"]].dropna()
    if len(entre) >= N_MIN_CELDA:
        print(f"  Correlacion amarillas_90 vs rojas_90 (n={len(entre)}): Pearson "
              f"{entre['amarillas_90'].corr(entre['rojas_90']):.3f}")

    e01.graficar_histograma(d["amarillas_90"], "amarillas_90", ruta_figuras / "tarjetas_hist_amarillas_90.png")
    e01.graficar_histograma(d["rojas_90"], "rojas_90", ruta_figuras / "tarjetas_hist_rojas_90.png")
    return univ, corr


# ---------------------------------------------------------------------------
# 9. Con / sin porteros (descriptivo)
# ---------------------------------------------------------------------------

def seccion_porteros_correlaciones(dataset, es_portero, ruta_reports):
    tabla = e05.construir_tabla_efectiva(dataset)[e05.ESPECIFICACION_FINAL_PROPUESTA].copy()
    for col in e04.COLUMNAS_CONTEXTO_FINAL:
        tabla[col] = dataset[col]
    dv = dataset[DV]

    def corr(mascara, sufijo):
        # Local en vez de e05.correlaciones_vs_dv: aquella usa pandas method="spearman", que importa scipy.
        filas = []
        for col in tabla.columns:
            pareja = pd.DataFrame({col: tabla.loc[mascara, col], DV: dv[mascara]}).dropna()
            n = len(pareja)
            pearson = pareja[col].corr(pareja[DV]) if n >= N_MIN_CELDA else np.nan
            spearman = spearman_sin_scipy(pareja[col], pareja[DV]) if n >= N_MIN_CELDA else np.nan
            filas.append({"variable": col, f"n_{sufijo}": n, f"pearson_{sufijo}": pearson, f"spearman_{sufijo}": spearman})
        return pd.DataFrame(filas)

    todos = corr(pd.Series(True, index=dataset.index), "todos")
    sin = corr(~es_portero, "sin_porteros")
    solo = corr(es_portero, "solo_porteros")
    resultado = todos.merge(sin, on="variable").merge(solo, on="variable")
    resultado["delta_pearson_sin_vs_todos"] = resultado["pearson_sin_porteros"] - resultado["pearson_todos"]
    e01.guardar_csv_legible(resultado, ruta_reports / "porteros_correlaciones_spec_vs_dv.csv")
    print(f"\n[9] Correlacion con la DV de la especificacion cerrada: todos vs sin porteros vs solo porteros "
          f"({int(es_portero.sum())} filas de porteros de {len(dataset)}):")
    print(resultado.round(3).to_string(index=False))
    return resultado


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(description="e07: diagnosticos de efectos temporales y de muestra.")
    parser.add_argument("--omitir-crudas", action="store_true",
                        help="No carga las tablas crudas de Kaggle (omite la seccion 7).")
    args, _ = parser.parse_known_args(argv)

    estilo.aplicar_estilo()
    dataset = e01.cargar_dataset_modelable()
    print(f"Dataset: {dataset.shape[0]} filas, {dataset.shape[1]} columnas.")
    faltan = [c for c in COLUMNAS_REQUERIDAS if c not in dataset.columns]
    if faltan:
        raise KeyError(f"Faltan columnas en dataset_modelable: {faltan}")

    ruta_reports = config.ruta_reports_script(Path(__file__).stem)
    ruta_figuras = config.ruta_figuras_script(Path(__file__).stem)
    es_portero = detectar_porteros(dataset)

    serie_global = seccion_serie_global(dataset, es_portero, ruta_reports, ruta_figuras)
    seccion_serie_por_posicion(dataset, es_portero, ruta_reports, ruta_figuras)
    seccion_deriva_anual(dataset, es_portero, ruta_reports)
    seccion_cohorte_aleatoria(dataset, ruta_reports, ruta_figuras)
    seccion_recambio(dataset, ruta_reports, ruta_figuras)
    seccion_huecos(dataset, ruta_reports, ruta_figuras)
    seccion_minutos(dataset, ruta_reports, ruta_figuras)
    seccion_serie_por_banda_edad(dataset, ruta_reports, ruta_figuras)
    seccion_crecimiento_intrajugador(dataset, ruta_reports, ruta_figuras)
    seccion_pandemia(dataset, serie_global, ruta_reports, ruta_figuras)
    seccion_altura(dataset, ruta_reports, ruta_figuras)

    if args.omitir_crudas:
        print("\n[7] Omitida (--omitir-crudas).")
    else:
        import d02_construir_variables_contexto as ctx
        seccion_valor_previo(dataset, ctx.cargar_tablas(), ruta_reports)

    seccion_tarjetas(dataset, ruta_reports, ruta_figuras)
    seccion_porteros_correlaciones(dataset, es_portero, ruta_reports)

    print(f"\nListo. Tablas en {ruta_reports}, figuras en {ruta_figuras}. Este script no decide nada: "
          "es la evidencia para elegir tratamiento temporal, definir el cambio al panel y las "
          "sensibilidades de m01.")


if __name__ == "__main__":
    main()