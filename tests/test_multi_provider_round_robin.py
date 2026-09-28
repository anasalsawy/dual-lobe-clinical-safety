from dual_lobe_crewai import runner


class Spec:
    def __init__(self, label):
        self.label = label


def test_round_robin_rotates_each_role_independently():
    runner._RR_INDEX.clear()
    specs = [Spec("p1"), Spec("p2"), Spec("p3")]

    assert [x.label for x in runner._round_robin_specs("A", specs)] == ["p1", "p2", "p3"]
    assert [x.label for x in runner._round_robin_specs("A", specs)] == ["p2", "p3", "p1"]
    assert [x.label for x in runner._round_robin_specs("A", specs)] == ["p3", "p1", "p2"]
    assert [x.label for x in runner._round_robin_specs("A", specs)] == ["p1", "p2", "p3"]

    # B maintains its own pointer.
    assert [x.label for x in runner._round_robin_specs("B_VERIFY", specs)] == ["p1", "p2", "p3"]


def test_round_robin_single_provider_is_unchanged():
    runner._RR_INDEX.clear()
    specs = [Spec("only")]
    assert [x.label for x in runner._round_robin_specs("A", specs)] == ["only"]


def test_round_robin_four_provider_sequence():
    runner._RR_INDEX.clear()
    specs = [Spec("1"), Spec("2"), Spec("3"), Spec("4")]
    starts = [
        runner._round_robin_specs("A", specs)[0].label
        for _ in range(8)
    ]
    assert starts == ["1", "2", "3", "4", "1", "2", "3", "4"]
