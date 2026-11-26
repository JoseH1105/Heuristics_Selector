"""App de interfaz para el generador de instancias (herramienta de apoyo, fuera del paquete).

Permite generar instancias de la capa núcleo o ampliada, cargar instancias existentes
(.json, .alb, .IN2), visualizarlas (grafo por etapas, tareas, tiempos), resolverlas con las
12 reglas, el cóctel y el *rollout*, y guardarlas o descargarlas.

Ejecutar desde la raíz del proyecto:

    streamlit run apps/generator_app.py
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import time

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from salbp_selector.core import RULES, run_cocktail, run_rollout, run_rule, validate_instance  # noqa: E402
from salbp_selector.core.io import (  # noqa: E402
    instance_from_json, instance_to_alb, instance_to_json, parse_alb, parse_in2, save_instance,
    write_jsonl_gz,
)
from salbp_selector.gen import (  # noqa: E402
    CORE_GRAPH_COMBOS, CellSpec, GenerationError, generate, load_config, os_tolerance,
    sample_extended_cell,
)
from salbp_selector.gen.graphs import graph_measures, levels  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "configs" / "generator.yaml"
STRUCT_LABEL = {"mixed": "MIXED (sin requisito)", "chain": "CH (cadenas)", "bottleneck": "BN (cuellos de botella)"}
DIST_LABEL = {"pb": "PB · pico inferior", "bm": "BM · bimodal", "pm": "PM · pico central"}
PALETTE = ["#4C78A8", "#F58518", "#54A24B", "#E45756", "#72B7B2", "#EECA3B", "#B279A2",
           "#FF9DA6", "#9D755D", "#BAB0AC"]

st.set_page_config(page_title="Generador SALBP-1", page_icon="🏭", layout="wide")


@st.cache_data(show_spinner=False)
def get_config() -> dict:
    return load_config(CONFIG_PATH if CONFIG_PATH.exists() else None)


cfg = get_config()


# ============================================================================ utilidades
def task_table(inst, g: dict) -> pd.DataFrame:
    lev = levels(inst.n, inst.precedences)
    chains, bns = set(g["chain_task_list"]), set(g["bottleneck_tasks"])
    rows = []
    for i in range(1, inst.n + 1):
        role = "cuello de botella" if i in bns else "cadena" if i in chains else ""
        rows.append({
            "tarea": i, "t_i": inst.t[i], "t_i/c": round(inst.t[i] / inst.cycle_time, 3), "etapa": lev[i],
            "predecesoras": ", ".join(map(str, inst.imm_pred[i])),
            "sucesoras": ", ".join(map(str, inst.imm_succ[i])),
            "NSI": inst.nsi[i], "NS": inst.ns[i], "PP": inst.pp[i], "CI": inst.ci[i], "CS": inst.cs[i],
            "holgura": inst.cs[i] - inst.ci[i], "papel": role,
        })
    return pd.DataFrame(rows)


def graph_dot(inst, g: dict, color_by: str, stations: list[list[int]] | None, show_times: bool) -> str:
    lev = levels(inst.n, inst.precedences)
    chains, bns = set(g["chain_task_list"]), set(g["bottleneck_tasks"])
    station_of = {}
    if stations:
        for k, st_ in enumerate(stations):
            for i in st_:
                station_of[i] = k
    lines = ["digraph G {", "rankdir=LR; splines=true; nodesep=0.15; ranksep=0.45;",
             'node [shape=circle, style=filled, fontname="Helvetica", fontsize=10, width=0.42, fixedsize=true];',
             'edge [color="#8a8a8a", arrowsize=0.5];']
    for i in range(1, inst.n + 1):
        if color_by == "Estación" and station_of:
            fill = PALETTE[station_of[i] % len(PALETTE)]
        elif color_by == "Tiempo":
            x = inst.t[i] / inst.cycle_time
            fill = matplotlib.colors.to_hex(plt.cm.YlOrRd(0.15 + 0.85 * x))
        else:
            fill = "#F58518" if i in bns else "#72B7B2" if i in chains else "#DDE3EA"
        label = f"{i}\\n{inst.t[i]}" if show_times else str(i)
        tip = f"t={inst.t[i]} etapa={lev[i]}"
        lines.append(f'{i} [label="{label}", fillcolor="{fill}", tooltip="{tip}"];')
    by_level: dict[int, list[int]] = {}
    for i in range(1, inst.n + 1):
        by_level.setdefault(lev[i], []).append(i)
    for nodes in by_level.values():
        lines.append("{rank=same; " + " ".join(map(str, nodes)) + ";}")
    lines += [f"{i} -> {j};" for i, j in inst.precedences]
    lines.append("}")
    return "\n".join(lines)


def times_figure(inst):
    x = np.array(inst.times) / inst.cycle_time
    fig, ax = plt.subplots(figsize=(6, 2.8))
    ax.hist(x, bins=np.linspace(0, 1, 26), color="#4C78A8", edgecolor="white")
    ax.set_xlabel("t_i / c")
    ax.set_ylabel("tareas")
    ax.set_xlim(0, 1)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    return fig


def loads_figure(inst, stations):
    loads = [sum(inst.t[i] for i in s) for s in stations]
    fig, ax = plt.subplots(figsize=(6, 2.8))
    ax.bar(range(1, len(loads) + 1), loads, color="#54A24B")
    ax.axhline(inst.cycle_time, color="#E45756", ls="--", lw=1, label="c")
    ax.set_xlabel("estación")
    ax.set_ylabel("carga")
    ax.legend(loc="lower right")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    return fig


def set_instance(inst, origin: str) -> None:
    st.session_state["inst"] = inst
    st.session_state["origin"] = origin
    for key in ("cocktail", "rollout", "batch"):
        st.session_state.pop(key, None)


# ============================================================================== barra lateral
st.sidebar.title("🏭 Generador SALBP-1")
mode = st.sidebar.radio("Modo", ["Generar instancia", "Cargar instancia"], horizontal=True)

if mode == "Generar instancia":
    layer = st.sidebar.radio("Capa", ["Núcleo (63 celdas)", "Ampliada"], horizontal=True)
    sizes = list(cfg["sizes"])
    seed = int(st.sidebar.number_input("Semilla", min_value=0, max_value=2**32 - 1, value=12345, step=1))
    index = int(st.sidebar.number_input("Índice (para el instance_id)", min_value=0, value=0, step=1))
    cell: CellSpec | None = None
    if layer.startswith("Núcleo"):
        n = st.sidebar.selectbox("Tamaño n", sizes, index=1)
        combos = [f"{STRUCT_LABEL[s]} · OS {os_:.1f}" for s, os_ in CORE_GRAPH_COMBOS]
        combo = st.sidebar.selectbox("Estructura y order strength (Tabla 6)", range(len(combos)),
                                     format_func=lambda k: combos[k])
        dist = st.sidebar.selectbox("Distribución de tiempos", list(DIST_LABEL), index=1,
                                    format_func=DIST_LABEL.get)
        structure, os_t = CORE_GRAPH_COMBOS[combo]
        cell = CellSpec(int(n), os_t, structure, dist, "core", cycle_time=int(cfg["cycle_time"]))
    else:
        how = st.sidebar.radio("Parámetros", ["Sortear celda con la semilla", "Elegir a mano"])
        if how.startswith("Sortear"):
            cell = sample_extended_cell(np.random.default_rng(seed), cfg)
            extra = ""
            if cell.chain_share is not None:
                extra += f", cadenas ≥ {cell.chain_share:.0%}"
            if cell.n_bottlenecks:
                extra += f", {cell.n_bottlenecks} cuello(s) de botella de grado {cell.bottleneck_degree}"
            st.sidebar.caption(f"Celda sorteada: n = {cell.n}, {STRUCT_LABEL[cell.structure]}, "
                               f"OS = {cell.os_target}, {DIST_LABEL[cell.time_dist]}{extra}")
        else:
            ext = cfg["extended"]
            n = int(st.sidebar.selectbox("Tamaño n", sizes, index=1))
            structure = st.sidebar.selectbox("Estructura", list(STRUCT_LABEL), format_func=STRUCT_LABEL.get)
            lo, hi = ext["os_range"][structure]
            os_t = st.sidebar.slider("Order strength objetivo", float(lo), float(hi), float(lo + hi) / 2, 0.01)
            chain_share = n_bn = deg = None
            if structure in ext["chain_share_range"]:
                a, b = ext["chain_share_range"][structure]
                chain_share = st.sidebar.slider("Fracción de tareas en cadenas", float(a), float(b),
                                                float(a), 0.01)
            if structure == "bottleneck":
                bcfg = cfg["structures"]["bottleneck"]
                k_lo = max(1, int(np.ceil(bcfg["share_range"][0] * n - 1e-9)))
                k_hi = max(k_lo, int(np.floor(bcfg["share_range"][1] * n + 1e-9)))
                n_bn = int(st.sidebar.number_input("Número de cuellos de botella", k_lo, k_hi, k_lo))
                d_rng = bcfg["degree_range"].get(n, bcfg["degree_range"].get(str(n), bcfg["degree_range"]["default"]))
                deg = int(st.sidebar.slider("Grado de los cuellos de botella", int(d_rng[0]), int(d_rng[1]),
                                            int(d_rng[0])))
            dist = st.sidebar.selectbox("Distribución de tiempos", list(DIST_LABEL), index=1,
                                        format_func=DIST_LABEL.get)
            cell = CellSpec(n, round(os_t, 3), structure, dist, "extended", chain_share, n_bn, deg,
                            int(cfg["cycle_time"]))
    if st.sidebar.button("⚙️ Generar", type="primary", use_container_width=True):
        try:
            with st.spinner("Generando…"):
                inst = generate(cell, seed, cfg, index=index)
            set_instance(inst, "generada")
        except GenerationError as exc:
            st.sidebar.error(str(exc))
    st.session_state["cell"] = cell
else:
    up = st.sidebar.file_uploader("Instancia (.json, .alb, .IN2)", type=["json", "alb", "in2"])
    c_in2 = int(st.sidebar.number_input("Tiempo de ciclo (solo .IN2)", min_value=1, value=1000))
    if up is not None and st.sidebar.button("📂 Cargar", type="primary", use_container_width=True):
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
            st.sidebar.error(f"No se pudo leer el archivo: {exc}")

st.sidebar.divider()
st.sidebar.caption("Parámetros de `configs/generator.yaml`. Base: Otto, Otto y Scholl (2013), SALBPGen.")

# ============================================================================== contenido
inst = st.session_state.get("inst")
if inst is None:
    st.title("Generador de instancias SALBP-1")
    st.info("Elija la celda en la barra lateral y pulse **Generar**, o cargue una instancia existente.")
    st.markdown(
        "- **Núcleo**: 3 tamaños × 7 combinaciones de grafo (Tabla 6) × 3 distribuciones de tiempo = 63 celdas.\n"
        "- **Ampliada**: valores intermedios de OS, fracción de cadenas y cuellos de botella dentro de los mismos rangos.\n"
        "- Cada instancia queda ligada a su semilla: la misma celda y semilla producen la misma instancia.")
    st.stop()

g = graph_measures(inst.n, inst.precedences)
errors = validate_instance(inst)
st.title(inst.instance_id)
st.caption(f"Instancia {st.session_state.get('origin', '')}" + (" · ✅ válida" if not errors else " · ❌ inválida"))
if errors:
    st.error("\n".join(errors))

m = inst.meta
cols = st.columns(4) + st.columns(4)
cols[0].metric("Tareas n", inst.n)
cols[1].metric("Ciclo c", inst.cycle_time)
cols[2].metric("Arcos directos", g["n_arcs"])
os_target = m.get("os_target")
cols[3].metric("Order strength", f"{g['os']:.3f}",
               delta=f"{g['os'] - os_target:+.3f} vs {os_target}" if os_target is not None else None,
               delta_color="off")
cols[4].metric("Tareas en cadena", f"{100 * g['chain_share']:.0f} %")
cols[5].metric("Cuellos de botella", g["n_bottlenecks"],
               help=f"grados: {g['bottleneck_degrees']}" if g["bottleneck_degrees"] else None)
cols[6].metric("Etapas", g["n_stages"])
cols[7].metric("LB1", inst.lb1)
if "attempts" in m:
    tol = os_tolerance(inst.n, cfg)
    st.caption(f"Capa **{m.get('layer')}** · celda `{m.get('cell_id')}` · semilla efectiva {m.get('seed')} "
               f"(base {m.get('base_seed')}) · intentos {m.get('attempts')} · rechazos {m.get('rejections') or '—'} · "
               f"tolerancia de OS ±{tol} · {1000 * m.get('seconds', 0):.0f} ms")

tab_graph, tab_tasks, tab_times, tab_rules, tab_batch, tab_save = st.tabs(
    ["🕸️ Grafo", "📋 Tareas", "⏱️ Tiempos", "🧮 Heurísticos", "📦 Lote", "💾 Guardar / JSON"])

with tab_graph:
    c1, c2, c3 = st.columns([2, 2, 1])
    color_by = c1.radio("Colorear por", ["Estructura", "Tiempo", "Estación"], horizontal=True)
    rule_for_color = c2.selectbox("Regla para colorear estaciones", list(RULES),
                                  format_func=lambda r: f"{RULES[r].code} · {RULES[r].name}",
                                  disabled=color_by != "Estación")
    show_times = c3.checkbox("Mostrar t_i", value=inst.n <= 50)
    stations = run_rule(inst, rule_for_color).stations if color_by == "Estación" else None
    if inst.n > 100:
        st.warning("Grafo grande: el dibujo puede tardar.")
    st.graphviz_chart(graph_dot(inst, g, color_by, stations, show_times), use_container_width=True)
    if color_by == "Estructura":
        st.caption("🟠 cuello de botella · 🟦 tarea de cadena · ⬜ resto. Columnas = etapas (camino más largo).")
    elif color_by == "Estación":
        st.caption(f"Colores = estaciones de la solución de {RULES[rule_for_color].code} "
                   f"(K = {len(stations)}).")

with tab_tasks:
    st.dataframe(task_table(inst, g), use_container_width=True, hide_index=True, height=480)

with tab_times:
    c1, c2 = st.columns([3, 2])
    c1.pyplot(times_figure(inst), use_container_width=True)
    x = np.array(inst.times) / inst.cycle_time
    c2.dataframe(pd.DataFrame({
        "medida": ["Σ t_i", "media t_i/c", "desv. t_i/c", "mín t_i", "máx t_i", "tareas > c/2"],
        "valor": [inst.total_time, round(x.mean(), 3), round(x.std(ddof=1), 3) if inst.n > 1 else 0,
                  min(inst.times), max(inst.times), int((x > 0.5).sum())],
    }), hide_index=True, use_container_width=True)
    if m.get("time_dist"):
        c2.caption(f"Distribución: {DIST_LABEL.get(m['time_dist'], m['time_dist'])}")

with tab_rules:
    if "cocktail" not in st.session_state:
        st.session_state["cocktail"] = run_cocktail(inst)
    res = st.session_state["cocktail"]
    rows = [{"regla": RULES[r].code, "nombre": RULES[r].name, "sentido": RULES[r].sense,
             "expresión": RULES[r].expression, "K": res["K"][r],
             "exceso": res["K"][r] - res["K_min"], "ms": round(1000 * res["seconds"][r], 2)}
            for r in RULES]
    df = pd.DataFrame(rows).sort_values(["K", "regla"], kind="stable")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Cóctel (mín. K)", res["K_min"])
    c2.metric("LB1", inst.lb1)
    c3.metric("Reglas óptimas", f"{len(res['best_rules'])}/12")
    c4.metric("Tiempo del cóctel", f"{1000 * res['seconds_total']:.1f} ms")
    st.dataframe(df, hide_index=True, use_container_width=True)
    if st.button("Ejecutar rollout"):
        with st.spinner("Rollout…"):
            st.session_state["rollout"] = run_rollout(inst)
    if "rollout" in st.session_state:
        ro = st.session_state["rollout"]
        st.success(f"Rollout: K = {ro.K} (cóctel {res['K_min']}) · estados de decisión "
                   f"{ro.extra['n_decision_states']} · {ro.seconds:.2f} s")
    st.subheader("Cargas por estación")
    rule_sel = st.selectbox("Regla", list(RULES), format_func=lambda r: f"{RULES[r].code} · {RULES[r].name}",
                            index=res["best_rules"][0] - 1, key="rule_loads")
    sol = run_rule(inst, rule_sel)
    c1, c2 = st.columns([3, 2])
    c1.pyplot(loads_figure(inst, sol.stations), use_container_width=True)
    c2.dataframe(pd.DataFrame({"estación": range(1, sol.K + 1),
                               "tareas": [", ".join(map(str, s)) for s in sol.stations],
                               "carga": sol.loads(inst)}), hide_index=True, use_container_width=True)

with tab_batch:
    st.write("Genera varias instancias de la **misma celda** (semillas base + 1000·k, k = 1, 2, …) "
             "para ver la variabilidad y la tasa de rechazo, y opcionalmente guardarlas.")
    cell = st.session_state.get("cell")
    if cell is None or "attempts" not in m:
        st.info("Disponible para instancias generadas en esta sesión.")
    else:
        c1, c2 = st.columns(2)
        k = int(c1.number_input("Número de instancias", 1, 500, 20))
        out_dir = c2.text_input("Carpeta de salida", "data/raw/app_batches")
        if st.button("Generar lote"):
            insts, prog = [], st.progress(0.0)
            base = int(m.get("base_seed", 0))
            for j in range(k):
                insts.append(generate(cell, base + 1000 * (j + 1), cfg, index=j))
                prog.progress((j + 1) / k)
            st.session_state["batch"] = insts
        batch = st.session_state.get("batch")
        if batch:
            bdf = pd.DataFrame([{"instance_id": b.instance_id, "seed": b.meta["seed"], "OS": b.meta["os"],
                                 "cadenas": b.meta["chain_share"], "BN": b.meta["n_bottlenecks"],
                                 "arcos": b.meta["n_arcs"], "etapas": b.meta["n_stages"],
                                 "LB1": b.lb1, "intentos": b.meta["attempts"]} for b in batch])
            att = bdf["intentos"].sum()
            st.caption(f"Tasa de rechazo: {100 * (1 - len(bdf) / att):.1f} % · "
                       f"rechazos: {dict(sum((Counter(b.meta['rejections']) for b in batch), Counter()))}")
            st.dataframe(bdf, hide_index=True, use_container_width=True)
            if st.button("Guardar lote (.jsonl.gz)"):
                path = ROOT / out_dir / f"{batch[0].meta['cell_id']}-{int(time.time())}.jsonl.gz"
                write_jsonl_gz(batch, path)
                st.success(f"Guardado en {path}")

with tab_save:
    c1, c2 = st.columns(2)
    c1.download_button("⬇️ Descargar JSON", instance_to_json(inst, indent=1), f"{inst.instance_id}.json",
                       "application/json", use_container_width=True)
    c2.download_button("⬇️ Descargar .alb", instance_to_alb(inst), f"{inst.instance_id}.alb", "text/plain",
                       use_container_width=True)
    folder = st.text_input("Guardar en la carpeta del proyecto", "data/raw/app")
    fmt = st.radio("Formato", [".json", ".alb"], horizontal=True)
    if st.button("💾 Guardar"):
        path = ROOT / folder / f"{inst.instance_id}{fmt}"
        save_instance(inst, path)
        st.success(f"Guardada en {path}")
    st.subheader("meta")
    st.json(inst.meta, expanded=False)
    with st.expander("JSON completo"):
        st.code(instance_to_json(inst, indent=1), language="json")
