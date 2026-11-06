from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required


@staff_member_required
def runs(request):
    # TODO: replace this placeholder page.
    return render(request, "evaluation/runs.html", {"title": "Evaluation"})
