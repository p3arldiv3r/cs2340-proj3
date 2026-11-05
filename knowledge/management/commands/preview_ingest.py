import json
from dataclasses import asdict

from django.core.management.base import BaseCommand, CommandError

from knowledge.ingestion import INGESTORS, IngestionError, get_ingestor


class Command(BaseCommand):
    help = (
        "Run an ingestion method and print the documents it finds. Nothing is "
        "saved to the database.\n"
        "  manage.py preview_ingest upload sample_data/programs.csv\n"
        "  manage.py preview_ingest web https://example.org/page --json out.json"
    )

    def add_arguments(self, parser):
        parser.add_argument("method", choices=list(INGESTORS))
        parser.add_argument("locations", nargs="+", help="File paths (upload) or URLs (web).")
        parser.add_argument("--json", dest="json_path", help="Also write the documents to this JSON file.")
        parser.add_argument("--full", action="store_true", help="Print each document's full text.")
        parser.add_argument("--ignore-robots", action="store_true",
                            help="web only: skip the robots.txt check (only for sites you run).")

    def handle(self, method, locations, json_path, full, ignore_robots, **options):
        ingestor = get_ingestor(method, check_robots=False) if method == "web" and ignore_robots \
            else get_ingestor(method)

        documents = []
        for location in locations:
            try:
                found = list(ingestor.fetch(location))
            except IngestionError as exc:
                raise CommandError(str(exc))
            self.stdout.write(self.style.MIGRATE_HEADING(f"{location}: {len(found)} document(s)"))
            for doc in found:
                text = doc.text.strip()
                preview = text if full else " ".join(text.split())[:300]
                self.stdout.write(f"\n  {doc.title}  [{doc.external_id}]  {len(doc.text)} chars")
                if doc.metadata:
                    self.stdout.write(f"  metadata: {doc.metadata}")
                self.stdout.write(f"  {preview}{'' if full or len(preview) < 300 else '...'}")
            documents.extend(found)

        if json_path:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump([asdict(d) for d in documents], f, indent=2, ensure_ascii=False)
            self.stdout.write(f"\nWrote {json_path}")
        self.stdout.write(self.style.SUCCESS(f"\nTotal: {len(documents)} document(s)"))
