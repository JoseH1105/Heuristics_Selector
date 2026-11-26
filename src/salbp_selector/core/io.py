"""Lectura, escritura y validación de instancias (contrato §9 y §10).

Formatos soportados:
- ``.json``: formato del contrato de datos (una instancia por archivo).
- ``.alb``: formato de assembly-line-balancing.de (Otto, Otto y Scholl, 2013).
- ``.in2``: formato clásico de Scholl (solo grafo y tiempos); requiere ``cycle_time``.
- ``.jsonl.gz``: varias instancias, una por línea, comprimido (capa 1 de datos).
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
import gzip
import hashlib
import io as _io
import json
from numbers import Integral
from pathlib import Path

from .instance import Instance


# --------------------------------------------------------------------- JSON
def instance_to_json(inst: Instance, indent: int | None = None) -> str:
    return json.dumps(inst.to_dict(), ensure_ascii=False, indent=indent, sort_keys=False)


def instance_from_json(text: str) -> Instance:
    return Instance.from_dict(json.loads(text))


def save_instance(inst: Instance, path: str | Path) -> None:
    """Guarda la instancia en JSON (``.json``) o en ``.alb`` según la extensión."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".alb":
        path.write_text(instance_to_alb(inst), encoding="utf-8")
    else:
        path.write_text(instance_to_json(inst, indent=1), encoding="utf-8")


def load_instance(path: str | Path, cycle_time: int | None = None) -> Instance:
    """Carga una instancia desde ``.json``, ``.alb`` o ``.in2`` (este último requiere ``cycle_time``)."""
    path = Path(path)
    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8", errors="replace")
    if suffix == ".json":
        return instance_from_json(text)
    if suffix == ".alb":
        return parse_alb(text, instance_id=path.stem, cycle_time=cycle_time)
    if suffix == ".in2":
        if cycle_time is None:
            raise ValueError("El formato .IN2 no incluye el tiempo de ciclo: indique cycle_time")
        return parse_in2(text, instance_id=f"{path.stem}-c{cycle_time}", cycle_time=cycle_time)
    raise ValueError(f"Formato no soportado: {path.suffix}")


# ---------------------------------------------------------------------- ALB
def parse_alb(text: str, instance_id: str = "alb", cycle_time: int | None = None) -> Instance:
    """Lee el formato ``.alb``: secciones ``<number of tasks>``, ``<cycle time>``,
    ``<task times>``, ``<precedence relations>`` y ``<end>``. Ignora las demás secciones."""
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("<") and line.endswith(">"):
            current = line[1:-1].strip().lower()
            if current == "end":
                break
            sections[current] = []
            continue
        if current is not None:
            sections[current].append(line)

    n = int(sections["number of tasks"][0])
    if cycle_time is None:
        if "cycle time" not in sections:
            raise ValueError("El archivo .alb no tiene <cycle time>; indique cycle_time")
        cycle_time = int(float(sections["cycle time"][0].replace(",", ".")))

    times_map: dict[int, int] = {}
    for line in sections.get("task times", []):
        parts = line.replace(",", " ").split()
        times_map[int(parts[0])] = int(float(parts[1]))
    times = tuple(times_map[i] for i in range(1, n + 1))

    arcs = []
    for line in sections.get("precedence relations", []):
        parts = line.replace(";", ",").replace(" ", ",").split(",")
        parts = [p for p in parts if p]
        arcs.append((int(parts[0]), int(parts[1])))

    meta = {"source": "alb"}
    if "order strength" in sections:
        try:
            meta["os_file"] = float(sections["order strength"][0].replace(",", "."))
        except ValueError:
            pass
    return Instance(instance_id, n, cycle_time, times, tuple(arcs), meta)


def instance_to_alb(inst: Instance) -> str:
    """Escribe la instancia en formato ``.alb``."""
    lines = [
        "<number of tasks>", str(inst.n), "",
        "<cycle time>", str(inst.cycle_time), "",
        "<order strength>", f"{inst.order_strength:.3f}".replace(".", ","), "",
        "<task times>",
    ]
    lines += [f"{i} {t}" for i, t in enumerate(inst.times, start=1)]
    lines += ["", "<precedence relations>"]
    lines += [f"{i},{j}" for i, j in inst.precedences]
    lines += ["", "<end>", ""]
    return "\n".join(lines)


# ---------------------------------------------------------------------- IN2
def parse_in2(text: str, instance_id: str, cycle_time: int) -> Instance:
    """Formato de Scholl: n; n tiempos; arcos ``i,j``; termina en ``-1,-1``."""
    tokens = [ln.strip() for ln in text.splitlines() if ln.strip()]
    n = int(tokens[0])
    times = tuple(int(float(x)) for x in tokens[1 : n + 1])
    arcs = []
    for ln in tokens[n + 1 :]:
        i, j = (int(x) for x in ln.replace(" ", "").split(",")[:2])
        if i == -1 and j == -1:
            break
        arcs.append((i, j))
    return Instance(instance_id, n, cycle_time, times, tuple(arcs), {"source": "in2"})


# ------------------------------------------------------------- JSONL.GZ
def write_jsonl_gz(instances: Iterable[Instance], path: str | Path) -> int:
    """Escribe instancias en JSON por líneas comprimido. Es determinista (``mtime=0``),
    de modo que la misma lista produce el mismo *hash* SHA-256. Devuelve el número escrito."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with open(path, "wb") as fh, gzip.GzipFile(filename="", mode="wb", fileobj=fh, mtime=0) as gz:
        with _io.TextIOWrapper(gz, encoding="utf-8", newline="\n") as w:
            for inst in instances:
                w.write(instance_to_json(inst))
                w.write("\n")
                count += 1
    return count


def read_jsonl_gz(path: str | Path) -> Iterator[Instance]:
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                yield instance_from_json(line)


def file_sha256(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def content_hash(inst: Instance) -> str:
    """*Hash* del contenido (n, c, tiempos y arcos), independiente de id y meta.
    Sirve para descartar duplicados exactos."""
    payload = json.dumps([inst.n, inst.cycle_time, list(inst.times), [list(a) for a in inst.precedences]])
    return hashlib.sha256(payload.encode()).hexdigest()


# --------------------------------------------------------------- validación
def validate_instance(inst: Instance, require_topological: bool = True) -> list[str]:
    """Devuelve la lista de errores (vacía si la instancia es válida).

    Comprueba: n coincide con ``times``; tiempos enteros positivos; t_i ≤ c; arcos en 1..n;
    grafo acíclico; numeración topológica (i < j en todo arco) si P8 está activa.
    """
    errors: list[str] = []
    if not isinstance(inst.n, Integral) or inst.n < 1:
        errors.append(f"n inválido: {inst.n}")
        return errors
    if len(inst.times) != inst.n:
        errors.append(f"n = {inst.n} pero hay {len(inst.times)} tiempos")
    if not isinstance(inst.cycle_time, Integral) or inst.cycle_time <= 0:
        errors.append(f"tiempo de ciclo inválido: {inst.cycle_time}")
    for idx, t in enumerate(inst.times, start=1):
        if not isinstance(t, Integral) or isinstance(t, bool):
            errors.append(f"t_{idx} = {t!r} no es entero")
        elif t <= 0:
            errors.append(f"t_{idx} = {t} no es positivo")
        elif t > inst.cycle_time:
            errors.append(f"t_{idx} = {t} > c = {inst.cycle_time}")
    arcs_ok = True
    for i, j in inst.precedences:
        if not (1 <= i <= inst.n and 1 <= j <= inst.n):
            errors.append(f"arco ({i}, {j}) fuera de 1..{inst.n}")
            arcs_ok = False
        elif i == j:
            errors.append(f"arco ({i}, {j}) es un lazo")
            arcs_ok = False
        elif require_topological and i > j:
            errors.append(f"arco ({i}, {j}) no respeta la numeración topológica (P8)")
    if arcs_ok and len(inst.times) == inst.n:
        try:
            _ = inst.topological_order
        except ValueError as exc:
            errors.append(str(exc))
    return errors
