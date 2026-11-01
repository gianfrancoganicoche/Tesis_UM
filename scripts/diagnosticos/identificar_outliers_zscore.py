"""
Diagnostico puntual (24/09/2026, tercera vuelta): agrega nombre de jugador y
club a los casos extremos ya identificados por revisar_outliers_zscore.py,
para poder citarlos con nombre y equipo en la nota metodologica del z-score.

No reemplaza revisar_outliers_zscore.py -- ese sigue siendo el diagnostico
completo, con todas las columnas de contexto (minutos_confiables, grupo_n,
grupo_chico, etc.) para decidir si un caso es ruido o senal real. Este script
es un complemento, pensado para despues de que esa decision ya esta tomada
(en esta sesion: el piso conjunto de 2 partidos + 180 minutos ya filtro el
ruido, lo que queda es mayormente senal real) -- solo agrega identificacion
legible (nombre de jugador / nombre de club) y guarda una tabla en reports/
para citar directamente en el documento.

No reajusta nada: usa los parametros YA guardados por d09
(data/processed/parametros_zscore_rendimiento_atributos.json) via
zscore.cargar_parametros() + zscore.aplicar_zscore(), igual que
revisar_outliers_zscore.py -- si el reajuste con el piso nuevo todavia no se
corrio, correr primero:
  uv run scripts/dataset/d09_estandarizar_zscore.py --forzar-reajuste

Fuente de nombre/club: players.csv ("name", o "first_name"+"last_name" si
"name" no existe) y clubs.csv ("name") via
d02_construir_variables_contexto.cargar_tablas() -- no se usa ninguna otra
columna de esas tablas. El club de cada fila es el club_id ya presente en el
panel (columna "club_id" del dataset_modelable, si existe) -- es el club
asignado a esa temporada por el pipeline, no necesariamente el club actual
del jugador.
"""

import sys
from pathlib import Path

import pandas as pd

_RAIZ_SCRIPTS = Path(__file__).resolve().parents[1]  # scripts/
for _carpeta in ("config", "dataset", "eda", "diagnosticos"):
    sys.path.insert(0, str(_RAIZ_SCRIPTS / _carpeta))

import config
import d02_construir_variables_contexto as ctx
import d09_estandarizar_zscore as zscore

UMBRAL_Z_EXTREMO = 8  # mismo umbral que revisar_outliers_zscore.py, por consistencia


def _nombre_jugador(players):
    if "name" in players.columns:
        return players.set_index("player_id")["name"]
    if {"first_name", "last_name"}.issubset(players.columns):
        nombre = (players["first_name"].fillna("") + " " + players["last_name"].fillna("")).str.strip()
        return pd.Series(nombre.values, index=players["player_id"])
    raise KeyError(
        "players.csv no tiene ni 'name' ni 'first_name'/'last_name' -- no se puede "
        "armar el nombre del jugador con las columnas disponibles."
    )


def _nombre_club(clubs):
    if "name" not in clubs.columns:
        raise KeyError("clubs.csv no tiene columna 'name' -- no se puede identificar el club.")
    return clubs.set_index("club_id")["name"]


def identificar_variable(dataset, resultado, variable, nombres_jugador, nombres_club):
    """
    Devuelve un DataFrame con los casos de `variable` que superan
    UMBRAL_Z_EXTREMO, con nombre de jugador/club agregados -- o None si no
    hay ningun caso.
    """
    col_z = f"z_{variable}"
    mascara = resultado[col_z].abs() >= UMBRAL_Z_EXTREMO
    if mascara.sum() == 0:
        return None

    columnas_base = ["player_id", "season"]
    columnas_contexto = [
        c for c in ("posicion_amplia_predominante", "club_id", "minutos_totales", "partidos_jugados")
        if c in dataset.columns
    ]
    casos = dataset.loc[mascara, columnas_base + columnas_contexto].copy()
    casos.insert(0, "variable", variable)
    casos["valor_efectivo"] = zscore.serie_efectiva(dataset, variable).loc[mascara]
    casos["z"] = resultado.loc[mascara, col_z]

    casos.insert(1, "jugador", casos["player_id"].map(nombres_jugador))
    if "club_id" in casos.columns:
        idx_club = casos.columns.get_loc("club_id")
        casos.insert(idx_club + 1, "club", casos["club_id"].map(nombres_club))

    return casos.sort_values("z", key=lambda s: s.abs(), ascending=False)


def main():
    candidatos = sorted(config.RUTA_DATOS_PROCESSED.glob("dataset_modelable_*.csv"))
    if not candidatos:
        raise FileNotFoundError(
            "No se encontro ningun dataset_modelable_*.csv en data/processed -- "
            "correr primero d06_extraer_panel_predictores.py."
        )
    ruta_dataset = candidatos[-1]
    print(f"Usando: {ruta_dataset.name}")
    dataset = pd.read_csv(ruta_dataset)

    parametros = zscore.cargar_parametros()
    print(
        f"Parametros de z-score: ajustados el {parametros['fecha_ajuste']} sobre "
        f"{parametros['n_filas_ajuste']} filas."
    )
    resultado = zscore.aplicar_zscore(dataset, parametros)

    tablas = ctx.cargar_tablas()
    nombres_jugador = _nombre_jugador(tablas["players"])
    nombres_club = _nombre_club(tablas["clubs"]) if "clubs" in tablas else None
    if nombres_club is None:
        print("(No se encontro 'clubs' en cargar_tablas() -- se omite el nombre de club.)")

    columnas_mostrar_candidatas = [
        "jugador", "club", "season", "posicion_amplia_predominante",
        "minutos_totales", "partidos_jugados", "valor_efectivo", "z",
    ]

    todos = []
    for variable in parametros["variables"]:
        casos = identificar_variable(dataset, resultado, variable, nombres_jugador, nombres_club)
        if casos is None:
            continue
        todos.append(casos)
        print(f"\n=== {variable}: {len(casos)} caso(s) con |z| >= {UMBRAL_Z_EXTREMO} ===")
        columnas_mostrar = [c for c in columnas_mostrar_candidatas if c in casos.columns]
        print(casos[columnas_mostrar].to_string(index=False))

    if todos:
        tabla_final = pd.concat(todos, ignore_index=True)
        config.RUTA_REPORTS.mkdir(parents=True, exist_ok=True)
        ruta_salida = config.RUTA_REPORTS / "outliers_zscore_con_nombres.csv"
        # ; y coma decimal -- mismo criterio que el resto de reports/ para que
        # Excel en configuracion regional espanol no corra las columnas.
        tabla_final.to_csv(ruta_salida, index=False, sep=";", decimal=",")
        print(f"\nGuardado: {ruta_salida}")
    else:
        print("\nNo hay casos extremos en ninguna variable.")

    return todos


if __name__ == "__main__":
    resultados_identificados = main()