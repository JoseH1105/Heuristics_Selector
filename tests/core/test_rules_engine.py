"""Motor y reglas.

Instancia de 7 tareas (c = 10), tiempos (6, 3, 5, 4, 2, 5, 4) y arcos
1→3, 1→4, 2→4, 3→5, 4→5, 4→6, 5→7, 6→7. Soluciones calculadas a mano:

- R8 (menor número):   [1,2] [3,4] [5,6] [7]  → K = 4
- R2 (mayor tiempo):   [1,2] [3,4] [6,5] [7]  → K = 4
- R1 (peso posicional, PP = 26,18,11,15,6,9,4): [1,2] [4,3] [6,5] [7] → K = 4
"""

import pytest

from salbp_selector.core import (
    RULE_IDS, Instance, initial_state, run, run_cocktail, run_rule, step, verify_solution,
)
from salbp_selector.core.engine import complete_k
from salbp_selector.core.rules import RULES, TIEBREAKS, rank_vector

from ..conftest import random_instance


@pytest.mark.parametrize("rule, expected", [
    (8, [[1, 2], [3, 4], [5, 6], [7]]),
    (2, [[1, 2], [3, 4], [6, 5], [7]]),
    (1, [[1, 2], [4, 3], [6, 5], [7]]),
])
def test_hand_solutions(hand_instance, rule, expected):
    sol = run_rule(hand_instance, rule)
    assert sol.stations == expected
    assert sol.K == 4


def test_rule_table_complete():
    assert sorted(RULES) == list(range(1, 13))
    assert {r.sense for r in RULES.values()} == {"max", "min"}


def test_all_rules_feasible_and_above_lb1():
    for seed in range(150):
        inst = random_instance(seed, 5, 25)
        for tb in TIEBREAKS:
            for r in RULE_IDS:
                sol = run_rule(inst, r, tiebreak=tb)
                assert verify_solution(inst, sol.stations) == [], (seed, r, tb)
                assert sol.K >= inst.lb1


def test_determinism(hand_instance):
    inst = random_instance(3, 20, 20)
    for r in RULE_IDS:
        assert run_rule(inst, r).stations == run_rule(inst, r).stations


def test_sequential_consistency():
    """Un step con r y luego completar con r da el mismo K que completar con r desde el inicio."""
    for seed in range(100):
        inst = random_instance(seed, 5, 20)
        s0 = initial_state(inst)
        for r in RULE_IDS:
            k_full = run_rule(inst, r).K
            assert complete_k(s0, r) == k_full
            s1 = step(s0, r)
            assert complete_k(s1, r) == k_full
            assert s0.step == 0  # step no modifica el estado original


def test_r11_zero_slack_does_not_fail():
    inst = Instance("zero-slack", 2, 10, (10, 10), ((1, 2),))
    assert inst.cs[1] - inst.ci[1] == 0
    assert run_rule(inst, 11).K == 2


def test_fraction_ties_are_exact():
    # PP/(NS+1): 6/3 = 2 y 4/2 = 2 → empate exacto, gana el menor índice
    inst = Instance("frac", 5, 100, (2, 2, 2, 2, 2), ((1, 2), (1, 3), (4, 5)))
    assert inst.pp[1] == 6 and inst.ns[1] == 2 and inst.pp[4] == 4 and inst.ns[4] == 1
    assert RULES[12].value(inst, 1) == RULES[12].value(inst, 4) == 2
    rank = rank_vector(inst, 12)
    assert rank[1] < rank[4]
    rank_tb = rank_vector(inst, 12, "largest_pp")
    assert rank_tb[1] < rank_tb[4]  # con desempate por PP también gana la tarea 1 (PP 6 > 4)


def test_cocktail_is_min(hand_instance):
    res = run_cocktail(hand_instance)
    assert res["K_min"] == min(res["K"].values())
    assert res["best_rules"] == [r for r in RULE_IDS if res["K"][r] == res["K_min"]]


def test_run_with_policy_switching_rules():
    inst = random_instance(11, 15, 15)
    sol = run(inst, lambda s: (s.step % 12) + 1)
    assert verify_solution(inst, sol.stations) == []
    assert sol.rule_sequence[:3] == [1, 2, 3]
