from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path("", include("core.urls")),
    path("assistant/", include("assistant.urls")),
    path("knowledge/", include("knowledge.urls")),
    path("evaluation/", include("evaluation.urls")),
    path("monitoring/", include("monitoring.urls")),
    path("admin/", admin.site.urls),
]
