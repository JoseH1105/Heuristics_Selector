"""Generación de grafos de precedencia por etapas (SALBPGen, Otto, Otto y Scholl, 2013, §5.2)
y medidas de estructura (§5.1).

Procedimiento de cuatro pasos:
1. **Estructuras.** Se siembran las cadenas y los cuellos de botella que pida la celda.
2. **Reparto en etapas.** El resto de tareas se reparte entre las etapas (uniforme en esperanza).
3. **Anclaje.** Cada tarea de una etapa se une con exactamente una tarea, al azar, de la
   etapa anterior (si la tarea admite predecesora y hay alguna que admita sucesora).
4. **Arcos hasta el OS objetivo.** Se insertan al azar arcos no redundantes, actualizando la
   clausura transitiva con máscaras de bits, hasta llegar al OS objetivo sin pasar del límite
   superior del intervalo de tolerancia.

Las estructuras sembradas se protegen con capacidades de grado:
- cadena: cada tarea admite como máximo 1 predecesora y 1 sucesora;
- alimentadora de un cuello de botella: solo admite 1 sucesora (el cuello de botella);
- seguidora de un cuello de botella: solo admite 1 predecesora (el cuello de botella).

Al terminar se eliminan los arcos redundantes (reducción transitiva), se numeran las tareas
por etapas (numeración topológica, P8) y se miden las estructuras.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

import numpy as np

from ..core.instance import iter_bits


class GraphGenerationError(Exception):
    """El grafo no se pudo construir con los parámetros dados (se reintenta con otra semilla)."""


@dataclass(frozen=True)
class GraphSpec:
    n: int
    os_target: float
    os_tolerance: float
    n_stages: int
    chain_share: float = 0.0
    n_bottlenecks: int = 0
    bottleneck_degree: int = 0
    max_direct_successors: int | None = None
    max_chain_length: int | None = None


@dataclass
class GraphResult:
    arcs: list[tuple[int, int]]  # arcos directos 1..n, i < j
    stage: list[int]  # etapa planificada de cada tarea (índice 1..n; posición 0 = -1)
    role: list[str]  # papel sembrado: "free", "chain", "bottleneck", "feeder", "follower", "relay"
    os: float
    reached: bool
    n_stages_planned: int
    n_stages_used: int
    closure_pairs: int


# =========================================================================== builder
class _Builder:
    def __init__(self, max_direct: int | None) -> None:
        self.stage: list[int] = []
        self.max_in: list[int | None] = []
        self.max_out: list[int | None] = []
        self.role: list[str] = []
        self.preds: list[set[int]] = []
        self.succs: list[set[int]] = []
        self.max_direct = max_direct

    @property
    def count(self) -> int:
        return len(self.stage)

    def add(self, stage: int, role: str = "free", max_in: int | None = None, max_out: int | None = None) -> int:
        v = len(self.stage)
        self.stage.append(stage)
        self.role.append(role)
        self.max_in.append(max_in)
        self.max_out.append(max_out)
        self.preds.append(set())
        self.succs.append(set())
        return v

    def arc(self, u: int, v: int) -> None:
        self.succs[u].add(v)
        self.preds[v].add(u)

    def can_out(self, u: int) -> bool:
        k = len(self.succs[u])
        mo = self.max_out[u]
        if mo is not None and k >= mo:
            return False
        return self.max_direct is None or k < self.max_direct

    def can_in(self, v: int) -> bool:
        mi = self.max_in[v]
        return mi is None or len(self.preds[v]) < mi


def _chain_lengths(total: int, lmax: int, rng: np.random.Generator) -> list[int]:
    """Longitudes (≥ 2, ≤ lmax) que suman ``total`` (o ``total`` + 1 si no se puede exacto)."""
    if lmax < 2:
        raise GraphGenerationError("chains_need_2_stages")
    lengths: list[int] = []
    remaining = total
    while remaining > 0:
        if remaining == 1:
            # Alargar una cadena existente o añadir una de 2 (se pasa en una tarea: "al menos").
            for k, L in enumerate(lengths):
                if L < lmax:
                    lengths[k] += 1
                    break
            else:
                lengths.append(2)
            break
        L = int(rng.integers(2, min(lmax, remaining) + 1))
        if remaining - L == 1:
            L = L + 1 if L + 1 <= min(lmax, remaining) else L - 1 if L - 1 >= 2 else L
        lengths.append(L)
        remaining -= L
    return lengths


# ========================================================================= generación
def generate_graph(spec: GraphSpec, rng: np.random.Generator) -> GraphResult:
    """Genera un grafo de precedencias según ``spec`` (ver docstring del módulo)."""
    n, S = spec.n, max(1, spec.n_stages)
    b = _Builder(spec.max_direct_successors)

    # ---------------------------------------------------------------- 1. estructuras
    n_chain = int(round(spec.chain_share * n))
    if n_chain > 0:
        lmax = min(S, spec.max_chain_length or S)
        for L in _chain_lengths(n_chain, lmax, rng):
            s0 = int(rng.integers(0, S - L + 1))
            nodes = [b.add(s0 + k, "chain", max_in=1, max_out=1) for k in range(L)]
            for u, v in zip(nodes, nodes[1:]):
                b.arc(u, v)

    if spec.n_bottlenecks > 0:
        if S < 3:
            raise GraphGenerationError("bottleneck_needs_3_stages")
        d = spec.bottleneck_degree
        if d < 4:
            raise GraphGenerationError("bottleneck_degree_below_4")
        stages_bn = sorted(int(rng.integers(1, S - 1)) for _ in range(spec.n_bottlenecks))
        reusable: dict[int, list[int]] = defaultdict(list)  # seguidoras que pueden alimentar
        for sb in stages_bn:
            k_in = int(rng.integers(2, d - 1))  # en [2, d-2] → k_out ≥ 2
            k_out = d - k_in
            bn = b.add(sb, "bottleneck")
            pool = reusable[sb - 1]
            for _ in range(k_in):
                if pool:  # una seguidora de otro cuello de botella sirve de alimentadora
                    f = pool.pop()
                    b.role[f] = "relay"
                    b.max_out[f] = 1
                else:
                    f = b.add(sb - 1, "feeder", max_out=1)
                b.arc(f, bn)
            for _ in range(k_out):
                f = b.add(sb + 1, "follower", max_in=1)
                b.arc(bn, f)
                reusable[sb + 1].append(f)

    if b.count > n:
        raise GraphGenerationError("structures_exceed_n")

    # ---------------------------------------------------------- 2. reparto en etapas
    rest = n - b.count
    if rest:
        counts = rng.multinomial(rest, [1.0 / S] * S)
        for s, k in enumerate(counts):
            for _ in range(int(k)):
                b.add(s, "free")
    used = sorted(set(b.stage))
    remap = {s: k for k, s in enumerate(used)}
    b.stage = [remap[s] for s in b.stage]
    S_used = len(used)
    by_stage: list[list[int]] = [[] for _ in range(S_used)]
    for v, s in enumerate(b.stage):
        by_stage[s].append(v)

    # ------------------------------------------------------------------ 3. anclaje
    for s in range(1, S_used):
        nodes = by_stage[s]
        for idx in rng.permutation(len(nodes)):
            v = nodes[int(idx)]
            if b.preds[v] or not b.can_in(v):
                continue
            parents = [u for u in by_stage[s - 1] if b.can_out(u)]
            if parents:
                b.arc(parents[int(rng.integers(len(parents)))], v)

    # ----------------------------------------------------- clausura transitiva inicial
    succ_all = [0] * n
    pred_all = [0] * n
    for s in range(S_used - 1, -1, -1):
        for v in by_stage[s]:
            m = 0
            for w in b.succs[v]:
                m |= (1 << w) | succ_all[w]
            succ_all[v] = m
    for s in range(S_used):
        for v in by_stage[s]:
            m = 0
            for u in b.preds[v]:
                m |= (1 << u) | pred_all[u]
            pred_all[v] = m
    total = sum(m.bit_count() for m in succ_all)

    pairs = n * (n - 1) / 2 if n > 1 else 1.0
    lo = max(0.0, spec.os_target - spec.os_tolerance) * pairs
    hi = (spec.os_target + spec.os_tolerance) * pairs
    goal = spec.os_target * pairs

    # ------------------------------------------------- 4. arcos hasta el OS objetivo
    if total < goal:
        cand = [(u, v) for u in range(n) for v in range(n) if b.stage[u] < b.stage[v]]
        for idx in rng.permutation(len(cand)):
            if total >= goal:
                break
            u, v = cand[int(idx)]
            if (succ_all[u] >> v) & 1:
                continue  # redundante: v ya es sucesora de u
            if not b.can_out(u) or not b.can_in(v):
                continue
            A = pred_all[u] | (1 << u)
            B = succ_all[v] | (1 << v)
            added = 0
            for a in iter_bits(A):
                added += (B & ~succ_all[a]).bit_count()
            if total + added > hi:
                continue
            for a in iter_bits(A):
                succ_all[a] |= B
            for w in iter_bits(B):
                pred_all[w] |= A
            total += added
            b.arc(u, v)

    reached = lo - 1e-9 <= total <= hi + 1e-9

    # ------------------------------------------------------- reducción transitiva
    for u in range(n):
        for v in list(b.succs[u]):
            if any((succ_all[w] >> v) & 1 for w in b.succs[u] if w != v):
                b.succs[u].discard(v)
                b.preds[v].discard(u)

    # --------------------------------------------------- numeración por etapas (P8)
    tie = rng.random(n)
    order = sorted(range(n), key=lambda v: (b.stage[v], tie[v]))
    number = [0] * n
    for pos, v in enumerate(order):
        number[v] = pos + 1
    arcs = sorted((number[u], number[v]) for u in range(n) for v in b.succs[u])
    stage = [-1] * (n + 1)
    role = [""] * (n + 1)
    for v in range(n):
        stage[number[v]] = b.stage[v] + 1
        role[number[v]] = b.role[v]
    return GraphResult(
        arcs=arcs,
        stage=stage,
        role=role,
        os=2.0 * total / (n * (n - 1)) if n > 1 else 0.0,
        reached=reached,
        n_stages_planned=S,
        n_stages_used=S_used,
        closure_pairs=total,
    )


# ============================================================================ medidas
def adjacency(n: int, arcs) -> tuple[list[list[int]], list[list[int]]]:
    preds: list[list[int]] = [[] for _ in range(n + 1)]
    succs: list[list[int]] = [[] for _ in range(n + 1)]
    for i, j in arcs:
        succs[i].append(j)
        preds[j].append(i)
    return preds, succs


def _topo(n: int, preds, succs) -> list[int]:
    indeg = [len(p) for p in preds]
    stack = [i for i in range(n, 0, -1) if indeg[i] == 0]
    order = []
    while stack:
        i = stack.pop()
        order.append(i)
        for j in succs[i]:
            indeg[j] -= 1
            if indeg[j] == 0:
                stack.append(j)
    if len(order) != n:
        raise ValueError("el grafo tiene un ciclo")
    return order


def closure(n: int, arcs) -> list[int]:
    """Máscaras de sucesoras (todas) por tarea, índice 1..n."""
    preds, succs = adjacency(n, arcs)
    masks = [0] * (n + 1)
    for i in reversed(_topo(n, preds, succs)):
        m = 0
        for j in succs[i]:
            m |= (1 << j) | masks[j]
        masks[i] = m
    return masks


def order_strength(n: int, arcs) -> float:
    if n < 2:
        return 0.0
    return 2.0 * sum(m.bit_count() for m in closure(n, arcs)) / (n * (n - 1))


def levels(n: int, arcs) -> list[int]:
    """Nivel de cada tarea = longitud del camino más largo que termina en ella (fuentes = 1)."""
    preds, succs = adjacency(n, arcs)
    lev = [0] * (n + 1)
    for i in _topo(n, preds, succs):
        lev[i] = 1 + max((lev[p] for p in preds[i]), default=0)
    return lev


def chain_tasks(n: int, arcs) -> set[int]:
    """Tareas en cadenas (§5.1): componentes de ≥ 2 tareas formadas por tareas con como máximo
    una predecesora y una sucesora directas, unidas entre sí. Un arco entre dos de esas tareas
    es exclusivo: la predecesora no tiene otras sucesoras ni la sucesora otras predecesoras."""
    preds, succs = adjacency(n, arcs)
    simple = [False] + [len(preds[i]) <= 1 and len(succs[i]) <= 1 for i in range(1, n + 1)]
    seen = [False] * (n + 1)
    result: set[int] = set()
    for i in range(1, n + 1):
        if not simple[i] or seen[i]:
            continue
        comp, stack = [], [i]
        seen[i] = True
        while stack:
            u = stack.pop()
            comp.append(u)
            for w in preds[u] + succs[u]:
                if simple[w] and not seen[w]:
                    seen[w] = True
                    stack.append(w)
        if len(comp) >= 2:
            result.update(comp)
    return result


def bottleneck_tasks(n: int, arcs) -> list[dict]:
    """Cuellos de botella (§5.1): tarea que es la única sucesora directa de al menos dos de sus
    predecesoras directas y la única predecesora directa de al menos dos de sus sucesoras."""
    preds, succs = adjacency(n, arcs)
    out = []
    for b in range(1, n + 1):
        ex_in = sum(1 for p in preds[b] if len(succs[p]) == 1)
        ex_out = sum(1 for s in succs[b] if len(preds[s]) == 1)
        if ex_in >= 2 and ex_out >= 2:
            out.append({
                "task": b,
                "in_degree": len(preds[b]),
                "out_degree": len(succs[b]),
                "degree": len(preds[b]) + len(succs[b]),
                "exclusive_in": ex_in,
                "exclusive_out": ex_out,
            })
    return out


def graph_measures(n: int, arcs) -> dict:
    """Medidas de estructura usadas en la validación y en ``meta``."""
    preds, succs = adjacency(n, arcs)
    lev = levels(n, arcs)
    chains = chain_tasks(n, arcs)
    bns = bottleneck_tasks(n, arcs)
    indeg = [len(preds[i]) for i in range(1, n + 1)]
    outdeg = [len(succs[i]) for i in range(1, n + 1)]
    non_src = [d for d in indeg if d > 0]
    non_snk = [d for d in outdeg if d > 0]
    return {
        "os": order_strength(n, arcs),
        "n_arcs": len(arcs),
        "mean_degree": 2 * len(arcs) / n if n else 0.0,
        "mean_in_degree": float(np.mean(non_src)) if non_src else 0.0,
        "mean_out_degree": float(np.mean(non_snk)) if non_snk else 0.0,
        "max_in_degree": max(indeg, default=0),
        "max_out_degree": max(outdeg, default=0),
        "n_stages": max(lev[1:], default=0),
        "n_sources": sum(1 for d in indeg if d == 0),
        "n_sinks": sum(1 for d in outdeg if d == 0),
        "n_chain_tasks": len(chains),
        "chain_share": len(chains) / n if n else 0.0,
        "n_bottlenecks": len(bns),
        "bottleneck_degrees": sorted((b["degree"] for b in bns), reverse=True),
        "bottleneck_tasks": [b["task"] for b in bns],
        "chain_task_list": sorted(chains),
    }
