"""Validación del generador (F2B §4.6) y redacción de ``reports/F2B_validacion_generador.md``.

1. Cumplimiento de celda (criterio 100 %).
2. Parecido estructural con el conjunto público de Otto et al. (requiere sus archivos ``.alb``).
3. Parecido en desempeño (K promedio por regla) con el conjunto público.
4. Discriminación entre reglas por celda (empate total y brecha SBS–cóctel).
5. Cobertura de la capa ampliada (histogramas, sin huecos).
6. Reproducibilidad (*hash* idéntico al generar dos veces con la misma semilla).

Uso::

    python -m salbp_selector.gen.validate --per-cell 100 --extended 2000 \
        [--public-dir data/external/otto2013 --cell-map data/external/otto2013/cells.csv]
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import datetime as _dt
from pathlib import Path
import tempfile
import time

import numpy as np
import pandas as pd

from ..core.engine import run_cocktail
from ..core.instance import Instance
from ..core.io import file_sha256, load_instance, validate_instance, write_jsonl_gz
from ..core.rules import RULE_IDS
from .generator import (
    CellSpec, bottleneck_min_degree, check_cell, core_cells, derive_seed, generate,
    generate_batch, load_config, os_tolerance, resolve_config,
)
from .graphs import graph_measures
from .times import time_bounds

MEASURES = ["os", "mean_in_degree", "mean_out_degree", "n_arcs", "n_stages", "chain_share",
            "t_mean", "t_sd", "lb1"]


# ============================================================================ medidas
def instance_measures(inst: Instance) -> dict:
    g = graph_measures(inst.n, inst.precedences)
    t = np.array(inst.times, dtype=float) / inst.cycle_time
    return {
        "instance_id": inst.instance_id, "n": inst.n, **{k: g[k] for k in (
            "os", "mean_in_degree", "mean_out_degree", "mean_degree", "n_arcs", "n_stages",
            "chain_share", "n_bottlenecks")},
        "max_bn_degree": max(g["bottleneck_degrees"], default=0),
        "t_mean": float(t.mean()), "t_sd": float(t.std(ddof=1)) if t.size > 1 else 0.0,
        "lb1": inst.lb1,
    }


# ===================================================================== 1. cumplimiento
def compliance_check(inst: Instance, cell: CellSpec, cfg: dict) -> list[str]:
    """Comprobación independiente del cumplimiento de la celda (recalcula todo desde los arcos)."""
    errs = validate_instance(inst)
    g = graph_measures(inst.n, inst.precedences)
    reason = check_cell(cell, g, cfg)
    if reason:
        errs.append(reason)
    lo, hi = time_bounds(inst.cycle_time, cfg["times"])
    if any(t < lo or t > hi for t in inst.times):
        errs.append("times_out_of_range")
    return errs


def run_compliance(per_cell: int, master_seed: int, cfg: dict, sizes=None):
    rows, by_cell = [], {}
    for ci, cell in enumerate(core_cells(cfg["sizes"], int(cfg["cycle_time"]))):
        if sizes and cell.n not in sizes:
            continue
        insts, ok, attempts = [], 0, 0
        t0 = time.perf_counter()
        for k in range(per_cell):
            inst = generate(cell, derive_seed(master_seed, "core", ci, k), cfg, index=k)
            insts.append(inst)
            attempts += inst.meta["attempts"]
            # la celda real (con los parámetros de estructura que resolvió el generador)
            real = CellSpec(cell.n, cell.os_target, cell.structure, cell.time_dist, "core",
                            inst.meta["chain_share_target"], inst.meta["n_bottlenecks_target"],
                            inst.meta["bottleneck_degree_target"], cell.cycle_time)
            ok += not compliance_check(inst, real, cfg)
        secs = time.perf_counter() - t0
        os_v = np.array([i.meta["os"] for i in insts])
        rows.append({
            "cell": cell.cell_id, "n": cell.n, "structure": cell.structure, "os_target": cell.os_target,
            "time_dist": cell.time_dist, "instances": len(insts), "compliance_pct": 100.0 * ok / len(insts),
            "os_mean": os_v.mean(), "os_min": os_v.min(), "os_max": os_v.max(),
            "chain_share_mean": np.mean([i.meta["chain_share"] for i in insts]),
            "n_bn_mean": np.mean([i.meta["n_bottlenecks"] for i in insts]),
            "rejection_rate": 1 - len(insts) / attempts, "ms_per_instance": 1000 * secs / len(insts),
        })
        by_cell[cell.cell_id] = insts
    return pd.DataFrame(rows), by_cell


# ==================================================================== 4. discriminación
def cocktail_table(instances: list[Instance]) -> pd.DataFrame:
    rows = []
    for inst in instances:
        res = run_cocktail(inst)
        row = {"instance_id": inst.instance_id, "n": inst.n, "cell": inst.meta.get("cell_id", ""),
               "LB1": inst.lb1, "K_cocktail": res["K_min"], "n_best": len(res["best_rules"])}
        row.update({f"K_r{r}": res["K"][r] for r in RULE_IDS})
        rows.append(row)
    return pd.DataFrame(rows)


def discrimination(perf: pd.DataFrame) -> pd.DataFrame:
    kcols = [f"K_r{r}" for r in RULE_IDS]
    rows = []
    for cell, g in perf.groupby("cell", sort=False):
        means = g[kcols].mean()
        sbs = int(means.idxmin()[3:])
        rows.append({
            "cell": cell, "instances": len(g),
            "tie_all_pct": 100.0 * (g["n_best"] == 12).mean(),
            "sbs_rule": f"R{sbs}", "K_sbs": means.min(), "K_cocktail": g["K_cocktail"].mean(),
            "gap_sbs_cocktail": means.min() - g["K_cocktail"].mean(),
            "pct_other_beats_sbs": 100.0 * (g["K_cocktail"] < g[f"K_r{sbs}"]).mean(),
            "mean_opt_set_size": g["n_best"].mean(),
            "flag_tie_gt_90": bool((g["n_best"] == 12).mean() > 0.9),
        })
    return pd.DataFrame(rows)


# ======================================================================== 5. cobertura
def extended_coverage(n_ext: int, master_seed: int, cfg: dict, fig_dir: Path | None):
    insts = list(generate_batch(0, n_ext, master_seed, cfg))
    df = pd.DataFrame([{**i.meta, "n": i.n} for i in insts])
    checks = []

    def gaps(values, lo, hi, bins=10):
        if len(values) == 0:
            return bins
        h, _ = np.histogram(values, bins=bins, range=(lo, hi))
        return int((h == 0).sum())

    ext = cfg["extended"]
    for struct, (lo, hi) in ext["os_range"].items():
        v = df.loc[df.structure == struct, "os"].to_numpy()
        checks.append({"measure": f"OS ({struct})", "range": f"[{lo}, {hi}]", "instances": len(v),
                       "min": v.min() if len(v) else np.nan, "max": v.max() if len(v) else np.nan,
                       "empty_bins_of_10": gaps(v, lo, hi)})
    for struct, (lo, hi) in ext["chain_share_range"].items():
        v = df.loc[df.structure == struct, "chain_share_target"].astype(float).to_numpy()
        checks.append({"measure": f"cadenas objetivo ({struct})", "range": f"[{lo}, {hi}]", "instances": len(v),
                       "min": v.min() if len(v) else np.nan, "max": v.max() if len(v) else np.nan,
                       "empty_bins_of_10": gaps(v, lo, hi)})
    bn = df[df.structure == "bottleneck"]
    for n, g in bn.groupby("n"):
        rng_ = cfg["structures"]["bottleneck"]["degree_range"]
        lo, hi = rng_.get(n, rng_.get(str(n), rng_["default"]))
        v = g["bottleneck_degree_target"].astype(int).to_numpy()
        checks.append({"measure": f"grado cuello de botella (n={n})", "range": f"[{lo}, {hi}]",
                       "instances": len(v), "min": v.min(), "max": v.max(),
                       "empty_bins_of_10": int(len(set(range(lo, hi + 1)) - set(v.tolist())))})
    if fig_dir is not None:
        _coverage_figure(df, fig_dir / "F2B_cobertura_ampliada.png")
    rej = df.groupby(["n", "structure"]).apply(
        lambda g: 1 - len(g) / g["attempts"].sum(), include_groups=False).rename("rejection_rate").reset_index()
    return pd.DataFrame(checks), rej, insts


def _coverage_figure(df: pd.DataFrame, path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(1, 3, figsize=(13, 3.6))
    for struct in ("mixed", "chain", "bottleneck"):
        ax[0].hist(df.loc[df.structure == struct, "os"], bins=28, range=(0.2, 0.9), alpha=0.6, label=struct)
    ax[0].set(title="OS medido", xlabel="OS", ylabel="instancias")
    ax[0].legend()
    for struct in ("chain", "mixed"):
        ax[1].hist(df.loc[df.structure == struct, "chain_share"], bins=24, range=(0, 0.8), alpha=0.6, label=struct)
    ax[1].set(title="Fracción de tareas en cadenas (medida)", xlabel="fracción")
    ax[1].legend()
    bn = df[df.structure == "bottleneck"]
    for n, g in bn.groupby("n"):
        ax[2].hist(g["bottleneck_degree_target"].astype(int), bins=np.arange(3.5, 15.5, 1), alpha=0.6, label=f"n={n}")
    ax[2].set(title="Grado de los cuellos de botella", xlabel="grado")
    ax[2].legend()
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


# ===================================================================== 6. reproducibilidad
def reproducibility(master_seed: int, cfg: dict, per_cell: int = 1, n_ext: int = 50) -> dict:
    hashes = []
    with tempfile.TemporaryDirectory() as tmp:
        for k in range(2):
            p = Path(tmp) / f"run{k}.jsonl.gz"
            # se quita "seconds" de meta: es tiempo de reloj, no contenido
            insts = []
            for i in generate_batch(per_cell, n_ext, master_seed, cfg):
                meta = {kk: v for kk, v in i.meta.items() if kk != "seconds"}
                insts.append(Instance(i.instance_id, i.n, i.cycle_time, i.times, i.precedences, meta))
            write_jsonl_gz(insts, p)
            hashes.append(file_sha256(p))
    return {"hash_run1": hashes[0], "hash_run2": hashes[1], "identical": hashes[0] == hashes[1],
            "instances": per_cell * 63 + n_ext}


# ============================================================= 2 y 3. conjunto público
def load_public(public_dir: Path, cell_map: Path | None) -> list[Instance]:
    insts = [load_instance(p) for p in sorted(public_dir.rglob("*.alb"))]
    if cell_map and cell_map.exists():
        cm = pd.read_csv(cell_map).set_index("file")
        out = []
        for inst in insts:
            if inst.instance_id in cm.index:
                r = cm.loc[inst.instance_id]
                code = {"chain": "ch", "bottleneck": "bn", "mixed": "mix"}[r["structure"]]
                cell = f"n{inst.n}-os{int(round(float(r['os']) * 10)):02d}-{code}-{r['time_dist']}"
                inst = Instance(inst.instance_id, inst.n, inst.cycle_time, inst.times, inst.precedences,
                                {**inst.meta, "cell_id": cell})
            out.append(inst)
        insts = out
    return insts


def compare_with_public(own: list[Instance], public: list[Instance]) -> pd.DataFrame:
    from scipy.stats import ks_2samp

    o = pd.DataFrame([{**instance_measures(i), "cell": i.meta.get("cell_id", "")} for i in own])
    p = pd.DataFrame([{**instance_measures(i), "cell": i.meta.get("cell_id", "")} for i in public])
    key = "cell" if (p["cell"] != "").any() else "n"
    rows = []
    for gval, pg in p.groupby(key):
        og = o[o[key] == gval]
        if og.empty:
            continue
        for m in MEASURES:
            q1, q3 = pg[m].quantile([0.25, 0.75])
            mean_own = og[m].mean()
            rows.append({key: gval, "measure": m, "public_q1": q1, "public_q3": q3,
                         "public_mean": pg[m].mean(), "own_mean": mean_own,
                         "inside_iqr": bool(q1 - 1e-12 <= mean_own <= q3 + 1e-12),
                         "ks_p": ks_2samp(og[m], pg[m]).pvalue})
    return pd.DataFrame(rows)


# ============================================================================ informe
def md_table(df: pd.DataFrame, floatfmt: str = ".3f") -> str:
    if df is None or df.empty:
        return "_(sin datos)_\n"
    cols = list(df.columns)
    lines = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            if isinstance(v, (float, np.floating)):
                cells.append(format(float(v), floatfmt))
            else:
                cells.append(str(v))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def write_report(path: Path, ctx: dict) -> None:
    comp, disc, cov, cov_rej, rep = ctx["compliance"], ctx["discrimination"], ctx["coverage"], ctx["coverage_rej"], ctx["repro"]
    perf_n = ctx["perf_by_n"]
    ok_all = bool((comp["compliance_pct"] == 100).all())
    rej_big = comp[(comp.n >= 50)]["rejection_rate"].max()
    s = [f"# F2B · Validación del generador de instancias\n",
         f"Generado automáticamente por `python -m salbp_selector.gen.validate` el "
         f"{_dt.datetime.now():%Y-%m-%d %H:%M}. Semilla maestra {ctx['master_seed']}; "
         f"{ctx['per_cell']} instancias por celda del núcleo; {ctx['n_ext']} de la capa ampliada; "
         f"tiempo total {ctx['seconds']:.0f} s.\n",
         "## Resumen de criterios\n",
         "| Criterio | Resultado |", "|---|---|",
         f"| 1. Cumplimiento de celda (100 %) | {'CUMPLE' if ok_all else 'NO CUMPLE'} (mínimo {comp['compliance_pct'].min():.1f} %) |",
         f"| Tasa de rechazo < 50 % en n = 50 y 100 | {'CUMPLE' if rej_big < 0.5 else 'NO CUMPLE'} (máximo {100 * rej_big:.1f} %) |",
         f"| 2. Parecido estructural con el conjunto público | {ctx['public_status']} |",
         f"| 3. Parecido en desempeño con el conjunto público | {ctx['public_status']} |",
         f"| 4. Discriminación entre reglas | {int(disc['flag_tie_gt_90'].sum())} celdas con empate total > 90 % |",
         f"| 5. Cobertura de la capa ampliada | {int((cov['empty_bins_of_10'] > 0).sum())} medidas con huecos |",
         f"| 6. Reproducibilidad | {'CUMPLE' if rep['identical'] else 'NO CUMPLE'} (SHA-256 `{rep['hash_run1'][:16]}…`) |",
         "",
         "## 1. Cumplimiento de celda y tasa de rechazo\n",
         "Comprobación independiente: se recalculan OS, cadenas y cuellos de botella desde los arcos, "
         "se valida la instancia (`validate_instance`) y se comprueba que los tiempos estén en [0,02c; c].\n",
         md_table(comp),
         "\n## 2 y 3. Comparación con el conjunto público de Otto et al.\n"]
    if ctx.get("public_cmp") is not None and not ctx["public_cmp"].empty:
        s += [md_table(ctx["public_cmp"]), "\n", md_table(ctx.get("public_perf"))]
    else:
        s += ["Pendiente: no se encontró el conjunto público. Descargar las instancias SALBP de "
              "Otto et al. (2013) de `assembly-line-balancing.de`, copiar los `.alb` en "
              "`data/external/otto2013/` (y, si se tiene, un `cells.csv` con columnas "
              "`file,os,structure,time_dist`) y repetir con `--public-dir`. De esta comparación salen "
              "las desviaciones definitivas de PB y PM.\n"]
    s += ["\nK promedio por regla en las instancias propias del núcleo, por tamaño (referencia para el paso 3):\n",
          md_table(perf_n),
          "\n## 4. Discriminación entre reglas por celda\n",
          "SBS de la celda = regla con menor K promedio en la celda. Se marca la celda si el empate total "
          "(las 12 reglas con el mismo K) supera el 90 %.\n",
          md_table(disc),
          "\n## 5. Cobertura de la capa ampliada\n",
          md_table(cov), "\nTasa de rechazo en la capa ampliada por tamaño y estructura:\n", md_table(cov_rej),
          "\n![Cobertura de la capa ampliada](figures/F2B_cobertura_ampliada.png)\n",
          "\n## 6. Reproducibilidad\n",
          f"Se generó dos veces el mismo lote ({rep['instances']} instancias) con la semilla "
          f"{ctx['master_seed']} y se compararon los archivos `.jsonl.gz`:\n\n"
          f"- ejecución 1: `{rep['hash_run1']}`\n- ejecución 2: `{rep['hash_run2']}`\n- idénticos: **{rep['identical']}**\n",
          "\n## Supuestos y desviaciones documentadas\n",
          "- Número de etapas: modo `auto` (S = 1 + f·OS·(n − 1)) mientras no se copien los valores de la "
          "Tabla 5 del artículo en `configs/generator.yaml` (`stages.fixed`).\n",
          "- Longitud máxima de cadena = 5 (supuesto medido: cadenas más largas impiden alcanzar OS 0,6).\n",
          "- Desviaciones de PB (0,15c) y PM (0,05c): supuestos pendientes de contrastar con el conjunto público.\n",
          "- Núcleo BN: el número de cuellos de botella se sortea entre el 1 % y el 6 % de las tareas y el grado "
          "en [8, 14] ([4, 8] para n = 20), igual que en la capa ampliada.\n",
          "- No se implementan módulos ni tareas aisladas (no los necesita el conjunto de referencia).\n"]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(s), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m salbp_selector.gen.validate")
    ap.add_argument("--config", default="configs/generator.yaml")
    ap.add_argument("--per-cell", type=int, default=100)
    ap.add_argument("--extended", type=int, default=2000)
    ap.add_argument("--master-seed", type=int, default=None)
    ap.add_argument("--public-dir", default=None)
    ap.add_argument("--cell-map", default=None)
    ap.add_argument("--out", default="reports")
    args = ap.parse_args(argv)

    cfg_path = Path(args.config)
    cfg = load_config(cfg_path) if cfg_path.exists() else resolve_config()
    seed = args.master_seed if args.master_seed is not None else int(cfg["master_seed"])
    out = Path(args.out)
    t0 = time.perf_counter()

    print("1. Cumplimiento de celda…", flush=True)
    comp, by_cell = run_compliance(args.per_cell, seed, cfg)
    print("4. Discriminación entre reglas (12 reglas por instancia)…", flush=True)
    own = [i for v in by_cell.values() for i in v]
    perf = cocktail_table(own)
    disc = discrimination(perf)
    kcols = [f"K_r{r}" for r in RULE_IDS]
    perf_n = perf.groupby("n")[kcols + ["K_cocktail", "LB1"]].mean().reset_index()
    print("5. Cobertura de la capa ampliada…", flush=True)
    cov, cov_rej, _ = extended_coverage(args.extended, seed + 1, cfg, out / "figures")
    print("6. Reproducibilidad…", flush=True)
    rep = reproducibility(seed, cfg)

    ctx = {"compliance": comp, "discrimination": disc, "coverage": cov, "coverage_rej": cov_rej,
           "repro": rep, "perf_by_n": perf_n, "master_seed": seed, "per_cell": args.per_cell,
           "n_ext": args.extended, "public_status": "PENDIENTE (falta el conjunto público)"}
    if args.public_dir and Path(args.public_dir).exists():
        print("2-3. Comparación con el conjunto público…", flush=True)
        public = load_public(Path(args.public_dir), Path(args.cell_map) if args.cell_map else None)
        ctx["public_cmp"] = compare_with_public(own, public)
        pperf = cocktail_table(public)
        ctx["public_perf"] = pd.concat([
            pperf.groupby("n")[kcols + ["K_cocktail"]].mean().assign(source="público"),
            perf.groupby("n")[kcols + ["K_cocktail"]].mean().assign(source="propio"),
        ]).reset_index()
        inside = ctx["public_cmp"]["inside_iqr"].mean() * 100
        ctx["public_status"] = f"{inside:.0f} % de las medias propias dentro del RIC público"
    ctx["seconds"] = time.perf_counter() - t0
    perf.to_csv(out / "F2B_desempeno_nucleo.csv", index=False) if out.exists() else None
    write_report(out / "F2B_validacion_generador.md", ctx)
    print(f"Informe escrito en {out / 'F2B_validacion_generador.md'} ({ctx['seconds']:.0f} s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
