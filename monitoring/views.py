from django.shortcuts import render


def dashboard(request):
    # TODO: replace this placeholder page.
    return render(request, "monitoring/dashboard.html", {"title": "Monitoring"})
