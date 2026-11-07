from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from .services import summarize

PERIODS = (1, 7, 30)


@staff_member_required
def dashboard(request):
    try:
        days = int(request.GET.get('days', 7))
    except ValueError:
        days = 7
    if days not in PERIODS:
        days = 7
    return render(request, "monitoring/dashboard.html", {
        "title": "Monitoring", "summary": summarize(days), "periods": PERIODS})
