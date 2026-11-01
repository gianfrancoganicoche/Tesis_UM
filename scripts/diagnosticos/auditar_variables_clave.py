"""
Diagnostico puntual (25/09/2026, version corregida): investigar POR QUE
faltan datos en tres variables clave del modelo -- posicion_amplia_predominante,
edad y log_valor_mercado (variable dependiente).

CORRECCION IMPORTANTE (25/09, misma tarde): la primera version de este
script cruzaba las filas con posicion_amplia_predominante faltante contra
appearances.csv, buscando una columna de posicion ahi. Eso estaba MAL: la
funcion real (construir_posicion_amplia_jugador_temporada, en
d02_construir_variables_contexto.py) usa game_lineups.csv, no
appearances.csv -- y appearances.csv ni siquiera tiene columna de posicion en
este dataset. La corrida real de la version anterior reporto "5.727 filas
con apariciones pero sin posicion determinada", pero eso solo confirmaba que
esas filas tenian registros en appearances.csv (una tabla distinta, sin
relacion con como se arma la posicion) -- no probaba nada sobre por que
falta la posicion. Esta version corrige el cruce usando game_lineups.csv +
games.csv, exactamente las mismas dos tablas y el mismo filtro
(season >= ANIO_MIN_COBERTURA_GAMES, competition_type == "domestic_league")
que usa la funcion real, reimportando su propio MAPA_POSICION_AMPLIA en vez
de duplicarlo (evita que las dos copias diverjan silenciosamente).

Con las tablas correctas, se distinguen tres causas posibles para una fila
con posicion_amplia_predominante faltante:
  (a) CERO filas en game_lineups.csv para ese (player_id, season) despues del
      filtro domestic_league -- explicacion directa de cobertura de datos
      (analoga a la ya documentada para games.csv, pero de una tabla
      distinta: la cobertura de LINEUPS puede empezar mas tarde que la
      cobertura de PARTIDOS, son fuentes separadas en el dataset).
  (b) SI hay filas en game_lineups.csv para ese (player_id, season), pero
      NINGUNA con un valor de 'position' reconocido por MAPA_POSICION_AMPLIA
      -- esto seria una perdida silenciosa de datos (dropna sin aviso),
      exactamente el mismo riesgo que construir_competencia_interna_puesto()
      SI controla con un print de advertencia, pero
      construir_posicion_amplia_jugador_temporada() no.
  (c) Hay filas en game_lineups.csv con posicion reconocida, pero el merge
      con games.csv y/o el filtro de competition_type=="domestic_league"
      las descarta (ej. el jugador solo jugo copa o torneos internacionales
      esa temporada) -- haria falta revisar el propio filtro, no un
      problema de datos crudos.

Ademas, se agrega un chequeo de cobertura de game_lineups.csv POR TEMPORADA,
independiente de cualquier jugador puntual: cuantos game_id de games.csv
(domestic_league, season >= anio_min) tienen AL MENOS una fila en
game_lineups.csv. Esto prueba o descarta directamente la hipotesis de que
game_lineups.csv tiene su PROPIO piso de cobertura, mas tardio que el ya
documentado ANIO_MIN_COBERTURA_GAMES=2012 de games.csv.

Para edad: se agrega un chequeo de causa raiz de los casos "SOLO edad falta"
(log_valor_mercado presente, edad NaN) -- se cruza contra players.csv para
confirmar si date_of_birth esta ausente para esos jugadores (hipotesis mas
probable) o si, mas raro, esta presente y el calculo fallo por otra razon.

log_valor_mercado: sin cambios respecto a la primera version (el cruce
contra player_valuations.csv ya usaba la tabla correcta).

Graceful degradation: si 'game_lineups' o 'games' no estan en cargar_tablas(),
o si game_lineups.csv no tiene la columna 'position' esperada, se avisa y se
sigue con lo que si se puede calcular.
"""

import sys
from pathlib import Path

import pandas as pd

_RAIZ_SCRIPTS = Path(__file__).resolve().parents[1]  # scripts/
for _carpeta in ("config", "dataset", "eda", "diagnosticos"):
    sys.path.insert(0, str(_RAIZ_SCRIPTS / _carpeta))

import config
import d02_construir_variables_contexto as ctx


def cobertura_por_temporada(dataset, columna):
    """Tabla season -> total filas, filas con `columna` faltante, % faltante."""
    tabla = dataset.groupby("season").agg(
        total=(columna, "size"),
        faltantes=(columna, lambda s: s.isna().sum()),
    )
    tabla["pct_faltante"] = (tabla["faltantes"] / tabla["total"] * 100).round(2)
    return tabla.sort_index()


def _lineups_filtrados(game_lineups, games, anio_min):
    """Mismo merge + filtro que usa construir_posicion_amplia_jugador_temporada()."""
    lineups = game_lineups.merge(games[["game_id", "season", "competition_type"]], on="game_id")
    return lineups[(lineups["season"] >= anio_min) & (lineups["competition_type"] == "domestic_league")].copy()


def auditar_cobertura_game_lineups_por_temporada(tablas, anio_min):
    """
    Cuantos partidos (domestic_league, season >= anio_min) de games.csv
    tienen al menos una fila en game_lineups.csv -- prueba directa de si
    game_lineups.csv tiene su propio piso de cobertura, distinto (y
    potencialmente mas tardio) que el de games.csv.
    """
    if "game_lineups" not in tablas or "games" not in tablas:
        print(
            "\n(No se encontro 'game_lineups' y/o 'games' en cargar_tablas() -- se omite el "
            f"chequeo de cobertura de game_lineups.csv por temporada. Claves disponibles: "
            f"{sorted(tablas.keys())})"
        )
        return

    games = tablas["games"]
    game_lineups = tablas["game_lineups"]

    partidos = games[(games["season"] >= anio_min) & (games["competition_type"] == "domestic_league")]
    game_ids_con_lineup = set(game_lineups["game_id"].unique())

    resumen = partidos.groupby("season").agg(total_partidos=("game_id", "nunique")).reset_index()
    resumen["partidos_con_lineup"] = partidos.groupby("season")["game_id"].apply(
        lambda ids: ids.isin(game_ids_con_lineup).sum()
    ).values
    resumen["pct_con_lineup"] = (resumen["partidos_con_lineup"] / resumen["total_partidos"] * 100).round(2)

    print(
        "\nCobertura de game_lineups.csv por temporada (partidos domestic_league de games.csv "
        "que tienen al menos una fila en game_lineups.csv):"
    )
    print(resumen.sort_values("season").to_string(index=False))


def auditar_posicion(dataset, tablas):
    print("\n" + "=" * 70)
    print("AUDITORIA: posicion_amplia_predominante")
    print("=" * 70)

    anio_min = getattr(config, "ANIO_MIN_COBERTURA_GAMES", 2012)

    cobertura_total = dataset["posicion_amplia_predominante"].notna().mean()
    print(f"Cobertura total: {cobertura_total:.4f}")

    tabla_temporada = cobertura_por_temporada(dataset, "posicion_amplia_predominante")
    print("\nCobertura por temporada (temporadas con >0% faltante):")
    print(tabla_temporada[tabla_temporada["faltantes"] > 0].to_string())

    auditar_cobertura_game_lineups_por_temporada(tablas, anio_min)

    faltantes = dataset[dataset["posicion_amplia_predominante"].isna()]
    if faltantes.empty:
        print("\n(No hay filas con posicion_amplia_predominante faltante en este dataset.)")
        return
    print(f"\nTotal de filas con posicion faltante: {len(faltantes)}")

    if "game_lineups" not in tablas or "games" not in tablas:
        print(
            "\n(No se encontro 'game_lineups' y/o 'games' en cargar_tablas() -- se omite el "
            "cruce fila por fila con la fuente real de la posicion. Claves disponibles: "
            f"{sorted(tablas.keys())})"
        )
        return

    if "position" not in tablas["game_lineups"].columns:
        print("\n(game_lineups.csv no tiene columna 'position' -- se omite el cruce fila por fila.)")
        return

    lineups_filtrados = _lineups_filtrados(tablas["game_lineups"], tablas["games"], anio_min)
    lineups_filtrados["posicion_amplia"] = (
        lineups_filtrados["position"].str.lower().str.strip().map(ctx.MAPA_POSICION_AMPLIA)
    )

    claves_faltantes = set(zip(faltantes["player_id"], faltantes["season"]))
    filas_resumen = []
    for player_id, season in claves_faltantes:
        sub = lineups_filtrados[
            (lineups_filtrados["player_id"] == player_id) & (lineups_filtrados["season"] == season)
        ]
        n_lineups = len(sub)
        n_con_posicion_reconocida = sub["posicion_amplia"].notna().sum()
        if n_lineups == 0:
            causa = "(a) sin filas en game_lineups.csv (domestic_league) esa temporada"
        elif n_con_posicion_reconocida == 0:
            causa = "(b) hay filas pero NINGUNA con 'position' reconocida por MAPA_POSICION_AMPLIA"
        else:
            causa = "(c) hay filas con posicion reconocida -- revisar por que no se agrego igual"
        filas_resumen.append({
            "player_id": player_id, "season": season,
            "n_lineups_domestic_league": n_lineups,
            "n_con_posicion_reconocida": n_con_posicion_reconocida,
            "causa": causa,
        })

    resumen = pd.DataFrame(filas_resumen)
    print(
        "\nCausa de cada fila con posicion faltante (recalculado desde game_lineups.csv + "
        "games.csv, con el mismo filtro que usa la funcion real):"
    )
    print(resumen["causa"].value_counts().to_string())

    ejemplos_b_o_c = resumen[resumen["causa"].str.startswith(("(b)", "(c)"))]
    if len(ejemplos_b_o_c) > 0:
        print("\nEjemplos de causa (b)/(c) -- estos SI ameritan mirar la logica de construccion:")
        print(ejemplos_b_o_c.head(10).to_string(index=False))
    else:
        print(
            "\nTodas las filas con posicion faltante caen en causa (a): sin ninguna fila en "
            "game_lineups.csv esa temporada. Es un piso de cobertura de datos de ORIGEN, "
            "no un problema de la logica de construccion."
        )


def auditar_edad(dataset, tablas):
    print("\n" + "=" * 70)
    print("AUDITORIA: edad")
    print("=" * 70)

    if "edad" not in dataset.columns or "log_valor_mercado" not in dataset.columns:
        print("(Faltan 'edad' y/o 'log_valor_mercado' en el dataset -- se omite este audit.)")
        return

    cobertura_edad = dataset["edad"].notna().mean()
    cobertura_dv = dataset["log_valor_mercado"].notna().mean()
    print(f"Cobertura edad: {cobertura_edad:.4f}")
    print(f"Cobertura log_valor_mercado: {cobertura_dv:.4f}")

    mascara_solo_edad = dataset["edad"].isna() & dataset["log_valor_mercado"].notna()
    mascara_solo_dv = dataset["edad"].notna() & dataset["log_valor_mercado"].isna()
    ambas_faltan = (dataset["edad"].isna() & dataset["log_valor_mercado"].isna()).sum()
    print(f"\nFilas con ambas faltantes (esperado): {ambas_faltan}")
    print(f"Filas con SOLO edad faltante: {mascara_solo_edad.sum()}")
    print(f"Filas con SOLO log_valor_mercado faltante: {mascara_solo_dv.sum()}")

    tabla_temporada = cobertura_por_temporada(dataset, "edad")
    print("\nCobertura de edad por temporada (temporadas con >0% faltante):")
    print(tabla_temporada[tabla_temporada["faltantes"] > 0].to_string())

    solo_edad = dataset[mascara_solo_edad]
    if solo_edad.empty:
        print("\n(No hay casos de 'SOLO edad falta' para investigar la causa raiz.)")
        return

    print(f"\nCausa raiz de los {len(solo_edad)} casos 'SOLO edad falta':")
    if "players" not in tablas or "date_of_birth" not in tablas["players"].columns:
        print(
            "(No se encontro 'players' con columna 'date_of_birth' en cargar_tablas() -- "
            "se omite la confirmacion de causa. Claves disponibles: "
            f"{sorted(tablas.keys())})"
        )
        return

    dob = tablas["players"].set_index("player_id")["date_of_birth"]
    solo_edad = solo_edad.copy()
    solo_edad["date_of_birth"] = solo_edad["player_id"].map(dob)
    sin_fecha_nacimiento = solo_edad["date_of_birth"].isna().sum()
    con_fecha_nacimiento = len(solo_edad) - sin_fecha_nacimiento
    print(
        f"  {sin_fecha_nacimiento} de {len(solo_edad)} no tienen date_of_birth en players.csv "
        "(explicacion directa -- sin fecha de nacimiento no se puede calcular la edad)."
    )
    if con_fecha_nacimiento > 0:
        print(
            f"  {con_fecha_nacimiento} SI tienen date_of_birth -- anomalia real, revisar estos "
            "casos puntuales (posible error en el calculo, no en el dato de origen):"
        )
        print(
            solo_edad.loc[solo_edad["date_of_birth"].notna(), ["player_id", "season", "date_of_birth"]]
            .head(10)
            .to_string(index=False)
        )


def auditar_dv(dataset, tablas):
    print("\n" + "=" * 70)
    print("AUDITORIA: log_valor_mercado (variable dependiente)")
    print("=" * 70)

    if "log_valor_mercado" not in dataset.columns:
        print("(Falta 'log_valor_mercado' en el dataset -- se omite este audit.)")
        return

    cobertura_total = dataset["log_valor_mercado"].notna().mean()
    print(f"Cobertura total: {cobertura_total:.4f}")

    tabla_temporada = cobertura_por_temporada(dataset, "log_valor_mercado")
    print("\nCobertura por temporada (temporadas con >0% faltante):")
    print(tabla_temporada[tabla_temporada["faltantes"] > 0].to_string())

    faltantes = dataset[dataset["log_valor_mercado"].isna()]
    if faltantes.empty:
        print("\n(No hay filas con log_valor_mercado faltante en este dataset.)")
        return

    print(f"\nTotal de filas sin DV esa temporada: {len(faltantes)}")
    for col in ("partidos_jugados", "minutos_totales", "minutos_confiables"):
        if col in dataset.columns:
            print(f"\n{col} -- describe() de las filas sin DV:")
            print(faltantes[col].describe())

    if "player_valuations" not in tablas:
        print(
            "\n(No se encontro 'player_valuations' en cargar_tablas() -- se omite el chequeo de "
            f"si el jugador tiene valuaciones en OTRAS temporadas. Claves disponibles: "
            f"{sorted(tablas.keys())})"
        )
        return

    valuaciones = tablas["player_valuations"]
    jugadores_alguna_vez_valuados = set(valuaciones["player_id"].unique())
    jugadores_sin_dv_esta_temporada = set(faltantes["player_id"].unique())

    nunca_valuados = jugadores_sin_dv_esta_temporada - jugadores_alguna_vez_valuados
    valuados_otro_anio = jugadores_sin_dv_esta_temporada & jugadores_alguna_vez_valuados

    print(
        f"\nDe {len(jugadores_sin_dv_esta_temporada)} jugadores con al menos una fila sin DV: "
        f"{len(nunca_valuados)} no tienen NINGUNA valuacion registrada en todo player_valuations.csv "
        f"(nunca fueron valuados); {len(valuados_otro_anio)} SI tienen valuaciones registradas, "
        "solo que no coinciden con esa temporada puntual."
    )


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

    tablas = ctx.cargar_tablas()

    auditar_posicion(dataset, tablas)
    auditar_edad(dataset, tablas)
    auditar_dv(dataset, tablas)


if __name__ == "__main__":
    main()