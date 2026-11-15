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
    """Logistic model: one intercept per regimen, then age, ECOG, geriatric
    domains, haemoglobin, albumin and a reduced starting dose."""
    m = cfg["severe_toxicity_90d"]
    regimens = [r for r in m["regimen_rates"] if any(p["regimen"] == r for p in baseline)]
    ref = m["reference_patient"]
    ref_age = ref["age_years"]
    reduced_below = m["thresholds"]["reduced_starting_dose_below"]
    x, y = [], []
    for p in baseline:
        if p["regimen"] not in regimens:
            continue
        row = [1.0 if p["regimen"] == r else 0.0 for r in regimens]
        row += [
            (p["age_years"] - ref_age) / 10,
            1.0 if p["ecog"] >= 2 else 0.0,
            float(p["ga_impaired_domains"] or 0),
            ref["haemoglobin_g_dl"] - p["haemoglobin_g_dl"],
            (ref["albumin_g_l"] - p["albumin_g_l"]) / 10,
            1.0 if p["starting_dose_level"] < reduced_below else 0.0,
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
    names = ["per_10_years_of_age", "ecog_2_or_higher", "per_impaired_ga_domain",
             "per_g_dl_haemoglobin_below_reference", "per_10_g_l_albumin_below_reference", "reduced_starting_dose"]
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
    tests = models.ild_tests(cfg)
    x, y = [], []
    for p in baseline:
        if p["regimen"] not in regimens:
            continue
        row = [1.0 if p["regimen"] == r else 0.0 for r in regimens]
        # The risk factors count only on the regimens they apply to.
        uses = models.ild_uses_factors(p["regimen"], cfg)
        row += [1.0 if uses and tests[f](p) else 0.0 for f in factors]
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
            "risk_factors": models.ild_uses_factors(r, cfg),
            "source": "fitted; rate is the observed rate in the data",
        }
    ratios = {
        f: {"value": math.exp(coef[k + j]), "ci95": _ci(coef[k + j], se[k + j]), "basis": "fitted"}
        for j, f in enumerate(factors)
    }
    return fitted, ratios


def _fit_regimen_odds(baseline, outcomes, cfg, block, outcome, columns):
    """Logistic model of candidates 3 and 4: one intercept per regimen, then
    the log odds ratios. columns is a list of (name in the configuration,
    function(patient) -> number). Returns (regimen entries, odds ratios)."""
    m = cfg[block]
    regimens = [r for r in m["regimen_rates"] if any(p["regimen"] == r for p in baseline)]
    x, y = [], []
    for p in baseline:
        if p["regimen"] not in regimens:
            continue
        x.append([1.0 if p["regimen"] == r else 0.0 for r in regimens] + [float(f(p)) for _, f in columns])
        y.append(int(outcomes[p["patient_id"]][outcome]))
    # A factor that is the same for all patients of every regimen cannot be told
    # apart from the regimens. Its effect is part of the fitted risk of the
    # reference patient, so its odds ratio becomes 1.
    k = len(regimens)
    keep = [j for j in range(len(columns))
            if any(len({row[k + j] for row in x if row[i]}) > 1 for i in range(k))]
    x = [row[:k] + [row[k + j] for j in keep] for row in x]
    result = glm.fit(x, y, link="logit")
    _warn_if_not_converged(result)
    coef, se = result["coefficients"], result["standard_errors"]
    fitted = {}
    for i, r in enumerate(regimens):
        group = [yi for row, yi in zip(x, y) if row[i]]
        fitted[r] = dict(m["regimen_rates"][r], rate=sum(group) / len(group),
                         reference_risk=1 / (1 + math.exp(-coef[i])),
                         source="fitted; rate is the observed rate in the data")
    ratios = {name: {"value": 1.0, "basis": "not estimable: the same for all patients of every regimen in the data"}
              for name, _ in columns}
    for n, j in enumerate(keep):
        ratios[columns[j][0]] = {"value": math.exp(coef[k + n]), "ci95": _ci(coef[k + n], se[k + n]), "basis": "fitted"}
    return fitted, ratios


def fit_neutropenia(baseline, outcomes, cfg):
    """Candidate 3: the yes-or-no factors, renal function and white cells."""
    m = cfg["neutropenia"]
    ref = m["reference_patient"]

    def test(name):
        return lambda p: models.neutropenia_tests(p["regimen"], cfg)[name](p)
    columns = [(name, test(name)) for name in models.NEUTROPENIA_LABELS if name not in ("egfr", "white_cells")]
    columns.append(("per_ml_min_of_egfr", lambda p: p["egfr_ml_min"] - ref["egfr_ml_min"]))
    columns.append(("per_10e9_l_of_white_cells", lambda p: p["white_cells_10e9_l"] - ref["white_cells_10e9_l"]))
    return _fit_regimen_odds(baseline, outcomes, cfg, "neutropenia", "severe_neutropenia_90d", columns)


def fit_diarrhoea(baseline, outcomes, cfg):
    """Candidate 4: age, ECOG, albumin and UGT1A1 with irinotecan."""
    def test(name):
        return lambda p: models.diarrhoea_tests(p["regimen"], cfg)[name](p)
    columns = [(name, test(name)) for name in models.DIARRHOEA_LABELS]
    return _fit_regimen_odds(baseline, outcomes, cfg, "diarrhoea", "severe_diarrhoea_90d", columns)


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
    for block, fit_block in (("neutropenia", fit_neutropenia), ("diarrhoea", fit_diarrhoea)):
        rates, ratios = fit_block(baseline, outcomes, cfg)
        cfg[block]["regimen_rates"] = rates
        cfg[block]["odds_ratios"] = ratios
    rates, prior, ratios = fit_cardiovascular(baseline, outcomes, cfg)
    cfg["cardiovascular"]["adt_rates"] = rates
    cfg["cardiovascular"]["prior_event_hazard_ratios"] = prior
    cfg["cardiovascular"]["hazard_ratios"] = ratios
    # The fitted rates already describe the time window of the model and
    # cardiovascular events alone.
    cfg["cardiovascular"]["rate_window_days"] = cfg["cardiovascular"]["window_days"]
    cfg["cardiovascular"]["cardiovascular_share_of_events"] = {"value": 1.0, "basis": "fitted rates count cardiovascular events"}
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
                       ("neutropenia", "odds_ratios"), ("diarrhoea", "odds_ratios"),
                       ("cardiovascular", "prior_event_hazard_ratios"), ("cardiovascular", "hazard_ratios")):
        print(f"\n{model}: {key}")
        for name, v in cfg[model][key].items():
            interval = f"(95% CI {v['ci95'][0]:.3f}-{v['ci95'][1]:.3f})" if "ci95" in v else "(not estimated)"
            print(f"  {name:<40}{v['value']:>8.3f}  {interval}")


if __name__ == "__main__":
    main()
