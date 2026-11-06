"""Fetch and prepare before atomically replacing a source's documents."""
from django.db import transaction
from .ingestion import get_ingestor
from .models import Source, Document, Chunk
from .preprocessing import clean_text, preprocess, content_hash

def ingest_source(source):
    prepared = [(raw, preprocess(raw.text)) for raw in get_ingestor(source.method).fetch(source.location)]
    with transaction.atomic():
        source.save()
        source.documents.all().delete()
        for raw, chunks in prepared:
            if not chunks:
                continue
            document = Document.objects.create(source=source, external_id=raw.external_id,
                title=clean_text(raw.title), text=clean_text(raw.text),
                metadata=raw.metadata, content_hash=content_hash(raw.text))
            Chunk.objects.bulk_create([Chunk(document=document, position=i, text=text) for i, text in enumerate(chunks)])
    return sum(bool(chunks) for _, chunks in prepared)

def clear_knowledge_base():
    Document.objects.all().delete()

def reload_knowledge_base():
    with transaction.atomic():
        return sum(ingest_source(source) for source in Source.objects.all())
