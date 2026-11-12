"""Storage of the synthetic data. Records keep the layout of the central
schema (schema/), so the database needs no change when the schema grows."""
from django.db import models


class Dataset(models.Model):
    """One generated data set. metadata is the metadata of the engine."""
    created = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField()

    def __str__(self):
        return f"{self.metadata.get('n')} patients, seed {self.metadata.get('seed')}"


class Patient(models.Model):
    patient_id = models.CharField(primary_key=True, max_length=32)
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name="patients")
    baseline = models.JSONField()
    outcome = models.JSONField()

    class Meta:
        ordering = ["patient_id"]

    def __str__(self):
        return self.patient_id

    def record(self):
        """Baseline and outcome in one flat dict."""
        return {**self.baseline, **self.outcome}
