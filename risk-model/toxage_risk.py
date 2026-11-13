"""Common interface to the toxicity risk models of toxage-sim.

A risk model estimates, from one baseline record, the probability of one
boolean outcome of the outcome table. All models share one interface, so that
the app and evaluation code can treat them alike:

    from toxage_risk import load
    for model in load():
        model.risk(patient)             # probability from 0 to 1, None if not applicable
        model.reference_risk(patient)   # risk without risk factors on the same regimen
        model.factors(patient)          # what drives the risk, as Factor records
        model.describe()                # id, name, outcome field, window, source

The calculations are in models.py, the coefficients in config/models.json.
New models subclass RiskModel and are added to MODELS. The module also offers
the metrics of metrics.py in a form that accepts patients without a risk.

It needs only the Python standard library.
"""
import sys
from dataclasses import dataclass
from pathlib import Path

MODEL_DIR = Path(__file__).resolve().parent
if str(MODEL_DIR) not in sys.path:
    sys.path.insert(0, str(MODEL_DIR))

import metrics  # noqa: E402
import models as calc  # noqa: E402

FACTOR_LABELS = {
    "age": "Age",
    "ecog_2_or_higher": "ECOG 2 or higher",
    "ga_impaired_domains": "Impaired geriatric domains",
    **{name: label[0].upper() + label[1:] for name, label in calc.ILD_LABELS.items()},
    **{name: label[0].upper() + label[1:] for name, label in calc.CV_LABELS.items()},
}


@dataclass(frozen=True)
class Factor:
    """One risk factor of one patient. A ratio of 1 means no effect."""
    name: str
    label: str
    ratio: float


class RiskModel:
    """Base class. Subclasses set the attributes and implement the methods."""
    id = ""            # short unique key, used in URLs and as data key
    name = ""          # display name
    outcome = ""       # boolean field of the outcome table that the model predicts
    onset = ""         # day field of the outcome table, the day of the event
    window_days = 0    # time window of the outcome
    ratio_kind = ""    # what Factor.ratio means, e.g. "odds ratio"
    candidate = 0      # number of the candidate in background/toxicity-report.md
    source = ""

    def __init__(self, cfg=None):
        self.cfg = cfg if cfg is not None else calc.load_config()

    def applies(self, patient):
        """True if the model gives a risk for this patient."""
        return True

    def reference_risk(self, patient):
        """Risk of a patient with the same regimen and no risk factors."""
        raise NotImplementedError

    def risk(self, patient):
        """Probability of the outcome, or None if the model does not apply."""
        raise NotImplementedError

    def factors(self, patient):
        """List of Factor, or an empty list if the model does not apply.
        Factors that do not apply to the patient have a ratio of 1."""
        raise NotImplementedError

    def describe(self):
        return {key: getattr(self, key) for key in (
            "id", "name", "outcome", "onset", "window_days", "ratio_kind",
            "candidate", "source")}


def _factors(pairs):
    return [Factor(name, FACTOR_LABELS.get(name, name), ratio) for name, ratio in pairs]


class SevereToxicityModel(RiskModel):
    id = "severe90"
    name = "Severe toxicity, 90 days"
    outcome = "severe_toxicity_90d"
    onset = "severe_toxicity_day"
    window_days = 90
    ratio_kind = "odds ratio"
    candidate = 1
    source = "regimen rate from the trials; effects of age, ECOG and geriatric domains assumed"

    def reference_risk(self, patient):
        return self.cfg["severe_toxicity_90d"]["regimen_rates"][patient["regimen"]]["rate"]

    def risk(self, patient):
        return calc.severe_toxicity_risk(patient, self.cfg)

    def factors(self, patient):
        applied = {name: ratio for name, _, ratio in calc.severe_toxicity_terms(patient, self.cfg)}
        return _factors([
            ("age", applied.get("age", 1.0)),
            ("ecog_2_or_higher", applied.get("ecog", 1.0)),
            ("ga_impaired_domains", applied.get("geriatric_assessment", 1.0)),
        ])


class LungToxicityModel(RiskModel):
    id = "ild"
    name = "Lung toxicity"
    outcome = "ild"
    onset = "ild_onset_day"
    ratio_kind = "hazard ratio"
    candidate = 2
    source = "hazard ratios of Powell et al. (2022), set to the regimen rate of Modi et al. (2022)"

    def __init__(self, cfg=None):
        super().__init__(cfg)
        self.window_days = self.cfg["ild"]["window_days"]
        self._r0 = {r: calc.ild_baseline_risk(r, self.cfg) for r in self.cfg["ild"]["regimen_rates"]}

    def applies(self, patient):
        return calc.ild_applicable(patient, self.cfg)

    def reference_risk(self, patient):
        return self._r0.get(patient["regimen"])

    def risk(self, patient):
        if not self.applies(patient):
            return None
        return calc.ild_risk(patient, self.cfg, self._r0[patient["regimen"]])

    def factors(self, patient):
        if not self.applies(patient):
            return []
        applied = {name: ratio for name, _, ratio in calc.ild_terms(patient, self.cfg)}
        return _factors([(name, applied.get(name, 1.0)) for name in calc.ILD_FACTORS])


class CardiovascularModel(RiskModel):
    id = "cv"
    name = "Cardiovascular events"
    outcome = "cv_event_1y"
    onset = "cv_event_day"
    ratio_kind = "hazard ratio"
    candidate = 5
    source = ("rates and the effect of an earlier event from HERO (Shore et al., 2020); "
              "effects of age, diabetes, hypertension, smoking and renal function assumed")

    def __init__(self, cfg=None):
        super().__init__(cfg)
        self.window_days = self.cfg["cardiovascular"]["window_days"]
        self._r0 = {a: calc.cv_baseline_risk(a, self.cfg) for a in self.cfg["cardiovascular"]["adt_rates"]}

    def applies(self, patient):
        return calc.cv_applicable(patient, self.cfg)

    def reference_risk(self, patient):
        return self._r0.get(patient.get("adt_type"))

    def risk(self, patient):
        if not self.applies(patient):
            return None
        return calc.cv_risk(patient, self.cfg, self._r0[patient["adt_type"]])

    def factors(self, patient):
        if not self.applies(patient):
            return []
        applied = {name: ratio for name, _, ratio in calc.cv_terms(patient, self.cfg)}
        return _factors([(name, applied.get(name, 1.0)) for name in calc.CV_LABELS])


MODELS = [SevereToxicityModel, LungToxicityModel, CardiovascularModel]


def load(cfg=None):
    """Return one instance of every registered model. cfg is a model
    configuration such as one written by fit.py; the default is the
    literature configuration."""
    cfg = cfg if cfg is not None else calc.load_config()
    return [cls(cfg) for cls in MODELS]


# Metrics. risks and events are sequences of equal length; pairs with a risk
# of None are left out.

def _pairs(risks, events):
    pairs = [(r, int(bool(e))) for r, e in zip(risks, events) if r is not None]
    return [r for r, _ in pairs], [e for _, e in pairs]


def auc(risks, events):
    """Area under the ROC curve, None without events or without non-events."""
    return metrics.auc(*_pairs(risks, events))


def brier(risks, events):
    """Mean squared difference between risk and outcome, None without data."""
    risks, events = _pairs(risks, events)
    return metrics.brier(risks, events) if risks else None


def calibration(risks, events, groups=10):
    """Split the patients by risk into groups of nearly equal size.

    Returns a list of (mean predicted risk, observed rate, n) per group.
    """
    risks, events = _pairs(risks, events)
    rows = metrics.calibration_groups(risks, events, min(groups, len(risks)))
    return [(mean, observed, n) for n, mean, observed in rows]
