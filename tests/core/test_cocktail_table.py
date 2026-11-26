"""Prueba de reproducción de la tabla publicada del cóctel (F2A §5).

Necesita las 269 instancias de Scholl en ``data/external/scholl/`` (o en la carpeta de la
variable de entorno ``SCHOLL_DIR``), en una de estas formas:
- archivos ``.alb`` (una instancia = grafo + tiempo de ciclo por archivo), o
- archivos ``.IN2`` más ``cycle_times.csv`` con columnas ``graph,cycle_time`` (una fila por instancia).

Si no están, la prueba se omite. Criterio: |media propia − media publicada| ≤ 0,02 por regla con
alguna variante de desempate. Si ninguna variante cumple, se documenta la diferencia (no se fuerza).
"""

import os
from pathlib import Path

import pandas as pd
import pytest

from salbp_selector.core import RULE_IDS, TIEBREAKS, load_instance, run_cocktail

PUBLISHED = {1: 22.513, 2: 22.595, 3: 22.981, 4: 22.743, 5: 23.520, 6: 23.260, 7: 22.788,
             8: 23.186, 9: 22.535, 10: 22.535, 11: 22.751, 12: 22.881}
PUBLISHED_COCKTAIL = 22.290

ROOT = Path(__file__).resolve().parents[2]
SCHOLL = Path(os.environ.get("SCHOLL_DIR", ROOT / "data" / "external" / "scholl"))


def _load_scholl():
    albs = sorted(SCHOLL.rglob("*.alb")) if SCHOLL.exists() else []
    if albs:
        return [load_instance(p) for p in albs]
    csv = SCHOLL / "cycle_times.csv"
    if csv.exists():
        files = {p.stem.upper(): p for p in SCHOLL.rglob("*") if p.suffix.lower() == ".in2"}
        df = pd.read_csv(csv)
        return [load_instance(files[str(r.graph).upper()], int(r.cycle_time)) for r in df.itertuples()]
    return []


@pytest.mark.slow
def test_reproduce_cocktail_table():
    insts = _load_scholl()
    if len(insts) == 0:
        pytest.skip(f"No se encontraron las instancias de Scholl en {SCHOLL}")
    report = {}
    for tb in TIEBREAKS:
        res = [run_cocktail(i, tiebreak=tb) for i in insts]
        means = {r: sum(x["K"][r] for x in res) / len(res) for r in RULE_IDS}
        report[tb] = {r: means[r] - PUBLISHED[r] for r in RULE_IDS}
    best = min(report, key=lambda tb: max(abs(d) for d in report[tb].values()))
    diff = pd.DataFrame(report)
    print("\nDiferencia (propia − publicada) por regla y desempate:\n", diff.round(3))
    assert len(insts) == 269, f"se esperaban 269 instancias y hay {len(insts)}"
    assert max(abs(d) for d in report[best].values()) <= 0.02, (
        f"Ninguna variante reproduce la tabla (mejor: {best}). Documentar y consultar a los tutores.")
