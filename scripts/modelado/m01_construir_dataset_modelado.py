"""
m01_construir_dataset_modelado.py

Primer script del bloque de modelado (m0X, hierarchical Bayesian model /
Alternativa 3). NO ajusta ningun modelo -- arma el dataset final de modelado
a partir de dataset_modelable (salida de d06, ya con el z-score de d09
mergeado), con dos tareas:

1. SELECCION DE COLUMNAS: recorta dataset_modelable a la especificacion ya
   cerrada (ver overview.md/learnings-and-pitfalls.md del proyecto -- no se
   re-litiga aca, solo se ensambla):
     valor_it = curva_edad(edad, posicion) + contexto_it + rendimiento_it + alpha_i + eps_it
   - identificadores: player_id (para el shrinkage jerarquico alpha_i), season
   - variable dependiente: log_valor_mercado (+ valor_mercado_eur de respaldo)
   - insumos de la curva de edad: edad, posicion_amplia_predominante (para la
     interaccion edad x posicion, H2)
   - contexto_it (4 variables, bloque cerrado 23/09): pca_exito_deportivo,
     companieros_valor_promedio, formaciones_distintas, fase_maxima_alcanzada
   - rendimiento_it (6 variables, bloque cerrado 24/09) YA ESTANDARIZADAS por
     d09 (z_<variable>, por posicion x temporada) -- se usa la version z, no
     la cruda, que ya cumplio su proposito como insumo del z-score
   - atributos de jugador (d08): altura (z-scoreada por d09, z_altura_cm),
     pie_habil (categorica, no se z-scorea), es_comunitario (binaria)

2. FLAGS DE POBLACION (hipotesis_y_diseno_v2.md SS4, tres capas): se agregan
   como columnas booleanas, NO como filtro duro sobre las filas -- cada
   consumidor de este dataset (estimacion de curva de edad, modelo H1/H2,
   etc.) filtra segun la capa que le corresponda.
     - es_valido_curva_edad: capa 1 (curva de edad) -- carrera completa, sin
       restriccion de edad ni liga. Solo exige edad/DV/player_id no nulos.
     - es_sub23: capa 2 (poblacion de interes) -- edad < 23, sin restriccion
       de liga.
     - es_poblacion_h1: capa 3 (test de H1/H2) -- sub-23 en ligas de PRIMERA
       DIVISION EUROPEAS (competitions.csv: confederation=="europa",
       type=="domestic_league", sub_type=="first_tier"), 23 ligas/23 paises
       ya confirmado en el diseno.

       RESUELTO (25/09): confirmado que panel_predictores trae club_id por
       (player_id, season) (el crosswalk ya usado para los context vars).
       Con eso, es_poblacion_h1 se arma reusando
       construir_mapa_club_liga_por_temporada() de d02 (club_id+season ->
       competition_id, via moda de partidos reales de domestic_league) y
       cruzando ese competition_id contra competitions.csv (confederation/
       type/sub_type). Ver construir_columnas_liga() mas abajo.
       dataset_modelable no necesita tener club_id el mismo -- si no lo
       tiene, se busca automaticamente en el panel_predictores_*.csv mas
       reciente de la misma carpeta (ver cargar_club_por_jugador_temporada()).
       Si ninguna de las dos fuentes tiene club_id, o faltan
       games/club_games/competitions, la funcion degrada a advertencia +
       es_poblacion_h1=False -- no inventa el join.

No modifica dataset_modelable en el repo -- lo lee (reutilizando
cargar_dataset_modelable() de e01, mismo patron que d02) y escribe un
archivo nuevo, dataset_modelado_<fecha>.csv, en data/processed/.
"""
import sys
from pathlib import Path

import pandas as pd

_RAIZ_SCRIPTS = Path(__file__).resolve().parents[1]
for _carpeta in ("config", "dataset", "eda", "diagnosticos", "modelos"):
    sys.path.insert(0, str(_RAIZ_SCRIPTS / _carpeta))

import config
import d02_construir_variables_contexto as ctx
from e01_analisis_exploratorio import cargar_dataset_modelable

# ---------------------------------------------------------------------------
# Especificacion final de columnas (CERRADA -- ver overview.md /
# learnings-and-pitfalls.md del proyecto Tesis; no re-litigar aca).
# ---------------------------------------------------------------------------

COLUMNA_JUGADOR = "player_id"
COLUMNA_TEMPORADA = "season"
COLUMNA_CLUB = "club_id"  # para el cruce de liga (es_poblacion_h1), no forma parte de COLUMNAS_FINALES

COLUMNA_DV = "log_valor_mercado"
COLUMNA_DV_NIVEL = "valor_mercado_eur"  # se conserva para poder des-logaritmar en reportes

COLUMNA_EDAD = "edad"
COLUMNA_POSICION = "posicion_amplia_predominante"  # necesaria para la interaccion edad x posicion (H2)

COLUMNAS_CONTEXTO = [
    "pca_exito_deportivo",
    "companieros_valor_promedio",
    "formaciones_distintas",
    "fase_maxima_alcanzada",
]

# rendimiento_it: version YA estandarizada por d09 (z-score por posicion x
# temporada). La version cruda (goles_90, etc.) queda fuera de este dataset
# de modelado -- ya cumplio su proposito como insumo del z-score.
COLUMNAS_RENDIMIENTO_Z = [
    "z_goles_90",
    "z_asistencias_90",
    "z_participacion_produccion",
    "z_goles_recibidos_ajustados_90",
    "z_edad_debut",
    "z_tarjetas_90",
]

# Atributos de jugador (d08): altura ya estandarizada por d09 (misma logica
# que rendimiento_it); pie_habil/es_comunitario NO se z-scorean (categorica
# de 3 niveles / binaria).
COLUMNA_ALTURA_Z = "z_altura_cm"
COLUMNA_PIE = "pie_habil"
COLUMNA_COMUNITARIO = "es_comunitario"

COLUMNAS_FINALES = (
    [COLUMNA_JUGADOR, COLUMNA_TEMPORADA, COLUMNA_DV, COLUMNA_DV_NIVEL, COLUMNA_EDAD, COLUMNA_POSICION]
    + COLUMNAS_CONTEXTO
    + COLUMNAS_RENDIMIENTO_Z
    + [COLUMNA_ALTURA_Z, COLUMNA_PIE, COLUMNA_COMUNITARIO]
)

# Columnas de liga que, SI existieran en dataset_modelable, permitirian
# construir es_poblacion_h1 (capa 3) en esta misma corrida. Ver PENDIENTE en
# el docstring del modulo -- hoy no se asume que existan.
COLUMNAS_LIGA_H1 = ["confederation_liga", "type_liga", "sub_type_liga"]

EDAD_MAXIMA_SUB23 = 23.0  # sub-23: edad < 23.0 (frontera excluyente, no <=)


# ---------------------------------------------------------------------------
# Construccion
# ---------------------------------------------------------------------------

def construir_flags_poblacion(dataset):
    """Agrega es_valido_curva_edad / es_sub23 / es_poblacion_h1 como columnas
    booleanas -- recorte via flag, no via drop de filas."""
    resultado = dataset.copy()

    resultado["es_valido_curva_edad"] = (
        resultado[COLUMNA_EDAD].notna()
        & resultado[COLUMNA_DV].notna()
        & resultado[COLUMNA_JUGADOR].notna()
    )

    resultado["es_sub23"] = resultado["es_valido_curva_edad"] & (resultado[COLUMNA_EDAD] < EDAD_MAXIMA_SUB23)

    if all(c in resultado.columns for c in COLUMNAS_LIGA_H1):
        es_liga_top_europa = (
            (resultado["confederation_liga"] == "europa")
            & (resultado["type_liga"] == "domestic_league")
            & (resultado["sub_type_liga"] == "first_tier")
        )
        resultado["es_poblacion_h1"] = resultado["es_sub23"] & es_liga_top_europa
    else:
        print(
            "ADVERTENCIA: no se encontraron las columnas de liga "
            f"({COLUMNAS_LIGA_H1}) en el dataset -- es_poblacion_h1 queda en "
            "False para todas las filas. Pasar `tablas` (de "
            "d02_construir_variables_contexto.cargar_tablas()) a "
            "construir_dataset_modelado() para construirlas."
        )
        resultado["es_poblacion_h1"] = False

    return resultado


def cargar_club_por_jugador_temporada(dataset_modelable):
    """Devuelve un DataFrame [player_id, season, club_id]. Si dataset_modelable
    ya trae club_id lo usa directo; si no, busca el panel_predictores_*.csv
    mas reciente en la misma carpeta (confirmado 25/09: ahi SI esta club_id,
    via el crosswalk ya usado para los context vars) y lo lee solo con las
    3 columnas necesarias. Devuelve None (con advertencia impresa) si
    ninguna de las dos fuentes lo tiene."""
    if COLUMNA_CLUB in dataset_modelable.columns:
        return dataset_modelable[[COLUMNA_JUGADOR, COLUMNA_TEMPORADA, COLUMNA_CLUB]].copy()

    candidatos = sorted(config.RUTA_DATOS_PROCESSED.glob("panel_predictores_*.csv"))
    if not candidatos:
        print(
            "ADVERTENCIA: dataset_modelable no trae club_id y no se encontro "
            "ningun panel_predictores_*.csv en data/processed para buscarlo -- "
            "es_poblacion_h1 va a quedar en False."
        )
        return None

    ruta = candidatos[-1]
    print(f"club_id no estaba en dataset_modelable -- usando {ruta.name} para el cruce de liga.")
    panel = pd.read_csv(ruta, usecols=[COLUMNA_JUGADOR, COLUMNA_TEMPORADA, COLUMNA_CLUB])
    return panel


def construir_columnas_liga(dataset_modelable, tablas):
    """Arma confederation_liga/type_liga/sub_type_liga por (player_id, season),
    reusando construir_mapa_club_liga_por_temporada() de d02 (club_id+season
    -> competition_id) y cruzando contra competitions.csv. Devuelve None (con
    advertencia impresa) si falta club_id o alguna de las tablas crudas
    necesarias -- nunca inventa el join."""
    club_por_jugador = cargar_club_por_jugador_temporada(dataset_modelable)
    if club_por_jugador is None:
        return None

    tablas_faltantes = [t for t in ("games", "club_games", "competitions") if t not in tablas]
    if tablas_faltantes:
        print(
            f"ADVERTENCIA: faltan tablas crudas {tablas_faltantes} para construir "
            "la liga por club-temporada -- es_poblacion_h1 va a quedar en False."
        )
        return None

    mapa_club_liga = ctx.construir_mapa_club_liga_por_temporada(tablas["games"], tablas["club_games"])

    liga_por_jugador = club_por_jugador.merge(
        mapa_club_liga, on=[COLUMNA_CLUB, COLUMNA_TEMPORADA], how="left"
    )
    liga_por_jugador = liga_por_jugador.merge(
        tablas["competitions"][["competition_id", "confederation", "type", "sub_type"]],
        on="competition_id", how="left",
    )
    liga_por_jugador = liga_por_jugador.rename(columns={
        "confederation": "confederation_liga",
        "type": "type_liga",
        "sub_type": "sub_type_liga",
    })
    return liga_por_jugador[[COLUMNA_JUGADOR, COLUMNA_TEMPORADA] + COLUMNAS_LIGA_H1]


def construir_dataset_modelado(dataset_modelable, tablas=None):
    faltantes = [c for c in COLUMNAS_FINALES if c not in dataset_modelable.columns]
    if faltantes:
        raise KeyError(
            f"Faltan columnas esperadas en dataset_modelable: {faltantes}. "
            "Revisar si cambio el nombre de alguna columna en d06/d08/d09 "
            "(por ejemplo si dataset_modelable no viene de una corrida "
            "posterior al merge de d09, las columnas z_* no van a existir)."
        )

    # Las columnas de liga (COLUMNAS_LIGA_H1) no son parte de la especificacion
    # final CERRADA, pero si estan presentes (o se pueden construir) hay que
    # conservarlas/agregarlas ANTES de restringir a COLUMNAS_FINALES, si no se
    # pierden antes de poder usarlas para es_poblacion_h1.
    columnas_liga_presentes = [c for c in COLUMNAS_LIGA_H1 if c in dataset_modelable.columns]
    resultado = dataset_modelable[COLUMNAS_FINALES + columnas_liga_presentes].copy()

    if not columnas_liga_presentes and tablas is not None:
        liga = construir_columnas_liga(dataset_modelable, tablas)
        if liga is not None:
            resultado = resultado.merge(liga, on=[COLUMNA_JUGADOR, COLUMNA_TEMPORADA], how="left")

    resultado = construir_flags_poblacion(resultado)
    return resultado


def resumen_cobertura(dataset_modelado):
    print(f"\nDataset de modelado: {len(dataset_modelado)} filas x {dataset_modelado.shape[1]} columnas")
    for flag in ("es_valido_curva_edad", "es_sub23", "es_poblacion_h1"):
        n = int(dataset_modelado[flag].sum())
        pct = dataset_modelado[flag].mean() * 100
        print(f"  {flag}: {n} filas ({pct:.2f}%)")
    print("\nCobertura por columna final (no-nulos):")
    for col in COLUMNAS_FINALES:
        pct = dataset_modelado[col].notna().mean() * 100
        print(f"  {col}: {pct:.2f}%")


def main():
    dataset_modelable = cargar_dataset_modelable()
    tablas = ctx.cargar_tablas()
    dataset_modelado = construir_dataset_modelado(dataset_modelable, tablas=tablas)
    resumen_cobertura(dataset_modelado)

    ruta_salida = config.RUTA_DATOS_PROCESSED / f"dataset_modelado_{pd.Timestamp.today().date()}.csv"
    dataset_modelado.to_csv(ruta_salida, index=False)
    print(f"\nGuardado: {ruta_salida}")
    return dataset_modelado


if __name__ == "__main__":
    main()