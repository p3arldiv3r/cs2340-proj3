import logging
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods
from .ingestion import IngestionError
from .models import Source, Document, Chunk
from .pipeline import clear_knowledge_base, reload_knowledge_base

logger = logging.getLogger(__name__)


@staff_member_required
@require_http_methods(['GET', 'POST'])
def manage(request):
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'clear':
            clear(request)
        elif action == 'reload':
            reload(request)
        else:
            messages.error(request, 'Unknown action.')
        return redirect('knowledge:manage')
    sources = Source.objects.annotate(document_count=Count('documents')).order_by('method', 'location')
    return render(request, "knowledge/manage.html", {
        "title": "Knowledge base", "sources": sources,
        "document_count": Document.objects.count(), "chunk_count": Chunk.objects.count()})


def clear(request):
    if request.POST.get('confirm') != 'yes':
        messages.error(request, 'Tick the confirmation box to clear the knowledge base.')
        return
    documents = Document.objects.count()
    if request.POST.get('forget_sources') == 'yes':
        Source.objects.all().delete()
        messages.success(request, f'Cleared {documents} documents and removed all sources.')
    else:
        clear_knowledge_base()
        messages.success(request, f'Cleared {documents} documents. Sources are kept, so you can reload them.')
    logger.info('Knowledge base cleared by %s', request.user)


def reload(request):
    if not Source.objects.exists():
        messages.error(request, 'There are no sources to reload. Add one with the ingest command first.')
        return
    try:
        count = reload_knowledge_base()
    except (IngestionError, OSError) as exc:
        logger.exception('Knowledge base reload failed')
        messages.error(request, f'Reload failed, so the existing documents were kept: {exc}')
        return
    messages.success(request, f'Reloaded {count} documents from {Source.objects.count()} sources.')
    logger.info('Knowledge base reloaded by %s', request.user)
