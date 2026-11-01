"""
Poblacion de trabajo por capa (e08, 10/10/2026): cuanto dato hay en cada una de
las tres capas del diseno, ANTES de ajustar ningun modelo. NO modifica datos ni
decide nada -- es el insumo para elegir con que capa se corre cada chequeo de
m0X (puntos 1, 3, 8 y 9 de Alan).

Capas (m01_construir_dataset_modelado.py, hipotesis_y_diseno_v2.md SS4):
  capa 1  es_valido_curva_edad : carrera completa (edad y DV no nulas).
  capa 2  es_sub23             : edad < 23.
  capa 3  es_poblacion_h1      : sub-23 en primera division europea (H1/H2).

Que mide, para cada capa:
  1. Tamano: filas, jugadores, clubes, rango de temporadas.
  2. Filas por jugador: cuantos jugadores tienen 1, 2, 3, 4 o 5+ filas. Con 1 sola
     fila el efecto de jugador (alfa_i) no se separa del error y el jugador no
     aporta a la parte "dentro de jugador" (curva de edad, componente
     autorregresivo).
  3. Pares consecutivos (jugador con fila en t-1 y en t): es la base del
     componente autorregresivo (punto 9).
  4. Casos completos: filas sin ningun faltante en la especificacion cerrada
     (4 contexto + 6 rendimiento z + altura z + pie + es_comunitario), y cuantas
     de esas pertenecen a jugadores con 2+ filas completas / tienen par completo.
  5. Faltantes por variable (que variable es el cuello de botella).
  6. Porteros y posiciones: filas y jugadores por posicion (punto 3).
  7. Por temporada: filas por capa (punto 8: ver si 2019-2020 y 2021 pesan).
  8. Variables de club vendedor (punto 1): filas con reputacion_vendedor no nula
     y con club_vendedor_reconocido verdadero, dentro de cada capa.

  9. Faltantes de rendimiento por posicion y por tramo de minutos (capa 3): sirve
     para ver si los faltantes son estructurales (una variable que no aplica a
     una posicion, un piso de minutos) o aleatorios, y asi elegir como tratarlos.
 10. Cobertura de las variables de club vendedor por temporada (capa 3): la
     ventana de 5 anios deberia dejar vacias las primeras temporadas.
 11. Filas SIN POSICION (capa 3) contra las que si la tienen: minutos, edad, valor,
     faltantes de rendimiento y filas por jugador.

Lee el dataset_modelado MAS RECIENTE de data/processed/ (salida de m01). Las
variables del club vendedor no estan en la especificacion cerrada: si no vienen
en dataset_modelado se traen del dataset_modelable mas reciente (cruce por
player_id + season). Si no existen en ninguno, esa seccion se omite con aviso.

Uso:
    uv run scripts/eda/e08_poblacion_por_capa.py

Salidas (reports/e08_poblacion_por_capa/):
    resumen_por_capa.csv, filas_por_jugador.csv, casos_completos.csv,
    faltantes_por_variable.csv, por_posicion.csv, por_temporada.csv,
    club_vendedor.csv, faltantes_rendimiento_por_posicion.csv,
    faltantes_rendimiento_por_tramo_minutos.csv, vendedor_por_temporada.csv,
    perfil_sin_posicion.csv
"""

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

_RAIZ_SCRIPTS = Path(__file__).resolve().parents[1]  # scripts/
for _carpeta in ("config", "dataset", "eda", "diagnosticos"):
    sys.path.insert(0, str(_RAIZ_SCRIPTS / _carpeta))

import config
import e01_analisis_exploratorio as e01

COL_JUGADOR = "player_id"
COL_TEMPORADA = "season"
COL_CLUB = "club_id"
COL_POSICION = "posicion_amplia_predominante"
PATRON_PORTERO = r"arquer|portero|goalkeep|keeper"

CAPAS = {
    "capa1_curva_edad": "es_valido_curva_edad",
    "capa2_sub23": "es_sub23",
    "capa3_h1": "es_poblacion_h1",
}

BLOQUES_SPEC = {
    "contexto": [
        "pca_exito_deportivo", "companieros_valor_promedio",
        "formaciones_distintas", "fase_maxima_alcanzada",
    ],
    "rendimiento": [
        "z_goles_90", "z_asistencias_90", "z_participacion_produccion",
        "z_goles_recibidos_ajustados_90", "z_edad_debut", "z_amarillas_90", "tuvo_roja",
    ],
    "atributos": ["z_altura_cm", "pie_habil", "es_comunitario"],
}
COLUMNAS_SPEC = [c for cols in BLOQUES_SPEC.values() for c in cols]

COLUMNAS_VENDEDOR = ["reputacion_vendedor", "club_vendedor_reconocido"]
COL_MINUTOS = "minutos_totales"
COL_EDAD = "edad"
COL_DV = "log_valor_mercado"
SIN_POSICION = "(sin posicion)"
LIMITES_TRAMO_MINUTOS = [0, 450, 900, 1800, np.inf]
ETIQUETAS_TRAMO_MINUTOS = ["<450", "450-900", "900-1800", ">=1800"]
CLAVE = [COL_JUGADOR, COL_TEMPORADA]


# ---------------------------------------------------------------------------
# Carga
# ---------------------------------------------------------------------------

def cargar_dataset_modelado():
    """dataset_modelado mas reciente, mas club_id y variables de vendedor si faltan."""
    candidatos = sorted(config.RUTA_DATOS_PROCESSED.glob("dataset_modelado_*.csv"))
    if not candidatos:
        raise FileNotFoundError(
            "No se encontro ningun dataset_modelado_*.csv en data/processed -- "
            "correr primero m01_construir_dataset_modelado.py."
        )
    print(f"Usando: {candidatos[-1].name}")
    dataset = pd.read_csv(candidatos[-1])

    extras = [c for c in [COL_CLUB, COL_MINUTOS] + COLUMNAS_VENDEDOR if c not in dataset.columns]
    if extras:
        modelable = e01.cargar_dataset_modelable()
        traer = [c for c in extras if c in modelable.columns]
        if traer:
            dataset = dataset.merge(
                modelable[CLAVE + traer].drop_duplicates(CLAVE), on=CLAVE, how="left"
            )
        no_estan = [c for c in extras if c not in modelable.columns]
        if no_estan:
            print(f"AVISO: no se encontraron las columnas {no_estan} en ningun dataset.")
    return dataset


def detectar_porteros(dataset):
    valores = dataset[COL_POSICION].dropna().unique()
    etiquetas = [v for v in valores if re.search(PATRON_PORTERO, str(v), re.IGNORECASE)]
    if not etiquetas:
        raise ValueError(
            f"No se encontro categoria de portero en {COL_POSICION}: {sorted(map(str, valores))}"
        )
    return dataset[COL_POSICION].isin(etiquetas)


# ---------------------------------------------------------------------------
# Funciones puras (se prueban con datos sinteticos)
# ---------------------------------------------------------------------------

def mascara_capa(dataset, flag):
    return dataset[flag].fillna(False).astype(bool)


def mascara_par_consecutivo(sub):
    """Mascara: la fila (jugador, t) tiene fila (jugador, t-1) en `sub`."""
    existentes = set(zip(sub[COL_JUGADOR], sub[COL_TEMPORADA]))
    return pd.Series(
        [(j, t - 1) in existentes for j, t in zip(sub[COL_JUGADOR], sub[COL_TEMPORADA])],
        index=sub.index,
    )


def resumen_capa(sub):
    por_jugador = sub.groupby(COL_JUGADOR).size()
    par = mascara_par_consecutivo(sub)
    return {
        "filas": len(sub),
        "jugadores": sub[COL_JUGADOR].nunique(),
        "clubes": sub[COL_CLUB].nunique() if COL_CLUB in sub.columns else np.nan,
        "temporada_min": sub[COL_TEMPORADA].min() if len(sub) else np.nan,
        "temporada_max": sub[COL_TEMPORADA].max() if len(sub) else np.nan,
        "filas_por_jugador_media": por_jugador.mean() if len(sub) else np.nan,
        "filas_por_jugador_mediana": por_jugador.median() if len(sub) else np.nan,
        "jugadores_con_2mas_filas": int((por_jugador >= 2).sum()),
        "pct_jugadores_con_2mas_filas": float((por_jugador >= 2).mean() * 100) if len(sub) else np.nan,
        "filas_con_par_consecutivo": int(par.sum()),
    }


def distribucion_filas_por_jugador(sub):
    por_jugador = sub.groupby(COL_JUGADOR).size()
    tramos = pd.cut(por_jugador, bins=[0, 1, 2, 3, 4, np.inf], labels=["1", "2", "3", "4", "5+"])
    conteo = tramos.value_counts().reindex(["1", "2", "3", "4", "5+"]).fillna(0).astype(int)
    out = pd.DataFrame({"filas_por_jugador": conteo.index.astype(str), "jugadores": conteo.values})
    out["pct_jugadores"] = out["jugadores"] / max(len(por_jugador), 1) * 100
    return out


def casos_completos(sub, bloques=BLOQUES_SPEC):
    """Filas sin faltantes por bloque y en toda la especificacion, y su utilidad para alfa_i / AR."""
    presentes = {b: [c for c in cols if c in sub.columns] for b, cols in bloques.items()}
    completo_bloque = {b: sub[cols].notna().all(axis=1) if cols else pd.Series(False, index=sub.index)
                       for b, cols in presentes.items()}
    todo = pd.concat(completo_bloque.values(), axis=1).all(axis=1) if completo_bloque else pd.Series(False, index=sub.index)

    comp = sub[todo]
    por_jugador = comp.groupby(COL_JUGADOR).size()
    filas = {"filas_capa": len(sub)}
    for b, m in completo_bloque.items():
        filas[f"completas_{b}"] = int(m.sum())
    filas["completas_spec_total"] = int(todo.sum())
    filas["pct_completas_spec"] = float(todo.mean() * 100) if len(sub) else np.nan
    filas["jugadores_completos"] = int(comp[COL_JUGADOR].nunique())
    filas["jugadores_completos_2mas_filas"] = int((por_jugador >= 2).sum())
    filas["filas_completas_de_jugadores_2mas"] = int(por_jugador[por_jugador >= 2].sum())
    filas["filas_completas_con_par_consecutivo"] = int(mascara_par_consecutivo(comp).sum()) if len(comp) else 0
    faltan = [c for cols in bloques.values() for c in cols if c not in sub.columns]
    filas["columnas_spec_ausentes"] = ";".join(faltan)
    return filas


def faltantes_por_variable(sub, columnas=COLUMNAS_SPEC):
    filas = []
    for c in columnas:
        if c not in sub.columns:
            filas.append({"variable": c, "pct_faltante": np.nan, "nota": "columna ausente"})
        else:
            filas.append({"variable": c, "pct_faltante": float(sub[c].isna().mean() * 100), "nota": ""})
    return pd.DataFrame(filas)


def tabla_posicion(sub):
    por_pos = sub.groupby(COL_POSICION, dropna=False).agg(
        filas=(COL_JUGADOR, "size"), jugadores=(COL_JUGADOR, "nunique")
    ).reset_index()
    por_pos[COL_POSICION] = por_pos[COL_POSICION].astype(object).where(por_pos[COL_POSICION].notna(), "(sin posicion)")
    return por_pos


def tabla_vendedor(sub):
    fila = {"filas_capa": len(sub)}
    if "reputacion_vendedor" in sub.columns:
        m = sub["reputacion_vendedor"].notna()
        fila["filas_reputacion_no_nula"] = int(m.sum())
        fila["pct_reputacion_no_nula"] = float(m.mean() * 100) if len(sub) else np.nan
        fila["jugadores_reputacion_no_nula"] = int(sub.loc[m, COL_JUGADOR].nunique())
        fila["clubes_reputacion_no_nula"] = int(sub.loc[m, COL_CLUB].nunique()) if COL_CLUB in sub.columns else np.nan
    if "club_vendedor_reconocido" in sub.columns:
        r = sub["club_vendedor_reconocido"].fillna(False).astype(bool)
        fila["filas_vendedor_reconocido"] = int(r.sum())
        fila["pct_vendedor_reconocido"] = float(r.mean() * 100) if len(sub) else np.nan
        fila["jugadores_vendedor_reconocido"] = int(sub.loc[r, COL_JUGADOR].nunique())
    return fila


def tramo_minutos(sub):
    """Tramo de minutos_totales; 'sin dato' si es NaN (misma convencion que e07)."""
    tramo = pd.cut(sub[COL_MINUTOS], bins=LIMITES_TRAMO_MINUTOS,
                   labels=ETIQUETAS_TRAMO_MINUTOS, right=False).astype(object)
    return tramo.where(sub[COL_MINUTOS].notna(), "sin dato")


def faltantes_rendimiento_por_grupo(sub, grupo, nombre_grupo):
    """% faltante de cada variable de rendimiento z_* por grupo, mas % con rendimiento completo."""
    cols = [c for c in BLOQUES_SPEC["rendimiento"] if c in sub.columns]
    d = sub[cols].isna().astype(float)
    d[nombre_grupo] = grupo.astype(object).where(grupo.notna(), SIN_POSICION).values
    out = d.groupby(nombre_grupo)[cols].mean() * 100
    out.insert(0, "filas", sub.groupby(grupo.astype(object).where(grupo.notna(), SIN_POSICION).values).size())
    out["pct_rendimiento_completo"] = (
        sub[cols].notna().all(axis=1).groupby(grupo.astype(object).where(grupo.notna(), SIN_POSICION).values).mean() * 100
    )
    return out.reset_index()


def vendedor_por_temporada(sub):
    filas = []
    for t, g in sub.groupby(COL_TEMPORADA):
        fila = {"season": t, "filas": len(g)}
        if "reputacion_vendedor" in g.columns:
            fila["pct_reputacion_no_nula"] = float(g["reputacion_vendedor"].notna().mean() * 100)
        if "club_vendedor_reconocido" in g.columns:
            fila["pct_vendedor_reconocido"] = float(g["club_vendedor_reconocido"].fillna(False).astype(bool).mean() * 100)
        filas.append(fila)
    return pd.DataFrame(filas)


def perfil_sin_posicion(sub):
    """Compara filas sin posicion contra las que si la tienen."""
    sin = sub[COL_POSICION].isna()
    cols = [c for c in BLOQUES_SPEC["rendimiento"] if c in sub.columns]
    filas = []
    for etiqueta, m in (("sin posicion", sin), ("con posicion", ~sin)):
        g = sub[m]
        fila = {
            "grupo": etiqueta,
            "filas": len(g),
            "jugadores": g[COL_JUGADOR].nunique(),
            "filas_por_jugador": len(g) / max(g[COL_JUGADOR].nunique(), 1),
            "edad_media": g[COL_EDAD].mean() if COL_EDAD in g.columns else np.nan,
            "log_valor_medio": g[COL_DV].mean() if COL_DV in g.columns else np.nan,
            "pct_rendimiento_completo": float(g[cols].notna().all(axis=1).mean() * 100) if len(g) else np.nan,
            "faltante_medio_rendimiento_pct": float(g[cols].isna().mean().mean() * 100) if len(g) else np.nan,
        }
        if COL_MINUTOS in g.columns:
            fila["pct_minutos_sin_dato"] = float(g[COL_MINUTOS].isna().mean() * 100) if len(g) else np.nan
            fila["minutos_mediana"] = g[COL_MINUTOS].median()
        filas.append(fila)
    return pd.DataFrame(filas)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def imprimir(titulo, tabla):
    print(f"\n{titulo}")
    with pd.option_context("display.width", 200, "display.max_columns", 50, "display.float_format", "{:,.1f}".format):
        print(tabla.to_string(index=False) if isinstance(tabla, pd.DataFrame) else tabla)


def main():
    dataset = cargar_dataset_modelado()
    print(f"Dataset: {dataset.shape[0]} filas, {dataset.shape[1]} columnas.")
    faltan_flags = [f for f in CAPAS.values() if f not in dataset.columns]
    if faltan_flags:
        raise KeyError(f"Faltan los flags de capa {faltan_flags}: correr m01.")

    ruta = config.ruta_reports_script(Path(__file__).stem)
    detectar_porteros(dataset)  # falla temprano si la categoria de portero no se encuentra
    subconjuntos = {nombre: dataset[mascara_capa(dataset, flag)] for nombre, flag in CAPAS.items()}

    if len(subconjuntos["capa3_h1"]) == 0:
        print("ADVERTENCIA: la capa 3 esta vacia -- m01 probablemente no pudo construir las "
              "columnas de liga (ver el aviso de m01).")

    # 1. Tamano
    resumen = pd.DataFrame([{"capa": n, **resumen_capa(s)} for n, s in subconjuntos.items()])
    imprimir("[1] Tamano por capa", resumen)
    resumen.to_csv(ruta / "resumen_por_capa.csv", index=False)

    # 2. Filas por jugador
    dist = pd.concat([distribucion_filas_por_jugador(s).assign(capa=n) for n, s in subconjuntos.items()])
    dist = dist[["capa", "filas_por_jugador", "jugadores", "pct_jugadores"]]
    imprimir("[2] Jugadores segun cuantas filas tienen", dist)
    dist.to_csv(ruta / "filas_por_jugador.csv", index=False)

    # 4. Casos completos
    comp = pd.DataFrame([{"capa": n, **casos_completos(s)} for n, s in subconjuntos.items()])
    imprimir("[3] Casos completos en la especificacion cerrada", comp)
    comp.to_csv(ruta / "casos_completos.csv", index=False)

    # 5. Faltantes por variable
    falt = pd.concat([faltantes_por_variable(s).assign(capa=n) for n, s in subconjuntos.items()])
    ancho = falt.pivot(index="variable", columns="capa", values="pct_faltante").reindex(COLUMNAS_SPEC).reset_index()
    imprimir("[4] % faltante por variable", ancho)
    falt.to_csv(ruta / "faltantes_por_variable.csv", index=False)

    # 6. Posicion
    pos = pd.concat([tabla_posicion(s).assign(capa=n) for n, s in subconjuntos.items()])
    pos = pos[["capa", COL_POSICION, "filas", "jugadores"]]
    imprimir("[5] Filas y jugadores por posicion", pos)
    pos.to_csv(ruta / "por_posicion.csv", index=False)

    # 7. Temporada
    temp = pd.DataFrame({n: s.groupby(COL_TEMPORADA).size() for n, s in subconjuntos.items()}).fillna(0).astype(int)
    temp = temp.rename_axis("season").reset_index()
    imprimir("[6] Filas por temporada y capa", temp)
    temp.to_csv(ruta / "por_temporada.csv", index=False)

    # 8. Club vendedor
    if any(c in dataset.columns for c in COLUMNAS_VENDEDOR):
        v = pd.DataFrame([{"capa": n, **tabla_vendedor(s)} for n, s in subconjuntos.items()])
        imprimir("[7] Variables del club vendedor por capa", v)
        v.to_csv(ruta / "club_vendedor.csv", index=False)
    else:
        print("\n[7] Omitida: no hay variables de club vendedor en los datos.")

    # 9. Faltantes de rendimiento en capa 3
    c3 = subconjuntos["capa3_h1"]
    por_pos = faltantes_rendimiento_por_grupo(c3, c3[COL_POSICION], "posicion")
    imprimir("[8] % faltante de rendimiento por posicion (capa 3)", por_pos)
    por_pos.to_csv(ruta / "faltantes_rendimiento_por_posicion.csv", index=False)
    if COL_MINUTOS in c3.columns:
        por_tramo = faltantes_rendimiento_por_grupo(c3, tramo_minutos(c3), "tramo_minutos")
        orden = ETIQUETAS_TRAMO_MINUTOS + ["sin dato"]
        por_tramo = por_tramo.set_index("tramo_minutos").reindex(orden).dropna(how="all").reset_index()
        imprimir("[9] % faltante de rendimiento por tramo de minutos (capa 3)", por_tramo)
        por_tramo.to_csv(ruta / "faltantes_rendimiento_por_tramo_minutos.csv", index=False)
    else:
        print(f"\n[9] Omitida: no hay {COL_MINUTOS} en los datos.")

    # 10. Vendedor por temporada
    if any(c in c3.columns for c in COLUMNAS_VENDEDOR):
        vt = vendedor_por_temporada(c3)
        imprimir("[10] Cobertura de variables de vendedor por temporada (capa 3)", vt)
        vt.to_csv(ruta / "vendedor_por_temporada.csv", index=False)

    # 11. Sin posicion
    ps = perfil_sin_posicion(c3)
    imprimir("[11] Filas sin posicion vs con posicion (capa 3)", ps)
    ps.to_csv(ruta / "perfil_sin_posicion.csv", index=False)

    print(f"\nListo. Tablas en {ruta}. Este script no decide nada: es la evidencia para elegir la "
          "capa de trabajo de cada chequeo de m0X.")


if __name__ == "__main__":
    main()