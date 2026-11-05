from django.shortcuts import render


def home(request):
    # TODO: replace this placeholder page.
    return render(request, "core/home.html", {"title": "Home"})
