"""Generate synthetic patients with baseline data and toxicity outcomes.

Usage: python3 engine/generate.py --n 5000 --seed 1 --out engine/output
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
import population  # noqa: E402
import toxicity  # noqa: E402


def load_config():
    with open(ENGINE_DIR / "config" / "regimens.json", encoding="utf-8") as f:
        regimens = json.load(f)["regimens"]
    with open(ENGINE_DIR / "config" / "parameters.json", encoding="utf-8") as f:
        params = json.load(f)
    return regimens, params


def generate(n, seed):
    """Return (baseline records, outcome records, metadata)."""
    regimens, params = load_config()
    rng = random.Random(seed)
    baseline = [population.draw_baseline(rng, i + 1, regimens, params) for i in range(n)]

    ild_baseline_risks = {}
    for name, regimen in regimens.items():
        if regimen["ild_rate"] is not None:
            group = [p for p in baseline if p["regimen"] == name]
            ild_baseline_risks[name] = toxicity.calibrate_ild_baseline_risk(
                group, regimen["ild_rate"], params
            )

    outcomes = [
        toxicity.draw_outcome(rng, p, regimens, params, ild_baseline_risks)
        for p in baseline
    ]
    toxage_schema.validate("baseline", baseline)
    toxage_schema.validate("outcome", outcomes)
    metadata = {
        "n": n,
        "seed": seed,
        "schema_version": {t: toxage_schema.load(t)["version"] for t in toxage_schema.TABLES},
        "ild_baseline_risks": ild_baseline_risks,
    }
    return baseline, outcomes, metadata


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


def summary(baseline, outcomes):
    """Return rows (regimen, n, severe toxicity rate, lung toxicity rate)."""
    by_id = {o["patient_id"]: o for o in outcomes}
    rows = []
    for regimen in toxage_schema.allowed_values("baseline", "regimen"):
        group = [by_id[p["patient_id"]] for p in baseline if p["regimen"] == regimen]
        if group:
            rows.append((
                regimen,
                len(group),
                sum(o["severe_toxicity_90d"] for o in group) / len(group),
                sum(o["ild"] for o in group) / len(group),
            ))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--n", type=int, default=5000, help="number of patients")
    parser.add_argument("--seed", type=int, default=1, help="random seed")
    parser.add_argument("--out", default=str(ENGINE_DIR / "output"), help="output folder")
    args = parser.parse_args()

    baseline, outcomes, metadata = generate(args.n, args.seed)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    write_csv(out / "baseline.csv", "baseline", baseline)
    write_csv(out / "outcome.csv", "outcome", outcomes)
    with open(out / "metadata.json", "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    print(f"{args.n} patients written to {out}")
    print(f"{'regimen':<30}{'n':>6}{'severe 90d':>12}{'lung tox':>10}")
    for regimen, n, severe, ild in summary(baseline, outcomes):
        lung = f"{ild:.1%}" if regimen in metadata["ild_baseline_risks"] else "-"
        print(f"{regimen:<30}{n:>6}{severe:>12.1%}{lung:>10}")


if __name__ == "__main__":
    main()
