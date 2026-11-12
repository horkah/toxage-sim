from django.urls import path

from . import views

urlpatterns = [
    path("", views.explorer, name="explorer"),
    path("random/", views.random_patient, name="random"),
    path("disclaimer/", views.disclaimer, name="disclaimer"),
    path("disclaimer/revoke/", views.revoke, name="revoke"),
]
