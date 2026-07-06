"""
Pipeline de construcción del panel T -> T+3 para la tesis
==========================================================
Predicción del desarrollo de jugadores jóvenes vía crecimiento
del valor de mercado (Transfermarkt), aislando efectos de liga/año/posición.

Estructura del script:
    1. Configuración e imports
    2. Carga de datos crudos (Kaggle)
    3. Construcción de pares T -> T+3 (por jugador)
    4. Reducción a una ventana por jugador-año (thinning)
    5. Enriquecimiento con datos del jugador (edad, posición) y filtro sub-23
    6. Diagnósticos de calidad de datos
    7. Recuperación de ligas faltantes (liga_T)
    8. Construcción de la variable dependiente (crecimiento_log)
    9. Inspección de casos extremos ("descubrimientos")
    10. Limpieza final y primer modelo de efectos fijos (v1)
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import kagglehub
from linearmodels.panel import PanelOLS

pd.set_option("display.width", 160)

# ---------------------------------------------------------------------------
# 1. CONFIGURACIÓN
# ---------------------------------------------------------------------------
ANIO_MIN_COBERTURA = 2010     # antes de esto la densidad de datos es muy baja
HORIZONTE_ANIOS = 3           # ventana T -> T+3
TOLERANCIA_DIAS = 120         # margen para matchear la valuación más cercana a T+3
EDAD_MAX_T = 20                # sub-23: edad <=20 en T para seguir siendo joven en T+3
UMBRAL_OUTLIER_LOG = 4         # log-crecimiento > 4 => casos de "descubrimiento"
PISO_VALUACION = 50_000        # piso típico de Transfermarkt para jugadores no identificados


# ---------------------------------------------------------------------------
# 2. CARGA DE DATOS CRUDOS
# ---------------------------------------------------------------------------
def cargar_datos():
    path = kagglehub.dataset_download("davidcariboo/player-scores")

    valuations = pd.read_csv(f"{path}/player_valuations.csv")
    valuations["date"] = pd.to_datetime(valuations["date"])
    valuations = valuations[valuations["date"].dt.year >= ANIO_MIN_COBERTURA].copy()

    players = pd.read_csv(f"{path}/players.csv")
    players_slim = players[["player_id", "date_of_birth", "position", "sub_position", "name"]].copy()
    players_slim["date_of_birth"] = pd.to_datetime(players_slim["date_of_birth"])

    competitions = pd.read_csv(f"{path}/competitions.csv")

    return valuations, players_slim, competitions, path


# ---------------------------------------------------------------------------
# 3. CONSTRUCCIÓN DE PARES T -> T+3
# ---------------------------------------------------------------------------
def construir_pares(df, horizonte_anios=HORIZONTE_ANIOS, tol_dias=TOLERANCIA_DIAS):
    """Para cada valuación de un jugador, busca la valuación más cercana
    a 'horizonte_anios' después, dentro de una tolerancia de 'tol_dias'."""
    pares = []
    for pid, g in df.groupby("player_id"):
        g = g.sort_values("date").reset_index(drop=True)
        for _, row in g.iterrows():
            fecha_objetivo = row["date"] + pd.DateOffset(years=horizonte_anios)
            candidatos = g[(g["date"] - fecha_objetivo).abs() <= pd.Timedelta(days=tol_dias)]
            if not candidatos.empty:
                mejor = candidatos.iloc[(candidatos["date"] - fecha_objetivo).abs().argmin()]
                pares.append({
                    "player_id": pid,
                    "fecha_T": row["date"],
                    "valor_T": row["market_value_in_eur"],
                    "liga_T": row["player_club_domestic_competition_id"],
                    "fecha_T3": mejor["date"],
                    "valor_T3": mejor["market_value_in_eur"],
                    "liga_T3": mejor["player_club_domestic_competition_id"],
                })
    return pd.DataFrame(pares)


# ---------------------------------------------------------------------------
# 4. THINNING: UNA VENTANA POR JUGADOR-AÑO (reduce pseudo-replicación)
# ---------------------------------------------------------------------------
def aplicar_thinning(panel_t3):
    panel_t3 = panel_t3.copy()
    panel_t3["anio_T"] = panel_t3["fecha_T"].dt.year
    panel_thin = (
        panel_t3.sort_values("fecha_T")
        .groupby(["player_id", "anio_T"])
        .first()
        .reset_index()
    )
    return panel_thin


# ---------------------------------------------------------------------------
# 5. ENRIQUECIMIENTO CON DATOS DEL JUGADOR Y FILTRO SUB-23
# ---------------------------------------------------------------------------
def filtrar_sub23(panel_thin, players_slim, edad_max=EDAD_MAX_T):
    panel = panel_thin.merge(players_slim, on="player_id", how="left")
    panel["edad_T"] = (panel["fecha_T"] - panel["date_of_birth"]).dt.days / 365.25
    panel_sub23 = panel[panel["edad_T"] <= edad_max].copy()
    panel_sub23 = panel_sub23[panel_sub23["position"] != "Missing"].dropna(subset=["position"])
    return panel_sub23


# ---------------------------------------------------------------------------
# 6. DIAGNÓSTICOS DE CALIDAD DE DATOS
# ---------------------------------------------------------------------------
def diagnosticos_calidad(panel_sub23, valuations, players_slim):
    print("\n--- Cobertura y tamaño de muestra ---")
    print("Shape panel sub-23:", panel_sub23.shape)
    print("Jugadores únicos:", panel_sub23["player_id"].nunique())
    print("Ventanas promedio por jugador:", panel_sub23.groupby("player_id").size().mean())

    print("\n--- Distribución de edad en T ---")
    print(panel_sub23["edad_T"].describe())
    print("Casos con edad_T < 16:", (panel_sub23["edad_T"] < 16).sum())

    print("\n--- Cobertura por liga (top 15) ---")
    print(panel_sub23.groupby("liga_T").size().sort_values(ascending=False).head(15))

    print("\n--- Distribución por posición ---")
    print(panel_sub23["position"].value_counts())

    print("\n--- Ceros / nulos en valores ---")
    print("valor_T = 0:", (panel_sub23["valor_T"] == 0).sum())
    print("valor_T3 = 0:", (panel_sub23["valor_T3"] == 0).sum())
    print("valor_T3 nulo:", panel_sub23["valor_T3"].isna().sum())

    print("\n--- Amplitud de cobertura sub-23 por liga (todos los jugadores, no solo pares T->T+3) ---")
    sub23_all = valuations.merge(players_slim, on="player_id", how="left")
    sub23_all["edad"] = (sub23_all["date"] - sub23_all["date_of_birth"]).dt.days / 365.25
    sub23_all = sub23_all[sub23_all["edad"] <= EDAD_MAX_T]
    print(sub23_all.groupby("player_club_domestic_competition_id")["player_id"]
          .nunique().sort_values(ascending=False).head(10))


# ---------------------------------------------------------------------------
# 7. RECUPERACIÓN DE LIGAS FALTANTES (liga_T con NaN)
# ---------------------------------------------------------------------------
def recuperar_liga_faltante(panel_sub23, valuations):
    print("\n--- Recuperación de liga_T faltante ---")
    print("NaN antes:", panel_sub23["liga_T"].isna().mean())

    valuations_sorted = valuations.sort_values(["player_id", "date"]).copy()
    valuations_sorted["liga_rellenada"] = (
        valuations_sorted.groupby("player_id")["player_club_domestic_competition_id"]
        .transform(lambda x: x.ffill().bfill())
    )

    liga_lookup = valuations_sorted[["player_id", "date", "liga_rellenada"]]

    panel_sub23 = panel_sub23.merge(
        liga_lookup.rename(columns={"date": "fecha_T", "liga_rellenada": "liga_T_fix"}),
        on=["player_id", "fecha_T"], how="left"
    )
    panel_sub23 = panel_sub23.merge(
        liga_lookup.rename(columns={"date": "fecha_T3", "liga_rellenada": "liga_T3_fix"}),
        on=["player_id", "fecha_T3"], how="left"
    )
    panel_sub23["liga_T"] = panel_sub23["liga_T"].fillna(panel_sub23["liga_T_fix"])
    panel_sub23["liga_T3"] = panel_sub23["liga_T3"].fillna(panel_sub23["liga_T3_fix"])

    print("NaN residual (irreductible):", panel_sub23["liga_T"].isna().mean())

    # Modelo principal: se dropean los NaN residuales (~3.6%)
    panel_final = panel_sub23.dropna(subset=["liga_T"]).copy()
    return panel_final, panel_sub23  # panel_sub23 queda disponible con NaN para sensibilidad


# ---------------------------------------------------------------------------
# 8. VARIABLE DEPENDIENTE: CRECIMIENTO LOGARÍTMICO
# ---------------------------------------------------------------------------
def construir_variable_dependiente(panel_final):
    panel_final = panel_final.copy()
    panel_final["crecimiento_log"] = (
        np.log(panel_final["valor_T3"]) - np.log(panel_final["valor_T"])
    )
    panel_final["valor_T_piso"] = panel_final["valor_T"] <= PISO_VALUACION

    print("\n--- Distribución de crecimiento_log ---")
    print(panel_final["crecimiento_log"].describe())

    plt.figure()
    panel_final["crecimiento_log"].plot(kind="hist", bins=50)
    plt.title("Distribución de crecimiento_log (T -> T+3)")
    plt.show()

    return panel_final


# ---------------------------------------------------------------------------
# 9. CASOS EXTREMOS ("DESCUBRIMIENTOS")
# ---------------------------------------------------------------------------
def inspeccionar_extremos(panel_final, umbral=UMBRAL_OUTLIER_LOG):
    extremos = panel_final[panel_final["crecimiento_log"] > umbral].sort_values(
        "crecimiento_log", ascending=False
    )
    print(f"\n--- Casos extremos (crecimiento_log > {umbral}) ---")
    print(extremos[["name", "fecha_T", "valor_T", "fecha_T3", "valor_T3",
                     "crecimiento_log", "liga_T"]].head(20).to_string())
    return extremos


# ---------------------------------------------------------------------------
# 10. PRIMER MODELO DE EFECTOS FIJOS (liga + año + posición)
# ---------------------------------------------------------------------------
def modelo_efectos_fijos_v1(panel_final):
    panel = panel_final.copy()
    panel["anio_T_col"] = panel["anio_T"]  # copia fuera del índice, necesaria para la fórmula
    panel = panel.set_index(["player_id", "anio_T"])

    modelo = PanelOLS.from_formula(
        "crecimiento_log ~ 1 + C(liga_T) + C(anio_T_col) + C(position)",
        data=panel
    )
    resultado = modelo.fit(cov_type="clustered", cluster_entity=True)
    print("\n--- Modelo v1: efectos fijos de liga + año + posición ---")
    print(resultado)
    return resultado


# ---------------------------------------------------------------------------
# MAIN: corre todo el pipeline en orden
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    valuations, players_slim, competitions, path = cargar_datos()

    panel_t3 = construir_pares(valuations)
    panel_thin = aplicar_thinning(panel_t3)
    panel_sub23 = filtrar_sub23(panel_thin, players_slim)

    diagnosticos_calidad(panel_sub23, valuations, players_slim)

    panel_final, panel_sub23_con_nan = recuperar_liga_faltante(panel_sub23, valuations)
    panel_final = construir_variable_dependiente(panel_final)
    extremos = inspeccionar_extremos(panel_final)

    resultado_v1 = modelo_efectos_fijos_v1(panel_final)
