"""
Diagnostico puntual (24/09/2026): investigar los z-scores extremos (20+
desvios) que aparecieron en la primera corrida real de
d09_estandarizar_zscore.py (goles_90 max=22.58, asistencias_90 max=21.70,
participacion_produccion max=15.73, tarjetas_90 max=13.90). Hipotesis a
distinguir, NO excluyentes entre si:

  (a) Artefacto de GRUPO CHICO: el grupo (posicion, season) de esa fila
      tiene pocas observaciones (cerca de o por debajo de
      d09.UMBRAL_N_MIN_GRUPO=30) y por eso un desvio estimado inestable
      (chico por casualidad de muestra) -- el mismo valor crudo, en un
      grupo mas grande, daria un z mucho mas moderado.
  (b) Dato real pero EXTREMO dentro de un grupo grande: el grupo tiene
      tamanio normal, pero la distribucion de la variable es naturalmente
      muy asimetrica (la mayoria de los valores cerca de 0, cola larga a la
      derecha) -- una temporada realmente excepcional de un jugador puede
      generar un z legitimo de 10+ sin que haya ningun problema de datos.
  (c) Resabio de baja muestra de minutos PESE al piso de confiabilidad: el
      piso (minutos_confiables) filtra los casos mas obvios de
      extrapolacion (ver revisar_outliers_rate_90.py, 14 filas con
      minutos_totales=1), pero podria no eliminar del todo una muestra
      todavia chica que pasa el piso y aun asi extrapola una tasa alta.

No es parte del pipeline (no depende de nada de d0X salvo d09 y config, para
poder recalcular los z-scores exactamente igual que la corrida real, sin
tener que esperar a que Gianfranco vuelva a correr d06) -- consulta ad-hoc,
sin prefijo, mismo patron que revisar_outliers_rate_90.py y
revisar_edad_outliers.py. Usa los parametros YA guardados por
d09_estandarizar_zscore.py (data/processed/parametros_zscore_rendimiento_atributos.json)
-- si no existen todavia, correr d09 una vez primero.
"""

import sys
from pathlib import Path

import pandas as pd

_RAIZ_SCRIPTS = Path(__file__).resolve().parents[1]  # scripts/
for _carpeta in ("config", "dataset", "eda", "diagnosticos"):
    sys.path.insert(0, str(_RAIZ_SCRIPTS / _carpeta))

import config
import d09_estandarizar_zscore as zscore

UMBRAL_Z_EXTREMO = 8  # deliberadamente por debajo de los casos reportados (13-22), para no dejar afuera casos limitrofes


def diagnosticar_variable(dataset, resultado, parametros, variable, columnas_contexto):
    col_z = f"z_{variable}"
    clave_grupo = zscore._clave_grupo(dataset)
    efectiva = zscore.serie_efectiva(dataset, variable)
    grupos_variable = parametros["grupos"][variable]

    mascara = resultado[col_z].abs() >= UMBRAL_Z_EXTREMO
    n_casos = mascara.sum()
    print(f"\n=== {col_z}: {n_casos} fila(s) con |z| >= {UMBRAL_Z_EXTREMO} (de {len(dataset)}) ===")
    if n_casos == 0:
        return

    casos = dataset.loc[mascara, ["player_id", "season"] + columnas_contexto].copy()
    casos["valor_efectivo"] = efectiva.loc[mascara]
    casos["z"] = resultado.loc[mascara, col_z]
    casos["clave_grupo"] = clave_grupo.loc[mascara]
    casos["grupo_media"] = casos["clave_grupo"].map(lambda c: grupos_variable.get(c, {}).get("media"))
    casos["grupo_desvio"] = casos["clave_grupo"].map(lambda c: grupos_variable.get(c, {}).get("desvio"))
    casos["grupo_n"] = casos["clave_grupo"].map(lambda c: grupos_variable.get(c, {}).get("n"))
    casos["grupo_chico"] = casos["grupo_n"] < zscore.UMBRAL_N_MIN_GRUPO

    casos = casos.sort_values("z", key=lambda s: s.abs(), ascending=False)
    print(casos.drop(columns=["clave_grupo"]).to_string(index=False))

    print(f"\n  De estos {n_casos} casos: {casos['grupo_chico'].sum()} en grupo chico (n < "
          f"{zscore.UMBRAL_N_MIN_GRUPO}, hipotesis (a)); {(~casos['grupo_chico']).sum()} en grupo "
          "de tamanio normal (hipotesis (b) o (c), ver minutos_totales/partidos_jugados si estan "
          "disponibles en el dataset para distinguirlas).")
    print("  grupo_n -- describe de estos casos:")
    print(casos["grupo_n"].describe())


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
    print(f"Parametros de z-score: ajustados el {parametros['fecha_ajuste']} sobre "
          f"{parametros['n_filas_ajuste']} filas.")
    resultado = zscore.aplicar_zscore(dataset, parametros)

    # Columnas de contexto extra para leer los casos a ojo -- se agregan solo
    # si existen en el dataset (minutos_totales/partidos_jugados pueden no
    # estar en un dataset_modelable viejo o en un stub de test).
    columnas_contexto_candidatas = [
        zscore.COLUMNA_POSICION, "minutos_totales", "partidos_jugados", "minutos_confiables",
    ]
    columnas_contexto = [c for c in columnas_contexto_candidatas if c in dataset.columns]
    faltantes_contexto = [c for c in columnas_contexto_candidatas if c not in dataset.columns]
    if faltantes_contexto:
        print(f"(Columnas de contexto no disponibles en este dataset, se omiten del detalle: {faltantes_contexto})")

    for variable in parametros["variables"]:
        diagnosticar_variable(dataset, resultado, parametros, variable, columnas_contexto)

    return resultado, parametros


if __name__ == "__main__":
    resultado_diagnostico, parametros_diagnostico = main()