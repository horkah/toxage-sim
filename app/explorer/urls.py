from django.urls import path

from . import pages, tour, views

urlpatterns = [
    path("", views.explorer, name="explorer"),
    path("random/", views.random_patient, name="random"),
    path("data/", pages.data, name="data"),
    path("data/generate/", pages.data_generate, name="data_generate"),
    path("data/delete/", pages.data_delete, name="data_delete"),
    path("data/use/", pages.data_use, name="data_use"),
    path("data/<int:pk>/records/", pages.records, name="records"),
    path("data/<int:pk>/export/<str:table>.csv", pages.export, name="export"),
    path("data/archive/", pages.archive_export, name="archive"),
    path("data/<int:pk>/archive/", pages.archive_export, name="archive_dataset"),
    path("data/import/", pages.archive_import, name="archive_import"),
    path("parameters/", pages.parameters, name="parameters_start"),
    path("parameters/<str:key>/", pages.parameters, name="parameters"),
    path("schema/", pages.schema, name="schema"),
    path("documents/", pages.documents, name="documents"),
    path("documents/<str:key>/", pages.documents, name="document"),
    path("tour/state/", tour.state, name="tour_state"),
    path("tour/snapshot/", tour.snapshot, name="tour_snapshot"),
    path("tour/restore/", tour.restore, name="tour_restore"),
    path("about/", views.about, name="about"),
    path("disclaimer/", views.disclaimer, name="disclaimer"),
    path("disclaimer/revoke/", views.revoke, name="revoke"),
]
