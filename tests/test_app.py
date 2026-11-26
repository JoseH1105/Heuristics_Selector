"""Prueba de humo de la app del generador con streamlit.testing (sin navegador)."""

from pathlib import Path

import pytest

AppTest = pytest.importorskip("streamlit.testing.v1").AppTest
APP = str(Path(__file__).resolve().parents[1] / "apps" / "generator_app.py")


def _run(at):
    at.run(timeout=60)
    assert not at.exception, [e.value for e in at.exception]
    return at


def test_empty_state_and_example():
    at = _run(AppTest.from_file(APP))
    next(b for b in at.button if b.label.startswith("Probar con un ejemplo")).click()
    _run(at)
    assert at.session_state["inst"].instance_id.startswith("gen-v1-core-n20")


@pytest.mark.parametrize("structure, n", [("chain", 100), ("bottleneck", 50), ("mixed", 20)])
def test_generate_and_all_views(structure, n):
    at = _run(AppTest.from_file(APP))
    at.segmented_control(key="n").set_value(n)
    at.segmented_control(key="structure").set_value(structure)
    _run(at)
    next(b for b in at.button if b.label == "Generar instancia").click()
    _run(at)
    # colorear por estación y resaltar una tarea
    at.segmented_control(key="color_mode").set_value("Estación")
    _run(at)
    at.selectbox(key="focus_task").set_value(3)
    _run(at)
    # rollout
    next(b for b in at.button if b.label == "Ejecutar rollout").click()
    _run(at)
    assert at.session_state["rollout"].K >= 1


def test_extended_layer():
    at = _run(AppTest.from_file(APP))
    at.segmented_control(key="layer").set_value("extended")
    _run(at)
    next(b for b in at.button if b.label == "Generar instancia").click()
    _run(at)
    assert at.session_state["inst"].meta["layer"] == "extended"
