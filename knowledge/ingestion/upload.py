"""Ingestion method 2: data files we provide (e.g. .txt, .csv)."""

from .base import Ingestor


class FileUploadIngestor(Ingestor):
    def fetch(self, source):
        raise NotImplementedError
