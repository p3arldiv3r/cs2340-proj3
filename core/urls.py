from django.urls import path

from . import views


app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("activities/", views.activities, name="activities"),
    path("help/", views.help_page, name="help"),
]
