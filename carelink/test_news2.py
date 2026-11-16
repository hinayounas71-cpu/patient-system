from news2 import check

def v(rr=16, spo2=98, bp=120, pulse=70, temp=37.0):
    return dict(resp_rate=rr, spo2=spo2, systolic_bp=bp, pulse=pulse, temp=temp)

def test_safe():
    r = check(v()); assert r.total == 0 and not r.unsafe

def test_single_3():
    r = check(v(spo2=90)); assert r.max_single == 3 and r.unsafe
    assert r.summary == "oxygen 90%"

def test_proposal_example_total_6():
    r = check(v(spo2=93, pulse=115, rr=22))
    assert r.total == 6 and r.max_single == 2 and r.unsafe

def test_total_4_no_alert():
    r = check(v(spo2=93, pulse=115)); assert r.total == 4 and not r.unsafe

def test_boundaries():
    assert check(v(temp=36.1)).scores["temp"] == 0
    assert check(v(temp=36.0)).scores["temp"] == 1
    assert check(v(temp=38.1)).scores["temp"] == 1
    assert check(v(temp=39.1)).scores["temp"] == 2
    assert check(v(temp=35.0)).scores["temp"] == 3
    assert check(v(pulse=50)).scores["pulse"] == 1
    assert check(v(pulse=91)).scores["pulse"] == 1
    assert check(v(pulse=131)).scores["pulse"] == 3
    assert check(v(bp=111)).scores["systolic_bp"] == 0
    assert check(v(bp=110)).scores["systolic_bp"] == 1
    assert check(v(bp=220)).scores["systolic_bp"] == 3
    assert check(v(rr=11)).scores["resp_rate"] == 1
    assert check(v(rr=12)).scores["resp_rate"] == 0
    assert check(v(rr=25)).scores["resp_rate"] == 3
    assert check(v(spo2=96)).scores["spo2"] == 0
    assert check(v(spo2=92)).scores["spo2"] == 2
