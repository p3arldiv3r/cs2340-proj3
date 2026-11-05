# Testing: data ingestion

**Story:** As a Developer, I want to ingest data using at least two distinct
ingestion methods (e.g., API-based ingestion, document scraping, or direct
text/file uploads) so I can build a rich and flexible knowledge base.

**Branch:** `ingestion`

## What was built

Two ingestion methods in `knowledge/ingestion/`. Both produce the same output, a
list of `RawDocument`s, so the rest of the pipeline doesn't care where data came from.

| Method | File | Input | Output |
|---|---|---|---|
| Web scraping | `web.py` | A web page URL | 1 document per page: readable text only (no scripts, nav, header, footer, forms); prefers `<main>`/`<article>`; respects `robots.txt` |
| File upload | `upload.py` | A file path or a Django uploaded file | `.txt`/`.md`: 1 document per file. `.csv`: 1 per row. `.json`: 1 per record |

Ingestion does **not** clean text or save to the database:
- Cleaning and chunking belong to the preprocessing story (`knowledge/preprocessing.py`).
- Storing belongs to the dataset story (`knowledge/models.py`).

Ingestion hands both of them `RawDocument`s.

### The hand-off format: `RawDocument`

```python
@dataclass
class RawDocument:
    title: str         # page <title>, CSV "title" column, or "# heading"
    text: str          # raw text, NOT cleaned yet
    method: str        # "web" or "upload"
    location: str      # URL, or file name
    external_id: str   # URL, CSV/JSON "id", or "file.csv#3" if no id
    metadata: dict     # every other CSV column / JSON key
```

### Using it in your story

```python
from knowledge.ingestion import IngestionError, get_ingestor

try:
    docs = list(get_ingestor("upload").fetch("sample_data/programs.csv"))
    docs += list(get_ingestor("web").fetch("https://example.org/page"))
except IngestionError as exc:
    # exc has a plain-language message, safe to show an admin
    ...

# From a Django upload form:
docs = list(get_ingestor("upload").fetch(request.FILES["file"]))
```

### Data file format rules

- **CSV/JSON:** each row needs a text field named `text`, `description`, `body` or
  `content`. `title` and `id` are optional. Every other column becomes metadata.
- **Headers:** case and extra spaces don't matter (` Title ` works). An Excel
  byte-order mark is handled.
- **Empty rows:** rows with empty text are skipped.
- **JSON shape:** either a list of objects, or `{"records": [...]}` /
  `{"results": [...]}`.
- **Errors:** any other file type, a missing text column, or invalid JSON
  raises `IngestionError` with a message saying what to fix.

## 1. Automated tests

From the repo root:

```
python manage.py test knowledge.test_ingestion
```

Expected: `Ran 40 tests ... OK`. The tests never use the internet. Web
requests are replaced with a fake response, so they pass offline and on any
machine.

They cover:
- Both methods are registered.
- CSV, JSON, Markdown, plain text, and Django uploaded files.
- Messy CSVs: Excel byte-order mark, header case, empty rows, missing id/title.
- Error messages: missing text column, bad JSON, wrong file type, missing file.
- HTML extraction: main content kept; nav, footer, scripts, styles and asides dropped.
- Scraping: title fallback, plain-text pages, non-text content, HTTP errors,
  unreachable sites, non-web addresses.
- robots.txt: rules followed, fetched with our user agent, missing / forbidden /
  unreachable handled; the check can be turned off.
- The `preview_ingest` command, including JSON export.

## 2. Manual check (about 5 minutes)

`preview_ingest` runs an ingestion method and prints what it found. It saves
nothing.

**a. File upload, all four file types**

```
python manage.py preview_ingest upload sample_data/programs.csv sample_data/programs.json sample_data/book_circle.md sample_data/faq.txt
```

Expect `Total: 10 document(s)`:
- `programs.csv` → 5 documents, first one `Afternoon Book Circle [prog-001]`
  with metadata `{'format': 'Online', 'time_of_day': 'Afternoon', 'cost': 'Free'}`
- `programs.json` → 3 documents (`prog-101` to `prog-103`)
- `book_circle.md` → 1 document titled `Afternoon Book Circle: how it works`
- `faq.txt` → 1 document titled `Faq`. Its text still has messy whitespace and
  the copyright line; that is expected, because cleaning is the preprocessing story.

**b. Web scraping, offline, against a local server**

Terminal 1:
```
python -m http.server 8765 -d sample_data
```
Terminal 2:
```
python manage.py preview_ingest web http://localhost:8765/sample_page.html
```

Expect 1 document titled `Garden Walk Club | Sample Community Network`.

- **Included:** the walk description, "tea & conversation", "step-free", "$2 per walk".
- **Not included:** "Home", "Programs", "About", "Contact", "newsletter",
  the copyright line, or any CSS/JavaScript.

Then try a page that doesn't exist:
```
python manage.py preview_ingest web http://localhost:8765/missing.html
```
Expect `CommandError: ... returned HTTP 404 (File not found).` with no traceback.
Stop the server with Ctrl+C.

**c. Web scraping, a real site (optional, needs internet)**

```
python manage.py preview_ingest web https://en.wikipedia.org/wiki/Social_isolation
```
Expect 1 document titled `Social isolation - Wikipedia`, starting with the
article text. Some sites refuse scrapers:
- If a site's robots.txt blocks them, you'll see a message saying it was
  skipped. That's correct behavior.
- If a site's bot protection blocks them, you'll see an HTTP error such as
  `405 (Not Allowed)`. For example, nia.nih.gov does this.

**d. Export for your own story**

```
python manage.py preview_ingest upload sample_data/programs.csv --json docs.json
```
`docs.json` holds the documents in the exact `RawDocument` shape. Use it as
fixture data while building preprocessing, storage or retrieval. Don't commit it.

## Done checklist

- [ ] `python manage.py test knowledge.test_ingestion` passes
- [ ] Manual check (a) shows 10 documents with the right titles and IDs
- [ ] Manual check (b) shows only the main page content, and a clean 404 message
- [ ] Two distinct methods (web scraping + file upload) produce the same `RawDocument` format

## Known limits / follow-ups

- **One page per URL:** the scraper doesn't follow links. Pass several URLs to
  scrape several pages.
- **No JavaScript:** pages built with JavaScript come back mostly empty.
- **File types:** no PDF or Word support. That would need a new dependency (e.g. `pypdf`).
- **Large files:** a file is read into memory all at once. That's fine for
  class-sized data, but very large files should be streamed.
