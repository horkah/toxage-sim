"""Storage of the synthetic data. Records keep the layout of the central
schema (schema/), so the database needs no change when the schema grows.

A data set holds the patients once and, per scenario, one course for every
patient. A course keeps the outcome apart from the bulky weekly observations,
so that cohort views read only what they need.
"""
from django.db import models


class Dataset(models.Model):
    """One generated data set. metadata is the metadata of the engine,
    scenarios the records of the scenario table."""
    created = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField()
    scenarios = models.JSONField(default=list)

    def __str__(self):
        return f"{self.metadata.get('n')} patients, seed {self.metadata.get('seed')}"


class Patient(models.Model):
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name="patients")
    patient_id = models.CharField(max_length=32)
    baseline = models.JSONField()

    class Meta:
        ordering = ["patient_id"]
        constraints = [models.UniqueConstraint(fields=["dataset", "patient_id"], name="patient_once_per_dataset")]

    def __str__(self):
        return self.patient_id


class Course(models.Model):
    """The course of one patient in one scenario. events and alerts are lists
    of records; observations holds one list per field, in week order."""
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="courses")
    scenario_id = models.CharField(max_length=64)
    outcome = models.JSONField()
    events = models.JSONField(default=list)
    alerts = models.JSONField(default=list)
    observations = models.JSONField(default=dict)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["patient", "scenario_id"], name="course_once_per_scenario")]
        indexes = [models.Index(fields=["scenario_id"])]
