from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required


@staff_member_required
def manage(request):
    # TODO: replace this placeholder page.
    return render(request, "knowledge/manage.html", {"title": "Knowledge base"})
