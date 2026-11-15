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
    "haemoglobin": "Haemoglobin",
    "albumin": "Albumin",
    "reduced_starting_dose": "Reduced starting dose",
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
        """Keep the model configuration; the default is the literature configuration."""
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
        """The attributes of the model as a dictionary, e.g. for documentation and
        tests."""
        return {key: getattr(self, key) for key in (
            "id", "name", "outcome", "onset", "window_days", "ratio_kind",
            "candidate", "source")}


def _capital(label):
    """The label with a capital first letter."""
    return label[0].upper() + label[1:]


def _factors(pairs, labels=None):
    """Factor records with readable labels from (name, ratio) pairs."""
    labels = labels or FACTOR_LABELS
    return [Factor(name, labels.get(name, name), ratio) for name, ratio in pairs]


class SevereToxicityModel(RiskModel):
    """Candidate 1: any severe adverse event (grade 3 to 5) within 90 days, logistic
    model."""
    id = "severe90"
    name = "Severe toxicity, 90 days"
    outcome = "severe_toxicity_90d"
    onset = "severe_toxicity_day"
    window_days = 90
    ratio_kind = "odds ratio"
    candidate = 1
    source = ("regimen rate from the trials; effects of haemoglobin and albumin from Extermann et al. (2012); "
              "effects of age, ECOG, geriatric domains and starting dose assumed")

    def reference_risk(self, patient):
        """The published rate of the regimen."""
        return self.cfg["severe_toxicity_90d"]["regimen_rates"][patient["regimen"]]["rate"]

    def risk(self, patient):
        """The modelled risk of the patient."""
        return calc.severe_toxicity_risk(patient, self.cfg)

    def factors(self, patient):
        """Age, ECOG, geriatric domains, haemoglobin, albumin and starting dose as
        odds ratios; 1 where a factor does not apply."""
        applied = {name: ratio for name, _, ratio in calc.severe_toxicity_terms(patient, self.cfg)}
        return _factors([
            ("age", applied.get("age", 1.0)),
            ("ecog_2_or_higher", applied.get("ecog", 1.0)),
            ("ga_impaired_domains", applied.get("geriatric_assessment", 1.0)),
            ("haemoglobin", applied.get("haemoglobin", 1.0)),
            ("albumin", applied.get("albumin", 1.0)),
            ("reduced_starting_dose", applied.get("reduced_starting_dose", 1.0)),
        ])


class LungToxicityModel(RiskModel):
    """Candidate 2: lung toxicity (ILD) under trastuzumab deruxtecan, with the
    published risk factors (proportional hazards), and under single-agent
    chemotherapy, with the published rate."""
    id = "ild"
    name = "Lung toxicity"
    outcome = "ild"
    onset = "ild_onset_day"
    ratio_kind = "hazard ratio"
    candidate = 2
    source = "hazard ratios of Powell et al. (2022), set to the regimen rate of Modi et al. (2022)"

    def __init__(self, cfg=None):
        """Read the time window and prepare the baseline risk r0 of every covered
        regimen."""
        super().__init__(cfg)
        self.window_days = self.cfg["ild"]["window_days"]
        self._r0 = {r: calc.ild_baseline_risk(r, self.cfg) for r in self.cfg["ild"]["regimen_rates"]}

    def applies(self, patient):
        """True for the covered regimens."""
        return calc.ild_applicable(patient, self.cfg)

    def reference_risk(self, patient):
        """Risk of a patient without risk factors on the same regimen, None if not
        covered."""
        return self._r0.get(patient["regimen"])

    def risk(self, patient):
        """The modelled risk, None if the model does not apply."""
        if not self.applies(patient):
            return None
        return calc.ild_risk(patient, self.cfg, self._r0[patient["regimen"]])

    def factors(self, patient):
        """The six published risk factors as hazard ratios; empty if the model does
        not apply or the regimen has no risk factors."""
        if not self.applies(patient) or not calc.ild_uses_factors(patient["regimen"], self.cfg):
            return []
        applied = {name: ratio for name, _, ratio in calc.ild_terms(patient, self.cfg)}
        labels = {name: _capital(label) for name, label in calc.ild_labels(self.cfg).items()}
        return _factors([(name, applied.get(name, 1.0)) for name in calc.ILD_FACTORS], labels)


    def risk_by_day(self, patient, day):
        """Probability of lung toxicity up to a day of the time window."""
        if not self.applies(patient):
            return None
        return calc.ild_risk_by_day(patient, day, self.cfg, self._r0[patient["regimen"]])

    def remaining_risk(self, patient, day):
        """Probability of lung toxicity in the rest of the time window for a
        patient who is free of it on the given day."""
        if not self.applies(patient):
            return None
        return calc.ild_remaining_risk(patient, day, self.cfg, self._r0[patient["regimen"]])


class _RegimenOddsModel(RiskModel):
    """A logistic model for the regimens of its configuration block: the risk
    of the reference patient on the regimen and odds ratios."""
    block = ""          # key of the model in the configuration
    ratio_kind = "odds ratio"
    window_days = 90
    labels = {}
    _reference = _terms = _risk = None   # functions of models.py

    def __init__(self, cfg=None):
        """Prepare the risk of the reference patient of every covered regimen."""
        super().__init__(cfg)
        self.window_days = self.cfg[self.block]["window_days"]
        reference = type(self)._reference
        self._r0 = {r: reference(r, self.cfg) for r in self.cfg[self.block]["regimen_rates"]}

    def applies(self, patient):
        """True for the covered regimens."""
        return patient["regimen"] in self._r0

    def reference_risk(self, patient):
        """Risk of the reference patient on the same regimen, None if not covered."""
        return self._r0.get(patient["regimen"])

    def risk(self, patient):
        """The modelled risk, None if the model does not apply."""
        if not self.applies(patient):
            return None
        return type(self)._risk(patient, self.cfg, self._r0[patient["regimen"]])

    def factors(self, patient):
        """All factors of the model as odds ratios, 1 where a factor does not
        apply; empty if the model does not apply."""
        if not self.applies(patient):
            return []
        applied = {name: ratio for name, _, ratio in type(self)._terms(patient, self.cfg)}
        labels = {name: _capital(label) for name, label in self.labels.items()}
        return _factors([(name, applied.get(name, 1.0)) for name in self.labels], labels)


class NeutropeniaModel(_RegimenOddsModel):
    """Candidate 3: neutropenia of grade 3 or higher or febrile neutropenia
    within 90 days, logistic model with the factors of Lyman et al. (2011)."""
    id = "neutropenia"
    name = "Severe neutropenia, 90 days"
    outcome = "severe_neutropenia_90d"
    onset = "severe_neutropenia_day"
    candidate = 3
    block = "neutropenia"
    labels = calc.NEUTROPENIA_LABELS
    source = "regimen rate from the trials; odds ratios of Lyman et al. (2011); effect of UGT1A1 assumed"
    _reference = staticmethod(calc.neutropenia_reference_risk)
    _terms = staticmethod(calc.neutropenia_terms)
    _risk = staticmethod(calc.neutropenia_risk)


class DiarrhoeaModel(_RegimenOddsModel):
    """Candidate 4: diarrhoea of grade 3 or higher within 90 days, logistic
    model."""
    id = "diarrhoea"
    name = "Severe diarrhoea, 90 days"
    outcome = "severe_diarrhoea_90d"
    onset = "severe_diarrhoea_day"
    candidate = 4
    block = "diarrhoea"
    labels = calc.DIARRHOEA_LABELS
    source = "regimen rate from NAPOLI 3 (Wainberg et al., 2023); effects of age, ECOG, albumin and UGT1A1 assumed"
    _reference = staticmethod(calc.diarrhoea_reference_risk)
    _terms = staticmethod(calc.diarrhoea_terms)
    _risk = staticmethod(calc.diarrhoea_risk)


class CardiovascularModel(RiskModel):
    """Candidate 5: major cardiovascular events within one year under androgen
    deprivation, proportional hazards."""
    id = "cv"
    name = "Cardiovascular events"
    outcome = "cv_event_1y"
    onset = "cv_event_day"
    ratio_kind = "hazard ratio"
    candidate = 5
    source = ("rates from HERO (Shore et al., 2020); effect of an earlier event from HERO and PRONOUNCE "
              "(Lopes et al., 2021); effects of age, diabetes, hypertension, smoking, renal function and "
              "cardiovascular disease without an event assumed")

    def __init__(self, cfg=None):
        """Read the time window and prepare the baseline risk r0 of both types of
        androgen deprivation."""
        super().__init__(cfg)
        self.window_days = self.cfg["cardiovascular"]["window_days"]
        self._r0 = {a: calc.cv_baseline_risk(a, self.cfg) for a in self.cfg["cardiovascular"]["adt_rates"]}

    def applies(self, patient):
        """True for men with prostate cancer under a GnRH agonist or antagonist."""
        return calc.cv_applicable(patient, self.cfg)

    def reference_risk(self, patient):
        """Risk of a man of the reference age without risk factors on the same type,
        None if not covered."""
        return self._r0.get(patient.get("adt_type"))

    def risk(self, patient):
        """The modelled risk, None if the model does not apply."""
        if not self.applies(patient):
            return None
        return calc.cv_risk(patient, self.cfg, self._r0[patient["adt_type"]])

    def factors(self, patient):
        """Earlier event, age and the yes-or-no factors as hazard ratios; empty if
        the model does not apply."""
        if not self.applies(patient):
            return []
        applied = {name: ratio for name, _, ratio in calc.cv_terms(patient, self.cfg)}
        return _factors([(name, applied.get(name, 1.0)) for name in calc.CV_LABELS])


    def risk_on(self, patient, adt_type):
        """Risk of the same man on another type of androgen deprivation, None if
        the model does not apply."""
        if not self.applies(patient) or adt_type not in self._r0:
            return None
        return calc.cv_risk(dict(patient, adt_type=adt_type), self.cfg, self._r0[adt_type])


MODELS = [SevereToxicityModel, LungToxicityModel, NeutropeniaModel, DiarrhoeaModel, CardiovascularModel]


def load(cfg=None):
    """Return one instance of every registered model. cfg is a model
    configuration such as one written by fit.py; the default is the
    literature configuration."""
    cfg = cfg if cfg is not None else calc.load_config()
    return [cls(cfg) for cls in MODELS]


# Metrics. risks and events are sequences of equal length; pairs with a risk
# of None are left out.

def _pairs(risks, events):
    """Risks and outcomes (as 0 or 1) of the pairs that have a risk."""
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
