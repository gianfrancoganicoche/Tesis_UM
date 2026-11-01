"""
Script 1 de 7 del pipeline de datos.

Guarda una copia local versionada del dataset crudo (davidcariboo/player-scores)
en data/raw/, separada del cache de kagglehub.

Este script copia los CSVs a data/raw/<fecha>_<version>/, con un metadata.json 
al lado que registra version exacta y fecha de descarga -- asi cualquier resultado 
se puede atar a una copia fija de los datos, no a "la version que estaba en cache ese dia".

kagglehub.dataset_download() guarda en cache local
(~/.cache/kagglehub/), pero eso NO esta versionado ni dentro del repo -- si
Kaggle actualiza la version del dataset, el cache cambia silenciosamente y se
pierde reproducibilidad de cualquier corrida anterior. 

Es el UNICO script del pipeline que pega contra Kaggle en vivo -- todos los
demas (2 a 7) trabajan siempre sobre la copia local ya guardada aca.

Uso: correr desde la raiz del repo (con data/ como subcarpeta). No depende
de nada de src/.
"""

import json
import os
import shutil
from datetime import datetime

import kagglehub

DATASET = "davidcariboo/player-scores"


def guardar_copia_local(dataset: str = DATASET, destino_base: str = "data/raw") -> str:
    """
    Descarga (o reutiliza cache) el dataset via kagglehub y copia los CSVs
    a destino_base/<fecha>_<version>/. No pisa copias anteriores -- cada
    corrida en una fecha distinta, o con una version distinta del dataset,
    genera una carpeta nueva.
    """
    try:
        path_cache = kagglehub.dataset_download(dataset)
    except Exception as e:
        raise RuntimeError(
            f"No se pudo descargar el dataset '{dataset}' via kagglehub. "
            "Verificar que las credenciales de Kaggle esten configuradas "
            "(archivo ~/.kaggle/kaggle.json o variables KAGGLE_USERNAME/KAGGLE_KEY) "
            "y que haya conexion a internet."
        ) from e

    print(f"Dataset en cache: {path_cache}")

    # La version viene codificada en el path de cache de kagglehub
    # (.../versions/N) -- se extrae para que quede en el nombre de carpeta
    # y en el metadata, sin hardcodearla.
    version = os.path.basename(os.path.normpath(path_cache))
    if not version.isdigit():
        print(
            f"Aviso: '{version}' no parece un numero de version de Kaggle "
            "(se esperaba algo como '23'). Se usa igual como parte del nombre "
            "de carpeta, pero vale la pena revisar el path de cache."
        )

    fecha = datetime.now().strftime("%Y-%m-%d")  # noqa: DTZ005
    nombre_carpeta = f"{fecha}_v{version}"
    destino = os.path.join(destino_base, nombre_carpeta)

    if os.path.exists(destino):
        print(f"Ya existe una copia local en {destino} -- no se vuelve a copiar.")
        return destino

    os.makedirs(destino, exist_ok=True)

    csvs = [f for f in os.listdir(path_cache) if f.endswith(".csv")]
    if not csvs:
        raise RuntimeError(f"No se encontraron CSVs en {path_cache} -- revisar la descarga.")

    for csv in csvs:
        shutil.copy2(os.path.join(path_cache, csv), os.path.join(destino, csv))

    metadata = {
        "dataset": dataset,
        "version": version,
        "fecha_descarga": fecha,
        "path_cache_original": path_cache,
        "archivos": sorted(csvs),
    }
    with open(os.path.join(destino, "metadata.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"Copia local guardada en: {destino}")
    print(f"Archivos copiados: {len(csvs)}")

    return destino


if __name__ == "__main__":
    guardar_copia_local()