"""Generador de instancias de SALBP-1 basado en SALBPGen (F2B §4.5).

Dos capas con los mismos factores:
- **núcleo** (``core``): las 63 celdas del diseño factorial del conjunto de referencia;
- **ampliada** (``extended``): valores intermedios dentro de los mismos rangos.

La semilla de cada instancia se deriva de ``master_seed``, la celda y el índice con
``numpy.random.SeedSequence``: la misma terna produce la misma instancia en cualquier máquina.
Si una instancia no cumple su celda se descarta y se reintenta con la semilla siguiente
(``seed + 1``, ``seed + 2``, …); el número de intentos queda en ``meta``.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterator
import copy
from dataclasses import asdict, dataclass, replace
import math
from pathlib import Path
import time

import numpy as np
import yaml

from ..core.instance import Instance
from ..core.io import content_hash, validate_instance
from .graphs import GraphGenerationError, GraphSpec, generate_graph, graph_measures
from .times import DEFAULT_TIME_PARAMS, TIME_DISTS, sample_times, time_bounds

GENERATOR_VERSION = 1
STRUCTURES = ("chain", "bottleneck", "mixed")
STRUCTURE_CODE = {"chain": "ch", "bottleneck": "bn", "mixed": "mix"}
# Tabla 6 del artículo: 7 combinaciones útiles de estructura y OS.
CORE_GRAPH_COMBOS = (
    ("mixed", 0.2), ("mixed", 0.6), ("mixed", 0.9),
    ("chain", 0.2), ("chain", 0.6),
    ("bottleneck", 0.2), ("bottleneck", 0.6),
)

DEFAULT_CONFIG: dict = {
    "version": GENERATOR_VERSION,
    "master_seed": 20261116,
    "cycle_time": 1000,
    "sizes": [20, 50, 100],
    "os_tolerance": [  # §5.2
        {"max_n": 20, "tol": 0.10},
        {"max_n": 49, "tol": 0.05},
        {"max_n": None, "tol": 0.005},
    ],
    "stages": {"mode": "auto",
               "anchor_os_fraction": {"mixed": 0.9, "chain": 0.9, "bottleneck": 0.3},
               "min_stages": 3,
               "fixed": {20: None, 50: None, 100: None}},
    "max_direct_successors": None,
    "max_chain_length": 5,
    "max_attempts": 500,
    "structures": {
        "chain_min_share_core": 0.40,
        "bottleneck": {
            "min_degree": {20: 4, "default": 8},
            "degree_range": {20: [4, 8], "default": [8, 14]},
            "share_range": [0.01, 0.06],
        },
    },
    "times": copy.deepcopy(DEFAULT_TIME_PARAMS),
    "extended": {
        "structure_weights": {"mixed": 3 / 7, "chain": 2 / 7, "bottleneck": 2 / 7},
        "os_range": {"mixed": [0.20, 0.90], "chain": [0.20, 0.60], "bottleneck": [0.20, 0.60]},
        "chain_share_range": {"chain": [0.40, 0.60], "mixed": [0.0, 0.45]},
    },
}


class GenerationError(RuntimeError):
    """No se logró una instancia válida para la celda en ``max_attempts`` intentos."""


# ============================================================================ config
def _deep_update(base: dict, upd: dict) -> dict:
    for k, v in upd.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _deep_update(base[k], v)
        else:
            base[k] = v
    return base


def resolve_config(config: dict | None = None) -> dict:
    """Combina ``config`` con los valores por defecto (no modifica la entrada)."""
    cfg = copy.deepcopy(DEFAULT_CONFIG)
    if config:
        _deep_update(cfg, copy.deepcopy(config))
    return cfg


def load_config(path: str | Path | None) -> dict:
    """Lee ``configs/generator.yaml`` y lo combina con los valores por defecto."""
    if path is None:
        return resolve_config()
    with open(path, encoding="utf-8") as fh:
        return resolve_config(yaml.safe_load(fh) or {})


def _by_size(table: dict, n: int):
    if n in table:
        return table[n]
    if str(n) in table:
        return table[str(n)]
    return table["default"]


def os_tolerance(n: int, cfg: dict) -> float:
    for row in cfg["os_tolerance"]:
        if row["max_n"] is None or n <= row["max_n"]:
            return float(row["tol"])
    return 0.005


def n_stages_for(n: int, os_target: float, cfg: dict, structure: str = "mixed") -> int:
    """Número de etapas. ``fixed`` (Tabla 5 del artículo) tiene prioridad; si es nulo se usa
    el modo ``auto``: S = 1 + f·OS·(n − 1). En un bosque de anclaje con etapas de igual tamaño
    el OS vale (S − 1)/(n − 1), así que el anclaje deja el OS en una fracción f del objetivo y
    el paso 4 tiene margen para llegar a él. ``f`` puede darse por estructura."""
    st = cfg["stages"]
    fixed = st.get("fixed") or {}
    val = fixed.get(n, fixed.get(str(n)))
    if val:
        return int(val)
    f = st.get("anchor_os_fraction", 0.6)
    if isinstance(f, dict):
        f = f.get(structure, f.get("default", 0.6))
    s = round(1 + float(f) * os_target * (n - 1))
    return int(min(n, max(st.get("min_stages", 3), s)))


def bottleneck_min_degree(n: int, cfg: dict) -> int:
    return int(_by_size(cfg["structures"]["bottleneck"]["min_degree"], n))


# ============================================================================= celdas
@dataclass(frozen=True)
class CellSpec:
    n: int
    os_target: float
    structure: str  # "chain" | "bottleneck" | "mixed"
    time_dist: str  # "pb" | "bm" | "pm"
    layer: str = "core"  # "core" | "extended"
    chain_share: float | None = None
    n_bottlenecks: int | None = None
    bottleneck_degree: int | None = None
    cycle_time: int = 1000

    @property
    def cell_id(self) -> str:
        """Identificador de celda para estratificar (núcleo) o agrupar (ampliada)."""
        code = STRUCTURE_CODE[self.structure]
        if self.layer == "core":
            return f"n{self.n}-os{int(round(self.os_target * 10)):02d}-{code}-{self.time_dist}"
        return f"ext-n{self.n}-{code}-{self.time_dist}"


def core_cells(sizes=(20, 50, 100), cycle_time: int = 1000) -> list[CellSpec]:
    """Las 63 celdas del núcleo: 3 tamaños × 7 combinaciones de grafo × 3 distribuciones."""
    return [
        CellSpec(n, os_t, struct, dist, "core", cycle_time=cycle_time)
        for n in sizes
        for struct, os_t in CORE_GRAPH_COMBOS
        for dist in TIME_DISTS
    ]


def sample_extended_cell(rng: np.random.Generator, config: dict | None = None,
                         sizes=None) -> CellSpec:
    """Sortea una celda de la capa ampliada (F2B §4.2)."""
    cfg = resolve_config(config)
    ext = cfg["extended"]
    sizes = list(sizes or cfg["sizes"])
    n = int(sizes[int(rng.integers(len(sizes)))])
    names = list(ext["structure_weights"])
    w = np.array([ext["structure_weights"][k] for k in names], dtype=float)
    structure = names[int(rng.choice(len(names), p=w / w.sum()))]
    lo, hi = ext["os_range"][structure]
    os_target = round(float(rng.uniform(lo, hi)), 3)
    chain_share = None
    n_bn = deg = None
    if structure in ext["chain_share_range"]:
        a, b = ext["chain_share_range"][structure]
        chain_share = round(float(rng.uniform(a, b)), 3)
    if structure == "bottleneck":
        n_bn, deg = _sample_bottlenecks(n, rng, cfg)
    dist = TIME_DISTS[int(rng.integers(len(TIME_DISTS)))]
    return CellSpec(n, os_target, structure, dist, "extended", chain_share, n_bn, deg,
                    int(cfg["cycle_time"]))


def _sample_bottlenecks(n: int, rng: np.random.Generator, cfg: dict) -> tuple[int, int]:
    bcfg = cfg["structures"]["bottleneck"]
    s_lo, s_hi = bcfg["share_range"]
    k_lo = max(1, math.ceil(s_lo * n - 1e-9))
    k_hi = max(k_lo, math.floor(s_hi * n + 1e-9))
    d_lo, d_hi = _by_size(bcfg["degree_range"], n)
    return int(rng.integers(k_lo, k_hi + 1)), int(rng.integers(d_lo, d_hi + 1))


def _resolve_structure(cell: CellSpec, rng: np.random.Generator, cfg: dict) -> CellSpec:
    """Completa los parámetros de estructura que la celda deja libres (capa núcleo)."""
    if cell.structure == "chain" and cell.chain_share is None:
        cell = replace(cell, chain_share=float(cfg["structures"]["chain_min_share_core"]))
    if cell.structure == "bottleneck" and (cell.n_bottlenecks is None or cell.bottleneck_degree is None):
        k, d = _sample_bottlenecks(cell.n, rng, cfg)
        cell = replace(cell, n_bottlenecks=cell.n_bottlenecks or k,
                       bottleneck_degree=cell.bottleneck_degree or d)
    return cell


def instance_id_for(cell: CellSpec, index: int, version: int = GENERATOR_VERSION) -> str:
    if cell.layer == "core":
        code = STRUCTURE_CODE[cell.structure]
        os_code = f"{int(round(cell.os_target * 10)):02d}"
        return f"gen-v{version}-core-n{cell.n}-os{os_code}-{code}-{cell.time_dist}-{index:06d}"
    return f"gen-v{version}-ext-n{cell.n}-{index:06d}"


def derive_seed(master_seed: int, layer: str, cell_index: int, index: int, purpose: int = 0) -> int:
    """Semilla de 32 bits derivada con ``SeedSequence`` (independiente de la máquina)."""
    layer_code = 0 if layer == "core" else 1
    ss = np.random.SeedSequence(int(master_seed), spawn_key=(layer_code, int(cell_index), int(index), purpose))
    return int(ss.generate_state(1, dtype=np.uint32)[0])


# ======================================================================== verificación
def check_cell(cell: CellSpec, measures: dict, cfg: dict) -> str | None:
    """Devuelve ``None`` si el grafo cumple la celda; si no, el motivo de rechazo."""
    tol = os_tolerance(cell.n, cfg)
    if abs(measures["os"] - cell.os_target) > tol + 1e-12:
        return "os_out_of_tolerance"
    if cell.structure == "chain":
        need = cell.chain_share if cell.chain_share is not None else cfg["structures"]["chain_min_share_core"]
        if measures["chain_share"] + 1e-12 < need:
            return "chain_share_below_target"
    if cell.structure == "bottleneck":
        dmin = bottleneck_min_degree(cell.n, cfg)
        ok = sum(1 for d in measures["bottleneck_degrees"] if d >= dmin)
        if ok < max(1, cell.n_bottlenecks or 1):
            return "bottlenecks_missing"
    return None


# ========================================================================== generar
def generate(cell: CellSpec, seed: int, config: dict | None = None, index: int = 0,
             skip_hashes: set[str] | None = None) -> Instance:
    """Genera una instancia de la celda. Reintenta con ``seed + k`` si la instancia no cumple
    la celda o ya existe (``skip_hashes``)."""
    cfg = resolve_config(config)
    rejections: Counter = Counter()
    max_attempts = int(cfg["max_attempts"])
    tol = os_tolerance(cell.n, cfg)
    t_lo, t_hi = time_bounds(cell.cycle_time, cfg["times"])
    t0 = time.perf_counter()
    for attempt in range(max_attempts):
        s = int(seed) + attempt
        rng = np.random.default_rng(s)
        params = _resolve_structure(cell, rng, cfg)
        n_stages = n_stages_for(cell.n, cell.os_target, cfg, cell.structure)
        spec = GraphSpec(
            n=cell.n,
            os_target=cell.os_target,
            os_tolerance=tol,
            n_stages=n_stages,
            chain_share=params.chain_share or 0.0,
            n_bottlenecks=params.n_bottlenecks or 0,
            bottleneck_degree=params.bottleneck_degree or 0,
            max_direct_successors=cfg.get("max_direct_successors"),
            max_chain_length=cfg.get("max_chain_length"),
        )
        try:
            graph = generate_graph(spec, rng)
        except GraphGenerationError as exc:
            rejections[str(exc)] += 1
            continue
        if not graph.reached:
            rejections["os_above_after_anchoring" if graph.os > cell.os_target else "os_below_target"] += 1
            continue
        measures = graph_measures(cell.n, graph.arcs)
        reason = check_cell(params, measures, cfg)
        if reason:
            rejections[reason] += 1
            continue
        times = sample_times(cell.n, cell.time_dist, cell.cycle_time, rng, cfg["times"])
        if any(t < t_lo or t > t_hi for t in times):
            rejections["times_out_of_range"] += 1
            continue
        inst = Instance(instance_id_for(cell, index, int(cfg["version"])), cell.n, cell.cycle_time,
                        tuple(times), tuple(graph.arcs))
        if validate_instance(inst):
            rejections["invalid_instance"] += 1
            continue
        h = content_hash(inst)
        if skip_hashes is not None and h in skip_hashes:
            rejections["duplicate"] += 1
            continue
        meta = {
            "source": "generator",
            "generator": "SALBPGen-py",
            "generator_version": int(cfg["version"]),
            "layer": cell.layer,
            "cell_id": cell.cell_id,
            "seed": s,
            "base_seed": int(seed),
            "attempts": attempt + 1,
            "rejections": dict(rejections),
            "os_target": cell.os_target,
            "os_tolerance": tol,
            "structure": cell.structure,
            "time_dist": cell.time_dist,
            "chain_share_target": params.chain_share,
            "n_bottlenecks_target": params.n_bottlenecks,
            "bottleneck_degree_target": params.bottleneck_degree,
            "n_stages_planned": graph.n_stages_planned,
            "n_stages_used": graph.n_stages_used,
            "os": round(measures["os"], 6),
            "chain_share": round(measures["chain_share"], 6),
            "n_bottlenecks": measures["n_bottlenecks"],
            "bottleneck_degrees": measures["bottleneck_degrees"],
            "n_arcs": measures["n_arcs"],
            "n_stages": measures["n_stages"],
            "content_hash": h,
            "seconds": round(time.perf_counter() - t0, 6),
        }
        return Instance(inst.instance_id, inst.n, inst.cycle_time, inst.times, inst.precedences, meta)
    raise GenerationError(
        f"celda {cell.cell_id} (semilla {seed}): sin instancia válida en {max_attempts} intentos; "
        f"rechazos: {dict(rejections)}"
    )


def generate_batch(n_core_per_cell: int, n_extended: int, master_seed: int,
                   config: dict | None = None, sizes=None) -> Iterator[Instance]:
    """Genera ``n_core_per_cell`` instancias por celda del núcleo y ``n_extended`` de la capa
    ampliada. Descarta duplicados exactos (mismo grafo y mismos tiempos)."""
    cfg = resolve_config(config)
    all_sizes = list(cfg["sizes"])
    sizes = list(sizes or all_sizes)
    seen: set[str] = set()
    for cell_index, cell in enumerate(core_cells(all_sizes, int(cfg["cycle_time"]))):
        if cell.n not in sizes:
            continue
        for k in range(n_core_per_cell):
            seed = derive_seed(master_seed, "core", cell_index, k)
            inst = generate(cell, seed, cfg, index=k, skip_hashes=seen)
            seen.add(inst.meta["content_hash"])
            yield inst
    for k in range(n_extended):
        cell_rng = np.random.default_rng(derive_seed(master_seed, "extended", 0, k, purpose=0))
        cell = sample_extended_cell(cell_rng, cfg, sizes)
        seed = derive_seed(master_seed, "extended", 0, k, purpose=1)
        inst = generate(cell, seed, cfg, index=k, skip_hashes=seen)
        seen.add(inst.meta["content_hash"])
        yield inst


def cell_from_meta(meta: dict, n: int, cycle_time: int = 1000) -> CellSpec:
    """Reconstruye la ``CellSpec`` a partir del ``meta`` de una instancia generada."""
    return CellSpec(
        n=n, os_target=meta["os_target"], structure=meta["structure"], time_dist=meta["time_dist"],
        layer=meta["layer"], chain_share=meta.get("chain_share_target"),
        n_bottlenecks=meta.get("n_bottlenecks_target"),
        bottleneck_degree=meta.get("bottleneck_degree_target"), cycle_time=cycle_time,
    )


def cell_to_dict(cell: CellSpec) -> dict:
    return asdict(cell)
