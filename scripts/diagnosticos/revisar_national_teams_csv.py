"""
revisar_national_teams_csv.py -- ad-hoc (25/09)

Motivo: corriendo revisar_fuentes_seleccion_nacional.py, Gianfranco encontro
dos archivos crudos que ese script no tenia en cuenta -- national_teams.csv y
countries.csv -- que no estaban documentados hasta ahora (aparecieron recien
en esta version de datos, 2026-09-21_v679, o simplemente no se habian mirado
todavia; el 24/09 Gianfranco ya habia pedido explorar "players, national_teams
y clubs" sin alcance mas especifico). Antes de asumir que no sirven para nada,
hay que mirar que traen realmente.

Este script NO asume ningun schema. Para cada archivo candidato que exista,
imprime: shape, columnas + dtypes, las primeras filas, y para cada columna
la cantidad de valores unicos + una muestra -- para poder decidir a ojo si
alguna de estas tablas ofrece una via DISTINTA de vincular jugador a
seleccion nacional (por ejemplo, un roster/plantel por temporada que no
dependa de un game_id especifico, a diferencia de todo lo ya revisado en
revisar_fuentes_seleccion_nacional.py).

Si national_teams.csv (o countries.csv) tiene una columna player_id, eso
cambia por completo la conclusion del diagnostico anterior -- se marca con
una alerta explicita al final.
"""
import sys
from pathlib import Path

import pandas as pd

_RAIZ_SCRIPTS = Path(__file__).resolve().parents[1]
for _carpeta in ("config", "dataset", "eda", "diagnosticos"):
    sys.path.insert(0, str(_RAIZ_SCRIPTS / _carpeta))

import config

ARCHIVOS_A_REVISAR = ["national_teams.csv", "countries.csv"]


def revisar_archivo(nombre_archivo, ruta_carpeta):
    ruta = ruta_carpeta / nombre_archivo
    if not ruta.exists():
        print(f"\n=== {nombre_archivo}: no existe en {ruta_carpeta}, se omite ===")
        return None

    tabla = pd.read_csv(ruta, low_memory=False)
    print(f"\n=== {nombre_archivo}: {tabla.shape[0]} filas x {tabla.shape[1]} columnas ===")
    print(f"Columnas y dtypes:\n{tabla.dtypes.to_string()}")

    print(f"\nPrimeras 10 filas:")
    print(tabla.head(10).to_string(index=False))

    print(f"\nPor columna -- nunique y muestra de valores:")
    for columna in tabla.columns:
        nunique = tabla[columna].nunique(dropna=True)
        muestra = tabla[columna].dropna().unique()[:5]
        print(f"  - {columna}: nunique={nunique}, muestra={list(muestra)}")

    return tabla


def main():
    ruta_carpeta = config.RUTA_DATOS_CONGELADOS
    tablas = {}
    for nombre_archivo in ARCHIVOS_A_REVISAR:
        tabla = revisar_archivo(nombre_archivo, ruta_carpeta)
        if tabla is not None:
            tablas[nombre_archivo] = tabla

    print("\n=== CONCLUSION ===")
    if not tablas:
        print("Ninguno de los dos archivos existe en esta carpeta de datos -- no hay nada nuevo que revisar.")
        return

    for nombre_archivo, tabla in tablas.items():
        if "player_id" in tabla.columns:
            print(
                f"ALERTA: {nombre_archivo} SI tiene columna 'player_id' -- esto puede ser una via "
                "distinta (independiente de game_id/appearances.csv/game_lineups.csv) para vincular "
                "jugador a seleccion nacional. Revisar el resto de sus columnas (arriba) para entender "
                "que representa cada fila -- ojo si tiene alguna nocion de season/anio/fecha, que es lo "
                "que definiria si sirve como variable de panel."
            )
        else:
            print(f"{nombre_archivo}: no tiene columna 'player_id' -- no vincula directamente jugador a seleccion. Revisar columnas de arriba por si sirve como tabla de referencia (ej. mapear un team_id de seleccion a un pais) en vez de como fuente directa.")


if __name__ == "__main__":
    main()