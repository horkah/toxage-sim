from django.core.management import call_command
from django.test import TestCase

from explorer import cohort


class CohortTestCase(TestCase):
    """Test case with a small generated cohort in the database."""
    n = 300

    @classmethod
    def setUpTestData(cls):
        call_command("load_cohort", n=cls.n, seed=5, stdout=open("/dev/null", "w"))

    def setUp(self):
        self.dataset, self.models, self.rows = cohort.current()
        self.severe, self.ild = self.models
        self.ild_rows = [r for r in self.rows if r["risk_ild"] is not None]
