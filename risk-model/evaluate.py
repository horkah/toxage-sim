"""Evaluate the risk models against outcomes.

Usage: python3 risk-model/evaluate.py --data engine/output [--config FILE]

Prints discrimination and calibration for both models, next to a comparison
model that knows only the regimen rate.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import data  # noqa: E402
import metrics  # noqa: E402
import models  # noqa: E402


def evaluate(baseline, outcomes, cfg=None):
    """Return {model name: {"model": summary, "regimen_only": summary,
    "groups": calibration rows, "by_regimen": {regimen: summary}}}."""
    model = models.RiskModel(cfg)
    scores = [model.score(p) for p in baseline]
    result = {}

    y = [outcomes[p["patient_id"]]["severe_toxicity_90d"] for p in baseline]
    risk = [s["severe_toxicity_90d_risk"] for s in scores]
    ref = [s["severe_toxicity_90d_regimen_rate"] for s in scores]
    result["severe_toxicity_90d"] = {
        "model": metrics.summary(risk, y),
        "regimen_only": metrics.summary(ref, y),
        "groups": metrics.calibration_groups(risk, y),
        "by_regimen": _by_regimen([p["regimen"] for p in baseline], risk, y),
    }

    pairs = [(p, s) for p, s in zip(baseline, scores) if s["ild_applicable"]]
    if pairs:
        risk = [s["ild_risk"] for _, s in pairs]
        ref = [s["ild_regimen_rate"] for _, s in pairs]
        y = [outcomes[p["patient_id"]]["ild"] for p, _ in pairs]
        result["ild"] = {
            "model": metrics.summary(risk, y),
            "regimen_only": metrics.summary(ref, y),
            "groups": metrics.calibration_groups(risk, y),
            "by_regimen": _by_regimen([p["regimen"] for p, _ in pairs], risk, y),
        }
    return result


def _by_regimen(regimens, risks, outcomes):
    out = {}
    for name in dict.fromkeys(regimens):
        idx = [i for i, r in enumerate(regimens) if r == name]
        out[name] = metrics.summary([risks[i] for i in idx], [outcomes[i] for i in idx])
    return out


def _fmt(v, pattern):
    return "-" if v is None else format(v, pattern)


def report(result):
    lines = []
    for name, r in result.items():
        lines.append(f"\n{name}: {r['model']['n']} patients, {r['model']['events']} events")
        lines.append(f"  {'':<22}{'model':>10}{'regimen only':>14}")
        for key, label, pattern in (
            ("observed_rate", "observed rate", ".3f"),
            ("mean_risk", "mean predicted risk", ".3f"),
            ("observed_to_expected", "observed / expected", ".2f"),
            ("auc", "AUC", ".3f"),
            ("brier", "Brier score", ".4f"),
            ("calibration_slope", "calibration slope", ".2f"),
        ):
            lines.append(
                f"  {label:<22}{_fmt(r['model'][key], pattern):>10}"
                f"{_fmt(r['regimen_only'][key], pattern):>14}"
            )
        lines.append(f"  by regimen:  {'n':>6}{'observed':>10}{'predicted':>11}{'AUC':>7}")
        for regimen, m in r["by_regimen"].items():
            lines.append(
                f"    {regimen:<28}{m['n']:>6}{m['observed_rate']:>10.3f}"
                f"{m['mean_risk']:>11.3f}{_fmt(m['auc'], '.3f'):>7}"
            )
        lines.append("  calibration by tenth of predicted risk (n, predicted, observed):")
        for n, pred, obs in r["groups"]:
            lines.append(f"    {n:>6}{pred:>8.3f}{obs:>8.3f}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data", required=True, help="folder with baseline.csv and outcome.csv")
    parser.add_argument("--config", default=str(models.DEFAULT_CONFIG), help="model configuration")
    args = parser.parse_args()

    baseline, outcomes = data.load(args.data)
    print(f"model configuration: {args.config}")
    print(report(evaluate(baseline, outcomes, models.load_config(args.config))))


if __name__ == "__main__":
    main()
