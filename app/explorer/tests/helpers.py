from django.core.management import call_command
from django.test import TestCase

from explorer import cohort


class CohortTestCase(TestCase):
    """Test case with a small generated cohort in the database."""
    n = 240

    @classmethod
    def setUpTestData(cls):
        call_command("load_cohort", n=cls.n, seed=5, stdout=open("/dev/null", "w"))

    def setUp(self):
        self.dataset, self.models, self.rows = cohort.current()
        by_id = {m.id: m for m in self.models}
        self.severe, self.ild, self.cv = by_id["severe90"], by_id["ild"], by_id["cv"]
        self.neutropenia, self.diarrhoea = by_id["neutropenia"], by_id["diarrhoea"]
        self.ild_rows = [r for r in self.rows if r["risk_ild"] is not None]
        self.cv_rows = [r for r in self.rows if r["risk_cv"] is not None]
