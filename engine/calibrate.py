"""Match the event rates of the engine to the literature.

The script simulates a large cohort, compares the share of patients with at
least one event of each type with the target from the literature, and adjusts
a factor per regimen and event type. The comparison uses patients with ECOG 0
or 1, who resemble trial patients, under usual care in the first 52 weeks. The factors are written to
config/calibration.json and used by generate.py.

Usage: python3 engine/calibrate.py
"""
import json
import math
import sys
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ENGINE_DIR.parent))
sys.path.insert(0, str(ENGINE_DIR))

import generate  # noqa: E402
import hazards  # noqa: E402


def realised_rates(patients, thresholds, regimens, params, iv, calibration):
    """Share of trial-like patients with at least one event, per regimen and
    type, under usual care within the calibration window."""
    table = hazards.HazardTable(regimens, params, calibration)
    limit = params["calibration"]["trial_like_maximum_ecog"]
    weeks = params["simulation"]["calibration_weeks"]
    counts = {name: {} for name in regimens}
    sizes = {name: 0 for name in regimens}
    for _, _, _, result, _ in generate.run(patients, thresholds, generate.USUAL_CARE,
                                           regimens, params, iv, table, weeks):
        patient = result["plan"]["patient"]
        if patient["ecog"] > limit:
            continue
        name = patient["regimen"]
        sizes[name] += 1
        seen = {e["event_type"] for e in result["events"] if e["event_type"] != hazards.ILD}
        if result["ild"]:
            seen.add(hazards.ILD)
        for event_type in seen:
            counts[name][event_type] = counts[name].get(event_type, 0) + 1
    return {name: {t: c / sizes[name] for t, c in counts[name].items()} for name in regimens}, table.targets


def calibrate(config=None, write=True, progress=None):
    """Return {"factors", "check"}. config is a configuration as
    generate.default_config() returns it; its calibration factors are ignored.
    With write=True the result goes to config/calibration.json."""
    config = config or generate.default_config()
    regimens, params, iv = config["regimens"], config["parameters"], config["interventions"]
    c = params["calibration"]
    patients, thresholds = generate.cohort(c["patients"], c["seed"], regimens, params, iv)
    factors = {name: {} for name in regimens}
    for iteration in range(c["iterations"] + 1):
        rates, targets = realised_rates(patients, thresholds, regimens, params, iv, factors)
        if progress:
            progress(iteration + 1, c["iterations"] + 1)
        if iteration == c["iterations"]:
            break
        for name in regimens:
            for event_type, target in targets[name].items():
                if target <= 0:
                    continue
                rate = rates[name].get(event_type, 0.0)
                step = 2.0 if rate <= 0 else math.log(1 - target) / math.log(1 - min(rate, 0.999))
                step = max(0.5, min(2.0, step)) ** 0.8  # damped, because the rates are noisy
                factors[name][event_type] = factors[name].get(event_type, 1.0) * step
    check = {
        name: {t: {"target": round(targets[name][t], 4), "realised": round(rates[name].get(t, 0.0), 4)}
               for t in targets[name]}
        for name in regimens
    }
    result = {
        "description": "Calibration factors per regimen and event type, written by calibrate.py. 'check' compares the target from the literature with the realised share of patients with ECOG 0 or 1 in the calibration cohort.",
        "patients": c["patients"],
        "factors": {n: {t: round(f, 4) for t, f in v.items()} for n, v in factors.items()},
        "check": check,
    }
    if write:
        with open(ENGINE_DIR / "config" / "calibration.json", "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
    return result


if __name__ == "__main__":
    out = calibrate(progress=lambda done, total: print(f"round {done} of {total} done"))
    print(f"{'regimen':<28}{'event type':<27}{'target':>8}{'realised':>10}")
    for name, types in out["check"].items():
        for event_type, v in types.items():
            print(f"{name:<28}{event_type:<27}{v['target']:>8.1%}{v['realised']:>10.1%}")
