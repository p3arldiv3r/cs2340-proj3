from dataclasses import dataclass, field


@dataclass
class RawDocument:
    """One document as it comes out of an ingestion method, before cleaning.

    This is the hand-off format between stories: preprocessing cleans and
    chunks `text`, and the dataset models store the result.
    """

    title: str
    text: str
    # Which ingestion method produced it: "web" or "upload".
    method: str
    # The URL or file name it came from.
    location: str
    # Stable ID within the source (the URL, a CSV row's id, ...). Shown to users
    # as the "record ID" in the source panel (DESIGN.md 5.4).
    external_id: str = ""
    # Any extra fields from the source (CSV columns, JSON keys, ...).
    metadata: dict = field(default_factory=dict)


class IngestionError(Exception):
    """Raised with a plain-language message when a source can't be ingested."""


class Ingestor:
    """Base class for an ingestion method."""

    method = None

    def fetch(self, location):
        """Yield RawDocuments from location (a URL or a file)."""
        raise NotImplementedError
