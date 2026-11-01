"""
Analisis exploratorio (e0X, 22/09/2026): PCA sobre el cluster 1 de
e02_correlaciones_predictores.py ("exito deportivo del club", decision ya
tomada de reducirlo via PCA en vez de representante unico o indice simple --
ver learnings-and-pitfalls). No guarda nada en el pipeline todavia -- es el
paso previo, con la varianza explicada, los loadings, la cobertura real y
los graficos de respaldo, antes de fijar la componente final en un script
d0X (d07).

PARTE 1 corre el PCA sobre las 8 variables originales del cluster. Esa
corrida mostro que pct_victorias_con/pct_victorias_sin no deberian estar en
este cluster -- generan el 100% del NaN del bloque (41.58% del panel, por el
piso propio de min_partidos_grupo=5 en construir_diferencial_con_sin_jugador)
y su contraste (PC2, loadings 0.74/-0.67 con el resto del cluster en ~0) mide
el efecto individual del jugador sobre el resultado del equipo (tipo
plus-minus, Hvattum 2020), no exito de club -- mismo tipo de problema de
mediador/endogeneidad ya resuelto para el cluster 3 de minutos jugados.

PARTE 2 corre el mismo PCA solo sobre las 6 variables genuinamente a nivel
club-temporada, sin el par con/sin, para recuperar cobertura completa (0%
NaN) y confirmar que el PC1 no cambia sustancialmente (chequeo de
continuidad al final de esa seccion).

PARTE 3 genera 3 graficos de esta segunda corrida (scree plot, loadings de
PC1, biplot PC1/PC2) en reports/figuras/, con el estilo compartido del repo.
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

_RAIZ_SCRIPTS = Path(__file__).resolve().parents[1]  # scripts/, tras la reorganizacion en subcarpetas (22/09)
for _carpeta in ("config", "dataset", "eda", "diagnosticos"):
    sys.path.insert(0, str(_RAIZ_SCRIPTS / _carpeta))

import config
import estilo_graficos as estilo

# Las 8 variables del cluster 1 (e02_correlaciones_predictores.py, |r| 0.72-0.99).
# posicion_final/posicion_promedio son "mas bajo = mejor" -- se invierten mas
# abajo para que las 8 apunten en la misma direccion ("exito"), asi el PC1
# resultante se puede leer directamente como un indice de exito, no de fracaso.
COLUMNAS_CLUSTER_EXITO = [
    "pct_victorias", "puntos_por_partido", "puntos_totales",
    "diferencia_gol_promedio", "posicion_final", "posicion_promedio",
    "pct_victorias_con", "pct_victorias_sin",
]
COLUMNAS_A_INVERTIR = ["posicion_final", "posicion_promedio"]

candidatos = sorted(config.RUTA_DATOS_PROCESSED.glob("dataset_modelable_*.csv"))
if not candidatos:
    raise FileNotFoundError(
        "No se encontro ningun dataset_modelable_*.csv en data/processed -- "
        "correr primero d06_extraer_panel_predictores.py."
    )
ruta_dataset = candidatos[-1]
print(f"Usando: {ruta_dataset.name}")

dataset = pd.read_csv(ruta_dataset)

faltantes = [c for c in COLUMNAS_CLUSTER_EXITO if c not in dataset.columns]
if faltantes:
    raise KeyError(
        f"No estan en el dataset: {faltantes}. Columnas disponibles: {list(dataset.columns)}"
    )

# =============================================================================
# PARTE 1 -- PCA sobre las 8 variables originales del cluster (referencia /
# el diagnostico que ya se corrio y discutio; se deja tal cual para que el
# script sea reproducible de punta a punta)
# =============================================================================

# ---------------------------------------------------------------------------
# 1) Cobertura: cuanto se pierde por NaN en cada columna, y en conjunto
# ---------------------------------------------------------------------------
print(f"\n{len(dataset)} filas totales en el dataset modelable.\n")
print("NaN por columna del cluster:")
print(dataset[COLUMNAS_CLUSTER_EXITO].isna().sum().sort_values(ascending=False))

mascara_completa = dataset[COLUMNAS_CLUSTER_EXITO].notna().all(axis=1)
print(f"\n{mascara_completa.sum()} de {len(dataset)} filas ({mascara_completa.mean():.2%}) "
      "tienen las 8 columnas completas (necesario para el PCA).")

# Cuanto de la perdida es especificamente por pct_victorias_con/sin (que
# tienen su propio piso de min_partidos_grupo=5 en ambos grupos, a diferencia
# de las otras 6 que solo dependen de que el club haya jugado liga domestica
# esa temporada)
solo_con_sin_faltante = (
    dataset[["pct_victorias_con", "pct_victorias_sin"]].isna().any(axis=1)
    & dataset[[c for c in COLUMNAS_CLUSTER_EXITO if c not in ("pct_victorias_con", "pct_victorias_sin")]].notna().all(axis=1)
)
print(f"De las filas incompletas, {solo_con_sin_faltante.sum()} faltan "
      "UNICAMENTE por pct_victorias_con/pct_victorias_sin (el piso de "
      "min_partidos_grupo=5 en ambos grupos) -- el resto del cluster esta completo ahi.")

# ---------------------------------------------------------------------------
# 2) PCA sobre las filas completas
# ---------------------------------------------------------------------------
datos_pca = dataset.loc[mascara_completa, COLUMNAS_CLUSTER_EXITO].copy()

for col in COLUMNAS_A_INVERTIR:
    datos_pca[col] = -datos_pca[col]

escalador = StandardScaler()
datos_std = escalador.fit_transform(datos_pca)

pca = PCA(n_components=len(COLUMNAS_CLUSTER_EXITO))
scores = pca.fit_transform(datos_std)

autovalores = pca.explained_variance_
var_explicada = pca.explained_variance_ratio_
var_acumulada = np.cumsum(var_explicada)

print("\nVarianza explicada por componente (autovalor / % / % acumulado):")
for i, (av, ve, va) in enumerate(zip(autovalores, var_explicada, var_acumulada), start=1):
    marca = "  <-- autovalor > 1 (criterio de Kaiser)" if av > 1 else ""
    print(f"  PC{i}: autovalor={av:.3f}  {ve:.2%}  acumulado={va:.2%}{marca}")

# ---------------------------------------------------------------------------
# 3) Loadings de las primeras componentes (las que probablemente se retengan)
# ---------------------------------------------------------------------------
n_mostrar = min(3, len(COLUMNAS_CLUSTER_EXITO))
loadings = pd.DataFrame(
    pca.components_[:n_mostrar].T,
    index=COLUMNAS_CLUSTER_EXITO,
    columns=[f"PC{i+1}" for i in range(n_mostrar)],
)
print(f"\nLoadings de las primeras {n_mostrar} componentes "
      "(recordar: posicion_final/posicion_promedio ya estan invertidas, "
      "signo positivo = mas exito en las 8):")
print(loadings.round(3))

# Comunalidad: cuanto de la varianza de CADA variable original queda
# capturado si se retienen solo las primeras n_mostrar componentes
comunalidad = (loadings ** 2).sum(axis=1)
print(f"\nComunalidad con las primeras {n_mostrar} componentes "
      "(fraccion de la varianza de cada variable original que se conserva):")
print(comunalidad.round(3).sort_values())

# ---------------------------------------------------------------------------
# 4) Poder predictivo de PC1 (y PC2) vs. las variables originales por separado
# ---------------------------------------------------------------------------
resultado = dataset.loc[mascara_completa, ["player_id", "season", "log_valor_mercado"]].copy()
for i in range(n_mostrar):
    resultado[f"pca_exito_deportivo_{i+1}"] = scores[:, i]

print("\nCorrelacion (Pearson) de cada componente con log_valor_mercado:")
for i in range(n_mostrar):
    r = resultado[f"pca_exito_deportivo_{i+1}"].corr(resultado["log_valor_mercado"])
    print(f"  PC{i+1}: {r:.3f}")

print("\nPara comparar, correlacion (Pearson) de cada variable original con log_valor_mercado "
      "(mismo subconjunto de filas completas, para que sea comparable):")
originales = dataset.loc[mascara_completa, COLUMNAS_CLUSTER_EXITO].copy()
for col in COLUMNAS_A_INVERTIR:
    originales[col] = -originales[col]
for col in COLUMNAS_CLUSTER_EXITO:
    r = originales[col].corr(dataset.loc[mascara_completa, "log_valor_mercado"])
    print(f"  {col}{' (invertida)' if col in COLUMNAS_A_INVERTIR else ''}: {r:.3f}")

# =============================================================================
# PARTE 2 -- Mismo PCA, sacando pct_victorias_con/pct_victorias_sin (ver nota
# al principio del script). Estas 6 variables tienen 0 NaN en el dataset
# modelable -- el PCA queda con cobertura completa (100% del panel).
# =============================================================================

COLUMNAS_CLUSTER_EXITO_SIN_CONSIN = [
    "pct_victorias", "puntos_por_partido", "puntos_totales",
    "diferencia_gol_promedio", "posicion_final", "posicion_promedio",
]

print("\n" + "=" * 78)
print("PARTE 2: PCA sobre las 6 variables de cluster 1 sin pct_victorias_con/sin")
print("=" * 78)

mascara_completa_6 = dataset[COLUMNAS_CLUSTER_EXITO_SIN_CONSIN].notna().all(axis=1)
print(f"\n{mascara_completa_6.sum()} de {len(dataset)} filas ({mascara_completa_6.mean():.2%}) "
      "tienen las 6 columnas completas (deberia ser ~100%, ya que ninguna de las 6 "
      "tenia NaN en la corrida anterior).")

datos_pca_6 = dataset.loc[mascara_completa_6, COLUMNAS_CLUSTER_EXITO_SIN_CONSIN].copy()
for col in COLUMNAS_A_INVERTIR:
    datos_pca_6[col] = -datos_pca_6[col]

escalador_6 = StandardScaler()
datos_std_6 = escalador_6.fit_transform(datos_pca_6)

pca_6 = PCA(n_components=len(COLUMNAS_CLUSTER_EXITO_SIN_CONSIN))
scores_6 = pca_6.fit_transform(datos_std_6)

autovalores_6 = pca_6.explained_variance_
var_explicada_6 = pca_6.explained_variance_ratio_
var_acumulada_6 = np.cumsum(var_explicada_6)

print("\nVarianza explicada por componente (autovalor / % / % acumulado):")
for i, (av, ve, va) in enumerate(zip(autovalores_6, var_explicada_6, var_acumulada_6), start=1):
    marca = "  <-- autovalor > 1 (criterio de Kaiser)" if av > 1 else ""
    print(f"  PC{i}: autovalor={av:.3f}  {ve:.2%}  acumulado={va:.2%}{marca}")

n_mostrar_6 = min(2, len(COLUMNAS_CLUSTER_EXITO_SIN_CONSIN))
loadings_6 = pd.DataFrame(
    pca_6.components_[:n_mostrar_6].T,
    index=COLUMNAS_CLUSTER_EXITO_SIN_CONSIN,
    columns=[f"PC{i+1}" for i in range(n_mostrar_6)],
)
print(f"\nLoadings de las primeras {n_mostrar_6} componentes:")
print(loadings_6.round(3))

comunalidad_6 = (loadings_6 ** 2).sum(axis=1)
print(f"\nComunalidad con las primeras {n_mostrar_6} componentes:")
print(comunalidad_6.round(3).sort_values())

resultado_6 = dataset.loc[mascara_completa_6, ["player_id", "season", "log_valor_mercado"]].copy()
for i in range(n_mostrar_6):
    resultado_6[f"pca_exito_deportivo_6v_{i+1}"] = scores_6[:, i]

print("\nCorrelacion (Pearson) de cada componente (6 variables) con log_valor_mercado:")
for i in range(n_mostrar_6):
    r = resultado_6[f"pca_exito_deportivo_6v_{i+1}"].corr(resultado_6["log_valor_mercado"])
    print(f"  PC{i+1}: {r:.3f}")

# Chequeo de continuidad: el PC1 de 6 variables (cobertura completa) vs. el
# PC1 de 8 variables (PARTE 1, solo sobre el subconjunto con las 8 completas)
# deberian ser casi la misma cosa si pct_victorias_con/sin no aportaban nada
# sustancial a la componente principal.
comparacion = resultado[["player_id", "season", "pca_exito_deportivo_1"]].merge(
    resultado_6[["player_id", "season", "pca_exito_deportivo_6v_1"]],
    on=["player_id", "season"], how="inner"
)
r_continuidad = comparacion["pca_exito_deportivo_1"].corr(comparacion["pca_exito_deportivo_6v_1"])
print(f"\nChequeo de continuidad -- correlacion entre PC1 (8 variables) y PC1 (6 variables) "
      f"en las {len(comparacion)} filas donde ambas existen: {r_continuidad:.4f} "
      "(deberia ser muy cercana a 1 si sacar el par con/sin no cambia la componente principal).")

# =============================================================================
# PARTE 3 -- Graficos del PCA de 6 variables (el que se termina usando),
# pensados para mostrar los conceptos (varianza explicada / criterio de
# Kaiser, loadings, biplot) mas que como diagnostico -- se guardan en una
# subcarpeta propia de este script dentro de reports/figuras/ (ver
# config.ruta_figuras_script()), con el estilo compartido del repo
# (Montserrat + paleta apta para daltonismo).
# =============================================================================

print("\n" + "=" * 78)
print("PARTE 3: graficos del PCA (6 variables)")
print("=" * 78)

ruta_figuras = config.ruta_figuras_script(Path(__file__).stem)
estilo.aplicar_estilo()

# --- Grafico 1: scree plot (varianza explicada + criterio de Kaiser) -------
fig, ax = plt.subplots(figsize=(7, 4.5))
n_comp = len(COLUMNAS_CLUSTER_EXITO_SIN_CONSIN)
x = np.arange(1, n_comp + 1)

ax.bar(x, var_explicada_6 * 100, color=estilo.COLOR_PRINCIPAL, label="% varianza explicada")
ax.plot(x, var_acumulada_6 * 100, color=estilo.COLOR_SECUNDARIO, marker="o",
        linewidth=2, label="% acumulado")

# Autovalor=1 (criterio de Kaiser), expresado en la misma escala de % que el
# eje: con 6 variables estandarizadas, la varianza total es 6, asi que un
# autovalor de 1 equivale a 100/6 = 16.67% de esa escala.
umbral_kaiser_pct = 100 / n_comp
ax.axhline(umbral_kaiser_pct, color=estilo.COLOR_NEUTRO, linestyle="--", linewidth=1.5)
ax.text(n_comp, umbral_kaiser_pct + 2, "criterio de Kaiser (autovalor = 1)",
        ha="right", va="bottom", fontsize=8, color="#555555")

for xi, av in zip(x, autovalores_6):
    ax.annotate(f"autovalor={av:.2f}", (xi, var_explicada_6[xi - 1] * 100),
                textcoords="offset points", xytext=(0, 6), ha="center", fontsize=7.5)

ax.set_xticks(x)
ax.set_xticklabels([f"PC{i}" for i in x])
ax.set_ylabel("% de varianza")
ax.set_title("Scree plot - PCA de exito deportivo del club (6 variables)")
ax.legend(frameon=False, loc="center right")
fig.tight_layout()
ruta_scree = ruta_figuras / "pca_exito_deportivo_scree.png"
fig.savefig(ruta_scree, dpi=150)
plt.close(fig)
print(f"Guardado: {ruta_scree}")

# --- Grafico 2: loadings de PC1 (que tan parejo pesa cada variable) --------
fig, ax = plt.subplots(figsize=(7, 4))
loadings_pc1_ordenados = loadings_6["PC1"].sort_values()
colores = [estilo.COLOR_PRINCIPAL if v >= 0 else estilo.COLOR_SECUNDARIO for v in loadings_pc1_ordenados]
ax.barh(loadings_pc1_ordenados.index, loadings_pc1_ordenados.values, color=colores)
ax.set_xlabel("Loading en PC1")
ax.set_title("Loadings de PC1 - las 6 variables pesan casi lo mismo")
ax.axvline(0, color="#0b0b0b", linewidth=0.8)
fig.tight_layout()
ruta_loadings = ruta_figuras / "pca_exito_deportivo_loadings.png"
fig.savefig(ruta_loadings, dpi=150)
plt.close(fig)
print(f"Guardado: {ruta_loadings}")

# --- Grafico 3: biplot (PC1 vs PC2 + vectores de las variables originales) -
muestra = resultado_6.sample(n=min(4000, len(resultado_6)), random_state=42)

fig, ax = plt.subplots(figsize=(7.5, 6.5))
disperso = ax.scatter(
    muestra["pca_exito_deportivo_6v_1"], muestra["pca_exito_deportivo_6v_2"],
    c=muestra["log_valor_mercado"], cmap=estilo.CMAP_SECUENCIAL,
    s=8, alpha=0.5, linewidths=0,
)
cbar = fig.colorbar(disperso, ax=ax)
cbar.set_label("log(valor de mercado)")

# Limites del grafico FIJADOS a partir de los scores (percentil 0.5-99.5 +
# margen generoso -- 20%, no 8% -- para dejarle lugar al texto de las
# etiquetas de los vectores, que se ubican MAS ALLA de la punta de la
# flecha), no de los vectores.
x_lim = np.percentile(muestra["pca_exito_deportivo_6v_1"], [0.5, 99.5])
y_lim = np.percentile(muestra["pca_exito_deportivo_6v_2"], [0.5, 99.5])
margen_x = (x_lim[1] - x_lim[0]) * 0.20
margen_y = (y_lim[1] - y_lim[0]) * 0.20
x_lim = (x_lim[0] - margen_x, x_lim[1] + margen_x)
y_lim = (y_lim[0] - margen_y, y_lim[1] + margen_y)

ax.axhline(0, color=estilo.COLOR_NEUTRO, linewidth=1)
ax.axvline(0, color=estilo.COLOR_NEUTRO, linewidth=1)

# Vectores de loadings, escalados POR EJE POR SEPARADO -- mismo criterio que
# usa biplot() en R cuando los dos componentes tienen varianzas muy distintas
# (aca PC1 explica 90.6% y PC2 solo 5.7%). Con un unico factor comun (bug de
# la version anterior: un solo "escala" calculado sobre AMBOS ejes mezclados),
# los loadings de PC2 -- que en valor absoluto son MAS grandes que los de PC1
# (hasta 0.625 vs 0.42) -- se proyectaban muy por fuera del rango angosto del
# eje PC2, y como ax.text()/ax.annotate() NO se recortan en los bordes del
# grafico por defecto (clip_on=False), el texto quedaba flotando en
# cualquier parte del lienzo -- incluso arriba del titulo o debajo del eje x,
# que es exactamente lo que se vio. Con escalas independientes por eje, cada
# vector llega como maximo a ~72% del rango visible EN SU PROPIO eje --no
# 85%-- para dejarle lugar de sobra a la etiqueta (que se dibuja mas alla de
# la punta de la flecha, no encima), y ademas se fuerza clip_on=True
# explicitamente como resguardo (probado con datos sinteticos antes de
# devolver el script: con 85%/8% de margen el texto se recortaba justo en
# el borde del grafico; con 72%/20% queda comodo).
alcance_x = min(abs(x_lim[0]), abs(x_lim[1]))
alcance_y = min(abs(y_lim[0]), abs(y_lim[1]))
escala_x = 0.72 * alcance_x / loadings_6["PC1"].abs().max()
escala_y = 0.72 * alcance_y / loadings_6["PC2"].abs().max()

for variable in loadings_6.index:
    lx = loadings_6.loc[variable, "PC1"] * escala_x
    ly = loadings_6.loc[variable, "PC2"] * escala_y
    ax.annotate(
        "", xy=(lx, ly), xytext=(0, 0),
        arrowprops={"arrowstyle": "->", "color": "#0b0b0b", "linewidth": 1.3, "clip_on": True},
    )
    ax.text(
        lx * 1.10, ly * 1.10, variable, fontsize=8, ha="center", va="center",
        color="#0b0b0b", clip_on=True,
        bbox={"facecolor": "#fcfcfb", "alpha": 0.8, "edgecolor": "none", "pad": 1.0},
    )

# set_xlim/set_ylim DESPUES de dibujar los vectores -- por si alguno igual
# quedo un poco por fuera del margen calculado, que se recorte en el borde
# (clip_on=True ya deberia garantizar esto, pero se deja como resguardo
# doble: total, si los vectores estan bien escalados, esto no cambia nada).
ax.set_xlim(x_lim)
ax.set_ylim(y_lim)

ax.set_xlabel(f"PC1 ({var_explicada_6[0]:.1%} de la varianza)")
ax.set_ylabel(f"PC2 ({var_explicada_6[1]:.1%} de la varianza)")
ax.set_title("Biplot - jugador-temporada proyectado sobre PC1/PC2\ny vectores de las variables originales (escalas de ejes independientes)")
fig.tight_layout()
ruta_biplot = ruta_figuras / "pca_exito_deportivo_biplot.png"
fig.savefig(ruta_biplot, dpi=150)
plt.close(fig)
print(f"Guardado: {ruta_biplot}")