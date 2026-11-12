"""Generate synthetic patients and their course over time.

Usage: python3 engine/generate.py --n 3000 --seed 1 --out engine/output
"""
import argparse
import csv
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
import measurements  # noqa: E402
import population  # noqa: E402


def load_config():
    with open(ENGINE_DIR / "config" / "regimens.json", encoding="utf-8") as f:
        regimens = json.load(f)["regimens"]
    with open(ENGINE_DIR / "config" / "parameters.json", encoding="utf-8") as f:
        params = json.load(f)
    return regimens, params


def load_calibration():
    path = ENGINE_DIR / "config" / "calibration.json"
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)["factors"]


def generate(n, seed, validate=True):
    """Return a dictionary with the four tables and metadata."""
    regimens, params = load_config()
    rng = random.Random(seed)
    table = hazards.HazardTable(regimens, params, load_calibration())
    data = {"baseline": [], "observation": [], "event": [], "outcome": []}
    for patient, latent in population.draw_cohort(rng, n, regimens, params):
        regimen = regimens[patient["regimen"]]
        rows, mult = table.for_patient(patient, latent)
        result = course.simulate(rng, patient, latent, regimen, params, rows)
        data["baseline"].append(patient)
        data["event"].extend(result["events"])
        data["outcome"].append(course.outcome(patient, result))
        data["observation"].extend(
            measurements.observations(rng, patient, latent, regimen, params, result, mult)
        )
    if validate:
        for name in toxage_schema.TABLES:
            toxage_schema.validate(name, data[name])
    data["metadata"] = {
        "n": n,
        "seed": seed,
        "weeks": params["simulation"]["weeks"],
        "schema_version": {t: toxage_schema.load(t)["version"] for t in toxage_schema.TABLES},
    }
    return data


def _cell(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return value


def write_csv(path, table, records):
    names = toxage_schema.fields(table)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(names)
        for record in records:
            writer.writerow([_cell(record[name]) for name in names])


def summary(data):
    """Return one row of key rates per regimen."""
    outcome = {o["patient_id"]: o for o in data["outcome"]}
    events = {}
    for e in data["event"]:
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
            "dose_reduced": share(lambda i: any(e["action"] == "dose_reduction" for e in events.get(i, []))),
            "stopped_for_toxicity": share(lambda i: outcome[i]["treatment_end_reason"] == "toxicity"),
            "died": share(lambda i: outcome[i]["death_day"] is not None),
        })
    return rows


def print_summary(data):
    print(f"{'regimen':<28}{'n':>6}{'severe':>8}{'severe':>8}{'lung':>7}{'dose':>9}{'stopped':>9}{'died':>7}")
    print(f"{'':<28}{'':>6}{'90 d':>8}{'any':>8}{'tox':>7}{'reduced':>9}{'for tox':>9}{'':>7}")
    for r in summary(data):
        print(f"{r['regimen']:<28}{r['n']:>6}{r['severe_90d']:>8.1%}{r['severe_any']:>8.1%}{r['ild']:>7.1%}"
              f"{r['dose_reduced']:>9.1%}{r['stopped_for_toxicity']:>9.1%}{r['died']:>7.1%}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--n", type=int, default=3000, help="number of patients, split equally over the three tumour types")
    parser.add_argument("--seed", type=int, default=1, help="random seed")
    parser.add_argument("--out", default=str(ENGINE_DIR / "output"), help="output folder")
    args = parser.parse_args()

    data = generate(args.n, args.seed)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for name in toxage_schema.TABLES:
        write_csv(out / f"{name}.csv", name, data[name])
    with open(out / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(data["metadata"], f, indent=2)

    print(f"{args.n} patients written to {out}: "
          + ", ".join(f"{len(data[name])} {name} records" for name in toxage_schema.TABLES))
    print_summary(data)


if __name__ == "__main__":
    main()
