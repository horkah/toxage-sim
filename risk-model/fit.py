"""Refit the coefficients of all models on data.

Usage: python3 risk-model/fit.py --data engine/output --out risk-model/output/fitted.json

The result has the same format as config/models.json and can be used in its
place. It keeps the model structure and replaces the numbers by estimates
from the data. The 95% confidence intervals are added for information.
"""
import argparse
import copy
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import data  # noqa: E402
import glm  # noqa: E402
import models  # noqa: E402


def _warn_if_not_converged(result):
    """Say on stderr when a fit did not converge: its coefficients are not
    estimates, e.g. because the data separate the outcome completely."""
    if not result.get("converged", True):
        print(f"warning: the fit did not converge in {result['iterations']} rounds; "
              "the coefficients are not reliable", file=sys.stderr)


def _ci(coef, se):
    """95% confidence interval of a ratio from a log coefficient and its standard
    error."""
    return [round(math.exp(coef - 1.96 * se), 4), round(math.exp(coef + 1.96 * se), 4)]


def fit_severe_toxicity(baseline, outcomes, cfg):
    """Logistic model: one intercept per regimen, then age, ECOG, geriatric domains."""
    m = cfg["severe_toxicity_90d"]
    regimens = [r for r in m["regimen_rates"] if any(p["regimen"] == r for p in baseline)]
    ref_age = m["reference_patient"]["age_years"]
    x, y = [], []
    for p in baseline:
        if p["regimen"] not in regimens:
            continue
        row = [1.0 if p["regimen"] == r else 0.0 for r in regimens]
        row += [
            (p["age_years"] - ref_age) / 10,
            1.0 if p["ecog"] >= 2 else 0.0,
            float(p["ga_impaired_domains"] or 0),
        ]
        x.append(row)
        y.append(int(outcomes[p["patient_id"]]["severe_toxicity_90d"]))
    result = glm.fit(x, y, link="logit")
    _warn_if_not_converged(result)
    coef, se = result["coefficients"], result["standard_errors"]
    k = len(regimens)
    fitted = {}
    for i, r in enumerate(regimens):
        fitted[r] = {
            "rate": 1 / (1 + math.exp(-coef[i])),
            "source": "fitted",
        }
    names = ["per_10_years_of_age", "ecog_2_or_higher", "per_impaired_ga_domain"]
    ratios = {
        name: {"value": math.exp(coef[k + j]), "ci95": _ci(coef[k + j], se[k + j]), "basis": "fitted"}
        for j, name in enumerate(names)
    }
    return fitted, ratios


def fit_ild(baseline, outcomes, cfg):
    """Proportional hazards model as binomial regression with cloglog link:
    one intercept per regimen, then the log hazard ratios."""
    regimens = [r for r in cfg["ild"]["regimen_rates"] if any(p["regimen"] == r for p in baseline)]
    factors = list(models.ILD_FACTORS)
    x, y = [], []
    for p in baseline:
        if p["regimen"] not in regimens:
            continue
        row = [1.0 if p["regimen"] == r else 0.0 for r in regimens]
        row += [1.0 if models.ILD_FACTORS[f](p) else 0.0 for f in factors]
        x.append(row)
        y.append(int(outcomes[p["patient_id"]]["ild"]))
    rates = []
    for i, r in enumerate(regimens):
        group = [yi for row, yi in zip(x, y) if row[i]]
        rates.append(sum(group) / len(group))
    start = [math.log(-math.log(1 - min(max(rt, 0.001), 0.9))) for rt in rates]
    start += [0.0] * len(factors)
    result = glm.fit(x, y, link="cloglog", start=start)
    _warn_if_not_converged(result)
    coef, se = result["coefficients"], result["standard_errors"]
    k = len(regimens)
    fitted = {}
    for i, r in enumerate(regimens):
        fitted[r] = {
            "rate": rates[i],
            "baseline_risk": 1 - math.exp(-math.exp(coef[i])),
            "source": "fitted; rate is the observed rate in the data",
        }
    ratios = {
        f: {"value": math.exp(coef[k + j]), "ci95": _ci(coef[k + j], se[k + j]), "basis": "fitted"}
        for j, f in enumerate(factors)
    }
    return fitted, ratios


def fit_cardiovascular(baseline, outcomes, cfg):
    """Proportional hazards model as binomial regression with cloglog link:
    one intercept per type of androgen deprivation, the earlier event per
    type, age, then the other log hazard ratios."""
    m = cfg["cardiovascular"]
    patients = [p for p in baseline if models.cv_applicable(p, cfg)]
    types = [a for a in m["adt_rates"] if any(p["adt_type"] == a for p in patients)]
    factors = list(models.CV_FACTORS)
    ref_age = m["reference_patient"]["age_years"]
    x, y = [], []
    for p in patients:
        row = [1.0 if p["adt_type"] == a else 0.0 for a in types]
        row += [1.0 if p["adt_type"] == a and p["prior_cardiovascular_event"] else 0.0 for a in types]
        row.append((p["age_years"] - ref_age) / 10)
        row += [1.0 if models.CV_FACTORS[f](p) else 0.0 for f in factors]
        x.append(row)
        y.append(int(outcomes[p["patient_id"]]["cv_event_1y"]))
    rates = []
    for i in range(len(types)):
        group = [yi for row, yi in zip(x, y) if row[i]]
        rates.append(sum(group) / len(group))
    k = len(types)
    start = [math.log(-math.log(1 - min(max(rt, 0.001), 0.9))) for rt in rates]
    start += [0.0] * (len(x[0]) - k)
    result = glm.fit(x, y, link="cloglog", start=start)
    _warn_if_not_converged(result)
    coef, se = result["coefficients"], result["standard_errors"]
    entry = lambda j: {"value": math.exp(coef[j]), "ci95": _ci(coef[j], se[j]), "basis": "fitted"}
    fitted = {a: {"rate": rates[i], "baseline_risk": 1 - math.exp(-math.exp(coef[i])),
                  "source": "fitted; rate is the observed rate in the data within the time window"}
              for i, a in enumerate(types)}
    prior = {a: entry(k + i) for i, a in enumerate(types)}
    ratios = {"per_10_years_of_age": entry(2 * k)}
    ratios.update({f: entry(2 * k + 1 + j) for j, f in enumerate(factors)})
    return fitted, prior, ratios


def fit(baseline, outcomes, cfg=None, label="data"):
    """Return a new configuration with coefficients estimated from the data."""
    cfg = copy.deepcopy(cfg or models.load_config())
    rates, ratios = fit_severe_toxicity(baseline, outcomes, cfg)
    cfg["severe_toxicity_90d"]["regimen_rates"] = rates
    cfg["severe_toxicity_90d"]["odds_ratios"] = ratios
    rates, ratios = fit_ild(baseline, outcomes, cfg)
    cfg["ild"]["regimen_rates"] = rates
    cfg["ild"]["hazard_ratios"] = ratios
    rates, prior, ratios = fit_cardiovascular(baseline, outcomes, cfg)
    cfg["cardiovascular"]["adt_rates"] = rates
    cfg["cardiovascular"]["prior_event_hazard_ratios"] = prior
    cfg["cardiovascular"]["hazard_ratios"] = ratios
    # The fitted rates already describe the time window of the model.
    cfg["cardiovascular"]["rate_window_days"] = cfg["cardiovascular"]["window_days"]
    cfg["version"] = cfg["version"] + "+fit"
    cfg["basis"] = f"fitted on {label} ({len(baseline)} patients); categories and grade share unchanged"
    return cfg


def main():
    """Command line: fit the models on generated data and write the fitted
    configuration."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data", required=True, help="folder with baseline.csv and outcome.csv")
    parser.add_argument("--out", required=True, help="output JSON file")
    args = parser.parse_args()

    baseline, outcomes = data.load(args.data)
    cfg = fit(baseline, outcomes, label=args.data)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

    print(f"fitted on {len(baseline)} patients, written to {out}")
    for model, key in (("severe_toxicity_90d", "odds_ratios"), ("ild", "hazard_ratios"),
                       ("cardiovascular", "prior_event_hazard_ratios"), ("cardiovascular", "hazard_ratios")):
        print(f"\n{model}: {key}")
        for name, v in cfg[model][key].items():
            print(f"  {name:<36}{v['value']:>7.2f}  (95% CI {v['ci95'][0]:.2f}-{v['ci95'][1]:.2f})")


if __name__ == "__main__":
    main()
