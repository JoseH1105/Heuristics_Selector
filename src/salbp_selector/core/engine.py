"""Motor constructivo común (contrato §9).

Algoritmo orientado a estaciones: se abre una estación; entre las candidatas (disponibles y
que caben) se asigna la de mejor prioridad según la regla; si no hay candidatas y quedan
tareas, se cierra la estación y se abre otra. K de un estado terminal = estaciones cerradas + 1.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
import time

from .instance import Instance
from .rules import RULE_IDS, pick, rank_vector
from .state import ConstructionState, initial_state

Policy = Callable[[ConstructionState], int]  # devuelve rule_id


@dataclass
class Solution:
    instance_id: str
    K: int
    stations: list[list[int]]
    rule_sequence: list[int]  # regla aplicada en cada asignación (0 = sin decisión)
    seconds: float
    extra: dict = field(default_factory=dict)

    @property
    def task_sequence(self) -> list[int]:
        return [i for st in self.stations for i in st]

    def loads(self, inst: Instance) -> list[int]:
        return [sum(inst.t[i] for i in st) for st in self.stations]


def step(state: ConstructionState, rule_id: int) -> ConstructionState:
    """Devuelve un estado nuevo tras asignar exactamente una tarea con la regla ``rule_id``."""
    new = state.copy()
    task = pick(new, rule_id)
    new.apply(task, rule_id)
    return new


def run(inst: Instance, policy: Policy, tiebreak: str | None = None) -> Solution:
    """Aplica la política hasta el estado terminal."""
    t0 = time.perf_counter()
    state = initial_state(inst, tiebreak)
    while not state.is_terminal():
        r = policy(state)
        state.apply(pick(state, r), r)
    return Solution(inst.instance_id, state.num_stations, state.stations, state.rule_sequence,
                    time.perf_counter() - t0)


def run_rule(inst: Instance, rule_id: int, tiebreak: str | None = None) -> Solution:
    return run(inst, lambda _s: rule_id, tiebreak)


def complete_k(state: ConstructionState, rule_id: int) -> int:
    """K total si desde ``state`` se aplica la regla ``rule_id`` hasta el final.

    Versión rápida: no copia el estado completo ni guarda estaciones."""
    inst = state.instance
    rank = rank_vector(inst, rule_id, state.tiebreak)
    t = inst.t
    succ = inst.imm_succ
    pending = list(state.pending)
    available = state.available
    assigned = state.assigned
    full = inst.full_mask
    idle = state.idle
    closed = state.closed_stations
    c = inst.cycle_time
    big = inst.n + 2
    while assigned != full:
        best = -1
        best_rank = big
        m = available
        while m:
            low = m & -m
            i = low.bit_length() - 1
            m ^= low
            if t[i] <= idle and rank[i] < best_rank:
                best = i
                best_rank = rank[i]
        if best < 0:
            closed += 1
            idle = c
            continue
        bit = 1 << best
        assigned |= bit
        available &= ~bit
        idle -= t[best]
        for j in succ[best]:
            pending[j] -= 1
            if pending[j] == 0:
                available |= 1 << j
    return closed + 1


def run_cocktail(inst: Instance, tiebreak: str | None = None) -> dict:
    """Ejecuta las 12 reglas y conserva el menor K.

    Devuelve ``{"K": {r: K_r}, "seconds": {r: s_r}, "K_min", "best_rules", "seconds_total"}``."""
    ks: dict[int, int] = {}
    secs: dict[int, float] = {}
    for r in RULE_IDS:
        t0 = time.perf_counter()
        ks[r] = complete_k(initial_state(inst, tiebreak), r)
        secs[r] = time.perf_counter() - t0
    k_min = min(ks.values())
    return {
        "K": ks,
        "seconds": secs,
        "K_min": k_min,
        "best_rules": [r for r in RULE_IDS if ks[r] == k_min],
        "seconds_total": sum(secs.values()),
    }
