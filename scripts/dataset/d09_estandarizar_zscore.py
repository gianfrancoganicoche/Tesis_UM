"""
Pipeline (d0X, 24/09/2026): estandarizacion z-score, por (posicion_amplia_predominante,
season) DE LA FILA, de las 6 variables finales de rendimiento_it (e05_seleccion_rendimiento.py,
CONFIRMADO 24/09: goles_90, asistencias_90, participacion_produccion,
goles_recibidos_ajustados_90, edad_debut, tarjetas_90) + altura_cm (atributo de
jugador, d08_construir_atributos_jugador.py, CONFIRMADO 24/09 via
e06_atributos_jugador.py que entra al modelo pese a su correlacion pooled/por
posicion debil).

Cierra los ultimos disenos pendientes antes de m01 (todos confirmados con
Gianfranco, ver hilo de decisiones de esta sesion):
  - Poblacion de referencia: TODA la base (capa 1 -- sin restringir edad ni
    liga), no la sub-23 de capa 2/3. El panel que llega a este script YA es
    capa 1 (la restriccion por edad/liga se aplica recien en m01, no en el
    pipeline de datos), asi que no hace falta filtrar nada aca.
  - Momento del calculo: AHORA, sobre toda la base -- no se difiere a
    "calcular solo sobre el split de train". Alternativa 3 es inferencial
    (test de razon de verosimilitud entre modelos anidados), no predictiva
    train/test, asi que no aplica la logica de "no filtrar informacion del
    futuro hacia el pasado" que si aplicaria en un pipeline de ML clasico.
  - Clave de estandarizacion: (posicion_amplia_predominante, season) DE LA
    FILA para las 7 variables, SIN excepcion -- incluye a edad_debut y
    altura_cm pese a ser atributos fijos del jugador (no varian por
    temporada), por consistencia con el resto en vez de una regla aparte
    para cada atributo fijo (altura_cm sigue el mismo criterio que ya se
    habia fijado para edad_debut, decision explicita 24/09).
  - altura_cm, valores fuera de rango plausible (13 filas, 17-19cm, ya
    reportadas sin modificar en d08): se EXCLUYEN de la referencia (no
    contaminan la media/desvio de su grupo) Y quedan con z-score NaN (no se
    les inventa un numero a partir de un dato que se sabe que esta mal) --
    decision explicita 24/09.

PISO DE CONFIABILIDAD: igual que en e01/e05 (goles_90/asistencias_90/
tarjetas_90 -> minutos_confiables; goles_recibidos_ajustados_90 ->
partidos_confiables_goles_ajustados; edad_debut -> debut_confiable;
participacion_produccion sin flag propio, se usa cruda). La definicion se
REPITE aca en vez de importarse de e01/e05 a proposito: d0X (pipeline de
datos) no debe depender de e0X (analisis exploratorio, que a su vez depende
de que el pipeline ya haya corrido) -- importar en esa direccion invertiria
la capa de dependencias del repo. Si la definicion de algun flag cambia, hay
que actualizarla en los dos lugares (e01/e05 y aca).

PISO ADICIONAL DE PARTIDOS PARA EL Z-SCORE (24/09/2026, segunda pasada):
la primera corrida real de este script sobre la base completa (90.408 filas)
dio z-scores extremos (hasta 22.58 desvios) en varias variables. El
diagnostico dedicado (revisar_outliers_zscore.py, ver ese modulo) separo los
casos en dos mecanismos distintos:
  (1) Ruido de muestra de un solo partido: filas con partidos_jugados=1,
      minutos_totales=90 -- pasan el piso de confiabilidad existente
      (minutos_confiables, calibrado para las variables crudas en general),
      pero una tasa "por 90" estimada con un solo partido como muestra tiene
      varianza de muestreo demasiado alta para el z-score -- CERO de los
      ~217 casos extremos tenia grupo chico (posicion x season con
      n < UMBRAL_N_MIN_GRUPO), asi que no era un artefacto de grupo de
      referencia chico, sino de muestra individual chica.
  (2) Eventos raros genuinos en subgrupos de varianza casi nula (ej. un
      arquero que convirtio un gol en una temporada completa de 2000+
      minutos): esto es señal real, no un problema de datos -- Gianfranco
      confirmo explicitamente dejar estos casos tal cual, sin tocar.
Resolucion (confirmada con Gianfranco, sus palabras: "subamos el piso a 2
partidos (180 minutos)"): se agrega PISO_PARTIDOS_MINIMO, un piso ADICIONAL
al de confiabilidad existente (no lo reemplaza), que enmascara a NaN las 5
variables derivadas de conteo de partidos/minutos
(VARIABLES_CON_PISO_PARTIDOS_ADICIONAL) cuando partidos_jugados < 2 --
tanto para el calculo de la referencia (ajustar_parametros) como para el
z-score individual (aplicar_zscore), via serie_efectiva(). Deliberadamente
NO se aplica a edad_debut ni a altura_cm: no son tasas por partido, no
tienen el mecanismo (1) de riesgo de muestra chica que este piso ataca.

SEGUNDA VUELTA (24/09, mismo dia): Gianfranco corrio el reajuste con el piso
de 2 partidos y confirmo con revisar_outliers_zscore.py que efectivamente
saco de la lista de casos extremos a todos los que tenian partidos_jugados=1
(ya no aparece ningun caso con ese valor). Pero el mismo diagnostico revelo
un patron nuevo: varios de los casos que SI pasan partidos_jugados>=2 tienen
apenas 90-150 minutos_totales en total (ej. 2 entradas cortas como suplente
de ~45 min cada una) -- el mismo riesgo de muestra chica que motivo el piso
original, solo que partidos_jugados>=2 no lo captura porque no exige que
esos partidos hayan sido de minutos significativos. Se agrega entonces
PISO_MINUTOS_MINIMO=180, EXIGIDO JUNTO CON (no en lugar de)
PISO_PARTIDOS_MINIMO=2 -- una fila necesita CUMPLIR AMBAS condiciones
(>=2 partidos Y >=180 minutos totales) para no quedar enmascarada por este
piso adicional, sobre las mismas 5 variables de VARIABLES_CON_PISO_PARTIDOS_ADICIONAL.

MISMO PATRON de ajustar/guardar/aplicar que d07_construir_pca_exito_deportivo.py
(ver ese docstring para el razonamiento completo de por que no se re-ajusta
en cada corrida): los parametros (media/desvio por grupo, por variable) se
ajustan UNA vez sobre la base con la que se cierra este diseño y se guardan
versionados en data/processed/parametros_zscore_rendimiento_atributos.json;
de ahi en adelante se aplican tal cual. Reajustar es una decision explicita
(main(forzar_reajuste=True)), no un efecto secundario de correr el pipeline.

Convencion de firma (import directo desde d06_extraer_panel_predictores.py,
sin ejecutar este __main__):
  - ajustar_parametros(dataset) -> dict de parametros (no toca disco)
  - aplicar_zscore(dataset, parametros) -> DataFrame [player_id, season, z_<variable>...]
  - guardar_parametros(parametros) / cargar_parametros() -> IO del .json
  - construir_zscore(dataset, forzar_reajuste=False) -> punto de entrada (usa
    parametros ya guardados si existen, los ajusta la primera vez)

GRUPOS CHICOS: se avisa (no se rompe) si algun grupo (posicion, season) tiene
menos de UMBRAL_N_MIN_GRUPO observaciones para alguna variable -- un desvio
estimado sobre muy pocos casos puede ser inestable. Un grupo con desvio 0 o
con un solo dato (desvio indefinido) deja z-score NaN para esas filas en vez
de devolver infinito o un numero sin sentido. Un grupo (posicion, season) que
aparece al APLICAR pero no existia al AJUSTAR (dato nuevo fuera de la
referencia original) tambien deja z-score NaN, no un error.

SALIDA: data/processed/parametros_zscore_rendimiento_atributos.json
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_RAIZ_SCRIPTS = Path(__file__).resolve().parents[1]  # scripts/
for _carpeta in ("config", "dataset", "eda", "diagnosticos"):
    sys.path.insert(0, str(_RAIZ_SCRIPTS / _carpeta))

import config

VARIABLES_A_ESTANDARIZAR = [
    "goles_90", "asistencias_90", "participacion_produccion",
    "goles_recibidos_ajustados_90", "edad_debut", "tarjetas_90", "altura_cm",
]

# Ver nota del modulo sobre por que esto se repite en vez de importarse de e01/e05.
PISO_CONFIABILIDAD = {
    "goles_90": "minutos_confiables",
    "asistencias_90": "minutos_confiables",
    "tarjetas_90": "minutos_confiables",
    "goles_recibidos_ajustados_90": "partidos_confiables_goles_ajustados",
    "edad_debut": "debut_confiable",
}

# Ver nota del modulo "PISO ADICIONAL DE PARTIDOS PARA EL Z-SCORE" -- capa
# extra sobre PISO_CONFIABILIDAD, especifica de este script (no de e01/e05).
VARIABLES_CON_PISO_PARTIDOS_ADICIONAL = [
    "goles_90", "asistencias_90", "participacion_produccion",
    "goles_recibidos_ajustados_90", "tarjetas_90",
]
COLUMNA_PARTIDOS = "partidos_jugados"
PISO_PARTIDOS_MINIMO = 2  # Gianfranco, 24/09: "subamos el piso a 2 partidos (180 minutos)"
COLUMNA_MINUTOS_TOTALES = "minutos_totales"
PISO_MINUTOS_MINIMO = 180  # Gianfranco, 24/09 (segunda vuelta): agregar tambien este piso --
# partidos_jugados>=2 NO garantiza minutos reales (pueden ser 2 entradas cortas como suplente),
# ver nota del modulo "PISO ADICIONAL DE PARTIDOS PARA EL Z-SCORE" para el hallazgo que lo motivo.

ALTURA_MIN_PLAUSIBLE = 140  # mismo rango que d08_construir_atributos_jugador.py
ALTURA_MAX_PLAUSIBLE = 220

COLUMNA_POSICION = "posicion_amplia_predominante"
COLUMNA_TEMPORADA = "season"
SENTINEL_SIN_POSICION = "__SIN_POSICION__"  # placeholder de texto -- JSON no admite NaN como clave de dict

UMBRAL_N_MIN_GRUPO = 30  # mismo piso que N_MIN_CORRELACION en el resto de e0X -- aca solo dispara un aviso, no bloquea nada

RUTA_PARAMETROS = config.RUTA_DATOS_PROCESSED / "parametros_zscore_rendimiento_atributos.json"


def serie_efectiva(dataset, variable):
    """
    Devuelve la serie de `variable` ya enmascarada donde corresponde -- unico
    punto de esta logica, para que ajustar_parametros() y aplicar_zscore()
    usen siempre la misma version de cada columna.
    """
    if variable == "altura_cm":
        s = dataset["altura_cm"]
        fuera_de_rango = s.notna() & ((s < ALTURA_MIN_PLAUSIBLE) | (s > ALTURA_MAX_PLAUSIBLE))
        return s.where(~fuera_de_rango)

    flag = PISO_CONFIABILIDAD.get(variable)
    if flag is None:
        s = dataset[variable]
    else:
        s = dataset[variable].where(dataset[flag].fillna(False))

    # Piso adicional (ver nota del modulo): se aplica DESPUES del enmascarado
    # por flag de confiabilidad, no en su lugar -- una fila puede pasar
    # minutos_confiables y aun asi tener muy pocos partidos/minutos como
    # muestra. Las dos condiciones son necesarias, no alternativas: se vio en
    # datos reales que partidos_jugados>=2 por si solo no alcanza (pueden ser
    # 2 entradas cortas como suplente, con apenas 90-150 minutos totales) --
    # exigimos ambas (partidos Y minutos) para considerar la muestra suficiente.
    if variable in VARIABLES_CON_PISO_PARTIDOS_ADICIONAL:
        muestra_insuficiente = (
            (dataset[COLUMNA_PARTIDOS].fillna(0) < PISO_PARTIDOS_MINIMO)
            | (dataset[COLUMNA_MINUTOS_TOTALES].fillna(0) < PISO_MINUTOS_MINIMO)
        )
        s = s.where(~muestra_insuficiente)

    return s


def _clave_grupo(dataset):
    """Serie de texto 'posicion||season', con SENTINEL_SIN_POSICION si la posicion es NaN."""
    posicion = dataset[COLUMNA_POSICION].astype("string").fillna(SENTINEL_SIN_POSICION)
    temporada = dataset[COLUMNA_TEMPORADA].astype("string")
    return posicion + "||" + temporada


def ajustar_parametros(dataset):
    """
    Ajusta media/desvio por (posicion, season), por variable, sobre la serie
    efectiva (ya enmascarada/filtrada) de cada una. No toca disco -- eso lo
    hace guardar_parametros() por separado.
    """
    faltantes = [c for c in VARIABLES_A_ESTANDARIZAR if c not in dataset.columns]
    if faltantes:
        raise KeyError(f"No estan en el dataset: {faltantes}.")
    for flag in set(PISO_CONFIABILIDAD.values()):
        if flag not in dataset.columns:
            raise KeyError(f"No esta la columna de flag '{flag}' -- necesaria para enmascarar.")
    if COLUMNA_POSICION not in dataset.columns or COLUMNA_TEMPORADA not in dataset.columns:
        raise KeyError(f"Faltan '{COLUMNA_POSICION}' y/o '{COLUMNA_TEMPORADA}'.")
    if COLUMNA_PARTIDOS not in dataset.columns:
        raise KeyError(
            f"No esta la columna '{COLUMNA_PARTIDOS}' -- necesaria para el piso adicional "
            "de partidos (ver nota del modulo 'PISO ADICIONAL DE PARTIDOS PARA EL Z-SCORE')."
        )
    if COLUMNA_MINUTOS_TOTALES not in dataset.columns:
        raise KeyError(
            f"No esta la columna '{COLUMNA_MINUTOS_TOTALES}' -- necesaria para el piso "
            "adicional de minutos (ver nota del modulo, agregado junto con el piso de partidos)."
        )

    clave_grupo = _clave_grupo(dataset)

    grupos = {}
    grupos_n_chico = {}
    for variable in VARIABLES_A_ESTANDARIZAR:
        efectiva = serie_efectiva(dataset, variable)
        tabla = pd.DataFrame({"clave": clave_grupo, "valor": efectiva}).dropna(subset=["valor"])
        stats = tabla.groupby("clave")["valor"].agg(media="mean", desvio="std", n="count")

        grupos[variable] = {
            clave: {"media": float(fila["media"]),
                    "desvio": (float(fila["desvio"]) if pd.notna(fila["desvio"]) else None),
                    "n": int(fila["n"])}
            for clave, fila in stats.iterrows()
        }
        chicos = stats[stats["n"] < UMBRAL_N_MIN_GRUPO]
        if len(chicos) > 0:
            grupos_n_chico[variable] = chicos.index.tolist()

    return {
        "variables": VARIABLES_A_ESTANDARIZAR,
        "columna_posicion": COLUMNA_POSICION,
        "columna_temporada": COLUMNA_TEMPORADA,
        "grupos": grupos,
        "grupos_n_chico": grupos_n_chico,
        "n_filas_ajuste": len(dataset),
        "fecha_ajuste": pd.Timestamp.now().strftime("%Y-%m-%d"),
    }


def guardar_parametros(parametros, ruta=RUTA_PARAMETROS):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(parametros, f, indent=2, ensure_ascii=False)


def cargar_parametros(ruta=RUTA_PARAMETROS):
    if not ruta.exists():
        raise FileNotFoundError(
            f"No existe {ruta} todavia -- correr ajustar_parametros() + guardar_parametros() "
            "una primera vez (construir_zscore() de este script lo hace automaticamente si el "
            "archivo no esta)."
        )
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def aplicar_zscore(dataset, parametros):
    """
    Aplica la transformacion FIJA (parametros ya ajustados, no un refit) a
    cada fila. z-score queda NaN (nunca inf/nan por division por cero) si:
    el valor efectivo de la fila es NaN, el grupo (posicion, season) de esa
    fila no existia al momento de ajustar los parametros, o el grupo tiene
    desvio nulo/indefinido (un solo dato o todos iguales).
    """
    clave_grupo = _clave_grupo(dataset)
    resultado = dataset[["player_id", "season"]].copy()

    for variable in parametros["variables"]:
        efectiva = serie_efectiva(dataset, variable)
        grupos_variable = parametros["grupos"][variable]

        medias = pd.to_numeric(
            clave_grupo.map(lambda c: grupos_variable.get(c, {}).get("media")), errors="coerce"  # noqa: B023
        )
        desvios = pd.to_numeric(
            clave_grupo.map(lambda c: grupos_variable.get(c, {}).get("desvio")), errors="coerce"  # noqa: B023
        )

        z = pd.Series(np.nan, index=dataset.index, dtype="float64")
        valido = efectiva.notna() & medias.notna() & desvios.notna() & (desvios > 0)
        z.loc[valido] = (efectiva.loc[valido] - medias.loc[valido]) / desvios.loc[valido]
        resultado[f"z_{variable}"] = z

    return resultado


def construir_zscore(dataset, forzar_reajuste=False):
    """
    Punto de entrada pensado para que lo importe d06_extraer_panel_predictores.py:
    usa los parametros ya guardados si existen (caso normal, todas las
    corridas del pipeline despues de la primera), o los ajusta y guarda por
    primera vez si todavia no hay archivo -- forzar_reajuste=True fuerza un
    reajuste deliberado aunque ya exista.
    """
    if RUTA_PARAMETROS.exists() and not forzar_reajuste:
        parametros = cargar_parametros()
        print(
            f"Z-score rendimiento/atributos: usando parametros ya ajustados "
            f"({RUTA_PARAMETROS.name}, ajustados el {parametros['fecha_ajuste']} "
            f"sobre {parametros['n_filas_ajuste']} filas)."
        )
    else:
        motivo = "forzado" if (RUTA_PARAMETROS.exists() and forzar_reajuste) else "primera vez"
        parametros = ajustar_parametros(dataset)
        guardar_parametros(parametros)
        print(f"Z-score rendimiento/atributos: parametros ajustados ({motivo}) y guardados en {RUTA_PARAMETROS}.")

    resultado = aplicar_zscore(dataset, parametros)
    return resultado, parametros


def main(forzar_reajuste=False):
    candidatos = sorted(config.RUTA_DATOS_PROCESSED.glob("dataset_modelable_*.csv"))
    if not candidatos:
        raise FileNotFoundError(
            "No se encontro ningun dataset_modelable_*.csv en data/processed -- "
            "correr primero d06_extraer_panel_predictores.py."
        )
    ruta_dataset = candidatos[-1]
    print(f"Usando: {ruta_dataset.name}")
    dataset = pd.read_csv(ruta_dataset)

    resultado, parametros = construir_zscore(dataset, forzar_reajuste=forzar_reajuste)

    print(f"\nGrupos ({COLUMNA_POSICION} x {COLUMNA_TEMPORADA}) con menos de "
          f"{UMBRAL_N_MIN_GRUPO} observaciones, por variable:")
    grupos_n_chico = parametros["grupos_n_chico"]
    if grupos_n_chico:
        for variable, claves in grupos_n_chico.items():
            print(f"  {variable}: {len(claves)} grupo(s) chico(s) -- ej. {claves[:5]}")
    else:
        print("  (ninguno)")

    print("\nCobertura de cada z-score (sobre el total del dataset):")
    for variable in parametros["variables"]:
        col = f"z_{variable}"
        print(f"  {col}: {resultado[col].notna().mean():.4f}")

    print(
        "\nDescribe de cada z-score (deberian rondar media~0 / desvio~1, sin ser exactos -- "
        "el promedio global no es exactamente el promedio de un promedio por grupo si los "
        "grupos tienen tamanios distintos):"
    )
    for variable in parametros["variables"]:
        col = f"z_{variable}"
        print(f"\n{col}:")
        print(resultado[col].describe())

    return resultado, parametros


if __name__ == "__main__":
    # --forzar-reajuste: unica forma de disparar un reajuste deliberado sin
    # editar el codigo (ver docstring del modulo / de construir_zscore sobre
    # por que esto nunca es automatico). Necesario, por ejemplo, la primera
    # vez que se corre este script despues de un cambio en la definicion de
    # serie_efectiva() (como el piso adicional de partidos, 24/09 segunda
    # pasada) -- si ya existe un .json de parametros viejo, una corrida normal
    # lo reutiliza tal cual e ignora el cambio de definicion.
    _forzar = "--forzar-reajuste" in sys.argv
    resultado_zscore, parametros_zscore = main(forzar_reajuste=_forzar)