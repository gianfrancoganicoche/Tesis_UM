"""
Analisis exploratorio (e0X, 24/09/2026): cierra la ultima decision de
especificacion pendiente antes de empezar los scripts de modelado (m0X) --
de las 8 variables de rendimiento individual candidatas
(docs/diccionario_variables.md, seccion C, construidas en
d03_construir_variables_rendimiento.py), cuales entran a la especificacion
final del termino rendimiento_it de Alternativa 3.

Mismo patron ya usado para el bloque de contexto (e02 -> e03 -> e04):
    1. Correlacion entre las candidatas entre si (Pearson/Spearman, pares
       unicos, mismo umbral 0.7 de e02_correlaciones_predictores.py)
    2. Correlacion de cada candidata contra la variable dependiente
       (log_valor_mercado)
    3. VIF conjunto de la especificacion resultante (mismo metodo que
       e04_vif_contexto.py: inversa de la matriz de correlacion, listwise
       deletion)

NO REABRE dos exclusiones ya resueltas, aunque diccionario_variables.md las
liste tambien como candidatas de rendimiento -- el argumento de exclusion no
dependia de en que bloque estuvieran clasificadas:
  - pct_victorias_con / pct_victorias_sin / diferencial_con_sin: excluidas el
    23/09 por mediador/endogeneidad con pca_exito_deportivo (ver
    2026-09-23_nota-metodologica-exclusion-pct-victorias.docx).
  - pct_minutos_disponibles: excluida el 22/09 junto con el resto del
    cluster 3 (volumen de minutos), mismo argumento de mediador.

Las 8 candidatas que SI se evaluan aca (nombres tal como los deja
d03_construir_variables_rendimiento.py):
    goles_90, asistencias_90, contribucion_gol_90, tarjetas_90,
    participacion_produccion, goles_recibidos_90, goles_recibidos_ajustados_90,
    edad_debut

PISO DE CONFIABILIDAD: 6 de las 8 ya tienen su flag en
COLUMNAS_CON_PISO_CONFIABILIDAD de e01 (se reusa e01.serie_efectiva() tal
cual, sin reimplementar esa logica). Las 2 que e01 todavia no cubre:
  - edad_debut: tiene su propio flag (debut_confiable, construido en
    construir_edad_debut()) -- se enmascara aca con la misma logica que
    serie_efectiva(), sin tocar el diccionario compartido de e01.
  - participacion_produccion: NO tiene flag de confiabilidad propio en el
    pipeline (a diferencia de lo que se podria suponer por analogia con
    goles_90/asistencias_90) -- su unico resguardo es el clip(lower=1) ya
    aplicado al denominador en construir_participacion_produccion_ofensiva().
    Se usa cruda, sin enmascarar, porque no hay un flag que enmascarar.

CUIDADO -- contribucion_gol_90 es, por construccion, goles_90 + asistencias_90
(ver d03): es una combinacion lineal EXACTA, no una tercera pieza de evidencia
independiente. Entra a las tablas de correlacion (para decidir si conviene el
combinado en vez de las dos partes sueltas) pero SE EXCLUYE del VIF conjunto
-- una matriz de correlacion con una columna combinacion lineal exacta de
otras dos es singular por definicion y devuelve VIF sin sentido (negativos o
desbordados) en vez de fallar limpio. Mismo tipo de caso que
competidores_totales_puesto/competidores_mismo_puesto (r=1.0 exacto) en el
chequeo de contexto.

CUIDADO 2 -- goles_recibidos_90/goles_recibidos_ajustados_90 son mucho mas
relevantes (y estan mucho mas pobladas) para arqueros/defensores que las
candidatas ofensivas para delanteros/mediocampistas. Si el N conjunto del VIF
cae demasiado respecto del N individual de cada variable, el numero conjunto
no es informativo -- el script avisa explicitamente si esto pasa (ver
AVISO_COBERTURA_MINIMA mas abajo) en vez de imprimir el VIF sin comentario.

SALIDAS (en reports/e05_seleccion_rendimiento/, figuras en
reports/figuras/e05_seleccion_rendimiento/, mismo patron que el resto de
e0X via config.ruta_reports_script()/ruta_figuras_script()):
    correlaciones_rendimiento_entre_si.csv
    correlaciones_rendimiento_vs_dv.csv
    vif_rendimiento.csv
    heatmap_correlaciones.png
    vif_rendimiento.png

No decide automaticamente que variables sacar: junta la evidencia (mismo
criterio que se uso para cerrar el bloque de contexto) para que la decision
final quede tan documentada como esa.
"""

import sys
from itertools import combinations
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

_RAIZ_SCRIPTS = Path(__file__).resolve().parents[1]  # scripts/
for _carpeta in ("config", "dataset", "eda", "diagnosticos"):
    sys.path.insert(0, str(_RAIZ_SCRIPTS / _carpeta))

import config
import e01_analisis_exploratorio as e01
import estilo_graficos as estilo

VARIABLE_DEPENDIENTE = "log_valor_mercado"
UMBRAL_PEARSON = 0.7  # mismo umbral que e02_correlaciones_predictores.py
UMBRAL_ATENCION = 5   # mismos umbrales de VIF que e04_vif_contexto.py
UMBRAL_SERIO = 10

# Candidatas que SI usan el enmascarado ya definido en e01 (reutilizado tal
# cual via e01.serie_efectiva -- no se duplica esa logica aca).
CANDIDATOS_CON_ENMASCARADO_E01 = [
    "goles_90", "asistencias_90", "contribucion_gol_90", "tarjetas_90",
    "goles_recibidos_90", "goles_recibidos_ajustados_90",
]

# edad_debut: mismo patron (valor crudo + flag), pero e01 todavia no lo
# cubre -- se enmascara localmente con su propio flag, sin tocar
# COLUMNAS_CON_PISO_CONFIABILIDAD de e01.
FLAG_EDAD_DEBUT = "debut_confiable"

# participacion_produccion: sin flag propio en el pipeline -- se usa cruda
# (ver docstring del modulo).
CANDIDATOS_SIN_ENMASCARADO = ["participacion_produccion"]

TODAS_LAS_CANDIDATAS = CANDIDATOS_CON_ENMASCARADO_E01 + ["edad_debut"] + CANDIDATOS_SIN_ENMASCARADO

# contribucion_gol_90 = goles_90 + asistencias_90 exacto (ver docstring) --
# afuera del VIF conjunto, adentro de las tablas de correlacion.
VARIABLES_VIF_CONJUNTO = [c for c in TODAS_LAS_CANDIDATAS if c != "contribucion_gol_90"]

# ---------------------------------------------------------------------------
# Especificacion final PROPUESTA de rendimiento_it (24/09, a partir de la
# primera corrida real de este script sobre dataset_modelable_2026-09-23.csv)
# -- no confirmada todavia, es la lectura de Claude de la evidencia, para que
# Gianfranco la valide o la corrija antes de darla por cerrada:
#
#   - contribucion_gol_90 SACADA: es goles_90+asistencias_90 exacto, y esas
#     dos por separado tienen VIF conjunto bajo (2.05 / 1.50 en la corrida
#     real) -- separadas preservan MAS informacion (goleador vs. generador de
#     juego son señales distintas, r=0.29 entre ellas) que colapsarlas en una
#     sola, sin costo de colinealidad.
#   - goles_recibidos_90 (version cruda) SACADA a favor de
#     goles_recibidos_ajustados_90: correlacionan 0.90 entre si (par
#     practicamente redundante), la version ajustada por fuerza del rival es
#     conceptualmente mas defendible (mismo criterio leave-one-out ya usado
#     en el resto del pipeline) y tiene una correlacion levemente mas fuerte
#     con la DV en la corrida real (-0.319 vs -0.273). Sacar la version cruda
#     tambien resuelve el VIF de ambas cruzando el umbral de atencion (5.1-5.2
#     en la corrida real, con las dos juntas).
#   - tarjetas_90 MANTENIDA pero con nota de cautela: no colisiona con nada
#     (VIF bajo, r maximo 0.03 con el resto), pero en la corrida real su
#     correlacion con la DV es la mas debil de las 8 candidatas y ademas poco
#     robusta (Pearson -0.084 vs. Spearman -0.016, casi cero) -- no hay
#     argumento estadistico para sacarla (no cuesta nada de colinealidad),
#     pero tampoco aporta mucha señal. Revisar con Gianfranco si se mantiene
#     por completitud teorica (esta en el diseño original) o se corta por
#     parsimonia.
#   - goles_90, asistencias_90, participacion_produccion, edad_debut
#     MANTENIDAS: participacion_produccion es, en la corrida real, la
#     candidata con la correlacion mas fuerte contra la DV de las 8 (0.32/0.37)
#     y con VIF bajo (2.57); edad_debut tiene una correlacion razonable
#     (-0.23/-0.20) y VIF minimo (1.04), pese a su cobertura mas baja (68.6%).
ESPECIFICACION_FINAL_PROPUESTA = [
    "goles_90",
    "asistencias_90",
    "participacion_produccion",
    "goles_recibidos_ajustados_90",
    "edad_debut",
    "tarjetas_90",
]


def construir_tabla_efectiva(dataset: pd.DataFrame) -> pd.DataFrame:
    """Arma un DataFrame con las 8 candidatas, cada una ya enmascarada donde corresponde."""
    columnas = {}
    for col in CANDIDATOS_CON_ENMASCARADO_E01:
        columnas[col] = e01.serie_efectiva(dataset, col)

    if FLAG_EDAD_DEBUT not in dataset.columns:
        raise KeyError(
            f"No se encontro la columna de flag '{FLAG_EDAD_DEBUT}' para enmascarar 'edad_debut'."
        )
    confiable_debut = dataset[FLAG_EDAD_DEBUT].fillna(False).astype(bool)
    columnas["edad_debut"] = dataset["edad_debut"].where(confiable_debut)

    for col in CANDIDATOS_SIN_ENMASCARADO:
        columnas[col] = dataset[col]

    return pd.DataFrame(columnas)


def correlaciones_entre_candidatas(tabla: pd.DataFrame) -> pd.DataFrame:
    """Pearson y Spearman por pares, deleccion pairwise (N reportado por par)."""
    filas = []
    for var_a, var_b in combinations(tabla.columns, 2):
        pareja = tabla[[var_a, var_b]].dropna()
        n = len(pareja)
        if n < 30:
            pearson = spearman = np.nan
        else:
            pearson = pareja[var_a].corr(pareja[var_b], method="pearson")
            spearman = pareja[var_a].corr(pareja[var_b], method="spearman")
        filas.append({
            "variable_a": var_a, "variable_b": var_b, "n": n,
            "pearson": pearson, "spearman": spearman,
            "supera_umbral": bool(pd.notna(pearson) and abs(pearson) >= UMBRAL_PEARSON),
        })
    tabla_pares = pd.DataFrame(filas)
    tabla_pares["_abs_pearson"] = tabla_pares["pearson"].abs()
    return tabla_pares.sort_values("_abs_pearson", ascending=False).drop(columns="_abs_pearson").reset_index(drop=True)


def correlaciones_vs_dv(tabla: pd.DataFrame, dv: pd.Series) -> pd.DataFrame:
    filas = []
    for col in tabla.columns:
        pareja = pd.DataFrame({col: tabla[col], VARIABLE_DEPENDIENTE: dv}).dropna()
        n = len(pareja)
        if n < 30:
            pearson = spearman = np.nan
        else:
            pearson = pareja[col].corr(pareja[VARIABLE_DEPENDIENTE], method="pearson")
            spearman = pareja[col].corr(pareja[VARIABLE_DEPENDIENTE], method="spearman")
        filas.append({"variable": col, "n": n, "pearson_vs_dv": pearson, "spearman_vs_dv": spearman})
    tabla_dv = pd.DataFrame(filas)
    tabla_dv["_abs_pearson"] = tabla_dv["pearson_vs_dv"].abs()
    return tabla_dv.sort_values("_abs_pearson", ascending=False).drop(columns="_abs_pearson").reset_index(drop=True)


def calcular_vif(tabla: pd.DataFrame, variables: list[str]) -> tuple[pd.Series, int]:
    """VIF via inversion de la matriz de correlacion -- mismo metodo que e04_vif_contexto.py.

    A diferencia de e04 (que ya sabia de antemano que su bloque de 4-6
    variables no tenia dependencias lineales exactas entre si), aca se agrega
    un chequeo de numero de condicion antes de invertir: si aparece una
    combinacion lineal exacta o casi exacta no anticipada, el error explica
    por que en vez de devolver un VIF sin sentido.
    """
    datos = tabla[variables].dropna()
    n = len(datos)
    if n < 30:
        raise ValueError(
            f"Solo {n} filas tienen las {len(variables)} candidatas simultaneamente -- "
            "insuficiente para un VIF conjunto confiable."
        )
    matriz_corr = datos.corr()
    numero_condicion = np.linalg.cond(matriz_corr.values)
    if numero_condicion > 1e10:
        raise ValueError(
            f"La matriz de correlacion de {variables} es casi singular (numero de "
            f"condicion={numero_condicion:.2e}) -- probablemente hay una combinacion "
            "lineal exacta o casi exacta no contemplada entre estas columnas. Revisar "
            "antes de confiar en el VIF resultante."
        )
    inversa = np.linalg.inv(matriz_corr.values)
    vif = pd.Series(np.diag(inversa), index=variables)
    return vif, n


def imprimir_vif(titulo, vif, n_filas):
    print(f"\n{titulo} (n={n_filas} filas completas)")
    for col, v in vif.sort_values(ascending=False).items():
        marca = ""
        if v > UMBRAL_SERIO:
            marca = f"  <-- > {UMBRAL_SERIO} (colinealidad seria)"
        elif v > UMBRAL_ATENCION:
            marca = f"  <-- > {UMBRAL_ATENCION} (amerita atencion)"
        print(f"  {col}: VIF={v:.3f}{marca}")


def graficar_heatmap_correlaciones(tabla: pd.DataFrame, ruta_png):
    corr = tabla.corr(method="pearson")
    n = len(corr.columns)
    fig, ax = plt.subplots(figsize=(max(6, 0.9 * n), max(6, 0.9 * n)))
    im = ax.imshow(corr.values, cmap=estilo.CMAP_DIVERGENTE, vmin=-1, vmax=1)
    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(corr.columns, rotation=45, ha="right", fontsize=8)
    ax.set_yticklabels(corr.columns, fontsize=8)
    for i in range(n):
        for j in range(n):
            valor = corr.values[i, j]
            ax.text(j, i, f"{valor:.2f}", ha="center", va="center",
                    color="white" if abs(valor) > 0.6 else "#0b0b0b", fontsize=7)
    fig.colorbar(im, ax=ax, shrink=0.8, label="Pearson")
    # fig.suptitle(), no ax.set_title(): el titulo va centrado sobre TODA la
    # figura (heatmap + colorbar), no solo sobre el ax del heatmap. Con
    # ax.set_title() y un titulo largo, el texto se centraba sobre el ax
    # (mas angosto por el "shrink" del colorbar) y su mitad derecha quedaba
    # tapada por el colorbar -- bug real, visto en la corrida de prueba con
    # las 8 candidatas (título recortado en "...individua|" contra el
    # colorbar). rect en tight_layout() deja el margen superior que el
    # suptitle necesita.
    fig.tight_layout()
    fig.subplots_adjust(top=0.92)
    fig.suptitle("Correlacion entre candidatas de rendimiento individual", fontsize=12)
    fig.savefig(ruta_png, dpi=150, bbox_inches="tight")
    plt.close(fig)


def graficar_vif(vif: pd.Series, ruta_png):
    variables_orden = vif.sort_values().index.tolist()
    valores = vif.loc[variables_orden]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.barh(variables_orden, valores.values, color=estilo.COLOR_PRINCIPAL)
    ax.axvline(UMBRAL_ATENCION, color=estilo.COLOR_SECUNDARIO, linestyle="--", linewidth=1.2,
               label=f"umbral de atencion ({UMBRAL_ATENCION})")
    ax.axvline(UMBRAL_SERIO, color="#b3261e", linestyle="--", linewidth=1.2,
               label=f"umbral serio ({UMBRAL_SERIO})")
    ax.set_xlabel("VIF")
    ax.set_title("VIF conjunto -- candidatas de rendimiento individual")
    ax.legend(frameon=False, loc="lower right", fontsize=8)
    fig.tight_layout()
    fig.savefig(ruta_png, dpi=150)
    plt.close(fig)


def main():
    estilo.aplicar_estilo()
    dataset = e01.cargar_dataset_modelable()
    print(f"Dataset: {dataset.shape[0]} filas, {dataset.shape[1]} columnas.")

    faltantes = [c for c in TODAS_LAS_CANDIDATAS if c not in dataset.columns]
    if faltantes:
        raise KeyError(
            f"No estan en el dataset: {faltantes}. Revisar si construir_variables_rendimiento.py "
            "cambio algun nombre de columna desde que se escribio este script."
        )

    ruta_reports = config.ruta_reports_script(Path(__file__).stem)
    ruta_figuras = config.ruta_figuras_script(Path(__file__).stem)

    tabla = construir_tabla_efectiva(dataset)

    print("\nCobertura individual de cada candidata (tras aplicar su piso de confiabilidad, donde aplica):")
    for col in tabla.columns:
        n_valido = tabla[col].notna().sum()
        print(f"  {col}: {n_valido} / {len(tabla)} ({n_valido / len(tabla):.1%})")

    pares = correlaciones_entre_candidatas(tabla)
    e01.guardar_csv_legible(pares, ruta_reports / "correlaciones_rendimiento_entre_si.csv")
    print(f"\nPares con |Pearson| >= {UMBRAL_PEARSON} entre candidatas de rendimiento:")
    pares_relevantes = pares[pares["supera_umbral"]]
    print(pares_relevantes.to_string(index=False) if len(pares_relevantes) else "  (ninguno)")

    tabla_dv = correlaciones_vs_dv(tabla, dataset[VARIABLE_DEPENDIENTE])
    e01.guardar_csv_legible(tabla_dv, ruta_reports / "correlaciones_rendimiento_vs_dv.csv")
    print(f"\nCorrelacion de cada candidata contra {VARIABLE_DEPENDIENTE}:")
    print(tabla_dv.to_string(index=False))

    graficar_heatmap_correlaciones(tabla, ruta_figuras / "heatmap_correlaciones.png")

    n_total = len(tabla)
    n_completo_vif = tabla[VARIABLES_VIF_CONJUNTO].dropna().shape[0]
    print(
        f"\nFilas con las {len(VARIABLES_VIF_CONJUNTO)} candidatas del VIF simultaneamente no-nulas: "
        f"{n_completo_vif} / {n_total} ({n_completo_vif / n_total:.1%}) -- N real del VIF de abajo "
        "(contribucion_gol_90 queda afuera del VIF por ser combinacion lineal exacta de "
        "goles_90+asistencias_90, ver docstring del modulo)."
    )
    if n_completo_vif / n_total < 0.5:
        print(
            "AVISO: el VIF conjunto cae sobre menos de la mitad del panel. Esperable si "
            "goles_recibidos_90/ajustados son mayormente relevantes para arqueros/defensores "
            "mientras que las ofensivas lo son para delanteros/mediocampistas -- antes de "
            "decidir en base a este numero, considerar partir el chequeo en dos VIF separados "
            "(ofensivas: goles_90/asistencias_90/participacion_produccion/tarjetas_90/edad_debut "
            "vs. defensivas: goles_recibidos_90/goles_recibidos_ajustados_90) en vez de uno conjunto."
        )

    vif, n_vif = calcular_vif(tabla, VARIABLES_VIF_CONJUNTO)
    tabla_vif = vif.rename("vif").rename_axis("variable").reset_index()
    e01.guardar_csv_legible(tabla_vif, ruta_reports / "vif_rendimiento.csv")
    imprimir_vif("VIF conjunto -- las 7 candidatas (sin contribucion_gol_90)", vif, n_vif)

    graficar_vif(vif, ruta_figuras / "vif_rendimiento.png")

    # -------------------------------------------------------------------
    # VIF de la especificacion final PROPUESTA (ver comentario junto a
    # ESPECIFICACION_FINAL_PROPUESTA mas arriba) -- mismo patron que
    # e04_vif_contexto.py: reportar el VIF de las candidatas completas Y el
    # de la especificacion reducida propuesta, no solo uno de los dos.
    # -------------------------------------------------------------------
    vif_final, n_vif_final = calcular_vif(tabla, ESPECIFICACION_FINAL_PROPUESTA)
    tabla_vif_final = vif_final.rename("vif").rename_axis("variable").reset_index()
    e01.guardar_csv_legible(tabla_vif_final, ruta_reports / "vif_rendimiento_especificacion_final.csv")
    imprimir_vif(
        f"VIF -- especificacion final PROPUESTA ({len(ESPECIFICACION_FINAL_PROPUESTA)} variables, "
        "sin contribucion_gol_90 ni goles_recibidos_90 crudo)",
        vif_final, n_vif_final,
    )
    graficar_vif(vif_final, ruta_figuras / "vif_rendimiento_especificacion_final.png")

    print(f"\nListo. Reportes en {ruta_reports}, figuras en {ruta_figuras}. Este script no descarta "
          "nada por si solo, solo junta la evidencia -- mismo criterio que se uso para cerrar el "
          "bloque de contexto. La ESPECIFICACION_FINAL_PROPUESTA de mas arriba es una lectura de "
          "Claude sobre esta misma corrida, no una decision ya tomada -- confirmar o ajustar antes "
          "de darla por cerrada.")

    return tabla, pares, tabla_dv, vif, vif_final


if __name__ == "__main__":
    tabla_rendimiento, correlaciones_pares, correlaciones_dv, vif_rendimiento, vif_especificacion_final = main()