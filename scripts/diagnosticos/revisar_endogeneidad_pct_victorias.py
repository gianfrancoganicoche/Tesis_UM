"""
Diagnostico ad-hoc (23/09/2026): evidencia empirica (no un test causal formal
-- ver nota abajo sobre por que) de que pct_victorias_con/pct_victorias_sin
NO son variables de contexto de club, sino un atributo del jugador puntual
(tipo plus-minus, Hvattum 2020), reforzando la decision ya tomada de
excluirlas del modelo de valor por el mismo argumento de mediador/endogeneidad
que cluster 3 (minutos jugados).

Por que no un test causal formal (Hausman/variables instrumentales): esos
tests necesitan una fuente de variacion exogena para "jugo o no jugo" que no
dependa de la calidad del jugador (el instrumento clasico en esta literatura
son lesiones). player-scores no tiene datos de lesiones ni ningun otro shock
exogeno identificable -- no es una limitacion de este script, es una
limitacion real del dataset.

Lo que si se puede hacer con los datos disponibles, y es lo que corre este
script:

PARTE 1 -- Descomposicion de varianza (eta cuadrado) por (club_id, season).
Las variables de contexto de club GENUINAS (ej. puntos_por_partido,
pca_exito_deportivo) son, por construccion, el MISMO valor para todos los
companeros de un mismo club esa temporada -- su eta cuadrado por
(club_id, season) deberia dar ~1.0 exacto (sirven de referencia/control de
que la metrica esta bien calculada). Si pct_victorias_con/sin varia
sustancialmente ENTRE companeros del MISMO equipo la MISMA temporada (eta
cuadrado bien por debajo de 1), es evidencia directa de que no es contexto
compartido -- es un numero que depende de CUAL jugador puntual se este
mirando, no del equipo en si.

Nota sobre grupos chicos: un grupo de tamanio 1 (un solo companero con dato
valido esa club-temporada) queda "perfectamente explicado" por su propia
media de forma trivial y no dice nada sobre si la variable varia entre
companeros -- por eso se filtra a grupos con al menos 2 jugadores con dato
valido (MIN_GRUPO), y se informa cuantas filas/grupos quedan.

Nota sobre COMO INTERPRETAR el numero (verificado con datos sinteticos antes
de devolver este script): con muchos grupos chicos, una variable de RUIDO
PURO -- sin ningun patron real de grupo -- NO da eta^2 cercano a 0, da un
valor moderado (en una prueba con 200 grupos de 2-5 companeros, ~0.29) por un
sesgo de muestra finita bien conocido en este tipo de descomposicion
(equivalente al R^2 inflado de una regresion con muchas variables dummy y
pocos datos por grupo). Por eso la comparacion correcta NO es "esta cerca de
0" sino "esta bien por debajo del ~1.0 de las variables de contexto genuino"
-- esas si dan exactamente 1.0 sea cual sea el tamanio de grupo, porque son
constantes dentro del grupo por construccion (inmunes a este sesgo).

PARTE 2 -- Comparacion de correlaciones: pct_victorias_con/sin correlacionado
contra el propio rendimiento individual del jugador (goles_90,
contribucion_gol_90 -- via serie_efectiva(), mismo piso de confiabilidad que
usa e01) vs. contra contexto de club puro (companieros_valor_promedio, que ya
excluye la propia valuacion del jugador; pca_exito_deportivo). Si correlaciona
mas fuerte con lo primero, refuerza la misma conclusion de PARTE 1.

No escribe nada en el pipeline -- es puramente diagnostico, para documentar
la decision con evidencia concreta en la nota metodologica correspondiente.
"""

import sys
from pathlib import Path

import pandas as pd  # noqa: F401

_RAIZ_SCRIPTS = Path(__file__).resolve().parents[1]  # scripts/
for _carpeta in ("config", "dataset", "eda", "diagnosticos"):
    sys.path.insert(0, str(_RAIZ_SCRIPTS / _carpeta))

import config  # noqa: F401
import e01_analisis_exploratorio as e01

MIN_GRUPO = 2
COLUMNAS_GRUPO = ["club_id", "season"]

# Variables de referencia -- contexto de club GENUINO, deberian dar eta^2 ~ 1.0
COLUMNAS_CONTEXTO_REFERENCIA = ["puntos_por_partido", "pca_exito_deportivo"]

# Las variables bajo sospecha
COLUMNAS_A_TESTEAR = ["pct_victorias_con", "pct_victorias_sin"]


def eta_cuadrado_entre_grupos(dataset, columna, columnas_grupo=COLUMNAS_GRUPO, min_grupo=MIN_GRUPO):
    """
    Fraccion de la varianza total de `columna` explicada por pertenecer a un
    mismo grupo (club_id, season) -- eta cuadrado de un ANOVA de un factor.
    1.0 = la variable es CONSTANTE dentro de cada grupo (todo companero de
    equipo esa temporada tiene el mismo valor -- patron de una variable de
    CONTEXTO). Valores bajos = la variable varia mucho entre companeros del
    MISMO equipo la MISMA temporada -- patron de un atributo INDIVIDUAL.

    Filtra a grupos con al menos `min_grupo` filas con dato valido (ver nota
    en el docstring del modulo sobre por que un grupo de tamanio 1 distorsiona
    el resultado). Devuelve (eta_cuadrado, n_filas_usadas, n_grupos_usados).
    """
    datos = dataset[[*columnas_grupo, columna]].dropna()
    tamanios = datos.groupby(columnas_grupo)[columna].transform("size")
    datos = datos[tamanios >= min_grupo]

    n_grupos = datos.groupby(columnas_grupo).ngroups
    if datos.empty:
        return float("nan"), 0, 0

    media_general = datos[columna].mean()
    ss_total = ((datos[columna] - media_general) ** 2).sum()
    if ss_total == 0:
        return float("nan"), len(datos), n_grupos

    medias_grupo = datos.groupby(columnas_grupo)[columna].transform("mean")
    # sum_filas (media_grupo - media_general)^2 == sum_grupos n_g * (media_g - media_general)^2
    # (cada grupo aporta su termino repetido n_g veces, una por fila) -- es la
    # formula correcta de SS_entre para grupos de tamanio desigual.
    ss_entre = ((medias_grupo - media_general) ** 2).sum()

    return ss_entre / ss_total, len(datos), n_grupos


def main():
    dataset = e01.cargar_dataset_modelable()
    print(f"Dataset: {dataset.shape[0]} filas, {dataset.shape[1]} columnas.\n")

    faltantes = [c for c in COLUMNAS_CONTEXTO_REFERENCIA + COLUMNAS_A_TESTEAR + COLUMNAS_GRUPO
                 if c not in dataset.columns]
    if faltantes:
        raise KeyError(
            f"No estan en el dataset: {faltantes}. Si falta 'pca_exito_deportivo', "
            "correr primero d06_extraer_panel_predictores.py con d07 ya integrado."
        )

    # -------------------------------------------------------------------
    # PARTE 1 -- eta^2 por (club_id, season)
    # -------------------------------------------------------------------
    print("=" * 78)
    print(f"PARTE 1: eta^2 por (club_id, season) -- min. {MIN_GRUPO} companeros con dato valido por grupo")
    print("=" * 78)

    print("\nReferencia -- contexto de club GENUINO (deberia dar ~1.0 exacto):")
    for col in COLUMNAS_CONTEXTO_REFERENCIA:
        eta2, n_filas, n_grupos = eta_cuadrado_entre_grupos(dataset, col)
        print(f"  {col}: eta^2={eta2:.4f}  (n={n_filas} filas, {n_grupos} grupos club-temporada)")

    print("\nBajo sospecha -- si el patron fuera 'contexto de club', tambien deberia dar ~1.0:")
    for col in COLUMNAS_A_TESTEAR:
        eta2, n_filas, n_grupos = eta_cuadrado_entre_grupos(dataset, col)
        print(f"  {col}: eta^2={eta2:.4f}  (n={n_filas} filas, {n_grupos} grupos club-temporada)")

    # -------------------------------------------------------------------
    # PARTE 2 -- correlaciones: rendimiento propio vs. contexto de club puro
    # -------------------------------------------------------------------
    print("\n" + "=" * 78)
    print("PARTE 2: correlacion (Pearson) -- rendimiento individual propio vs. contexto de club puro")
    print("=" * 78)

    columnas_rendimiento_propio = ["goles_90", "contribucion_gol_90", "asistencias_90"]
    columnas_contexto_puro = ["companieros_valor_promedio", "pca_exito_deportivo"]

    for col_test in COLUMNAS_A_TESTEAR:
        print(f"\n{col_test}:")
        print("  contra rendimiento individual propio:")
        for col in columnas_rendimiento_propio:
            serie_rendimiento = e01.serie_efectiva(dataset, col)
            r = dataset[col_test].corr(serie_rendimiento)
            print(f"    {col}: {r:.3f}")
        print("  contra contexto de club puro:")
        for col in columnas_contexto_puro:
            r = dataset[col_test].corr(dataset[col])
            print(f"    {col}: {r:.3f}")

    return dataset


if __name__ == "__main__":
    dataset_diagnostico = main()