from django.shortcuts import render
from knowledge.models import Document


def activity_documents():
    return Document.objects.exclude(metadata={}).filter(metadata__has_key='format').select_related('source').order_by('pk')


def home(request):
    return render(request, "core/home.html", {"title": "Home", "activities": activity_documents()[:3]})


def activities(request):
    return render(request, 'core/activities.html', {'title': 'Activities', 'activities': activity_documents()})


def help_page(request):
    return render(request, 'core/help.html', {'title': 'Help'})
