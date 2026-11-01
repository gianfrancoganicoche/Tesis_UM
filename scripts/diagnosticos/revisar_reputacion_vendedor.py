"""
Script ad-hoc: revisar_reputacion_vendedor.py

Investiga la barra aislada cerca del maximo en el histograma de
reputacion_vendedor (~3.4-3.5M).
"""
import sys
from pathlib import Path

_RAIZ_SCRIPTS = Path(__file__).resolve().parents[1]  # scripts/, tras la reorganizacion en subcarpetas (22/09)
for _carpeta in ("config", "dataset", "eda", "diagnosticos"):
    sys.path.insert(0, str(_RAIZ_SCRIPTS / _carpeta))
import d02_construir_variables_contexto as ctx


def main():
    tablas = ctx.cargar_tablas()

    mapa_club_liga = ctx.construir_mapa_club_liga_por_temporada(
        tablas["games"], tablas["club_games"]
    )
    score_prestigio = ctx.construir_score_prestigio_liga(
        tablas["transfers"], tablas["players"], mapa_club_liga, tablas["competitions"]
    )
    reputacion = ctx.construir_reputacion_club_vendedor(
        tablas["transfers"], tablas["players"], mapa_club_liga, score_prestigio
    )

    print("=== Ligas por score de prestigio, de mayor a menor ===")
    print(
        score_prestigio.dropna(subset=["score_prestigio_liga"])
        .sort_values("score_prestigio_liga", ascending=False)
        [["name", "country_name", "score_prestigio_liga", "transferencias_consideradas"]]
        .to_string(index=False)
    )

    con_dato = reputacion.dropna(subset=["reputacion_vendedor"])
    umbral_alto = con_dato["reputacion_vendedor"].quantile(0.99)
    altos = con_dato[con_dato["reputacion_vendedor"] >= umbral_alto]

    print(f"\nClub-temporadas con reputacion_vendedor >= percentil 99 ({umbral_alto:,.0f}): {len(altos)}")
    print(altos.sort_values("reputacion_vendedor", ascending=False).to_string(index=False))

    liga_top = (
        score_prestigio.dropna(subset=["score_prestigio_liga"])
        .sort_values("score_prestigio_liga", ascending=False)
        .iloc[0]
    )
    print(f"\nLiga de mayor score_prestigio_liga: {liga_top['name']} ({liga_top['country_name']}), "
          f"score={liga_top['score_prestigio_liga']:,.0f}")
    print("Si el valor del pico aislado coincide con este score, confirma que son clubes")
    print("cuyas ventas con score fueron TODAS a esa unica liga.")

    return score_prestigio, reputacion


if __name__ == "__main__":
    score_prestigio_ligas, reputacion_vendedor_diagnostico = main()