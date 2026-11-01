"""
revisar_cobertura_historica_jugador.py -- ad-hoc (25/09): usa un caso conocido
(Haaland, cuya etapa temprana en Noruega/Austria ya sabemos -- via
listar_ligas_europa_sin_cobertura.py -- que son ligas SIN cobertura real en
appearances.csv) para responder la pregunta abierta: la restriccion a las 14
ligas cubiertas, es solo del subconjunto sub-23 (Capas 2/3), o de TODO el
panel de modelado (incluida la Capa 1, "toda la carrera")? Esto importa
porque panel_rendimiento se construye desde appearances.csv desde la base,
no como un filtro que se aplica despues.

Compara, por jugador:
- que dice player_valuations.csv (valor de mercado -- independiente de
  appearances.csv, Transfermarkt lo trackea sin importar en que liga jugaba)
- si esa temporada aparece o no como fila en dataset_modelable

OJO con la comparacion de anios: `season` usa la convencion de anio de
arranque de temporada (ver README_convencion_scripts.md), mientras que aca
se usa el anio calendario de la fecha de valuation tal cual, sin pasar por
derivar_season_desde_fecha() (no se quiso asumir su lógica exacta sin
tenerla a mano). Por eso: mirar los AÑOS DE TRANSICION (ej. una valuation de
enero) con un poco de margen -- un desfasaje de +/-1 anio justo en el borde
de una temporada puede ser solo una cuestion de convencion, no un hueco real.
Para las etapas de Molde/Salzburgo especificamente (multiples anios de por
medio, no un caso de borde) el diagnostico es igual de conclusivo.
"""
import sys
from pathlib import Path

import pandas as pd

_RAIZ_SCRIPTS = Path(__file__).resolve().parents[1]
for _carpeta in ("config", "dataset", "eda", "diagnosticos"):
    sys.path.insert(0, str(_RAIZ_SCRIPTS / _carpeta))

import config
import d02_construir_variables_contexto as ctx


def main():
    tablas = ctx.cargar_tablas()
    players = tablas["players"]
    player_valuations = tablas["player_valuations"]

    if "name" not in players.columns:
        print(f"ADVERTENCIA: players.csv no tiene columna 'name' -- columnas reales: {list(players.columns)}. Ajustar el filtro.")
        return

    candidatos = players[players["name"].str.contains("haaland", case=False, na=False)]
    print("=== jugadores que matchean 'haaland' en players.csv ===")
    print(candidatos[["player_id", "name"]].to_string(index=False))
    if len(candidatos) == 0:
        print("No se encontro ningun jugador con ese nombre.")
        return
    if len(candidatos) > 1:
        print("ADVERTENCIA: mas de un candidato -- confirmar el player_id correcto antes de seguir.")
    player_id = candidatos.iloc[0]["player_id"]
    print(f"\nUsando player_id={player_id}")

    valuations = player_valuations[player_valuations["player_id"] == player_id].copy()
    valuations["anio"] = pd.to_datetime(valuations["date"]).dt.year
    print(f"\n=== player_valuations.csv para este jugador: {len(valuations)} filas ===")
    print(valuations[["date", "anio", "market_value_in_eur"]].sort_values("date").to_string(index=False))

    candidatos_dataset = sorted(config.RUTA_DATOS_PROCESSED.glob("dataset_modelable_*.csv"))
    if not candidatos_dataset:
        print("\nNo se encontro ningun dataset_modelable_*.csv en data/processed -- correr d06 primero.")
        return
    ruta = candidatos_dataset[-1]
    print(f"\nUsando {ruta.name} para el panel de modelado")
    dataset_modelable = pd.read_csv(ruta)
    panel_jugador = dataset_modelable[dataset_modelable["player_id"] == player_id].copy()
    print(f"\n=== filas de este jugador en {ruta.name}: {len(panel_jugador)} ===")
    columnas_interes = [c for c in ["player_id", "season", "edad", "log_valor_mercado", "valor_mercado_eur"] if c in panel_jugador.columns]
    if len(panel_jugador) > 0:
        print(panel_jugador[columnas_interes].sort_values("season").to_string(index=False))
    else:
        print("(0 filas -- este jugador no tiene NINGUNA temporada en el panel de modelado)")

    print("\n=== COMPARACION: anios con valor de mercado vs. seasons presentes en el panel ===")
    anios_con_valuation = sorted(valuations["anio"].unique())
    anios_en_panel = sorted(panel_jugador["season"].unique()) if "season" in panel_jugador.columns else []
    print(f"Anios con valor de mercado registrado (player_valuations.csv): {anios_con_valuation}")
    print(f"Seasons presentes en el panel de modelado (dataset_modelable):  {anios_en_panel}")
    faltantes = sorted(set(anios_con_valuation) - set(anios_en_panel))
    print(f"\nAnios CON valor de mercado pero SIN fila en el panel: {faltantes}")
    print(
        "-> Si estos anios coinciden con su etapa en una liga SIN cobertura real "
        "(Molde en Noruega / Salzburgo en Austria, ambas confirmadas sin appearances.csv "
        "via listar_ligas_europa_sin_cobertura.py), confirma que la restriccion de las "
        "14 ligas alcanza a TODO el panel de modelado (incluida la Capa 1 de curva de "
        "edad), no solo al subconjunto sub-23 de las Capas 2/3.\n"
        "-> Recordar el matiz de arriba: un desfasaje de un unico anio justo en el borde "
        "de una temporada puede ser un tema de convencion season vs. anio calendario, no "
        "un hueco real -- lo concluyente es una racha de VARIOS anios faltantes seguidos."
    )


if __name__ == "__main__":
    main()