from django.urls import path

from . import views


app_name = "knowledge"

urlpatterns = [
    path("", views.manage, name="manage"),
]
