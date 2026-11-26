"""Las 12 reglas de prioridad del IOC (Corominas, García-Villoria y Pastor, 2012).

Cada regla tiene un vector de prioridades estático (se calcula una vez por instancia).
Para elegir rápido, por cada combinación (regla, desempate) se precalcula el **rango**
de cada tarea: 0 es la de mejor prioridad. ``pick`` elige, entre las candidatas, la de
menor rango.

Decisiones abiertas implementadas aquí (contexto maestro §6):
- P1: desempate configurable en un solo lugar (``DEFAULT_TIEBREAK``); variantes en ``TIEBREAKS``.
- P2: en R11, holgura CS_i − CI_i ≤ 0 → prioridad +∞ (la holgura negativa no debería darse;
  se trata igual que la holgura cero por seguridad).
- R9, R10, R11 y R12 usan ``fractions.Fraction``: los empates no dependen del redondeo.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from fractions import Fraction
import math
from typing import TYPE_CHECKING, Any

from .instance import Instance

if TYPE_CHECKING:  # pragma: no cover
    from .state import ConstructionState

# ----------------------------------------------------------------- desempate (P1)
TIEBREAKS: dict[str, Callable[[Instance, int], tuple]] = {
    "lowest_index": lambda inst, i: (i,),
    "longest_time": lambda inst, i: (-inst.t[i], i),
    "largest_pp": lambda inst, i: (-inst.pp[i], i),
}
DEFAULT_TIEBREAK = "lowest_index"
N_RULES = 12
RULE_IDS = tuple(range(1, N_RULES + 1))


@dataclass(frozen=True)
class Rule:
    rule_id: int
    code: str
    name: str
    sense: str  # "max" | "min"
    expression: str
    func: Callable[[Instance, int], Any] = field(repr=False, compare=False)

    def value(self, inst: Instance, i: int) -> Any:
        return self.func(inst, i)

    def priorities(self, inst: Instance) -> tuple:
        """Vector de prioridades con índice 1..n (posición 0 = None)."""
        return (None, *(self.func(inst, i) for i in range(1, inst.n + 1)))


def _slack(inst: Instance, i: int) -> int:
    return inst.cs[i] - inst.ci[i]


def _r11(inst: Instance, i: int) -> Any:
    s = _slack(inst, i)
    if s <= 0:  # P2
        return math.inf
    return Fraction(inst.ns[i], s)


def _r10(inst: Instance, i: int) -> Any:
    cs = inst.cs[i]
    return Fraction(inst.t[i], cs) if cs > 0 else math.inf


_RULE_LIST = [
    Rule(1, "R1", "Peso posicional", "max", "PP_i", lambda s, i: s.pp[i]),
    Rule(2, "R2", "Tiempo de tarea", "max", "t_i", lambda s, i: s.t[i]),
    Rule(3, "R3", "Sucesoras inmediatas", "max", "NSI_i", lambda s, i: s.nsi[i]),
    Rule(4, "R4", "Sucesoras", "max", "NS_i", lambda s, i: s.ns[i]),
    Rule(5, "R5", "Cota inferior", "min", "CI_i", lambda s, i: s.ci[i]),
    Rule(6, "R6", "Cota superior", "min", "CS_i", lambda s, i: s.cs[i]),
    Rule(7, "R7", "Holgura", "min", "CS_i − CI_i", _slack),
    Rule(8, "R8", "Número de tarea", "min", "i", lambda s, i: i),
    Rule(9, "R9", "Cota superior entre sucesoras", "min", "CS_i / (NS_i + 1)",
         lambda s, i: Fraction(s.cs[i], s.ns[i] + 1)),
    Rule(10, "R10", "Tiempo entre cota superior", "max", "t_i / CS_i", _r10),
    Rule(11, "R11", "Sucesoras entre holgura", "max", "NS_i / (CS_i − CI_i)", _r11),
    Rule(12, "R12", "Peso posicional medio", "max", "PP_i / (NS_i + 1)",
         lambda s, i: Fraction(s.pp[i], s.ns[i] + 1)),
]
RULES: dict[int, Rule] = {r.rule_id: r for r in _RULE_LIST}


def rank_vector(inst: Instance, rule_id: int, tiebreak: str | None = None) -> tuple[int, ...]:
    """Rango de cada tarea para la regla (0 = mejor). Índice 1..n; la posición 0 vale n+1."""
    tb = tiebreak or DEFAULT_TIEBREAK
    key = ("rank", rule_id, tb)
    cache = inst._cache
    hit = cache.get(key)
    if hit is not None:
        return hit
    rule = RULES[rule_id]
    tbf = TIEBREAKS[tb]
    pr = rule.priorities(inst)
    if rule.sense == "max":
        order = sorted(range(1, inst.n + 1), key=lambda i: (-pr[i], tbf(inst, i)))
    else:
        order = sorted(range(1, inst.n + 1), key=lambda i: (pr[i], tbf(inst, i)))
    rank = [inst.n + 1] * (inst.n + 1)
    for pos, i in enumerate(order):
        rank[i] = pos
    result = tuple(rank)
    cache[key] = result
    return result


def pick(state: "ConstructionState", rule_id: int) -> int:
    """Tarea que elige la regla ``rule_id`` en ``state``.

    Si ninguna tarea disponible cabe en la estación abierta, se elige entre las disponibles
    (la que se asignará tras abrir una estación nueva), como hace ``engine.step``.
    """
    cands = state.effective_candidates()
    if not cands:
        raise ValueError("No hay tareas por asignar: el estado es terminal")
    rank = rank_vector(state.instance, rule_id, state.tiebreak)
    return min(cands, key=rank.__getitem__)


def picks(state: "ConstructionState") -> tuple[int, ...]:
    """Tarea elegida por cada una de las 12 reglas (posición r-1 → regla r)."""
    cands = state.effective_candidates()
    inst, tb = state.instance, state.tiebreak
    return tuple(min(cands, key=rank_vector(inst, r, tb).__getitem__) for r in RULE_IDS)
