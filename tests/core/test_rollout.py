import numpy as np

from salbp_selector.core import completions, initial_state, picks, run_cocktail, run_rollout, run_rule, verify_solution

from ..conftest import random_instance


def test_rollout_never_worse_than_cocktail():
    """Prueba de propiedad sobre 500 instancias aleatorias pequeñas."""
    for seed in range(500):
        inst = random_instance(seed, 5, 14)
        sol = run_rollout(inst)
        assert verify_solution(inst, sol.stations) == []
        assert sol.K <= run_cocktail(inst)["K_min"], seed
        assert sol.K >= inst.lb1


def test_completions_match_run_rule():
    inst = random_instance(42, 15, 15)
    ks = completions(initial_state(inst))
    assert ks.tolist() == [run_rule(inst, r).K for r in range(1, 13)]


def test_records_are_decision_states():
    for seed in range(50):
        inst = random_instance(seed, 8, 18)
        sol, recs = run_rollout(inst, record=True)
        assert sol.extra["n_decision_states"] == len(recs)
        for rec in recs:
            assert len(set(rec.picks)) > 1  # las reglas no eligen todas la misma tarea
            assert rec.completions.min() == rec.completions[rec.applied_rule - 1]
            assert np.array_equal(rec.completions, completions(rec.state))
        if recs:
            assert recs[-1].completions.min() == sol.K


def test_rollout_deterministic():
    inst = random_instance(7, 18, 18)
    assert run_rollout(inst).stations == run_rollout(inst).stations


def test_non_decision_when_all_rules_agree():
    from salbp_selector.core import Instance

    chain = Instance("chain", 4, 10, (3, 3, 3, 3), ((1, 2), (2, 3), (3, 4)))
    sol, recs = run_rollout(chain, record=True)
    assert recs == [] and sol.K == 2
    assert len(set(picks(initial_state(chain)))) == 1
