"""Detection model for lung toxicity: reads the weekly home measurements of a
patient and says when the patient should be examined.

The rule follows the expert panel in Swain et al. (2022): a fall of the oxygen
saturation at rest by 2 to 4 points against the patient's own reference should
lead to an examination. With one measurement per week this becomes:

    alert if the saturation is lower than the reference by `fall_once` points, or
          by `fall_confirmed` points in two reports in a row, or
          by `fall_confirmed` points together with cough or breathlessness that
          is worse than the patient's reference by `symptom_rise` levels.

The reference is the first report of the patient. After an alert the detector
starts again from the current report, because the patient is examined.

The engine uses this detector for its lung monitoring. evaluate() measures it on
generated data: how many events it finds before usual care does, how many days
earlier, and how many false alerts it gives.

Usage: python3 risk-model/detect.py --data engine/output
"""
import argparse
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import models  # noqa: E402

FIELDS = ("spo2_percent", "pro_cough", "pro_dyspnoea")


def default_rule():
    """The rule of the model configuration (lung_detection)."""
    return models.load_config()["lung_detection"]


class LungDetector:
    """Follows one patient. report() takes the values of one week, None where a
    value is missing, and returns True if the patient should be examined."""

    def __init__(self, rule=None):
        """Start without a reference; the first report with a saturation sets it."""
        self.rule = rule if rule is not None else default_rule()
        self.reset()

    def reset(self):
        """Forget the reference and the last report."""
        self.reference = {}
        self.fallen_before = False

    def report(self, values):
        """Take the values of one report, {field: value or None}. Returns True
        for an alert; the detector then starts again from this report."""
        rule = self.rule
        for field in FIELDS:
            if field not in self.reference and values.get(field) is not None:
                self.reference[field] = values[field]
        spo2 = values.get("spo2_percent")
        if spo2 is None or "spo2_percent" not in self.reference:
            return False     # without a saturation the report says nothing; the last one stays
        fall = self.reference["spo2_percent"] - spo2
        symptoms = any(
            values.get(f) is not None and f in self.reference
            and values[f] - self.reference[f] >= rule["symptom_rise"]
            for f in ("pro_cough", "pro_dyspnoea"))
        fallen = fall >= rule["fall_confirmed"]
        alert = fall >= rule["fall_once"] or (fallen and (self.fallen_before or symptoms))
        self.fallen_before = fallen
        if alert:
            self.reset()
            for field in FIELDS:
                if values.get(field) is not None:
                    self.reference[field] = values[field]
        return alert


def alert_days(observations, rule=None):
    """Days of the alerts of one patient from the observation records in week
    order: the last day of each week with an alert."""
    detector = LungDetector(rule)
    return [o["day"] + 6 for o in observations if detector.report(o)]


def evaluate(baseline, observations, outcomes, regimens=("trastuzumab_deruxtecan",), rule=None):
    """Measure the detector on the patients of the given regimens under usual
    care. observations: {patient_id: records in week order}; outcomes:
    {patient_id: outcome record}. Returns a dictionary of key numbers.

    An alert counts as true from the onset of lung toxicity until its
    recognition by usual care, as early if it comes before that recognition."""
    weeks = alerts = false_alerts = events = found = 0
    lead, by_grade = [], {}
    for p in baseline:
        if p["regimen"] not in regimens:
            continue
        o, rows = outcomes[p["patient_id"]], observations.get(p["patient_id"], [])
        onset, diagnosis = o["ild_onset_day"], o["ild_diagnosis_day"]
        if diagnosis is not None:
            rows = [r for r in rows if r["day"] <= diagnosis]     # after the diagnosis nothing is left to find
        days = alert_days(rows, rule)
        weeks += len(rows)
        alerts += len(days)
        true = [d for d in days if onset is not None and d >= onset]
        false_alerts += len(days) - len(true)
        if o["ild"] and diagnosis is not None:
            events += 1
            grade = by_grade.setdefault(o["ild_grade"], [0, 0])
            grade[0] += 1
            early = [d for d in true if d < diagnosis]
            if early:
                found += 1
                grade[1] += 1
                lead.append(diagnosis - early[0])
    return {
        "patient_weeks": weeks,
        "alerts": alerts,
        "false_alerts_per_week": false_alerts / weeks if weeks else None,
        "events": events,
        "found_early": found,
        "sensitivity": found / events if events else None,
        "median_lead_days": statistics.median(lead) if lead else None,
        "by_grade": {g: {"events": n, "found_early": f} for g, (n, f) in sorted(by_grade.items())},
    }


def main():
    """Command line: measure the detector on generated data."""
    import data
    from data import toxage_schema
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--data", required=True, help="folder with baseline.csv, observation.csv and outcome.csv")
    args = parser.parse_args()
    baseline, outcomes = data.load(args.data)
    observations = {}
    for r in toxage_schema.read_csv(Path(args.data) / "observation.csv", "observation"):
        if r["scenario_id"] == "usual_care":
            observations.setdefault(r["patient_id"], []).append(r)
    result = evaluate(baseline, observations, outcomes)
    print(f"{result['patient_weeks']} patient-weeks, {result['alerts']} alerts, "
          f"{result['false_alerts_per_week']:.4f} false alerts per week")
    print(f"{result['events']} recognised events, {result['found_early']} found before usual care "
          f"({result['sensitivity']:.0%}), median {result['median_lead_days']} days earlier")
    for grade, v in result["by_grade"].items():
        print(f"  grade {grade}: {v['found_early']} of {v['events']}")


if __name__ == "__main__":
    main()
