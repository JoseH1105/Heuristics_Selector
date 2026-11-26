import time

import numpy as np
import pytest

from salbp_selector.core import validate_instance
from salbp_selector.core.io import content_hash
from salbp_selector.gen import (
    CellSpec, core_cells, derive_seed, generate, generate_batch, os_tolerance, resolve_config,
    sample_extended_cell, sample_times,
)
from salbp_selector.gen.graphs import bottleneck_tasks, chain_tasks, graph_measures, levels, order_strength
from salbp_selector.gen.times import time_bounds

CFG = resolve_config()


# ------------------------------------------------- definiciones sobre grafos a mano
def test_order_strength_hand():
    assert order_strength(3, [(1, 2), (2, 3)]) == 1.0
    assert order_strength(3, []) == 0.0
    assert order_strength(4, [(1, 2), (3, 4)]) == pytest.approx(2 * 2 / 12)


def test_chain_definition_hand():
    # 1→2→3 es cadena; 4 se bifurca a 5 y 6, que no son de cadena; 7→8 sí
    arcs = [(1, 2), (2, 3), (3, 4), (4, 5), (4, 6), (7, 8)]
    assert chain_tasks(8, arcs) == {1, 2, 3, 7, 8}
    # una tarea cuya predecesora tiene otras sucesoras no se une a la cadena de esa predecesora
    assert chain_tasks(3, [(1, 2), (1, 3)]) == set()
    # una tarea aislada no es cadena (mínimo 2 tareas)
    assert chain_tasks(1, []) == set()


def test_bottleneck_definition_hand():
    # 1,2 → 3 → 4,5 : 3 es cuello de botella de grado 4
    arcs = [(1, 3), (2, 3), (3, 4), (3, 5)]
    bns = bottleneck_tasks(5, arcs)
    assert [b["task"] for b in bns] == [3] and bns[0]["degree"] == 4
    # si la predecesora 2 tiene otra sucesora, 3 solo tiene 1 predecesora exclusiva → no lo es
    arcs2 = arcs + [(2, 6)]
    assert bottleneck_tasks(6, arcs2) == []


def test_levels_hand():
    assert levels(4, [(1, 2), (2, 4), (1, 3)])[1:] == [1, 2, 2, 3]


# ----------------------------------------------------------------------- tiempos
@pytest.mark.parametrize("dist", ["pb", "bm", "pm"])
def test_times_in_range(dist):
    rng = np.random.default_rng(0)
    t = sample_times(5000, dist, 1000, rng)
    assert min(t) >= 20 and max(t) <= 1000 and all(isinstance(x, int) for x in t)
    assert time_bounds(1000) == (20, 1000)


def test_time_shapes():
    rng = np.random.default_rng(1)
    pm = np.array(sample_times(5000, "pm", 1000, rng))
    assert abs(pm.mean() - 500) < 10
    pb = np.array(sample_times(5000, "pb", 1000, rng))
    assert np.median(pb) < 200


# ------------------------------------------------------------- generador completo
def test_63_core_cells():
    cells = core_cells()
    assert len(cells) == 63 and len({c.cell_id for c in cells}) == 63


@pytest.mark.parametrize("ci", range(0, 63, 4))
def test_generated_instances_comply(ci):
    cell = core_cells()[ci]
    for k in range(3):
        inst = generate(cell, derive_seed(5, "core", ci, k), index=k)
        assert validate_instance(inst) == []  # acíclica, topológica, tiempos válidos
        assert all(i < j for i, j in inst.precedences)
        g = graph_measures(inst.n, inst.precedences)
        assert abs(g["os"] - cell.os_target) <= os_tolerance(cell.n, CFG) + 1e-12
        lo, hi = time_bounds(1000)
        assert all(lo <= t <= hi for t in inst.times)
        if cell.structure == "chain":
            assert g["chain_share"] >= 0.40
        if cell.structure == "bottleneck":
            dmin = 4 if cell.n == 20 else 8
            assert sum(d >= dmin for d in g["bottleneck_degrees"]) >= 1
        assert inst.meta["layer"] == "core" and inst.instance_id.startswith("gen-v1-core-")


def test_determinism_by_seed():
    cell = CellSpec(50, 0.6, "mixed", "bm")
    a = generate(cell, 123)
    b = generate(cell, 123)
    assert a == b and a.meta["content_hash"] == b.meta["content_hash"]
    c = generate(cell, 124)
    assert content_hash(a) != content_hash(c)


def test_extended_cells_in_ranges():
    rng = np.random.default_rng(0)
    for _ in range(300):
        cell = sample_extended_cell(rng)
        lo, hi = CFG["extended"]["os_range"][cell.structure]
        assert lo <= cell.os_target <= hi and cell.n in (20, 50, 100)
        if cell.structure == "bottleneck":
            assert cell.n_bottlenecks >= 1
            d_lo, d_hi = (4, 8) if cell.n == 20 else (8, 14)
            assert d_lo <= cell.bottleneck_degree <= d_hi


def test_batch_no_duplicates_and_ids():
    insts = list(generate_batch(1, 40, master_seed=99, sizes=[20]))
    hashes = [i.meta["content_hash"] for i in insts]
    assert len(hashes) == len(set(hashes)) == 21 + 40
    assert len({i.instance_id for i in insts}) == len(insts)
    assert any(i.instance_id.startswith("gen-v1-ext-n20-") for i in insts)


@pytest.mark.slow
def test_rejection_rate_below_50pct_for_n50_n100():
    for ci, cell in enumerate(core_cells()):
        if cell.n < 50:
            continue
        att = sum(generate(cell, derive_seed(11, "core", ci, k)).meta["attempts"] for k in range(20))
        assert 1 - 20 / att < 0.5, cell.cell_id


@pytest.mark.slow
def test_100_instances_n100_under_a_minute():
    t0 = time.perf_counter()
    cells = [c for c in core_cells() if c.n == 100]
    for k in range(100):
        generate(cells[k % len(cells)], derive_seed(3, "core", k, k))
    assert time.perf_counter() - t0 < 60
