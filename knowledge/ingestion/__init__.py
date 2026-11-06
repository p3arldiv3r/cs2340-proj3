"""Ingestion methods.

Story: "As a Developer, I want to ingest data using at least two distinct
ingestion methods so I can build a rich and flexible knowledge base."

Our two methods: web scraping (web.py) and data files we provide (upload.py).
Both yield RawDocuments (base.py). See docs/testing/ingestion.md.

    from knowledge.ingestion import get_ingestor
    for doc in get_ingestor("upload").fetch("sample_data/programs.csv"):
        ...
"""

from .base import IngestionError, Ingestor, RawDocument
from .upload import FileUploadIngestor
from .web import WebScrapeIngestor


INGESTORS = {
    FileUploadIngestor.method: FileUploadIngestor,
    WebScrapeIngestor.method: WebScrapeIngestor,
}


def get_ingestor(method, **options):
    """Return an ingestor instance for "web" or "upload"."""
    try:
        return INGESTORS[method](**options)
    except KeyError:
        raise IngestionError(f"Unknown ingestion method {method!r}. Options: {', '.join(INGESTORS)}.")


__all__ = [
    "INGESTORS",
    "FileUploadIngestor",
    "IngestionError",
    "Ingestor",
    "RawDocument",
    "WebScrapeIngestor",
    "get_ingestor",
]
