"""Prueba piloto de F2A (§4.7) sobre instancias generadas por F2B (o sobre una carpeta de instancias).

Calcula, por tamaño: K promedio por regla, SBS, cóctel y *rollout*; fracción de instancias en que el
*rollout* mejora al cóctel; empate total y tamaño del conjunto óptimo; estados de decisión; tiempos;
y una estimación del tiempo y disco que necesitará F3A. Escribe ``reports/F2A_piloto.md``.

Uso::

    python scripts/pilot_f2a.py --per-size 100            # instancias generadas (núcleo, celdas al azar)
    python scripts/pilot_f2a.py --instances-dir data/external/scholl   # instancias .alb/.json propias
"""

from __future__ import annotations

import argparse
import datetime as _dt
from pathlib import Path
import sys
import time

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from salbp_selector.core import RULE_IDS, load_instance, run_cocktail, run_rollout  # noqa: E402
from salbp_selector.gen import core_cells, derive_seed, generate, load_config  # noqa: E402
from salbp_selector.gen.validate import md_table  # noqa: E402


def generated_instances(per_size: int, seed: int, cfg: dict):
    cells = core_cells(cfg["sizes"], int(cfg["cycle_time"]))
    for n in cfg["sizes"]:
        cn = [(ci, c) for ci, c in enumerate(cells) if c.n == n]
        for k in range(per_size):
            ci, cell = cn[k % len(cn)]  # recorre las 21 celdas del tamaño en orden
            yield generate(cell, derive_seed(seed, "core", ci, 10_000 + k), cfg, index=10_000 + k)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-size", type=int, default=100)
    ap.add_argument("--instances-dir", default=None)
    ap.add_argument("--seed", type=int, default=20261116)
    ap.add_argument("--out", default=str(ROOT / "reports" / "F2A_piloto.md"))
    args = ap.parse_args(argv)
    cfg = load_config(ROOT / "configs" / "generator.yaml")

    if args.instances_dir:
        files = [p for p in Path(args.instances_dir).rglob("*") if p.suffix.lower() in (".alb", ".json")]
        insts = [load_instance(p) for p in sorted(files)]
        source = f"carpeta `{args.instances_dir}` ({len(insts)} instancias)"
    else:
        insts = list(generated_instances(args.per_size, args.seed, cfg))
        source = f"generador F2B, {args.per_size} instancias por tamaño repartidas entre las 21 celdas del núcleo"

    rows = []
    t_start = time.perf_counter()
    for k, inst in enumerate(insts, 1):
        c = run_cocktail(inst)
        sol, recs = run_rollout(inst, record=True)
        picks_same = inst.n - len(recs)
        row = {"instance_id": inst.instance_id, "n": inst.n, "LB1": inst.lb1, "K_cocktail": c["K_min"],
               "K_rollout": sol.K, "n_best": len(c["best_rules"]), "decision_states": len(recs),
               "decision_frac": len(recs) / inst.n, "non_decision": picks_same,
               "sec_rule_mean": np.mean(list(c["seconds"].values())), "sec_cocktail": c["seconds_total"],
               "sec_rollout": sol.seconds}
        row.update({f"K_r{r}": c["K"][r] for r in RULE_IDS})
        rows.append(row)
        if k % 50 == 0:
            print(f"  {k}/{len(insts)} ({time.perf_counter() - t_start:.0f} s)", flush=True)
    df = pd.DataFrame(rows)
    kcols = [f"K_r{r}" for r in RULE_IDS]

    summary = []
    for n, g in df.groupby("n"):
        means = g[kcols].mean()
        sbs = means.idxmin()
        summary.append({
            "n": n, "instancias": len(g), "SBS": sbs.replace("K_r", "R"), "K_SBS": means.min(),
            "K_cóctel": g["K_cocktail"].mean(), "K_rollout": g["K_rollout"].mean(),
            "% otro supera al SBS": 100 * (g["K_cocktail"] < g[sbs]).mean(),
            "% rollout < cóctel": 100 * (g["K_rollout"] < g["K_cocktail"]).mean(),
            "Δ medio rollout−cóctel": (g["K_rollout"] - g["K_cocktail"]).mean(),
            "% empate total": 100 * (g["n_best"] == 12).mean(),
            "estados de decisión/inst.": g["decision_states"].mean(),
            "% estados de decisión": 100 * g["decision_frac"].mean(),
            "ms por regla": 1000 * g["sec_rule_mean"].mean(),
            "ms cóctel": 1000 * g["sec_cocktail"].mean(),
            "ms rollout": 1000 * g["sec_rollout"].mean(),
        })
    summ = pd.DataFrame(summary)
    per_rule = df.groupby("n")[kcols].mean().reset_index()
    opt_size = df.groupby("n")["n_best"].value_counts().unstack(fill_value=0).reset_index()

    # Estimación de F3A: 50 por celda × 63 + 3150 ampliadas = 6300 instancias (repartidas por igual por tamaño)
    n_f3a = 6300
    t_by_n = df.groupby("n")["sec_rollout"].mean() + df.groupby("n")["sec_cocktail"].mean()
    est_hours_1core = float(t_by_n.mean() * n_f3a / 3600)
    states_per = float(df["decision_states"].mean())
    est_disk_mb = n_f3a * (2.0 + states_per * 0.6) / 1024  # ~2 KB por instancia + ~0,6 KB por estado (≈ 70 columnas)

    lines = [
        "# F2A · Prueba piloto del motor, las 12 reglas y el rollout\n",
        f"Generado por `scripts/pilot_f2a.py` el {_dt.datetime.now():%Y-%m-%d %H:%M}. Fuente: {source}. "
        f"Desempate: menor número de tarea (P1). Tiempo total: {time.perf_counter() - t_start:.0f} s.\n",
        "## Resumen por tamaño\n", md_table(summ),
        "\n## K promedio por regla\n", md_table(per_rule),
        "\n## Tamaño del conjunto óptimo (número de instancias por tamaño del conjunto)\n", md_table(opt_size),
        "\n## Estimación para F3A\n",
        f"- Instancias previstas: {n_f3a} (50 por celda del núcleo + 3150 ampliadas).\n",
        f"- Tiempo de etiquetado (cóctel + rollout) en un núcleo: ≈ {est_hours_1core:.2f} h; "
        f"con 8 núcleos (joblib): ≈ {est_hours_1core / 8:.2f} h.\n",
        f"- Estados de decisión por instancia: {states_per:.1f} → ≈ {states_per * n_f3a:,.0f} estados.\n",
        f"- Disco estimado (instancias + estados, sin comprimir): ≈ {est_disk_mb:,.0f} MB (presupuesto: 10 GB).\n",
        "\n## Pendiente\n",
        "- Repetir con al menos 30 instancias de Scholl (`--instances-dir data/external/scholl`) cuando estén "
        "disponibles, y ejecutar `pytest -m slow tests/core/test_cocktail_table.py` para la reproducción de "
        "la tabla del cóctel.\n",
    ]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    df.to_csv(out.with_suffix(".csv"), index=False)
    print(summ.to_string(index=False))
    print(f"Informe: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
