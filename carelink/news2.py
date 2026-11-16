"""Safe-limit check (NEWS2 style). Simple if-then rules, no AI.
Source: Royal College of Physicians, NEWS2 (2017). 5 measurements, SpO2 scale 1."""
from dataclasses import dataclass

LABELS = {
    "resp_rate": ("breathing rate", "/min"),
    "spo2": ("oxygen", "%"),
    "systolic_bp": ("BP", " mmHg"),
    "pulse": ("pulse", "/min"),
    "temp": ("temperature", " C"),
}


def score_resp_rate(v):
    if v <= 8 or v >= 25: return 3
    if v >= 21: return 2
    if v >= 9 and v <= 11: return 1
    return 0


def score_spo2(v):
    if v <= 91: return 3
    if v <= 93: return 2
    if v <= 95: return 1
    return 0


def score_systolic_bp(v):
    if v <= 90 or v >= 220: return 3
    if v <= 100: return 2
    if v <= 110: return 1
    return 0


def score_pulse(v):
    if v <= 40 or v >= 131: return 3
    if v >= 111: return 2
    if v <= 50 or v >= 91: return 1
    return 0


def score_temp(v):
    if v <= 35.0: return 3
    if v >= 39.1: return 2
    if v <= 36.0 or v >= 38.1: return 1
    return 0


SCORERS = {
    "resp_rate": score_resp_rate,
    "spo2": score_spo2,
    "systolic_bp": score_systolic_bp,
    "pulse": score_pulse,
    "temp": score_temp,
}


@dataclass
class Result:
    scores: dict
    total: int
    max_single: int
    unsafe: bool
    summary: str


def check(values: dict) -> Result:
    """values: resp_rate, spo2, systolic_bp, pulse, temp"""
    scores = {k: SCORERS[k](values[k]) for k in SCORERS}
    total = sum(scores.values())
    max_single = max(scores.values())
    # Alert rule: any one value has score 3, OR total score is 5 or more
    unsafe = max_single == 3 or total >= 5

    # Words for the alert: show the worst values only
    shown = [k for k, s in scores.items() if s >= 2] or [k for k, s in scores.items() if s > 0]
    shown.sort(key=lambda k: -scores[k])
    parts = []
    for k in shown:
        name, unit = LABELS[k]
        parts.append(f"{name} {values[k]}{unit}")
    return Result(scores, total, max_single, unsafe, ", ".join(parts))
