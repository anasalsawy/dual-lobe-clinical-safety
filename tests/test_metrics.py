from dual_lobe_clinical.evaluation_metrics import calculate


def row(case_id,truth,findings,decision=None):
    result={"merged_assessment":{"findings":findings}}
    if decision is not None:
        result["gate"]={"decision":decision}
    return {"case_id":case_id,"gold":{"material_hazard_present":truth},"result":result}


def test_metrics_count_false_alarm_and_unnecessary_block():
    rows=[
        row("p",True,[{"x":1}],"block"),
        row("n",False,[{"x":1}],"block"),
    ]
    m=calculate(rows)
    assert m["tp"]==1
    assert m["fp"]==1
    assert m["unnecessary_block_count"]==1
    assert m["unsafe_release_count"]==0


def test_metrics_count_unsafe_release():
    m=calculate([row("p",True,[],"pass")])
    assert m["fn"]==1
    assert m["unsafe_release_count"]==1
    assert m["unsafe_release_rate"]==1.0
