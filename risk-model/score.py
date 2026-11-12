"""Compute risk scores for baseline records.

Usage: python3 risk-model/score.py --baseline engine/output/baseline.csv --out risk-model/output/risk_score.csv

Writes one record per patient in the format of schema/risk_score.schema.json.
--config selects another model configuration, e.g. one written by fit.py.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import data  # noqa: E402
import models  # noqa: E402
from data import toxage_schema  # noqa: E402


def score_all(baseline, cfg=None):
    model = models.Scorer(cfg)
    scores = [model.score(p) for p in baseline]
    toxage_schema.validate("risk_score", scores)
    return scores


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--baseline", required=True, help="baseline CSV file")
    parser.add_argument("--out", required=True, help="output CSV file")
    parser.add_argument("--config", default=str(models.DEFAULT_CONFIG), help="model configuration")
    args = parser.parse_args()

    baseline = toxage_schema.read_csv(args.baseline, "baseline")
    scores = score_all(baseline, models.load_config(args.config))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    toxage_schema.write_csv(out, "risk_score", scores)
    print(f"{len(scores)} risk scores written to {out}")


if __name__ == "__main__":
    main()
