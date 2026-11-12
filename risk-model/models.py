"""Risk models for candidates 1 and 2.

Candidate 1: any adverse event of grade 3 to 5 within 90 days (logistic model).
Candidate 2: interstitial lung disease or pneumonitis (proportional hazards).

Both models take one baseline record (schema/baseline.schema.json) and need
only the Python standard library.
"""
import itertools
import json
import math
from pathlib import Path

MODEL_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG = MODEL_DIR / "config" / "models.json"


def load_config(path=DEFAULT_CONFIG):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _logit(p):
    return math.log(p / (1 - p))


def _sigmoid(x):
    return 1 / (1 + math.exp(-x))


def category(risk, thresholds):
    if risk >= thresholds["high_from"]:
        return "high"
    if risk >= thresholds["intermediate_from"]:
        return "intermediate"
    return "low"


# Candidate 1 ----------------------------------------------------------------

def severe_toxicity_terms(patient, cfg):
    """Return the factors of candidate 1 that apply to the patient.

    Each term is (factor, value shown to the user, odds ratio applied).
    """
    m = cfg["severe_toxicity_90d"]
    odds = m["odds_ratios"]
    ref_age = m["reference_patient"]["age_years"]
    age = patient["age_years"]
    terms = [(
        "age",
        f"{age} years (reference {ref_age})",
        odds["per_10_years_of_age"]["value"] ** ((age - ref_age) / 10),
    )]
    if patient["ecog"] >= 2:
        terms.append(("ecog", f"ECOG {patient['ecog']}", odds["ecog_2_or_higher"]["value"]))
    domains = patient["ga_impaired_domains"]
    if domains:
        terms.append((
            "geriatric_assessment",
            f"{domains} impaired domain(s)",
            odds["per_impaired_ga_domain"]["value"] ** domains,
        ))
    return terms


def severe_toxicity_risk(patient, cfg):
    m = cfg["severe_toxicity_90d"]
    x = _logit(m["regimen_rates"][patient["regimen"]]["rate"])
    for _, _, ratio in severe_toxicity_terms(patient, cfg):
        x += math.log(ratio)
    return _sigmoid(x)


# Candidate 2 ----------------------------------------------------------------

# Risk factors of candidate 2: name in the configuration, test on a patient.
ILD_FACTORS = {
    "age_below_65": lambda p: p["age_years"] < 65,
    "lung_comorbidity": lambda p: p["lung_comorbidity"],
    "renal_mild_decrease": lambda p: p["renal_function"] == "mild_decrease",
    "renal_moderate_severe_decrease": lambda p: p["renal_function"] == "moderate_severe_decrease",
    "more_than_4_years_since_diagnosis": lambda p: p["years_since_diagnosis"] > 4,
    "spo2_below_95": lambda p: p["spo2_percent"] < 95,
}

ILD_LABELS = {
    "age_below_65": "age below 65",
    "lung_comorbidity": "lung comorbidity",
    "renal_mild_decrease": "renal function mildly decreased",
    "renal_moderate_severe_decrease": "renal function moderately or severely decreased",
    "more_than_4_years_since_diagnosis": "more than 4 years since diagnosis",
    "spo2_below_95": "oxygen saturation below 95%",
}


def ild_applicable(patient, cfg):
    return patient["regimen"] in cfg["ild"]["regimen_rates"]


def ild_terms(patient, cfg):
    """Return the risk factors of candidate 2 that apply to the patient.

    Each term is (factor, label, hazard ratio).
    """
    hr = cfg["ild"]["hazard_ratios"]
    return [
        (name, ILD_LABELS[name], hr[name]["value"])
        for name, test in ILD_FACTORS.items()
        if test(patient)
    ]


def _reference_profiles(ref):
    """All combinations of risk factors with their share in the reference
    population, assuming independent factors. Yields (share, factor names)."""
    renal = [
        (1 - ref["renal_mild_decrease"] - ref["renal_moderate_severe_decrease"], []),
        (ref["renal_mild_decrease"], ["renal_mild_decrease"]),
        (ref["renal_moderate_severe_decrease"], ["renal_moderate_severe_decrease"]),
    ]
    binary = [
        [(1 - ref[name], []), (ref[name], [name])]
        for name in ("age_below_65", "lung_comorbidity",
                     "more_than_4_years_since_diagnosis", "spo2_below_95")
    ]
    for combo in itertools.product(renal, *binary):
        share = math.prod(s for s, _ in combo)
        yield share, [n for _, names in combo for n in names]


def ild_baseline_risk(regimen, cfg):
    """Risk r0 of a patient without risk factors on the given regimen.

    A fitted configuration stores r0 directly. Otherwise r0 is chosen so that
    the mean risk in the reference population equals the regimen rate.
    """
    entry = cfg["ild"]["regimen_rates"][regimen]
    if "baseline_risk" in entry:
        return entry["baseline_risk"]
    hr = cfg["ild"]["hazard_ratios"]
    profiles = [
        (share, math.prod(hr[n]["value"] for n in names))
        for share, names in _reference_profiles(cfg["ild"]["reference_population"])
    ]
    target = entry["rate"]
    low, high = 0.0, target
    for _ in range(60):
        mid = (low + high) / 2
        mean = sum(share * (1 - (1 - mid) ** ratio) for share, ratio in profiles)
        low, high = (mid, high) if mean < target else (low, mid)
    return (low + high) / 2


def ild_risk(patient, cfg, baseline_risk=None):
    """Probability of lung toxicity, or None if the model does not apply."""
    if not ild_applicable(patient, cfg):
        return None
    r0 = baseline_risk if baseline_risk is not None else ild_baseline_risk(patient["regimen"], cfg)
    ratio = math.prod(t[2] for t in ild_terms(patient, cfg))
    return 1 - (1 - r0) ** ratio


# Scores for the app -----------------------------------------------------------

class RiskModel:
    """Both models with one configuration. Scores follow schema/risk_score."""

    def __init__(self, cfg=None):
        self.cfg = cfg or load_config()
        self.ild_r0 = {r: ild_baseline_risk(r, self.cfg) for r in self.cfg["ild"]["regimen_rates"]}

    def score(self, patient):
        """Return one risk score record."""
        c1 = self.cfg["severe_toxicity_90d"]
        c2 = self.cfg["ild"]
        severe = severe_toxicity_risk(patient, self.cfg)
        record = {
            "patient_id": patient["patient_id"],
            "model_version": self.cfg["version"],
            "severe_toxicity_90d_risk": severe,
            "severe_toxicity_90d_regimen_rate": c1["regimen_rates"][patient["regimen"]]["rate"],
            "severe_toxicity_90d_category": category(severe, c1["categories"]),
            "ild_applicable": ild_applicable(patient, self.cfg),
            "ild_risk": None,
            "ild_grade2plus_risk": None,
            "ild_regimen_rate": None,
            "ild_category": None,
        }
        if record["ild_applicable"]:
            risk = ild_risk(patient, self.cfg, self.ild_r0[patient["regimen"]])
            record.update(
                ild_risk=risk,
                ild_grade2plus_risk=risk * c2["grade2plus_share"]["value"],
                ild_regimen_rate=c2["regimen_rates"][patient["regimen"]]["rate"],
                ild_category=category(risk, c2["categories"]),
            )
        return record

    def explain(self, patient):
        """Return the factors behind the scores of one patient, for display.

        Candidate 1 lists odds ratios against the reference patient on the same
        regimen, candidate 2 hazard ratios against a patient without risk factors.
        """
        regimen = patient["regimen"]
        c1 = self.cfg["severe_toxicity_90d"]
        out = {
            "severe_toxicity_90d": {
                "start": {
                    "label": "reference patient on this regimen",
                    "risk": c1["regimen_rates"][regimen]["rate"],
                    "source": c1["regimen_rates"][regimen].get("source"),
                },
                "factors": [
                    {"factor": f, "value": v, "odds_ratio": r}
                    for f, v, r in severe_toxicity_terms(patient, self.cfg)
                ],
            },
            "ild": None,
        }
        if ild_applicable(patient, self.cfg):
            out["ild"] = {
                "start": {
                    "label": "patient without risk factors on this regimen",
                    "risk": self.ild_r0[regimen],
                    "source": self.cfg["ild"]["regimen_rates"][regimen].get("source"),
                },
                "factors": [
                    {"factor": f, "value": label, "hazard_ratio": r}
                    for f, label, r in ild_terms(patient, self.cfg)
                ],
            }
        return out
