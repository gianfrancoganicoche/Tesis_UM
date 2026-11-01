"""
Script de extraccion: corre el pipeline completo (variables de contexto +
rendimiento + panel de predictores + variable dependiente) y guarda los
resultados en data/processed/ (via config.RUTA_DATOS_PROCESSED).

Es el punto de entrada / orquestador: no define logica de negocio propia,
solo llama a los builders (d02 a d05, d08) en orden y persiste los dos
productos finales -- panel_predictores (solo predictores) y dataset_modelable
(predictores + variable dependiente, lo que efectivamente se usa para
modelar).

CAMBIO 16/09/2026: este script tenia su propia cargar_tablas() duplicada,
que llamaba a kagglehub.dataset_download() en vivo sin fijar version. Se
elimina la duplicacion: usa d02_construir_variables_contexto.cargar_tablas(),
que lee del snapshot congelado fijado en config.RUTA_DATOS_CONGELADOS.

CAMBIO 19/09/2026: main() ahora tambien construye la variable dependiente
(T41) y hace el merge final -- antes el script se quedaba en el panel de
predictores, que no es el dataset modelable.

CAMBIO 21/09/2026 (reorganizacion/auditoria): se absorben aca los chequeos
de sanidad que vivian sueltos en extraer_dataset_modelable.py -- ese archivo
era un fragmento exploratorio, no un script corrible por si solo (su propio
comentario decia "en extraer_panel_predictores.py, o un script nuevo
extraer_dataset_modelable.py", disyuntiva que el cambio del 19/09 ya habia
resuelto a favor de la primera opcion). Ese archivo queda retirado del
pipeline reorganizado.

De paso, las rutas de guardado pasan de strings relativos ("data/processed")
a config.RUTA_DATOS_PROCESSED, para que no dependan de desde donde se corre
el script (mismo motivo que en config.py / construir_variables_contexto.py).

CAMBIO 24/09/2026: se agrega el merge de atributos_jugador (d08 -- altura_cm
y pie_habil desde players.csv). Merge por player_id solo (no player_id+season,
son atributos fijos del jugador), justo despues del panel de predictores y
su chequeo de duplicados -- antes del PCA de contexto, sin relacion con el.

CAMBIO 24/09/2026 (mismo dia, segunda pasada): d08 ahora tambien construye
es_comunitario (misma logica de merge por player_id, ya venia con altura_cm
y pie_habil -- ver docstring de d08 para la reconstruccion completa de esta
variable, que existia como resultado documentado pero no como codigo).

CAMBIO 24/09/2026 (mismo dia, tercera pasada): se agrega el merge de d09
(z-score de las 6 variables finales de rendimiento_it + altura_cm, por
posicion_amplia_predominante x season de la fila). Va sobre dataset_modelable
(no sobre panel), al final, despues del merge con la variable dependiente --
d09 no necesita la DV para nada, pero mantenerlo como ultimo paso evita tener
que reordenar los chequeos de sanidad de mas abajo (todos indiferentes a las
columnas z_*).

CAMBIO 31/10/2026 (decisiones previas al modelo base, nota para el tutor):
(1) se agrega el merge de valor_previo (d05.construir_valor_previo: log_valor_previo
y rezago_previo, variante C -- sin filas nuevas), justo despues del merge de la
variable dependiente; (2) d03 ahora trae amarillas_90 y tuvo_roja y d09 estandariza
amarillas_90 en lugar de tarjetas_90: como cambia la lista de variables del z-score,
los parametros guardados quedan viejos y hay que reajustarlos UNA vez -- correr con
`--forzar-reajuste-zscore`.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

_RAIZ_SCRIPTS = Path(__file__).resolve().parents[1]  # scripts/, tras la reorganizacion en subcarpetas (22/09)
for _carpeta in ("config", "dataset", "eda", "diagnosticos"):
    sys.path.insert(0, str(_RAIZ_SCRIPTS / _carpeta))

import config
import d02_construir_variables_contexto as ctx
import d05_construir_variable_dependiente as dv
import d07_construir_pca_exito_deportivo as pca_exito
import d08_construir_atributos_jugador as atributos
import d09_estandarizar_zscore as zscore
from d04_construir_panel_predictores import construir_panel_predictores


def main(forzar_reajuste_zscore=False):
    tablas = ctx.cargar_tablas()

    panel = construir_panel_predictores(tablas)

    # NaN de competencias europeas = "no jugo europeo esa temporada", no dato
    # faltante -- rellenar explicito (ver bitacora entrada 4, 20/07/2026)
    cols_europeas_a_cero = ["partidos_europeos", "fase_maxima_alcanzada", "competencias_distintas"]
    panel[cols_europeas_a_cero] = panel[cols_europeas_a_cero].fillna(0)
    panel["jugo_fase_grupos_o_mas"] = panel["jugo_fase_grupos_o_mas"].fillna(False)

    # Chequeo de sanidad antes de guardar -- no guardar silenciosamente un
    # panel con duplicados de clave
    n_duplicados = panel.duplicated(subset=["player_id", "season"]).sum()
    if n_duplicados > 0:
        raise ValueError(
            f"El panel tiene {n_duplicados} filas duplicadas en (player_id, season). "
            "No se guarda hasta resolver la causa."
        )
    print(f"Panel de predictores: {panel.shape[0]} filas, {panel.shape[1]} columnas. Sin duplicados.")

    # --- Atributos de jugador (d08 -- altura_cm y pie_habil desde players.csv) ---
    # Merge por player_id (no player_id+season): son atributos fijos del
    # jugador, no varian por temporada. construir_atributos_jugador ya valida
    # que no haya player_id duplicado en players.csv antes de devolver el
    # dataframe, asi que este merge no deberia poder fanear filas del panel.
    n_filas_antes_atributos = panel.shape[0]
    atributos_jugador = atributos.construir_atributos_jugador(tablas["players"])
    panel = panel.merge(atributos_jugador, on="player_id", how="left")
    if panel.shape[0] != n_filas_antes_atributos:
        raise ValueError(
            f"El merge de atributos_jugador cambio la cantidad de filas del panel "
            f"({n_filas_antes_atributos} -> {panel.shape[0]}). No deberia pasar con "
            "un merge left por player_id sin duplicados -- no se guarda hasta revisar."
        )
    print(f"Cobertura altura_cm: {panel['altura_cm'].notna().mean():.4f}")
    print(f"Cobertura pie_habil: {panel['pie_habil'].notna().mean():.4f}")
    print(f"Cobertura es_comunitario: {panel['es_comunitario'].notna().mean():.4f}")
    print(f"Proporcion comunitaria (sobre no-nulos): {panel['es_comunitario'].mean():.4f}")

    # --- PCA de exito deportivo del club (d07) ---
    # Usa parametros ya ajustados y guardados si existen (caso normal en
    # todas las corridas despues de la primera); si es la primera vez que se
    # corre el pipeline reorganizado, los ajusta y los guarda en
    # data/processed/parametros_pca_exito_deportivo.json -- ver docstring de
    # d07 para el razonamiento completo de por que esto NO es un refit en
    # cada corrida.
    pca_resultado, _parametros_pca = pca_exito.construir_pca_exito_deportivo(panel)
    panel = panel.merge(pca_resultado, on=["player_id", "season"], how="left")
    print(f"Cobertura pca_exito_deportivo: {panel['pca_exito_deportivo'].notna().mean():.4f}")

    # --- Variable dependiente (T41) + merge final ---
    variable_dependiente = dv.construir_variable_dependiente(
        tablas["player_valuations"], tablas["players"]
    )
    dataset_modelable = panel.merge(variable_dependiente, on=["player_id", "season"], how="left")

    # Chequeo de sanidad agregado (21/09): variable_dependiente ya sale unica
    # por (player_id, season) de construir_valor_mercado_por_temporada
    # (drop_duplicates keep="last"), asi que este merge no deberia introducir
    # duplicados -- pero se valida en vez de asumirlo, mismo criterio que el
    # chequeo de arriba.
    n_duplicados_final = dataset_modelable.duplicated(subset=["player_id", "season"]).sum()
    if n_duplicados_final > 0:
        raise ValueError(
            f"El dataset modelable tiene {n_duplicados_final} filas duplicadas en "
            "(player_id, season) despues del merge con la variable dependiente. "
            "No se guarda hasta resolver la causa."
        )

    # --- Valor previo (variante C, 31/10/2026) ---
    # Ultima valuacion anterior a la temporada de cada fila (incluye valuaciones de antes
    # de que el jugador entrara al panel). No agrega filas: left join por clave unica.
    n_filas_antes_previo = dataset_modelable.shape[0]
    valor_mercado_temporada = dv.construir_valor_mercado_por_temporada(tablas["player_valuations"])
    valor_previo = dv.construir_valor_previo(
        valor_mercado_temporada, dataset_modelable[["player_id", "season"]]
    )
    dataset_modelable = dataset_modelable.merge(valor_previo, on=["player_id", "season"], how="left")
    if dataset_modelable.shape[0] != n_filas_antes_previo:
        raise ValueError(
            f"El merge de valor_previo cambio la cantidad de filas del dataset modelable "
            f"({n_filas_antes_previo} -> {dataset_modelable.shape[0]}). No se guarda hasta revisar."
        )
    print(f"Cobertura log_valor_previo: {dataset_modelable['log_valor_previo'].notna().mean():.4f}")
    print("rezago_previo (temporadas hasta la valuacion previa) - distribucion:")
    print(dataset_modelable["rezago_previo"].value_counts(dropna=False).sort_index().head(8))

    # --- Z-score de rendimiento_it + altura_cm (d09) ---
    # Merge por player_id+season (a diferencia de d08): el z-score de cada
    # variable, aun para las que son atributos fijos del jugador (edad_debut,
    # altura_cm), se calcula con la clave (posicion_amplia_predominante,
    # season) DE LA FILA -- ver docstring de d09 para el porque de esta
    # decision. construir_zscore ya valida coincidencia de filas por si sola
    # (aplicar_zscore devuelve una fila por cada fila de entrada, mismo
    # indice), pero se chequea el conteo de todas formas, mismo criterio que
    # el resto de los merges de este script.
    n_filas_antes_zscore = dataset_modelable.shape[0]
    zscore_resultado, _parametros_zscore = zscore.construir_zscore(
        dataset_modelable, forzar_reajuste=forzar_reajuste_zscore
    )
    dataset_modelable = dataset_modelable.merge(zscore_resultado, on=["player_id", "season"], how="left")
    if dataset_modelable.shape[0] != n_filas_antes_zscore:
        raise ValueError(
            f"El merge del z-score cambio la cantidad de filas del dataset modelable "
            f"({n_filas_antes_zscore} -> {dataset_modelable.shape[0]}). No deberia pasar -- "
            "no se guarda hasta revisar."
        )
    for variable in zscore.VARIABLES_A_ESTANDARIZAR:
        col = f"z_{variable}"
        print(f"Cobertura {col}: {dataset_modelable[col].notna().mean():.4f}")

    print(f"\nDataset modelable: {dataset_modelable.shape[0]} filas, {dataset_modelable.shape[1]} columnas.")
    print(f"Cobertura log_valor_mercado: {dataset_modelable['log_valor_mercado'].notna().mean():.4f}")
    print(f"Cobertura edad: {dataset_modelable['edad'].notna().mean():.4f}")

    print("\nedad - describe:")
    print(dataset_modelable["edad"].describe())

    print("\nvalor_mercado_eur - describe:")
    print(dataset_modelable["valor_mercado_eur"].describe())

    # Chequeos de sanidad especificos (migrados de extraer_dataset_modelable.py,
    # ver nota del modulo) -- log(0) o log(negativo) da -inf/NaN sin tirar
    # error visible; valores <=0 o nulos en market_value_in_eur romperian
    # log_valor_mercado en silencio si no se los detecta aca.
    n_valor_no_positivo = (dataset_modelable["valor_mercado_eur"] <= 0).sum()
    n_log_infinito = np.isinf(dataset_modelable["log_valor_mercado"]).sum()
    print(f"\nFilas con valor_mercado_eur <= 0: {n_valor_no_positivo}")
    print(f"Filas con log_valor_mercado infinito: {n_log_infinito}")

    # Edad fuera de rango razonable para el dataset (deberia rondar 15-40)
    fuera_de_rango = dataset_modelable.loc[
        (dataset_modelable["edad"] < 14) | (dataset_modelable["edad"] > 42), "edad"
    ]
    print(f"\nFilas con edad < 14 o > 42: {fuera_de_rango.shape[0]}")
    if fuera_de_rango.shape[0] > 0:
        print(fuera_de_rango.describe())

    config.RUTA_DATOS_PROCESSED.mkdir(parents=True, exist_ok=True)
    fecha = pd.Timestamp.now().strftime("%Y-%m-%d")

    def _guardar(df, nombre):
        try:
            ruta_parquet = config.RUTA_DATOS_PROCESSED / f"{nombre}_{fecha}.parquet"
            df.to_parquet(ruta_parquet, index=False)
            print(f"Guardado: {ruta_parquet}")
        except ImportError:
            print("pyarrow/fastparquet no disponibles -- guardando solo CSV.")
        ruta_csv = config.RUTA_DATOS_PROCESSED / f"{nombre}_{fecha}.csv"
        df.to_csv(ruta_csv, index=False)
        print(f"Guardado: {ruta_csv}")

    _guardar(panel, "panel_predictores")
    _guardar(dataset_modelable, "dataset_modelable")

    return tablas, panel, dataset_modelable


if __name__ == "__main__":
    # --forzar-reajuste-zscore: reajusta (y guarda) los parametros del z-score de d09.
    # Necesario la primera vez tras cambiar la lista de variables estandarizadas.
    tablas, panel_predictores, dataset_modelable = main(
        forzar_reajuste_zscore="--forzar-reajuste-zscore" in sys.argv
    )