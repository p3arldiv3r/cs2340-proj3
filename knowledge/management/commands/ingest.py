from django.core.management.base import BaseCommand, CommandError
from knowledge.ingestion import IngestionError, INGESTORS
from knowledge.models import Source
from knowledge.pipeline import ingest_source

class Command(BaseCommand):
    help = 'Load a file or web page into the searchable knowledge base.'
    def add_arguments(self, parser):
        parser.add_argument('method', choices=INGESTORS)
        parser.add_argument('location')
    def handle(self, method, location, **options):
        source = Source.objects.filter(method=method, location=location).first() or Source(method=method, location=location)
        try:
            count = ingest_source(source)
        except (IngestionError, OSError) as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(self.style.SUCCESS(f'Loaded {count} documents.'))
