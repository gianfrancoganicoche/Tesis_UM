"""
listar_ligas_europa_sin_cobertura.py -- ad-hoc (25/09): de las 23 ligas
domesticas europeas de competitions.csv (Capa 3 nominal, hipotesis_y_diseno_v2.md),
lista cuales de ellas SI tienen cobertura real en appearances.csv (las 14 ya
confirmadas via revisar_cobertura_appearances.py) y cuales NO -- para saber
exactamente que le falta a la Capa 3 real respecto de la nominal, con nombre
y pais, no solo con el codigo de competition_id.
"""
import sys
from pathlib import Path

_RAIZ_SCRIPTS = Path(__file__).resolve().parents[1]
for _carpeta in ("config", "dataset", "eda", "diagnosticos"):
    sys.path.insert(0, str(_RAIZ_SCRIPTS / _carpeta))

import d02_construir_variables_contexto as ctx

# Las 14 confirmadas por revisar_cobertura_appearances.py (25/09, corrida real)
LIGAS_CON_COBERTURA_REAL = {
    "IT1", "ES1", "GB1", "FR1", "TR1", "L1", "NL1",
    "PO1", "BE1", "RU1", "GR1", "SC1", "UKR1", "DK1",
}


def main():
    tablas = ctx.cargar_tablas()
    competitions = tablas["competitions"]

    europa_domesticas = competitions[
        (competitions["type"] == "domestic_league") & (competitions["confederation"] == "europa")
    ].copy()
    print(f"Ligas domesticas 'europa' en competitions.csv: {len(europa_domesticas)}")

    europa_domesticas["tiene_cobertura_real"] = europa_domesticas["competition_id"].isin(LIGAS_CON_COBERTURA_REAL)

    columnas = [c for c in ["competition_id", "name", "country_name"] if c in europa_domesticas.columns]
    columnas = columnas + ["tiene_cobertura_real"]

    print("\n=== CON cobertura real en appearances.csv (14 esperadas) ===")
    print(europa_domesticas[europa_domesticas["tiene_cobertura_real"]][columnas].to_string(index=False))

    print("\n=== SIN cobertura real en appearances.csv (listadas en competitions.csv/games.csv, pero appearances.csv no tiene eventos) ===")
    sin_cobertura = europa_domesticas[~europa_domesticas["tiene_cobertura_real"]][columnas]
    print(sin_cobertura.to_string(index=False))
    print(f"\nTotal sin cobertura real: {len(sin_cobertura)} (deberian ser 23-14=9 si todo cuadra)")


if __name__ == "__main__":
    main()