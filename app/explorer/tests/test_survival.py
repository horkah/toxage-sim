"""Estimators and endpoints of survival.py, checked on examples with known results."""
from django.test import SimpleTestCase

from explorer import survival
from explorer.survival import Record


def records(*items):
    """Records from (time, cause) pairs; patient ids are their positions."""
    return [Record(str(i), t, c) for i, (t, c) in enumerate(items)]


class EstimatorTest(SimpleTestCase):
    def test_kaplan_meier(self):
        # Events at 1, 2 and 3; censored at 2 (after the event of that day) and 4.
        steps = survival.kaplan_meier(records((1, "d"), (2, "d"), (2, None), (3, "d"), (4, None)))
        self.assertEqual([t for t, _ in steps], [0, 1, 2, 3])
        for (_, got), want in zip(steps, [1, 0.8, 0.6, 0.3]):
            self.assertAlmostEqual(got, want)
        self.assertEqual(survival.median(steps), 3)
        self.assertAlmostEqual(survival.value_at(steps, 2.5), 0.6)

    def test_kaplan_meier_without_censoring_is_the_share_without_event(self):
        steps = survival.kaplan_meier(records((1, "d"), (5, "d"), (9, None), (9, None)))
        self.assertAlmostEqual(survival.value_at(steps, 9), 0.5)

    def test_cumulative_incidence_with_a_competing_cause(self):
        data = records((1, "a"), (2, "b"), (3, "a"), (4, None))
        a = survival.cumulative_incidence(data, "a")
        self.assertAlmostEqual(survival.value_at(a, 1), 0.25)
        self.assertAlmostEqual(survival.value_at(a, 3), 0.5)
        b = survival.cumulative_incidence(data, "b")
        self.assertAlmostEqual(survival.value_at(b, 4), 0.25)
        # 1 - Kaplan-Meier with "b" as censoring would overestimate "a".
        naive = survival.kaplan_meier([r if r.cause == "a" else Record(r.patient_id, r.time, None) for r in data])
        self.assertGreater(1 - survival.value_at(naive, 3), 0.5)

    def test_restricted_mean(self):
        steps = [(0.0, 1.0), (2.0, 0.5)]
        self.assertAlmostEqual(survival.restricted_mean(steps, 4), 3.0)
        self.assertAlmostEqual(survival.restricted_mean(steps, 1), 1.0)
        # Equal to the mean of the per-patient times up to the horizon without censoring.
        data = records((1, "d"), (3, "d"), (10, None))
        self.assertAlmostEqual(survival.restricted_mean(survival.kaplan_meier(data), 5), (1 + 3 + 5) / 3)

    def test_at_risk_and_sampling(self):
        data = records((1, "d"), (2, None), (3, "d"))
        self.assertEqual([survival.at_risk(data, t) for t in (0, 1, 1.5, 3, 4)], [3, 3, 2, 1, 0])
        steps = [(float(t), 1 - t / 1000) for t in range(1000)]
        points = survival.sampled(steps, 999, most=10)
        self.assertEqual(len(points), 12)
        self.assertEqual(points[-1][0], 999)

    def test_paired_comparison(self):
        p = survival.paired({"a": 3, "b": 5, "c": 4}, {"a": 1, "b": 4, "c": 4, "x": 9})
        self.assertEqual(p.n, 3)
        self.assertAlmostEqual(p.a, 4)
        self.assertAlmostEqual(p.b, 3)
        self.assertAlmostEqual(p.diff, 1)
        self.assertLess(p.low, 1)
        self.assertGreater(p.high, 1)
        self.assertIsNone(survival.paired({}, {}))

    def test_complete_follow_up(self):
        data = records((1, "d"), (10, None))
        self.assertTrue(survival.complete_until(data, 10))
        self.assertFalse(survival.complete_until(data, 11))
        self.assertEqual(survival.had_event(data, 5), {"0": 1, "1": 0})
        self.assertEqual(survival.restricted_times(data, 5), {"0": 1, "1": 5})


def row(pid, death=None, end=None, reason="ongoing", follow=3640, **more):
    """An outcome row with the fields the endpoints read."""
    base = {"patient_id": pid, "death_day": death, "follow_up_days": death or follow,
            "treatment_end_day": end, "treatment_end_reason": reason,
            "ild": False, "ild_onset_day": None, "ild_grade": None, "cv_event": False, "cv_event_day": None}
    base.update(more)
    return base


class EndpointTest(SimpleTestCase):
    def test_overall_survival(self):
        out = survival.overall_survival([row("A", death=100), row("B")])
        self.assertEqual(out, [Record("A", 100, "death"), Record("B", 3640, None)])

    def test_severe_free_survival_takes_the_earlier_of_event_and_death(self):
        events = {"A": [{"grade": 2, "day": 5}, {"grade": 3, "day": 40}], "B": [{"grade": 4, "day": 9}]}
        out = survival.severe_free_survival([row("A", death=200), row("B", death=7), row("C")], events)
        self.assertEqual(out, [Record("A", 40, "severe"), Record("B", 7, "death"), Record("C", 3640, None)])

    def test_therapy_end(self):
        out = survival.therapy_end([row("A", end=30, reason="toxicity"), row("B", death=50)])
        self.assertEqual(out, [Record("A", 30, "toxicity"), Record("B", 50, None)])

    def test_specific_events_compete_with_death(self):
        rows = [row("A", ild=True, ild_onset_day=20, ild_grade=2), row("B", ild=True, ild_onset_day=30, ild_grade=1),
                row("C", death=60)]
        self.assertEqual(survival.lung_toxicity(rows),
                         [Record("A", 20, "event"), Record("B", 3640, None), Record("C", 60, "death")])
        self.assertEqual(survival.cardiovascular([row("A", cv_event=True, cv_event_day=99)]), [Record("A", 99, "event")])
