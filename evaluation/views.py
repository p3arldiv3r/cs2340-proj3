from django.shortcuts import render


def runs(request):
    # TODO: replace this placeholder page.
    return render(request, "evaluation/runs.html", {"title": "Evaluation"})
