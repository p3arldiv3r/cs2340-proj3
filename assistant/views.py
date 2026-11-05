from django.shortcuts import render


def chat(request):
    # TODO: replace this placeholder page.
    return render(request, "assistant/chat.html", {"title": "Your assistant"})
