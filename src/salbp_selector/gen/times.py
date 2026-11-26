"""Tiempos de tarea (SALBPGen §5.2 y §8).

Tiempos enteros, redondeados, en [0,02·c; c]. Las muestras fuera del intervalo se vuelven
a sortear (truncación por rechazo).

| Distribución | Definición |
|---|---|
| BM, bimodal | p = 0,85: N(0,1·c; 0,15·c); p = 0,15: N(0,5·c; 0,05·c) (valores explícitos del artículo) |
| PB, pico inferior | N(0,1·c; 0,15·c) (supuesto: componente inferior de la bimodal) |
| PM, pico central | N(0,5·c; 0,05·c) (supuesto: componente superior de la bimodal) |

Los parámetros se leen de ``configs/generator.yaml`` (sección ``times``).
"""

from __future__ import annotations

import math

import numpy as np

TIME_DISTS = ("pb", "bm", "pm")

DEFAULT_TIME_PARAMS = {
    "min_fraction": 0.02,
    "max_fraction": 1.0,
    "bm": {"p_low": 0.85, "low_mean": 0.10, "low_sd": 0.15, "high_mean": 0.50, "high_sd": 0.05},
    "pb": {"mean": 0.10, "sd": 0.15},
    "pm": {"mean": 0.50, "sd": 0.05},
}


def time_bounds(cycle_time: int, params: dict | None = None) -> tuple[int, int]:
    p = params or DEFAULT_TIME_PARAMS
    lo = math.ceil(p.get("min_fraction", 0.02) * cycle_time - 1e-9)
    hi = math.floor(p.get("max_fraction", 1.0) * cycle_time + 1e-9)
    return max(1, lo), hi


def _draw(k: int, dist: str, c: int, rng: np.random.Generator, p: dict) -> np.ndarray:
    if dist == "bm":
        q = p["bm"]
        low = rng.random(k) < q["p_low"]
        x = np.where(
            low,
            rng.normal(q["low_mean"] * c, q["low_sd"] * c, k),
            rng.normal(q["high_mean"] * c, q["high_sd"] * c, k),
        )
    elif dist in ("pb", "pm"):
        q = p[dist]
        x = rng.normal(q["mean"] * c, q["sd"] * c, k)
    else:
        raise ValueError(f"distribución de tiempos desconocida: {dist}")
    return np.rint(x)


def sample_times(n: int, dist: str, cycle_time: int, rng: np.random.Generator,
                 params: dict | None = None, max_rounds: int = 1000) -> list[int]:
    """Sortea ``n`` tiempos enteros en [⌈0,02·c⌉; c] con la distribución ``dist``."""
    p = params or DEFAULT_TIME_PARAMS
    lo, hi = time_bounds(cycle_time, p)
    out = np.empty(0)
    for _ in range(max_rounds):
        need = n - out.size
        if need <= 0:
            break
        x = _draw(max(need * 2, 8), dist, cycle_time, rng, p)
        x = x[(x >= lo) & (x <= hi)]
        out = np.concatenate([out, x[:need]])
    if out.size < n:
        raise RuntimeError("no se pudieron sortear tiempos dentro del intervalo")
    return [int(v) for v in out[:n]]
