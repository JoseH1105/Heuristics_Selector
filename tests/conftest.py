"""Utilidades compartidas por las pruebas."""

from __future__ import annotations

import random

import pytest

from salbp_selector.core.instance import Instance


def random_instance(seed: int, n_min: int = 5, n_max: int = 12, c: int = 20, p_arc: float = 0.3) -> Instance:
    """Instancia aleatoria pequeña (DAG con numeración topológica), independiente del generador."""
    rnd = random.Random(seed)
    n = rnd.randint(n_min, n_max)
    times = tuple(rnd.randint(1, c) for _ in range(n))
    arcs = tuple((i, j) for i in range(1, n + 1) for j in range(i + 1, n + 1) if rnd.random() < p_arc)
    return Instance(f"rand-{seed}", n, c, times, arcs, {"source": "test"})


@pytest.fixture
def hand_instance() -> Instance:
    """Instancia de 7 tareas resuelta a mano (ver tests/core/test_rules_engine.py)."""
    return Instance(
        "hand-7", 7, 10, (6, 3, 5, 4, 2, 5, 4),
        ((1, 3), (1, 4), (2, 4), (3, 5), (4, 5), (4, 6), (5, 7), (6, 7)),
    )
