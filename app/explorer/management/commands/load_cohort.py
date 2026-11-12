"""Generate synthetic patients with the engine and store their baseline and
outcome records, replacing the data set that was there before."""
from django.core.management.base import BaseCommand
from django.db import transaction

from engine import generate
from explorer.models import Dataset, Patient
from schema import toxage_schema


class Command(BaseCommand):
    help = __doc__

    def add_arguments(self, parser):
        parser.add_argument("--n", type=int, default=5000, help="number of patients")
        parser.add_argument("--seed", type=int, default=1, help="random seed")

    def handle(self, *args, n, seed, **options):
        data = generate.generate(n, seed)
        baseline, outcomes, metadata = data["baseline"], data["outcome"], data["metadata"]
        outcome_fields = [f for f in toxage_schema.fields("outcome") if f != "patient_id"]
        with transaction.atomic():
            Dataset.objects.all().delete()
            dataset = Dataset.objects.create(metadata=metadata)
            Patient.objects.bulk_create(
                Patient(
                    patient_id=b["patient_id"],
                    dataset=dataset,
                    baseline=b,
                    outcome={f: o[f] for f in outcome_fields},
                )
                for b, o in zip(baseline, outcomes)
            )
        self.stdout.write(f"{n} patients stored (seed {seed})")
