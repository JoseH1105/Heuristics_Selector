"""Línea de comandos del generador.

Ejemplo (F2B §4.5)::

    python -m salbp_selector.gen --config configs/generator.yaml --core-per-cell 50 --extended 3150 --out data/raw/instances/

Escribe ``{out}/all/n{n}/core.jsonl.gz`` y ``{out}/all/n{n}/extended.jsonl.gz`` (la partición en
entrenamiento, validación y prueba la hace F3A) y ``{out}/generation_log.json`` con la
configuración, conteos, tasas de rechazo por celda y el *hash* SHA-256 de cada archivo.
Con ``--format json`` escribe además un archivo ``.json`` por instancia.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import datetime as _dt
import json
from pathlib import Path
import platform
import sys
import time

from .. import __version__
from ..core.io import file_sha256, save_instance, write_jsonl_gz
from .generator import generate_batch, load_config


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m salbp_selector.gen",
                                description="Generador de instancias de SALBP-1 (SALBPGen en Python)")
    p.add_argument("--config", default="configs/generator.yaml", help="archivo YAML de configuración")
    p.add_argument("--core-per-cell", type=int, default=50, help="instancias por celda del núcleo (63 celdas)")
    p.add_argument("--extended", type=int, default=3150, help="instancias de la capa ampliada")
    p.add_argument("--master-seed", type=int, default=None, help="semilla maestra (por defecto, la del YAML)")
    p.add_argument("--sizes", type=int, nargs="*", default=None, help="limitar a estos tamaños (p. ej. 20 50)")
    p.add_argument("--out", default="data/raw/instances/", help="carpeta de salida")
    p.add_argument("--format", choices=["jsonl", "json", "both"], default="jsonl",
                   help="jsonl.gz por tamaño y capa, un .json por instancia, o ambos")
    p.add_argument("--quiet", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    cfg_path = Path(args.config)
    cfg = load_config(cfg_path if cfg_path.exists() else None)
    if not cfg_path.exists():
        print(f"[aviso] no existe {cfg_path}; se usan los valores por defecto", file=sys.stderr)
    master_seed = args.master_seed if args.master_seed is not None else int(cfg["master_seed"])
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    groups: dict[tuple[int, str], list] = defaultdict(list)
    per_cell: dict[str, dict] = defaultdict(lambda: {"count": 0, "attempts": 0, "rejections": defaultdict(int)})
    total_expected = args.core_per_cell * 21 * len(args.sizes or cfg["sizes"]) + args.extended
    t0 = time.perf_counter()
    for k, inst in enumerate(generate_batch(args.core_per_cell, args.extended, master_seed, cfg, args.sizes), 1):
        groups[(inst.n, inst.meta["layer"])].append(inst)
        pc = per_cell[inst.meta["cell_id"]]
        pc["count"] += 1
        pc["attempts"] += inst.meta["attempts"]
        for r, c in inst.meta["rejections"].items():
            pc["rejections"][r] += c
        if args.format in ("json", "both"):
            save_instance(inst, out / "json" / f"n{inst.n}" / f"{inst.instance_id}.json")
        if not args.quiet and (k % 200 == 0 or k == total_expected):
            print(f"  {k}/{total_expected} instancias ({time.perf_counter() - t0:.1f} s)", flush=True)
    elapsed = time.perf_counter() - t0

    files = {}
    if args.format in ("jsonl", "both"):
        for (n, layer), insts in sorted(groups.items()):
            path = out / "all" / f"n{n}" / f"{layer}.jsonl.gz"
            write_jsonl_gz(insts, path)
            files[str(path.relative_to(out)).replace("\\", "/")] = {
                "count": len(insts), "sha256": file_sha256(path), "bytes": path.stat().st_size}

    log = {
        "created": _dt.datetime.now().isoformat(timespec="seconds"),
        "package_version": __version__,
        "python": platform.python_version(),
        "command": " ".join(sys.argv),
        "master_seed": master_seed,
        "core_per_cell": args.core_per_cell,
        "extended": args.extended,
        "sizes": args.sizes or cfg["sizes"],
        "seconds": round(elapsed, 2),
        "config": cfg,
        "files": files,
        "cells": {
            cid: {"count": v["count"], "attempts": v["attempts"],
                  "rejection_rate": round(1 - v["count"] / v["attempts"], 4) if v["attempts"] else 0.0,
                  "rejections": dict(v["rejections"])}
            for cid, v in sorted(per_cell.items())
        },
    }
    (out / "generation_log.json").write_text(json.dumps(log, indent=1, default=str), encoding="utf-8")
    n_total = sum(len(v) for v in groups.values())
    print(f"Generadas {n_total} instancias en {elapsed:.1f} s -> {out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
