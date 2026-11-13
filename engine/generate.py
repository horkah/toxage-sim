"""Generate synthetic patients and their course over time, under one or
several intervention scenarios.

Usage: python3 engine/generate.py --n 3000 --seed 1 --out engine/output
"""
import argparse
import json
import random
import sys
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ENGINE_DIR.parent))
sys.path.insert(0, str(ENGINE_DIR))

from schema import toxage_schema  # noqa: E402
import course  # noqa: E402
import hazards  # noqa: E402
import interventions  # noqa: E402
import measurements  # noqa: E402
import population  # noqa: E402
from draws import Draws  # noqa: E402

# Tables of the central schema that the engine writes.
TABLES = ("scenario", "baseline", "observation", "event", "alert", "outcome")
USUAL_CARE = "usual_care"


def _read(name):
    with open(ENGINE_DIR / "config" / name, encoding="utf-8") as f:
        return json.load(f)


def load_config():
    """Return (regimens, parameters) as stored in the repository."""
    return _read("regimens.json")["regimens"], _read("parameters.json")


def load_interventions():
    return _read("interventions.json")


def load_calibration():
    path = ENGINE_DIR / "config" / "calibration.json"
    return _read("calibration.json")["factors"] if path.exists() else {}


def default_config():
    """The whole configuration of the engine as one dictionary. A caller can
    change values in a copy and pass it to generate()."""
    regimens, params = load_config()
    return {"regimens": regimens, "parameters": params,
            "interventions": load_interventions(), "calibration": load_calibration()}


def cohort(n, seed, regimens, params, iv):
    """Return the patients with everything that is the same in all scenarios:
    (baseline record, latent values, fixed random numbers, predictor scores)."""
    rng = random.Random(seed)
    patients = []
    for index, (patient, latent) in enumerate(population.draw_cohort(rng, n, regimens, params)):
        draws = Draws(seed, index)
        scores = {perfect: interventions.predictor_score(patient, latent, draws, params, iv, perfect)
                  for perfect in (False, True)}
        patients.append((patient, latent, draws, scores))
    thresholds = {perfect: interventions.flag_threshold([s[perfect] for *_, s in patients], iv)
                  for perfect in (False, True)}
    return patients, thresholds


def run(patients, thresholds, scenario_id, regimens, params, iv, table, weeks=None):
    """Simulate all patients under one scenario. Yields (latent, plan, course, multipliers)."""
    scenario = iv["scenarios"][scenario_id]
    for patient, latent, draws, scores in patients:
        regimen = regimens[patient["regimen"]]
        perfect = scenario["perfect"]
        plan = interventions.plan(patient, latent, regimen, draws, scenario, params, iv,
                                  scores[perfect], thresholds[perfect])
        plan["scenario_id"] = scenario_id
        rows, mult = table.for_patient(plan["patient"], latent, plan["general_factor"])
        result = course.simulate(draws, latent, regimen, params, iv, plan, rows, weeks)
        yield latent, draws, regimen, result, mult


def generate(n, seed, scenarios=None, validate=True, config=None, progress=None):
    """Return a dictionary with the tables and metadata.

    scenarios is a list of scenario ids; the default is all scenarios of the
    configuration. config is a configuration as default_config() returns it.
    progress, if given, is called with (scenarios done, scenarios in total).
    """
    config = config or default_config()
    regimens, params, iv = config["regimens"], config["parameters"], config["interventions"]
    scenarios = list(scenarios or iv["scenarios"])
    table = hazards.HazardTable(regimens, params, config["calibration"])
    patients, thresholds = cohort(n, seed, regimens, params, iv)
    data = {name: [] for name in TABLES}
    data["baseline"] = [p for p, *_ in patients]
    for scenario_id in scenarios:
        s = iv["scenarios"][scenario_id]
        data["scenario"].append({
            "scenario_id": scenario_id, "title": s["title"], "description": s["description"],
            **{c: c in s["components"] for c in interventions.COMPONENTS},
        })
        for latent, draws, regimen, result, mult in run(
                patients, thresholds, scenario_id, regimens, params, iv, table):
            data["event"].extend(result["events"])
            data["alert"].extend(result["alerts"])
            data["outcome"].append(course.outcome(latent, result, iv))
            data["observation"].extend(
                measurements.observations(draws, latent, regimen, params, result, mult))
        if progress:
            progress(len(data["scenario"]), len(scenarios))
    if validate:
        for name in TABLES:
            toxage_schema.validate(name, data[name])
    data["metadata"] = {
        "n": n,
        "seed": seed,
        "weeks": params["simulation"]["weeks"],
        "scenarios": scenarios,
        "schema_version": {t: toxage_schema.load(t)["version"] for t in TABLES},
    }
    return data


def of_scenario(records, scenario_id=USUAL_CARE):
    """Records of one scenario."""
    return [r for r in records if r["scenario_id"] == scenario_id]


def scenario_summary(data):
    """Return one row of key numbers per scenario."""
    n = len(data["baseline"])
    rows = []
    for s in data["scenario"]:
        sid = s["scenario_id"]
        outcomes = of_scenario(data["outcome"], sid)
        events = of_scenario(data["event"], sid)
        mean = lambda key: sum(o[key] for o in outcomes) / n
        rows.append({
            "scenario_id": sid,
            "participating": mean("participating"),
            "severe_90d": mean("severe_toxicity_90d"),
            "severe_events": sum(e["grade"] >= 3 for e in events) / n,
            "cv_events": sum(o["cv_event"] for o in outcomes),
            "toxic_deaths": sum(o["death_from_toxicity"] for o in outcomes),
            "hospital_days": mean("hospital_days"),
            "alerts": mean("alerts"),
            "qaly": mean("qaly"),
            "cost_care": mean("cost_care"),
            "cost_intervention": mean("cost_intervention"),
        })
    return rows


def summary(data, scenario_id=USUAL_CARE):
    """Return one row of key rates per regimen for one scenario."""
    outcome = {o["patient_id"]: o for o in of_scenario(data["outcome"], scenario_id)}
    events = {}
    for e in of_scenario(data["event"], scenario_id):
        events.setdefault(e["patient_id"], []).append(e)
    rows = []
    for regimen in toxage_schema.allowed_values("baseline", "regimen"):
        ids = [p["patient_id"] for p in data["baseline"] if p["regimen"] == regimen]
        if not ids:
            continue
        share = lambda test: sum(test(i) for i in ids) / len(ids)
        rows.append({
            "regimen": regimen,
            "n": len(ids),
            "severe_90d": share(lambda i: outcome[i]["severe_toxicity_90d"]),
            "severe_any": share(lambda i: any(e["grade"] >= 3 for e in events.get(i, []))),
            "ild": share(lambda i: outcome[i]["ild"]),
            "cv_event": share(lambda i: outcome[i]["cv_event"]),
            "dose_reduced": share(lambda i: any(e["action"] == "dose_reduction" for e in events.get(i, []))),
            "stopped_for_toxicity": share(lambda i: outcome[i]["treatment_end_reason"] == "toxicity"),
            "died": share(lambda i: outcome[i]["death_day"] is not None),
        })
    return rows


def print_summary(data):
    if any(s["scenario_id"] == USUAL_CARE for s in data["scenario"]):
        print("\nUsual care, by regimen")
        print(f"{'regimen':<28}{'n':>6}{'severe':>8}{'severe':>8}{'lung':>7}{'heart':>8}{'dose':>9}{'stopped':>9}{'died':>7}")
        print(f"{'':<28}{'':>6}{'90 d':>8}{'any':>8}{'tox':>7}{'event':>8}{'reduced':>9}{'for tox':>9}{'':>7}")
        for r in summary(data):
            print(f"{r['regimen']:<28}{r['n']:>6}{r['severe_90d']:>8.1%}{r['severe_any']:>8.1%}{r['ild']:>7.1%}{r['cv_event']:>8.1%}"
                  f"{r['dose_reduced']:>9.1%}{r['stopped_for_toxicity']:>9.1%}{r['died']:>7.1%}")
    print("\nScenarios, per patient")
    print(f"{'scenario':<27}{'taking':>8}{'severe':>8}{'severe':>8}{'heart':>8}{'toxic':>8}{'hospital':>10}{'alerts':>8}"
          f"{'QALY':>8}{'cost of':>9}{'cost of':>9}")
    print(f"{'':<27}{'part':>8}{'90 d':>8}{'events':>8}{'events':>8}{'deaths':>8}{'days':>10}{'':>8}{'':>8}{'care':>9}{'interv.':>9}")
    for r in scenario_summary(data):
        print(f"{r['scenario_id']:<27}{r['participating']:>8.1%}{r['severe_90d']:>8.1%}{r['severe_events']:>8.2f}"
              f"{r['cv_events']:>8}{r['toxic_deaths']:>8}{r['hospital_days']:>10.2f}{r['alerts']:>8.2f}{r['qaly']:>8.3f}"
              f"{r['cost_care']:>9.0f}{r['cost_intervention']:>9.0f}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--n", type=int, default=3000, help="number of patients, split equally over the three tumour types")
    parser.add_argument("--seed", type=int, default=1, help="random seed")
    parser.add_argument("--out", default=str(ENGINE_DIR / "output"), help="output folder")
    parser.add_argument("--scenarios", nargs="*", help="scenario ids; default: all")
    args = parser.parse_args()

    data = generate(args.n, args.seed, args.scenarios)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for name in TABLES:
        toxage_schema.write_csv(out / f"{name}.csv", name, data[name])
    with open(out / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(data["metadata"], f, indent=2)

    print(f"{args.n} patients written to {out}: "
          + ", ".join(f"{len(data[name])} {name} records" for name in TABLES))
    print_summary(data)


if __name__ == "__main__":
    main()
