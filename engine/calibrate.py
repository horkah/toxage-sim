"""Match the event rates of the engine to the literature.

The script simulates a large cohort, compares the share of patients with at
least one event of each type with the target from the literature, and adjusts
a factor per regimen and event type. The comparison uses patients with ECOG 0
or 1, who resemble trial patients. The factors are written to
config/calibration.json and used by generate.py.

Usage: python3 engine/calibrate.py
"""
import json
import math
import random
import sys
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ENGINE_DIR.parent))
sys.path.insert(0, str(ENGINE_DIR))

import course  # noqa: E402
import hazards  # noqa: E402
import population  # noqa: E402
from generate import load_config  # noqa: E402


def realised_rates(patients, regimens, params, calibration, seed):
    """Share of trial-like patients with at least one event, per regimen and type."""
    rng = random.Random(seed)
    table = hazards.HazardTable(regimens, params, calibration)
    limit = params["calibration"]["trial_like_maximum_ecog"]
    counts = {name: {} for name in regimens}
    sizes = {name: 0 for name in regimens}
    for patient, latent in patients:
        rows, _ = table.for_patient(patient, latent)
        result = course.simulate(rng, patient, latent, regimens[patient["regimen"]], params, rows)
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


def calibrate():
    regimens, params = load_config()
    c = params["calibration"]
    rng = random.Random(c["seed"])
    patients = population.draw_cohort(rng, c["patients"], regimens, params)
    factors = {name: {} for name in regimens}
    for iteration in range(c["iterations"] + 1):
        rates, targets = realised_rates(patients, regimens, params, factors, c["seed"] + 1)
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
        print(f"iteration {iteration + 1} done")
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
    with open(ENGINE_DIR / "config" / "calibration.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    return result


if __name__ == "__main__":
    out = calibrate()
    print(f"{'regimen':<28}{'event type':<27}{'target':>8}{'realised':>10}")
    for name, types in out["check"].items():
        for event_type, v in types.items():
            print(f"{name:<28}{event_type:<27}{v['target']:>8.1%}{v['realised']:>10.1%}")
