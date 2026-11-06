import sys
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from knowledge.preprocessing import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    chunk_text,
    clean_text,
    content_hash,
    is_useful,
)


class Command(BaseCommand):
    help = (
        "Show what preprocessing does to a text file: the cleaned text and the "
        "chunks it is split into. Nothing is saved.\n"
        "  manage.py preview_preprocess sample_data/messy_page.txt --size 300"
    )

    def add_arguments(self, parser):
        parser.add_argument("path")
        parser.add_argument("--size", type=int, default=CHUNK_SIZE)
        parser.add_argument("--overlap", type=int, default=CHUNK_OVERLAP)

    def handle(self, path, size, overlap, **options):
        # Windows consoles can't print every character; show "?" instead of crashing.
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(errors="replace")
        try:
            raw = Path(path).read_text(encoding="utf-8-sig", errors="replace")
        except FileNotFoundError:
            raise CommandError(f"File not found: {path}")

        cleaned = clean_text(raw)
        self.stdout.write(self.style.MIGRATE_HEADING("Cleaned text"))
        self.stdout.write(cleaned or "(empty)")
        self.stdout.write(f"\n{len(raw)} chars before, {len(cleaned)} after. Hash {content_hash(raw)[:12]}")

        if not is_useful(cleaned):
            self.stdout.write(self.style.WARNING("\nNot useful: too little content, would be skipped."))
            return

        try:
            chunks = chunk_text(cleaned, size=size, overlap=overlap)
        except ValueError as exc:
            raise CommandError(str(exc))
        self.stdout.write(self.style.MIGRATE_HEADING(f"\n{len(chunks)} chunk(s), size {size}, overlap {overlap}"))
        for i, chunk in enumerate(chunks, start=1):
            self.stdout.write(f"\n--- chunk {i} ({len(chunk)} chars) ---\n{chunk}")
