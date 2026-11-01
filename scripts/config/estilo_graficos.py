"""
Estilo visual compartido para todos los graficos del proyecto (tipografia,
colores). Unica fuente de verdad -- mismo criterio que config.py: se importa
en cualquier script que genere figuras (hoy e01, mas adelante cualquier otro
analisis o el modelado) para que todos los graficos de la tesis se vean
consistentes, sin repetir la configuracion en cada script.

PALETA -- NO ELEGIDA A OJO:
Los colores no se eligieron por gusto -- se corrieron contra un validador
computacional (metodo de dataviz de Anthropic, scripts/validate_palette.js)
que mide, sobre cada color:
  - banda de luminosidad OKLCH (ni muy claro ni muy oscuro para el rol)
  - piso de croma (que no "lea" como gris)
  - separacion de color (Delta E en OKLab) bajo simulacion de daltonismo
    protanopia/deuteranopia (modelo Machado-Oliveira-Fernandes 2009)
  - contraste minimo 3:1 contra el fondo (WCAG)

Se probo explicitamente una version "pastel" (mezclando estos mismos colores
con 20% y 40% de blanco) y NO paso el validador: aclarar los colores los saca
de la banda de luminosidad valida, los deja por debajo del piso de croma, y
reduce la separacion de color bajo daltonismo por debajo del umbral seguro --
sobre un fondo blanco, "pastel" y "seguro para daltonismo" tiran en
direcciones opuestas. Por eso se opto por esta paleta base (tonos suaves pero
no lavados), que ademas de pasar todos los chequeos de separacion de color,
supera el piso de contraste SIN necesitar ningun resguardo adicional (ver
notas de cada constante abajo). Paleta completa (8 tonos, orden fijo) en
docs/estilo_graficos_notas.md si en algun momento hace falta un tercer o
cuarto color categorico -- por ahora este script solo usa 2 (azul/naranja)
mas gris neutro, que son los unicos que hacen falta para EDA univariado/
bivariado.

TIPOGRAFIA:
Monserrat, cargada desde archivos .ttf locales (no depende de que este
instalada en el sistema operativo -- mismo motivo de reproducibilidad que
config.py: que un grafico se vea igual en cualquier maquina que corra este
repo, no solo en la tuya). Los archivos NO se pueden descargar automatico
desde este entorno -- hay que bajarlos una vez a mano, ver instrucciones en
el mensaje que acompaño este script. Si no estan presentes, cae de forma
prolija a la fuente sans-serif por defecto del sistema (avisando por
consola, nunca rompe la corrida).
"""

import sys
import warnings
from pathlib import Path

import matplotlib
import matplotlib.font_manager as fm
from matplotlib.colors import LinearSegmentedColormap

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config

RUTA_FUENTES = config.REPO_ROOT / "assets" / "fonts" / "Montserrat"
NOMBRE_FUENTE = "Montserrat"

# --- Paleta categorica (2 de los 8 slots validados -- ver docstring) ---
COLOR_PRINCIPAL = "#2a78d6"   # slot 1 (azul) -- serie unica / True / polo positivo
COLOR_SECUNDARIO = "#eb6834"  # slot 2 (naranja) -- accento/overlay / False / polo negativo
COLOR_NEUTRO = "#c3c2b7"      # gris neutro (baseline/axis del esquema) -- NaN / faltante

# --- Rampa secuencial (un solo hue, claro->oscuro -- para densidad/magnitud) ---
# Pasos documentados del hue "azul" (100->700 claro->oscuro), no inventados.
_PASOS_AZUL = [
    "#cde2fb", "#b7d3f6", "#9ec5f4", "#86b6ef", "#6da7ec", "#5598e7",
    "#3987e5", "#2a78d6", "#256abf", "#1c5cab", "#184f95", "#104281", "#0d366b",
]
CMAP_SECUENCIAL = LinearSegmentedColormap.from_list("secuencial_azul", _PASOS_AZUL)

# --- Rampa divergente (para correlaciones: polo negativo <-> neutro <-> polo positivo) ---
CMAP_DIVERGENTE = LinearSegmentedColormap.from_list(
    "divergente_rojo_azul", ["#e34948", "#f0efec", "#2a78d6"]
)


def _registrar_montserrat():
    if not RUTA_FUENTES.is_dir():
        warnings.warn(
            f"No se encontro la carpeta de fuentes en {RUTA_FUENTES} -- "
            "los graficos van a usar la tipografia sans-serif por defecto. "
            "Ver instrucciones para descargar Montserrat.",
            stacklevel=2,
        )
        return False

    archivos_ttf = list(RUTA_FUENTES.glob("*.ttf"))
    if not archivos_ttf:
        warnings.warn(
            f"La carpeta {RUTA_FUENTES} existe pero no tiene archivos .ttf -- "
            "los graficos van a usar la tipografia sans-serif por defecto.",
            stacklevel=2,
        )
        return False

    for archivo in archivos_ttf:
        fm.fontManager.addfont(str(archivo))

    return True


def aplicar_estilo():
    """
    Configura matplotlib para todo el resto del script: tipografia (Montserrat
    si esta disponible, sans-serif por defecto si no) y una estetica sobria
    (ejes/grilla recesivos, sin marco superior/derecho) -- se llama UNA vez al
    principio de main(), antes de generar cualquier figura.
    """
    matplotlib.use("Agg")

    fuente_disponible = _registrar_montserrat()
    familia = NOMBRE_FUENTE if fuente_disponible else "sans-serif"

    matplotlib.rcParams.update({
        "font.family": familia,
        "font.size": 10,
        "axes.titlesize": 12,
        "axes.labelsize": 10,
        "axes.edgecolor": COLOR_NEUTRO,
        "axes.labelcolor": "#0b0b0b",
        "axes.grid": False,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "figure.facecolor": "#fcfcfb",
        "axes.facecolor": "#fcfcfb",
        "text.color": "#0b0b0b",
    })

    if not fuente_disponible:
        print(f"(graficos con tipografia por defecto -- ver notas para instalar {NOMBRE_FUENTE})")