"""Storage of the synthetic data and of the settings of the user.

Records keep the layout of the central schema (schema/), so the database
needs no change when the schema grows.

  Dataset   one generated cohort with its state and the settings it was made with
  Patient   one patient of a data set with the baseline record
  Course    one patient in one scenario: outcome, events, alerts, weekly observations
  Setting   values of the user that differ from the defaults in the repository

A course keeps the outcome apart from the bulky weekly observations, so that
cohort views read only what they need. Deleting a data set deletes its
patients and courses.
"""
from django.db import models


class Dataset(models.Model):
    """One generated cohort: its state while it is made, its scenarios, and the
    settings it was made with."""
    RUNNING, READY, FAILED = "running", "ready", "failed"

    name = models.CharField(max_length=80)
    created = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, default=RUNNING)
    progress = models.FloatField(default=0)       # 0 to 1 while running
    message = models.CharField(max_length=300, blank=True)
    n = models.PositiveIntegerField()
    seed = models.IntegerField()
    metadata = models.JSONField(default=dict)     # metadata of the engine
    scenarios = models.JSONField(default=list)    # records of the scenario table
    settings = models.JSONField(default=dict)     # values that differed from the defaults
    calibrated = models.BooleanField(default=False)

    class Meta:
        """Newest first; the explorer shows the newest by default."""
        ordering = ["-created", "-pk"]

    def __str__(self):
        """The name, e.g. in the admin and in messages."""
        return self.name

    @property
    def ready(self):
        """True once the data set is complete and can be explored."""
        return self.status == self.READY


class Patient(models.Model):
    """One patient of a data set with the baseline record of the central schema."""
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name="patients")
    patient_id = models.CharField(max_length=32)
    baseline = models.JSONField()

    class Meta:
        """In order of the patient id; one id once per data set."""
        ordering = ["patient_id"]
        constraints = [models.UniqueConstraint(fields=["dataset", "patient_id"], name="patient_once_per_dataset")]

    def __str__(self):
        """The patient id."""
        return self.patient_id


class Course(models.Model):
    """events and alerts are lists of records; observations holds one list
    per field, in week order."""
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name="courses")
    scenario_id = models.CharField(max_length=64)
    outcome = models.JSONField()
    events = models.JSONField(default=list)
    alerts = models.JSONField(default=list)
    observations = models.JSONField(default=dict)

    class Meta:
        """One course per patient and scenario; scenario_id is indexed for the views
        of one scenario."""
        constraints = [models.UniqueConstraint(fields=["patient", "scenario_id"], name="course_once_per_scenario")]
        indexes = [models.Index(fields=["scenario_id"])]


class Setting(models.Model):
    """Changed values of one parameter file as {path: value}."""
    key = models.CharField(max_length=40, primary_key=True)
    value = models.JSONField(default=dict)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        """The key of the parameter file."""
        return self.key
