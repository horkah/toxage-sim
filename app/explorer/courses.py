"""Courses of the scenarios, stored without duplicates.

The same patients are simulated under several scenarios, and much of a
course is the same in all of them: an intervention changes a patient's
course only from the point where it acts, and many patients are not reached
at all. One scenario of every data set is its base, usual care where it
exists. In the other scenarios each of the four fields of a course (outcome,
events, alerts, observations) is stored as NULL when it is identical to the
field of the base; NULL means "the same as in the base scenario".

Every reading path takes the courses through full(), which fills such fields
from the base in the database query. Deleting the base scenario first copies
its fields into the courses that refer to them, then makes the next scenario
the base and removes the duplicates against it again.
"""
import json

from django.db import connection
from django.db.models import JSONField, OuterRef, Subquery
from django.db.models.functions import Coalesce

from .models import Course, Patient

FIELDS = ("outcome", "events", "alerts", "observations")
USUAL_CARE = "usual_care"


def choose_base(scenario_ids):
    """The base scenario among the ids: usual care where it exists, else the first."""
    return USUAL_CARE if USUAL_CARE in scenario_ids else scenario_ids[0]


def base_of(dataset):
    """The base scenario of a data set; older data sets without the entry in
    their metadata have usual care or their first scenario."""
    return dataset.metadata.get("base") or choose_base([s["scenario_id"] for s in dataset.scenarios])


def _text(value):
    """A field as the JSON text the database stores, to compare two fields exactly."""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def deduplicate(courses, base):
    """Set the fields of the course records [{scenario_id, outcome, events,
    alerts, observations}] of one patient to None where they equal those of
    the base scenario. The records are changed in place and returned."""
    reference = next((c for c in courses if c["scenario_id"] == base), None)
    if reference is not None:
        texts = {f: _text(reference[f]) for f in FIELDS}
        for c in courses:
            if c is not reference:
                for f in FIELDS:
                    if c[f] is not None and _text(c[f]) == texts[f]:
                        c[f] = None
    return courses


def full(queryset, dataset, *fields):
    """The course rows with annotations full_<field>: the field of the row or,
    where it is NULL, the field of the base scenario of the same patient.
    The base is looked up with the unique index on (patient, scenario)."""
    base = base_of(dataset)
    annotations = {}
    for f in fields:
        from_base = Subquery(Course.objects.filter(patient=OuterRef("patient"), scenario_id=base).values(f)[:1])
        annotations[f"full_{f}"] = Coalesce(f, from_base, output_field=JSONField())
    return queryset.annotate(**annotations)


def full_values(queryset, dataset, *names):
    """values_list() of course rows in which the names of the four fields stand
    for their complete values; other names (e.g. patient__patient_id) as they are."""
    wanted = [n for n in names if n in FIELDS]
    return full(queryset, dataset, *wanted).values_list(*(f"full_{n}" if n in FIELDS else n for n in names))


def _sql(statement, params):
    """Run one SQL statement."""
    with connection.cursor() as cursor:
        cursor.execute(statement, params)


def _remove_duplicates(dataset, base):
    """Set to NULL every field of the dataset's non-base courses that is
    identical to the field of the base course of the same patient."""
    course, patient = Course._meta.db_table, Patient._meta.db_table
    for f in FIELDS:
        _sql(f"""UPDATE {course} SET {f} = NULL
                 WHERE scenario_id != %s AND {f} IS NOT NULL
                   AND patient_id IN (SELECT id FROM {patient} WHERE dataset_id = %s)
                   AND {f} = (SELECT b.{f} FROM {course} b
                              WHERE b.patient_id = {course}.patient_id AND b.scenario_id = %s)""",
             [base, dataset.pk, base])


def _copy_from_base(dataset, base):
    """Fill every NULL field of the dataset's non-base courses with the field of
    the base course of the same patient, so that no course needs the base."""
    course, patient = Course._meta.db_table, Patient._meta.db_table
    for f in FIELDS:
        _sql(f"""UPDATE {course} SET {f} = (SELECT b.{f} FROM {course} b
                                         WHERE b.patient_id = {course}.patient_id AND b.scenario_id = %s)
                 WHERE scenario_id != %s AND {f} IS NULL
                   AND patient_id IN (SELECT id FROM {patient} WHERE dataset_id = %s)""",
             [base, base, dataset.pk])


def delete_scenario(dataset, scenario_id, remaining):
    """Delete the courses of one scenario. If it is the base, its fields go to
    the courses that refer to them first, the first remaining scenario becomes
    the base, and the duplicates against it are removed. Returns the base after
    the deletion. Must run inside a transaction; the caller stores the base in
    the metadata of the data set."""
    base = base_of(dataset)
    if scenario_id == base:
        _copy_from_base(dataset, base)
    Course.objects.filter(patient__dataset=dataset, scenario_id=scenario_id).delete()
    if scenario_id != base:
        return base
    new_base = choose_base(remaining)
    _remove_duplicates(dataset, new_base)
    return new_base


def compress(dataset):
    """Remove the duplicates of a data set stored before deduplication, and note
    its base. Returns the base."""
    base = base_of(dataset)
    _remove_duplicates(dataset, base)
    return base
