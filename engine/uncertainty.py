"""Uncertainty of the results: repeat the simulation with parameters drawn
from their published uncertainty.

Each draw takes the ratios, shares and regimen rates of config/uncertainty.json
from their distributions and simulates the same patients, with the same fixed
random numbers, under the chosen scenarios. What differs between two draws is
therefore the parameters alone. The result is, per scenario, the mean and the
2.5% and 97.5% quantiles of the key numbers and of their differences to usual
care.

Only parameters with a published interval or a known number of patients are
drawn. Assumptions keep their value, and the calibration is not repeated, so
the intervals show a part of the uncertainty, not all of it.

Usage: python3 engine/uncertainty.py --n 1500 --draws 40 --seed 1
"""
import argparse
import copy
import json
import math
import random
import sys
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ENGINE_DIR.parent))
sys.path.insert(0, str(ENGINE_DIR))

import generate  # noqa: E402

SCENARIOS = ("usual_care", "risk_adapted_start", "model_guided_start", "symptom_monitoring", "combined")
# Key numbers per scenario: name, title, function of (outcome records, number of patients).
MEASURES = (
    ("severe_90d", "Severe toxicity, 90 days", lambda rows, n: sum(o["severe_toxicity_90d"] for o in rows) / n),
    ("toxic_deaths", "Deaths from toxicity per 1000", lambda rows, n: 1000 * sum(o["death_from_toxicity"] for o in rows) / n),
    ("hospital_days", "Hospital days", lambda rows, n: sum(o["hospital_days"] for o in rows) / n),
    ("qaly", "QALY", lambda rows, n: sum(o["qaly"] for o in rows) / n),
    ("cost", "Cost of care and intervention", lambda rows, n: sum(o["cost_care"] + o["cost_intervention"] for o in rows) / n),
)


def load_uncertainty():
    """The uncertain parameters as stored in the repository."""
    with open(ENGINE_DIR / "config" / "uncertainty.json", encoding="utf-8") as f:
        return json.load(f)


def _get(config, path):
    """Value at a path such as parameters/hazards/dose_exponent/value."""
    node = config
    for key in path.split("/"):
        node = node[key]
    return node


def _set(config, path, value):
    """Set the value at a path."""
    *keys, last = path.split("/")
    node = config
    for key in keys:
        node = node[key]
    node[last] = value


def _beta(rng, share, patients):
    """A share drawn from the beta distribution of an observed share among a
    number of patients (Jeffreys prior), kept away from 0 and 1."""
    events = share * patients
    return min(0.999, max(1e-6, rng.betavariate(events + 0.5, patients - events + 0.5)))


def draw_config(rng, config, uncertainty):
    """Return a copy of the configuration with the uncertain parameters drawn,
    and the drawn values as {name: value}."""
    drawn_config, drawn = copy.deepcopy(config), {}
    for entry in uncertainty["ratios"]:
        low, high = entry["interval"]
        sigma = (math.log(high) - math.log(low)) / (2 * 1.96)
        value = _get(config, entry["paths"][0]) * math.exp(rng.gauss(0, sigma))
        for path in entry["paths"]:
            _set(drawn_config, path, value)
        drawn[entry["name"]] = value
    for entry in uncertainty["shares"]:
        observed = entry["events"] / entry["patients"]
        # The draw is taken around the value of the configuration, with the
        # spread of the observed share.
        value = _get(config, entry["paths"][0]) * _beta(rng, observed, entry["patients"]) / observed
        for path in entry["paths"]:
            _set(drawn_config, path, value)
        drawn[entry["name"]] = value
    for name, patients in uncertainty["regimen_patients"].items():
        if name == "basis" or name not in drawn_config["regimens"]:
            continue
        regimen = drawn_config["regimens"][name]
        regimen["severe_toxicity_rate"] = _beta(rng, regimen["severe_toxicity_rate"], patients)
        drawn[f"{name}: severe toxicity"] = regimen["severe_toxicity_rate"]
        for event_type, rate in regimen["severe_event_rates"].items():
            regimen["severe_event_rates"][event_type] = _beta(rng, rate, patients)
        if regimen["ild_rate"] is not None:
            regimen["ild_rate"] = _beta(rng, regimen["ild_rate"], patients)
    # One rate of cardiovascular events for all regimens with androgen deprivation.
    rates = {r["cardiovascular_event_rate"] for r in config["regimens"].values()} - {None}
    for rate in rates:
        value = _beta(rng, rate, uncertainty["cardiovascular_rate_patients"]["value"])
        for regimen in drawn_config["regimens"].values():
            if regimen["cardiovascular_event_rate"] == rate:
                regimen["cardiovascular_event_rate"] = value
        drawn["Cardiovascular event rate under an agonist"] = value
    return drawn_config, drawn


def key_numbers(data):
    """{scenario: {measure: value}} of one simulated data set."""
    n = len(data["baseline"])
    return {s["scenario_id"]: {name: f(generate.of_scenario(data["outcome"], s["scenario_id"]), n)
                               for name, _, f in MEASURES}
            for s in data["scenario"]}


def _quantile(values, q):
    """Quantile of a list by linear interpolation."""
    ordered = sorted(values)
    position = q * (len(ordered) - 1)
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def _summary(values):
    """Mean and 95% interval of the values of all draws."""
    return {"mean": sum(values) / len(values), "low": _quantile(values, 0.025), "high": _quantile(values, 0.975)}


def analyse(n, draws, seed=1, scenarios=SCENARIOS, config=None, uncertainty=None, progress=None):
    """Simulate n patients under the scenarios once per draw.

    Returns {"draws": the drawn values, "scenarios": {scenario: {measure:
    {"value": summary, "difference": summary of the difference to usual
    care}}}}. The patients and their random numbers are the same in every
    draw (seed); the parameters come from a generator of their own.
    """
    config = config or generate.default_config()
    uncertainty = uncertainty or load_uncertainty()
    scenarios = list(scenarios)
    if generate.USUAL_CARE not in scenarios:
        scenarios.insert(0, generate.USUAL_CARE)
    rng = random.Random(f"uncertainty-{seed}")
    results, drawn_values = [], []
    for i in range(draws):
        drawn_config, drawn = draw_config(rng, config, uncertainty)
        results.append(key_numbers(generate.generate(n, seed, scenarios, validate=False, config=drawn_config)))
        drawn_values.append(drawn)
        if progress:
            progress(i + 1, draws)
    out = {}
    for s in scenarios:
        out[s] = {}
        for name, _, _ in MEASURES:
            values = [r[s][name] for r in results]
            differences = [r[s][name] - r[generate.USUAL_CARE][name] for r in results]
            out[s][name] = {"value": _summary(values), "difference": _summary(differences)}
    return {"n": n, "draws": draws, "seed": seed, "drawn": drawn_values, "scenarios": out}


def report(result):
    """The analysis as a text table."""
    lines = [f"{result['n']} patients, {result['draws']} draws of the parameters. "
             "Mean and 95% interval over the draws; differences are against usual care."]
    for name, title, _ in MEASURES:
        lines.append(f"\n{title}")
        lines.append(f"  {'scenario':<24}{'value':>30}{'difference':>34}")
        for s, measures in result["scenarios"].items():
            v, d = measures[name]["value"], measures[name]["difference"]
            fmt = (lambda x: f"{x:.1%}") if name == "severe_90d" else (lambda x: f"{x:.3f}") if name == "qaly" else (lambda x: f"{x:.1f}")
            lines.append(f"  {s:<24}{fmt(v['mean']):>10} ({fmt(v['low'])} to {fmt(v['high'])})".ljust(58)
                         + f"{fmt(d['mean']):>10} ({fmt(d['low'])} to {fmt(d['high'])})")
    return "\n".join(lines)


def main():
    """Command line: run the analysis and print the table."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--n", type=int, default=1500, help="number of patients per draw")
    parser.add_argument("--draws", type=int, default=40, help="number of draws of the parameters")
    parser.add_argument("--seed", type=int, default=1, help="seed of the patients and of the draws")
    parser.add_argument("--scenarios", nargs="*", default=list(SCENARIOS), help="scenario ids")
    parser.add_argument("--out", help="JSON file for the full result")
    args = parser.parse_args()
    result = analyse(args.n, args.draws, args.seed, args.scenarios,
                     progress=lambda done, total: print(f"draw {done} of {total}", file=sys.stderr))
    print(report(result))
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)


if __name__ == "__main__":
    main()
