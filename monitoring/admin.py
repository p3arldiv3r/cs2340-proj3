from django.contrib import admin
from .models import QueryLog


@admin.register(QueryLog)
class QueryLogAdmin(admin.ModelAdmin):
    list_display = ['created_at', 'channel', 'latency_ms', 'succeeded', 'source_count', 'error_type']
    list_filter = ['succeeded', 'channel', 'created_at']
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
