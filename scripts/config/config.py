"""
Configuracion compartida del pipeline de datos: rutas y constantes que usan
varios scripts. Unica fuente de verdad -- evita que la ruta al snapshot de
datos (o los pisos de cobertura por anio) queden duplicados, y potencialmente
desincronizados, en cada script.

Anclado a la ubicacion de este archivo (no al cwd del proceso), por el mismo
motivo ya documentado en construir_variables_contexto.py: correr un script
desde la raiz del repo, desde scripts/, o via %run en Positron da working
directories distintos, y una ruta relativa se rompe en cuanto el cwd no es
exactamente el esperado.

22/09/2026 (reorganizacion en subcarpetas): este archivo vive en
scripts/config/config.py -- dos niveles por debajo de la raiz del repo (antes
vivia en scripts/, un solo nivel), de ahi el tercer ".parent" en REPO_ROOT
mas abajo. Si este archivo se vuelve a mover, ese es el numero a ajustar.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

RUTA_DATOS_RAW = REPO_ROOT / "data" / "raw"
RUTA_DATOS_PROCESSED = REPO_ROOT / "data" / "processed"

# Reportes de analisis exploratorio (e0X): tablas resumen (.csv) y figuras
# (.png) que no son datos del pipeline en si, sino su salida diagnostica.
RUTA_REPORTS = REPO_ROOT / "reports"
RUTA_REPORTS_FIGURAS = RUTA_REPORTS / "figuras"


def ruta_reports_script(nombre_script):
    """
    Subcarpeta de reports/ dedicada a un script en particular (ej.
    reports/e02_correlaciones_predictores/) -- evita que las tablas de
    distintos scripts de EDA queden sueltas y mezcladas en reports/. Crea la
    carpeta si no existe.

    Uso tipico en el script que llama: config.ruta_reports_script(Path(__file__).stem)
    -- Path(__file__).stem da el nombre del script sin extension, asi el
    nombre de la subcarpeta se deriva solo del nombre del archivo (si el
    script se renombra, la carpeta lo sigue automaticamente, sin que haya que
    tocar este llamado).
    """
    ruta = RUTA_REPORTS / nombre_script
    ruta.mkdir(parents=True, exist_ok=True)
    return ruta


def ruta_figuras_script(nombre_script):
    """
    Misma idea que ruta_reports_script(), pero para reports/figuras/ (ej.
    reports/figuras/e01_analisis_exploratorio/). Ver esa funcion para el
    razonamiento completo.
    """
    ruta = RUTA_REPORTS_FIGURAS / nombre_script
    ruta.mkdir(parents=True, exist_ok=True)
    return ruta

# Snapshot local del dataset (davidcariboo/player-scores) que usan todos los
# scripts por defecto. Para actualizar deliberadamente a una version mas
# nueva: correr guardar_copia_local_datos.py para generar un nuevo
# data/raw/<fecha>_vNNN/, re-validar todo lo que dependa de datos crudos, y
# recien despues actualizar esta ruta -- es la UNICA linea que hay que tocar
# para que todo el pipeline pase a usar la version nueva.
#
# 21/09/2026: se paso deliberadamente de v673 (el snapshot con el que se
# habian validado originalmente las 8 variables de contexto en Tesis_UM) a
# v679, como prueba de punta a punta del pipeline reorganizado. Los numeros
# de cobertura/shapes documentados en los comentarios de
# construir_variables_contexto.py corresponden a v673 -- se esperan
# diferencias reales al correr contra v679 (es precisamente lo que se busca
# comparar), no son un bug si no coinciden exactamente.
RUTA_DATOS_CONGELADOS = RUTA_DATOS_RAW / "2026-09-21_v679"

# Referencia al snapshot anterior (v673), para poder recuperarlo o comparar
# explicitamente mas adelante (ej. cargar_tablas(ruta=RUTA_DATOS_V673)) --
# no se usa por defecto. Solo funciona si esa carpeta existe en este repo
# (copiada desde Tesis_UM); no hace falta para correr el pipeline con v679.
RUTA_DATOS_V673 = RUTA_DATOS_RAW / "2026-07-31_v673"

ANIO_MIN_COBERTURA = 2010        # piso de player_valuations.csv
ANIO_MIN_COBERTURA_GAMES = 2012  # games.csv: cobertura recien densa/consecutiva desde 2012

# 25/09: hallazgo de auditar_variables_clave.py -- game_lineups.csv (fuente real de
# posicion_amplia_predominante) tiene su PROPIO piso de cobertura, distinto y un anio
# mas tarde que el de games.csv: 0.00% de partidos de liga domestica con alguna fila
# de lineup en season=2012, recien confiable (91-100%+) desde 2013. No es un bug de
# construir_posicion_amplia_jugador_temporada(): la funcion arma bien la posicion con
# los datos que existen, simplemente no hay dato de origen para 2012 en esta tabla.
ANIO_MIN_COBERTURA_LINEUPS = 2013