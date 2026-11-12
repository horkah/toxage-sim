"""Common interface to the toxicity risk models of toxage-sim.

A risk model estimates, from one baseline record, the probability of one
boolean outcome of the outcome table. All models share one interface, so that
the app and evaluation code can treat them alike:

    from toxage_risk import load
    for model in load(metadata):        # metadata of the generated data set
        model.risk(patient)             # probability from 0 to 1, None if not applicable
        model.factors(patient)          # what drives the risk, as Factor records
        model.describe()                # id, name, outcome field, window, source

New models subclass RiskModel and are added to MODELS. The module also holds
the metrics that compare predicted risks with observed outcomes.

It needs only the Python standard library.
"""
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_DIR = Path(__file__).resolve().parents[1]
if str(REPO_DIR) not in sys.path:
    sys.path.insert(0, str(REPO_DIR))

from engine import toxicity  # noqa: E402
from engine.generate import load_config  # noqa: E402

FACTOR_LABELS = {
    "age": "Age",
    "ecog_2_or_higher": "ECOG 2 or higher",
    "ga_impaired_domains": "Impaired geriatric domains",
    "age_below_65": "Age below 65",
    "lung_comorbidity": "Lung comorbidity",
    "renal_mild_decrease": "Renal function, mild decrease",
    "renal_moderate_severe_decrease": "Renal function, moderate or severe decrease",
    "more_than_4_years_since_diagnosis": "More than 4 years since diagnosis",
    "spo2_below_95": "Oxygen saturation below 95%",
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

    def __init__(self, regimens, params, metadata):
        self.regimens = regimens
        self.params = params
        self.metadata = metadata

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
        """List of Factor, or an empty list if the model does not apply."""
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
    source = "engine model: regimen rate from the trials, effects of age, ECOG and geriatric domains assumed"

    def reference_risk(self, patient):
        return self.regimens[patient["regimen"]]["severe_toxicity_rate"]

    def risk(self, patient):
        return toxicity.severe_toxicity_risk(patient, self.regimens, self.params)

    def factors(self, patient):
        return _factors(toxicity.severe_toxicity_factors(patient, self.params))


class LungToxicityModel(RiskModel):
    id = "ild"
    name = "Lung toxicity"
    outcome = "ild"
    onset = "ild_onset_day"
    window_days = 730
    ratio_kind = "hazard ratio"
    candidate = 2
    source = "engine model: hazard ratios of Powell et al. (2022), calibrated to the regimen rate"

    def _baseline_risks(self):
        return self.metadata.get("ild_baseline_risks", {})

    def applies(self, patient):
        return patient["regimen"] in self._baseline_risks()

    def reference_risk(self, patient):
        return self._baseline_risks().get(patient["regimen"])

    def risk(self, patient):
        if not self.applies(patient):
            return None
        return toxicity.ild_risk(patient, self.reference_risk(patient), self.params)

    def factors(self, patient):
        if not self.applies(patient):
            return []
        return _factors(toxicity.ild_factors(patient, self.params))


MODELS = [SevereToxicityModel, LungToxicityModel]


def load(metadata):
    """Return one instance of every registered model."""
    regimens, params = load_config()
    return [cls(regimens, params, metadata) for cls in MODELS]


# Metrics. risks and events are sequences of equal length; pairs with a risk
# of None are left out.

def _pairs(risks, events):
    return [(r, bool(e)) for r, e in zip(risks, events) if r is not None]


def auc(risks, events):
    """Area under the ROC curve (Mann-Whitney), None without events or non-events."""
    pairs = sorted(_pairs(risks, events))
    positives = sum(e for _, e in pairs)
    negatives = len(pairs) - positives
    if not positives or not negatives:
        return None
    rank_sum, i = 0.0, 0
    while i < len(pairs):
        j = i
        while j < len(pairs) and pairs[j][0] == pairs[i][0]:
            j += 1
        mean_rank = (i + 1 + j) / 2
        rank_sum += mean_rank * sum(e for _, e in pairs[i:j])
        i = j
    return (rank_sum - positives * (positives + 1) / 2) / (positives * negatives)


def brier(risks, events):
    """Mean squared difference between risk and outcome, None without data."""
    pairs = _pairs(risks, events)
    if not pairs:
        return None
    return sum((r - e) ** 2 for r, e in pairs) / len(pairs)


def calibration(risks, events, groups=10):
    """Split the patients by risk into groups of nearly equal size.

    Returns a list of (mean predicted risk, observed rate, n) per group.
    """
    pairs = sorted(_pairs(risks, events))
    groups = min(groups, len(pairs))
    result = []
    for g in range(groups):
        part = pairs[g * len(pairs) // groups:(g + 1) * len(pairs) // groups]
        result.append((
            sum(r for r, _ in part) / len(part),
            sum(e for _, e in part) / len(part),
            len(part),
        ))
    return result
