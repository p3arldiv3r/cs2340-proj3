"""Staff-only evaluation dashboard and CSRF-protected evaluation action."""
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from .models import EvaluationRun
from .runner import run_evaluation


@staff_member_required
def runs(request):
    latest = EvaluationRun.objects.prefetch_related("results").first()
    results = list(latest.results.all()) if latest else []
    return render(request, "evaluation/runs.html", {
        "title": "Response Evaluation",
        "latest": latest,
        "results": results,
        "recent_results": results[:5],
    })


@staff_member_required
@require_POST
def execute(request):
    try:
        run = run_evaluation()
    except ValueError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, f"Evaluation finished: {run.passed} of {run.total} checks passed.")
    return redirect("evaluation:runs")
