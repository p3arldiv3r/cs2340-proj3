class Ingestor:
    """Base class for an ingestion method (file upload, web scrape, API, ...)."""

    def fetch(self, source):
        """Yield raw documents from a source."""
        raise NotImplementedError
