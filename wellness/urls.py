from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "Garden administration"
admin.site.site_title = "Garden administration"
admin.site.index_title = "Staff tools"


urlpatterns = [
    path("", include("core.urls")),
    path("assistant/", include("assistant.urls")),
    path("knowledge/", include("knowledge.urls")),
    path("evaluation/", include("evaluation.urls")),
    path("monitoring/", include("monitoring.urls")),
    path("admin/", admin.site.urls),
]
