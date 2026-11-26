from salbp_selector.core import Instance, load_instance, run_rule, save_instance, validate_instance
from salbp_selector.core.io import content_hash, parse_in2, read_jsonl_gz, write_jsonl_gz

from ..conftest import random_instance


def test_static_attributes(hand_instance):
    inst = hand_instance
    assert inst.ns[1:] == (5, 4, 2, 3, 1, 1, 0)
    assert inst.nsi[1:] == (2, 1, 1, 2, 1, 1, 0)
    assert inst.pp[1:] == (26, 18, 11, 15, 6, 9, 4)
    assert inst.ci[1:] == (1, 1, 2, 2, 2, 2, 3)
    assert inst.cs[1:] == (5, 6, 6, 6, 7, 7, 7)
    assert inst.lb1 == 3
    # Clausura transitiva: 7 es sucesora de todas
    assert all((inst.succ_all[i] >> 7) & 1 for i in range(1, 7))
    assert abs(inst.order_strength - 2 * 16 / 42) < 1e-12  # |E*| = Σ NS_i = 16


def test_validation_detects_errors():
    ok = Instance("ok", 3, 10, (1, 2, 3), ((1, 2), (2, 3)))
    assert validate_instance(ok) == []
    assert validate_instance(Instance("a", 3, 10, (1, 2), ()))  # n no coincide
    assert validate_instance(Instance("b", 2, 10, (11, 1), ()))  # t > c
    assert validate_instance(Instance("c", 2, 10, (0, 1), ()))  # t no positivo
    assert validate_instance(Instance("d", 2, 10, (1, 1), ((1, 3),)))  # arco fuera de rango
    assert validate_instance(Instance("e", 2, 10, (1, 1), ((2, 1),)))  # no topológico
    cyc = Instance("f", 3, 10, (1, 1, 1), ((1, 2), (2, 3), (3, 1)))
    assert any("ciclo" in e for e in validate_instance(cyc, require_topological=False))


def test_json_and_alb_roundtrip(tmp_path, hand_instance):
    for ext in (".json", ".alb"):
        p = tmp_path / f"x{ext}"
        save_instance(hand_instance, p)
        back = load_instance(p)
        assert back.times == hand_instance.times
        assert back.precedences == hand_instance.precedences
        assert back.cycle_time == hand_instance.cycle_time
        for r in range(1, 13):
            assert run_rule(back, r).stations == run_rule(hand_instance, r).stations


def test_in2_parser():
    text = "4\n3\n5\n2\n4\n1,2\n1,3\n3,4\n-1,-1\n"
    inst = parse_in2(text, "toy", 10)
    assert inst.n == 4 and inst.times == (3, 5, 2, 4) and inst.precedences == ((1, 2), (1, 3), (3, 4))


def test_jsonl_gz_deterministic(tmp_path):
    insts = [random_instance(s) for s in range(20)]
    a, b = tmp_path / "a.jsonl.gz", tmp_path / "b.jsonl.gz"
    write_jsonl_gz(insts, a)
    write_jsonl_gz(insts, b)
    assert a.read_bytes() == b.read_bytes()
    back = list(read_jsonl_gz(a))
    assert [content_hash(i) for i in back] == [content_hash(i) for i in insts]
