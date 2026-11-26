"""Instancia de SALBP-1 inmutable (contrato §9 del contexto maestro).

Las tareas se numeran 1..n. Los conjuntos de tareas se representan como máscaras
de bits en enteros de Python: el bit i corresponde a la tarea i (el bit 0 no se usa).

Al primer uso se calculan y guardan en caché (``functools.cached_property``):
predecesoras y sucesoras inmediatas, clausura transitiva como máscaras
(``succ_all``, ``pred_all``) y los atributos estáticos de las reglas
NS, NSI, PP, CI y CS.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from functools import cached_property
import heapq
from typing import Any


def iter_bits(mask: int) -> Iterator[int]:
    """Recorre los índices de los bits activos de ``mask`` de menor a mayor."""
    while mask:
        low = mask & -mask
        yield low.bit_length() - 1
        mask ^= low


def mask_of(tasks: Iterable[int]) -> int:
    """Máscara de bits de un conjunto de tareas."""
    m = 0
    for i in tasks:
        m |= 1 << i
    return m


def ceil_div(a: int, b: int) -> int:
    """⌈a/b⌉ exacto para enteros (b > 0)."""
    return -(-a // b)


@dataclass(frozen=True)
class Instance:
    """Instancia de SALBP-1: n tareas, tiempos enteros, precedencias y tiempo de ciclo."""

    instance_id: str
    n: int
    cycle_time: int
    times: tuple[int, ...]  # times[i-1] = t_i
    precedences: tuple[tuple[int, int], ...]  # arcos directos (i, j): i antes que j
    meta: dict[str, Any] = field(default_factory=dict, compare=False, hash=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "n", int(self.n))
        object.__setattr__(self, "cycle_time", int(self.cycle_time))
        object.__setattr__(self, "times", tuple(self.times))
        arcs = sorted({(int(i), int(j)) for i, j in self.precedences})
        object.__setattr__(self, "precedences", tuple(arcs))
        object.__setattr__(self, "meta", dict(self.meta) if self.meta else {})

    # ------------------------------------------------------------------ básicos
    @cached_property
    def t(self) -> tuple[int, ...]:
        """Tiempos con índice 1..n (t[0] = 0) para evitar restar 1 en los bucles."""
        return (0, *self.times)

    @cached_property
    def total_time(self) -> int:
        return sum(self.times)

    @cached_property
    def lb1(self) -> int:
        """LB1 = ⌈Σ t_i / c⌉."""
        return ceil_div(self.total_time, self.cycle_time)

    @cached_property
    def full_mask(self) -> int:
        """Máscara con las n tareas (bits 1..n)."""
        return (1 << (self.n + 1)) - 2

    @cached_property
    def _cache(self) -> dict:
        """Caché interna para estructuras derivadas (p. ej., rangos de prioridad)."""
        return {}

    # ------------------------------------------------------------ grafo directo
    @cached_property
    def imm_pred(self) -> tuple[tuple[int, ...], ...]:
        preds: list[list[int]] = [[] for _ in range(self.n + 1)]
        for i, j in self.precedences:
            preds[j].append(i)
        return tuple(tuple(sorted(p)) for p in preds)

    @cached_property
    def imm_succ(self) -> tuple[tuple[int, ...], ...]:
        succs: list[list[int]] = [[] for _ in range(self.n + 1)]
        for i, j in self.precedences:
            succs[i].append(j)
        return tuple(tuple(sorted(s)) for s in succs)

    @cached_property
    def topological_order(self) -> tuple[int, ...]:
        """Orden topológico (Kahn; entre disponibles, el menor número). Lanza ValueError si hay ciclo."""
        indeg = [len(p) for p in self.imm_pred]
        heap = [i for i in range(1, self.n + 1) if indeg[i] == 0]
        heapq.heapify(heap)
        order: list[int] = []
        while heap:
            i = heapq.heappop(heap)
            order.append(i)
            for j in self.imm_succ[i]:
                indeg[j] -= 1
                if indeg[j] == 0:
                    heapq.heappush(heap, j)
        if len(order) != self.n:
            raise ValueError(f"{self.instance_id}: el grafo de precedencias tiene un ciclo")
        return tuple(order)

    # ------------------------------------------------------ clausura transitiva
    @cached_property
    def succ_all(self) -> tuple[int, ...]:
        """succ_all[i] = máscara de todas las sucesoras (directas e indirectas) de i."""
        masks = [0] * (self.n + 1)
        for i in reversed(self.topological_order):
            m = 0
            for j in self.imm_succ[i]:
                m |= (1 << j) | masks[j]
            masks[i] = m
        return tuple(masks)

    @cached_property
    def pred_all(self) -> tuple[int, ...]:
        """pred_all[i] = máscara de todas las predecesoras de i."""
        masks = [0] * (self.n + 1)
        for j in self.topological_order:
            m = 0
            for i in self.imm_pred[j]:
                m |= (1 << i) | masks[i]
            masks[j] = m
        return tuple(masks)

    @cached_property
    def order_strength(self) -> float:
        """OS = 2·|E*| / (n·(n − 1)), con E* la clausura transitiva."""
        if self.n < 2:
            return 0.0
        closure = sum(m.bit_count() for m in self.succ_all)
        return 2.0 * closure / (self.n * (self.n - 1))

    def mask_time(self, mask: int) -> int:
        """Suma de tiempos de las tareas de ``mask``."""
        t = self.t
        return sum(t[i] for i in iter_bits(mask))

    # ------------------------------------------- atributos estáticos de reglas
    @cached_property
    def ns(self) -> tuple[int, ...]:
        """NS_i = número de sucesoras (todas)."""
        return tuple(m.bit_count() for m in self.succ_all)

    @cached_property
    def nsi(self) -> tuple[int, ...]:
        """NSI_i = número de sucesoras inmediatas."""
        return tuple(len(s) for s in self.imm_succ)

    @cached_property
    def pp(self) -> tuple[int, ...]:
        """PP_i = t_i + Σ_{j∈S_i} t_j (peso posicional)."""
        return (0, *(self.t[i] + self.mask_time(self.succ_all[i]) for i in range(1, self.n + 1)))

    @cached_property
    def ci(self) -> tuple[int, ...]:
        """CI_i = ⌈(t_i + Σ_{j∈P_i} t_j)/c⌉ (cota inferior de estación)."""
        c = self.cycle_time
        return (0, *(ceil_div(self.t[i] + self.mask_time(self.pred_all[i]), c) for i in range(1, self.n + 1)))

    @cached_property
    def cs(self) -> tuple[int, ...]:
        """CS_i = n + 1 − ⌈PP_i/c⌉ (cota superior de estación)."""
        c = self.cycle_time
        return (0, *(self.n + 1 - ceil_div(self.pp[i], c) for i in range(1, self.n + 1)))

    # ---------------------------------------------------------------- utilidades
    def to_dict(self) -> dict[str, Any]:
        """Diccionario con el formato JSON del contrato de datos (§10)."""
        return {
            "instance_id": self.instance_id,
            "n": self.n,
            "cycle_time": self.cycle_time,
            "times": list(self.times),
            "precedences": [list(a) for a in self.precedences],
            "meta": self.meta,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Instance":
        return cls(
            instance_id=str(d["instance_id"]),
            n=int(d["n"]),
            cycle_time=int(d["cycle_time"]),
            times=tuple(d["times"]),
            precedences=tuple(tuple(a) for a in d["precedences"]),
            meta=dict(d.get("meta") or {}),
        )
