"""
Atributos fisicos/de perfil del jugador (altura, pie habil, condicion
comunitaria), tomados directamente de players.csv.

Motivo (24/09/2026): hipotesis_y_diseno_v2.md ya planeaba incluir altura
(estandarizada por posicion), pie habil y es_comunitario en el modelo. De
las tres, altura y pie nunca se habian construido en ningun momento del
pipeline (columnas crudas de players.csv sin usar). es_comunitario es
distinta: los documentos de diseno (hipotesis_y_diseno_v2.md,
diccionario_variables.md, tema_tesis.md) confirman que SI se construyo y
valido en algun momento -- cobertura 99.5%, 41.6% de la base clasificada
como comunitaria -- pero el codigo que la produjo no aparece en ninguno de
los scripts del pipeline disponibles hoy (se reviso especificamente
construir_panel_predictores.py, construir_variable_dependiente.py,
construir_variables_contexto.py y construir_variables_rendimiento.py del
repo viejo Tesis_UM: cero coincidencias). Tratamiento: los NUMEROS
documentados (99.5%/41.6%) se toman como un resultado historico real, pero
el CODIGO se reconstruye de cero aca -- no hay nada que "portar".

A diferencia del resto de las variables de contexto/rendimiento (que se
agregan desde games/appearances/transfers a nivel club-temporada o
jugador-temporada), esto es un passthrough casi directo de players.csv:
altura, pie y ciudadania son atributos FIJOS del jugador (una sola fila por
player_id), no varian por temporada -- por eso el merge aguas abajo es por
player_id solo, no por (player_id, season) como el resto del panel.

Limpieza aplicada (ver construir_atributos_jugador):
- altura_cm: valores <=0 se tratan como sentinela de "sin dato" (se
  convierten a NaN, no se dejan pasar como si fueran una altura real).
  Valores fuera de un rango humanamente plausible (140-220 cm) se REPORTAN
  pero NO se tocan -- podrian ser datos legitimos de casos extremos
  (arqueros muy altos) o errores de carga; se deja a revision manual, mismo
  criterio que "edad < 14 o > 42" en d06.
- pie_habil: se normaliza a minusculas/sin espacios y se reporta cualquier
  categoria fuera del vocabulario esperado {"right", "left", "both"} sin
  descartarla (mismo patron defensivo que MAPA_POSICION_AMPLIA en d02:
  avisar, no fallar en silencio).
- es_comunitario: country_of_citizenship contra PAISES_LIBRE_CIRCULACION
  (UE-27 + EEE (Islandia, Liechtenstein, Noruega) + Suiza). Decision
  explicita (confirmada con Gianfranco 24/09): Reino Unido (England,
  Scotland, Wales, Northern Ireland, United Kingdom, bajo cualquiera de
  esos nombres) se trata SIEMPRE como no comunitario, sin importar la
  temporada -- se prioriza simplicidad y consistencia sobre precision
  historica pre/post-Brexit (enero 2021). Limitacion reconocida y
  documentada, no un descuido: un futbolista britanico que jugo en la UE
  en 2018 con libre circulacion real queda igual clasificado como no
  comunitario que uno que juega hoy. Ciudadania nula -> es_comunitario
  nulo (no False: "sin dato" y "no comunitario" son cosas distintas). Si
  el campo trae mas de una ciudadania separada por coma (posible caso de
  doble ciudadania, ver limitacion documentada en hipotesis_y_diseno_v2.md
  de que el campo "no captura dobles ciudadanias por ascendencia"), se
  considera comunitario si CUALQUIERA de las ciudadanias listadas lo es --
  mejora marginal sobre la limitacion documentada, no una solucion
  completa (sigue dependiendo de que el dato crudo las liste todas).
- Se valida que players.csv no tenga player_id duplicado antes de mergear
  -- si lo tuviera, un merge por player_id fanearia filas del panel en
  silencio.
"""

import sys
from pathlib import Path

import pandas as pd

_RAIZ_SCRIPTS = Path(__file__).resolve().parents[1]  # scripts/
for _carpeta in ("config", "dataset", "eda", "diagnosticos"):
    sys.path.insert(0, str(_RAIZ_SCRIPTS / _carpeta))

ALTURA_MIN_PLAUSIBLE = 140
ALTURA_MAX_PLAUSIBLE = 220
VOCABULARIO_PIE_ESPERADO = {"right", "left", "both"}

# UE-27
_PAISES_UE = {
    "austria", "belgium", "bulgaria", "croatia", "cyprus", "czech republic",
    "czechia", "denmark", "estonia", "finland", "france", "germany",
    "greece", "hungary", "ireland", "italy", "latvia", "lithuania",
    "luxembourg", "malta", "netherlands", "poland", "portugal", "romania",
    "slovakia", "slovenia", "spain", "sweden",
}
# EEE no-UE
_PAISES_EEE_NO_UE = {"iceland", "liechtenstein", "norway"}
# Suiza (acuerdo bilateral de libre circulacion con la UE, no es EEE formalmente)
_SUIZA = {"switzerland"}

PAISES_LIBRE_CIRCULACION = _PAISES_UE | _PAISES_EEE_NO_UE | _SUIZA

# Reino Unido: excluido siempre, ver nota de Brexit en el docstring del modulo.
_PAISES_UK_EXCLUIDOS_EXPLICITAMENTE = {
    "england", "scotland", "wales", "northern ireland", "united kingdom",
}


def _es_comunitario_una_ciudadania(pais_normalizado):
    return pais_normalizado in PAISES_LIBRE_CIRCULACION


def _calcular_es_comunitario(valor_crudo):
    """
    valor_crudo: el string original de country_of_citizenship (o NaN).
    Devuelve True/False/pd.NA. Soporta el caso de mas de una ciudadania
    separada por coma (ver nota de doble ciudadania en el docstring).
    """
    if pd.isna(valor_crudo):
        return pd.NA

    paises = [p.strip().lower() for p in str(valor_crudo).split(",") if p.strip()]
    if not paises:
        return pd.NA

    return any(_es_comunitario_una_ciudadania(p) for p in paises)


def construir_atributos_jugador(players):
    """
    Devuelve un DataFrame (player_id, altura_cm, pie_habil, es_comunitario)
    -- una fila por jugador, lista para mergear por player_id (no por
    player_id+season) contra panel_predictores / dataset_modelable.
    """
    duplicados = players["player_id"].duplicated().sum()
    if duplicados > 0:
        raise ValueError(
            f"players.csv tiene {duplicados} player_id duplicados -- no se "
            "mergea hasta resolver la causa (un merge por player_id fanearia "
            "filas del panel en silencio)."
        )

    atributos = players[["player_id", "height_in_cm", "foot", "country_of_citizenship"]].copy()
    atributos = atributos.rename(columns={"height_in_cm": "altura_cm", "foot": "pie_habil"})

    # --- altura_cm ---
    n_altura_no_positiva = (atributos["altura_cm"] <= 0).sum()
    if n_altura_no_positiva > 0:
        print(f"altura_cm <= 0 (sentinela de sin-dato, se convierte a NaN): {n_altura_no_positiva}")
        atributos.loc[atributos["altura_cm"] <= 0, "altura_cm"] = pd.NA

    fuera_de_rango = atributos[
        atributos["altura_cm"].notna()
        & ((atributos["altura_cm"] < ALTURA_MIN_PLAUSIBLE) | (atributos["altura_cm"] > ALTURA_MAX_PLAUSIBLE))
    ]
    print(
        f"altura_cm fuera de rango plausible ({ALTURA_MIN_PLAUSIBLE}-{ALTURA_MAX_PLAUSIBLE} cm), "
        f"NO modificado, a revisar a mano: {len(fuera_de_rango)}"
    )
    if len(fuera_de_rango) > 0:
        print(fuera_de_rango[["player_id", "altura_cm"]].to_string(index=False))

    # --- pie_habil ---
    atributos["pie_habil"] = atributos["pie_habil"].astype("string").str.strip().str.lower()
    valores_observados = set(atributos["pie_habil"].dropna().unique())
    inesperados = valores_observados - VOCABULARIO_PIE_ESPERADO
    if inesperados:
        print(f"pie_habil -- categorias fuera del vocabulario esperado {VOCABULARIO_PIE_ESPERADO}: {inesperados}")

    # --- es_comunitario ---
    n_con_coma = atributos["country_of_citizenship"].astype("string").str.contains(",", na=False).sum()
    if n_con_coma > 0:
        print(f"country_of_citizenship con mas de una ciudadania listada (separadas por coma): {n_con_coma}")

    atributos["es_comunitario"] = atributos["country_of_citizenship"].apply(_calcular_es_comunitario)
    atributos["es_comunitario"] = atributos["es_comunitario"].astype("boolean")  # preserva NA, no lo castea a False

    # Paises no reconocidos como comunitarios, para que Gianfranco pueda
    # chequear a ojo que no haya variantes de escritura de un pais de la
    # lista que se esten perdiendo (ej. si el dataset trajera "Czechia" en
    # vez de "Czech Republic" ya esta cubierto arriba, pero esto sirve como
    # red de seguridad para casos no anticipados).
    no_comunitarios_normalizados = (
        atributos.loc[atributos["es_comunitario"] == False, "country_of_citizenship"]
        .astype("string").str.strip().str.lower()
    )
    top_no_comunitarios = no_comunitarios_normalizados.value_counts().head(15)
    print("\nTop 15 valores de country_of_citizenship clasificados como NO comunitario (chequeo visual de variantes de escritura):")
    print(top_no_comunitarios.to_string())

    solapa_con_uk_excluido = set(no_comunitarios_normalizados.unique()) & _PAISES_UK_EXCLUIDOS_EXPLICITAMENTE
    if solapa_con_uk_excluido:
        print(f"\n(De los anteriores, {solapa_con_uk_excluido} corresponden a Reino Unido -- excluido a proposito, ver docstring del modulo)")

    return atributos[["player_id", "altura_cm", "pie_habil", "es_comunitario"]]


if __name__ == "__main__":
    import d02_construir_variables_contexto as ctx

    tablas = ctx.cargar_tablas()
    atributos_jugador = construir_atributos_jugador(tablas["players"])

    print(f"\natributos_jugador: {atributos_jugador.shape[0]} filas, {atributos_jugador.shape[1]} columnas.")
    print(f"Cobertura altura_cm: {atributos_jugador['altura_cm'].notna().mean():.4f}")
    print(f"Cobertura pie_habil: {atributos_jugador['pie_habil'].notna().mean():.4f}")
    print(f"Cobertura es_comunitario: {atributos_jugador['es_comunitario'].notna().mean():.4f}")
    print(f"Proporcion comunitaria (sobre no-nulos): {atributos_jugador['es_comunitario'].mean():.4f}")
    print("\naltura_cm - describe:")
    print(atributos_jugador["altura_cm"].describe())
    print("\npie_habil - value_counts:")
    print(atributos_jugador["pie_habil"].value_counts(dropna=False))
    print("\nes_comunitario - value_counts:")
    print(atributos_jugador["es_comunitario"].value_counts(dropna=False))