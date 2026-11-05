from django.shortcuts import render


def manage(request):
    # TODO: replace this placeholder page.
    return render(request, "knowledge/manage.html", {"title": "Knowledge base"})
