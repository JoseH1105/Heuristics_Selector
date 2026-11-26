"""Verificación de factibilidad independiente del motor.

Solo usa los datos crudos de la instancia (tiempos, arcos y c), sin las estructuras
derivadas ni el código del motor, para que las pruebas no se validen a sí mismas.
"""

from __future__ import annotations

from .instance import Instance


def verify_solution(inst: Instance, stations: list[list[int]]) -> list[str]:
    """Lista de errores (vacía si la solución es factible): cada tarea en una sola
    estación, carga ≤ c y precedencias respetadas (estación de i ≤ estación de j)."""
    errors: list[str] = []
    where: dict[int, int] = {}
    for k, st in enumerate(stations):
        load = 0
        for i in st:
            if i in where:
                errors.append(f"la tarea {i} aparece en las estaciones {where[i] + 1} y {k + 1}")
            where[i] = k
            load += inst.times[i - 1]
        if load > inst.cycle_time:
            errors.append(f"estación {k + 1}: carga {load} > c = {inst.cycle_time}")
    missing = set(range(1, inst.n + 1)) - set(where)
    if missing:
        errors.append(f"tareas sin asignar: {sorted(missing)}")
    for i, j in inst.precedences:
        if i in where and j in where and where[i] > where[j]:
            errors.append(f"precedencia ({i}, {j}) violada: estación {where[i] + 1} > {where[j] + 1}")
    # Dentro de una estación el orden también debe respetar las precedencias.
    for st in stations:
        pos = {i: p for p, i in enumerate(st)}
        for i, j in inst.precedences:
            if i in pos and j in pos and pos[i] > pos[j]:
                errors.append(f"precedencia ({i}, {j}) violada dentro de una estación")
    if any(len(st) == 0 for st in stations):
        errors.append("hay estaciones vacías")
    return errors
