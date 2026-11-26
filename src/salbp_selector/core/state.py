"""Estado de construcción del algoritmo voraz orientado a estaciones (contrato §9).

El conjunto de tareas disponibles (todas sus predecesoras asignadas) se mantiene de forma
incremental con contadores de predecesoras pendientes, para no recorrer todas las tareas
en cada paso.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .instance import Instance, iter_bits
from .rules import DEFAULT_TIEBREAK


@dataclass
class ConstructionState:
    instance: Instance
    assigned: int = 0  # máscara de bits de tareas asignadas
    closed_stations: int = 0  # estaciones ya cerradas
    idle: int = -1  # tiempo libre de la estación abierta (-1 → c al crear)
    step: int = 0  # asignaciones realizadas
    available: int = -1  # máscara de tareas no asignadas con predecesoras asignadas
    pending: list[int] | None = None  # predecesoras inmediatas aún sin asignar
    stations: list[list[int]] = field(default_factory=list)
    rule_sequence: list[int] = field(default_factory=list)
    tiebreak: str = DEFAULT_TIEBREAK

    def __post_init__(self) -> None:
        inst = self.instance
        if self.idle < 0:
            self.idle = inst.cycle_time
        if self.pending is None:
            self.pending = [len(p) for p in inst.imm_pred]
        if self.available < 0:
            self.available = 0
            for i in range(1, inst.n + 1):
                if self.pending[i] == 0 and not (self.assigned >> i) & 1:
                    self.available |= 1 << i
        if not self.stations:
            self.stations = [[]]

    # ------------------------------------------------------------- consultas
    def candidates(self) -> list[int]:
        """Tareas disponibles cuyo tiempo cabe en el tiempo libre de la estación abierta."""
        t, idle = self.instance.t, self.idle
        return [i for i in iter_bits(self.available) if t[i] <= idle]

    def effective_candidates(self) -> list[int]:
        """Candidatas; si no hay y quedan tareas, las disponibles (tras abrir estación)."""
        c = self.candidates()
        if c or self.is_terminal():
            return c
        return list(iter_bits(self.available))

    def is_terminal(self) -> bool:
        return self.assigned == self.instance.full_mask

    @property
    def num_stations(self) -> int:
        """Estaciones usadas hasta ahora (cerradas + la abierta)."""
        return self.closed_stations + 1

    @property
    def remaining(self) -> int:
        return self.instance.n - self.step

    def copy(self) -> "ConstructionState":
        return ConstructionState(
            instance=self.instance,
            assigned=self.assigned,
            closed_stations=self.closed_stations,
            idle=self.idle,
            step=self.step,
            available=self.available,
            pending=list(self.pending),
            stations=[list(s) for s in self.stations],
            rule_sequence=list(self.rule_sequence),
            tiebreak=self.tiebreak,
        )

    # ------------------------------------------------------------ mutación
    def apply(self, task: int, rule_id: int = 0) -> None:
        """Asigna ``task`` en el lugar (abre estación si no cabe). Uso interno del motor."""
        inst = self.instance
        bit = 1 << task
        if not self.available & bit:
            raise ValueError(f"La tarea {task} no está disponible")
        t = inst.t[task]
        if t > self.idle:
            if self.candidates():
                raise ValueError(f"La tarea {task} no cabe y hay otras candidatas que sí caben")
            self.closed_stations += 1
            self.idle = inst.cycle_time
            self.stations.append([])
        self.assigned |= bit
        self.available &= ~bit
        self.idle -= t
        self.stations[-1].append(task)
        pending = self.pending
        for j in inst.imm_succ[task]:
            pending[j] -= 1
            if pending[j] == 0:
                self.available |= 1 << j
        self.step += 1
        self.rule_sequence.append(rule_id)


def initial_state(inst: Instance, tiebreak: str | None = None) -> ConstructionState:
    return ConstructionState(inst, tiebreak=tiebreak or DEFAULT_TIEBREAK)
