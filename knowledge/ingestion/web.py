"""Ingestion method 1: scrape web pages."""

from .base import Ingestor


class WebScrapeIngestor(Ingestor):
    def fetch(self, source):
        raise NotImplementedError
