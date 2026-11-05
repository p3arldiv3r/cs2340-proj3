"""Ingestion method 2: data files we provide.

Supported file types:
- .txt / .md: the whole file is one document. A first-line markdown heading
  ("# Title") becomes the title; otherwise the file name does.
- .csv: one document per row. Needs a text column ("text", "description",
  "body" or "content"); "title", "id" and any other columns are optional.
- .json: a list of records (or {"records": [...]}), same fields as CSV.
"""

import csv
import io
import json
from pathlib import Path

from .base import IngestionError, Ingestor, RawDocument


TEXT_FIELDS = ("text", "description", "body", "content")
SUPPORTED_TYPES = (".txt", ".md", ".csv", ".json")


def _read(file):
    """Return (name, text) for a path or an uploaded file object."""
    if isinstance(file, (str, Path)):
        path = Path(file)
        try:
            data = path.read_bytes()
        except FileNotFoundError:
            raise IngestionError(f"File not found: {path}")
        name = path.name
    else:
        # Django UploadedFile, or any open file with .name and .read().
        if hasattr(file, "seek"):
            file.seek(0)
        data = file.read()
        name = Path(file.name).name
    if isinstance(data, bytes):
        # utf-8-sig drops the byte-order mark Excel adds to CSV exports.
        data = data.decode("utf-8-sig", errors="replace")
    return name, data


def _title_from_name(name):
    return Path(name).stem.replace("_", " ").replace("-", " ").strip().capitalize()


class FileUploadIngestor(Ingestor):
    method = "upload"

    def fetch(self, file):
        """file is a path, or an uploaded file object (anything with .name and .read())."""
        name, data = _read(file)
        suffix = Path(name).suffix.lower()

        if suffix in (".txt", ".md"):
            yield self._text_file(name, data)
        elif suffix == ".csv":
            yield from self._records(list(csv.DictReader(io.StringIO(data))), name)
        elif suffix == ".json":
            yield from self._records(self._json_records(name, data), name)
        else:
            raise IngestionError(
                f"Can't ingest {name}: supported file types are {', '.join(SUPPORTED_TYPES)}."
            )

    def _text_file(self, name, data):
        title = _title_from_name(name)
        first_line = data.lstrip().split("\n", 1)[0].strip()
        if first_line.startswith("# "):
            title = first_line[2:].strip()
        return RawDocument(title=title, text=data, method=self.method, location=name, external_id=name)

    def _json_records(self, name, data):
        try:
            payload = json.loads(data)
        except json.JSONDecodeError as exc:
            raise IngestionError(f"{name} is not valid JSON: {exc}")
        if isinstance(payload, dict):
            payload = payload.get("records", payload.get("results"))
        if not isinstance(payload, list) or not all(isinstance(r, dict) for r in payload):
            raise IngestionError(f"{name} must contain a list of records (objects).")
        return payload

    def _records(self, records, name):
        for i, record in enumerate(records, start=1):
            # Header case and stray spaces vary between spreadsheets.
            record = {str(k).strip().lower(): v for k, v in record.items() if k is not None}
            text_field = next((f for f in TEXT_FIELDS if f in record), None)
            if text_field is None:
                raise IngestionError(
                    f"{name} record {i} has no text column. Add one named {', '.join(TEXT_FIELDS)}."
                )
            text = str(record.pop(text_field) or "")
            for other in TEXT_FIELDS:
                record.pop(other, None)
            if not text.strip():
                continue
            title = str(record.pop("title", "") or f"{_title_from_name(name)} {i}")
            yield RawDocument(
                title=title,
                text=text,
                method=self.method,
                location=name,
                external_id=str(record.pop("id", "") or f"{name}#{i}"),
                metadata=record,
            )
