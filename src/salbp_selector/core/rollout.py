"""*Rollout* sobre las 12 reglas (contrato §9, F2A §4.5).

En cada asignación se completa la solución con cada regla y se aplica la que da menos
estaciones. Empate en el mínimo: se conserva la regla del paso anterior si está entre las
mínimas; si no, la de menor índice. Así el *rollout* nunca empeora al cóctel.

Estado de decisión: estado en el que las 12 reglas no eligen todas la misma tarea. En los
demás no se calculan terminaciones. Tras aplicar la regla r*, su terminación desde el estado
siguiente ya se conoce (es la misma), así que no se recalcula.
"""

from __future__ import annotations

from dataclasses import dataclass
import time

import numpy as np

from .engine import Solution, complete_k
from .instance import Instance
from .rules import RULE_IDS, picks
from .state import ConstructionState, initial_state


@dataclass
class DecisionRecord:
    instance_id: str
    step: int
    state: ConstructionState  # copia del estado de decisión (antes de asignar)
    completions: np.ndarray  # K total con cada regla (posición r-1)
    applied_rule: int
    picks: tuple[int, ...]  # tarea elegida por cada regla


def completions(state: ConstructionState) -> np.ndarray:
    """K total si desde ``state`` se sigue cada regla hasta el final (12 valores)."""
    return np.array([complete_k(state, r) for r in RULE_IDS], dtype=np.int64)


def run_rollout(inst: Instance, record: bool = False, tiebreak: str | None = None):
    """Ejecuta el *rollout*. Devuelve ``Solution`` o, si ``record``, ``(Solution, [DecisionRecord])``.

    En ``Solution.rule_sequence`` las asignaciones sin decisión llevan la regla vigente
    (0 si aún no hubo ninguna decisión). ``Solution.extra`` trae el número de estados de decisión.
    """
    t0 = time.perf_counter()
    state = initial_state(inst, tiebreak)
    prev_rule = 0
    known: tuple[int, int] | None = None  # (regla, K) de la terminación ya conocida
    records: list[DecisionRecord] = []
    n_decisions = 0
    while not state.is_terminal():
        chosen = picks(state)
        if len(set(chosen)) == 1:
            # No es estado de decisión: todas las reglas eligen la misma tarea.
            state.apply(chosen[0], prev_rule)
            continue
        n_decisions += 1
        ks = np.empty(len(RULE_IDS), dtype=np.int64)
        for r in RULE_IDS:
            if known is not None and known[0] == r:
                ks[r - 1] = known[1]
            else:
                ks[r - 1] = complete_k(state, r)
        k_min = int(ks.min())
        if prev_rule and ks[prev_rule - 1] == k_min:
            rule = prev_rule
        else:
            rule = int(np.flatnonzero(ks == k_min)[0]) + 1
        if record:
            records.append(DecisionRecord(inst.instance_id, state.step, state.copy(), ks, rule, chosen))
        state.apply(chosen[rule - 1], rule)
        prev_rule = rule
        known = (rule, k_min)
    sol = Solution(inst.instance_id, state.num_stations, state.stations, state.rule_sequence,
                   time.perf_counter() - t0, extra={"n_decision_states": n_decisions})
    return (sol, records) if record else sol
