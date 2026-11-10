from django.urls import path

from . import views

app_name = "evaluation"

urlpatterns = [
    path("", views.runs, name="runs"),
    path("run/", views.execute, name="execute"),
]
