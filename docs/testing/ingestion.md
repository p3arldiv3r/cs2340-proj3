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
| File upload | `upload.py` | A file path or a Django uploaded file | `.txt`/`.md`: 1 document per file. `.csv`: 1 per row. `.json`: 1 per record. `.html`/`.htm` (a page saved from a browser): 1 document, extracted exactly like the scraper |

Ingestion does **not** clean text or save to the database:
- Cleaning and chunking belong to the preprocessing story (`knowledge/preprocessing.py`).
- Storing belongs to the dataset story (`knowledge/models.py`).

Ingestion hands both of them `RawDocument`s.

### When a site blocks the scraper

Many sites run bot protection that turns away any automated visitor, whatever
robots.txt says. Four of the team's seven articles do (checked 2026-11-05):

| Article | Result |
|---|---|
| WHO, both PMC papers (Ashley's, Lily's) | Scrape fine |
| CDC (Aditi) | Blocked (Akamai, HTTP 403). Saved from Chrome and uploaded: works (see check d) |
| Michigan Medicine (Lily) | Blocked (Cloudflare, HTTP 403) |
| NIA (Vinisha) | Blocked (CloudFront, HTTP 405) |
| canada.ca (Benita) | Connection hangs until it times out |

For these, use the upload method instead: open the article in a browser, use
**File > Save Page As** (Chrome: "Webpage, HTML only"; Firefox: "Web Page,
HTML only"), and upload the `.html` file. You get the same text as scraping,
and the article's real URL is read from the saved file (`metadata["url"]`), so
citations still link to the original page. We don't try to get past bot
protection.

The error messages tell these cases apart:
- the site's robots.txt rules forbid the page ("off-limits to scrapers in the
  site's robots.txt")
- the site blocks automated access, an HTTP 401/403/405/429, or a timeout:
  the message suggests Save Page As
- anything else, such as a 404, is a plain HTTP error

### The hand-off format: `RawDocument`

```python
@dataclass
class RawDocument:
    title: str         # page <title>, CSV "title" column, or "# heading"
    text: str          # raw text, NOT cleaned yet
    method: str        # "web" or "upload"
    location: str      # URL, or file name
    external_id: str   # URL, CSV/JSON "id", or "file.csv#3" if no id
    metadata: dict     # every other CSV column / JSON key; "url" for saved .html pages
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

Expected: `Ran 51 tests ... OK`. The tests never use the internet. Web
requests are replaced with a fake response, so they pass offline and on any
machine.

They cover:
- Both methods are registered.
- CSV, JSON, Markdown, plain text, saved `.html` pages, and Django uploaded files.
- Finding a saved page's real URL ("saved from" comment, canonical link, og:url).
- Messy CSVs: Excel byte-order mark, header case, empty rows, missing id/title.
- Error messages: missing text column, bad JSON, wrong file type, missing file.
- HTML extraction: main content kept; nav, footer, scripts, styles and asides dropped.
- Scraping: title fallback, plain-text pages, non-text content, HTTP errors,
  unreachable sites, non-web addresses.
- robots.txt: rules followed, fetched with our user agent, missing / unreachable
  allowed; a forbidden robots.txt reported as "blocks automated access", not as
  a robots.txt rule; the check can be turned off.
- Bot-blocking status codes (401/403/405/429) and timeouts suggest Save Page As;
  ordinary errors like 404 don't.
- The `preview_ingest` command, including JSON export.

## 2. Manual check (about 5 minutes)

`preview_ingest` runs an ingestion method and prints what it found. It saves
nothing.

**a. File upload: text, Markdown, CSV and JSON**

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

**c. Web scraping, the team's real articles (optional, needs internet)**

```
python manage.py preview_ingest web https://www.who.int/activities/reducing-social-isolation-and-loneliness-among-older-people
python manage.py preview_ingest web https://www.cdc.gov/social-connectedness/improving/index.html
```
- **WHO:** expect 1 document titled `Reducing social isolation and loneliness
  among older people`.
- **CDC:** expect `CommandError: www.cdc.gov blocks automated access ...` with
  the Save Page As suggestion. It should not mention robots.txt.

**d. Saved page upload (the fix for blocked sites)**

1. Open https://www.cdc.gov/social-connectedness/improving/index.html in your browser.
2. Use File > Save Page As, "Webpage, HTML only". Save it anywhere outside the repo.
3. Run:
```
python manage.py preview_ingest upload "<path to the saved .html file>"
```
Expect:
- 1 document with the CDC article's title
- article text only, with no site menu or footer
- usually `metadata: {'url': 'https://www.cdc.gov/...'}`, read from the saved
  file's "saved from url" comment or the page's canonical link

If the metadata line is missing, the saved file didn't record the URL. The
document is still ingested, with the file name as its ID.

**Verified 2026-11-05 with Chrome on Windows.** The CDC page saved with Ctrl+S
gave a 734 KB file. That's much bigger than the page's original 48 KB, because
Chrome saves the page as displayed, including UI injected by browser
extensions. Uploading it gave:
- title `Improving Social Connectedness | Social Connection | CDC`
- `metadata: {'url': 'https://www.cdc.gov/social-connectedness/improving/index.html'}`,
  read from both the "saved from url" comment and the canonical link
- the full article, every section from "Building social connections matters"
  to "Things parents can do"
- no site menu, and nothing from the browser extension

Share buttons and the feedback widget did come through; preprocessing removes
them.

**e. Export for your own story**

```
python manage.py preview_ingest upload sample_data/programs.csv --json docs.json
```
`docs.json` holds the documents in the exact `RawDocument` shape. Use it as
fixture data while building preprocessing, storage or retrieval. Don't commit it.

## Done checklist

- [ ] `python manage.py test knowledge.test_ingestion` passes
- [ ] Manual check (a) shows 10 documents with the right titles and IDs
- [ ] Manual check (b) shows only the main page content, and a clean 404 message
- [ ] Manual check (d): a page saved from a blocked site ingests via upload, with its real URL
- [ ] Two distinct methods (web scraping + file upload) produce the same `RawDocument` format

## Known limits / follow-ups

- **One page per URL:** the scraper doesn't follow links. Pass several URLs to
  scrape several pages.
- **No JavaScript:** pages built with JavaScript come back mostly empty. Saving
  with "Webpage, Complete" may capture them after the browser has run the
  JavaScript, but that hasn't been tested.
- **Blocked sites need a person:** someone has to save each blocked page by hand.
  Re-save it when the article changes.
- **File types:** no PDF or Word support. That would need a new dependency (e.g. `pypdf`).
- **Large files:** a file is read into memory all at once. That's fine for
  class-sized data, but very large files should be streamed.
