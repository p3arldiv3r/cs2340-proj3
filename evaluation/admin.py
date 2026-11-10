from django.contrib import admin
from .models import EvaluationRun, EvaluationResult


class EvaluationResultInline(admin.TabularInline):
    model = EvaluationResult
    extra = 0
    can_delete = False
    readonly_fields = ("position", "question", "expected", "actual", "source_ids", "passed", "feedback")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(EvaluationRun)
class EvaluationRunAdmin(admin.ModelAdmin):
    list_display = ("id", "created_at", "passed", "total", "accuracy")
    readonly_fields = ("created_at", "passed", "total")
    inlines = (EvaluationResultInline,)

    def has_add_permission(self, request):
        return False


@admin.register(EvaluationResult)
class EvaluationResultAdmin(admin.ModelAdmin):
    list_display = ("question", "run", "passed")
    list_filter = ("passed",)
    readonly_fields = ("run", "position", "question", "expected", "actual", "source_ids", "passed", "feedback")

    def has_add_permission(self, request):
        return False
