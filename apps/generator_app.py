"""Generador de instancias SALBP-1: interfaz de apoyo (fuera del paquete).

Sirve para generar instancias del núcleo o de la capa ampliada, cargar instancias existentes
(.json, .alb, .IN2), ver el grafo por etapas, las tareas y los tiempos, resolver con las 12 reglas,
el cóctel y el rollout, y guardar o descargar el resultado.

Ejecutar desde la raíz del proyecto:

    streamlit run apps/generator_app.py
"""

from __future__ import annotations

from collections import Counter
from html import escape
from pathlib import Path
import random
import time

import matplotlib

matplotlib.use("Agg")
from matplotlib.colors import LinearSegmentedColormap, to_hex, to_rgb  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from salbp_selector.core import RULES, run_cocktail, run_rollout, run_rule, validate_instance  # noqa: E402
from salbp_selector.core.io import (  # noqa: E402
    instance_from_json, instance_to_alb, instance_to_json, parse_alb, parse_in2, save_instance,
    write_jsonl_gz,
)
from salbp_selector.gen import CellSpec, GenerationError, generate, load_config, os_tolerance  # noqa: E402
from salbp_selector.gen import sample_extended_cell  # noqa: E402
from salbp_selector.gen.generator import bottleneck_min_degree, check_cell  # noqa: E402
from salbp_selector.gen.graphs import graph_measures, levels  # noqa: E402
from salbp_selector.gen.times import time_bounds  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs" / "generator.yaml"

# ------------------------------------------------------------------------------ paleta
INK, MUTED, LINE, SURFACE = "#0F172A", "#64748B", "#E2E8F0", "#FFFFFF"
PRIMARY, PRIMARY_SOFT, PRIMARY_DARK = "#4F46E5", "#E0E7FF", "#3730A3"
TEAL, TEAL_SOFT = "#0D9488", "#CCFBF1"
AMBER, AMBER_SOFT = "#D97706", "#FEF3C7"
ROSE = "#E11D48"
NODE_FILL, NODE_LINE = "#F1F5F9", "#94A3B8"
STATION_COLORS = ["#6366F1", "#14B8A6", "#F59E0B", "#F43F5E", "#0EA5E9",
                  "#8B5CF6", "#84CC16", "#F97316", "#64748B", "#EC4899"]
TIME_CMAP = LinearSegmentedColormap.from_list("time", ["#EEF2FF", "#A5B4FC", "#4F46E5", "#312E81"])

STRUCTURES = {"mixed": "MIXED", "chain": "CH", "bottleneck": "BN"}
STRUCT_HELP = {
    "mixed": "Sin requisito de estructura.",
    "chain": "Al menos el 40 % de las tareas en cadenas.",
    "bottleneck": "Con cuellos de botella de grado ≥ 8 (≥ 4 si n = 20).",
}
DISTS = {"pb": "PB", "bm": "BM", "pm": "PM"}
DIST_HELP = {
    "pb": "Pico inferior: casi todas las tareas son cortas.",
    "bm": "Bimodal: 85 % cortas y 15 % de unas 0,5c.",
    "pm": "Pico central: tiempos alrededor de 0,5c. Suele dar instancias difíciles.",
}
CORE_OS = {"mixed": [0.2, 0.6, 0.9], "chain": [0.2, 0.6], "bottleneck": [0.2, 0.6]}

st.set_page_config(page_title="Generador SALBP-1", page_icon=":material/account_tree:", layout="wide")

# Colores de tarjetas y bordes translúcidos y texto heredado: se leen bien con el tema claro del
# proyecto (.streamlit/config.toml) y también si Streamlit usa el tema oscuro del sistema.
UI_INK, UI_MUTED = "inherit", MUTED
UI_LINE, UI_SURFACE, UI_SUBTLE = "rgba(100,116,139,.22)", "rgba(148,163,184,.10)", "rgba(148,163,184,.07)"

CSS = f"""
<style>
.block-container {{padding-top: 1.4rem; padding-bottom: 3rem; max-width: 1440px;}}
h1, h2, h3 {{letter-spacing: -0.01em;}}
.step {{font-size: .72rem; font-weight: 700; color: {PRIMARY}; letter-spacing: .08em;
        text-transform: uppercase; margin: 1.1rem 0 .1rem;}}
.step-title {{font-size: .95rem; font-weight: 650; color: {UI_INK}; margin-bottom: .35rem;}}
.hero-id {{font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 1.45rem;
           font-weight: 650; color: {UI_INK}; margin: 0 0 .35rem; word-break: break-all;}}
.chips {{margin: .1rem 0 .8rem;}}
.chip {{display: inline-block; padding: 3px 11px; border-radius: 999px; font-size: .76rem;
        font-weight: 600; margin: 0 6px 6px 0; border: 1px solid transparent;}}
.chip-info {{background: {PRIMARY_SOFT}; color: {PRIMARY_DARK};}}
.chip-ok {{background: #DCFCE7; color: #166534;}}
.chip-bad {{background: #FFE4E6; color: #9F1239;}}
.chip-muted {{background: {UI_SURFACE}; color: {UI_MUTED}; border-color: {UI_LINE};}}
.kpi {{background: {UI_SURFACE}; border: 1px solid {UI_LINE}; border-radius: 14px; padding: 14px 16px 12px;
       height: 100%; box-shadow: 0 1px 2px rgba(15, 23, 42, .04);}}
.kpi .label {{font-size: .72rem; color: {UI_MUTED}; text-transform: uppercase; letter-spacing: .06em;
              font-weight: 600;}}
.kpi .value {{font-size: 1.7rem; font-weight: 700; color: {UI_INK}; line-height: 1.25; margin-top: 2px;}}
.kpi .sub {{font-size: .78rem; color: {UI_MUTED}; margin-top: 2px;}}
.osbar {{position: relative; height: 8px; background: {UI_LINE}; border-radius: 999px; margin: 9px 0 4px;}}
.osband {{position: absolute; top: 0; height: 8px; background: {PRIMARY_SOFT}; border-radius: 999px;}}
.osmark {{position: absolute; top: -4px; width: 4px; height: 16px; background: {PRIMARY}; border-radius: 2px;}}
.legend {{font-size: .8rem; color: {UI_INK}; margin: .2rem 0 .6rem;}}
.legend span.item {{margin-right: 16px; white-space: nowrap;}}
.legend span.dot {{display: inline-block; width: 11px; height: 11px; border-radius: 50%;
                   margin-right: 6px; vertical-align: -1px; border: 1.5px solid;}}
.empty {{background: {UI_SURFACE}; border: 1px solid {UI_LINE}; border-radius: 16px; padding: 26px 28px;}}
.empty h3 {{margin-top: 0;}}
.howto {{display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-top: 14px;}}
.howto div {{background: {UI_SUBTLE}; border: 1px solid {UI_LINE}; border-radius: 12px; padding: 14px;}}
.howto b {{color: {PRIMARY}; display: block; font-size: .75rem; letter-spacing: .06em;}}
.muted {{color: {UI_MUTED}; font-size: .85rem;}}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def get_config() -> dict:
    return load_config(CONFIG_PATH if CONFIG_PATH.exists() else None)


cfg = get_config()
C = int(cfg["cycle_time"])


# ================================================================================ utilidades
def soft(color: str, amount: float = 0.72) -> str:
    """Mezcla un color con blanco (amount = proporción de blanco)."""
    r, g, b = to_rgb(color)
    return to_hex((r + (1 - r) * amount, g + (1 - g) * amount, b + (1 - b) * amount))


def kpi(col, label: str, value, sub: str = "", extra_html: str = "") -> None:
    col.markdown(f'<div class="kpi"><div class="label">{escape(label)}</div>'
                 f'<div class="value">{value}</div>{extra_html}'
                 f'<div class="sub">{sub}</div></div>', unsafe_allow_html=True)


def chips(items: list[tuple[str, str]]) -> None:
    html = "".join(f'<span class="chip chip-{kind}">{escape(text)}</span>' for text, kind in items)
    st.markdown(f'<div class="chips">{html}</div>', unsafe_allow_html=True)


def legend(items: list[tuple[str, str, str]]) -> None:
    html = "".join(f'<span class="item"><span class="dot" style="background:{fill};border-color:{line}">'
                   f'</span>{escape(text)}</span>' for text, fill, line in items)
    st.markdown(f'<div class="legend">{html}</div>', unsafe_allow_html=True)


def style_axes(ax) -> None:
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color(LINE)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.grid(axis="x", color="#EEF2F7", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.xaxis.label.set_color(MUTED)
    ax.yaxis.label.set_color(MUTED)


def set_instance(inst, origin: str) -> None:
    st.session_state["inst"] = inst
    st.session_state["origin"] = origin
    for key in ("rollout", "batch", "focus_task"):
        st.session_state.pop(key, None)


def new_seed() -> None:
    st.session_state["seed"] = random.randint(0, 999_999)


def pick(label: str, options: list, default, fmt=str, key: str | None = None, help: str | None = None):
    """Control segmentado que nunca queda vacío."""
    value = st.segmented_control(label, options, default=default, format_func=fmt, key=key, help=help)
    return default if value is None else value


@st.cache_data(show_spinner=False, max_entries=64)
def cached_cocktail(inst_json: str) -> dict:
    return run_cocktail(instance_from_json(inst_json))


@st.cache_data(show_spinner=False, max_entries=64)
def cached_stations(inst_json: str, rule: int) -> list[list[int]]:
    return run_rule(instance_from_json(inst_json), rule).stations


# ================================================================================= gráficos
def graph_dot(inst, g: dict, mode: str, stations, show_times: bool, focus: int | None) -> str:
    lev = levels(inst.n, inst.precedences)
    chains, bns = set(g["chain_task_list"]), set(g["bottleneck_tasks"])
    station_of = {i: k for k, st_ in enumerate(stations or []) for i in st_}
    anc = desc = 0
    if focus:
        anc, desc = inst.pred_all[focus], inst.succ_all[focus]
    size = 0.5 if show_times else 0.36
    out = ["digraph G {",
           'graph [rankdir=LR, bgcolor="transparent", nodesep=0.18, ranksep=0.5, splines=true];',
           f'node [shape=circle, style=filled, fixedsize=true, width={size}, fontname="Helvetica", '
           f'fontsize=10, penwidth=1.4];',
           f'edge [color="#B6C2D2", arrowsize=0.55, penwidth=1.0];']
    for i in range(1, inst.n + 1):
        font = INK
        if focus:
            if i == focus:
                fill, line, font = PRIMARY, PRIMARY_DARK, "#FFFFFF"
            elif (anc >> i) & 1:
                fill, line = PRIMARY_SOFT, PRIMARY
            elif (desc >> i) & 1:
                fill, line = AMBER_SOFT, AMBER
            else:
                fill, line, font = "#F8FAFC", "#E2E8F0", "#94A3B8"
        elif mode == "Estación" and station_of:
            base = STATION_COLORS[station_of[i] % len(STATION_COLORS)]
            fill, line = soft(base, 0.55), base
        elif mode == "Tiempo":
            x = inst.t[i] / inst.cycle_time
            fill, line = to_hex(TIME_CMAP(x)), PRIMARY_DARK
            font = "#FFFFFF" if x > 0.45 else INK
        else:
            if i in bns:
                fill, line = AMBER_SOFT, AMBER
            elif i in chains:
                fill, line = TEAL_SOFT, TEAL
            else:
                fill, line = NODE_FILL, NODE_LINE
        label = f"{i}\\n{inst.t[i]}" if show_times else str(i)
        tip = f"Tarea {i} | t = {inst.t[i]} | etapa {lev[i]} | NS = {inst.ns[i]}"
        out.append(f'{i} [label="{label}", fillcolor="{fill}", color="{line}", fontcolor="{font}", '
                   f'tooltip="{tip}"];')
    by_level: dict[int, list[int]] = {}
    for i in range(1, inst.n + 1):
        by_level.setdefault(lev[i], []).append(i)
    out += ["{rank=same; " + " ".join(map(str, nodes)) + ";}" for nodes in by_level.values()]
    up_set = anc | (1 << focus) if focus else 0
    down_set = desc | (1 << focus) if focus else 0
    for i, j in inst.precedences:
        if not focus:
            out.append(f"{i} -> {j};")
        elif (up_set >> i) & 1 and (up_set >> j) & 1:
            out.append(f'{i} -> {j} [color="{PRIMARY}", penwidth=1.6];')
        elif (down_set >> i) & 1 and (down_set >> j) & 1:
            out.append(f'{i} -> {j} [color="{AMBER}", penwidth=1.6];')
        else:
            out.append(f'{i} -> {j} [color="#E2E8F0"];')
    out.append("}")
    return "\n".join(out)


def fig_times(inst):
    x = np.array(inst.times) / inst.cycle_time
    fig, ax = plt.subplots(figsize=(7, 2.9))
    bins = np.linspace(0, 1, 26)
    counts, edges, patches = ax.hist(x, bins=bins, color=PRIMARY, edgecolor="white", linewidth=1)
    for p, left in zip(patches, edges[:-1]):
        p.set_facecolor(TIME_CMAP(0.25 + 0.7 * left))
    ax.axvline(x.mean(), color=ROSE, lw=1.4, ls="--")
    ax.text(x.mean(), ax.get_ylim()[1] * 0.95, f"  media {x.mean():.2f}", color=ROSE, fontsize=9, va="top")
    ax.set_xlabel("t_i / c")
    ax.set_ylabel("tareas")
    ax.set_xlim(0, 1)
    style_axes(ax)
    ax.grid(axis="y", color="#EEF2F7")
    fig.tight_layout()
    return fig


def fig_rules(res: dict, lb1: int):
    rules = list(RULES)
    ks = [res["K"][r] for r in rules]
    best = set(res["best_rules"])
    fig, ax = plt.subplots(figsize=(7, 3.9))
    y = np.arange(len(rules))[::-1]
    lo = min(lb1, min(ks)) - 1
    for yi, r, k in zip(y, rules, ks):
        color = PRIMARY if r in best else "#94A3B8"
        ax.hlines(yi, lo, k, color=soft(color, 0.55), lw=3)
        ax.plot(k, yi, "o", color=color, ms=9, zorder=3)
        ax.text(k + 0.12, yi, str(k), va="center", fontsize=9, color=INK if r in best else MUTED)
    ax.axvline(lb1, color=ROSE, ls="--", lw=1.3)
    ax.text(lb1, len(rules) - 0.2, " LB1", color=ROSE, fontsize=9, va="bottom")
    ax.set_yticks(y, [f"{RULES[r].code}  {RULES[r].name}" for r in rules])
    ax.set_xlim(lo, max(ks) + 1)
    ax.xaxis.get_major_locator().set_params(integer=True)
    ax.set_xlabel("estaciones K")
    style_axes(ax)
    fig.tight_layout()
    return fig


def fig_stations(inst, stations):
    k = len(stations)
    fig, ax = plt.subplots(figsize=(8, max(2.2, 0.42 * k + 0.9)))
    for s, tasks in enumerate(stations):
        left = 0
        base = STATION_COLORS[s % len(STATION_COLORS)]
        for j, task in enumerate(tasks):
            w = inst.t[task]
            ax.barh(s, w, left=left, color=soft(base, 0.25 if j % 2 == 0 else 0.5), edgecolor="white", height=0.72)
            if w >= 0.045 * inst.cycle_time:
                ax.text(left + w / 2, s, str(task), ha="center", va="center", fontsize=8, color=INK)
            left += w
        ax.text(inst.cycle_time * 1.01, s, f"{100 * left / inst.cycle_time:.0f} %", va="center",
                fontsize=8.5, color=MUTED)
    ax.axvline(inst.cycle_time, color=ROSE, lw=1.3, ls="--")
    ax.set_yticks(range(k), [f"E{s + 1}" for s in range(k)])
    ax.invert_yaxis()
    ax.set_xlim(0, inst.cycle_time * 1.08)
    ax.set_xlabel("tiempo acumulado en la estación (la línea es el ciclo c)")
    style_axes(ax)
    fig.tight_layout()
    return fig


def fig_batch(df: pd.DataFrame, target: float | None, tol: float | None):
    fig, axes = plt.subplots(1, 2, figsize=(9, 2.6))
    ax = axes[0]
    if target is not None:
        ax.axvspan(target - tol, target + tol, color=PRIMARY_SOFT)
    ax.hist(df["OS"], bins=15, color=PRIMARY, edgecolor="white")
    ax.set_xlabel("order strength medido")
    style_axes(ax)
    ax = axes[1]
    ax.hist(df["LB1"], bins=range(int(df["LB1"].min()), int(df["LB1"].max()) + 2), color=TEAL,
            edgecolor="white", align="left")
    ax.set_xlabel("LB1")
    style_axes(ax)
    fig.tight_layout()
    return fig


# ================================================================================ barra lateral
with st.sidebar:
    st.markdown("## Generador SALBP-1")
    st.caption("Basado en SALBPGen (Otto, Otto y Scholl, 2013). Parámetros en `configs/generator.yaml`.")

    st.markdown('<div class="step">Paso 1</div><div class="step-title">Origen de la instancia</div>',
                unsafe_allow_html=True)
    mode = pick("Origen", ["gen", "load"], "gen",
                fmt=lambda v: "Generar" if v == "gen" else "Cargar archivo", key="mode")

    if mode == "gen":
        st.markdown('<div class="step">Paso 2</div><div class="step-title">Celda</div>',
                    unsafe_allow_html=True)
        layer = pick("Capa", ["core", "extended"], "core",
                     fmt=lambda v: "Núcleo" if v == "core" else "Ampliada", key="layer",
                     help="Núcleo: las 63 celdas del conjunto de referencia. "
                          "Ampliada: valores intermedios dentro de los mismos rangos.")
        cell: CellSpec | None = None
        if layer == "core":
            n = pick("Tareas (n)", list(cfg["sizes"]), 50, key="n")
            structure = pick("Estructura del grafo", list(STRUCTURES), "mixed", fmt=STRUCTURES.get,
                             key="structure", help=" ".join(f"{STRUCTURES[k]}: {v}" for k, v in STRUCT_HELP.items()))
            os_opts = CORE_OS[structure]
            os_t = pick("Order strength", os_opts, 0.6 if 0.6 in os_opts else os_opts[0],
                        fmt=lambda v: f"{v:.1f}", key=f"os_{structure}",
                        help="Fracción de pares de tareas con precedencia (directa o indirecta). "
                             "0,9 solo existe para MIXED (Tabla 6 del artículo).")
            dist = pick("Tiempos de tarea", list(DISTS), "bm", fmt=DISTS.get, key="dist",
                        help=" ".join(f"{DISTS[k]}: {v}" for k, v in DIST_HELP.items()))
            st.caption(f"{STRUCT_HELP[structure]} {DIST_HELP[dist]}")
            cell = CellSpec(int(n), os_t, structure, dist, "core", cycle_time=C)
        else:
            ext_mode = pick("Parámetros", ["random", "manual"], "random",
                            fmt=lambda v: "Sortear" if v == "random" else "Elegir", key="ext_mode")
            ext = cfg["extended"]
            if ext_mode == "manual":
                n = int(pick("Tareas (n)", list(cfg["sizes"]), 50, key="n_ext"))
                structure = pick("Estructura del grafo", list(STRUCTURES), "mixed", fmt=STRUCTURES.get,
                                 key="structure_ext")
                lo, hi = ext["os_range"][structure]
                os_t = st.slider("Order strength objetivo", float(lo), float(hi), float(round((lo + hi) / 2, 2)), 0.01)
                chain_share = n_bn = deg = None
                if structure in ext["chain_share_range"]:
                    a, b = ext["chain_share_range"][structure]
                    chain_share = st.slider("Tareas en cadenas (mínimo)", float(a), float(b), float(a), 0.01,
                                            format="%.2f")
                if structure == "bottleneck":
                    bcfg = cfg["structures"]["bottleneck"]
                    k_lo = max(1, int(np.ceil(bcfg["share_range"][0] * n - 1e-9)))
                    k_hi = max(k_lo, int(np.floor(bcfg["share_range"][1] * n + 1e-9)))
                    n_bn = int(st.number_input("Cuellos de botella", k_lo, k_hi, k_lo)) if k_hi > k_lo else k_lo
                    d_rng = bcfg["degree_range"].get(n, bcfg["degree_range"].get(str(n), bcfg["degree_range"]["default"]))
                    deg = int(st.slider("Grado de cada cuello de botella", int(d_rng[0]), int(d_rng[1]), int(d_rng[0])))
                dist = pick("Tiempos de tarea", list(DISTS), "bm", fmt=DISTS.get, key="dist_ext")
                cell = CellSpec(n, round(os_t, 3), structure, dist, "extended", chain_share, n_bn, deg, C)

        st.markdown('<div class="step">Paso 3</div><div class="step-title">Semilla</div>',
                    unsafe_allow_html=True)
        if "seed" not in st.session_state:
            st.session_state["seed"] = 12345
        c1, c2 = st.columns([1.3, 1], vertical_alignment="bottom")
        seed = int(c1.number_input("Semilla", min_value=0, max_value=2**32 - 1, step=1, key="seed",
                                   help="La misma celda con la misma semilla da siempre la misma instancia."))
        c2.button("Al azar", icon=":material/casino:", on_click=new_seed, width="stretch",
                  help="Elige una semilla aleatoria entre 0 y 999 999.")
        if layer == "extended" and ext_mode == "random":
            cell = sample_extended_cell(np.random.default_rng(seed), cfg)
            extra = []
            if cell.chain_share is not None:
                extra.append(f"cadenas ≥ {cell.chain_share:.0%}")
            if cell.n_bottlenecks:
                extra.append(f"{cell.n_bottlenecks} cuello(s) de botella de grado {cell.bottleneck_degree}")
            st.caption(f"Celda sorteada: n = {cell.n}, {STRUCTURES[cell.structure]}, OS {cell.os_target}, "
                       f"{DISTS[cell.time_dist]}" + (", " + ", ".join(extra) if extra else ""))
        st.session_state["cell"] = cell
        st.write("")
        if st.button("Generar instancia", type="primary", icon=":material/play_arrow:", width="stretch"):
            try:
                with st.spinner("Generando"):
                    set_instance(generate(cell, seed, cfg), "generada")
            except GenerationError as exc:
                st.error(f"No se pudo generar la celda: {exc}")
    else:
        st.markdown('<div class="step">Paso 2</div><div class="step-title">Archivo</div>',
                    unsafe_allow_html=True)
        up = st.file_uploader("Instancia .json, .alb o .IN2", type=["json", "alb", "in2"])
        c_in2 = int(st.number_input("Tiempo de ciclo (solo .IN2)", min_value=1, value=1000))
        if st.button("Cargar", type="primary", icon=":material/upload_file:", width="stretch", disabled=up is None):
            text = up.getvalue().decode("utf-8", errors="replace")
            stem, suffix = Path(up.name).stem, Path(up.name).suffix.lower()
            try:
                if suffix == ".json":
                    inst = instance_from_json(text)
                elif suffix == ".alb":
                    inst = parse_alb(text, stem)
                else:
                    inst = parse_in2(text, f"{stem}-c{c_in2}", c_in2)
                set_instance(inst, f"cargada de {up.name}")
            except Exception as exc:  # noqa: BLE001
                st.error(f"No se pudo leer el archivo: {exc}")

# ================================================================================ estado vacío
inst = st.session_state.get("inst")
if inst is None:
    st.markdown(
        '<div class="empty"><h3>Genera tu primera instancia</h3>'
        '<p class="muted">Cada instancia es un problema SALBP-1: tareas con tiempos, un grafo de '
        'precedencias y un tiempo de ciclo c = 1000. La app la genera con el método de SALBPGen y la dibuja.</p>'
        '<div class="howto">'
        '<div><b>PASO 1</b>Elige la capa y la celda en el panel izquierdo: tamaño, estructura, order strength '
        'y distribución de tiempos.</div>'
        '<div><b>PASO 2</b>Pulsa <i>Generar instancia</i>. La semilla fija el resultado, así que puedes '
        'repetirlo cuando quieras.</div>'
        '<div><b>PASO 3</b>Revisa el grafo, las tareas y los tiempos, compara las 12 reglas y descarga o guarda '
        'la instancia.</div></div></div>', unsafe_allow_html=True)
    st.write("")
    if st.button("Probar con un ejemplo (n = 20, MIXED, OS 0,6, BM)", icon=":material/bolt:"):
        set_instance(generate(CellSpec(20, 0.6, "mixed", "bm", cycle_time=C), 12345, cfg), "generada")
        st.rerun()
    st.stop()

# ================================================================================ cabecera
inst_json = instance_to_json(inst)
g = graph_measures(inst.n, inst.precedences)
errors = validate_instance(inst)
m = inst.meta
res = cached_cocktail(inst_json)

st.markdown(f'<div class="hero-id">{escape(inst.instance_id)}</div>', unsafe_allow_html=True)
head = [("Válida" if not errors else "Inválida", "ok" if not errors else "bad")]
if m.get("layer"):
    head += [("Núcleo" if m["layer"] == "core" else "Capa ampliada", "info"),
             (f"celda {m.get('cell_id')}", "muted"),
             (f"semilla {m.get('seed')}", "muted"),
             (f"{m.get('attempts')} intento(s)", "muted")]
else:
    head.append((f"Instancia {st.session_state.get('origin', '')}", "muted"))
chips(head)
if errors:
    st.error("La instancia no es válida: " + "; ".join(errors))

# Cumplimiento de la celda
if "os_target" in m and m.get("structure"):
    tol = os_tolerance(inst.n, cfg)
    t_lo, t_hi = time_bounds(inst.cycle_time, cfg["times"])
    cell_real = CellSpec(inst.n, m["os_target"], m["structure"], m["time_dist"], m["layer"],
                         m.get("chain_share_target"), m.get("n_bottlenecks_target"),
                         m.get("bottleneck_degree_target"), inst.cycle_time)
    reason = check_cell(cell_real, g, cfg)
    os_ok = abs(g["os"] - m["os_target"]) <= tol + 1e-12
    if m["structure"] == "chain":
        struct_txt = f"cadenas {g['chain_share']:.0%} ≥ {cell_real.chain_share or 0.4:.0%}"
    elif m["structure"] == "bottleneck":
        struct_txt = f"cuello de botella de grado ≥ {bottleneck_min_degree(inst.n, cfg)}"
    else:
        struct_txt = "estructura libre"
    times_ok = all(t_lo <= t <= t_hi for t in inst.times)
    chips([(f"OS dentro de ±{tol}", "ok" if os_ok else "bad"),
           (struct_txt, "ok" if reason in (None, "os_out_of_tolerance") else "bad"),
           (f"tiempos en [{t_lo}, {t_hi}]", "ok" if times_ok else "bad"),
           ("grafo acíclico y numeración topológica", "ok" if not errors else "bad")])
    tol_used = tol
else:
    tol_used = None

# KPIs
os_target = m.get("os_target")
os_html = ""
if os_target is not None and tol_used is not None:
    left = max(0.0, os_target - tol_used) * 100
    width = (min(1.0, os_target + tol_used) - max(0.0, os_target - tol_used)) * 100
    os_html = (f'<div class="osbar"><div class="osband" style="left:{left:.1f}%;width:{max(width, 0.8):.1f}%"></div>'
               f'<div class="osmark" style="left:calc({g["os"] * 100:.1f}% - 2px)"></div></div>')
cols = st.columns(4)
kpi(cols[0], "Tareas", inst.n, f"c = {inst.cycle_time} · Σt = {inst.total_time}")
kpi(cols[1], "Order strength", f"{g['os']:.3f}",
    f"objetivo {os_target} ± {tol_used}" if os_target is not None else "medido", os_html)
kpi(cols[2], "Estaciones (cóctel)", res["K_min"],
    f"LB1 = {inst.lb1} · {len(res['best_rules'])} de 12 reglas lo alcanzan")
kpi(cols[3], "Etapas", g["n_stages"], f"{g['n_arcs']} arcos directos")
st.write("")
cols = st.columns(4)
kpi(cols[0], "Tareas en cadena", f"{g['chain_share']:.0%}", f"{g['n_chain_tasks']} tareas")
kpi(cols[1], "Cuellos de botella", g["n_bottlenecks"],
    "grados " + ", ".join(map(str, g["bottleneck_degrees"])) if g["bottleneck_degrees"] else "ninguno")
kpi(cols[2], "Grado medio", f"{g['mean_degree']:.2f}",
    f"máx. entrada {g['max_in_degree']} · máx. salida {g['max_out_degree']}")
x_t = np.array(inst.times) / inst.cycle_time
kpi(cols[3], "Tiempo medio", f"{x_t.mean():.2f}c", f"desv. {x_t.std(ddof=1) if inst.n > 1 else 0:.2f}c")
st.write("")

# ================================================================================ pestañas
tab_graph, tab_tasks, tab_times, tab_rules, tab_batch, tab_export = st.tabs([
    ":material/account_tree: Grafo", ":material/table_rows: Tareas", ":material/timer: Tiempos",
    ":material/leaderboard: Heurísticas", ":material/stacks: Lote", ":material/download: Exportar"])

with tab_graph:
    c1, c2, c3, c4 = st.columns([2.2, 2, 1.6, 1.2], vertical_alignment="bottom")
    color_mode = c1.segmented_control("Color de los nodos", ["Estructura", "Tiempo", "Estación"],
                                      default="Estructura", key="color_mode") or "Estructura"
    rule_color = c2.selectbox("Regla para las estaciones", list(RULES),
                              format_func=lambda r: f"{RULES[r].code} · {RULES[r].name}",
                              index=res["best_rules"][0] - 1, disabled=color_mode != "Estación")
    focus = c3.selectbox("Resaltar una tarea", [None, *range(1, inst.n + 1)],
                         format_func=lambda v: "Ninguna" if v is None else f"Tarea {v}", key="focus_task",
                         help="Marca sus predecesoras (azul) y sucesoras (ámbar), directas e indirectas.")
    show_times = c4.toggle("Tiempos", value=inst.n <= 50, help="Muestra t_i debajo del número de tarea.")
    stations = cached_stations(inst_json, rule_color) if color_mode == "Estación" else None

    if focus:
        legend([(f"Tarea {focus}", PRIMARY, PRIMARY_DARK),
                (f"{inst.pred_all[focus].bit_count()} predecesoras", PRIMARY_SOFT, PRIMARY),
                (f"{inst.succ_all[focus].bit_count()} sucesoras", AMBER_SOFT, AMBER),
                ("sin relación", "#F8FAFC", "#E2E8F0")])
    elif color_mode == "Estructura":
        legend([("cuello de botella", AMBER_SOFT, AMBER), ("tarea de cadena", TEAL_SOFT, TEAL),
                ("resto", NODE_FILL, NODE_LINE)])
    elif color_mode == "Tiempo":
        legend([("tarea corta", to_hex(TIME_CMAP(0.05)), PRIMARY_DARK),
                ("media", to_hex(TIME_CMAP(0.45)), PRIMARY_DARK),
                ("cercana a c", to_hex(TIME_CMAP(0.95)), PRIMARY_DARK)])
    else:
        legend([(f"E{k + 1}", soft(STATION_COLORS[k % len(STATION_COLORS)], 0.55),
                 STATION_COLORS[k % len(STATION_COLORS)]) for k in range(min(len(stations), 10))]
               + ([("…", "#FFFFFF", "#FFFFFF")] if len(stations) > 10 else []))
    with st.container(border=True):
        # Grafos con pocas etapas se dibujan a tamaño natural; los anchos se ajustan al contenedor.
        st.graphviz_chart(graph_dot(inst, g, color_mode, stations, show_times, focus),
                          width="stretch" if g["n_stages"] > 11 else "content")
    st.caption("Cada columna es una etapa (camino más largo desde las tareas sin predecesoras). "
               "Pasa el cursor sobre un nodo para ver su tiempo y su número de sucesoras.")

with tab_tasks:
    lev = levels(inst.n, inst.precedences)
    chains_set, bns_set = set(g["chain_task_list"]), set(g["bottleneck_tasks"])
    rows = []
    for i in range(1, inst.n + 1):
        rows.append({
            "Tarea": i, "t_i": inst.t[i], "t_i / c": inst.t[i] / inst.cycle_time, "Etapa": lev[i],
            "Papel": "cuello de botella" if i in bns_set else "cadena" if i in chains_set else "",
            "Predecesoras": ", ".join(map(str, inst.imm_pred[i])) or "",
            "Sucesoras": ", ".join(map(str, inst.imm_succ[i])) or "",
            "NSI": inst.nsi[i], "NS": inst.ns[i], "PP": inst.pp[i], "CI": inst.ci[i], "CS": inst.cs[i],
            "Holgura": inst.cs[i] - inst.ci[i],
        })
    df_tasks = pd.DataFrame(rows)
    c1, c2 = st.columns([3, 1], vertical_alignment="bottom")
    query = c1.text_input("Filtrar", placeholder="Número de tarea o papel (cadena, cuello)", label_visibility="collapsed")
    c2.download_button("Descargar CSV", df_tasks.to_csv(index=False), f"{inst.instance_id}-tareas.csv",
                       "text/csv", icon=":material/download:", width="stretch")
    if query:
        q = query.strip().lower()
        df_tasks = df_tasks[df_tasks["Tarea"].astype(str).eq(q) | df_tasks["Papel"].str.contains(q, case=False)]
    st.dataframe(
        df_tasks, hide_index=True, width="stretch", height=min(560, 38 + 35 * len(df_tasks)),
        column_config={
            "t_i / c": st.column_config.ProgressColumn("t_i / c", min_value=0.0, max_value=1.0, format="%.2f"),
            "NS": st.column_config.NumberColumn("NS", help="Número de sucesoras (todas)"),
            "NSI": st.column_config.NumberColumn("NSI", help="Sucesoras inmediatas"),
            "PP": st.column_config.NumberColumn("PP", help="Peso posicional: t_i más los tiempos de todas sus sucesoras"),
            "CI": st.column_config.NumberColumn("CI", help="Cota inferior de estación"),
            "CS": st.column_config.NumberColumn("CS", help="Cota superior de estación"),
        })
    st.caption("NS, NSI, PP, CI y CS son los atributos que usan las 12 reglas de prioridad.")

with tab_times:
    c1, c2 = st.columns([3, 1.3])
    with c1:
        st.pyplot(fig_times(inst), width="stretch")
    with c2:
        stats = [("Suma de tiempos", f"{inst.total_time}"), ("Tarea más corta", f"{min(inst.times)}"),
                 ("Tarea más larga", f"{max(inst.times)}"), ("Tareas > c/2", f"{int((x_t > 0.5).sum())}"),
                 ("LB1 = ⌈Σt / c⌉", f"{inst.lb1}")]
        for label, value in stats:
            st.markdown(f'<div class="kpi" style="margin-bottom:8px;padding:10px 14px">'
                        f'<div class="label">{label}</div><div class="value" style="font-size:1.2rem">{value}'
                        f'</div></div>', unsafe_allow_html=True)
    if m.get("time_dist"):
        st.caption(f"Distribución {DISTS[m['time_dist']]}: {DIST_HELP[m['time_dist']]}")

with tab_rules:
    c1, c2 = st.columns([1.35, 1])
    with c1:
        st.markdown("**Estaciones con cada regla**")
        st.pyplot(fig_rules(res, inst.lb1), width="stretch")
        st.caption("En azul, las reglas que logran el mínimo (el resultado del cóctel). "
                   "La línea roja es la cota inferior LB1.")
    with c2:
        st.markdown("**Resumen**")
        k_sorted = sorted(RULES, key=lambda r: (res["K"][r], r))
        df_rules = pd.DataFrame([{"Regla": RULES[r].code, "Criterio": RULES[r].name,
                                  "K": res["K"][r], "Exceso": res["K"][r] - res["K_min"],
                                  "ms": round(1000 * res["seconds"][r], 2)} for r in k_sorted])
        st.dataframe(df_rules, hide_index=True, width="stretch", height=455)
    with st.container(border=True):
        c1, c2 = st.columns([3, 1], vertical_alignment="center")
        c1.markdown("**Rollout.** En cada asignación completa la solución con las 12 reglas y aplica la que "
                    "da menos estaciones. Nunca da más estaciones que el cóctel.")
        if c2.button("Ejecutar rollout", icon=":material/route:", width="stretch"):
            with st.spinner("Calculando"):
                st.session_state["rollout"] = run_rollout(inst)
        if "rollout" in st.session_state:
            ro = st.session_state["rollout"]
            delta = ro.K - res["K_min"]
            verdict = "mejora al cóctel" if delta < 0 else "iguala al cóctel"
            chips([(f"K rollout = {ro.K}", "info"), (verdict, "ok"),
                   (f"{ro.extra['n_decision_states']} estados de decisión", "muted"),
                   (f"{ro.seconds:.2f} s", "muted")])
    st.markdown("**Asignación por estación**")
    rule_sel = st.selectbox("Regla", list(RULES), format_func=lambda r: f"{RULES[r].code} · {RULES[r].name}",
                            index=res["best_rules"][0] - 1, key="rule_loads")
    sol_st = cached_stations(inst_json, rule_sel)
    st.pyplot(fig_stations(inst, sol_st), width="stretch")
    util = inst.total_time / (len(sol_st) * inst.cycle_time)
    st.caption(f"{len(sol_st)} estaciones con {RULES[rule_sel].code}. Utilización media {util:.0%}. "
               "Cada bloque es una tarea con su número; el porcentaje es la carga de la estación.")

with tab_batch:
    cell = st.session_state.get("cell")
    if cell is None or "attempts" not in m:
        st.info("El lote está disponible para instancias generadas en esta sesión.")
    else:
        st.markdown(f"Genera varias instancias de la celda **{escape(m.get('cell_id', ''))}** con semillas "
                    f"distintas para ver cuánto varían y cuántos intentos se rechazan.")
        c1, c2, c3 = st.columns([1, 2, 1], vertical_alignment="bottom")
        k = int(c1.number_input("Instancias", 1, 500, 20))
        out_dir = c2.text_input("Carpeta de salida", "data/raw/app_batches")
        if c3.button("Generar lote", icon=":material/stacks:", width="stretch"):
            insts, prog = [], st.progress(0.0, text="Generando")
            base = int(m.get("base_seed", 0))
            for j in range(k):
                insts.append(generate(cell, base + 1000 * (j + 1), cfg, index=j))
                prog.progress((j + 1) / k, text=f"Generando {j + 1} de {k}")
            prog.empty()
            st.session_state["batch"] = insts
        batch = st.session_state.get("batch")
        if batch:
            bdf = pd.DataFrame([{"instance_id": b.instance_id, "Semilla": b.meta["seed"], "OS": b.meta["os"],
                                 "Cadenas": b.meta["chain_share"], "Cuellos": b.meta["n_bottlenecks"],
                                 "Arcos": b.meta["n_arcs"], "Etapas": b.meta["n_stages"], "LB1": b.lb1,
                                 "Intentos": b.meta["attempts"]} for b in batch])
            rej = sum((Counter(b.meta["rejections"]) for b in batch), Counter())
            chips([(f"{len(bdf)} instancias", "info"),
                   (f"rechazo {1 - len(bdf) / bdf['Intentos'].sum():.0%}", "muted")]
                  + [(f"{r}: {c}", "muted") for r, c in rej.most_common(3)])
            st.pyplot(fig_batch(bdf, m.get("os_target"), tol_used), width="stretch")
            st.dataframe(bdf, hide_index=True, width="stretch",
                         column_config={"OS": st.column_config.NumberColumn(format="%.3f"),
                                        "Cadenas": st.column_config.NumberColumn(format="%.2f")})
            if st.button("Guardar lote como .jsonl.gz", icon=":material/save:"):
                path = ROOT / out_dir / f"{batch[0].meta['cell_id']}-{int(time.time())}.jsonl.gz"
                write_jsonl_gz(batch, path)
                st.success(f"Lote guardado en {path}")

with tab_export:
    c1, c2 = st.columns(2)
    with c1, st.container(border=True):
        st.markdown("**Descargar**")
        st.download_button("JSON del proyecto", instance_to_json(inst, indent=1), f"{inst.instance_id}.json",
                           "application/json", icon=":material/data_object:", width="stretch")
        st.download_button("Formato .alb", instance_to_alb(inst), f"{inst.instance_id}.alb", "text/plain",
                           icon=":material/description:", width="stretch")
    with c2, st.container(border=True):
        st.markdown("**Guardar en el proyecto**")
        folder = st.text_input("Carpeta", "data/raw/app")
        fmt = pick("Formato", [".json", ".alb"], ".json", key="save_fmt")
        if st.button("Guardar", icon=":material/save:", width="stretch"):
            path = ROOT / folder / f"{inst.instance_id}{fmt}"
            save_instance(inst, path)
            st.success(f"Guardada en {path}")
    with st.expander("Metadatos de la generación"):
        st.json(inst.meta, expanded=True)
    with st.expander("JSON completo"):
        st.code(instance_to_json(inst, indent=1), language="json")
